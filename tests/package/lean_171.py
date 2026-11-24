#!/usr/bin/env python3
"""LEAN, the evidence from build 171's own record (b171-20261124T175600Z-3268449, ledger_20261124_175601, 12:56 ET Nov 24):
no model is asked, nothing is written. It reads the build's record (package.json, FINGERPRINT.json), the model replies
its commit added (tests/package/fixtures/replies, one file per live call, with its prompt, back-end and bill) and the
lean router's own reservation sizes (providers.Router on a scratch copy of the day's ledger).

(A) THE COMPLETION RESERVE (issues 5 and 3): every capped call build 171 made, in order, with its bill on the cap's basis
    (vendor-reported, the estimate where a vendor reports none) and the router's reservation for it; which phase it
    belongs to (the search, or the finishing of line-up 1, the one line-up that passed its clips-alone verdict); the
    calls the spend stop refused. Then the same calls under the lean reserve: (i) on build 171's day (it started at
    $0.832 of $1.50), (ii) on a fresh day ($0.00 of $1.50).
(B) A RE-RUN: which of build 171's recorded calls a re-run on the same inputs (the same day) would serve from their
    recordings (no call), and which it must ask, on the lean path.
Usage: python3 -B tests/package/lean_171.py [--json]"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(REPO, "pipeline"), os.path.join(REPO, "tests", "package")]
import package as PK  # noqa: E402
import providers as P  # noqa: E402
import proof_ly as PL  # noqa: E402

COMMIT = "88ffce7b6"                                   # pp-selectid build 171's commit (its record and its replies)
RUN = os.path.join(HERE, "proof", "ledger_20261124_175601")
START = "2026-11-24T17:56:01Z"                         # the build's render clock (its folder's stamp)
LINEUP1_AT = "2026-11-24T18:07:55Z"                    # line-up 1's clips-alone verdict: PASS (the record, the replies)
FINISH_END = "2026-11-24T18:16:15Z"                    # line-up 1's finishing ends with its refused verdict (log)
OLD = "community of bitcoins who"                      # 8b5ec831 as the transcript wrote it
NEW = "community of bitcoiners who"                    # as the lock heard it (ruling 163 (2)(b))
EXT = "16473ccae3baf3b8d118"                           # the CoinTelegraph clip refused by the out-edge question


def replies():
    names = subprocess.run(["git", "-C", REPO, "show", "--name-only", "--format=", COMMIT], capture_output=True,
                           text=True, check=True).stdout.split()
    out = []
    for n in names:
        if "fixtures/replies/" not in n:
            continue
        with open(os.path.join(REPO, n)) as f:
            d = json.load(f)
        d["_file"] = n
        out.append(d)
    return sorted(out, key=lambda d: d.get("recorded_at") or "")


def router():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "SPEND.json")
    shutil.copyfile(os.path.join(HERE, "proof", "SPEND_D20261123.json"), p)    # the day build 171 charged
    r = P.Router(spend_path=p, limit_usd=PL.DAY_CAP_USD, limit_basis=PL.LY_LIMIT_BASIS,
                 chains=PL.chains("heimdall_first"), uncapped=PL.UNCAPPED)
    return r, d


def reservation(r, d):
    b = r.backends.get(d["backend"])
    if b is None or b.free() or not r._capped(d["backend"]):
        return 0.0
    if d["role"] == "transcribe":
        return round(b.usd({"seconds": float((d.get("usage") or {}).get("seconds") or 0) + 5.0}), 6)
    prompt = {"text": d.get("prompt") or "", "images": ["x"]} if d["role"] == "visual_check" else (d.get("prompt") or "")
    frac = r._reserve_fraction(b)
    up = b.upper_usd(prompt, int(d.get("max_tokens") or 0), d.get("system"))
    return round(up * frac, 6) if frac is not None else round(up, 6)


def bill(d):
    """The call on the cap's basis (Router._basis_total): a capped vendor's own reported figure, else its estimate."""
    if str(d.get("backend", "")).startswith("heimdall:"):
        return 0.0
    rep = (d.get("usage") or {}).get("usd_reported")
    return float(rep) if isinstance(rep, (int, float)) else float(d.get("usd") or 0.0)


def what(d):
    p = d.get("prompt") or ""
    if d["role"] == "coherence_verdict":
        return ("hook rating" if p.startswith("You judge OPENING") else "join table" if p.startswith("You judge JOINS")
                else "clips-alone verdict" if p.startswith("You watch a short video made ONLY") else "coherence")
    return {"context_verdict": "step A", "transcribe": "second ear", "visual_check": "vision",
            "exclusion_verdict": "exclusion", "out_edge": "out-edge question", "angle_write": "angle writer",
            "shadow86:coherence_verdict:hook": "hook shadow"}.get(d["role"], d["role"])


def main(argv):
    with open(os.path.join(RUN, "package.json")) as f:
        pk = json.load(f)
    with open(os.path.join(RUN, "FINGERPRINT.json")) as f:
        fp = json.load(f)
    r, tmp = router()
    try:
        R = PK.completion_reserve(r)
        calls = []
        for d in replies():
            if (d.get("recorded_at") or "") < START:
                continue                                 # recorded before this build (another run's)
            phase = "finish line-up 1" if LINEUP1_AT < d["recorded_at"] <= FINISH_END else "search"
            calls.append({"at": d["recorded_at"][11:19], "what": what(d), "role": d["role"], "backend": d["backend"],
                          "bill": round(bill(d), 6), "res": reservation(r, d), "phase": phase,
                          "old_words": OLD in (d.get("prompt") or "").lower(),
                          "new_words": NEW in (d.get("prompt") or "").lower(), "ext": EXT in (d.get("prompt") or "")})
    finally:
        shutil.rmtree(tmp, True)
    pre_before = sum(1 for d in replies() if (d.get("recorded_at") or "") < START)
    spend = pk["spend_ruling_48"]
    s0, cap = float(spend["before"]), float(spend["cap"])
    refused = [   # FINGERPRINT.json spend_refused: 4 Grok calls; the record names three, the fourth by elimination
        {"at": "18:16:15", "what": "clips-alone verdict on the corrected words (line-up 1)", "phase": "finish line-up 1",
         "res": 0.08, "named_by": "spend_refused's 4th; no reply recorded; the record says 'fails'"},
        {"at": "18:16:20", "what": "clips-alone verdict, line-up 2", "phase": "search", "res": 0.08,
         "named_by": pk["never_empty"]["soft_record"]["tried"][1]["medley"]["error"]},
        {"at": "18:16:40", "what": "clips-alone verdict, line-up 3", "phase": "search", "res": 0.08,
         "named_by": pk["never_empty"]["soft_record"]["tried"][2]["medley"]["error"]},
        {"at": "18:17:00", "what": "the spotlight's step A", "phase": "search", "res": 0.10,
         "named_by": pk["spotlight"]["moments"]["0e3160565b2e82d0211b"]["out"][:160]}]
    capped = [c for c in calls if c["bill"] or c["res"]]

    def walk(start, reserve):
        spent, rows = start, []
        for c in sorted(capped + [dict(x, bill=0.0, refused_in_171=True) for x in refused], key=lambda c: c["at"]):
            margin = 0.0 if c["phase"] == "finish line-up 1" else reserve
            ok = spent + c["res"] + margin <= cap
            rows.append(dict(c, spent_before=round(spent, 4), allowed=ok))
            if ok:
                spent += c["bill"]
        return rows, round(spent, 4)
    actual, _ = walk(s0, 0.0)
    lean_day, _ = walk(s0, R["usd"])
    lean_fresh, lean_fresh_end = walk(0.0, R["usd"])
    stages = {}
    for c in calls:
        k = (c["phase"], c["what"])
        st = stages.setdefault(k, {"calls": 0, "bill": 0.0})
        st["calls"] += 1
        st["bill"] = round(st["bill"] + c["bill"], 6)
    upto = lambda rows, at: next((x for x in rows if x["at"] >= at), None)
    lu = {"line-up 1": LINEUP1_AT[11:19], "line-up 2": "18:16:20", "line-up 3": "18:16:40"}
    lineups = {}
    for name, at in lu.items():
        row = {k: next(x for x in rows if x["at"] == at and "clips-alone" in x["what"])
               for k, rows in (("actual", actual), ("lean_171_day", lean_day), ("lean_fresh_day", lean_fresh))}
        lineups[name] = {k: {"spent_before": v["spent_before"], "reservation": v["res"], "asked": v["allowed"],
                             "speculative_money_left": round(cap - v["spent_before"] - (0 if k == "actual" else
                                                                                         R["usd"]), 4)}
                         for k, v in row.items()}
    first_refused = next((x for x in lean_day if not x["allowed"]), None)
    for name in lineups:                                 # on build 171's day the search's first paid call is refused:
        if first_refused and first_refused["at"] < lu[name]:   # no line-up is reached as recorded
            lineups[name]["lean_171_day"] = {"reached": False, "speculative_money_left": round(cap - s0 - R["usd"], 4),
                                             "why": f"the search's first paid call ({first_refused['what']}, "
                                                    f"{first_refused['at']} UTC) is refused by the reserve: the "
                                                    f"day's ${cap - s0:.3f} is under one package's ${R['usd']:.4f}"}
    # (B) THE RE-RUN, on the lean path, the same inputs and day: a recorded call is served from its recording when
    # its prompt is unchanged (Router._call: the record key is role, back-end, prompt, max_tokens, seed, system)
    changed = [c for c in calls if c["old_words"] and c["what"] in ("join table", "clips-alone verdict")]
    rerun = {"recorded_calls_in_171": len(calls), "recorded_before_its_start_not_counted": pre_before,
             "served_from_recordings": len(calls) - len(changed),
             "asked_again_on_the_corrected_words": [{k: c[k] for k in ("at", "what", "backend")} for c in changed],
             "never_made_in_171_asked": [x["what"] for x in refused if "corrected words" not in x["what"]],
             "not_needed_under_lean": [x["what"] for x in refused if "corrected words" in x["what"]],
             "new_spans_of_lean_2": "16473cca's extension: its step A first screen, its second ear and its own "
                                    "out-edge question (3 calls; their answers need a live model)",
             "writer_probes": "12 probe calls each build (Heimdall, free, never recorded: proof_ledger.writer_probe)"}
    out = {"reserve": R, "day_start": s0, "cap": cap, "spent_in_171": round(float(spend["after"]) - s0, 4),
           "stages": {f"{a} / {b}": v for (a, b), v in sorted(stages.items())},
           "refused_in_171": refused, "lineups": lineups,
           "lean_171_day": {"first_refused": first_refused and {k: first_refused[k] for k in
                                                                ("at", "what", "res", "spent_before")},
                            "spent_before_it": 0.0,
                            "after_it": "not computed: the stages after a refused step A run on HELD moments (ruling "
                                        "102), not as recorded; only a re-run shows them"},
           "lean_fresh_day": {"spent": lean_fresh_end},
           "corrected_words_calls": [{k: c[k] for k in ("at", "what", "backend", "bill")} for c in calls
                                     if c["new_words"]],
           "rerun": rerun}
    if "--json" in argv:
        print(json.dumps(out, indent=1))
        return 0
    print(f"build 171: the day at ${s0:.3f} of ${cap:.2f} at its start; it spent ${out['spent_in_171']:.4f}; "
          f"{len(calls)} live calls recorded ({sum(1 for c in calls if c['bill'])} billed on the cap's basis)")
    print(f"the lean completion reserve: ${R['usd']:.4f} (" + "; ".join(f"{p['what']} {p['calls']} x "
                                                                        f"${p['usd_each']:.4f}" for p in R["parts"]) + ")")
    for k, v in out["stages"].items():
        print(f"  {k}: {v['calls']} call(s), ${v['bill']:.4f}")
    for x in refused:
        print(f"  REFUSED in 171 at {x['at']} ({x['phase']}): {x['what']}, reservation ${x['res']:.2f}")
    for name, v in lineups.items():
        print(f"{name}: " + "; ".join(f"{k}: " + (f"spent ${w['spent_before']:.4f} before it, "
                                                  f"{'ASKED' if w['asked'] else 'REFUSED'}" if "asked" in w else
                                                  "NOT REACHED") +
                                      f" (speculative money left ${w['speculative_money_left']:.4f})"
                                      for k, w in v.items()))
    print(f"lean on build 171's day: the first refusal {out['lean_171_day']['first_refused']}; spent before it $0.00; "
          f"after it: {out['lean_171_day']['after_it']}")
    print(f"lean on a fresh day: spent ${out['lean_fresh_day']['spent']:.4f}")
    print("the corrected words were judged by: " + ", ".join(f"{c['at']} {c['what']}" for c in
                                                             out["corrected_words_calls"]))
    print("re-run: " + json.dumps(rerun, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
