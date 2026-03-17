#!/usr/bin/env python3
"""
PREFLIGHT.PY v2 — Protocol Pulse Pipeline Smoke Gate
=====================================================
<15 second runtime. Catches every class of failure seen in production.

Exit 0 = safe to render. Exit 1 = DO NOT render.

Usage:
  python3 preflight.py           # full check inc. live TTS
  python3 preflight.py --no-tts  # skip live ElevenLabs call
"""

import os, sys, ast, json, re, time, tempfile, argparse, subprocess
from datetime import datetime

BASE = '/home/ultron/protocol_pulse'
V3   = f'{BASE}/video_pipeline_v3'

PASS = '\033[92m✅ PASS\033[0m'
FAIL = '\033[91m❌ FAIL\033[0m'
HEAD = '\033[96m'
RST  = '\033[0m'

results = []

def chk(name, passed, detail=''):
    print(f'  {PASS if passed else FAIL}  {name}' + (f'\n         → {detail}' if detail and not passed else ''))
    results.append((name, passed, detail))
    return passed

def sec(title):
    print(f'\n{HEAD}── {title} {"─"*(52-len(title))}{RST}')

def env():
    e = {}
    if os.path.exists(f'{BASE}/.env'):
        for ln in open(f'{BASE}/.env'):
            ln = ln.strip()
            if ln and not ln.startswith('#') and '=' in ln:
                k, v = ln.split('=', 1)
                e[k.strip()] = v.strip()
    return e

# ── 1. SYNTAX ─────────────────────────────────────────────
def check_syntax():
    sec('SYNTAX & COMPILE')
    ok = True
    for name in ['tts_engine.py', 'daily_producer.py', 'assembler.py']:
        path = f'{V3}/{name}'
        if not os.path.exists(path):
            chk(f'Exists: {name}', False, f'NOT FOUND: {path}'); ok = False; continue
        try:
            ast.parse(open(path).read())
            chk(f'Syntax OK: {name}', True)
        except SyntaxError as e:
            chk(f'Syntax OK: {name}', False, str(e)); ok = False
    return ok

# ── 2. REQUIRED CONSTANTS ─────────────────────────────────
def check_constants():
    sec('REQUIRED CONSTANTS — tts_engine.py')
    ok = True
    c = open(f'{V3}/tts_engine.py').read() if os.path.exists(f'{V3}/tts_engine.py') else ''

    for const, val in [('SILENCE_GAP', '0.3'), ('MAX_CHUNK_CHARS', '500'), ('VOICE_MODES', '{')]:
        present = bool(re.search(rf'^{const}\s*=', c, re.MULTILINE))
        if not chk(f'Constant: {const} = {val}', present,
                   f'MISSING — add: {const} = {val}'):
            ok = False

    # _KEY_CACHE — must exist exactly once
    kc = len(re.findall(r'^_KEY_CACHE', c, re.MULTILINE))
    if not chk(f'_KEY_CACHE declared (x{kc})', kc == 1,
               f'Found {kc} declarations — deduplicate to exactly 1'):
        ok = False
    return ok

# ── 3. BANNED PATTERNS ────────────────────────────────────
def check_banned():
    sec('BANNED PATTERNS')
    ok = True
    tts = open(f'{V3}/tts_engine.py').read() if os.path.exists(f'{V3}/tts_engine.py') else ''
    asm = open(f'{V3}/assembler.py').read()   if os.path.exists(f'{V3}/assembler.py')   else ''

    # Banned voice (returns 200 + 0 bytes silently)
    if not chk('Banned voice absent: uxKr2vlA4hYgXZR1oPRT',
               'uxKr2vlA4hYgXZR1oPRT' not in tts,
               'BANNED voice ID in tts_engine.py — delete immediately'):
        ok = False

    # Wrong sample rates
    for pat in ['r=44100', 'ar 44100', '-ar 44100', 'cl=mono']:
        if not chk(f'No legacy rate: "{pat}"', pat not in tts,
                   f'{pat} still present — must be 48000Hz stereo'):
            ok = False

    # assembler: ban BARE 0xFF0000 (no @) — atmospheric @0.xx are OK per PIPELINE_LAWS
    bare_red = bool(re.search(r'0xFF0000[^@\s]', asm))
    if not chk('No bare 0xFF0000 in assembler', not bare_red,
               'Bare 0xFF0000 found (no opacity) — use COLOR_RED (0xFF3333)'):
        ok = False

    # assembler: 0xFF0033 always banned (off-spec red)
    if not chk('No 0xFF0033 off-spec red', '0xFF0033' not in asm,
               '0xFF0033 found — replace with COLOR_RED (0xFF3333)'):
        ok = False

    # assembler: ban BARE 0xFFFFFF (no @) — with opacity is OK for subtle UI
    bare_white = bool(re.search(r'0xFFFFFF[^@]', asm))
    if not chk('No bare 0xFFFFFF in assembler', not bare_white,
               'Bare 0xFFFFFF found — use COLOR_WHITE (0xF4F5F8)'):
        ok = False

    return ok

# ── 4. ENVIRONMENT ────────────────────────────────────────
def check_env():
    sec('ENVIRONMENT')
    ok = True
    e = env()

    if not chk('TTS_PROVIDER=elevenlabs', e.get('TTS_PROVIDER','').lower() == 'elevenlabs',
               f'TTS_PROVIDER={e.get("TTS_PROVIDER","MISSING")!r}'):
        ok = False

    for key in ['ELEVENLABS_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY']:
        val = e.get(key, '')
        if not chk(f'{key} set', len(val) > 10, f'{key} missing/empty in .env'):
            ok = False
    return ok

# ── 5. VOICE IDs ──────────────────────────────────────────
def check_voices():
    sec('VOICE IDs — SINGLE HOST PBX')
    c = open(f'{V3}/tts_engine.py').read() if os.path.exists(f'{V3}/tts_engine.py') else ''
    chk('PBX voice present: HmUVvDlHsEz0m3eUGLgu', 'HmUVvDlHsEz0m3eUGLgu' in c,
        'PBX voice ID missing from tts_engine.py')
    chk('Banned voice absent: uxKr2vlA4hYgXZR1oPRT', 'uxKr2vlA4hYgXZR1oPRT' not in c,
        'BANNED voice in tts_engine.py — causes silent 0-byte audio')
    chk('Banned Eryn voice absent: kdnRe2koJdOK4Ovxn2DI',
        'kdnRe2koJdOK4Ovxn2DI' not in c,
        'Eryn voice ID still in tts_engine.py — BANNED since Render20')
    chk('Deborah voice absent (HOST_1 removed)', 'VeCVR24o7g2y1IxLJzZs' not in c,
        'Deborah voice ID still in tts_engine.py — Option A requires PBX only')

    # FIX 1: Live HTTP check — verify PBX voice ID exists on ElevenLabs
    import urllib.request as ul
    e = env()
    api_key = e.get('ELEVENLABS_API_KEY', '')
    if api_key:
        try:
            req = ul.Request('https://api.elevenlabs.io/v1/voices/HmUVvDlHsEz0m3eUGLgu',
                             headers={'xi-api-key': api_key})
            with ul.urlopen(req, timeout=10) as r:
                chk('PBX voice live HTTP check (200)', r.status == 200)
        except Exception as ex:
            chk('PBX voice live HTTP check (200)', False, f'Voice ID 404 or API error: {ex}')

# ── 5B. ELEVENLABS QUOTA ─────────────────────────────────
def check_elevenlabs_quota():
    sec('ELEVENLABS QUOTA')
    import urllib.request as ul
    e = env()
    api_key = e.get('ELEVENLABS_API_KEY', '')
    if not api_key:
        chk('ElevenLabs key available for quota check', False, 'Key missing'); return
    try:
        req = ul.Request('https://api.elevenlabs.io/v1/user/subscription',
                         headers={'xi-api-key': api_key})
        with ul.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        used = data.get('character_count', 0)
        limit = data.get('character_limit', 1)
        pct = (used / limit) * 100 if limit else 100
        if pct >= 95:
            chk(f'ElevenLabs quota ({pct:.1f}% used)', False,
                f'{used:,}/{limit:,} chars — CRITICALLY LOW, render will fail')
        elif pct >= 80:
            chk(f'ElevenLabs quota ({pct:.1f}% used)', True,
                f'WARNING: {used:,}/{limit:,} chars — approaching limit')
            # Store for final report
            check_elevenlabs_quota._pct = pct
        else:
            chk(f'ElevenLabs quota ({pct:.1f}% used)', True)
        check_elevenlabs_quota._pct = pct
    except Exception as ex:
        chk('ElevenLabs quota check', False, str(ex))
check_elevenlabs_quota._pct = None

# ── 5C. DISK SPACE ───────────────────────────────────────
def check_disk_space():
    sec('DISK SPACE')
    import shutil
    usage = shutil.disk_usage(BASE)
    free_gb = usage.free / (1024 ** 3)
    if free_gb < 5:
        chk(f'Disk free space ({free_gb:.1f} GB)', False,
            f'Under 5 GB free — render will fail (need space for clips + TTS + final)')
    elif free_gb < 10:
        chk(f'Disk free space ({free_gb:.1f} GB)', True,
            f'WARNING: Under 10 GB free — monitor closely')
    else:
        chk(f'Disk free space ({free_gb:.1f} GB)', True)

# ── 5D. FFMPEG / FFPROBE BINARIES ────────────────────────
def check_ffmpeg_binaries():
    sec('FFMPEG / FFPROBE BINARIES')
    for binary in ['ffmpeg', 'ffprobe']:
        try:
            r = subprocess.run([binary, '-version'], capture_output=True, text=True, timeout=5)
            version_line = r.stdout.split('\n')[0] if r.stdout else 'unknown'
            chk(f'{binary} available ({version_line.split(" ")[2] if len(version_line.split(" ")) > 2 else "ok"})',
                r.returncode == 0)
        except FileNotFoundError:
            chk(f'{binary} available', False, f'{binary} not found in PATH')
        except Exception as ex:
            chk(f'{binary} available', False, str(ex))

# ── 5E. ANTHROPIC API PING ───────────────────────────────
def check_anthropic_api():
    sec('ANTHROPIC API')
    import urllib.request as ul
    e = env()
    api_key = e.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        chk('Anthropic API key for ping', False, 'Key missing'); return
    try:
        req = ul.Request('https://api.anthropic.com/v1/models',
                         headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01'})
        with ul.urlopen(req, timeout=10) as r:
            chk('Anthropic API reachable (200)', r.status == 200)
    except Exception as ex:
        chk('Anthropic API reachable (200)', False, str(ex))

# ── 6. ASSEMBLER CONSTANTS ────────────────────────────────
def check_assembler():
    sec('ASSEMBLER COLOR CONSTANTS')
    c = open(f'{V3}/assembler.py').read() if os.path.exists(f'{V3}/assembler.py') else ''
    for const, val in [('COLOR_RED','0xFF3333'),('COLOR_WHITE','0xF4F5F8'),('COLOR_BG','0x0A0A0F')]:
        chk(f'{const} = {val}', const in c and val in c,
            f'{const} missing or wrong value — expected {val}')

# ── 7. LIVE TTS SMOKE TEST ────────────────────────────────

def check_branded_assets():
    """Verify new branded assets exist and are non-empty."""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
    required = [
        ('intro_tag.mp4',        1_000_000),   # min 1MB
        ('bg_loop.mp4',          10_000_000),  # min 10MB
        ('outro_branded_new.mp4', 1_000_000),  # min 1MB
        ('intro_music.mp3',       100_000),    # min 100KB
        ('logo_protocol_pulse.png', 10_000),   # min 10KB
    ]
    for fname, min_size in required:
        fpath = os.path.join(base, fname)
        if not os.path.exists(fpath):
            chk(f'Branded asset missing: {fname}', False)
        elif os.path.getsize(fpath) < min_size:
            chk(f'Branded asset too small: {fname} ({os.path.getsize(fpath)}B < {min_size}B)', False)
        else:
            chk(f'Branded asset present: {fname}', True)

def check_tts_smoke():
    sec('LIVE TTS SMOKE TEST — PBX VOICE')
    import urllib.request as ul
    e = env()
    api_key = e.get('ELEVENLABS_API_KEY', '')
    if not api_key:
        chk('ElevenLabs key available', False, 'Cannot smoke test — key missing'); return

    VOICE = 'HmUVvDlHsEz0m3eUGLgu'  # PBX — sole host
    url   = f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}'
    body  = json.dumps({'text': 'Bitcoin. Signal confirmed.',
                        'model_id': 'eleven_turbo_v2_5',
                        'voice_settings': {'stability': 0.55, 'similarity_boost': 0.80, 'style': 0.15}}).encode()
    try:
        t0  = time.time()
        req = ul.Request(url, data=body, headers={
            'xi-api-key': api_key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
        with ul.urlopen(req, timeout=20) as r:
            audio = r.read()
        elapsed = time.time() - t0
        chk('ElevenLabs API reachable', True)
        size_ok = len(audio) > 10240
        chk(f'Audio >10KB ({len(audio)//1024}KB, {elapsed:.1f}s)', size_ok,
            f'Only {len(audio)}B — check quota / API key')
        if size_ok:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(audio); tmp = f.name
            r2 = subprocess.run(
                ['ffprobe','-v','quiet','-show_entries','format=duration',
                 '-of','default=noprint_wrappers=1:nokey=1', tmp],
                capture_output=True, text=True)
            os.unlink(tmp)
            dur = float(r2.stdout.strip()) if r2.stdout.strip() else 0.0
            chk(f'Audio duration > 0.4s ({dur:.2f}s)', dur > 0.4,
                'Zero-duration audio — silent response from ElevenLabs')
    except Exception as ex:
        chk('ElevenLabs API reachable', False, str(ex))

# ── MAIN ──────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--no-tts', action='store_true')
    args = p.parse_args()

    print(f'\n{"═"*60}')
    print(f'  PROTOCOL PULSE PREFLIGHT  —  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"═"*60}')

    check_syntax()
    check_constants()
    check_banned()
    check_env()
    check_voices()
    check_elevenlabs_quota()
    check_disk_space()
    check_ffmpeg_binaries()
    check_anthropic_api()
    check_assembler()
    check_branded_assets()
    if not args.no_tts:
        check_tts_smoke()

    total  = len(results)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f'\n{"═"*60}')
    if failed == 0:
        print(f'\033[92m  ✅  ALL {total} CHECKS PASSED — SAFE TO RENDER\033[0m')
    else:
        print(f'\033[91m  ❌  {failed}/{total} FAILED — DO NOT START RENDER\033[0m')
        for name, ok, detail in results:
            if not ok:
                print(f'     • {name}')
                if detail: print(f'       → {detail}')
    if check_elevenlabs_quota._pct is not None:
        print(f'  ElevenLabs quota: {check_elevenlabs_quota._pct:.1f}% used')
    print(f'{"═"*60}\n')
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
