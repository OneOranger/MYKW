from aipayment_kb_agent.knowledge.splitter import split_text


def test_split_text_basic():
    text = "a" * 2000
    chunks = split_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    assert all(chunks)
