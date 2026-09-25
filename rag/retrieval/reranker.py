"""Step 6: rerank candidates with a cross-encoder (reads question + chunk together)."""
from functools import lru_cache

from sentence_transformers import CrossEncoder


@lru_cache
def _model(name: str) -> CrossEncoder:
    return CrossEncoder(name)


def rerank(question: str, chunks: list[dict], model_name: str, top_n: int) -> list[dict]:
    if not chunks:
        return []
    scores = _model(model_name).predict([(question, c["text"]) for c in chunks])
    for c, s in zip(chunks, scores):
        c["rerank_score"] = float(s)
    return sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)[:top_n]
