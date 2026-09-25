"""Load the versioned config and give it a fingerprint."""
import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str = "configs/rag.yaml") -> dict:
    cfg = yaml.safe_load((ROOT / path).read_text())
    prompt = (ROOT / "rag/generation/prompts" / f"{cfg['llm']['prompt_version']}.txt").read_text()
    # Fingerprint = hash of config + prompt text. Same fingerprint => same behaviour.
    blob = json.dumps(cfg, sort_keys=True) + prompt
    cfg["fingerprint"] = hashlib.sha256(blob.encode()).hexdigest()[:12]
    return cfg


def index_name(cfg: dict) -> str:
    """Vector collection name tied to what shapes the index (chunking + embedding).

    Changing either one builds a new collection instead of silently mixing old and new vectors.
    """
    key = json.dumps([cfg["chunking"], cfg["embedding"]], sort_keys=True)
    return "docs_" + hashlib.sha256(key.encode()).hexdigest()[:8]
