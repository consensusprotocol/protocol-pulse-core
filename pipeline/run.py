#!/usr/bin/env python3
"""pipeline/run.py — CLI orchestrator for the Pulse Check pipeline.

Usage:
    python3 -m pipeline.run --segment <segment_dir> --stage <stage>

Stages:
    all       — Run all stages in order
    edl       — Validate EDL only (requires edl_rules.py)
    vo        — Generate VO stems
    shoutout  — Render shoutout scene
    render16  — Render 16:9 final
    render9   — Render 9:16 vertical
    gates     — Run QA gates on 16:9 output
    gates9    — Run QA gates on 9:16 output
    review    — Grok vision second-opinion review
    telegram  — Send Telegram drop (requires all gates PASS)
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import resolve_paths


def stage_vo(segment_dir, args):
    from vo import generate_vo
    return generate_vo(segment_dir,
                       voice_key=args.voice_key,
                       model_id=args.model)


def stage_shoutout(segment_dir, args):
    from shoutout import build_shoutout
    build_shoutout(segment_dir, args.qa_version, "16x9")
    build_shoutout(segment_dir, args.qa_version, "9x16")


def stage_render16(segment_dir, args):
    from render16 import render_16x9
    return render_16x9(segment_dir, args.qa_version, args.output_name or "segment.mp4")


def stage_render9(segment_dir, args):
    """Render 9:16 vertical using the canonical renderer."""
    paths = resolve_paths(segment_dir, args.qa_version)

    # Find 16:9 final
    out_dir = paths["out_dir"]
    horiz = os.path.join(out_dir, args.output_name or "segment.mp4")
    if not os.path.exists(horiz):
        print(f"ERROR: 16:9 output not found at {horiz}")
        sys.exit(1)

    cuts_json = paths["cuts_json"]
    layout_table = args.layout_table or "/home/ultron/protocol_pulse/vertical/layout_tables"

    cmd = [
        sys.executable,
        "/home/ultron/protocol_pulse/vertical/render_vertical.py",
        "--segment", segment_dir,
        "--version", str(args.qa_version or 1),
        "--horizontal", horiz,
        "--cuts", cuts_json,
        "--layout-table", layout_table,
    ]

    import subprocess
    r = subprocess.run(cmd, timeout=1800)
    return r.returncode == 0


def stage_gates(segment_dir, args):
    from gates import run_gates
    paths = resolve_paths(segment_dir, args.qa_version)
    out_dir = paths["out_dir"]
    qa_dir = paths["qa_dir"]

    final_mp4 = os.path.join(out_dir, args.output_name or "segment.mp4")
    manifest = os.path.join(qa_dir, "concat_manifest_16x9.json")

    ok, results = run_gates(segment_dir, final_mp4, manifest, args.qa_version)
    if not ok:
        print("\n** GATE FAILURE — HARD STOP (Law 17) **")
        sys.exit(1)
    return ok


def stage_all(segment_dir, args):
    """Run full pipeline in order."""
    t0 = time.time()
    print(f"=== FULL PIPELINE: {segment_dir} ===\n")

    # VO
    print(">>> Stage: VO")
    stage_vo(segment_dir, args)

    # Shoutout
    print("\n>>> Stage: SHOUTOUT")
    stage_shoutout(segment_dir, args)

    # Render 16:9
    print("\n>>> Stage: RENDER 16:9")
    stage_render16(segment_dir, args)

    # Gates 16:9
    print("\n>>> Stage: GATES 16:9")
    stage_gates(segment_dir, args)

    # Render 9:16
    print("\n>>> Stage: RENDER 9:16")
    stage_render9(segment_dir, args)

    elapsed = time.time() - t0
    print(f"\n=== FULL PIPELINE COMPLETE: {elapsed:.0f}s ({elapsed/60:.1f}min) ===")


STAGES = {
    "all": stage_all,
    "vo": stage_vo,
    "shoutout": stage_shoutout,
    "render16": stage_render16,
    "render9": stage_render9,
    "gates": stage_gates,
}


def main():
    p = argparse.ArgumentParser(description="Pulse Check pipeline CLI")
    p.add_argument("--segment", required=True, help="Segment directory")
    p.add_argument("--stage", required=True, choices=list(STAGES.keys()),
                   help="Pipeline stage to run")
    p.add_argument("--qa-version", type=int, default=None, help="QA version number")
    p.add_argument("--output-name", default="segment.mp4", help="Output filename")
    p.add_argument("--voice-key", default="ELEVENLABS_VOICE_ID_PP2", help="Voice env key")
    p.add_argument("--model", default="eleven_v4", help="ElevenLabs model ID")
    p.add_argument("--layout-table", default=None, help="Layout table dir or JSON")
    args = p.parse_args()

    STAGES[args.stage](args.segment, args)


if __name__ == "__main__":
    main()
