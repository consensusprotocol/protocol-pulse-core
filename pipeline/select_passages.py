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
    # The section start actually requested from yt-dlp (whole seconds) IS the recorded offset
    # (2026-11-11: '*54-100' was requested while 53.57 was recorded). Keyframe/priming can still
    # move the file start by ~0.1 s, so cut words are located by text (sentence_law.anchor), never
    # by offset arithmetic; the offset is provenance only.
    dl_start = float(round(max(0, start_s - pad)))

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


def _generate_vo_script(keyword, hook_text, clips, channels):
    """Generate the default body-VO shape under M20 / Editorial Law 2.

    Commentary must earn its place. AUTO/PIN therefore create no body VO by
    default: no intro and no bridges. A future human/model editorial review may
    explicitly supply body VO with a declared allowed job, which the shared
    pre-render editorial gate must approve. Credits/signoff remain independent
    and are always generated later by signoff.py in the voice stage.
    """
    return {"intro": None, "bridges": []}


def build_vertical_overrides(hook_seg, clip_segs, registry=None):
    """vertical_overrides.json content — default letterbox for all (M21).
    Channels with approved hand tables use those ('crop'); others get letterbox.
    Shared by AUTO (select_and_build_edl) and PINNED (pinned.build_edl)."""
    if registry is None:
        registry = []
        channels_path = os.path.join(PIPELINE_DIR, "channels.json")
        if os.path.exists(channels_path):
            with open(channels_path) as f:
                registry = json.load(f)
    approved_channels = set()
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
    return overrides


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

    # SENTENCE LAW (sentence_law.py): the editor's chosen sentences are located in the downloaded
    # file's own transcript by TEXT, sealed in a selection lock, and both edges must be legal,
    # cuttable sentence boundaries in this file's audio. Nothing is ever picked by nearest word.
    import sentence_law as L
    channels_used = set()
    boundary_report = []
    adj = L.Adjudicator()

    def _build_segment(passage, label):
        vid = passage["video_id"]
        words = transcripts[vid].get("words", [])
        offset = offsets.get(vid, 0)
        tpath = os.path.join(run_dir, "transcripts", f"{vid}.json")
        rec = {"segment": label, "video_id": vid, "channel": passage["channel"],
               "window_full_video_s": [passage["start"], passage["end"]], "selected_text": passage["text"]}
        boundary_report.append(rec)
        a = L.anchor(words, passage["text"], t0=passage["start"] - offset - 5.0,
                     t1=passage["end"] - offset + 5.0)
        if a is None:
            rec["result"] = "rejected: selected text not found in this file's transcript"
            return None
        i0, i1, ratio = a
        lock = L.make_lock(vid, words, i0, i1, L.sha256_file(tpath), passage["text"],
                           [passage["start"], passage["end"]], ratio, "select_passages")
        plan = L.edge_plan(L.SourceAudio(sources[vid]), words, i0, i1, adj, context=f"select {label}")
        rec.update(locked=f"'{lock['first_word']}' ... '{lock['last_word']}'", align_ratio=ratio,
                   **{f"{s}_edge": {k: plan[s].get(k) for k in ("valid", "cuttable", "pause", "lexical", "reason",
                                                                 "cut_lo", "cut_hi", "lead_in_pad_s")}
                      for s in ("in", "out")})
        if not plan["ok"]:
            rec["result"] = "rejected: " + "; ".join(
                f"{s.upper()} {plan[s].get('reason') or 'not cuttable'}" for s in ("in", "out")
                if not plan[s].get("cuttable"))
            return None
        rec["result"] = "accepted"
        channels_used.add(passage["channel"])
        # EDL times are SOURCE-FILE coordinates (sources/<vid>.mp4); the offset is provenance only.
        return {
            "video_id": vid,
            "channel": passage["channel"],
            "handle": passage.get("handle", ""),
            "video_title": passage.get("title", ""),
            "text": passage["text"],
            "first_word": lock["first_word"],
            "last_word": lock["last_word"],
            "word_start": round(words[i0]["start"], 3),
            "word_end": round(words[i1]["end"], 3),
            "duration": round(words[i1]["end"] - words[i0]["start"], 2),
            "time_coords": "source_file",
            "source_window_offset_s": round(offset, 3),
            "selection_lock": lock,
        }

    try:
        hook_seg = _build_segment(hook, "hook")
        clip_segs = []
        if hook_seg is not None:
            for i, clip in enumerate(clips):
                seg = _build_segment(clip, f"clip_{i+1:02d}")
                if seg:
                    seg["index"] = len(clip_segs) + 1
                    clip_segs.append(seg)
    finally:
        adj.close()
        with open(os.path.join(run_dir, "SELECT_BOUNDARIES.json"), "w") as f:
            json.dump(boundary_report, f, indent=2)
    for r in boundary_report:
        print(f"    {r['segment']} {r['channel']}: {r['result']}")
    if hook_seg is None:
        print("  Cannot build hook segment (sentence law) — STOP")
        return False
    if len(clip_segs) < 1:
        print("  No valid clip segments (sentence law) — STOP")
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

    overrides = build_vertical_overrides(hook_seg, clip_segs)

    overrides_path = os.path.join(run_dir, "vertical_overrides.json")
    with open(overrides_path, "w") as f:
        json.dump(overrides, f, indent=2)

    elapsed = time.time() - t0
    print(f"  EDL built: hook + {len(clip_segs)} clips from {len(channels_used)} channels")
    print(f"  Total clip duration: {total_dur:.1f}s")
    print(f"  Select time: {elapsed:.1f}s")
    return True
