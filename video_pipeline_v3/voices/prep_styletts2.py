#!/usr/bin/env python3
"""
StyleTTS2 Dataset Prep
Reuses segments_v2/ WAVs + re-transcribes with Whisper.
Outputs LJSpeech-format metadata: filename|normalized_text|normalized_text
"""
import os, csv, subprocess, re, shutil
from pathlib import Path
from faster_whisper import WhisperModel

VOICES_DIR = Path(__file__).parent
SEGMENTS_DIR = VOICES_DIR / "segments_v2"
STYLETTS2_DIR = VOICES_DIR / "styletts2"
WAVS_DIR = STYLETTS2_DIR / "wavs"
METADATA_PATH = STYLETTS2_DIR / "metadata.csv"

MIN_CHARS = 15
MAX_CHARS = 220


def normalize_text(text):
    """Normalize for StyleTTS2 training alignment."""
    replacements = {
        "BTC": "Bitcoin", "ETH": "Ethereum",
        "UTXO": "U T X O", "ATH": "all time high",
        "ETF": "E T F", "FUD": "F U D",
        "DeFi": "dee fie", "BTCPay": "Bitcoin Pay",
    }
    for k, v in replacements.items():
        text = re.sub(rf'\b{re.escape(k)}\b', v, text)
    text = re.sub(r'\$(\d+(?:\.\d+)?)k\b',
                  lambda m: f"{float(m.group(1)):.0f} thousand dollars", text)
    text = re.sub(r'\$(\d+(?:\.\d+)?)\s*[Mm]illion',
                  lambda m: f"{m.group(1)} million dollars", text)
    text = re.sub(r'\$(\d+(?:\.\d+)?)\s*[Bb]illion',
                  lambda m: f"{m.group(1)} billion dollars", text)
    text = re.sub(r'(\d+(?:\.\d+)?)%', r'\1 percent', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


if __name__ == "__main__":
    STYLETTS2_DIR.mkdir(exist_ok=True)
    WAVS_DIR.mkdir(exist_ok=True)

    segs = sorted(SEGMENTS_DIR.glob("raw_*.wav"))
    print(f"Found {len(segs)} segments in segments_v2/")

    print("Loading Whisper large-v3...")
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")

    entries = []
    for i, seg in enumerate(segs):
        if i % 30 == 0:
            print(f"  {i}/{len(segs)}...")
        dur = get_duration(str(seg))
        if not (1.5 <= dur <= 15.0):
            continue
        try:
            segs_out, _ = model.transcribe(
                str(seg), language="en", beam_size=5,
                condition_on_previous_text=False)
            text = " ".join(s.text.strip() for s in segs_out).strip()
        except Exception as e:
            print(f"  Whisper error {seg.name}: {e}")
            continue

        if not (MIN_CHARS <= len(text) <= MAX_CHARS):
            continue
        alpha = sum(c.isalpha() for c in text) / max(len(text), 1)
        if alpha < 0.5:
            continue

        normalized = normalize_text(text)

        wav_name = f"pbx_{i:04d}.wav"
        dest = WAVS_DIR / wav_name
        shutil.copy2(str(seg), str(dest))

        entries.append((wav_name.replace(".wav", ""), text, normalized))

    with open(METADATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="|")
        for entry in entries:
            writer.writerow(entry)

    print(f"\nStyleTTS2 dataset ready: {len(entries)} entries")
    print(f"   WAVs: {WAVS_DIR}")
    print(f"   Metadata: {METADATA_PATH}")
    for e in entries[:3]:
        print(f"   {e[0]}: {e[2][:60]}")
