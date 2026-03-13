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

    for const, val in [('SILENCE_GAP', '0.3'), ('MAX_CHUNK_CHARS', '500')]:
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
    sec('VOICE IDs')
    c = open(f'{V3}/tts_engine.py').read() if os.path.exists(f'{V3}/tts_engine.py') else ''
    chk('Eryn voice present: kdnRe2koJdOK4Ovxn2DI', 'kdnRe2koJdOK4Ovxn2DI' in c,
        'Eryn voice ID missing from tts_engine.py')
    chk('Mark voice present: 1SM7GgM6IMuvQlz2BwM3', '1SM7GgM6IMuvQlz2BwM3' in c,
        'Mark voice ID missing from tts_engine.py')
    chk('Banned voice absent: uxKr2vlA4hYgXZR1oPRT', 'uxKr2vlA4hYgXZR1oPRT' not in c,
        'BANNED voice in tts_engine.py — causes silent 0-byte audio')

# ── 6. ASSEMBLER CONSTANTS ────────────────────────────────
def check_assembler():
    sec('ASSEMBLER COLOR CONSTANTS')
    c = open(f'{V3}/assembler.py').read() if os.path.exists(f'{V3}/assembler.py') else ''
    for const, val in [('COLOR_RED','0xFF3333'),('COLOR_WHITE','0xF4F5F8'),('COLOR_BG','0x0A0A0F')]:
        chk(f'{const} = {val}', const in c and val in c,
            f'{const} missing or wrong value — expected {val}')

# ── 7. LIVE TTS SMOKE TEST ────────────────────────────────
def check_tts_smoke():
    sec('LIVE TTS SMOKE TEST')
    import urllib.request as ul
    e = env()
    api_key = e.get('ELEVENLABS_API_KEY', '')
    if not api_key:
        chk('ElevenLabs key available', False, 'Cannot smoke test — key missing'); return

    VOICE = 'kdnRe2koJdOK4Ovxn2DI'
    url   = f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}'
    body  = json.dumps({'text': 'Bitcoin. Signal confirmed.',
                        'model_id': 'eleven_turbo_v2',
                        'voice_settings': {'stability': 0.45, 'similarity_boost': 0.82}}).encode()
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
    check_assembler()
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
    print(f'{"═"*60}\n')
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
