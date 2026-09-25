"""CI/CD gate: pass only if the latest eval meets thresholds and doesn't regress.

    code/prompt change -> run eval -> gate -> pass? deploy : stop
"""
import json
import shutil
from pathlib import Path

import yaml

LATEST = Path("eval/results/latest.json")
BASELINE = Path("eval/results/baseline.json")
LOWER_IS_BETTER = {"latency_p95_s"}


def check_gate(gates_path: str = "configs/gates.yaml") -> tuple[bool, list[str]]:
    gates = yaml.safe_load(Path(gates_path).read_text())
    metrics = json.loads(LATEST.read_text())["metrics"]
    baseline = json.loads(BASELINE.read_text())["metrics"] if BASELINE.exists() else {}
    failures = []

    for name, limit in gates["thresholds"].items():
        value = metrics[name]
        bad = value > limit if name in LOWER_IS_BETTER else value < limit
        print(f"  {'FAIL' if bad else 'pass'}  {name:<20} {value:<8} (limit {limit})")
        if bad:
            failures.append(f"{name}={value} misses limit {limit}")

    for name, old in baseline.items():
        if name in LOWER_IS_BETTER:
            continue
        if metrics[name] < old - gates["max_regression"]:
            failures.append(f"{name} regressed {old} -> {metrics[name]}")
    return not failures, failures


def promote():
    """Mark the latest passing run as the new baseline (the 'deploy' step)."""
    shutil.copy(LATEST, BASELINE)
