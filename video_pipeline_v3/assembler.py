#!/usr/bin/env python3
"""Assembler V5 — clip-first episode assembly.

Structure:
  1. Cold open TTS (with background music)
  2. Intro jingle (if exists)
  3. For each clip (1-5):
     a. Host setup TTS (with background music)
     b. Transition sting
     c. YouTube clip at FULL SCREEN with ORIGINAL AUDIO (no background music)
     d. Host reaction TTS (with background music)
  4. Wrap-up TTS (with background music)
  5. Outro jingle (if exists)

Visual rules:
  - During host dialogue: dark gradient background + speaker label + lower-third ticker
  - During clips: full screen, small "Source: @Channel" attribution top-right
  - Clips play with ORIGINAL audio — no muting, no TTS overlay
"""
import json
import logging
import os
import shutil
import subprocess
import tempfile

from music import (
    has_music, has_intro, has_transition, has_outro,
    mix_tts_with_music, INTRO_JINGLE, TRANSITION, OUTRO_JINGLE,
    ffprobe_duration,
)

logger = logging.getLogger("Assembler")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[assemble] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        logger.error(f"FAIL {label}: {r.stderr[-400:]}")
        return False
    return True


def run_ffmpeg_filtergraph(inputs: list, filtergraph: str, maps: list,
                           output_args: list, output_path: str,
                           label: str = "", timeout: int = 300) -> bool:
    fd, fpath = tempfile.mkstemp(suffix=".txt", prefix="ff_filter_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(filtergraph)
        cmd = ["ffmpeg", "-y"]
        for inp in inputs:
            if isinstance(inp, list):
                cmd.extend(inp)
            else:
                cmd.extend(["-i", inp])
        cmd.extend(["-filter_complex_script", fpath])
        for m in maps:
            cmd.extend(["-map", m])
        cmd.extend(output_args)
        cmd.append(output_path)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            logger.error(f"FAIL {label}: {r.stderr[-400:]}")
            return False
        return True
    finally:
        os.unlink(fpath)


def ensure_audio(video_path: str) -> str:
    """Ensure video has an audio stream."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
        capture_output=True, text=True,
    )
    if "audio" in r.stdout:
        return video_path
    out = video_path.replace(".mp4", "_waud.mp4")
    dur = ffprobe_duration(video_path)
    run_ffmpeg(
        ["-i", video_path, "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
         "-t", str(dur), "-c:v", "copy", "-c:a", "aac", "-shortest", out],
        "add silence", 60,
    )
    return out if os.path.exists(out) else video_path


# ── Host dialogue visual ─────────────────────────────────────────────────────

def make_host_visual(audio_path: str, host: int, text: str,
                     output_path: str, btc_price: str = "N/A",
                     label: str = "") -> str:
    """Create a host dialogue video: dark gradient + speaker label + ticker.

    No B-roll / stock footage. Clean dark studio look.
    """
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = audio_dur + 0.2

    host_names = {1: "JESSICA", 2: "CHRIS"}
    host_colors = {1: "0xCC0000", 2: "0x0066CC"}
    speaker = host_names.get(host, "HOST")
    color = host_colors.get(host, "0xCC0000")

    ticker_text = f"PROTOCOL PULSE  |  PULSE CHECK  |  BTC {btc_price}"
    ticker_text = ticker_text.replace("'", "").replace('"', '')

    fg = (
        # Dark gradient background
        f"color=c=0x080808:s=1920x1080:d={total_dur}:r=30[bg0];\n"
        # Subtle red gradient on right side
        f"color=c=0x150505:s=400x1080:d={total_dur}:r=30[rgr];\n"
        f"[bg0][rgr]overlay=1520:0[bg];\n"
        # Speaker label bar (left side)
        f"color=c={color}:s=6x60:d={total_dur}[spkbar];\n"
        f"color=c=0x0A0A0A@0.85:s=220x60:d={total_dur}[spkbg];\n"
        f"[spkbg][spkbar]overlay=0:0[spkbase];\n"
        f"[spkbase]drawtext=fontfile={FONT_BOLD}:text='{speaker}':"
        f"fontcolor=white:fontsize=24:x=20:y=18[spklabel];\n"
        # Lower-third ticker
        f"color=c=0x0A0A0A@0.9:s=1920x50:d={total_dur}[tickbg];\n"
        f"[tickbg]drawtext=fontfile={FONT_MONO}:text='{ticker_text}':"
        f"fontcolor=0xAAAAAA:fontsize=20:x=(w-text_w)/2:y=15[ticker];\n"
        # Compose
        f"[bg][spklabel]overlay=60:H-180[v1];\n"
        f"[v1][ticker]overlay=0:H-50[v2];\n"
        f"[v2]drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
        f"fontcolor=white@0.25:fontsize=16:x=W-220:y=20,"
        f"format=yuv420p[outv];\n"
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
    )

    inputs = [
        ["-f", "lavfi", "-i", f"color=c=0x080808:s=1920x1080:d={total_dur}:r=30"],
        audio_path,
    ]

    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k", "-t", str(total_dur)],
        output_path, label or f"host visual ({speaker})",
    )
    return output_path if ok else ""


# ── YouTube clip visual ──────────────────────────────────────────────────────

def make_clip_visual(clip_path: str, source: str, output_path: str,
                     btc_price: str = "N/A") -> str:
    """Full-screen YouTube clip with original audio + source attribution.

    CRITICAL: Original audio is preserved. No muting. No background music overlay.
    """
    clip_dur = ffprobe_duration(clip_path)
    if clip_dur <= 0:
        logger.warning(f"Clip has zero duration: {clip_path}")
        return ""

    safe_source = source.replace("'", "").replace('"', '').replace(":", "")
    ticker_text = f"PROTOCOL PULSE  |  PULSE CHECK  |  BTC {btc_price}"
    ticker_text = ticker_text.replace("'", "").replace('"', '')

    fg = (
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"setsar=1,fps=30[clip];\n"
        # Source attribution (top-right corner)
        f"color=c=0x0A0A0A@0.7:s=320x40:d={clip_dur}[srcbg];\n"
        f"[srcbg]drawtext=fontfile={FONT_MONO}:text='Source  {safe_source}':"
        f"fontcolor=white:fontsize=16:x=10:y=10[srclabel];\n"
        # Compose — source overlay top-right, NO other overlays
        f"[clip][srclabel]overlay=W-340:15,"
        f"format=yuv420p[outv];\n"
        # ORIGINAL AUDIO — just normalize volume
        f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
    )

    ok = run_ffmpeg_filtergraph(
        [clip_path], fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k"],
        output_path, f"clip visual ({safe_source})",
    )
    return output_path if ok else ""


# ── Jingle / transition visual ───────────────────────────────────────────────

def make_jingle_visual(audio_path: str, output_path: str,
                       text: str = "PULSE CHECK") -> str:
    """Create a visual for intro/outro jingle — dark bg with branding."""
    dur = ffprobe_duration(audio_path)
    if dur <= 0:
        return ""

    safe_text = text.replace("'", "")
    fg = (
        f"color=c=0x080808:s=1920x1080:d={dur}:r=30,"
        f"drawtext=fontfile={FONT_BOLD}:text='{safe_text}':"
        f"fontcolor=0xCC0000:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2,"
        f"format=yuv420p[outv];\n"
        f"[1:a]anull[outa]"
    )

    ok = run_ffmpeg_filtergraph(
        [["-f", "lavfi", "-i", f"color=c=0x080808:s=1920x1080:d={dur}:r=30"],
         audio_path],
        fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k"],
        output_path, "jingle visual",
    )
    return output_path if ok else ""


def make_transition_visual(output_path: str, duration: float = 2.0) -> str:
    """Short transition — sting audio (if exists) or just a dark flash."""
    if has_transition():
        return make_jingle_visual(TRANSITION, output_path, text="")

    # No sting — create brief dark transition
    cmd = [
        "-f", "lavfi", "-i", f"color=c=0x0A0A0A:s=1920x1080:d={duration}:r=30",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
        "-shortest",
        output_path,
    ]
    ok = run_ffmpeg(cmd, "transition", 30)
    return output_path if ok else ""


# ── Concatenation ────────────────────────────────────────────────────────────

def normalize_part(part_path: str, output_path: str) -> str:
    """Normalize a video part to consistent format for concatenation."""
    part_path = ensure_audio(part_path)
    ok = run_ffmpeg(
        ["-i", part_path, "-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-r", "30", "-vf", "scale=1920:1080,setsar=1,format=yuv420p",
         "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
         output_path],
        f"normalize", 120,
    )
    return output_path if (ok and os.path.exists(output_path)) else part_path


def concatenate_parts(parts: list, output_path: str) -> str:
    """Concat video parts using FFmpeg concat demuxer."""
    valid = [p for p in parts if p and os.path.exists(p)]
    if not valid:
        return ""
    if len(valid) == 1:
        shutil.copy2(valid[0], output_path)
        return output_path

    # Normalize all parts
    normalized = []
    for i, p in enumerate(valid):
        tmp = output_path + f".norm{i}.mp4"
        norm = normalize_part(p, tmp)
        normalized.append(norm)

    # Concat
    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for p in normalized:
            f.write(f"file '{os.path.abspath(p)}'\n")

    ok = run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", concat_file,
         "-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k", output_path],
        "concat final", 600,
    )

    # Cleanup temp files
    for p in normalized:
        if ".norm" in p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    for p in valid:
        if p.endswith("_waud.mp4") and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    if os.path.exists(concat_file):
        os.remove(concat_file)

    return output_path if ok else ""


# ── Main assembly ────────────────────────────────────────────────────────────

def assemble_episode(script: dict, audio_data: dict, extracted_clips: dict,
                     output_path: str, btc_price: str = "N/A") -> str:
    """Assemble a V5 clip-first episode.

    Args:
        script: V5 script with dialogue array (from generate_from_clips)
        audio_data: From generate_dialogue_audio() — {lines, full, total_duration}
        extracted_clips: From clip_extractor.extract_all() — {rank: {path, channel, ...}}
        output_path: Final video path
        btc_price: BTC price string for ticker

    Returns:
        Path to final video, or "" on failure
    """
    logger.info("=" * 60)
    logger.info("ASSEMBLING V5 CLIP-FIRST EPISODE")
    logger.info("=" * 60)

    work_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "work")
    os.makedirs(work_dir, exist_ok=True)

    dialogue = script.get("dialogue", [])
    lines = audio_data.get("lines", [])
    parts = []
    part_idx = 0

    for i, entry in enumerate(dialogue):
        host = entry.get("host")
        entry_type = entry.get("type", "")

        if host == "CLIP":
            # YouTube clip — FULL SCREEN, ORIGINAL AUDIO
            rank = entry.get("rank", 0)
            clip_info = extracted_clips.get(rank, {})
            clip_path = clip_info.get("path", "")

            if clip_path and os.path.exists(clip_path):
                # Add transition before clip
                trans_out = os.path.join(work_dir, f"trans_{part_idx:03d}.mp4")
                trans = make_transition_visual(trans_out)
                if trans:
                    parts.append(trans)
                    part_idx += 1

                # The clip itself
                clip_out = os.path.join(work_dir, f"clip_{part_idx:03d}_r{rank}.mp4")
                channel = clip_info.get("channel", "")
                handle = f"@{channel.replace(' ', '')}" if channel else ""
                result = make_clip_visual(clip_path, handle, clip_out,
                                          btc_price=btc_price)
                if result:
                    parts.append(result)
                    dur = ffprobe_duration(result)
                    logger.info(f"  Clip #{rank} [{channel}]: {dur:.1f}s")
                    part_idx += 1
            else:
                logger.warning(f"  Clip #{rank}: file not found, skipping")
            continue

        # Host dialogue line
        if i >= len(lines):
            continue
        line = lines[i]
        if not line.get("path") or not os.path.exists(line["path"]):
            continue

        host_num = int(line.get("host", 1)) if line.get("host") not in ("CLIP",) else 1
        text = line.get("text", "")

        # Mix TTS with background music if available
        audio_path = line["path"]
        if has_music():
            mixed_path = os.path.join(work_dir, f"mixed_{part_idx:03d}.m4a")
            if mix_tts_with_music(audio_path, mixed_path):
                audio_path = mixed_path

        # Create host visual
        line_out = os.path.join(work_dir, f"host_{part_idx:03d}_{entry_type}.mp4")
        result = make_host_visual(
            audio_path, host_num, text, line_out,
            btc_price=btc_price, label=f"{entry_type} {part_idx}",
        )
        if result:
            parts.append(result)
            part_idx += 1

        # Add intro jingle after cold open
        if entry_type == "cold_open" and has_intro():
            jingle_out = os.path.join(work_dir, f"intro_jingle_{part_idx:03d}.mp4")
            result = make_jingle_visual(INTRO_JINGLE, jingle_out, "PULSE CHECK")
            if result:
                parts.append(result)
                part_idx += 1

    # Outro jingle
    if has_outro():
        outro_out = os.path.join(work_dir, f"outro_jingle_{part_idx:03d}.mp4")
        result = make_jingle_visual(OUTRO_JINGLE, outro_out, "PROTOCOL PULSE")
        if result:
            parts.append(result)
            part_idx += 1

    # Concatenate all parts
    logger.info(f"Concatenating {len(parts)} parts...")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    result = concatenate_parts(parts, output_path)

    if result and os.path.exists(result):
        dur = ffprobe_duration(result)
        sz = os.path.getsize(result) / 1024 / 1024
        logger.info(f"DONE: {result} ({dur:.1f}s, {sz:.1f}MB)")
        return result

    logger.error("Assembly failed — no output produced")
    return ""


def verify_video(path: str) -> bool:
    """Verify output video meets spec."""
    logger.info(f"Verifying: {os.path.basename(path)}")

    if not os.path.exists(path):
        logger.error("File does not exist")
        return False

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True,
    )
    try:
        info = json.loads(r.stdout)
    except Exception:
        logger.error("Cannot parse ffprobe output")
        return False

    streams = info.get("streams", [])
    fmt = info.get("format", {})
    vid = next((s for s in streams if s.get("codec_type") == "video"), None)
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)

    checks = []
    if vid:
        w, h = int(vid.get("width", 0)), int(vid.get("height", 0))
        checks.append(("Video codec", vid.get("codec_name") == "h264", vid.get("codec_name")))
        checks.append(("Resolution", w == 1920 and h == 1080, f"{w}x{h}"))
    else:
        checks.append(("Video stream", False, "MISSING"))

    if aud:
        checks.append(("Audio codec", aud.get("codec_name") == "aac", aud.get("codec_name")))
        checks.append(("Sample rate", aud.get("sample_rate") == "44100", aud.get("sample_rate")))
    else:
        checks.append(("Audio stream", False, "MISSING"))

    duration = float(fmt.get("duration", 0))
    size_mb = int(fmt.get("size", 0)) / 1024 / 1024
    checks.append(("Duration", 10 <= duration <= 600, f"{duration:.1f}s"))
    checks.append(("File size", 0.5 <= size_mb <= 500, f"{size_mb:.1f}MB"))

    all_pass = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        logger.info(f"  [{status}] {name}: {detail}")

    return all_pass


if __name__ == "__main__":
    logger.info("Assembler V5 — use daily_producer.py to run the full pipeline")
