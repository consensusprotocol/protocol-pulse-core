#!/usr/bin/env python3
"""tests/select_by_id/proof/*.json (proof_saved_runs.py) -> the proof table in docs/audits/parallel/pp-selectid_PROOF_TABLE.md
(per run: models, groups, story calls / outcomes, line-up, ids resolve, eligibility re-check, claim; the preview's
overlap with the approved passages). Usage: python3 tests/select_by_id/proof_table.py"""
import glob
import json
import os
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_PROOF_TABLE.md")
ORDER = ("fresh_20261112_050611", "fresh_20261111_190259", "fresh_20261111_213954", "fresh_20261112_001448", "fresh_20261112_013452",
         "fresh_20261110_093150", "fresh_20261111_192645", "fresh_20261107_080503", "fresh_20261107_065702",
         "fresh_20261106_213852", "pinned_20261111_172202")


def story_outcomes(r):
    c = Counter()
    for g in r.get("groups") or []:
        st = g.get("story") or {}
        s = st.get("status")
        if s == "accepted":
            lo = g.get("lineup") or {}
            s = "story; line-up " + ({"accepted": "ACCEPTED", "declined": "declined", "rejected": "rejected",
                                      "model_error": "model error"}.get(lo.get("status"), "not asked (no word record)"))
        c[s] += 1
    return ", ".join(f"{n} {k}" for k, n in c.most_common())


def table(col):
    """Lines of one proof column (a directory of proof_saved_runs.py records)."""
    recs, paths = {}, {}
    for p in glob.glob(os.path.join(HERE, col, "*.json")):
        if os.path.basename(p) == "SPEND.json":
            continue
        r = json.load(open(p))
        recs[r["run"]], paths[r["run"]] = r, p
    try:
        spend = json.load(open(os.path.join(HERE, "proof", "SPEND.json")))
    except (OSError, ValueError):
        spend = {}
    lines = ["| run | written (ET) | judge | groups screened 48h / 72h | story calls | outcomes per group | line-up | "
             "every id resolves | line-up passes eligibility (re-check) | claim (verbatim source sentence) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for name in ORDER:
        r = recs.get(name)
        if not r:
            lines.append(f"| {name} | - | - | - | - | not run yet in this column | - | - | - | - |")
            continue
        res = r.get("result") or {}
        cl = r.get("clusters") or {}
        scr = cl.get("screened") or {}
        claim = (res.get("claim") or {}).get("text") if res.get("lineup") else next(
            ((g["story"]["claim"]["text"] if isinstance(g["story"].get("claim"), dict) else None)
             for g in r.get("groups") or [] if (g.get("story") or {}).get("status") == "accepted"), None)
        when = datetime.fromtimestamp(os.path.getmtime(paths[name]), ZoneInfo("America/New_York")).strftime("%H:%M")
        judge = ((r.get("models") or {}).get("judge (ModelChecks)") or "-").replace("xai:", "")
        lines.append(f"| {name} | {when} | {judge} | {scr.get('48h', '-')} / {scr.get('72h', '-')} | {r.get('story_calls')} | "
                     f"{story_outcomes(r) or r.get('stopped', '-')} | {'YES' if res.get('lineup') else 'no'} | "
                     f"{res.get('ids_resolve', '-') if res.get('lineup') else '-'} | "
                     f"{res.get('eligibility_recheck', '-') if res.get('lineup') else '-'} | "
                     f"{(claim or '-')[:110].replace('|', '/')} |")
    models = sorted({json.dumps(r.get("models"), sort_keys=True) for r in recs.values() if r.get("models")})
    lines.append("\nModels per run file (generator / judge): " + "; ".join(models) if models else "\nModels: not recorded")
    lines.append(f"\nStand-in spend estimate, all proof runs of this session: ${spend.get('usd_estimate')} over "
                 f"{spend.get('calls')} calls ({spend.get('prompt_tokens')} prompt / {spend.get('completion_tokens')} "
                 "completion tokens); per model, at the upper-bound USD prices per 1M tokens [input, output] each "
                 "stand-in declares:")
    for name, m in sorted((spend.get("by_model") or {}).items()):
        lines.append(f"- {name}: {m.get('calls')} calls, ${m.get('usd_estimate')} at {m.get('price_usd_per_1m')}")
    for name in ORDER:
        r = recs.get(name)
        if not r or not (r.get("result") or {}).get("lineup"):
            continue
        res = r["result"]
        lines.append(f"\n### {name}: the accepted line-up ({res.get('pool')}, story tier {res.get('story_tier')})")
        for s in res["segments"]:
            lines.append(f"- {s['segment']} {s['channel']} {s['video_id']} {s['start']:.2f}-{s['end']:.2f} "
                         f"({s['seconds']} s): \"{s['text']}\"")
    pv = recs.get("pinned_20261111_172202")
    if pv and pv.get("overlap_with_approved"):
        lines.append("\n### pinned_20261111_172202 (the approved preview): overlap with its four passages")
        lines.append("| approved | channel | chosen by select_by_id | same words | overlap s | eligible with the model's "
                     "own story | why not |")
        lines.append("|---|---|---|---|---|---|---|")
        for o in pv["overlap_with_approved"]:
            lines.append(f"| {o['approved']} | {o['channel']} | {o.get('chosen') or '-'} | {o.get('same_words')} | "
                         f"{o.get('overlap_s') or '-'} | {o.get('eligible_with_the_models_story', '-')} | "
                         f"{(o.get('reasons_with_the_models_story') or '').replace('|', '/')[:220]} |")
    return lines


COLUMNS = (("proof_judge_t0", "COLUMN OF RECORD: generator claude-fable-5-2, judge grok-4.20-0309-reasoning at "
            "temperature 0 with the attempt's seed (production parity: LocalLLM checks run at temperature 0)"),
           ("proof_judge_default", "SENSITIVITY: the same generator and recordings, the judge at the API's DEFAULT "
            "temperature (its verdicts varied across attempts); rows written before 02:25 ET come from the pre-audit-C2 "
            "code (the 02:02 run) and are superseded"))


def main():
    out = ["# pp-selectid — proof table (generated by tests/select_by_id/proof_table.py)", ""]
    for col, title in COLUMNS:
        if not glob.glob(os.path.join(HERE, col, "*.json")):
            continue
        out += [f"## {title}", ""] + table(col) + [""]
    open(OUT, "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
