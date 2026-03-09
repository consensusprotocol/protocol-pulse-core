# VIDEO PIPELINE FIX — AUTONOMOUS 10+1 OVERNIGHT GOSPEL
# Operator: PBX | Date: 2026-03-09 | Priority: CRITICAL

## CONTEXT — CONFIRMED BUGS FROM FORENSIC AUDIT

### BUG 1 — WRONG VOICE IDs (CRITICAL)
`dual_host_tts.py` uses Nicole (piTKgcLEGmPE4e6mEKli) + Chris (iP95p4xoKVk53GoZ742B)
PIPELINE_LAWS specifies Eryn (kdnRe2koJdOK4Ovxn2DI) + Mark (1SM7GgM6IMuvQlz2BwM3)
PBX directive: **SINGLE HOST ONLY — Mark (1SM7GgM6IMuvQlz2BwM3) at 1.10x speed**
Remove female narrator entirely. All host=1 AND host=2 lines go to Mark only.

### BUG 2 — CLIP EXTRACTION FAILURE → BROKEN SEGMENT FLOW
Clip #2 (TheInvestorPodcastNetwork/Preston Pysh) failed to download.
Script had 4 CLIP entries but only 3 clips in yt_clips/
When clip not found: assembler skips clip but narration continues, causing:
- Narrator speaking over where clip should be
- PiP frame showing empty/black "next source" 
- Two narrators going back and forth over muted full-screen clip video
FIX: Robust fallback — if clip missing, skip BOTH the clip entry AND its flanking setup/react narration, or use a branded "clip unavailable" 10s placeholder with narration still playing

### BUG 3 — PiP SHOWING EMPTY BLACK FRAME
When pip_previews has no entry for a rank (because clip failed), overlay still renders
but shows empty frame labeled "next source". Must check if pip_path exists before overlay.

### BUG 4 — NARRATORS SPEAKING OVER CLIP AUDIO  
The CLIP segment preserves original audio AND volume. But assembler stitches:
[setup narration] → [clip video with original audio]
The issue: at transition point, audio from previous narration segment bled into clip
or the PiP preview video (with "COMING UP..." label) was treated as the actual clip segment.
FIX: Hard cut only. No overlap at clip boundaries. Verify clip original audio is isolated and narration TTS is NOT present in clip segment.

### BUG 5 — AV SYNC FAILURE ON YT CLIPS
fix_av_sync() uses setpts=PTS-STARTPTS but some yt-dlp --download-sections outputs
have DTS discontinuities that survive this. 
FIX: Add `-itsoffset 0` explicit reset + `-copyts` removal + strict `-vsync 2` in fix_av_sync.
Also: validate sync BEFORE the clip is used in assembly, not just after extraction.

### BUG 6 — TWEET SEGMENT + OUTRO TIMING ISSUES
- Outro clip plays too late 
- Outro AV out of sync
- Social card audio/visual timing misaligned
FIX: Audit make_branded_outro() and make_social_card_visual() timing logic

### BUG 7 — NotebookLM AUDIO (cannot automate — xAI Grok audio is alternative)
PBX asked about NotebookLM. NotebookLM has no API. 
Alternative: Use ElevenLabs "Mark" voice at premium quality with proper speed/style settings.
Keep pipeline as-is with single Mark host. Document this for PBX.

---

## MISSION: AUTONOMOUS 10+1 VIDEO IMPROVEMENT LOOP

You will run 10 sequential render+analyze+fix cycles, then produce a final 11th video.
Each cycle: render → forensic analysis → Grok Vision frame analysis → LLM trifecta audit → fix → verify.

**TOTAL EXPECTED TIME: 6-10 hours. Run autonomously. Do not stop.**

---

## STEP 0: SETUP

```bash
cd ~/protocol_pulse
source .env && export ANTHROPIC_API_KEY XAI_API_KEY OPENAI_API_KEY GEMINI_API_KEY ELEVENLABS_API_KEY
PIPE=~/protocol_pulse/video_pipeline_v3
LOG_DIR=~/protocol_pulse/logs/overnight_fix
mkdir -p $LOG_DIR ~/protocol_pulse/docs/overnight_renders
```

Read these files FULLY before touching any code:
- `~/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS.md`
- `~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md`
- `~/protocol_pulse/ARTICLE_PAGE_LAWS.md` (for any route changes)

---

## STEP 1: IMPLEMENT ALL CONFIRMED FIXES IN CODE

### Fix 1A: Rewrite dual_host_tts.py — Single Host (Mark only)
```python
# VOICES dict becomes single entry:
VOICES = {
    1: {
        "voice_id": "1SM7GgM6IMuvQlz2BwM3",  # Mark — PBX approved
        "name": "Mark",
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.80,
            "style": 0.15,
            "use_speaker_boost": True,
            "speed": 1.10,  # Mark at 1.10x per PIPELINE_LAWS
        },
    },
    2: {  # Map host 2 ALSO to Mark — single host
        "voice_id": "1SM7GgM6IMuvQlz2BwM3",
        "name": "Mark",
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.80,
            "style": 0.15,
            "use_speaker_boost": True,
            "speed": 1.10,
        },
    },
}
```
Also: remove all references to "Nicole", "Chris", "deborah", host gender logic.
Audio files: all named `line_NNN_mark.m4a` regardless of host number.

### Fix 1B: assembler.py — Robust clip fallback + PiP guard
In `_assemble_episode_inner`, in the `if host_field == "CLIP":` block:
```python
if not clip_path or not os.path.exists(clip_path):
    logger.warning(f"[---] Clip #{rank}: MISSING — injecting branded placeholder")
    # Create 8s branded placeholder with "CLIP UNAVAILABLE" message
    placeholder_out = os.path.join(work_dir, f"part_{part_idx:03d}_clip_placeholder_r{rank}.mp4")
    # Use make_transition_visual or a simple colored card
    # DO NOT skip silently — show something and keep timeline intact
    placeholder_result = _make_clip_unavailable_card(rank, placeholder_out, btc_price)
    if placeholder_result:
        parts.append(placeholder_result)
        part_idx += 1
    continue
```

Add new function `_make_clip_unavailable_card(rank, output_path, btc_price)`:
- 8 second duration
- Black Diamond background
- Red text: "⚡ CLIP #{rank} LOADING..."
- Subtext: "Source unavailable — signal interrupted"
- Same info rail as other segments
- Silent audio (anullsrc)

### Fix 1C: overlay_pip_on_narration — Guard against missing pip
```python
def overlay_pip_on_narration(narration_path, pip_path, output_path):
    if not pip_path or not os.path.exists(pip_path):
        return narration_path  # already exists, just return it
```
Currently missing this guard — if pip_path is "" it crashes.

### Fix 1D: fix_av_sync() in clip_extractor.py — Nuclear-first approach
Replace current fix_av_sync with more aggressive version:
```python
def fix_av_sync(input_path, output_path):
    return _run_ffmpeg([
        "-fflags", "+genpts+igndts+discardcorrupt",
        "-itsoffset", "0",
        "-i", input_path,
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
        "-r", "30", "-vsync", "cfr",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30,format=yuv420p,setpts=PTS-STARTPTS",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-af", "aresample=async=1:min_hard_comp=0.1:first_pts=0,asetpts=PTS-STARTPTS",
        "-avoid_negative_ts", "make_zero",
        "-max_interleave_delta", "0",
        "-movflags", "+faststart",
        output_path,
    ], "av_sync_fix_v2", 300)
```

### Fix 1E: Outro timing — make_branded_outro() audit
Check if wrap_audio is actually being passed and applied to outro.
Current code sets `wrap_audio` but passes `narration_audio=""` to `make_branded_outro`.
Fix: Pass `wrap_audio` properly:
```python
outro_result = make_branded_outro(outro_out, narration_audio=wrap_audio)
```

### Fix 1F: Tweet/social segment AV sync
In `make_social_card_visual()` and `make_remotion_social_card()`:
- Ensure audio duration matches video duration exactly
- Add `-shortest` guard
- Ensure `durationInFrames` always rounds UP not down

### Fix 1G: Visual enhancements (creative freedom)
While in the code, enhance:
1. **Clip lower-third**: More polished glass panel — add subtle gradient, channel logo placeholder
2. **Host visual**: Add animated waveform or subtle heartbeat pulse on the info rail during speech
3. **Transitions**: Ensure xfade is actually being used between ALL segment types, not just normalized parts
4. **Intro title card**: Add BTC price ticker animation to the 2s title card
5. **PiP frame**: Border should pulse red when "COMING UP..." — add animated drawbox timing

---

## STEP 2: CROSS-LLM AUDIT OF ALL FIXES

After implementing fixes, run:
```bash
python3 ~/protocol_pulse/utils/cross_llm_audit.py \
    --feature video_pipeline_overnight \
    --files ~/protocol_pulse/video_pipeline_v3/dual_host_tts.py \
            ~/protocol_pulse/video_pipeline_v3/assembler.py \
            ~/protocol_pulse/video_pipeline_v3/clip_extractor.py \
    --context "$(cat ~/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS.md)" \
    --output ~/protocol_pulse/docs/overnight_renders/AUDIT_cycle_0.md
```

Read FINAL_CONSENSUS.md, implement all P0 items before first render.

---

## STEP 3: THE 10-RENDER LOOP

For each cycle N = 1 to 10:

### 3A: Render
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT=~/protocol_pulse/video_pipeline_v3/output/overnight_v${N}_${TIMESTAMP}.mp4
cd ~/protocol_pulse && python3 -m video_pipeline_v3.daily_run --output $OUTPUT 2>&1 | tee $LOG_DIR/render_v${N}.log
```

Wait for render to complete. Check exit code. If failure: read log, fix crash, retry.

### 3B: Forensic Analysis
```bash
# Auto-forensic (MANDATORY per PIPELINE_LAWS — never skip)
ffprobe -v quiet -print_format json -show_format -show_streams $OUTPUT > $LOG_DIR/ffprobe_v${N}.json
ffmpeg -i $OUTPUT -vf "blackdetect=d=0.1:pix_th=0.1" -an -f null - 2> $LOG_DIR/blackdetect_v${N}.txt
ffmpeg -i $OUTPUT -af "silencedetect=noise=-50dB:d=0.3" -vn -f null - 2> $LOG_DIR/silencedetect_v${N}.txt
ffmpeg -i $OUTPUT -af ebur128=metadata=1 -f null - 2> $LOG_DIR/ebur128_v${N}.txt
# Extract frames every 3s
mkdir -p $LOG_DIR/frames_v${N}
ffmpeg -i $OUTPUT -vf "fps=1/3" $LOG_DIR/frames_v${N}/frame_%04d.jpg
```

Parse all results. Log:
- Total duration, video/audio codec
- Black frame timestamps (should be 0 except planned transitions)
- Silence gaps (>2s = bug unless it's a clip segment)
- LUFS integrated loudness (target: -14 LUFS)
- AV sync drift measurement

### 3C: Grok Vision Analysis
Write a Python script that:
1. Selects 20 representative frames from $LOG_DIR/frames_v${N}/ (spread across full duration)
2. Also extracts specific key frames at: 0:00, 0:05, 4:10, 4:16, 4:20, 5:30, 5:36, tweet segment start, outro start
3. Sends frames + this prompt to Grok Vision API:

```python
import base64, os, requests, json

def analyze_video_with_grok(frame_dir, video_number, log_path):
    XAI_KEY = os.getenv("XAI_API_KEY")
    
    # Load frames
    frames = sorted(os.listdir(frame_dir))
    # Select 20 spread evenly + key timestamp frames
    step = max(1, len(frames) // 20)
    selected = frames[::step][:20]
    
    content = [
        {"type": "text", "text": f"""You are a professional video producer reviewing Protocol Pulse video #{video_number}.
        
This is a Bitcoin intelligence show with a single male host (Mark) narrating over:
- Intro title card with BTC price
- Host narration segments with animated cyberpunk background
- YouTube partner channel clips (full screen with original audio)
- PiP preview frames (small video in corner showing upcoming clip)
- Tweet/social segment cards
- Branded outro

Review ALL frames carefully. Report on:

CRITICAL ISSUES (show-stoppers):
1. Any black/empty frames that shouldn't be there
2. Any visible text errors, overflow, or missing text
3. Any frames where the visual clearly doesn't match expected segment (e.g., host frame during clip segment)
4. AV sync issues visible from still frames (lip sync, text out of frame)
5. Empty PiP frames labeled "next source" or black boxes
6. Missing visuals — segments that should have branded content but show nothing

QUALITY ISSUES:
7. Any visual element that looks unfinished or amateurish
8. Branding consistency — does PROTOCOL PULSE watermark appear consistently?
9. Color palette consistency (should be dark bg, red accents, white text, gold info bar)
10. Lower-third legibility — can you read the channel names?
11. Transition quality — smooth or jarring?
12. Tweet cards — do they look professional?
13. Outro — branded and polished?

IMPROVEMENT SUGGESTIONS:
14. What specific visual elements could be enhanced for world-class quality?
15. What is working really well that should be preserved?

Be brutally specific. Include frame numbers where you see issues."""}
    ]
    
    # Add frame images
    for fname in selected:
        fpath = os.path.join(frame_dir, fname)
        with open(fpath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })
    
    response = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
        json={
            "model": "grok-2-vision-latest",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 4000,
            "temperature": 0.3,
        },
        timeout=120,
    )
    result = response.json()
    analysis = result["choices"][0]["message"]["content"]
    with open(log_path, "w") as f:
        f.write(analysis)
    return analysis
```

### 3D: LLM Trifecta Audit
After Grok Vision analysis, run cross_llm_audit.py with:
- The full assembler.py, dual_host_tts.py, clip_extractor.py code
- The forensic data from 3B
- The Grok Vision analysis from 3C
- Context: PIPELINE_LAWS.md

```bash
python3 ~/protocol_pulse/utils/cross_llm_audit.py \
    --feature video_pipeline_v${N} \
    --files ~/protocol_pulse/video_pipeline_v3/assembler.py \
            ~/protocol_pulse/video_pipeline_v3/dual_host_tts.py \
            ~/protocol_pulse/video_pipeline_v3/clip_extractor.py \
    --extra_context "$(cat $LOG_DIR/grok_vision_v${N}.txt) FORENSIC: $(cat $LOG_DIR/ffprobe_v${N}.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[\"format\"][\"duration\"], d[\"streams\"][0].get(\"codec_name\"))')" \
    --output ~/protocol_pulse/docs/overnight_renders/AUDIT_v${N}.md
```

### 3E: Implement Cycle Fixes
Read FINAL_CONSENSUS.md for this cycle.
Implement ALL P0 items immediately.
Implement P1 items that don't risk regression.
Flag P2 items in a TODO comment.
Run regression_test.sh — fix until zero FAILs.
Commit: `git add -A && git commit -m "fix(pipeline): overnight cycle v${N} — [brief summary of fixes]"`
git push origin main

### 3F: Log the Cycle Summary
Write to $LOG_DIR/cycle_v${N}_summary.md:
```
## Cycle ${N} Summary
- Render time: Xs
- Duration: Xs
- LUFS: X dB
- Black frames: X
- Grok Vision top issues: [list]
- LLM consensus P0 fixes: [list]  
- Fixes implemented: [list]
- Quality trend: IMPROVING / STABLE / REGRESSED
```

---

## STEP 4: FINAL RENDER — VIDEO 11

After all 10 cycles complete:
1. Run full regression_test.sh — zero FAILs required
2. Run cross_llm_audit.py one final time on the complete pipeline
3. Implement any remaining P0 items from final audit
4. Render the 11th video with a timestamp suffix "_FINAL"
5. Run complete forensic analysis on the final video
6. Run Grok Vision analysis one final time
7. Write ~/protocol_pulse/docs/overnight_renders/FINAL_REPORT.md containing:
   - All 10 cycle summaries
   - Complete list of bugs found and fixed
   - Quality metrics trajectory
   - Grok Vision final assessment
   - What's working perfectly
   - Any remaining known issues (if any)
   - NotebookLM recommendation: cannot automate (no API). ElevenLabs Mark at 1.10x is the approved single-voice solution.

---

## RULES — INVIOLABLE

1. NEVER skip the auto-forensic analysis after any render
2. NEVER skip the cross-LLM audit after each cycle  
3. NEVER merge without regression_test.sh passing zero FAILs
4. NEVER skip Grok Vision analysis
5. If render fails 3 times in a row: write the error to FINAL_REPORT.md and move to next cycle
6. NEVER remove voice rate limiting in ElevenLabs calls
7. NEVER use Creatomate, OpusClip, Suno API, MuseTalk, SadTalker
8. Keep Mark as SOLE narrator — do NOT re-add female voice for any reason
9. Every git commit must push to origin main
10. If out of disk space: delete all .norm*.mp4 and intermediate work files from old runs first
