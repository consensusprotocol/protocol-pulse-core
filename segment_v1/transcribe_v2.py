#!/usr/bin/env python3
"""Stage 1d v2: Transcribe WAV files with faster-whisper on GPU."""
import json
import os
import time
import subprocess

AUDIO_DIR = "/home/ultron/protocol_pulse/segment_v1/audio16k"
TRANSCRIPTS_DIR = "/home/ultron/protocol_pulse/segment_v1/transcripts"
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

video_ids = ["bSmFGoAKPBc", "5ripuS9GDaM", "Eojd18J_wuU", "7QIB_zdKU9A"]

import faster_whisper
import ctranslate2
print(f"faster_whisper={faster_whisper.__version__}, ctranslate2={ctranslate2.__version__}")

from faster_whisper import WhisperModel
print("Loading whisper model large-v3 on GPU (float16)...", flush=True)
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
print("Model loaded.", flush=True)

# Verify GPU util on first file
first = True
for vid_id in video_ids:
    wav_path = os.path.join(AUDIO_DIR, f"{vid_id}.wav")
    transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{vid_id}.json")

    if not os.path.exists(wav_path):
        print(f"  SKIP {vid_id}: no WAV file")
        continue
    if os.path.exists(transcript_path) and os.path.getsize(transcript_path) > 100:
        print(f"  SKIP {vid_id}: transcript already exists")
        continue

    print(f"  Transcribing {vid_id}...", flush=True)
    t0 = time.time()

    segments_gen, info = model.transcribe(
        wav_path,
        word_timestamps=True,
        language="en",
        beam_size=1,
        vad_filter=True,
    )

    words = []
    segment_texts = []
    last_report = t0

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

        now = time.time()
        if now - last_report >= 15:
            elapsed = now - t0
            audio_pos = seg.end
            rtf = audio_pos / elapsed if elapsed > 0 else 0
            print(f"    {audio_pos:.0f}s / {info.duration:.0f}s  ({elapsed:.0f}s elapsed, {rtf:.1f}x realtime)", flush=True)
            last_report = now

        # Check GPU util after first 5 seconds of transcription
        if first and time.time() - t0 > 5:
            first = False
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5,
                )
                utils = [int(x.strip()) for x in r.stdout.strip().split("\n") if x.strip()]
                max_util = max(utils) if utils else 0
                print(f"    GPU util check: {utils} (max={max_util}%)", flush=True)
                if max_util < 50:
                    print(f"    WARNING: GPU util < 50%. Printing diagnostics...")
                    print(f"    faster_whisper={faster_whisper.__version__}")
                    print(f"    ctranslate2={ctranslate2.__version__}")
                    r2 = subprocess.run(["python3", "-c", "import ctranslate2; print(ctranslate2.get_cuda_device_count())"],
                                       capture_output=True, text=True, timeout=5)
                    print(f"    CUDA devices: {r2.stdout.strip()}")
            except Exception as e:
                print(f"    GPU check error: {e}")

    elapsed = time.time() - t0
    rtf = info.duration / elapsed if elapsed > 0 else 0
    print(f"  DONE {vid_id}: {len(words)} words, {info.duration:.0f}s audio in {elapsed:.0f}s ({rtf:.1f}x realtime)", flush=True)

    transcript = {
        "video_id": vid_id,
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 2),
        "segments": segment_texts,
        "words": words,
    }

    with open(transcript_path, "w") as f:
        json.dump(transcript, f, indent=2)

print("\nAll transcriptions complete.")
