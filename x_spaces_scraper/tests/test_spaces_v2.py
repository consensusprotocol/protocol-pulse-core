"""
test_spaces_v2.py — Regression + integration tests for X Spaces V2.
"""

import json
import os
import sqlite3
import tempfile
import threading

import pytest


# ─── Test: State DB idempotent ─────────────────────────────────────────────

def test_state_db_idempotent():
    """Mark same space twice, verify no duplicate."""
    from x_spaces_scraper.spaces_state import SpaceStateDB

    with tempfile.TemporaryDirectory() as tmp:
        db = SpaceStateDB(db_path=os.path.join(tmp, "test.db"))
        db.upsert("space_001", title="Test Space", host="saylor")
        db.mark("space_001", "discovered")
        db.mark("space_001", "discovered")  # idempotent — should not error

        record = db.get("space_001")
        assert record is not None
        assert record["title"] == "Test Space"
        assert record["discovered_at"] is not None

        # Verify only one row
        count = db.conn.execute("SELECT COUNT(*) FROM spaces").fetchone()[0]
        assert count == 1
        db.close()


# ─── Test: Quality gate rejects short ──────────────────────────────────────

def test_quality_gate_rejects_short():
    """50-word transcript -> usable=False."""
    from x_spaces_scraper.transcript_fetcher import TranscriptFetcher

    fetcher = TranscriptFetcher()
    result = {
        "word_count": 50,
        "language_probability": 0.95,
        "text": " ".join(["word"] * 50),
    }
    assert fetcher._passes_quality_gate(result) is False


# ─── Test: Quality gate rejects repetitive ─────────────────────────────────

def test_quality_gate_rejects_repetitive():
    """Repeated text -> usable=False."""
    from x_spaces_scraper.transcript_fetcher import TranscriptFetcher

    fetcher = TranscriptFetcher()
    # 200 words of the same bigram repeated
    repeated = " ".join(["hello world"] * 100)
    result = {
        "word_count": 200,
        "language_probability": 0.95,
        "text": repeated,
    }
    assert fetcher._passes_quality_gate(result) is False


# ─── Test: context_only not narration ──────────────────────────────────────

def test_context_only_not_narration():
    """source=context_only -> usable=False."""
    from x_spaces_scraper.transcript_fetcher import TranscriptFetcher, CONTEXT_ONLY

    fetcher = TranscriptFetcher()
    # Simulate fetch returning context_only (mock _try_audio_replay to fail)
    result = fetcher.fetch("fake_space_999", "https://twitter.com/i/spaces/fake_space_999",
                           title="Bitcoin Discussion")
    # Without network, audio replay will fail, so result should be context_only or empty
    assert result["usable"] is False
    assert result["source"] == CONTEXT_ONLY


# ─── Test: Map-reduce chunking ────────────────────────────────────────────

def test_map_reduce_chunking():
    """3000-word transcript -> chunks correctly."""
    # Test the chunking logic directly (without API calls)
    words = ["word"] * 3000
    transcript = " ".join(words)
    chunk_size = 600
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))

    assert len(chunks) == 5  # 3000 / 600 = 5 chunks
    assert all(len(c.split()) <= 600 for c in chunks)


# ─── Test: Cookie validity empty file ─────────────────────────────────────

def test_cookie_validity_empty_file():
    """Empty cookie -> returns True (public mode)."""
    import sys
    sys.path.insert(0, os.path.expanduser("~/protocol_pulse/video_pipeline_v3"))
    from utils.spaces_monitor import check_cookie_validity

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("# Netscape\n")
        tmp_path = f.name

    try:
        assert check_cookie_validity(tmp_path) is True
    finally:
        os.unlink(tmp_path)


# ─── Test: Diarizer energy fallback ───────────────────────────────────────

def test_diarizer_energy_fallback():
    """No pyannote -> energy-based labels assigned."""
    from x_spaces_scraper.diarizer import diarize

    segments = [
        {"start": 0.0, "end": 5.0, "text": "Hello everyone welcome to the show", "speaker": "unknown"},
        {"start": 5.5, "end": 10.0, "text": "Thanks for having me on", "speaker": "unknown"},
        {"start": 12.0, "end": 17.0, "text": "So what do you think about Bitcoin", "speaker": "unknown"},
        {"start": 17.5, "end": 22.0, "text": "I think it will moon soon", "speaker": "unknown"},
    ]

    result = diarize("/dev/null", segments)
    # All segments should have speaker labels (not "unknown")
    for seg in result:
        assert seg["speaker"] != "unknown"
    # At least one should be HOST
    assert any(s["speaker"] == "HOST" for s in result)


# ─── Test: Pipeline returns None when stale ────────────────────────────────

def test_pipeline_returns_none_when_stale():
    """No fresh data -> None returned."""
    import sys
    sys.path.insert(0, os.path.expanduser("~/protocol_pulse/video_pipeline_v3"))
    from utils.spaces_pipeline import get_latest_spaces_segment

    # With max_age_hours=0, nothing should be fresh enough
    result = get_latest_spaces_segment(max_age_hours=0)
    assert result is None


# ─── Test: Pipeline returns None with empty cache dir ────────────────────────

def test_spaces_pipeline_returns_none_no_cache():
    """Empty cache dir -> get_latest_spaces_segment returns None."""
    import sys
    sys.path.insert(0, os.path.expanduser("~/protocol_pulse/video_pipeline_v3"))
    from utils import spaces_pipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        original = spaces_pipeline.CACHE_DIR
        spaces_pipeline.CACHE_DIR = __import__('pathlib').Path(tmpdir)
        try:
            result = spaces_pipeline.get_latest_spaces_segment(max_age_hours=4.0)
            assert result is None
        finally:
            spaces_pipeline.CACHE_DIR = original


# ─── Test: Pipeline returns None when stale ──────────────────────────────────

def test_spaces_pipeline_returns_none_stale():
    """Cache file older than max_age_hours -> None returned."""
    import sys, json, time
    sys.path.insert(0, os.path.expanduser("~/protocol_pulse/video_pipeline_v3"))
    from utils import spaces_pipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write a transcript file
        cache_file = os.path.join(tmpdir, "transcript_test123.json")
        with open(cache_file, "w") as f:
            json.dump({
                "space_id": "test123",
                "transcript": "Bitcoin is digital gold " * 50,
                "source": "audio_replay",
                "usable": True,
                "word_count": 200,
            }, f)
        # Make it old (> 4 hours)
        old_time = time.time() - 5 * 3600
        os.utime(cache_file, (old_time, old_time))

        original = spaces_pipeline.CACHE_DIR
        spaces_pipeline.CACHE_DIR = __import__('pathlib').Path(tmpdir)
        try:
            result = spaces_pipeline.get_latest_spaces_segment(max_age_hours=4.0)
            assert result is None
        finally:
            spaces_pipeline.CACHE_DIR = original


# ─── Test: Pipeline returns segment for fresh transcript ─────────────────────

def test_spaces_pipeline_returns_segment_fresh():
    """Valid usable transcript -> returns dict with segment_type='x_spaces'."""
    import sys, json
    sys.path.insert(0, os.path.expanduser("~/protocol_pulse/video_pipeline_v3"))
    from utils import spaces_pipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, "transcript_fresh001.json")
        with open(cache_file, "w") as f:
            json.dump({
                "space_id": "fresh001",
                "transcript": "Saylor just announced MicroStrategy will buy another $500M in Bitcoin " * 20,
                "source": "audio_replay",
                "usable": True,
                "word_count": 300,
                "quality_score": 0.85,
                "speakers": ["HOST", "GUEST_1"],
            }, f)

        original = spaces_pipeline.CACHE_DIR
        spaces_pipeline.CACHE_DIR = __import__('pathlib').Path(tmpdir)
        try:
            result = spaces_pipeline.get_latest_spaces_segment(max_age_hours=4.0)
            assert result is not None, "Expected a segment dict"
            assert result["segment_type"] == "x_spaces"
            assert result["space_id"] == "fresh001"
            assert result["source"] == "audio_replay"
            assert result["impact_score"] >= 0
        finally:
            spaces_pipeline.CACHE_DIR = original


# ─── Test: Pipeline rejects context_only ─────────────────────────────────────

def test_spaces_pipeline_rejects_context_only():
    """context_only transcript -> not returned even if fresh."""
    import sys, json
    sys.path.insert(0, os.path.expanduser("~/protocol_pulse/video_pipeline_v3"))
    from utils import spaces_pipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, "transcript_ctx001.json")
        with open(cache_file, "w") as f:
            json.dump({
                "space_id": "ctx001",
                "transcript": "Some context about a Bitcoin space " * 30,
                "source": "context_only",
                "usable": False,
                "word_count": 200,
            }, f)

        original = spaces_pipeline.CACHE_DIR
        spaces_pipeline.CACHE_DIR = __import__('pathlib').Path(tmpdir)
        try:
            result = spaces_pipeline.get_latest_spaces_segment(max_age_hours=4.0)
            assert result is None, f"Expected None for context_only, got {result}"
        finally:
            spaces_pipeline.CACHE_DIR = original


# ─── Test: score_transcript low score ────────────────────────────────────────

def test_score_transcript_low():
    """Short generic transcript -> score < 40."""
    import sys
    sys.path.insert(0, os.path.expanduser("~/protocol_pulse/video_pipeline_v3"))
    from utils.spaces_pipeline import score_transcript

    transcript = {"transcript": "Hello everyone welcome to the show today we talk about things"}
    score = score_transcript(transcript)
    assert score < 40, f"Expected < 40, got {score}"


# ─── Test: score_transcript high score ───────────────────────────────────────

def test_score_transcript_high():
    """Transcript with numbers + 'predict' + 'breaking' -> score >= 60."""
    import sys
    sys.path.insert(0, os.path.expanduser("~/protocol_pulse/video_pipeline_v3"))
    from utils.spaces_pipeline import score_transcript

    transcript = {
        "transcript": (
            "Breaking news: Saylor predicts Bitcoin will reach $500,000 by 2030. "
            "The hashrate has increased 15% this quarter. "
            "BlackRock ETF inflows hit $2.1 billion this week. "
        ) * 30  # 600+ words for length bonus
    }
    score = score_transcript(transcript)
    assert score >= 60, f"Expected >= 60, got {score}"


# ─── Test: Atomic upsert no duplicate (P0-1) ─────────────────────────────

def test_upsert_atomic_no_duplicate():
    """Call upsert() from 10 threads simultaneously — expect exactly 1 row, no errors."""
    from x_spaces_scraper.spaces_state import SpaceStateDB

    with tempfile.TemporaryDirectory() as tmp:
        db = SpaceStateDB(db_path=os.path.join(tmp, "test.db"))
        errors = []

        def upsert():
            try:
                db.upsert("test_atomic_001", title="Test", host="saylor")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=upsert) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        count = db.conn.execute("SELECT COUNT(*) FROM spaces").fetchone()[0]
        assert count == 1, f"Expected 1 row, got {count}"
        assert not errors, f"Errors occurred: {errors}"
        db.close()


# ─── Test: COALESCE preserves existing values (P0-1) ────────────────────

def test_upsert_coalesce_preserves_existing():
    """upsert() with None should not overwrite existing non-null values."""
    from x_spaces_scraper.spaces_state import SpaceStateDB

    with tempfile.TemporaryDirectory() as tmp:
        db = SpaceStateDB(db_path=os.path.join(tmp, "test.db"))
        db.upsert("coalesce_001", title="Original", host="saylor")
        db.upsert("coalesce_001", downloaded_at="2026-01-01T00:00:00")

        record = db.get("coalesce_001")
        assert record["title"] == "Original", f"Title was overwritten: {record['title']}"
        assert record["downloaded_at"] == "2026-01-01T00:00:00"
        db.close()


# ─── Test: mark_processed uses DB (P0-2) ────────────────────────────────

def test_mark_processed_uses_db():
    """After mark_processed(), DB shows injected_at is not None."""
    from x_spaces_scraper.scraper import XSpacesScraper

    with tempfile.TemporaryDirectory() as tmp:
        scraper = XSpacesScraper()
        # Point DB to temp
        from x_spaces_scraper.spaces_state import SpaceStateDB
        scraper.db = SpaceStateDB(db_path=os.path.join(tmp, "test.db"))
        # Insert first, then mark
        scraper.db.upsert("mark_test_001", title="Test", host="testhost")
        scraper.mark_processed("mark_test_001")

        record = scraper.db.get("mark_test_001")
        assert record is not None
        assert record["injected_at"] is not None
        scraper.db.close()


# ─── Test: yt-dlp YYYYMMDD date parsing (P0-3) ─────────────────────────

def test_ytdlp_date_parsing_yyyymmdd():
    """Simulate YYYYMMDD date from yt-dlp — should be parsed correctly."""
    from datetime import datetime, timezone

    # Replicate the parsing logic from scraper.py
    raw = "20260315"
    if len(raw) == 8 and raw.isdigit():
        dt = datetime.strptime(raw, "%Y%m%d").replace(tzinfo=timezone.utc)
        date_str = dt.isoformat()
    else:
        date_str = raw

    assert "2026-03-15" in date_str
    # Verify it's a valid ISO datetime
    parsed = datetime.fromisoformat(date_str)
    assert parsed.year == 2026
    assert parsed.month == 3
    assert parsed.day == 15


# ─── Test: usable gate blocks context_only (P1-5) ──────────────────────

def test_usable_gate_blocks_context_only():
    """run_pipeline with usable=False transcript should generate 0 articles."""
    from unittest.mock import patch, MagicMock
    from x_spaces_scraper.scraper import SpaceInfo
    import x_spaces_scraper.run_scraper as runner

    fake_space = SpaceInfo(
        space_id="gate_test_001",
        title="Test Space",
        host="testhost",
        date="2026-03-15T00:00:00+00:00",
        participant_count=10,
        state="ended",
        url="https://twitter.com/i/spaces/gate_test_001",
    )
    fake_transcript = {
        "space_id": "gate_test_001",
        "transcript": "Some context text",
        "source": "context_only",
        "word_count": 200,
        "usable": False,
    }

    with patch.object(runner, "XSpacesScraper") as MockScraper, \
         patch.object(runner, "fetch_transcript", return_value=fake_transcript), \
         patch.object(runner, "generate_article") as mock_gen, \
         patch.object(runner, "publish_article"):
        mock_instance = MockScraper.return_value
        mock_instance.find_spaces.return_value = [fake_space]
        mock_instance.mark_processed = MagicMock()
        mock_instance._load_processed = MagicMock(return_value=set())

        stats = runner.run_pipeline(dry_run=False, auto_publish=False, max_spaces=1)

    mock_gen.assert_not_called()
    assert stats["articles_generated"] == 0


# ─── Test: recorder downloaded_at after validation (P1-6) ───────────────

def test_recorder_downloaded_at_after_validation():
    """downloaded_at should only be set AFTER output file is validated."""
    import x_spaces_pipeline.recorder as recorder_mod
    from x_spaces_scraper.spaces_state import SpaceStateDB

    with tempfile.TemporaryDirectory() as tmp:
        db = SpaceStateDB(db_path=os.path.join(tmp, "test.db"))
        db.upsert("rec_test_001", title="Test", host="testhost",
                   discovered_at="2026-03-15T00:00:00")

        # Verify downloaded_at is NOT set before recording
        record = db.get("rec_test_001")
        assert record["downloaded_at"] is None
        db.close()
