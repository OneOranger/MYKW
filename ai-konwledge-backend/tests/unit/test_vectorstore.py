from pathlib import Path

import numpy as np

from aipayment_kb_agent.knowledge.vectorstore import LanceVectorStore


def test_vector_store_add_and_search(tmp_path: Path):
    store = LanceVectorStore(tmp_path / "vectorstores", "knowledge_chunks")
    records = [
        {
            "id": "1",
            "content": "hello world",
            "metadata": {
                "category": "test",
                "collection": "test",
                "doc_title": "a",
                "doc_type": "txt",
                "source": "s1",
                "chunk_index": 1,
                "updated_at": "now",
                "tags": [],
            },
        },
        {
            "id": "2",
            "content": "another text",
            "metadata": {
                "category": "test",
                "collection": "test",
                "doc_title": "b",
                "doc_type": "txt",
                "source": "s2",
                "chunk_index": 1,
                "updated_at": "now",
                "tags": [],
            },
        },
    ]
    vectors = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    store.add(records, vectors)
    hits = store.search(np.array([1.0, 0.0], dtype=np.float32), top_k=1)
    assert hits
    assert hits[0]["record"]["id"] == "1"
