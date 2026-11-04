#!/usr/bin/env python3
"""Stage 1b: Topic selection with one Gemini call."""
import json
import os
import sys

# Load sources
with open("/home/ultron/protocol_pulse/segment_v1/sources.json") as f:
    sources = json.load(f)

# Add the extra videos from Bitcoin Magazine and CoinDesk scans
extra_videos = [
    {
        "channel_name": "Bitcoin Magazine", "channel_handle": "@BitcoinMagazine",
        "channel_id": "UCni7PAlyNS0_12H-26DJJ3w",
        "video_id": "7mdg_cazehA", "title": "Prediction Markets See 'Wild' Election Arbitrage Opportunity",
        "duration_s": 422, "upload_date": "20261102",
        "url": "https://www.youtube.com/watch?v=7mdg_cazehA",
    },
    {
        "channel_name": "Bitcoin Magazine", "channel_handle": "@BitcoinMagazine",
        "channel_id": "UCni7PAlyNS0_12H-26DJJ3w",
        "video_id": "I62qZeTjym4", "title": "$2.3 Billion AUM Clocktower Macro Chief: How to Invest in a 'Higher for Longer' World",
        "duration_s": 1095, "upload_date": "20261102",
        "url": "https://www.youtube.com/watch?v=I62qZeTjym4",
    },
    {
        "channel_name": "Bitcoin Magazine", "channel_handle": "@BitcoinMagazine",
        "channel_id": "UCni7PAlyNS0_12H-26DJJ3w",
        "video_id": "lYR2vp9wCQQ", "title": "Andrew Hohns: Why Bitcoin Can Fix America's Debt Spiral",
        "duration_s": 1078, "upload_date": "20261102",
        "url": "https://www.youtube.com/watch?v=lYR2vp9wCQQ",
    },
    {
        "channel_name": "Bitcoin Magazine", "channel_handle": "@BitcoinMagazine",
        "channel_id": "UCni7PAlyNS0_12H-26DJJ3w",
        "video_id": "rCByOV2seAg", "title": "Bitwise's André Dragosch: Bitcoin's 'Fair Value' of $197,000",
        "duration_s": 3071, "upload_date": "20261101",
        "url": "https://www.youtube.com/watch?v=rCByOV2seAg",
    },
    {
        "channel_name": "CoinDesk", "channel_handle": "@CoinDesk",
        "channel_id": "UCwgr28VHKiRaIJUqfYkQMgg",
        "video_id": "7QIB_zdKU9A", "title": "Bitcoin ETFs Hit by $643M Selloff as Binance Hack Shakes Crypto",
        "duration_s": 2179, "upload_date": "20261102",
        "url": "https://www.youtube.com/watch?v=7QIB_zdKU9A",
        "extra_channel_reason": "CoinDesk: major crypto news outlet, established 2013, industry standard"
    },
]

# Merge into sources, dedup by video_id
existing_ids = {v["video_id"] for v in sources["videos"]}
for ev in extra_videos:
    if ev["video_id"] not in existing_ids:
        sources["videos"].append(ev)
        existing_ids.add(ev["video_id"])

# Save updated sources
with open("/home/ultron/protocol_pulse/segment_v1/sources.json", "w") as f:
    json.dump(sources, f, indent=2)

# Load RSS headlines
try:
    with open("/home/ultron/protocol_pulse/segment_v1/rss_headlines.json") as f:
        rss = json.load(f)
except FileNotFoundError:
    rss = []

# Build the prompt for Gemini
video_list = "\n".join(
    f"- [{v['channel_name']}] \"{v['title']}\" ({v['upload_date']})"
    for v in sources["videos"]
)
rss_list = "\n".join(
    f"- [{h['source']}] \"{h['title']}\""
    for h in rss
)

prompt = f"""You are a Bitcoin news editor. Below are YouTube video titles from the last 48 hours and RSS headlines.

YOUTUBE VIDEOS:
{video_list}

RSS HEADLINES:
{rss_list}

TASK: Identify the top 5 news topics discussed across these sources. For each topic:
1. Give a short topic name (5-10 words)
2. Count how many DISTINCT channels/sources cover it
3. List which channels/sources cover it
4. Rate news relevance 1-10 (10 = massive breaking story)

Then pick the BEST topic for a 60-90 second multi-channel medley. The topic MUST be covered by at least 3 distinct channels. If none qualifies with 3+, pick the best 2-channel topic and note it.

For the chosen topic, provide:
- Topic name
- One-sentence editorial angle for a short medley
- List of videos that cover this topic (with video titles)

Respond in valid JSON with this structure:
{{
  "ranked_topics": [
    {{"rank": 1, "topic": "...", "channel_count": N, "channels": [...], "relevance": N}},
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
}}
"""

# One Gemini call
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv("/home/ultron/protocol_pulse/.env")

genai.configure(api_key=os.environ["GEMINI_API_KEY_MEDLEY"])
model = genai.GenerativeModel("gemini-3.8-flash")
response = model.generate_content(
    prompt,
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json",
        temperature=0.3,
    )
)

result = json.loads(response.text)
print(json.dumps(result, indent=2))

# Write topic.json
with open("/home/ultron/protocol_pulse/segment_v1/topic.json", "w") as f:
    json.dump(result, f, indent=2)

print(f"\nTopic selected: {result['chosen_topic']['topic']}")
print(f"Angle: {result['chosen_topic']['angle']}")
print(f"Qualifies (>=3 channels): {result['chosen_topic']['qualifies_3_channels']}")
print(f"Videos: {len(result['chosen_topic']['videos'])}")
