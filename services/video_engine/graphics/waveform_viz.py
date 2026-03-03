"""
Audio Waveform Visualization
==============================
Generates animated waveform videos from audio for cinematic audio segments.
When showing Spaces clips or podcast segments, the waveform provides
visual interest for audio-only content.
"""
import logging
import os
import shutil
import struct
import tempfile
import wave
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from services.video_engine.assembly import ffmpeg_ops

logger = logging.getLogger("WaveformViz")

# Design
W, H = 1920, 1080
BG_COLOR = (10, 15, 10)
RED = (204, 34, 34)
DARK_RED = (120, 20, 20)
WHITE = (255, 255, 255)
GRAY = (160, 160, 160)
FPS = 30

FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def _font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def audio_to_waveform_video(audio_path: str, output_path: str,
                            duration: float = None,
                            color: str = "#CC2222",
                            bg_color: str = "#0a0f0a",
                            style: str = "bars") -> str:
    """
    Generate a waveform visualization video from audio.

    Uses ffmpeg showwaves for fast generation, with Pillow frame rendering
    as a more cinematic alternative.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if style == "ffmpeg_waves":
        return _waveform_ffmpeg(audio_path, output_path, color)

    # Default: Pillow-rendered bars (more cinematic)
    return _waveform_pillow_bars(audio_path, output_path, duration)


def render_audio_segment(audio_path: str, speaker_name: str,
                         topic: str, output_path: str,
                         source_badge: str = "Audio") -> str:
    """
    Render a complete audio segment with:
    - Dark background (1920x1080)
    - Speaker name + topic at top
    - Animated waveform in center
    - Source badge at bottom
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Get audio duration
    info = ffmpeg_ops.probe(audio_path)
    duration = info.get("duration", 10)

    total_frames = int(duration * FPS)
    if total_frames < 1:
        total_frames = FPS  # minimum 1 second

    # Load audio samples for waveform
    samples = _load_audio_samples(audio_path, total_frames)

    frame_dir = tempfile.mkdtemp(prefix="wave_seg_")
    font_name = _font(FONT_SANS_BOLD, 48)
    font_topic = _font(FONT_SANS, 32)
    font_badge = _font(FONT_SANS_BOLD, 24)
    font_wm = _font(FONT_MONO, 18)

    try:
        for f in range(total_frames):
            img = Image.new("RGB", (W, H), BG_COLOR)
            draw = ImageDraw.Draw(img)

            # Top bar: red accent
            draw.rectangle([0, 0, W, 3], fill=RED)

            # Speaker name (centered)
            bbox_n = font_name.getbbox(speaker_name)
            nw = bbox_n[2] - bbox_n[0]
            draw.text(((W - nw) // 2, 80), speaker_name, font=font_name, fill=WHITE)

            # Topic
            bbox_t = font_topic.getbbox(topic)
            tw = bbox_t[2] - bbox_t[0]
            draw.text(((W - tw) // 2, 145), topic, font=font_topic, fill=GRAY)

            # Waveform bars (center area, y=350 to y=730)
            _draw_waveform_bars(draw, samples, f, total_frames,
                               y_center=540, bar_area_w=1600, max_h=300)

            # Source badge
            badge_text = f"  {source_badge}  "
            bbox_b = font_badge.getbbox(badge_text)
            bw = bbox_b[2] - bbox_b[0]
            badge_x = (W - bw) // 2
            draw.rectangle([badge_x - 5, H - 120, badge_x + bw + 5, H - 85],
                          fill=RED)
            draw.text((badge_x, H - 118), badge_text, font=font_badge, fill=WHITE)

            # Watermark
            draw.text((W - 220, H - 40), "PULSE CHECK", font=font_wm, fill=(30, 35, 30))

            img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

        # Encode with audio
        ffmpeg_ops.frames_to_video(
            os.path.join(frame_dir, "frame_%04d.png"),
            output_path, fps=FPS, audio_path=audio_path
        )
        logger.info(f"  Audio segment rendered: {speaker_name} ({duration:.1f}s)")
        return output_path

    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)


def _waveform_ffmpeg(audio_path: str, output_path: str, color: str) -> str:
    """Fast waveform using ffmpeg showwaves filter."""
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-filter_complex",
        f"[0:a]showwaves=s={W}x400:mode=cline:rate={FPS}:colors={color},"
        f"pad={W}:{H}:0:{(H-400)//2}:color=0x0a0f0a[v]",
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    ffmpeg_ops._run(cmd, timeout=300, label="waveform_ffmpeg")
    return output_path


def _waveform_pillow_bars(audio_path: str, output_path: str,
                          duration: float = None) -> str:
    """Render animated bar waveform with Pillow frames."""
    info = ffmpeg_ops.probe(audio_path)
    dur = duration or info.get("duration", 10)
    total_frames = int(dur * FPS)

    samples = _load_audio_samples(audio_path, total_frames)

    frame_dir = tempfile.mkdtemp(prefix="wave_frames_")

    try:
        for f in range(total_frames):
            img = Image.new("RGB", (W, H), BG_COLOR)
            draw = ImageDraw.Draw(img)

            _draw_waveform_bars(draw, samples, f, total_frames,
                               y_center=H // 2, bar_area_w=1700, max_h=400)

            img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

        ffmpeg_ops.frames_to_video(
            os.path.join(frame_dir, "frame_%04d.png"),
            output_path, fps=FPS, audio_path=audio_path
        )
        return output_path

    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)


def _draw_waveform_bars(draw: ImageDraw.ImageDraw, samples: list,
                        frame: int, total_frames: int,
                        y_center: int = 540, bar_area_w: int = 1600,
                        max_h: int = 300, num_bars: int = 64):
    """Draw mirrored waveform bars for a single frame."""
    x_start = (W - bar_area_w) // 2
    bar_w = bar_area_w // num_bars - 2
    gap = 2

    # Window of samples around current frame
    window_size = max(num_bars, 32)
    center_idx = int((frame / max(total_frames - 1, 1)) * max(len(samples) - 1, 1))

    for i in range(num_bars):
        # Get sample value for this bar
        sample_idx = center_idx - num_bars // 2 + i
        if 0 <= sample_idx < len(samples):
            val = samples[sample_idx]
        else:
            val = 0

        bar_h = int(val * max_h)
        bar_h = max(bar_h, 3)  # minimum visible height

        x = x_start + i * (bar_w + gap)

        # Color gradient: brighter for taller bars
        intensity = min(1.0, val * 2)
        r = int(120 + 84 * intensity)
        g = int(20 + 14 * intensity)
        b = int(20 + 14 * intensity)
        color = (r, g, b)

        # Top half (above center)
        draw.rectangle([x, y_center - bar_h, x + bar_w, y_center], fill=color)
        # Bottom half (mirror)
        draw.rectangle([x, y_center, x + bar_w, y_center + bar_h], fill=color)


def _load_audio_samples(audio_path: str, num_frames: int) -> list:
    """Load audio and compute RMS energy per video frame."""
    # Convert to wav for easy loading
    wav_path = audio_path
    if not audio_path.endswith(".wav"):
        wav_path = audio_path + ".temp.wav"
        try:
            ffmpeg_ops._run([
                "ffmpeg", "-y", "-i", audio_path,
                "-ar", "16000", "-ac", "1", wav_path
            ], timeout=60, label="wav_convert")
        except Exception:
            return [0.1] * num_frames

    try:
        with wave.open(wav_path, "r") as wf:
            n_frames = wf.getnframes()
            sample_rate = wf.getframerate()
            raw = wf.readframes(n_frames)

        # Parse samples
        n_channels = 1
        samples = struct.unpack(f"<{n_frames * n_channels}h", raw)

        # Compute RMS per video frame
        samples_per_frame = max(1, len(samples) // max(num_frames, 1))
        rms_values = []

        for f in range(num_frames):
            start = f * samples_per_frame
            end = min(start + samples_per_frame, len(samples))
            chunk = samples[start:end]

            if chunk:
                rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5
                normalized = min(1.0, rms / 12000)
            else:
                normalized = 0

            rms_values.append(normalized)

        return rms_values

    except Exception as e:
        logger.warning(f"  Audio sample loading failed: {e}")
        return [0.1] * num_frames

    finally:
        if wav_path != audio_path and Path(wav_path).exists():
            Path(wav_path).unlink(missing_ok=True)
