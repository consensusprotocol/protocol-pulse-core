#!/usr/bin/env python3
"""
smart_render_loop.py - Self-improving overnight render engine.
Each iteration: render -> forensics -> grade -> extract lessons -> CC fix -> repeat.
Lessons accumulate in PIPELINE_LESSONS.md and get injected into every CC fix prompt.
Max 8 iterations or 6 hours. Grade A = lock WINNER_RECIPE.json + stop.
"""
import os, sys, json, subprocess, time, re, glob, urllib.request
from datetime import datetime

BASE = '/home/ultron/protocol_pulse'
PIPELINE = f'{BASE}/video_pipeline_v3'
LOG_DIR = f'{PIPELINE}/logs'
LOG = f'{LOG_DIR}/smart_loop.log'
LESSONS_FILE = f'{BASE}/PIPELINE_LESSONS.md'
RECIPE_FILE = f'{LOG_DIR}/WINNER_RECIPE.json'
MAX_ITER = 8
MAX_HOURS = 6

os.makedirs(LOG_DIR, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    open(LOG, 'a').write(line + '\n')

def load_env():
    env = os.environ.copy()
    try:
        with open(f'{BASE}/.env') as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith('#') and '=' in l:
                    k, _, v = l.partition('=')
                    env[k.strip()] = v.strip().strip("'").strip('"')
    except: pass
    return env

def run(cmd, timeout=7200, cwd=BASE):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                         timeout=timeout, cwd=cwd, env=load_env())

def tmux_alive(name):
    return subprocess.run(f'tmux has-session -t {name} 2>/dev/null',
                         shell=True).returncode == 0

def load_lessons():
    if not os.path.exists(LESSONS_FILE):
        return "No lessons yet - this is iteration 1."
    return open(LESSONS_FILE).read()[-3000:]  # last 3000 chars

def append_lesson(iteration, grade, score, failures, fixes_applied):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    entry = f"""
## Iteration {iteration} — {ts} — Grade {grade} ({score}/100)

### Failures:
{chr(10).join(f'- {f}' for f in failures)}

### Fixes applied:
{chr(10).join(f'- {f}' for f in fixes_applied)}

### Key insight:
{'Grade A achieved - recipe locked.' if grade == 'A' else 'Carry forward: ' + '; '.join(failures[:2])}

---
"""
    open(LESSONS_FILE, 'a').write(entry)
    log(f"Lesson appended for iteration {iteration}")

def wipe_tts_cache():
    run(f'rm -rf {PIPELINE}/tts_cache/ && mkdir -p {PIPELINE}/tts_cache/')
    log("TTS cache wiped")

def fire_render(iteration):
    log(f"Firing render iteration {iteration}...")
    wipe_tts_cache()
    log_path = f'{LOG_DIR}/render_iter{iteration}.log'
    r = subprocess.run(
        ['python3', 'daily_producer.py', '--skip-scan'],
        capture_output=True, text=True, timeout=7200,
        cwd=PIPELINE, env=load_env()
    )
    open(log_path, 'w').write(r.stdout + r.stderr)
    log(f"Render done, exit={r.returncode}")
    # find output
    today = datetime.now().strftime('%Y-%m-%d')
    candidates = []
    for pat in [f'output/{today}/*.mp4', 'output/*.mp4']:
        for f in glob.glob(f'{PIPELINE}/{pat}'):
            if not any(x in f for x in ['music_mixed','concat_raw','.norm','whoosh','placeholder']):
                candidates.append((os.path.getmtime(f), f))
    candidates.sort(reverse=True)
    if candidates:
        video = candidates[0][1]
        sz = os.path.getsize(video)
        log(f"Output: {video} ({sz//1048576}MB)")
        return video
    log("ERROR: no output file found")
    return None

def run_forensics(video):
    results = {}
    log("Running forensics...")
    # duration + size
    r = run(f'ffprobe -v quiet -print_format json -show_format "{video}"', timeout=30)
    try:
        fmt = json.loads(r.stdout).get('format', {})
        results['duration'] = float(fmt.get('duration', 0))
        results['size_mb'] = int(fmt.get('size', 0)) // 1048576
        results['bitrate_mbps'] = round(float(fmt.get('bit_rate', 0)) / 1000000, 2)
    except: pass
    # silence
    r = run(f'ffmpeg -i "{video}" -af "silencedetect=n=-50dB:d=2.0" -f null - 2>&1', timeout=300)
    results['silence_gaps'] = len(re.findall(r'silence_start', r.stdout + r.stderr))
    # true peak
    r = run(f'ffmpeg -i "{video}" -af "ebur128=peak=true" -f null - 2>&1', timeout=600)
    m = re.search(r'True peak\s*:\s*([-+\d.]+)', r.stdout + r.stderr)
    results['true_peak'] = float(m.group(1)) if m else 999
    # black frames
    r = run(f'ffmpeg -i "{video}" -vf "blackdetect=d=0.5:pix_th=0.10" -f null - 2>&1', timeout=300)
    results['black_frames'] = len(re.findall(r'black_start', r.stdout + r.stderr))
    log(f"Forensics: dur={results.get('duration',0):.0f}s peak={results.get('true_peak',999)}dBTP "
        f"silence={results.get('silence_gaps',0)} black={results.get('black_frames',0)}")
    return results

def grade_video(iteration):
    log("Grading with Gemini...")
    grade_log = f'{LOG_DIR}/grade_iter{iteration}.log'
    r = subprocess.run(['python3', 'gemini_grade.py'],
                      capture_output=True, text=True, timeout=600,
                      cwd=PIPELINE, env=load_env())
    open(grade_log, 'w').write(r.stdout + r.stderr)
    # parse grade
    for line in (r.stdout + r.stderr).split('\n'):
        m = re.search(r'GRADE_([A-F])_?(PASS|FAIL)\|(\d+)', line)
        if m:
            return m.group(1), int(m.group(3)), grade_log
    # fallback parse
    m = re.search(r'Grade ([A-F]).*?(\d+)/100', r.stdout + r.stderr)
    if m:
        return m.group(1), int(m.group(2)), grade_log
    return 'F', 0, grade_log

def extract_failures(grade_log, forensics):
    failures = []
    if os.path.exists(grade_log):
        for line in open(grade_log):
            if '!! ' in line or 'CRITICAL' in line:
                m = re.search(r'!!?\s+(.+)', line)
                if m: failures.append(m.group(1).strip()[:120])
    # add forensic failures
    if forensics.get('true_peak', 0) > -1.0:
        failures.append(f"Audio clipping: true peak {forensics['true_peak']}dBTP (limit -1.0)")
    if forensics.get('silence_gaps', 0) > 0:
        failures.append(f"Silent gaps: {forensics['silence_gaps']} gaps >2s detected")
    if forensics.get('black_frames', 0) > 0:
        failures.append(f"Black frames: {forensics['black_frames']} segments")
    dur = forensics.get('duration', 0)
    if dur < 240 or dur > 600:
        failures.append(f"Duration out of range: {dur:.0f}s (target 400-550s)")
    if forensics.get('bitrate_mbps', 0) < 3.0:
        failures.append(f"Low bitrate: {forensics.get('bitrate_mbps')}Mbps (min 3.0)")
    return failures[:8]

def fire_cc_fix(iteration, failures, grade, score):
    """CC FIX SESSIONS PERMANENTLY DISABLED.
    Were reverting proven fixes every iteration. Fixes pre-applied to source.
    """
    log(f"CC fix SKIPPED (disabled - fixes pre-applied to source before loop)")
    try:
        with open(f"{BASE}/PIPELINE_LESSONS.md", "a") as fh:
            fh.write(f"\n### Run4 Iter{iteration} Grade:{grade} Score:{score}\n")
            for fail in failures:
                fh.write(f"- {fail[:120]}\n")
    except Exception as ex:
        log(f"lessons write error: {ex}")


def main():
    log("=" * 60)
    log(f"SMART RENDER LOOP START — max {MAX_ITER} iterations, {MAX_HOURS}h")
    log("=" * 60)
    start_time = time.time()
    # init lessons file
    if not os.path.exists(LESSONS_FILE):
        open(LESSONS_FILE, 'w').write("# Pipeline Lessons Learned\n\n")
        log("Created PIPELINE_LESSONS.md")
    for iteration in range(1, MAX_ITER + 1):
        elapsed = (time.time() - start_time) / 3600
        if elapsed > MAX_HOURS:
            log(f"Max time {MAX_HOURS}h reached after {iteration-1} iterations")
            break
        log(f"\n{'='*60}")
        log(f"ITERATION {iteration}/{MAX_ITER} — {elapsed:.1f}h elapsed")
        log(f"{'='*60}")
        # render
        video = fire_render(iteration)
        if not video:
            log(f"Render failed iter {iteration}, retrying in 60s...")
            time.sleep(60)
            continue
        # forensics
        forensics = run_forensics(video)
        # grade
        grade, score, grade_log = grade_video(iteration)
        log(f"GRADE: {grade} ({score}/100)")
        # extract failures
        failures = extract_failures(grade_log, forensics)
        log(f"Failures: {failures}")
        if grade == 'A' and score >= 88:
            log("*** GRADE A — LOCKING RECIPE ***")
            recipe = {
                'iteration': iteration, 'grade': grade, 'score': score,
                'timestamp': datetime.now().isoformat(),
                'video': video, 'forensics': forensics
            }
            json.dump(recipe, open(RECIPE_FILE, 'w'), indent=2)
            append_lesson(iteration, grade, score, [], ['Grade A achieved'])
            log(f"Winner locked: {RECIPE_FILE}")
            # update handoff
            run('bash sync_handoff.sh 2>/dev/null')
            log("Handoff doc updated")
            break
        # append lesson BEFORE fixing
        fixes = fire_cc_fix(iteration, failures, grade, score)
        append_lesson(iteration, grade, score, failures, fixes or [])
        log(f"Lesson recorded. Proceeding to iteration {iteration+1}...")
    else:
        log(f"All {MAX_ITER} iterations complete")
    # write final report
    report = f"""# Smart Loop Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Iterations run: {iteration}
## Final grade: {grade} ({score}/100)
## Winner locked: {os.path.exists(RECIPE_FILE)}

## Lessons accumulated:
{load_lessons()}
"""
    open(f'{BASE}/docs/overnight_report.md', 'w').write(report)
    run('git add docs/overnight_report.md PIPELINE_LESSONS.md && git commit -m "chore: smart loop report" && git push 2>/dev/null')
    run('bash sync_handoff.sh 2>/dev/null')
    log("SMART LOOP COMPLETE")

if __name__ == '__main__':
    main()
