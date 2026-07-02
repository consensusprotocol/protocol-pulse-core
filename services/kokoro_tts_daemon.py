#!/usr/bin/env python3
"""kokoro_tts_daemon — dedicated Kokoro af_heart TTS microservice (Fable5).

Why: Kokoro inside avatar_server takes 20-32s per call (in-process pathology);
the identical call in a standalone process takes 0.31s (43x realtime, benched
2026-07-02). This daemon IS that standalone process, kept warm on GPU1.

API: POST /tts  {"text": "..."}  ->  16kHz mono WAV bytes (loudnorm applied)
     GET  /health                ->  {"status":"ok","device":...,"last_synth_sec":...}
Port: 8250 (localhost only). Env: CUDA_VISIBLE_DEVICES=1.
"""
import io
import json
import logging
import os
import subprocess
import tempfile
import time

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # voices/model are cached locally

import numpy as np
import soundfile as sf
import torch
from flask import Flask, Response, jsonify, request

logging.basicConfig(level=logging.INFO,
                    format="[tts_daemon] %(asctime)s %(message)s")
log = logging.getLogger("tts_daemon")

app = Flask(__name__)
_PIPE = None
_LAST = {"sec": None, "chars": None}


def _init():
    global _PIPE
    from kokoro import KPipeline
    _PIPE = KPipeline(lang_code="a")
    try:
        _PIPE.model = _PIPE.model.to("cuda:0")
    except Exception as e:
        log.warning("GPU move failed, CPU mode: %s", e)
    # warm-up: absorbs any first-call overhead so requests are always hot
    for _ in _PIPE("warm up the pipeline now", voice="af_heart"):
        pass
    dev = "?"
    try:
        dev = str(next(_PIPE.model.parameters()).device)
    except Exception:
        pass
    log.info("Kokoro af_heart ready on %s", dev)


@app.route("/health")
def health():
    dev = "?"
    try:
        dev = str(next(_PIPE.model.parameters()).device)
    except Exception:
        pass
    return jsonify({"status": "ok", "device": dev,
                    "last_synth_sec": _LAST["sec"], "last_chars": _LAST["chars"]})


@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    t0 = time.time()
    chunks = []
    for _gs, _ps, audio in _PIPE(text, voice="af_heart"):
        chunks.append(audio)
    if not chunks:
        return jsonify({"error": "no audio"}), 500
    full = np.concatenate(chunks)
    synth = time.time() - t0
    _LAST.update({"sec": round(synth, 2), "chars": len(text)})

    # 24k float -> 16kHz mono WAV + loudnorm via single ffmpeg pass
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, full, 24000)
        p24 = tmp.name
    p16 = p24 + ".16k.wav"
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", p24,
         "-af", "aresample=16000,loudnorm=I=-14:TP=-1.5:LRA=11",
         "-ac", "1", "-f", "wav", p16],
        capture_output=True, timeout=30)
    try:
        os.unlink(p24)
    except OSError:
        pass
    if r.returncode != 0 or not os.path.exists(p16):
        return jsonify({"error": "resample failed"}), 500
    wav = open(p16, "rb").read()
    try:
        os.unlink(p16)
    except OSError:
        pass
    log.info("synth %.2fs for %d chars -> %d bytes", synth, len(text), len(wav))
    return Response(wav, mimetype="audio/wav",
                    headers={"X-Synth-Sec": f"{synth:.2f}"})


if __name__ == "__main__":
    _init()
    from waitress import serve
    serve(app, host="127.0.0.1", port=8250, threads=2)
