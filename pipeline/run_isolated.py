#!/usr/bin/env python3
"""pipeline/run_isolated.py — Isolated v2f render orchestration (STEP 1 glue).

Creates a fresh run dir, sha256-checks all inputs, runs cutter + renderers + gates.
No edits to renderers, cutter, G14, G15, or any gate.
"""
import hashlib
import json
import os
import shutil
import sys
import time

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)

SEGMENT_V2 = "/home/ultron/protocol_pulse/segment_v2"
RUNS_DIR = "/home/ultron/protocol_pulse/runs"

# Known-good sha256 hashes (from PRE_RENDER_CHECKPOINT.md section 7)
SOURCE_HASHES = {
    "RBFN4CB60To.mp4": "cfb2c57aebbfd9d41fb98694fa8adbfa5011bf880c9364ababd9dd49b2125460",
    "Pxrak-iMT0g.mp4": "57ba9c51544bbbe0449c3914c95b83448886db6d35cf400bf55ecce7d0f1354a",
    "QCgW8RlTu5Q.mp4": "a1f760077bf02cf1725f9bf68ef1ee7f23dfa192868a71b1cd73fdedb5b65bd4",
}

VO_HASHES = {
    "vo_intro_pp2_v1.wav": "ce576ec2373bbea0efaf0c96e0916cca3feec3153a0f1411a4808de3c6a95290",
    "vo_bridge_01_pp2_v1.wav": "6721610b1b69f20425e59df79bac3f96dfa167b8e08b5805935e9bbcec7d29a3",
    "vo_signoff_pp2_v1.wav": "8796e840c666c0e74e8d31a9d3d61c540ba3c8d183f8832cc94b3209a9462b78",
}

# v2e reference values for abort check (orchestrator STEP 3)
V2E_CUTS = {
    "clip_01": {"cut_out": 249.670, "range": (249.62, 249.72)},
    "clip_02": {"cut_out": 636.72},
    "clip_03": {"cut_in": 998.0, "cut_out": 1011.80},
}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def create_run_dir():
    """Create runs/v2f_<UTC timestamp>. Refuses if it exists."""
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    run_dir = os.path.join(RUNS_DIR, f"v2f_{ts}")
    if os.path.exists(run_dir):
        raise FileExistsError(f"ABORT: run dir already exists: {run_dir}")
    os.makedirs(run_dir)
    os.makedirs(os.path.join(run_dir, "sources"))
    os.makedirs(os.path.join(run_dir, "vo_audio"))
    os.makedirs(os.path.join(run_dir, "transcripts"))
    os.makedirs(os.path.join(run_dir, "out"))
    os.makedirs(os.path.join(run_dir, "qa"))
    return run_dir


def verify_and_link(run_dir):
    """sha256-check sources + VO stems, symlink into run dir. Refuses on mismatch."""
    src_dir = os.path.join(SEGMENT_V2, "sources")
    for name, expected in SOURCE_HASHES.items():
        path = os.path.join(src_dir, name)
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"ABORT: hash mismatch {name}: {actual[:16]}... != {expected[:16]}...")
        os.symlink(path, os.path.join(run_dir, "sources", name))
        print(f"  source OK: {name}")

    vo_src = os.path.join(SEGMENT_V2, "vo_audio")
    for name, expected in VO_HASHES.items():
        path = os.path.join(vo_src, name)
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"ABORT: VO hash mismatch {name}: {actual[:16]}... != {expected[:16]}...")
        os.symlink(path, os.path.join(run_dir, "vo_audio", name))
        print(f"  VO stem OK: {name}")

    # Copy VO_MANIFEST.json and edl.json and topic.json
    shutil.copy2(os.path.join(vo_src, "VO_MANIFEST.json"),
                 os.path.join(run_dir, "vo_audio", "VO_MANIFEST.json"))
    shutil.copy2(os.path.join(SEGMENT_V2, "edl.json"),
                 os.path.join(run_dir, "edl.json"))
    shutil.copy2(os.path.join(SEGMENT_V2, "topic.json"),
                 os.path.join(run_dir, "topic.json"))

    # Copy transcripts (needed by acoustic cutter)
    tx_src = os.path.join(SEGMENT_V2, "transcripts")
    for f in os.listdir(tx_src):
        shutil.copy2(os.path.join(tx_src, f), os.path.join(run_dir, "transcripts", f))

    print("  All inputs verified and linked.")


def run_cutter(run_dir):
    """Run acoustic cutter. Print cut table vs v2e. Return cuts dict."""
    from cut import compute_all_cuts
    compute_all_cuts(run_dir)

    with open(os.path.join(run_dir, "cuts_final.json")) as f:
        cuts = {c["clip_id"]: c for c in json.load(f)}

    print("\n  CUT TABLE (cutter vs v2e):")
    print(f"  {'clip':<10} {'cutter_in':>10} {'cutter_out':>11} {'v2e_out':>10} {'delta':>8}")
    for cid in ["hook", "clip_01", "clip_02", "clip_03"]:
        c = cuts.get(cid, {})
        v2e = V2E_CUTS.get(cid, {})
        v2e_out = v2e.get("cut_out", "—")
        delta = ""
        if isinstance(v2e_out, (int, float)):
            delta = f"{c.get('cut_out', 0) - v2e_out:+.3f}"
        print(f"  {cid:<10} {c.get('cut_in', 0):10.3f} {c.get('cut_out', 0):11.3f} "
              f"{str(v2e_out):>10} {delta:>8}")
    return cuts


def abort_check(cuts):
    """Orchestrator abort check. Returns (ok, messages)."""
    msgs = []
    c1 = cuts.get("clip_01", {})
    lo, hi = V2E_CUTS["clip_01"]["range"]
    if not (lo <= c1.get("cut_out", 0) <= hi):
        msgs.append(f"clip_01 cut_out={c1.get('cut_out')} outside [{lo}, {hi}]")

    for cid in ["clip_02", "clip_03"]:
        c = cuts.get(cid, {})
        v2e = V2E_CUTS[cid]
        if "cut_out" in v2e:
            delta = abs(c.get("cut_out", 0) - v2e["cut_out"])
            if delta > 0.005:
                msgs.append(f"{cid} cut_out delta={delta:.3f} > 0.005 "
                            f"(cutter={c.get('cut_out')}, v2e={v2e['cut_out']})")
        if "cut_in" in v2e:
            delta = abs(c.get("cut_in", 0) - v2e["cut_in"])
            if delta > 0.005:
                msgs.append(f"{cid} cut_in delta={delta:.3f} > 0.005 "
                            f"(cutter={c.get('cut_in')}, v2e={v2e['cut_in']})")
    return (len(msgs) == 0, msgs)


def run_pipeline(run_dir):
    """Run renderers + gates. Stops before telegram."""
    from types import SimpleNamespace
    args = SimpleNamespace(qa_version=None, output_name="segment.mp4",
                           voice_key=None, model=None)

    # Shoutout (needs edl.json only)
    from shoutout import build_shoutout
    print("\n=== SHOUTOUT ===")
    build_shoutout(run_dir, None, "16x9")
    build_shoutout(run_dir, None, "9x16")

    # Render 16:9
    print("\n=== RENDER 16:9 ===")
    from render16 import render_16x9
    render_16x9(run_dir, None, "segment.mp4")

    # Gates 16:9
    print("\n=== GATES 16:9 ===")
    from gates import run_gates
    from config import resolve_paths
    paths = resolve_paths(run_dir)
    final_16 = os.path.join(paths["out_dir"], "segment.mp4")
    manifest_16 = os.path.join(paths["qa_dir"], "concat_manifest_16x9.json")
    ok16, _ = run_gates(run_dir, final_16, manifest_16)
    if not ok16:
        print("** GATE FAILURE 16:9 — HARD STOP **")
        return False

    # Render 9:16
    print("\n=== RENDER 9:16 ===")
    from render_vertical import render_9x16
    render_9x16(run_dir, None, "segment_vertical.mp4")

    # Gates 9:16
    print("\n=== GATES 9:16 ===")
    final_9 = os.path.join(paths["out_dir"], "segment_vertical.mp4")
    manifest_9 = os.path.join(paths["qa_dir"], "concat_manifest_9x16.json")
    ok9, _ = run_gates(run_dir, final_9, manifest_9)
    if not ok9:
        print("** GATE FAILURE 9:16 — HARD STOP **")
        return False

    print("\n=== PIPELINE COMPLETE (stopped before telegram) ===")
    return True


def main():
    t0 = time.time()
    print("=== ISOLATED v2f RENDER ===\n")

    # 1. Create run dir
    run_dir = create_run_dir()
    print(f"Run dir: {run_dir}")

    # 2. Verify and link inputs
    print("\nVerifying inputs...")
    verify_and_link(run_dir)

    # 3. Acoustic cutter
    print("\nRunning acoustic cutter...")
    cuts = run_cutter(run_dir)

    # 4. Abort check
    ok, msgs = abort_check(cuts)
    if not ok:
        print("\n** ABORT CHECK FAILED **")
        for m in msgs:
            print(f"  - {m}")
        print("\nRun dir preserved for inspection:", run_dir)
        sys.exit(2)

    # 5. Render + gates
    success = run_pipeline(run_dir)

    elapsed = time.time() - t0
    print(f"\nTotal: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    if not success:
        sys.exit(1)
    print(f"\nOutput: {run_dir}/out/")


if __name__ == "__main__":
    main()
