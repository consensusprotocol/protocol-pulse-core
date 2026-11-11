# DEC-1 — response to the late Heimdall chunk on pipeline/run_fresh.py (2026-11-11 ET)

The run_fresh.py chunk of the DEC-1 Heimdall audit (deepseek, qwen27b, glm) finished after 9aa4fdb2 was
committed. Two majority findings. Measured, not argued.

## 1. [critical, deepseek+qwen27b] "G8's 16:9 source is the render itself -> ratio 1 -> vacuous pass" — REJECTED (premise false), residual gap recorded as OD-3

`qa/final_<clip>.mp4` is the PREPARED clip (run_isolated.prerender_clips: cut, lanczos scale/pad to
1920x1080, 24 fps CFR, NVENC QP 20), i.e. the renderer's INPUT. The gated 16:9 final is
`out/segment.mp4`. The same wiring was G8's approved relative reference before DEC-1
("prepared 1920x1080 clip (source camera, scaled)"); DEC-1 only fed it to the production gate.

Laplacian medians at G8's own five sample instants per clip (scratchpad g8m/measure.py, read-only):

| run | clip | original download | prepared | 16:9 final | prepared/original | final/prepared | final/original |
|---|---|---|---|---|---|---|---|
| Nov 10 | hook | 495.66 | 515.58 | 507.71 | 1.040 | 0.985 | 1.024 |
| Nov 10 | clip_01 | 34.87 | 34.33 | 35.71 | 0.985 | 1.040 | 1.024 |
| Nov 10 | clip_02 | 94.81 | 94.05 | 93.44 | 0.992 | 0.994 | 0.986 |
| v2f (approved) | hook | 35.80 | 27.22 | 27.56 | **0.760** | 1.013 | **0.770** |
| v2f (approved) | clip_01 | 179.73 | 178.45 | 171.87 | 0.993 | 0.963 | 0.956 |
| v2f (approved) | clip_02 | 385.86 | 268.40 | 265.74 | **0.696** | 0.990 | **0.689** |
| v2f (approved) | clip_03 | 97.08 | 91.18 | 89.39 | 0.939 | 0.980 | 0.921 |

- final/prepared is 0.963-1.040: not 1 by construction. The premise is false.
- The suggested fix (original download as the source) would fail the APPROVED reference on the
  unchanged 0.85 ratio (hook 0.770, clip_02 0.689). Making it pass would need a ratio calibrated down
  to 0.689: an acceptance change, which the standing rules reserve to DEC-1 (thresholds the reference
  fails as reported) — not taken.
- Residual gap, real: G8 measures the RENDER stage only. The prepare encode lowers Laplacian variance
  by up to 30 % on the approved reference (largely grain removal at NVENC QP 20; the approved look
  includes it). Prepare fidelity is ungated. Recorded as OD-3 for the orchestrator; no gate changed.

## 2. [high, deepseek+qwen27b] "G9 row adds `(identical or not fallback)` beyond the calibrated gate" — IMPLEMENTED (no acceptance change)

`identical` already contains `and not fallback`, so the term was `not fallback`: a tail measured on a
conform-fallback outro failed G9 even when it cleared the floor. Intentional (the floor is the locked
outro's tail), but hidden inside G9. Now:
- `G9_tail` = the calibrated gate alone (`_status(g9_pass)`),
- `outro_locked` = its own row, FAIL on a conform fallback (fail closed, the run still holds).
Same acceptance as 9aa4fdb2; the policy is visible. Test asked for by qwen27b:
`test_dec1_calibration.py::TestTailRows` (luma passes + fallback -> outro_locked FAIL -> HOLD).
