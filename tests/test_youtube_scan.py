"""
Test YouTube Scanner + Local Whisper — End-to-End
"""
import sys
sys.path.insert(0, "/home/ultron/protocol_pulse")

from services.video_engine.sources.youtube_scanner import YouTubeScanner
from services.video_engine.local_whisper import download_audio, transcribe_audio

TEST_CHANNELS = [
    {"name": "Simply Bitcoin", "handle": "@SimplyBitcoin", "channel_id": "", "enabled": True, "tags": ["daily"], "priority": "high"},
    {"name": "Bitcoin Magazine", "handle": "@BitcoinMagazine", "channel_id": "", "enabled": True, "tags": ["news"], "priority": "high"},
    {"name": "The Bitcoin Layer", "handle": "@TheBitcoinLayer", "channel_id": "", "enabled": True, "tags": ["macro"], "priority": "medium"},
]


def test_scan():
    print("=" * 60)
    print("TEST: YouTube Scanner — Channel Scan")
    print("=" * 60)

    scanner = YouTubeScanner(TEST_CHANNELS, max_age_hours=168)  # 7 days
    videos = scanner.scan_all()

    print(f"\nFound {len(videos)} videos:")
    for v in videos:
        print(f"  [{v['priority']}] {v['channel_name']}: {v['title'][:60]}")
        print(f"    ID: {v['video_id']}, Duration: {v['duration_seconds']}s")

    assert len(videos) >= 1, "Should find at least 1 video"
    return videos


def test_download_transcribe(video):
    print("\n" + "=" * 60)
    print(f"TEST: Download + Transcribe — {video['title'][:50]}")
    print("=" * 60)

    audio = download_audio(video["video_id"], "/tmp/yt_test")
    assert audio, "Audio download should succeed"

    # Transcribe first 2 minutes
    import subprocess
    short_path = f"/tmp/yt_test/{video['video_id']}_short.wav"
    subprocess.run(["ffmpeg", "-y", "-i", audio, "-t", "120", "-ar", "16000", "-ac", "1", short_path],
                   capture_output=True, timeout=60)

    result = transcribe_audio(short_path, model_size="base")
    print(f"  Text: {result['text'][:200]}...")
    print(f"  Segments: {result['segment_count']}")
    print(f"  Words: {result['word_count']}")
    print(f"  Has word timestamps: {result['has_word_timestamps']}")

    assert result["word_count"] > 0, "Should have word-level timestamps"
    return result


if __name__ == "__main__":
    videos = test_scan()
    if videos:
        test_download_transcribe(videos[0])
    print("\n✓ All YouTube scanner tests passed!")
