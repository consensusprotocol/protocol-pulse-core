import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
import anthropic as anthropic_sdk

from config import settings
from schemas import (
    InterruptRequest, InterruptResponse,
    OracleAskRequest, OracleAskResponse,
)
from elevenlabs_client import ElevenLabsClient
from viseme import build_viseme_timeline

ACTIVE_INTERRUPTS: dict[str, str] = {}

ORACLE_SYSTEM = """You are the Protocol Pulse Oracle — a Bitcoin intelligence avatar on the Protocol Pulse platform. 
You deliver sharp, authoritative, concise answers about Bitcoin, mining, macro economics, on-chain data, and sovereignty.
Keep responses to 2-4 sentences max — you are speaking aloud, not writing an essay.
Be direct. No filler. Sound like you are live on air.
Never say "As an AI" or "I cannot". Just answer with conviction."""

def generate_answer(question: str) -> str:
    """Call Claude claude-sonnet-4-6 for Oracle responses."""
    client = anthropic_sdk.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=ORACLE_SYSTEM,
        messages=[{"role": "user", "content": question}]
    )
    return msg.content[0].text.strip()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.eleven = ElevenLabsClient()
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
        "port": settings.oracle_port,
    }

@app.post("/oracle/interrupt", response_model=InterruptResponse)
async def oracle_interrupt(req: InterruptRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())
    interrupt_id = req.interrupt_id or str(uuid.uuid4())
    ACTIVE_INTERRUPTS[conversation_id] = interrupt_id
    return InterruptResponse(ok=True, conversation_id=conversation_id, interrupt_id=interrupt_id)

@app.post("/oracle/ask", response_model=OracleAskResponse)
async def oracle_ask(req: OracleAskRequest):
    if not settings.elevenlabs_api_key:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured")
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    conversation_id = req.conversation_id or str(uuid.uuid4())
    interrupt_id = req.interrupt_id or ACTIVE_INTERRUPTS.get(conversation_id) or str(uuid.uuid4())
    ACTIVE_INTERRUPTS[conversation_id] = interrupt_id
    ask_started = time.perf_counter()

    # Step 1: Claude generates answer
    try:
        answer_text = generate_answer(req.question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    if ACTIVE_INTERRUPTS.get(conversation_id) != interrupt_id:
        raise HTTPException(status_code=409, detail="Interrupted")

    # Step 2: ElevenLabs TTS + timestamps
    try:
        tts_data, tts_elapsed = await app.state.eleven.text_to_speech_with_timestamps(
            text=answer_text, voice_id=req.voice_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ElevenLabs call failed: {exc}") from exc

    audio_b64 = tts_data.get("audio_base64", "")
    alignment = tts_data.get("alignment", {}) or {}
    duration = app.state.eleven.estimate_duration_from_alignment(alignment)

    if ACTIVE_INTERRUPTS.get(conversation_id) != interrupt_id:
        raise HTTPException(status_code=409, detail="Interrupted")

    # Step 3: Viseme timeline
    timeline = build_viseme_timeline(answer_text, alignment)
    total_elapsed = time.perf_counter() - ask_started

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.oracle_bind, port=settings.oracle_port,
                reload=False, log_level=settings.log_level)

# ── Static file serving (added for browser UI) ──────────────────────────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os as _os

_FRONTEND_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "frontend")

@app.api_route("/", methods=["GET","HEAD"])
async def serve_ui(request):
    from fastapi.responses import Response
    idx = _os.path.join(_FRONTEND_DIR, "index.html")
    if request.method == "HEAD":
        return Response(headers={"content-type":"text/html","cache-control":"no-store"})
    return FileResponse(idx, headers={"cache-control":"no-store"})

@app.get("/js/{filename}")
async def serve_js(filename: str):
    fp = _os.path.join(_FRONTEND_DIR, filename)
    if _os.path.exists(fp):
        return FileResponse(fp, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Not found")

