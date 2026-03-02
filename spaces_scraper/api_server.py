"""
api_server.py — FastAPI REST API on port 8210
Exposes real-time data from the Spaces scraper pipeline.

Endpoints:
  GET  /                          Health + status
  GET  /spaces/active             Currently monitored live spaces
  GET  /spaces/feed               Latest transcript chunks with sentiment
  GET  /spaces/sentiment          Rolling aggregate sentiment
  GET  /spaces/{id}/transcript    Full rolling transcript for a specific space
  GET  /spaces/{id}/sentiment     Per-space sentiment detail
  POST /spaces/force-scan         Trigger an immediate detection scan
"""

import logging
import time
from typing import Optional, TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config

if TYPE_CHECKING:
    from detector import SpaceDetector
    from transcriber import RealtimeTranscriber
    from analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Protocol Pulse — Spaces Scraper",
    description="Real-time Bitcoin X Spaces intelligence: transcripts, sentiment, topics.",
    version="1.0.0",
)

# CORS — allow Protocol Pulse frontend to consume this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─── State (injected by main.py) ─────────────────────────────────────────────
# These are set by main.py after startup so the API can access live data.
_detector: Optional["SpaceDetector"] = None
_transcriber: Optional["RealtimeTranscriber"] = None
_analyzer: Optional["SentimentAnalyzer"] = None
_started_at: float = time.time()


def inject_state(detector, transcriber, analyzer):
    global _detector, _transcriber, _analyzer
    _detector = detector
    _transcriber = transcriber
    _analyzer = analyzer


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    uptime = int(time.time() - _started_at)
    active_count = len(_detector.active_spaces) if _detector else 0
    transcribed = _transcriber.get_stats()["segments_processed"] if _transcriber else 0
    return {
        "service": "spaces-scraper",
        "status": "running",
        "uptime_seconds": uptime,
        "active_spaces": active_count,
        "segments_transcribed": transcribed,
        "api_version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {"ok": True, "ts": time.time()}


@app.get("/spaces/active")
async def active_spaces():
    """List all currently monitored live spaces."""
    if not _detector:
        return {"spaces": [], "note": "detector not initialized"}

    spaces = _detector.active_spaces
    return {
        "spaces": [
            {
                "id": s.space_id,
                "host": f"@{s.host_username}",
                "title": s.title or "(untitled)",
                "participants": s.participant_count,
                "started_at": s.started_at,
                "url": s.url,
                "has_hls": bool(s.hls_url),
                "is_transcribing": (
                    _transcriber is not None
                    and s.space_id in _transcriber.get_all_transcripts()
                ),
                "detected_via": s.detected_via,
                "detected_at": s.detected_at,
            }
            for s in spaces
        ],
        "count": len(spaces),
        "updated_at": time.time(),
    }


@app.get("/spaces/feed")
async def transcript_feed(limit: int = 50):
    """
    Latest transcript chunks across all active spaces, newest first.
    Optionally filtered by space_id query param.
    """
    if not _transcriber:
        return {"chunks": [], "note": "transcriber not initialized"}

    all_chunks = []
    for space_id, rolling in _transcriber.get_all_transcripts().items():
        for chunk in rolling.get_all():
            all_chunks.append({
                "space_id": space_id,
                "text": chunk.text,
                "timestamp": chunk.timestamp,
                "confidence": chunk.confidence,
                "latency_ms": chunk.transcription_latency_ms,
            })

    # Sort newest first
    all_chunks.sort(key=lambda c: c["timestamp"], reverse=True)

    return {
        "chunks": all_chunks[:limit],
        "total": len(all_chunks),
        "updated_at": time.time(),
    }


@app.get("/spaces/sentiment")
async def rolling_sentiment():
    """Aggregate sentiment across all active spaces."""
    if not _analyzer:
        return {
            "overall_score": 50,
            "label": "NEUTRAL",
            "active_spaces_count": 0,
            "topics": [],
            "note": "analyzer not initialized",
            "updated_at": time.time(),
        }

    agg = _analyzer.get_aggregate_sentiment()
    agg["sample_window_minutes"] = config.TRANSCRIPT_WINDOW_MINUTES
    return agg


@app.get("/spaces/{space_id}/transcript")
async def space_transcript(space_id: str, minutes: float = 10.0):
    """Full rolling transcript for a specific space."""
    if not _transcriber:
        raise HTTPException(status_code=503, detail="transcriber not initialized")

    rolling = _transcriber.get_transcript(space_id)
    if not rolling:
        raise HTTPException(status_code=404, detail=f"Space {space_id} not found")

    chunks = rolling.get_recent(minutes=minutes)
    return {
        "space_id": space_id,
        "text": rolling.get_text(minutes=minutes),
        "chunks": [
            {
                "text": c.text,
                "timestamp": c.timestamp,
                "confidence": c.confidence,
            }
            for c in chunks
        ],
        "chunk_count": len(chunks),
        "window_minutes": minutes,
    }


@app.get("/spaces/{space_id}/sentiment")
async def space_sentiment(space_id: str):
    """Detailed sentiment for a specific space."""
    if not _analyzer:
        raise HTTPException(status_code=503, detail="analyzer not initialized")

    result = _analyzer.get_latest(space_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"No sentiment data for space {space_id}")

    return result.to_dict()


@app.post("/spaces/force-scan")
async def force_scan():
    """Trigger an immediate detection scan (bypasses poll interval)."""
    if not _detector:
        raise HTTPException(status_code=503, detail="detector not initialized")

    import asyncio
    spaces = await _detector.detect_once()
    return {
        "found": len(spaces),
        "spaces": [{"id": s.space_id, "host": s.host_username} for s in spaces],
    }


@app.get("/stats")
async def stats():
    """Internal stats for monitoring."""
    transcriber_stats = _transcriber.get_stats() if _transcriber else {}
    return {
        "transcriber": transcriber_stats,
        "uptime_seconds": int(time.time() - _started_at),
        "active_spaces": len(_detector.active_spaces) if _detector else 0,
        "sentiment_results": (
            len(_analyzer._latest) if _analyzer else 0
        ),
    }
