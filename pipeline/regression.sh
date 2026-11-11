#!/bin/bash
# pipeline/regression.sh — Regression test suite for Pulse Check pipeline
# Runs: unit tests, v2d repro check, v2e verify
# Usage: bash pipeline/regression.sh 2>&1 | tee segment_v2/qa/regression_$(date +%Y%m%d_%H%M%S).txt

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== REGRESSION SUITE: $(date -Iseconds) ==="
echo ""

# ── Step 1: Unit tests ──
echo "--- STEP 1: UNIT TESTS ---"
python3 -m pytest pipeline/test_edl_rules.py -x -q
echo ""

# ── Step 2: Syntax checks ──
echo "--- STEP 2: SYNTAX CHECKS ---"
for f in pipeline/acoustic.py pipeline/config.py pipeline/edl_rules.py \
         pipeline/render16.py pipeline/render_vertical.py pipeline/run.py \
         pipeline/shoutout.py pipeline/signoff.py pipeline/telegram.py \
         pipeline/gates.py; do
    if [ -f "$f" ]; then
        python3 -m py_compile "$f" && echo "  $f: OK" || echo "  $f: FAIL"
    fi
done
echo ""

# ── Step 3: M19a valley rule on clip_01 source ──
echo "--- STEP 3: M19a VALLEY RULE ---"
python3 -c "
from pipeline.acoustic import compute_acoustic_cut_out
import json
source = 'segment_v2/sources/Pxrak-iMT0g.mp4'
import os
if os.path.exists(source):
    result = compute_acoustic_cut_out(source, whisper_word_end=249.3)
    print(json.dumps(result, indent=2))
    assert result['safe'], f'FAIL: boundary not safe: {result}'
    assert abs(result['cut_out'] - 249.64) < 0.05, f'FAIL: cut_out {result[\"cut_out\"]} not near 249.64'
    assert result['valley']['depth_db'] >= 12.0, f'FAIL: valley depth {result[\"valley\"][\"depth_db\"]} < 12'
    assert result['valley']['width_ms'] >= 40, f'FAIL: valley width {result[\"valley\"][\"width_ms\"]} < 40'
    print('M19a clip_01: PASS')
else:
    print('SKIP: clip_01 source not available')
"
echo ""

# ── Step 4: v2d repro check ──
echo "--- STEP 4: V2D REPRO CHECK ---"
V2D_16x9="segment_v2/qa_v1/final_clip_01_v2d_backup.mp4"
if [ -f "$V2D_16x9" ]; then
    DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V2D_16x9")
    echo "  v2d clip_01 backup: ${DUR}s (expected 11.250)"
    python3 -c "assert abs($DUR - 11.250) < 0.01, f'v2d clip_01 duration mismatch: $DUR'"
    echo "  v2d clip_01: PASS"
else
    echo "  SKIP: v2d backup not available"
fi
echo ""

# ── Step 5: v2e output verify ──
echo "--- STEP 5: V2E OUTPUT VERIFY ---"
for f in segment_v2/out/segment_v2e.mp4 segment_v2/out/segment_vertical_v2e.mp4; do
    if [ -f "$f" ]; then
        DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
        SIZE=$(stat -c%s "$f")
        MD5=$(md5sum "$f" | cut -d' ' -f1)
        echo "  $f: ${DUR}s, ${SIZE} bytes, md5=${MD5}"
    else
        echo "  MISSING: $f"
    fi
done

# Parity check
DUR16=$(ffprobe -v error -show_entries format=duration -of csv=p=0 segment_v2/out/segment_v2e.mp4 2>/dev/null || echo "0")
DUR9=$(ffprobe -v error -show_entries format=duration -of csv=p=0 segment_v2/out/segment_vertical_v2e.mp4 2>/dev/null || echo "0")
if [ "$DUR16" != "0" ] && [ "$DUR9" != "0" ]; then
    python3 -c "
d16, d9 = $DUR16, $DUR9
delta = abs(d16 - d9)
print(f'  Parity: {delta:.3f}s (threshold 0.25s) {\"PASS\" if delta < 0.25 else \"FAIL\"}')
"
fi
echo ""

# ── Step 6: second protected reference (law L-d) ──
echo "--- STEP 6: PROTECTED REFERENCE pulse_preview_2026-11-11 (selection + cut + layout must reproduce) ---"
set +e
python3 pipeline/check_preview_reference.py
PREVIEW_RC=$?
set -e
if [ "$PREVIEW_RC" -ne 0 ] && [ "$PREVIEW_RC" -ne 2 ]; then      # 2 = reference not on this machine (SKIP)
    echo "  FAIL: the PBX-approved preview's decisions changed (docs/references/REFERENCE_PULSE_PREVIEW_2026-11-11.md)"
    exit 1
fi
echo ""

echo "=== REGRESSION COMPLETE ==="
