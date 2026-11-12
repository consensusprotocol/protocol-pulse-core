#!/usr/bin/env python3
"""Record this session's gate replies for pipeline_pp_tests' exam (tests/adversarial/corpora, format v1), so that the
exam's harness, which forbids network connections, replays them offline (PP_GATES_REPLAY=1).

Each case is stripped EXACTLY as the harness strips it before the gate sees it (moments_exam.py:117-129): top-level
"expected" and "origin", "provenance" at any depth, and the real id (replaced by case-<12 hex>). This script never reads an answer. It writes
nothing but the recorded replies (pipeline/moments_gate_adapter.py's record dir) and a verdict log keyed by the
blinded id. The confusion table is the harness's to compute.

Usage: python3 tests/package/run_exam_record.py --corpus /home/ultron/worktrees/pp-tests/tests/adversarial/corpora
       [--chain ROLE=BACKEND ...]   (pin a leg of the L-x A/B; default: pipeline/model_providers.json)
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import moments_gate_adapter as A  # noqa: E402
import providers as P  # noqa: E402

GATES = (("context_integrity", "context_integrity"), ("vo_fidelity", "vo_fidelity"), ("exclusions", "exclusion"))


def blind(case, salt=""):
    """Exactly the harness's blinding (moments_exam.py:117-129): top-level "expected" and "origin" removed,
    "provenance" removed at any depth, the id replaced (the gate's prompts never carry the id)."""
    import copy

    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k != "provenance"}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return x
    c = strip(copy.deepcopy({k: v for k, v in case.items() if k not in ("expected", "origin")}))
    c["id"] = "case-" + hashlib.sha256((salt + str(case.get("id"))).encode()).hexdigest()[:12]
    return c


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--chain", nargs="*", default=[], help="ROLE=BACKEND (config names), one per role to pin")
    ap.add_argument("--out", default=os.path.join(HERE, "exam"))
    a = ap.parse_args(argv)
    chains = {}
    for x in a.chain:
        role, backend = x.split("=", 1)
        chains.setdefault(role, []).append(backend)
    A._router = P.Router(env_path=A.ENV, record_dir=A.RECORD, spend_path=A.SPEND, chains=chains or None,
                         limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")))     # the phase-2 guard
    os.makedirs(a.out, exist_ok=True)
    log = []
    for corpus, gate in GATES:
        d = os.path.join(a.corpus, corpus)
        if not os.path.isdir(d):
            continue
        for f in sorted(x for x in os.listdir(d) if x.endswith(".json") and x != "INDEX.json"):
            case = blind(json.load(open(os.path.join(d, f))))
            try:
                v = getattr(A, gate)(case)
            except P.SpendLimit as e:
                log.append({"gate": gate, "case": case["id"], "stopped": str(e)})
                print("SPEND GUARD:", e)
                json.dump(log, open(os.path.join(a.out, "record_log.json"), "w"), indent=1)
                return 2
            except Exception as e:                       # a gate that could not measure is an ERROR (audit p2 M5)
                v = {"verdict": "error", "why": f"{type(e).__name__}: {str(e)[:200]}"}
            log.append({"gate": gate, "case": case["id"], "verdict": v["verdict"]})
            print(gate, case["id"], v["verdict"], flush=True)
    json.dump(log, open(os.path.join(a.out, "record_log.json"), "w"), indent=1)
    if A._router.notices:
        print("NOTICES:", A._router.notices)
    return 0


if __name__ == "__main__":
    sys.exit(main())
