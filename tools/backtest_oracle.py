#!/usr/bin/env python3
"""tools/backtest_oracle.py — editorial supply backtest (order pp-backtest 2026-11-12). CPU and API only.

  export  [--runs NAME ...] [--out DIR]   BITCOIN_STATEMENTS_<stamp>.jsonl + manifest for every saved universe
  probe                                   one tiny structured call per model (key, model id, schema accepted)
  oracle  [--runs NAME ...] [--parallel N] [--no-judge] [--variant V]   blind oracle + blind judge per day
          (pipeline/oracle/run.py); V = same_dev_hard (the order's rules, default) | same_dev | moments (the 01:55
          note: windows as targets, PBX's 01:48 moments rule, as many sentence-disjoint line-ups as exist)
  replay  [--runs NAME ...]               the selector at THIS code on each saved universe, CPU only, gemma from its
                                          validated-reply cache only (pipeline/oracle/replay.py; NOT_RERUN at a miss)
  witness [--runs NAME ...]               the reviewers' witness checks on accepted moments line-ups, each clip in
                                          its original context (pipeline/oracle/witness.py; 02:30 note)
  ab      --role R [--backends B,...] [--runs ...] [--limit N]   blind A/B of one model role on saved data (law L-x):
          judge / witness / grouping replay the exact stored prompts on each back-end against the recorded verdicts
          (+ must-fail swaps for the judge); writer re-runs the given days per back-end with the judge fixed. A local
          GPU0 back-end runs only inside the integrator's GPU0 lease (PP_GPU0_LEASE_HELD=1).
  group   [--runs NAME ...] [--variant V]  the accepted line-ups grouped by development (one blind grouping
                                          call per day with >= 2; integrator Q1: distinct legal developments per day)
  score   [--runs NAME ...]               the selector's records vs the judged line-ups (pipeline/oracle/score.py)
  report                                  docs/audits/BACKTEST_SUPPLY_REPORT.md from DAY.json + SCORE.json
Defaults: runs = every runs/fresh_* whose TOPIC_SELECTION.json saved a universe with transcript shas; artefacts in
/home/ultron/heimdall_probe/pp_redteam/oracle/<stamp>/ (the order's oracle dir); spend ledger SPEND.jsonl there,
capped at llm.SPEND_CAP_USD. Reads the main tree's runs and transcript store, never writes to them.
"""
import argparse
import glob
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
MAIN_RUNS = "/home/ultron/protocol_pulse/runs"
OUT_ROOT = "/home/ultron/heimdall_probe/pp_redteam/oracle"
os.environ.setdefault("PP_EDITORIAL_STORE", "/home/ultron/protocol_pulse/data/editorial")   # read-only reads


def saved_runs(runs_dir=MAIN_RUNS, names=None):
    out = []
    for p in sorted(glob.glob(os.path.join(runs_dir, "fresh_*", "TOPIC_SELECTION.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if d.get("started") and any(u.get("transcript_sha256") for u in d.get("universe") or []):
            out.append(os.path.dirname(p))
    return [r for r in out if not names or os.path.basename(r) in names]


def stamp(run_dir):
    return os.path.basename(os.path.normpath(run_dir)).replace("fresh_", "")


def cmd_export(a):
    from pipeline.oracle import export as X
    rows = []
    for r in saved_runs(names=a.runs):
        path, man = X.write_export(r, os.path.join(a.out, stamp(r)))
        rows.append((stamp(r), man))
        print(f"{stamp(r)}  rows {man['rows']:5d}  bitcoin {man['bitcoin_rows']:4d}  videos {man['exported_videos']:3d}"
              f"/{man['universe_videos']}  gaps {len(man['gaps']):2d}  sha256 {man['rows_sha256']}", flush=True)
    return 0


def cmd_probe(a):
    from pipeline.oracle import llm, providers as PV
    ledger = llm.Ledger(os.path.join(a.out, "SPEND.jsonl"))
    schema = {"type": "object", "additionalProperties": False, "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
    for name in a.only or list(PV.BACKENDS):
        ok, why = PV.available(name, notify_dir=a.out)
        if not ok:
            print(f"{name}: skipped ({why})")
            continue
        try:
            text, raw, row = PV.call_backend(name, "Reply with JSON only.", 'Return {"ok": true}.', schema, ledger,
                                             f"probe {name}")
            print(f"{name}: {row['model']} {text[:40]!r} {row['seconds']} s {row['usd']} USD")
        except Exception as e:
            print(f"{name}: FAILED " + llm.redact(f"{type(e).__name__}: {e}")[:180])
    print(f"ledger spent {ledger.spent():.4f} USD")
    return 0


def _chain(text):
    return [x for x in (text or "").split(",") if x] or None


def writer_vendor(vdir):
    """The vendor that wrote a day's line-ups (from ORACLE.json usage; pre-L-x artefacts carry only the model)."""
    from pipeline.oracle import providers as PV
    with open(os.path.join(vdir, "ORACLE.json"), encoding="utf-8") as f:
        o = json.load(f)
    use = (o["attempts"][o["attempt_used"] - 1].get("usage") or {}) if o.get("attempt_used") else {}
    vendor = use.get("vendor") or PV.vendor_of_model(use.get("model"))
    if not vendor:          # a judge-like role cannot be kept off a writer it cannot name (audit F4): refuse
        raise SystemExit(f"{vdir}: the writer's vendor is not recorded and its model {use.get('model')!r} is not in "
                         "the provider config; this day's judge-like roles cannot be kept off the writer's vendor")
    return vendor


def cmd_oracle(a):
    from pipeline.oracle import export as X, llm, providers as PV, run as R
    ledger = llm.Ledger(os.path.join(a.out, "SPEND.jsonl"))

    def one(run_dir):
        st = stamp(run_dir)
        day_dir = os.path.join(a.out, st)
        path = os.path.join(day_dir, f"BITCOIN_STATEMENTS_{st}.jsonl")
        rows = X.read_rows(path)
        with open(path.replace(".jsonl", ".manifest.json"), encoding="utf-8") as f:
            now = json.load(f)["started"]
        writer, judge = PV.paired_calls(_chain(a.writer_chain), _chain(a.judge_chain), a.out)   # L-x
        day = R.run_day(day_dir, rows, now, writer, judge, ledger, judge=not a.no_judge, variant=a.variant)
        return (f"{st}  {a.variant}  {day['availability']}  ({len(day['lineups'])} line-ups, accepted "
                f"{day['accepted']}, distinct {day['distinct_accepted']}, hard-window distinct "
                f"{day['distinct_accepted_hard_windows']}; writer {day['oracle_model']}, judge {day['judge_model']}; "
                f"spent {ledger.spent():.2f} USD)")
    with ThreadPoolExecutor(a.parallel) as ex:
        for line in ex.map(one, saved_runs(names=a.runs)):
            print(line, flush=True)
    return 0


def cmd_group(a):
    from pipeline.oracle import export as X, lineup as L, llm, providers as PV, run as R
    ledger = llm.Ledger(os.path.join(a.out, "SPEND.jsonl"))
    for r in saved_runs(names=a.runs):
        st = stamp(r)
        base = os.path.join(a.out, st)
        day_dir = os.path.join(base, L.VARIANTS[a.variant]["subdir"]) if L.VARIANTS[a.variant]["subdir"] else base
        if not os.path.exists(os.path.join(day_dir, "DAY.json")):
            print(f"{st}  no DAY.json for {a.variant}", flush=True)
            continue
        rows = X.read_rows(os.path.join(base, f"BITCOIN_STATEMENTS_{st}.jsonl"))
        with open(os.path.join(base, f"BITCOIN_STATEMENTS_{st}.manifest.json"), encoding="utf-8") as f:
            now = json.load(f)["started"]
        g = R.group_developments(day_dir, rows, now, PV.role_call("grouping", {writer_vendor(day_dir)},
                                                                 notify_dir=a.out), ledger)
        print(f"{st}  {a.variant}  {g['status']}  accepted {len(g['accepted'])}  developments "
              f"{len(g.get('groups') or []) if g['status'] == 'OK' else 'not measured'}", flush=True)
    return 0


def cmd_witness(a):
    from pipeline.oracle import export as X, llm, providers as PV, witness as W
    ledger = llm.Ledger(os.path.join(a.out, "SPEND.jsonl"))

    def one(r):
        st = stamp(r)
        base = os.path.join(a.out, st)
        vdir = os.path.join(base, "moments")
        if not os.path.exists(os.path.join(vdir, "DAY.json")):
            return f"{st}  no moments DAY.json"
        rows = X.read_rows(os.path.join(base, f"BITCOIN_STATEMENTS_{st}.jsonl"))
        with open(os.path.join(base, f"BITCOIN_STATEMENTS_{st}.manifest.json"), encoding="utf-8") as f:
            now = json.load(f)["started"]
        w = W.run_witness(vdir, rows, now, PV.role_call("witness", {writer_vendor(vdir)}, notify_dir=a.out), ledger)
        n = {c: sum(1 for x in w["lineups"] if x["checks"].get(c) is True) for c in W.CHECKS}
        failed = sum(1 for x in w["lineups"] if x["status"] != "OK")
        return f"{st}  accepted {len(w['lineups'])}  pass per check {n}  witness_failed {failed}"
    with ThreadPoolExecutor(5) as ex:
        for line in ex.map(one, saved_runs(names=a.runs)):
            print(line, flush=True)
    return 0


def cmd_ab(a):
    from pipeline.oracle import ab as AB, export as X, llm, providers as PV, run as R
    ledger = llm.Ledger(os.path.join(a.out, "SPEND.jsonl"))
    stamps = [stamp(r) for r in saved_runs(names=a.runs)]
    backends = _chain(a.backends) or [b for b in PV.BACKENDS]
    out = os.path.join(a.out, "ab")
    if a.role == "writer":
        res = {}
        for name in backends:
            ok, why = PV.available(name, notify_dir=a.out)
            if not ok:
                res[name] = {"skipped": why}
                continue
            for st in stamps:
                base = os.path.join(a.out, st)
                rows = X.read_rows(os.path.join(base, f"BITCOIN_STATEMENTS_{st}.jsonl"))
                with open(os.path.join(base, f"BITCOIN_STATEMENTS_{st}.manifest.json"), encoding="utf-8") as f:
                    now = json.load(f)["started"]
                vend = PV.BACKENDS[name]["vendor"]
                day_dir = os.path.join(out, "writer", name, st)        # never inside the day dir the report reads
                os.makedirs(day_dir, exist_ok=True)
                t0 = time.time()
                stored = os.path.exists(os.path.join(day_dir, "DAY.json"))
                resumed = bool(a.resume and stored)
                if resumed:                                             # finished earlier: read, no call
                    with open(os.path.join(day_dir, "DAY.json"), encoding="utf-8") as f:
                        day = json.load(f)
                elif a.rejudge and stored:                              # judge only what was never judged whole
                    day = R.rejudge_day(day_dir, rows, now, PV.role_call("judge", {vend}, chain=_chain(a.judge_chain),
                                                                         notify_dir=a.out), ledger)
                else:
                    day = R.run_day(day_dir, rows, now,
                                    PV.role_call("writer", chain=[name], notify_dir=a.out),
                                    PV.role_call("judge", {vend}, chain=_chain(a.judge_chain), notify_dir=a.out),
                                    ledger)
                res.setdefault(name, {})[st] = {k: day.get(k) for k in ("availability", "accepted", "distinct_accepted",
                                                                        "oracle_status", "oracle_model", "judge_model")}
                with open(os.path.join(day_dir, "ORACLE.json"), encoding="utf-8") as f:
                    atts = json.load(f)["attempts"]
                res[name][st].update(
                    seconds=None if resumed else round(time.time() - t0), resumed=resumed,
                    lineups=len(day["lineups"]),
                    checkfail=sum(1 for x in day["lineups"] if x["violations"]),
                    judge_illegal=sum(1 for x in day["lineups"] if (x["judge"] or {}).get("verdict") == "ILLEGAL"),
                    writer_attempts=len(atts), writer_failed_attempts=sum(1 for x in atts if x.get("error")),
                    writer_s=[(x.get("usage") or {}).get("seconds") for x in atts],
                    writer_usd=round(sum((x.get("usage") or {}).get("usd") or 0.0 for x in atts), 6),
                    writer_usd_source=sorted({(x.get("usage") or {}).get("usd_source") for x in atts} - {None}))
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "AB_writer.json"), "w", encoding="utf-8") as f:
            json.dump({"role": "writer", "runs": stamps, "results": res}, f, indent=1, default=str)
        print(json.dumps(res, indent=1, default=str)[:3000])
        return 0
    items = AB.judge_items(a.out, stamps) if a.role == "judge" else AB.recorded_items(a.out, stamps, a.role)
    if a.mustfail_only:                                # the reference back-end: its own recorded verdicts are not re-asked
        items = [x for x in items if AB.is_swap(x[0])]
    subs = {"judge": ("", "same_dev_hard_max"), "witness": ("moments",), "grouping": ("", "same_dev")}[a.role]
    vendors = {writer_vendor(os.path.join(a.out, st, sub)) for st in stamps for sub in subs
               if os.path.exists(os.path.join(a.out, st, sub, "ORACLE.json"))}
    if None in vendors:                                # a writer that cannot be named cannot be kept off its own work
        raise SystemExit(f"writer vendor unknown for some {a.role} items: {sorted(map(str, vendors))}")
    print(f"{len(items[:a.limit])} items; writers' vendors kept off this role: {sorted(vendors)}", flush=True)
    res = AB.run_role(a.role, items, backends, ledger, os.path.join(out, a.tag or ""), vendors, limit=a.limit,
                      parallel=a.parallel)
    for name, r in res.items():
        print(name, {k: v for k, v in r.items() if k != "rows"})
    return 0


def cmd_replay(a):
    os.environ["CUDA_VISIBLE_DEVICES"] = ""          # no GPU may be touched (GPU0 is leased to the live run)
    from pipeline.oracle import replay as RP
    RP.TORCH_THREADS = a.threads
    E, digest = RP.CpuEmbedder(os.path.join(a.out, "cpu_vectors")), RP.cache_digest()
    with RP.no_writes_under(RP.MAIN_TREE):          # the store is read, never written (a write is a CRASH outcome)
        for r in saved_runs(names=a.runs):
            rec = RP.replay(r, os.path.join(a.out, stamp(r), "replay_head"), E, digest, MAIN_RUNS)
            print(f"{stamp(r)}  {rec['outcome'][:60]}  {(rec['gemma_miss'] or {}).get('call')} after "
                  f"{(rec['stopped_at'] or {}).get('phase')}  cache hits {rec['gemma_cache_hits']}  cpu vectors "
                  f"{len(rec['cpu_vectors_for'])}  {rec['seconds']} s", flush=True)
    return 0


def cmd_score(a):
    from pipeline.oracle import score as S
    for r in saved_runs(names=a.runs):
        res = S.score_run(r, os.path.join(a.out, stamp(r)))
        print(stamp(r), res["summary_line"], flush=True)
    return 0


def cmd_report(a):
    from pipeline.oracle import report as RP
    path = RP.write_report([os.path.join(a.out, stamp(r)) for r in saved_runs()], a.out,
                           os.path.join(REPO, "docs", "audits", "BACKTEST_SUPPLY_REPORT.md"),
                           analysis_path=os.path.join(REPO, "docs", "audits", "parallel", "pp-backtest_ANALYSIS.md"))
    print(path)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("export", "probe", "oracle", "group", "witness", "ab", "replay", "score", "report"):
        p = sub.add_parser(name)
        p.add_argument("--runs", nargs="*")
        p.add_argument("--out", default=OUT_ROOT)
        if name == "oracle":
            p.add_argument("--parallel", type=int, default=3)
            p.add_argument("--no-judge", action="store_true")
            p.add_argument("--variant", default="same_dev_hard",
                           choices=("same_dev_hard", "same_dev_hard_max", "same_dev", "moments"))
            p.add_argument("--writer-chain", help="comma list of back-ends (default: providers.ROLES['writer'])")
            p.add_argument("--judge-chain", help="comma list of back-ends (default: providers.ROLES['judge'])")
        if name == "ab":
            p.add_argument("--role", required=True, choices=("writer", "judge", "witness", "grouping"))
            p.add_argument("--backends", help="comma list of back-ends (default: every back-end)")
            p.add_argument("--judge-chain", help="writer A/B: the fixed judge chain")
            p.add_argument("--limit", type=int)
            p.add_argument("--mustfail-only", action="store_true")
            p.add_argument("--tag", help="sub-directory of ab/ for this batch")
            p.add_argument("--parallel", type=int, default=8, help="items in flight at once (all back-ends together)")
            p.add_argument("--resume", action="store_true", help="writer: a back-end / day with a DAY.json is read, "
                                                                  "not re-run")
            p.add_argument("--rejudge", action="store_true", help="writer: a stored day's line-ups whose judge never "
                                                                   "returned whole are judged again (nothing else)")
        if name == "group":
            p.add_argument("--variant", default="same_dev_hard", choices=("same_dev_hard", "same_dev_hard_max", "same_dev"))
        if name == "probe":
            p.add_argument("--only", nargs="*", help="back-end names (default: every back-end)")
        if name == "replay":
            p.add_argument("--threads", type=int, default=8)
    a = ap.parse_args(argv)
    return {"export": cmd_export, "probe": cmd_probe, "oracle": cmd_oracle, "group": cmd_group,
            "witness": cmd_witness, "ab": cmd_ab, "replay": cmd_replay, "score": cmd_score,
            "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
