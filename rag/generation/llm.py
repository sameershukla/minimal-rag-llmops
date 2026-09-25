"""Step 7: generate the answer with Claude.

Set RAG_OFFLINE=1 to skip the API and return the top chunk instead. Useful for
running the pipeline and retrieval evals without an API key.
"""
import os

import anthropic

_client = None


def generate(prompt: str, cfg: dict) -> dict:
    """Return the answer text and token usage."""
    if os.getenv("RAG_OFFLINE") == "1":
        return _offline(prompt)

    global _client
    _client = _client or anthropic.Anthropic()
    llm = cfg["llm"]
    resp = _client.beta.messages.create(
        model=llm["model"],
        max_tokens=llm["max_tokens"],
        output_config={"effort": llm["effort"]},
        # If the model declines, the API retries on a fallback model within the same call.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        text = "I can't help with that request."
    else:
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return {
        "text": text,
        "model": resp.model,
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "stop_reason": resp.stop_reason,
    }


def _offline(prompt: str) -> dict:
    # First context chunk, minus its "[1] (doc / section)" and breadcrumb lines.
    first = prompt.split("[1] ", 1)[-1].split("\n\n[2]", 1)[0]
    body = " ".join(first.split("\n")[2:])
    text = " ".join(body.split()[:80])
    return {"text": text, "model": "offline-extractive", "input_tokens": 0, "output_tokens": 0, "stop_reason": "offline"}
