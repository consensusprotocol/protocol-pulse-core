#!/usr/bin/env python3
"""Unit tests for comedy_machine (6.4) — deterministic logic only, no network."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, "/home/ultron/protocol_pulse")
sys.path.insert(0, "/home/ultron/protocol_pulse/services")
import comedy_machine as cm

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS {name}")
    else:
        FAIL += 1
        print(f"FAIL {name} {detail}")


# ── hard_filter ───────────────────────────────────────────────────────────────
ok, why = cm.hard_filter("Fed announces plan to print money faster than it can be counted, hires 14,000 abacus specialists")
check("filter_accepts_clean", ok, why)

ok, why = cm.hard_filter("Bitcoin is a game-changer for everyone")
check("filter_kills_banned_phrase", not ok and "banned phrase" in why, why)

ok, why = cm.hard_filter("New ethereum killer just dropped")
check("filter_kills_banned_topic", not ok and "banned topic" in why, why)

ok, why = cm.hard_filter("Big news everyone!!!")
check("filter_kills_exclaim", not ok, why)

ok, why = cm.hard_filter("The Fed did a thing — again")
check("filter_kills_emdash", not ok, why)

ok, why = cm.hard_filter("Central bank runs out of zeros.")
check("filter_kills_trailing_period", not ok, why)

ok, why = cm.hard_filter("Bitcoin fixes this \U0001F680")
check("filter_kills_emoji", not ok, why)

ok, why = cm.hard_filter("x" * 300)
check("filter_kills_length", not ok, why)

ok, why = cm.hard_filter("Treasury announces #hodl initiative")
check("filter_kills_hashtag", not ok, why)

ok, why = cm.hard_filter("Stay free stay sovereign brothers")
check("filter_kills_tribal_copy", not ok, why)

# ── cadence gate ──────────────────────────────────────────────────────────────
now = datetime.now(timezone.utc)
st_fresh = {"last_posted_at": (now - timedelta(days=1)).isoformat()}
check("cadence_blocks_at_1_day", cm.days_since_last_post(st_fresh, now) < 3)

st_ok = {"last_posted_at": (now - timedelta(days=3, hours=2)).isoformat()}
check("cadence_allows_at_3_days", cm.days_since_last_post(st_ok, now) >= 3)

st_never = {"last_posted_at": None}
check("cadence_allows_never_posted", cm.days_since_last_post(st_never, now) >= 3)

# ── _extract_json (incl. the inner-array trap the last session hit) ──────────
obj = cm._extract_json('Here you go:\n```json\n{"scores": [1,2], "verdict": "ship"}\n```')
check("json_object_with_inner_array", isinstance(obj, dict) and obj.get("verdict") == "ship", str(obj))

arr = cm._extract_json('[{"text": "a", "theme": "b"}, {"text": "c", "theme": "d"}]')
check("json_plain_array", isinstance(arr, list) and len(arr) == 2)

obj2 = cm._extract_json('{"reason": "quote \\"inside\\" [brackets]", "overall": 91}')
check("json_string_with_brackets", isinstance(obj2, dict) and obj2.get("overall") == 91, str(obj2))

try:
    cm._extract_json("no json here at all")
    check("json_raises_on_garbage", False)
except ValueError:
    check("json_raises_on_garbage", True)

# ── gate ship logic (offline, monkeypatched LLM) ─────────────────────────────
cfg = dict(cm.DEFAULT_CONFIG)

def fake_llm_factory(payload):
    def f(prompt, model):
        return json.dumps(payload)
    return f

orig = cm._llm
cand = {"text": "t", "theme": "th", "premise": "p"}

cm._llm = fake_llm_factory({"believable_as_real_news": False, "absurdity_clear": True,
                            "funny": 92, "on_voice": 90, "brand_safe": True,
                            "overall": 91, "verdict": "ship", "reason": "sharp"})
ship, _ = cm.gate(cand, cfg)
check("gate_ships_sharp_joke", ship)

cm._llm = fake_llm_factory({"believable_as_real_news": True, "absurdity_clear": True,
                            "funny": 95, "on_voice": 95, "brand_safe": True,
                            "overall": 95, "verdict": "ship", "reason": "but believable"})
ship, _ = cm.gate(cand, cfg)
check("gate_kills_believable_even_if_funny", not ship)

cm._llm = fake_llm_factory({"believable_as_real_news": False, "absurdity_clear": True,
                            "funny": 80, "on_voice": 85, "brand_safe": True,
                            "overall": 84, "verdict": "ship", "reason": "mid"})
ship, _ = cm.gate(cand, cfg)
check("gate_kills_below_floor", not ship)

cm._llm = fake_llm_factory({"believable_as_real_news": False, "absurdity_clear": True,
                            "funny": 92, "on_voice": 90, "brand_safe": False,
                            "overall": 93, "verdict": "ship", "reason": "edgy but unsafe"})
ship, _ = cm.gate(cand, cfg)
check("gate_kills_brand_unsafe", not ship)

cm._llm = orig

print(f"\n{PASS}/{PASS + FAIL} PASS")
sys.exit(1 if FAIL else 0)
