"""The full RAG flow, with every stage traced.

ingest:  docs -> normalize -> chunk -> embed -> vector DB
ask:     question -> retrieve -> rerank -> prompt -> LLM -> answer
"""
from rag.config import load_config
from rag.generation.llm import generate
from rag.generation.prompts import build_prompt
from rag.index.vectordb import build_index
from rag.ingest.chunker import chunk_blocks
from rag.ingest.normalize import load_docs
from rag.observability.tracer import Trace
from rag.retrieval.reranker import rerank
from rag.retrieval.retriever import retrieve


def ingest(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    blocks = load_docs(cfg["data"]["docs_dir"])
    chunks = chunk_blocks(blocks, **cfg["chunking"])
    name = build_index(chunks, cfg)
    return {"blocks": len(blocks), "chunks": len(chunks), "collection": name}


def ask(question: str, cfg: dict | None = None, save_trace: bool = True) -> dict:
    cfg = cfg or load_config()
    r = cfg["retrieval"]
    trace = Trace(question, cfg)

    print(f"Tracing: {trace}")
    with trace.span("retrieve"):
        candidates = retrieve(question, cfg)
    with trace.span("rerank"):
        top = rerank(question, candidates, r["rerank_model"], r["rerank_top_n"])
    with trace.span("generate"):
        out = generate(build_prompt(question, top, cfg["llm"]["prompt_version"]), cfg)

    trace.log(
        answer=out["text"],
        model=out["model"],
        tokens={"input": out["input_tokens"], "output": out["output_tokens"]},
        stop_reason=out["stop_reason"],
        sources=[{"doc": c["doc"], "section": c["section"], "rerank_score": round(c["rerank_score"], 3)} for c in top],
        top_rerank_score=round(top[0]["rerank_score"], 3) if top else None,
    )
    if save_trace:
        trace.save()
    return {"answer": out["text"], "contexts": top, "trace": trace.record}
