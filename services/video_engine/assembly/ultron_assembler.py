"""
Ultron Assembler
=================
Calls Ultron API to assemble the final video from the manifest.
Handles:
  - Horizontal (16:9) master video assembly
  - Vertical (9:16) shorts assembly
  - Audio-only podcast export
  - Asset upload (voiceovers, tweet cards)
"""
import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from services.video_engine.ultron_client import ultron
from services.video_engine.editorial.schemas import AssemblyManifest

logger = logging.getLogger("UltronAssembler")


class UltronAssembler:
    """Assemble videos via Ultron GPU server."""

    def __init__(self):
        self.job_ids = []

    def assemble_horizontal(self, manifest: AssemblyManifest,
                             bundle_path: Path = None) -> Optional[dict]:
        """
        Assemble the horizontal (16:9) master video.
        Converts the timeline manifest into Ultron's assembly format.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"ULTRON ASSEMBLY — Horizontal")
        logger.info(f"{'='*60}\n")

        # Check Ultron health
        try:
            health = ultron.health_check()
            if health.get("status") != "ok":
                logger.error("  Ultron offline — cannot assemble")
                return None
            logger.info(f"  Ultron: {health.get('gpu_count', 0)} GPUs available")
        except Exception as e:
            logger.error(f"  Ultron health check failed: {e}")
            return None

        # Convert timeline to Ultron segments format
        segments = self._manifest_to_ultron_segments(manifest)

        if not segments:
            logger.warning("  No segments to assemble")
            return None

        # Call Ultron assemble_advanced
        try:
            result = ultron.assemble_advanced(
                output_name=manifest.output_name,
                date_text=self._format_date(manifest.episode_date),
                segments=segments
            )

            job_id = result.get("job_id")
            if not job_id:
                logger.error(f"  Assembly request failed: {result}")
                return None

            self.job_ids.append(job_id)
            logger.info(f"  Assembly job started: {job_id}")

            # Poll for completion
            final_result = self._poll_job(job_id, "horizontal assembly", timeout=300)

            if final_result and final_result.get("status") == "complete":
                logger.info(f"  Assembly complete: {manifest.output_name}")
                logger.info(f"    Size: {final_result.get('size_mb', 0):.1f} MB")
                logger.info(f"    Segments: {final_result.get('segments_used', 0)}")

                # Download to episode bundle
                if bundle_path:
                    self._download_result(manifest.output_name,
                                          bundle_path / "final", "horizontal")

                return final_result
            else:
                logger.error(f"  Assembly failed: {final_result}")
                return None

        except Exception as e:
            logger.error(f"  Assembly failed: {e}")
            return None

    def assemble_shorts(self, shorts_manifests: List[dict],
                         bundle_path: Path = None) -> List[dict]:
        """Assemble vertical shorts via Ultron."""
        logger.info(f"\n  Assembling {len(shorts_manifests)} vertical shorts...")

        results = []
        for short in shorts_manifests:
            clip_file = short.get("clip_file")
            if not clip_file:
                logger.warning(f"  Short {short.get('short_index', '?')}: no clip file, skipping")
                continue

            output_name = short.get("output_name", f"short_{short['short_index']:02d}.mp4")

            try:
                result = ultron.generate_vertical(
                    clip_file,
                    output_name=output_name,
                    caption_text=short.get("hook_text", "")
                )

                job_id = result.get("job_id")
                if job_id:
                    final = self._poll_job(job_id, f"short {short['short_index']}", timeout=120)
                    if final and final.get("status") == "complete":
                        results.append({
                            "index": short["short_index"],
                            "filename": output_name,
                            "size_mb": final.get("size_mb", 0),
                            "status": "complete"
                        })

                        if bundle_path:
                            self._download_result(output_name,
                                                  bundle_path / "shorts", "short")
                    else:
                        results.append({
                            "index": short["short_index"],
                            "status": "failed"
                        })
                        logger.warning(f"  Short {short['short_index']} assembly failed")

            except Exception as e:
                logger.error(f"  Short {short['short_index']} failed: {e}")
                results.append({"index": short["short_index"], "status": "error",
                                "error": str(e)})

        success_count = len([r for r in results if r.get("status") == "complete"])
        logger.info(f"  Shorts assembled: {success_count}/{len(shorts_manifests)}")

        return results

    def export_audio_only(self, video_path: Path,
                           output_dir: Path) -> Optional[str]:
        """Export audio-only podcast version from assembled video."""
        audio_name = video_path.stem + "_audio.mp3"
        audio_path = output_dir / audio_name

        logger.info(f"  Exporting audio-only: {audio_name}")

        try:
            # Try via Ultron SSH (FFmpeg available there)
            import subprocess
            video_filename = video_path.name

            cmd = (
                f'ssh ultron "cd ~/video_engine/output && '
                f'ffmpeg -y -i {video_filename} -vn -c:a libmp3lame -b:a 192k '
                f'{audio_name}" 2>/dev/null'
            )
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=120)

            if result.returncode == 0:
                # Download the audio file
                self._download_result(audio_name, output_dir, "podcast audio",
                                       source_dir="output")
                return str(audio_path)
            else:
                logger.warning(f"  Audio export failed: {result.stderr.decode()[:200]}")
                return None

        except Exception as e:
            logger.warning(f"  Audio export failed: {e}")
            return None

    def upload_assets(self, assets: Dict[str, Path]) -> Dict[str, bool]:
        """Upload voiceovers and other assets to Ultron."""
        results = {}
        for name, path in assets.items():
            if not Path(path).exists():
                results[name] = False
                continue

            try:
                ultron.upload_voiceover(str(path), name)
                results[name] = True
                logger.info(f"  Uploaded: {name}")
            except Exception as e:
                logger.warning(f"  Upload failed for {name}: {e}")
                results[name] = False

        return results

    def _manifest_to_ultron_segments(self, manifest: AssemblyManifest) -> List[dict]:
        """Convert timeline entries to Ultron's segment format."""
        segments = []

        for entry in manifest.timeline:
            if entry.entry_type == "clip" and entry.source_video_path:
                segments.append({
                    "clip": entry.source_video_path,
                    "channel_name": entry.lower_third_title or "",
                    "lower_third_text": entry.lower_third_name or "",
                })

        return segments

    def _poll_job(self, job_id: str, label: str,
                   timeout: int = 300, interval: int = 10) -> Optional[dict]:
        """Poll Ultron job until complete or timeout."""
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

        logger.warning(f"  {label} job timed out after {timeout}s")
        return None

    def _download_result(self, filename: str, output_dir: Path,
                          label: str, source_dir: str = None):
        """Download a result file from Ultron."""
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        try:
            ultron.download_file(filename, str(output_path))
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"    Downloaded {label}: {filename} ({size_mb:.1f} MB)")
        except Exception as e:
            logger.warning(f"    Download failed for {filename}: {e}")

    @staticmethod
    def _format_date(date_str: str) -> str:
        """Format YYYY-MM-DD to display format."""
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%B %d, %Y")
        except Exception:
            return date_str
