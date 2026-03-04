"""
Local Assembler
================
Replaces the HTTP-based UltronAssembler with local moviepy/ffmpeg operations.
Assembles horizontal (16:9), vertical (9:16), and audio-only outputs
using the same AssemblyManifest schema.

Visual polish features:
- Looping tech_grid.mp4 background for host segments
- Background music (-18dB) mixed under voiceovers
- Glitch transitions between segments
- Animated overlays (stat cards, host lower thirds, watermark)
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
        self._audio_settings = {}  # populated from manifest

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

        # Store audio settings for use during rendering
        self._audio_settings = manifest.audio_settings

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

        # Concatenate all segments with crossfade transitions (0.3s overlap)
        logger.info(f"\n  Concatenating {len(segment_clips)} segments with 0.3s crossfades...")
        try:
            raw_output = str(self.work_dir / "raw_concat.mp4")
            ffmpeg_ops.concat_with_crossfade(segment_clips, raw_output, xf_duration=0.3)

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
        elif entry.entry_type == "transition":
            return self._render_transition(entry, seg_path, w, h)
        else:
            logger.warning(f"  Unknown entry type: {entry.entry_type}")
            return None

    def _render_clip(self, entry: TimelineEntry, seg_path: str,
                     w: int, h: int) -> Optional[str]:
        """Render a source video clip, scaled to target dimensions with lower third + watermark."""
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

            with_lt = seg_path.replace(".mp4", "_lt.mp4")
            ffmpeg_ops.add_text_overlay(
                scaled, lt_text, with_lt,
                fontsize=36, fontcolor="white",
                x="40", y=f"{h - 80}",
                box=True, boxcolor="black@0.7"
            )
            scaled = with_lt

        # Add watermark overlay if available
        watermark = self._audio_settings.get("watermark_path")
        if watermark and os.path.exists(watermark):
            try:
                from services.video_engine.graphics.motion_graphics import render_watermark_overlay
                wm_path = str(self.work_dir / f"wm_clip_{self._segment_index}.png")
                render_watermark_overlay(watermark, wm_path, max_size=60)
                if Path(wm_path).exists():
                    dur = ffmpeg_ops.get_duration(scaled)
                    ffmpeg_ops.overlay_png_timed(scaled, wm_path, seg_path,
                                                 x="20", y="20",
                                                 start=0, end=dur)
                    return seg_path
            except Exception as e:
                logger.warning(f"  Clip watermark failed ({e})")

        if scaled != seg_path:
            os.rename(scaled, seg_path)
        return seg_path

    def _render_voiceover(self, entry: TimelineEntry, seg_path: str,
                          w: int, h: int) -> Optional[str]:
        """Render voiceover audio over rotating branded background with bg music + overlays.

        Enhanced flow:
        1. Use per-entry background video (rotated from available backgrounds)
        2. Mix background music at -18dB under TTS
        3. Add stat/quote overlays if dialogue_text is provided
        4. Add host lower third
        5. Add watermark
        """
        audio = entry.audio_path
        if not audio or not Path(audio).exists():
            if entry.duration_sec and entry.duration_sec > 0:
                return ffmpeg_ops.generate_color_clip(
                    seg_path, duration=entry.duration_sec,
                    color="0x0a0f0a", w=w, h=h
                )
            return None

        bg_music = self._audio_settings.get("bg_music_path")
        watermark = self._audio_settings.get("watermark_path")

        # Step 1: Create base video — per-entry background (rotated) or fallback
        # Use source_video_path for the specific background assigned to this entry
        bg_video = entry.source_video_path
        if not bg_video or not Path(bg_video).exists():
            bg_video = self._audio_settings.get("tech_grid_path")

        base_path = seg_path.replace(".mp4", "_base.mp4")
        if bg_video and os.path.exists(bg_video):
            try:
                ffmpeg_ops.audio_over_looping_video(
                    bg_video, audio, base_path,
                    bg_music_path=bg_music,
                    bg_music_vol=0.125,  # ~-18dB
                    w=w, h=h
                )
            except Exception as e:
                logger.warning(f"  Background video failed ({e}), falling back to static")
                base_path = self._fallback_voiceover(entry, base_path, audio, w, h)
        else:
            base_path = self._fallback_voiceover(entry, base_path, audio, w, h)

        if not base_path or not Path(base_path).exists():
            return None

        # Step 2: Build overlay list
        overlays = []
        try:
            from services.video_engine.graphics.motion_graphics import (
                render_stat_overlay, render_host_lower_third,
                render_topic_label, render_watermark_overlay,
                extract_overlay_data
            )
            audio_dur = ffmpeg_ops.get_duration(base_path)

            # Host lower third (appears 0.5s-3.5s)
            if entry.host_name:
                lt_path = str(self.work_dir / f"lt_{self._segment_index}.png")
                host_title = "Senior Analyst" if entry.host_name == "JESSICA" else "Lead Reporter"
                render_host_lower_third(entry.host_name, host_title, lt_path, w, h)
                if Path(lt_path).exists():
                    overlays.append({
                        "path": lt_path, "x": "0", "y": str(h - 160),
                        "start": 0.5, "end": min(3.5, audio_dur - 0.5)
                    })

            # Topic label (top-right, 0-end)
            if entry.topic_label:
                tl_path = str(self.work_dir / f"topic_{self._segment_index}.png")
                render_topic_label(entry.topic_label, tl_path)
                if Path(tl_path).exists():
                    overlays.append({
                        "path": tl_path, "x": f"W-w-30", "y": "30",
                        "start": 0.3, "end": audio_dur
                    })

            # Stat/quote overlays from dialogue text
            if entry.dialogue_text:
                overlay_data = extract_overlay_data(entry.dialogue_text)
                time_offset = 2.0  # Start stats after 2s
                for oi, od in enumerate(overlay_data[:3]):  # Max 3 overlays
                    if od["type"] == "stat":
                        ov_path = str(self.work_dir / f"stat_{self._segment_index}_{oi}.png")
                        render_stat_overlay(od["value"], od.get("label", ""), ov_path, w=500, h=120)
                        if Path(ov_path).exists():
                            start = time_offset + oi * 3.5
                            end = min(start + 3.5, audio_dur - 0.3)
                            if start < audio_dur - 1:
                                overlays.append({
                                    "path": ov_path,
                                    "x": f"W-w-40", "y": f"H/2-60+{oi * 140}",
                                    "start": start, "end": end
                                })

            # Watermark (small, top-left, entire duration)
            if watermark and os.path.exists(watermark):
                wm_path = str(self.work_dir / f"wm_{self._segment_index}.png")
                render_watermark_overlay(watermark, wm_path, max_size=80)
                if Path(wm_path).exists():
                    overlays.append({
                        "path": wm_path, "x": "20", "y": "20",
                        "start": 0, "end": audio_dur
                    })

        except Exception as e:
            logger.warning(f"  Overlay generation failed ({e}), using base video")

        # Step 3: Apply overlays
        if overlays:
            try:
                ffmpeg_ops.multi_overlay(base_path, overlays, seg_path)
                return seg_path
            except Exception as e:
                logger.warning(f"  Overlay apply failed ({e}), using base video")

        # No overlays or overlay failed — use base
        os.rename(base_path, seg_path)
        return seg_path

    def _fallback_voiceover(self, entry: TimelineEntry, seg_path: str,
                             audio: str, w: int, h: int) -> Optional[str]:
        """Fallback voiceover rendering with static image background."""
        if entry.image_path and Path(entry.image_path).exists():
            return ffmpeg_ops.audio_over_image(entry.image_path, audio, seg_path)
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

    def _render_transition(self, entry: TimelineEntry, seg_path: str,
                            w: int, h: int) -> Optional[str]:
        """Render a transition clip (glitch transition with its own audio)."""
        source = entry.source_video_path
        if not source or not Path(source).exists():
            # Generate a quick dark flash as fallback
            return ffmpeg_ops.generate_color_clip(
                seg_path, duration=0.5, color="0x0a0f0a", w=w, h=h
            )

        # Use the pre-rendered transition — it already has scale_and_pad applied
        # from _generate_graphics, so just copy it
        import shutil
        shutil.copy2(source, seg_path)
        return seg_path

    def _render_branded(self, entry: TimelineEntry, seg_path: str,
                        w: int, h: int) -> Optional[str]:
        """Render branded intro/outro bumper.
        Custom video assets (intro.mp4/outro.mp4) already have their own audio."""
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
