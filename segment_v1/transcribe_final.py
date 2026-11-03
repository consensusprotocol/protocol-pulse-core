#!/usr/bin/env python3
"""Transcribe remaining 3 WAVs. 0.7x realtime is the ceiling on this box."""
import json, os, time

AUDIO_DIR = "/home/ultron/protocol_pulse/segment_v1/audio16k"
TRANSCRIPTS_DIR = "/home/ultron/protocol_pulse/segment_v1/transcripts"
REMAINING = ["5ripuS9GDaM", "Eojd18J_wuU", "7QIB_zdKU9A"]

from faster_whisper import WhisperModel
print("Loading large-v3 float16...", flush=True)
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
print("Ready.", flush=True)

for vid_id in REMAINING:
    wav = os.path.join(AUDIO_DIR, f"{vid_id}.wav")
    out = os.path.join(TRANSCRIPTS_DIR, f"{vid_id}.json")
    if not os.path.exists(wav):
        print(f"SKIP {vid_id}: no WAV"); continue
    if os.path.exists(out) and os.path.getsize(out) > 100:
        print(f"SKIP {vid_id}: done"); continue

    print(f"Transcribing {vid_id}...", flush=True)
    t0 = time.time()
    segments_gen, info = model.transcribe(
        wav, word_timestamps=True, language="en", beam_size=1,
        vad_filter=True, condition_on_previous_text=False,
    )
    words, segtexts = [], []
    for seg in segments_gen:
        segtexts.append({"start": round(seg.start,3), "end": round(seg.end,3), "text": seg.text.strip()})
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word.strip(), "start": round(w.start,3),
                              "end": round(w.end,3), "probability": round(w.probability,3)})
    elapsed = time.time() - t0
    factor = info.duration / elapsed if elapsed else 0
    print(f"  {vid_id}: {len(words)}w, {info.duration:.0f}s audio, {elapsed:.0f}s wall, {factor:.1f}x", flush=True)
    with open(out, "w") as f:
        json.dump({"video_id": vid_id, "language": info.language,
                   "language_probability": round(info.language_probability,3),
                   "duration": round(info.duration,2), "segments": segtexts, "words": words}, f, indent=2)

print("All done.", flush=True)
