#!/usr/bin/env python3
"""pipeline/oracle/report.py — docs/audits/BACKTEST_SUPPLY_REPORT.md from the saved DAY.json / SCORE.json files.

Data sections are generated (tables, counts beside every percentage, examples by sentence id); the analysis that
needs a reader's judgement (what each loss stage implies, trade-offs) is written by hand in
docs/audits/parallel/pp-backtest_ANALYSIS.md and included verbatim, so a re-run never overwrites it.
"""
import glob
import statistics
import json
import os
from collections import Counter
from datetime import datetime, timezone

from pipeline.oracle import export as X
from pipeline.oracle import lineup as L
from pipeline.oracle import run as R
from pipeline.oracle import score as S

RECORDS = ("as_run", "cold_backtest_394ffe5a", "replay_head")


def pct(k, n):
    return f"{k} of {n}" + (f" ({100 * k / n:.0f} %)" if n else " (not measured: n = 0)")


def et_date(utc_iso):
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(utc_iso).astimezone(ZoneInfo("America/New_York")).strftime("%b %d %H:%M ET")


def load(day_dir, name):
    p = os.path.join(day_dir, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _rows(day_dir):
    stamp = os.path.basename(day_dir)
    with open(os.path.join(day_dir, f"BITCOIN_STATEMENTS_{stamp}.jsonl"), encoding="utf-8") as f:
        return {r["id"]: r for r in map(json.loads, f)}


def lineup_text(lu, rows, limit=170):
    out = []
    for label, ids in L.segments(lu):
        r0 = rows[ids[0]]
        txt = " ".join(rows[i]["text"] for i in ids)
        out.append(f"  - {label} `{ids[0]}`{'..' + ids[-1].split(':')[1] if len(ids) > 1 else ''} {r0['channel']}: "
                   f"\"{txt[:limit]}{'...' if len(txt) > limit else ''}\"")
    return "\n".join(out)


def write_report(day_dirs, out_root, path, analysis_path=None):
    days = []
    for d in day_dirs:
        day, score, man = load(d, "DAY.json"), load(d, "SCORE.json"), None
        stamp = os.path.basename(d)
        man = load(d, f"BITCOIN_STATEMENTS_{stamp}.manifest.json")
        days.append({"dir": d, "stamp": stamp, "day": day, "score": score, "man": man,
                     "oracle": load(d, "ORACLE.json")})
    spend = []
    sp = os.path.join(out_root, "SPEND.jsonl")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as f:
            spend = [json.loads(x) for x in f if x.strip()]
    lines = ["# BACKTEST SUPPLY REPORT: did a line-up that passes our rules exist, and did the selector find it?", ""]
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    measured = [x for x in days if x["day"] and x["day"]["availability"].split(" ")[0] in
                ("AVAILABLE", "NONE", "NOT_AVAILABLE")]
    avail = [x for x in measured if x["day"]["availability"] == "AVAILABLE"]
    lines += [f"Generated {gen} by `tools/backtest_oracle.py report` (branch pp-backtest). Order pp-backtest, "
              "2026-11-12 (session pipeline_pp_backtest).", "",
              f"**Sample size: {len(days)} saved runs on {len({x['man']['today'] for x in days if x['man']})} UTC dates. "
              "This is a small sample: every number below is a count of these runs, stated with its raw count; no "
              "rate in this report generalises beyond them, and no confidence interval is claimed.**", ""]
    incomplete_at = len(lines)                      # filled in once every table is counted (incomplete_section)
    # ── the table ──
    lines += ["## 1. Per run", "",
              "| run (UTC stamp) | started (ET) | rows shown / exported | oracle | proposed / pass the code checks / pass the blind judge "
              "| availability | as-run selector | loss stage as run | cold backtest @394ffe5a | replay at HEAD | layout column |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    stage_counts = {r: Counter() for r in RECORDS}
    near_counts = {r: Counter() for r in RECORDS}
    layout_dead, layout_n = 0, 0
    recall = {r: [0, 0, 0] for r in RECORDS}
    selected = {r: [] for r in RECORDS}
    for x in days:
        day, score, man = x["day"], x["score"] or {}, x["man"]
        if not day:
            lines.append(f"| {x['stamp']} | - | - | not run | - | - | - | - | - | - | - |")
            continue
        lus = day["lineups"]
        prop, passed = len(lus), sum(1 for r in lus if not r["violations"])
        judged_ok = sum(1 for r in lus if r["accepted"])
        recs = {r["name"]: r for r in score.get("records", [])}
        loss = {}
        for name in RECORDS:
            st = [t["traces"][name]["loss_stage"] for t in score.get("lineups", []) if name in t["traces"]]
            loss[name] = ", ".join(sorted(set(st))) if st else "-"
            for s in st:
                stage_counts[name][s] += 1
            for t in score.get("lineups", []):                 # split across clusters: decided (complete record)
                tr = t["traces"].get(name) or {}                   # or where an incomplete record stopped
                if tr.get("loss_stage") == "CLUSTER_FORMATION" or (
                        tr.get("loss_stage") == "NOT_REACHED" and "no cluster held" in (tr.get("note") or "")):
                    near_counts[name][tr.get("near_furthest_stage") or (
                        "held one channel's, no decision recorded (NOT_REACHED)" if tr.get("n_near")
                        else "none held any")] += 1
            if name in recs:
                if recs[name].get("selected_lineup"):
                    selected[name].append(x["stamp"])
                if day["availability"] == "AVAILABLE" and recs[name].get("complete"):
                    recall[name][1] += 1
                    recall[name][0] += int(bool(recs[name].get("recall_hit")))
                elif day["availability"] == "AVAILABLE":
                    recall[name][2] += 1           # crashed / stopped / NOT_RERUN: no selection to measure
        for t in score.get("lineups", []):
            layout_n += 1
            layout_dead += int(not t["layout_survives"])
        lay = "; ".join(f"L{t['lineup']} {'survives' if t['layout_survives'] else 'DIES'}"
                        for t in score.get("lineups", [])) or "-"
        asrun = recs.get("as_run", {})
        outcome = ("SELECTED" if asrun.get("selected") else (asrun.get("decision") or
                   ("crashed" if asrun.get("crashed") else f"stopped at {asrun.get('progress')}")))
        rp = recs.get("replay_head", {}).get("replay", {})
        rp_txt = (f"{rp.get('outcome', '-')[:40]} at {(rp.get('stopped_at') or {}).get('phase')}; loss {loss['replay_head']}"
                  if rp else "-")
        lines.append(f"| {x['stamp']} | {et_date(man['started'])} | {day['rows_shown']} / {day['rows_exported']} | "
                     f"{day['oracle_status']} {day['oracle_verdict'] or ''} | {prop} / {passed} / {judged_ok} | "
                     f"{plain(day['availability'])} | {str(outcome)[:60]} | {loss['as_run']} | "
                     f"{loss['cold_backtest_394ffe5a'] if 'cold_backtest_394ffe5a' in recs else 'no record'} | {rp_txt} | {lay} |")
    n_lu = sum(len(x["score"]["lineups"]) for x in days if x["score"])
    lines += ["", "## 2. Overall (raw counts beside every rate)", "",
              f"- Availability (a line-up the oracle proposed, the deterministic checks pass and the blind judge says "
              f"passes our rules): {pct(len(avail), len(measured))} measured runs; not measured: "
              f"{len(days) - len(measured)} ({', '.join(x['stamp'] + ': ' + plain(x['day']['availability']) for x in days if x['day'] and x not in measured) or 'none'}).",
              f"- Accepted line-ups in total: {n_lu}."]
    for name in RECORDS:
        k, n, m = recall[name]
        lines.append(f"- Selector recall, {name}: " + (
            f"{pct(k, n)} available runs whose record completed a selection reached an equivalent line-up (same "
            f"development by a shared sentence in >= 2 channels' segments)" if n else
            "not measured: no record completed a selection") + (
            f"; {m} run(s) not measured (the record crashed, stopped or hit NOT_RERUN before selecting)" if m else "")
            + ".")
    for name in RECORDS:
        lines.append(f"- Selector precision, {name}: selector-accepted line-ups = {len(selected[name])}"
                     + (f" ({', '.join(selected[name])})" if selected[name] else
                        ": not measured (the selector accepted no line-up on any saved run in this record)") + ".")
    lines.append(f"- Layout column: {pct(layout_dead, layout_n)} accepted line-ups stop passing our rules "
                 "once segments from layout-ineligible channels (has_chyron: Bitcoin Magazine, CoinDesk) are removed.")
    lines += ["", "## 3. Where the line-ups that pass our rules were lost (count of accepted line-ups per stage)", "",
              "| stage | " + " | ".join(RECORDS) + " |", "|---|" + "---|" * len(RECORDS)]
    stages = sorted({s for c in stage_counts.values() for s in c}, key=lambda s: (S.ORDER.get(s, 99), s))
    for s in stages:
        lines.append(f"| {s} | " + " | ".join(str(stage_counts[r][s]) for r in RECORDS) + " |")
    caveat = {r: Counter((t["traces"][r]["loss_stage"], t["traces"][r]["note"]) for x in days if x["score"]
                         for t in x["score"]["lineups"] if r in t["traces"] and t["traces"][r].get("note")
                         and t["traces"][r]["loss_stage"] in ("CLUSTER_FORMATION", "NOT_REACHED")) for r in RECORDS}
    lines.append("")
    for r in RECORDS:
        for (stage, note), k in sorted(caveat[r].items()):
            lines.append(f"- {r}: {k} of its {stage} count: \"{note}\".")
    lines += ["", "Line-ups whose statements no single cluster held from two of their channels (decided CLUSTER_FORMATION "
              "in a complete record, or NOT_REACHED where an incomplete record stopped): how far the furthest "
              "one-channel cluster holding some of them got (its own stage):", "",
              "| furthest one-channel cluster | " + " | ".join(RECORDS) + " |", "|---|" + "---|" * len(RECORDS)]
    for s_ in sorted({s for c in near_counts.values() for s in c}, key=lambda s: (S.ORDER.get(s, 99), s)):
        lines.append(f"| {s_} | " + " | ".join(str(near_counts[r][s_]) for r in RECORDS) + " |")
    # ── every accepted line-up with its trace ──
    lines += ["", "## 4. Every accepted line-up, its sentences and its trace", ""]
    for x in days:
        if not (x["score"] and x["score"]["lineups"]):
            continue
        rows = _rows(x["dir"])
        lus = (x["oracle"] or {}).get("lineups") or []
        for t in x["score"]["lineups"]:
            lu = lus[t["lineup"] - 1]
            j = next(r["judge"] for r in x["day"]["lineups"] if r["lineup"] == t["lineup"])
            lines += [f"### {x['stamp']} L{t['lineup']}: {lu['development']}",
                      f"Channels {', '.join(t['summary']['channels'])}; content {t['summary']['content_s']} s "
                      f"(runtime ~{t['summary']['runtime_s']} s); blind judge: {VERDICT_WORDS.get(j['verdict'], j['verdict'])} "
                      f"({j['reason'][:220]})",
                      lineup_text(lu, rows), f"- layout: {t['layout_note']}"]
            for name, tr in t["traces"].items():
                b = tr.get("best_carrier") or {}
                held = "; ".join(f"{ch}: {', '.join(ids[:3])}" for ch, ids in (b.get("channels_held") or {}).items())
                lines.append(f"- {name}: **{tr['loss_stage']}**" + (f" [{tr['note']}]" if tr.get("note") else "") + (
                    f" via {b.get('path')} '{str(b.get('candidate') or b.get('claim') or '')[:90]}' holding [{held}]: "
                    f"{str(b.get('detail') or '')[:200]}" if b else
                    f" (no cluster or headline held its statements from >= 2 of its channels; {tr['n_near']} held one channel's)"))
                for n in (tr.get("near_carriers") or [])[:3]:
                    nh = "; ".join(f"{ch}: {', '.join(ids[:3])}" for ch, ids in (n.get("channels_held") or {}).items())
                    lines.append(f"  - one-channel {n.get('path')} {n.get('cluster', '')} "
                                 f"'{str(n.get('claim') or n.get('candidate') or '')[:80]}' (cluster channels "
                                 f"{', '.join((n.get('cluster_channels') or [])[:5]) or '-'}) holding [{nh}]: "
                                 f"{n.get('stage')} {str(n.get('detail') or '')[:120]}")
            lines.append("")
    if analysis_path and os.path.exists(analysis_path):
        lines += ["## 5. Analysis (hand-written, from the tables above)", "", analysis_text(analysis_path), ""]
    lines += ["## 6. Method and artefacts", "",
              f"- Export: tools/backtest_oracle.py export; rows = every sentence that names Bitcoin "
              f"(editorial_select.BITCOIN_TERMS) and its {X.NEIGHBOURHOOD} neighbours either side in the same video; text "
              "read as spoken (transcript_store.read_text), canon = canon.canon. Three independent exports (2026-11-12 "
              "01:03-01:08 ET, session log) were byte-identical; tests/oracle/test_oracle_export.py proves the property "
              "on fixtures "
              "(sha256 per run below).",
              "- Writer (oracle) and judge: the back-ends named per run in section 7 (pipeline/oracle/providers.py "
              "holds every back-end, its settings and price); JSON-schema output, parsed strictly. The writer is shown "
              "only the run's statements (rows longer than the 20 s clip budget hidden) and the written rules; up to one "
              "retry (schema error, or every line-up failing the deterministic checks). The judge is shown one line-up "
              "and the same rules, never who built it, and is never the writer's vendor.",
              "- Available = oracle proposed it AND the deterministic checks pass (ids, consecutive sentences, "
              "durations, >= 2 channels, per-video / per-channel limits, >= 46.5 s, altcoin word screen) AND the "
              "blind judge says it passes our rules. (In the raw artefacts the judge's verdict field reads LEGAL for "
              "passes our rules and ILLEGAL for fails them; the field name is kept so stored prompts stay byte-identical.)",
              ""]
    lines += ["| run | rows sha256 | rows | Bitcoin rows | videos exported / universe |", "|---|---|---|---|---|"]
    for x in days:
        m = x["man"]
        if m:
            lines.append(f"| {x['stamp']} | `{m['rows_sha256']}` | {m['rows']} | {m['bitcoin_rows']} | "
                         f"{m['exported_videos']} / {m['universe_videos']} |")
    from pipeline.oracle import llm
    usd = round(sum(r.get("usd") or 0.0 for r in spend), 2)
    by_usd, by_n = Counter(), Counter()
    for r in spend:
        k = r.get("backend") or r.get("model")
        by_usd[k] += r.get("usd") or 0.0
        by_n[k] += 1
    gw = round(sum(r.get("usd") or 0.0 for r in spend if r.get("usd_source") == "gateway-reported"), 4)
    from pipeline.oracle import providers as PV
    unpriced = sum(1 for r in spend if r.get("usd_source") == "unpriced" or (
        not r.get("usd_source") and r.get("backend") in PV.BACKENDS and not PV.BACKENDS[r["backend"]].get("price")
        and not PV.BACKENDS[r["backend"]].get("gpu0")))
    lines += ["", f"API spend (ledger {sp}): {usd} USD over {len(spend)} calls; per back-end: "
                  + "; ".join(f"{k} {round(v, 2)} USD / {by_n[k]} calls" for k, v in by_usd.most_common())
                  + ". The local back-end's calls are the integrator's runs under the GPU0 lease (REQUESTS R5); this "
                  "session never called it"
                  + f". Of the total, {gw} USD is the per-call cost a gateway reported; {unpriced} gateway calls made "
                  f"before per-call pricing was recorded carry no price. Guard: {llm.SPEND_CAP_USD:.0f} USD (the ledger "
                  "refuses any call whose worst case would pass it).", ""]
    lines += variant_section(day_dirs)
    lines[incomplete_at:incomplete_at] = incomplete_section(days, day_dirs, recall, stage_counts)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(path + ".tmp", path)
    return path


VERDICT_WORDS = {"LEGAL": "passes our rules", "ILLEGAL": "fails our rules"}


def plain(text):
    """An availability / verdict string as PBX reads it (note 02:31: never 'legal'); artefacts written before the
    wording change keep their raw text, so it is translated here."""
    t = str(text)
    return (t.replace("the judge called every checked line-up ILLEGAL",
                      "the blind judge said every checked line-up fails our rules")
            .replace("ILLEGAL", "fails our rules").replace("LEGAL", "passes our rules"))
VARIANT_DIRS = (("same_dev_hard", ""), ("same_dev_hard_max", "same_dev_hard_max"), ("same_dev", "same_dev"),
                ("moments", "moments"))


def variant_numbers(vdir):
    """{accepted, distinct, developments, accepted_hard, distinct_hard, availability, models} of one variant day dir,
    computed from ORACLE.json + DAY.json (so every variant is counted the same way), or None."""
    day, o = load(vdir, "DAY.json"), load(vdir, "ORACLE.json")
    if not day or not o:
        return None
    lus = o.get("lineups") or []
    acc = [lus[r["lineup"] - 1] for r in day["lineups"] if r["accepted"]]
    hard = [lu for lu in acc if not (lu.get("summary") or {}).get("window_misses")]
    le70 = [lu for lu in acc if (lu.get("summary") or {}).get("runtime_s", 999) <= 70.0]
    return {"availability": day["availability"].split(" ")[0], "accepted": len(acc),
            "accepted_le70": len(le70), "distinct_le70": len(L.disjoint_max(le70)),
            "distinct": len(L.disjoint_max(acc)),
            "developments": day.get("distinct_developments") if R.fresh(vdir, "GROUPS.json") else None,
            "accepted_hard": len(hard), "distinct_hard": len(L.disjoint_max(hard)),
            "oracle_model": day.get("oracle_model") or _models(vdir, "ORACLE.json"),
            "judge_model": day.get("judge_model") or _models(vdir, "JUDGE_L*.json")}


def _models(vdir, pattern):
    """The model names recorded in a day's artefacts' usage rows (legacy DAY.json files carry none)."""
    import glob as _g
    seen = set()
    for p in _g.glob(os.path.join(vdir, pattern)):
        with open(p, encoding="utf-8") as f:
            seen |= {(a.get("usage") or {}).get("model") for a in json.load(f).get("attempts", [])}
    return ", ".join(sorted(m for m in seen if m)) or "unknown"


def variant_section(day_dirs):
    out = ["", "## 7. Supply per universe under the 01:55 note: distinct line-ups, PBX's 01:48 moments rule, law L-o",
           "", "Three rule sets on the same exports (each column says which models produced it):"]
    for name, _ in VARIANT_DIRS:
        out.append(f"- **{name}**: {L.VARIANTS[name]['label']}.")
    out += ["", "Per cell: accepted line-ups / sentence-disjoint line-ups / distinct developments (the accepted line-ups "
            "grouped blind by development; '-' = no grouping: moments line-ups need not share one); then, in "
            "brackets, the same with the 8-12 s / 12-20 s windows applied as HARD limits after the fact (a target-mode "
            "line-up outside them does not count; a lower bound, since that oracle was told the windows are targets).",
            "", "| run | " + " | ".join(n for n, _ in VARIANT_DIRS) + " |", "|---|" + "---|" * len(VARIANT_DIRS)]
    tot = {n: {"avail": 0, "measured": 0, "accepted": 0, "distinct": 0, "dev": 0, "dev_n": 0, "avail_hard": 0,
               "distinct_hard": 0, "models": set(), "le70": 0, "dle70": 0, "avail_le70": 0} for n, _ in VARIANT_DIRS}
    for d in day_dirs:
        cells = []
        for name, sub in VARIANT_DIRS:
            x = variant_numbers(os.path.join(d, sub) if sub else d)
            if not x:
                cells.append("not run")
                continue
            t = tot[name]
            t["models"].add(f"oracle {x['oracle_model']}, judge {x['judge_model']}")
            if x["availability"] in ("AVAILABLE", "NONE", "NOT_AVAILABLE"):
                t["measured"] += 1
                t["avail"] += int(x["availability"] == "AVAILABLE")
                t["avail_hard"] += int(x["accepted_hard"] > 0)
            t["accepted"] += x["accepted"]
            t["distinct"] += x["distinct"]
            t["le70"] += x["accepted_le70"]
            t["dle70"] += x["distinct_le70"]
            t["avail_le70"] += int(x["accepted_le70"] > 0)
            t["distinct_hard"] += x["distinct_hard"]
            if x["developments"] is not None:
                t["dev"] += x["developments"]
                t["dev_n"] += 1
            dev = "-" if name == "moments" else ("not measured" if x["developments"] is None else x["developments"])
            cells.append(f"{x['accepted']} / {x['distinct']} / {dev} ({x['accepted_hard']} / {x['distinct_hard']})"
                         + ("" if x["availability"] == "AVAILABLE" else f" {plain(x['availability'])}"))
        out.append(f"| {os.path.basename(d)} | " + " | ".join(cells) + " |")
    out += ["", "| rule set | models | runs with an accepted line-up (windows targets / hard / runtime <= 70 s) | "
                "accepted line-ups (all / runtime <= 70 s) | sentence-disjoint line-ups (targets / hard / <= 70 s) | "
                "distinct developments |", "|---|---|---|---|---|---|"]
    for name, _ in VARIANT_DIRS:
        t = tot[name]
        out.append(f"| {name} | {'; '.join(sorted(t['models'])) or '-'} | {t['avail']} of {t['measured']} / "
                   f"{t['avail_hard']} of {t['measured']} / {t['avail_le70']} of {t['measured']} | {t['accepted']} / "
                   f"{t['le70']} | {t['distinct']} / {t['distinct_hard']} / {t['dle70']} | "
                   + ("-" if name == "moments" else f"{t['dev']} over {t['dev_n']} grouped runs") + " |")
    hidden = [load(d, "DAY.json").get("rows_hidden_longer_than_clip_budget") for d in day_dirs if load(d, "DAY.json")]
    out += ["", "Runtime = hook + clips + ~13.5 s of credits card and outro (an estimate); the floor of 60 s is enforced "
                "for every rule set, the 70 s ceiling only counted here (the approved preview ran 71.08 s).",
            "", f"Every rule set hid from the writer the sentences longer than the 20 s clip ceiling ({min(hidden)}-"
                f"{max(hidden)} per universe, {sum(hidden)} in all; mostly unpunctuated caption stretches, bible B6). "
                "Under the rule sets that treat the windows as targets (same_dev, moments) such a sentence could have "
                "been a clip, so those columns are lower bounds for this reason as well." if hidden else ""]
    out += witness_section(day_dirs)
    out += ab_section(os.path.join(os.path.dirname(day_dirs[0]), "ab") if day_dirs else "", day_dirs)
    return out


def _local_writer_fit(day_dirs, name):
    """(universes whose stored writer prompt fits the back-end's context, universes with a stored prompt)."""
    from pipeline.oracle import ab as AB, providers as PV
    fit = n = 0
    for d in day_dirs:
        p = os.path.join(d, "oracle_prompt.txt")
        if os.path.exists(p):
            n += 1
            fit += int(PV.fits(name, *AB._split(p))[0])
    return fit, n


def incomplete_section(days, day_dirs, recall, stage_counts):
    """'Read this first': every row of this report that is incomplete or not measured, with its count, from the
    recorded artefacts (orchestrator order 05:30 ET: nothing is re-run after the spend freeze)."""
    from pipeline.oracle import ab as AB, providers as PV
    out = ["## 0. Incomplete rows (read this first)", "",
           "Spend freeze 2026-11-12 05:30 ET: no paid model call was made after it and nothing below was re-run. Every "
           "row listed here is incomplete or not measured; it is never counted as a pass, a miss or a result.", ""]
    for name in RECORDS:
        k, n, m = recall[name]
        if m:
            out.append(f"- Selector recall, {name}: {m} of {n + m} runs with a line-up not measured (the record "
                       "crashed, was stopped or hit NOT_RERUN before selecting).")
    out.append("- Selector precision: not measured on any record (no record accepted a line-up).")
    nr = {r: stage_counts[r]["NOT_REACHED"] for r in RECORDS if stage_counts[r]["NOT_REACHED"]}
    if nr:
        out.append("- Loss stage NOT_REACHED (the record stopped before deciding the line-up): "
                   + "; ".join(f"{r} {k} of {sum(stage_counts[r].values())}" for r, k in nr.items()) + ".")
    hidden = [load(d, "DAY.json").get("rows_hidden_longer_than_clip_budget") for d in day_dirs if load(d, "DAY.json")]
    if hidden:
        out.append(f"- Windows-as-targets rule sets (same_dev, moments): lower bounds; {sum(hidden)} sentences longer "
                   "than the 20 s clip ceiling were never shown to the writer.")
    for sub in ("", "same_dev_hard_max", "same_dev"):
        missing = [os.path.basename(d) for d in day_dirs if (load(os.path.join(d, sub) if sub else d, "DAY.json") or {})
                   .get("accepted", 0) and (load(os.path.join(d, sub) if sub else d, "DAY.json") or {})
                   .get("distinct_developments") is None]
        if missing:
            out.append(f"- Distinct developments ({sub or 'same_dev_hard'}): not measured on {', '.join(missing)}.")
    ab_dir = os.path.join(os.path.dirname(day_dirs[0]), "ab") if day_dirs else ""
    for role in ("judge", "witness", "grouping"):
        files = sorted(glob.glob(os.path.join(ab_dir, "**", f"AB_{role}.json"), recursive=True), key=os.path.getmtime)
        planned, swaps = _planned(ab_dir, day_dirs, role) if day_dirs else (0, 0)
        merged = AB.merge(files) if files else {}
        for name in PV.ROLES[role]:
            if name == PV.ROLES[role][1]:
                continue                                  # the reference: its recorded verdicts ARE the yardstick
            r = merged.get(name)
            plan = swaps if (role == "judge" and name == PV.ROLES["judge"][1]) else planned
            if r is None or "skipped" in r:
                out.append(f"- A/B {role}, {name}: not run ({(r or {}).get('skipped') or 'no batch'}).")
                continue
            gaps = []
            if r["items"] < plan:
                gaps.append(f"{plan - r['items']} of {plan} planned items not run"
                            + (" (batch not finished at report time: still running or stopped early)"
                               if r.get("partial") else ""))
            if r["failed"]:
                gaps.append(f"{r['failed']} without a usable reply")
            if r["not_sent"]:
                gaps.append(f"{r['not_sent']} stopped by the spend guard")
            if r.get("failed_resamples"):
                gaps.append(f"{r['failed_resamples']} failed call(s) on items another sample measured")
            if gaps:
                out.append(f"- A/B {role}, {name}: " + "; ".join(gaps) + ".")
    wfile = os.path.join(ab_dir, "AB_writer.json")
    wd = json.load(open(wfile, encoding="utf-8")) if os.path.exists(wfile) else {"results": {}, "runs": []}
    out += [f"- A/B writer: {len(wd.get('runs') or [])} universe(s) only ({', '.join(wd.get('runs') or []) or 'none'}), "
            f"back-ends beside the reference: {', '.join(wd['results']) or 'none'}; the local writer cannot take a "
            "universe (context guard); the other writer back-ends of the chain were not run.",
            "- VO fidelity (law L-w 6): not measured (the backtest writes no voiceover).",
            "- Audit legs that never ran or failed, per round: docs/audits/parallel/pp-backtest_AUDIT.md (round 4, "
            "after the spend freeze, ran on Heimdall only and most of its legs are NOT MEASURED).", ""]
    return out


def analysis_text(path):
    """The hand-written analysis; a report is never written around an unfilled template placeholder (@NAME@)."""
    import re
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    left = sorted(set(re.findall(r"@[A-Z][A-Z0-9_]*@", text)))
    if left:
        raise ValueError(f"{path}: unfilled placeholders {left}: fill them (or write NOT MEASURED) first")
    return text


def _planned(ab_dir, day_dirs, role):
    """Items the A/B plans for a role on these days (a reference back-end is planned only for the swaps)."""
    from pipeline.oracle import ab as AB
    root, stamps = os.path.dirname(ab_dir), [os.path.basename(os.path.normpath(d)) for d in day_dirs]
    items = AB.judge_items(root, stamps) if role == "judge" else AB.recorded_items(root, stamps, role)
    return len(items), sum(1 for x in items if AB.is_swap(x[0]))


def ab_section(ab_dir, day_dirs=()):
    """Section 9: the blind A/B of every model role (law L-x) from ab/**/AB_<role>.json."""
    from pipeline.oracle import ab as AB, providers as PV
    out = ["", "## 9. Model roles: one provider interface, blind A/B on saved data (law L-x, note 02:45)", "",
           "Every model call of this instrument goes through pipeline/oracle/providers.py (the only place a vendor or "
           "a model name appears). Role chains, first available back-end answers, a vendor-side failure moves to the "
           "next, the judge-like roles never use the writer's vendor:", ""]
    out += [f"- **{r}**: {' -> '.join(c)} (default decided by: {PV.DECIDED_BY[r]})" for r, c in PV.ROLES.items()]
    local = ", ".join(f"{n} ({b['model']})" for n, b in PV.BACKENDS.items() if b.get("gpu0"))
    out += ["", "Judge / witness / grouping: the exact stored prompts replayed on each back-end and compared with the "
            "recorded reference verdicts (judge: plus must-fail swaps whose only right verdict is 'fails our rules'). "
            "Writer: the "
            f"saved day re-run per back-end with the judge fixed. The local back-end, {local}, runs only inside the "
            "integrator's GPU0 lease (this session never calls it): its rows below are the integrator's runs (REQUESTS "
            "R5; they are that back-end's calls in the spend ledger); a role it has not run yet reads PENDING. "
            "'items run / planned' shows what was never run. Dollars per call: "
            "frontier from the provider config's price table, a gateway's as it reports each call, local 0.", "",
            "Items the spend guard stopped before they were sent are NOT MEASURED (own column), never failures and never "
            "agreement; a batch re-run for them is merged per item (every paid call is counted in the dollars). A "
            "failed call on an item that another sample measured is shown beside the failed count, never dropped. The "
            "reference judge's own row holds only its result on the development swaps (its recorded verdicts are the "
            "reference and are not re-asked).", "",
            "| role | back-end | items run / planned | measured / not sent (spend guard) / failed (no usable reply) | agreement with "
            "the reference (of measured) | passes what the reference fails | fails what the reference passes | must-fail "
            "caught (of measured) | median s per call | USD |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for role in ("writer", "judge", "witness", "grouping"):
        files = sorted(glob.glob(os.path.join(ab_dir, "**", f"AB_{role}.json"), recursive=True), key=os.path.getmtime)
        seen = set()
        if role != "writer":
            planned, swaps = _planned(ab_dir, day_dirs, role) if day_dirs else (None, 0)
            for name, r in AB.merge(files).items():
                seen.add(name)
                if "skipped" in r:
                    out.append(f"| {role} | {name} | - | - | skipped: {r['skipped'][:80]} | - | - | - | - | - |")
                    continue
                mf = (f"{r['must_fail_caught']} of {r['must_fail_measured']}"
                      + (f" ({r['withdrawn']} rows of the 9 withdrawn first swaps not counted)" if r.get("withdrawn")
                         else "")
                      if role == "judge" else "-")
                lax = r["more_lenient"] if role != "grouping" else "-"
                tight = r["stricter"] if role != "grouping" else "-"
                part = " (batch still running or stopped early: counts are of the items it finished)" if r.get(
                    "partial") else ""
                plan = swaps if (role == "judge" and name == PV.ROLES["judge"][1]) else planned   # the reference
                resampled = (f" (+{r['failed_resamples']} failed call(s) on items another sample measured)"
                             if r.get("failed_resamples") else "")
                out.append(f"| {role} | {name}{part} | {r['items']} / {plan} | {r['measured']} / {r['not_sent']} / "
                           f"{r['failed']}{resampled} | "
                           f"{r['agree']} of {r['measured']} | {lax} | {tight} | {mf} | {r['median_s']} | "
                           f"{r['usd']} ({', '.join(r['usd_source'])}) |")
        for path in files if role == "writer" else ():
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            for name, r in d["results"].items():
                seen.add(name)
                if "skipped" in r:
                    out.append(f"| {role} | {name} | - | - | skipped: {r['skipped'][:80]} | - | - | - | - | - |")
                else:
                    for st, x in r.items():
                        secs = [t for t in x.get("writer_s") or [] if t is not None]
                        na, nf = x.get("writer_attempts") or 0, x.get("writer_failed_attempts") or 0
                        out.append(f"| writer | {name} ({st}) | {na} call(s) | {na - nf} / 0 / {nf} | "
                                   f"{plain(x.get('availability'))} "
                                   f"({x.get('oracle_status')}): {x.get('lineups')} line-ups, check-fail "
                                   f"{x.get('checkfail')}, judge says fails our rules {x.get('judge_illegal')}, accepted "
                                   f"{x.get('accepted')}, disjoint {x.get('distinct_accepted')} (judge "
                                   f"{x.get('judge_model')}) | - | - | - | {statistics.median(secs) if secs else '-'} | "
                                   f"{x.get('writer_usd')} ({', '.join(x.get('writer_usd_source') or [])}) |")
        for name in PV.ROLES[role]:
            if PV.BACKENDS[name].get("gpu0") and name not in seen:
                fit, n = _local_writer_fit(day_dirs, name) if role == "writer" else (None, 0)
                if role == "writer" and n and not fit:
                    out.append(f"| writer | {name} | {n} universes | - | not run: the stored writer prompt fits its "
                               f"context on 0 of {n} universes (context guard; a cut prompt is never sent) | - | - | "
                               "- | - | - |")
                else:
                    out.append(f"| {role} | {name} | - | - | PENDING: integrator, GPU0 lease"
                               + (f" ({fit} of {n} universes fit its context)" if n else "") + " | - | - | - | - | - |")
    return out


WITNESS_REQUIRE = (("base (blind judge: passes our rules)", ()), ("+ one excerpt per channel", ("one_excerpt_per_channel",)),
                   ("+ own sincere assertion in original context", ("sincere_in_context",)),
                   ("+ no implied relation across videos", ("no_implied_relation",)),
                   ("+ no named accusation / buy-sell imperative / ad read", ("no_accusation_imperative_ad",)),
                   ("all four witness checks", ("one_excerpt_per_channel", "sincere_in_context", "no_implied_relation",
                                                "no_accusation_imperative_ad")))


def witness_section(day_dirs):
    """Moments line-ups with and without the reviewers' witness checks (02:30 note), per check and all together."""
    from pipeline.oracle import witness as W
    rows, tot, failed, n = [], {lab: [0, 0, 0] for lab, _ in WITNESS_REQUIRE}, 0, 0
    wm = set()
    for d in day_dirs:
        w = load(os.path.join(d, "moments"), "WITNESS.json") or {}
        wm |= set(w.get("witness_models") or []) | {(a.get("usage") or {}).get("model") for x in w.get("lineups", [])
                                                     for a in x.get("attempts", []) if a.get("usage")}
    wmodels = ", ".join(sorted(m for m in wm if m))
    for d in day_dirs:
        vdir = os.path.join(d, "moments")
        w = load(vdir, "WITNESS.json")
        if not w:
            rows.append(f"| {os.path.basename(d)} | " + " | ".join("not run" for _ in WITNESS_REQUIRE) + " |")
            continue
        if not R.fresh(vdir, "WITNESS.json"):           # computed from an earlier ORACLE.json: never a result
            rows.append(f"| {os.path.basename(d)} | " + " | ".join("stale: not counted" for _ in WITNESS_REQUIRE) + " |")
            continue
        n += 1
        failed += sum(1 for x in w["lineups"] if x["status"] != "OK")
        cells = []
        for lab, req in WITNESS_REQUIRE:
            surv = W.survivors(vdir, req)
            dis = len(L.disjoint_max(surv))
            tot[lab][0] += int(bool(surv))
            tot[lab][1] += len(surv)
            tot[lab][2] += dis
            cells.append(f"{len(surv)} / {dis}")
        rows.append(f"| {os.path.basename(d)} | " + " | ".join(cells) + " |")
    out = ["", "## 8. Moments-first with the reviewers' witness checks (orchestrator note 02:30)", "",
           f"Each accepted moments line-up was re-read by {wmodels or 'the witness back-end'} (never the writer's "
           "vendor) with every clip inside its ORIGINAL context (the same transcript, 90 s before to 60 s after); one "
           "excerpt per channel is checked in code. Any 'uncertain' is a fail; a witness reply that is not whole and "
           f"consistent fails the checks (WITNESS_FAILED line-ups: {failed}). Cells: line-ups passing / of those, "
           "sentence-disjoint.", "",
           "| run | " + " | ".join(lab for lab, _ in WITNESS_REQUIRE) + " |", "|---|" + "---|" * len(WITNESS_REQUIRE)]
    out += rows
    out += ["", "| checks required | runs with a line-up left | line-ups left | sentence-disjoint line-ups left |",
            "|---|---|---|---|"]
    out += [f"| {lab} | {tot[lab][0]} of {n} | {tot[lab][1]} | {tot[lab][2]} |" for lab, _ in WITNESS_REQUIRE]
    return out
