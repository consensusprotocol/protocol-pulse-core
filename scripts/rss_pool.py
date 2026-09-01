#!/usr/bin/env python3
"""rss_pool.py — free 15-minute sensing. Appends unseen RSS items to data/intelligence/rss_pool.jsonl
so the 2-hour shadow cycle never misses an item that scrolled out of a feed. No LLM calls. No posting."""
import sys, os, json, time
sys.path.insert(0, os.path.expanduser("~/protocol_pulse"))
from dotenv import load_dotenv; load_dotenv(os.path.expanduser("~/protocol_pulse/.env"))
import services.story_engine as se
POOL = os.path.expanduser("~/protocol_pulse/data/intelligence/rss_pool.jsonl")
seen = set()
if os.path.exists(POOL):
    for line in open(POOL):
        try: seen.add(json.loads(line)["url"])
        except Exception: pass
items = se.harvest_rss()
new = [it for it in items if it.get("url") and it["url"] not in seen]
with open(POOL, "a") as f:
    for it in new: f.write(json.dumps(it, default=str) + "\n")
# trim pool to 72h
keep = []
for line in open(POOL):
    try:
        it = json.loads(line)
        if it.get("published_ts", 0) >= time.time() - 72 * 3600: keep.append(line)
    except Exception: pass
open(POOL, "w").writelines(keep)
print(f"{time.strftime('%H:%M:%S')} harvested {len(items)} | new {len(new)} | pool {len(keep)}")
