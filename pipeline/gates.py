#!/usr/bin/env python3
"""pipeline/gates.py — Parameterised QA gate runner.

FROZEN from segment_v1/qa_gates.py. Delegates to the original gate functions.
Only difference: paths resolved from --segment dir, VO_DIR set dynamically.

Usage:
    python3 -m pipeline.gates --segment <segment_dir> --final <mp4> --manifest <json> [--qa-version N]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import resolve_paths

# Patch BASE and VO_DIR before importing qa_gates
import importlib


def run_gates(segment_dir, final_mp4, manifest_path, qa_version=None,
              source_clips=None, vo_assembled_tracks=None):
    """Run all QA gates. Returns (all_pass, results_dict)."""
    paths = resolve_paths(segment_dir, qa_version)

    # Dynamically patch the frozen qa_gates module's BASE and VO_DIR
    sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
    import qa_gates
    qa_gates.BASE = segment_dir
    qa_gates.VO_DIR = paths["vo_dir"]

    qa_dir = paths["qa_dir"]

    # Load assembled VO tracks if path provided
    if vo_assembled_tracks is None:
        vo_tracks_path = os.path.join(qa_dir, "vo_assembled_tracks.json")
        if os.path.exists(vo_tracks_path):
            with open(vo_tracks_path) as f:
                vo_assembled_tracks = json.load(f)

    return qa_gates.run_all_gates(
        final_mp4, manifest_path, qa_dir,
        source_clips=source_clips,
        vo_assembled_tracks=vo_assembled_tracks,
    )


def main():
    p = argparse.ArgumentParser(description="Parameterised QA gate runner")
    p.add_argument("--segment", required=True, help="Segment directory")
    p.add_argument("--final", required=True, help="Final mp4 to test")
    p.add_argument("--manifest", required=True, help="Concat manifest JSON")
    p.add_argument("--qa-version", type=int, default=None)
    p.add_argument("--source-clip", action="append", default=[],
                   help="label:path pairs for G4 source layout classification")
    p.add_argument("--vo-track", action="append", default=[],
                   help="label:path pairs for assembled VO tracks")
    args = p.parse_args()

    source_clips = {}
    for sc in args.source_clip:
        parts = sc.split(":", 1)
        if len(parts) == 2:
            source_clips[parts[0]] = parts[1]

    vo_tracks = {}
    for vt in args.vo_track:
        parts = vt.split(":", 1)
        if len(parts) == 2:
            vo_tracks[parts[0]] = parts[1]

    ok, results = run_gates(
        args.segment, args.final, args.manifest, args.qa_version,
        source_clips=source_clips or None,
        vo_assembled_tracks=vo_tracks or None,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
