# PROTOCOL PULSE — PIPELINE LAWS
## Status: ACTIVE (being refined via 10-cycle gauntlet)

---

## PIXEL ZONES (confirmed spec)
- Background: full 1920×1080, color #0A0A0F (never pure black #000000)
- Text zone (narration): x=40-960, y=80-760 (left half only)
- PiP zone: x=960-1880, y=0-540 (top right)
- Subtitle band: y=778-885, full width (1920px), dark glass rgba(0,0,0,0.75), 4px red left bar
- Info rail (gold): bottom, y≈1032-1080, full width, #F8C15C text
- Title card: full canvas, no thumbnail bleed

## COLOR PALETTE (locked)
- Background: #0A0A0F (VDS dark navy)
- Accent / border: #FF3333 (red, 2px borders)
- Gold info text: #F8C15C
- Primary text: #FFFFFF
- Subtitle band bg: rgba(0,0,0,0.75) + blur

## AUDIO TARGETS (locked)
- Integrated LUFS: -14 ±2
- True peak: ≤ -1.5dBTP
- LRA: 7 LU
- Single loudnorm: only in concatenate_parts() — no per-segment loudnorm
- Sample rate: 48000 Hz
- Bitrate: 192k (audio)

## TTS (locked)
- Voice: Mark (ID: 1SM7GgM6IMuvQlz2BwM3) at 1.10x speed
- Both host=1 and host=2 → Mark (single narrator)
- Speed param: top-level body param, NOT inside voice_settings
- Fallback chain: ElevenLabs → pyttsx3 → gTTS → silence
- TTS cache: tts_cache/ SHA256(voice_id:segment_type:text)[:16].m4a

## FFMPEG TIMEOUTS (locked)
- Default run_ffmpeg_filtergraph() timeout: 300s (was 120s)
- Heavy filtergraphs (make_intro_coldopen, PiP): 300s minimum
- concatenate_parts(): 600s

## TIMING SPEC
- Title card: 2.0s exactly
- Cold open: 10-14s
- Narration segments: 15-35s each
- Clip segments: natural duration
- Tweet cards: 8-12s
- Outro: 10-15s
- Total: 8-15 minutes

## PRODUCTION RULES
- debug_mode = False in all production renders
- No debug overlays ("ORACLE NARRATION ACTIVE" etc.) — instant F grade if visible
- Cold open: NO logos, bars, watermarks — pure dramatic clip
- Clip segments: full-screen 1920×1080, NO narration overlays bleeding through
- Continuous BGM: music mixed ONCE in concatenate_parts(), not per-segment
- AV sync: nuclear PTS in fix_av_sync() + concatenate_parts()

## PRESERVED ELEMENTS (never touch)
- Gold bottom bar text color #F8C15C
- Red border thickness 2px where intentionally present
- Watermark: "PROTOCOL PULSE" white, lower-right, opacity 0.5
- PiP position: top-right, no text overlap

---

## CYCLE LEARNINGS

### PRE-GAUNTLET (cycles 1-3 on feature/video-audio-fix)
- Fixed: ElevenLabs fallback chain (gTTS added), AV sync, gold rail in make_host_visual, subtitle band in make_host_visual, per-segment loudnorm removed, bg color 0x0A0A0F, ffmpeg timeout raised to 300s
- Locked: Single loudnorm in concatenate_parts()
- Open: Subtitle band inconsistency (~50% of frames missing it), LUFS low (-17.7) due to cached silence audio



---

## QC PIPELINE LAW — PERMANENT — NEVER SKIP

### THE TWO-STAGE QC GATE:

STAGE 1 — GEMINI (automated, runs after every render):
- Gemini video analysis runs automatically as Step 8 of daily_run.py
- Output: GEMINI_QC_REPORT.json + GEMINI_QC_REPORT.md with scores per dimension
- The gauntlet MUST read EVERY score and EVERY finding from this report
- EVERY dimension scoring below 8/10 maps to a specific code fix — no exceptions
- EVERY bug listed maps to a specific code fix with file + line — no exceptions
- Nothing is summarized, nothing is skipped, nothing is cherry-picked
- Re-render after fixes → Gemini runs again → repeat until ALL dimensions ≥ 8/10 and grade = A
- ONLY when Gemini grades A does the video get served to PBX

STAGE 2 — GROK (manual, PBX-run, after Gemini A-grade confirmed):
- PBX takes the silver platter URL and runs it through Grok browser video analysis tool
- Grok produces a breakdown of any remaining issues
- Every Grok finding maps to a code fix in the NEXT render cycle
- Grok findings are treated with the same weight as Gemini findings — nothing ignored

### THE SILVER PLATTER RULE:
Video is NEVER shown to PBX until Gemini grades it A.
When Gemini grades A: post the URL as: 
  🎬 SILVER PLATTER: https://video.protocolpulse.io/[filename]
  Gemini grade: A | Scores: [all dimensions] | Ready for Grok review.

### WHAT COUNTS AS GRADE A (ALL must be true):
- pip ≥ 8/10
- cold_open ≥ 8/10  
- background ≥ 8/10
- voices = 10/10 (already achieved — never regress)
- audio_quality ≥ 9/10 (already achieved — never regress)
- debug_text = 10/10 (already achieved — never regress)
- Zero black frames detected by ffprobe blackdetect
- Zero silence segments detected by ffprobe silencedetect
- LUFS between -15 and -13 (target -14)



---

## QC PIPELINE LAW — PERMANENT — NEVER SKIP

### THE TWO-STAGE QC GATE:

STAGE 1 — GEMINI (automated, runs after every render):
- Gemini video analysis runs automatically as Step 8 of daily_run.py
- Output: GEMINI_QC_REPORT.json + GEMINI_QC_REPORT.md with scores per dimension
- The gauntlet MUST read EVERY score and EVERY finding from this report
- EVERY dimension scoring below 8/10 maps to a specific code fix — no exceptions
- EVERY bug listed maps to a specific code fix with file + line — no exceptions
- Nothing is summarized, nothing is skipped, nothing is cherry-picked
- Re-render after fixes → Gemini runs again → repeat until ALL dimensions ≥ 8/10 and grade = A
- ONLY when Gemini grades A does the video get served to PBX

STAGE 2 — GROK (manual, PBX-run, after Gemini A-grade confirmed):
- PBX takes the silver platter URL and runs it through Grok browser video analysis tool
- Grok produces a breakdown of any remaining issues
- Every Grok finding maps to a code fix in the NEXT render cycle
- Grok findings are treated with the same weight as Gemini findings — nothing ignored

### THE SILVER PLATTER RULE:
Video is NEVER shown to PBX until Gemini grades it A.
When Gemini grades A: post the URL as: 
  🎬 SILVER PLATTER: https://video.protocolpulse.io/[filename]
  Gemini grade: A | Scores: [all dimensions] | Ready for Grok review.

### WHAT COUNTS AS GRADE A (ALL must be true):
- pip ≥ 8/10
- cold_open ≥ 8/10  
- background ≥ 8/10
- voices = 10/10 (already achieved — never regress)
- audio_quality ≥ 9/10 (already achieved — never regress)
- debug_text = 10/10 (already achieved — never regress)
- Zero black frames detected by ffprobe blackdetect
- Zero silence segments detected by ffprobe silencedetect
- LUFS between -15 and -13 (target -14)
