"""Run the golden set through the pipeline and save scores for this config version."""
import json
import statistics
from pathlib import Path

from eval.metrics import answer_correctness, grounding, recall_at_k
from rag.config import load_config
from rag.pipeline import ask

GOLDEN = Path("eval/golden.jsonl")
RESULTS = Path("eval/results")


def _p95(values):
    values = sorted(values)
    return values[int(0.95 * (len(values) - 1))]


def run_eval() -> dict:
    cfg = load_config()
    cases = [json.loads(line) for line in GOLDEN.read_text().splitlines() if line.strip()]
    rows = []
    for case in cases:
        out = ask(case["question"], cfg, save_trace=False)  # eval traffic stays out of prod traces
        rows.append({
            "question": case["question"],
            "answer": out["answer"],
            "recall_at_k": recall_at_k(out["contexts"], case),
            "grounding": grounding(out["answer"], out["contexts"]),
            "answer_correctness": answer_correctness(out["answer"], case),
            "latency_s": out["trace"]["latency_s"]["retrieve"] + out["trace"]["latency_s"]["rerank"]
            + out["trace"]["latency_s"]["generate"],
        })
        print(f"  recall={rows[-1]['recall_at_k']:.0f} ground={rows[-1]['grounding']:.2f} "
              f"correct={rows[-1]['answer_correctness']:.2f}  {case['question'][:60]}")

    summary = {
        "version": cfg["version"],
        "fingerprint": cfg["fingerprint"],
        "model": cfg["llm"]["model"],
        "n": len(rows),
        "metrics": {
            "recall_at_k": round(statistics.mean(r["recall_at_k"] for r in rows), 3),
            "grounding": round(statistics.mean(r["grounding"] for r in rows), 3),
            "answer_correctness": round(statistics.mean(r["answer_correctness"] for r in rows), 3),
            "latency_p95_s": round(_p95([r["latency_s"] for r in rows]), 3),
        },
        "cases": rows,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    for name in (f"{cfg['version']}.json", "latest.json"):
        (RESULTS / name).write_text(json.dumps(summary, indent=2))
    return summary
