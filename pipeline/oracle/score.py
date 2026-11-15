#!/usr/bin/env python3
"""pipeline/oracle/score.py — the selector's recorded decision path against the judged line-ups.

Selector records of a day (each scored on its own; never mixed inside one trace):
  as_run          runs/<run>/TOPIC_SELECTION.json: what the selector decided that day, at that run's git HEAD
  cold_backtest   runs/backtest_cold1/<run>/TOPIC_SELECTION.json: the 2026-11-11 cold backtest at 394ffe5a (real
                  gemma), where it exists
  replay_head     <oracle dir>/<stamp>/replay_head/: this code, CPU only (pipeline/oracle/replay.py); stops with
                  NOT_RERUN at the first step that needs gemma without a cached reply
A trace follows the accepted line-up's OWN sentences (same video, overlapping time) through a record:
  carrier         a cluster whose member chunks, or a candidate whose adjudicated excerpts, hold statements of the
                  line-up from >= 2 of its channels (a selector object that could produce this line-up)
  stage           where each carrier stopped, in pipeline order; the line-up's loss stage in that record is the
                  stage of the carrier that got furthest; no carrier at all in a COMPLETE record = CLUSTER_FORMATION
                  (no cluster and no headline held them); in an incomplete record = NOT_REACHED (later pools and
                  headlines never ran)
Recall (per record): of the days with an accepted line-up whose record COMPLETED a selection, the days on which that
record SELECTED a line-up sharing a sentence with an accepted one in >= 2 channels' segments (same development by
shared statements); a crashed / stopped / NOT_RERUN record is not measured. Precision (per record): of that record's
selected line-ups, those the blind judge passes. Nothing measured is reported as not measured (law L-m), never as
0 % or 100 %.
"""
import json
import os

from pipeline.oracle import lineup as L
from pipeline.oracle import run as R
import transcript_store as ts  # noqa: E402

COLD_BACKTEST = "/home/ultron/protocol_pulse/runs/backtest_cold1"
STAGES = ("CLUSTER_FORMATION", "BITCOIN_SCREEN", "LABEL", "IMPORTANCE", "DEDUPE", "CURRENTNESS", "COVERAGE",
          "LAYOUT_ELIGIBILITY", "WINDOWS", "HOOK_SCORE", "STAND_ALONE", "ASSEMBLY", "INFRA", "LEDGER",
          "PRODUCIBLE", "SELECTED", "SENTENCE_LOCK")
ORDER = {s: i for i, s in enumerate(STAGES)}
TIERS = ("48h", "72h")
CLIP_STAGES = ("WINDOWS", "HOOK_SCORE", "STAND_ALONE", "ASSEMBLY", "INFRA")


def classify(c):
    """(stage, detail) of one candidate from its recorded decision; NOT_REACHED when the run stopped before it."""
    d = str(c.get("decision") or "")
    gate = "; ".join(c.get("importance_gate") or [])
    if c.get("merged_into"):
        return "DEDUPE", f"merged into '{c['merged_into'][:80]}' (DEDUPE_SIM)"
    rules = (("merged into the same-event candidate", "DEDUPE"), ("inconclusive: story-query derivation", "IMPORTANCE"),
             ("inconclusive: currentness", "CURRENTNESS"), ("rejected: coverage", "COVERAGE"),
             ("rejected: only", "LAYOUT_ELIGIBILITY"), ("rejected: no quote-anchored", "WINDOWS"),
             ("rejected: no hook passage", "HOOK_SCORE"), ("rejected: every hook", "STAND_ALONE"),
             ("rejected: clip quality", "ASSEMBLY"), ("rejected: word-level", "INFRA"), ("INFRA_HOLD", "INFRA"),
             ("already delivered", "LEDGER"), ("producible", "PRODUCIBLE"))
    for prefix, stage in rules:
        if d.startswith(prefix):
            return stage, d
    if d.startswith("not evaluated"):
        return "NOT_EVALUATED", d
    if gate:
        return "IMPORTANCE", gate
    if d == "coverage_qualified":
        return "NOT_REACHED", "coverage_qualified; the run stopped before clip quality"
    return "NOT_REACHED", d or "no decision recorded (the run stopped or crashed before this candidate)"


def sentences_of(lu, rows_by_id):
    return [{"segment": label, "id": i, "video_id": rows_by_id[i]["video_id"], "channel_id": rows_by_id[i]["channel_id"],
             "channel": rows_by_id[i]["channel"], "start": rows_by_id[i]["start_s"], "end": rows_by_id[i]["end_s"],
             "layout_eligible": rows_by_id[i]["layout_eligible"],
             "layout_eligible_run": rows_by_id[i].get("layout_eligible_run")}
            for label, ids in L.segments(lu) for i in ids]


def _spans(chunk_ids):
    out = {}
    for cid in chunk_ids or []:
        try:
            v, s, e = ts.parse_chunk_id(cid)
        except (ValueError, TypeError):
            continue
        out.setdefault(v, []).append((s, e))
    return out


def held(sents, chunk_ids):
    """{channel: [sentence ids]} of the line-up's sentences that lie in (overlap) any of these chunks."""
    sp, out = _spans(chunk_ids), {}
    for s in sents:
        if any(a < s["end"] and s["start"] < b for a, b in sp.get(s["video_id"], [])):
            out.setdefault(s["channel"], []).append(s["id"])
    return out


def _windows_held(c, sents):
    """The selector's clip-quality windows that overlap the line-up's sentences (with their scores)."""
    out = []
    for w in ((c.get("clip_quality") or {}).get("candidates") or []):
        ids = [s["id"] for s in sents if s["video_id"] == w.get("video_id") and w["start"] < s["end"] and s["start"] < w["end"]]
        if ids:
            out.append({"kind": w.get("kind"), "channel": w.get("channel"), "ids": ids, "score": w.get("clip_score"),
                        "fault": w.get("clip_fault"), "stand_alone": (w.get("stand_alone") or {}).get("why")})
    return out


def survival(c, sents):
    """How much of the line-up is still alive inside candidate c: its channels whose video was COUNTED as the same
    event, of those the layout-eligible ones, the channels with clip-quality windows in its videos, the windows on its
    own sentences and the anchor results for its videos."""
    verdicts = (c.get("coverage") or {}).get("verdicts") or []
    counted = {v["video_id"] for v in verdicts if v.get("counted_as_same_event")}
    # layout as THIS record decided it (each coverage verdict carries the run's own flag; the run's universe flag
    # if a verdict lacks it), never today's registry (audit F2)
    lay_rec = {v["video_id"]: v["layout_eligible"] for v in verdicts if "layout_eligible" in v}
    vids = {s["video_id"] for s in sents}
    cq = c.get("clip_quality") or {}
    return {"counted": sorted({s["channel"] for s in sents if s["video_id"] in counted}),
            "layout": sorted({s["channel"] for s in sents if s["video_id"] in counted
                              and lay_rec.get(s["video_id"], s.get("layout_eligible_run"))}),
            "windowed": sorted({w.get("channel") for w in cq.get("candidates") or [] if w.get("video_id") in vids}),
            "windows_on_lineup": _windows_held(c, sents),
            "verdicts": [{"channel": v.get("channel"), "video_id": v.get("video_id"), "verdict": v.get("verdict"),
                          "counted": v.get("counted_as_same_event"), "support": v.get("support"),
                          "quote_verified": v.get("quote_verified")} for v in verdicts if v.get("video_id") in vids],
            "anchors": [{k: a.get(k) for k in ("channel", "video_id", "result", "windows") if a.get(k) is not None}
                        for a in cq.get("anchors") or [] if a.get("video_id") in vids],
            "offline_no_words": sorted({s["channel"] for s in sents for f in cq.get("other_failures") or []
                                        if f and f[0] == s["video_id"] and str(f[1]).startswith("backtest:")})}


def lineup_stage(c, sents):
    """(stage, detail, survival) of the LINE-UP inside one candidate: a stage the candidate itself failed, or the
    point where fewer than MIN_CHANNELS of the line-up's own channels remained (counted / layout / windowed)."""
    st, detail = classify(c)
    surv = survival(c, sents)
    if st in ("DEDUPE", "IMPORTANCE", "NOT_EVALUATED", "CURRENTNESS", "LEDGER") or not surv["verdicts"]:
        return st, detail, surv
    if len(surv["counted"]) < L.MIN_CHANNELS:
        if (c.get("coverage") or {}).get("status") != "done":
            return "NOT_REACHED", f"coverage unfinished when the run stopped ({detail})", surv
        return "COVERAGE", (f"the line-up's statements counted as the same event for {len(surv['counted'])} of its "
                            f"channels ({', '.join(surv['counted']) or 'none'}); candidate: {detail}"), surv
    if len(surv["layout"]) < L.MIN_CHANNELS:
        if (c.get("coverage") or {}).get("status") != "done":
            return "NOT_REACHED", f"coverage unfinished when the run stopped ({detail})", surv
        return "LAYOUT_ELIGIBILITY", (f"counted line-up channels that are layout-eligible: "
                                      f"{', '.join(surv['layout']) or 'none'}; candidate: {detail}"), surv
    if st in ("COVERAGE", "LAYOUT_ELIGIBILITY", "NOT_REACHED", "PRODUCIBLE", "SELECTED"):
        return st, detail, surv
    if surv["offline_no_words"]:                 # a backtest without word records decided nothing about these videos
        return "NOT_RERUN", (f"no word transcript offline for {', '.join(surv['offline_no_words'])} (a live run would "
                             f"transcribe it); candidate: {detail}"), surv
    if len(surv["windowed"]) < L.MIN_CHANNELS:
        return "WINDOWS", (f"clip-quality windows in the line-up's videos from "
                           f"{', '.join(surv['windowed']) or 'no channel'}; candidate: {detail}"), surv
    return st, detail, surv


def trace(lu, rows_by_id, rec):
    """Every carrier of this line-up in one selector record, the line-up's stage inside it, and the line-up's loss
    stage in this record: the furthest stage any carrier took it (undecided carriers are counted, never ranked)."""
    sents = sentences_of(lu, rows_by_id)
    em, cands = rec.get("emergent_clusters") or [], rec.get("candidates") or []
    carriers, near = [], []
    for idx, e in enumerate(em):
        members = e.get("member_chunk_ids")
        partial = members is None                       # pre-DEC-13 record: only the label's excerpts are known
        h = held(sents, members if members is not None else ((e.get("label") or {}).get("excerpt_chunk_ids") or []))
        if not h:
            continue
        entry = {"path": "cluster", "cluster": idx, "channels_held": h, "cluster_channels": e.get("channels"),
                 "membership": "label excerpts only (pre-DEC-13 record)" if partial else "all members",
                 "claim": e.get("claim") or (e.get("label") or {}).get("headline")}
        screen = e.get("screen")
        c = None
        if len(h) < L.MIN_CHANNELS:                     # holds one of its channels: the cluster's own fate
            near.append(_near_stage(entry, e, idx, cands, partial))
            continue
        if screen is not None and screen not in TIERS:
            entry.update(stage="BITCOIN_SCREEN", detail=screen)
        else:
            c = next((c for c in cands if c.get("cluster_index") == idx), None) if not partial else next(
                (c for c in cands if c.get("origin") == "transcript_cluster"
                 and c.get("headline") == (e.get("label") or {}).get("headline")), None)
            if c is None:
                why = e.get("gate") or e.get("rejected") or "no candidate recorded"
                entry.update(stage="LABEL" if (str(why).startswith("label") or e.get("rejected")) else "NOT_REACHED",
                             detail=why)
            else:
                entry["candidate"] = c.get("headline")
                entry["stage"], entry["detail"], entry["survival"] = lineup_stage(c, sents)
        carriers.append(entry)
    traced = {c.get("candidate") for c in carriers + near}
    for c in cands:                      # headlines, merges, and cluster candidates whose coverage reached further
        if not c.get("coverage") or c.get("headline") in traced:
            continue
        h = held(sents, [x["chunk_id"] for v in c["coverage"].get("verdicts", []) for x in (v.get("excerpts") or [])])
        if not h:
            continue
        entry = {"path": f"{c.get('origin')} coverage", "candidate": c.get("headline"), "channels_held": h}
        if len(h) < L.MIN_CHANNELS:
            entry["stage"], entry["detail"] = classify(c)
            near.append(entry)
            continue
        entry["stage"], entry["detail"], entry["survival"] = lineup_stage(c, sents)
        carriers.append(entry)
    selected = (rec.get("selected") or {}).get("headline")
    for c in carriers:                  # the selected candidate carries the line-up only if the line-up survived
        if selected and c.get("candidate") == selected and c["stage"] in ("PRODUCIBLE", "SELECTED"):
            c["stage"] = "SELECTED"
    decided = [c for c in carriers if c["stage"] in ORDER]
    undecided = [c for c in carriers if c["stage"] not in ORDER]
    complete = bool(rec.get("decision")) and not rec.get("crashed")
    dec13 = any("member_chunk_ids" in e for e in em)
    note = None
    if decided and undecided and not complete:          # a carrier the run never decided might have got further
        best = max(decided, key=lambda c: ORDER[c["stage"]])
        stage = "NOT_REACHED"
        note = (f"furthest decided carrier: {best['stage']}; {len(undecided)} carrier(s) still undecided when the run "
                "stopped (audit round 3, F2: not a decided loss)")
    elif decided:
        best = max(decided, key=lambda c: ORDER[c["stage"]])
        stage = best["stage"]
    elif undecided:
        best, stage = undecided[0], undecided[0]["stage"]           # the run never decided this line-up
    elif not em:
        best, stage = None, "NOT_REACHED"                           # crashed / stopped before any cluster formed
        note = "no clusters in this record (the run crashed or stopped before clustering)"
    elif not complete and not dec13:
        best, stage = None, "NOT_REACHED"                           # partial membership AND unevaluated candidates
        note = "pre-DEC-13 record, incomplete: cluster membership not recorded and candidates left undecided"
    elif not complete:                                              # clusters formed, but later pools / headlines
        best, stage = None, "NOT_REACHED"                           # never ran: a carrier could still have come
        note = ("no cluster held its statements from >= 2 of its channels; the run stopped before every pool and "
                "headline was evaluated (audit F8: not a decided loss)")
    else:
        best, stage = None, "CLUSTER_FORMATION"
        note = "cluster membership = the label's excerpts only (pre-DEC-13 record)" if not dec13 else None
    ranked_near = [n for n in near if n.get("stage") in ORDER]
    near_best = max(ranked_near, key=lambda n: ORDER[n["stage"]]) if ranked_near else None
    near.sort(key=lambda n: -ORDER.get(n.get("stage"), -1))
    return {"loss_stage": stage, "note": note, "record_complete": complete, "best_carrier": best,
            "carriers": carriers, "undecided_carriers": len(undecided),
            "near_carriers": near[:12], "n_near": len(near), "near_furthest_stage": near_best and near_best["stage"],
            "near_furthest": near_best}


def _near_stage(entry, e, idx, cands, partial):
    """A cluster that holds statements of only one of the line-up's channels: how far the cluster itself got."""
    screen = e.get("screen")
    if screen is not None and screen not in TIERS:
        return dict(entry, stage="BITCOIN_SCREEN", detail=screen)
    c = next((c for c in cands if c.get("cluster_index") == idx), None) if not partial else next(
        (c for c in cands if c.get("origin") == "transcript_cluster"
         and c.get("headline") == (e.get("label") or {}).get("headline")), None)
    if c is None:
        why = e.get("gate") or e.get("rejected")
        if why and (str(why).startswith("label") or e.get("rejected")):
            return dict(entry, stage="LABEL", detail=why)
        return dict(entry, stage="NOT_REACHED", detail=why or "no candidate recorded")
    st, detail = classify(c)
    offline = [f[0] for f in (c.get("clip_quality") or {}).get("other_failures") or []
               if f and str(f[1]).startswith("backtest:")]
    if st in CLIP_STAGES and offline:            # the backtest had no word record for some of its videos
        st, detail = "NOT_RERUN", f"no word transcript offline for {', '.join(offline)}; candidate: {detail}"
    return dict(entry, candidate=c.get("headline"), stage=st, detail=detail)


def selected_lineup(record_dir):
    """The record's selected line-up (passages.json 'chosen'), or None."""
    p = os.path.join(record_dir, "passages.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f).get("chosen") or None


def equivalent(chosen, lu, rows_by_id):
    """A selected line-up is equivalent to an accepted one when they share a sentence in >= 2 channels' segments."""
    sents = sentences_of(lu, rows_by_id)
    shared = {s["channel"] for p in chosen for s in sents
              if s["video_id"] == p["video_id"] and p["start"] < s["end"] and s["start"] < p["end"]}
    return len(shared) >= L.MIN_CHANNELS, sorted(shared)


def records(run_dir, day_dir):
    run = os.path.basename(os.path.normpath(run_dir))
    out = [("as_run", run_dir)]
    if os.path.exists(os.path.join(COLD_BACKTEST, run, "TOPIC_SELECTION.json")):
        out.append(("cold_backtest_394ffe5a", os.path.join(COLD_BACKTEST, run)))
    if os.path.exists(os.path.join(day_dir, "replay_head", "TOPIC_SELECTION.json")):
        out.append(("replay_head", os.path.join(day_dir, "replay_head")))
    return out


def record_state(name, rdir):
    with open(os.path.join(rdir, "TOPIC_SELECTION.json"), encoding="utf-8") as f:
        rec = json.load(f)
    state = {"name": name, "decision": rec.get("decision"), "progress": (rec.get("progress") or {}).get("phase"),
             "crashed": bool(rec.get("crashed")), "selected": (rec.get("selected") or {}).get("headline")}
    if name == "replay_head" and os.path.exists(os.path.join(rdir, "REPLAY.json")):
        with open(os.path.join(rdir, "REPLAY.json"), encoding="utf-8") as f:
            state["replay"] = json.load(f)
    state["complete"] = bool(rec.get("decision")) and not rec.get("crashed")
    return rec, state


def score_run(run_dir, day_dir):
    """SCORE.json for one day: availability, each record's state, a trace per accepted line-up per record,
    recall / precision inputs and the layout column."""
    from pipeline.oracle import export as X
    stamp = os.path.basename(os.path.normpath(day_dir))
    with open(os.path.join(day_dir, "DAY.json"), encoding="utf-8") as f:
        day = json.load(f)
    rows = X.read_rows(os.path.join(day_dir, f"BITCOIN_STATEMENTS_{stamp}.jsonl"))
    by_id = {r["id"]: r for r in rows}
    with open(os.path.join(day_dir, "ORACLE.json"), encoding="utf-8") as f:
        oracle = json.load(f)
    lineups = oracle.get("lineups") or []
    accepted = [(row["lineup"], lineups[row["lineup"] - 1]) for row in day["lineups"] if row["accepted"]]
    out = {"stamp": stamp, "availability": day["availability"], "accepted": [k for k, _ in accepted],
           "records": [], "lineups": [], "oracle_sha256": R.oracle_sha(day_dir)}
    recs = []
    for name, rdir in records(run_dir, day_dir):
        rec, state = record_state(name, rdir)
        chosen = selected_lineup(rdir)
        state["selected_lineup"] = chosen
        state["recall_hit"] = any(equivalent(chosen, lu, by_id)[0] for _, lu in accepted) if chosen else False
        out["records"].append(state)
        recs.append((name, rec))
    for k, lu in accepted:
        summ = next(r["summary"] for r in day["lineups"] if r["lineup"] == k)
        ok, why = L.layout_survives(summ)
        out["lineups"].append({"lineup": k, "development": lu["development"], "summary": summ,
                               "layout_survives": ok, "layout_note": why,
                               "traces": {name: trace(lu, by_id, rec) for name, rec in recs}})
    stages = {name: [x["traces"][name]["loss_stage"] for x in out["lineups"]] for name, _ in recs}
    out["summary_line"] = f"{day['availability']}; accepted {out['accepted']}; loss stages {stages}"
    tmp = os.path.join(day_dir, "SCORE.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True, ensure_ascii=False, default=str)
    os.replace(tmp, os.path.join(day_dir, "SCORE.json"))
    return out
