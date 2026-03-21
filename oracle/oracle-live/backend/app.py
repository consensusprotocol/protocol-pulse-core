import time
import uuid
import logging
import os
import yaml
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
import httpx

from config import settings
from schemas import (
    InterruptRequest, InterruptResponse,
    OracleAskRequest, OracleAskResponse,
)
from elevenlabs_client import ElevenLabsClient
from viseme import build_viseme_timeline

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("oracle-live")

ACTIVE_INTERRUPTS: dict[str, str] = {}

def load_config():
    cfg_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            return yaml.safe_load(f)
    return {}

def generate_answer_via_claude(question: str, cfg: dict) -> str:
    """Call Claude API for oracle answers — mirrors existing oracle briefing logic."""
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY") or cfg.get("claude", {}).get("api_key", "")
    if not api_key:
        return f"Bitcoin Oracle responding: {question.strip()}. Hashrate is strong, fundamentals remain intact."
    
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=(
            "You are the Protocol Pulse Oracle — a Bitcoin intelligence avatar. "
            "Answer questions about Bitcoin, mining, markets, and macro in 2-4 concise sentences. "
            "Speak with authority. No disclaimers. Bitcoin-native vocabulary. No markdown."
        ),
        messages=[{"role": "user", "content": question}]
    )
    return msg.content[0].text

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.eleven = ElevenLabsClient()
    app.state.cfg = load_config()
    log.info("Oracle Live Avatar API started")
    yield

app = FastAPI(
    title="Protocol Pulse Oracle Live Avatar API",
    version="2.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "oracle-live-avatar",
        "version": "2.0.0",
        "voice_id": settings.elevenlabs_voice_id,
        "model_id": settings.elevenlabs_model_id,
        "features": ["viseme_timeline", "interruption", "state_machine", "bitcoin_lexicon"],
    }

@app.post("/oracle/interrupt", response_model=InterruptResponse)
async def oracle_interrupt(req: InterruptRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())
    interrupt_id = req.interrupt_id or str(uuid.uuid4())
    ACTIVE_INTERRUPTS[conversation_id] = interrupt_id
    log.info(f"Interrupt registered: conv={conversation_id} int={interrupt_id[:8]}")
    return InterruptResponse(ok=True, conversation_id=conversation_id, interrupt_id=interrupt_id)

@app.post("/oracle/ask", response_model=OracleAskResponse)
async def oracle_ask(req: OracleAskRequest):
    if not settings.elevenlabs_api_key:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured")

    conversation_id = req.conversation_id or str(uuid.uuid4())
    interrupt_id = req.interrupt_id or ACTIVE_INTERRUPTS.get(conversation_id) or str(uuid.uuid4())
    ACTIVE_INTERRUPTS[conversation_id] = interrupt_id

    ask_started = time.perf_counter()
    log.info(f"Oracle ask: conv={conversation_id[:8]} q={req.question[:60]}")

    # Step 1: Generate answer via Claude
    try:
        answer_text = generate_answer_via_claude(req.question, app.state.cfg)
    except Exception as e:
        log.error(f"Claude answer failed: {e}")
        answer_text = f"The Oracle is processing your question about {req.question[:50]}."

    # Check for interrupt after LLM call
    if ACTIVE_INTERRUPTS.get(conversation_id) != interrupt_id:
        log.info(f"Interrupted after LLM: {conversation_id[:8]}")
        raise HTTPException(status_code=409, detail="Interrupted")

    # Step 2: TTS + timestamps
    try:
        tts_data, tts_elapsed = await app.state.eleven.text_to_speech_with_timestamps(
            text=answer_text,
            voice_id=req.voice_id,
        )
    except Exception as exc:
        log.error(f"ElevenLabs call failed: {exc}")
        raise HTTPException(status_code=502, detail=f"ElevenLabs call failed: {exc}") from exc

    audio_b64 = tts_data.get("audio_base64", "")
    alignment = tts_data.get("alignment", {}) or {}
    duration = ElevenLabsClient.estimate_duration_from_alignment(alignment)

    if ACTIVE_INTERRUPTS.get(conversation_id) != interrupt_id:
        raise HTTPException(status_code=409, detail="Interrupted")

    # Step 3: Build viseme timeline
    timeline = build_viseme_timeline(answer_text, alignment)

    total_elapsed = time.perf_counter() - ask_started
    log.info(f"Oracle done: {total_elapsed:.2f}s | {len(timeline)} visemes | audio {duration:.2f}s")

    return OracleAskResponse(
        answer_text=answer_text,
        audio_base64=audio_b64,
        content_type="audio/mpeg",
        duration=round(duration, 3),
        generation_time=round(total_elapsed, 3),
        viseme_timeline=timeline,
        mode="viseme",
        conversation_id=conversation_id,
        interrupt_id=interrupt_id,
    )

@app.get("/benchmark")
async def benchmark():
    """Quick self-test to measure pipeline latency."""
    t0 = time.perf_counter()
    test_text = "Bitcoin hashrate just hit a new all-time high. Miners are fully committed."
    try:
        tts_data, tts_t = await app.state.eleven.text_to_speech_with_timestamps(test_text)
        alignment = tts_data.get("alignment", {}) or {}
        timeline = build_viseme_timeline(test_text, alignment)
        total_t = time.perf_counter() - t0
        return {
            "ok": True,
            "tts_sec": round(tts_t, 3),
            "viseme_count": len(timeline),
            "total_sec": round(total_t, 3),
            "audio_duration": ElevenLabsClient.estimate_duration_from_alignment(alignment),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "total_sec": round(time.perf_counter() - t0, 3)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.oracle_bind,
        port=settings.oracle_port,
        reload=False,
        log_level=settings.log_level,
    )
