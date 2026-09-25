"""Step 3: text -> vectors."""
from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache
def _model(name: str) -> SentenceTransformer:
    return SentenceTransformer(name)


def embed(texts: list[str], model_name: str) -> list[list[float]]:
    return _model(model_name).encode(texts, normalize_embeddings=True).tolist()
