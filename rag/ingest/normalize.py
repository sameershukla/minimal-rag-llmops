"""Step 1: turn raw .docx files into clean, uniform blocks.

Every block records where it came from (doc, section) and what it is
(heading / paragraph / list / code / table). The chunker uses that structure.
"""
import re
import unicodedata
from pathlib import Path

from docx import Document
from docx.table import Table

CODE_HINT = re.compile(r"^(\s{2,}|def |class |@|import |from |return |assert |builder\.|graph\s*=|[{}\[\])])")
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def clean(text: str, keep_indent: bool = False) -> str:
    text = unicodedata.normalize("NFKC", text).translate(QUOTES).replace("\xa0", " ")
    if keep_indent:
        return text.rstrip()
    return re.sub(r"\s+", " ", text).strip()


def _kind(style: str, text: str) -> str:
    if style.startswith("Heading") or style == "Title":
        return "heading"
    if style == "List Paragraph":
        return "list"
    if CODE_HINT.match(text):
        return "code"
    return "paragraph"


def _table_text(table: Table) -> str:
    rows = [" | ".join(clean(c.text) for c in row.cells) for row in table.rows]
    return "\n".join(rows)


def normalize_docx(path: Path) -> list[dict]:
    doc = Document(path)
    title, section = path.stem, "Introduction"
    blocks: list[dict] = []

    def add(kind: str, text: str):
        # Merge consecutive code lines into one code block so code is never split mid-way.
        if kind == "code" and blocks and blocks[-1]["kind"] == "code" and blocks[-1]["section"] == section:
            blocks[-1]["text"] += "\n" + text
            return
        blocks.append({"doc": path.stem, "title": title, "section": section, "kind": kind, "text": text})

    for item in doc.iter_inner_content():  # paragraphs and tables, in document order
        if isinstance(item, Table):
            add("table", _table_text(item))
            continue
        style = item.style.name if item.style is not None else ""
        raw = item.text
        if not raw.strip():
            continue
        kind = _kind(style, raw)
        text = clean(raw, keep_indent=(kind == "code"))
        if kind == "heading":
            if style == "Title":
                title = text
            else:
                section = text
            continue
        add(kind, text)
    return blocks


def load_docs(docs_dir: str) -> list[dict]:
    blocks = []
    for path in sorted(Path(docs_dir).glob("*.docx")):
        blocks.extend(normalize_docx(path))
    return blocks
