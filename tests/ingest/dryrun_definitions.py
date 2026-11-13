#!/usr/bin/env python3
"""tests/ingest/dryrun_definitions.py: option A of ruling 40 MEASURED before any ruling (a dry run; nothing is written
to the ledger, the queue or the adapter).

Option A is "a tighter miner prompt with those definitions": the miner's prompt (mine/2) with its three flag lines
replaced by the ruling's definitions, verbatim, and nothing else changed (one change, one test). The rows checked by
pipeline/ingest/flagcheck.py are re-mined from the same windows by the same model that mined them:
  control  mine/2 exactly as it ran (its prompt rebuilt and checked against the sha the ledger recorded), called again
           without the reply cache: how much a re-run alone moves the flags (the noise floor);
  A        mine/2 with the ruling's three definitions.
A row's flags in an arm are the union over every window containing its range (as mine_video joins observations).
Each arm is scored against the SAME checker answers (the flag check's second model), on the rows the arm returned
again (a re-mined window may not return the same range: counted as not re-observed, never as a flag change).
Rows mined by a model that cannot be called now (the spend freeze) are not re-mined: counted, not guessed.

usage: python3 tests/ingest/dryrun_definitions.py --check <flagcheck.json> [--out DIR] [--max-inflight 8]
"""
import argparse
import json
import os
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from pipeline.ingest import config, contract, flagcheck, ledger, mine, providers  # noqa: E402
from pipeline.ingest.providers import AllBackendsFailed  # noqa: E402

OLD_LINES = {
    "accusation": '  "accusation"              crime, fraud, insolvency or dishonesty alleged against a named person or company\n',
    "imperative": '  "imperative"              telling the viewer to buy, sell, use leverage or otherwise act financially\n',
    "single_source_breaking": '  "single_source_breaking"  an unconfirmed breaking factual claim\n',
}


def template_a():
    t = mine.PROMPT
    for f, old in OLD_LINES.items():
        assert t.count(old) == 1, f"mine.PROMPT no longer has the line for {f}"
        t = t.replace(old, f'  "{f}"{" " * (24 - len(f))}{flagcheck.DEFINITIONS[f]}\n')
    return t


def main(a):
    t0 = time.time()
    with open(a.check) as f:
        check = json.load(f)
    results = check["results"]
    root = config.store_root()
    path = os.path.join(root, "moments", "moment_ledger.jsonl")
    lines, _ = ledger.read(path)
    latest = {l["moment_id"]: l for l in lines}
    out = a.out or os.path.join(os.path.dirname(a.check), "dryrun_definitions")
    os.makedirs(out, exist_ok=True)
    cfg = providers.load_config()
    cfg["global"]["max_inflight"] = int(a.max_inflight)
    attempts, alock = [], threading.Lock()

    def on_attempt(rec):
        rec = dict(rec, at=config.iso())
        rec.pop("content", None)
        with alock:
            attempts.append(rec)
            with open(os.path.join(out, "attempts.jsonl"), "a") as f:
                f.write(json.dumps(rec, default=str) + "\n")

    router = providers.Router(cfg, on_attempt=on_attempt, cache_dir=os.path.join(out, "replies"))
    callable_mine = router.effective("mine")
    if not callable_mine:
        raise SystemExit("no callable mine back-end: nothing measured")
    bid = callable_mine[0]
    model = router.backends[bid].model
    tmpl_a = template_a()
    skipped = Counter()
    rows, jobs = [], {}
    for r in results:
        l = latest.get(r["moment_id"])
        if l is None:
            skipped["line not in the ledger"] += 1
            continue
        if l["mined"].get("model") != model:
            skipped[f"mined by {l['mined'].get('model')} (not callable now)"] += 1
            continue
        rec = ledger.record_by_sha(root, l["video_id"], l["transcript_sha256"])
        if rec is None:
            skipped["transcript record not found"] += 1
            continue
        _, _, sents = contract.sentences(rec)
        a_, b_ = l["sentences"]
        wins = [w for w in mine.windows(sents) if w[0]["k"] <= a_ and b_ <= w[-1]["k"]]
        if l["mined"]["window"] not in [[w[0]["k"], w[-1]["k"]] for w in wins]:
            skipped["the recorded window is not among today's windows"] += 1
            continue
        meta = {"exact_title": l["title"], "channel_name": l["channel_name"]}
        chan = {"display_name": l["channel_name"]}
        keys = []
        for w in wins:
            k = (l["video_id"], w[0]["k"], w[-1]["k"])
            keys.append(k)
            jobs.setdefault(k, (meta, chan, w, l["mined"]["prompt_sha256"] if [w[0]["k"], w[-1]["k"]] ==
                                l["mined"]["window"] else None))
        rows.append((r, l, keys))
    print(f"{len(rows)} rows re-mined from {len(jobs)} windows by {bid}; not re-mined: {dict(skipped)}")
    rebuilt = Counter()
    for k, (meta, chan, w, sha) in jobs.items():
        if sha is not None:
            rebuilt["same as recorded" if providers.sha256(mine.prompt(meta, chan, w)) == sha else "DIFFERENT"] += 1
    print(f"control prompts rebuilt vs the recorded sha: {dict(rebuilt)}")

    def run(job):
        k, arm = job
        meta, chan, w, _ = jobs[k]
        p = mine.prompt(meta, chan, w, template=None if arm == "control" else tmpl_a)
        try:
            o = router.run("mine", p, mine.SCHEMA, mine.validator([s["k"] for s in w]),
                           tag={"video_id": k[0], "window": [k[1], k[2]], "arm": arm}, only=bid,
                           use_cache=(arm != "control"))
        except AllBackendsFailed as e:
            return k, arm, None, str(e)[:200]
        return k, arm, o.obj, None

    replies, failed = {}, []
    with ThreadPoolExecutor(int(a.max_inflight)) as ex:
        for k, arm, obj, err in ex.map(run, [(k, arm) for k in jobs for arm in ("control", "A")]):
            if obj is None:
                failed.append({"window": list(k), "arm": arm, "error": err})
            else:
                replies[(k, arm)] = obj
    arms = {"original": {}, "control": {}, "A": {}}
    for r, l, keys in rows:
        rng = tuple(l["sentences"])
        arms["original"][r["moment_id"]] = set(l["risk"])
        for arm in ("control", "A"):
            got = [c for k in keys for c in (replies.get((k, arm)) or []) if tuple(c["s"]) == rng]
            if any((k, arm) not in replies for k in keys):
                continue                                   # a window failed: this row is not measured in the arm
            if got:
                arms[arm][r["moment_id"]] = set().union(*(set(c["risk"]) for c in got))
    checks = {r["moment_id"]: r["checks"] for r, _, _ in rows}
    common = set(arms["control"]) & set(arms["A"])
    report = {"backend": bid, "rows": len(rows), "windows": len(jobs), "not_re_mined": dict(skipped),
              "control_prompts_rebuilt": dict(rebuilt), "failed_windows": failed,
              "re_observed": {arm: len(arms[arm]) for arm in ("control", "A")}, "common_rows": len(common),
              "flags": {}, "all_moments": {}}
    for f in flagcheck.FLAGS:
        d = {}
        for arm in ("original", "control", "A"):
            flagged = [m for m in common if f in arms[arm][m]]
            cnt = Counter(flagcheck.cell(checks[m].get(f)) for m in flagged)
            n = cnt["yes"] + cnt["no"] + cnt["unsure"]
            missed = [m for m in common if f not in arms[arm][m] and flagcheck.cell(checks[m].get(f)) == "yes"]
            d[arm] = {"flagged": len(flagged), "checker": {c: cnt[c] for c in flagcheck.CELLS},
                      "precision": None if not n else round(cnt["yes"] / n, 3),
                      "checker_yes_not_flagged": len(missed)}
        d["control_differs_from_original"] = sum(1 for m in common if (f in arms["control"][m]) != (f in arms["original"][m]))
        d["A_differs_from_original"] = sum(1 for m in common if (f in arms["A"][m]) != (f in arms["original"][m]))
        report["flags"][f] = d
    for arm in ("control", "A"):
        ms = [c for (k, ar), obj in replies.items() if ar == arm for c in obj]
        report["all_moments"][arm] = {"moments": len(ms), **{f: sum(1 for c in ms if f in c["risk"])
                                                             for f in flagcheck.FLAGS},
                                      "any_hard": sum(1 for c in ms if set(c["risk"]) & set(mine.HARD_RISKS))}
    report["spend_usd"] = round(sum((x.get("cost_usd") or 0.0) for x in attempts), 6)
    report["calls"] = dict(Counter(x.get("kind") for x in attempts))
    report["seconds"] = round(time.time() - t0, 1)
    report["template_a_flag_lines"] = [ln for ln in tmpl_a.splitlines()
                                       if any(f'"{f}"' in ln for f in flagcheck.FLAGS) and ln.startswith('  "')]
    with open(os.path.join(out, "dryrun_definitions.json"), "w") as f:
        json.dump({"report": report, "arms": {arm: {m: sorted(v) for m, v in d.items()} for arm, d in arms.items()}},
                  f, indent=1)
    write_md(report, os.path.join(out, "DRYRUN.md"))
    print(json.dumps(report, indent=1))


def write_md(r, path):
    md = [f"Re-mined by {r['backend']}: {r['rows']} checked rows from {r['windows']} windows (not re-mined: "
          f"{r['not_re_mined']}); control prompts rebuilt vs the recorded hash: {r['control_prompts_rebuilt']}; "
          f"failed windows: {len(r['failed_windows'])}; rows returned again: control {r['re_observed']['control']}, "
          f"A {r['re_observed']['A']}; scored on the {r['common_rows']} rows both arms returned.", "",
          "| flag | arm | flagged | checker yes / no / unsure / unmeasured | precision | checker yes, not flagged | "
          "differs from the original |", "|---|---|---|---|---|---|---|"]
    for f, d in r["flags"].items():
        for arm in ("original", "control", "A"):
            x = d[arm]
            diff = {"original": "-", "control": d["control_differs_from_original"],
                    "A": d["A_differs_from_original"]}[arm]
            cells = " / ".join(str(x["checker"][c]) for c in flagcheck.CELLS)
            prec = "-" if x["precision"] is None else f"{100 * x['precision']:.0f} %"
            md.append(f"| {f} | {arm} | {x['flagged']} | {cells} | {prec} | {x['checker_yes_not_flagged']} | {diff} |")
    md += ["", "Every moment the two arms returned from these windows (not only the checked rows):", "",
           "| arm | moments | imperative | accusation | single_source_breaking | any hard flag |", "|---|---|---|---|---|---|"]
    for arm, x in r["all_moments"].items():
        md.append(f"| {arm} | {x['moments']} | {x['imperative']} | {x['accusation']} | {x['single_source_breaking']} | "
                  f"{x['any_hard']} |")
    md += ["", f"Spend ${r['spend_usd']:.4f} ({r['calls']}), {r['seconds']:.0f} s."]
    with open(path, "w") as fh:
        fh.write("\n".join(md) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", required=True, help="flagcheck.json of a flag-check run")
    ap.add_argument("--out")
    ap.add_argument("--max-inflight", type=int, default=8)
    main(ap.parse_args())
