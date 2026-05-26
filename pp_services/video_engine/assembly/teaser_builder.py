"""
Teaser Builder
===============
Creates a ~90-second teaser trailer for X/Twitter from the episode's best moments.
Hook1 → red flash → Hook2 → red flash → Hook3 → CTA
"""
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

from pp_services.video_engine.assembly import ffmpeg_ops

logger = logging.getLogger("TeaserBuilder")

W, H = 1920, 1080
FPS = 30
RED = (204, 34, 34)
WHITE = (255, 255, 255)
BG_COLOR = (10, 15, 10)

FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def _font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def build_teaser(show_plan: dict, clip_map: Dict[str, str],
                 audio_map: Dict[str, str],
                 output_path: str, max_duration: float = 90) -> Optional[str]:
    """
    Build a teaser trailer from the episode's best clips.

    Grabs 15-25s from each story clip, stitches with red flash transitions,
    ends with CTA card.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="teaser_"))
    segments = []
    per_clip_max = 20

    try:
        stories = show_plan.get("stories", [])

        # Gather clips
        for story in stories:
            sn = story.get("story_number", 0)
            for ci, clip in enumerate(story.get("clips", [])):
                clip_id = f"story{sn}_clip{ci}"
                clip_file = clip_map.get(clip_id)
                if not clip_file or not Path(clip_file).exists():
                    continue

                # Trim to first per_clip_max seconds
                trimmed = str(work_dir / f"teaser_clip_{sn}_{ci}.mp4")
                info = ffmpeg_ops.probe(clip_file)
                dur = min(info.get("duration", per_clip_max), per_clip_max)
                ffmpeg_ops.trim_clip(clip_file, trimmed, 0, dur)

                # Scale to 1920x1080
                scaled = str(work_dir / f"teaser_clip_{sn}_{ci}_scaled.mp4")
                ffmpeg_ops.scale_and_pad(trimmed, scaled, W, H)

                if Path(scaled).exists():
                    segments.append(scaled)

                    # Add red flash transition (0.5s)
                    flash = str(work_dir / f"flash_{sn}_{ci}.mp4")
                    _render_red_flash(flash, duration=0.5)
                    if Path(flash).exists():
                        segments.append(flash)

        if not segments:
            # Fallback: use cold open + outro audio over branded bg
            cold_audio = audio_map.get("cold_open")
            if cold_audio and Path(cold_audio).exists():
                bg = str(work_dir / "bg.png")
                _render_branded_bg(bg)
                seg = str(work_dir / "cold_open_seg.mp4")
                ffmpeg_ops.audio_over_image(bg, cold_audio, seg)
                segments.append(seg)

        if not segments:
            logger.warning("  No segments for teaser")
            return None

        # Add CTA card at the end
        cta = str(work_dir / "cta.mp4")
        _render_cta_card(cta, "Full episode at protocolpulse.io", duration=4)
        if Path(cta).exists():
            segments.append(cta)

        # Remove trailing flash if present
        if segments and "flash" in segments[-2]:
            segments.pop(-2)

        # Concatenate
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_ops.concat_clips(segments, output_path, copy_codec=False)

        if Path(output_path).exists():
            info = ffmpeg_ops.probe(output_path)
            duration = info.get("duration", 0)

            # Trim if over max
            if duration > max_duration:
                trimmed = output_path.replace(".mp4", "_trim.mp4")
                ffmpeg_ops.trim_clip(output_path, trimmed, 0, max_duration)
                os.replace(trimmed, output_path)

            logger.info(f"  Teaser built: {Path(output_path).name} "
                        f"({info.get('duration', 0):.0f}s)")
            return output_path

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return None


def _render_red_flash(output_path: str, duration: float = 0.5):
    """Render a red flash transition."""
    frame_dir = tempfile.mkdtemp(prefix="flash_")
    total_frames = max(int(duration * FPS), 2)

    try:
        for f in range(total_frames):
            img = Image.new("RGB", (W, H), BG_COLOR)
            draw = ImageDraw.Draw(img)

            # Red intensity peaks in middle
            progress = f / max(total_frames - 1, 1)
            intensity = 1.0 - abs(progress - 0.5) * 2
            r = int(204 * intensity)
            draw.rectangle([0, 0, W, H], fill=(r, 10, 10))

            # Center line
            draw.rectangle([0, H // 2 - 3, W, H // 2 + 3], fill=RED)

            img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

        ffmpeg_ops.frames_to_video(
            os.path.join(frame_dir, "frame_%04d.png"),
            output_path, fps=FPS
        )
    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)


def _render_cta_card(output_path: str, text: str, duration: float = 4):
    """Render a CTA end card."""
    frame_dir = tempfile.mkdtemp(prefix="cta_")
    font_cta = _font(FONT_SANS_BOLD, 56)
    font_badge = _font(FONT_SANS_BOLD, 36)
    font_wm = _font(FONT_MONO, 18)
    total_frames = int(duration * FPS)

    try:
        for f in range(total_frames):
            img = Image.new("RGB", (W, H), BG_COLOR)
            draw = ImageDraw.Draw(img)

            draw.rectangle([0, 0, W, 4], fill=RED)
            draw.rectangle([0, H - 4, W, H], fill=RED)

            # PULSE CHECK badge
            badge = "PULSE CHECK"
            bbx = font_badge.getbbox(badge)
            bw = bbx[2] - bbx[0]
            draw.rectangle([(W - bw) // 2 - 20, H // 2 - 100,
                            (W + bw) // 2 + 20, H // 2 - 50], fill=RED)
            draw.text(((W - bw) // 2, H // 2 - 97), badge,
                      font=font_badge, fill=WHITE)

            # Center line
            draw.rectangle([W // 4, H // 2 - 2, W * 3 // 4, H // 2 + 2], fill=RED)

            # CTA text
            cbx = font_cta.getbbox(text)
            cw = cbx[2] - cbx[0]
            draw.text(((W - cw) // 2, H // 2 + 30), text,
                      font=font_cta, fill=WHITE)

            # Watermark
            draw.text((W - 220, H - 35), "PROTOCOL PULSE",
                      font=font_wm, fill=(25, 30, 25))

            img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

        ffmpeg_ops.frames_to_video(
            os.path.join(frame_dir, "frame_%04d.png"),
            output_path, fps=FPS
        )
    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)


def _render_branded_bg(output_path: str):
    """Render dark branded background."""
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 3], fill=RED)
    draw.rectangle([0, H - 3, W, H], fill=RED)
    img.save(output_path)
