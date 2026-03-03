"""
Local Assembler
================
Replaces the HTTP-based UltronAssembler with local moviepy/ffmpeg operations.
Assembles horizontal (16:9), vertical (9:16), and audio-only outputs
using the same AssemblyManifest schema.
"""
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from services.video_engine.editorial.schemas import AssemblyManifest, TimelineEntry
from services.video_engine.assembly import ffmpeg_ops

logger = logging.getLogger("LocalAssembler")

# Standard output dimensions
HORIZONTAL = (1920, 1080)
VERTICAL = (1080, 1920)
FPS = 30


class LocalAssembler:
    """Assemble videos locally using ffmpeg."""

    def __init__(self, work_dir: str = None):
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="pulse_asm_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._segment_index = 0

    def assemble_horizontal(self, manifest: AssemblyManifest,
                             bundle_path: Path = None) -> Optional[dict]:
        """
        Assemble the horizontal (16:9) master video from timeline entries.
        Returns dict with status, output_path, size_mb, segments_used.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"LOCAL ASSEMBLY — Horizontal 1920x1080")
        logger.info(f"{'='*60}")

        output_dir = (bundle_path / "final") if bundle_path else self.work_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / manifest.output_name

        segment_clips = []
        segments_used = 0

        for i, entry in enumerate(manifest.timeline):
            try:
                clip_path = self._render_entry(entry, i, HORIZONTAL)
                if clip_path and Path(clip_path).exists():
                    segment_clips.append(clip_path)
                    segments_used += 1
                    logger.info(f"  [{i+1}/{len(manifest.timeline)}] {entry.entry_type} OK")
                else:
                    logger.warning(f"  [{i+1}/{len(manifest.timeline)}] {entry.entry_type} skipped (no output)")
            except Exception as e:
                logger.error(f"  [{i+1}/{len(manifest.timeline)}] {entry.entry_type} failed: {e}")

        if not segment_clips:
            logger.error("  No segments rendered — assembly failed")
            return None

        # Concatenate all segments
        logger.info(f"\n  Concatenating {len(segment_clips)} segments...")
        try:
            raw_output = str(self.work_dir / "raw_concat.mp4")
            ffmpeg_ops.concat_clips(segment_clips, raw_output, copy_codec=False)

            # Final loudnorm pass
            logger.info("  Applying loudness normalization...")
            ffmpeg_ops.loudnorm(raw_output, str(output_path))
        except Exception as e:
            logger.error(f"  Concat/loudnorm failed: {e}")
            # Fallback: use raw concat without loudnorm
            if os.path.exists(raw_output):
                import shutil
                shutil.copy2(raw_output, str(output_path))
            else:
                return None

        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            info = ffmpeg_ops.probe(str(output_path))
            logger.info(f"\n  Assembly complete: {output_path.name}")
            logger.info(f"    Size: {size_mb:.1f} MB")
            logger.info(f"    Duration: {info['duration']:.1f}s")
            logger.info(f"    Segments: {segments_used}")
            return {
                "status": "complete",
                "output_path": str(output_path),
                "size_mb": round(size_mb, 1),
                "duration": info["duration"],
                "segments_used": segments_used,
            }

        return None

    def assemble_vertical(self, manifest: AssemblyManifest,
                           bundle_path: Path = None) -> Optional[dict]:
        """Assemble vertical (9:16) version."""
        logger.info(f"\n{'='*60}")
        logger.info(f"LOCAL ASSEMBLY — Vertical 1080x1920")
        logger.info(f"{'='*60}")

        output_dir = (bundle_path / "shorts") if bundle_path else self.work_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        output_name = manifest.output_name.replace(".mp4", "_vertical.mp4")
        output_path = output_dir / output_name

        segment_clips = []
        for i, entry in enumerate(manifest.timeline):
            try:
                clip_path = self._render_entry(entry, i, VERTICAL, suffix="_vert")
                if clip_path and Path(clip_path).exists():
                    segment_clips.append(clip_path)
            except Exception as e:
                logger.warning(f"  Vertical entry {i} failed: {e}")

        if not segment_clips:
            return None

        ffmpeg_ops.concat_clips(segment_clips, str(output_path), copy_codec=False)

        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            return {
                "status": "complete",
                "output_path": str(output_path),
                "size_mb": round(size_mb, 1),
            }
        return None

    def export_audio_only(self, video_path: str, output_dir: str = None) -> Optional[str]:
        """Export audio-only podcast version from assembled video."""
        video = Path(video_path)
        if not video.exists():
            logger.error(f"  Video not found: {video_path}")
            return None

        out_dir = Path(output_dir) if output_dir else video.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        audio_path = out_dir / (video.stem + "_audio.mp3")

        try:
            ffmpeg_ops.extract_audio(str(video), str(audio_path))
            logger.info(f"  Exported podcast audio: {audio_path.name}")
            return str(audio_path)
        except Exception as e:
            logger.error(f"  Audio export failed: {e}")
            return None

    def _render_entry(self, entry: TimelineEntry, index: int,
                      dimensions: tuple, suffix: str = "") -> Optional[str]:
        """
        Render a single timeline entry to a video clip.
        Returns path to the rendered clip, or None.
        """
        w, h = dimensions
        self._segment_index += 1
        seg_path = str(self.work_dir / f"seg_{self._segment_index:04d}{suffix}.mp4")

        if entry.entry_type == "clip":
            return self._render_clip(entry, seg_path, w, h)
        elif entry.entry_type == "voiceover":
            return self._render_voiceover(entry, seg_path, w, h)
        elif entry.entry_type == "tweet_overlay":
            return self._render_tweet_overlay(entry, seg_path, w, h)
        elif entry.entry_type in ("branded_intro", "branded_outro"):
            return self._render_branded(entry, seg_path, w, h)
        elif entry.entry_type == "signal_vs_noise":
            return self._render_voiceover(entry, seg_path, w, h)
        else:
            logger.warning(f"  Unknown entry type: {entry.entry_type}")
            return None

    def _render_clip(self, entry: TimelineEntry, seg_path: str,
                     w: int, h: int) -> Optional[str]:
        """Render a source video clip, scaled to target dimensions with lower third."""
        source = entry.source_video_path
        if not source or not Path(source).exists():
            logger.warning(f"  Clip source missing: {source}")
            return None

        # Scale source clip to target dimensions
        scaled = seg_path.replace(".mp4", "_scaled.mp4")
        ffmpeg_ops.scale_and_pad(source, scaled, w, h)

        # Add lower third if specified
        if entry.lower_third_name:
            lt_text = entry.lower_third_name
            if entry.lower_third_title:
                lt_text += f" | {entry.lower_third_title}"

            return ffmpeg_ops.add_text_overlay(
                scaled, lt_text, seg_path,
                fontsize=36, fontcolor="white",
                x="40", y=f"{h - 80}",
                box=True, boxcolor="black@0.7"
            )

        os.rename(scaled, seg_path)
        return seg_path

    def _render_voiceover(self, entry: TimelineEntry, seg_path: str,
                          w: int, h: int) -> Optional[str]:
        """Render voiceover audio over a dark background or visual."""
        audio = entry.audio_path
        if not audio or not Path(audio).exists():
            # No audio — generate a short silent segment if duration specified
            if entry.duration_sec and entry.duration_sec > 0:
                return ffmpeg_ops.generate_color_clip(
                    seg_path, duration=entry.duration_sec,
                    color="0x0a0f0a", w=w, h=h
                )
            return None

        # If there's an image for the visual, use it
        if entry.image_path and Path(entry.image_path).exists():
            return ffmpeg_ops.audio_over_image(entry.image_path, audio, seg_path)

        # Default: dark background + audio
        bg_path = seg_path.replace(".mp4", "_bg.png")
        self._generate_dark_bg(bg_path, w, h)
        return ffmpeg_ops.audio_over_image(bg_path, audio, seg_path)

    def _render_tweet_overlay(self, entry: TimelineEntry, seg_path: str,
                              w: int, h: int) -> Optional[str]:
        """Render tweet card image with narrator audio."""
        image = entry.image_path
        audio = entry.audio_path

        if image and Path(image).exists():
            if audio and Path(audio).exists():
                return ffmpeg_ops.audio_over_image(image, audio, seg_path)
            else:
                duration = entry.duration_sec or 5
                return ffmpeg_ops.image_to_video(image, seg_path, duration=duration)

        # Fallback: no image, just voiceover on dark bg
        if audio and Path(audio).exists():
            bg_path = seg_path.replace(".mp4", "_bg.png")
            self._generate_dark_bg(bg_path, w, h)
            return ffmpeg_ops.audio_over_image(bg_path, audio, seg_path)

        return None

    def _render_branded(self, entry: TimelineEntry, seg_path: str,
                        w: int, h: int) -> Optional[str]:
        """Render branded intro/outro bumper."""
        duration = entry.duration_sec or 4

        # Check if pre-rendered video bumper exists
        source = entry.source_video_path or entry.visual
        if source and Path(str(source)).exists() and str(source).endswith(".mp4"):
            ffmpeg_ops.scale_and_pad(str(source), seg_path, w, h)
            return seg_path

        # Check if pre-rendered image exists
        if entry.visual and Path(str(entry.visual)).exists():
            return ffmpeg_ops.image_to_video(str(entry.visual), seg_path, duration=duration)

        # Generate placeholder color clip
        return ffmpeg_ops.generate_color_clip(
            seg_path, duration=duration,
            color="0x0a0f0a", w=w, h=h
        )

    def _generate_dark_bg(self, output_path: str, w: int = 1920, h: int = 1080):
        """Generate a dark background image using Pillow."""
        try:
            from PIL import Image
            img = Image.new("RGB", (w, h), (10, 15, 10))  # #0a0f0a
            img.save(output_path)
        except Exception:
            # Fallback: generate with ffmpeg
            import subprocess
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"color=c=0x0a0f0a:s={w}x{h}:d=0.1",
                "-frames:v", "1", output_path
            ], capture_output=True, timeout=10)
