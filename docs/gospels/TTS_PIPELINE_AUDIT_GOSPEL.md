# TTS PIPELINE AUDIT GOSPEL
# Target: video_pipeline_v3/tts_engine.py + video_pipeline_v3/daily_producer.py
# Problem: Inworld TTS generates correct audio (confirmed HTTP 200, 16-30KB MP3) 
#          but ffmpeg fails silently in pipeline context.
# 
# FILES TO AUDIT:
# - video_pipeline_v3/tts_engine.py (lines 300-400: tts_inworld function)
# - video_pipeline_v3/daily_producer.py (lines 509-600: generate_dialogue_audio)
#
# CONFIRMED FACTS:
# - Inworld API works: HTTP 200, audioContent key present, 16-30KB MP3 returned
# - Live test works: ffmpeg -y -i tmp.mp3 -filter:a atempo=1.200 -acodec pcm_s16le -ar 44100 -ac 1 out.wav -> rc=0
# - Pipeline FAILS: RuntimeError ffmpeg atempo failed (stderr truncated at 300 chars)
# - output_path passed to tts_inworld ends in .m4a (not .mp3 or .wav)
# - Our fix: out_wav = os.path.splitext(output_path)[0] + ".wav" then copy back
# - Live test of exact path logic confirmed working: 70214 bytes output
#
# AUDIT QUESTIONS FOR LLMs:
# 1. Is there any other reason tts_inworld could fail ONLY in pipeline context?
# 2. Is the output file size check (< 10240 bytes) causing false rejections?
# 3. Is there a race condition or file lock issue in generate_dialogue_audio?
# 4. Does generate_dialogue_audio properly handle the .wav output when it reads back duration?
# 5. What other silent failure modes exist in this TTS flow?
