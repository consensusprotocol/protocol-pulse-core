#!/usr/bin/env python3
"""Test A2 (R2-06): VO stem resampling before concat.

1s silence (48kHz stereo) + 2s tone (22050Hz mono) must concat to 3.00s +/- 0.02.
Without resampling, ffmpeg concat demuxer produces ~1.46s (the old bug).
"""
import os
import subprocess
import sys
import tempfile

PASS = 0
FAIL = 0


def _check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10, check=True)
    return float(r.stdout.strip())


def test_resample_concat():
    """1s silence + 2s tone (22050 mono) must equal 3.00s +/- 0.02."""
    print("\n--- Test A2: VO stem resample before concat ---")

    with tempfile.TemporaryDirectory() as td:
        # 1s silence at 48000 Hz stereo
        silence = os.path.join(td, "silence.wav")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", "1.0", "-c:a", "pcm_s16le", silence,
        ], capture_output=True, timeout=10, check=True)

        # 2s 440Hz tone at 22050 Hz mono (simulates ElevenLabs output)
        tone_22k = os.path.join(td, "tone_22050.wav")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2:sample_rate=22050",
            "-ac", "1", "-c:a", "pcm_s16le", tone_22k,
        ], capture_output=True, timeout=10, check=True)

        # Test 1: RAW concat (the bug) — should NOT be 3.00s
        raw_list = os.path.join(td, "raw_list.txt")
        raw_out = os.path.join(td, "raw_concat.wav")
        with open(raw_list, "w") as f:
            f.write(f"file '{silence}'\n")
            f.write(f"file '{tone_22k}'\n")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", raw_list,
            "-c:a", "pcm_s16le", raw_out,
        ], capture_output=True, timeout=10)
        raw_dur = get_duration(raw_out) if os.path.exists(raw_out) else 0
        _check("raw concat != 3.00s (demonstrates bug)", abs(raw_dur - 3.0) > 0.02,
               f"raw_dur={raw_dur:.3f}")

        # Test 2: RESAMPLED concat (the fix) — must be 3.00s +/- 0.02
        resampled = os.path.join(td, "tone_48k.wav")
        subprocess.run([
            "ffmpeg", "-y", "-i", tone_22k,
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", resampled,
        ], capture_output=True, timeout=10, check=True)

        fix_list = os.path.join(td, "fix_list.txt")
        fix_out = os.path.join(td, "fix_concat.wav")
        with open(fix_list, "w") as f:
            f.write(f"file '{silence}'\n")
            f.write(f"file '{resampled}'\n")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", fix_list,
            "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", fix_out,
        ], capture_output=True, timeout=10, check=True)
        fix_dur = get_duration(fix_out)
        _check("resampled concat == 3.00s +/- 0.02", abs(fix_dur - 3.0) <= 0.02,
               f"fix_dur={fix_dur:.3f}")


if __name__ == "__main__":
    print("=== A2 VO RESAMPLE TEST ===")
    test_resample_concat()
    total = PASS + FAIL
    print(f"\n{'='*40}")
    print(f"A2 TESTS: {PASS}/{total} passed, {FAIL} failed")
    if FAIL:
        sys.exit(1)
    print("ALL PASS")
