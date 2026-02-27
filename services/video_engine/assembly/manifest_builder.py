"""
Manifest Builder
=================
Transforms ShowPlanV2 → AssemblyManifest (timeline-based).

The manifest is the blueprint Ultron uses to assemble the final video.
Each entry in the timeline represents a visual+audio segment in order.

Timeline sequence:
  1. branded_intro (5 sec)
  2. voiceover: cold_open (over background loop)
  3. For each story:
     - voiceover: narrator intro (over background or broll)
     - For each clip: voiceover clip_intro → clip with lower-third → transition
     - For each tweet: tweet_overlay image + narrator_read audio
     - voiceover: bridge (if present)
     - voiceover: wrap
  4. voiceover: signal_vs_noise (over branded graphic)
  5. voiceover: community_pulse
  6. voiceover: outro
  7. branded_outro (10 sec)
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from services.video_engine.editorial.schemas import (
    AssemblyManifest, TimelineEntry, ShowPlanV2
)

logger = logging.getLogger("ManifestBuilder")


class ManifestBuilder:
    """Build assembly manifest from show plan + asset paths."""

    def __init__(self, show_plan: dict, audio_map: Dict[str, str],
                 clip_map: Dict[str, str],
                 tweet_images: Dict[str, str] = None):
        """
        Args:
            show_plan: ShowPlanV2 dict
            audio_map: {script_id: audio_path} from narration generator
            clip_map: {clip_id: clip_filename} from clip extractor
            tweet_images: {tweet_key: image_path} from tweet card renderer
        """
        self.plan = show_plan
        self.audio_map = audio_map
        self.clip_map = clip_map
        self.tweet_images = tweet_images or {}
        self.timeline = []

    def build(self, bundle_path: Path = None) -> AssemblyManifest:
        """Build the complete timeline manifest."""
        logger.info(f"\n{'='*60}")
        logger.info(f"MANIFEST BUILDER")
        logger.info(f"{'='*60}\n")

        date_str = self.plan.get("episode_date", "unknown")

        # 1. Branded intro
        self.timeline.append(TimelineEntry(
            entry_type="branded_intro",
            visual="branded_intro",
            duration_sec=5.0,
            transition_in="cut"
        ))

        # 2. Cold open
        cold_open_audio = self.audio_map.get("cold_open")
        if cold_open_audio:
            self.timeline.append(TimelineEntry(
                entry_type="voiceover",
                audio_path=cold_open_audio,
                visual="background_loop",
                transition_in="crossfade_0.5s"
            ))

        # 3. Stories
        for story in self.plan.get("stories", []):
            self._add_story(story)

        # 4. Quick hits
        for qh in self.plan.get("quick_hits", []):
            self._add_story(qh, prefix="quickhit")

        # 5. Signal vs Noise
        svn_audio = self.audio_map.get("signal_vs_noise")
        if svn_audio:
            self.timeline.append(TimelineEntry(
                entry_type="signal_vs_noise",
                audio_path=svn_audio,
                visual="signal_vs_noise_graphic",
                transition_in="crossfade_0.5s"
            ))

        # 6. Community Pulse
        cp = self.plan.get("community_pulse")
        if cp:
            cp_intro_audio = self.audio_map.get("community_intro")
            if cp_intro_audio:
                self.timeline.append(TimelineEntry(
                    entry_type="voiceover",
                    audio_path=cp_intro_audio,
                    visual="background_loop",
                    transition_in="crossfade_0.5s"
                ))

            for ti, tweet in enumerate(cp.get("tweets", [])):
                tweet_audio = self.audio_map.get(f"community_tweet{ti}")
                tweet_img = self.tweet_images.get(f"community_tweet{ti}")
                if tweet_audio:
                    self.timeline.append(TimelineEntry(
                        entry_type="tweet_overlay",
                        audio_path=tweet_audio,
                        image_path=tweet_img,
                        transition_in="cut"
                    ))

            hook_audio = self.audio_map.get("community_hook")
            if hook_audio:
                self.timeline.append(TimelineEntry(
                    entry_type="voiceover",
                    audio_path=hook_audio,
                    visual="background_loop"
                ))

        # 7. Outro
        outro_audio = self.audio_map.get("outro")
        if outro_audio:
            self.timeline.append(TimelineEntry(
                entry_type="voiceover",
                audio_path=outro_audio,
                visual="background_loop",
                transition_in="crossfade_0.5s"
            ))

        # 8. Branded outro
        self.timeline.append(TimelineEntry(
            entry_type="branded_outro",
            visual="branded_outro",
            duration_sec=10.0,
            transition_in="crossfade_1s"
        ))

        # Build manifest
        manifest = AssemblyManifest(
            episode_date=date_str,
            output_name=f"pulse_check_{date_str}.mp4",
            timeline=self.timeline,
            audio_settings={
                "narrator_lufs": -16,
                "clip_lufs": -18,
                "music_lufs": -30,
            }
        )

        logger.info(f"  Manifest built: {len(self.timeline)} timeline entries")
        logger.info(f"  Output: {manifest.output_name}")

        # Save manifest
        if bundle_path:
            out_path = bundle_path / "manifest" / "assembly_manifest.json"
            out_path.write_text(json.dumps(manifest.dict(), indent=2, default=str))
            logger.info(f"  Saved: {out_path}")

        return manifest

    def _add_story(self, story: dict, prefix: str = "story"):
        """Add a story's timeline entries."""
        sn = story.get("story_number", 0)
        broll = story.get("broll_category", "generic")

        # Story intro
        intro_audio = self.audio_map.get(f"{prefix}{sn}_intro")
        if intro_audio:
            self.timeline.append(TimelineEntry(
                entry_type="voiceover",
                audio_path=intro_audio,
                visual=f"broll_{broll}",
                transition_in="crossfade_0.5s"
            ))

        # Clips
        for ci, clip in enumerate(story.get("clips", [])):
            clip_id = f"story{sn}_clip{ci}" if prefix == "story" else f"quickhit{sn}_clip{ci}"

            # Clip intro voiceover
            clip_intro_audio = self.audio_map.get(f"{prefix}{sn}_clip{ci}_intro")
            if clip_intro_audio:
                self.timeline.append(TimelineEntry(
                    entry_type="voiceover",
                    audio_path=clip_intro_audio,
                    visual=f"broll_{broll}",
                    transition_in="cut"
                ))

            # The clip itself
            clip_file = self.clip_map.get(clip_id)
            if clip_file:
                self.timeline.append(TimelineEntry(
                    entry_type="clip",
                    source_video_path=clip_file,
                    lower_third_name=clip.get("speaker", ""),
                    lower_third_title=clip.get("source_name", ""),
                    transition_in="crossfade_0.5s"
                ))

        # Tweet overlays
        for ti, tweet in enumerate(story.get("tweet_overlays", [])):
            tweet_audio = self.audio_map.get(f"{prefix}{sn}_tweet{ti}")
            tweet_img = self.tweet_images.get(f"{prefix}{sn}_tweet{ti}")
            if tweet_audio or tweet_img:
                self.timeline.append(TimelineEntry(
                    entry_type="tweet_overlay",
                    audio_path=tweet_audio,
                    image_path=tweet_img,
                    transition_in="cut"
                ))

        # Bridge
        bridge_audio = self.audio_map.get(f"{prefix}{sn}_bridge")
        if bridge_audio:
            self.timeline.append(TimelineEntry(
                entry_type="voiceover",
                audio_path=bridge_audio,
                visual=f"broll_{broll}",
                transition_in="cut"
            ))

        # Wrap
        wrap_audio = self.audio_map.get(f"{prefix}{sn}_wrap")
        if wrap_audio:
            self.timeline.append(TimelineEntry(
                entry_type="voiceover",
                audio_path=wrap_audio,
                visual=f"broll_{broll}",
                transition_in="cut"
            ))


def build_shorts_manifests(show_plan: dict, audio_map: Dict[str, str],
                            clip_map: Dict[str, str]) -> List[dict]:
    """Build assembly manifests for vertical shorts from shorts_plan."""
    shorts = []
    for i, short in enumerate(show_plan.get("shorts_plan", [])):
        story_ref = short.get("story_ref", 0)
        clip_ref = short.get("clip_ref", 0)
        clip_id = f"story{story_ref}_clip{clip_ref}"

        short_manifest = {
            "short_index": i,
            "hook_text": short.get("hook_text", ""),
            "intro_audio": audio_map.get(f"short{i}_intro"),
            "clip_file": clip_map.get(clip_id),
            "takeaway_audio": audio_map.get(f"short{i}_takeaway"),
            "cta": short.get("cta", "Full Pulse Check in bio."),
            "output_name": f"short_{i:02d}_{show_plan.get('episode_date', 'unknown')}.mp4"
        }
        shorts.append(short_manifest)

    return shorts
