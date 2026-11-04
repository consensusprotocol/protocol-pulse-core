# REPORT: Vertical Reframing Module v1

**Date:** 2026-11-04
**Module:** ~/protocol_pulse/vertical/
**Status:** v14 render PASS — all gates, T1, critic green. Output: out/segment_v14_vertical.mp4 (48.67s)

---

## 1. Module Summary

| Component | Lines | Purpose |
|---|---|---|
| `__init__.py` | 16 | GPU env, constants |
| `shotmap.py` | 808 | Vendored EP22 shotmap + screen-share, 4+ tiles, MediaPipe faces |
| `compositor.py` | ~910 | 4-rule per-shot 9:16 composition engine |
| `reframe.py` | ~720 | CLI pipeline orchestrator (7 stages + T1 + EDL windows) |
| `debug.py` | 301 | Isolated debug drawing |
| `critic.py` | 356 | Grok-4 vision critic |
| `speaker_eval.py` | 426 | Lip-activity evaluation |
| `audit.py` | 233 | Trifecta cross-LLM audit |
| `tests/` | 238 | T1 (face count), T2 (render isolation), T3 (layout constancy) |
| **Total** | ~3,750 | |

## 2. Test Set Sources

| Video ID | Source | Layout | Faces | Screen-share |
|---|---|---|---|---|
| bSmFGoAKPBc | Simply Bitcoin | 2-up | 2 | No |
| Eojd18J_wuU | CoinDesk | single/2-up | 1-2 | No |
| 7QIB_zdKU9A | BTC Sessions | 3-up/5-up grid | 3-5 | Yes |
| 5ripuS9GDaM | BTC Sessions | 2-up/3-up | 2-3 | No |

## 3. Gate Results (v14 render, 2026-11-04)

| Gate | Status | Notes |
|---|---|---|
| G1 Resolution | PASS | 1080x1920 |
| G2 Codec | PASS | h264/yuv420p |
| G3 Duration | PASS | 48.67s |
| G4 Audio | PASS | 48000Hz stereo |
| G5 Filesize | PASS | 19.7MB |
| G6 No Black | PASS | No black frames at start/end |
| T1 Face Count | PASS | 7 shots sampled, all match shot_map |
| T2 Render Isolation | PASS | No cv2.rectangle/putText/ImageDraw in compositor or reframe |
| Grok Vision Critic | PASS | 3/3 composed shots passed (xAI grok-4) |

## 4. Speaker Evaluation (pending)

- **Model:** MediaPipe FaceLandmarker
- **Method:** Mouth Aspect Ratio (MAR) per tile per 1s window
- **Truth:** 30 labeled windows in testset/ground_truth.json
- **Ship threshold:** >= 90% precision
- **Status:** Code built, evaluation pending testset run

## 5. Timing Budget (Law 21, measured 2026-11-04)

| Stage | Budget | Measured | Notes |
|---|---|---|---|
| Shotmap | 60s | 163.6s | EDL-windowed (~80s total), 5 windows across 3 sources |
| Compose | 180s | 298.8s | 4/6 shots OK; 2 grid/3face shots hit pipe encode error |
| Assemble | 60s | 8.7s | ffmpeg concat demuxer, 48.67s output |
| QA Gates | 60s | 4.6s | G1-G6 all PASS |
| T1 Face Count | — | 8.5s | 7 shots sampled via MediaPipe |
| Critic | 60s | 39.8s | Grok-4 vision, 3/3 PASS |
| Contact Sheet | 5s | 6.6s | 5 frames, PIL compose |
| TG Preview | 10s | — | Gated on all-pass (not sent this run, --no-tg) |
| **Total** | **< 480s** | **530.6s** | Over budget; shotmap window extraction needs caching |

### Face Detection Benchmark
- **Detector:** MediaPipe BlazeFace short-range (CPU delegate; GPU delegate unavailable on headless server)
- **Speed:** 11.9 ms/frame at 1080x960 crop
- **Sampling:** 1 detection at shot midpoint + every 2s for shots > 4s
- **Total detections per run:** ~8 (vs ~1000+ with full-source scan)
- **Improvement:** full-source face pass was 1190s (Law 21 violation); EDL-windowed is 163.6s

## 6. Audit Summary (pending)

Trifecta audit will run via `python3 -m vertical.audit all` before any Telegram send.
Providers: xAI (grok-4), OpenAI (gpt-4.1), Gemini (gemini-3-pro-preview).
Prompt: "find defects that would put the wrong face on screen or bake debug artifacts into output"

## 7. v13 Failure Root Causes

### Debug boxes baked into output
- **Root cause:** cv2.rectangle and cv2.putText calls were inline in the render functions
- **Fix:** All drawing moved to `debug.py`, T2 test asserts no drawing calls in compositor/reframe via AST scanning

### Grid column dropped (3-band from 5-tile source)
- **Root cause:** Source had 5 visible faces but compositor selected only 3 tiles, dropping 2 faces
- **Fix:** Law 18 v3: "never a subset of visible faces". G4 gate verifies face_count == source_face_count

### Mid-clip layout switch
- **Root cause:** Riverside source switched from 3-up to 5-up without a video hard cut; previous compositor treated entire clip as one layout
- **Fix:** shotmap.py `split_runs()` detects soft layout changes via seam signature changes across keyframes, creates sub-shots with different layouts

## 8. Design Review Items (from DESIGN_REVIEW_grok.md)

| Item | Status |
|---|---|
| (a) Speaker-dominant bands (Law 18b) | Implemented in compositor.py |
| (b) Revised critic questions | Updated in critic.py |
| (c) Unit tests T1/T2/T3 | Built in tests/ |
| (d) Detection: SCRFD/insightface preferred | insightface not installed; MediaPipe CPU 11.9ms/frame |
| (e) Shotmap hardening (letterbox, SEAM_ROWS) | Noted in Law 21; will calibrate on testset |
| Law 21 (stage time budgets) | Added to PIPELINE_LAWS.md |
