#!/usr/bin/env python3
"""
v3_hook.py — Watches for V3 daily_run.py completion and triggers a parallel V4 render.
Polls for new V3 output files. When found, generates a V4 spec and renders.
V3 is never touched.
"""
import time
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

V3_OUTPUT = Path(__file__).parent.parent / "video_pipeline_v3" / "output"
V4_DIR = Path(__file__).parent
POLL_INTERVAL = 60  # seconds
SEEN_FILE = V4_DIR / "logs" / ".v3_hook_seen.json"


def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


def find_new_v3_outputs(seen: set) -> list[Path]:
    new = []
    if not V3_OUTPUT.exists():
        return new
    for date_dir in sorted(V3_OUTPUT.iterdir()):
        if not date_dir.is_dir():
            continue
        for mp4 in date_dir.glob("*.mp4"):
            key = str(mp4.relative_to(V3_OUTPUT))
            if key not in seen:
                new.append(mp4)
    return new


def trigger_v4_render():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] Generating V4 spec...")
    result = subprocess.run(
        [sys.executable, str(V4_DIR / "generate_spec.py")],
        capture_output=True, text=True,
        cwd=str(V4_DIR.parent),
    )
    if result.returncode != 0:
        print(f"[{ts}] generate_spec FAILED: {result.stderr}")
        return False

    spec_path = V4_DIR / "episode_spec.json"
    print(f"[{ts}] Rendering V4...")
    result = subprocess.run(
        [sys.executable, str(V4_DIR / "producer_v4.py"), str(spec_path)],
        capture_output=True, text=True,
        cwd=str(V4_DIR.parent),
    )
    if result.returncode != 0:
        print(f"[{ts}] V4 render FAILED: {result.stderr[-1000:]}")
        return False

    print(f"[{ts}] V4 render complete")
    return True


def main():
    print("[v3_hook] Starting V3 watcher...")
    seen = load_seen()

    while True:
        new_outputs = find_new_v3_outputs(seen)
        if new_outputs:
            for mp4 in new_outputs:
                key = str(mp4.relative_to(V3_OUTPUT))
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                print(f"[{ts}] New V3 output detected: {key}")
                seen.add(key)

            save_seen(seen)
            trigger_v4_render()

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
