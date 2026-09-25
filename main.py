"""RAG + LLMOps command line.

    python main.py ingest              # docs -> chunks -> vector DB
    python main.py ask "question"      # answer a question (traced)
    python main.py eval                # run golden-set evaluation
    python main.py gate [--promote]    # CI gate; --promote saves a passing run as baseline
    python main.py monitor             # summarise production traces + alerts
"""
import json
import sys

from dotenv import load_dotenv

load_dotenv()


def main():
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("help", [])

    if cmd == "ingest":
        from rag.pipeline import ingest
        print(ingest())
    elif cmd == "ask":
        from rag.pipeline import ask
        out = ask(" ".join(args))
        print(out["answer"], "\n")
        for c in out["contexts"]:
            print(f"  - {c['doc']} / {c['section']}  (rerank {c['rerank_score']:.2f})")
        print(f"\n  latency: {out['trace']['latency_s']}")
    elif cmd == "eval":
        from eval.run_eval import run_eval
        print(json.dumps(run_eval()["metrics"], indent=2))
    elif cmd == "gate":
        from eval.gate import check_gate, promote
        ok, failures = check_gate()
        if not ok:
            print("\nGATE FAILED - do not deploy:\n  " + "\n  ".join(failures))
            sys.exit(1)
        print("\nGATE PASSED - safe to deploy")
        if "--promote" in args:
            promote()
            print("Saved as new baseline.")
    elif cmd == "monitor":
        from rag.monitoring.monitor import summarize
        print(json.dumps(summarize(), indent=2))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
