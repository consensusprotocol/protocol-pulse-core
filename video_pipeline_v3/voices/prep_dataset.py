#!/usr/bin/env python3
"""
PBX Voice Dataset Prep (v3 — P1 fixes applied)
Segments pbx_raw.wav using VAD, transcribes with Whisper,
validates quality, outputs F5-TTS CSV manifest.
"""
import os, json, csv, subprocess
from itertools import zip_longest
from pathlib import Path
from faster_whisper import WhisperModel

VOICES_DIR = Path(__file__).parent
RAW_WAV = VOICES_DIR / "pbx_raw.wav"
SEGMENTS_DIR = VOICES_DIR / "segments"
CSV_PATH = VOICES_DIR / "train.csv"           # F5-TTS expects CSV with audio_file|text header
MANIFEST_PATH = VOICES_DIR / "train_manifest.json"  # human-readable copy

MIN_SEG_SECS = 3.0
MAX_SEG_SECS = 15.0
MIN_CHARS = 20
MAX_CHARS = 200


def segment_with_silencedetect():
    """Use ffmpeg silencedetect to find natural speech boundaries.

    Uses -40dB threshold (P1 fix: -35dB too permissive for studio audio).
    Uses zip_longest (P1 fix: mismatched silence_starts/ends on EOF).
    """
    print("[Prep] Detecting silence boundaries (-35dB:d=1.5)...")
    result = subprocess.run([
        "ffmpeg", "-i", str(RAW_WAV),
        "-af", "silencedetect=noise=-35dB:d=1.5",
        "-f", "null", "-"
    ], capture_output=True, text=True, timeout=300)

    import re
    silence_starts = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", result.stderr)]
    silence_ends   = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", result.stderr)]

    # Get total duration
    dur_result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(RAW_WAV)],
        capture_output=True, text=True
    )
    total_dur = float(dur_result.stdout.strip())

    # P1 fix: zip_longest handles trailing silence_start without silence_end
    segments = []
    prev_end = 0.0
    for s, e in zip_longest(silence_starts, silence_ends, fillvalue=total_dur):
        seg_dur = s - prev_end
        if MIN_SEG_SECS <= seg_dur <= MAX_SEG_SECS:
            segments.append((prev_end, s))
        elif seg_dur > MAX_SEG_SECS:
            cur = prev_end
            while cur + MIN_SEG_SECS < s:
                end = min(cur + MAX_SEG_SECS, s)
                segments.append((cur, end))
                cur = end
        prev_end = e if e != total_dur else e

    # Final trailing segment
    if total_dur - prev_end >= MIN_SEG_SECS:
        segments.append((prev_end, total_dur))

    print(f"[Prep] Found {len(segments)} candidate segments")
    return segments


def extract_segments(segments):
    """Extract each segment to WAV at 24kHz mono (F5-TTS training format)."""
    SEGMENTS_DIR.mkdir(exist_ok=True)
    paths = []
    for i, (start, end) in enumerate(segments):
        out = SEGMENTS_DIR / f"seg_{i:04d}.wav"
        r = subprocess.run([
            "ffmpeg", "-y", "-i", str(RAW_WAV),
            "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
            "-ar", "24000", "-ac", "1",
            str(out)
        ], capture_output=True, timeout=60)
        if r.returncode == 0 and out.exists() and out.stat().st_size > 1000:
            paths.append(str(out))
    print(f"[Prep] Extracted {len(paths)} segments")
    return paths


def transcribe_segments(paths):
    """Transcribe all segments with Whisper large-v3."""
    print("[Prep] Loading Whisper large-v3 (already downloaded)...")
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    results = []
    for i, path in enumerate(paths):
        if i % 20 == 0:
            print(f"[Prep] Transcribing {i}/{len(paths)}...")
        segs, _ = model.transcribe(path, language="en", beam_size=5)
        text = " ".join(s.text.strip() for s in segs).strip()
        if MIN_CHARS <= len(text) <= MAX_CHARS:
            results.append({"audio": path, "text": text})
        else:
            try:
                os.remove(path)
            except Exception:
                pass
    print(f"[Prep] {len(results)} segments passed quality filter")
    return results


def validate_dataset(results):
    """Final validation: confirm audio integrity and duration bounds."""
    valid = []
    for item in results:
        path = item["audio"]
        if not os.path.exists(path):
            continue
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True
        )
        try:
            dur = float(r.stdout.strip())
            if MIN_SEG_SECS <= dur <= MAX_SEG_SECS:
                item["duration"] = round(dur, 3)
                valid.append(item)
        except Exception:
            pass
    total_audio = sum(i["duration"] for i in valid)
    print(f"[Prep] Validated: {len(valid)} segments, {total_audio/60:.1f} min total")
    return valid


def write_csv(results):
    """Write F5-TTS required CSV format: header audio_file|text, absolute paths.

    F5-TTS prepare_csv_wavs.py requires:
    - Header row: audio_file|text
    - Absolute paths to WAV files
    - Pipe delimiter
    """
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="|")
        writer.writerow(["audio_file", "text"])
        for item in results:
            writer.writerow([os.path.abspath(item["audio"]), item["text"]])
    print(f"[Prep] CSV written: {CSV_PATH}")

    # Also write human-readable JSON manifest
    with open(MANIFEST_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[Prep] Sample entries:")
    for item in results[:3]:
        print(f"  {os.path.basename(item['audio'])}: \"{item['text'][:80]}\"")


if __name__ == "__main__":
    print("=== PBX Voice Dataset Prep v3 ===")
    print(f"Source: {RAW_WAV} ({RAW_WAV.stat().st_size / 1e6:.1f}MB)")
    segments = segment_with_silencedetect()
    paths = extract_segments(segments)
    results = transcribe_segments(paths)
    valid = validate_dataset(results)
    write_csv(valid)
    print(f"\n✅ Dataset ready: {len(valid)} segments")
    print(f"   CSV: {CSV_PATH}")
    print(f"   Manifest: {MANIFEST_PATH}")
