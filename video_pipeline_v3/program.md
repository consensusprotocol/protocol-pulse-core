# Protocol Pulse Video Pipeline — AutoResearch Program v2
# Updated with V57 viewer feedback

## Goal
Fix remaining quality issues in the Pulse Check video render and optimize for 2026 YouTube best practices.

## V57 Render Feedback (from PBX review)
These are the specific issues to fix, in priority order:

### ISSUE 1: Partner clips cut off before completing the thought
Clips end abruptly mid-sentence. The clip extractor uses silence detection with an 8-second window. 
FIX APPROACH: Use Whisper transcript timestamps to find sentence boundaries. Cut at the end of the last complete sentence, not at silence. Add 1.5s audio fadeout at cut point.
FILES: video_pipeline_v3/clip_extractor.py — _trim_clip() function

### ISSUE 2: Social media card text overflow
Tweet/Nostr post text flows past the red border container (see: text extends beyond box boundaries).
FIX APPROACH: Auto-calculate text height based on character count and font size. Expand container height dynamically. Use word-wrap with max line width. If text exceeds max container height, truncate with "..." 
FILES: video_pipeline_v3/render_social.py — make_social_card_visual() drawtext parameters

### ISSUE 3: "Fiat" pronunciation
Kokoro TTS mispronounces "fiat" — should sound like "fee-aht" not "fee-at" or "fy-at".
FIX APPROACH: Add text replacement in tts_engine.py: "fiat" -> "fee-aht" before sending to TTS.
FILES: video_pipeline_v3/tts_engine.py — pronunciation map
STATUS: ALREADY FIXED in this update

### ISSUE 4: Narrator intro delivery is stale and oddly toned
The opening narration sounds robotic and unnatural. Needs warmth, enthusiasm, authentic human energy.
FIX APPROACH: 
- Adjust Kokoro voice speed (try 1.0 instead of 1.1 for more natural pacing)
- Add slight pauses between sentences (insert 0.3s silence at period/comma boundaries)
- Script writer should generate more conversational, energetic opening lines
- Consider using Chatterbox PBX voice clone for warmer delivery (needs tts_chatterbox function defined)
FILES: video_pipeline_v3/tts_engine.py, video_pipeline_v3/script_writer.py

### ISSUE 5: Opening/closing polish
Intro and outro need to feel premium and polished, matching 2026 YouTube production standards.
FIX APPROACH: Review render_intro_outro.py for timing, transitions, and visual quality.
FILES: video_pipeline_v3/render_intro_outro.py

### ISSUE 6: geq filtergraph bottleneck (from prior AutoResearch session)
The geq per-pixel filter in _build_black_diamond_bg causes 83+ second renders for simple backgrounds.
FIX APPROACH: Replace geq with pre-rendered PNG backgrounds + simple overlay. Or use color + gradient filters.
FILES: video_pipeline_v3/render_narrator.py, render_social.py

## Success Metric
A test render that:
1. Completes without crash
2. All partner clips end at natural sentence boundaries (no mid-word cutoff)
3. Social card text fits within its container
4. "Fiat" pronounced correctly
5. Narrator sounds natural and enthusiastic
6. Total render time < 30 minutes

## Experiment Loop
1. Pick the highest-priority unfixed issue
2. Read the relevant file(s) completely before making changes
3. Make ONE targeted fix
4. If the fix involves TTS: generate a 10-second test audio and verify
5. If the fix involves visuals: render a single segment and verify with ffprobe/ffplay
6. If fix works: commit with "PASS: [issue] [description]"
7. If fix fails: revert, try different approach
8. Move to next issue
9. After all issues addressed: run full test render and verify

## Constraints
- Do NOT change clip_extractor.py and assembler.py in the same commit
- Do NOT remove timeout=900 force in run_ffmpeg
- TTS uses tts_kokoro (Kokoro af_heart voice) — tts_chatterbox is NOT defined yet
- All presets: "fast" or "ultrafast" for intermediates
- One change at a time, verify before moving on
