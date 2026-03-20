#!/usr/bin/env python3
"""
Auto-grade watcher — polls for new pulse_check renders and grades them via Gemini.
Stops after achieving Grade A.
"""

import glob
import os
import subprocess
import time
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
GRADE_LOG = os.path.join(BASE_DIR, "logs", "auto_grade_result.txt")
GRADER_SCRIPT = os.path.join(BASE_DIR, "gemini_grade.py")
POLL_INTERVAL = 60  # seconds
GRADED_FILES = set()


def find_todays_render():
    """Find a pulse_check mp4 for today that is >200MB and <30min old."""
    today = datetime.utcnow().strftime("%Y%m%d")
    today_dir = datetime.utcnow().strftime("%Y-%m-%d")
    search_dir = os.path.join(OUTPUT_DIR, today_dir)

    if not os.path.isdir(search_dir):
        return None

    pattern = os.path.join(search_dir, f"pulse_check_{today}*.mp4")
    candidates = glob.glob(pattern)

    for path in sorted(candidates, key=os.path.getmtime, reverse=True):
        if path in GRADED_FILES:
            continue
        size_mb = os.path.getsize(path) / (1024 * 1024)
        mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
        age = datetime.utcnow() - mtime

        if size_mb > 200 and age < timedelta(minutes=30):
            return path

    return None


def run_grader(mp4_path):
    """Run gemini_grade.py on the file and return (grade_letter, score, verdict)."""
    log(f"Grading: {os.path.basename(mp4_path)} ({os.path.getsize(mp4_path) / 1e6:.0f}MB)")

    try:
        result = subprocess.run(
            ["python3", GRADER_SCRIPT, mp4_path],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=BASE_DIR,
        )
        output = result.stdout + result.stderr

        # Parse grade from output — look for patterns like "Grade: A", "Score: 85/100"
        grade_letter = "?"
        score = 0
        verdict = output.strip().split("\n")[-1] if output.strip() else "no output"

        for line in output.split("\n"):
            line_lower = line.lower()
            if "grade:" in line_lower or "grade :" in line_lower:
                for ch in "ABCDF":
                    if ch in line.upper().split("grade")[-1][:10].upper():
                        grade_letter = ch
                        break
            if "score:" in line_lower or "/100" in line:
                import re
                m = re.search(r"(\d{1,3})\s*/?\s*100", line)
                if m:
                    score = int(m.group(1))

        # Write result to log
        os.makedirs(os.path.dirname(GRADE_LOG), exist_ok=True)
        with open(GRADE_LOG, "a") as f:
            f.write(f"[{datetime.utcnow().isoformat()}] {os.path.basename(mp4_path)} — "
                    f"Grade: {grade_letter} Score: {score}/100 — {verdict[:200]}\n")

        return grade_letter, score, verdict

    except subprocess.TimeoutExpired:
        log("Grader timed out after 300s")
        return "?", 0, "timeout"
    except Exception as e:
        log(f"Grader error: {e}")
        return "?", 0, str(e)


def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[WATCHER {ts}] {msg}", flush=True)


def main():
    log("Auto-grade watcher started")
    log(f"Watching: {OUTPUT_DIR}")
    log(f"Grader: {GRADER_SCRIPT}")
    log(f"Log: {GRADE_LOG}")

    if not os.path.isfile(GRADER_SCRIPT):
        log(f"ERROR: gemini_grade.py not found at {GRADER_SCRIPT}")
        return

    while True:
        mp4 = find_todays_render()
        if mp4:
            GRADED_FILES.add(mp4)
            grade, score, verdict = run_grader(mp4)
            log(f"Grade: {grade} ({score}/100) — {verdict[:120]}")

            if grade == "A":
                log("Grade A achieved! Stopping watcher.")
                break
        else:
            log("No new render found, waiting...")

        time.sleep(POLL_INTERVAL)

    log("Watcher exiting.")


if __name__ == "__main__":
    main()
