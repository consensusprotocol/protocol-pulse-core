#!/usr/bin/env python3
"""Orchestrator 06:00 ruling 3: the two narrowed context-integrity rules (REFERENT_OUTSIDE needs no antecedent or
completing predicate in the selection AND a changed assertion; STRONGER needs the VO / title words that raise the
certainty, cited verbatim, and a clip that does not already sound that certain alone) must not let ANY must-fail case
pass. This runs the exam's context-integrity MUST-FAIL cases (pipeline_pp_tests corpora, format v1) through the SAME
gate (pipeline/moments_gate_adapter.context_integrity), each case blinded exactly as the harness blinds it
(moments_exam.py:117-129: top-level "expected" and "origin" removed, "provenance" at any depth, the id salted). The
answers are read only to SELECT the must-fail cases and, after the gate answered, to count. Concurrent (threads).

Usage: python3 tests/package/ci_mustfail_check.py --corpus <corpora dir> [--chain ROLE=BACKEND ...] [--jobs 8]
Writes tests/package/exam/ci_mustfail_<stamp>.json."""
import argparse
import copy
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import moments_gate_adapter as A  # noqa: E402
import providers as P  # noqa: E402


def blind(case, salt):
    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k != "provenance"}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return x
    out = strip(copy.deepcopy({k: v for k, v in case.items() if k not in ("expected", "origin")}))
    out["id"] = "case-" + hashlib.sha256((salt + case["id"]).encode()).hexdigest()[:12]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--chain", nargs="*", default=[])
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    chains = {}
    for x in a.chain:
        role, backend = x.split("=", 1)
        chains.setdefault(role, []).append(backend)
    A._router = P.Router(env_path=A.ENV, record_dir=A.RECORD, spend_path=A.SPEND,
                         limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")), chains=chains or None)
    d = os.path.join(a.corpus, "context_integrity")
    cases = [json.load(open(os.path.join(d, f))) for f in sorted(os.listdir(d))
             if f.endswith(".json") and f != "INDEX.json"]
    must_fail = [c for c in cases if c["expected"]["verdict"] == "fail"]
    salt = os.urandom(8).hex()
    t0, led0 = time.time(), json.load(open(A.SPEND))["usd_estimate"]

    def run(c):
        try:
            v = A.context_integrity(blind(c, salt))
            return {"verdict": v["verdict"], "why": v["why"][:300]}
        except A.GateNotMeasured as e:
            return {"verdict": "ERROR", "why": f"not measured: {str(e)[:240]}"}
        except P.SpendLimit as e:
            return {"verdict": "ERROR", "why": f"spend guard: {e}"}
        except Exception as e:                             # noqa: BLE001 (a crash is an ERROR, never a verdict)
            return {"verdict": "ERROR", "why": f"{type(e).__name__}: {str(e)[:240]}"}

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        got = list(ex.map(run, must_fail))
    rows = [{"id": c["id"], "class": c["expected"].get("class"), **g} for c, g in zip(must_fail, got)]
    rejected = sum(r["verdict"] in ("fail", "uncertain") for r in rows)
    passed = [r for r in rows if r["verdict"] == "pass"]
    errors = [r for r in rows if r["verdict"] == "ERROR"]
    led1 = json.load(open(A.SPEND))["usd_estimate"]
    rep = {"corpus": d, "must_fail": len(rows), "rejected": rejected, "passed": len(passed), "errors": len(errors),
           "chains": chains, "seconds": round(time.time() - t0, 1), "usd": round(led1 - led0, 4), "rows": rows}
    os.makedirs(os.path.join(HERE, "exam"), exist_ok=True)
    out = os.path.join(HERE, "exam", f"ci_mustfail_{time.strftime('%Y%m%dT%H%M%S')}.json")
    json.dump(rep, open(out, "w"), indent=1)
    print(f"CONTEXT INTEGRITY MUST-FAIL: {rejected}/{len(rows)} rejected; {len(passed)} PASSED (a miss); "
          f"{len(errors)} ERROR (not measured) | {rep['seconds']} s, ${rep['usd']} | {out}")
    for r in passed + errors:
        print(f"  {r['verdict']}: {r['id']} ({r['class']}): {r['why'][:200]}")
    return 0 if rejected == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
