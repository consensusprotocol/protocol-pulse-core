#!/usr/bin/env python3
"""
Waits for render5 to complete, then fires:
1. Full forensic ffprobe analysis
2. Gemini full video upload + analysis
3. Cross-compares and sends findings to TG
"""
import os, sys, time, subprocess, json, urllib.request, glob

BASE = '/home/ultron/protocol_pulse'
PIPE = f'{BASE}/video_pipeline_v3'
LOGS = f'{BASE}/logs'

def load_env():
    env = {}
    try:
        for line in open(f'{BASE}/.env'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    except: pass
    return env

ENV = load_env()

def tg(msg):
    tok = ENV.get('TELEGRAM_BOT_TOKEN','')
    chat = ENV.get('TELEGRAM_CHAT_ID','')
    if not tok or not chat: return
    try:
        payload = json.dumps({'chat_id':chat,'text':msg}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{tok}/sendMessage',
            data=payload, headers={'Content-Type':'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f'TG error: {e}')

def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return ''

def wait_for_render():
    print('Waiting for render5 to complete...')
    while True:
        # Check if daily_producer is still running
        pid = run('pgrep -f daily_producer')
        if not pid:
            # Confirm QC gate ran
            log = open(f'{LOGS}/proof_render5.log').read() if os.path.exists(f'{LOGS}/proof_render5.log') else ''
            if 'QUALITY SCORE' in log:
                print('Render complete')
                return log
        time.sleep(30)

def get_latest_mp4():
    files = glob.glob(f'{PIPE}/output/2026-03-14/pulse_check_*.mp4')
    files = [f for f in files if '.mp4.' not in os.path.basename(f) and 'archived' not in f and 'work' not in f]
    return max(files, key=os.path.getmtime) if files else None

def forensic_analysis(mp4):
    results = {}

    # Duration + size
    out = run(f'ffprobe -v quiet -print_format json -show_format "{mp4}" 2>/dev/null')
    try:
        d = json.loads(out)['format']
        results['duration_min'] = round(float(d['duration'])/60, 1)
        results['size_mb'] = round(int(d['size'])/1024/1024)
        results['bitrate_kbps'] = int(d.get('bit_rate',0))//1000
    except: pass

    # Sample rate
    out = run(f'ffprobe -v quiet -select_streams a:0 -show_entries stream=sample_rate,codec_name -of default=noprint_wrappers=1 "{mp4}"')
    results['audio'] = out.strip()

    # Silence gaps
    out = run(f'ffmpeg -i "{mp4}" -af silencedetect=noise=-40dB:d=2.8 -f null - 2>&1 | grep silence_duration', timeout=90)
    gaps = []
    for line in out.split('\n'):
        if 'silence_duration' in line:
            try:
                gaps.append(round(float(line.split('silence_duration:')[1].strip()), 2))
            except: pass
    results['silence_gaps'] = gaps
    results['silence_count'] = len(gaps)

    # Black frames
    out = run(f'ffmpeg -i "{mp4}" -vf blackdetect=d=0.5:pix_th=0.10 -an -f null - 2>&1 | grep black_duration', timeout=90)
    blacks = []
    for line in out.split('\n'):
        if 'black_duration' in line:
            try:
                dur = float(line.split('black_duration:')[1].strip())
                if dur > 0.5:
                    blacks.append(round(dur, 2))
            except: pass
    results['black_frames'] = blacks

    # Loudness
    out = run(f'ffmpeg -i "{mp4}" -af ebur128 -f null - 2>&1 | grep "I:" | tail -1', timeout=90)
    results['lufs'] = out.strip()

    return results

def check_voice_routing():
    """Check who actually opens the episode from the log"""
    log_path = f'{LOGS}/proof_render5.log'
    if not os.path.exists(log_path): return {}
    log = open(log_path).read()

    results = {}
    
    # Who opens?
    import re
    setups = re.findall(r'\[(\d+)\] SETUP \[(\w+)\]', log)
    if setups:
        results['opener'] = f"Segment {setups[0][0]} opened by [{setups[0][1]}]"
        results['all_voices'] = [(s[0], s[1]) for s in setups[:8]]

    # Actual voice IDs used
    tts_lines = re.findall(r'\[tts\].*?\(([\w]+) \[([\w]+)\]\)', log)
    results['tts_voices'] = tts_lines[:6]

    # num2words
    results['num2words_fired'] = '[TTS] num2words' in log or 'expand_numbers' in log or 'spoken' in log.lower()

    # PBX opener forced?
    results['pbx_opener_forced'] = 'Forcing PBX opener' in log or 'PBX opener' in log

    # Placeholder?
    results['placeholder_used'] = 'SKIPPING slot' in log or 'injecting branded placeholder' in log
    
    # QC score
    m = re.search(r'QUALITY SCORE: (\d+)/100', log)
    results['score'] = int(m.group(1)) if m else None

    return results

def gemini_full_analysis(mp4):
    """Upload to Gemini and get full analysis"""
    import google.generativeai as genai
    genai.configure(api_key=ENV['GEMINI_API_KEY'])

    size = os.path.getsize(mp4)
    print(f'Uploading {size/1024/1024:.0f}MB to Gemini...')
    tg(f'🔬 Uploading render5 to Gemini for full analysis...')

    video_file = genai.upload_file(path=mp4, mime_type='video/mp4', display_name='pulse_check_render5')
    
    while video_file.state.name == 'PROCESSING':
        time.sleep(10)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name != 'ACTIVE':
        return f'FAILED: {video_file.state.name}'

    model = genai.GenerativeModel('gemini-2.5-pro')
    prompt = """You are a professional broadcast QC analyst. Watch this ENTIRE video from start to finish.

Answer these SPECIFIC questions with exact timestamps:

1. WHO OPENS THE EPISODE? Male or female voice? What are the first words spoken after the intro?

2. VOICES: How many distinct voices? Are both voices natural-sounding or clearly AI? Note any robotic/unnatural moments with timestamps.

3. NUMBERS: How do the narrators pronounce large numbers? Do they say "seventy-four thousand" or "74,000" robotically?

4. PARTNER CLIPS: Do any clips start with channel intro logos/jingles? List which ones.

5. SILENCE GAPS: List every moment of dead air >1 second with timestamp and duration.

6. TRANSITIONS: Do you see/hear a whoosh sound effect at transitions? Or hard silent black cuts?

7. INTRO: Does the branded intro play cleanly? Any double music layering?

8. BACKGROUND MUSIC: Is it continuous throughout or does it drop?

9. BIGGEST REMAINING ISSUE preventing broadcast quality.

10. GRADE 0-100 with one-line justification.

Be extremely specific with timestamps. This is fed directly into code fixes."""

    response = model.generate_content(
        [video_file, prompt],
        generation_config={'temperature': 0.1, 'max_output_tokens': 3000},
        request_options={'timeout': 300}
    )
    return response.text

# ── MAIN ──
tg('🔬 Post-render audit monitor started — waiting for render5...')

render_log = wait_for_render()
mp4 = get_latest_mp4()

if not mp4:
    tg('❌ No MP4 found after render')
    sys.exit(1)

tg(f'✅ Render5 complete — {os.path.getsize(mp4)//1024//1024}MB\nStarting dual forensic audit...')

# My forensic analysis
print('Running forensic analysis...')
forensic = forensic_analysis(mp4)
voice = check_voice_routing()

forensic_report = f"""
📊 FORENSIC REPORT — render5
Duration: {forensic.get('duration_min')} min | {forensic.get('size_mb')}MB
Audio: {forensic.get('audio')}
Score: {voice.get('score')}/100

🎤 VOICE ROUTING:
Opener: {voice.get('opener', 'unknown')}
PBX forced: {voice.get('pbx_opener_forced')}
Voices: {voice.get('all_voices', [])[:6]}

🔢 num2words active: {voice.get('num2words_fired')}
📋 Placeholder used: {voice.get('placeholder_used')}

🔇 SILENCE GAPS ({voice.get('score')} score):
Count: {forensic.get('silence_count')} gaps
Durations: {forensic.get('silence_gaps')}

⬛ BLACK FRAMES >0.5s: {forensic.get('black_frames')}

📢 LUFS: {forensic.get('lufs')}
"""

print(forensic_report)
tg(forensic_report)

# Save forensic report
with open(f'{LOGS}/render5_forensic.log', 'w') as f:
    f.write(forensic_report)

# Gemini analysis
try:
    print('Starting Gemini analysis...')
    gemini_report = gemini_full_analysis(mp4)
    with open(f'{LOGS}/render5_gemini.log', 'w') as f:
        f.write(gemini_report)
    
    # Send key findings to TG (truncated)
    summary = gemini_report[:1500] + '...[see logs/render5_gemini.log for full]'
    tg(f'🤖 GEMINI REPORT:\n{summary}')
    print('Gemini done')
except Exception as e:
    tg(f'⚠️ Gemini analysis failed: {e}')
    print(f'Gemini error: {e}')

tg('✅ Dual audit complete. Check logs/render5_forensic.log + render5_gemini.log')
