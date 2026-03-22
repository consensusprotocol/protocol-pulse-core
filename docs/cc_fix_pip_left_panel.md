Read ~/protocol_pulse/PIPELINE_LAWS.md first.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY AUDIT-FIRST LAW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DO NOT write any code until the cross-LLM audit completes.
The audit fires Gemini + GPT-4o + Grok in parallel on the actual files.
Their consensus determines what gets built and how.
This is non-negotiable — skipping the audit is what caused every regression tonight.

TASK: Restore world-class PiP left panel — episode title + sponsor carousel.
The left panel next to the PiP preview video is currently a plain background.
It must show: episode title, segment topic, and rotating sponsor cards.

FILES IN SCOPE:
- video_pipeline_v3/assembler.py (PiP section only)
DO NOT touch: tts_engine.py, overnight_render_loop.py, daily_producer.py, script_writer.py
DO NOT touch the right PiP panel (preview loop video) — leave it exactly as is.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — CROSS-LLM AUDIT (Cycle 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd ~/protocol_pulse
python3 utils/cross_llm_audit.py --feature fix-pip-left-panel
Save cycle 1 output path.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — CROSS-LLM AUDIT (Cycle 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 utils/cross_llm_audit.py --feature fix-pip-left-panel --cycle 2 --cycle1-results [C1_OUTPUT]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — READ VISUAL DESIGN SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cat ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md
This is gospel — match brand colors/typography exactly.
Brand: RED=#CC2222, BLACK=#06070A, WHITE=#FFFFFF, MONO_FONT=JetBrains Mono

Check git history for the last world-class left panel implementation:
git log --oneline -30 -- video_pipeline_v3/assembler.py
git show [BEST_COMMIT]:video_pipeline_v3/assembler.py | grep -n "title.*pill\|carousel\|sponsor\|left.*panel" | head -20

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — IMPLEMENT LEFT PANEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Left panel (960x1080px) design:
- TOP THIRD: "PULSE CHECK" kicker in red monospace, episode title in large white bold
- MIDDLE: Current segment topic label (from clip channel/title)
- BOTTOM THIRD: Sponsor carousel — 3 cards rotating every 8s using FFmpeg enable=
  Card 1 (0-8s):  "CURATED MINING — White-glove Bitcoin mining — curatedmining.io"
  Card 2 (8-16s): "DIGITAL RESIDENCY — Sovereign ID via RNS.ID — protocolpulse.io/digital-residency"  
  Card 3 (16+s):  "PROTOCOL PULSE+ — Premium intelligence — protocolpulse.io"
  Cards styled: dark bg, red accent border, white text, monospace font

Use pure FFmpeg drawtext/drawbox — no external dependencies.
Implement using the existing fg (filtergraph) string builder pattern in make_pip_scene().

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh  # 0 FAILs required
git add video_pipeline_v3/assembler.py
git commit -m "feat(assembler): restore PiP left panel — episode title + rotating sponsor carousel, Protocol Pulse brand"
git push