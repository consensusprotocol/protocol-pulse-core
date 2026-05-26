"""
YouTube Channel Scanner
========================
Scans partner channels for recent videos, downloads audio,
transcribes with word-level timestamps via Ultron.

Upgrade from intelligence_pipeline.py Phase 1:
- Word-level timestamps for precision clip cutting
- Structured transcript output with segments.words[]
- Age-based filtering (configurable hours)
"""
import os
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from pp_services.video_engine.ultron_client import ultron

logger = logging.getLogger("YouTubeScanner")


class YouTubeScanner:
    """Scan partner channels and produce transcripts with word-level timestamps."""

    def __init__(self, channels: List[dict], max_age_hours: int = 48):
        self.channels = [c for c in channels if c.get("enabled", True)]
        self.max_age_hours = max_age_hours

    def scan_all(self) -> List[dict]:
        """Scan all channels for recent videos. Returns list of video metadata dicts."""
        logger.info(f"Scanning {len(self.channels)} channels for videos < {self.max_age_hours}h old...")
        videos = []

        for channel in self.channels:
            try:
                video = self._scan_channel(channel)
                if video:
                    videos.append(video)
                    logger.info(f"  + {channel['name']}: {video['title'][:60]}")
                else:
                    logger.info(f"  - {channel['name']}: no recent videos")
            except Exception as e:
                logger.warning(f"  ! {channel['name']}: scan failed — {e}")

        logger.info(f"Found {len(videos)} recent videos across {len(self.channels)} channels")
        return videos

    def _scan_channel(self, channel: dict) -> Optional[dict]:
        """Fetch latest video from a channel via yt-dlp."""
        handle = channel.get("handle", "")
        channel_id = channel.get("channel_id", "")

        # Try handle first (more reliable), then channel_id
        urls = []
        if handle:
            urls.append(f"https://www.youtube.com/{handle}/videos")
        if channel_id:
            urls.append(f"https://www.youtube.com/channel/{channel_id}/videos")

        for url in urls:
            try:
                cmd = [
                    "yt-dlp", "--flat-playlist", "--no-download",
                    "--print", "%(id)s|||%(title)s|||%(duration)s|||%(upload_date)s",
                    "--playlist-items", "1",
                    url
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    continue

                line = result.stdout.strip()
                if not line or "|||" not in line:
                    continue

                parts = line.split("|||")
                if len(parts) < 4:
                    continue

                video_id, title, duration_str, upload_date = parts[0], parts[1], parts[2], parts[3]

                # Check age
                if upload_date and len(upload_date) == 8:
                    try:
                        upload_dt = datetime.strptime(upload_date, "%Y%m%d")
                        age = datetime.utcnow() - upload_dt
                        if age > timedelta(hours=self.max_age_hours):
                            return None
                    except ValueError:
                        pass

                duration = 0
                try:
                    duration = int(float(duration_str)) if duration_str and duration_str != "NA" else 0
                except (ValueError, TypeError):
                    pass

                return {
                    "channel_name": channel["name"],
                    "channel_handle": handle,
                    "channel_id": channel_id,
                    "video_id": video_id,
                    "title": title,
                    "duration_seconds": duration,
                    "upload_date": upload_date,
                    "tags": channel.get("tags", []),
                    "priority": channel.get("priority", "medium"),
                }

            except subprocess.TimeoutExpired:
                logger.warning(f"  yt-dlp timeout for {channel['name']}")
                continue
            except Exception as e:
                logger.warning(f"  yt-dlp error for {channel['name']}: {e}")
                continue

        return None

    def download_and_transcribe(self, videos: List[dict],
                                 bundle_path: Path = None) -> Dict[str, dict]:
        """
        Download audio and transcribe all videos via Ultron.
        Returns dict of video_id -> {transcript, segments, words, audio_path}.

        Requests word-level timestamps from Whisper for precision clip cutting.
        """
        if not videos:
            return {}

        video_ids = [v["video_id"] for v in videos]
        logger.info(f"Downloading audio for {len(video_ids)} videos on Ultron...")

        # Batch download audio
        try:
            dl_job_id = ultron.batch_download_audio(video_ids)
            if not dl_job_id:
                logger.error("Batch audio download: no job_id returned (Ultron unreachable?)")
                return {}
            dl_result = self._poll_job(dl_job_id, "audio download", timeout=600)
            if not dl_result:
                logger.error("Batch audio download: polling failed or timed out")
                return {}
        except Exception as e:
            logger.error(f"Batch audio download failed: {e}")
            return {}

        # Batch transcribe with word-level timestamps
        logger.info(f"Transcribing {len(video_ids)} videos on Ultron (word-level timestamps)...")
        try:
            tx_job_id = ultron.batch_transcribe(video_ids)
            if not tx_job_id:
                logger.error("Batch transcribe: no job_id returned (Ultron unreachable?)")
                return {}
            tx_result = self._poll_job(tx_job_id, "transcription", timeout=1800)
            if not tx_result:
                logger.error("Batch transcription: polling failed or timed out")
                return {}
        except Exception as e:
            logger.error(f"Batch transcription failed: {e}")
            return {}

        # Fetch transcripts
        logger.info("Fetching transcripts...")
        try:
            transcripts_data = ultron.get_transcripts(video_ids)
            raw_transcripts = transcripts_data.get("transcripts", transcripts_data)
        except Exception as e:
            logger.error(f"Transcript fetch failed: {e}")
            return {}

        # Process into structured format
        result = {}
        for vid in videos:
            vid_id = vid["video_id"]
            tx = raw_transcripts.get(vid_id, {})
            if not tx:
                logger.warning(f"  No transcript for {vid_id}")
                continue

            # Build structured transcript with word-level data
            text = tx.get("text", "")
            segments = tx.get("segments", [])

            # Extract word-level timestamps if available
            words = []
            for seg in segments:
                seg_words = seg.get("words", [])
                if seg_words:
                    words.extend(seg_words)

            # Build timestamped text for Grok
            timestamped_lines = []
            for seg in segments:
                start = seg.get("start", 0)
                seg_text = seg.get("text", "").strip()
                if seg_text:
                    mm = int(start // 60)
                    ss = int(start % 60)
                    timestamped_lines.append(f"[{mm:02d}:{ss:02d}] {seg_text}")

            result[vid_id] = {
                "channel_name": vid["channel_name"],
                "channel_handle": vid.get("channel_handle", ""),
                "video_id": vid_id,
                "title": vid["title"],
                "text": text,
                "segments": segments,
                "words": words,
                "timestamped_text": "\n".join(timestamped_lines),
                "char_count": len(text),
                "segment_count": len(segments),
                "word_count": len(words),
                "has_word_timestamps": len(words) > 0,
            }

            logger.info(f"  {vid['channel_name']}: {len(text)} chars, "
                        f"{len(segments)} segments, {len(words)} words")

        # Save to episode bundle if provided
        if bundle_path:
            source_data = {
                "scan_time": datetime.utcnow().isoformat(),
                "channels_scanned": len(self.channels),
                "videos_found": len(videos),
                "transcripts_obtained": len(result),
                "videos": [v for v in videos],
                "transcripts": {
                    vid_id: {
                        "channel_name": t["channel_name"],
                        "title": t["title"],
                        "char_count": t["char_count"],
                        "segment_count": t["segment_count"],
                        "word_count": t["word_count"],
                        "has_word_timestamps": t["has_word_timestamps"],
                    }
                    for vid_id, t in result.items()
                }
            }
            out_path = bundle_path / "inputs" / "youtube_scan.json"
            out_path.write_text(json.dumps(source_data, indent=2, default=str))

        return result

    def _poll_job(self, job_id: str, label: str, timeout: int = 600, interval: int = 10):
        """Poll Ultron job until complete or timeout."""
        start = time.time()
        consecutive_failures = 0
        max_failures = 10  # Abort after 10 consecutive poll failures

        while time.time() - start < timeout:
            try:
                result = ultron.get_job_status(job_id)

                if result is None:
                    consecutive_failures += 1
                    elapsed = int(time.time() - start)
                    logger.warning(
                        f"  {label}: poll returned None ({consecutive_failures}/{max_failures} failures, {elapsed}s elapsed)")
                    if consecutive_failures >= max_failures:
                        logger.error(f"  {label}: aborting after {max_failures} consecutive poll failures")
                        return None
                    time.sleep(interval)
                    continue

                consecutive_failures = 0  # Reset on success
                state = result.get("status", "unknown")
                progress = result.get("progress", 0)

                if state == "complete":
                    logger.info(f"  {label} job complete ({int(time.time() - start)}s)")
                    return result
                elif state in ("failed", "error"):
                    raise RuntimeError(f"{label} job failed: {result.get('error', 'unknown')}")

                logger.info(f"  {label}: {state} ({progress}%)")
                time.sleep(interval)

            except RuntimeError:
                raise
            except Exception as e:
                consecutive_failures += 1
                logger.warning(f"  {label}: poll error ({consecutive_failures}/{max_failures}): {e}")
                if consecutive_failures >= max_failures:
                    logger.error(f"  {label}: aborting after {max_failures} consecutive errors")
                    return None
                time.sleep(interval)

        logger.error(f"  {label}: timed out after {timeout}s")
        return None
