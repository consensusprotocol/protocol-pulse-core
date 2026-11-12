#!/usr/bin/env python3
"""Blind A/B per model role (law L-x, orchestrator 02:45: "for each role report a blind A/B on saved data: local
gemma3:27b vs frontier vs Heimdall: quality verdict, failures, latency, dollars"). The integrator runs the LOCAL leg
under the GPU0 lease (--local: a started story_semantics.LocalLLM is handed to the router); builders run the rest.
Generator and judge are always different models: the quality judge is a back-end outside the compared set.

Roles:
  mine        moments.mine on a saved universe with the role's chain pinned to ONE back-end per leg; quality: a blind
              pairwise judge (outside the compared vendors and families) sees two anonymised lists of each leg's best
              8 moments (verbatim text, channel), in BOTH orders, and says which list holds better moments for a
              60-second Bitcoin video; a split is a tie; failures = rejected / model_error calls; latency = model
              seconds; dollars from the spend ledger.
  verdicts    fidelity_verdict, context_verdict, viewer_takeaway, exclusion_verdict: the pp-tests exam corpora
              (format v1) through pipeline/moments_gate_adapter.py with the chain pinned per leg; quality = the
              confusion table against the exam's answers (read only AFTER the gate answered, by this harness, never
              by the gate).
Usage:
  python3 tests/providers/ab_roles.py mine --run fresh_20261112_050611 --legs heimdall:qwen/qwen3.8-27b openai:gpt-6.1-sol [--local]
  python3 tests/providers/ab_roles.py verdicts --corpus /home/ultron/worktrees/pp-tests/tests/adversarial/corpora --legs ...
Output: tests/providers/ab/<role>_<name>.json and a printed table.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
sys.path.insert(0, os.path.join(REPO, "tests", "package"))
import providers as P  # noqa: E402

OUT = os.path.join(HERE, "ab")
REPLIES = os.path.join(REPO, "tests", "moments", "fixtures", "replies")    # shared: a leg already mined replays
SPEND = os.path.join(REPO, "tests", "moments", "proof", "SPEND.json")
ENV = P.ENV_PATH

JUDGE_PROMPT = """Two editors each picked MOMENTS (verbatim quotes) for 60-second Bitcoin videos from the same
transcripts. Judge which LIST is better material: moments that grab attention in the first seconds, are quotable,
state something surprising or clear, stand alone without context, are about Bitcoin, and avoid accusations, advice,
ads and outrage. Ignore list length beyond the best 8.

LIST A:
{a}

LIST B:
{b}

Return ONLY this JSON object: {{"better": "A" | "B" | "tie", "why": "two sentences at most"}}"""


def _router(chains, local=None):
    return P.Router(env_path=ENV, record_dir=REPLIES, spend_path=SPEND, chains=chains,
                    limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")),           # the phase-2 guard
                    local_llm=local)


def _local_llm():
    import story_semantics as sm
    return sm.LocalLLM().start()                 # proves the GPU0-only Ollama listener (law L-r: the caller's lease)


def leg_mine(run, backend, local=None):
    import moments as M
    import proof_moments as PM
    import trend_brief as TB
    words, captions, ctx, saved = PM.universe_sources(run)
    r = _router({"mine": [backend]}, local)
    t0 = time.time()
    out = M.mine(r, words, ctx, TB.TOPICS, since=None, optout=M.optout_ids(), log=lambda s: None,
                 cycle=f"ab:{run}:{backend}", recent_h=72.0)
    secs = round(time.time() - t0, 1)
    statuses = [c["status"] for c in out["calls"]]
    usd = sum((a.get("meta") or {}).get("usd", 0.0) for c in out["calls"] for a in c["attempts"])
    return {"backend": backend, "calls": len(statuses), "accepted": statuses.count("accepted"),
            "failures": {s: statuses.count(s) for s in set(statuses) if s != "accepted"}, "seconds": secs,
            "usd": round(usd, 4), "moments": out["moments"]}


def judge_pair(judge_backend, a, b, seed):
    """The blind pairwise judge, in BOTH orders (audit p2 C17: one coin-flip order was n = 1); a split verdict is a
    tie. The lists are mine()'s output, ranked by rank_score, so [:8] is each leg's best 8."""
    def fmt(lst):
        return "\n".join(f"- [{m['channel_name']}] \"{m['text'][:400]}\"" for m in lst[:8]) or "(none)"
    r = _router({"ab_judge": [judge_backend]})
    votes, why = [], []
    for flip in (False, True):
        x, y = (b, a) if flip else (a, b)
        rep = r.call("ab_judge", JUDGE_PROMPT.format(a=fmt(x), b=fmt(y)), 600, seed + int(flip))
        v = json.loads(rep.text.strip())
        if not isinstance(v, dict) or v.get("better") not in ("A", "B", "tie"):
            raise ValueError("judge reply out of contract")
        votes.append(v["better"] if v["better"] == "tie" else (("B" if v["better"] == "A" else "A") if flip
                                                               else v["better"]))
        why.append(v.get("why"))
    better = votes[0] if votes[0] == votes[1] else "tie"
    return {"better": better, "votes": votes, "why": why, "judge": judge_backend}


def ab_mine(args):
    cfg = json.load(open(P.CONFIG))
    legs = [leg_mine(args.run, b) for b in args.legs]
    if args.local:
        local = next(n for n, s_ in cfg["backends"].items() if s_["vendor"] == "local")   # no model name in code (L-x)
        legs.append(leg_mine(args.run, local, _local_llm()))
    compared = {l["backend"] for l in legs}
    vendors = {cfg["backends"][c]["vendor"] for c in compared if c in cfg["backends"]}
    families = {cfg["backends"][c].get("family") for c in compared if c in cfg["backends"]}
    outside = [b for b, s_ in cfg["backends"].items() if b not in compared and s_["vendor"] not in vendors
               and s_.get("family") not in families and not s_["vendor"].endswith(("_stt", "_search"))]
    if args.judge and args.judge not in outside:
        raise SystemExit(f"--judge {args.judge} is a compared leg's vendor or family (or not a text back-end)")
    if not (args.judge or outside):
        raise SystemExit("no judge outside the compared vendors and families: pass --judge")
    judge = args.judge or outside[0]
    pairs = []
    for i in range(len(legs)):
        for j in range(i + 1, len(legs)):
            try:
                v = judge_pair(judge, legs[i]["moments"], legs[j]["moments"], seed=7 + i * 10 + j)
            except Exception as e:
                v = {"better": None, "why": f"judge failed: {type(e).__name__}: {str(e)[:160]}", "judge": judge}
            pairs.append({"A": legs[i]["backend"], "B": legs[j]["backend"], **v})
    rec = {"role": "mine", "run": args.run, "judge": judge,
           "legs": [{k: v for k, v in l.items() if k != "moments"} | {"n_moments": len(l["moments"])} for l in legs],
           "pairs": pairs}
    os.makedirs(OUT, exist_ok=True)
    json.dump(rec, open(os.path.join(OUT, f"mine_{args.run}.json"), "w"), indent=1, default=str)
    print(json.dumps(rec, indent=1, default=str)[:4000])


def ab_verdicts(args):
    import moments_gate_adapter as A
    rows = []
    for backend in args.legs:
        for gate, corpus, role in (("context_integrity", "context_integrity", ("context_verdict", "viewer_takeaway")),
                                   ("vo_fidelity", "vo_fidelity", ("fidelity_verdict",)),
                                   ("exclusion", "exclusions", ("exclusion_verdict",))):
            d = os.path.join(args.corpus, corpus)
            if not os.path.isdir(d):
                continue
            A._router = _router({r: [backend] for r in role})
            conf, secs = {}, 0.0
            for f in sorted(x for x in os.listdir(d) if x.endswith(".json") and x != "INDEX.json"):
                raw = json.load(open(os.path.join(d, f)))
                expected = (raw.get("expected") or {}).get("verdict")
                import run_exam_record as R
                case = R.blind(raw)                        # exactly the harness's blinding (audit p2 C17)
                t0 = time.time()
                try:
                    got = getattr(A, gate)(case)["verdict"]
                except Exception as e:
                    got = f"error:{type(e).__name__}"
                secs += time.time() - t0
                conf[(expected, got)] = conf.get((expected, got), 0) + 1
            rows.append({"backend": backend, "gate": gate, "confusion": {f"{k[0]}->{k[1]}": v for k, v in conf.items()},
                         "seconds": round(secs, 1)})
    os.makedirs(OUT, exist_ok=True)
    json.dump(rows, open(os.path.join(OUT, "verdicts.json"), "w"), indent=1)
    for r in rows:
        print(r)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=("mine", "verdicts"))
    ap.add_argument("--run")
    ap.add_argument("--corpus")
    ap.add_argument("--legs", nargs="+", required=True)
    ap.add_argument("--local", action="store_true", help="add the local gemma3:27b leg (the integrator, GPU0 lease)")
    ap.add_argument("--judge")
    a = ap.parse_args(argv)
    (ab_mine if a.role == "mine" else ab_verdicts)(a)


if __name__ == "__main__":
    main()
