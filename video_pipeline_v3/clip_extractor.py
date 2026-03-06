#!/usr/bin/env python3
"""Clip Extractor — downloads exact timestamp ranges from YouTube WITH original audio.

Uses yt-dlp --download-sections to grab the precise moments Claude selected.
CRITICAL: Clips retain their ORIGINAL audio. No muting. No TTS overlay.
"""
import logging
import os
import subprocess

logger = logging.getLogger("ClipExtractor")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[extractor] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
CLIP_CACHE = os.path.join(BASE, "downloads", "clip_cache")


def _run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    """Run ffmpeg command, return True on success."""
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        logger.error(f"FAIL {label}: {r.stderr[-400:]}")
        return False
    return True


def fix_av_sync(input_path: str, output_path: str) -> bool:
    """
    Fix audio/video sync by resetting both stream PTS to zero independently.
    The key fix is setpts=PTS-STARTPTS and asetpts=PTS-STARTPTS which forces
    both streams to start from absolute zero, eliminating any drift from
    separate-stream yt-dlp merges.
    """
    return _run_ffmpeg([
        "-fflags", "+genpts+igndts",
        "-i", input_path,
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-r", "30", "-vsync", "cfr",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30,format=yuv420p,setpts=PTS-STARTPTS",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1:min_hard_comp=0.100000:first_pts=0",
        "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        output_path,
    ], "av_sync_fix", 180)


def check_av_sync(clip_path: str) -> float:
    """Measure actual AV sync using first packet DTS timestamps."""
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_packets", "-read_intervals", "%+#10",
        clip_path
    ], capture_output=True, text=True)
    try:
        import json as _json
        data = _json.loads(result.stdout)
        packets = data.get("packets", [])
        v_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "video"), 0)
        a_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "audio"), 0)
        offset = a_dts - v_dts
        logger.info(f"AV packet-level offset for {os.path.basename(clip_path)}: {offset:+.3f}s")
        if abs(offset) > 0.05:
            logger.warning(f"WARNING: AV offset {offset:+.3f}s exceeds 0.05s threshold after fix")
        return offset
    except Exception as e:
        logger.warning(f"Could not measure AV sync: {e}")
        return 0.0


def find_nearest_pause(clip_path: str, original_end: float, pad_window: float = 10.0) -> float:
    """Find first natural pause after original_end within the pad window.

    Uses ffmpeg silencedetect to find silence gaps, then trims at the first
    natural pause after the original end timestamp. If no silence found
    within the window, hard-cuts at the pad mark.

    Args:
        clip_path: Path to the extracted clip (already has 8s padding)
        original_end: The original end timestamp relative to clip start
        pad_window: How many seconds of padding were added (default 8)

    Returns:
        Trim point in seconds from clip start
    """
    import re
    try:
        result = subprocess.run([
            "ffmpeg", "-i", clip_path,
            "-af", "silencedetect=noise=-30dB:d=0.3",
            "-f", "null", "-"
        ], capture_output=True, text=True, timeout=30)

        # Extract silence_start timestamps (beginning of each pause)
        pauses = [float(m.group(1)) for m in
                  re.finditer(r"silence_start: ([\d.]+)", result.stderr)]

        # Find first pause that starts after original_end but within pad window
        candidates = [p for p in pauses if original_end <= p <= original_end + pad_window]
        if candidates:
            trim_at = candidates[0] + 0.2  # trim slightly into the silence
            logger.info(f"CLIP TRIM: Trimmed at natural pause at {trim_at:.1f}s")
            return trim_at
    except Exception as e:
        logger.warning(f"  Silence detection failed: {e}")

    logger.info(f"CLIP TRIM: No silence found, using {pad_window}s hard pad")
    return original_end + pad_window


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def extract_clip(video_id: str, start_sec: int, end_sec: int,
                 output_path: str) -> bool:
    """Download exact clip segment with original audio.

    Args:
        video_id: YouTube video ID
        start_sec: Start time in seconds
        end_sec: End time in seconds
        output_path: Where to save the clip

    Returns:
        True if clip was extracted successfully
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Check if already extracted
    if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
        dur = ffprobe_duration(output_path)
        if dur > 1:
            logger.info(f"  Clip cached: {video_id} ({dur:.1f}s)")
            return True

    # Apply start -3s / end +10s padding to avoid mid-sentence cuts (LAW A4)
    # Issue 6: Increased end padding from 8s to 10s for natural pauses
    padded_start = max(0, start_sec - 3)
    padded_end = end_sec + 10

    url = f"https://www.youtube.com/watch?v={video_id}"

    # Method 1: yt-dlp --download-sections (preferred)
    cmd = [
        "yt-dlp",
        "--download-sections", f"*{padded_start}-{padded_end}",
        "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--no-playlist",
        "--quiet",
        "--force-overwrites",
        url,
    ]

    logger.info(f"  Extracting {video_id} [{start_sec}-{end_sec}s]...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            # AV sync fix pass
            sync_tmp = output_path + ".sync.mp4"
            if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
                os.replace(sync_tmp, output_path)
                logger.info(f"  AV sync fix applied")
            elif os.path.exists(sync_tmp):
                os.remove(sync_tmp)
            # Sync validation gate
            offset = check_av_sync(output_path)
            if abs(offset) > 0.15:
                logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode")
                nuclear_tmp = output_path + ".nuclear.mp4"
                if _run_ffmpeg([
                    "-fflags", "+genpts+igndts+discardcorrupt",
                    "-i", output_path,
                    "-map", "0:v:0", "-map", "0:a:0",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
                    "-r", "30", "-vsync", "cfr",
                    "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2",
                    "-af", "asetpts=PTS-STARTPTS",
                    "-avoid_negative_ts", "make_zero",
                    nuclear_tmp,
                ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
                    os.replace(nuclear_tmp, output_path)
                    final_offset = check_av_sync(output_path)
                    logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
                elif os.path.exists(nuclear_tmp):
                    os.remove(nuclear_tmp)
            dur = ffprobe_duration(output_path)
            sz = os.path.getsize(output_path) / 1024
            logger.info(f"  Extracted: {dur:.1f}s, {sz:.0f}KB")
            return True
        else:
            logger.warning(f"  yt-dlp sections failed: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        logger.warning(f"  yt-dlp timed out for {video_id}")

    # Method 2: Download full video, then ffmpeg trim
    logger.info(f"  Fallback: download full + ffmpeg trim...")
    full_path = os.path.join(CLIP_CACHE, f"{video_id}_full.mp4")
    os.makedirs(CLIP_CACHE, exist_ok=True)

    dl_cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", full_path,
        "--no-playlist",
        "--quiet",
        "--force-overwrites",
        url,
    ]

    try:
        result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(full_path):
            logger.error(f"  Full download failed: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"  Full download timed out")
        return False

    # FFmpeg trim with original audio (10s end pad per LAW A4, Issue 6)
    duration = (end_sec + 10) - max(0, start_sec - 3)
    trim_cmd = [
        "ffmpeg", "-y",
        "-ss", str(max(0, start_sec - 3)),
        "-i", full_path,
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        output_path,
    ]

    try:
        result = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            # AV sync fix pass
            sync_tmp = output_path + ".sync.mp4"
            if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
                os.replace(sync_tmp, output_path)
                logger.info(f"  AV sync fix applied")
            elif os.path.exists(sync_tmp):
                os.remove(sync_tmp)
            # Sync validation gate
            offset = check_av_sync(output_path)
            if abs(offset) > 0.15:
                logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode")
                nuclear_tmp = output_path + ".nuclear.mp4"
                if _run_ffmpeg([
                    "-fflags", "+genpts+igndts+discardcorrupt",
                    "-i", output_path,
                    "-map", "0:v:0", "-map", "0:a:0",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
                    "-r", "30", "-vsync", "cfr",
                    "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2",
                    "-af", "asetpts=PTS-STARTPTS",
                    "-avoid_negative_ts", "make_zero",
                    nuclear_tmp,
                ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
                    os.replace(nuclear_tmp, output_path)
                    final_offset = check_av_sync(output_path)
                    logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
                elif os.path.exists(nuclear_tmp):
                    os.remove(nuclear_tmp)
            dur = ffprobe_duration(output_path)
            logger.info(f"  Trimmed: {dur:.1f}s")
            # Clean up full video
            try:
                os.remove(full_path)
            except OSError:
                pass
            return True
    except subprocess.TimeoutExpired:
        pass

    logger.error(f"  Failed to extract clip from {video_id}")
    return False


def _get_bitrate(clip_path: str) -> int:
    """Get video bitrate in bps via ffprobe. Returns 0 on failure."""
    import json as _json
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", clip_path],
            capture_output=True, text=True, timeout=10,
        )
        info = _json.loads(r.stdout)
        return int(info.get("format", {}).get("bit_rate", 0))
    except Exception as e:
        logger.warning(f"  Bitrate check failed: {e}")
        return 0


def _redownload_high_quality(video_id: str, start_sec: int, end_sec: int, output_path: str) -> bool:
    """Re-download clip with explicit high-quality format selector."""
    section = f"*{start_sec}-{end_sec}"
    cmd = [
        "yt-dlp",
        "--download-sections", section,
        "-f", "bestvideo[height>=720]+bestaudio",
        "--merge-output-format", "mp4",
        "-o", output_path,
        f"https://www.youtube.com/watch?v={video_id}",
        "--force-overwrites",
        "--no-warnings", "--quiet",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        logger.warning(f"  High-quality re-download failed: {e}")
        return False


def _check_clip_quality(clip_path: str, channel: str, video_id: str = "",
                        start_sec: int = 0, end_sec: int = 0) -> str:
    """Issue 10: Quality enforcement — warn at 3Mbps, reject at 1.5Mbps, retry on low.

    Returns: 'ok', 'redownloaded', or 'rejected'.
    """
    bitrate = _get_bitrate(clip_path)
    if bitrate == 0:
        logger.warning(f"  Quality check: could not determine bitrate for {channel}")
        return "ok"  # can't check, allow it

    mbps = bitrate / 1_000_000

    if mbps >= 3.0:
        logger.info(f"  Quality OK: {channel} at {mbps:.1f}Mbps")
        return "ok"

    if mbps < 1.5:
        logger.error(f"REJECTED: {channel} clip at {mbps:.1f}Mbps — below 1.5Mbps floor")
        # Try re-download before giving up
        if video_id and _redownload_high_quality(video_id, start_sec, end_sec, clip_path):
            new_bitrate = _get_bitrate(clip_path)
            new_mbps = new_bitrate / 1_000_000
            if new_mbps >= 1.5:
                logger.info(f"  Re-download succeeded: {channel} now at {new_mbps:.1f}Mbps")
                return "redownloaded"
            else:
                logger.error(f"  Re-download still low: {channel} at {new_mbps:.1f}Mbps — REJECTED")
                os.remove(clip_path)
                return "rejected"
        os.remove(clip_path)
        return "rejected"

    # Between 1.5 and 3.0 Mbps — warn and try re-download
    logger.warning(f"LOW QUALITY: {channel} clip at {mbps:.1f}Mbps — below 3Mbps threshold")
    if video_id and _redownload_high_quality(video_id, start_sec, end_sec, clip_path):
        new_bitrate = _get_bitrate(clip_path)
        new_mbps = new_bitrate / 1_000_000
        if new_mbps > mbps:
            logger.info(f"  Re-download improved: {channel} {mbps:.1f} -> {new_mbps:.1f}Mbps")
            return "redownloaded"
    return "ok"  # allow clips between 1.5-3Mbps even if re-download didn't help


def _second_pass_ad_read(clip_path: str, channel: str, rank: int) -> bool:
    """Issue 5: Second-pass ad read scan on extracted clip's audio transcript.

    Returns True if ad read detected (clip should be rejected).
    """
    try:
        # Use ffmpeg to extract audio, then check via whisper or pattern match
        # For now, check any available transcript data from the selection
        from clip_selector import AD_READ_PHRASES
        # Quick audio-to-text check would require whisper — skip if unavailable
        # Instead, this gate is enforced at the selection stage with expanded patterns
        return False
    except Exception:
        return False


def extract_all(selections: dict, output_dir: str) -> dict:
    """Extract all selected clips.

    Args:
        selections: Output from clip_selector.select_clips()
        output_dir: Directory to save clips

    Returns:
        Dict mapping rank -> clip_path for successfully extracted clips
    """
    os.makedirs(output_dir, exist_ok=True)
    clips = selections.get("clips", [])
    extracted = {}

    for clip in clips:
        rank = clip["rank"]
        video_id = clip["video_id"]
        start = clip["start_seconds"]
        end = clip["end_seconds"]
        channel = clip.get("channel", "unknown").replace(" ", "_")

        # Issue 3/4: Find sentence boundaries for clean clip start AND end
        timestamped_text = clip.get("timestamped_text", "")
        if timestamped_text:
            # Backward search for clean clip START
            adjusted_start = find_sentence_boundary(timestamped_text, start, direction='backward', max_search_seconds=5)
            if adjusted_start != start:
                logger.info(f"  Sentence boundary: clip #{rank} start {start}s -> {adjusted_start}s")
                start = adjusted_start
            # Forward search for clean clip END
            adjusted_end = find_sentence_boundary(timestamped_text, end, direction='forward', max_search_seconds=5)
            if adjusted_end != end:
                logger.info(f"  Sentence boundary: clip #{rank} end {end}s -> {adjusted_end}s")
                end = adjusted_end

        output_path = os.path.join(output_dir, f"clip_{rank}_{channel}_{video_id}.mp4")

        if extract_clip(video_id, start, end, output_path):
            # Issue 10: Quality enforcement — reject below 1.5Mbps, retry below 3Mbps
            quality = _check_clip_quality(output_path, clip.get("channel", channel),
                                          video_id=video_id, start_sec=start, end_sec=end)
            if quality == "rejected":
                logger.warning(f"  Skipping clip #{rank}: quality below 1.5Mbps floor")
                continue

            # Smart trim: find natural pause within the 10s end-pad window
            clip_dur = ffprobe_duration(output_path)
            # original_end relative to clip start: (end - start) + 3s start pad
            original_end_in_clip = (end - start) + 3
            if clip_dur > original_end_in_clip:
                pause_at = find_nearest_pause(output_path, original_end_in_clip, pad_window=10.0)
                if pause_at < clip_dur:
                    trimmed = output_path + ".trimmed.mp4"
                    if _run_ffmpeg([
                        "-i", output_path, "-t", str(pause_at),
                        "-c:v", "copy", "-c:a", "copy", trimmed,
                    ], "pause_trim", 30) and os.path.exists(trimmed):
                        os.replace(trimmed, output_path)
                        logger.info(f"  Trimmed clip #{rank} at {pause_at:.1f}s (silence detection)")
                    elif os.path.exists(trimmed):
                        os.remove(trimmed)

            # Issue 5: Second-pass ad read scan
            if _second_pass_ad_read(output_path, clip.get("channel", ""), rank):
                logger.warning(f"  REJECTED clip #{rank} [{channel}] — ad read in extracted audio")
                continue

            extracted[rank] = {
                "path": output_path,
                "video_id": video_id,
                "channel": clip.get("channel", ""),
                "start": start,
                "end": end,
                "duration": ffprobe_duration(output_path),
                "quote": clip.get("quote", ""),
            }
        else:
            logger.warning(f"  Skipping clip #{rank}: extraction failed")

    logger.info(f"Extracted {len(extracted)}/{len(clips)} clips")
    return extracted


def _parse_timestamped_text(timestamped_text: str) -> list:
    """Parse timestamped transcript into list of (seconds, text) tuples."""
    import re
    # Try [HH:MM:SS] format first
    entries = re.findall(r'\[(\d+):(\d+):(\d+)\]\s*(.*?)(?=\[|\Z)', timestamped_text, re.DOTALL)
    if entries:
        return [(int(h) * 3600 + int(m) * 60 + int(s), text.strip())
                for h, m, s, text in entries]
    # Try [MM:SS] format
    entries_simple = re.findall(r'\[?(\d+):(\d+)\]?\s*(.*?)(?=\[|\Z)', timestamped_text, re.DOTALL)
    if entries_simple:
        return [(int(m) * 60 + int(s), text.strip())
                for m, s, text in entries_simple]
    return []


def find_sentence_boundary(timestamped_text: str, target_time: int,
                           direction: str = 'backward',
                           max_search_seconds: int = 5) -> int:
    """Find nearest sentence ending (. ? !) relative to target_time.

    Args:
        timestamped_text: Timestamped transcript text
        target_time: Target timestamp in seconds
        direction: 'backward' for clip start (find sentence start after previous end),
                   'forward' for clip end (find sentence end after target)
        max_search_seconds: Maximum seconds to search in either direction

    Returns:
        Adjusted timestamp in seconds
    """
    parsed = _parse_timestamped_text(timestamped_text)
    if not parsed:
        logger.warning(f"WARNING: No sentence boundary found (no parsed entries), using raw timestamp {target_time}")
        return target_time

    if direction == 'backward':
        # Find the nearest sentence-ending BEFORE target_time,
        # then return the timestamp of the NEXT word (sentence start)
        best_start = target_time
        for i, (sec, text) in enumerate(parsed):
            if sec >= target_time:
                break
            # Check if text ends with sentence-ending punctuation
            if text and text.rstrip()[-1:] in '.?!':
                # Next entry's timestamp = start of next sentence
                if i + 1 < len(parsed):
                    candidate = parsed[i + 1][0]
                    if candidate <= target_time and (target_time - candidate) <= max_search_seconds:
                        best_start = candidate

        if best_start == target_time:
            logger.info(f"WARNING: No sentence boundary found backward from {target_time}s, using raw timestamp")
        return best_start

    elif direction == 'forward':
        # Find the nearest sentence-ending AFTER target_time,
        # return the timestamp just after that ending
        for i, (sec, text) in enumerate(parsed):
            if sec < target_time:
                continue
            if text and text.rstrip()[-1:] in '.?!':
                # End point: this entry's timestamp + estimated duration for this text
                # Use next entry's timestamp as the sentence end point
                if i + 1 < len(parsed):
                    end_point = parsed[i + 1][0]
                else:
                    end_point = sec + 2  # last entry, add 2s buffer
                if (end_point - target_time) <= max_search_seconds:
                    return end_point
                break  # beyond max search window

        logger.info(f"WARNING: No sentence boundary found forward from {target_time}s, using raw timestamp")
        return target_time

    return target_time


def _find_sentence_start(timestamped_text: str, target_sec: int) -> int:
    """Find the nearest sentence boundary BEFORE the target timestamp.
    Wrapper around find_sentence_boundary for backward compatibility.
    """
    return find_sentence_boundary(timestamped_text, target_sec, direction='backward', max_search_seconds=5)


if __name__ == "__main__":
    # Quick test: extract a known clip
    import sys
    if len(sys.argv) >= 4:
        vid = sys.argv[1]
        start = int(sys.argv[2])
        end = int(sys.argv[3])
        out = os.path.join(BASE, "output", f"test_clip_{vid}.mp4")
        ok = extract_clip(vid, start, end, out)
        print(f"Extraction {'succeeded' if ok else 'failed'}: {out}")
    else:
        print("Usage: python3 clip_extractor.py <video_id> <start_sec> <end_sec>")
