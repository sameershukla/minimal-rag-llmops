# RAG + LLMOps: a minimal project for learning

```
docs/*.docx -> normalize -> structure-aware chunk -> embed -> Chroma
question    -> retrieve (top_k) -> rerank (cross-encoder) -> prompt vN -> Claude -> answer
```

## Layout

| Path | What it does | LLMOps concern |
|---|---|---|
| `configs/rag.yaml` | Every setting that affects quality (chunking, models, top_k, prompt version) | **Versioning** |
| `rag/config.py` | Loads the config and computes a `fingerprint` (hash of config + prompt text) | **Versioning** |
| `rag/ingest/normalize.py` | .docx -> clean blocks tagged with doc/section/kind (paragraph, list, code, table) | |
| `rag/ingest/chunker.py` | Chunks stay inside one section, keep code and tables whole, and carry a "Title > Section" header | |
| `rag/index/` | Embeddings + Chroma. The collection name is a hash of the chunking and embedding config | **Versioning** |
| `rag/retrieval/` | Vector search, then cross-encoder rerank | |
| `rag/generation/prompts/v1.txt` | Prompt template. Add `v2.txt` and switch `prompt_version` to try a new one | **Versioning** |
| `rag/generation/llm.py` | Claude call (`RAG_OFFLINE=1` returns the top chunk instead, so no API key is needed) | |
| `rag/observability/tracer.py` | Latency for each stage, tokens, sources and scores -> `traces/requests.jsonl` | **Observability** |
| `rag/monitoring/monitor.py` | p50/p95 latency, "I don't know" rate, low-relevance rate, alerts | **Prod monitoring** |
| `eval/golden.jsonl` | Questions with the expected doc/section and the facts the answer must contain | **Eval** |
| `eval/metrics.py` | Recall@K, grounding, answer correctness | **Eval** |
| `eval/gate.py`, `configs/gates.yaml` | Thresholds plus a regression check against the baseline | **CI/CD gate** |
| `.github/workflows/rag-ci.yml` | PR -> tests -> ingest -> eval -> gate -> deploy (main only) | **CI/CD gate** |

## Run

```bash
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

python main.py ingest
python main.py ask "What are the three risk tiers for refunds?"
python main.py eval
python main.py gate --promote     # pass -> saves eval/results/baseline.json
python main.py monitor
```

No API key yet? Prefix commands with `RAG_OFFLINE=1` to test retrieval, tracing and the gate.
Answer correctness will be low in this mode because the "answer" is just the top chunk.

## The LLMOps loop

1. Change something, for example `chunking.max_tokens: 250` or a new `prompts/v2.txt`.
2. Bump `version:` in `configs/rag.yaml`.
3. Run `python main.py ingest && python main.py eval && python main.py gate`.
4. Compare `eval/results/v1.json` with `v2.json`. The gate blocks the change if it misses a
   threshold or drops more than 5 points against the baseline.
5. In prod, `python main.py monitor` on a schedule. Add questions that fail in prod to `golden.jsonl`.

## Metrics

- **Recall@K**: did the reranked top-N include a chunk from the expected section?
- **Grounding**: share of answer sentences whose words mostly appear in the retrieved context
  (a cheap proxy for faithfulness; a common upgrade is an LLM judge).
- **Answer correctness**: share of the expected facts that appear in the answer.
- **Latency p95**: retrieve + rerank + generate, in seconds.
