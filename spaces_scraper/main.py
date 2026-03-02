"""
main.py — Spaces Scraper Entry Point

Wires together:
  SpaceDetector → AudioCapture → RealtimeTranscriber → SentimentAnalyzer
  → FastAPI server on port 8210

Usage:
  python3 main.py                 # run full pipeline
  python3 main.py --test          # 60s test pipeline run, then print report
  python3 main.py --api-only      # start API only (no live capture)
"""

import argparse
import asyncio
import logging
import logging.handlers
import sys
import time
from typing import Optional

import uvicorn

import config
from api_server import app, inject_state
from analyzer import SentimentAnalyzer
from capture import make_capture
from detector import SpaceDetector, LiveSpace
from transcriber import RealtimeTranscriber

# ─── Logging Setup ───────────────────────────────────────────────────────────

def setup_logging(level: str = "INFO"):
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)-20s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # File handler (rotating)
    fh = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=3
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)


logger = logging.getLogger(__name__)


# ─── Pipeline Orchestrator ───────────────────────────────────────────────────

class SpacesPipeline:
    """
    Manages the full pipeline lifecycle:
    - Polls for live spaces
    - Starts/stops audio capture per space
    - Feeds transcription queue
    - Runs sentiment analysis loop
    """

    def __init__(self):
        self.detector = SpaceDetector()
        self.transcriber = RealtimeTranscriber()
        self.analyzer = SentimentAnalyzer()
        self._audio_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._active_captures: dict[str, object] = {}  # space_id → capture task
        self._running = False

    async def start(self):
        """Start all pipeline components concurrently."""
        self._running = True
        inject_state(self.detector, self.transcriber, self.analyzer)

        logger.info("=== Spaces Scraper Pipeline Starting ===")
        logger.info(f"Target accounts: {len(config.TARGET_ACCOUNTS)}")
        logger.info(f"Poll interval: {config.DETECTOR_POLL_INTERVAL}s")
        logger.info(f"Whisper model: {config.WHISPER_MODEL} on {config.WHISPER_DEVICE}")
        logger.info(f"API port: {config.API_PORT}")

        # Warm up Whisper in background
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, lambda: __import__("transcriber").get_whisper_model())

        await asyncio.gather(
            self._detection_loop(),
            self.transcriber.process_queue(self._audio_queue),
            self.analyzer.run_analysis_loop(self.transcriber),
        )

    async def _detection_loop(self):
        """Poll for live spaces and manage capture tasks."""
        logger.info("Detection loop started")
        while self._running:
            try:
                spaces = await self.detector.detect_once()
                if spaces:
                    logger.info(f"Live spaces: {[s.host_username for s in spaces]}")
                await self._sync_captures(spaces)
            except Exception as e:
                logger.error(f"Detection loop error: {e}", exc_info=True)

            await asyncio.sleep(config.DETECTOR_POLL_INTERVAL)

    async def _sync_captures(self, live_spaces: list[LiveSpace]):
        """
        Start capture for newly detected spaces; stop capture for ended spaces.
        Respects MAX_CONCURRENT_SPACES limit.
        """
        live_ids = {s.space_id for s in live_spaces}
        active_ids = set(self._active_captures.keys())

        # Stop captures for spaces that ended
        ended = active_ids - live_ids
        for space_id in ended:
            logger.info(f"Space ended, stopping capture: {space_id}")
            task = self._active_captures.pop(space_id, None)
            if task:
                task.cancel()

        # Start captures for new spaces (up to MAX_CONCURRENT_SPACES)
        new_spaces = [s for s in live_spaces if s.space_id not in active_ids]
        slots_available = config.MAX_CONCURRENT_SPACES - len(self._active_captures)

        for space in new_spaces[:slots_available]:
            if not space.hls_url:
                logger.warning(f"No HLS URL for space {space.space_id} (@{space.host_username}) — skipping capture")
                continue

            logger.info(f"Starting capture for @{space.host_username}: {space.space_id}")
            capture = make_capture(space.space_id, space.hls_url, self._audio_queue)
            task = asyncio.create_task(capture.start(), name=f"capture_{space.space_id}")
            self._active_captures[space.space_id] = task

    def stop(self):
        self._running = False
        self.transcriber.stop()
        self.analyzer.stop()
        for task in self._active_captures.values():
            task.cancel()


# ─── Test Mode ───────────────────────────────────────────────────────────────

async def run_test_mode():
    """Run a 60-second test: detect spaces, capture, transcribe, analyze, print report."""
    setup_logging("INFO")
    logger.info("=== TEST MODE: 60-second pipeline test ===")

    pipeline = SpacesPipeline()
    inject_state(pipeline.detector, pipeline.transcriber, pipeline.analyzer)

    # Step 1: Detect
    logger.info("Step 1/4: Detecting live spaces...")
    spaces = await pipeline.detector.detect_once()
    print(f"\n[DETECTOR] Found {len(spaces)} live space(s):")
    for s in spaces:
        print(f"  [{s.detected_via}] @{s.host_username}: {s.title or '(no title)'}")
        print(f"    HLS: {s.hls_url or 'NOT RESOLVED'}")

    if not spaces:
        print("\n  No live spaces found — will test transcriber in isolation.")

    # Step 2: Test transcriber
    logger.info("Step 2/4: Testing Whisper transcriber...")
    import subprocess, tempfile, os
    test_wav = tempfile.mktemp(suffix=".wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anoisesrc=r=16000:color=white:amplitude=0.001:duration=10",
        "-ar", "16000", "-ac", "1", test_wav
    ], capture_output=True)

    t0 = time.perf_counter()
    chunk = pipeline.transcriber.transcribe_file(test_wav, "test")
    elapsed = time.perf_counter() - t0
    print(f"\n[TRANSCRIBER] Whisper large-v3 on RTX 4090:")
    if chunk:
        print(f"  10s audio transcribed in {elapsed:.2f}s ({10/elapsed:.1f}x realtime)")
        print(f"  Text: '{chunk.text or '(silence)'}'")
    else:
        print(f"  FAILED — check GPU/CUDA setup")

    # Step 3: If we have a live space with HLS, capture 60s
    if spaces and spaces[0].hls_url:
        s = spaces[0]
        logger.info(f"Step 3/4: Capturing 60s from @{s.host_username}...")
        print(f"\n[CAPTURE] Capturing 60s from @{s.host_username}...")
        capture = make_capture(s.space_id, s.hls_url, pipeline._audio_queue)
        capture_task = asyncio.create_task(capture.start())

        # Process queue for 60s
        process_task = asyncio.create_task(
            pipeline.transcriber.process_queue(pipeline._audio_queue)
        )

        await asyncio.sleep(60)
        capture.stop()
        pipeline.transcriber.stop()
        capture_task.cancel()
        process_task.cancel()
        await asyncio.sleep(1)

        rolling = pipeline.transcriber.get_transcript(s.space_id)
        if rolling:
            print(f"  Captured {rolling.total_chunks} transcript chunks")
            print(f"  Transcript: {rolling.get_text()[:200]}...")

            # Step 4: Analyze
            logger.info("Step 4/4: Analyzing sentiment...")
            transcript = rolling.get_text()
            result = pipeline.analyzer.analyze_transcript(s.space_id, transcript)
            if result:
                print(f"\n[SENTIMENT] {result.sentiment_label} ({result.sentiment_score}/100)")
                print(f"  Topics: {result.key_topics}")
                print(f"  Signals: {result.market_signals}")
                print(f"  Confidence: {result.confidence:.2f}")
    else:
        print("\n[CAPTURE] No live space with HLS — skipping capture test.")
        print("[SENTIMENT] Skipping (no transcript data).")

    stats = pipeline.transcriber.get_stats()
    print(f"\n=== SUMMARY ===")
    print(f"  Spaces detected: {len(spaces)}")
    print(f"  Segments transcribed: {stats['segments_processed']}")
    print(f"  Avg latency: {stats.get('avg_latency_ms', 0):.0f}ms")
    print(f"  Realtime factor: {stats.get('realtime_factor', 0):.1f}x")
    print(f"\nAPI would be available at: http://localhost:{config.API_PORT}/")


# ─── Entry Point ─────────────────────────────────────────────────────────────

async def main_async(args):
    if args.test:
        await run_test_mode()
        return

    setup_logging(config.LOG_LEVEL)

    if args.api_only:
        logger.info("API-only mode — no live capture")
        inject_state(SpaceDetector(), RealtimeTranscriber(), SentimentAnalyzer())
        # Fall through to uvicorn below
    else:
        # Start pipeline in background
        pipeline = SpacesPipeline()
        asyncio.create_task(pipeline.start())

    # Start FastAPI server
    uvicorn_config = uvicorn.Config(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(uvicorn_config)
    logger.info(f"API server starting on http://{config.API_HOST}:{config.API_PORT}")
    await server.serve()


def main():
    parser = argparse.ArgumentParser(description="Protocol Pulse — X Spaces Scraper")
    parser.add_argument("--test", action="store_true", help="Run 60s integration test")
    parser.add_argument("--api-only", action="store_true", help="Start API server only")
    parser.add_argument("--log-level", default=config.LOG_LEVEL, help="Log level")
    args = parser.parse_args()

    if not args.test:
        setup_logging(args.log_level)

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Interrupted — shutting down")


if __name__ == "__main__":
    main()
