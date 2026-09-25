"""Versioned prompts: each version is a file in prompts/, chosen by config."""
from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"


def build_prompt(question: str, chunks: list[dict], version: str) -> str:
    template = (PROMPT_DIR / f"{version}.txt").read_text()
    context = "\n\n".join(f"[{i}] ({c['doc']} / {c['section']})\n{c['text']}" for i, c in enumerate(chunks, 1))
    return template.format(context=context, question=question)
