#!/usr/bin/env python3
"""Stage S3: Select passages from transcripts. Generalized — keywords and VIDEO_META
derived from topic.json + sources.json, never hard-coded.
One clip per channel, 8-20s, sentence-complete, ranked by relevance to the angle.
REJECT reaction-to-reaction passages. Simply Bitcoin only when original dialogue."""
import json
import os
import re
import sys
import requests
from dotenv import load_dotenv

load_dotenv("/home/ultron/protocol_pulse/.env")

BASE = "/home/ultron/protocol_pulse/segment_v2"
TRANS_DIR = f"{BASE}/transcripts"

with open(f"{BASE}/topic.json") as f:
    topic = json.load(f)
with open(f"{BASE}/sources.json") as f:
    sources = json.load(f)

OUTPUT_EDL = f"{BASE}/edl.json"
OUTPUT_CANDIDATES = f"{BASE}/candidates.json"

chosen = topic["chosen_topic"]
selected_vids = {v["video_id"]: v for v in chosen["videos"]}

# Build VIDEO_META from sources
VIDEO_META = {}
for v in sources["videos"]:
    if v["video_id"] in selected_vids:
        VIDEO_META[v["video_id"]] = {
            "channel": v["channel_name"],
            "handle": v["channel_handle"],
            "title": v["title"],
        }

print(f"Topic: {chosen['topic']}")
print(f"Angle: {chosen['angle']}")
print(f"Videos: {list(VIDEO_META.keys())}")

# Generate topic keywords via Grok (one quick call)
XAI_KEY = os.environ.get("XAI_API_KEY_MEDLEY")
kw_prompt = f"""Given this topic: "{chosen['topic']}"
And this angle: "{chosen['angle']}"

List 20-30 search keywords and short phrases that would appear in transcripts covering this topic.
Include specific terms, names, numbers, and concepts.
Return as a JSON array of lowercase strings only (no markdown fences).
Example: ["federal reserve", "dollar", "debt spiral", "print money", "bitcoin"]"""

print("Generating topic keywords via Grok...")
resp = requests.post(
    "https://api.x.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
    json={"model": "grok-3-mini-fast",
          "messages": [{"role": "user", "content": kw_prompt}],
          "temperature": 0.2},
    timeout=30,
)
raw_kw = resp.json()["choices"][0]["message"]["content"]
if raw_kw.startswith("```"):
    raw_kw = raw_kw.split("\n", 1)[1]
    if raw_kw.endswith("```"):
        raw_kw = raw_kw[:-3]
TOPIC_KEYWORDS = json.loads(raw_kw)
print(f"Keywords ({len(TOPIC_KEYWORDS)}): {TOPIC_KEYWORDS[:10]}...")

# Reaction-to-reaction detection phrases
REACTION_PHRASES = [
    "this clip", "this video", "listen to this", "watch this",
    "as you can see", "let me show you", "playing a clip",
    "let's watch", "check this out", "look at this",
    "let me play", "here's what he said", "here's what she said",
]


def load_transcript(vid_id):
    path = os.path.join(TRANS_DIR, f"{vid_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def is_reaction(text):
    """Detect if passage is reacting to another creator's clip."""
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in REACTION_PHRASES)


def find_candidate_passages(transcript, vid_id):
    """Find 8-20s passages on topic with complete sentences."""
    words = transcript["words"]
    segments = transcript["segments"]
    if not words:
        return []

    channel = VIDEO_META[vid_id]["channel"]
    candidates = []

    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue

        text_lower = text.lower()
        topic_hits = sum(1 for kw in TOPIC_KEYWORDS if kw in text_lower)
        if topic_hits == 0:
            continue

        duration = seg["end"] - seg["start"]
        if duration < 6 or duration > 25:
            continue

        # Reaction-to-reaction law
        if is_reaction(text):
            continue

        # Simply Bitcoin: only when original dialogue
        if channel == "Simply Bitcoin" and is_reaction(text):
            continue

        seg_words = [w for w in words if w["start"] >= seg["start"] - 0.5
                     and w["end"] <= seg["end"] + 0.5]
        if not seg_words:
            continue

        score = 0
        numbers = re.findall(r'\$[\d,.]+|\d+\s*(?:billion|million|trillion|percent|%)', text_lower)
        score += len(numbers) * 15
        score += topic_hits * 10
        if 10 <= duration <= 20:
            score += 10
        elif duration < 8 or duration > 22:
            score -= 10

        first_word = seg_words[0]["word"].lower().strip()
        if first_word in ("and", "but", "so", "because", "which", "that's", "since", "meaning"):
            score -= 15
        if first_word in ("he", "she", "they", "them", "him", "her", "it's", "its"):
            score -= 10

        if "!" in text:
            score += 5

        candidates.append({
            "video_id": vid_id,
            "channel": channel,
            "text": text,
            "start": seg["start"],
            "end": seg["end"],
            "duration": round(duration, 2),
            "first_word": seg_words[0]["word"].strip(),
            "last_word": seg_words[-1]["word"].strip(),
            "word_start": seg_words[0]["start"],
            "word_end": seg_words[-1]["end"],
            "score": score,
            "topic_hits": topic_hits,
            "num_words": len(seg_words),
        })

    return candidates


def merge_adjacent_segments(transcript, vid_id):
    segments = transcript["segments"]
    words = transcript["words"]
    channel = VIDEO_META[vid_id]["channel"]
    candidates = []

    for i in range(len(segments) - 1):
        for span in range(2, 4):
            if i + span > len(segments):
                break
            merged_segs = segments[i:i+span]
            merged_text = " ".join(s["text"].strip() for s in merged_segs)
            merged_start = merged_segs[0]["start"]
            merged_end = merged_segs[-1]["end"]
            duration = merged_end - merged_start

            if duration < 8 or duration > 22:
                continue

            if is_reaction(merged_text):
                continue

            text_lower = merged_text.lower()
            topic_hits = sum(1 for kw in TOPIC_KEYWORDS if kw in text_lower)
            if topic_hits < 2:
                continue

            seg_words = [w for w in words if w["start"] >= merged_start - 0.5
                         and w["end"] <= merged_end + 0.5]
            if not seg_words:
                continue

            score = topic_hits * 10
            numbers = re.findall(r'\$[\d,.]+|\d+\s*(?:billion|million|trillion|percent|%)', text_lower)
            score += len(numbers) * 15
            if 10 <= duration <= 20:
                score += 10

            first_word = seg_words[0]["word"].lower().strip()
            if first_word in ("and", "but", "so", "because", "which", "that's"):
                score -= 15

            candidates.append({
                "video_id": vid_id,
                "channel": channel,
                "text": merged_text,
                "start": merged_start,
                "end": merged_end,
                "duration": round(duration, 2),
                "first_word": seg_words[0]["word"].strip(),
                "last_word": seg_words[-1]["word"].strip(),
                "word_start": seg_words[0]["start"],
                "word_end": seg_words[-1]["end"],
                "score": score,
                "topic_hits": topic_hits,
                "num_words": len(seg_words),
                "merged_segments": span,
            })

    return candidates


# Collect candidates
all_candidates = []
for vid_id in VIDEO_META:
    t = load_transcript(vid_id)
    if not t:
        print(f"WARNING: No transcript for {vid_id}")
        continue
    print(f"Processing {vid_id} ({VIDEO_META[vid_id]['channel']})...")
    single = find_candidate_passages(t, vid_id)
    merged = merge_adjacent_segments(t, vid_id)
    print(f"  Single: {len(single)}, Merged: {len(merged)}")
    all_candidates.extend(single)
    all_candidates.extend(merged)

# Deduplicate overlapping, keep highest score
all_candidates.sort(key=lambda x: x["score"], reverse=True)
selected = []
used_ranges = {}

for c in all_candidates:
    vid = c["video_id"]
    if vid not in used_ranges:
        used_ranges[vid] = []
    overlap = any(c["start"] < e and c["end"] > s for s, e in used_ranges[vid])
    if not overlap:
        selected.append(c)
        used_ranges[vid].append((c["start"], c["end"]))

print(f"\nTotal non-overlapping candidates: {len(selected)}")

# Write all candidates
with open(OUTPUT_CANDIDATES, "w") as f:
    json.dump(selected[:20], f, indent=2)

# Print top 10
print("\n=== TOP 10 CANDIDATES ===")
for i, c in enumerate(selected[:10]):
    print(f"\n#{i+1} [score={c['score']}] {c['channel']} ({c['duration']:.1f}s)")
    print(f"  {c['text'][:120]}...")
    print(f"  words: \"{c['first_word']}\" -> \"{c['last_word']}\"  time: {c['word_start']:.2f}-{c['word_end']:.2f}")

# === BUILD EDL ===
# ONE clip per channel, narrative order: setup -> scale -> lesson
# Target 3-4 clips, hook = single strongest line

print("\n\n=== BUILDING EDL ===")

# Best per channel (enforce one-per-channel)
best_per_channel = {}
for c in selected:
    ch = c["channel"]
    if ch not in best_per_channel:
        best_per_channel[ch] = c

edl_clips = list(best_per_channel.values())

# Narrative order: setup -> scale -> lesson
# Use Grok to order them
if len(edl_clips) >= 2:
    clip_descs = "\n".join(
        f"CLIP {i+1} [{c['channel']}]: \"{c['text'][:150]}\""
        for i, c in enumerate(edl_clips)
    )
    order_prompt = f"""Given these clips about "{chosen['topic']}":

{clip_descs}

Order them for a medley: setup -> scale -> lesson.
Return ONLY a JSON array of clip numbers (1-indexed) in the best narrative order.
Example: [2, 1, 3]"""

    resp = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
        json={"model": "grok-3-mini-fast",
              "messages": [{"role": "user", "content": order_prompt}],
              "temperature": 0.1},
        timeout=20,
    )
    try:
        order_raw = resp.json()["choices"][0]["message"]["content"]
        if order_raw.startswith("```"):
            order_raw = order_raw.split("\n", 1)[1]
            if order_raw.endswith("```"):
                order_raw = order_raw[:-3]
        order = json.loads(order_raw)
        reordered = [edl_clips[i-1] for i in order if 1 <= i <= len(edl_clips)]
        if len(reordered) == len(edl_clips):
            edl_clips = reordered
            print(f"Narrative order from Grok: {order}")
    except Exception as e:
        print(f"WARNING: Could not parse Grok order: {e}. Using score order.")

# Find hook: single strongest line <=12s from any clip
hook = None
for c in selected:
    if c["duration"] <= 12 and c["score"] >= 20:
        hook = c
        break
if not hook and selected:
    hook = selected[0]

total_dur = sum(c["duration"] for c in edl_clips)
print(f"Selected {len(edl_clips)} clips, total: {total_dur:.1f}s")

# Build VO script (intro + bridges + signoff)
channels_in_edl = [c["channel"] for c in edl_clips]
all_channels_str = ", ".join(channels_in_edl[:-1]) + f" and {channels_in_edl[-1]}" if len(channels_in_edl) > 1 else channels_in_edl[0]

vo_prompt = f"""Write voiceover narration for a 60-90 second Bitcoin medley about: "{chosen['topic']}"
Angle: {chosen['angle']}

The medley has {len(edl_clips)} clips from: {all_channels_str}.
Clip summaries:
{chr(10).join(f"Clip {i+1} [{c['channel']}]: {c['text'][:100]}..." for i, c in enumerate(edl_clips))}

Write:
1. intro (2-3 sentences, hook the viewer, set up the topic)
2. One bridge per clip transition (1-2 sentences each, value-add or affirmative, SHORT)
3. signoff (1-2 sentences, shout out every channel: {all_channels_str})

Rules:
- Short, punchy sentences
- Value-add: don't just summarize, add insight
- Affirmative tone (Bitcoin is the answer)
- Signoff must name ALL channels

Return valid JSON (no markdown fences):
{{
  "intro": "...",
  "bridges": [
    {{"after_clip": 1, "text": "..."}},
    ...
  ],
  "signoff": "..."
}}"""

print("Generating VO script via Grok...")
resp = requests.post(
    "https://api.x.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
    json={"model": "grok-3-mini-fast",
          "messages": [{"role": "user", "content": vo_prompt}],
          "temperature": 0.4},
    timeout=30,
)
vo_raw = resp.json()["choices"][0]["message"]["content"]
if vo_raw.startswith("```"):
    vo_raw = vo_raw.split("\n", 1)[1]
    if vo_raw.endswith("```"):
        vo_raw = vo_raw[:-3]
vo = json.loads(vo_raw)

# Build final EDL
edl = {
    "topic": chosen["topic"],
    "angle": chosen["angle"],
    "hook": {
        "video_id": hook["video_id"] if hook else None,
        "channel": hook["channel"] if hook else None,
        "text": hook["text"][:200] if hook else None,
        "first_word": hook["first_word"] if hook else None,
        "last_word": hook["last_word"] if hook else None,
        "word_start": hook["word_start"] if hook else None,
        "word_end": hook["word_end"] if hook else None,
        "duration": hook["duration"] if hook else None,
    },
    "clips": [],
    "vo": vo,
    "total_clip_duration": 0,
}

for i, c in enumerate(edl_clips):
    clip = {
        "index": i + 1,
        "video_id": c["video_id"],
        "channel": c["channel"],
        "handle": VIDEO_META[c["video_id"]]["handle"],
        "video_title": VIDEO_META[c["video_id"]]["title"],
        "text": c["text"],
        "first_word": c["first_word"],
        "last_word": c["last_word"],
        "word_start": c["word_start"],
        "word_end": c["word_end"],
        "duration": c["duration"],
    }
    edl["clips"].append(clip)
    edl["total_clip_duration"] = round(edl["total_clip_duration"] + c["duration"], 2)

print(f"\nFinal EDL: {len(edl['clips'])} clips, {edl['total_clip_duration']:.1f}s total")
print(f"Hook: {edl['hook']['text'][:80]}..." if edl['hook']['text'] else "No hook")

for clip in edl["clips"]:
    print(f"  #{clip['index']} {clip['channel']} ({clip['duration']:.1f}s): {clip['text'][:80]}...")

print(f"\nVO intro: {vo['intro'][:100]}...")
print(f"VO signoff: {vo['signoff'][:100]}...")

with open(OUTPUT_EDL, "w") as f:
    json.dump(edl, f, indent=2)

print(f"\nEDL written to {OUTPUT_EDL}")
print(f"Candidates written to {OUTPUT_CANDIDATES}")
