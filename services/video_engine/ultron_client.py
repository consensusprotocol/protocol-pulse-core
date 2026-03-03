"""
ULTRON CLIENT
==============
Unified HTTP client for communicating with the Ultron GPU server.
Supports batch operations, retries, streaming downloads, and auth.
"""

import os
import time
import json
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("UltronClient")

ULTRON_HOST = os.environ.get("ULTRON_HOST", "")
ULTRON_TOKEN = os.environ.get("ULTRON_API_TOKEN", "")
ULTRON_BASE = f"https://{ULTRON_HOST}" if ULTRON_HOST else ""
DEFAULT_TIMEOUT = 120
MAX_RETRIES = 3

# Local mode: use local ffmpeg/moviepy when ULTRON_HOST is empty or localhost
LOCAL_MODE = not ULTRON_HOST or ULTRON_HOST in ("localhost", "127.0.0.1", "")


class UltronClient:
    """HTTP client for the Ultron Video Engine API v3."""

    def __init__(self):
        self.base_url = ULTRON_BASE
        self.session = requests.Session()
        if ULTRON_TOKEN:
            self.session.headers["Authorization"] = f"Bearer {ULTRON_TOKEN}"
        self.session.headers["Content-Type"] = "application/json"

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make an HTTP request with retries."""
        url = f"{self.base_url}{endpoint}"
        timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)

        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.request(method, url, timeout=timeout, **kwargs)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 401:
                    logger.error("Ultron auth failed — check ULTRON_API_TOKEN")
                    return None
                else:
                    logger.warning(f"Ultron {endpoint} returned {resp.status_code}: {resp.text[:200]}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
            except requests.exceptions.Timeout:
                logger.warning(f"Ultron {endpoint} timed out (attempt {attempt + 1})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError:
                logger.error(f"Ultron connection failed (attempt {attempt + 1})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Ultron request error: {e}")
                return None

        logger.error(f"Ultron {endpoint} failed after {MAX_RETRIES} attempts")
        return None

    # --- Health ---

    def health_check(self) -> Dict:
        """Check Ultron server health and GPU status."""
        result = self._request("GET", "/health")
        return result or {"status": "offline"}

    # --- Batch Operations (v3) ---

    def batch_download_audio(self, video_ids: List[str]) -> Optional[str]:
        """Start batch audio download. Returns job_id."""
        result = self._request("POST", "/batch_download_audio",
                               json={"video_ids": video_ids}, timeout=30)
        if result:
            logger.info(f"Batch download started: {result.get('job_id')} ({result.get('count')} videos)")
            return result.get("job_id")
        return None

    def batch_transcribe(self, video_ids: List[str]) -> Optional[str]:
        """Start batch transcription. Returns job_id."""
        result = self._request("POST", "/batch_transcribe",
                               json={"video_ids": video_ids}, timeout=30)
        if result:
            logger.info(f"Batch transcribe started: {result.get('job_id')} ({result.get('count')} videos)")
            return result.get("job_id")
        return None

    def get_transcripts(self, video_ids: List[str]) -> Dict:
        """Fetch multiple transcripts at once."""
        result = self._request("POST", "/get_transcripts",
                               json={"video_ids": video_ids}, timeout=60)
        if result:
            logger.info(f"Fetched {result.get('found', 0)}/{result.get('requested', 0)} transcripts")
            return result.get("transcripts", {})
        return {}

    # --- Job Polling ---

    def poll_job(self, job_id: str, max_wait: int = 600, interval: int = 10) -> Optional[Dict]:
        """Poll a job until completion or timeout."""
        elapsed = 0
        consecutive_failures = 0
        max_failures = 10

        while elapsed < max_wait:
            result = self._request("GET", f"/job/{job_id}", timeout=15)

            if not result:
                consecutive_failures += 1
                logger.warning(f"  Job {job_id}: poll failed ({consecutive_failures}/{max_failures})")
                if consecutive_failures >= max_failures:
                    logger.error(f"  Job {job_id}: aborting after {max_failures} consecutive failures")
                    return None
                time.sleep(interval)
                elapsed += interval
                continue

            consecutive_failures = 0
            status = result.get("status", "")
            if status in ("complete", "error", "failed"):
                return result

            progress = result.get("progress", 0)
            logger.info(f"  Job {job_id}: {status} ({progress}%)")

            time.sleep(interval)
            elapsed += interval

        logger.warning(f"Job {job_id} timed out after {max_wait}s")
        return None

    # --- Standard Operations ---

    def download_audio(self, video_id: str) -> Optional[Dict]:
        """Download audio for a single video."""
        return self._request("POST", "/download_audio",
                             json={"video_id": video_id}, timeout=300)

    def download_video(self, video_id: str, quality: str = "720") -> Optional[Dict]:
        """Download full video."""
        return self._request("POST", "/download_video",
                             json={"video_id": video_id, "quality": quality}, timeout=600)

    def extract_clip(self, video_id: str, start_time: float, end_time: float,
                     output_name: str) -> Optional[Dict]:
        """Extract a clip from a downloaded video."""
        return self._request("POST", "/extract_clip", json={
            "video_id": video_id,
            "start_time": start_time,
            "end_time": end_time,
            "output_name": output_name
        }, timeout=120)

    def assemble_advanced(self, manifest: Dict) -> Optional[str]:
        """Start advanced assembly. Returns job_id."""
        result = self._request("POST", "/assemble_advanced",
                               json=manifest, timeout=30)
        if result:
            return result.get("job_id")
        return None

    def generate_vertical(self, params: Dict) -> Optional[str]:
        """Start vertical short generation. Returns job_id."""
        result = self._request("POST", "/generate_vertical",
                               json=params, timeout=30)
        if result:
            return result.get("job_id")
        return None

    # --- File Operations ---

    def upload_voiceover(self, local_path: str, remote_name: str) -> Optional[Dict]:
        """Upload a voiceover file to Ultron."""
        try:
            with open(local_path, "rb") as f:
                resp = self.session.post(
                    f"{self.base_url}/upload_voiceover",
                    files={"file": (remote_name, f, "audio/mpeg")},
                    data={"filename": remote_name},
                    headers={k: v for k, v in self.session.headers.items()
                             if k != "Content-Type"},
                    timeout=60
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"Upload voiceover failed: {e}")
        return None

    def upload_asset(self, local_path: str, remote_name: str) -> Optional[Dict]:
        """Upload an asset file to Ultron."""
        try:
            with open(local_path, "rb") as f:
                resp = self.session.post(
                    f"{self.base_url}/upload_asset",
                    files={"file": (remote_name, f)},
                    data={"filename": remote_name},
                    headers={k: v for k, v in self.session.headers.items()
                             if k != "Content-Type"},
                    timeout=60
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"Upload asset failed: {e}")
        return None

    def download_output(self, filename: str, local_dir: str) -> Optional[str]:
        """Download an output file from Ultron."""
        return self._download_file(f"/download/{filename}", filename, local_dir)

    def download_short(self, filename: str, local_dir: str) -> Optional[str]:
        """Download a short from Ultron."""
        return self._download_file(f"/download_short/{filename}", filename, local_dir)

    def _download_file(self, endpoint: str, filename: str, local_dir: str) -> Optional[str]:
        """Stream download a file from Ultron."""
        local_path = Path(local_dir) / filename
        try:
            resp = self.session.get(f"{self.base_url}{endpoint}",
                                    stream=True, timeout=300)
            if resp.status_code == 200:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Downloaded: {local_path} ({local_path.stat().st_size / 1024 / 1024:.1f} MB)")
                return str(local_path)
        except Exception as e:
            logger.error(f"Download failed: {e}")
        return None

    # --- Avatar (MuseTalk) ---

    def generate_avatar(self, audio_file: str, face_image: str = "oracle_face.png",
                         output_name: str = None) -> Optional[Dict]:
        """Generate a talking-head avatar video via MuseTalk.

        Args:
            audio_file: Audio filename (already uploaded to Ultron)
            face_image: Face image filename on Ultron
            output_name: Output video filename

        Returns:
            {"job_id": "...", "status": "processing"} or None
        """
        return self._request("POST", "/generate_avatar", json={
            "audio_file": audio_file,
            "face_image": face_image,
            "output_name": output_name or f"avatar_{audio_file.replace('.mp3', '.mp4')}"
        }, timeout=30)

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a specific job."""
        return self._request("GET", f"/job/{job_id}", timeout=15)

    def download_file(self, filename: str, local_path: str) -> Optional[str]:
        """Download a file from Ultron output to local path."""
        try:
            resp = self.session.get(f"{self.base_url}/download/{filename}",
                                     stream=True, timeout=300)
            if resp.status_code == 200:
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Downloaded: {local_path}")
                return local_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
        return None

    # --- Utility ---

    def list_output(self) -> List[Dict]:
        """List output files on Ultron."""
        result = self._request("GET", "/list_output")
        return result.get("files", []) if result else []

    def disk_usage(self) -> Optional[Dict]:
        """Get Ultron disk usage."""
        return self._request("GET", "/disk")

    def cleanup(self, days: int = 7) -> Optional[Dict]:
        """Clean up old files on Ultron."""
        return self._request("POST", "/cleanup", json={"days": days})


# Singleton instance
ultron = UltronClient()

# Export local mode flag so other modules can check
def is_local_mode() -> bool:
    """Returns True when pipeline should use local ffmpeg instead of HTTP API."""
    return LOCAL_MODE
