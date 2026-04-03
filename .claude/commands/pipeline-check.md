Verify the video pipeline is ready to render:
1. GPU available: `nvidia-smi --query-gpu=memory.free --format=csv,noheader`
2. Disk space: `df -h /home/ultron`
3. No other renders running: `pgrep -fa daily_producer`
4. yt-dlp working: `yt-dlp --version`
5. Deno installed: `deno --version`
6. ElevenLabs key valid: check .env has ELEVENLABS_API_KEY
7. Claude API key valid: check .env has ANTHROPIC_API_KEY
8. Assembler imports clean: `cd ~/protocol_pulse/video_pipeline_v3 && python3 -c "from assembler import assemble_episode; print('OK')"`
9. All pipeline modules compile: py_compile each render_*.py
Report each check.