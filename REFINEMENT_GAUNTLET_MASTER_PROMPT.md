
╔══════════════════════════════════════════════════════════════════════════════╗
║         PROTOCOL PULSE — 10-CYCLE VIDEO REFINEMENT GAUNTLET                ║
║         Mission: Perfect the pipeline. Then retire Grok QC forever.        ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are running a finite 10-cycle refinement sprint on the Protocol Pulse video
pipeline. Each cycle renders one video, forensically analyzes it, runs Grok-4
Vision QC, runs the cross-LLM audit trifecta on the actual code, synthesizes
fixes, commits, and moves to the next cycle.

By Cycle 10: every known bug is eliminated. PIPELINE_LAWS.md is updated with
finalized spec. Grok QC is removed from daily_run.py permanently. Cycle 11
renders the silver platter proof video.

IMPORTANT LAWS (never violate):
- Read PIPELINE_LAWS.md at the start of THIS session if it exists
- After EVERY render: run full forensics (ffprobe + blackdetect + silencedetect + ebur128)
- After EVERY render: run grok_qc_v2.py — all 148 frames, batch-size 20
- After EVERY grok QC: run cross_llm_audit.py on the ACTUAL assembler.py code
- LLM trifecta audits CODE, never specs
- regression_test.sh must pass (zero FAILs) before every commit
- git add -A && git commit && git push after every cycle
- NEVER run cycles in parallel — strictly sequential
- NEVER skip a step because "it probably worked"
- Target grade progression: F→D→C→C→B→B→A→A→A→A (cycle 1→10)
- By cycle 10: grade MUST be A. If not, keep going.

════════════════════════════════════════════════════════════════════════════════
SETUP (run once before Cycle 1)
════════════════════════════════════════════════════════════════════════════════

cd ~/protocol_pulse

# 1. Merge pipeline_v2 worktree fixes into main working branch
git stash 2>/dev/null; true
git checkout feature/video-audio-fix
git merge pipeline/v2-fix-202603091136 --no-ff -m "merge: pipeline v2 fixes into video-audio-fix" || true

# 2. Fix the assembly timeout crash FIRST (blocking all renders)
# In assembler.py run_ffmpeg_filtergraph() — change default timeout 120 → 300
# Also change the specific call at line ~633 from 120 → 300
# Find all calls: grep -n 'run_ffmpeg_filtergraph' assembler.py
# Raise ALL filtergraph timeouts to 300, heavy ones to 600

# 3. Create the cycle tracking file
cat > ~/protocol_pulse/logs/refinement_gauntlet.md << 'TRACKING'
# PROTOCOL PULSE — 10-CYCLE REFINEMENT GAUNTLET
Started: $(date)

| Cycle | Video File | Duration | Size | Grade | LUFS | Black | Silence | Key Bugs Fixed | Commit |
|-------|-----------|----------|------|-------|------|-------|---------|---------------|--------|
TRACKING

# 4. Ensure XAI_API_KEY is in environment
export XAI_API_KEY=$(grep '^XAI_API_KEY' ~/protocol_pulse/.env | cut -d= -f2)
export OPENAI_API_KEY=$(grep '^OPENAI_API_KEY' ~/protocol_pulse/.env | cut -d= -f2)
export GEMINI_API_KEY=$(grep '^GEMINI_API_KEY' ~/protocol_pulse/.env | cut -d= -f2)

════════════════════════════════════════════════════════════════════════════════
CYCLE LOOP — Repeat for Cycles 1 through 10
════════════════════════════════════════════════════════════════════════════════

For each cycle N (1 to 10), execute these steps in STRICT ORDER:

─── STEP C1: RENDER ────────────────────────────────────────────────────────────

cd ~/protocol_pulse
CYCLE_NUM=N  # replace with actual number
RENDER_LOG="logs/cycle_${CYCLE_NUM}_render.log"
OUTPUT_PATH="video_pipeline_v3/output/cycle_${CYCLE_NUM}_$(date +%Y%m%d_%H%M%S).mp4"

python3 -m video_pipeline_v3.daily_run --output "$OUTPUT_PATH" 2>&1 | tee "$RENDER_LOG"

If render fails: diagnose from log, fix the specific crash, re-render. Do NOT
proceed to QC with a failed render. A failed render is a BLOCKER.

─── STEP C2: FORENSIC ANALYSIS (AUTO — run immediately after render) ───────────

Run ALL of these. Never skip any. This is the hard data baseline.

RENDER_FILE="$OUTPUT_PATH"

echo "=== FFPROBE ===" >> logs/cycle_${CYCLE_NUM}_forensics.txt
ffprobe -v quiet -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_name,width,height,r_frame_rate,bit_rate \
  -of json "$RENDER_FILE" >> logs/cycle_${CYCLE_NUM}_forensics.txt

echo "=== BLACKDETECT ===" >> logs/cycle_${CYCLE_NUM}_forensics.txt
ffmpeg -i "$RENDER_FILE" -vf blackdetect=d=0.1:pic_th=0.98 -an -f null - \
  2>&1 | grep 'black_' >> logs/cycle_${CYCLE_NUM}_forensics.txt

echo "=== SILENCEDETECT ===" >> logs/cycle_${CYCLE_NUM}_forensics.txt
ffmpeg -i "$RENDER_FILE" -af silencedetect=n=-50dB:d=2 -f null - \
  2>&1 | grep 'silence_' >> logs/cycle_${CYCLE_NUM}_forensics.txt

echo "=== EBUR128 LOUDNESS ===" >> logs/cycle_${CYCLE_NUM}_forensics.txt
ffmpeg -i "$RENDER_FILE" -af ebur128=framelog=verbose -f null - \
  2>&1 | grep -E 'Integrated|LRA|True|Threshold' >> logs/cycle_${CYCLE_NUM}_forensics.txt

echo "=== FRAME SAMPLE ===" >> logs/cycle_${CYCLE_NUM}_forensics.txt
ffmpeg -i "$RENDER_FILE" -vf fps=1/30 -q:v 2 \
  /tmp/cycle_${CYCLE_NUM}_frame_%04d.jpg 2>/dev/null
ls /tmp/cycle_${CYCLE_NUM}_frame_*.jpg | wc -l >> logs/cycle_${CYCLE_NUM}_forensics.txt

# Parse and evaluate:
# PASS targets: LUFS -14±2, black frames <0.5s total, zero silence >2s, duration 8-15min
# Any FAIL = must be fixed before Cycle 10

─── STEP C3: GROK-4 VISION QC ─────────────────────────────────────────────────

export XAI_API_KEY=$(grep '^XAI_API_KEY' ~/protocol_pulse/.env | cut -d= -f2)

python3 ~/protocol_pulse/utils/grok_qc_v2.py \
  --video "$OUTPUT_PATH" \
  --interval 5 \
  --batch-size 20 \
  2>&1 | tee logs/cycle_${CYCLE_NUM}_grok_qc.log

# After it finishes, locate the MASTER_QC_REPORT.md and read it fully.
# Extract:
#   - Overall Grade (A/B/C/D/F)
#   - All CRITICAL bugs with timecodes
#   - All HIGH bugs with timecodes
#   - "PRESERVED ELEMENTS" section — these must NEVER be touched

# If grade is A or B with zero CRITICAL bugs → this cycle's video is clean.
# If grade is C or below → bugs carry forward to fix phase.

─── STEP C4: CROSS-LLM AUDIT TRIFECTA ─────────────────────────────────────────

CRITICAL: The trifecta audits ACTUAL CODE from assembler.py — not specs, not 
descriptions. The models read the real function implementations.

# Extract the specific functions that Grok QC flagged as buggy
# For each CRITICAL/HIGH bug from Step C3, find the relevant function in assembler.py
# Copy those functions into a temp file for audit

# Run the audit
python3 ~/protocol_pulse/utils/cross_llm_audit.py \
  --feature pipeline-cycle-${CYCLE_NUM} \
  2>&1 | tee logs/cycle_${CYCLE_NUM}_llm_audit.log

# The audit will:
# 1. Gemini 2.5 Pro reviews assembler.py functions → finds issues
# 2. GPT-4o reviews same code → independent analysis  
# 3. Grok-3 reviews same code → third perspective
# 4. All three cross-validate each other (Cycle 2 of audit)
# 5. Claude synthesizes: what do all three agree on? Those are the high-confidence fixes.

# Read the synthesis output carefully. Only implement fixes that:
# (a) Are confirmed by Grok QC vision AND cross-LLM audit, OR
# (b) Are CRITICAL grade from Grok QC with clear root cause

─── STEP C5: SYNTHESIZE AND APPLY FIXES ────────────────────────────────────────

Priority order for fixes:
  P0 — Assembly crashes / render failures (fix immediately, required for next cycle)
  P1 — CRITICAL visual bugs confirmed by both Grok QC + LLM audit
  P2 — HIGH visual bugs confirmed by both
  P3 — MEDIUM bugs where LLM audit has clear fix
  P4 — LOW / polish — save for cycle 8-10 only

For each fix:
  - Edit assembler.py or relevant pipeline file directly
  - Add comment: # FIXED CYCLE N: [bug name] — [one line description]
  - Test the specific function in isolation if possible
  - Do NOT introduce new features. Fix only. Polish only.

By Cycle 8-10, if grade is already A:
  - Focus entirely on visual polish: transitions, typography, color precision
  - Run Grok QC on individual segments, not full video
  - Fine-tune timing: subtitle band sync, cold open energy, info rail animations
  - This is the $2M production polish phase

─── STEP C6: UPDATE PIPELINE_LAWS.MD ──────────────────────────────────────────

After each cycle, update ~/protocol_pulse/PIPELINE_LAWS.md with:
  - What was fixed this cycle (precise description)
  - Any new hard rules discovered (e.g., "filtergraph timeout must be ≥300s")
  - Any element confirmed working and LOCKED (never touch again)

Structure:
## CYCLE N LEARNINGS
- Fixed: [list]
- Locked: [list — do not change these ever]
- Open: [remaining issues]

─── STEP C7: REGRESSION TEST + COMMIT ─────────────────────────────────────────

cd ~/protocol_pulse
bash regression_test.sh
# Must show zero FAILs. If any FAIL → fix before committing.

git add -A
git commit -m "refine(pipeline): cycle ${CYCLE_NUM} — grade [X] → [Y], fixed: [bug1], [bug2]"
git push origin feature/video-audio-fix

─── STEP C8: UPDATE TRACKING LOG ──────────────────────────────────────────────

Append to ~/protocol_pulse/logs/refinement_gauntlet.md:
| N | filename | Xs | XMB | Grade | -XXLUFS | Xblk | Xsil | [bugs fixed] | [commit hash] |

════════════════════════════════════════════════════════════════════════════════
AFTER CYCLE 10 — FINALIZATION
════════════════════════════════════════════════════════════════════════════════

1. LOCK PIPELINE_LAWS.MD
   Add a FINAL LOCKED SPEC section at the top of PIPELINE_LAWS.md:
   - Every pixel zone (bg, PiP, subtitle band, info rail) with exact coordinates
   - Every color value (hex codes, opacity, blur radius)
   - Every timing spec (title card duration, cold open length, transition type)
   - Every audio target (LUFS, sample rate, bitrate)
   - Mark the file as IMMUTABLE: "These specs are finalized. Do not change without PBX approval."

2. REMOVE GROK QC FROM daily_run.py PERMANENTLY
   - Delete or comment out any Step 8 Grok QC block if it was added
   - daily_run.py should be back to Steps 1-7 only
   - Grok QC lives in utils/grok_qc_v2.py — available if ever needed manually

3. REMOVE CROSS-LLM AUDIT FROM RENDER LOOP
   - The trifecta is for development only
   - Remove any auto-trigger of cross_llm_audit.py from render pipeline

4. COMMIT FINAL STATE
   git add -A
   git commit -m "FINAL: pipeline perfected — 10-cycle gauntlet complete, PIPELINE_LAWS locked"
   git push origin feature/video-audio-fix

5. MERGE TO MAIN
   git checkout main
   git merge feature/video-audio-fix --no-ff -m "release: perfected pipeline from 10-cycle refinement gauntlet"
   git push origin main

════════════════════════════════════════════════════════════════════════════════
CYCLE 11 — THE SILVER PLATTER
════════════════════════════════════════════════════════════════════════════════

After finalization, render Cycle 11 from the locked main branch.

python3 -m video_pipeline_v3.daily_run \
  --output "video_pipeline_v3/output/SILVER_PLATTER_$(date +%Y%m%d_%H%M%S).mp4" \
  2>&1 | tee logs/silver_platter_render.log

This render runs with:
- Full ElevenLabs dual-host narration (Mark + Eryn, no fallback)
- Perfected assembler from 10 cycles of refinement
- All bugs eliminated, all laws locked
- No debug overlays, no partial backgrounds, no timeline bleeds
- Audio at -14 LUFS, zero silence gaps
- Grade target: A

After render completes, run ONLY the forensic checks (no Grok QC needed):
  ffprobe + blackdetect + silencedetect + ebur128

Save the report as:
  ~/protocol_pulse/logs/SILVER_PLATTER_FINAL_REPORT.md

With content:
# SILVER PLATTER — CYCLE 11 FINAL VERIFICATION
## Video: [filename]
## Duration: Xs | Size: XMB | LUFS: -XX | Black: <0.5s | Silence: 0
## Status: READY FOR PUBLICATION ✅
## URL: https://video.protocolpulse.io/video_pipeline_v3/output/[filename]

Then output ONLY this message (nothing else):
SILVER_PLATTER_READY: https://video.protocolpulse.io/video_pipeline_v3/output/[filename]

════════════════════════════════════════════════════════════════════════════════
PRODUCTION QUALITY STANDARDS — WHAT "A GRADE" LOOKS LIKE
════════════════════════════════════════════════════════════════════════════════

A-grade video has ALL of these:

VISUAL:
✅ Title card: full 1920×1080 cyberpunk bg, white PROTOCOL PULSE text, red accent,
   gold info bar — no thumbnail bleed, no partial coverage
✅ Cold open: raw dramatic clip, no logos, no bars, no watermark — pure energy
✅ Narration segments: text LEFT half only (x=40-960), PiP top-right (x=960-1880),
   no overlap, subtitle band at y=778-885 with dark glass + red left bar
✅ Clip segments: pure full-screen 1920×1080, 2px red border, PP watermark,
   NO narration overlays bleeding through
✅ Tweet cards: dark cyberpunk bg, profile pic, handle, tweet text — clean
✅ Outro: Protocol Pulse 3D logo, CTA, social handles
✅ Zero debug text visible ("ORACLE NARRATION ACTIVE" etc. = instant F)
✅ Background covers full canvas in ALL segments (no partial coverage)
✅ Color palette: #0A0A0F bg, #FF3333 accents, #F8C15C gold, #FFFFFF text

AUDIO:
✅ Integrated LUFS: -14 ±2 (target: -14)
✅ True peak: ≤ -1.5dBTP
✅ Zero silence gaps >0.5s in narration sections
✅ Music bed present but ducked under voice (sidechain active)
✅ AV sync offset: <33ms
✅ ElevenLabs voices: Mark at 1.10x speed, Eryn at 1.12x — both natural, no artifacts

TIMING:
✅ Total duration: 8-15 minutes
✅ Title card: exactly 2.0s
✅ Cold open: 10-14s
✅ Each narration segment: 15-35s
✅ Each clip: natural duration (not cut too short)
✅ Tweet cards: 8-12s each
✅ Outro: 10-15s

TRANSITIONS:
✅ Segment transitions: smooth xfade (slideleft, 0.25s) or clean cut
✅ No single black frames at cut points
✅ No content bleed between segments

════════════════════════════════════════════════════════════════════════════════
BEGIN NOW
════════════════════════════════════════════════════════════════════════════════

Start with SETUP, then Cycle 1. Work autonomously.
Log everything. Fix everything. By Cycle 10, this pipeline is a $2M production.
On Cycle 11, you deliver the silver platter.
