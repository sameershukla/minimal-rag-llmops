"""Step 4: store and search vectors (Chroma, on local disk)."""
import chromadb

from rag.config import index_name
from rag.index.embedder import embed


def _collection(cfg: dict, reset: bool = False):
    client = chromadb.PersistentClient(path=cfg["vectordb"]["path"])
    name = index_name(cfg)
    if reset:
        try:
            client.delete_collection(name)
        except Exception:
            pass
    return client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


def build_index(chunks: list[dict], cfg: dict) -> str:
    col = _collection(cfg, reset=True)
    col.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embed([c["text"] for c in chunks], cfg["embedding"]["model"]),
        metadatas=[{"doc": c["doc"], "title": c["title"], "section": c["section"]} for c in chunks],
    )
    return col.name


def search(query: str, cfg: dict, k: int) -> list[dict]:
    print(f"Searching {query}")
    col = _collection(cfg)
    if col.count() == 0:
        raise RuntimeError("Index is empty. Run: python main.py ingest")
    res = col.query(query_embeddings=embed([query], cfg["embedding"]["model"]), n_results=k)
    return [
        {"id": i, "text": t, **m, "score": 1 - d}
        for i, t, m, d in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]
