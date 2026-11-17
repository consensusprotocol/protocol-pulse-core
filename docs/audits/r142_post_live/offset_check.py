#!/usr/bin/env python3
"""Ruling 142 (3): is a post_live stream's FULL download usable, on the transcript's clock? (a) its sha256 against the
ingest's media_sha256; (b) the render's own decoder (select_passages._whisper_transcribe) on a window cut from it,
aligned word by word to the word pass's record of that window (source-clock word times): the offset (median) and its
spread. Free: local GPU0 under the lease, released at the end; this process exits after."""
import hashlib
import json
import os
import statistics
import subprocess
import sys
from difflib import SequenceMatcher

REPO = "/home/ultron/protocol_pulse"
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import gpu0  # noqa: E402
import select_passages  # noqa: E402

media, lo, hi, record, out_dir = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5]
VID = "MeC8YEmUx_w"
os.makedirs(out_dir, exist_ok=True)
h = hashlib.sha256()
with open(media, "rb") as f:
    for b in iter(lambda: f.read(1 << 20), b""):
        h.update(b)
meta = json.load(open(os.path.join(REPO, "data", "editorial", "transcripts", VID, "transcript.whisper.json")))
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1",
                            media], capture_output=True, text=True).stdout.strip() or 0)
print(f"media: {os.path.getsize(media)} bytes, {dur:.2f} s | sha256 {h.hexdigest()[:16]} | the ingest's "
      f"{str(meta.get('media_sha256'))[:16]} ({meta.get('media_bytes')} bytes) | identical: "
      f"{h.hexdigest() == meta.get('media_sha256')}", flush=True)

wav = os.path.join(out_dir, "window.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", media, "-ss", f"{lo:.3f}", "-to", f"{hi:.3f}", "-ac", "1", "-ar",
                "16000", wav], check=True, timeout=300)
with gpu0.lease("integrator ruling 142 (3) post_live offset check (free, local)", wait_s=300):
    try:
        got = select_passages._whisper_transcribe(wav, VID + "_r142", out_dir)
    finally:
        gpu0.release_all()
mine = [(str(w["word"]).strip().lower().strip(".,?!\"'"), float(w["start"]) + lo) for w in got.get("words") or []]
rec = [(str(w["word"]).strip().lower().strip(".,?!\"'"), float(w["start"]))
       for w in json.load(open(record)).get("words") or []]
sm = SequenceMatcher(None, [m[0] for m in mine], [r[0] for r in rec], autojunk=False)
deltas = [mine[a + k][1] - rec[b + k][1] for op, a, a2, b, b2 in sm.get_opcodes() if op == "equal" for k in range(a2 - a)]
med = statistics.median(deltas) if deltas else None
q = statistics.quantiles(deltas, n=4) if len(deltas) >= 4 else None
print(f"decoder words {len(mine)}, record words {len(rec)}, aligned {len(deltas)} "
      f"({len(deltas) / max(1, len(rec)):.0%} of the record)", flush=True)
if med is not None:
    print(f"OFFSET (this file's clock minus the transcript's): median {med * 1000:+.0f} ms, IQR "
          f"{(q[0] * 1000 if q else 0):+.0f}..{(q[2] * 1000 if q else 0):+.0f} ms", flush=True)
json.dump({"media_sha256": h.hexdigest(), "ingest_media_sha256": meta.get("media_sha256"), "duration_s": dur,
           "window": [lo, hi], "aligned": len(deltas), "record_words": len(rec), "median_offset_s": med,
           "quartiles_s": q}, open(os.path.join(out_dir, "offset_check.json"), "w"), indent=1)
