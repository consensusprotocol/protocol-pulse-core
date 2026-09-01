#!/usr/bin/env python3
"""
shadow_cycle.py — one expensive cycle of the frozen SOCIAL_ENGINE_V1 in SHADOW MODE.
  1. story_engine.run() (harvest + cluster + score + audit + external verify), merging the
     free 15-minute RSS pool so nothing that scrolled out of a feed is missed
  2. writer on stories that are writer_eligible AND not already seen by the queue
  3. enqueue into the human review queue at /admin/review
Posts nothing. Does not read POSTING_PAUSED because it never reaches a posting path.
Cron: every 2h. Log: logs/shadow_cycle.log
"""
import sys, os, json, time
sys.path.insert(0, os.path.expanduser("~/protocol_pulse"))
from dotenv import load_dotenv; load_dotenv(os.path.expanduser("~/protocol_pulse/.env"))
import services.story_engine as se
import services.writer_test as wt
import services.review_queue as rq

POOL = os.path.expanduser("~/protocol_pulse/data/intelligence/rss_pool.jsonl")

def load_pool(max_age_h=48):
    items, cutoff = [], time.time() - max_age_h * 3600
    if os.path.exists(POOL):
        for line in open(POOL):
            try:
                it = json.loads(line)
                if it.get("published_ts", 0) >= cutoff: items.append(it)
            except Exception: pass
    return items

def main():
    t0 = time.time()
    print(f"=== SHADOW CYCLE {time.strftime('%Y-%m-%d %H:%M:%S %Z')} ===")
    pool = load_pool()
    print(f"  RSS pool items (<=48h): {len(pool)}")
    stories = se.run(extra_items=pool)
    seen = rq.seen_ids()
    todo = [s for s in stories if s.get("writer_eligible") and s.get("story_id") not in seen]
    print(f"=== WRITER on {len(todo)} eligible+unseen (of {sum(1 for s in stories if s.get('writer_eligible'))} eligible) ===")
    records = []
    for s in todo:
        try:
            rec = wt.write_story(s); records.append(rec)
            print(f"  [{rec['postable_count']}/3 postable] {rec['headline'][:70]}")
        except Exception as e:
            print(f"  [writer error] {type(e).__name__}: {s.get('headline','')[:60]}")
    n = rq.enqueue(records)
    print(f"=== QUEUED {n} new candidates -> /admin/review | pending {len(rq.pending())} | {time.time()-t0:.0f}s ===")

if __name__ == "__main__":
    main()
