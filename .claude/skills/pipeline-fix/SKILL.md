---
name: pipeline-fix
description: Fix issues in the Protocol Pulse video pipeline. Use when debugging render failures, clip selection, TTS, assembler, or social segment issues.
---
# Pipeline Fix Skill

When fixing pipeline issues:

1. **Identify the stage** - which of the 12 pipeline stages failed?
2. **Read the relevant guide** - load the appropriate reference file from this directory:
   - Render/assembler issues: read ASSEMBLER_GUIDE.md
   - Clip selection/extraction: read clip_selector.py and clip_extractor.py source
   - Pronunciation/TTS: read PRONUNCIATION.md
   - Chart/data overlay: read CHART_MAPPING.md
   - Social/signal dedup: read SOCIAL_DEDUP.md
   - Pipeline laws/rules: read PIPELINE_LAWS.md
3. **Read the actual code** before making changes
4. **Syntax check** every file after editing: python3 -m py_compile <file>
5. **Commit with descriptive message**

## Key Files
- daily_producer.py: Main orchestrator (~/protocol_pulse/video_pipeline_v3/)
- assembler.py: Video assembly engine
- clip_selector.py: Claude API clip selection
- clip_extractor.py: yt-dlp extraction + AV sync
- render_social.py: Tweet cards + social segments
- render_data.py: Chart overlays + data panels
- tts_engine.py: ElevenLabs TTS + pronunciation
- script_writer.py: Episode script generation
