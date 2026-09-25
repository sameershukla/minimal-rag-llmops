# Application Flow Diagram

The diagrams use Mermaid. They render in GitHub and in PyCharm's Markdown preview
(enable Mermaid under Settings → Languages & Frameworks → Markdown if needed).
A plain-text version follows each diagram.

Legend: 🟦 RAG pipeline · 🟩 LLMOps (versioning, eval, gate, observability, monitoring)

---

## 1. The whole system

```mermaid
flowchart TB
    subgraph VER["🟩 VERSIONING"]
        CFG["configs/rag.yaml<br/>version, chunking, models,<br/>top_k, prompt_version"]
        PR["rag/generation/prompts/v1.txt"]
        FP["rag/config.py<br/>load_config → fingerprint<br/>index_name → collection hash"]
        CFG --> FP
        PR --> FP
    end

    subgraph ING["🟦 INGEST  ·  python main.py ingest  ·  pipeline.ingest()"]
        D["docs/*.docx"] --> N["normalize<br/>rag/ingest/normalize.py"]
        N --> C["structure-aware chunk<br/>rag/ingest/chunker.py"]
        C --> E["embed<br/>rag/index/embedder.py"]
        E --> V[("Chroma vector DB<br/>rag/index/vectordb.py<br/>collection = docs_&lt;hash&gt;")]
    end

    subgraph ASK["🟦 QUERY  ·  python main.py ask  ·  pipeline.ask()"]
        Q["question"] --> R["retrieve top 10<br/>rag/retrieval/retriever.py"]
        R --> RR["rerank → top 4<br/>rag/retrieval/reranker.py"]
        RR --> P["build prompt<br/>rag/generation/prompts.py"]
        P --> L["Claude<br/>rag/generation/llm.py"]
        L --> A["answer + sources"]
    end

    V -. search .-> R
    FP -. settings .-> ING
    FP -. settings .-> ASK

    subgraph OBS["🟩 OBSERVABILITY"]
        T["Trace spans: retrieve / rerank / generate<br/>rag/observability/tracer.py"]
        TF[("traces/requests.jsonl")]
        T --> TF
    end
    ASK -- "every prod request" --> T

    subgraph MON["🟩 PROD MONITORING  ·  python main.py monitor"]
        M["rag/monitoring/monitor.py<br/>p50/p95 latency, idk_rate,<br/>low_relevance_rate → ALERTS"]
    end
    TF --> M

    subgraph EV["🟩 EVALUATION  ·  python main.py eval"]
        G["eval/golden.jsonl"] --> RE["eval/run_eval.py<br/>runs each question through pipeline.ask()"]
        RE --> MT["eval/metrics.py<br/>Recall@K, grounding,<br/>answer correctness, latency p95"]
        MT --> RES[("eval/results/&lt;version&gt;.json<br/>latest.json")]
    end
    RE -. "same pipeline, save_trace=False" .-> ASK

    subgraph GATE["🟩 CI/CD GATE  ·  python main.py gate"]
        GT{"eval/gate.py<br/>thresholds in configs/gates.yaml<br/>+ no regression vs baseline"}
        GT -- pass --> DEP["deploy + promote<br/>baseline.json"]
        GT -- fail --> STOP["stop · exit 1"]
    end
    RES --> GT

    M -. "failing questions become<br/>new golden cases" .-> G
```

<details>
<summary>Plain-text version</summary>

```
                 ┌──────────────── VERSIONING ────────────────┐
                 │ configs/rag.yaml + prompts/v1.txt          │
                 │   → rag/config.py: fingerprint, index hash │
                 └─────────────────────┬──────────────────────┘
                                       │ settings
       ┌───────────────────────────────┴─────────────────────────────┐
       ▼                                                             ▼
 INGEST (main.py ingest)                                  QUERY (main.py ask)
 docs/*.docx                                              question
   → normalize.py                                           → retrieve top 10 ◄──┐
   → chunker.py (structure-aware)                           → rerank → top 4     │
   → embedder.py                                            → build prompt (v1)  │
   → Chroma (docs_<hash>) ─────────── search ───────────────→ Claude             │
                                                             → answer + sources   │
                                                                   │              │
                                              every prod request   ▼              │
                                   OBSERVABILITY: tracer.py → traces/requests.jsonl
                                                                   │              │
                                   MONITORING: monitor.py → p95, idk_rate, alerts │
                                                                   │              │
                                        failing questions ─────────┘              │
                                                ▼                                 │
                        EVALUATION: golden.jsonl → run_eval.py ── same ask() ─────┘
                                     → metrics.py → eval/results/<version>.json
                                                ▼
                        CI/CD GATE: gate.py + gates.yaml
                                     pass → deploy + promote baseline
                                     fail → stop (exit 1)
```
</details>

---

## 2. Query flow in detail (who calls what)

`main.py` is only the entry point. `rag/pipeline.py → ask()` orchestrates the steps.

```mermaid
sequenceDiagram
    participant U as User
    participant M as main.py
    participant P as pipeline.ask()
    participant T as Trace
    participant R as retriever / vectordb
    participant RR as reranker
    participant G as prompts + llm
    participant F as traces/requests.jsonl

    U->>M: python main.py ask "question"
    M->>P: ask(question)
    P->>T: Trace(question, cfg)  (version, fingerprint)
    P->>R: retrieve()  [span: retrieve]
    R-->>P: 10 candidate chunks
    P->>RR: rerank()  [span: rerank]
    RR-->>P: top 4 chunks + scores
    P->>G: build_prompt(v1) → generate()  [span: generate]
    G-->>P: answer, model, tokens, stop_reason
    P->>T: trace.log(answer, sources, tokens...)
    T->>F: trace.save()  (one JSON line)
    P-->>M: answer, contexts, trace
    M-->>U: prints answer, sources, latency
```

<details>
<summary>Plain-text version</summary>

```
main.py ask
  └─ pipeline.ask()                                     rag/pipeline.py:25
       ├─ Trace(question, cfg)                          rag/observability/tracer.py:17
       ├─ [span retrieve] retrieve() → vectordb.search() → 10 chunks     line 30
       ├─ [span rerank]   rerank() → top 4                               line 32
       ├─ [span generate] build_prompt(v1) → generate() → Claude         line 34-35
       ├─ trace.log(answer, sources, tokens, stop_reason)                line 37
       └─ trace.save() → traces/requests.jsonl                           line 46
```
</details>

---

## 3. CI/CD gate flow

```mermaid
flowchart TD
    CH["Code / prompt / config change<br/>(bump version in rag.yaml)"] --> PRQ["Pull request or push to main"]
    PRQ --> UT["pytest -q<br/>tests/test_chunker.py"]
    UT --> IN["python main.py ingest"]
    IN --> EVL["python main.py eval<br/>Recall@K · Grounding · Correctness · Latency p95"]
    EVL --> GQ{"python main.py gate<br/>thresholds met AND<br/>no drop > 0.05 vs baseline?"}
    GQ -- No --> ST["❌ Stop: build fails (exit 1)<br/>eval/results uploaded for review"]
    GQ -- Yes --> BR{"branch == main?"}
    BR -- No --> OK["✅ PR marked safe to merge"]
    BR -- Yes --> DP["🚀 Deploy job<br/>(needs: eval-gate)"]
```

Defined in `.github/workflows/rag-ci.yml`.

---

## 4. LLMOps in the code

| LLMOps area | Where in the code | What it does |
|---|---|---|
| Versioning: config | `configs/rag.yaml:3` (`version`), `:27` (`prompt_version`) | Every quality setting lives in one versioned file |
| Versioning: prompt | `rag/generation/prompts/v1.txt`, `rag/generation/prompts.py:7` | A prompt is a file; switch versions in the config |
| Versioning: fingerprint | `rag/config.py:11-17` | Hash of config + prompt text identifies the exact setup |
| Versioning: index | `rag/config.py:20-27`, `rag/index/vectordb.py:8` | New Chroma collection when chunking or embedding changes |
| Evaluation: dataset | `eval/golden.jsonl` | 14 questions with expected sections and facts |
| Evaluation: metrics | `eval/metrics.py:8` Recall@K, `:17` grounding, `:31` correctness | Deterministic scores, no LLM judge |
| Evaluation: runner | `eval/run_eval.py:19`, results at `:51` | Scores are saved per version |
| CI/CD gate: thresholds | `configs/gates.yaml` | Minimums, latency max, allowed regression |
| CI/CD gate: logic | `eval/gate.py:16` check, `:37` promote | Pass/fail + baseline comparison |
| CI/CD gate: pipeline | `.github/workflows/rag-ci.yml:29-33`, `:41` | ingest → eval → gate → deploy only on pass |
| Observability: tracer | `rag/observability/tracer.py:17-44` | Spans, fields, one JSON line per request |
| Observability: usage | `rag/pipeline.py:30-46` | Times each stage; logs sources, tokens, model |
| Prod monitoring | `rag/monitoring/monitor.py:11` alerts, `:23` summarize | p50/p95, idk rate, low-relevance rate, alerts |

A detailed explanation of each area is in `configs/llmops_implementation.txt`.

---

## 5. External references for learning LLMOps

**Foundations**
- Google Cloud: *MLOps: Continuous delivery and automation pipelines in machine learning*. The maturity levels (manual → CI/CD → continuous training) that LLMOps builds on.
  https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning
- Chip Huyen: *Building LLM applications for production*. Covers prompt versioning, evaluation, cost and latency.
  https://huyenchip.com/2023/04/11/llm-engineering.html
- Eugene Yan: *Patterns for Building LLM-based Systems & Products*. Covers evals, RAG, guardrails and collecting feedback.
  https://eugeneyan.com/writing/llm-patterns/

**RAG**
- Lewis et al. (2020): *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, the original RAG paper.
  https://arxiv.org/abs/2005.11401
- Sentence-Transformers: embeddings and cross-encoder reranking, as used in `embedder.py` and `reranker.py`.
  https://www.sbert.net/ · https://sbert.net/examples/cross_encoder/applications/README.html
- Chroma: the vector DB used in `vectordb.py`.
  https://docs.trychroma.com/

**Evaluation**
- Anthropic / Claude docs: *Create strong empirical evaluations*. How to design test cases and grading.
  https://docs.claude.com/en/docs/test-and-evaluate/develop-tests
- Ragas: RAG metrics (faithfulness, context recall, answer relevancy). A natural upgrade from `eval/metrics.py`.
  https://docs.ragas.io/

**Observability and monitoring**
- Langfuse: open-source LLM tracing, prompt management and evals. The next step after `traces/requests.jsonl`.
  https://langfuse.com/docs
- Arize Phoenix: open-source LLM/RAG tracing and evaluation.
  https://arize.com/docs/phoenix
- OpenTelemetry semantic conventions for GenAI: the standard field names for LLM spans.
  https://opentelemetry.io/docs/specs/semconv/gen-ai/

**Diagram syntax**
- Mermaid, if you want to edit these diagrams: https://mermaid.js.org/
