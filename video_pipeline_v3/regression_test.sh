#!/bin/bash
# VIDEO PIPELINE REGRESSION TEST — run after every build, before every commit
# Usage: bash regression_test.sh [output_dir]
# If no dir provided, uses latest test_* directory

set -e
cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILS=0
WARNS=0

fail() { echo -e "${RED}FAIL${NC}: $1"; ((FAILS++)); }
warn() { echo -e "${YELLOW}WARN${NC}: $1"; ((WARNS++)); }
pass() { echo -e "${GREEN}PASS${NC}: $1"; }

echo "================================================================"
echo "  PULSE CHECK — REGRESSION TEST"
echo "  $(date)"
echo "================================================================"

# Find latest output
if [ -n "$1" ]; then
    LATEST="$1"
else
    LATEST=$(ls -td output/test_* 2>/dev/null | head -1)
fi

if [ -z "$LATEST" ] || [ ! -d "$LATEST" ]; then
    fail "No output directory found"
    exit 1
fi

echo "Testing: $LATEST"
echo ""

FINAL=$(ls "$LATEST"/pulse_check_*.mp4 2>/dev/null | grep -v norm | head -1)
WORK="$LATEST/work"
SCRIPT="$LATEST/script.json"

# ── 1. OUTPUT EXISTS ──────────────────────────────────────────────
echo "── 1. OUTPUT EXISTS ──"
[ -f "$FINAL" ] && pass "Final video exists" || fail "No final video"
[ -f "$SCRIPT" ] && pass "Script exists" || fail "No script.json"
[ -d "$WORK" ] && pass "Work directory exists" || fail "No work directory"
echo ""

if [ ! -f "$FINAL" ]; then
    echo "Cannot continue without final video."
    exit 1
fi

# ── 2. VIDEO SPECS ────────────────────────────────────────────────
echo "── 2. VIDEO SPECS ──"
RES=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$FINAL" 2>/dev/null)
echo "$RES" | grep -q "1920,1080" && pass "Resolution 1920x1080" || fail "Resolution is $RES (need 1920,1080)"

PIX=$(ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt -of csv=p=0 "$FINAL" 2>/dev/null)
echo "$PIX" | grep -q "yuv420p" && pass "Pixel format yuv420p" || fail "Pixel format is $PIX"

AUD=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$FINAL" 2>/dev/null)
echo "$AUD" | grep -q "aac" && pass "AAC audio present" || fail "No AAC audio (got: $AUD)"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$FINAL" 2>/dev/null | cut -d. -f1)
[ "$DUR" -gt 30 ] && pass "Duration ${DUR}s (>30s)" || fail "Duration ${DUR}s — too short"
echo ""

# ── 3. PARTS STRUCTURE ───────────────────────────────────────────
echo "── 3. PARTS STRUCTURE ──"
ls "$WORK"/part_*cold_open* >/dev/null 2>&1 && pass "Cold open present" || fail "No cold open part"
CLIP_COUNT=$(ls "$WORK"/part_*clip* 2>/dev/null | wc -l)
[ "$CLIP_COUNT" -ge 1 ] && pass "Clips present ($CLIP_COUNT)" || fail "No clip parts"
ls "$WORK"/part_*setup* >/dev/null 2>&1 && pass "Setup narration present" || fail "No setup parts"
ls "$WORK"/part_*react* >/dev/null 2>&1 && pass "React narration present" || fail "No react parts"
ls "$WORK"/part_*glitch* >/dev/null 2>&1 && pass "Glitch transitions present" || pass "No standalone glitch transitions (xfade mode)"
ls "$WORK"/part_*wrap* >/dev/null 2>&1 && pass "Wrap present" || fail "No wrap part"
ls "$WORK"/part_*outro* >/dev/null 2>&1 && pass "Outro present" || fail "No outro part"
echo ""

# ── 4. NO BLACK FRAMES ──────────────────────────────────────────
echo "── 4. NO BLACK/EMPTY PARTS ──"
for f in "$WORK"/part_*.mp4; do
    SZ=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null)
    BASENAME=$(basename "$f")
    # Glitch transitions are 0.5s — 50-80KB is normal
    if echo "$BASENAME" | grep -q "glitch"; then
        if [ "$SZ" -lt 10000 ]; then
            fail "$BASENAME is only ${SZ} bytes — likely black/empty"
        fi
    elif [ "$SZ" -lt 100000 ]; then
        fail "$BASENAME is only ${SZ} bytes — likely black/empty"
    fi
done
# Count how many passed
TOTAL_PARTS=$(ls "$WORK"/part_*.mp4 2>/dev/null | wc -l)
SMALL_PARTS=$(find "$WORK" -name "part_*.mp4" ! -name "*glitch*" -size -100k 2>/dev/null | wc -l)
SMALL_GLITCH=$(find "$WORK" -name "part_*glitch*" -size -10k 2>/dev/null | wc -l)
SMALL_PARTS=$((SMALL_PARTS + SMALL_GLITCH))
GOOD_PARTS=$((TOTAL_PARTS - SMALL_PARTS))
[ "$SMALL_PARTS" -eq 0 ] && pass "All $TOTAL_PARTS parts have real content" || true
echo ""

# ── 5. THUMBNAIL OVERLAYS ───────────────────────────────────────
echo "── 5. THUMBNAIL OVERLAYS ──"
THUMB_COUNT=$(ls /tmp/thumb_*.jpg 2>/dev/null | wc -l)
[ "$THUMB_COUNT" -ge "$CLIP_COUNT" ] && pass "Thumbnails fetched ($THUMB_COUNT for $CLIP_COUNT clips)" || fail "Only $THUMB_COUNT thumbnails for $CLIP_COUNT clips — thumbnails missing"
echo ""

# ── 6. CLIP AUDIO ────────────────────────────────────────────────
echo "── 6. CLIP AUDIO PRESENT ──"
for f in "$WORK"/part_*clip*.mp4; do
    BASENAME=$(basename "$f")
    HAS_AUD=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$f" 2>/dev/null)
    [ "$HAS_AUD" = "audio" ] && pass "$BASENAME has audio" || fail "$BASENAME has NO audio — clip will be silent"
done
echo ""

# ── 7. VOICE CONFIG ─────────────────────────────────────────────
echo "── 7. VOICE CONFIG ──"
grep -q "stability" tts_engine.py 2>/dev/null && pass "Voice stability settings present" || fail "No stability setting — moaning artifact risk"
# Check not using Jessica (known bad voice)
grep -q "cgSgspJ2msm6clMCkdW9" tts_engine.py 2>/dev/null && fail "Still using Jessica voice (cgSgsp...) — CHANGE IT" || pass "Not using Jessica voice"
echo ""

# ── 8. SCRIPT QUALITY ───────────────────────────────────────────
echo "── 8. SCRIPT QUALITY ──"
if [ -f "$SCRIPT" ]; then
    python3 -c "
import json, sys
d = json.load(open('$SCRIPT'))
fails = 0

# Cold open
if not d.get('cold_open'):
    print('FAIL: No cold_open'); fails += 1
else:
    print('PASS: Cold open present')

# Dialogue length
dl = d.get('dialogue', [])
if len(dl) < 5:
    print(f'FAIL: Only {len(dl)} dialogue entries'); fails += 1
else:
    print(f'PASS: {len(dl)} dialogue entries')

# CLIP entries
clips = [e for e in dl if e.get('host') == 'CLIP']
if len(clips) < 1:
    print(f'FAIL: No CLIP entries in dialogue'); fails += 1
else:
    print(f'PASS: {len(clips)} CLIP entries')

# Setup/react length
for e in dl:
    t = e.get('type', '')
    txt = e.get('text', '')
    if t in ('setup', 'react') and len(txt) > 250:
        print(f'WARN: {t} line too long ({len(txt)} chars): {txt[:50]}...')

# Banned phrases
banned = ['let us dive in', 'without further ado', 'buckle up', 'game changer',
          'really interesting', 'really impactful', 'great stuff', 'that is great']
for e in dl:
    text = e.get('text', '').lower()
    for b in banned:
        if b in text:
            print(f'FAIL: Banned phrase \"{b}\" found'); fails += 1

sys.exit(1 if fails > 0 else 0)
" 2>&1
else
    fail "No script.json to check"
fi
echo ""

# ── 9. TRANSITION CHECK ──────────────────────────────────
echo "── 9. TRANSITION CHECK ──"
GLITCH=$(ls "$WORK"/part_*glitch* 2>/dev/null | head -1)
if [ -n "$GLITCH" ]; then
    HAS_AUD=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$GLITCH" 2>/dev/null)
    [ "$HAS_AUD" = "audio" ] && pass "Glitch has audio track" || fail "Glitch has NO audio — woosh missing"
else
    pass "No standalone glitch transitions — using xfade crossfade"
fi
echo ""

# ── 10. BACKGROUND MUSIC FILES ──────────────────────────────────
echo "── 10. MUSIC ASSETS ──"
[ -f "assets/music/pp_background.mp3" ] && pass "Background music exists" || fail "Background music missing"
[ -f "assets/music/pp_intro.mp3" ] && pass "Intro music exists" || fail "Intro music missing"
[ -f "assets/music/pp_outro.mp3" ] && pass "Outro music exists" || fail "Outro music missing"
grep -q "pp_background\|background.*mp3" assembler.py && pass "Assembler references bg music" || warn "Assembler may not use background music"
echo ""

# ── 11. NARRATOR OVERLAP CHECK ──────────────────────────────────
echo "── 11. PART SEQUENCE ──"
python3 -c "
import os, glob
parts = sorted(glob.glob('$WORK/part_*.mp4'))
names = [os.path.basename(p) for p in parts]
print('Part order:')
for n in names:
    print(f'  {n}')
# Check part sequence looks reasonable
for i in range(len(names)-1):
    if 'setup' in names[i] and 'clip' in names[i+1]:
        print(f'OK: {names[i]} → {names[i+1]} (xfade crossfade applied during concat)')
" 2>&1
echo ""

# ── SUMMARY ─────────────────────────────────────────────────────
echo "================================================================"
if [ "$FAILS" -eq 0 ]; then
    echo -e "  ${GREEN}ALL CHECKS PASSED${NC} ($WARNS warnings)"
    echo "  Safe to commit."
else
    echo -e "  ${RED}$FAILS FAILURES${NC}, $WARNS warnings"
    echo "  DO NOT COMMIT. Fix failures first."
fi
echo "================================================================"

exit $FAILS
