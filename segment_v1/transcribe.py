#!/usr/bin/env python3
"""Stage 1d: Transcribe with faster-whisper large-v3 on GPU."""
import json
import os

PCM_DIR = "/home/ultron/protocol_pulse/segment_v1/sources_pcm"
TRANSCRIPTS_DIR = "/home/ultron/protocol_pulse/segment_v1/transcripts"
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

video_ids = ["bSmFGoAKPBc", "5ripuS9GDaM", "Eojd18J_wuU", "7QIB_zdKU9A"]

from faster_whisper import WhisperModel
print("Loading whisper model large-v3 on GPU...", flush=True)
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
print("Model loaded.")

for vid_id in video_ids:
    pcm_path = os.path.join(PCM_DIR, f"{vid_id}.mkv")
    transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{vid_id}.json")

    if not os.path.exists(pcm_path):
        print(f"  SKIP {vid_id}: no PCM file")
        continue
    if os.path.exists(transcript_path) and os.path.getsize(transcript_path) > 100:
        print(f"  SKIP {vid_id}: transcript already exists")
        continue

    print(f"  Transcribing {vid_id}...", end=" ", flush=True)
    segments, info = model.transcribe(
        pcm_path,
        word_timestamps=True,
        language="en",
        beam_size=5,
        vad_filter=True,
    )

    words = []
    segment_texts = []
    for seg in segments:
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
    print(f"OK ({len(words)} words, {info.duration:.0f}s)")

print("\nDone.")
