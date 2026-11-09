"""Offline, release-specific ServiceNow Australia knowledge retrieval.

The bundled SQLite FTS5 corpus contains document text (not external URLs), so the
model can use documentation even when it cannot browse the internet.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
import sqlite3

DOCS_DIR = Path(__file__).resolve().parents[2] / 'docs'
CORPUS = DOCS_DIR / 'servicenow_corpus.sqlite3'
LEGACY_DIR = DOCS_DIR / 'servicenow-australia'
MAX_DOCUMENT_CHARS = 18000
STOP = {'the','and','for','are','with','from','how','that','this','can','you','want','create','servicenow','please','what','into','when','using','will','your','need','does','have','should','name','named'}


def _db() -> sqlite3.Connection:
    if not CORPUS.is_file():
        raise RuntimeError('The bundled ServiceNow offline knowledge database is missing.')
    return sqlite3.connect(f'file:{CORPUS.as_posix()}?mode=ro', uri=True)


def _query_terms(query: str) -> list[str]:
    words = re.findall(r'[a-zA-Z0-9_]{3,}', query.lower())
    return list(dict.fromkeys(x for x in words if x not in STOP))[:18]


def search_docs(query: str, limit: int = 5) -> list[dict]:
    """Find relevant passages without network requests or loading the full corpus."""
    terms = _query_terms(query)
    if not terms:
        return []
    expression = ' OR '.join('"' + term.replace('"','') + '"' for term in terms)
    count = max(1, min(int(limit), 10))
    with _db() as db:
        rows = db.execute('''
            SELECT path,title,snippet(docs,2,'','',' … ',30),bm25(docs,0,9,1)
            FROM docs WHERE docs MATCH ? ORDER BY bm25(docs,0,9,1) LIMIT ?
        ''', (expression,count * 5)).fetchall()
    # Full text ranking is useful, but prevent a one-word match in a long irrelevant
    # document from displacing pages matching several distinct query concepts.
    ranked = []
    for path,title,excerpt,score in rows:
        hay = (path+' '+title+' '+excerpt).lower()
        coverage = sum(t in hay for t in terms)
        ranked.append((coverage,score,{'path':path,'title':title,'updated':'','url':'',
                                       'excerpt':excerpt.strip()}))
    ranked.sort(key=lambda item:(-item[0],item[1]))
    return [item[2] for item in ranked[:count]]


def read_doc(path: str) -> dict:
    """Read actual documentation by an exact corpus path, never a filesystem path."""
    if not isinstance(path,str) or not path.endswith('.md') or path.startswith('/') or '\\' in path or '..' in Path(path).parts:
        raise ValueError('Invalid documentation path')
    with _db() as db:
        row = db.execute('SELECT title,body FROM docs WHERE path=? LIMIT 1',(path,)).fetchone()
    if row is None:
        raise ValueError('Documentation page not found')
    title,content=row
    return {'path':path,'title':title,'updated':'','url':'',
            'content':content[:MAX_DOCUMENT_CHARS], 'truncated':len(content)>MAX_DOCUMENT_CHARS}


def corpus_stats() -> dict:
    with _db() as db:
        return {'documents':int(db.execute("SELECT value FROM meta WHERE key='documents'").fetchone()[0]),
                'mode':'bundled_offline_text', 'external_network_required':False}
