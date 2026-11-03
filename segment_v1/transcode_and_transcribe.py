#!/usr/bin/env python3
"""Stage 1c-d: Transcode to PCM MOV and transcribe with faster-whisper."""
import json
import subprocess
import os
import sys
import glob

SOURCES_DIR = "/home/ultron/protocol_pulse/segment_v1/sources"
PCM_DIR = "/home/ultron/protocol_pulse/segment_v1/sources_pcm"
TRANSCRIPTS_DIR = "/home/ultron/protocol_pulse/segment_v1/transcripts"

os.makedirs(PCM_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

# Get list of downloaded videos
video_ids = ["bSmFGoAKPBc", "5ripuS9GDaM", "Eojd18J_wuU", "7QIB_zdKU9A"]

# Step 1: Transcode to PCM audio MOV
print("=== STAGE 1c: Transcode to PCM MOV ===")
for vid_id in video_ids:
    src = os.path.join(SOURCES_DIR, f"{vid_id}.mp4")
    dst = os.path.join(PCM_DIR, f"{vid_id}.mov")
    if not os.path.exists(src):
        # Try webm
        src = os.path.join(SOURCES_DIR, f"{vid_id}.webm")
    if not os.path.exists(src):
        # Try mkv
        src = os.path.join(SOURCES_DIR, f"{vid_id}.mkv")
    if not os.path.exists(src):
        print(f"  SKIP {vid_id}: source not found")
        continue
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        print(f"  SKIP {vid_id}: PCM already exists ({os.path.getsize(dst)} bytes)")
        continue

    print(f"  Transcoding {vid_id}...", end=" ", flush=True)
    # Try video stream copy + PCM audio first
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", src,
            "-c:v", "copy", "-c:a", "pcm_s16le",
            "-ar", "48000", "-ac", "2",
            dst,
        ],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        # Container refused stream copy; re-encode video with h264_nvenc
        print("stream copy failed, re-encoding with nvenc...", end=" ", flush=True)
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", src,
                "-c:v", "h264_nvenc", "-preset", "p4", "-crf", "17",
                "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                dst,
            ],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            print(f"FAILED: {result.stderr[-200:]}")
            continue
    size_mb = os.path.getsize(dst) / (1024 * 1024)
    print(f"OK ({size_mb:.1f} MB)")

# Step 2: Transcribe with faster-whisper
print("\n=== STAGE 1d: Transcribe with faster-whisper ===")
from faster_whisper import WhisperModel

print("Loading whisper model large-v3 on GPU...", flush=True)
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
print("Model loaded.")

for vid_id in video_ids:
    pcm_path = os.path.join(PCM_DIR, f"{vid_id}.mov")
    transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{vid_id}.json")

    if not os.path.exists(pcm_path):
        print(f"  SKIP {vid_id}: no PCM file")
        continue
    if os.path.exists(transcript_path):
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
            "start": seg.start,
            "end": seg.end,
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

print("\nDone. Transcripts in", TRANSCRIPTS_DIR)
