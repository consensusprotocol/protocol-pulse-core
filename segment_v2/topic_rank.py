#!/usr/bin/env python3
"""Stage S2: Topic selection via Grok (xAI). Same JSON contract as Gemini version.
Uses XAI_API_KEY_MEDLEY. Requires >=3 distinct channels for a qualifying topic."""
import json
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv("/home/ultron/protocol_pulse/.env")

BASE = "/home/ultron/protocol_pulse/segment_v2"
SOURCES_FILE = f"{BASE}/sources.json"
OUTPUT_FILE = f"{BASE}/topic.json"

XAI_KEY = os.environ.get("XAI_API_KEY_MEDLEY")
if not XAI_KEY:
    print("FATAL: XAI_API_KEY_MEDLEY not set"); sys.exit(1)

with open(SOURCES_FILE) as f:
    sources = json.load(f)

# Load RSS headlines as supporting signal
rss_lines = []
rss_path = "/home/ultron/protocol_pulse/data/intelligence/rss_pool.jsonl"
if os.path.exists(rss_path):
    for line in open(rss_path).readlines()[-30:]:
        try:
            d = json.loads(line)
            rss_lines.append(f"- [{d.get('source','?')}] \"{d.get('title','?')}\"")
        except Exception:
            pass

video_list = "\n".join(
    f"- [{v['channel_name']}] \"{v['title']}\" (video_id={v['video_id']}, uploaded {v['upload_date']}, {v['duration_s']}s)"
    for v in sources["videos"]
)
rss_list = "\n".join(rss_lines) if rss_lines else "(no RSS headlines available)"

prompt = f"""You are a Bitcoin news editor for Protocol Pulse, a Bitcoin-only intelligence show.

YOUTUBE VIDEOS (last {sources['window_hours']} hours):
{video_list}

RSS HEADLINES (supporting signal only):
{rss_list}

TASK: Identify the top 3 news topics discussed across these video sources. For each topic:
1. Give a short topic name (5-10 words)
2. Count how many DISTINCT YouTube channels cover it
3. List which channels cover it
4. Rate news relevance 1-10 (10 = massive breaking Bitcoin story)

Then pick the BEST topic for a 60-90 second multi-channel medley. The topic MUST be covered by at least 3 distinct channels. If none qualifies with 3+, pick the best 2-channel topic and note it fails the threshold.

For the chosen topic, provide:
- Topic name
- One-sentence editorial angle for a short medley (Bitcoin-focused, not altcoin)
- List of videos that cover this topic, using the EXACT video_id values from the list above

IMPORTANT:
- Only consider Bitcoin-relevant topics. Ignore altcoin-specific content.
- Use the EXACT video_id values provided. Do NOT make up IDs.
- A topic about macro/economy/elections counts if the videos discuss its impact on BITCOIN.

Respond in valid JSON only (no markdown fences, no comments):
{{
  "ranked_topics": [
    {{"rank": 1, "topic": "...", "channel_count": N, "channels": ["..."], "relevance": N}},
    ...
  ],
  "chosen_topic": {{
    "topic": "...",
    "angle": "...",
    "qualifies_3_channels": true/false,
    "videos": [
      {{"channel": "...", "title": "...", "video_id": "..."}}
    ]
  }}
}}"""

print(f"Calling Grok with {len(sources['videos'])} videos...")
resp = requests.post(
    "https://api.x.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
    json={
        "model": "grok-3-mini-fast",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    },
    timeout=60,
)

if resp.status_code != 200:
    print(f"FATAL: Grok API {resp.status_code}: {resp.text[:300]}")
    sys.exit(1)

raw = resp.json()["choices"][0]["message"]["content"]
if raw.startswith("```"):
    raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]

result = json.loads(raw)

# Validate video IDs — strip any that Grok hallucinated
valid_ids = {v["video_id"] for v in sources["videos"]}
id_to_meta = {v["video_id"]: v for v in sources["videos"]}
cleaned = []
for v in result["chosen_topic"]["videos"]:
    if v["video_id"] in valid_ids:
        cleaned.append(v)
    else:
        print(f"WARNING: Grok hallucinated video_id '{v['video_id']}' — dropped")
result["chosen_topic"]["videos"] = cleaned

# Re-count distinct channels after cleanup
ch_set = set(v["channel"] for v in cleaned)
result["chosen_topic"]["qualifies_3_channels"] = len(ch_set) >= 3

print(json.dumps(result, indent=2))

with open(OUTPUT_FILE, "w") as f:
    json.dump(result, f, indent=2)

chosen = result["chosen_topic"]
print(f"\nTopic: {chosen['topic']}")
print(f"Angle: {chosen['angle']}")
print(f"Qualifies (>=3 channels): {chosen['qualifies_3_channels']}")
print(f"Videos: {len(chosen['videos'])}")

if not chosen["qualifies_3_channels"]:
    print("\nSTOP: No qualifying topic with >=3 distinct channels.")
    sys.exit(2)
