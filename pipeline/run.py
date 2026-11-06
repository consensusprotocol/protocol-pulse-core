#!/usr/bin/env python3
"""pipeline/run.py — CLI orchestrator for the Pulse Check pipeline.

Usage:
    # Legacy manual mode (existing stages):
    python3 -m pipeline.run --segment <dir> --stage <stage>

    # Keyword mode (automated end-to-end):
    python3 -m pipeline.run --keyword "Dollar Hegemony" --niche bitcoin --freshness breaking
"""
import argparse
import json
import os
import sys
import time
import datetime
import tempfile
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import resolve_paths

# ── Logging ──

_log_handler = None


def _setup_logging(run_dir):
    """Tee all output to runs/<run_id>/run.log."""
    global _log_handler
    log_path = os.path.join(run_dir, "run.log")
    _log_handler = logging.FileHandler(log_path, mode="a")
    _log_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                                 datefmt="%H:%M:%S"))
    root = logging.getLogger()
    root.addHandler(_log_handler)
    root.setLevel(logging.INFO)

    # Also redirect stdout/stderr to tee
    class Tee:
        def __init__(self, stream, fh):
            self.stream = stream
            self.fh = fh

        def write(self, data):
            self.stream.write(data)
            self.fh.write(data)
            self.fh.flush()

        def flush(self):
            self.stream.flush()
            self.fh.flush()

    fh = open(log_path, "a")
    sys.stdout = Tee(sys.__stdout__, fh)
    sys.stderr = Tee(sys.__stderr__, fh)


# ── Status JSON contract ──

def _now_iso():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).isoformat()


def _load_status(run_dir):
    path = os.path.join(run_dir, "status.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _write_status(run_dir, status):
    """Atomic write of status.json."""
    path = os.path.join(run_dir, "status.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(status, f, indent=2)
    os.replace(tmp, path)


def _init_status(run_dir, run_id, keyword, niche, freshness, stage_names):
    status = {
        "run_id": run_id,
        "keyword": keyword,
        "niche": niche,
        "freshness": freshness,
        "created": _now_iso(),
        "stages": [
            {"name": name, "status": "waiting", "started": None, "ended": None, "detail": None}
            for name in stage_names
        ],
        "outputs": {"h16": None, "v916": None, "thumb": None},
        "gates": {"16x9": None, "9x16": None},
        "sources": [],
        "signoff": None,
        "error": None,
    }
    _write_status(run_dir, status)
    return status


def _update_stage(run_dir, status, stage_name, new_status, detail=None):
    for s in status["stages"]:
        if s["name"] == stage_name:
            s["status"] = new_status
            if new_status == "running":
                s["started"] = _now_iso()
            elif new_status in ("passed", "failed"):
                s["ended"] = _now_iso()
            if detail is not None:
                s["detail"] = detail
            break
    _write_status(run_dir, status)


# ── Legacy stage wrappers (unchanged) ──

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
    from render_vertical import render_9x16
    return render_9x16(segment_dir, args.qa_version,
                       args.output_name.replace("segment", "segment_vertical")
                       if args.output_name else "segment_vertical.mp4")


def stage_gates16(segment_dir, args):
    from gates import run_gates
    paths = resolve_paths(segment_dir, args.qa_version)
    final_mp4 = os.path.join(paths["out_dir"], args.output_name or "segment.mp4")
    manifest = os.path.join(paths["qa_dir"], "concat_manifest_16x9.json")
    ok, results = run_gates(segment_dir, final_mp4, manifest, args.qa_version)
    if not ok:
        print("\n** GATE FAILURE 16:9 — HARD STOP (M2) **")
        return False
    return True


def stage_gates9(segment_dir, args):
    from gates import run_gates
    paths = resolve_paths(segment_dir, args.qa_version)
    vert_name = (args.output_name.replace("segment", "segment_vertical")
                 if args.output_name else "segment_vertical.mp4")
    final_mp4 = os.path.join(paths["out_dir"], vert_name)
    manifest = os.path.join(paths["qa_dir"], "concat_manifest_9x16.json")
    ok, results = run_gates(segment_dir, final_mp4, manifest, args.qa_version)
    if not ok:
        print("\n** GATE FAILURE 9:16 — HARD STOP (M2) **")
        return False
    return True


def stage_telegram(segment_dir, args):
    from telegram_drop import send_telegram_preview
    send_telegram_preview(segment_dir, args.qa_version)


# ── Legacy stage_all (fail-closed fix: check return values) ──

def stage_all(segment_dir, args):
    """Run full pipeline in order. FAIL-CLOSED: stops on any False/exception."""
    t0 = time.time()
    print(f"=== FULL PIPELINE: {segment_dir} ===\n")

    stages = [
        ("VO", lambda: stage_vo(segment_dir, args)),
        ("SHOUTOUT", lambda: stage_shoutout(segment_dir, args)),
        ("RENDER 16:9", lambda: stage_render16(segment_dir, args)),
        ("GATES 16:9", lambda: stage_gates16(segment_dir, args)),
        ("RENDER 9:16", lambda: stage_render9(segment_dir, args)),
        ("GATES 9:16", lambda: stage_gates9(segment_dir, args)),
    ]

    for name, fn in stages:
        print(f"\n>>> Stage: {name}")
        t1 = time.time()
        result = fn()
        elapsed = time.time() - t1
        print(f"  [{name}] {elapsed:.1f}s")
        if result is False:
            print(f"\n** PIPELINE FAIL at {name} — HARD STOP **")
            sys.exit(1)

    elapsed = time.time() - t0
    print(f"\n=== FULL PIPELINE COMPLETE: {elapsed:.0f}s ({elapsed/60:.1f}min) ===")


# ── Keyword mode stages ──

KEYWORD_STAGE_NAMES = [
    "discover", "rank", "select", "validate", "cut",
    "voice", "shoutout", "render16", "gates16",
    "render9", "gates9", "review", "ready",
]


def _run_keyword_stage(name, fn, run_dir, status):
    """Run a single keyword stage with status tracking and fail-closed logic."""
    _update_stage(run_dir, status, name, "running")
    t0 = time.time()
    try:
        result = fn()
        elapsed = time.time() - t0
        if result is False:
            _update_stage(run_dir, status, name, "failed",
                          f"returned False after {elapsed:.1f}s")
            return False
        _update_stage(run_dir, status, name, "passed",
                      f"{elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - t0
        detail = f"{type(e).__name__}: {e} after {elapsed:.1f}s"
        _update_stage(run_dir, status, name, "failed", detail)
        status["error"] = detail
        _write_status(run_dir, status)
        print(f"\n** STAGE {name} EXCEPTION: {e} **")
        import traceback
        traceback.print_exc()
        return False


def stage_keyword(args):
    """Run keyword-mode pipeline: 13 stages, status.json after every transition."""
    run_id = args.run_id or f"kw_{int(time.time())}"
    run_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "runs", run_id)
    os.makedirs(run_dir, exist_ok=True)

    # Create standard subdirectories
    for sub in ("sources", "transcripts", "vo_audio", "out", "qa"):
        os.makedirs(os.path.join(run_dir, sub), exist_ok=True)

    _setup_logging(run_dir)

    print(f"=== KEYWORD PIPELINE: '{args.keyword}' ===")
    print(f"  niche={args.niche}, freshness={args.freshness}, run_id={run_id}")
    print(f"  run_dir={run_dir}")
    print()

    status = _init_status(run_dir, run_id, args.keyword, args.niche, args.freshness,
                          KEYWORD_STAGE_NAMES)

    # Set segment_dir for downstream stages
    args.segment = run_dir
    args.qa_version = None
    t_pipeline = time.time()

    # ── S1: DISCOVER ──
    def do_discover():
        from discover import discover_sources
        sources = discover_sources(
            args.keyword, args.niche, args.freshness, run_dir)
        status["sources"] = [s.get("video_id", "") for s in sources]
        _write_status(run_dir, status)
        if len(sources) < 2:
            print(f"  Only {len(sources)} sources found — need >= 2")
            return False
        return True

    # ── S2: RANK ──
    def do_rank():
        from rank import rank_passages
        return rank_passages(args.keyword, args.niche, run_dir)

    # ── S3: SELECT ──
    def do_select():
        from select_passages import select_and_build_edl
        return select_and_build_edl(args.keyword, args.niche, run_dir)

    # ── S4: VALIDATE ──
    def do_validate():
        from edl_rules import validate_edl
        edl_path = os.path.join(run_dir, "edl.json")
        with open(edl_path) as f:
            edl = json.load(f)
        channels_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "channels.json")
        channels = None
        if os.path.exists(channels_path):
            with open(channels_path) as f:
                channels = json.load(f)
        ok, results = validate_edl(edl, channels_registry=channels)
        for r in results:
            tag = "PASS" if r["pass"] else "FAIL"
            print(f"  {r['rule']}: [{tag}] {r.get('reason', '')}")
        if not ok:
            print("  EDL validation FAILED")
        return ok

    # ── S5: CUT ──
    def do_cut():
        from cut import compute_all_cuts
        return compute_all_cuts(run_dir)

    # ── S6: VOICE ──
    def do_voice():
        return stage_vo(run_dir, args)

    # ── S7: SHOUTOUT ──
    def do_shoutout():
        stage_shoutout(run_dir, args)
        return True

    # ── S8: RENDER 16:9 ──
    def do_render16():
        result = stage_render16(run_dir, args)
        if result:
            h16 = os.path.join(run_dir, "out", args.output_name or "segment.mp4")
            if os.path.exists(h16):
                status["outputs"]["h16"] = h16
                _write_status(run_dir, status)
        return result is not None

    # ── S9: GATES 16:9 ──
    def do_gates16():
        ok = stage_gates16(run_dir, args)
        if ok:
            qa_dir = os.path.join(run_dir, "qa")
            results_path = os.path.join(qa_dir, "gate_results_16x9.json")
            if os.path.exists(results_path):
                with open(results_path) as f:
                    status["gates"]["16x9"] = json.load(f)
                _write_status(run_dir, status)
        return ok

    # ── S10: RENDER 9:16 ──
    def do_render9():
        result = stage_render9(run_dir, args)
        if result:
            vert_name = (args.output_name.replace("segment", "segment_vertical")
                         if args.output_name else "segment_vertical.mp4")
            v916 = os.path.join(run_dir, "out", vert_name)
            if os.path.exists(v916):
                status["outputs"]["v916"] = v916
                _write_status(run_dir, status)
        return result is not None

    # ── S11: GATES 9:16 ──
    def do_gates9():
        ok = stage_gates9(run_dir, args)
        if ok:
            qa_dir = os.path.join(run_dir, "qa")
            results_path = os.path.join(qa_dir, "gate_results_9x16.json")
            if os.path.exists(results_path):
                with open(results_path) as f:
                    status["gates"]["9x16"] = json.load(f)
                _write_status(run_dir, status)
        return ok

    # ── S12: REVIEW ──
    def do_review():
        from review import vision_review
        return vision_review(run_dir, status)

    # ── S13: READY ──
    def do_ready():
        elapsed_total = time.time() - t_pipeline
        # Write READY_FOR_REVIEW.md
        ready_path = os.path.join(run_dir, "READY_FOR_REVIEW.md")
        with open(ready_path, "w") as f:
            f.write(f"# {run_id} — READY FOR REVIEW\n\n")
            f.write(f"- Keyword: {args.keyword}\n")
            f.write(f"- Niche: {args.niche}\n")
            f.write(f"- Freshness: {args.freshness}\n")
            f.write(f"- Total wall-clock: {elapsed_total:.0f}s ({elapsed_total/60:.1f}min)\n\n")
            f.write("## Stage Timings\n\n")
            f.write("| Stage | Status | Time |\n|-------|--------|------|\n")
            for s in status["stages"]:
                f.write(f"| {s['name']} | {s['status']} | {s.get('detail', '')} |\n")
            f.write(f"\n## Outputs\n")
            for k, v in status["outputs"].items():
                if v:
                    f.write(f"- {k}: {v}\n")
        # Write TIMINGS.md
        timings_path = os.path.join(run_dir, "TIMINGS.md")
        with open(timings_path, "w") as f:
            f.write(f"# {run_id} — TIMINGS\n\n")
            f.write("| Stage | Wall-clock |\n|-------|------------|\n")
            for s in status["stages"]:
                f.write(f"| {s['name']} | {s.get('detail', 'N/A')} |\n")
            f.write(f"\n**Total: {elapsed_total:.0f}s ({elapsed_total/60:.1f}min)**\n")
        return True

    # ── Execute all stages ──
    stage_fns = [
        ("discover", do_discover),
        ("rank", do_rank),
        ("select", do_select),
        ("validate", do_validate),
        ("cut", do_cut),
        ("voice", do_voice),
        ("shoutout", do_shoutout),
        ("render16", do_render16),
        ("gates16", do_gates16),
        ("render9", do_render9),
        ("gates9", do_gates9),
        ("review", do_review),
        ("ready", do_ready),
    ]

    for name, fn in stage_fns:
        ok = _run_keyword_stage(name, fn, run_dir, status)
        if not ok:
            print(f"\n** KEYWORD PIPELINE STOPPED at '{name}' **")
            elapsed_total = time.time() - t_pipeline
            print(f"  Total elapsed: {elapsed_total:.0f}s ({elapsed_total/60:.1f}min)")
            sys.exit(1)

    elapsed_total = time.time() - t_pipeline
    print(f"\n=== KEYWORD PIPELINE COMPLETE: {elapsed_total:.0f}s ({elapsed_total/60:.1f}min) ===")
    print(f"  run_id: {run_id}")
    print(f"  run_dir: {run_dir}")
    print(f"READY {run_id}")
    return run_id


# ── Stage dispatch ──

# Backward compat: "gates" maps to gates16
def stage_gates(segment_dir, args):
    return stage_gates16(segment_dir, args)


STAGES = {
    "all": stage_all,
    "vo": lambda sd, a: stage_vo(sd, a),
    "shoutout": lambda sd, a: stage_shoutout(sd, a),
    "render16": lambda sd, a: stage_render16(sd, a),
    "render9": lambda sd, a: stage_render9(sd, a),
    "gates": lambda sd, a: stage_gates(sd, a),
    "gates16": lambda sd, a: stage_gates16(sd, a),
    "gates9": lambda sd, a: stage_gates9(sd, a),
    "telegram": lambda sd, a: stage_telegram(sd, a),
}


def main():
    p = argparse.ArgumentParser(description="Pulse Check pipeline CLI")
    p.add_argument("--segment", default=None, help="Segment directory (legacy mode)")
    p.add_argument("--stage", default=None, choices=list(STAGES.keys()),
                   help="Pipeline stage to run (legacy mode)")

    # Keyword mode
    p.add_argument("--keyword", default=None, help="Keyword topic for automated pipeline")
    p.add_argument("--niche", default="bitcoin", choices=["bitcoin", "open"],
                   help="Discovery niche")
    p.add_argument("--freshness", default="breaking",
                   choices=["breaking", "developing", "analysis"],
                   help="Recency filter")
    p.add_argument("--run-id", default=None, help="Custom run ID (default: auto-generated)")

    # Common
    p.add_argument("--qa-version", type=int, default=None, help="QA version number")
    p.add_argument("--output-name", default="segment.mp4", help="Output filename")
    p.add_argument("--voice-key", default="ELEVENLABS_VOICE_ID_PP2", help="Voice env key")
    p.add_argument("--model", default="eleven_v4", help="ElevenLabs model ID")
    p.add_argument("--layout-table", default=None, help="Layout table dir or JSON")
    args = p.parse_args()

    if args.keyword:
        stage_keyword(args)
    elif args.segment and args.stage:
        STAGES[args.stage](args.segment, args)
    else:
        p.error("Either --keyword or (--segment + --stage) required")


if __name__ == "__main__":
    main()
