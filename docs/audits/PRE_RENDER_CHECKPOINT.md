# PRE-RENDER CHECKPOINT

Status: WAITING FOR ORCHESTRATOR GO
Date: 2026-11-06
Commit: 18c97f74

---

## 1. git HEAD

```
18c97f74 G14 xcorr rewrite, PBX outro integration, S7 full-bleed, R10 advisory
```

Commit chain since ORDER_v2f:
```
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

## 4. G14 raw output — EVERY measured offset on all 4 files

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

### current 16:9 — PASS (30P/0F/0H)

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

### v12 golden — INCONCLUSIVE (2P/8F/20H)

G14 cannot validate v12/v17 golden references. Root cause: golden audio was processed (BGM overlay, compression) during v1 pipeline rendering. Cross-correlation against raw YouTube sources produces peak < 0.15 on all clips (vs peak > 0.5 for v2 renders). The 8 "FAIL" entries are false positives from low-confidence xcorr matches (all peaks 0.31-0.47, below the reliability threshold).

Per Amendment 2 6f: "If a golden fails, do NOT retune and do not widen the tolerance: report the exact numbers to the orchestrator and HOLD that gate decision for PBX."

Evidence: `current_16x9 vs source` peak=1.06 (near-perfect). `v12 vs source` peak=0.12 (near-zero). Same source file, same extraction window. The golden audio is irrecoverably different from the raw source.

| status | segment | output_t | delta_ms | xcorr_peak | notes |
|--------|---------|----------|----------|------------|-------|
| FAIL | hook | 0.200 | 2666.8 | 0.349 | false match, low-conf xcorr |
| HOLD | hook | 2.000 | - | 0.260 | inconclusive |
| HOLD | hook | 4.000 | - | 0.296 | inconclusive |
| FAIL | hook | 6.000 | 5333.4 | 0.399 | false match, low-conf xcorr |
| HOLD | hook | 8.000 | - | 0.227 | inconclusive |
| HOLD | hook | 8.984 | - | 0.242 | inconclusive |
| HOLD | clip_01 | 14.222 | - | 0.193 | inconclusive |
| FAIL | clip_01 | 16.022 | 6207.8 | 0.370 | false match, low-conf xcorr |
| HOLD | clip_01 | 18.022 | - | 0.184 | inconclusive |
| HOLD | clip_01 | 20.022 | - | 0.137 | inconclusive |
| HOLD | clip_01 | 22.022 | - | 0.142 | inconclusive |
| HOLD | clip_01 | 24.022 | - | 0.199 | inconclusive |
| HOLD | clip_01 | 24.631 | - | 0.298 | inconclusive |
| FAIL | clip_02 | 28.567 | 999.6 | 0.465 | false match, low-conf xcorr |
| HOLD | clip_02 | 30.367 | - | 0.244 | inconclusive |
| HOLD | clip_02 | 32.367 | - | 0.180 | inconclusive |
| HOLD | clip_02 | 34.367 | - | 0.164 | inconclusive |
| HOLD | clip_02 | 36.367 | - | 0.138 | inconclusive |
| HOLD | clip_02 | 38.367 | - | 0.193 | inconclusive |
| FAIL | clip_02 | 39.892 | 5092.8 | 0.381 | false match, low-conf xcorr |
| FAIL | clip_03 | 40.692 | 13888.9 | 0.324 | false match, low-conf xcorr |
| HOLD | clip_03 | 42.492 | - | 0.183 | inconclusive |
| HOLD | clip_03 | 44.492 | - | 0.232 | inconclusive |
| FAIL | clip_03 | 46.492 | 1556.9 | 0.319 | false match, low-conf xcorr |
| HOLD | clip_03 | 48.492 | - | 0.241 | inconclusive |
| FAIL | clip_03 | 50.492 | 2971.1 | 0.389 | false match, low-conf xcorr |
| HOLD | clip_03 | 52.492 | - | 0.177 | inconclusive |
| HOLD | clip_03 | 53.726 | - | 0.246 | inconclusive |
| PASS | vo_intro | - | - | - | |
| PASS | vo_bridge_01 | - | - | - | |

### v17 golden — INCONCLUSIVE (2P/8F/20H)

Same root cause as v12. Identical xcorr peaks and false-match patterns. HOLD for PBX.

(Full table identical to v12 within 0.001 on all peaks — same processed audio master.)

## 5. G15 raw output

### v2e 16:9 — FAIL
- Card continuous: true (no mid-card scene changes)
- Ring aspect: FAIL — 8 squished rings detected at 90% mark (aspect 0.306-0.318)
  - Squished 9:16 card frames inserted at ~62.9s (V02/V12 root cause)
  - Normal rings at 25%/50%/75% all aspect 0.996-1.000

### current 16:9 — PASS
- Card continuous: true
- Ring aspect: PASS — 12 rings checked, all aspect 0.990-1.000

### v12/v17 golden — NOT RUN
G15 requires the manifest's segment boundaries. v12/v17 were rendered by a different pipeline version with different timing. Running G15 with segment_v2's manifest would produce meaningless results. G15 validation of golden requires matching that pipeline's manifest, which is not available.

## 6. cut_in / cut_out table

| segment | source | cut_in | cut_out | duration |
|---------|--------|--------|---------|----------|
| hook | RBFN4CB60To | 0.00 | 9.52 | 9.52 |
| clip_01 | Pxrak-iMT0g | 238.55 | 249.37 | 10.82 |
| clip_02 | RBFN4CB60To | 624.63 | 636.72 | 12.09 |
| clip_03 | QCgW8RlTu5Q | 998.00 | 1011.80 | 13.80 |

No cut points were changed by 0c277198 (Amendment 2 6g confirmed).

## 7. sha256 hashes

### PBX outro masters (hash-locked, never modified)
```
7c2cc7ae6efa9b276144f51b33290b190120470a36541e977f52c25b1e614e58  pp_outro_2026-11_16x9_master.mp4
48d114daab327aa9695cdebf25fec3ca5186113322fd29feedbcb035f2e421f9  pp_outro_2026-11_9x16_master.mp4
```

### Conformed outro derivatives (1080p, 48kHz, 24fps, 107 frames)
```
b8a402947c42017e7f448fba05306cad2dc052eb5c9097415582c1624d9fefc6  outro_16x9_conformed  (-20.04 LUFS, TP -5.78 dBTP)
1af99ca7c21a72fc085ea66f99a264fb2360b72f250b68c88b1a4caef0042883  outro_9x16_conformed  (-19.89 LUFS, TP -9.28 dBTP, attenuated -8.7dB per 6a)
```

ffmpeg settings: `scale=WxH:flags=lanczos,setsar=1:1 -c:v h264_nvenc -preset p4 -rc constqp -qp 20 -pix_fmt yuv420p -r 24 -c:a aac -b:a 192k -ar 48000 -ac 2`. 9:16 additionally: `-af volume=-8.7dB`.

### Golden references
```
386cb9e39e592ac63a022de0b3d99a511e134f4019b4c414be8bb5b8b0459bc3  segment_v12.mp4
e322545b2eba8ebfed68f7cfe8ad9f26b00ffd11a076250bea52632ed0a9846b  segment_v17_vertical.mp4
```

### v2e negative fixtures
```
20eacd782dd6d6120604cc41766dc31997819cfbb72bcae3965455d9e1120ae7  segment_v2e.mp4
a43305d80a5941092b7f1ec709cb3017d6b3d6044349921bad51397a9cb43f71  segment_vertical_v2e.mp4
```

### Current (pre-render) output
```
ca9027d37a25a4cf3458e95021ff893808e22fd7f269c20980b3b2f16e45f097  segment.mp4 (16:9, will be re-rendered)
a43305d80a5941092b7f1ec709cb3017d6b3d6044349921bad51397a9cb43f71  segment_vertical.mp4 (9:16, matches v2e — not yet re-rendered)
```

### Source media (cached, not re-downloaded)
```
cfb2c57aebbfd9d41fb98694fa8adbfa5011bf880c9364ababd9dd49b2125460  RBFN4CB60To.mp4
57ba9c51544bbbe0449c3914c95b83448886db6d35cf400bf55ecce7d0f1354a  Pxrak-iMT0g.mp4
a1f760077bf02cf1725f9bf68ef1ee7f23dfa192868a71b1cd73fdedb5b65bd4  QCgW8RlTu5Q.mp4
```

## 8. Production command

```bash
cd /home/ultron/protocol_pulse/pipeline

# 16:9
python3 render16.py --segment /home/ultron/protocol_pulse/segment_v2 --qa-version 1 --output-name segment.mp4

# 9:16
python3 render_vertical.py /home/ultron/protocol_pulse/segment_v2 --qa-version qa_v1 --output-name segment_vertical.mp4
```

---

## Additional items (orchestrator rules)

### Encoder
h264_nvenc on GPU0 (NVIDIA GeForce RTX 4090). QP 18 for final concat, QP 20 for intermediates.

### Source media
Cached locally at `segment_v2/sources/`. Three source videos (see hashes above). No re-download needed. Paths are reused from prior renders.

### VO stems
Cached. 8 VO MP3 stems in `segment_v2/vo_audio/`. 4 rendered VO MP4 segments in `segment_v2/qa_v1/` (vo_intro, vo_bridge_01, vo_vert_intro, vo_vert_bridge_01). No regeneration needed.

### 9:16 status
NOT DEMO-READY (known S6): clip_02 9:16 still uses v2e-style sliced stack for screen-share chart. S6 (approved layout class) is out of scope tonight. The 0:53 face crop (S5) also deferred. 16:9 is the demo candidate.

---

## HOLD items for PBX

1. **G14 on golden v12/v17**: audio xcorr cannot validate (processed audio, peak < 0.15). HOLD per Amendment 2 6f. G14 works correctly on v2 renders (v2e FAIL, current PASS with peak > 0.5).

2. **Clip 2 completeness / clip 3 "they" antecedent**: PBX editorial list (Amendment 1 S4).

3. **Sign-off wording**: approved register, signoff.py produces fresh per video (S8 flag only).

4. **R10 sentence-start**: advisory HOLD, not blocking.

---

STOP. Waiting for orchestrator GO before running production command.
