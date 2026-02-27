#!/usr/bin/env python3
"""
test_single_channel.py — Test the video engine pipeline with a single channel.

Tests Phases 1-3: Scan → Transcribe → Analyze (Grok) → Select

Does NOT produce video or distribute (Phase 4-5). Use this to verify
the intelligence pipeline works before running the full production pipeline.

Usage:
    python scripts/test_single_channel.py                     # Uses first enabled channel
    python scripts/test_single_channel.py --channel "Simply Bitcoin"
    python scripts/test_single_channel.py --video-id "dQw4w9WgXcQ"  # Test with specific video
"""

import os
import sys
import json
import argparse
import logging
import subprocess
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Test video engine with single channel")
    parser.add_argument('--channel', type=str, help='Channel name to test')
    parser.add_argument('--video-id', type=str, help='Specific YouTube video ID to test')
    parser.add_argument('--skip-transcribe', action='store_true', help='Skip transcription (use cached)')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("SINGLE CHANNEL TEST — Video Engine Pipeline")
    print("=" * 60)

    # Step 1: Check Ultron
    print("\n--- Step 1: Check Ultron ---")
    from services.video_engine.ultron_client import ultron
    health = ultron.health_check()
    if health.get("status") != "ok":
        print(f"FAIL: Ultron is not healthy: {health}")
        return 1
    print(f"OK: Ultron v{health.get('version', '?')}, {health.get('gpu_count', 0)} GPUs")

    # Step 2: Select channel
    print("\n--- Step 2: Select Channel ---")
    from services.config_loader import get_enabled_channels
    channels = get_enabled_channels()

    if args.channel:
        channel = next((c for c in channels if c["name"].lower() == args.channel.lower()), None)
        if not channel:
            print(f"FAIL: Channel '{args.channel}' not found. Available:")
            for c in channels:
                print(f"  - {c['name']}")
            return 1
    else:
        channel = channels[0]

    print(f"OK: Testing with '{channel['name']}' ({channel['channel_id']})")

    # Step 3: Get latest video
    print("\n--- Step 3: Get Latest Video ---")
    if args.video_id:
        video = {"id": args.video_id, "title": "Manual test video", "duration": 0}
        print(f"OK: Using provided video ID: {args.video_id}")
    else:
        try:
            # Use handle for yt-dlp (more reliable than channel_id)
            handle = channel.get('handle', '')
            channel_id = channel.get('channel_id', '')
            url = f"https://www.youtube.com/{handle}/videos" if handle else f"https://www.youtube.com/channel/{channel_id}/videos"

            cmd = [
                "yt-dlp", "--flat-playlist", "--playlist-items", "1",
                "--print", '{"id": "%(id)s", "title": "%(title)s", "duration": %(duration)s, "upload_date": "%(upload_date)s"}',
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            lines = [l for l in result.stdout.strip().split('\n') if l.startswith('{')]
            if not lines:
                print(f"FAIL: No videos found for {channel['name']} via {url}")
                print(f"  stderr: {result.stderr[:200]}")
                return 1
            video = json.loads(lines[-1])
            print(f"OK: {video.get('title', 'Unknown')[:60]}")
            print(f"    Video ID: {video['id']}")
            print(f"    Duration: {video.get('duration', 0)}s")
            print(f"    Upload: {video.get('upload_date', 'unknown')}")
        except Exception as e:
            print(f"FAIL: Error fetching video: {e}")
            return 1

    # Step 4: Download audio on Ultron
    print("\n--- Step 4: Download Audio (Ultron) ---")
    if not args.skip_transcribe:
        download_job = ultron.batch_download_audio([video["id"]])
        if download_job:
            print(f"  Job started: {download_job}")
            dl_result = ultron.poll_job(download_job, max_wait=120, interval=5)
            print(f"  Result: {json.dumps(dl_result, indent=2)[:200]}")
        else:
            print("  WARNING: batch_download_audio returned None (may already be cached)")
    else:
        print("  SKIPPED (--skip-transcribe)")

    # Step 5: Transcribe on Ultron
    print("\n--- Step 5: Transcribe Audio (Ultron GPU) ---")
    if not args.skip_transcribe:
        transcribe_job = ultron.batch_transcribe([video["id"]])
        if transcribe_job:
            print(f"  Job started: {transcribe_job}")
            tr_result = ultron.poll_job(transcribe_job, max_wait=300, interval=10)
            print(f"  Result: {json.dumps(tr_result, indent=2)[:200]}")
        else:
            print("  WARNING: batch_transcribe returned None")
    else:
        print("  SKIPPED (--skip-transcribe)")

    # Step 6: Fetch transcript
    print("\n--- Step 6: Fetch Transcript ---")
    transcripts = ultron.get_transcripts([video["id"]])
    if video["id"] not in transcripts:
        print(f"FAIL: No transcript returned for {video['id']}")
        return 1

    transcript = transcripts[video["id"]]
    text = transcript.get("text", "")
    segments = transcript.get("segments", [])
    print(f"OK: {len(text)} chars, {len(segments)} segments")
    if text:
        print(f"  First 200 chars: {text[:200]}...")

    # Step 7: Analyze with Grok
    print("\n--- Step 7: Analyze with Grok ---")
    grok_key = os.environ.get("XAI_API_KEY")
    if not grok_key:
        print("SKIP: No XAI_API_KEY set — cannot test Grok analysis")
        print("  Set XAI_API_KEY in Replit Secrets to enable this step")
    else:
        from services.video_engine.intelligence_pipeline import IntelligencePipeline
        pipeline = IntelligencePipeline()

        timestamped = "\n".join([f"[{s['start']:.1f}s] {s['text']}" for s in segments])
        highlight = pipeline.analyze_with_grok(timestamped, channel, video.get("title", ""))

        if highlight:
            print(f"OK: Grok analysis complete")
            print(f"  Hook Score: {highlight.get('hook_score', 0)}")
            print(f"  Key Quote: {highlight.get('key_quote', '')[:80]}")
            print(f"  Clip: {highlight.get('start_time', 0):.1f}s - {highlight.get('end_time', 0):.1f}s")
            print(f"  Themes: {', '.join(highlight.get('themes', []))}")
            print(f"  Tweet: {highlight.get('tweet_text', '')[:100]}")

            # Save result
            out_path = f"data/video_engine/intel/test_single_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w") as f:
                json.dump({
                    "channel": channel["name"],
                    "video_id": video["id"],
                    "video_title": video.get("title", ""),
                    "highlight": highlight,
                    "transcript_length": len(text),
                    "timestamp": datetime.now().isoformat()
                }, f, indent=2)
            print(f"\n  Results saved to: {out_path}")
        else:
            print("FAIL: Grok analysis returned None")
            return 1

    print("\n" + "=" * 60)
    print("SINGLE CHANNEL TEST COMPLETE")
    print("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
