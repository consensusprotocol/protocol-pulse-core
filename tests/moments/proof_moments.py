#!/usr/bin/env python3
"""Phase-2 proof driver, step 1 (MINE) on saved universes. CPU only; read-only inputs (the run's universe, the store's
records by the recorded sha, as tests/select_by_id/proof_saved_runs.py reads them); every model reply recorded under
tests/moments/fixtures/replies (offline replay); spend in tests/moments/proof/SPEND.json with the phase-2 $40 guard.

Mining scope here: the videos with a sentence-ready word record in the store (on-screen capable, law L-e). A
caption-only video can be mined in production after the cycle's word pass (pipeline_pp_ingest); in this CPU replay it is
reported as awaiting the word pass, never mined from caption timing for the screen.

Usage: python3 tests/moments/proof_moments.py --runs fresh_20261112_050611 [--replay] [--recent-h 72]
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
import eligibility as E  # noqa: E402
import moments as M  # noqa: E402
import providers as P  # noqa: E402
import proof_saved_runs as PS  # noqa: E402
import trend_brief as TB  # noqa: E402

REPLIES = os.path.join(HERE, "fixtures", "replies")
OUT = os.path.join(HERE, "proof")
SPEND = os.path.join(OUT, "SPEND.json")
LIMIT_USD = 64.28                  # the phase-2 guard: $40 from 01:55 ET Nov 12, raised at 05:30 by $25 from
                                   # $39.28 (orchestrator amendment 05:30: $25, a package for tonight first)


def universe_sources(run):
    """(word Sources of the run's universe, caption-only video ids, ctx) from the saved run, read-only."""
    saved = json.load(open(os.path.join(PS.RUNS, run, "TOPIC_SELECTION.json")))
    started = datetime.fromisoformat(saved["started"])
    assert started.tzinfo is not None
    now = started.astimezone(timezone.utc)
    ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
    words, captions = [], []
    for u in saved.get("universe") or []:
        if not u.get("transcript_sha256") or u["video_id"] in E.V2F_VIDEO_IDS:
            continue
        w = PS.word_source(u, ctx)
        if w is not None:
            words.append(w)
        else:
            captions.append(u["video_id"])
    return words, captions, ctx, saved


def run_one(run, router, recent_h, log=print):
    words, captions, ctx, saved = universe_sources(run)
    t0 = time.time()
    base = TB.local_baseline(words, ctx, hours=24.0)
    out = M.mine(router, words, ctx, TB.TOPICS, since=None, optout=M.optout_ids(), log=log, cycle=f"proof:{run}",
                 recent_h=recent_h)
    for m in out["moments"]:
        m["trend"] = TB.trend_match(m, None, base)
    rec = {"run": run, "now": ctx.now.isoformat(), "seconds": round(time.time() - t0, 1),
           "scope": {"word_sources": len(words), "caption_only_awaiting_word_pass": len(captions)},
           "baseline": base, "rows": out["rows"], "sources_in_window": out["sources"], "skipped": out["skipped"],
           "calls": [{k: v for k, v in c.items() if k != "attempts"} | {"attempts": [
               {k2: v2 for k2, v2 in a.items() if k2 in ("attempt", "rejected", "declined", "model_error", "accepted",
                                                        "meta", "prompt_sha256")} for a in c["attempts"]]}
               for c in out["calls"]],
           "moments": out["moments"]}
    os.makedirs(os.path.join(OUT, run), exist_ok=True)
    json.dump(rec, open(os.path.join(OUT, run, "moments.json"), "w"), indent=1, default=str)
    usable = [m for m in out["moments"] if m["on_screen_ok"] and not m["excluded"]]
    log(f"{run}: {len(words)} word sources ({len(captions)} caption-only), rows {out['rows']}, calls "
        f"{[c['status'] for c in out['calls']]}, moments {len(out['moments'])}, usable on screen {len(usable)} "
        f"({rec['seconds']} s)")
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--recent-h", type=float, default=72.0, help="the first cycle of a saved universe: its whole 72 h")
    ap.add_argument("--chain", nargs="*", help="pin the mine role's chain (config names), e.g. for the A/B")
    a = ap.parse_args(argv)
    router = P.Router(env_path=PS.ENV, record_dir=REPLIES, replay=a.replay, spend_path=SPEND, limit_usd=LIMIT_USD,
                      chains={"mine": a.chain} if a.chain else None)
    for run in a.runs:
        run_one(run, router, a.recent_h)
    if router.notices:
        print("NOTICES:", router.notices)


if __name__ == "__main__":
    main()
