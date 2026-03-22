#!/usr/bin/env python3
"""
overnight_render_loop.py - Autonomous video engine perfection loop.
Max 8 iterations, max 6 hours. Each: render -> forensics -> Gemini grade -> CC fix -> repeat.
Grade A = stop and lock WINNER_RECIPE.json.

Production modes:
  python3 overnight_render_loop.py              # single cycle (for cron)
  python3 overnight_render_loop.py --daemon     # continuous loop, runs at 08:00 ET daily
  python3 overnight_render_loop.py --dry-run    # startup checks only, no render
  python3 overnight_render_loop.py --help       # show args

Cron entry:
  0 12 * * * cd /home/ultron/protocol_pulse && python3 overnight_render_loop.py >> /tmp/overnight_loop.log 2>&1
"""
import os, sys, json, subprocess, time, re, urllib.request, argparse, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.join(BASE, 'video_pipeline_v3')
ENV_FILE = os.path.join(BASE, '.env')
LOG = os.path.join(PIPELINE, 'logs', 'overnight_loop.log')
RECIPE_FILE = os.path.join(PIPELINE, 'logs', 'WINNER_RECIPE.json')
HEARTBEAT_FILE = os.path.join(BASE, 'logs', 'loop_heartbeat.json')
ELEVENLABS_QUOTA_SENTINEL = os.path.join(BASE, 'logs', 'elevenlabs_quota_exhausted')
MAX_ITERATIONS = 8
MAX_HOURS = 6
RETRY_WAIT_SECONDS = 1800  # 30 minutes
MAX_ATTEMPTS_PER_CYCLE = 2

os.makedirs(os.path.join(PIPELINE, 'logs'), exist_ok=True)
os.makedirs(os.path.join(BASE, 'logs'), exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────
logger = logging.getLogger('overnight_loop')
logger.setLevel(logging.DEBUG)
_fmt = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt)
logger.addHandler(_sh)
_fh = logging.FileHandler(LOG)
_fh.setFormatter(_fmt)
logger.addHandler(_fh)


def log(msg):
    """Backward-compat wrapper."""
    logger.info(msg)


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
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                             timeout=timeout, env=env or load_env(), cwd=PIPELINE)
    except subprocess.TimeoutExpired as e:
        log(f"TIMEOUT after {timeout}s: {str(cmd)[:80]}")
        # Return a fake CompletedProcess so callers don't crash
        import subprocess as _sp
        r = _sp.CompletedProcess(cmd, returncode=-1)
        r.stdout = ""
        r.stderr = f"TIMEOUT after {timeout}s"
        return r
    except Exception as e:
        log(f"run() error: {e} cmd={str(cmd)[:80]}")
        import subprocess as _sp
        r = _sp.CompletedProcess(cmd, returncode=-1)
        r.stdout = ""
        r.stderr = str(e)
        return r


# ── FIX 6: Startup checks ────────────────────────────────────────
def startup_checks():
    """Verify environment before any render. Returns True if all pass."""
    ok = True

    # FFmpeg available
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            log("STARTUP FAIL: ffmpeg returned non-zero")
            ok = False
        else:
            ver = r.stdout.split('\n')[0] if r.stdout else '?'
            log(f"FFmpeg: {ver}")
    except FileNotFoundError:
        log("STARTUP FAIL: ffmpeg not found in PATH")
        ok = False
    except Exception as e:
        log(f"STARTUP FAIL: ffmpeg check error: {e}")
        ok = False

    # Python path includes pipeline
    if PIPELINE not in sys.path:
        sys.path.insert(0, PIPELINE)
    log(f"Pipeline dir: {PIPELINE} (exists={os.path.isdir(PIPELINE)})")
    if not os.path.isdir(PIPELINE):
        log("STARTUP FAIL: video_pipeline_v3 directory missing")
        ok = False

    # Output directory writable
    out_dir = os.path.join(PIPELINE, 'output')
    os.makedirs(out_dir, exist_ok=True)
    test_file = os.path.join(out_dir, '.write_test')
    try:
        with open(test_file, 'w') as f:
            f.write('ok')
        os.remove(test_file)
        log(f"Output dir writable: {out_dir}")
    except Exception as e:
        log(f"STARTUP FAIL: output dir not writable: {e}")
        ok = False

    # TTS provider check
    local_tts = Path(os.path.expanduser("~/protocol_pulse/video_pipeline_v3/tts_local.py")).exists()
    env = load_env()
    elevenlabs_key = bool(env.get('ELEVENLABS_API_KEY', '').strip())
    quota_exhausted = os.path.exists(ELEVENLABS_QUOTA_SENTINEL)

    if local_tts:
        log("TTS provider: LOCAL (tts_local.py found)")
    elif elevenlabs_key and not quota_exhausted:
        log("TTS provider: ElevenLabs (API key present)")
    elif elevenlabs_key and quota_exhausted:
        log("WARNING: ElevenLabs key present but quota sentinel exists")
    else:
        log("WARNING: No TTS provider found (no local TTS, no ElevenLabs key)")

    if not local_tts and not elevenlabs_key:
        log("STARTUP FAIL: No TTS provider available")
        ok = False

    return ok


# ── FIX 3: Heartbeat ─────────────────────────────────────────────
_total_episodes = 0
_consecutive_failures = 0


def write_heartbeat(verdict, duration_s):
    """Write heartbeat JSON after every cycle."""
    global _total_episodes, _consecutive_failures
    if verdict == "PASS":
        _total_episodes += 1
        _consecutive_failures = 0
    elif verdict == "ERROR":
        _consecutive_failures += 1
    elif verdict == "HOLD":
        _consecutive_failures += 1
    # DEGRADED counts as partial success
    elif verdict == "DEGRADED":
        _total_episodes += 1
        _consecutive_failures = 0

    heartbeat = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "last_verdict": verdict,
        "last_duration": round(duration_s, 1),
        "total_episodes": _total_episodes,
        "consecutive_failures": _consecutive_failures,
    }
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            json.dump(heartbeat, f, indent=2)
        log(f"Heartbeat written: {verdict} | failures={_consecutive_failures}")
    except Exception as e:
        log(f"WARNING: heartbeat write failed: {e}")

    # Telegram alert on 3+ consecutive failures
    if _consecutive_failures >= 3:
        send_telegram_alert(
            f"🚨 Protocol Pulse loop: {_consecutive_failures} consecutive failures\n"
            f"Last verdict: {verdict}\n"
            f"Time: {heartbeat['last_run']}"
        )


def send_telegram_alert(message):
    """Send alert via Telegram if bot token + chat ID are configured."""
    env = load_env()
    token = env.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = env.get('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id:
        log("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            log(f"Telegram alert sent (status {r.status})")
    except Exception as e:
        log(f"Telegram alert failed: {e}")


# ── FIX 4: TTS provider awareness ────────────────────────────────
def check_tts_ready():
    """Check TTS availability before render. Returns (ready, provider_name)."""
    local_tts = Path(os.path.expanduser("~/protocol_pulse/video_pipeline_v3/tts_local.py")).exists()
    if local_tts:
        return True, "local (Kokoro/F5-TTS)"

    env = load_env()
    if not env.get('ELEVENLABS_API_KEY', '').strip():
        return False, "none"

    if os.path.exists(ELEVENLABS_QUOTA_SENTINEL):
        log("ElevenLabs quota sentinel exists — skipping render")
        return False, "elevenlabs (quota exhausted)"

    return True, "ElevenLabs"


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
    for pat in [f'output/{today}/*.mp4']:  # today-only — no stale fallback
        for f in glob.glob(os.path.join(PIPELINE, pat)):
            if any(x in f for x in ['.bgl_audio', '.intro_mus', '.concat_raw', '.music_mixed', '.whoosh', '.norm']):
                continue
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
    r = run(f'ffmpeg -i "{video}" -af "ebur128=peak=true" -f null - 2>&1', timeout=120)
    out = r.stderr + r.stdout
    im = re.search(r'I:\s*([-\d.]+)\s*LUFS', out)
    tp = re.search(r'True peak.*?([-\d.]+)\s*dBFS', out)
    res['integrated_lufs'] = float(im.group(1)) if im else None
    res['true_peak_dbfs'] = float(tp.group(1)) if tp else None
    r = run(f'ffmpeg -i "{video}" -vf "freezedetect=n=0.001:d=1.0" -an -f null - 2>&1', timeout=300)
    res['freeze_count'] = len(re.findall(r'freeze_start', r.stderr+r.stdout))

    # TTS ARTIFACT CHECK — run in isolated subprocess with hard 45s timeout
    # Prevents WhisperModel from blocking forensics pipeline
    tts_artifacts = []
    try:
        import subprocess as _sp, tempfile as _tf, os as _os, json as _json
        with _tf.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
        _sp.run(['ffmpeg', '-y', '-i', video, '-t', '60', '-ar', '16000',
                 '-ac', '1', tmp_path], capture_output=True, timeout=30)
        # Run whisper in subprocess so it cannot block the loop
        checker = (
            "import sys, json\n"
            "from faster_whisper import WhisperModel\n"
            "model = WhisperModel('tiny', device='cpu', compute_type='int8')\n"
            "segs, _ = model.transcribe(sys.argv[1], language='en')\n"
            "t = ' '.join(s.text for s in segs).lower()\n"
            "bad = ['pause','breath','emphasis','break colon','slash','open bracket','close bracket']\n"
            "print(json.dumps([w for w in bad if w in t]))\n"
        )
        r = _sp.run(['python3', '-c', checker, tmp_path],
                    capture_output=True, text=True, timeout=45)
        if r.returncode == 0 and r.stdout.strip():
            tts_artifacts = _json.loads(r.stdout.strip())
        _os.unlink(tmp_path)
    except Exception as _e:
        log(f"TTS artifact check skipped: {_e}")
    res['tts_artifacts'] = tts_artifacts
    if tts_artifacts:
        log(f"TTS ARTIFACT ALERT: narrator reading markers aloud: {tts_artifacts}")
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


def run_single_render():
    """Execute one full perfection loop (up to MAX_ITERATIONS). Returns verdict string."""
    log("="*60)
    log(f"OVERNIGHT LOOP START | max {MAX_ITERATIONS} iters | max {MAX_HOURS}h")
    log("="*60)
    start = time.time()
    grade_result = {}
    final_verdict = "ERROR"

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
            final_verdict = "PASS"
            break
        elif grade in ('B', 'C') and broadcast:
            final_verdict = "DEGRADED"
        log(f"Grade {grade} - firing CC fix...")
        fire_cc_fix(iteration, grade_result)
    else:
        log("Max iterations reached without Grade A")
        with open(os.path.join(PIPELINE,'logs/overnight_diagnostic.json'),'w') as f:
            json.dump({'final_grade': grade_result}, f, indent=2)
        if final_verdict == "ERROR":
            final_verdict = "HOLD"

    log("OVERNIGHT LOOP COMPLETE")
    return final_verdict


def run_cycle():
    """FIX 1+2: Run a single render cycle with exception handling and retry logic."""
    cycle_start = time.time()

    # FIX 4: Check TTS before render
    tts_ready, tts_provider = check_tts_ready()
    log(f"TTS provider: {tts_provider}")
    if not tts_ready:
        log(f"[loop] TTS not available ({tts_provider}) — skipping cycle")
        write_heartbeat("ERROR", time.time() - cycle_start)
        return

    for attempt in range(1, MAX_ATTEMPTS_PER_CYCLE + 1):
        log(f"[loop] Attempt {attempt}/{MAX_ATTEMPTS_PER_CYCLE}")
        try:
            verdict = run_single_render()
        except Exception as e:
            logger.error(f"[loop] Render cycle exception: {e}", exc_info=True)
            verdict = "ERROR"

        if verdict in ("PASS", "DEGRADED"):
            write_heartbeat(verdict, time.time() - cycle_start)
            return

        # Failed — retry logic
        if attempt < MAX_ATTEMPTS_PER_CYCLE:
            log(f"[loop] Attempt {attempt} failed ({verdict}), waiting {RETRY_WAIT_SECONDS//60}min before retry...")
            time.sleep(RETRY_WAIT_SECONDS)
        else:
            log(f"[loop] All {MAX_ATTEMPTS_PER_CYCLE} attempts failed — waiting for next scheduled cycle")

    write_heartbeat(verdict, time.time() - cycle_start)


# ── FIX 5: Daemon mode ───────────────────────────────────────────
def sleep_until_next_8am_et():
    """Sleep until next 08:00 ET (12:00 UTC or 11:00 UTC during DST)."""
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    now = datetime.now(et)
    target = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    wait = (target - now).total_seconds()
    log(f"[daemon] Sleeping {wait/3600:.1f}h until {target.isoformat()}")
    time.sleep(wait)


def main():
    parser = argparse.ArgumentParser(
        description="Protocol Pulse overnight render loop — production hardened",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 overnight_render_loop.py              # single cycle\n"
            "  python3 overnight_render_loop.py --daemon      # continuous, 08:00 ET daily\n"
            "  python3 overnight_render_loop.py --dry-run     # startup checks only\n"
        )
    )
    parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon (loop at 08:00 ET daily)")
    parser.add_argument("--dry-run", action="store_true", help="Run startup checks only, no render")
    args = parser.parse_args()

    # FIX 6: Startup checks always run
    log("="*60)
    log("STARTUP CHECKS")
    log("="*60)
    if not startup_checks():
        log("STARTUP CHECKS FAILED — exiting")
        sys.exit(1)
    log("All startup checks passed")

    if args.dry_run:
        log("--dry-run mode: startup checks passed, exiting")
        sys.exit(0)

    # Load existing heartbeat state
    global _total_episodes, _consecutive_failures
    try:
        with open(HEARTBEAT_FILE) as f:
            hb = json.load(f)
            _total_episodes = hb.get('total_episodes', 0)
            _consecutive_failures = hb.get('consecutive_failures', 0)
        log(f"Heartbeat loaded: episodes={_total_episodes}, consecutive_failures={_consecutive_failures}")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    if args.daemon:
        log("DAEMON MODE — will loop at 08:00 ET daily")
        while True:
            run_cycle()
            sleep_until_next_8am_et()
    else:
        run_cycle()


if __name__ == '__main__':
    main()
