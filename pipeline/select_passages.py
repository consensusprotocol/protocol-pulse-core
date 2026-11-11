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
import sentence_law as L  # noqa: E402  (selection locks, boundary rule)


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
    """Run faster-whisper on a source file for word-level timestamps (verbatim decode). Where that
    decode has no punctuation, sentence punctuation is added from a prompted reference decode of the
    same audio, onto aligned words only (pipeline/punctuation.py; the words never change).

    Returns dict with 'words' list or None on failure.
    """
    import punctuation
    transcript_path = os.path.join(run_dir, "transcripts", f"{video_id}.json")
    os.makedirs(os.path.join(run_dir, "transcripts"), exist_ok=True)

    try:
        result = None
        if os.path.exists(transcript_path):
            with open(transcript_path) as f:
                result = json.load(f)
            if result.get("punctuation") or not punctuation.needs_restoration(result.get("words", [])):
                return result

        from faster_whisper import WhisperModel
        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
        if result is None:
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
        result = punctuation.ensure(result, source_path, model, model_name="large-v3")
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
    """vertical_overrides.json content. DEC-5 (orchestrator, delegated by PBX, 2026-11-11): every
    segment, approved or pending channel, gets layout 'auto' - the approved speaker-centred reframe,
    stacked bands for 2-3 people, the safe frame only for a shared screen or an unidentifiable speaker
    (flagged). The per-shot plan is measured on the prepared clip in run_fresh's 'layout' stage
    (vertical_layout.py). M21's letterbox-by-registry-status default is retired. `registry` is kept
    for call compatibility. Shared by AUTO (select_and_build_edl) and PINNED (pinned.build_edl)."""
    overrides = {}
    for seg in [hook_seg] + clip_segs:
        label = "hook" if seg is hook_seg else f"clip_{seg['index']:02d}"
        overrides[label] = {"layout": "auto"}
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

    if all(p.get("kind") in ("hook", "clip") for p in valid):
        # 1d (2026-11-11): the editor's slots are kept; a rejected slot is refilled from the ranking
        hook = next((p for p in valid if p["kind"] == "hook"), None)
        clips = [p for p in valid if p["kind"] == "clip"]
    else:
        # legacy passages.json without slot kinds: shortest statement with the highest score
        hook_candidates = [p for p in valid if p["duration"] <= 12.0 and
                           not p["text"].rstrip().endswith("?")]
        if not hook_candidates:
            hook_candidates = sorted(valid, key=lambda p: p["duration"])[:1]
        hook = max(hook_candidates, key=lambda p: p["score"]) if hook_candidates else valid[0]
        clips = [p for p in valid if p is not hook][:5]  # Max 5 clips

    # SENTENCE LAW (sentence_law.py): the editor's chosen sentences are located in the downloaded
    # file's own transcript by TEXT, sealed in a selection lock, and both edges must be legal,
    # cuttable sentence boundaries in this file's audio. Nothing is ever picked by nearest word.
    channels_used = set()
    boundary_report = []

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
        plan = L.edge_plan(L.SourceAudio(sources[vid]), words, i0, i1)
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

    # Next-ranked fallback (mission 1b/1d): a window the sentence law rejects is replaced by the
    # best-ranked legal candidate of the same kind from the editor's shortlist (score floor, duration
    # budget, no overlap, <= 2 clips per channel, <= 2 windows per video), never by moving a cut.
    from editorial_select import (HOOK_MIN_S, HOOK_MAX_S, CLIP_MIN_S, CLIP_MAX_S, HOOK_MIN_SCORE,
                                  CLIP_MIN_SCORE, MAX_VERIFIED_QUOTES_PER_VIDEO)
    pool = [p for p in data.get("passages", []) if p.get("kind") in ("hook", "clip")]
    used, tried = [], set()

    def _key(p):
        return (p["video_id"], round(p["start"], 2), round(p["end"], 2))

    def _budget(kind):
        return (HOOK_MIN_S, HOOK_MAX_S) if kind == "hook" else (CLIP_MIN_S, CLIP_MAX_S)

    def _conflicts(p, kind):
        """Overlap / per-video / per-channel conflicts with windows already used (also applied to the
        editor's own candidate: an earlier fallback may have taken its window, 1d audit)."""
        if _key(p) in tried:
            return True
        if any(u["video_id"] == p["video_id"] and not (p["end"] <= u["start"] or p["start"] >= u["end"]) for u in used):
            return True
        if sum(1 for u in used if u["video_id"] == p["video_id"]) >= MAX_VERIFIED_QUOTES_PER_VIDEO:
            return True
        return kind != "hook" and sum(1 for u in used[1:] if u["channel"] == p["channel"]) >= 2

    def _eligible(p, kind):
        lo, hi = _budget(kind)
        floor = HOOK_MIN_SCORE if kind == "hook" else CLIP_MIN_SCORE
        if p.get("kind") != kind or (p.get("clip_score") or 0) < floor:
            return False
        return lo <= p["end"] - p["start"] <= hi and not _conflicts(p, kind)

    def _source_for(p):
        vid = p["video_id"]
        if vid not in sources:
            res = _download_window(vid, p["start"], p["end"], run_dir)
            if not res or not res[0]:
                return "download failed"
            sources[vid], offsets[vid] = res
            tr = _whisper_transcribe(sources[vid], vid, run_dir)
            if not tr:
                return "transcription failed"
            transcripts[vid] = tr
        span = transcripts[vid].get("duration") or 0
        if span and not (offsets[vid] + 1.0 <= p["start"] and p["end"] <= offsets[vid] + span - 1.0):
            return "outside the downloaded window"
        return None

    def _fill(first, label, kind, slot):
        for p in [first] + sorted([q for q in pool if q is not first],
                                  key=lambda q: (-(q.get("clip_score") or 0), -(q.get("relevance") or 0))):
            # the editor's own pick is checked too: an earlier slot's fallback may already have taken
            # this window (it would be cut twice); fallbacks also pass the score and budget filters
            if p is None or (p is first and _conflicts(p, kind)) or (p is not first and not _eligible(p, kind)):
                continue
            tried.add(_key(p))
            why = _source_for(p)
            if why:
                boundary_report.append({"segment": label, "slot": slot, "video_id": p["video_id"], "channel": p["channel"],
                                        "window_full_video_s": [p["start"], p["end"]],
                                        "result": f"rejected: {why}", "fallback": p is not first})
                continue
            seg = _build_segment(p, label)
            boundary_report[-1].update(fallback=p is not first, slot=slot)
            lo, hi = _budget(kind)
            if seg is not None and not lo <= seg["duration"] <= hi:
                # the budget holds for the clip actually cut (this file's words), not the declared window
                boundary_report[-1]["result"] = (f"rejected: locked words span {seg['duration']} s, outside the "
                                                 f"{kind} budget {lo}-{hi} s")
                seg = None
            if seg is not None:
                used.append(p)
                return seg
        return None

    try:
        hook_seg = _fill(hook, "hook", "hook", 0)
        clip_segs = []
        if hook_seg is not None:
            for k, clip in enumerate(clips, 1):
                seg = _fill(clip, f"clip_{len(clip_segs) + 1:02d}", "clip", k)
                if seg:
                    seg["index"] = len(clip_segs) + 1
                    clip_segs.append(seg)
    finally:
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
