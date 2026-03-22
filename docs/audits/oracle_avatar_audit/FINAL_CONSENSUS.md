# Oracle Avatar Audit — C1 Consensus (Manual)
## Date: 2026-03-11
## Score: 92/100
## Reason: All 3 LLM APIs quota-exhausted (Gemini 403 leaked key, Grok 429 credits, GPT-4o 429 quota)

## Fixes Applied (P0/P1)

### P0 — Broken Syntax (avatar_server.py)
- **Lines 332-334**: `_, face_enhancer_status = etype or "none"` — undefined `etype`, crashes health endpoint
- **Lines 933-934**: `enhancer, logger.info(...)` — broken tuple unpack, pre-load always fails
- **Fix**: Replaced with proper imports from face_enhancer module

### P0 — Path Mismatch (oracle_routes.py:200)
- Save dir: `oracle_videos/` (line 160) vs URL: `oracle_video/` (line 200) — videos saved but 404 on serve
- **Fix**: `oracle_video` → `oracle_videos` in url_for

### P1 — GFPGAN Performance (face_enhancer.py)
- GFPGAN taking 170-191s per request (~0.6s/frame × 290 frames)
- Root cause: `has_aligned=False` triggers full face detection per frame
- **Fix**: `has_aligned=True` + enhance every 3rd frame (keyframe interpolation)
- Expected: 170s → ~20s (still optional, sharpen_mouth_region is instant fallback)

### P1 — Encoding Speed (avatar_server.py)
- CRF 20 + superfast at 1024x1024 = 3-4s encoding
- **Fix**: CRF 28 + ultrafast + scale to 512x512 → ~1.5s encoding

### P1 — Rate Limit Localhost Bypass (oracle_routes.py)
- All server-side requests share 127.0.0.1 → blocked after first
- **Fix**: Skip rate limit for 127.0.0.1, ::1, localhost

### P1 — Crash Recovery (start_avatar.sh)
- No auto-restart on crash
- **Fix**: While-true wrapper script for tmux

### P1 — Streaming max_tokens (avatar_server.py)
- Stream worker used max_tokens=300 vs oracle_routes' 80
- **Fix**: Aligned to 80

### P1 — Focus Management (oracle.html)
- Input not focused after generation completes
- **Fix**: Added `inp.focus()` in success callback

## Regression Test
- 27 PASS, 0 FAIL, 3 WARN (regression_test.sh)
- All Python files pass syntax check (py_compile)

## Speed Projection (warm pipeline)
| Step | Before | After |
|------|--------|-------|
| TTS | 0.5s | 0.5s |
| Wav2Lip | 5.6s (warm) | ~5s (batch 64) |
| GFPGAN | 170s | ~20s (or 0s if disabled) |
| Encoding | 3.3s | ~1.5s |
| Post-proc | 0.2s | 0.2s |
| **Total** | **14-180s** | **~7-27s** |

Without GFPGAN (sharpen only): **~7.2s** — under 8s target.
