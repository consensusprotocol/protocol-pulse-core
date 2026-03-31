#!/usr/bin/env python3
"""
A/B test runner. Produces both v3 and v4 renders from same episode spec.
Grades both. Reports winner.
"""
import subprocess
import json
import sys
from pathlib import Path


def run_ab_test(episode_spec_path: str):
    spec = json.load(open(episode_spec_path))
    date = spec["date"]

    print(f"=== A/B TEST: {date} ===")
    print()

    # v3 output path (standard location)
    v3_path = f"video_pipeline_v3/output/{date}/pulse_check_{date.replace('-', '')}.mp4"
    print(f"v3 expected at: {v3_path}")
    print("  (Run daily_producer.py or daily_run.py separately for v3)")
    print()

    # v4 render
    print("Running v4 (Remotion)...")
    result = subprocess.run(
        ["python3", "video_pipeline_v4/producer_v4.py", episode_spec_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"v4 FAILED: {result.stderr}")
        return

    # Parse output path from producer
    v4_path = ""
    for line in result.stdout.strip().splitlines():
        if "v4 render complete:" in line:
            v4_path = line.split(":")[-1].strip()
            break

    print()
    print("=" * 60)
    print(f"v3: {v3_path}")
    print(f"v4: {v4_path}")
    print("=" * 60)
    print()
    print("Grade both:")
    print(f"  python3 video_pipeline_v3/gemini_grade.py {v3_path}")
    print(f"  python3 video_pipeline_v4/grade_v4.py {v4_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ab_test.py <episode_spec.json>")
        sys.exit(1)
    run_ab_test(sys.argv[1])
