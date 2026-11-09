from app.ai.docs import corpus_stats,search_docs,read_doc

def test_full_corpus_is_available():
    assert corpus_stats()['documents'] >= 50000

def test_cross_topic_lookup():
    for query in ('flow designer triggers', 'CMDB identification reconciliation',
                  'access control rules ACL', 'import set transform map',
                  'service catalog variable', 'GlideRecord addQuery'):
        matches = search_docs(query, 5)
        assert matches, query
        assert read_doc(matches[0]['path'])['content']

def test_rejects_invalid_document_path():
    for path in ('../../.env', '/etc/passwd.md', 'not-present.md'):
        try: read_doc(path)
        except ValueError: pass
        else: raise AssertionError(path)
