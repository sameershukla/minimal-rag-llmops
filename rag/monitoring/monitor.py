"""Production monitoring: summarise traces and raise alerts.

Run it on a schedule (cron / CI job) against production traces.
"""
import json
import statistics
from pathlib import Path

from rag.observability.tracer import TRACE_FILE

ALERTS = {
    "latency_p95_s": 15.0,      # slower than this -> alert
    "idk_rate": 0.20,           # more "I don't know" answers than this -> retrieval may be failing
    "low_relevance_rate": 0.30, # top rerank score < 0 on this share of requests -> questions drifting from docs
}


def _p95(values: list[float]) -> float:
    values = sorted(values)
    return values[int(0.95 * (len(values) - 1))] if values else 0.0


def summarize(path: Path = TRACE_FILE, last_n: int = 500) -> dict:
    if not path.exists():
        return {"requests": 0, "alerts": ["no traces yet"]}
    rows = [json.loads(line) for line in path.read_text().splitlines()[-last_n:]]
    total = [r["latency_s"]["total"] for r in rows]
    report = {
        "requests": len(rows),
        "versions": sorted({r["version"] for r in rows}),
        "latency_p50_s": round(statistics.median(total), 3),
        "latency_p95_s": round(_p95(total), 3),
        "idk_rate": round(sum("don't know" in r["answer"].lower() for r in rows) / len(rows), 3),
        "low_relevance_rate": round(sum((r["top_rerank_score"] or -99) < 0 for r in rows) / len(rows), 3),
        "avg_output_tokens": round(statistics.mean(r["tokens"]["output"] for r in rows), 1),
    }
    report["alerts"] = [f"{k}={report[k]} > {limit}" for k, limit in ALERTS.items() if report[k] > limit]
    return report
