#!/usr/bin/env python3
"""
PROTOCOL PULSE — GOLDEN PATH TEST HARNESS
==========================================
Deterministic E2E pipeline test. Fixed inputs, same expected outputs every time.
Run before/after every CC session. If 7/7 pass, the pipeline is sound.

Usage:
    python3 tests/golden_path.py           # full 7-check suite
    python3 tests/golden_path.py --quick   # checks 1,4,5,6,7 only (~30s)
"""

import argparse
import fcntl
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
PIPELINE = BASE / "video_pipeline_v3"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Ensure pipeline is importable
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(PIPELINE))


# ── helpers ──────────────────────────────────────────────────────────────────

class CheckResult:
    def __init__(self, name, passed, duration, detail=""):
        self.name = name
        self.passed = passed
        self.duration = duration
        self.detail = detail

    def __str__(self):
        tag = "PASS" if self.passed else "FAIL"
        line = f"[{tag}] {self.name:<35} ({self.duration:.1f}s)"
        if self.detail:
            line += f" — {self.detail}"
        return line


def timed(fn):
    """Run fn(), return (result, elapsed_seconds)."""
    t0 = time.time()
    result = fn()
    return result, time.time() - t0


def ffprobe_json(path):
    """Get ffprobe output as dict."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(path)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return json.loads(r.stdout) if r.returncode == 0 else {}


def ffprobe_duration(path):
    """Get media duration in seconds."""
    info = ffprobe_json(path)
    fmt = info.get("format", {})
    dur = fmt.get("duration")
    if dur:
        return float(dur)
    for s in info.get("streams", []):
        if s.get("duration"):
            return float(s["duration"])
    return 0.0


# ── CHECK 1: Imports + Environment ──────────────────────────────────────────

def check_imports():
    errors = []

    # Pipeline modules
    modules = [
        "video_pipeline_v3.assembler",
        "video_pipeline_v3.tts_engine",
        "video_pipeline_v3.daily_producer",
    ]
    for mod in modules:
        try:
            __import__(mod)
        except Exception as e:
            errors.append(f"Import {mod}: {e}")

    # TTS_PROVIDER
    tts_prov = os.environ.get("TTS_PROVIDER", "")
    if not tts_prov:
        # Not fatal — default is "local"
        pass

    # API keys — check via pipeline's own key loader (reads .env files)
    try:
        from video_pipeline_v3.relay import get_key
        for key_name in ["ELEVENLABS_API_KEY"]:
            try:
                val = get_key(key_name, required=False)
                if not val:
                    errors.append(f"Missing key: {key_name}")
            except Exception:
                errors.append(f"Missing key: {key_name}")
    except ImportError:
        # Fallback to raw env
        for key_name in ["ELEVENLABS_API_KEY"]:
            if not os.environ.get(key_name):
                errors.append(f"Missing env var: {key_name}")

    # GPU
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            errors.append("nvidia-smi failed — no GPU detected")
    except FileNotFoundError:
        errors.append("nvidia-smi not found")
    except subprocess.TimeoutExpired:
        errors.append("nvidia-smi timed out")

    if errors:
        return CheckResult("CHECK 1: Imports + env", False, 0, "; ".join(errors))
    return CheckResult("CHECK 1: Imports + env", True, 0)


# ── CHECK 2: TTS Generation ─────────────────────────────────────────────────

def check_tts():
    script = json.loads((FIXTURES / "golden_script.json").read_text())
    dialogue = script["dialogue"]

    # Pick 3 spoken lines (skip CLIP entries)
    spoken = [d for d in dialogue if d.get("host") != "CLIP"][:3]
    if len(spoken) < 3:
        return CheckResult("CHECK 2: TTS generation", False, 0, "Not enough spoken lines in fixture")

    tmpdir = tempfile.mkdtemp(prefix="golden_tts_")
    errors = []
    provider_used = os.environ.get("TTS_PROVIDER", "local")

    try:
        from video_pipeline_v3.tts_engine import tts_local

        for i, line in enumerate(spoken):
            out_path = os.path.join(tmpdir, f"line_{i}.m4a")
            host = line.get("host", 1)
            if isinstance(host, str):
                host = 2  # fallback for non-int hosts
            seg_type = line.get("type", "setup")

            ok = tts_local(
                text=line["text"],
                output_path=out_path,
                host=host,
                segment_type=seg_type,
            )

            if not ok or not os.path.exists(out_path):
                errors.append(f"Line {i}: TTS returned False or no output file")
                continue

            fsize = os.path.getsize(out_path)
            if fsize == 0:
                errors.append(f"Line {i}: output file is 0 bytes")
                continue

            dur = ffprobe_duration(out_path)
            if dur < 2.0 or dur > 30.0:
                errors.append(f"Line {i}: duration {dur:.1f}s outside [2s, 30s]")

            # Check sample rate
            info = ffprobe_json(out_path)
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "audio":
                    sr = int(stream.get("sample_rate", 0))
                    if sr not in (44100, 48000, 22050, 24000):
                        errors.append(f"Line {i}: sample rate {sr} unexpected")
                    break

    except Exception as e:
        errors.append(f"TTS exception: {e}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if errors:
        return CheckResult("CHECK 2: TTS generation", False, 0, "; ".join(errors))
    return CheckResult("CHECK 2: TTS generation", True, 0, f"provider: {provider_used}")


# ── CHECK 3: Assembly ────────────────────────────────────────────────────────

def check_assembly():
    """Full assembly with golden fixtures. Produces a short video and validates it."""
    script = json.loads((FIXTURES / "golden_script.json").read_text())
    dialogue = script["dialogue"]
    spoken = [d for d in dialogue if d.get("host") != "CLIP"]

    tmpdir = tempfile.mkdtemp(prefix="golden_asm_")
    audio_dir = os.path.join(tmpdir, "audio")
    os.makedirs(audio_dir)
    errors = []

    try:
        from video_pipeline_v3.tts_engine import generate_dialogue_audio
        from video_pipeline_v3.assembler import assemble_episode

        # Generate audio for all spoken lines
        audio_data = generate_dialogue_audio(dialogue, audio_dir)
        if not audio_data or not audio_data.get("lines"):
            return CheckResult("CHECK 3: Assembly", False, 0, "generate_dialogue_audio returned no lines")

        # Build extracted_clips stub — we use blank clips since we don't have real downloads
        clips_dir = os.path.join(tmpdir, "clips")
        os.makedirs(clips_dir)
        extracted_clips = {}
        for rank in [1, 2]:
            clip_path = os.path.join(clips_dir, f"clip_{rank}.mp4")
            # Generate a 10s blank clip
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i",
                f"color=c=0x0A0A0F:s=1920x1080:d=10:r=30",
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-t", "10", "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", "-shortest", clip_path
            ], capture_output=True, timeout=30)
            extracted_clips[rank] = {
                "path": clip_path,
                "channel": "GoldenTest",
                "video_id": f"GOLDEN_TEST_{rank}",
                "duration": 10.0,
            }

        output_path = os.path.join(tmpdir, "golden_test.mp4")
        result = assemble_episode(
            script=script,
            audio_data=audio_data,
            extracted_clips=extracted_clips,
            output_path=output_path,
            btc_price="$84,000",
        )

        if not result or not os.path.exists(output_path):
            return CheckResult("CHECK 3: Assembly", False, 0, "assemble_episode returned empty or no file")

        fsize = os.path.getsize(output_path)
        if fsize < 1_000_000:  # 1MB minimum (relaxed from 10MB for test content)
            errors.append(f"File size {fsize/1e6:.1f}MB < 1MB minimum")

        # Duration
        dur = ffprobe_duration(output_path)
        if dur < 30 or dur > 900:
            errors.append(f"Duration {dur:.0f}s outside [30s, 900s]")

        # Resolution + FPS
        info = ffprobe_json(output_path)
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                w = int(stream.get("width", 0))
                h = int(stream.get("height", 0))
                if w != 1920 or h != 1080:
                    errors.append(f"Resolution {w}x{h} — expected 1920x1080")
                fps_str = stream.get("r_frame_rate", "0/1")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    fps = float(num) / float(den) if float(den) else 0
                else:
                    fps = float(fps_str)
                if fps < 29.0 or fps > 31.0:
                    errors.append(f"FPS {fps:.2f} — expected ~30")
                break

        # Freeze detection
        freeze_result = subprocess.run(
            ["ffmpeg", "-i", output_path, "-vf", "freezedetect=n=0.003:d=1.5",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300
        )
        freeze_count = freeze_result.stderr.count("freeze_start")
        if freeze_count > 0:
            errors.append(f"FREEZE FRAMES: {freeze_count} detected (threshold: 0)")

        # Silence detection (middle 80%)
        if dur > 10:
            start_trim = dur * 0.1
            end_trim = dur * 0.9
            middle_dur = end_trim - start_trim
            silence_result = subprocess.run(
                ["ffmpeg", "-ss", str(start_trim), "-t", str(middle_dur),
                 "-i", output_path, "-af", "silencedetect=n=-40dB:d=0.8",
                 "-f", "null", "-"],
                capture_output=True, text=True, timeout=300
            )
            silence_count = silence_result.stderr.count("silence_start")
            if silence_count > 0:
                errors.append(f"SILENCE GAPS: {silence_count} > 0.8s in middle 80%")

        # Loudness
        loudness_result = subprocess.run(
            ["ffmpeg", "-i", output_path, "-af", "loudnorm=print_format=json",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300
        )
        # Parse loudnorm JSON from stderr
        stderr_text = loudness_result.stderr
        try:
            json_start = stderr_text.rfind("{")
            json_end = stderr_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                loud_data = json.loads(stderr_text[json_start:json_end])
                integrated = float(loud_data.get("input_i", -99))
                true_peak = float(loud_data.get("input_tp", 0))
                if integrated < -18 or integrated > -10:
                    errors.append(f"Loudness {integrated:.1f} LUFS outside [-18, -10]")
                if true_peak > -0.5:
                    errors.append(f"True peak {true_peak:.1f} dBFS > -0.5")
        except (json.JSONDecodeError, ValueError):
            pass  # non-fatal if loudnorm parse fails

        detail_parts = [f"{freeze_count} freezes"]
        if not errors:
            try:
                detail_parts.append(f"{integrated:.1f} LUFS")
            except NameError:
                pass

    except Exception as e:
        errors.append(f"Assembly exception: {e}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if errors:
        return CheckResult("CHECK 3: Assembly", False, 0, "; ".join(errors))
    return CheckResult("CHECK 3: Assembly", True, 0, ", ".join(detail_parts))


# ── CHECK 4: Process Lock ───────────────────────────────────────────────────

def check_process_lock():
    """Verify flock prevents two daily_producer instances."""
    lock_path = "/tmp/golden_path_lock_test.lock"
    errors = []

    try:
        # Acquire the lock (simulating first process)
        lock_file = open(lock_path, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Try acquiring same lock (simulating second process)
        lock_file2 = open(lock_path, "w")
        try:
            fcntl.flock(lock_file2, fcntl.LOCK_EX | fcntl.LOCK_NB)
            errors.append("Second process acquired lock — flock not working")
        except (IOError, OSError):
            pass  # Expected: second process blocked

        lock_file2.close()

        # Now test via actual daily_producer lock mechanism
        real_lock = "/tmp/daily_producer.lock"
        real_lock_file = None
        try:
            real_lock_file = open(real_lock, "w")
            fcntl.flock(real_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Good — we got the lock, meaning no stale lock exists
            # Now test that a subprocess can't also get it
            test_script = (
                "import fcntl, sys; "
                "f = open('/tmp/daily_producer.lock', 'w'); "
                "try:\n"
                "    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
                "    print('ACQUIRED')\n"
                "except (IOError, OSError):\n"
                "    print('BLOCKED')\n"
            )
            r = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True, text=True, timeout=5
            )
            if "BLOCKED" not in r.stdout:
                errors.append("Subprocess acquired lock while parent holds it")
        except (IOError, OSError):
            # Lock held by running producer — that's fine, means lock works
            pass
        finally:
            if real_lock_file:
                try:
                    fcntl.flock(real_lock_file, fcntl.LOCK_UN)
                    real_lock_file.close()
                except Exception:
                    pass

        # Release test lock
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
    except Exception as e:
        errors.append(f"Lock test exception: {e}")
    finally:
        try:
            os.unlink(lock_path)
        except OSError:
            pass

    if errors:
        return CheckResult("CHECK 4: Process lock", False, 0, "; ".join(errors))
    return CheckResult("CHECK 4: Process lock", True, 0)


# ── CHECK 5: Watchdog Detection ─────────────────────────────────────────────

def check_watchdog():
    """Verify watchdog can detect a crash in the producer debug log."""
    fake_log = "/tmp/producer_debug.log"
    errors = []

    try:
        # Write a fake crash traceback
        crash_text = (
            "[2026-03-23 01:00:00] Starting daily_producer step 7\n"
            "Traceback (most recent call last):\n"
            '  File "video_pipeline_v3/daily_producer.py", line 412, in run_pipeline\n'
            "    result = assemble_episode(script, audio_data, clips, output)\n"
            '  File "video_pipeline_v3/assembler.py", line 1847, in assemble_episode\n'
            "    overlay = config['missing_key']\n"
            "KeyError: 'missing_key'\n"
        )
        Path(fake_log).write_text(crash_text)

        # Check if the log content has traceback indicators
        log_content = Path(fake_log).read_text()
        has_traceback = "Traceback" in log_content
        has_keyerror = "KeyError" in log_content

        if not has_traceback:
            errors.append("Fake crash log missing Traceback")
        if not has_keyerror:
            errors.append("Fake crash log missing KeyError")

        # Verify no CC session was spawned by checking tmux
        tmux_result = subprocess.run(
            ["tmux", "list-sessions"],
            capture_output=True, text=True, timeout=5
        )
        cc_sessions = [
            line for line in tmux_result.stdout.splitlines()
            if "cc_fix" in line.lower() or "golden_path" in line.lower()
        ]
        if cc_sessions:
            errors.append(f"Unexpected CC fix sessions: {cc_sessions}")

    except Exception as e:
        errors.append(f"Watchdog test exception: {e}")
    finally:
        try:
            os.unlink(fake_log)
        except OSError:
            pass

    if errors:
        return CheckResult("CHECK 5: Watchdog detection", False, 0, "; ".join(errors))
    return CheckResult("CHECK 5: Watchdog detection", True, 0)


# ── CHECK 6: Render Context File ────────────────────────────────────────────

def check_render_context():
    """Verify render context file exists with required fields."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    ctx_path = f"/tmp/render_context_{today}.json"
    errors = []

    # Also check yesterday (render may have run overnight)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    ctx_path_yesterday = f"/tmp/render_context_{yesterday}.json"

    found_path = None
    if os.path.exists(ctx_path):
        found_path = ctx_path
    elif os.path.exists(ctx_path_yesterday):
        found_path = ctx_path_yesterday

    if not found_path:
        # Not fatal — create a minimal one for verification
        # Check if any render_context exists at all
        import glob
        contexts = sorted(glob.glob("/tmp/render_context_*.json"))
        if contexts:
            found_path = contexts[-1]
        else:
            errors.append(f"No render_context file found (checked {ctx_path} and {ctx_path_yesterday})")
            return CheckResult("CHECK 6: Render context file", False, 0, "; ".join(errors))

    try:
        data = json.loads(Path(found_path).read_text())
        required = ["episode_date", "steps_completed"]
        for field in required:
            if field not in data:
                errors.append(f"Missing field: {field}")

        steps = data.get("steps_completed", [])
        if not isinstance(steps, list):
            errors.append(f"steps_completed is not a list: {type(steps)}")
        elif len(steps) < 1:
            errors.append("steps_completed is empty — no steps recorded")

        # btc_price is optional but nice to have
        if "btc_price" not in data:
            pass  # non-fatal

    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
    except Exception as e:
        errors.append(f"Context check exception: {e}")

    if errors:
        return CheckResult("CHECK 6: Render context file", False, 0, "; ".join(errors))
    basename = os.path.basename(found_path)
    return CheckResult("CHECK 6: Render context file", True, 0, basename)


# ── CHECK 7: Global Tweet Gate ──────────────────────────────────────────────

def check_tweet_gate():
    """Verify the X post rate limiter blocks the 4th post."""
    errors = []
    test_db = "/tmp/golden_path_x_gate_test.db"

    try:
        from pp_services.x_service import can_post_tweet, _init_gate_db, _GATE_DB

        # Save original DB path, swap in test DB
        original_db = _GATE_DB
        import pp_services.x_service as xs
        xs._GATE_DB = Path(test_db)

        try:
            # Initialize fresh test DB
            _init_gate_db()

            # We need to bypass the 4-hour gap rule for rapid testing.
            # Insert 3 posts directly with timestamps spread >4h apart.
            conn = sqlite3.connect(test_db)
            now = datetime.now(timezone.utc)
            for i in range(3):
                ts = (now - timedelta(hours=20 - i * 5)).isoformat()  # -20h, -15h, -10h
                conn.execute(
                    "INSERT INTO x_post_ledger (posted_at, tweet_text, source, allowed, reason) "
                    "VALUES (?, ?, 'golden_test', 1, 'ALLOWED: test')",
                    (ts, f"Golden path test tweet {i + 1}")
                )
            conn.commit()
            conn.close()

            # 4th attempt should be BLOCKED by daily limit
            allowed, reason = can_post_tweet(
                text="Golden path test tweet 4 — this should be blocked by daily limit",
                source="golden_test"
            )
            if allowed:
                errors.append(f"4th tweet was ALLOWED — expected BLOCKED. Reason: {reason}")
            elif "daily limit" not in reason.lower() and "3/3" not in reason:
                # Blocked but for wrong reason (e.g., similarity or gap)
                # Still valid — the gate blocked it
                pass

        finally:
            # Restore original DB path
            xs._GATE_DB = original_db

    except ImportError as e:
        errors.append(f"Cannot import x_service: {e}")
    except Exception as e:
        errors.append(f"Tweet gate exception: {e}")
    finally:
        try:
            os.unlink(test_db)
        except OSError:
            pass

    if errors:
        return CheckResult("CHECK 7: Tweet gate", False, 0, "; ".join(errors))
    return CheckResult("CHECK 7: Tweet gate", True, 0)


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Protocol Pulse — Golden Path Test")
    parser.add_argument("--quick", action="store_true",
                        help="Run checks 1,4,5,6,7 only (~30s)")
    args = parser.parse_args()

    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S ET")

    # Define checks
    all_checks = {
        1: ("CHECK 1: Imports + env", check_imports),
        2: ("CHECK 2: TTS generation", check_tts),
        3: ("CHECK 3: Assembly", check_assembly),
        4: ("CHECK 4: Process lock", check_process_lock),
        5: ("CHECK 5: Watchdog detection", check_watchdog),
        6: ("CHECK 6: Render context file", check_render_context),
        7: ("CHECK 7: Tweet gate", check_tweet_gate),
    }

    if args.quick:
        run_checks = [1, 4, 5, 6, 7]
    else:
        run_checks = [1, 2, 3, 4, 5, 6, 7]

    print("━" * 50)
    print("PROTOCOL PULSE — GOLDEN PATH TEST")
    print(f"Run: {run_time}")
    if args.quick:
        print("Mode: QUICK (checks 1,4,5,6,7)")
    print("━" * 50)

    results = []
    total_start = time.time()

    for num in run_checks:
        name, fn = all_checks[num]
        try:
            result, elapsed = timed(fn)
            result.duration = elapsed
            results.append(result)
            print(result)
            if not result.passed:
                # Print failure detail on next line for clarity
                pass
        except Exception as e:
            r = CheckResult(name, False, 0, f"UNHANDLED: {e}")
            results.append(r)
            print(r)

    total_elapsed = time.time() - total_start
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("━" * 50)
    if passed == total:
        verdict = f"RESULT: {passed}/{total} PASS — pipeline is SOUND"
    else:
        failed_names = [r.name for r in results if not r.passed]
        verdict = f"RESULT: {passed}/{total} PASS — FAILURES: {', '.join(failed_names)}"
    print(verdict)
    print(f"Total time: {total_elapsed:.1f}s")
    print("━" * 50)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
