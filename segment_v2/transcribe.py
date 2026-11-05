#!/usr/bin/env python3
"""Transcribe source videos with faster-whisper large-v3 on GPU (CUDA:0)."""
import json
import os
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

BASE = "/home/ultron/protocol_pulse/segment_v2"
SOURCES_DIR = f"{BASE}/sources"
TRANS_DIR = f"{BASE}/transcripts"
os.makedirs(TRANS_DIR, exist_ok=True)

from faster_whisper import WhisperModel

print("Loading whisper large-v3 on cuda:0...")
t0 = time.time()
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
print(f"Model loaded in {time.time()-t0:.1f}s")

# Get videos from topic.json
with open(f"{BASE}/topic.json") as f:
    topic = json.load(f)

video_ids = [v["video_id"] for v in topic["chosen_topic"]["videos"]]
print(f"Transcribing {len(video_ids)} videos: {video_ids}")

for vid_id in video_ids:
    src = f"{SOURCES_DIR}/{vid_id}.mp4"
    out = f"{TRANS_DIR}/{vid_id}.json"

    if os.path.exists(out):
        print(f"  {vid_id}: already transcribed, skipping")
        continue

    if not os.path.exists(src):
        print(f"  {vid_id}: source not found, skipping")
        continue

    print(f"  Transcribing {vid_id}...", flush=True)
    t1 = time.time()

    segments_raw, info = model.transcribe(
        src,
        beam_size=5,
        word_timestamps=True,
        language="en",
    )

    words = []
    segments = []
    for seg in segments_raw:
        seg_words = []
        for w in seg.words:
            wd = {"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3),
                  "probability": round(w.probability, 3)}
            words.append(wd)
            seg_words.append(wd)
        segments.append({
            "text": seg.text.strip(),
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "words": seg_words,
        })

    elapsed = time.time() - t1
    print(f"    {len(segments)} segments, {len(words)} words in {elapsed:.1f}s")

    with open(out, "w") as f:
        json.dump({"words": words, "segments": segments, "language": info.language,
                   "duration": info.duration}, f, indent=2)

print("\nAll transcriptions complete.")
