#!/usr/bin/env python3
"""PBX Assembler — Avatar left, clip right, lower third.

Layout (1920x1080):
  ┌─────────────┬───────────────────┐
  │  PBX AVATAR │   CLIP / B-ROLL   │  ← 720px tall, starts at y=0
  │  640×720    │   1280×720        │
  └─────────────┴───────────────────┘
  ┌─────────────────────────────────┐
  │ LOWER THIRD: topic + branding  │  ← 360px tall (waveform + ticker)
  └─────────────────────────────────┘

PBX avatar: Wav2Lip lip-synced base loop (v1) or HeyGen (hero renders).
Right panel: clip being discussed, or PP chart/waveform when narrating.
Lower third: topic title, BTC price ticker, PP branding, audio waveform.
"""
import os, sys, json, subprocess, shutil, logging, glob, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "video_pipeline_v3"))

logger = logging.getLogger("pbx_assembler")

# ── Paths ────────────────────────────────────────────────────────────────────
V3_DIR = Path(__file__).resolve().parent.parent / "video_pipeline_v3"
ASSETS_DIR = V3_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
FONT_BOLD = str(FONTS_DIR / "DejaVuSans-Bold.ttf")
FONT_MONO = str(FONTS_DIR / "DejaVuSansMono.ttf")
INTRO_VIDEO = str(ASSETS_DIR / "intro.mp4")
OUTRO_VIDEO = str(ASSETS_DIR / "outro_branded_new.mp4")
GLITCH_TRANSITION = str(ASSETS_DIR / "transitions" / "glitch_transition_waud.mp4")
BG_MUSIC = str(ASSETS_DIR / "music" / "pp_background.mp3")
WATERMARK = str(ASSETS_DIR / "logo" / "watermark.png")

# PBX avatar base video — a looping clip of PBX at desk
PBX_BASE_VIDEO = str(ASSETS_DIR / "pbx_Paul-Broadcaster.mp4")

# ── Color System (APEX UNIFIED) ──────────────────────────────────────────────
COLOR_BG = "0x0A0A0F"
COLOR_RED = "0xCC2222"
COLOR_WHITE = "0xF4F5F8"
COLOR_GOLD = "0xF5A623"
COLOR_MUTED = "0x888888"
COLOR_GREEN = "0x6EE7B7"
COLOR_DARK_PANEL = "0x111118"

# ── Resolution ───────────────────────────────────────────────────────────────
WIDTH = 1920
HEIGHT = 1080
FPS = 30
AVATAR_W = 640
AVATAR_H = 720
CLIP_W = 1280
CLIP_H = 720
LOWER_H = 360  # bottom section for waveform + ticker + title


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return -1.0


def _escape_ffmpeg_text(text: str) -> str:
    """Escape special chars for FFmpeg drawtext filter."""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text


# ── Wav2Lip Integration ──────────────────────────────────────────────────────

def generate_wav2lip_avatar(audio_path: str, output_path: str,
                             base_video: str = None, duration: float = None) -> bool:
    """Generate lip-synced avatar video using Wav2Lip.

    If Wav2Lip is not available, falls back to the static base video
    looped to match audio duration with a subtle zoom animation.
    """
    base = base_video or PBX_BASE_VIDEO
    if not os.path.exists(base):
        logger.error(f"PBX base video not found: {base}")
        return False

    if not os.path.exists(audio_path):
        logger.error(f"Audio not found: {audio_path}")
        return False

    if duration is None:
        duration = ffprobe_duration(audio_path)
    if duration <= 0:
        duration = 30.0

    # Try Wav2Lip first
    wav2lip_ok = _try_wav2lip(base, audio_path, output_path, duration)
    if wav2lip_ok:
        return True

    # Fallback: loop base video with subtle Ken Burns zoom + overlay audio
    logger.info("Wav2Lip unavailable — using animated base loop fallback")
    return _animated_base_fallback(base, audio_path, output_path, duration)


def _try_wav2lip(base_video: str, audio_path: str, output_path: str, duration: float) -> bool:
    """Attempt Wav2Lip inference. Returns False if not installed."""
    try:
        wav2lip_dir = os.path.expanduser("~/Wav2Lip")
        if not os.path.isdir(wav2lip_dir):
            return False

        checkpoint = os.path.join(wav2lip_dir, "checkpoints", "wav2lip_gan.pth")
        if not os.path.exists(checkpoint):
            logger.warning("Wav2Lip checkpoint not found")
            return False

        # Loop base video to match duration
        looped = output_path + ".looped.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", base_video,
            "-t", str(duration), "-c:v", "libx264", "-crf", "18",
            "-preset", "fast", "-an", "-pix_fmt", "yuv420p", looped
        ], capture_output=True, text=True, timeout=120)

        if not os.path.exists(looped):
            return False

        r = subprocess.run([
            sys.executable, os.path.join(wav2lip_dir, "inference.py"),
            "--checkpoint_path", checkpoint,
            "--face", looped,
            "--audio", audio_path,
            "--outfile", output_path,
            "--resize_factor", "1",
            "--nosmooth",
        ], capture_output=True, text=True, timeout=600)

        os.remove(looped)

        if r.returncode == 0 and os.path.exists(output_path):
            logger.info(f"Wav2Lip OK: {ffprobe_duration(output_path):.1f}s")
            return True

        logger.warning(f"Wav2Lip failed: {r.stderr[:300]}")
        return False

    except Exception as e:
        logger.warning(f"Wav2Lip error: {e}")
        return False


def _animated_base_fallback(base_video: str, audio_path: str,
                              output_path: str, duration: float) -> bool:
    """Loop base video with subtle Ken Burns zoom + audio overlay."""
    r = subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", base_video,
        "-i", audio_path,
        "-t", str(duration),
        "-filter_complex",
        f"[0:v]scale={AVATAR_W}:{AVATAR_H},fps={FPS},"
        f"zoompan=z='1+0.001*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d=1:s={AVATAR_W}x{AVATAR_H}:fps={FPS}[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest", output_path
    ], capture_output=True, text=True, timeout=300)

    if r.returncode == 0 and os.path.exists(output_path):
        logger.info(f"Animated fallback OK: {ffprobe_duration(output_path):.1f}s")
        return True

    # Ultra-fallback: just loop + add audio, no zoom
    logger.warning("Zoompan failed, using simple loop")
    r = subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", base_video,
        "-i", audio_path,
        "-t", str(duration),
        "-vf", f"scale={AVATAR_W}:{AVATAR_H},fps={FPS}",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest", output_path
    ], capture_output=True, text=True, timeout=300)

    return r.returncode == 0 and os.path.exists(output_path)


# ── Part Builders ────────────────────────────────────────────────────────────

def make_narration_part(avatar_video: str, audio_path: str,
                         topic_text: str, btc_price: str,
                         output_path: str, duration: float = None) -> bool:
    """Build a narration segment: PBX avatar left, waveform/chart right, lower third.

    Used for: cold_open, setup, react, social_segment, wrap, data.
    """
    if duration is None:
        duration = ffprobe_duration(audio_path)

    topic_escaped = _escape_ffmpeg_text(topic_text[:80])
    price_escaped = _escape_ffmpeg_text(f"BTC {btc_price}")

    # Right panel: procedural waveform visualization from audio
    filter_complex = (
        # Scale avatar to left panel
        f"[0:v]scale={AVATAR_W}:{AVATAR_H},setsar=1[avatar];"

        # Generate waveform visualization for right panel from audio
        f"[1:a]showwaves=s={CLIP_W}x{CLIP_H}:mode=cline:rate={FPS}"
        f":colors={COLOR_RED.replace('0x', '#')}|{COLOR_WHITE.replace('0x', '#')}[waves];"
        f"color=c={COLOR_BG}:s={CLIP_W}x{CLIP_H}:d={duration}[rbg];"
        f"[rbg][waves]overlay=0:0:shortest=1[right];"

        # Stack horizontally: avatar | waveform
        f"[avatar][right]hstack=inputs=2[top];"

        # Lower third: dark bar with topic title and BTC price
        f"color=c={COLOR_DARK_PANEL}:s={WIDTH}x{LOWER_H}:d={duration}[bar];"
        f"[bar]drawtext=fontfile={FONT_BOLD}:text='{topic_escaped}'"
        f":fontcolor=white:fontsize=32:x=40:y=30[bar2];"
        f"[bar2]drawtext=fontfile={FONT_MONO}:text='{price_escaped}'"
        f":fontcolor={COLOR_GOLD.replace('0x', '#')}:fontsize=28:x=40:y=80[bar3];"
        f"[bar3]drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE'"
        f":fontcolor={COLOR_RED.replace('0x', '#')}:fontsize=22:x=w-350:y=30[bar4];"

        # Scrolling ticker on lower third
        f"[bar4]drawtext=fontfile={FONT_MONO}"
        f":text='STAY SOVEREIGN  ///  PULSE CHECK  ///  {price_escaped}  ///  STAY SOVEREIGN'"
        f":fontcolor={COLOR_MUTED.replace('0x', '#')}:fontsize=18"
        f":x=w-mod(t*80\\,w+tw):y={LOWER_H - 40}[lower];"

        # Pad top section and overlay lower third
        f"[top]pad={WIDTH}:{HEIGHT}:0:0:color={COLOR_BG}[padded];"
        f"[padded][lower]overlay=0:{AVATAR_H}[out]"
    )

    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", avatar_video,     # 0: avatar
        "-i", audio_path,       # 1: audio (for waveform + sound)
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "1:a",
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        output_path
    ], capture_output=True, text=True, timeout=300)

    if r.returncode != 0:
        logger.error(f"Narration part failed: {r.stderr[:500]}")
        return False

    logger.info(f"Narration part OK: {ffprobe_duration(output_path):.1f}s — {topic_text[:50]}")
    return True


def make_clip_part(avatar_video: str, clip_path: str,
                    source_label: str, output_path: str,
                    duration: float = None) -> bool:
    """Build a clip segment: PBX avatar left (muted/listening), clip right with original audio.

    The avatar still appears but is smaller/dimmed, clip is the focus.
    """
    if duration is None:
        duration = ffprobe_duration(clip_path)

    source_escaped = _escape_ffmpeg_text(source_label[:60])

    filter_complex = (
        # Avatar: scaled, slightly dimmed (listening mode)
        f"[0:v]scale={AVATAR_W}:{AVATAR_H},setsar=1,"
        f"colorbalance=bs=-0.1:gs=-0.1:rs=-0.1[avatar];"

        # Clip: scaled to right panel
        f"[1:v]scale={CLIP_W}:{CLIP_H},setsar=1[clip];"

        # Stack horizontally
        f"[avatar][clip]hstack=inputs=2[top];"

        # Lower third with source attribution
        f"color=c={COLOR_DARK_PANEL}:s={WIDTH}x{LOWER_H}:d={duration}[bar];"
        f"[bar]drawtext=fontfile={FONT_BOLD}:text='{source_escaped}'"
        f":fontcolor=white:fontsize=28:x=40:y=30[bar2];"
        f"[bar2]drawtext=fontfile={FONT_BOLD}:text='SOURCE'"
        f":fontcolor={COLOR_RED.replace('0x', '#')}:fontsize=18:x=40:y=70[bar3];"
        f"[bar3]drawtext=fontfile={FONT_BOLD}:text='PROTOCOL PULSE'"
        f":fontcolor={COLOR_RED.replace('0x', '#')}:fontsize=22:x=w-350:y=30[lower];"

        # Combine
        f"[top]pad={WIDTH}:{HEIGHT}:0:0:color={COLOR_BG}[padded];"
        f"[padded][lower]overlay=0:{AVATAR_H}[out]"
    )

    r = subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", avatar_video,  # 0: avatar (looped)
        "-i", clip_path,                             # 1: clip
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "1:a",
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-shortest",
        output_path
    ], capture_output=True, text=True, timeout=600)

    if r.returncode != 0:
        logger.error(f"Clip part failed: {r.stderr[:500]}")
        return False

    logger.info(f"Clip part OK: {ffprobe_duration(output_path):.1f}s — {source_label}")
    return True


def make_transition(output_path: str, duration: float = 0.5) -> bool:
    """Create a glitch transition part."""
    if os.path.exists(GLITCH_TRANSITION):
        r = subprocess.run([
            "ffmpeg", "-y", "-i", GLITCH_TRANSITION,
            "-t", str(duration),
            "-vf", f"scale={WIDTH}:{HEIGHT},fps={FPS}",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            output_path
        ], capture_output=True, text=True, timeout=30)
        return r.returncode == 0

    # Fallback: black frame flash
    r = subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={COLOR_BG}:s={WIDTH}x{HEIGHT}:d={duration}",
        "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
        "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
        output_path
    ], capture_output=True, text=True, timeout=30)
    return r.returncode == 0


# ── Episode Assembly ─────────────────────────────────────────────────────────

def assemble_episode(script: dict, audio_dir: str, clips_dir: str,
                      output_path: str, btc_price: str = "$0") -> dict:
    """Assemble a full PBX episode from script, audio, and clips.

    Args:
        script: Episode script with dialogue list and metadata.
        audio_dir: Directory containing per-line TTS audio files.
        clips_dir: Directory containing extracted YouTube clips.
        output_path: Final output video path.
        btc_price: Current BTC price string for lower third.

    Returns:
        dict with: ok, output_path, duration, parts_count
    """
    dialogue = script.get("dialogue", [])
    work_dir = os.path.join(os.path.dirname(output_path), "work")
    os.makedirs(work_dir, exist_ok=True)

    parts = []
    part_idx = 0

    # Step 1: Generate PBX avatar video (entire narration)
    full_audio = os.path.join(audio_dir, "full_dialogue.m4a")
    avatar_video = os.path.join(work_dir, "pbx_avatar.mp4")

    if os.path.exists(full_audio):
        logger.info("Generating PBX avatar video...")
        generate_wav2lip_avatar(full_audio, avatar_video)
    else:
        logger.warning("No full_dialogue.m4a — using static avatar")
        avatar_video = PBX_BASE_VIDEO

    # Step 2: Build parts for each dialogue entry
    audio_offset = 0.0  # Track position in full_dialogue for segment extraction

    for i, entry in enumerate(dialogue):
        entry_type = entry.get("type", "")
        host = entry.get("host", 2)

        part_path = os.path.join(work_dir, f"part_{part_idx:03d}.mp4")

        if host == "CLIP":
            # Insert transition before clip
            trans_path = os.path.join(work_dir, f"trans_{part_idx:03d}.mp4")
            if make_transition(trans_path):
                parts.append(trans_path)
                part_idx += 1
                part_path = os.path.join(work_dir, f"part_{part_idx:03d}.mp4")

            # Clip segment
            rank = entry.get("rank", 1)
            clip_file = _find_clip(clips_dir, rank, entry)
            if clip_file:
                source = entry.get("channel", entry.get("source", f"Clip #{rank}"))
                clip_dur = entry.get("duration", ffprobe_duration(clip_file))
                if make_clip_part(avatar_video, clip_file, source, part_path, clip_dur):
                    parts.append(part_path)
                    part_idx += 1

            # Transition after clip
            trans_path = os.path.join(work_dir, f"trans_{part_idx:03d}.mp4")
            if make_transition(trans_path):
                parts.append(trans_path)
                part_idx += 1

        elif entry.get("text", "").strip():
            # Narration segment — find its audio file
            line_audio = os.path.join(audio_dir, f"line_{i:04d}.m4a")
            if not os.path.exists(line_audio):
                logger.warning(f"Missing audio for line {i}: {entry.get('text', '')[:50]}")
                continue

            topic = entry.get("topic", entry.get("text", "")[:60])
            dur = ffprobe_duration(line_audio)

            if make_narration_part(avatar_video, line_audio, topic, btc_price, part_path, dur):
                parts.append(part_path)
                part_idx += 1

    if not parts:
        logger.error("No parts assembled!")
        return {"ok": False, "error": "No parts"}

    # Step 3: Add intro and outro
    all_parts = []

    # Intro
    if os.path.exists(INTRO_VIDEO):
        intro_part = os.path.join(work_dir, "intro_scaled.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", INTRO_VIDEO,
            "-vf", f"scale={WIDTH}:{HEIGHT},fps={FPS}",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-t", "5",
            intro_part
        ], capture_output=True, text=True, timeout=60)
        if os.path.exists(intro_part):
            all_parts.append(intro_part)

    all_parts.extend(parts)

    # Outro
    if os.path.exists(OUTRO_VIDEO):
        outro_part = os.path.join(work_dir, "outro_scaled.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", OUTRO_VIDEO,
            "-vf", f"scale={WIDTH}:{HEIGHT},fps={FPS}",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-t", "5",
            outro_part
        ], capture_output=True, text=True, timeout=60)
        if os.path.exists(outro_part):
            all_parts.append(outro_part)

    # Step 4: Concatenate all parts
    logger.info(f"Concatenating {len(all_parts)} parts...")
    concat_list = os.path.join(work_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for p in all_parts:
            f.write(f"file '{p}'\n")

    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-fflags", "+genpts+igndts",
        "-avoid_negative_ts", "make_zero",
        output_path
    ], capture_output=True, text=True, timeout=900)

    if r.returncode != 0:
        logger.error(f"Concat failed: {r.stderr[:500]}")
        return {"ok": False, "error": "concat failed"}

    final_dur = ffprobe_duration(output_path)
    logger.info(f"Episode assembled: {final_dur:.1f}s, {len(all_parts)} parts → {output_path}")

    return {
        "ok": True,
        "output_path": output_path,
        "duration": final_dur,
        "parts_count": len(all_parts),
    }


def _find_clip(clips_dir: str, rank: int, entry: dict) -> str:
    """Find clip file by rank or video_id."""
    if not os.path.isdir(clips_dir):
        return ""

    # Try by video_id
    vid = entry.get("video_id", "")
    if vid:
        for ext in (".mp4", ".webm", ".mkv"):
            path = os.path.join(clips_dir, f"{vid}{ext}")
            if os.path.exists(path):
                return path

    # Try by rank
    for ext in (".mp4", ".webm", ".mkv"):
        path = os.path.join(clips_dir, f"clip_{rank}{ext}")
        if os.path.exists(path):
            return path

    # Try any clip by pattern
    pattern = os.path.join(clips_dir, f"*rank{rank}*")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]

    # Fallback: first available clip
    all_clips = glob.glob(os.path.join(clips_dir, "*.mp4"))
    if all_clips and rank <= len(all_clips):
        return sorted(all_clips)[rank - 1]

    logger.warning(f"Clip not found: rank={rank}, video_id={vid}")
    return ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    print("PBX Assembler ready.")
    print(f"  Avatar base: {PBX_BASE_VIDEO} (exists: {os.path.exists(PBX_BASE_VIDEO)})")
    print(f"  Intro: {os.path.exists(INTRO_VIDEO)}")
    print(f"  Outro: {os.path.exists(OUTRO_VIDEO)}")
    print(f"  Glitch: {os.path.exists(GLITCH_TRANSITION)}")
