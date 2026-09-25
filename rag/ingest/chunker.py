"""Step 2: structure-aware chunking.

Rules:
  * A chunk never crosses a section boundary.
  * Tables and code blocks are kept whole (unless one alone is too big).
  * Each chunk starts with a breadcrumb "Title > Section" so it makes sense on its own.
"""
import hashlib


def _words(text: str) -> int:
    return len(text.split())


def _split_big(text: str, max_words: int) -> list[str]:
    """Split an oversized block on line boundaries, then on words as a last resort."""
    parts, cur = [], []
    for line in text.split("\n"):
        if cur and _words("\n".join(cur + [line])) > max_words:
            parts.append("\n".join(cur))
            cur = []
        cur.append(line)
    if cur:
        parts.append("\n".join(cur))
    out = []
    for p in parts:
        words = p.split(" ")
        out.extend(" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words))
    return out


def chunk_blocks(blocks: list[dict], max_tokens: int = 350, overlap: int = 40) -> list[dict]:
    chunks: list[dict] = []
    sections: dict[tuple, list[dict]] = {}
    for b in blocks:  # dicts keep insertion order, so document order is preserved
        sections.setdefault((b["doc"], b["title"], b["section"]), []).append(b)

    for (doc, title, section), items in sections.items():
        header = f"{title} > {section}"
        pieces: list[str] = []
        for b in items:
            pieces.extend(_split_big(b["text"], max_tokens) if _words(b["text"]) > max_tokens else [b["text"]])

        buf: list[str] = []
        for piece in pieces:
            if buf and _words("\n".join(buf)) + _words(piece) > max_tokens:
                chunks.append(_make(doc, title, section, header, buf))
                tail = " ".join("\n".join(buf).split()[-overlap:]) if overlap else ""
                buf = [tail] if tail else []
            buf.append(piece)
        if buf:
            chunks.append(_make(doc, title, section, header, buf))
    return chunks


def _make(doc, title, section, header, buf) -> dict:
    text = f"{header}\n" + "\n".join(buf)
    return {
        "id": hashlib.md5(text.encode()).hexdigest(),
        "text": text,
        "doc": doc,
        "title": title,
        "section": section,
    }
