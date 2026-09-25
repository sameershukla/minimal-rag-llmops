"""RAG evaluation metrics. Simple, deterministic, no LLM judge needed."""
import re

STOP = set("the a an and or of to in is are was be it this that for on with as by at from not no do does can "
           "you your they their its has have if then than so what when which who why how".split())


def recall_at_k(contexts: list[dict], case: dict) -> float:
    """1.0 if any retrieved chunk comes from an expected (doc, section)."""
    return float(any(c["doc"] == case["doc"] and c["section"] in case["sections"] for c in contexts))


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9$_\[\]]+", text.lower()) if len(w) > 2 and w not in STOP}


def grounding(answer: str, contexts: list[dict], min_overlap: float = 0.5) -> float:
    """Share of answer sentences whose content words mostly appear in the context.

    A cheap proxy for faithfulness: sentences with ideas not in the context score 0.
    """
    ctx = _content_words(" ".join(c["text"] for c in contexts))
    answer = re.sub(r"\[\d+\]", "", answer)  # drop citation markers
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", answer) if _content_words(s)]
    if not sentences:
        return 0.0
    supported = sum(len(_content_words(s) & ctx) / len(_content_words(s)) >= min_overlap for s in sentences)
    return supported / len(sentences)


def answer_correctness(answer: str, case: dict) -> float:
    """Share of expected facts (keywords) that appear in the answer."""
    facts = case["facts"]
    return sum(f.lower() in answer.lower() for f in facts) / len(facts)
