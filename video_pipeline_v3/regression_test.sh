#!/bin/bash
# ════════════════════════════════════════════════════════════════════════
# PROTOCOL PULSE — REGRESSION TEST SUITE
# Every verified fix gets a test here. Run before EVERY commit.
# If ANY test fails: exit 1. DO NOT COMMIT.
# See LOCKED_FIXES.md for documentation of each fix.
# ════════════════════════════════════════════════════════════════════════
set -o pipefail
cd "$(dirname "$0")"
PASS=0; FAIL=0; TOTAL=0

check() {
    TOTAL=$((TOTAL + 1))
    if eval "$2" > /dev/null 2>&1; then
        echo "  PASS: $1"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $1"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== PROTOCOL PULSE REGRESSION TESTS ==="
echo ""

# ── AUDIO / VIDEO PIPELINE ────────────────────────────────────────────

# FIX-001: No aresample=async=1 in assembler (causes lip desync)
check "FIX-001: No async=1 in assembler.py" \
    "! grep -q 'async=1' assembler.py"

# FIX-002: No aresample=async=1 in render modules (lip sync)
check "FIX-002a: No async=1 in render_clip.py" \
    "! grep 'async=1' render_clip.py 2>/dev/null | grep -v '#' | grep -q 'async=1'"

check "FIX-002b: No async=1 in render_narrator.py" \
    "! grep -q 'async=1' render_narrator.py"

check "FIX-002c: No async=1 in render_intro_outro.py" \
    "! grep -q 'async=1' render_intro_outro.py"

check "FIX-002d: No async=1 in assembler_common.py" \
    "! grep -q 'async=1' assembler_common.py"

check "FIX-002e: No async=1 in daily_producer.py" \
    "! grep -q 'async=1' daily_producer.py"

# FIX-003: async=1 MUST exist in clip_extractor (nuclear fix for source clips)
check "FIX-003: async=1 in clip_extractor fix_av_sync" \
    "grep -q 'async=1' clip_extractor.py"

# FIX-004: Episode-level whoosh mastering disabled (double whoosh fix)
check "FIX-004: Episode whoosh disabled" \
    "grep -q 'has_whoosh = False' assembler.py"

# FIX-005: PiP retry at 40% for dark-intro channels
check "FIX-005: PiP retry at 40%" \
    "grep -q 'position_pct=0.40' assembler.py"

# FIX-006: confident_02.mp3 is locked signature track
check "FIX-006: Music locked to confident_02" \
    "grep -q 'confident_02' daily_producer.py || grep -q 'confident_02' assembler.py"

# ── SYSTEM / INFRASTRUCTURE ────────────────────────────────────────────

# FIX-007: No gunicorn on port 5000 (waitress only)
check "FIX-007: No gunicorn on port 5000" \
    "! grep -rq 'gunicorn.*5000' ../scripts/*.sh 2>/dev/null"

# FIX-008: Avatar server blocked in hooks
check "FIX-008: Avatar server blocked by hook" \
    "grep -qi 'avatar' ../scripts/hooks/pre_bash_gate.sh 2>/dev/null"

# FIX-009: CLAUDE.md constitution exists
check "FIX-009: CLAUDE.md exists" \
    "test -f ../CLAUDE.md"

# FIX-010: CC hooks configured
check "FIX-010: CC settings.json exists" \
    "test -f ../.claude/settings.json"

# ── VOICE / TTS ────────────────────────────────────────────────────────

# FIX-011: No Kokoro/dual-host (single PBX host)
check "FIX-011: No Kokoro/dual-host" \
    "! grep -qi 'kokoro' tts_engine.py"

# FIX-012: PiP fallback exists in assembler
check "FIX-012: PiP fallback in assembler" \
    "grep -q '_any_pip\|PiP FALLBACK' assembler.py"

# FIX-013: Stay sovereign signoff
check "FIX-013: Stay sovereign signoff" \
    "grep -qi 'stay sovereign' script_writer.py 2>/dev/null || grep -qi 'stay sovereign' daily_producer.py 2>/dev/null"

# FIX-014: ElevenLabs pronunciation dictionary integrated
check "FIX-014: Pronunciation dictionary in TTS" \
    "grep -q 'pronunciation_dictionary_locators' tts_engine.py"

# FIX-015: X posts in Signal Active (not just Nostr)
check "FIX-015: X posts in signal_intelligence" \
    "grep -q 'x_posts' signal_intelligence.py"

# ── SYNTAX CHECKS ──────────────────────────────────────────────────────

for f in assembler.py render_narrator.py render_clip.py render_social.py \
         render_intro_outro.py render_data.py audio_master.py tts_engine.py \
         daily_producer.py clip_extractor.py script_writer.py \
         assembler_common.py signal_intelligence.py; do
    if [ -f "$f" ]; then
        check "SYNTAX: $f" "python3 -m py_compile $f"
    fi
done

echo ""
echo "=== RESULTS: $PASS passed, $FAIL failed, $TOTAL total ==="
if [ $FAIL -gt 0 ]; then
    echo "REGRESSION DETECTED — DO NOT COMMIT"
    exit 1
else
    echo "ALL REGRESSION TESTS PASS"
    exit 0
fi
