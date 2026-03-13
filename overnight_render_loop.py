#!/usr/bin/env python3
"""
overnight_render_loop.py - Autonomous video engine perfection loop.
Max 8 iterations, max 6 hours. Each: render -> forensics -> Gemini grade -> CC fix -> repeat.
Grade A = stop and lock WINNER_RECIPE.json.
"""
import os, sys, json, subprocess, time, re, urllib.request
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.join(BASE, 'video_pipeline_v3')
ENV_FILE = os.path.join(BASE, '.env')
LOG = os.path.join(PIPELINE, 'logs', 'overnight_loop.log')
RECIPE_FILE = os.path.join(PIPELINE, 'logs', 'WINNER_RECIPE.json')
MAX_ITERATIONS = 8
MAX_HOURS = 6

os.makedirs(os.path.join(PIPELINE, 'logs'), exist_ok=True)

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')

def load_env():
    env = os.environ.copy()
    try:
        with open(ENV_FILE) as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith('#') and '=' in l:
                    k, _, v = l.partition('=')
                    k = k.strip(); v = v.strip().strip("'").strip('"')
                    if k: env[k] = v
    except Exception as e:
        log(f"WARNING: .env load failed: {e}")
    return env

def run(cmd, timeout=7200, env=None):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                         timeout=timeout, env=env or load_env(), cwd=PIPELINE)

def gemini_call(prompt, max_tokens=8000):
    env = load_env()
    key = env.get('GEMINI_API_KEY', '')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}'
    payload = {'contents': [{'parts': [{'text': prompt}]}],
               'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.05}}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                  headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
        parts = d['candidates'][0]['content'].get('parts', [])
        return next((p['text'] for p in parts if 'text' in p), None)

def run_render(iteration):
    log(f"RENDER START iteration {iteration}")
    run("rm -rf tts_cache/ && mkdir -p tts_cache/")
    log("TTS cache wiped")
    env = load_env()
    r = run("python3 daily_producer.py --skip-scan", timeout=7200, env=env)
    log(f"Render exit: {r.returncode}")
    import glob
    today = datetime.now().strftime('%Y-%m-%d')
    candidates = []
    for pat in [f'output/{today}/*.mp4', 'output/pulse_check_*.mp4']:
        for f in glob.glob(os.path.join(PIPELINE, pat)):
            if not any(x in f for x in ['music_mixed', 'concat_raw', '.norm', 'whoosh']):
                candidates.append((os.path.getmtime(f), f))
    candidates.sort(reverse=True)
    out = candidates[0][1] if candidates else None
    if out: log(f"Output: {out} ({os.path.getsize(out)//1048576}MB)")
    else: log("FATAL: no output file")
    return out, r.stdout + r.stderr

def run_forensics(video):
    log("Running forensics...")
    res = {}
    r = run(f'ffprobe -v quiet -print_format json -show_format -show_streams "{video}"')
    try:
        p = json.loads(r.stdout)
        fmt = p.get('format', {}); streams = p.get('streams', [])
        res['duration'] = float(fmt.get('duration', 0))
        res['filesize_mb'] = int(fmt.get('size', 0)) / 1048576
        v = next((s for s in streams if s.get('codec_type') == 'video'), {})
        a = next((s for s in streams if s.get('codec_type') == 'audio'), {})
        res['width'] = v.get('width', 0); res['height'] = v.get('height', 0)
        res['fps'] = eval(v.get('r_frame_rate', '0/1').replace('/', '/'))
        res['vcodec'] = v.get('codec_name', '?'); res['acodec'] = a.get('codec_name', '?')
    except: pass
    r = run(f'ffmpeg -i "{video}" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1', timeout=300)
    segs = re.findall(r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)', r.stderr+r.stdout)
    dur = res.get('duration', 0)
    res['black_mid_count'] = len([(s,e,d) for s,e,d in segs if float(s)>2 and float(e)<dur-2])
    r = run(f'ffmpeg -i "{video}" -af "ebur128=peak=true" -f null - 2>&1', timeout=600)
    out = r.stderr + r.stdout
    im = re.search(r'I:\s*([-\d.]+)\s*LUFS', out)
    tp = re.search(r'True peak.*?([-\d.]+)\s*dBFS', out)
    res['integrated_lufs'] = float(im.group(1)) if im else None
    res['true_peak_dbfs'] = float(tp.group(1)) if tp else None
    r = run(f'ffmpeg -i "{video}" -vf "freezedetect=n=0.001:d=1.0" -an -f null - 2>&1', timeout=300)
    res['freeze_count'] = len(re.findall(r'freeze_start', r.stderr+r.stdout))
    log(f"Forensics: {res.get('duration',0):.0f}s {res.get('width')}x{res.get('height')} "
        f"LUFS={res.get('integrated_lufs')} TP={res.get('true_peak_dbfs')} "
        f"black={res.get('black_mid_count')} freeze={res.get('freeze_count')}")
    return res

def grade_with_gemini(video, forensics, render_log):
    log("Calling Gemini for 24-dimension grade...")
    prompt = f"""Grade this Protocol Pulse Bitcoin show episode across 24 dimensions.
Only award Grade A if you would genuinely be proud to publish it as world-class Bitcoin media.

FORENSICS:
- Duration: {forensics.get('duration',0):.1f}s ({forensics.get('duration',0)/60:.1f}min)
- Resolution: {forensics.get('width')}x{forensics.get('height')} @ {forensics.get('fps',0):.1f}fps
- Codec: {forensics.get('vcodec')} + {forensics.get('acodec')}
- Loudness: {forensics.get('integrated_lufs')} LUFS (target -16 to -14)
- True Peak: {forensics.get('true_peak_dbfs')} dBFS (must be <= -1.0)
- Black frames (mid): {forensics.get('black_mid_count',0)} (0 = perfect)
- Freeze frames: {forensics.get('freeze_count',0)} (0 = perfect)

RENDER LOG (last 200 lines):
{chr(10).join(render_log.splitlines()[-200:])}

RUBRIC (24 dimensions, Grade A = score >= 88, zero critical failures):
Technical (40%): duration, resolution, fps, loudness, true_peak, black_frames, silence, freezes, codec, file_integrity
Content (35%): clip_relevance, script_quality, cold_open, narrative_arc, host_authenticity, episode_title, no_filler, timeliness
Production (25%): music_mix, transitions, visual_polish, no_artifacts, audio_quality, pacing

Respond ONLY with raw JSON (no fences):
{{"grade":"A|B|C|D|F","overall_score":0-100,"broadcast_ready":true|false,
"dimensions":{{"duration_check":{{"score":0-10,"note":""}},"resolution_check":{{"score":0-10,"note":""}},"framerate_check":{{"score":0-10,"note":""}},"loudness_check":{{"score":0-10,"note":""}},"true_peak_check":{{"score":0-10,"note":""}},"black_frames_check":{{"score":0-10,"note":""}},"silence_check":{{"score":0-10,"note":""}},"freeze_check":{{"score":0-10,"note":""}},"codec_check":{{"score":0-10,"note":""}},"file_integrity_check":{{"score":0-10,"note":""}},"clip_relevance":{{"score":0-10,"note":""}},"script_quality":{{"score":0-10,"note":""}},"cold_open_hook":{{"score":0-10,"note":""}},"narrative_arc":{{"score":0-10,"note":""}},"host_authenticity":{{"score":0-10,"note":""}},"episode_title":{{"score":0-10,"note":""}},"no_filler":{{"score":0-10,"note":""}},"timeliness":{{"score":0-10,"note":""}},"music_mix":{{"score":0-10,"note":""}},"transitions":{{"score":0-10,"note":""}},"visual_polish":{{"score":0-10,"note":""}},"no_artifacts":{{"score":0-10,"note":""}},"audio_quality":{{"score":0-10,"note":""}},"pacing":{{"score":0-10,"note":""}}}},
"critical_failures":[],"warnings":[],"strengths":[],"targeted_fix_instructions":"Precise instructions for CC session to fix only failing dimensions - file, function, lines.",
"verdict":"One punchy sentence"}}"""
    text = gemini_call(prompt, 8000)
    if not text: return None
    clean = text.strip()
    for fence in ['```json', '```']:
        if fence in clean:
            clean = clean.split(fence)[1].split('```')[0].strip()
    try: return json.loads(clean)
    except: log(f"JSON parse fail: {clean[:200]}"); return None

def fire_cc_fix(iteration, grade_result):
    failures = grade_result.get('critical_failures', [])
    dims = grade_result.get('dimensions', {})
    failing = [(k, v['score'], v.get('note','')) for k,v in dims.items()
               if isinstance(v.get('score'), int) and v['score'] < 7]
    failing.sort(key=lambda x: x[1])
    prompt = f"""# PIPELINE FIX - ITERATION {iteration} - GRADE {grade_result.get('grade')} ({grade_result.get('overall_score')}/100)
VERDICT: {grade_result.get('verdict','')}
CRITICAL FAILURES: {chr(10).join(f'- {f}' for f in failures) or 'None'}
FAILING DIMS (<7/10): {chr(10).join(f'- {k}: {s}/10 - {n[:80]}' for k,s,n in failing[:8]) or 'None'}
FIX INSTRUCTIONS: {grade_result.get('targeted_fix_instructions','')}

Read PIPELINE_LAWS.md first. Fix ONLY failing dimensions. Run regression_test.sh after every change.
Commit: git add -A && git commit -m "fix(pipeline): iter{iteration}" && git push"""
    pf = os.path.join(PIPELINE, f'logs/cc_fix_iter{iteration}.md')
    with open(pf, 'w') as f: f.write(prompt)
    sn = f'fix_iter{iteration}'
    subprocess.run(f'tmux kill-session -t {sn} 2>/dev/null', shell=True)
    subprocess.run(f'tmux new-session -d -s {sn}', shell=True)
    subprocess.run(f"tmux send-keys -t {sn} 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter", shell=True)
    time.sleep(10)
    subprocess.run(f"tmux send-keys -t {sn} \"$(cat {pf})\" Enter", shell=True)
    log(f"CC session {sn} launched")
    deadline = time.time() + 2700
    while time.time() < deadline:
        time.sleep(60)
        r = subprocess.run(f'tmux has-session -t {sn} 2>/dev/null', shell=True)
        if r.returncode != 0: log("CC session ended"); break
        log(f"CC running... {int((deadline-time.time())/60)}min left")
    time.sleep(30)

def main():
    log("="*60)
    log(f"OVERNIGHT LOOP START | max {MAX_ITERATIONS} iters | max {MAX_HOURS}h")
    log("="*60)
    start = time.time()
    grade_result = {}
    for iteration in range(1, MAX_ITERATIONS+1):
        if (time.time()-start)/3600 >= MAX_HOURS:
            log(f"TIME LIMIT ({MAX_HOURS}h). Stopping."); break
        log(f"\n{'='*60}\nITERATION {iteration}/{MAX_ITERATIONS}\n{'='*60}")
        video, rlog = run_render(iteration)
        if not video:
            log("Render failed, skipping"); time.sleep(60); continue
        forensics = run_forensics(video)
        grade_result = grade_with_gemini(video, forensics, rlog)
        if not grade_result:
            log("Grading failed, skipping"); continue
        gf = os.path.join(PIPELINE, f'logs/grade_iter{iteration}.json')
        with open(gf, 'w') as f: json.dump(grade_result, f, indent=2)
        grade = grade_result.get('grade','F')
        score = grade_result.get('overall_score', 0)
        broadcast = grade_result.get('broadcast_ready', False)
        log(f"GRADE: {grade} | SCORE: {score}/100 | BROADCAST: {broadcast}")
        log(f"VERDICT: {grade_result.get('verdict','')}")
        for dim, data in grade_result.get('dimensions',{}).items():
            s = data.get('score','?')
            flag = ' ✓' if isinstance(s,int) and s>=8 else (' !!' if isinstance(s,int) and s<6 else '')
            log(f"  {dim:30s} {s}/10{flag}")
        if grade == 'A' and broadcast and score >= 88:
            log("*** GRADE A — LOCKING WINNER RECIPE ***")
            recipe = {'winner': True, 'iteration': iteration, 'timestamp': datetime.now().isoformat(),
                     'video': video, 'grade': grade, 'score': score,
                     'verdict': grade_result.get('verdict'), 'dimensions': grade_result.get('dimensions',{})}
            with open(RECIPE_FILE, 'w') as f: json.dump(recipe, f, indent=2)
            log(f"WINNER: {RECIPE_FILE}")
            break
        log(f"Grade {grade} - firing CC fix...")
        fire_cc_fix(iteration, grade_result)
    else:
        log(f"Max iterations reached without Grade A")
        with open(os.path.join(PIPELINE,'logs/overnight_diagnostic.json'),'w') as f:
            json.dump({'final_grade': grade_result}, f, indent=2)
    log("OVERNIGHT LOOP COMPLETE")

if __name__ == '__main__':
    main()
