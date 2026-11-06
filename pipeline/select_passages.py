#!/usr/bin/env python3
"""pipeline/select_passages.py — K3 stage: build EDL from ranked passages.

Takes passages.json, downloads the chosen video windows,
runs faster-whisper for word-level timestamps,
builds edl.json with hook + clips + VO script (M20 commentary rules).

M20: Commentary must earn its place — no bridge that restates a clip.
     Zero bridges allowed. Intro only if the hook needs framing.
     Sign-off always (signoff.py).
"""
import json
import os
import re
import subprocess
import sys
import time

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)


def _download_window(video_id, start_s, end_s, run_dir, pad=15.0):
    """Download a specific time window from a YouTube video.

    Uses yt-dlp --download-sections for precise extraction.
    Returns (path, dl_start) tuple or (None, 0).
    dl_start is the offset in the original video that t=0 in the downloaded file maps to.
    """
    sources_dir = os.path.join(run_dir, "sources")
    os.makedirs(sources_dir, exist_ok=True)

    out_path = os.path.join(sources_dir, f"{video_id}.mp4")
    dl_start = max(0, start_s - pad)

    if os.path.exists(out_path) and os.path.getsize(out_path) > 100_000:
        return out_path, dl_start  # Cache hit

    dl_end = end_s + pad

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--download-sections", f"*{dl_start:.0f}-{dl_end:.0f}",
        "--merge-output-format", "mp4",
        "-o", out_path,
        "--no-warnings", "--quiet",
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    cookies = os.path.join(os.path.dirname(PIPELINE_DIR), "data", "yt_cookies.txt")
    if os.path.exists(cookies):
        cmd.extend(["--cookies", cookies])

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"    WARN: download timeout for {video_id}")
        return None

    if os.path.exists(out_path) and os.path.getsize(out_path) > 10_000:
        return out_path, dl_start
    return None, 0


def _whisper_transcribe(source_path, video_id, run_dir):
    """Run faster-whisper on a source file for word-level timestamps.

    Returns dict with 'words' list or None on failure.
    """
    transcript_path = os.path.join(run_dir, "transcripts", f"{video_id}.json")
    if os.path.exists(transcript_path):
        with open(transcript_path) as f:
            return json.load(f)

    os.makedirs(os.path.join(run_dir, "transcripts"), exist_ok=True)

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
        segments, info = model.transcribe(
            source_path, language="en", beam_size=5,
            word_timestamps=True, vad_filter=False,
        )

        words = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 3),
                    })

        result = {"words": words, "language": info.language,
                  "duration": info.duration}
        with open(transcript_path, "w") as f:
            json.dump(result, f, indent=2)
        return result

    except Exception as e:
        print(f"    WARN: whisper failed for {video_id}: {e}")
        return None


def _find_word_boundaries(words, start_s, end_s, text_hint=None, min_dur=8.0):
    """Find the best first_word and last_word within a passage time range.

    Widens the search window to ensure clips meet min_dur.
    Returns (first_word, last_word, word_start, word_end) or None.
    """
    # Widen search window: use a generous margin around the passage
    margin = 3.0
    window_words = [w for w in words
                    if w["start"] >= start_s - margin and w["end"] <= end_s + margin]
    if not window_words:
        # Try even wider — use ALL words
        window_words = words
    if not window_words:
        return None

    # First word: closest to start_s, but must be a sentence start if possible
    # Look for words near start_s that begin a sentence (after a period)
    first = min(window_words, key=lambda w: abs(w["start"] - start_s))

    # Last word: find sentence-ending word that gives us >= min_dur
    min_end_time = first["start"] + min_dur
    sentence_enders = [w for w in window_words
                       if w["word"].rstrip().endswith((".", "!", "?"))
                       and w["end"] >= min_end_time
                       and w["end"] <= end_s + margin]
    if sentence_enders:
        # Pick the one closest to end_s
        last = min(sentence_enders, key=lambda w: abs(w["end"] - end_s))
    else:
        # No sentence ender meeting min_dur: pick the latest word in range
        candidates = [w for w in window_words if w["end"] >= min_end_time]
        if candidates:
            last = max(candidates, key=lambda w: w["end"])
        else:
            last = max(window_words, key=lambda w: w["end"])

    # Verify minimum duration
    dur = last["end"] - first["start"]
    if dur < min_dur and len(window_words) > 5:
        # Expand: take first word and the last sentence ender that gives >= min_dur
        all_enders = [w for w in words if w["word"].rstrip().endswith((".", "!", "?"))
                      and w["end"] >= first["start"] + min_dur]
        if all_enders:
            last = min(all_enders, key=lambda w: w["end"])

    return first["word"], last["word"], first["start"], last["end"]


def _generate_vo_script(keyword, hook_text, clips, channels):
    """Generate VO script following M20 rules.

    M20: Commentary must earn its place.
    - Zero bridges allowed
    - Intro only if the hook needs framing
    - Sign-off always via signoff.py
    """
    # Intro: brief framing only if needed (< 15 words)
    intro = None
    hook_lower = hook_text.lower()
    # If the hook is self-explanatory (mentions the keyword), skip intro
    keyword_terms = [t.lower() for t in keyword.split() if len(t) >= 3]
    hook_has_keyword = any(t in hook_lower for t in keyword_terms)
    if not hook_has_keyword:
        intro = f"This story is unfolding right now."

    # No bridges per M20
    bridges = []

    # Sign-off: generated via signoff.py at voice stage
    channel_names = [c for c in channels]

    vo = {"intro": intro, "bridges": bridges}
    return vo


def select_and_build_edl(keyword, niche, run_dir):
    """Main entry point: download windows, transcribe, build EDL.

    Writes edl.json and vertical_overrides.json.
    Returns True on success, False on failure.
    """
    t0 = time.time()
    print(f"\n=== SELECT: '{keyword}' ===")

    passages_path = os.path.join(run_dir, "passages.json")
    with open(passages_path) as f:
        data = json.load(f)

    chosen = data.get("chosen", [])
    if len(chosen) < 2:
        print("  Not enough passages chosen — STOP")
        return False

    # Download video windows for each unique video_id
    video_ids = list(set(p["video_id"] for p in chosen))
    print(f"  Downloading {len(video_ids)} source windows...")

    sources = {}  # vid -> path
    offsets = {}   # vid -> dl_start offset (t=0 in file = dl_start in original)
    for vid in video_ids:
        # Find time range for this video across all chosen passages
        vid_passages = [p for p in chosen if p["video_id"] == vid]
        min_start = min(p["start"] for p in vid_passages)
        max_end = max(p["end"] for p in vid_passages)
        result = _download_window(vid, min_start, max_end, run_dir)
        if result and result[0]:
            path, dl_start = result
            sources[vid] = path
            offsets[vid] = dl_start
            print(f"    {vid}: downloaded (offset={dl_start:.0f}s)")
        else:
            print(f"    {vid}: FAILED")

    if len(sources) < 2:
        print("  Not enough sources downloaded — STOP")
        return False

    # Transcribe each source with faster-whisper
    print(f"  Transcribing {len(sources)} sources...")
    transcripts = {}
    for vid, path in sources.items():
        result = _whisper_transcribe(path, vid, run_dir)
        if result:
            transcripts[vid] = result
            print(f"    {vid}: {len(result.get('words', []))} words")
        else:
            print(f"    {vid}: FAILED")

    # Filter chosen passages to those with successful downloads + transcripts
    valid = [p for p in chosen if p["video_id"] in sources and p["video_id"] in transcripts]
    if len(valid) < 2:
        print("  Not enough valid passages — STOP")
        return False

    # Pick hook: shortest passage with highest score, must be a statement
    hook_candidates = [p for p in valid if p["duration"] <= 12.0 and
                       not p["text"].rstrip().endswith("?")]
    if not hook_candidates:
        hook_candidates = sorted(valid, key=lambda p: p["duration"])[:1]

    hook = max(hook_candidates, key=lambda p: p["score"]) if hook_candidates else valid[0]
    clips = [p for p in valid if p is not hook][:5]  # Max 5 clips

    # Build word boundaries from transcripts
    channels_used = set()

    def _build_segment(passage, label):
        vid = passage["video_id"]
        words = transcripts[vid].get("words", [])
        offset = offsets.get(vid, 0)
        # Passage times are in full-video coords; whisper times are in local (downloaded) coords
        # local_time = full_video_time - offset
        local_start = passage["start"] - offset
        local_end = passage["end"] - offset
        bounds = _find_word_boundaries(words, local_start, local_end)
        if bounds is None:
            return None
        first_word, last_word, word_start, word_end = bounds
        # EDL times stay in SOURCE-FILE coordinates (the downloaded window):
        # cut.py and the clip pre-render seek into sources/<vid>.mp4, and the
        # whisper words are measured on that same file. The window offset is
        # recorded for provenance only (fresh-topic generalization B).
        word_start_abs = word_start
        word_end_abs = word_end
        channels_used.add(passage["channel"])
        return {
            "video_id": vid,
            "channel": passage["channel"],
            "handle": passage.get("handle", ""),
            "video_title": passage.get("title", ""),
            "text": passage["text"],
            "first_word": first_word,
            "last_word": last_word,
            "word_start": round(word_start_abs, 3),
            "word_end": round(word_end_abs, 3),
            "duration": round(word_end - word_start, 2),
            "time_coords": "source_file",
            "source_window_offset_s": round(offset, 3),
        }

    hook_seg = _build_segment(hook, "hook")
    if hook_seg is None:
        print("  Cannot build hook segment — STOP")
        return False

    clip_segs = []
    for i, clip in enumerate(clips):
        seg = _build_segment(clip, f"clip_{i+1:02d}")
        if seg:
            seg["index"] = i + 1
            clip_segs.append(seg)

    if len(clip_segs) < 1:
        print("  No valid clip segments — STOP")
        return False

    # Generate VO script (M20 rules)
    vo = _generate_vo_script(keyword, hook_seg["text"], clip_segs, sorted(channels_used))

    # Build EDL
    total_dur = hook_seg["duration"] + sum(c["duration"] for c in clip_segs)
    edl = {
        "topic": keyword,
        "angle": f"Keyword search: {keyword}",
        "hook": hook_seg,
        "clips": clip_segs,
        "vo": vo,
        "total_clip_duration": round(total_dur, 2),
    }

    edl_path = os.path.join(run_dir, "edl.json")
    with open(edl_path, "w") as f:
        json.dump(edl, f, indent=2)

    # Build vertical_overrides.json — default letterbox for all (M21)
    # Channels with approved hand tables use those; others get letterbox
    channels_path = os.path.join(PIPELINE_DIR, "channels.json")
    approved_channels = set()
    if os.path.exists(channels_path):
        with open(channels_path) as f:
            registry = json.load(f)
        for ch in registry:
            if ch.get("layout_status") == "approved":
                approved_channels.add(ch.get("display_name", ""))

    overrides = {}
    for seg in [hook_seg] + clip_segs:
        label = "hook" if seg is hook_seg else f"clip_{seg['index']:02d}"
        if seg["channel"] in approved_channels:
            overrides[label] = {"layout": "crop"}  # Use approved layout
        else:
            overrides[label] = {"layout": "letterbox"}  # M21

    overrides_path = os.path.join(run_dir, "vertical_overrides.json")
    with open(overrides_path, "w") as f:
        json.dump(overrides, f, indent=2)

    elapsed = time.time() - t0
    print(f"  EDL built: hook + {len(clip_segs)} clips from {len(channels_used)} channels")
    print(f"  Total clip duration: {total_dur:.1f}s")
    print(f"  Select time: {elapsed:.1f}s")
    return True
