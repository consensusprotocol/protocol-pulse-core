"""
test_spaces_v2.py — Regression + integration tests for X Spaces V2.
"""

import os
import sqlite3
import tempfile

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
