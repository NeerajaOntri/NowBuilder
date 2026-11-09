"""Download ServiceNow's official Fluent / ServiceNow SDK documentation and add it to nowBuilder.

Where it comes from: ServiceNow publishes the SDK docs (the site servicenow.github.io/sdk) in its public
GitHub repository https://github.com/ServiceNow/sdk, branch `docs-gh-pages`, one folder per SDK version.

What this script does (run from the nowBuilder folder, backend virtual environment active):

    pip install beautifulsoup4 lxml
    python tools/import_fluent_docs.py                # version 4.14.0, the SDK nowBuilder installs flows with
    python tools/import_fluent_docs.py --version 4.15.0

1. `git clone --depth 1 --branch docs-gh-pages https://github.com/ServiceNow/sdk` into a temporary folder.
2. Converts every HTML page of that version to Markdown (headings, tables and code examples kept) into
   backend/docs/servicenow-sdk-fluent/<version>/ - readable in VS Code.
3. Adds the pages to nowBuilder's searchable documentation database (backend/docs/servicenow_corpus.sqlite3,
   SQLite full-text search) under the path servicenow-sdk-fluent/<version>/…, replacing an earlier import.

The AI then finds them with its `search_servicenow_docs` / `read_servicenow_doc` tools.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "https://github.com/ServiceNow/sdk"
BRANCH = "docs-gh-pages"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "backend" / "docs"
CORPUS = DOCS / "servicenow_corpus.sqlite3"


def convert(src: Path, out: Path) -> int:
    from bs4 import BeautifulSoup
    n = 0
    for f in sorted(src.rglob("*.html")):
        rel = f.relative_to(src)
        if rel.parts[0] in ("tags", "category"):
            continue
        soup = BeautifulSoup(f.read_text(encoding="utf-8", errors="ignore"), "lxml")
        art = soup.find("article") or soup.find("main")
        if not art:
            continue
        for t in art.select("nav, .theme-doc-breadcrumbs, .pagination-nav, button, .theme-doc-footer, .hash-link"):
            t.decompose()
        for pre in art.find_all("pre"):
            lines = [ln.get_text() for ln in pre.select(".token-line")]
            code = "\n".join(lines) if lines else pre.get_text()
            pre.replace_with(soup.new_string("\n```\n" + code.rstrip() + "\n```\n"))
        for code in art.find_all("code"):
            code.replace_with(soup.new_string("`" + code.get_text() + "`"))
        for h in art.find_all(re.compile("^h[1-6]$")):
            h.replace_with(soup.new_string("\n" + "#" * int(h.name[1]) + " " + h.get_text().strip() + "\n"))
        for tr in art.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            tr.replace_with(soup.new_string("| " + " | ".join(cells) + " |\n"))
        for li in art.find_all("li"):
            li.insert(0, soup.new_string("\n- "))
        for p in art.find_all(["p", "div"]):
            p.append(soup.new_string("\n"))
        text = re.sub(r"\n{3,}", "\n\n", art.get_text()).strip()
        dest = out / rel.with_suffix(".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text + "\n", encoding="utf-8")
        n += 1
    return n


def index(folder: Path, version: str) -> int:
    con = sqlite3.connect(CORPUS)
    prefix = f"servicenow-sdk-fluent/{version}/"
    con.execute("DELETE FROM docs WHERE path LIKE ?", (prefix + "%",))
    n = 0
    for f in sorted(folder.rglob("*.md")):
        body = f.read_text(encoding="utf-8")
        if len(body) < 200:
            continue
        m = re.search(r"^#\s+(.+)$", body, re.M)
        title = (m.group(1).strip() if m else f.stem) + f" (ServiceNow SDK / Fluent {version})"
        con.execute("INSERT INTO docs(path, title, body) VALUES (?, ?, ?)",
                    (prefix + f.relative_to(folder).as_posix(), title, body))
        n += 1
    total = con.execute("SELECT count(*) FROM docs").fetchone()[0]
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('documents', ?)", (str(total),))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('fluent_sdk_docs', ?)",
                (f"{version} from {REPO} branch {BRANCH}",))
    con.commit()
    con.execute("INSERT INTO docs(docs) VALUES ('optimize')")
    con.commit()
    con.close()
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="4.14.0")
    args = ap.parse_args()
    try:
        import bs4  # noqa: F401
        import lxml  # noqa: F401
    except ImportError:
        print("First run: pip install beautifulsoup4 lxml")
        return 1
    if not shutil.which("git"):
        print("Git is needed to download the docs: install it from https://git-scm.com, then run this again.")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        print(f"1/3 Downloading {REPO} ({BRANCH}) …", flush=True)
        subprocess.run(["git", "clone", "--depth", "1", "--branch", BRANCH, REPO, tmp + "/sdk"], check=True)
        src = Path(tmp) / "sdk" / "docs" / args.version
        if not src.is_dir():
            versions = sorted(p.name for p in (Path(tmp) / "sdk" / "docs").iterdir() if re.match(r"\d", p.name))
            print(f"No docs for {args.version}. Available: {', '.join(versions)}")
            return 1
        out = DOCS / "servicenow-sdk-fluent" / args.version
        if out.exists():
            shutil.rmtree(out)
        print(f"2/3 Converting pages to Markdown in {out} …", flush=True)
        pages = convert(src, out)
    print(f"3/3 Adding them to {CORPUS.name} …", flush=True)
    indexed = index(out, args.version)
    print(f"Done: {pages} pages converted, {indexed} added to nowBuilder's documentation search.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
