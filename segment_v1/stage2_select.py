#!/usr/bin/env python3
"""Stage 2: Select passages and build EDL for the single-story medley."""
import json
import os
import re
import math

TRANSCRIPTS_DIR = "/home/ultron/protocol_pulse/segment_v1/transcripts"
TOPIC_FILE = "/home/ultron/protocol_pulse/segment_v1/topic.json"
OUTPUT_EDL = "/home/ultron/protocol_pulse/segment_v1/edl.json"
OUTPUT_CANDIDATES = "/home/ultron/protocol_pulse/segment_v1/candidates.json"

with open(TOPIC_FILE) as f:
    topic = json.load(f)

# Topic keywords for matching
TOPIC_KEYWORDS = [
    "binance", "hack", "hacker", "hackers", "hacked", "stolen", "theft", "heist",
    "self-custody", "self custody", "not your keys", "not your coins",
    "cold storage", "hardware wallet", "custodial", "exchange risk",
    "6.3 billion", "6.3b", "$6.3", "billion dollar",
    "security", "breach", "exploit", "vulnerability",
    "withdrawal", "withdrawals", "frozen", "freeze",
]

VIDEO_META = {
    "bSmFGoAKPBc": {"channel": "Simply Bitcoin", "handle": "@SimplyBitcoin",
                     "title": "Why Bitcoin Is Holding Strong After a $6.3B Hack?"},
    "5ripuS9GDaM": {"channel": "Simply Bitcoin", "handle": "@SimplyBitcoin",
                     "title": "Was The $6.3B Binance Heist an Inside Job?"},
    "Eojd18J_wuU": {"channel": "BTC Sessions", "handle": "@BTCSessions",
                     "title": "Binance Just Proved Why Self-Custody Matters"},
    "7QIB_zdKU9A": {"channel": "CoinDesk", "handle": "@CoinDesk",
                     "title": "Bitcoin ETFs Hit by $643M Selloff as Binance Hack Shakes Crypto"},
}


def load_transcript(vid_id):
    path = os.path.join(TRANSCRIPTS_DIR, f"{vid_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def find_candidate_passages(transcript, vid_id):
    """Find 8-25s passages on topic with complete sentences."""
    words = transcript["words"]
    segments = transcript["segments"]
    if not words:
        return []

    # Build sentence boundaries from segments
    candidates = []

    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue

        # Check if segment is on-topic
        text_lower = text.lower()
        topic_hits = sum(1 for kw in TOPIC_KEYWORDS if kw in text_lower)
        if topic_hits == 0:
            continue

        duration = seg["end"] - seg["start"]

        # We want 8-25s passages
        if duration < 6 or duration > 30:
            continue

        # Find word-level boundaries for this segment
        seg_words = [w for w in words if w["start"] >= seg["start"] - 0.5
                     and w["end"] <= seg["end"] + 0.5]
        if not seg_words:
            continue

        # Score: specificity (numbers, names, claims), energy, self-containment
        score = 0

        # Specificity: numbers
        numbers = re.findall(r'\$[\d,.]+|\d+\s*(?:billion|million|percent|%)', text_lower)
        score += len(numbers) * 15

        # Specificity: names/entities
        names = re.findall(r'(?:Binance|Bitcoin|BTC|CZ|Changpeng|Zhao|SafePal|Ledger|Trezor|ETF)', text, re.IGNORECASE)
        score += min(len(names), 3) * 5

        # Topic keyword density
        score += topic_hits * 10

        # Self-containment: penalize if starts with continuation words
        first_word = seg_words[0]["word"].lower().strip()
        if first_word in ("and", "but", "so", "because", "which", "that's", "since", "meaning"):
            score -= 15

        # Penalize dangling pronouns at start
        if first_word in ("he", "she", "they", "them", "him", "her", "it's", "its"):
            # Check if it refers to something outside
            score -= 10

        # Ideal duration (12-20s sweet spot)
        if 10 <= duration <= 22:
            score += 10
        elif duration < 8 or duration > 25:
            score -= 10

        # Energy: exclamation marks, strong verbs
        if "!" in text:
            score += 5

        candidates.append({
            "video_id": vid_id,
            "channel": VIDEO_META[vid_id]["channel"],
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
    """Also try merging 2-3 adjacent on-topic segments for longer passages."""
    segments = transcript["segments"]
    words = transcript["words"]
    candidates = []

    for i in range(len(segments) - 1):
        for span in range(2, 4):  # 2 or 3 segments
            if i + span > len(segments):
                break
            merged_segs = segments[i:i+span]
            merged_text = " ".join(s["text"].strip() for s in merged_segs)
            merged_start = merged_segs[0]["start"]
            merged_end = merged_segs[-1]["end"]
            duration = merged_end - merged_start

            if duration < 8 or duration > 25:
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
            numbers = re.findall(r'\$[\d,.]+|\d+\s*(?:billion|million|percent|%)', text_lower)
            score += len(numbers) * 15
            if 10 <= duration <= 22:
                score += 10

            first_word = seg_words[0]["word"].lower().strip()
            if first_word in ("and", "but", "so", "because", "which", "that's"):
                score -= 15

            candidates.append({
                "video_id": vid_id,
                "channel": VIDEO_META[vid_id]["channel"],
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


# Collect all candidates
all_candidates = []
for vid_id in VIDEO_META:
    t = load_transcript(vid_id)
    if not t:
        print(f"WARNING: No transcript for {vid_id}")
        continue
    print(f"Processing {vid_id} ({VIDEO_META[vid_id]['channel']})...")
    single = find_candidate_passages(t, vid_id)
    merged = merge_adjacent_segments(t, vid_id)
    print(f"  Single-segment candidates: {len(single)}")
    print(f"  Merged candidates: {len(merged)}")
    all_candidates.extend(single)
    all_candidates.extend(merged)

# Deduplicate overlapping candidates (keep highest score)
all_candidates.sort(key=lambda x: x["score"], reverse=True)
selected = []
used_ranges = {}  # vid_id -> list of (start, end)

for c in all_candidates:
    vid = c["video_id"]
    if vid not in used_ranges:
        used_ranges[vid] = []
    # Check overlap with already selected
    overlap = False
    for (s, e) in used_ranges[vid]:
        if c["start"] < e and c["end"] > s:
            overlap = True
            break
    if not overlap:
        selected.append(c)
        used_ranges[vid].append((c["start"], c["end"]))

print(f"\nTotal non-overlapping candidates: {len(selected)}")

# Write all candidates
with open(OUTPUT_CANDIDATES, "w") as f:
    json.dump(selected[:15], f, indent=2)

# Print top 15
print("\n=== TOP 15 CANDIDATES ===")
for i, c in enumerate(selected[:15]):
    print(f"\n#{i+1} [score={c['score']}] {c['channel']} ({c['duration']:.1f}s)")
    print(f"  {c['text'][:120]}...")
    print(f"  words: \"{c['first_word']}\" -> \"{c['last_word']}\"  time: {c['word_start']:.2f}-{c['word_end']:.2f}")

# === BUILD EDL ===
# Pick 4-6 passages, one per video max (unless clearly different points), logical order
# Story arc: setup -> claim -> counterpoint -> implication

print("\n\n=== BUILDING EDL ===")

# Strategy: pick best from each video, then arrange in story order
best_per_video = {}
for c in selected:
    vid = c["video_id"]
    if vid not in best_per_video:
        best_per_video[vid] = []
    if len(best_per_video[vid]) < 3:
        best_per_video[vid].append(c)

# For the EDL, we want:
# 1. SETUP: what happened (the hack itself) - likely CoinDesk or Simply Bitcoin
# 2. CLAIM: how big / how bad - Simply Bitcoin or CoinDesk
# 3. ANALYSIS: was it inside job / how - Simply Bitcoin (heist video)
# 4. IMPLICATION: self-custody lesson - BTC Sessions
# 5. OUTLOOK: Bitcoin holding strong - Simply Bitcoin

# Select up to 6 clips fitting this arc
edl_clips = []

# Try to find clips for each arc position
arc_roles = [
    ("setup", "What happened - the hack itself"),
    ("scale", "How massive - $6.3B, largest ever"),
    ("analysis", "How it happened / inside job angle"),
    ("lesson", "Self-custody is the answer"),
    ("resilience", "Bitcoin holding strong despite hack"),
]

used_videos = set()
for role, desc in arc_roles:
    best = None
    for c in selected:
        vid = c["video_id"]
        # Allow max 2 from same video
        vid_count = sum(1 for e in edl_clips if e["video_id"] == vid)
        if vid_count >= 2:
            continue
        # Rough role matching
        text_lower = c["text"].lower()
        if role == "setup" and ("hack" in text_lower or "breach" in text_lower or "stolen" in text_lower):
            if not best or c["score"] > best["score"]:
                best = c
        elif role == "scale" and ("billion" in text_lower or "6.3" in text_lower or "largest" in text_lower):
            if not best or c["score"] > best["score"]:
                best = c
        elif role == "analysis" and ("inside" in text_lower or "how" in text_lower or "exploit" in text_lower):
            if not best or c["score"] > best["score"]:
                best = c
        elif role == "lesson" and ("self-custody" in text_lower or "self custody" in text_lower or "not your keys" in text_lower or "hardware wallet" in text_lower or "cold storage" in text_lower):
            if not best or c["score"] > best["score"]:
                best = c
        elif role == "resilience" and ("holding" in text_lower or "strong" in text_lower or "recover" in text_lower or "resili" in text_lower):
            if not best or c["score"] > best["score"]:
                best = c
    if best:
        # Check not already in EDL (overlapping)
        already = False
        for e in edl_clips:
            if e["video_id"] == best["video_id"] and abs(e["start"] - best["start"]) < 5:
                already = True
                break
        if not already:
            edl_clips.append({**best, "role": role, "role_desc": desc})

total_dur = sum(c["duration"] for c in edl_clips)
print(f"Selected {len(edl_clips)} clips, total duration: {total_dur:.1f}s")

# If under 50s, add more clips
if total_dur < 50 and len(selected) > len(edl_clips):
    for c in selected:
        if total_dur >= 75:
            break
        already = any(
            e["video_id"] == c["video_id"] and abs(e["start"] - c["start"]) < 5
            for e in edl_clips
        )
        vid_count = sum(1 for e in edl_clips if e["video_id"] == c["video_id"])
        if not already and vid_count < 2:
            edl_clips.append({**c, "role": "additional", "role_desc": "Additional coverage"})
            total_dur += c["duration"]

# Re-sort EDL in story order
role_order = {"setup": 0, "scale": 1, "analysis": 2, "lesson": 3, "resilience": 4, "additional": 5}
edl_clips.sort(key=lambda x: role_order.get(x.get("role", "additional"), 99))

# Find hook: single most interesting complete sentence <=8s
hook = None
for c in selected:
    if c["duration"] <= 10:
        hook = c
        break
# If no short candidate, try to extract a sentence from a longer one
if not hook and selected:
    # Just use the first few seconds of the best candidate
    best = selected[0]
    hook = {
        **best,
        "note": "Hook extracted from longer passage - may need trimming to <=8s"
    }

# Build final EDL
edl = {
    "topic": topic["chosen_topic"]["topic"],
    "angle": topic["chosen_topic"]["angle"],
    "hook": {
        "video_id": hook["video_id"] if hook else None,
        "channel": hook["channel"] if hook else None,
        "text": hook["text"][:200] if hook else None,
        "first_word": hook["first_word"] if hook else None,
        "last_word": hook["last_word"] if hook else None,
        "word_start": hook["word_start"] if hook else None,
        "word_end": hook["word_end"] if hook else None,
        "duration": hook["duration"] if hook else None,
        "reason": "Most impactful short statement on the topic"
    },
    "clips": [],
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
        "role": c.get("role", "additional"),
        "reason": c.get("role_desc", ""),
    }
    edl["clips"].append(clip)
    edl["total_clip_duration"] = round(edl["total_clip_duration"] + c["duration"], 2)

print(f"\nFinal EDL: {len(edl['clips'])} clips, {edl['total_clip_duration']:.1f}s total")
print(f"Hook: {edl['hook']['text'][:80]}..." if edl['hook']['text'] else "No hook found")

for clip in edl["clips"]:
    print(f"  #{clip['index']} [{clip['role']}] {clip['channel']} ({clip['duration']:.1f}s): {clip['text'][:80]}...")

with open(OUTPUT_EDL, "w") as f:
    json.dump(edl, f, indent=2)

print(f"\nEDL written to {OUTPUT_EDL}")
print(f"Candidates written to {OUTPUT_CANDIDATES}")
