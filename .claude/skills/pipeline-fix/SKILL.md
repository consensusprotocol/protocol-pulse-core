---
name: pipeline-fix
description: Use when fixing video pipeline issues. Auto-loads PIPELINE_LAWS and module architecture.
---

## Before ANY pipeline change:
1. Read PIPELINE_LAWS.md: `cat ~/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS.md`
2. Understand the split architecture — assembler.py is a THIN orchestrator
3. Edit the correct MODULE, not assembler.py:
   - Narration/PiP issues → render_narrator.py
   - Clip rendering → render_clip.py  
   - Social cards/tweets → render_social.py
   - Intro/outro → render_intro_outro.py
   - Charts/data → render_data.py
   - Audio/music/loudness → audio_master.py
   - Transitions/whoosh → transitions.py

## After ANY pipeline change:
1. Syntax check: `python3 -m py_compile <file>`
2. Import test: `python3 -c "from assembler import assemble_episode; print('OK')"`
3. Git add + commit + push
4. Test render: `python3 daily_producer.py --fast-test`

## Supporting files:
- ~/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS.md
- ~/protocol_pulse/video_pipeline_v3/config.yaml
- ~/protocol_pulse/video_pipeline_v3/channels.yaml
