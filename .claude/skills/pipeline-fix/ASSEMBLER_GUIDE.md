# Assembler Architecture
assembler.py is the main render engine (~1800 lines).
Split into modules: render_narrator.py, render_social.py, render_intro_outro.py,
render_clip.py, render_data.py, render_segment.py, render_chart_assets.py

Key rules:
- Music: confident_02.mp3 LOCKED as signature track
- Music volume: 0.22 narration, 0.04 clips, 0.15 social
- TTS: ElevenLabs PBX voice, 1.2x speed
- True peak: alimiter=limit=0.89 as LAST audio op
- AV sync: setpts=PTS-STARTPTS + asetpts=PTS-STARTPTS on all clips
- Black holes: fill with bg loop, never black frames
