"""
Shorts Builder
===============
Creates vertical (9:16, 1080x1920) short-form clips for TikTok/IG/YT Shorts.
Each short: hook text → narrator setup → clip excerpt → takeaway → CTA.
Under 60 seconds, branded top/bottom bars.
"""
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

from services.video_engine.assembly import ffmpeg_ops

logger = logging.getLogger("ShortsBuilder")

W, H = 1080, 1920
FPS = 30
RED = (204, 34, 34)
WHITE = (255, 255, 255)
GRAY = (156, 163, 175)
BG_COLOR = (10, 15, 10)

FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def _font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


class ShortsBuilder:
    """Build vertical shorts from show plan."""

    def __init__(self, work_dir: str = None):
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="shorts_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def build_all_shorts(self, show_plan: dict,
                          audio_map: Dict[str, str],
                          clip_map: Dict[str, str],
                          output_dir: str) -> List[dict]:
        """
        Build all shorts from the shorts_plan in show plan.
        Returns list of result dicts.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        shorts_plan = show_plan.get("shorts_plan", [])
        if not shorts_plan:
            logger.info("  No shorts plan — skipping")
            return []

        results = []
        for i, short in enumerate(shorts_plan):
            logger.info(f"  Building short {i}...")
            result = self._build_single_short(i, short, show_plan,
                                                audio_map, clip_map, output_path)
            if result:
                results.append(result)
                logger.info(f"    + {result['filename']} ({result.get('duration', 0):.0f}s)")
            else:
                logger.warning(f"    - Short {i} failed")

        logger.info(f"  Shorts: {len(results)}/{len(shorts_plan)} created")
        return results

    def _build_single_short(self, index: int, short: dict,
                              show_plan: dict, audio_map: Dict[str, str],
                              clip_map: Dict[str, str],
                              output_dir: Path) -> Optional[dict]:
        """Build a single vertical short."""
        story_ref = short.get("story_ref", 1)
        clip_ref = short.get("clip_ref", 0)
        hook_text = short.get("hook_text", "")
        cta = short.get("cta", "Full Pulse Check in bio.")

        clip_id = f"story{story_ref}_clip{clip_ref}"
        clip_file = clip_map.get(clip_id)

        segments = []

        # Segment 1: Hook card (3 seconds)
        if hook_text:
            hook_path = str(self.work_dir / f"short{index}_hook.mp4")
            self._render_hook_card(hook_text, hook_path)
            if Path(hook_path).exists():
                segments.append(hook_path)

        # Segment 2: Clip (vertical crop, max 45s)
        if clip_file and Path(clip_file).exists():
            vert_clip = str(self.work_dir / f"short{index}_clip.mp4")
            self._make_vertical_clip(clip_file, vert_clip, max_duration=45)
            if Path(vert_clip).exists():
                segments.append(vert_clip)
        else:
            # No clip — use narrator intro audio over branded bg
            intro_audio = audio_map.get(f"story{story_ref}_intro")
            if intro_audio and Path(intro_audio).exists():
                vo_seg = str(self.work_dir / f"short{index}_vo.mp4")
                bg_img = str(self.work_dir / f"short{index}_bg.png")
                self._render_branded_bg(bg_img)
                ffmpeg_ops.audio_over_image(bg_img, intro_audio, vo_seg)
                # Make it vertical
                vert_vo = str(self.work_dir / f"short{index}_vo_vert.mp4")
                ffmpeg_ops.scale_and_pad(vo_seg, vert_vo, W, H)
                if Path(vert_vo).exists():
                    segments.append(vert_vo)

        # Segment 3: CTA card (3 seconds)
        cta_path = str(self.work_dir / f"short{index}_cta.mp4")
        self._render_cta_card(cta, cta_path)
        if Path(cta_path).exists():
            segments.append(cta_path)

        if not segments:
            return None

        # Concatenate
        date_str = show_plan.get("episode_date", "unknown")
        filename = f"short_{index:02d}_{date_str}.mp4"
        output_path = str(output_dir / filename)

        ffmpeg_ops.concat_clips(segments, output_path, copy_codec=False)

        if Path(output_path).exists():
            info = ffmpeg_ops.probe(output_path)
            duration = info.get("duration", 0)

            # Trim to 60s max
            if duration > 60:
                trimmed = output_path.replace(".mp4", "_trim.mp4")
                ffmpeg_ops.trim_clip(output_path, trimmed, 0, 59)
                os.replace(trimmed, output_path)
                duration = 59

            return {
                "filename": filename,
                "output_path": output_path,
                "duration": duration,
                "width": info.get("width", W),
                "height": info.get("height", H),
                "hook_text": hook_text,
            }

        return None

    def _make_vertical_clip(self, source: str, output: str,
                              max_duration: float = 45):
        """Crop/pad a horizontal clip to vertical 1080x1920."""
        # First trim to max duration
        info = ffmpeg_ops.probe(source)
        duration = min(info.get("duration", max_duration), max_duration)

        trimmed = output.replace(".mp4", "_trimmed.mp4")
        ffmpeg_ops.trim_clip(source, trimmed, 0, duration)

        # Scale and pad to vertical
        ffmpeg_ops.scale_and_pad(trimmed, output, W, H)
        Path(trimmed).unlink(missing_ok=True)

    def _render_hook_card(self, text: str, output_path: str, duration: float = 3):
        """Render a 3-second hook text card at 1080x1920."""
        frame_dir = tempfile.mkdtemp(prefix="hook_")
        font_hook = _font(FONT_SANS_BOLD, 72)
        font_badge = _font(FONT_SANS_BOLD, 28)
        total_frames = int(duration * FPS)

        try:
            for f in range(total_frames):
                img = Image.new("RGB", (W, H), BG_COLOR)
                draw = ImageDraw.Draw(img)

                # Red accent
                draw.rectangle([0, 0, W, 4], fill=RED)
                draw.rectangle([0, H - 4, W, H], fill=RED)

                # PULSE CHECK badge
                badge = "PULSE CHECK"
                bbx = font_badge.getbbox(badge)
                bw = bbx[2] - bbx[0]
                draw.rectangle([(W - bw) // 2 - 15, 100, (W + bw) // 2 + 15, 145], fill=RED)
                draw.text(((W - bw) // 2, 103), badge, font=font_badge, fill=WHITE)

                # Hook text centered
                import textwrap
                wrapped = textwrap.fill(text.upper(), width=14)
                lines = wrapped.split("\n")
                line_h = 90
                start_y = (H - len(lines) * line_h) // 2

                for i, line in enumerate(lines):
                    lbbox = font_hook.getbbox(line)
                    lw = lbbox[2] - lbbox[0]
                    x = (W - lw) // 2
                    y = start_y + i * line_h
                    draw.text((x + 3, y + 3), line, font=font_hook, fill=(20, 20, 20))
                    draw.text((x, y), line, font=font_hook, fill=WHITE)

                img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

            ffmpeg_ops.frames_to_video(
                os.path.join(frame_dir, "frame_%04d.png"),
                output_path, fps=FPS
            )
        finally:
            shutil.rmtree(frame_dir, ignore_errors=True)

    def _render_cta_card(self, text: str, output_path: str, duration: float = 3):
        """Render a CTA end card."""
        frame_dir = tempfile.mkdtemp(prefix="cta_")
        font_cta = _font(FONT_SANS_BOLD, 48)
        font_badge = _font(FONT_SANS_BOLD, 28)
        total_frames = int(duration * FPS)

        try:
            for f in range(total_frames):
                img = Image.new("RGB", (W, H), BG_COLOR)
                draw = ImageDraw.Draw(img)

                draw.rectangle([0, 0, W, 4], fill=RED)
                draw.rectangle([0, H - 4, W, H], fill=RED)

                # Center line
                draw.rectangle([W // 2 - 200, H // 2 - 2, W // 2 + 200, H // 2 + 2], fill=RED)

                # Badge above
                badge = "PULSE CHECK"
                bbx = font_badge.getbbox(badge)
                bw = bbx[2] - bbx[0]
                draw.rectangle([(W - bw) // 2 - 15, H // 2 - 80, (W + bw) // 2 + 15, H // 2 - 40],
                               fill=RED)
                draw.text(((W - bw) // 2, H // 2 - 77), badge, font=font_badge, fill=WHITE)

                # CTA text below
                import textwrap
                wrapped = textwrap.fill(text, width=24)
                lines = wrapped.split("\n")
                for i, line in enumerate(lines):
                    lbbox = font_cta.getbbox(line)
                    lw = lbbox[2] - lbbox[0]
                    draw.text(((W - lw) // 2, H // 2 + 30 + i * 60), line,
                              font=font_cta, fill=WHITE)

                img.save(os.path.join(frame_dir, f"frame_{f:04d}.png"))

            ffmpeg_ops.frames_to_video(
                os.path.join(frame_dir, "frame_%04d.png"),
                output_path, fps=FPS
            )
        finally:
            shutil.rmtree(frame_dir, ignore_errors=True)

    def _render_branded_bg(self, output_path: str):
        """Render a branded vertical background image."""
        img = Image.new("RGB", (W, H), BG_COLOR)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, W, 4], fill=RED)
        draw.rectangle([0, H - 4, W, H], fill=RED)
        font = _font(FONT_MONO, 18)
        draw.text((W - 200, H - 40), "PULSE CHECK", font=font, fill=(25, 30, 25))
        img.save(output_path)
