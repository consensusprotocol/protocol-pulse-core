#!/usr/bin/env python3
"""pipeline/rank.py — K2 stage: download auto-subs, score passages, pick best set.

Takes sources.json, fetches subtitles for top 15 candidates (parallel 6),
scores passages for keyword relevance + statement-ness + specificity,
picks story-coherent set of 3-6 passages from >= 2 distinct channels (M5/R5).

Output: passages.json with ranked passages and chosen set.
"""
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)

# ── Subtitle fetching ──

def _fetch_subs(video_id, run_dir, timeout=30):
    """Download auto-subs for a video. Returns transcript text or None."""
    subs_dir = os.path.join(run_dir, "subs")
    os.makedirs(subs_dir, exist_ok=True)

    out_template = os.path.join(subs_dir, f"{video_id}")
    vtt_path = os.path.join(subs_dir, f"{video_id}.en.vtt")
    json_path = os.path.join(run_dir, "transcripts", f"{video_id}.json")

    # Cache hit: already have word-level transcript
    if os.path.exists(json_path):
        return json_path

    # Cache hit: already have VTT
    if os.path.exists(vtt_path):
        return vtt_path

    cmd = [
        "yt-dlp", "--write-auto-subs", "--sub-lang", "en",
        "--skip-download", "--no-warnings", "--quiet",
        "-o", out_template,
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    cookies = os.path.join(os.path.dirname(PIPELINE_DIR), "data", "yt_cookies.txt")
    if os.path.exists(cookies):
        cmd.extend(["--cookies", cookies])

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if os.path.exists(vtt_path):
        return vtt_path

    # Try .en.vtt variant names
    for ext in [".en.vtt", ".en-orig.vtt", ".en.srt"]:
        p = os.path.join(subs_dir, f"{video_id}{ext}")
        if os.path.exists(p):
            return p

    return None


def _parse_vtt(vtt_path):
    """Parse VTT subtitle file into list of {start, end, text} segments."""
    segments = []
    try:
        with open(vtt_path) as f:
            content = f.read()
    except Exception:
        return segments

    # Parse VTT cue blocks
    blocks = re.split(r"\n\n+", content)
    for block in blocks:
        lines = block.strip().split("\n")
        for i, line in enumerate(lines):
            m = re.match(r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})", line)
            if m:
                start = _vtt_to_seconds(m.group(1))
                end = _vtt_to_seconds(m.group(2))
                text = " ".join(lines[i + 1:]).strip()
                # Remove VTT tags
                text = re.sub(r"<[^>]+>", "", text)
                text = text.strip()
                if text:
                    segments.append({"start": start, "end": end, "text": text})
                break
    return segments


def _vtt_to_seconds(ts):
    """Convert HH:MM:SS.mmm to seconds."""
    parts = ts.split(":")
    h, m = int(parts[0]), int(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s


def _score_passage(text, keyword_terms, is_statement=True):
    """Score a passage for keyword relevance, statement-ness, and specificity."""
    text_lower = text.lower()
    score = 0.0

    # Keyword relevance (0-40 points)
    hits = sum(1 for t in keyword_terms if t in text_lower)
    score += min(40, hits * 10)

    # Statement-ness: penalize questions (R1)
    if text.rstrip().endswith("?"):
        score -= 20

    # Specificity: reward numbers, proper nouns, dollar amounts
    if re.search(r"\$[\d,.]+", text):
        score += 10
    if re.search(r"\d+%", text):
        score += 8
    if re.search(r"\d{4}", text):  # years
        score += 5
    # Count capitalized words (proper nouns) beyond sentence starts
    words = text.split()
    proper_nouns = sum(1 for w in words[1:] if w[0:1].isupper()) if len(words) > 1 else 0
    score += min(10, proper_nouns * 2)

    # Length bonus: 15-60 words ideal for a clip
    word_count = len(words)
    if 15 <= word_count <= 60:
        score += 10
    elif word_count < 8 or word_count > 120:
        score -= 10

    return score


def _find_passages(sub_segments, keyword_terms, min_dur=10.0, max_dur=25.0):
    """Find candidate passages from subtitle segments.

    Returns list of {start, end, text, score, duration} dicts.
    """
    if not sub_segments:
        return []

    # Merge adjacent subtitle lines into longer passages
    merged = []
    current = None
    for seg in sub_segments:
        if current is None:
            current = dict(seg)
            continue
        # Merge if gap < 1.0s and combined duration < max_dur * 1.5
        if seg["start"] - current["end"] < 1.0 and (seg["end"] - current["start"]) < max_dur * 1.5:
            current["end"] = seg["end"]
            current["text"] = current["text"] + " " + seg["text"]
        else:
            merged.append(current)
            current = dict(seg)
    if current:
        merged.append(current)

    # Score each merged passage
    passages = []
    for seg in merged:
        dur = seg["end"] - seg["start"]
        if dur < min_dur or dur > max_dur:
            continue

        score = _score_passage(seg["text"], keyword_terms)
        passages.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"],
            "score": round(score, 1),
            "duration": round(dur, 2),
        })

    passages.sort(key=lambda p: p["score"], reverse=True)
    return passages


def rank_passages(keyword, niche, run_dir):
    """Main entry point: fetch subs, score passages, pick best set.

    Writes passages.json to run_dir.
    Returns True on success (>= 2 channels with usable passages), False otherwise.
    """
    t0 = time.time()
    print(f"\n=== RANK: '{keyword}' ===")

    sources_path = os.path.join(run_dir, "sources.json")
    with open(sources_path) as f:
        sources = json.load(f)

    # Take top 15 by tier
    top = sources[:15]
    print(f"  Fetching subs for {len(top)} candidates...")

    # Parallel subtitle fetch (max 6)
    sub_results = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_subs, s["video_id"], run_dir): s for s in top}
        for future in as_completed(futures):
            src = futures[future]
            result = future.result()
            if result:
                sub_results[src["video_id"]] = {
                    "path": result,
                    "source": src,
                }

    print(f"  Got subs for {len(sub_results)}/{len(top)} videos")

    # Build keyword terms for scoring
    keyword_terms = [t.strip().lower() for t in keyword.split() if len(t.strip()) >= 3]

    # Find and score passages per video
    all_passages = []
    for vid, info in sub_results.items():
        path = info["path"]
        src = info["source"]

        if path.endswith(".vtt") or path.endswith(".srt"):
            sub_segments = _parse_vtt(path)
        elif path.endswith(".json"):
            # Word-level transcript
            with open(path) as f:
                data = json.load(f)
            words = data.get("words", [])
            # Build segments from word groups
            sub_segments = []
            current_text = []
            current_start = None
            for w in words:
                if current_start is None:
                    current_start = w["start"]
                current_text.append(w["word"])
                # Break on sentence endings or every ~10 words
                if (w["word"].rstrip().endswith((".", "!", "?")) or len(current_text) >= 10):
                    sub_segments.append({
                        "start": current_start,
                        "end": w["end"],
                        "text": " ".join(current_text),
                    })
                    current_text = []
                    current_start = None
            if current_text and current_start is not None:
                sub_segments.append({
                    "start": current_start,
                    "end": words[-1]["end"],
                    "text": " ".join(current_text),
                })
        else:
            continue

        passages = _find_passages(sub_segments, keyword_terms)
        for p in passages[:5]:  # Top 5 per video
            p["video_id"] = vid
            p["channel"] = src["channel"]
            p["handle"] = src.get("handle", "")
            p["title"] = src["title"]
            p["tier"] = src.get("tier", 9)
            all_passages.append(p)

    print(f"  Total scored passages: {len(all_passages)}")

    if not all_passages:
        print("  NO usable passages found")
        # Write empty passages.json
        with open(os.path.join(run_dir, "passages.json"), "w") as f:
            json.dump({"passages": [], "chosen": [], "channels": []}, f, indent=2)
        return False

    # Sort by score
    all_passages.sort(key=lambda p: p["score"], reverse=True)

    # Pick story-coherent set: 3-6 passages from >= 2 channels (M5/R5)
    chosen = []
    channels_used = set()

    for p in all_passages:
        if len(chosen) >= 6:
            break
        # Diversity: don't take more than 2 from same channel
        ch_count = sum(1 for c in chosen if c["channel"] == p["channel"])
        if ch_count >= 2:
            continue
        # No temporal overlap with already chosen
        overlap = any(
            c["video_id"] == p["video_id"] and
            not (p["end"] <= c["start"] or p["start"] >= c["end"])
            for c in chosen
        )
        if overlap:
            continue
        chosen.append(p)
        channels_used.add(p["channel"])

    # Verify >= 2 channels
    if len(channels_used) < 2:
        print(f"  Only {len(channels_used)} channel(s) — need >= 2")
        # Try to add from a different channel even if lower score
        for p in all_passages:
            if p["channel"] not in channels_used:
                chosen.append(p)
                channels_used.add(p["channel"])
                break
        if len(channels_used) < 2:
            print("  CANNOT find passages from 2+ channels — STOP")
            with open(os.path.join(run_dir, "passages.json"), "w") as f:
                json.dump({"passages": all_passages[:20], "chosen": chosen,
                           "channels": list(channels_used),
                           "error": f"only {len(channels_used)} channel(s)"}, f, indent=2)
            return False

    # Ensure minimum 3 passages
    if len(chosen) < 3:
        for p in all_passages:
            if p not in chosen:
                chosen.append(p)
                if len(chosen) >= 3:
                    break

    print(f"  Chosen: {len(chosen)} passages from {len(channels_used)} channels")
    for i, p in enumerate(chosen):
        print(f"    [{i+1}] {p['channel']}: {p['text'][:60]}... (score={p['score']})")

    # Write passages.json
    result = {
        "keyword": keyword,
        "passages": all_passages[:30],  # Top 30 for reference
        "chosen": chosen,
        "channels": sorted(channels_used),
    }
    with open(os.path.join(run_dir, "passages.json"), "w") as f:
        json.dump(result, f, indent=2)

    elapsed = time.time() - t0
    print(f"  Rank time: {elapsed:.1f}s")
    return True
