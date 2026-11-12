#!/usr/bin/env python3
"""pipeline/backtest.py — editorial selection on every saved universe (orchestrator order 2026-11-11 '21:10').

Every fresh run that saved its universe (runs/fresh_*/TOPIC_SELECTION.json with transcript shas) is a free test
day. Each day goes through editorial selection only (select_story: clusters -> coverage -> clip quality, whose
windows already apply the stand-alone screen and the text-level sentence rules: boundary start, full-stop end,
whole sentences, durations), with:
  - the day's OWN transcript records (by the sha it recorded; frozen inputs, so a code change is what moves a row),
  - existing word records only (store word records, else a run's large-v3 transcript; no download, no GPU swap),
  - the story-engine items the day saw (rebuilt from its saved candidates),
  - 'now' pinned to that run's start,
  - the cached embeddings and the validated LLM reply cache (warm days re-ask nothing).
Not covered (needs media): the acoustic sentence law at the cut, review / validate on the EDL, render, gates.

One table: day, universe, clusters (>= 2 channels), Bitcoin-screened (48 h / 72 h), coverage-qualified,
producible, and the selected lineup (story, channels), or the gate that stopped each of the top 5. From now on this
is the selection regression suite: a change that lowers the number of producible days is a HOLD on the change.

Usage: CUDA_VISIBLE_DEVICES=0 python3 pipeline/backtest.py [--runs NAME ...] [--out DIR]
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
sys.path.insert(0, PIPELINE_DIR)
import transcript_store as ts  # noqa: E402

RUNS_DIR = os.environ.get("PP_RUNS_DIR", os.path.join(REPO, "runs"))   # a worktree backtest reads the main runs
# acceptance-critical day first (Nov 10: the protected preview's day), then the newest
PRIORITY = ("fresh_20261110_093150", "fresh_20261112_013452", "fresh_20261111_213954", "fresh_20261107_080503",
            "fresh_20261106_213852")


def saved_days(runs_dir=RUNS_DIR):
    """Run dirs whose TOPIC_SELECTION.json carries a universe with transcript shas, priority days first."""
    out = []
    for p in sorted(glob.glob(os.path.join(runs_dir, "fresh_*", "TOPIC_SELECTION.json"))):
        try:
            d = json.load(open(p))
        except (OSError, ValueError):
            continue
        uni = d.get("universe") or []
        if d.get("started") and any(u.get("transcript_sha256") for u in uni):
            out.append(os.path.dirname(p))
    rank = {n: i for i, n in enumerate(PRIORITY)}
    return sorted(out, key=lambda r: (rank.get(os.path.basename(r), len(rank)), os.path.basename(r)))


def frozen_transcripts(saved):
    """transcript_fn: the record with the sha this day recorded (hash-checked on read), else None."""
    want = {u["video_id"]: u.get("transcript_sha256") for u in saved.get("universe") or []}

    def fn(video_id):
        sha = want.get(video_id)
        if not sha:
            return None
        try:
            return next((r for r in ts.transcript_records(video_id) if r["transcript_sha256"] == sha), None)
        except (OSError, ValueError, ts.AcquisitionError):
            return None
    return fn


def _run_transcript(video_id, runs_dir=RUNS_DIR):
    """A run's own large-v3 word transcript of this video (select_passages), wrapped as a word record."""
    import punctuation
    for p in sorted(glob.glob(os.path.join(runs_dir, "*", "transcripts", f"{video_id}.json"))):
        try:
            d = json.load(open(p))
        except (OSError, ValueError):
            continue
        words = d.get("words") or []
        if words and (d.get("punctuation") or not punctuation.needs_restoration(words)):
            return {"video_id": video_id, "words": words, "transcript_method": "run_transcript:large-v3",
                    "transcript_model": "large-v3 (run transcript)", "source_path": os.path.relpath(p, REPO),
                    "transcript_sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}
    return None


def offline_words(runs_dir=RUNS_DIR):
    """words_fn: a sentence-ready store word record, else a run's large-v3 transcript, else none (a live run
    would transcribe: recorded as the gate)."""
    def fn(video_id):
        r = ts.canonical_transcript(video_id)
        if ts.sentence_ready(r):
            return r, f"store {r['transcript_method']}"
        r = _run_transcript(video_id, runs_dir)
        if r:
            return r, f"run transcript {r['source_path']}"
        return None, "backtest: no word record (a live run would transcribe it)"
    return fn


def stories_of(saved):
    """The story-engine items this day saw, rebuilt from its saved candidates."""
    items = []
    for c in saved.get("candidates") or []:
        if c.get("origin") != "story_engine" or not c.get("headline"):
            continue
        items.append({"rank": c.get("engine_rank"), "overall_score": c.get("engine_score"),
                      "headline": c["headline"], "summary": c.get("summary") or "",
                      "source_domain": c.get("source_domain") or "",
                      "freshness_minutes": round((c.get("age_h") or 0) * 60)})
    gen = (saved.get("story_engine") or {}).get("generated_at") or saved["started"]
    return {"generated_at": gen, "stories": items}


def universe_of(saved, registry):
    by_cid = {c["channel_id"]: c for c in registry if c.get("channel_id")}

    def fn(hours):
        out = []
        for u in saved.get("universe") or []:
            ch = by_cid.get(u.get("channel_id")) or {"channel_id": u.get("channel_id"), "display_name": u.get("channel")}
            out.append({"video_id": u["video_id"], "rss": {"title": u.get("title"), "published": u.get("published_at")},
                        "channel": ch, "age_h": u.get("age_h")})
        return out
    return fn


def summarise(day_dir, out_dir, seconds, outcome):
    t = json.load(open(os.path.join(out_dir, "TOPIC_SELECTION.json")))
    em = t.get("emergent_clusters") or []
    cands = t.get("candidates") or []
    row = {"run": os.path.basename(day_dir), "day": (t.get("today") or ""), "outcome": outcome,
           "seconds": round(seconds), "universe": (t.get("universe_summary") or {}).get("videos"),
           "with_transcript": (t.get("universe_summary") or {}).get("with_transcript"),
           "clusters": len(em), "screen_48h": sum(e.get("screen") == "48h" for e in em),
           "screen_72h": sum(e.get("screen") == "72h" for e in em),
           "coverage_qualified": sum(1 for c in cands if c.get("clip_quality") is not None),
           "producible": sum(1 for c in cands if c.get("decision") == "producible"),
           "llm": t.get("llm", {}).get("calls"), "llm_cache_hits": t.get("llm", {}).get("cache_hits")}
    if t.get("selected"):
        chosen = json.load(open(os.path.join(out_dir, "passages.json"))).get("chosen") or []
        row["selected"] = {"headline": t["selected"]["headline"], "origin": t["selected"]["origin"],
                           "channels": [p["channel"] for p in chosen],
                           "lineup": [{"kind": p["kind"], "channel": p["channel"], "video_id": p["video_id"],
                                       "start": p["start"], "end": p["end"], "text": p["text"][:160]} for p in chosen]}
    ranked = sorted((c for c in cands if c.get("importance")),
                    key=lambda c: -c["importance"].get("importance_score", 0))
    row["top5"] = [{"headline": c["headline"][:100], "origin": c["origin"],
                    "score": c["importance"].get("importance_score"),
                    "gate": c.get("decision") or "; ".join(c.get("importance_gate") or []) or "not evaluated"}
                   for c in ranked[:5]]
    return row


def run_day(day_dir, out_root, L, E, registry):
    import editorial_select as es
    saved = json.load(open(os.path.join(day_dir, "TOPIC_SELECTION.json")))
    out_dir = os.path.join(out_root, os.path.basename(day_dir))
    os.makedirs(out_dir, exist_ok=True)
    sp = os.path.join(out_dir, "stories.json")
    json.dump(stories_of(saved), open(sp, "w"))
    now = datetime.fromisoformat(saved["started"]).astimezone(timezone.utc)
    logf = open(os.path.join(out_dir, "selection.log"), "w")
    t0 = time.time()
    try:
        es.select_story(out_dir, log=lambda s: (logf.write(str(s) + "\n"), logf.flush()), embedder=E, llm=L,
                        universe_fn=universe_of(saved, registry), stories_path=sp, topup=False, now=now,
                        transcript_fn=frozen_transcripts(saved), words_fn=offline_words())
        outcome = "PRODUCIBLE"
    except es.NoProducibleStory as e:
        outcome = f"HOLD: {e}"
    except Exception as e:                                         # a crash is a row, never a silent skip
        outcome = f"CRASH: {type(e).__name__}: {e}"
        logf.write(traceback.format_exc())
    finally:
        logf.close()
    try:
        return summarise(day_dir, out_dir, time.time() - t0, outcome)
    except (OSError, ValueError, KeyError) as e:
        return {"run": os.path.basename(day_dir), "outcome": outcome, "summary_error": str(e),
                "seconds": round(time.time() - t0)}


def table(rows):
    lines = ["| run | day | outcome | universe | clusters | 48h / 72h | cov-qualified | producible | lineup | s | LLM calls / cache hits |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        sel = r.get("selected")
        lineup = (f"{sel['headline'][:70]} ({', '.join(sel['channels'])})" if sel else "-")
        lines.append(f"| {r['run']} | {r.get('day', '')} | {r['outcome'][:60]} | {r.get('universe')} / "
                     f"{r.get('with_transcript')} | {r.get('clusters')} | {r.get('screen_48h')} / {r.get('screen_72h')} | "
                     f"{r.get('coverage_qualified')} | {r.get('producible')} | {lineup} | {r.get('seconds')} | "
                     f"{r.get('llm')} / {r.get('llm_cache_hits')} |")
    days = {r.get("day") for r in rows if r["outcome"] == "PRODUCIBLE"}
    lines.append(f"\nProducible days: {len(days)} of {len({r.get('day') for r in rows})} ({sorted(days)})")
    for r in rows:
        if r["outcome"] != "PRODUCIBLE":
            lines.append(f"\n{r['run']} top 5 by importance and the gate that stopped each:")
            lines += [f"- [{c['score']}] {c['headline']} ({c['origin']}): {c['gate'][:200]}" for c in r.get("top5", [])]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", help="run dir names (default: every saved universe)")
    ap.add_argument("--out", default=os.path.join(RUNS_DIR, "backtest_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")))
    a = ap.parse_args(argv)
    import story_semantics as sm
    days = saved_days()
    if a.runs:
        days = [d for d in days if os.path.basename(d) in set(a.runs)]
    os.makedirs(a.out, exist_ok=True)
    registry = json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))
    E, L = sm.Embedder(), sm.LocalLLM().start()
    rows, t0 = [], time.time()
    try:
        for d in days:
            print(f"== {os.path.basename(d)}", flush=True)
            rows.append(run_day(d, a.out, L, E, registry))
            r = rows[-1]
            print(f"   {r['outcome'][:100]} | {r.get('seconds')} s | LLM {r.get('llm')} calls, "
                  f"{r.get('llm_cache_hits')} cached", flush=True)
            json.dump({"rows": rows, "seconds": round(time.time() - t0)}, open(os.path.join(a.out, "backtest.json"), "w"),
                      indent=1)
            open(os.path.join(a.out, "BACKTEST.md"), "w").write(table(rows) + "\n")
    finally:
        L.stop()
        E.close()
    print(table(rows))
    print(f"total {round(time.time() - t0)} s -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
