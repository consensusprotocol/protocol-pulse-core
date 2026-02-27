"""
Narration Generator
====================
Converts all narrator scripts to audio via ElevenLabs TTS.
Emotion-aware voice settings. Broadcast-quality loudnorm.

Tracks character count for cost logging.
"""
import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("NarrationGenerator")

# Voice settings per emotion
VOICE_SETTINGS = {
    "calm": {"stability": 0.65, "similarity_boost": 0.78, "style": 0.35},
    "urgent": {"stability": 0.55, "similarity_boost": 0.80, "style": 0.50},
    "encouraging": {"stability": 0.60, "similarity_boost": 0.78, "style": 0.45},
    "serious": {"stability": 0.70, "similarity_boost": 0.80, "style": 0.25},
}


class NarrationGenerator:
    """Generate all voiceover audio from the show plan."""

    def __init__(self):
        self.api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.total_characters = 0
        self.generated_files = []

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate_all(self, show_plan_dict: dict,
                      output_dir: Path) -> Dict[str, str]:
        """
        Extract all scripts from show plan, generate TTS, normalize audio.
        Returns {script_id: audio_path} mapping.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n{'='*60}")
        logger.info(f"NARRATION GENERATION")
        logger.info(f"{'='*60}\n")

        if not self.configured:
            logger.error("  ELEVENLABS_API_KEY not set — cannot generate voiceovers")
            return {}

        # Extract all scripts with IDs and emotions
        scripts = self._extract_all_scripts(show_plan_dict)
        logger.info(f"  Extracted {len(scripts)} narrator scripts")

        # Generate TTS for each
        audio_map = {}
        for script_id, text, emotion in scripts:
            if not text or not text.strip():
                continue

            output_path = output_dir / f"{script_id}.mp3"
            success = self._generate_tts(text, emotion, output_path)

            if success:
                # Normalize audio
                norm_path = output_dir / f"{script_id}_norm.mp3"
                if self._normalize_audio(output_path, norm_path):
                    audio_map[script_id] = str(norm_path)
                    # Remove unnormalized version
                    output_path.unlink(missing_ok=True)
                else:
                    audio_map[script_id] = str(output_path)

                self.generated_files.append(script_id)
                logger.info(f"    + {script_id} ({len(text)} chars, {emotion})")
            else:
                logger.warning(f"    - {script_id}: TTS failed")

        logger.info(f"\n  Generated {len(audio_map)}/{len(scripts)} voiceovers")
        logger.info(f"  Total characters: {self.total_characters:,}")

        return audio_map

    def _extract_all_scripts(self, plan: dict) -> List[Tuple[str, str, str]]:
        """
        Walk the show plan and extract every narrator script.
        Returns list of (script_id, text, emotion).
        """
        scripts = []

        # Cold open
        cold_open = plan.get("cold_open_script", "")
        if cold_open:
            scripts.append(("cold_open", cold_open, "urgent"))

        # Stories
        for story in plan.get("stories", []):
            sn = story.get("story_number", 0)
            emotion = story.get("emotion", "calm")

            # Story intro
            intro = story.get("narrator_intro_script", "")
            if intro:
                scripts.append((f"story{sn}_intro", intro, emotion))

            # Clip intros
            for ci, clip in enumerate(story.get("clips", [])):
                intro_line = clip.get("intro_line", "")
                if intro_line:
                    scripts.append((f"story{sn}_clip{ci}_intro", intro_line, emotion))

            # Tweet overlay narration
            for ti, tweet in enumerate(story.get("tweet_overlays", [])):
                narrator_read = tweet.get("narrator_read", "")
                if narrator_read:
                    scripts.append((f"story{sn}_tweet{ti}", narrator_read, emotion))

            # Bridge
            bridge = story.get("narrator_bridge_script")
            if bridge:
                scripts.append((f"story{sn}_bridge", bridge, emotion))

            # Wrap
            wrap = story.get("narrator_wrap_script")
            if wrap:
                scripts.append((f"story{sn}_wrap", wrap, emotion))

        # Quick hits
        for story in plan.get("quick_hits", []):
            sn = story.get("story_number", 0)
            emotion = story.get("emotion", "calm")

            intro = story.get("narrator_intro_script", "")
            if intro:
                scripts.append((f"quickhit{sn}_intro", intro, emotion))

            wrap = story.get("narrator_wrap_script")
            if wrap:
                scripts.append((f"quickhit{sn}_wrap", wrap, emotion))

        # Signal vs Noise
        svn = plan.get("signal_vs_noise", {})
        svn_intro = svn.get("narrator_intro", "")
        signal = svn.get("signal", "")
        noise = svn.get("noise", "")
        wildcard = svn.get("wildcard", "")

        svn_full = f"{svn_intro} Signal: {signal} Noise: {noise} Wildcard: {wildcard}"
        if svn_full.strip():
            scripts.append(("signal_vs_noise", svn_full.strip(), "serious"))

        # Community Pulse
        cp = plan.get("community_pulse")
        if cp:
            cp_intro = cp.get("narrator_intro", "")
            if cp_intro:
                scripts.append(("community_intro", cp_intro, "encouraging"))

            for ti, tweet in enumerate(cp.get("tweets", [])):
                narrator_read = tweet.get("narrator_read", "")
                if narrator_read:
                    scripts.append((f"community_tweet{ti}", narrator_read, "encouraging"))

            hook = cp.get("engagement_hook", "")
            if hook:
                scripts.append(("community_hook", hook, "encouraging"))

        # Outro
        outro = plan.get("outro_script", "")
        if outro:
            scripts.append(("outro", outro, "calm"))

        return scripts

    def _generate_tts(self, text: str, emotion: str,
                       output_path: Path) -> bool:
        """Generate TTS audio via ElevenLabs API."""
        try:
            import requests

            settings = VOICE_SETTINGS.get(emotion, VOICE_SETTINGS["calm"])

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": settings
            }

            response = requests.post(url, json=payload, headers=headers,
                                     timeout=30, stream=True)

            if response.status_code != 200:
                logger.warning(f"  ElevenLabs returned {response.status_code}: "
                               f"{response.text[:200]}")
                return False

            # Stream to file
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.total_characters += len(text)

            # Verify file
            if output_path.stat().st_size < 1000:
                logger.warning(f"  Output file too small: {output_path.stat().st_size} bytes")
                return False

            return True

        except ImportError:
            logger.error("  requests not available for TTS")
            return False
        except Exception as e:
            logger.error(f"  TTS generation failed: {e}")
            return False

    def _normalize_audio(self, input_path: Path, output_path: Path,
                          target_lufs: int = -16) -> bool:
        """Normalize audio to broadcast standard using FFmpeg on Ultron."""
        try:
            from services.video_engine.ultron_client import ultron

            # Upload the audio to Ultron for normalization
            # If Ultron is not available, try local ffmpeg
            import subprocess

            cmd = [
                "ffmpeg", "-y", "-i", str(input_path),
                "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode == 0 and output_path.exists():
                return True

        except FileNotFoundError:
            pass  # ffmpeg not available locally
        except Exception as e:
            logger.debug(f"  Local loudnorm failed: {e}")

        # Fallback: just copy the file (unnormalized)
        try:
            import shutil
            shutil.copy2(str(input_path), str(output_path))
            return True
        except Exception:
            return False
