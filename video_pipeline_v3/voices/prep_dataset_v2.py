#!/usr/bin/env python3
"""
PBX Voice Dataset Prep v3 (all audit fixes applied)
Fixes: ordered silencedetect parsing, SHA256 full-file dedup, energy filter
enforced, reference clip excluded, transcript normalization, audio normalization,
condition_on_previous_text=False, synthetic/real mix cap (40% max synthetic).
"""
import os, json, csv, subprocess, hashlib, re
from pathlib import Path
from faster_whisper import WhisperModel

VOICES_DIR = Path(__file__).parent
RAW_WAV = VOICES_DIR / "pbx_raw.wav"
REF_CLIP = VOICES_DIR / "pbx_reference.wav"     # MUST be excluded from training
SEGMENTS_DIR = VOICES_DIR / "segments_v2"
ELABS_DIR = VOICES_DIR / "segments_elabs"
CSV_PATH = VOICES_DIR / "train_v2.csv"
MANIFEST_PATH = VOICES_DIR / "train_manifest_v2.json"
VALIDATION_PATH = VOICES_DIR / "validation_manifest.json"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

MIN_SEG_SECS = 2.0
MAX_SEG_SECS = 15.0
MIN_CHARS = 15
MAX_CHARS = 220
MIN_RMS_DB = -45.0          # reject near-silent lines
MAX_SYNTHETIC_RATIO = 0.40  # cap ElevenLabs at 40% of final dataset
VALIDATION_SIZE = 20        # held-out real PBX clips, never in training


def get_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def get_rms_db(path):
    """Get mean volume in dBFS via ffmpeg volumedetect."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stderr.split("\n"):
            if "mean_volume" in line:
                return float(line.split("mean_volume:")[1].split("dB")[0].strip())
    except Exception:
        pass
    return -99.0


def normalize_audio(src_path, out_path):
    """Normalize audio: 24kHz mono, -23 LUFS, no DC offset, no clipping."""
    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(src_path),
        "-af", "highpass=f=80,loudnorm=I=-23:LRA=7:TP=-2,aformat=sample_fmts=s16:sample_rates=24000:channel_layouts=mono",
        str(out_path)
    ], capture_output=True, timeout=60)
    return r.returncode == 0 and os.path.exists(out_path)


def sha256_file(path):
    """Full-file SHA256 hash — audit P0 fix (was MD5 of first 8KB)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_transcript(text):
    """Normalize text for TTS training alignment — Gemini audit P1 fix.

    Converts numbers/abbreviations to spoken form so text matches audio.
    Critical: if text says '$70k' but audio says 'seventy thousand dollars',
    the model gets confused during alignment, causing glitchy speech.
    """
    # Bitcoin/crypto terms
    text = re.sub(r'\bBTC\b', 'B-T-C', text)
    text = re.sub(r'\bETH\b', 'E-T-H', text)
    text = re.sub(r'\bUTXO\b', 'U-T-X-O', text)
    text = re.sub(r'\bETF\b', 'E-T-F', text)
    text = re.sub(r'\bATH\b', 'all-time high', text)
    text = re.sub(r'\bFUD\b', 'F-U-D', text)
    text = re.sub(r'\bDeFi\b', 'de-fi', text)

    # Dollar amounts
    text = re.sub(r'\$(\d+(?:\.\d+)?)k\b', lambda m: f"{float(m.group(1)):.0f} thousand dollars", text)
    text = re.sub(r'\$(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million dollars", text)
    text = re.sub(r'\$(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion dollars", text)

    # Percentages
    text = re.sub(r'(\d+(?:\.\d+)?)%', r'\1 percent', text)

    # Clean up
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def segment_raw_wav(threshold_db=50):
    """Segment pbx_raw.wav using ORDERED event parsing — audit P0 fix.

    Old approach: zip_longest(silence_starts, silence_ends) — fragile.
    New approach: parse events in stream order, track state machine.
    Also excludes reference clip content (first 40s used as pbx_reference.wav).
    """
    print(f"[Prep v2] Segmenting pbx_raw.wav at -{threshold_db}dB:d=0.3...")
    result = subprocess.run([
        "ffmpeg", "-i", str(RAW_WAV),
        "-af", f"silencedetect=noise=-{threshold_db}dB:d=0.3",
        "-f", "null", "-"
    ], capture_output=True, text=True, timeout=300)

    # Get total duration
    dur_r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", str(RAW_WAV)],
                           capture_output=True, text=True)
    total_dur = float(dur_r.stdout.strip())

    # Parse events in ORDER — fixes zip_longest fragility
    events = []
    for line in result.stderr.split("\n"):
        m = re.search(r"silence_(start|end): ([\d.]+)", line)
        if m:
            events.append((m.group(1), float(m.group(2))))

    # Build speech segments via state machine
    segments = []
    in_silence = True
    speech_start = 0.0

    # Reference clip = first 30s (skip to avoid data leakage — Gemini audit)
    REF_CLIP_END = 40.0  # skip first 40s (10s lead + 30s reference clip)

    for event_type, timestamp in events:
        if event_type == "end":
            # Silence ended → speech begins
            speech_start = max(timestamp, REF_CLIP_END)
            in_silence = False
        elif event_type == "start":
            # Speech ended → silence begins
            if not in_silence and speech_start < timestamp:
                seg_dur = timestamp - speech_start
                if seg_dur < MIN_SEG_SECS:
                    pass  # too short
                elif seg_dur <= MAX_SEG_SECS:
                    segments.append((speech_start, timestamp))
                else:
                    # Split long segment
                    cur = speech_start
                    while cur + MIN_SEG_SECS < timestamp:
                        end = min(cur + MAX_SEG_SECS, timestamp)
                        segments.append((cur, end))
                        cur = end
            in_silence = True

    # Final trailing segment (after last silence_end or from start if no silences)
    if not in_silence and speech_start < total_dur:
        seg_dur = total_dur - speech_start
        if seg_dur >= MIN_SEG_SECS:
            if seg_dur <= MAX_SEG_SECS:
                segments.append((speech_start, total_dur))
            else:
                cur = speech_start
                while cur + MIN_SEG_SECS < total_dur:
                    end = min(cur + MAX_SEG_SECS, total_dur)
                    segments.append((cur, end))
                    cur = end

    print(f"[Prep v2] Found {len(segments)} raw segments (threshold: -{threshold_db}dB)")
    return segments


def extract_raw_segments(segments):
    """Extract + normalize raw WAV segments."""
    SEGMENTS_DIR.mkdir(exist_ok=True)
    paths = []
    for i, (start, end) in enumerate(segments):
        raw_out = SEGMENTS_DIR / f"raw_{i:04d}_prenorm.wav"
        norm_out = SEGMENTS_DIR / f"raw_{i:04d}.wav"
        r = subprocess.run([
            "ffmpeg", "-y", "-i", str(RAW_WAV),
            "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
            "-ar", "24000", "-ac", "1", str(raw_out)
        ], capture_output=True, timeout=60)
        if r.returncode != 0 or not raw_out.exists():
            continue
        # Normalize loudness
        if normalize_audio(raw_out, norm_out):
            raw_out.unlink(missing_ok=True)
            if norm_out.exists() and norm_out.stat().st_size > 500:
                paths.append(str(norm_out))
        else:
            if raw_out.exists():
                raw_out.rename(norm_out)
                paths.append(str(norm_out))
    print(f"[Prep v2] Extracted {len(paths)} raw segments")
    return paths


def harvest_elevenlabs_lines():
    """Harvest ElevenLabs PBX render cache with full audit fixes.

    Fixes:
    - SHA256 full-file dedup (was MD5 of 8KB)
    - Energy filter actually enforced (was defined but never called)
    - Audio normalized before adding to dataset
    - Max count cap (MAX_SYNTHETIC_RATIO applied in validate_and_write)
    """
    import glob
    print("[Prep v2] Harvesting ElevenLabs PBX lines...")
    ELABS_DIR.mkdir(exist_ok=True)

    patterns = [
        str(OUTPUT_DIR / "run_*" / "audio" / "line_*_mark.m4a"),
        str(OUTPUT_DIR / "run_*" / "audio" / "line_*_pbx.m4a"),
    ]
    all_files = []
    for pat in patterns:
        all_files.extend(glob.glob(pat))
    print(f"[Prep v2] Found {len(all_files)} ElevenLabs line files")

    seen_hashes = set()
    paths = []
    rejected = {"duration": 0, "size": 0, "energy": 0, "dedup": 0, "convert": 0}

    for i, src in enumerate(sorted(all_files)):
        # Duration filter
        dur = get_duration(src)
        if not (MIN_SEG_SECS <= dur <= MAX_SEG_SECS):
            rejected["duration"] += 1
            continue

        # Size filter
        if os.path.getsize(src) < 5000:
            rejected["size"] += 1
            continue

        # Full-file SHA256 dedup — audit P0 fix
        try:
            content_hash = sha256_file(src)
        except Exception:
            continue
        if content_hash in seen_hashes:
            rejected["dedup"] += 1
            continue
        seen_hashes.add(content_hash)

        # Convert M4A → WAV 24kHz mono (pre-normalization)
        raw_wav = ELABS_DIR / f"elabs_{i:04d}_raw.wav"
        norm_wav = ELABS_DIR / f"elabs_{i:04d}.wav"
        r = subprocess.run([
            "ffmpeg", "-y", "-i", src, "-ar", "24000", "-ac", "1", str(raw_wav)
        ], capture_output=True, timeout=30)
        if r.returncode != 0 or not raw_wav.exists():
            rejected["convert"] += 1
            continue

        # Energy filter — audit P0 fix (was defined but never enforced)
        rms = get_rms_db(str(raw_wav))
        if rms < MIN_RMS_DB:
            rejected["energy"] += 1
            raw_wav.unlink(missing_ok=True)
            continue

        # Normalize loudness
        if normalize_audio(raw_wav, norm_wav):
            raw_wav.unlink(missing_ok=True)
        else:
            raw_wav.rename(norm_wav)

        if norm_wav.exists() and norm_wav.stat().st_size > 500:
            paths.append(str(norm_wav))

        if len(paths) % 100 == 0 and len(paths) > 0:
            print(f"[Prep v2] Harvested {len(paths)} ElevenLabs segments...")

    print(f"[Prep v2] ElevenLabs harvest: {len(paths)} usable")
    print(f"  Rejected — duration: {rejected['duration']}, size: {rejected['size']}, "
          f"energy: {rejected['energy']}, dedup: {rejected['dedup']}, convert: {rejected['convert']}")
    return paths


def transcribe_all(raw_paths, elabs_paths):
    """Transcribe with condition_on_previous_text=False — audit P1 fix.

    condition_on_previous_text=False prevents carryover bias on independent clips.
    Transcript normalization ensures text matches spoken audio form.
    """
    all_paths = [(p, "raw") for p in raw_paths] + [(p, "elevenlabs") for p in elabs_paths]
    print(f"[Prep v2] Transcribing {len(all_paths)} segments with Whisper large-v3...")
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    results = []
    rejected_transcript = 0

    for i, (path, source) in enumerate(all_paths):
        if i % 50 == 0:
            print(f"[Prep v2] {i}/{len(all_paths)}...")
        try:
            segs, _ = model.transcribe(
                path,
                language="en",
                beam_size=5,
                condition_on_previous_text=False  # audit P1 fix
            )
            text = " ".join(s.text.strip() for s in segs).strip()

            # Transcript QC — audit P1 fix
            if len(text) < MIN_CHARS or len(text) > MAX_CHARS:
                rejected_transcript += 1
                try: os.remove(path)
                except Exception: pass
                continue
            # Reject if transcript is mostly punctuation/symbols
            alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
            if alpha_ratio < 0.5:
                rejected_transcript += 1
                try: os.remove(path)
                except Exception: pass
                continue

            # Normalize transcript for alignment accuracy — Gemini audit fix
            normalized_text = normalize_transcript(text)

            results.append({"audio": path, "text": normalized_text,
                            "raw_text": text, "source": source})
        except Exception as e:
            print(f"  Whisper error on {path}: {e}")
            rejected_transcript += 1

    print(f"[Prep v2] {len(results)} segments passed transcript QC "
          f"({rejected_transcript} rejected)")
    return results


def validate_and_write(results):
    """Apply synthetic ratio cap, split validation set, write CSV + manifests.

    Audit fixes:
    - MAX_SYNTHETIC_RATIO cap (40% max ElevenLabs)
    - Held-out validation set from real PBX only (never in training)
    - Provenance schema in manifest
    """
    # Validate durations
    valid = []
    for item in results:
        path = item["audio"]
        if not os.path.exists(path):
            continue
        dur = get_duration(path)
        if MIN_SEG_SECS <= dur <= MAX_SEG_SECS:
            item["duration"] = round(dur, 3)
            valid.append(item)

    raw_items = [i for i in valid if i["source"] == "raw"]
    elab_items = [i for i in valid if i["source"] == "elevenlabs"]

    # Apply synthetic ratio cap — ChatGPT audit fix
    max_elab = int(len(raw_items) / (1 - MAX_SYNTHETIC_RATIO) * MAX_SYNTHETIC_RATIO)
    if len(elab_items) > max_elab:
        print(f"[Prep v2] Capping ElevenLabs at {max_elab} (was {len(elab_items)}) "
              f"to maintain {int(MAX_SYNTHETIC_RATIO*100)}% synthetic ratio")
        import random
        random.shuffle(elab_items)
        elab_items = elab_items[:max_elab]

    # Split validation set from raw PBX — ChatGPT audit fix
    # Held-out: never included in training, used for A/B evaluation
    import random
    random.shuffle(raw_items)
    val_items = raw_items[:VALIDATION_SIZE]
    train_raw = raw_items[VALIDATION_SIZE:]
    train_items = train_raw + elab_items

    total_audio = sum(i["duration"] for i in train_items)
    print(f"\n[Prep v2] Final training dataset: {len(train_items)} segments")
    print(f"  Raw PBX: {len(train_raw)} | ElevenLabs: {len(elab_items)}")
    print(f"  Synthetic ratio: {len(elab_items)/len(train_items)*100:.1f}%")
    print(f"  Total audio: {total_audio/60:.1f} min")
    print(f"  Held-out validation: {len(val_items)} real PBX clips")

    # Write training CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="|")
        writer.writerow(["audio_file", "text"])
        for item in train_items:
            writer.writerow([os.path.abspath(item["audio"]),
                             item["text"].replace("|", " ")])

    # Write manifests with provenance — audit fix
    with open(MANIFEST_PATH, "w") as f:
        json.dump(train_items, f, indent=2)
    with open(VALIDATION_PATH, "w") as f:
        json.dump(val_items, f, indent=2)

    print(f"[Prep v2] CSV: {CSV_PATH}")
    print(f"[Prep v2] Manifest: {MANIFEST_PATH}")
    print(f"[Prep v2] Validation: {VALIDATION_PATH}")
    return train_items, val_items


if __name__ == "__main__":
    import sys
    threshold_db = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    print(f"=== PBX Voice Dataset Prep v2 (threshold: -{threshold_db}dB) ===")
    segs = segment_raw_wav(threshold_db)
    raw_paths = extract_raw_segments(segs)
    elabs_paths = harvest_elevenlabs_lines()
    results = transcribe_all(raw_paths, elabs_paths)
    train_items, val_items = validate_and_write(results)
    print(f"\n✅ Dataset ready: {len(train_items)} training + {len(val_items)} validation")
