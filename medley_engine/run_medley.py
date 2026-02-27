#!/usr/bin/env python3
"""
Protocol Pulse — YouTube Medley Engine (4090).

Monitors YouTube channels for new daily uploads, extracts 60-second 'Alpha' clips
based on Bitcoin-related keywords (GPU transcription via faster-whisper),
merges clips into a single medley with smooth cross-dissolve, and appends
the branding tag at the end.

Usage:
  cd ~/protocol_pulse   # or medley_engine/
  source venv/bin/activate
  pip install -r requirements.txt
  python run_medley.py [--daily | --channels-only | --merge-only]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Project layout
# -----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


def load_config():
    try:
        import yaml
        with open(ROOT / "config.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Config load error: {e}", file=sys.stderr)
        return {}


def ensure_dirs(cfg):
    paths = cfg.get("paths", {})
    for key in ("channels_dir", "clips_dir", "output_dir", "logs_dir"):
        d = paths.get(key)
        if d:
            (ROOT / d).mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Phase A: Monitor channels for new daily uploads (yt-dlp)
# -----------------------------------------------------------------------------
def fetch_recent_uploads(cfg):
    """Use yt-dlp to list recent uploads from configured channels (e.g. last 24h)."""
    channels = cfg.get("channels", [])
    if not channels:
        print("No channels in config.yaml; add URLs under 'channels:'.")
        return []
    channels_dir = Path(cfg["paths"]["channels_dir"])
    channels_dir.mkdir(parents=True, exist_ok=True)
    out_tpl = str(channels_dir / "%(channel)s_%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dateafter", "today-1",
        "--print", "url",
        "-o", out_tpl,
    ] + channels
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        urls = [u.strip() for u in result.stdout.splitlines() if u.strip()]
        print(f"Found {len(urls)} recent upload(s).")
        return urls
    except subprocess.TimeoutExpired:
        print("yt-dlp timed out.", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("yt-dlp not found. Install: pip install yt-dlp (or system yt-dlp).", file=sys.stderr)
        return []


# -----------------------------------------------------------------------------
# Phase B: Download + transcribe with faster-whisper (GPU 0), extract Alpha clips
# -----------------------------------------------------------------------------
def transcribe_with_whisper(audio_path: Path, cfg) -> list[tuple[float, float, str]]:
    """Return list of (start_sec, end_sec, text) segments from audio."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("faster_whisper not installed. pip install faster-whisper", file=sys.stderr)
        return []
    device = cfg.get("whisper_device", "cuda")
    model_size = cfg.get("whisper_model", "large-v3")
    model = WhisperModel(model_size, device=device, compute_type="float16")
    segments, _ = model.transcribe(str(audio_path), word_timestamps=True)
    result = []
    for s in segments:
        result.append((s.start, s.end, (s.text or "").strip()))
    return result


def find_alpha_windows(segments, keywords, window_sec: float = 60.0):
    """Find 60s windows that contain any of the keywords. Returns [(start, end), ...]."""
    keywords_lower = [k.lower() for k in keywords]
    windows = []
    for start, end, text in segments:
        if not text:
            continue
        tlower = text.lower()
        if any(kw in tlower for kw in keywords_lower):
            # take a 60s window centered around this segment (or start-aligned)
            w_start = max(0.0, start - 5.0)
            w_end = min(w_start + window_sec, end + window_sec)
            windows.append((w_start, w_end))
    # merge overlapping windows
    windows.sort(key=lambda x: x[0])
    merged = []
    for s, e in windows:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged[:20]  # cap


def extract_clips_from_videos(video_urls: list[str], cfg):
    """Download audio/video, transcribe on GPU, extract 60s Alpha clips into clips_dir."""
    clips_dir = Path(cfg["paths"]["clips_dir"])
    keywords = cfg.get("alpha_keywords", ["bitcoin"])
    duration = float(cfg.get("clip_duration_seconds", 60))
    clip_paths = []

    for url in video_urls:
        try:
            out_tpl = str(clips_dir / "dl_%(id)s.%(ext)s")
            subprocess.run(
                ["yt-dlp", "-f", "bestaudio/best", "-o", out_tpl, "--no-playlist", url],
                check=True, capture_output=True, timeout=300,
            )
        except subprocess.CalledProcessError:
            continue
        # find the downloaded file
        files = list(clips_dir.glob("dl_*.*"))
        if not files:
            continue
        media_path = files[-1]
        # extract audio for whisper if needed (faster-whisper can take audio or video)
        audio_path = media_path
        if media_path.suffix != ".wav":
            audio_path = clips_dir / (media_path.stem + "_audio.wav")
            subprocess.run([
                "ffmpeg", "-y", "-i", str(media_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                str(audio_path)
            ], check=True, capture_output=True, timeout=120)
        segments = transcribe_with_whisper(audio_path, cfg)
        windows = find_alpha_windows(segments, keywords, duration)
        for i, (start, end) in enumerate(windows):
            clip_out = clips_dir / f"alpha_{media_path.stem}_{i:02d}.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-i", str(media_path),
                "-ss", str(start), "-t", str(duration),
                "-c:v", "libx264", "-c:a", "aac", "-avoid_negative_ts", "1",
                str(clip_out)
            ], check=True, capture_output=True, timeout=60)
            clip_paths.append(clip_out)
    return clip_paths


# -----------------------------------------------------------------------------
# Phase C: Merge clips with cross-dissolve + append branding (ffmpeg, NVENC)
# -----------------------------------------------------------------------------
def merge_clips_with_dissolve(clip_paths: list[Path], output_path: Path, cfg):
    """Merge clips with xfade cross-dissolve; encode with NVENC if available."""
    if not clip_paths:
        print("No clips to merge.")
        return
    dissolve = float(cfg.get("cross_dissolve_duration", 1.5))
    # Build filter_complex for video xfade + audio acrossfade
    n = len(clip_paths)
    inputs = []
    for p in clip_paths:
        inputs.extend(["-i", str(p)])
    # Get duration of first clip for offset calculation (simplified: assume fixed length)
    clip_dur = float(cfg.get("clip_duration_seconds", 60))
    v_filters = []
    a_filters = []
    for i in range(n):
        if i == 0:
            v_filters.append(f"[0:v]copy[v0]")
            a_filters.append(f"[0:a]acopy[a0]")
        else:
            # Start transition at end of previous chain: i*(clip_dur - dissolve)
            offset = i * (clip_dur - dissolve)
            v_filters.append(
                f"[v{i-1}][{i}:v]xfade=transition=dissolve:duration={dissolve}:offset={offset}[v{i}]"
            )
            a_filters.append(
                f"[a{i-1}][{i}:a]acrossfade=d={dissolve}[a{i}]"
            )
    v_last = f"[v{n-1}]"
    a_last = f"[a{n-1}]"
    map_v = v_last
    map_a = a_last
    filter_complex = ";".join(v_filters) + ";" + ";".join(a_filters)
    # Prefer NVENC on 4090; fallback to libx264
    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + ["-filter_complex", filter_complex, "-map", v_last, "-map", a_last]
        + ["-c:v", "h264_nvenc", "-c:a", "aac", "-preset", "p4", str(output_path)]
    )
    try:
        subprocess.run(cmd, check=True, timeout=600, capture_output=True)
    except subprocess.CalledProcessError:
        cmd = (
            ["ffmpeg", "-y"]
            + inputs
            + ["-filter_complex", filter_complex, "-map", v_last, "-map", a_last]
            + ["-c:v", "libx264", "-c:a", "aac", "-preset", "medium", str(output_path)]
        )
        subprocess.run(cmd, check=True, timeout=900)


def append_branding(medley_path: Path, branding_path: Path, final_path: Path):
    """Concatenate medley + branding tag (same codec)."""
    if not branding_path.exists():
        print(f"Branding file not found: {branding_path}; outputting medley only.")
        if medley_path != final_path:
            import shutil
            shutil.copy(medley_path, final_path)
        return
    list_file = ROOT / "concat_list.txt"
    with open(list_file, "w") as f:
        f.write(f"file '{medley_path.resolve()}'\n")
        f.write(f"file '{branding_path.resolve()}'\n")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", str(final_path)
    ], check=True, timeout=300)
    list_file.unlink(missing_ok=True)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Protocol Pulse YouTube Medley Engine")
    parser.add_argument("--daily", action="store_true", help="Full run: fetch uploads, extract clips, merge, tag")
    parser.add_argument("--channels-only", action="store_true", help="Only fetch recent upload URLs")
    parser.add_argument("--merge-only", action="store_true", help="Only merge existing clips in clips_dir + tag")
    parser.add_argument("--max-clips", type=int, default=None, help="Max clips to use in one medley")
    args = parser.parse_args()

    cfg = load_config()
    ensure_dirs(cfg)
    paths = cfg.get("paths", {})
    clips_dir = Path(paths.get("clips_dir", "clips"))
    output_dir = Path(paths.get("output_dir", "output"))
    branding_path = ROOT / paths.get("branding_path", "branding/tag.mp4")
    max_clips = args.max_clips or cfg.get("max_clips_per_medley", 12)

    if args.channels_only:
        urls = fetch_recent_uploads(cfg)
        for u in urls:
            print(u)
        return

    if args.merge_only:
        clip_paths = sorted(clips_dir.glob("alpha_*.mp4"))[:max_clips]
        if not clip_paths:
            print("No alpha_*.mp4 clips in", clips_dir)
            return
        medley_path = output_dir / "medley_pre_tag.mp4"
        final_path = output_dir / "medley_tagged.mp4"
        merge_clips_with_dissolve(clip_paths, medley_path, cfg)
        append_branding(medley_path, branding_path, final_path)
        print("Output:", final_path)
        return

    # Default: full daily run
    urls = fetch_recent_uploads(cfg)
    if not urls:
        print("No recent uploads; try --merge-only with existing clips.")
        clip_paths = sorted(clips_dir.glob("alpha_*.mp4"))[:max_clips]
        if clip_paths:
            medley_path = output_dir / "medley_pre_tag.mp4"
            final_path = output_dir / "medley_tagged.mp4"
            merge_clips_with_dissolve(clip_paths, medley_path, cfg)
            append_branding(medley_path, branding_path, final_path)
            print("Output:", final_path)
        return
    clip_paths = extract_clips_from_videos(urls, cfg)[:max_clips]
    if not clip_paths:
        print("No Alpha clips extracted; check keywords and transcripts.")
        return
    medley_path = output_dir / "medley_pre_tag.mp4"
    final_path = output_dir / "medley_tagged.mp4"
    merge_clips_with_dissolve(clip_paths, medley_path, cfg)
    append_branding(medley_path, branding_path, final_path)
    print("Output:", final_path)


if __name__ == "__main__":
    main()
