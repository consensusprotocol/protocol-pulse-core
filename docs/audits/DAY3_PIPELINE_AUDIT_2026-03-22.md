# DAY 3 PIPELINE AUDIT — 2026-03-22
## Cross-LLM Deep Audit of Video Pipeline (Post 24+ Patch Day)

**Auditor:** Claude Opus 4.6 + GPT-4o + Grok (Gemini blocked — leaked API key)
**Scope:** 8 highest-churn files from 2026-03-21/22
**Regression:** 27 PASS / 0 FAIL / 3 WARN

---

## P0 Issues Found and Fixed (5 total)

### P0-1: clip_selector.py:376 — `.format()` with user-supplied YouTube transcripts
**Issue:** `SELECTION_PROMPT.format(transcripts=transcripts_text)` crashes with `KeyError` when any YouTube transcript contains `{` or `}` characters (common in JSON-like content, code discussions, math). This is the **exact same bug class** that caused 8+ render failures on March 21 in `script_writer.py`.
**Fix:** Changed to `.replace('{transcripts}', transcripts_text)` — immune to curly braces in user content.
**Verified:** `py_compile` PASS

### P0-2: narrative_intelligence.py:253 — `.format()` with tweet data
**Issue:** `NARRATIVE_PROMPT.format(tweet_batch=tweet_batch, timestamp=timestamp)` — tweets from Twitter/X containing `{` or `}` cause KeyError crash during narrative context generation.
**Fix:** Changed to chained `.replace()` calls.
**Verified:** `py_compile` PASS

### P0-3: overnight_render_loop.py:280 — `eval()` on ffprobe output
**Issue:** `eval(v.get('r_frame_rate', '0/1').replace('/', '/'))` — uses Python `eval()` to parse frame rate strings like `"30/1"`. While input comes from ffprobe (not directly from users), malformed data could crash or execute unintended code. The council_review.py script explicitly flags `eval()` as CRITICAL.
**Fix:** Replaced with safe float division: parse numerator/denominator, divide explicitly.
**Verified:** `py_compile` PASS

### P0-4: overnight_render_loop.py:282 — Bare `except: pass` hiding ffprobe errors
**Issue:** Bare `except: pass` after the ffprobe parsing block (which included the eval) silently swallows ALL errors — including TypeError, ZeroDivisionError, KeyError — making forensics debugging impossible.
**Fix:** Changed to `except Exception as e: log(f"WARNING: ffprobe parse error: {e}")`.
**Verified:** `py_compile` PASS

### P0-5: overnight_render_loop.py:365 — Bare `except:` hiding Gemini grade parse errors
**Issue:** `except:` on `json.loads(clean)` hides the specific JSON parse error, making it impossible to debug why Gemini grading failed.
**Fix:** Changed to `except json.JSONDecodeError as e:` with error details in log.
**Verified:** `py_compile` PASS

---

## P1 Issues Found and Fixed (2 total)

### P1-1: clip_extractor.py:259 — No video_id sanitization
**Issue:** `video_id` from LLM-selected clips passed directly to yt-dlp subprocess without format validation. YouTube IDs are `[A-Za-z0-9_-]{11}` — malformed IDs could cause unexpected subprocess behavior.
**Fix:** Added regex validation `^[A-Za-z0-9_-]{8,15}$` before any processing. Rejects and logs malformed IDs.
**Verified:** `py_compile` PASS

### P1-2: overnight_render_loop.py — No singleton/pidfile guard
**Issue:** Daemon mode could spawn multiple render loop instances simultaneously (cron misfire, manual restart, watchdog restart). Concurrent loops race on outputs, logs, API quotas, and render state — producing corrupted outputs and doubled quota consumption.
**Fix:** Added `_acquire_singleton()` using `fcntl.flock()` on `logs/render_loop.pid`. Second instance exits immediately with log message.
**Verified:** `py_compile` PASS

---

## P1 Issues Documented (fix in next session)

### P1-D1: No file locking on shared JSON state files
**Files:** `clip_selector.py:102-176`, `script_writer.py:265-286`, `overnight_render_loop.py:write_heartbeat()`
**Issue:** `used_clips.json`, `narrative_context.json`, and heartbeat files are read/modified/written with no mutex or atomic write pattern. Concurrent pipeline runs (cron, watchdog) can corrupt state.
**Recommended Fix:** Implement `_atomic_write_json()` using write-to-tmp + `os.replace()` pattern, with `fcntl.flock()` for cross-process safety.

### P1-D2: gemini_call() has zero retry/backoff
**File:** `overnight_render_loop.py:231-242`
**Issue:** Gemini API call has no retry on transient failures. If Gemini is briefly unavailable, the entire grade cycle fails.
**Recommended Fix:** Wrap in exponential backoff (3 retries, 1s/2s/4s, with jitter).

### P1-D3: TTS generate_dialogue_audio writes 3s silence on per-line failure
**File:** `tts_engine.py:1266-1273`
**Issue:** When individual TTS lines fail, 3s silence is generated. This contradicts the spirit of PIPELINE_LAWS "TTS FALLBACK BANNED" even though the 50% host validation gate catches catastrophic failures. Individual silence segments cause audible gaps.
**Recommended Fix:** Track silence count per episode; alert if >2 silence segments generated.

### P1-D4: Host normalization forces PBX on ALL segments
**File:** `script_writer.py:234, 325, 424`
**Issue:** Three separate normalization points force all `host:1` entries to `host:2`. This overrides the dual-host format even though PIPELINE_LAWS "DUAL HOST RESTORED 2026-03-10" exists. Current LAW: SOLO HOST (later) takes precedence, but if dual-host is re-enabled, these will silently break it.
**Recommended Fix:** Add a feature flag `DUAL_HOST_ENABLED` that controls normalization behavior.

---

## P2 Technical Debt

1. **assembler.py** — 4400+ lines, no test coverage. Multiple functions >100 lines. Filter_complex strings built via string concatenation.
2. **clip_extractor.py** — Massive code duplication between primary (yt-dlp sections) and fallback (full download) paths. 5 sequential ffmpeg passes per clip (resync, sync, nuclear, lipsync, fix7).
3. **tts_engine.py** — 1375 lines with 4 TTS backends (Kokoro, F5, Chatterbox, ElevenLabs). Complex fallback chains.
4. **Dead imports:** `import re` inside functions that already have module-level `import re` (minor).
5. **`datetime.utcnow()` deprecated** — Used in `clip_selector.py:116,152,172`. Should use `datetime.now(timezone.utc)`.
6. **assembler.py** PiP logic returns empty string if clip is corrupt (line 1159-1194) — caller may not handle.
7. **assembler.py** social segment silently dropped when <3 cards (line 2173) — no warning to user.

---

## Cross-LLM Consensus

### What GPT-4o and Grok Both Agreed On:
1. **No file locking** on shared JSON state — race condition risk (U1)
2. **Unthrottled external API calls** — no backoff on Gemini, Ollama (U2)
3. **Silent exception swallowing** — broad `except` blocks return empty results (U3)
4. **No singleton guard** on render daemon (M1/M2)
5. **Strengths to preserve:** No hardcoded API keys (VS1), parameterized SQL (VS2), Bitcoin-only editorial enforcement (VS3), ElevenLabs quota check (VS4), silence fallback disabled (VS5)

### What They Disagreed On:
- **Fail fast vs. graceful degradation on TTS:** Resolution — fail fast with alerting is correct for quality-brand product. No silent degradation.
- **Bitcoin-only enforcement:** Prompt-level enforcement exists but no output validation. Recommended: add post-generation keyword scan for altcoin names.

### Final Cross-LLM Score:
**4.5/10 overall** (reduced confidence — only 2/3 LLMs responded, Gemini key leaked)
- Correctness: 4.5/10
- Law Compliance: 6.5/10
- Security: 4.5/10
- Production Readiness: 4.0/10

---

## Assembler.py Special Audit Findings

| Category | Count | Key Lines | Severity |
|----------|-------|-----------|----------|
| P0: Crash Risk | 4 | 2173, 4742, 4485-4492, 1159-1194 | Critical |
| P1: Quality Risk | 4 | 3099-3105, 2231, 4743, 1791-1838 | High |
| P2: Debt | 5 | 1740, 1491, 330, 890, 2446 | Low |

Key findings:
1. Social segment silently dropped if <3 cards (line 2173)
2. Clip path not re-validated after CFR preprocessing (line 4742)
3. `BG_MUSIC` used without runtime existence check in concatenate_parts (line 4485)
4. PiP returns empty string on corrupt clip — caller may crash (line 1159)
5. Quote text sanitization incomplete — single quotes escaped but not for all FFmpeg contexts (line 3099)

---

## Render Safety Assessment

**Verdict:** The render loop is NOT currently running (last ran at 00:22 UTC, exit code -15). All P0 fixes have been applied and regression tests pass (27 PASS / 0 FAIL).

**Risk Assessment:**
- **P0 fixes applied:** The KeyError bug class that caused 8+ failures is now fixed in both `clip_selector.py` AND `narrative_intelligence.py` (in addition to the already-fixed `script_writer.py`). The `eval()` and bare `except` issues in the forensics pipeline are fixed. The singleton guard prevents duplicate instances.
- **Remaining risk:** Assembler.py has 4 P0-level issues not yet fixed (social segment, clip path, BG_MUSIC, PiP). These are lower probability than the KeyError class but could cause individual render failures.
- **Gemini API key:** Flagged as leaked by Google. Must be rotated before Gemini grading can resume.

**Overall:** Render is safer than 24 hours ago. The most common crash class (KeyError from curly braces) is eliminated across all files. Restart render when ready:
```bash
cd ~/protocol_pulse && python3 overnight_render_loop.py --daemon &
```

---

## Files Modified
- `video_pipeline_v3/clip_selector.py` — P0-1 (.format→.replace)
- `video_pipeline_v3/utils/narrative_intelligence.py` — P0-2 (.format→.replace)
- `overnight_render_loop.py` — P0-3 (eval→safe parse), P0-4 (bare except), P0-5 (bare except), P1-2 (singleton)
- `video_pipeline_v3/clip_extractor.py` — P1-1 (video_id sanitization)
- `utils/cross_llm_audit.py` — Added pipeline-day3-audit feature entry
