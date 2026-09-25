"""Observability: time each pipeline stage and write one JSON line per request.

traces/requests.jsonl is what the monitor reads. In a real deployment, ship
these same records to your log/trace backend (Langfuse, Datadog, OpenTelemetry...).
"""
import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

TRACE_FILE = Path("traces/requests.jsonl")


class Trace:
    def __init__(self, question: str, cfg: dict):
        self.record = {
            "trace_id": uuid.uuid4().hex[:12],
            "ts": datetime.now(timezone.utc).isoformat(),
            "version": cfg["version"],
            "fingerprint": cfg["fingerprint"],
            "question": question,
            "latency_s": {},
        }

    @contextmanager
    def span(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.record["latency_s"][name] = round(time.perf_counter() - start, 3)

    def log(self, **fields):
        self.record.update(fields)

    def save(self):
        self.record["latency_s"]["total"] = round(sum(self.record["latency_s"].values()), 3)
        TRACE_FILE.parent.mkdir(exist_ok=True)
        with TRACE_FILE.open("a") as f:
            f.write(json.dumps(self.record) + "\n")
