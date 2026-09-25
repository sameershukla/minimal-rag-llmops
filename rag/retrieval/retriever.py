"""Step 5: fetch candidate chunks for a question."""
from rag.index.vectordb import search


def retrieve(question: str, cfg: dict) -> list[dict]:
    print(f"Retrieving candidate chunks for {question}")
    return search(question, cfg, k=cfg["retrieval"]["top_k"])
