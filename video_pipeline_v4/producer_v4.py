#!/usr/bin/env python3
"""
v4 Remotion-based producer. Reads episode JSON from daily_producer.py output.
Renders via Remotion instead of assembler.py.
Outputs to video_pipeline_v4/output/YYYY-MM-DD/pulse_check_v4_YYYYMMDD.mp4
"""
import subprocess
import json
import os
import sys
from pathlib import Path

REMOTION_DIR = Path(__file__).parent / "remotion"
OUTPUT_DIR = Path(__file__).parent / "output"


def render(episode_spec_path: str, output_path: str = None, test: bool = False):
    spec_path = Path(episode_spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    date = spec["date"]
    out_dir = OUTPUT_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)
    if not output_path:
        output_path = str(out_dir / f"pulse_check_v4_{date.replace('-', '')}.mp4")

    # Write spec to remotion public dir for composition to read
    spec_dest = REMOTION_DIR / "public" / "episode_spec.json"
    spec_dest.write_text(json.dumps(spec, indent=2))

    # Write props file with embedded spec so PulseCheckWrapper can read it
    props_file = REMOTION_DIR / "public" / "render_props.json"
    props_file.write_text(json.dumps({"spec": spec}))

    cmd = [
        "npx",
        "remotion",
        "render",
        "PulseCheck",
        output_path,
        "--props",
        str(props_file.resolve()),
        "--codec",
        "h264",
        "--crf",
        "17",  # PIPELINE LAW: CRF-17 only
        "--fps",
        "30",
        "--width",
        "1920",
        "--height",
        "1080",
        "--concurrency",
        "8",
        "--timeout",
        "60000",
    ]

    if test:
        cmd += ["--frames", "0-89"]  # 90-frame test render (3s @ 30fps)
        print("[v4] TEST MODE: rendering 90 frames only")

    print(f"[v4] Rendering: {' '.join(cmd[:5])}...")
    result = subprocess.run(cmd, cwd=REMOTION_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print("RENDER FAILED:")
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
        sys.exit(1)
    print(f"v4 render complete: {output_path}")
    return output_path


if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--test"]
    if not args:
        print("Usage: python3 producer_v4.py <episode_spec.json> [output_path] [--test]")
        sys.exit(1)
    render(args[0], args[1] if len(args) > 1 else None, test=test_mode)
