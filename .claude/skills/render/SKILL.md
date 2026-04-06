---
name: render
description: Fire a Protocol Pulse video render. Supports test, fast, full modes.
invocation: user
---
# Render Skill
Fire: cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py --$MODE --no-resume
Modes: test (3 clips), fast (cached scan), full (production)
Steps: 1) Kill existing renders 2) Preflight check 3) Fire 4) Monitor 5) Report
