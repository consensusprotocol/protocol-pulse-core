#!/usr/bin/env bash
# ============================================================
# PROTOCOL PULSE — regression_test.sh
# GOSPEL. Run before every commit. Zero FAILs required.
# ============================================================
set -euo pipefail
PASS=0; FAIL=0; WARN=0
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE="$BASE/video_pipeline_v3"
CORE="$BASE/core"
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

ok()   { echo -e "${GREEN}[PASS]${NC} $1"; ((PASS++)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; ((FAIL++)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; ((WARN++)); }

echo "============================================================"
echo " PROTOCOL PULSE REGRESSION TEST"
echo " $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"

# ── SECTION 1: GPU ──────────────────────────────────────────
echo -e "\n── GPU ──"
if nvidia-smi > /dev/null 2>&1; then
    GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
    ok "GPU available: $GPU_COUNT device(s)"
else
    fail "GPU not available — nvidia-smi failed"
fi

# GPU lock check
if [ -f /tmp/gpu_render.lock ]; then
    LOCK_OWNER=$(python3 -c "import json; d=json.load(open('/tmp/gpu_render.lock')); print(d.get('owner','unknown'))" 2>/dev/null || echo "unknown")
    warn "GPU render lock held by: $LOCK_OWNER"
fi

# ── SECTION 2: PIPELINE LAWS ────────────────────────────────
echo -e "\n── PIPELINE LAWS ──"
LAWS="$PIPELINE/PIPELINE_LAWS.md"
if [ -f "$LAWS" ]; then
    ok "PIPELINE_LAWS.md exists ($(wc -l < $LAWS) lines)"
    # Check for critical law markers
    for marker in "SECTION 1" "SECTION 2" "SECTION 3" "SECTION 4" "SECTION 5"; do
        grep -q "$marker" "$LAWS" && ok "Law $marker present" || fail "Law $marker MISSING"
    done
else
    fail "PIPELINE_LAWS.md NOT FOUND — abort"
fi

# ── SECTION 3: PYTHON SYNTAX ────────────────────────────────
echo -e "\n── PYTHON SYNTAX ──"
PIPELINE_PY_FILES=(
    "$PIPELINE/daily_run.py"
    "$PIPELINE/assembler.py"
    "$PIPELINE/tts_engine.py"
    "$PIPELINE/script_writer.py"
    "$PIPELINE/clip_extractor.py"
    "$PIPELINE/shorts_cutter.py"
    "$PIPELINE/utils/spaces_monitor.py"
    "$PIPELINE/utils/tradfi_monitor.py"
    "$PIPELINE/utils/live_monitor.py"
)
for f in "${PIPELINE_PY_FILES[@]}"; do
    if [ -f "$f" ]; then
        python3 -m py_compile "$f" 2>/dev/null && ok "Syntax OK: $(basename $f)" || fail "Syntax ERROR: $(basename $f)"
    else
        warn "Missing: $(basename $f)"
    fi
done

# Core Python files
CORE_PY_FILES=(
    "$CORE/routes.py"
    "$CORE/services/spaces_sentiment_service.py"
    "$CORE/services/sentiment_tracker_service.py"
    "$CORE/services/scheduler.py"
)
for f in "${CORE_PY_FILES[@]}"; do
    if [ -f "$f" ]; then
        python3 -m py_compile "$f" 2>/dev/null && ok "Syntax OK: $(basename $f)" || fail "Syntax ERROR: $(basename $f)"
    else
        warn "Missing core: $(basename $f)"
    fi
done

# ── SECTION 4: CRITICAL ASSETS ──────────────────────────────
echo -e "\n── CRITICAL ASSETS ──"
ASSETS=(
    "$PIPELINE/config/feature_flags.json"
    "$PIPELINE/config/api_keys.json"
    "$PIPELINE/assets/outro_branded.mp4"
    "$BASE/video_pipeline_v3/PIPELINE_LAWS.md"
)
for f in "${ASSETS[@]}"; do
    [ -f "$f" ] && ok "Asset exists: $(basename $f)" || fail "MISSING asset: $(basename $f)"
done

# Music assets
MUSIC_COUNT=$(ls "$PIPELINE/assets/music/"*.mp3 2>/dev/null | wc -l)
[ "$MUSIC_COUNT" -gt 0 ] && ok "Music assets: $MUSIC_COUNT tracks" || fail "No music assets found"

# ── SECTION 5: API KEY RESOLUTION ───────────────────────────
echo -e "\n── API KEY RESOLUTION ──"
cd "$PIPELINE"
python3 -c "
from relay import get_key
keys_to_check = ['ELEVENLABS_API_KEY', 'ANTHROPIC_API_KEY', 'TWITTER_BEARER_TOKEN']
for k in keys_to_check:
    v = get_key(k)
    if v and len(v) > 10:
        print(f'[PASS] {k}: present ({len(v)} chars)')
    else:
        print(f'[FAIL] {k}: MISSING or empty')
" 2>/dev/null || warn "Key resolution check failed — relay may be down"

# ── SECTION 6: FEATURE FLAGS ────────────────────────────────
echo -e "\n── FEATURE FLAGS ──"
python3 -c "
import json
try:
    d = json.load(open('$PIPELINE/config/feature_flags.json'))
    print(f'[PASS] feature_flags.json valid JSON ({len(d)} flags)')
except Exception as e:
    print(f'[FAIL] feature_flags.json: {e}')
"

# ── SECTION 7: IMPORT SMOKE TEST ────────────────────────────
echo -e "\n── IMPORT SMOKE TEST ──"
cd "$PIPELINE"
python3 -c "
import sys
tests = [
    ('assembler', 'assembler'),
    ('tts_engine', 'tts_engine'),
    ('script_writer', 'script_writer'),
]
for mod, name in tests:
    try:
        __import__(mod)
        print(f'[PASS] import {name}')
    except Exception as e:
        print(f'[FAIL] import {name}: {str(e)[:60]}')
" 2>/dev/null

# ── SECTION 8: GIT STATE ────────────────────────────────────
echo -e "\n── GIT STATE ──"
cd "$BASE"
BRANCH=$(git branch --show-current)
ok "Branch: $BRANCH"
UNCOMMITTED=$(git status --porcelain | wc -l)
[ "$UNCOMMITTED" -eq 0 ] && ok "Working tree clean" || warn "$UNCOMMITTED uncommitted changes"

STASH_COUNT=$(git stash list | wc -l)
[ "$STASH_COUNT" -gt 5 ] && warn "$STASH_COUNT stashed changes — consider cleaning" || ok "Stash count: $STASH_COUNT"

# ── SECTION 9: LIVE SERVICES ────────────────────────────────
echo -e "\n── LIVE SERVICES ──"
# Oracle live
curl -sf https://oracle-live.protocolpulse.io/health > /dev/null 2>&1 && ok "oracle-live responding" || warn "oracle-live not responding"
# Video server
curl -sf http://localhost:5100/ > /dev/null 2>&1 && ok "video server responding" || warn "video server not responding"

# ── FINAL REPORT ────────────────────────────────────────────
echo ""
echo "============================================================"
echo " RESULTS: ${PASS} PASS  |  ${FAIL} FAIL  |  ${WARN} WARN"
echo "============================================================"
if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED} REGRESSION FAILED — DO NOT COMMIT${NC}"
    exit 1
else
    echo -e "${GREEN} ALL TESTS PASSED — safe to commit${NC}"
    exit 0
fi
