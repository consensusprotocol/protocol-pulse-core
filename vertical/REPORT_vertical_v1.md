# REPORT: Vertical Reframing Module v1

**Date:** 2026-11-04
**Module:** ~/protocol_pulse/vertical/
**Status:** Built, T2 isolation tests PASS, awaiting offline render test

---

## 1. Module Summary

| Component | Lines | Purpose |
|---|---|---|
| `__init__.py` | 16 | GPU env, constants |
| `shotmap.py` | 808 | Vendored EP22 shotmap + screen-share, 4+ tiles, MediaPipe faces |
| `compositor.py` | ~910 | 4-rule per-shot 9:16 composition engine |
| `reframe.py` | 470 | CLI pipeline orchestrator (7 stages) |
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

## 3. Gate Results (pending render)

| Gate | Status | Notes |
|---|---|---|
| T2 Render Isolation | PASS | No cv2.rectangle/putText/ImageDraw in compositor or reframe |
| T3 Layout Constancy | SKIP | Requires shot_map.json from shotmap run |
| T1 Face Count | SKIP | Requires rendered output |
| G1-G6 QA Gates | PENDING | Will run after first render |
| Grok Vision Critic | PENDING | Will run after first render |

## 4. Speaker Evaluation (pending)

- **Model:** MediaPipe FaceLandmarker
- **Method:** Mouth Aspect Ratio (MAR) per tile per 1s window
- **Truth:** 30 labeled windows in testset/ground_truth.json
- **Ship threshold:** >= 90% precision
- **Status:** Code built, evaluation pending testset run

## 5. Timing Budget (Law 21, pending measurement)

| Stage | Budget | Measured |
|---|---|---|
| Shotmap | 60s | TBD |
| Compose | 180s | TBD |
| Assemble | 60s | TBD |
| QA Gates | 60s | TBD |
| Critic | 60s | TBD |
| Contact Sheet | 5s | TBD |
| TG Preview | 10s | TBD |
| **Total** | **< 480s** | **TBD** |

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
| (d) Detection: SCRFD/insightface preferred | Noted; MediaPipe as fallback; both use GPU |
| (e) Shotmap hardening (letterbox, SEAM_ROWS) | Noted in Law 21; will calibrate on testset |
| Law 21 (stage time budgets) | Added to PIPELINE_LAWS.md |
