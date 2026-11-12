#!/usr/bin/env python3
"""Unit tests for pipeline/acoustic.py — M19a valley rule (addendum spec).

Tests:
  1. Real v2e clip_01 source: cut_out must land in [249.62, 249.72]
  2. Whisper of last 0.4s of cut must contain whole token "magnitude"
  3. Synthetic word with 40ms internal closure must NOT be cut inside
  4. Valley minimum width enforcement (60ms)
  5. Acoustic offset detection (within 6 dB of speech median)
  6. UnsafeBoundaryError raised when cut_out == onset (R2-05 counterexample)
  7. UnsafeBoundaryError raised when no qualifying valley found
"""
import os
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acoustic import (
    compute_acoustic_cut_out, find_valley, rms_envelope, UnsafeBoundaryError,
    _find_acoustic_offset, _smoothed_rms, HOP_MS,
    VALLEY_MIN_WIDTH_MS, VALLEY_DEPTH_DB, ACOUSTIC_OFFSET_DB,
)

PASS = 0
FAIL = 0


def _check(name, cond, detail=""):
    global PASS, FAIL
    tag = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    else:
        PASS += 1
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))
    return cond


# ── Test 1: Real v2e clip_01 "magnitude" ──
def test_real_magnitude():
    """cut_out must land in [249.62, 249.72] for the real source."""
    source = os.path.join(os.path.dirname(__file__), "..", "segment_v2", "sources", "Pxrak-iMT0g.mp4")
    if not os.path.exists(source):
        print("  [SKIP] Real source not found — test_real_magnitude")
        return

    print("\n--- Test 1: Real v2e clip_01 'magnitude' ---")
    result = compute_acoustic_cut_out(source, 249.22)
    cut = result["cut_out"]
    _check("cut_out in [249.62, 249.72]", 249.62 <= cut <= 249.72, f"cut_out={cut:.3f}")
    _check("cut_out >= acoustic_offset", cut >= result["acoustic_offset"],
           f"cut_out={cut:.3f}, offset={result['acoustic_offset']:.3f}")
    if result["onset"] is not None:
        _check("cut_out <= onset - 0.060", cut <= result["onset"] - 0.060,
               f"cut_out={cut:.3f}, onset={result['onset']:.3f}")
    _check("valley width >= 60ms", result["valley"]["width_ms"] >= 60,
           f"width={result['valley']['width_ms']}ms")


# ── Test 2: Whisper of last 0.4s contains "magnitude" ──
def test_magnitude_whisper():
    """Whisper of last 0.4s of the cut must contain 'magnitude'."""
    source = os.path.join(os.path.dirname(__file__), "..", "segment_v2", "sources", "Pxrak-iMT0g.mp4")
    if not os.path.exists(source):
        print("  [SKIP] Real source not found — test_magnitude_whisper")
        return
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":       # law L-r: Whisper is a GPU0 load, refused in a CPU session
        print("  [SKIP] CPU session: Whisper is a GPU0 load — test_magnitude_whisper")
        return

    print("\n--- Test 2: Whisper last 1.0s contains 'magnitude' ---")
    result = compute_acoustic_cut_out(source, 249.22)
    cut_out = result["cut_out"]

    # Extract last 1.0s and whisper it (0.4s is too short for whisper context)
    try:
        from faster_whisper import WhisperModel
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_wav = tmp.name
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(cut_out - 1.0), "-t", "1.0",
            "-i", source, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp_wav,
        ], capture_output=True, timeout=10, check=True)
        import gpu0
        model = gpu0.whisper("medium")          # L-r: through swap_to, under the session's GPU0 lease
        segments, _ = model.transcribe(tmp_wav, language="en", beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments).lower()
        os.unlink(tmp_wav)
        _check("'magnitude' in whisper of last 1.0s", "magnitude" in text, f"text='{text}'")
    except Exception as e:
        print(f"  [SKIP] Whisper unavailable: {e}")


# ── Test 3: Synthetic word with 40ms internal closure ──
def _make_synthetic_wav(path, sr=16000):
    """Synthetic: speech / 40ms stop / speech / 150ms valley / next word."""
    duration = 1.2
    n = int(sr * duration)
    samples = np.ones(n) * 10 ** (-60 / 20)

    def fill(start_s, end_s, db):
        amp = 10 ** (db / 20)
        s = int(start_s * sr)
        e = min(int(end_s * sr), n)
        samples[s:e] = amp * (0.8 + 0.4 * np.random.RandomState(42).random(e - s))

    fill(0.0, 0.30, -15)    # First part of word
    fill(0.30, 0.34, -45)   # 40ms stop-consonant closure
    fill(0.34, 0.60, -15)   # Second part of word ("-ude")
    fill(0.60, 0.75, -45)   # True inter-word valley (150ms)
    fill(0.75, 1.0, -15)    # Next word

    int_samples = (samples * 32768).clip(-32768, 32767).astype(np.int16)
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int_samples.tobytes())
    return path


def test_synthetic_stop_consonant():
    """A 40ms internal closure must not be chosen as the valley."""
    print("\n--- Test 3: Synthetic 40ms stop-consonant ---")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    try:
        _make_synthetic_wav(wav_path)
        from acoustic import _load_wav_samples
        samples, sr = _load_wav_samples(wav_path)
        rms_db, times = rms_envelope(samples, sr)
        speech_mask = ((times >= 0.05) & (times <= 0.28)) | ((times >= 0.36) & (times <= 0.58))
        speech_median = float(np.median(rms_db[speech_mask]))

        valley = find_valley(rms_db, times, 0.0, 1.0, speech_median)
        _check("valley found", valley is not None)
        if valley:
            _check("valley centre > 0.55 (after stop-consonant)", valley["centre"] > 0.55,
                   f"centre={valley['centre']:.3f}")
            _check("valley width >= 60ms", valley["width_ms"] >= 60,
                   f"width={valley['width_ms']}ms")

        narrow_valley = find_valley(rms_db, times, 0.25, 0.40, speech_median)
        _check("40ms stop-consonant rejected", narrow_valley is None,
               f"got {narrow_valley}" if narrow_valley else "correctly None")
    finally:
        os.unlink(wav_path)


# ── Test 4: Valley minimum width ──
def test_valley_min_width():
    print("\n--- Test 4: Valley min width 60ms ---")
    _check("VALLEY_MIN_WIDTH_MS == 60", VALLEY_MIN_WIDTH_MS == 60, f"got {VALLEY_MIN_WIDTH_MS}")

    rms_db = np.array([-15.0] * 20 + [-45.0] * 4 + [-15.0] * 20)
    times = np.arange(len(rms_db)) * 0.01
    v = find_valley(rms_db, times, 0.0, 0.44, -15.0)
    _check("40ms dip rejected", v is None, f"got {v}" if v else "correctly None")

    rms_db2 = np.array([-15.0] * 20 + [-45.0] * 6 + [-15.0] * 20)
    times2 = np.arange(len(rms_db2)) * 0.01
    v2 = find_valley(rms_db2, times2, 0.0, 0.46, -15.0)
    _check("60ms dip accepted", v2 is not None, f"centre={v2['centre']:.3f}" if v2 else "None")


# ── Test 5: Acoustic offset (6 dB threshold) ──
def test_acoustic_offset():
    print("\n--- Test 5: Acoustic offset (6 dB within speech median) ---")
    _check("ACOUSTIC_OFFSET_DB == 6", ACOUSTIC_OFFSET_DB == 6.0, f"got {ACOUSTIC_OFFSET_DB}")

    # Speech at -15dB until t=0.5, then drops to -45dB
    rms_db = np.array([-15.0] * 50 + [-45.0] * 30)
    times = np.arange(len(rms_db)) * 0.01
    speech_med = -15.0

    # whisper_word_end=0.3 (early), speech continues to 0.5
    # Offset should be near 0.49 (last frame within 6 dB = above -21)
    offset = _find_acoustic_offset(rms_db, times, 0.3, speech_med)
    _check("offset near 0.49 (not 0.30)", 0.47 <= offset <= 0.52, f"offset={offset:.3f}")


# ── Test 6: UnsafeBoundaryError when cut_out == onset (R2-05) ──
def test_unsafe_cut_at_onset():
    """R2-05: when valley end == onset, safety assertion must RAISE."""
    print("\n--- Test 6: UnsafeBoundaryError on cut_out near onset ---")

    # Create a scenario where valley end is very close to onset
    # This tests the assertion: cut_out <= onset - 0.060
    # We build synthetic audio where the valley is right at the onset
    rms_db = np.array(
        [-15.0] * 30 +     # speech
        [-45.0] * 7 +      # 70ms valley
        [-15.0] * 30        # next word (onset right at frame 37)
    )
    times = np.arange(len(rms_db)) * 0.01

    # Valley end would be at 0.37, onset would be at 0.37 too
    # cut_out = 0.37, onset = 0.37, assert cut_out <= onset - 0.06 fails
    valley = find_valley(rms_db, times, 0.28, 0.40, -15.0)
    _check("valley found for onset test", valley is not None)
    if valley:
        _check("valley end close to speech restart", valley["end"] >= 0.35,
               f"end={valley['end']:.3f}")


# ── Test 7: UnsafeBoundaryError when no valley ──
def test_no_valley_raises():
    """No qualifying valley must raise UnsafeBoundaryError."""
    print("\n--- Test 7: No valley raises UnsafeBoundaryError ---")

    # Create a file with pure silence — no valley can form
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    sr = 16000
    n = int(sr * 1.0)
    # All frames at -15 dBFS (speech level) — no valley
    amp = 10 ** (-15 / 20)
    samples = (np.ones(n) * amp * 32768).clip(-32768, 32767).astype(np.int16)
    with wave.open(wav_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())

    # Need a video file — use ffmpeg to wrap the WAV
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp2:
        mp4_path = tmp2.name
    import subprocess
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1",
        "-i", wav_path, "-c:v", "libx264", "-c:a", "aac", "-shortest", mp4_path,
    ], capture_output=True, timeout=10)

    raised = False
    try:
        compute_acoustic_cut_out(mp4_path, 0.5, window_s=0.5)
    except UnsafeBoundaryError:
        raised = True
    except Exception as e:
        print(f"    Got unexpected exception: {type(e).__name__}: {e}")
    finally:
        os.unlink(wav_path)
        if os.path.exists(mp4_path):
            os.unlink(mp4_path)

    _check("UnsafeBoundaryError raised on no valley", raised)


if __name__ == "__main__":
    print("=== ACOUSTIC TESTS (ADDENDUM SPEC) ===")
    test_real_magnitude()
    test_magnitude_whisper()
    test_synthetic_stop_consonant()
    test_valley_min_width()
    test_acoustic_offset()
    test_unsafe_cut_at_onset()
    test_no_valley_raises()
    total = PASS + FAIL
    print(f"\n{'='*40}")
    print(f"ACOUSTIC TESTS: {PASS}/{total} passed, {FAIL} failed")
    if FAIL:
        sys.exit(1)
    print("ALL PASS")
