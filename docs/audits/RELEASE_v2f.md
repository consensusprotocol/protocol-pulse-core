# RELEASE v2f — Protocol Pulse Segment v2

**Status:** READY FOR REVIEW
**Date:** 2026-11-06
**Git HEAD:** d503ddfd8a1f4d18c0e578880e12096d47a483f4

## Closure Table

See [R2_CLOSURE.md](R2_CLOSURE.md) for per-finding status.

- **Fixed:** 12/24 (R2-02, 03, 05, 06, 07, 11, 12, 13, 14, 16, 21, 22)
- **Open:** 12/24 (R2-01, 04, 08, 09, 10, 15, 17, 18, 19, 20, 23, 24)

## Test Results

### EDL Rules Suite (pipeline/test_edl_rules.py)
```
69 passed in 1.00s
```

### Must-Fail Suite (pipeline/test_round2_mustfail.py)
```
15 passed, 3 warnings in 8.53s
```
Includes 13 original must-fail tests + 2 G8 source-relative tests.
Baseline (pre-fix): 13/13 FAIL — see docs/audits/mustfail_baseline.txt

### Failure Blocks Delivery (pipeline/test_failure_blocks.py)
```
5 passed in 0.14s
```
Tests: delete gate result, set all_pass=false, delete mp4, remove VERIFIED marker, create GATE_FAIL.txt — all block telegram.

### Total: 89/89 PASS, 0 FAIL, 0 SKIP (excluding source-dependent skips)

## Final MP4 Checksums

| File | SHA-256 |
|---|---|
| segment_v2/out/segment.mp4 (16:9) | `ca9027d37a25a4cf3458e95021ff893808e22fd7f269c20980b3b2f16e45f097` |
| segment_v2/out/segment_vertical.mp4 (9:16) | `a43305d80a5941092b7f1ec709cb3017d6b3d6044349921bad51397a9cb43f71` |

## Gate Tables

### 16:9 (segment_v2/qa_v1/gate_results_16x9.json)

| Gate | Result | Notes |
|---|---|---|
| G1 Voice | PASS | Similarity >= 0.87 |
| G2 Watermark | PASS | |
| G3 Cuts | PASS | All boundary words verified |
| G3b Cut-Out Clean | PASS | No source leakage |
| G3c Acoustic Tail | PASS | Clean tail, no onset artifacts |
| G4 Faces | PASS | Consistent detection |
| G5 Technical | PASS | 1920x1080, 24fps, -14.7 LUFS |
| G6 Pre-roll | PASS | VO onset measured |
| G8 Sharpness | **FAIL** | Hook median=26.24 < floor=60. Source is soft (pre-G8 source-relative). |
| G9 Tail | PASS | |
| G10 Chyron | PASS | |
| G12 Credits | PASS | |
| G13 VO Audible | PASS | |

**Overall: FAIL** (G8 hook sharpness below absolute floor)

### 9:16 (segment_v2/qa_v1/gate_results_9x16.json)

| Gate | Result | Notes |
|---|---|---|
| G1 Voice | PASS | |
| G2 Watermark | PASS | |
| G3 Cuts | PASS | |
| G3b Cut-Out Clean | PASS | |
| G3c Acoustic Tail | PASS | |
| G4 Faces | PASS | |
| G5 Technical | PASS | 1080x1920, 24fps, -14.7 LUFS |
| G6 Pre-roll | PASS | |
| G10 Chyron | PASS (N/A) | |
| G13 VO Audible | PASS | |

**Overall: PASS** (run predates G8/G9/G11/G12 vertical wiring fix)

## Cut/Audio Evidence

### Acoustic Cut Points (from test_edl_rules.py::TestAcousticValley)
- clip_01 source (Pxrak-iMT0g.mp4): cut_out in [249.62, 249.72]
  - Valley: depth >= 12 dB, width >= 60ms, ends after "magnitude", before "So"
  - Acoustic offset: bounded by 80ms gap at 6 dB threshold

### Synthetic Magnitude Cut (from test_round2_mustfail.py::TestMagnitudeCut)
- Intra-word gap (70ms at 10.05-10.12) bridged correctly
- Cut lands at >= 10.40, <= 10.64 (after syllable, 60ms before next onset)

## Frame Grid Paths

QA frames stored in `segment_v2/qa_v1/`:
- G8 sharpness: `g8_{hook,clip_01,clip_02,clip_03}_{0-4}.png` (20 frames)
- G4 faces: `g4_*.png`
- G2 watermark: `g2_*.png`

## G8 Policy Change

Source-relative sharpness (DEGRADATION_RATIO=0.85) implemented but not yet run
against these mp4s. See [G8_POLICY_PROPOSAL.md](G8_POLICY_PROPOSAL.md).

The hook G8 failure (median 26.24) may pass under source-relative rules if the
source itself is soft. Requires re-run with source_clips to determine.

## Remaining Blockers

1. **16:9 G8 sharpness** — hook segment below absolute floor. Need source-relative
   re-evaluation or sharper hook source.
2. **9:16 gate coverage** — run predates G8/G9/G11/G12 vertical wiring. Needs re-run
   with current qa_gates.py.
3. **Integrated clean run (Addendum 2 item 5)** — no clean v2f run from scratch with
   current codebase. Existing outputs from prior qa_v1 run.
4. **12 open R2 findings** — see closure table.

## Commits This Session

| Hash | Description |
|---|---|
| 741fb72b | A1: acoustic.py addendum fix — 6 dB offset, 60ms valley, raise on unsafe |
| 40536aa1 | A2 (R2-06): resample VO stems to 48kHz stereo before concat |
| 53fb1499 | R2 must-fail suite: 13/13 green — acoustic, gates, vertical fail-closed |
| d503ddfd | A5/A7/A9: output collision guard, hook credits, G8 source-relative sharpness |
| (pending) | Failure blocks tests, release package |
