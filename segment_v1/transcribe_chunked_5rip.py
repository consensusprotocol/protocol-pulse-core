#!/usr/bin/env python3
"""Chunked transcription for 5ripuS9GDaM on GPU1. 300s chunks."""
import json, os, sys, time, subprocess, tempfile
from faster_whisper import WhisperModel

AUD = "/home/ultron/protocol_pulse/segment_v1/audio16k"
OUT = "/home/ultron/protocol_pulse/segment_v1/transcripts"
VID = "5ripuS9GDaM"
CH = 300

wav = f"{AUD}/{VID}.wav"
out = f"{OUT}/{VID}.json"

if os.path.exists(out) and os.path.getsize(out) > 500:
    print(f"SKIP: {out} already exists ({os.path.getsize(out)} bytes)")
    sys.exit(0)

dur = float(subprocess.check_output(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav]
).decode().strip())

print(f"Loading large-v3 float16 on cuda...", flush=True)
m = WhisperModel("large-v3", device="cuda", compute_type="float16")
print(f"Loaded. Transcribing {VID} ({dur:.0f}s) in {CH}s chunks...", flush=True)

t0 = time.time()
words = []
segs = []
off = 0.0

while off < dur:
    tmp = tempfile.mktemp(suffix=".wav")
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-ss", str(off), "-t", str(CH),
        "-i", wav, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp
    ], check=True)
    sg, info = m.transcribe(
        tmp, word_timestamps=True, language="en", beam_size=1,
        vad_filter=True, condition_on_previous_text=False
    )
    for s in sg:
        segs.append({"start": round(s.start + off, 3), "end": round(s.end + off, 3), "text": s.text.strip()})
        for w in (s.words or []):
            words.append({
                "word": w.word.strip(), "start": round(w.start + off, 3),
                "end": round(w.end + off, 3), "probability": round(w.probability, 3)
            })
    os.remove(tmp)
    el = time.time() - t0
    print(f"  chunk@{off:.0f}s done, {len(words)} words, elapsed {el:.0f}s, running {(off+CH)/el:.1f}x", flush=True)
    off += CH

el = time.time() - t0
with open(out, "w") as f:
    json.dump({"video_id": VID, "language": "en", "language_probability": 1.0,
               "duration": round(dur, 2), "segments": segs, "words": words}, f, indent=1)
print(f"DONE {VID}: {len(words)} words, {dur:.0f}s audio in {el:.0f}s = {dur/el:.1f}x", flush=True)
