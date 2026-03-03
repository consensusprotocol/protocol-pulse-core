"""
Episode Builder
================
Master assembly function that takes ALL generated assets
and produces the final video + podcast audio + thumbnail.

Assembly order:
  a. INTRO BUMPER (4s) — from motion_graphics
  b. COLD OPEN narration — voiceover with branded background
  c. For each STORY:
     - TITLE CARD (2s) — story number + headline
     - NARRATOR INTRO — voiceover with branded bg
     - SOURCE CLIP — YouTube clip with lower third
     - NARRATOR WRAP — post-clip voiceover
  d. SIGNAL vs NOISE (30s) — narration + branded card
  e. COMMUNITY PULSE — tweet/nostr screenshots + narration
  f. OUTRO BUMPER (3s) — from motion_graphics
"""
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional

from services.video_engine.assembly import ffmpeg_ops
from services.video_engine.assembly.local_assembler import LocalAssembler
from services.video_engine.assembly.manifest_builder import ManifestBuilder
from services.video_engine.editorial.schemas import AssemblyManifest, TimelineEntry

logger = logging.getLogger("EpisodeBuilder")


class EpisodeBuilder:
    """Build a complete Pulse Check episode from generated assets."""

    def __init__(self, bundle_path: str, show_plan: dict,
                 audio_map: Dict[str, str], clip_map: Dict[str, str],
                 tweet_images: Dict[str, str] = None,
                 nostr_images: Dict[str, str] = None):
        """
        Args:
            bundle_path: directory containing all episode assets
            show_plan: ShowPlanV2 dict from Claude Director
            audio_map: {script_id: audio_path} from narration generator
            clip_map: {clip_id: clip_path} from clip extractor
            tweet_images: {key: image_path} from tweet screenshot
            nostr_images: {key: image_path} from nostr card renderer
        """
        self.bundle = Path(bundle_path)
        self.plan = show_plan
        self.audio_map = audio_map
        self.clip_map = clip_map
        self.tweet_images = tweet_images or {}
        self.nostr_images = nostr_images or {}
        self.date_str = show_plan.get("episode_date", "unknown")

        # Working directory for intermediate files
        self.work_dir = self.bundle / "work"
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # Output directories
        self.final_dir = self.bundle / "final"
        self.final_dir.mkdir(parents=True, exist_ok=True)

    def build(self) -> dict:
        """
        Build the complete episode.
        Returns dict with all output file paths and metadata.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"EPISODE BUILDER — {self.date_str}")
        logger.info(f"{'='*60}\n")

        start = time.time()
        results = {}

        # Step 1: Generate motion graphics assets
        logger.info("Step 1: Generating motion graphics...")
        graphics = self._generate_graphics()

        # Step 2: Build the assembly manifest with real asset paths
        logger.info("\nStep 2: Building manifest...")
        manifest = self._build_manifest(graphics)

        # Step 3: Assemble horizontal (16:9) master video
        logger.info("\nStep 3: Assembling horizontal video...")
        assembler = LocalAssembler(str(self.work_dir))
        h_result = assembler.assemble_horizontal(manifest, self.bundle)
        if h_result:
            results["horizontal"] = h_result
            results["video_path"] = h_result["output_path"]
            logger.info(f"  Horizontal: {h_result['output_path']} "
                        f"({h_result.get('size_mb', 0)} MB, "
                        f"{h_result.get('duration', 0):.0f}s)")
        else:
            logger.error("  Horizontal assembly FAILED")

        # Step 4: Export podcast audio
        if results.get("video_path"):
            logger.info("\nStep 4: Exporting podcast audio...")
            audio_path = assembler.export_audio_only(
                results["video_path"], str(self.final_dir))
            if audio_path:
                results["audio_path"] = audio_path
                logger.info(f"  Podcast: {audio_path}")

        # Step 5: Generate thumbnail
        logger.info("\nStep 5: Generating thumbnail...")
        thumb = self._generate_thumbnail()
        if thumb:
            results["thumbnail_path"] = thumb

        # Step 6: Save build manifest
        elapsed = time.time() - start
        results["build_time_seconds"] = round(elapsed, 1)
        results["episode_date"] = self.date_str
        results["segments_count"] = len(manifest.timeline)

        manifest_path = self.bundle / "manifest" / "assembly_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest.dict(), indent=2, default=str))

        build_log = self.bundle / "build_log.json"
        build_log.write_text(json.dumps(results, indent=2, default=str))

        logger.info(f"\n{'='*60}")
        logger.info(f"BUILD COMPLETE — {elapsed:.0f}s")
        logger.info(f"{'='*60}")
        for key in ["video_path", "audio_path", "thumbnail_path"]:
            if key in results:
                logger.info(f"  {key}: {results[key]}")

        return results

    def _generate_graphics(self) -> dict:
        """Generate all motion graphics and return paths."""
        gfx = {}
        gfx_dir = self.work_dir / "graphics"
        gfx_dir.mkdir(exist_ok=True)

        try:
            from services.video_engine.graphics.motion_graphics import (
                generate_intro, generate_outro, generate_transition,
                render_title_card, render_signal_noise_card, render_branded_bg
            )

            # Intro bumper
            intro_path = str(gfx_dir / "intro.mp4")
            generate_intro(intro_path)
            gfx["intro"] = intro_path
            logger.info("  + Intro bumper")

            # Outro bumper
            outro_path = str(gfx_dir / "outro.mp4")
            generate_outro(outro_path)
            gfx["outro"] = outro_path
            logger.info("  + Outro bumper")

            # Transition
            trans_path = str(gfx_dir / "transition.mp4")
            generate_transition(trans_path)
            gfx["transition"] = trans_path
            logger.info("  + Transition")

            # Title cards per story
            for story in self.plan.get("stories", []):
                sn = story.get("story_number", 0)
                headline = story.get("headline", "")
                tc_path = str(gfx_dir / f"title_card_{sn}.mp4")
                render_title_card(headline, sn, tc_path)
                gfx[f"title_card_{sn}"] = tc_path
                logger.info(f"  + Title card: Story {sn}")

            # Signal vs Noise card
            svn = self.plan.get("signal_vs_noise", {})
            if svn:
                svn_path = str(gfx_dir / "signal_vs_noise.png")
                render_signal_noise_card(
                    svn.get("signal", ""),
                    svn.get("noise", ""),
                    svn.get("wildcard", ""),
                    svn_path
                )
                gfx["signal_vs_noise_card"] = svn_path
                logger.info("  + Signal vs Noise card")

            # Branded background
            bg_path = str(gfx_dir / "branded_bg.png")
            render_branded_bg(bg_path)
            gfx["branded_bg"] = bg_path

        except Exception as e:
            logger.error(f"  Graphics generation error: {e}")

        return gfx

    def _build_manifest(self, graphics: dict) -> AssemblyManifest:
        """Build assembly manifest with real file paths for everything."""
        timeline = []

        # 1. Intro bumper
        intro_path = graphics.get("intro")
        if intro_path and Path(intro_path).exists():
            timeline.append(TimelineEntry(
                entry_type="branded_intro",
                source_video_path=intro_path,
                visual=intro_path,
                duration_sec=4.0,
                transition_in="cut"
            ))

        # 2. Cold open
        cold_audio = self.audio_map.get("cold_open")
        bg = graphics.get("branded_bg")
        if cold_audio:
            timeline.append(TimelineEntry(
                entry_type="voiceover",
                audio_path=cold_audio,
                image_path=bg,
                visual="branded_bg",
                transition_in="crossfade_0.5s"
            ))

        # 3. Stories
        for story in self.plan.get("stories", []):
            sn = story.get("story_number", 0)

            # Title card
            tc = graphics.get(f"title_card_{sn}")
            if tc and Path(tc).exists():
                timeline.append(TimelineEntry(
                    entry_type="branded_intro",
                    source_video_path=tc,
                    visual=tc,
                    duration_sec=2.0,
                    transition_in="crossfade_0.5s"
                ))

            # Narrator intro
            intro_audio = self.audio_map.get(f"story{sn}_intro")
            if intro_audio:
                timeline.append(TimelineEntry(
                    entry_type="voiceover",
                    audio_path=intro_audio,
                    image_path=bg,
                    visual="branded_bg",
                    transition_in="cut"
                ))

            # Clips
            for ci, clip in enumerate(story.get("clips", [])):
                clip_id = f"story{sn}_clip{ci}"

                # Clip intro voiceover
                clip_intro_audio = self.audio_map.get(f"story{sn}_clip{ci}_intro")
                if clip_intro_audio:
                    timeline.append(TimelineEntry(
                        entry_type="voiceover",
                        audio_path=clip_intro_audio,
                        image_path=bg,
                        visual="branded_bg",
                        transition_in="cut"
                    ))

                # The clip itself
                clip_file = self.clip_map.get(clip_id)
                if clip_file and Path(clip_file).exists():
                    timeline.append(TimelineEntry(
                        entry_type="clip",
                        source_video_path=clip_file,
                        lower_third_name=clip.get("speaker", ""),
                        lower_third_title=clip.get("source_name", ""),
                        transition_in="crossfade_0.5s"
                    ))

            # Tweet overlays
            for ti, tweet in enumerate(story.get("tweet_overlays", [])):
                tweet_key = f"story{sn}_tweet{ti}"
                tweet_audio = self.audio_map.get(tweet_key)
                tweet_img = self.tweet_images.get(tweet_key)
                if tweet_audio or tweet_img:
                    timeline.append(TimelineEntry(
                        entry_type="tweet_overlay",
                        audio_path=tweet_audio,
                        image_path=tweet_img,
                        transition_in="cut"
                    ))

            # Narrator wrap
            wrap_audio = self.audio_map.get(f"story{sn}_wrap")
            if wrap_audio:
                timeline.append(TimelineEntry(
                    entry_type="voiceover",
                    audio_path=wrap_audio,
                    image_path=bg,
                    visual="branded_bg",
                    transition_in="cut"
                ))

        # 4. Quick hits
        for qh in self.plan.get("quick_hits", []):
            sn = qh.get("story_number", 0)
            intro_audio = self.audio_map.get(f"quickhit{sn}_intro")
            if intro_audio:
                timeline.append(TimelineEntry(
                    entry_type="voiceover",
                    audio_path=intro_audio,
                    image_path=bg,
                    visual="branded_bg",
                    transition_in="cut"
                ))
            wrap_audio = self.audio_map.get(f"quickhit{sn}_wrap")
            if wrap_audio:
                timeline.append(TimelineEntry(
                    entry_type="voiceover",
                    audio_path=wrap_audio,
                    image_path=bg,
                    visual="branded_bg",
                    transition_in="cut"
                ))

        # 5. Signal vs Noise
        svn_audio = self.audio_map.get("signal_vs_noise")
        svn_img = graphics.get("signal_vs_noise_card")
        if svn_audio:
            timeline.append(TimelineEntry(
                entry_type="signal_vs_noise",
                audio_path=svn_audio,
                image_path=svn_img,
                visual="signal_vs_noise_graphic",
                transition_in="crossfade_0.5s"
            ))

        # 6. Community Pulse
        cp = self.plan.get("community_pulse")
        if cp:
            cp_intro_audio = self.audio_map.get("community_intro")
            if cp_intro_audio:
                timeline.append(TimelineEntry(
                    entry_type="voiceover",
                    audio_path=cp_intro_audio,
                    image_path=bg,
                    visual="branded_bg",
                    transition_in="crossfade_0.5s"
                ))

            for ti, tweet in enumerate(cp.get("tweets", [])):
                tweet_audio = self.audio_map.get(f"community_tweet{ti}")
                tweet_img = self.tweet_images.get(f"community_tweet{ti}")
                if tweet_audio:
                    timeline.append(TimelineEntry(
                        entry_type="tweet_overlay",
                        audio_path=tweet_audio,
                        image_path=tweet_img,
                        transition_in="cut"
                    ))

            hook_audio = self.audio_map.get("community_hook")
            if hook_audio:
                timeline.append(TimelineEntry(
                    entry_type="voiceover",
                    audio_path=hook_audio,
                    image_path=bg,
                    visual="branded_bg",
                    transition_in="cut"
                ))

        # 7. Outro
        outro_audio = self.audio_map.get("outro")
        if outro_audio:
            timeline.append(TimelineEntry(
                entry_type="voiceover",
                audio_path=outro_audio,
                image_path=bg,
                visual="branded_bg",
                transition_in="crossfade_0.5s"
            ))

        # 8. Outro bumper
        outro_path = graphics.get("outro")
        if outro_path and Path(outro_path).exists():
            timeline.append(TimelineEntry(
                entry_type="branded_outro",
                source_video_path=outro_path,
                visual=outro_path,
                duration_sec=3.0,
                transition_in="crossfade_0.5s"
            ))

        manifest = AssemblyManifest(
            episode_date=self.date_str,
            output_name=f"pulse_check_{self.date_str}.mp4",
            timeline=timeline,
            audio_settings={
                "narrator_lufs": -16,
                "clip_lufs": -18,
                "music_lufs": -30,
            }
        )

        logger.info(f"  Manifest: {len(timeline)} entries")
        return manifest

    def _generate_thumbnail(self) -> Optional[str]:
        """Generate episode thumbnail."""
        try:
            from services.video_engine.graphics.thumbnail import (
                generate_thumbnail
            )

            headline = self.plan.get("episode_headline", "PULSE CHECK")
            # Get source names from stories
            sources = []
            for story in self.plan.get("stories", []):
                for clip in story.get("clips", []):
                    name = clip.get("source_name", "")
                    if name and name not in sources:
                        sources.append(name)

            thumb_path = str(self.final_dir / f"pulse_check_{self.date_str}_thumb.png")
            generate_thumbnail(headline, sources, self.date_str, thumb_path)
            logger.info(f"  Thumbnail: {thumb_path}")
            return thumb_path

        except Exception as e:
            logger.error(f"  Thumbnail generation failed: {e}")
            return None
