"""
Avatar Generator — Oracle AI Narrator
=======================================
Generates talking-head avatar videos from voiceover audio + reference face.
Uses MuseTalk on Ultron for real-time lip-sync inference.

Pipeline:
  1. Upload voiceover audio to Ultron
  2. Call /generate_avatar endpoint
  3. Poll for completion
  4. Download result video
  5. The assembled video inserts avatar segments where specified

Avatar modes:
  - "full_narration": Avatar speaks during all narrator voiceover segments
  - "intro_outro": Avatar appears only for cold open + outro
  - "highlights": Avatar appears for story intros + signal_vs_noise
"""
import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("AvatarGenerator")

# Default face image on Ultron
DEFAULT_FACE_IMAGE = "oracle_face.png"


class AvatarGenerator:
    """Generate talking-head avatar videos via Ultron MuseTalk."""

    def __init__(self, mode: str = "intro_outro"):
        """
        Args:
            mode: Avatar mode — "full_narration", "intro_outro", or "highlights"
        """
        self.mode = mode
        self.face_image = os.environ.get("AVATAR_FACE_IMAGE", DEFAULT_FACE_IMAGE)
        self.configured = self._check_configured()

    def _check_configured(self) -> bool:
        """Check if avatar generation is available."""
        try:
            from pp_services.video_engine.ultron_client import ultron
            health = ultron.health_check()
            if health.get("status") != "ok":
                return False
            # Check if MuseTalk endpoint exists
            return health.get("musetalk_available", False)
        except Exception:
            return False

    def generate_avatar_segments(self, audio_map: Dict[str, str],
                                  bundle_path: Path) -> Dict[str, str]:
        """
        Generate avatar video segments for selected voiceovers.

        Args:
            audio_map: {script_id: audio_path} from narration generator
            bundle_path: Episode bundle directory

        Returns:
            {script_id: avatar_video_path} for segments that got avatar treatment
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"AVATAR GENERATOR — Mode: {self.mode}")
        logger.info(f"{'='*60}\n")

        if not self.configured:
            logger.warning("  MuseTalk not available on Ultron — skipping avatar generation")
            return {}

        # Select which segments get avatar treatment based on mode
        target_segments = self._select_segments(audio_map)

        if not target_segments:
            logger.info("  No segments selected for avatar — skipping")
            return {}

        logger.info(f"  Selected {len(target_segments)} segments for avatar generation")

        from pp_services.video_engine.ultron_client import ultron

        avatar_dir = bundle_path / "avatars"
        avatar_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        for script_id, audio_path in target_segments.items():
            logger.info(f"  Generating avatar for: {script_id}")

            try:
                # Upload audio to Ultron if not already there
                audio_filename = Path(audio_path).name
                ultron.upload_voiceover(audio_path, audio_filename)

                # Call avatar generation
                result = ultron.generate_avatar(
                    audio_file=audio_filename,
                    face_image=self.face_image,
                    output_name=f"avatar_{script_id}.mp4"
                )

                job_id = result.get("job_id")
                if not job_id:
                    logger.warning(f"    Avatar request failed for {script_id}: {result}")
                    continue

                # Poll for completion
                final = self._poll_job(ultron, job_id, script_id, timeout=120)

                if final and final.get("status") == "complete":
                    # Download result
                    output_name = f"avatar_{script_id}.mp4"
                    output_path = avatar_dir / output_name

                    ultron.download_file(output_name, str(output_path))

                    if output_path.exists():
                        size_mb = output_path.stat().st_size / (1024 * 1024)
                        logger.info(f"    Avatar generated: {output_name} ({size_mb:.1f}MB)")
                        results[script_id] = str(output_path)
                    else:
                        logger.warning(f"    Avatar download failed for {script_id}")
                else:
                    logger.warning(f"    Avatar generation failed for {script_id}")

            except Exception as e:
                logger.error(f"    Avatar error for {script_id}: {e}")

        logger.info(f"\n  Avatar segments generated: {len(results)}/{len(target_segments)}")
        return results

    def _select_segments(self, audio_map: Dict[str, str]) -> Dict[str, str]:
        """Select which voiceover segments get avatar treatment."""
        if self.mode == "full_narration":
            # All voiceover segments
            return {k: v for k, v in audio_map.items()
                    if not k.startswith("short")}

        elif self.mode == "intro_outro":
            # Only cold open + outro
            targets = {}
            for key in ["cold_open", "outro"]:
                if key in audio_map:
                    targets[key] = audio_map[key]
            return targets

        elif self.mode == "highlights":
            # Story intros + signal vs noise + cold open
            targets = {}
            for key, path in audio_map.items():
                if key in ("cold_open", "signal_vs_noise", "outro"):
                    targets[key] = path
                elif key.endswith("_intro") and key.startswith("story"):
                    targets[key] = path
            return targets

        return {}

    def _poll_job(self, ultron, job_id: str, label: str,
                   timeout: int = 120, interval: int = 5) -> Optional[dict]:
        """Poll Ultron job until complete."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                status = ultron.get_job_status(job_id)
                state = status.get("status", "unknown")
                if state == "complete":
                    return status
                elif state in ("failed", "error"):
                    return status
                time.sleep(interval)
            except Exception:
                time.sleep(interval)

        logger.warning(f"  Avatar job {label} timed out after {timeout}s")
        return None
