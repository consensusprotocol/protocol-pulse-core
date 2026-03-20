#!/usr/bin/env python3
"""
gemini_grade.py — Protocol Pulse V6 Quality Gate
Submits full forensic data to Gemini 2.5 Pro for rigorous grading.
Only exits 0 (PASS) if grade == A and broadcast_ready == True.
PBX sees NOTHING until this exits 0.
"""
import os, sys, json, urllib.request, subprocess, re, time

# Load env
for line in open('/home/ultron/protocol_pulse/.env'):
    l = line.strip()
    if '=' in l and not l.startswith('#'):
        k, _, v = l.partition('=')
        k = k.strip(); v = v.strip().strip("'").strip('"')
        if k: os.environ[k] = v

GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')
LOG = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/grade_report.log'
GRADE_FILE = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/v6_gemini_grade.json'
PASS_FILE = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/v6_grade_PASS.txt'
RENDER_LOG = None  # resolved dynamically below

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()

# ── Find the output file ──────────────────────────────────────────────────────
OUTPUT_DIR = '/home/ultron/protocol_pulse/video_pipeline_v3/output'
today = time.strftime('%Y%m%d')

candidates = []
for root, dirs, files in os.walk(OUTPUT_DIR):
    for f in files:
        if f.endswith('.mp4') and 'pulse_check' in f and '.mp4.' not in os.path.basename(f) and 'bgl_audio' not in f and 'archived' not in f and 'music_mixed' not in f and 'concat_raw' not in f and 'norm' not in f:
            full = os.path.join(root, f)
            candidates.append((os.path.getmtime(full), full))

candidates.sort(reverse=True)
LATEST = candidates[0][1] if candidates else None

if not LATEST:
    log("FATAL: No MP4 output found")
    sys.exit(2)

log(f"Grading: {LATEST}")

# ── ffprobe ───────────────────────────────────────────────────────────────────
log("Running ffprobe...")
probe_raw = run(f'ffprobe -v quiet -print_format json -show_format -show_streams "{LATEST}"')
try:
    probe = json.loads(probe_raw)
    fmt = probe.get('format', {})
    streams = probe.get('streams', [])
    duration = float(fmt.get('duration', 0))
    filesize_mb = int(fmt.get('size', 0)) / 1048576
    v_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
    a_stream = next((s for s in streams if s.get('codec_type') == 'audio'), {})
    width = v_stream.get('width', 0)
    height = v_stream.get('height', 0)
    vcodec = v_stream.get('codec_name', 'unknown')
    fps_raw = v_stream.get('r_frame_rate', '0/1')
    fps_num, fps_den = fps_raw.split('/') if '/' in fps_raw else (fps_raw, '1')
    fps = round(int(fps_num) / max(int(fps_den), 1), 2)
    acodec = a_stream.get('codec_name', 'unknown')
    sample_rate = a_stream.get('sample_rate', '?')
    channels = a_stream.get('channel_layout', '?')
    num_streams = len(streams)
    bit_rate_kbps = round(int(fmt.get('bit_rate', 0)) / 1000)
except Exception as e:
    log(f"ffprobe parse error: {e}")
    duration = filesize_mb = 0
    width = height = fps = 0
    vcodec = acodec = 'unknown'
    sample_rate = channels = '?'
    num_streams = 0
    bit_rate_kbps = 0

log(f"Duration: {duration:.1f}s | Size: {filesize_mb:.1f}MB | {width}x{height} @ {fps}fps | {vcodec}/{acodec}")

# ── Black frame detection ─────────────────────────────────────────────────────
log("Running blackdetect...")
black_raw = run(f'ffmpeg -i "{LATEST}" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1 | grep black_')
black_segments = re.findall(r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)', black_raw)
# Filter out very short blacks at start/end (normal fade in/out)
black_mid = [(s,e,d) for s,e,d in black_segments
             if float(s) > 2.0 and float(e) < duration - 2.0]
black_count_total = len(black_segments)
black_count_mid = len(black_mid)
log(f"Black segments: {black_count_total} total, {black_count_mid} mid-video (problem ones)")

# ── Silence detection ─────────────────────────────────────────────────────────
log("Running silencedetect...")
silence_raw = run(f'ffmpeg -i "{LATEST}" -af "silencedetect=noise=-45dB:d=0.8" -f null - 2>&1 | grep silence_')
silence_starts = re.findall(r'silence_start: ([\d.]+)', silence_raw)
silence_ends = re.findall(r'silence_end: ([\d.]+)', silence_raw)
silence_mid = [float(s) for s in silence_starts if float(s) > 2.0 and float(s) < duration - 2.0]
silence_count = len(silence_mid)
log(f"Silence gaps >0.8s mid-video: {silence_count}")

# ── EBU R128 loudness ─────────────────────────────────────────────────────────
log("Running EBU R128 loudness measurement...")
loudness_raw = run(f'ffmpeg -i "{LATEST}" -map 0:a -af "ebur128=peak=true" -f null - 2>&1')
# Parse the summary block at the end (lines starting with spaces + label + colon)
integrated_match = re.search(r'^\s+I:\s+(-[\d.]+)\s+LUFS', loudness_raw, re.MULTILINE)
true_peak_match = re.search(r'^\s+Peak:\s+(-?[\d.]+)\s+dBFS', loudness_raw, re.MULTILINE)
lra_match = re.search(r'^\s+LRA:\s+([\d.]+)\s+LU', loudness_raw, re.MULTILINE)
integrated_lufs = float(integrated_match.group(1)) if integrated_match else None
true_peak_dbfs = float(true_peak_match.group(1)) if true_peak_match else None
lra_lu = float(lra_match.group(1)) if lra_match else None
log(f"Loudness: {integrated_lufs} LUFS | True Peak: {true_peak_dbfs} dBFS | LRA: {lra_lu} LU")

# ── Freeze frame detection ────────────────────────────────────────────────────
log("Running freezedetect...")
freeze_raw = run(f'ffmpeg -i "{LATEST}" -vf "freezedetect=n=0.003:d=1.0" -an -f null - 2>&1 | grep freeze')
# Only count freezes lasting >2.0s — shorter freezes are intentional b-roll backgrounds
_freeze_durations = re.findall(r'freeze_duration:\s*([\d.]+)', freeze_raw)
freeze_count = sum(1 for d in _freeze_durations if float(d) > 2.0)
log(f"Freeze frames >2s: {freeze_count} (total detected: {len(_freeze_durations)}, short ignored)")

# ── Audio/video stream count ──────────────────────────────────────────────────
has_video = v_stream != {}
has_audio = a_stream != {}

# ── Read render log for content context ──────────────────────────────────────
# Find most recent render log by mtime (v6_render.log is stale)
render_log_content = ''
try:
    import glob as _glob
    _log_dir = '/home/ultron/protocol_pulse/video_pipeline_v3/logs'
    _candidates = (_glob.glob(f'{_log_dir}/render_*.log') +
                   _glob.glob(f'{_log_dir}/full_render_*.log') +
                   _glob.glob(f'{_log_dir}/v6_render.log'))
    _candidates = [f for f in _candidates if os.path.isfile(f)]
    # FIX 5: Only accept render logs with mtime within last 2 hours
    _fresh_cutoff = time.time() - 7200
    _candidates = [f for f in _candidates if os.path.getmtime(f) >= _fresh_cutoff]
    if _candidates:
        RENDER_LOG = max(_candidates, key=os.path.getmtime)
    else:
        RENDER_LOG = None  # No fresh render log available
    if not RENDER_LOG:
        log("No fresh render log found (within 2h) — using empty context")
        render_log_content = ''
        raise FileNotFoundError("skip")
    log(f"Using render log: {RENDER_LOG}")
    with open(RENDER_LOG) as f:
        lines = f.readlines()
    # Filter noise, keep last 50 meaningful lines
    keep = [l.strip() for l in lines if l.strip() and
            not any(x in l for x in ['urllib3', 'HTTP Request', 'DEBUG', 'WARNING: Retrying'])]
    render_log_content = '\n'.join(keep[-50:])
except:
    render_log_content = 'Render log unavailable'

# ── Build Gemini prompt ───────────────────────────────────────────────────────
log("Building Gemini grading prompt...")

PROMPT = f"""You are the Chief Quality Officer for Protocol Pulse, a daily autonomous cypherpunk Bitcoin intelligence video show viewed through an Austrian economics lens.
PBX is the SOLE host. This is a single-host show — there is no co-host, no second voice, no guest expected. Do NOT penalise for the absence of a second host.
Your job: grade this episode with maximum rigour. Be brutally honest. A grade A means it is genuinely broadcast-ready and PBX will publish it immediately. Do not hand out A grades lightly.

=== EPISODE FORENSIC DATA ===

FILE: {os.path.basename(LATEST)}
DURATION: {duration:.1f} seconds ({duration/60:.1f} minutes)
FILE SIZE: {filesize_mb:.1f} MB
BITRATE: {bit_rate_kbps} kbps
RESOLUTION: {width}x{height}
FRAMERATE: {fps} fps
VIDEO CODEC: {vcodec}
AUDIO CODEC: {acodec} | {sample_rate} Hz | {channels}
TOTAL STREAMS: {num_streams}

LOUDNESS (EBU R128):
  Integrated: {integrated_lufs} LUFS   (target: -16 to -14 LUFS)
  True Peak: {true_peak_dbfs} dBFS     (must be under -1.0 dBFS)
  LRA: {lra_lu} LU                     (target: 4-18 LU)

BLACK FRAME SEGMENTS: {black_count_total} total | {black_count_mid} mid-video
  (Mid-video blacks are critical failures. Start/end fades OK.)
  Details: {str(black_mid[:5]) if black_mid else 'none'}

SILENCE GAPS (>0.8s, mid-video): {silence_count}

FREEZE FRAMES (>1s): {freeze_count}

=== RENDER LOG (content/script details) ===
{render_log_content}

=== GRADING RUBRIC ===

Grade each dimension 1-10. Then calculate weighted overall score.

TECHNICAL QUALITY (40% weight):
1. duration_check: 480-900s ideal (8-15min). Under 180s = automatic F. 300-480s acceptable but short. Over 900s penalise.
2. resolution_check: 1920x1080 = 10. 1280x720 = 7. Anything else = fail.
3. framerate_check: 24-30fps = 10. Under 24fps = 5. Under 15fps = 0.
4. loudness_check: -16 to -14 LUFS = 10. -18 to -12 LUFS = 7. Outside -20 to -10 = critical failure (score 0).
5. true_peak_check: Under -1 dBFS = 10. -1 to 0 = 7. Over 0 dBFS = critical failure (clipping).
6. black_frames_check: 0 mid-video blacks = 10. 1 = 6. 2+ = critical failure (score 0).
7. silence_check: 0 gaps = 10. 1-2 gaps = 6. 3+ = major issue (score 3).
8. freeze_check: 0 freezes = 10. 1 = 5. 2+ = critical failure.
9. codec_check: h264/aac = 10. h265/aac = 10. Other combos = 5.
10. file_integrity_check: Clean container, both streams present, reasonable bitrate (500-5000 kbps) = 10.

CONTENT QUALITY (35% weight):
11. clip_relevance: Are clips from real Bitcoin news? Are the sources credible (not altcoin shills, not 24/7 loops)? Preston Pysh, Lyn Alden, Robert Breedlove, TFTC, and Simply Bitcoin rank editorially higher — clips from these sources are a positive signal. Austrian economics framing (sound money, Cantillon effect, time preference, proof-of-work ethos) is a positive editorial signal. Signal Active Nostr content (npubs, zaps, relay discussion) is a feature, not a bug — do not penalise.
12. script_quality: Is the narration between clips informed, specific, and adds value beyond just re-reading the clips?
13. cold_open_hook: Does the episode open with a compelling, specific hook that makes you want to keep watching?
14. narrative_arc: Does the episode flow logically from open -> clips -> analysis -> close? Or is it random?
15. host_authenticity: PBX is the SOLE host — score 10/10 if PBX voice is clean, natural, authoritative, and well-paced throughout. Do NOT penalise for absence of a second host or co-host. Only deduct for dead air, robotic tone, or missing audio in PBX's voice.
16. episode_title: Is the title specific and punchy? Not generic clickbait. Should reflect the actual main story.
17. no_filler: No ad reads, no sponsor segments, no off-topic content, no repeated clips.
18. timeliness: Is the content from today or yesterday? Not stale week-old news.

PRODUCTION QUALITY (25% weight):
19. music_mix: Background music present at proper level, not overpowering narration. Sidechain ducking working?
20. transitions: Are there clean glitch transitions between segments? No hard cuts mid-sentence.
21. visual_polish: Cyberpunk aesthetic consistent. Lower thirds present. No graphical glitches.
22. no_artifacts: No stuttering, no looping, no corrupted frames visible.
23. audio_quality: Narration clear, no clipping, no echo, no background noise in voiceover.
24. pacing: Does the episode feel tight? Not dragging? Not too rushed?

=== YOUR RESPONSE ===

You MUST respond ONLY with valid JSON. No preamble, no explanation, no markdown fences. Raw JSON only.

{{
  "grade": "A|B|C|D|F",
  "overall_score": 0-100,
  "broadcast_ready": true|false,
  "technical_score": 0-100,
  "content_score": 0-100,
  "production_score": 0-100,
  "dimensions": {{
    "duration_check": {{"score": 0-10, "note": "explain"}},
    "resolution_check": {{"score": 0-10, "note": "explain"}},
    "framerate_check": {{"score": 0-10, "note": "explain"}},
    "loudness_check": {{"score": 0-10, "note": "explain"}},
    "true_peak_check": {{"score": 0-10, "note": "explain"}},
    "black_frames_check": {{"score": 0-10, "note": "explain"}},
    "silence_check": {{"score": 0-10, "note": "explain"}},
    "freeze_check": {{"score": 0-10, "note": "explain"}},
    "codec_check": {{"score": 0-10, "note": "explain"}},
    "file_integrity_check": {{"score": 0-10, "note": "explain"}},
    "clip_relevance": {{"score": 0-10, "note": "explain"}},
    "script_quality": {{"score": 0-10, "note": "explain"}},
    "cold_open_hook": {{"score": 0-10, "note": "explain"}},
    "narrative_arc": {{"score": 0-10, "note": "explain"}},
    "host_authenticity": {{"score": 0-10, "note": "explain"}},
    "episode_title": {{"score": 0-10, "note": "explain"}},
    "no_filler": {{"score": 0-10, "note": "explain"}},
    "timeliness": {{"score": 0-10, "note": "explain"}},
    "music_mix": {{"score": 0-10, "note": "explain"}},
    "transitions": {{"score": 0-10, "note": "explain"}},
    "visual_polish": {{"score": 0-10, "note": "explain"}},
    "no_artifacts": {{"score": 0-10, "note": "explain"}},
    "audio_quality": {{"score": 0-10, "note": "explain"}},
    "pacing": {{"score": 0-10, "note": "explain"}}
  }},
  "critical_failures": [],
  "warnings": [],
  "strengths": [],
  "verdict": "One punchy sentence summarising the episode quality",
  "recommendation": "PUBLISH|FIX_AND_RERENDER|DO_NOT_PUBLISH"
}}

Grade thresholds:
- A: overall_score >= 88, zero critical_failures, broadcast_ready = true
- B: overall_score 75-87, at most 1 minor critical failure
- C: overall_score 60-74
- D: overall_score 40-59
- F: overall_score < 40 OR duration < 180s OR clipping OR 2+ mid-video black segments
Note: Episodes 8-15 minutes (480-900s) are the ideal target format. 5 clips is the target.
"""

# ── Call Gemini ───────────────────────────────────────────────────────────────
log("Calling Gemini 2.5 Pro for grading (this may take 30-60s)...")

url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}'
payload = {
    'contents': [{'parts': [{'text': PROMPT}]}],
    'generationConfig': {'maxOutputTokens': 8000, 'temperature': 0.05}
}

req_obj = urllib.request.Request(url,
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req_obj, timeout=90) as resp:
        d = json.loads(resp.read())
        parts = d['candidates'][0]['content'].get('parts', [])
        text = next((p['text'] for p in parts if 'text' in p), None)
        if not text:
            log("FATAL: Gemini returned no text")
            sys.exit(2)
except urllib.error.HTTPError as e:
    log(f"FATAL: Gemini HTTP error {e.code}: {e.read().decode()[:200]}")
    sys.exit(2)
except Exception as e:
    log(f"FATAL: Gemini call failed: {e}")
    sys.exit(2)

# ── Parse result ──────────────────────────────────────────────────────────────
clean = text.strip()
if '```json' in clean:
    clean = clean.split('```json')[1].split('```')[0].strip()
elif '```' in clean:
    clean = clean.split('```')[1].split('```')[0].strip()

try:
    result = json.loads(clean)
except json.JSONDecodeError as e:
    log(f"FATAL: Could not parse Gemini JSON: {e}")
    log(f"Raw response: {clean[:500]}")
    sys.exit(2)

grade = result.get('grade', 'F')
score = result.get('overall_score', 0)
broadcast = result.get('broadcast_ready', False)
recommendation = result.get('recommendation', 'DO_NOT_PUBLISH')
verdict = result.get('verdict', '')
critical = result.get('critical_failures', [])
warnings = result.get('warnings', [])
strengths = result.get('strengths', [])

# Save full grade report — legacy path + per-render timestamped copy
with open(GRADE_FILE, 'w') as f:
    json.dump(result, f, indent=2)
log(f"Grade report saved to {GRADE_FILE}")

# Per-render grade history
GRADES_DIR = '/home/ultron/protocol_pulse/video_pipeline_v3/logs/grades'
os.makedirs(GRADES_DIR, exist_ok=True)
ts_tag = time.strftime('%Y%m%d_%H%M%S')
per_render_path = os.path.join(GRADES_DIR, f'grade_{ts_tag}.json')
with open(per_render_path, 'w') as f:
    json.dump(result, f, indent=2)
log(f"Per-render grade saved to {per_render_path}")

# ── Print full scorecard ──────────────────────────────────────────────────────
log("=" * 60)
log(f"GEMINI GRADE: {grade}  |  SCORE: {score}/100  |  {recommendation}")
log(f"VERDICT: {verdict}")
log(f"Technical: {result.get('technical_score')}/100  Content: {result.get('content_score')}/100  Production: {result.get('production_score')}/100")
log("-" * 60)

dims = result.get('dimensions', {})
for dim, data in dims.items():
    s = data.get('score', '?')
    n = data.get('note', '')
    flag = '  ✓' if isinstance(s, int) and s >= 8 else ('  !' if isinstance(s, int) and s < 6 else '')
    log(f"  {dim:30s} {s}/10{flag}  {n[:80]}")

log("-" * 60)
if critical:
    log(f"CRITICAL FAILURES ({len(critical)}):")
    for c in critical:
        log(f"  !! {c}")
if warnings:
    log(f"WARNINGS ({len(warnings)}):")
    for w in warnings:
        log(f"  -- {w}")
if strengths:
    log(f"STRENGTHS ({len(strengths)}):")
    for s in strengths:
        log(f"  ++ {s}")
log("=" * 60)

# ── Record to episode memory ─────────────────────────────────────────────
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from episode_memory import record_episode
    _render_id = os.path.basename(os.path.dirname(LATEST)) or os.path.basename(LATEST).replace('.mp4', '')
    _date = time.strftime('%Y-%m-%d')
    _clips_used = []
    _manifest_path = os.path.join(os.path.dirname(LATEST), 'episode_manifest.json')
    if os.path.exists(_manifest_path):
        with open(_manifest_path) as _mf:
            _manifest = json.load(_mf)
        for _seg in _manifest.get('segments', []):
            if _seg.get('type') == 'partner_clip':
                _vpath = _seg.get('video_path', '')
                _fname = os.path.basename(_vpath)
                _parts = _fname.replace('.mp4', '').split('_', 2)
                _clip_info = {'channel': _parts[2].rsplit('_', 1)[0] if len(_parts) > 2 else 'Unknown',
                              'video_id': _parts[2].rsplit('_', 1)[-1] if len(_parts) > 2 else ''}
                _clips_used.append(_clip_info)
    record_episode(_render_id, _date, result, _clips_used)
    log(f"Episode memory recorded: {_render_id} — grade {grade}, {len(_clips_used)} clips")
except Exception as _em_err:
    log(f"[WARN] Episode memory recording failed: {_em_err}")

# ── Pass/fail gate ────────────────────────────────────────────────────────────
if grade == 'A' and broadcast and score >= 88:
    log("*** GRADE A CONFIRMED — BROADCAST READY ***")
    with open(PASS_FILE, 'w') as f:
        f.write(f"GRADE A CONFIRMED\n")
        f.write(f"File: {LATEST}\n")
        f.write(f"Score: {score}/100\n")
        f.write(f"Verdict: {verdict}\n")
        f.write(f"Graded: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"\nGRADE_A_PASS|{score}|{LATEST}|{verdict}")
    sys.exit(0)
else:
    log(f"NOT GRADE A: {grade} ({score}/100) — PBX will not be shown this render")
    print(f"\nGRADE_{grade}_FAIL|{score}|{LATEST}|{verdict}")
    sys.exit(1)
