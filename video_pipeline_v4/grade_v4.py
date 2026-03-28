#!/usr/bin/env python3
"""
v4 Grader — delegates to v3's gemini_grade.py.
This is a thin wrapper so v4 can be graded identically to v3.
"""
import subprocess
import sys
import os

V3_GRADER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "video_pipeline_v3",
    "gemini_grade.py",
)


def grade(video_path: str):
    """Grade a v4 render using the same Gemini grader as v3."""
    if not os.path.exists(V3_GRADER):
        print(f"ERROR: v3 grader not found at {V3_GRADER}")
        sys.exit(1)
    result = subprocess.run(
        ["python3", V3_GRADER, video_path],
        capture_output=False,
    )
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 grade_v4.py <video_path.mp4>")
        sys.exit(1)
    sys.exit(grade(sys.argv[1]))
