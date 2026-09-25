from eval.metrics import answer_correctness, grounding, recall_at_k
from rag.ingest.chunker import chunk_blocks


def _block(section, text, kind="paragraph"):
    return {"doc": "d", "title": "T", "section": section, "kind": kind, "text": text}


def test_chunks_never_cross_sections():
    chunks = chunk_blocks([_block("A", "one two"), _block("B", "three four")], max_tokens=100)
    assert [c["section"] for c in chunks] == ["A", "B"]
    assert chunks[0]["text"].startswith("T > A")


def test_long_section_is_split_under_limit():
    blocks = [_block("A", "word " * 60) for _ in range(5)]
    chunks = chunk_blocks(blocks, max_tokens=100, overlap=10)
    assert len(chunks) > 1
    assert all(len(c["text"].split()) <= 100 + 10 + 3 for c in chunks)


def test_metrics():
    ctx = [{"doc": "d", "section": "A", "text": "refunds above 500 dollars are blocked"}]
    case = {"doc": "d", "sections": ["A"], "facts": ["500"]}
    assert recall_at_k(ctx, case) == 1.0
    assert grounding("Refunds above 500 dollars are blocked [1].", ctx) == 1.0
    assert grounding("The moon is made of cheese.", ctx) == 0.0
    assert answer_correctness("The limit is $500.", case) == 1.0
