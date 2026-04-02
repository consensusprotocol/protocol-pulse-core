# PIPELINE FIX — OPTION A: SINGLE HOST PBX

## Context
Load PIPELINE_LAWS.md before anything. This session fixes a single root-cause bug that has produced 9 consecutive Grade F renders.

## The Problem (diagnosed externally)
Every render fails because of a **host identity contradiction** across files:

1. `script_writer.py` generates ALL lines as `host: 2` (PBX solo) — correct
2. `tts_engine.py` has HOST_1 = Deborah (VeCVR24o7g2y1IxLJzZs) mapped, so when `host_num` falls back to `1` for any line, it calls a different ElevenLabs voice
3. That ElevenLabs call sometimes returns zero bytes silently — no exception raised
4. The assembler renders dead air + freeze frames around the zero-byte audio
5. `gemini_qc.py` grades for DUAL hosts (Eryn + Mark) and fails every single-host render
6. `gemini_grade.py` asks "do Eryn and Mark sound distinct?" — wrong hosts
7. `preflight.py` checks for Eryn's banned voice ID as a WARNING, not a PASS
8. `utils/quality_gate.py` reports 94/100 PASS on catastrophically broken renders

## The Fix: Option A — Lock everything to PBX solo

### File 1: tts_engine.py
- Remove HOST_1 entirely from VOICES dict — only HOST_2 (PBX) exists
- Add a HARD ABORT if any TTS call returns zero bytes: raise an exception, do NOT silently continue
- Add a per-line audio duration check: if generated audio is < 0.5s for any line > 10 chars, raise an exception and abort the entire render
- Remove the fallback logic `if spoken_count == 0 and host_num != 2: host_num = 2` — everything is already host 2
- Remove all Inworld voice config (dual_host_tts.py references) — locked to ElevenLabs per PIPELINE_LAWS
- Add a preflight TTS test: call ElevenLabs with a 5-word test phrase before the render starts, confirm > 1000 bytes returned

### File 2: dual_host_tts.py  
- This file is now obsolete — replace with a single-line stub that imports from tts_engine and re-exports generate_dialogue_audio
- Or delete it and update any imports

### File 3: script_writer.py
- Already correct (all host: 2) — verify this is still the case
- Update SCRIPT_PROMPT: remove any mention of Eryn, Mark, dual hosts — PBX is explicitly solo
- Remove `eryn_intro_hook` from the prompt template — it references a non-existent host

### File 4: gemini_qc.py
- Remove the dual-host requirement entirely
- Update grading criteria: "voices" check should now verify PBX's single voice is clear, consistent, not robotic — NOT check for a second host
- Remove: `voices >= 9 (both Eryn AND Mark present)` threshold
- Replace with: `voice_quality >= 8 (PBX voice clear, well-paced, not robotic, no dead air)`

### File 5: gemini_grade.py
- Question 15 currently asks: "Do the two hosts (Eryn and Mark) sound like distinct voices?"
- Replace with: "Does PBX's voice sound natural, authoritative, and well-paced throughout? Is there any dead air, robotic tone, or missing audio?"
- Update all other host references from Eryn/Mark → PBX

### File 6: preflight.py
- Remove the Eryn voice ID check entirely (`kdnRe2koJdOK4Ovxn2DI` check should be GONE)
- Add instead: ElevenLabs API live test (generate 5 words, verify >1000 bytes) as a HARD FAIL check
- Add: check that TTS_PROVIDER=elevenlabs in env (or absent, defaulting to elevenlabs)
- Add: check that PBX voice ID `HmUVvDlHsEz0m3eUGLgu` is configured in tts_engine.py

### File 7: utils/quality_gate.py
- Read the actual QC output from gemini_qc.py and use it correctly
- The bug: it's returning 94/100 while gemini_qc is reporting critical failures
- Find where the score is computed and fix it so Gemini QC failures propagate correctly
- A render with ANY critical failure from gemini_qc should score < 50 regardless of other metrics

### File 8: assembler.py
- Add zero-byte audio detection: before concatenating any part file, check its duration with ffprobe
- If any audio part has duration < 0.1s AND the script line is > 5 chars: ABORT with a clear error
- Add a post-TTS validation step: after all TTS generation, run ffprobe on every generated .m4a/.mp3 file, verify duration > 0 and > expected minimum
- Never silently render around missing audio

## After all fixes:
1. Run: `python3 preflight.py` — must show 0 errors, 0 warnings
2. Run: `python3 daily_producer.py --fast-test` — must complete without errors
3. Examine the fast-test output: confirm no zero-byte audio files, no freeze frames
4. If fast-test passes, run: `python3 daily_producer.py --test` — short real render
5. Check grade on the test render — must be > 50/100 (any improvement from F validates the fix)

## CRITICAL RULES
- PIPELINE_LAWS.md is gospel — load it first, never violate encoding specs
- No pyttsx3 fallback — if ElevenLabs fails, ABORT the render, do NOT substitute
- The abort-on-zero-bytes rule is NON-NEGOTIABLE — silence is worse than no video
- Run `regression_test.sh` after fixes if it exists
- Every commit: git add + commit + push

## Files to read first (before writing any code):
1. PIPELINE_LAWS.md
2. tts_engine.py (full)
3. script_writer.py (full)
4. gemini_qc.py (full)
5. gemini_grade.py (full)
6. preflight.py (full)
7. utils/quality_gate.py (full)
8. assembler.py — search for zero-byte handling specifically
