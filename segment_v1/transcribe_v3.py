#!/usr/bin/env python3
"""Transcribe remaining 3 WAVs. Fresh process, clean GPU, exact options."""
import json, os, time, subprocess

AUDIO_DIR = "/home/ultron/protocol_pulse/segment_v1/audio16k"
TRANSCRIPTS_DIR = "/home/ultron/protocol_pulse/segment_v1/transcripts"

REMAINING = ["5ripuS9GDaM", "Eojd18J_wuU", "7QIB_zdKU9A"]

from faster_whisper import WhisperModel

print("Loading large-v3 float16 on cuda...", flush=True)
t_load = time.time()
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
print(f"Loaded in {time.time()-t_load:.1f}s", flush=True)

for vid_id in REMAINING:
    wav = os.path.join(AUDIO_DIR, f"{vid_id}.wav")
    out = os.path.join(TRANSCRIPTS_DIR, f"{vid_id}.json")
    if not os.path.exists(wav):
        print(f"SKIP {vid_id}: no WAV"); continue
    if os.path.exists(out) and os.path.getsize(out) > 100:
        print(f"SKIP {vid_id}: already done"); continue

    print(f"Transcribing {vid_id}...", flush=True)
    t0 = time.time()

    segments_gen, info = model.transcribe(
        wav,
        word_timestamps=True,
        language="en",
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
    )

    words = []
    segment_texts = []
    checked_gpu = False

    for seg in segments_gen:
        segment_texts.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
        })
        if seg.words:
            for w in seg.words:
                words.append({
                    "word": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "probability": round(w.probability, 3),
                })

        # Gate: check factor after 60s of audio processed
        if not checked_gpu and seg.end >= 60:
            checked_gpu = True
            elapsed = time.time() - t0
            factor = seg.end / elapsed
            print(f"  60s gate: {seg.end:.0f}s audio in {elapsed:.1f}s wall = {factor:.1f}x realtime", flush=True)
            if factor < 5.0:
                print("  FAIL: factor < 5x. Dumping nvidia-smi and stopping.", flush=True)
                r = subprocess.run(
                    ["nvidia-smi", "--query-compute-apps=gpu_bus_id,pid,name,used_memory",
                     "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5)
                print(f"  GPU processes: {r.stdout.strip()}", flush=True)
                r2 = subprocess.run(
                    ["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used",
                     "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5)
                print(f"  GPU state: {r2.stdout.strip()}", flush=True)
                import sys; sys.exit(1)

    elapsed = time.time() - t0
    factor = info.duration / elapsed if elapsed > 0 else 0
    print(f"  DONE {vid_id}: {len(words)} words, {info.duration:.0f}s audio, "
          f"{elapsed:.1f}s wall, {factor:.1f}x realtime", flush=True)

    with open(out, "w") as f:
        json.dump({
            "video_id": vid_id,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(info.duration, 2),
            "segments": segment_texts,
            "words": words,
        }, f, indent=2)
    print(f"  Written {out}", flush=True)

print("\nAll 3 transcriptions complete.", flush=True)
