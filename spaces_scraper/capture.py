"""
capture.py — HLS Audio Stream Capture
Monitors an X Spaces HLS playlist, downloads new audio segments as they appear,
and pushes them to an asyncio queue for the transcriber.

Design:
- One AudioCapture instance per active Space
- Fetches the master .m3u8 → finds audio-only variant → polls for new segments
- Segments are ~2–6s of AAC audio; written to tmp files then queued
- ffmpeg converts each segment from AAC→WAV (16 kHz mono) for Whisper
"""

import asyncio
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiohttp
import m3u8

import config

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    path: str        # temp WAV file path
    space_id: str
    segment_index: int
    captured_at: float


class AudioCapture:
    """
    Captures audio from a single live X Space via its HLS stream URL.
    Segments are decoded to 16 kHz mono WAV and placed in `queue`.
    """

    def __init__(self, space_id: str, hls_url: str, output_queue: asyncio.Queue):
        self.space_id = space_id
        self.hls_url = hls_url
        self.queue = output_queue
        self.running = False
        self._seen_segments: set[str] = set()
        self._segment_index = 0
        self._tmpdir = tempfile.mkdtemp(prefix=f"spaces_{space_id}_")
        logger.info(f"AudioCapture [{space_id}] temp dir: {self._tmpdir}")

    async def start(self):
        """Begin capturing. Runs until stop() is called."""
        self.running = True
        logger.info(f"AudioCapture [{self.space_id}] starting HLS pull from {self.hls_url[:70]}...")
        try:
            await self._pull_loop()
        finally:
            self.running = False
            logger.info(f"AudioCapture [{self.space_id}] stopped.")

    def stop(self):
        self.running = False

    # ─── Internal ─────────────────────────────────────────────────────────

    async def _resolve_audio_playlist(self, master_url: str) -> Optional[str]:
        """
        From a master .m3u8 playlist, find the audio-only variant URL.
        X Spaces often has: audio-only/chunk_...m3u8
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(master_url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    r.raise_for_status()
                    content = await r.text()

            playlist = m3u8.loads(content)

            # Look for audio-only or lowest-bandwidth variant
            if playlist.is_variant:
                # Prefer "audio-only" track
                for media in (playlist.media or []):
                    if media.type == "AUDIO" and media.uri:
                        uri = media.uri
                        if not uri.startswith("http"):
                            base = master_url.rsplit("/", 1)[0]
                            uri = f"{base}/{uri}"
                        logger.info(f"Resolved audio media URI: {uri[:70]}")
                        return uri

                # Fall back to first playlist (usually lowest bitrate)
                for pl in playlist.playlists:
                    uri = pl.uri
                    if not uri.startswith("http"):
                        base = master_url.rsplit("/", 1)[0]
                        uri = f"{base}/{uri}"
                    # Prefer "audio-only" in the URL path
                    if "audio-only" in uri or "audio_only" in uri:
                        logger.info(f"Resolved audio-only variant: {uri[:70]}")
                        return uri

                # Take first variant
                first = playlist.playlists[0].uri
                if not first.startswith("http"):
                    base = master_url.rsplit("/", 1)[0]
                    first = f"{base}/{first}"
                logger.info(f"Using first variant: {first[:70]}")
                return first

            # Already a media playlist
            return master_url

        except Exception as e:
            logger.error(f"_resolve_audio_playlist: {e}")
            return None

    async def _pull_loop(self):
        """
        Main loop: fetch the media playlist every ~2s, download new segments.
        """
        audio_playlist_url = await self._resolve_audio_playlist(self.hls_url)
        if not audio_playlist_url:
            logger.error(f"[{self.space_id}] Could not resolve audio playlist — aborting capture")
            return

        consecutive_errors = 0
        while self.running:
            try:
                new_segments = await self._fetch_new_segments(audio_playlist_url)
                if new_segments:
                    logger.debug(f"[{self.space_id}] {len(new_segments)} new segment(s)")
                    for seg_url in new_segments:
                        wav_path = await self._download_and_convert(seg_url)
                        if wav_path:
                            item = AudioSegment(
                                path=wav_path,
                                space_id=self.space_id,
                                segment_index=self._segment_index,
                                captured_at=time.time(),
                            )
                            self._segment_index += 1
                            await self.queue.put(item)
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                logger.warning(f"[{self.space_id}] pull_loop error ({consecutive_errors}): {e}")
                if consecutive_errors >= 5:
                    logger.error(f"[{self.space_id}] Too many consecutive errors — stopping capture")
                    break

            await asyncio.sleep(2)

    async def _fetch_new_segments(self, playlist_url: str) -> list[str]:
        """Fetch media playlist and return URIs of segments we haven't seen yet."""
        async with aiohttp.ClientSession() as session:
            async with session.get(playlist_url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                r.raise_for_status()
                content = await r.text()

        playlist = m3u8.loads(content)
        base = playlist_url.rsplit("/", 1)[0]

        new = []
        for seg in playlist.segments:
            uri = seg.uri
            if not uri.startswith("http"):
                uri = f"{base}/{uri}"
            if uri not in self._seen_segments:
                self._seen_segments.add(uri)
                new.append(uri)

        return new

    async def _download_and_convert(self, segment_url: str) -> Optional[str]:
        """
        Download an AAC segment and convert to 16 kHz mono WAV via ffmpeg.
        Returns path to the WAV file, or None on failure.
        """
        seg_name = re.sub(r"[^\w]", "_", segment_url.split("/")[-1].split("?")[0])
        aac_path = os.path.join(self._tmpdir, f"{self._segment_index}_{seg_name}.aac")
        wav_path = os.path.join(self._tmpdir, f"{self._segment_index}_{seg_name}.wav")

        try:
            # Download AAC segment
            async with aiohttp.ClientSession() as session:
                async with session.get(segment_url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    r.raise_for_status()
                    data = await r.read()

            with open(aac_path, "wb") as f:
                f.write(data)

            # Convert to WAV with ffmpeg
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-i", aac_path,
                "-ar", "16000",   # 16 kHz sample rate for Whisper
                "-ac", "1",       # mono
                "-f", "wav",
                wav_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=30)

            if proc.returncode != 0:
                logger.warning(f"ffmpeg failed for {seg_name}")
                return None

            # Clean up raw AAC
            os.unlink(aac_path)
            return wav_path

        except asyncio.TimeoutError:
            logger.warning(f"Timeout downloading/converting segment: {segment_url[:60]}")
            return None
        except Exception as e:
            logger.warning(f"_download_and_convert failed: {e}")
            return None

    def cleanup(self):
        """Remove temp directory."""
        try:
            import shutil
            shutil.rmtree(self._tmpdir, ignore_errors=True)
        except Exception:
            pass


# ─── ffmpeg-based direct capture (alternative) ──────────────────────────────

class FFmpegCapture:
    """
    Alternative: pipe the whole HLS stream through ffmpeg → chunked WAV files.
    Simpler but produces larger temp files. Use if segment-by-segment fails.
    """

    CHUNK_SECONDS = 5

    def __init__(self, space_id: str, hls_url: str, output_queue: asyncio.Queue):
        self.space_id = space_id
        self.hls_url = hls_url
        self.queue = output_queue
        self.running = False
        self._tmpdir = tempfile.mkdtemp(prefix=f"ffcap_{space_id}_")
        self._chunk_index = 0

    async def start(self):
        self.running = True
        logger.info(f"FFmpegCapture [{self.space_id}] starting segment-split capture")
        try:
            await self._capture_loop()
        finally:
            self.running = False

    def stop(self):
        self.running = False

    async def _capture_loop(self):
        """
        Run ffmpeg to split HLS stream into N-second WAV chunks.
        Uses segment muxer to produce individual files.
        """
        output_pattern = os.path.join(self._tmpdir, "chunk_%04d.wav")

        cmd = [
            "ffmpeg", "-y",
            "-i", self.hls_url,
            "-ar", "16000",
            "-ac", "1",
            "-f", "segment",
            "-segment_time", str(self.CHUNK_SECONDS),
            "-segment_format", "wav",
            "-reset_timestamps", "1",
            output_pattern,
        ]

        logger.info(f"ffmpeg command: {' '.join(cmd[:5])} ...")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        # Watch for new chunk files while ffmpeg runs
        last_chunk = -1
        while self.running:
            # Scan for completed chunks
            for i in range(last_chunk + 1, last_chunk + 10):
                chunk_path = os.path.join(self._tmpdir, f"chunk_{i:04d}.wav")
                # A file is "done" when the NEXT chunk exists (ffmpeg is writing it)
                next_chunk = os.path.join(self._tmpdir, f"chunk_{i+1:04d}.wav")
                if os.path.exists(chunk_path) and os.path.exists(next_chunk):
                    await self.queue.put(AudioSegment(
                        path=chunk_path,
                        space_id=self.space_id,
                        segment_index=i,
                        captured_at=time.time(),
                    ))
                    last_chunk = i

            if proc.returncode is not None:
                logger.info(f"FFmpegCapture [{self.space_id}] ffmpeg exited: {proc.returncode}")
                break

            await asyncio.sleep(1)

        if proc.returncode is None:
            proc.terminate()
            await proc.wait()

    def cleanup(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)


def make_capture(space_id: str, hls_url: str, queue: asyncio.Queue) -> AudioCapture:
    """Factory: returns the appropriate capture implementation."""
    return AudioCapture(space_id, hls_url, queue)
