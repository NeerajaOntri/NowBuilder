"""Documentation retrieval checks: independent of external LLM or instance credentials."""
from app.ai.docs import search_docs, read_doc


def test_docs_search_flow_triggers():
    found = search_docs('workflow studio record flow trigger', 5)
    assert found
    assert all('path' in d and 'url' in d for d in found)
    assert any('workflow-studio' in d['path'] for d in found)


def test_docs_read_and_path_safety():
    results = search_docs('ask approval action flow designer', 2)
    doc = read_doc(results[0]['path'])
    assert doc['content'] and doc['title']
    try:
        read_doc('../../.env')
    except ValueError:
        pass
    else:
        raise AssertionError('Traversal should be rejected')
