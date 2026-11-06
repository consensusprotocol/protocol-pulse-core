# PRE-RENDER CHECKPOINT (v2, corrected)

Status: WAITING FOR ORCHESTRATOR GO
Date: 2026-11-06
Commit: 8224c070

---

## 1. git HEAD

```
8224c070 PRE_RENDER_CHECKPOINT.md: full gate output, hashes, STOP for GO
18c97f74 G14 xcorr rewrite, PBX outro integration, S7 full-bleed, R10 advisory
0c277198 S4: acoustic cut_in (M24), sentence-start rule R10, validate_edl updated
a2ca31dd S3: magnitude word verified complete, V2E_CLOSURE.md started
13b3319a S2+S1: aspect-isolated shoutout build dirs, G14 scene alignment, G15 credits gate
```

## 2. git status (pipeline-relevant only)

No uncommitted pipeline changes. Data files modified (not pipeline):
```
 M data/perception_layer.json
 M data/signals.json
 M data/sovereign_context/latest.json
 M video_pipeline_v3/cache/active_signal.json
```
These do not affect the render.

## 3. git diff (pipeline files vs last commit)

All pipeline changes are committed in 18c97f74. No pending diffs.

## C1: MAGNITUDE REGRESSION — ACOUSTIC CUTTER VERIFICATION

**CRITICAL**: `cuts_final.json` in segment_v2 contains stale v2e values (clip_01 cut_out=249.37). The acoustic cutter (M19a valley rule) computes different values. The cutter MUST run in the production pipeline before any render.

Acoustic cutter output (run against segment_v2/sources/ on 2026-11-06):

| segment | video_id | word_end | CUTTER cut_out | v2e cut_out | delta |
|---------|----------|----------|----------------|-------------|-------|
| hook | RBFN4CB60To | 9.02 | **9.130** | 9.520 | -0.390s |
| clip_01 | Pxrak-iMT0g | 249.30 | **249.670** | 249.370 | +0.300s |
| clip_02 | RBFN4CB60To | 636.22 | **636.780** | 636.720 | +0.060s |
| clip_03 | QCgW8RlTu5Q | 1011.74 | **1012.130** | 1011.800 | +0.330s |

clip_01: valley={centre: 249.64, end: 249.67, depth_db: 17.4, width_ms: 60}. cut_out = **249.670**, in required range [249.62, 249.72].

clip_02: delta +0.060s — cutter extends slightly past v2e value. No truncation concern (v2e was already verified in V2E_CLOSURE.md; the cutter refines the tail by 60ms).

clip_03: delta +0.330s — cutter finds a later valley. The v2e value (1011.80) was already verified to contain the full sentence. The cutter extends further into the silence after the final word. No truncation. If the cutter value moves significantly from this, STOP and report.

## C2: PRODUCTION COMMAND — run.py ASSESSMENT

**run.py cannot do a full isolated run from `--stage all`**. The legacy `stage_all` flow is: VO -> shoutout -> render16 -> gates16 -> render9 -> gates9. It does NOT include the `cut` stage (acoustic cutter). The `cut` stage only exists in keyword mode (`stage_keyword`), which also runs discover/rank/select stages that require API calls and are not appropriate here (sources and EDL already exist).

**What run.py cannot do from a fresh dir without new code:**
1. No `--stage cut` in the legacy mode dispatch table
2. `stage_all` assumes `cuts_final.json` already exists
3. No mechanism to symlink/copy source files into a fresh run dir
4. No sha256 check of reused VO audio stems before re-rendering plates

**Honest statement**: To run in an isolated `runs/v2f_<ts>/` dir with the acoustic cutter, I would need to either (a) add a `cut` stage to the legacy mode and add a `--stage cut,all` chain, or (b) write a short orchestration script that copies edl.json + sources into the fresh dir, runs `cut.py`, then calls `run.py --stage all`. Both require new code, which is out of scope per the SCOPE FREEZE.

**The orchestrator must decide**: either (a) allow me to write the orchestration glue (small, ~30 lines) in the next session, or (b) provide the production command to use.

## 4. G14 raw output — EVERY measured offset on all files

### v2e 16:9 — FAIL (24P/4F/2H)

| status | segment | output_t | delta_ms | xcorr_peak | frame_sim | notes |
|--------|---------|----------|----------|------------|-----------|-------|
| PASS | hook | 0.200 | 0.0 | 1.278 | 1.000 | |
| PASS | hook | 2.000 | 0.0 | 0.686 | 1.000 | |
| PASS | hook | 4.000 | 0.0 | 1.227 | 1.000 | |
| PASS | hook | 6.000 | 0.0 | 0.742 | 1.000 | |
| PASS | hook | 8.000 | 0.0 | 0.915 | 1.000 | |
| PASS | hook | 8.984 | 0.0 | 0.591 | 1.000 | |
| FAIL | clip_01 | 14.222 | 0.0 | 1.134 | 0.177 | audio OK, frame mismatch (v2e video lag) |
| FAIL | clip_01 | 16.022 | 0.0 | 0.547 | 0.175 | audio OK, frame mismatch (v2e video lag) |
| PASS | clip_01 | 18.022 | 0.0 | 1.147 | 0.931 | |
| PASS | clip_01 | 20.022 | 0.0 | 0.954 | 0.917 | |
| PASS | clip_01 | 22.022 | 0.0 | 1.287 | 0.944 | |
| PASS | clip_01 | 24.022 | 0.0 | 1.297 | 0.936 | |
| PASS | clip_01 | 24.631 | 0.0 | 0.553 | 0.354 | |
| FAIL | clip_02 | 28.567 | 0.0 | 1.245 | 0.107 | audio OK, frame mismatch (v2e video lag) |
| HOLD | clip_02 | 30.367 | - | 0.151 | - | inconclusive xcorr |
| PASS | clip_02 | 32.367 | 0.0 | 1.584 | 0.997 | |
| PASS | clip_02 | 34.367 | 0.0 | 1.268 | 0.997 | |
| PASS | clip_02 | 36.367 | 0.0 | 0.909 | 0.998 | |
| PASS | clip_02 | 38.367 | 0.0 | 1.081 | 0.994 | |
| HOLD | clip_02 | 39.892 | - | 0.231 | - | inconclusive xcorr |
| PASS | clip_03 | 40.692 | 0.0 | 0.594 | 0.988 | |
| PASS | clip_03 | 42.492 | 0.0 | 0.844 | 0.973 | |
| PASS | clip_03 | 44.492 | 0.0 | 0.726 | 0.989 | |
| PASS | clip_03 | 46.492 | 0.0 | 1.429 | 0.987 | |
| PASS | clip_03 | 48.492 | 0.0 | 0.985 | 0.991 | |
| PASS | clip_03 | 50.492 | 0.0 | 0.431 | 0.978 | |
| FAIL | clip_03 | 52.492 | 6385.3 | 0.325 | - | low-conf xcorr false match |
| PASS | clip_03 | 53.726 | 0.0 | 0.462 | 0.959 | |
| PASS | vo_intro | - | - | - | - | VO pre-roll declared |
| PASS | vo_bridge_01 | - | - | - | - | VO pre-roll declared |

v2e correctly caught: frame mismatch at 14.222, 16.022, 28.567 (3.5s video lag zone).

### C3: v2e 9:16 — FAIL (16P/14F/0H) — POSITIVE CONTROL

| status | segment | output_t | delta_ms | xcorr_peak | frame_sim | notes |
|--------|---------|----------|----------|------------|-----------|-------|
| PASS | hook | 0.200 | 0.0 | 1.278 | 0.532 | face-crop reduces sim vs 16:9 source |
| PASS | hook | 2.000 | 0.0 | 0.686 | 0.539 | |
| PASS | hook | 4.000 | 0.0 | 1.228 | 0.536 | |
| PASS | hook | 6.000 | 0.0 | 0.742 | 0.540 | |
| PASS | hook | 8.000 | 0.0 | 0.914 | 0.538 | |
| PASS | hook | 8.984 | 0.0 | 0.590 | 0.531 | |
| FAIL | clip_01 | 14.222 | 0.0 | 1.158 | 0.000 | audio OK, frame=black/wrong (v2e lag) |
| FAIL | clip_01 | 16.022 | 0.0 | 0.552 | 0.000 | audio OK, frame=black/wrong (v2e lag) |
| FAIL | clip_01 | 18.022 | 0.0 | 1.159 | 0.000 | audio OK, frame=0.000 |
| FAIL | clip_01 | 20.022 | 0.0 | 0.964 | 0.000 | audio OK, frame=0.000 |
| FAIL | clip_01 | 22.022 | 0.0 | 1.315 | 0.000 | audio OK, frame=0.000 |
| FAIL | clip_01 | 24.022 | 11.4 | 1.018 | 0.000 | audio OK, frame=0.000 |
| FAIL | clip_01 | 24.297 | 11.3 | 1.240 | 0.179 | audio OK, frame=0.179 |
| FAIL | clip_02 | 28.233 | 0.0 | 1.314 | 0.265 | audio OK, frame below 0.3 threshold |
| FAIL | clip_02 | 30.033 | 0.0 | 0.373 | 0.249 | |
| FAIL | clip_02 | 32.033 | 0.0 | 0.400 | 0.261 | |
| FAIL | clip_02 | 34.033 | 0.0 | 0.344 | 0.251 | |
| FAIL | clip_02 | 36.033 | 0.0 | 0.968 | 0.247 | |
| FAIL | clip_02 | 38.033 | 0.0 | 0.843 | 0.240 | |
| FAIL | clip_02 | 39.558 | 0.0 | 0.825 | 0.246 | |
| PASS | clip_03 | 40.358 | 0.0 | 1.093 | 0.365 | |
| PASS | clip_03 | 42.158 | 0.0 | 1.232 | 0.353 | |
| PASS | clip_03 | 44.158 | 0.0 | 0.698 | 0.365 | |
| PASS | clip_03 | 46.158 | 0.0 | 1.020 | 0.376 | |
| PASS | clip_03 | 48.158 | 0.0 | 0.967 | 0.374 | |
| PASS | clip_03 | 50.158 | 0.0 | 0.488 | 0.426 | |
| PASS | clip_03 | 52.158 | 0.0 | 0.847 | 0.421 | |
| PASS | clip_03 | 53.392 | 0.0 | 0.776 | 0.477 | |
| PASS | vo_intro | - | - | - | - | VO pre-roll declared |
| PASS | vo_bridge_01 | - | - | - | - | VO pre-roll declared |

**Analysis**: clip_01 FAIL at 14.222 (frame_sim=0.000 — v2e bug: wrong frame rendered). clip_02 FAIL at 28.233 (frame_sim=0.265 — 9:16 face-crop layout diverges from 16:9 source below 0.3 threshold). Audio delta 0.0ms throughout: audio playhead is correct even where the picture is wrong.

The 14.00 and 28.04 join points do NOT "pass by comparing the rendered picture with the source frame at the final audio playhead" — they FAIL with frame_sim 0.000 and 0.265 respectively, confirming v2e's video lag defect.

### "current" 16:9 — PASS (30P/0F/0H) — measured on sha ca9027d3

**C4(c) caveat**: This result was measured on the pre-v2f segment.mp4 (sha `ca9027d3`), not on v2f output. The v2f render has not happened yet. This table validates that G14 works correctly on the current pipeline's output but is NOT a measurement of the v2f render.

| status | segment | output_t | delta_ms | xcorr_peak | frame_sim |
|--------|---------|----------|----------|------------|-----------|
| PASS | hook | 0.200 | 0.0 | 1.278 | 1.000 |
| PASS | hook | 2.000 | 0.0 | 0.686 | 1.000 |
| PASS | hook | 4.000 | 0.0 | 1.227 | 1.000 |
| PASS | hook | 6.000 | 0.0 | 0.742 | 1.000 |
| PASS | hook | 8.000 | 0.0 | 0.915 | 1.000 |
| PASS | hook | 8.984 | 0.0 | 0.590 | 1.000 |
| PASS | clip_01 | 14.222 | 0.0 | 1.136 | 0.991 |
| PASS | clip_01 | 16.022 | 0.0 | 0.546 | 0.964 |
| PASS | clip_01 | 18.022 | 0.0 | 1.149 | 0.957 |
| PASS | clip_01 | 20.022 | 0.0 | 0.955 | 0.977 |
| PASS | clip_01 | 22.022 | 0.0 | 1.287 | 0.967 |
| PASS | clip_01 | 24.022 | 0.0 | 1.300 | 0.981 |
| PASS | clip_01 | 24.631 | 0.0 | 0.974 | 0.985 |
| PASS | clip_02 | 28.567 | 0.0 | 1.235 | 0.998 |
| PASS | clip_02 | 30.367 | 0.0 | 0.413 | 0.998 |
| PASS | clip_02 | 32.367 | 0.0 | 0.361 | 0.998 |
| PASS | clip_02 | 34.367 | 0.0 | 0.365 | 0.994 |
| PASS | clip_02 | 36.367 | 0.0 | 0.949 | 0.998 |
| PASS | clip_02 | 38.367 | 0.0 | 1.005 | 0.998 |
| PASS | clip_02 | 39.892 | 0.0 | 0.949 | 0.997 |
| PASS | clip_03 | 40.692 | 0.0 | 1.105 | 0.998 |
| PASS | clip_03 | 42.492 | 0.0 | 1.242 | 0.996 |
| PASS | clip_03 | 44.492 | 0.0 | 0.684 | 0.996 |
| PASS | clip_03 | 46.492 | 0.0 | 0.950 | 0.987 |
| PASS | clip_03 | 48.492 | 0.0 | 0.979 | 0.998 |
| PASS | clip_03 | 50.492 | 0.0 | 0.510 | 0.993 |
| PASS | clip_03 | 52.492 | 0.0 | 0.906 | 0.992 |
| PASS | clip_03 | 53.726 | 0.0 | 0.781 | 0.980 |
| PASS | vo_intro | - | - | - | - |
| PASS | vo_bridge_01 | - | - | - | - |

### v12/v17 golden — UNSCORED (C5: accepted by PBX)

G14 cannot validate golden references (processed audio, peak < 0.15). Accepted as unscored tonight per orchestrator C5.

## 5. G15 raw output

### v2e 16:9 — FAIL
- Card continuous: true (no mid-card scene changes)
- Ring aspect: FAIL — 8 squished rings detected at 90% mark (aspect 0.306-0.318)

### current 16:9 — PASS
- Card continuous: true
- Ring aspect: PASS — 12 rings checked, all aspect 0.990-1.000

## 6. cut_in / cut_out table

**WARNING (C1)**: The values below are from `cuts_final.json` which contains STALE v2e values. The acoustic cutter produces different (correct) values. The cutter MUST run in the production pipeline. See C1 section above for cutter output.

| segment | source | v2e cut_in | v2e cut_out | CUTTER cut_out | required range |
|---------|--------|------------|-------------|----------------|----------------|
| hook | RBFN4CB60To | 0.000 | 9.520 | 9.130 | — |
| clip_01 | Pxrak-iMT0g | 238.550 | 249.370 | **249.670** | [249.62, 249.72] IN RANGE |
| clip_02 | RBFN4CB60To | 624.630 | 636.720 | 636.780 | — (no truncation) |
| clip_03 | QCgW8RlTu5Q | 998.000 | 1011.800 | 1012.130 | — (no truncation) |

## 7. sha256 hashes

### PBX outro masters (hash-locked)
```
7c2cc7ae6efa9b276144f51b33290b190120470a36541e977f52c25b1e614e58  pp_outro_2026-11_16x9_master.mp4
48d114daab327aa9695cdebf25fec3ca5186113322fd29feedbcb035f2e421f9  pp_outro_2026-11_9x16_master.mp4
```

### Conformed outro derivatives (1080p, 48kHz, 24fps, 107 frames)
```
b8a402947c42017e7f448fba05306cad2dc052eb5c9097415582c1624d9fefc6  outro_16x9_conformed  (-20.04 LUFS)
1af99ca7c21a72fc085ea66f99a264fb2360b72f250b68c88b1a4caef0042883  outro_9x16_conformed  (-19.89 LUFS, attenuated -8.7dB per 6a)
```

### v2e negative fixtures
```
20eacd782dd6d6120604cc41766dc31997819cfbb72bcae3965455d9e1120ae7  segment_v2e.mp4
a43305d80a5941092b7f1ec709cb3017d6b3d6044349921bad51397a9cb43f71  segment_vertical_v2e.mp4
```

### Source media (reusable, hashes verified)
```
cfb2c57aebbfd9d41fb98694fa8adbfa5011bf880c9364ababd9dd49b2125460  RBFN4CB60To.mp4
57ba9c51544bbbe0449c3914c95b83448886db6d35cf400bf55ecce7d0f1354a  Pxrak-iMT0g.mp4
a1f760077bf02cf1725f9bf68ef1ee7f23dfa192868a71b1cd73fdedb5b65bd4  QCgW8RlTu5Q.mp4
```

### Pre-v2f output (will be replaced by v2f render)
```
ca9027d37a25a4cf3458e95021ff893808e22fd7f269c20980b3b2f16e45f097  segment.mp4 (pre-v2f 16:9)
a43305d80a5941092b7f1ec709cb3017d6b3d6044349921bad51397a9cb43f71  segment_vertical.mp4 (matches v2e — NOT re-rendered)
```

## 8. Production command

**BLOCKED on C2.** run.py `--stage all` cannot run the acoustic cutter or set up an isolated run dir without new code. The orchestrator must decide the approach. See C2 section above.

---

## C4: HONEST LIMITS OF G14

### (a) Static talking-head blind spot
v2e 16:9 PASSED G14 at t=18.022-24.022 (frame_sim 0.917-0.944) despite the video being ~3.5s behind the audio at those points. Root cause: the guest is a static talking head — the frame at t=18.022 (showing what should be t~14.5) looks similar to the frame at source t=242.551 because the guest barely moves. The frame similarity test (threshold **0.3**) cannot detect a temporal slip when the visual content is near-static. It only catches slips when the frame changes significantly (e.g., at 14.222 where frame_sim drops to 0.177 because the preceding VO plate is visually different from the clip).

Note: t=24.631 passed at frame_sim=**0.354** — barely above the 0.3 threshold. This is at the tail of clip_01 where the guest's posture shifts slightly.

### (b) VO rows auto-PASS
G14 declares VO segments as "pre-roll declared" and auto-PASSes them. It does NOT verify that the bridge VO plate shows the correct blur plate (rather than the previous guest's face). The orchestrator verifies VO plate correctness by visual inspection and listening on the output.

### (c) "current 16:9 PASS" is pre-v2f
The "current 16:9 PASS (30P/0F/0H)" was measured on `segment.mp4` sha `ca9027d3`, which is the pre-v2f render. It is NOT a measurement of the v2f output. The v2f render has not happened yet. G14 must be re-run on the v2f output after rendering.

---

## C5: v12/v17 UNSCORED

v12/v17 golden audio was processed by the v1 pipeline (BGM overlay, compression). Cross-correlation against raw YouTube sources produces peak < 0.15 (vs > 0.5 for v2 renders). Accepted as unscored tonight per orchestrator.

---

## HOLD items for PBX

1. **G14 on v2f output**: must be re-run after render (C4c).
2. **Clip 2 completeness / clip 3 "they" antecedent**: PBX editorial list.
3. **R10 sentence-start**: advisory HOLD, not blocking.
4. **C2 production command**: requires orchestrator decision on isolated run dir approach.

---

STOP. Waiting for orchestrator GO.
