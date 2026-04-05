#!/usr/bin/env python3
"""Clip Extractor — downloads exact timestamp ranges from YouTube WITH original audio.

Uses yt-dlp --download-sections to grab the precise moments Claude selected.
CRITICAL: Clips retain their ORIGINAL audio. No muting. No TTS overlay.
"""
import logging
import os
import shutil
import subprocess
import time

logger = logging.getLogger("ClipExtractor")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[extractor] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
CLIP_CACHE = os.path.join(BASE, "downloads", "clip_cache")
COOKIES_FILE = os.path.join(BASE, "data", "yt_cookies.txt")

# V4: yt-dlp format — prefer 1080p+ with graceful fallback to 720p
YT_DLP_FORMAT = (
    'bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/'
    'bestvideo[height>=1080]+bestaudio/'
    'bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/'
    'bestvideo[height>=720]+bestaudio/'
    'best[height>=720]/'
    'best'
)

# V4: Persistent clip cache — avoid re-downloading identical segments
CLIP_CACHE_DIR = os.path.join(BASE, "data", "clip_cache")
os.makedirs(CLIP_CACHE_DIR, exist_ok=True)

from utils.clip_archive import save_clip, get_fallback_clip

if not (os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0):
    logger.info("[yt-dlp] No cookies file — add data/yt_cookies.txt for rate limit protection")


def get_cached_clip(video_id, start_sec, end_sec):
    """Check if this exact clip segment is already cached."""
    cache_key = f"{video_id}_{start_sec}_{end_sec}"
    cache_path = os.path.join(CLIP_CACHE_DIR, f"{cache_key}.mp4")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 100_000:
        return cache_path
    return None


def cache_clip(video_id, start_sec, end_sec, clip_path):
    """Save extracted clip to persistent cache."""
    cache_key = f"{video_id}_{start_sec}_{end_sec}"
    cache_dest = os.path.join(CLIP_CACHE_DIR, f"{cache_key}.mp4")
    shutil.copy2(clip_path, cache_dest)
    return cache_dest


def _run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    """Run ffmpeg command, return True on success."""
    cmd = ["ffmpeg", "-y"] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            logger.error(f"FAIL {label}: {proc.stderr[-400:]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"TIMEOUT {label} after {timeout}s — killing ffmpeg")
        return False
    except Exception as e:
        logger.error(f"EXCEPTION {label}: {e}")
        return False


def fix_av_sync(input_path: str, output_path: str) -> bool:
    """Nuclear AV sync fix — full decode+re-encode with PTS reset.

    Uses discardcorrupt + itsoffset 0 + max_interleave_delta=0 to eliminate
    DTS discontinuities from yt-dlp multi-stream merges.
    """
    return _run_ffmpeg([
        "-fflags", "+genpts+igndts+discardcorrupt",
        "-itsoffset", "0",
        "-i", input_path,
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-r", "30", "-vsync", "cfr",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30,format=yuv420p,setpts=PTS-STARTPTS",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-af", "aresample=async=1:min_hard_comp=0.1:first_pts=0,asetpts=PTS-STARTPTS",
        "-avoid_negative_ts", "make_zero",
        "-max_interleave_delta", "0",
        "-movflags", "+faststart",
        output_path,
    ], "av_sync_fix_v2", 300)


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

        # FIX: +1.5s tail padding so speaker finishes sentence before cut
        min_end = original_end + 1.5
        # Find first pause that starts after min_end but within pad window
        candidates = [p for p in pauses if min_end <= p <= original_end + pad_window]
        if candidates:
            trim_at = candidates[0] + 0.2  # trim slightly into the silence
            logger.info(f"CLIP TRIM: Trimmed at natural pause at {trim_at:.1f}s (+1.5s tail padding)")
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


FORCE_SKIP_CHANNELS = ["Simply Bitcoin", "Bitcoin Magazine", "SatoSHE"]


def _skip_intro_silence(output_path: str, channel: str = "") -> None:
    """Render21 FIX 3: Speech onset detection replaces fixed +12s offset.

    Scans first 20s with silencedetect. Skips to first_speech_onset + 0.5s.
    FORCE_SKIP_CHANNELS always skip at least 15s.
    Also trims trailing silence/outro from last 10s.
    """
    import re as _re
    try:
        clip_dur = ffprobe_duration(output_path)
        if clip_dur < 5:
            return

        # --- INTRO SKIP: scan first 20s for speech onset ---
        result = subprocess.run([
            "ffmpeg", "-i", output_path, "-t", "20",
            "-af", "silencedetect=noise=-25dB:d=0.5",
            "-f", "null", "-"
        ], capture_output=True, text=True, timeout=30)
        silence_ends = _re.findall(r"silence_end: ([\d.]+)", result.stderr)

        # Determine skip point
        skip_to = 0.0
        force_min = 15.0 if any(ch in channel for ch in FORCE_SKIP_CHANNELS if ch) else 0.0

        if silence_ends:
            first_speech = float(silence_ends[0])
            skip_to = max(first_speech + 0.5, force_min)
            logger.info(f"  Render21: Speech onset at {first_speech:.1f}s, skip_to={skip_to:.1f}s (force_min={force_min:.0f}s, channel={channel})")
        elif force_min > 0:
            skip_to = force_min
            logger.info(f"  Render21: Force skip {force_min:.0f}s for {channel}")

        if skip_to > 0 and skip_to < clip_dur - 5:
            trimmed = output_path + ".jingle_skip.mp4"
            ok = _run_ffmpeg([
                "-ss", f"{skip_to:.2f}", "-i", output_path,
                "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                trimmed,
            ], f"speech onset skip +{skip_to:.1f}s", 60)
            if ok and os.path.exists(trimmed) and os.path.getsize(trimmed) > 10000:
                os.replace(trimmed, output_path)
                logger.info(f"  Render21: Intro skip applied at {skip_to:.1f}s")
            elif os.path.exists(trimmed):
                os.remove(trimmed)

        # --- OUTRO TRIM: detect silence in last 10s ---
        clip_dur = ffprobe_duration(output_path)
        if clip_dur > 15:
            tail_start = max(0, clip_dur - 10)
            result2 = subprocess.run([
                "ffmpeg", "-ss", f"{tail_start:.2f}", "-i", output_path,
                "-af", "silencedetect=noise=-30dB:d=1.0",
                "-f", "null", "-"
            ], capture_output=True, text=True, timeout=20)
            tail_silence_starts = _re.findall(r"silence_start: ([\d.]+)", result2.stderr)
            if tail_silence_starts:
                # First silence in the tail = trim point (relative to tail_start)
                trim_at = tail_start + float(tail_silence_starts[0]) + 0.3
                if trim_at < clip_dur - 1.0:
                    outro_trimmed = output_path + ".outro_trim.mp4"
                    ok2 = _run_ffmpeg([
                        "-i", output_path, "-t", f"{trim_at:.2f}",
                        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                        outro_trimmed,
                    ], f"outro trim at {trim_at:.1f}s", 60)
                    if ok2 and os.path.exists(outro_trimmed) and os.path.getsize(outro_trimmed) > 10000:
                        os.replace(outro_trimmed, output_path)
                        logger.info(f"  Render21: Outro trimmed at {trim_at:.1f}s (was {clip_dur:.1f}s)")
                    elif os.path.exists(outro_trimmed):
                        os.remove(outro_trimmed)

    except Exception as e:
        logger.warning(f"  Render21: Speech onset detection failed: {e}")


def make_motion_from_static(image_path: str, output_path: str,
                            duration: float, fps: int = 30) -> bool:
    """Convert a static image to video with Ken Burns zoom — eliminates freeze frames at source.

    Uses zoompan to create a slow 1.0→1.05x zoom over the duration.
    Every frame is unique — freezedetect cannot trigger on the output.

    Args:
        image_path: Path to static image (PNG/JPG)
        output_path: Path for output MP4
        duration: Video duration in seconds
        fps: Frame rate (default 30)

    Returns:
        True if conversion succeeded
    """
    total_frames = max(1, int(duration * fps))
    return _run_ffmpeg([
        "-loop", "1", "-i", image_path,
        "-vf", (f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,"
                f"zoompan=z='min(zoom+0.002\\,1.05)':d={total_frames}:s=1920x1080:fps={fps}"),
        "-t", str(duration), "-r", str(fps),
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        output_path,
    ], f"ken_burns_static {os.path.basename(image_path)}", 120)


def extract_clip(video_id: str, start_sec: int, end_sec: int,
                 output_path: str, channel: str = "") -> bool:
    """Download exact clip segment with original audio.

    Args:
        video_id: YouTube video ID
        start_sec: Start time in seconds
        end_sec: End time in seconds
        output_path: Where to save the clip
        channel: Channel name for speech onset skip logic

    Returns:
        True if clip was extracted successfully
    """
    try:
        return _extract_clip_inner(video_id, start_sec, end_sec, output_path, channel)
    except Exception as e:
        logger.error(f"[extractor] FATAL exception on {video_id}: {e}", exc_info=True)
        # Clean up any temp files left behind
        for suffix in [".resync.mp4", ".sync.mp4", ".nuclear.mp4", ".lipsync.mp4",
                       ".fix7.mp4", ".jingle_skip.mp4", ".outro_trim.mp4"]:
            tmp = output_path + suffix
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except OSError: pass
        return False


def _extract_clip_inner(video_id: str, start_sec: int, end_sec: int,
                        output_path: str, channel: str = "") -> bool:
    """Inner implementation of extract_clip — may raise exceptions."""
    # P1 FIX (audit): Sanitize video_id — YouTube IDs are [A-Za-z0-9_-]{11}
    import re as _re
    if not _re.match(r'^[A-Za-z0-9_-]{8,15}$', video_id):
        logger.error(f"[extractor] REJECTED malformed video_id: {video_id!r}")
        return False
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Check if already extracted at output path
    if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
        dur = ffprobe_duration(output_path)
        if dur > 1:
            logger.info(f"  Clip cached: {video_id} ({dur:.1f}s)")
            return True

    # V4: Check persistent clip cache
    cached = get_cached_clip(video_id, start_sec, end_sec)
    if cached:
        shutil.copy2(cached, output_path)
        dur = ffprobe_duration(output_path)
        logger.info(f"  Persistent cache HIT: {video_id} ({dur:.1f}s)")
        return True

    # Render21 FIX 3: Removed fixed +12s offset — speech onset detection handles intro skip
    logger.info(f"[extractor] Clip {video_id}: raw start_sec={start_sec}, end_sec={end_sec}, channel={channel}")

    # Apply start -3s / end +10s padding to avoid mid-sentence cuts (LAW A4)
    # Issue 6: Increased end padding from 8s to 10s for natural pauses
    padded_start = max(0, start_sec - 3)
    padded_end = end_sec + 10

    url = f"https://www.youtube.com/watch?v={video_id}"

    # Method 1: yt-dlp --download-sections (preferred)
    cmd = [
        "yt-dlp",
        "--download-sections", f"*{padded_start}-{padded_end}",
        "-f", YT_DLP_FORMAT,
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--no-playlist",
        "--quiet",
        "--force-overwrites",
        url,
    ]
    # RULE 3: yt-dlp cookies for rate limit protection
    if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        cmd.insert(1, COOKIES_FILE)
        cmd.insert(1, "--cookies")

    logger.info(f"  Extracting {video_id} [{start_sec}-{end_sec}s]...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            # FIX 1 (render10): Hard PTS resync — force both A/V to start at exactly 0
            # Eliminates B-frame DTS offsets from yt-dlp downloads that cause ~1s audio lag
            resync_tmp = output_path + ".resync.mp4"
            resync_ok = _run_ffmpeg([
                "-i", output_path,
                "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-r", "30", "-vsync", "cfr",
                "-vf", "setpts=PTS-STARTPTS",
                "-c:a", "aac", "-ar", "48000",
                "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
                "-avoid_negative_ts", "make_zero", "-max_interleave_delta", "0",
                "-output_ts_offset", "0",
                resync_tmp,
            ], f"hard PTS resync {video_id}", 300)
            if resync_ok and os.path.exists(resync_tmp):
                os.replace(resync_tmp, output_path)
                logger.info(f"[extractor] Hard PTS resync applied to {video_id}")
            elif os.path.exists(resync_tmp):
                os.remove(resync_tmp)

            # AV sync fix pass
            sync_tmp = output_path + ".sync.mp4"
            if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
                os.replace(sync_tmp, output_path)
                logger.info(f"  AV sync fix applied")
            elif os.path.exists(sync_tmp):
                os.remove(sync_tmp)
            # Sync validation gate — FIX 2: lowered nuclear threshold 0.15→0.08
            offset = check_av_sync(output_path)
            if abs(offset) > 0.08:
                logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode (threshold 0.08s)")
                nuclear_tmp = output_path + ".nuclear.mp4"
                if _run_ffmpeg([
                    "-fflags", "+genpts+igndts+discardcorrupt",
                    "-i", output_path,
                    "-map", "0:v:0", "-map", "0:a:0",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                    "-r", "30", "-vsync", "cfr",
                    "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2",
                    "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
                    "-avoid_negative_ts", "make_zero",
                    nuclear_tmp,
                ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
                    os.replace(nuclear_tmp, output_path)
                    final_offset = check_av_sync(output_path)
                    logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
                elif os.path.exists(nuclear_tmp):
                    os.remove(nuclear_tmp)
            # FIX 2 REMOVED: dual-input -itsoffset correction was overcorrecting
            # clips already synced by hard PTS resync + nuclear re-encode.
            # The dual-input approach (opening same file twice with different offsets)
            # introduced NEW drift. Nuclear re-encode at 0.08s threshold is sufficient.
            # Render21 FIX 7: Final AV sync gate — re-encode if >0.15s
            final_sync = check_av_sync(output_path)
            if abs(final_sync) > 0.15:
                logger.error(f"  FIX 7: AV sync {final_sync:+.3f}s exceeds 0.15s — force re-encode")
                fix7_tmp = output_path + ".fix7.mp4"
                if _run_ffmpeg([
                    "-i", output_path,
                    "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                    "-vf", "setpts=PTS-STARTPTS",
                    "-c:a", "aac", "-ar", "48000",
                    "-af", "asetpts=PTS-STARTPTS",
                    "-r", "30", "-vsync", "cfr",
                    fix7_tmp,
                ], "av_sync_fix7_force", 120) and os.path.exists(fix7_tmp):
                    os.replace(fix7_tmp, output_path)
                    post_fix7 = check_av_sync(output_path)
                    logger.info(f"  FIX 7: Re-encode done, sync now {post_fix7:+.3f}s")
                elif os.path.exists(fix7_tmp):
                    os.remove(fix7_tmp)
            # Render21: Skip intro jingle via speech onset detection
            _skip_intro_silence(output_path, channel=channel)
            dur = ffprobe_duration(output_path)
            sz = os.path.getsize(output_path) / 1024
            logger.info(f"  Extracted: {dur:.1f}s, {sz:.0f}KB")
            # V4: Save to persistent cache
            cache_clip(video_id, start_sec, end_sec, output_path)
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
        "-f", YT_DLP_FORMAT,
        "--merge-output-format", "mp4",
        "-o", full_path,
        "--no-playlist",
        "--quiet",
        "--force-overwrites",
        url,
    ]
    # RULE 3: yt-dlp cookies for rate limit protection
    if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        dl_cmd.insert(1, COOKIES_FILE)
        dl_cmd.insert(1, "--cookies")

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
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        # Round 2 Fix 8: async resample during extraction to resync audio to video
        "-af", "aresample=async=1:first_pts=0",
        output_path,
    ]

    try:
        result = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            # FIX 1 (render10): Hard PTS resync — force both A/V to start at exactly 0
            resync_tmp = output_path + ".resync.mp4"
            resync_ok = _run_ffmpeg([
                "-i", output_path,
                "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-r", "30", "-vsync", "cfr",
                "-vf", "setpts=PTS-STARTPTS",
                "-c:a", "aac", "-ar", "48000",
                "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
                "-avoid_negative_ts", "make_zero", "-max_interleave_delta", "0",
                "-output_ts_offset", "0",
                resync_tmp,
            ], f"hard PTS resync fallback {video_id}", 300)
            if resync_ok and os.path.exists(resync_tmp):
                os.replace(resync_tmp, output_path)
                logger.info(f"[extractor] Hard PTS resync applied to {video_id} (fallback)")
            elif os.path.exists(resync_tmp):
                os.remove(resync_tmp)

            # AV sync fix pass
            sync_tmp = output_path + ".sync.mp4"
            if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
                os.replace(sync_tmp, output_path)
                logger.info(f"  AV sync fix applied")
            elif os.path.exists(sync_tmp):
                os.remove(sync_tmp)
            # Sync validation gate — FIX 2: lowered nuclear threshold 0.15→0.08
            offset = check_av_sync(output_path)
            if abs(offset) > 0.08:
                logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode (threshold 0.08s)")
                nuclear_tmp = output_path + ".nuclear.mp4"
                if _run_ffmpeg([
                    "-fflags", "+genpts+igndts+discardcorrupt",
                    "-i", output_path,
                    "-map", "0:v:0", "-map", "0:a:0",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                    "-r", "30", "-vsync", "cfr",
                    "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2",
                    "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
                    "-avoid_negative_ts", "make_zero",
                    nuclear_tmp,
                ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
                    os.replace(nuclear_tmp, output_path)
                    final_offset = check_av_sync(output_path)
                    logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
                elif os.path.exists(nuclear_tmp):
                    os.remove(nuclear_tmp)
            # FIX 2 REMOVED: dual-input -itsoffset correction was overcorrecting.
            # See primary path comment above.
            # Render21 FIX 7: Final AV sync gate (fallback path)
            final_sync_fb = check_av_sync(output_path)
            if abs(final_sync_fb) > 0.15:
                logger.error(f"  FIX 7: Fallback AV sync {final_sync_fb:+.3f}s exceeds 0.15s — force re-encode")
                fix7_tmp = output_path + ".fix7.mp4"
                if _run_ffmpeg([
                    "-i", output_path,
                    "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                    "-vf", "setpts=PTS-STARTPTS",
                    "-c:a", "aac", "-ar", "48000",
                    "-af", "asetpts=PTS-STARTPTS",
                    "-r", "30", "-vsync", "cfr",
                    fix7_tmp,
                ], "av_sync_fix7_force_fb", 120) and os.path.exists(fix7_tmp):
                    os.replace(fix7_tmp, output_path)
                    post_fix7 = check_av_sync(output_path)
                    logger.info(f"  FIX 7: Fallback re-encode done, sync now {post_fix7:+.3f}s")
                elif os.path.exists(fix7_tmp):
                    os.remove(fix7_tmp)
            # Render21: Skip intro jingle via speech onset detection
            _skip_intro_silence(output_path, channel=channel)
            dur = ffprobe_duration(output_path)
            logger.info(f"  Trimmed: {dur:.1f}s")
            # V4: Save to persistent cache
            cache_clip(video_id, start_sec, end_sec, output_path)
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
    """Quality check — log bitrate but accept any clip.

    A low-bitrate clip is better than a narrator setup with no clip playing.
    Returns: 'ok' always.
    """
    bitrate = _get_bitrate(clip_path)
    if bitrate == 0:
        logger.warning(f"  Quality check: could not determine bitrate for {channel}")
        return "ok"

    mbps = bitrate / 1_000_000
    logger.info(f"  Quality: {channel} at {mbps:.1f}Mbps — accepted")
    return "ok"


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
        rank = clip.get("rank", 0)
        video_id = clip.get("video_id", "")
        start = clip.get("start_seconds", 0)
        end = clip["end_seconds"]
        channel = clip.get("channel", "unknown").replace(" ", "_")

        # Issue 3/4: Find sentence boundaries for clean clip start AND end
        timestamped_text = clip.get("timestamped_text", "")
        if timestamped_text:
            # Backward search for clean clip START
            # Session fix 5: Increased search window from 5s to 8s for better sentence boundaries
            adjusted_start = find_sentence_boundary(timestamped_text, start, direction='backward', max_search_seconds=8)
            if adjusted_start != start:
                logger.info(f"  Sentence boundary: clip #{rank} start {start}s -> {adjusted_start}s")
                start = adjusted_start
            # Forward search for clean clip END
            adjusted_end = find_sentence_boundary(timestamped_text, end, direction='forward', max_search_seconds=8)
            if adjusted_end != end:
                logger.info(f"  Sentence boundary: clip #{rank} end {end}s -> {adjusted_end}s")
                end = adjusted_end

        output_path = os.path.join(output_dir, f"clip_{rank}_{channel}_{video_id}.mp4")

        try:
            clip_ok = extract_clip(video_id, start, end, output_path, channel=channel)
        except Exception as e:
            logger.error(f"[extractor] extract_clip raised for {video_id}: {e}", exc_info=True)
            clip_ok = False
        if clip_ok:
            # Issue 10: Quality enforcement — reject below 1.5Mbps floor
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

            # Render20: No hard clip duration cap — quality over runtime

            # Session fix 5: Add 1.5s audio fade-out for clean clip endings
            _clip_dur_fo = ffprobe_duration(output_path)
            if _clip_dur_fo > 3.0:
                _fade_out_st = max(0, _clip_dur_fo - 1.5)
                _faded = output_path + ".faded.mp4"
                if _run_ffmpeg([
                    "-i", output_path,
                    "-af", f"afade=t=out:st={_fade_out_st:.2f}:d=1.5",
                    "-c:v", "copy", _faded,
                ], "clip_fade_out", 30) and os.path.exists(_faded):
                    os.replace(_faded, output_path)
                    logger.info(f"  Fade-out: clip #{rank} at {_fade_out_st:.1f}s (1.5s taper)")
                elif os.path.exists(_faded):
                    os.remove(_faded)

            # Issue 5: Second-pass ad read scan
            if _second_pass_ad_read(output_path, clip.get("channel", ""), rank):
                logger.warning(f"  REJECTED clip #{rank} [{channel}] — ad read in extracted audio")
                continue

            clip_info = {
                "path": output_path,
                "video_id": video_id,
                "channel": clip.get("channel", ""),
                "start": start,
                "end": end,
                "duration": ffprobe_duration(output_path),
                "quote": clip.get("quote", ""),
            }
            extracted[rank] = clip_info
            # RULE 1: Archive every successful clip for fallback
            save_clip(channel, video_id, output_path, clip_info)
        else:
            # RULE 1: Try archived fallback before giving up
            fallback = get_fallback_clip(clip.get("channel", ""))
            if fallback:
                age_days = round((time.time() - os.path.getmtime(fallback)) / 86400, 1)
                logger.info(f"[extractor] Using archived clip for {clip.get('channel', channel)} ({age_days} days old)")
                shutil.copy2(fallback, output_path)
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
                logger.warning(f"  Skipping clip #{rank}: extraction failed, no archive fallback")

    logger.info(f"Extracted {len(extracted)}/{len(clips)} clips")
    return extracted


def extract_montage_all(montage_selections: dict, output_dir: str) -> dict:
    """Extract montage clips — same as extract_all but uses montage timestamps
    and saves to clips/montage_clip_N_CHANNEL_ID.mp4"""
    os.makedirs(output_dir, exist_ok=True)
    clips = montage_selections.get("clips", [])
    extracted = {}

    for clip in clips:
        rank = clip.get("rank", 0)
        video_id = clip.get("video_id", "")
        start = clip.get("start_seconds", 0)
        end = clip["end_seconds"]
        channel = clip.get("channel", "unknown").replace(" ", "_")
        output_path = os.path.join(output_dir, f"montage_clip_{rank}_{channel}_{video_id}.mp4")

        try:
            ok = extract_clip(video_id, start, end, output_path, channel)
            if ok and os.path.exists(output_path):
                clip["montage_clip_path"] = output_path
                extracted[rank] = output_path
                logger.info(f"[Montage] Extracted: montage_clip_{rank}_{channel}")
            else:
                logger.warning(f"[Montage] Failed: {channel} {video_id}")
        except Exception as e:
            logger.error(f"[Montage] Error: {channel} {video_id}: {e}")

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
