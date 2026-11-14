# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0915
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 891 s finish=length usage in 20207 / out 24000 usd~0.421 (upper-bound price)

<critical>

**C1. `universe_levels` reads `universe["built_at"]` / `universe["news"]` with subscript, but the "unreadable case" test proves the intended contract is `.get` — and the v1.1 schema makes `universe` optional, so a v1.1 case with no `universe` key raises KeyError → GateNotMeasured, while the same case without the key is documented as "v1 cases are unchanged" (test line 394-398 passes only because it strips the key). Actually — wait, re-read: the test at line 395 builds the case by *removing* `title` and `universe`, so a v1 case never reaches the new code. But a v1.1 case that *omits* `universe` (schema-legal, since the adapter guards `case.get("universe") is not None` at line 93) hits line 64 `E._parse_time(universe["built_at"])` only when `universe` is present — so this is consistent. Downgrade: not critical.**

Let me re-verify each attack surface precisely.

---

<critical>

**C1. `spotlight.py:143` — `changes_near` counts markers, not speaker *changes*, and the marker at the clip's own start/end inflates it; but the real bug is the window: `start - NEAR_CLIP_S <= t <= end + NEAR_CLIP_S` uses the *clip* bounds, so a marker exactly at `end + 300.0` counts, while the ruling says "in the 10 minutes around the clip" — 5 min each side of the clip, i.e. the window is `[start-300, end+300]`, which is what's implemented. The concrete break: a clip of 20 s duration has a "10 minutes around" window of 620 s, not 600 s — the ruling's "10 minutes" is read as 5 min each side of the *clip's edges*, so a 20 s clip gets a 620 s window. Is that "sensible"? The ruling says "the 10 minutes around the clip", and the code comment (line 107-109) says "read as 5 minutes each side of it" — this is a documented, defensible reading. Not a bug.**

**The actual critical: `caption_evidence` (spotlight.py:139) — `opens = [u[0] for u in units if u[2]]` assumes every unit is a 3-tuple `(t, text, is_open)`. If `speakers.captions` returns 2-tuples or dicts, this raises TypeError, caught by the broad `except Exception` at line 134 only for the *initial call* — no, the list comprehension is *after* the try, so a TypeError there propagates out of `caption_evidence` uncaught, killing the whole build stage, not just the evidence.** But the diff shows `episode_turns` (line 113-114, unchanged) already indexes `u[0]` and `u[2]` the same way, so the unit shape is established. Not a break.

---

<critical>

**C1. `moments_gate_adapter.py:64-68` — `universe_levels` raises ValueError for a *zoned-time* failure, but the test at line 425-426 expects `GateNotMeasured` with message "not a zoned time" — meaning `vo_fidelity` must catch ValueError and re-raise as GateNotMeasured. The diff of `vo_fidelity` (lines 84-97) shows NO try/except around `universe_levels(case["universe"])` at line 94 — the only try/except (line 95-97) wraps `VF.check` and catches `P.ReplayMiss`. So a case with `built_at="2026-11-12T05:06:13"` (zoneless) raises ValueError from `universe_levels`, which propagates as ValueError, NOT GateNotMeasured — the harness counts it as... whatever it counts a non-GateNotMeasured exception as. The test `test_an_unreadable_case_is_the_harness_error_never_a_guess` (line 419-426) asserts `assertRaises(A.GateNotMeasured)` for exactly this input, so either the test fails, or there's an unshown conversion.** The diff hunk at lines 84-97 shows the full function body around the change; the `try:` at line 95 begins *after* the `levels = ...` / `if levels is None and case.get("universe") is not None: levels = universe_levels(...)` lines. So the ValueError from `universe_levels` is raised *outside* the try. Unless `vo_fidelity`'s caller wraps it, the test as written fails. **Verify: does the harness (tests/package/run_exam_record.py, unchanged in this diff except line 308-311) catch bare ValueError?** The diff doesn't show it. If it doesn't, the test fails, or the harness's ERROR accounting differs. This is the highest-confidence finding: **the test at line 425-426 (`assertRaisesRegex(A.GateNotMeasured, "not a zoned time")`) cannot pass with the shown code unless `vo_fidelity` converts ValueError→GateNotMeasured, and no such conversion is in the diff.**

Hmm — wait. Let me re-read the vo_fidelity hunk. Lines 84-97:

```
def vo_fidelity(case):
    ...
    if case.get("title") is not None:
        if not isinstance(case["title"], str) or not case["title"].strip():
            raise ValueError("the case's title is not a non-empty string")
        lines.append({"slot": "title", ...})
    levels = case.get("current_levels") if isinstance(case.get("current_levels"), list) else None
    if levels is None and case.get("universe") is not None:
        levels = universe_levels(case["universe"])
    try:
        res = VF.check(router(), segments, lines, writer_vendor=None, manifest=man, current_levels=levels)
    except P.ReplayMiss as e:
```


## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 61 s finish=stop usage in 19817 / out 438 usd~0.110 (upper-bound price)

<critical> pipeline/moments_gate_adapter.py:89 (title block) + :65 (universe_levels built_at parse): concrete input `v11(title="")` or `v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13"))` makes `vo_fidelity` raise `ValueError` (as written in diff); test_exam_adapter.py:423-426 asserts `GateNotMeasured` (with regex "not a zoned time") and top comment:7-8 requires `GateNotMeasured` for harness ERROR (law L-m, unmeasurable = ERROR never pass/guess).
<high> pipeline/spotlight.py:245: `layout_for` does `hashlib.sha256(ev_text.encode())` (new cache key with `evidence_text`); diff adds no `import hashlib` (test_spotlight.py:573 does, locally); concrete: any `build` hitting `caption_evidence` + `layout_for(..., evidence=ev)` (e.g. moment with marked captions) raises NameError.
<medium> pipeline/spotlight.py:140 (`minutes = (units[-1][0] - units[0][0]) / 60.0`): no guard for `len(units) < 2`; concrete: captions record with 1 unit yields `turns_per_min=None`, `evidence_text:162` puts literal "None speaker turns a minute ... (x in 0.0 min)" into LAYOUT_PROMPT; test_caption_evidence covers only multi-unit cases.
<medium> pipeline/spotlight.py:208 (`conv = [x for x in sts if not (isinstance... and ... <= 0)]`): filters on episode `turns_per_min` (overall) while ruling 92 amended + `markers_refuse:152` refuses on `changes_near==0` (per-clip, 300s window); concrete: upload with `turns_per_min=2.0` but `changes_near=0` for a clip would reach `next_attempt` conversation list then fail at build:292.
SHIP: no

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 295 s finish=stop usage in 22379 / out 10201 usd~0.220 (upper-bound price)

# Audit: pp-selectid-0915

## Findings

### <high> `spotlight.py`: `caption_evidence` crashes on empty caption units (ZeroDivisionError)
**File:** `pipeline/spotlight.py` (new function `caption_evidence`, diff lines 139-141)

```python
opens = [u[0] for u in units if u[2]]
minutes = (units[-1][0] - units[0][0]) / 60.0   # <-- IndexError if units is empty
```

The guard `if not units:` (line 136) returns early only when `units` is falsy. However, the code path that reaches line 140 is:
1. `units` is a non-empty list (passes the `if not units` check).
2. But wait — if `units` is non-empty, `units[-1]` and `units[0]` exist. So `minutes` calculation is safe *if* `units` is non-empty.

**Correction:** Let me re-read. Line 136: `if not units: return ...`. So if we reach line 140, `units` is non-empty. `units[-1][0]` and `units[0][0]` are valid. The division by 60.0 is fine. The only risk is if `minutes` is 0.0, but that's handled by the ternary on line 142 (`if minutes > 0 else None`).

**Revised assessment:** This is **not** a bug. The guard is sufficient.

---

### <high> `spotlight.py`: `caption_evidence` — `units` elements assumed to be 3-tuples; no validation
**File:** `pipeline/spotlight.py`, `caption_evidence` (diff lines 139-144)

```python
opens = [u[0] for u in units if u[2]]
```

This assumes every element `u` in `units` is a sequence with at least 3 elements (`u[0]`, `u[2]`). The docstring says "units" come from `speakers.captions` (ruling 69's reader), which returns `(start, text, is_speaker_change)` tuples. If a malformed caption record returns 2-tuples or strings, this raises `IndexError` or `TypeError`.

**Concrete scenario:** A caption file with a malformed line causes `speakers.captions` to return `[(0.0, "hello")]` (2-tuple). `u[2]` raises `IndexError`. The `try/except` on line 134 catches it and returns `{"measured": False, ...}`, which is fail-closed. **This is acceptable** — the exception is caught and treated as "no evidence." Not a bug, but fragile.

---

### <high> `spotlight.py`: `markers_refuse` — `changes_near == 0` check is correct, but `one_turn` is not used in the refusal
**File:** `pipeline/spotlight.py`, `markers_refuse` (diff lines 148-152)

```python
def markers_refuse(evidence):
    ev = evidence or {}
    return ev.get("measured") is True and ev.get("marked") is True and ev.get("changes_near") == 0
```

The ruling says: "they refuse by themselves only when the episode is marked and has ZERO speaker changes in the 10 minutes around the clip." The code matches this exactly. `one_turn` is not part of the refusal condition, which is correct per the ruling. **No issue.**

---

### <high> `spotlight.py`: `source_test` — unmeasured layout never passes, but `markers_refuse` is checked first
**File:** `pipeline/spotlight.py`, `source_test` (diff lines 167-188)

```python
def source_test(evidence, layout):
    if markers_refuse(evidence):
        return False, (...)
    if not (layout or {}).get("measured"):
        return False, f"the layout is not measured: ..."
    lay = layout["layout"]
    if lay not in LAYOUT_OK:
        return False, ...
    return True, ...
```

**Scenario:** A marked episode with zero changes near the clip, AND an unmeasured layout. The code returns the `markers_refuse` reason, not the "not measured" reason. This is correct behavior (the markers refuse first), and the result is the same (False). **No issue.**

---

### <high> `spotlight.py`: `layout_for` cache key includes evidence hash — correct, but `evidence_text` is called twice
**File:** `pipeline/spotlight.py`, `layout_for` (diff lines 228-245)

```python
ev_text = evidence_text(evidence)
k = f"{m['moment_id']}:{sha}:{LAYOUT_VERSION}:{hashlib.sha256(ev_text.encode()).hexdigest()[:12]}"
```

`evidence_text` is called once and stored in `ev_text`, then used for both the cache key and the prompt. **No issue.**

---

### <high> `spotlight.py`: `build` — `caption_evidence` is called with `float(m["start"])` and `float(m["end"])`
**File:** `pipeline/spotlight.py`, `build` (diff lines 290-291)

```python
ev = caption_evidence(m["video_id"], float(m["start"]), float(m["end"]), captions_for)
```

If `m["start"]` or `m["end"]` is `None` or a non-numeric string, `float()` raises `ValueError` or `TypeError`. This is not caught in `build`. **Concrete scenario:** A moment record with `"start": null` causes a crash in `build`, which is not fail-closed (it's an unhandled exception).

**Severity:** <high> — an unhandled exception in the build path. The moment should be skipped with a recorded failure, not crash the build.

---

### <high> `moments_gate_adapter.py`: `universe_levels` — `E._parse_time` is a private function
**File:** `pipeline/moments_gate_adapter.py`, `universe_levels` (diff line 64)

```python
now = E._parse_time(universe["built_at"])
```

Calling a private function (`_parse_time`) from another mod

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 0915 (the orchestrator's 09:03 rulings: R-29 and ruling 92 amended), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP no. One <critical>, one <high>, two <medium>. The <critical> and the <high> are refuted from the code
  (below); the two <medium> are cosmetic or by design.
- qwen3.8-27b: no SHIP line. Most of its <high> tags resolve inside its own text ("Not a bug", "No issue"). Its points
  that stand: caption_evidence's 2-tuple case (implemented: its claim that the guard catches it was wrong for this
  diff), the build's float(m["start"]) (refuted), the private E._parse_time and the sentence split (kept, measured).
- glm-5.3-flash: finish=length at 24000 tokens, no SHIP line. Its <critical> on ValueError is refuted. Its H66 is a
  real defect (implemented). It also notes that caption_evidence counts after its guard (implemented).

Upper-bound cost: about $0.75 ($0.110 + $0.220 + $0.421), outside SPEND_LY.json.

## Implemented

1. glm H66: the ruling-95 report dropped an UNMARKED episode.
   - pp-ingest writes an unmarked episode as `"turns_per_min": 0.0` and `"unmarked": true` (its episode_measure:
     `round(n / mins, 2)` and `n == 0`). next_attempt's filter dropped every numeric turns_per_min <= 0.
   - So an unmarked episode (unknown, never solo) left "the newest conversation upload". The amended rule says only a
     MARKED episode with zero turns is out.
   - Now state() carries `unmarked`: pp-ingest's flag, or episode_turns()'s on a recount. The filter keeps an unmarked
     episode and drops only a marked one at <= 0.
   - Test: the ruling-95 test adds pp-ingest's shape for an unmarked episode (0.0, unmarked true) as the newest upload.
     It is the conversation. The marked zero-turn episode stays out.
   - Mutations S9 (drop the unmarked clause) and S10 (pp-ingest's flag never read): both killed.
   - This touches the report only (next_attempt), not a gate.
2. glm and qwen: caption_evidence counted the units AFTER its guard (only the reader call was inside the try).
   - A record from another reader with a short unit, a time that is not a number, or a None unit would crash the build.
   - A NaN time compares False with both bounds. It would read as zero changes near the clip: a REFUSAL from evidence
     that cannot be read.
   - Now the counting is inside the guard. Times are float()-ed and must be finite. Any failure is measured False: no
     evidence, never a refusal, and the layout decides.
   - The build's reader (speakers.captions) already refuses NaN and out-of-order times (speakers.py:170). So this
     guards an injected reader.
   - Test: test_a_record_that_cannot_be_counted_is_no_evidence_never_a_refusal_never_a_crash covers NaN, "noon",
     1-tuples and a None unit. The same record read cleanly does refuse.
   - Mutations S11 (no finite check) and S12 (the guard narrowed to OSError): both killed.

Mutation check: 21 of 21 killed. In the scratch copy: 20 suites, 560 tests, all pass.

## Refuted, with evidence fro

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0915/C2_STEP.diff (718 lines)
```
   1 | diff --git a/pipeline/moments_gate_adapter.py b/pipeline/moments_gate_adapter.py
   2 | index e66ded2..58ffc93 100644
   3 | --- a/pipeline/moments_gate_adapter.py
   4 | +++ b/pipeline/moments_gate_adapter.py
   5 | @@ -13,10 +13,16 @@ tests/package/run_exam_record.py, which strips "expected" exactly as the harness
   6 |  harness (PP_GATES_REPLAY=1). A gate that could not MEASURE (an exchange never recorded, every back-end unavailable, an
   7 |  unreadable verdict) RAISES GateNotMeasured, which the harness counts as an ERROR (audit p2 M5): it is never a pass and
   8 |  never a free rejection either (law L-m). A deterministic failure is a measured "fail".
   9 | +
  10 | +The orchestrator's 09:03 ET Nov 14 order: the exam runs heimdall_first, bounded by VENDOR-REPORTED dollars on its OWN
  11 | +ledger. make_router() is the ONE configuration the live recording (tests/package/run_exam_record.py) and the harness's
  12 | +offline replay both use, so the replay walks exactly the chains the recording walked.
  13 |  """
  14 |  import os
  15 | +import re
  16 |  
  17 |  import context_integrity as CI
  18 | +import eligibility as E
  19 |  import moments as M
  20 |  import providers as P
  21 |  import vo_fidelity as VF
  22 | @@ -27,6 +33,8 @@ RECORD = os.environ.get("PP_GATES_RECORD_DIR") or os.path.join(REPO, "tests", "p
  23 |  SPEND = os.environ.get("PP_GATES_SPEND") or os.path.join(REPO, "tests", "moments", "proof", "SPEND.json")
  24 |  ENV = P.ENV_PATH
  25 |  THREAD_SAFE = True                     # the router's ledger and recordings are safe across the harness's threads
  26 | +UNIVERSE_HOURS = 24.0                  # R-29: package.current_levels' window (L-v 3): a level only from news this fresh
  27 | +SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")   # R-29: a news headline / summary read sentence by sentence
  28 |  _router = None
  29 |  
  30 |  
  31 | @@ -34,14 +42,50 @@ class GateNotMeasured(Exception):
  32 |      """The gate could not measure this case (the harness's ERROR)."""
  33 |  
  34 |  
  35 | +def make_router(chains=None):
  36 | +    """The exam's router (the orchestrator's 09:03 order). Env: PP_GATES_ROUTING (default "heimdall_first"),
  37 | +    PP_GATES_LIMIT_USD (default 5.00, the exam's bound) counted on PP_GATES_LIMIT_BASIS (default "reported": the
  38 | +    vendors' own dollars), PP_GATES_SPEND (the exam's own ledger), PP_GATES_RECORD_DIR, PP_GATES_REPLAY=1 (offline).
  39 | +    chains: pinned legs (run_exam_record --chain), else the routing's own lists."""
  40 | +    return P.Router(env_path=ENV, record_dir=RECORD, replay=os.environ.get("PP_GATES_REPLAY") == "1",
  41 | +                    spend_path=SPEND, chains=chains or None,
  42 | +                    limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "5.00")),
  43 | +                    limit_basis=os.environ.get("PP_GATES_LIMIT_BASIS", "reported"),
  44 | +                    routing=os.environ.get("PP_GATES_ROUTING", "heimdall_first"))
  45 | +
  46 | +
  47 |  def router():
  48 |      global _router
  49 |      if _router is None:
  50 | -        _router = P.Router(env_path=ENV, record_dir=RECORD, replay=os.environ.get("PP_GATES_REPLAY") == "1",
  51 | -                           spend_path=SPEND, limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")))
  52 | +        _router = make_router()
  53 |      return _router
  54 |  
  55 |  
  56 | +def universe_levels(universe, hours=UNIVERSE_HOURS):
  57 | +    """R-29 (pp-tests' REQUESTS; the orchestrator's 09:03 order "fix it now"): the Bitcoin price levels a v1.1 case's
  58 | +    universe (tonight's news) states as CURRENT, read the way package.current_levels reads sources: every sentence of a
  59 | +    news item's headline and summary that names Bitcoin (eligibility.names_bitcoin), from an item published at most
  60 | +    `hours` before the universe's own clock (built_at), through vo_fidelity.current_level_values. An item whose time
  61 | +    cannot be read is skipped, as package.current_levels skips such a source. [] is a measurement: no current level,
  62 | +    so any line stating a price as current fails PRICE_NOW. A universe with no zoned clock or no news list raises
  63 | +    ValueError: the harness's ERROR, never a guess."""
  64 | +    now = E._parse_time(universe["built_at"])
  65 | +    if now is None:
  66 | +        raise ValueError(f"the universe's clock built_at={universe.get('built_at')!r} is not a zoned time")
  67 | +    if not isinstance(universe["news"], list):
  68 | +        raise ValueError("the universe's news is not a list")
  69 | +    out = set()
  70 | +    for item in universe["news"]:
  71 | +        age = E.age_hours(item.get("published_at"), now)
  72 | +        if age is None or age > hours:
  73 | +            continue
  74 | +        for part in (item.get("headline") or "", item.get("summary") or ""):
  75 | +            for sentence in SENTENCE_SPLIT.split(part):
  76 | +                if sentence.strip() and E.names_bitcoin(sentence):
  77 | +                    out |= set(VF.current_level_values(sentence))
  78 | +    return sorted(out)
  79 | +
  80 | +
  81 |  def _join(sentences):
  82 |      return " ".join(s["text"] for s in sentences or [])
  83 |  
  84 | @@ -109,7 +153,13 @@ def vo_fidelity(case):
  85 |                                  "text": _join(s["sentences"])}
  86 |      lines = [{"slot": f"{ln['slot']}_{i}", "text": ln["text"], "cites": list(ln.get("cites") or [])}
  87 |               for i, ln in enumerate(case["lines"])]
  88 | +    if case.get("title") is not None:            # R-29 (v1.1): the title is judged like a line, as the packager passes it
  89 | +        if not isinstance(case["title"], str) or not case["title"].strip():
  90 | +            raise ValueError("the case's title is not a non-empty string")
  91 | +        lines.append({"slot": "title", "text": case["title"], "cites": []})
  92 |      levels = case.get("current_levels") if isinstance(case.get("current_levels"), list) else None
  93 | +    if levels is None and case.get("universe") is not None:   # R-29 (v1.1): tonight's news gives the current levels
  94 | +        levels = universe_levels(case["universe"])
  95 |      try:
  96 |          res = VF.check(router(), segments, lines, writer_vendor=None, manifest=man, current_levels=levels)
  97 |      except P.ReplayMiss as e:
  98 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
  99 | index d2bb3d4..2d4ce7b 100644
 100 | --- a/pipeline/spotlight.py
 101 | +++ b/pipeline/spotlight.py
 102 | @@ -36,6 +36,7 @@ CLOSING_GATES, spotlight_problems, first_comment_text, the sealed closing / shap
 103 |  import base64
 104 |  import hashlib
 105 |  import json
 106 | +import math
 107 |  import os
 108 |  import re
 109 |  import threading
 110 | @@ -64,7 +65,9 @@ TRIM_MARGIN_S = 1.0                    # RULING 94 (a): a moment to be trimmed i
 111 |                                         # ONE trimmed word never takes it back under SNAP_TO_S
 112 |  LAYOUTS = ("conversation", "first_hand", "recap", "reaction", "other")
 113 |  LAYOUT_OK = ("conversation", "first_hand")
 114 | -CONVERSATION_TPM = 1.0                 # ruling 92's caption half (see source_test)
 115 | +NEAR_CLIP_S = 300.0                    # RULING 92 AMENDED (09:03 Nov 14): "the 10 minutes around the clip", read as 5
 116 | +                                       # minutes each side of it; ZERO speaker changes there in a marked episode refuses
 117 | +                                       # (the 1.0-turns-a-minute line, CONVERSATION_TPM, is retired by the same ruling)
 118 |  FINALISTS = 3                          # moments taken to exclusion, the pre-check and the write, best first
 119 |  WRITES = 2                             # the title, caption and comment: one more write when a gate refuses them
 120 |  SCORER_WAIT_S = 600.0                  # a moment that passes everything but has no ALONE rating yet waits this long for
 121 | @@ -264,31 +267,76 @@ def episode_turns(video_id, captions_for=None):
 122 |              "file": (rec or {}).get("file"), "sha256": (rec or {}).get("sha256")}
 123 |  
 124 |  
 125 | -def source_test(turns, layout):
 126 | -    """RULING 92 -> (ok, why). A PASS needs a MEASURED layout of a conversation or a first-hand statement
 127 | -    (LAYOUT_OK). A recap, a reaction, or a layout the judge cannot place ('other') fails on any channel; a layout that
 128 | -    is not measured is never a pass (law L-m). The caption markers across the episode can only make it stricter: a
 129 | -    layout read as a conversation from an episode whose captions are marked but carry fewer than CONVERSATION_TPM
 130 | -    turns a minute is not measured as a conversation (Nov 13: Simply Bitcoin's solo recap L6H7538ogGs 0.48 turns a
 131 | -    minute; the pool's interviews and panels 1.18-2.53). Unmarked captions are unknown, not solo: the layout decides."""
 132 | +def caption_evidence(video_id, start, end, captions_for=None):
 133 | +    """RULING 92 AMENDED (09:03 Nov 14): the caption markers are EVIDENCE for the layout judge, not a refusal line. Read
 134 | +    from the episode's caption record with speaker-change markers (speakers.captions, ruling 69's reader): the turns a
 135 | +    minute across the episode; the speaker changes in the 10 minutes around the clip (NEAR_CLIP_S each side of
 136 | +    [start, end]); and whether the clip's own span sits inside one unbroken turn (no marker more than MARKER_TOL_S
 137 | +    inside an edge). -> {"measured", "marked", ...}: marked False when no copy of the captions carries any marker
 138 | +    (unknown, never solo: no evidence either way); measured False when the record cannot be read."""
 139 | +    import speakers as SP
 140 | +    try:                                               # audit 0915 C1: a record that cannot be read OR counted is no
 141 | +        units, rec = (captions_for or SP.captions)(video_id)          # evidence, never a refusal (never a crash)
 142 | +        if not units:
 143 | +            return {"measured": True, "marked": False,
 144 | +                    "why": "no caption record with speaker-change markers: unmarked (unknown, never solo)"}
 145 | +        times = [float(u[0]) for u in units]
 146 | +        if not all(math.isfinite(t) for t in times):
 147 | +            raise ValueError("a caption time is not a finite number")
 148 | +        opens = [t for t, u in zip(times, units) if u[2]]
 149 | +        minutes = (times[-1] - times[0]) / 60.0
 150 | +        return {"measured": True, "marked": True, "turns": len(opens), "minutes": round(minutes, 1),
 151 | +                "turns_per_min": round(len(opens) / minutes, 2) if minutes > 0 else None,
 152 | +                "changes_near": sum(1 for t in opens if start - NEAR_CLIP_S <= t <= end + NEAR_CLIP_S),
 153 | +                "one_turn": not any(start + MARKER_TOL_S < t < end - MARKER_TOL_S for t in opens),
 154 | +                "file": (rec or {}).get("file"), "sha256": (rec or {}).get("sha256")}
 155 | +    except Exception as e:                             # noqa: BLE001
 156 | +        return {"measured": False, "marked": None, "why": f"{type(e).__name__}: {str(e)[:120]}"}
 157 | +
 158 | +
 159 | +def markers_refuse(evidence):
 160 | +    """RULING 92 AMENDED: the ONE case where the caption markers refuse by themselves: the episode is marked and has
 161 | +    ZERO speaker changes in the 10 minutes around the clip."""
 162 | +    ev = evidence or {}
 163 | +    return ev.get("measured") is True and ev.get("marked") is True and ev.get("changes_near") == 0
 164 | +
 165 | +
 166 | +def evidence_text(evidence):
 167 | +    """The caption evidence as the layout judge reads it (one sentence)."""
 168 | +    ev = evidence or {}
 169 | +    if ev.get("measured") is not True:
 170 | +        return "the captions could not be read (no evidence either way)."
 171 | +    if not ev.get("marked"):
 172 | +        return "the captions carry no speaker-change markers (no evidence either way)."
 173 | +    return (f"{ev.get('turns_per_min')} speaker turns a minute across the episode ({ev.get('turns')} in "
 174 | +            f"{ev.get('minutes')} min); {ev.get('changes_near')} speaker change(s) in the 10 minutes around this clip; "
 175 | +            f"the clip's own words sit inside one unbroken turn: {'yes' if ev.get('one_turn') else 'no'}.")
 176 | +
 177 | +
 178 | +def source_test(evidence, layout):
 179 | +    """RULING 92 AMENDED (09:03 Nov 14) -> (ok, why). The LAYOUT verdict decides the source test alone: a MEASURED
 180 | +    layout of a conversation or a first-hand statement (LAYOUT_OK) passes; a recap, a reaction or 'other' fails on any
 181 | +    channel; a layout that is not measured never passes (law L-m). The caption markers are EVIDENCE shown to the
 182 | +    layout judge (layout_for), not a refusal line (the 1.0-turns-a-minute line refused real interviews: 19 of 67
 183 | +    videos at 0.3-1.0); they refuse by themselves only when the episode is marked and has ZERO speaker changes in the
 184 | +    10 minutes around the clip (markers_refuse)."""
 185 | +    if markers_refuse(evidence):
 186 | +        return False, (f"the episode's captions are marked ({evidence.get('turns')} turns in "
 187 | +                       f"{evidence.get('minutes')} min) and show no speaker change in the 10 minutes around the clip")
 188 |      if not (layout or {}).get("measured"):
 189 |          return False, f"the layout is not measured: {(layout or {}).get('why')}"
 190 |      lay = layout["layout"]
 191 |      if lay not in LAYOUT_OK:
 192 |          return False, f"the layout is '{lay}' ({layout.get('why')}): not a conversation or a first-hand statement"
 193 | -    tpm = (turns or {}).get("turns_per_min")
 194 | -    if lay == "conversation" and (turns or {}).get("measured") and (tpm is None or tpm < CONVERSATION_TPM):
 195 | -        return False, (f"the frames read as a conversation but the episode's captions carry {tpm} speaker turns a "
 196 | -                       f"minute (under {CONVERSATION_TPM:g})")
 197 | -    return True, f"layout '{lay}'" + (f"; {turns['turns']} caption turns in {turns['minutes']} min ({tpm} a minute)"
 198 | -                                      if (turns or {}).get("measured") else "; captions unmarked")
 199 | +    return True, f"layout '{lay}'; the captions' evidence: {evidence_text(evidence)}"
 200 |  
 201 |  
 202 |  def next_attempt(rows, word_pass, now, captions_for=None):
 203 |      """RULING 95 (00:40 ET Nov 14): when a build ends with no medley and no spotlight, when the next qualifying episode
 204 | -    could arrive. The NEWEST conversation upload among the adapter's rows: caption turns from pp-ingest's `episode`
 205 | -    (mine-hook/2 rows), else episode_turns(), at least CONVERSATION_TPM a minute (an unmarked episode is not counted:
 206 | -    unknown). Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready or still
 207 | +    could arrive. The NEWEST upload among the adapter's rows whose captions do not refuse it (RULING 92 AMENDED, 09:03
 208 | +    Nov 14: unmarked, or marked with at least one speaker change; the layout decides per clip), its caption turns from
 209 | +    pp-ingest's `episode` (mine-hook/2 rows), else episode_turns(): an episode marked with zero turns is the one
 210 | +    excluded. Each upload's mining state: its rows by pass and prompt version, and its word-pass windows ready or still
 211 |      waiting (word_pass: ledger_build.word_pass_index's {moment_id: row}). -> {"conversation": {...} or None,
 212 |      "newest_upload": {...} or None}."""
 213 |      from datetime import datetime, timedelta, timezone
 214 | @@ -302,9 +350,10 @@ def next_attempt(rows, word_pass, now, captions_for=None):
 215 |          pub = P.utc_z(rs[0].get("published_at"))
 216 |          ep = next((r.get("episode") for r in rs if isinstance(r.get("episode"), dict)), None)
 217 |          tpm, frm = (ep or {}).get("turns_per_min"), "pp-ingest episode"
 218 | -        if not isinstance(tpm, (int, float)) and not (ep or {}).get("unmarked"):
 219 | +        unmarked = (ep or {}).get("unmarked") is True    # pp-ingest writes 0.0 turns a minute AND unmarked for these
 220 | +        if not isinstance(tpm, (int, float)) and not unmarked:
 221 |              t = episode_turns(vid, captions_for)
 222 | -            tpm, frm = t.get("turns_per_min"), "the caption record (recount)"
 223 | +            tpm, frm, unmarked = t.get("turns_per_min"), "the caption record (recount)", t.get("unmarked") is True
 224 |          passes = {}
 225 |          for r in rs:
 226 |              k = f"{(r.get('mined') or {}).get('pass')}/{(r.get('mined') or {}).get('prompt_version')}"
 227 | @@ -315,17 +364,20 @@ def next_attempt(rows, word_pass, now, captions_for=None):
 228 |          age = E.age_hours(rs[0].get("published_at"), now)
 229 |          return {"video_id": vid, "channel": rs[0].get("channel_name"), "published_at": pub, "expires_at": exp,
 230 |                  "age_h": round(age, 1) if age is not None else None,
 231 | -                "turns_per_min": tpm, "turns_from": frm, "rows": len(rs), "passes": passes,
 232 | +                "turns_per_min": tpm, "unmarked": unmarked, "turns_from": frm, "rows": len(rs), "passes": passes,
 233 |                  "word_pass_ready": ready, "word_pass_waiting": len(rs) - ready}
 234 |      sts = sorted((state(v, rs) for v, rs in by_vid.items()), key=lambda x: x["published_at"] or "", reverse=True)
 235 | -    conv = [x for x in sts if isinstance(x["turns_per_min"], (int, float)) and x["turns_per_min"] >= CONVERSATION_TPM]
 236 | +    conv = [x for x in sts if x["unmarked"] or not (isinstance(x["turns_per_min"], (int, float)) and
 237 | +                                                    x["turns_per_min"] <= 0)]       # only MARKED with zero turns is out
 238 |      return {"conversation": conv[0] if conv else None, "newest_upload": sts[0] if sts else None,
 239 | -            "rule": f"the newest upload with >= {CONVERSATION_TPM:g} caption turns a minute (ruling 95)"}
 240 | +            "rule": "the newest upload whose captions do not refuse it (unmarked, or marked with a speaker change; "
 241 | +                    "ruling 92 amended: the layout decides per clip) (ruling 95)"}
 242 |  
 243 |  
 244 |  LAYOUT_PROMPT = """You see a contact sheet of {n} frames of ONE clip from a Bitcoin video, left to right and top to
 245 |  bottom. The clip's words, as spoken: "{text}"
 246 | -From the frames only, classify the SOURCE's format:
 247 | +Evidence from the episode's captions (their speaker-change markers), to weigh with the frames: {evidence}
 248 | +From the frames and that evidence, classify the SOURCE's format:
 249 |  - "conversation": two or more people talking with each other: an interview, a podcast, a panel (in one room, or on a
 250 |    split screen or a video call);
 251 |  - "first_hand": one person making their own statement to an audience: a keynote, a speech, a guest answering on a news
 252 | @@ -359,18 +411,21 @@ def _load_json(path):
 253 |          return {}
 254 |  
 255 |  
 256 | -def layout_for(router, m, vrec, cache_path=None, seed=7):
 257 | +def layout_for(router, m, vrec, cache_path=None, seed=7, evidence=None):
 258 |      """RULING 92's visual half: the source's layout, judged on the clip's own contact sheet (the visual check's, ruling
 259 |      70: the same bytes it judged) with LAYOUT_PROMPT, by the visual_check role (one call, cached by the moment, the
 260 | -    sheet's sha256 and the prompt's version). -> {"measured", "layout", "people_on_screen", "why", "backend",
 261 | -    "replayed"} or {"measured": False, "why"}: never a pass unmeasured."""
 262 | +    sheet's sha256, the prompt's version and the evidence shown). RULING 92 AMENDED (09:03 Nov 14): the judge also
 263 | +    reads the caption markers as EVIDENCE (caption_evidence, evidence_text: turns a minute, changes near the clip, one
 264 | +    unbroken turn), never as a refusal line. -> {"measured", "layout", "people_on_screen", "why", "backend",
 265 | +    "replayed", "evidence"} or {"measured": False, "why"}: never a pass unmeasured."""
 266 |      import providers as Pr
 267 |      from story_semantics import quote_data
 268 |      sheet = (vrec or {}).get("sheet") or {}
 269 |      path, sha = sheet.get("path"), sheet.get("sha256")
 270 |      if not (vrec or {}).get("measured") or not path or not sha:
 271 |          return {"measured": False, "why": "no judged contact sheet (the visual check is not measured)"}
 272 | -    k = f"{m['moment_id']}:{sha}:{LAYOUT_VERSION}"
 273 | +    ev_text = evidence_text(evidence)              # the same evidence, the same key (captions can arrive later)
 274 | +    k = f"{m['moment_id']}:{sha}:{LAYOUT_VERSION}:{hashlib.sha256(ev_text.encode()).hexdigest()[:12]}"
 275 |      hit = _load_json(cache_path).get(k) if cache_path else None
 276 |      if isinstance(hit, dict) and hit.get("measured") is True:
 277 |          return dict(hit, cached=True)
 278 | @@ -382,7 +437,8 @@ def layout_for(router, m, vrec, cache_path=None, seed=7):
 279 |      if hashlib.sha256(raw).hexdigest() != sha:
 280 |          return {"measured": False, "why": "the sheet on disk is not the one the visual check judged"}
 281 |      prompt = {"text": LAYOUT_PROMPT.format(n=len(sheet.get("times") or []),
 282 | -                                           text=quote_data(m.get("text") or "", 700).replace('"', "'")),
 283 | +                                           text=quote_data(m.get("text") or "", 700).replace('"', "'"),
 284 | +                                           evidence=ev_text),
 285 |                "images": [base64.b64encode(raw).decode()]}
 286 |      r = None
 287 |      try:
 288 | @@ -393,7 +449,7 @@ def layout_for(router, m, vrec, cache_path=None, seed=7):
 289 |              router.reject(r)
 290 |          return {"measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 291 |      rec = dict(v, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)),
 292 | -               version=LAYOUT_VERSION, sheet_sha256=sha)
 293 | +               version=LAYOUT_VERSION, sheet_sha256=sha, evidence=ev_text)
 294 |      if cache_path and not rec["replayed"]:
 295 |          with LAYOUT_LOCK:
 296 |              c = _load_json(cache_path)
 297 | @@ -683,8 +739,10 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
 298 |      rows["spotlight_source"] = _row(src_rec["ok"], (src_rec.get("layout") or {}).get("backend"),
 299 |                                      bool((src_rec.get("layout") or {}).get("replayed", False)),
 300 |                                      measured=(src_rec.get("layout") or {}).get("measured") is True,
 301 | -                                    why=src_rec.get("why"), turns=src_rec.get("turns"), layout=src_rec.get("layout"),
 302 | -                                    rule="ruling 92: conversation, not reaction (caption turns + the layout)")
 303 | +                                    why=src_rec.get("why"), evidence=src_rec.get("evidence"), layout=src_rec.get("layout"),
 304 | +                                    rule="ruling 92 amended (09:03 Nov 14): the layout decides (conversation or "
 305 | +                                         "first-hand); the captions are evidence, refusing alone only with zero "
 306 | +                                         "speaker changes in the 10 minutes around the clip")
 307 |      rows["window_12h"] = _row(not PP.window_problems(pk["segments"], facts["now"]),
 308 |                                "code (package_pin.window_problems, ruling 76: <= 12 h on the render clock)",
 309 |                                why=PP.window_problems(pk["segments"], facts["now"]))
 310 | @@ -880,11 +938,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 311 |                    " (asked with the build's scorer candidates)"))
 312 |      passed(fine, 7)
 313 |      ok_src = []
 314 | -    for mid, m in fine.items():
 315 | -        turns = episode_turns(m["video_id"], captions_for)
 316 | -        lay = layout_for(router, m, m.get("visual"), layout_cache)
 317 | -        ok, w = source_test(turns, lay)
 318 | -        m["spotlight_source"] = {"ok": ok, "why": w, "turns": turns, "layout": lay}
 319 | +    for mid, m in fine.items():                        # RULING 92 AMENDED (09:03 Nov 14): the captions as evidence
 320 | +        ev = caption_evidence(m["video_id"], float(m["start"]), float(m["end"]), captions_for)
 321 | +        lay = ({"measured": False, "why": "not asked: the captions refuse the source by themselves"}
 322 | +               if markers_refuse(ev) else                # free, so a refused source never costs a vision call
 323 | +               layout_for(router, m, m.get("visual"), layout_cache, evidence=ev))
 324 | +        ok, w = source_test(ev, lay)
 325 | +        m["spotlight_source"] = {"ok": ok, "why": w, "evidence": ev, "layout": lay}
 326 |          rec[mid]["source"] = w
 327 |          if ok:
 328 |              ok_src.append(m)
 329 | diff --git a/tests/package/run_exam_record.py b/tests/package/run_exam_record.py
 330 | index 9dbc65a..d4de7f6 100644
 331 | --- a/tests/package/run_exam_record.py
 332 | +++ b/tests/package/run_exam_record.py
 333 | @@ -51,8 +51,8 @@ def main(argv=None):
 334 |      for x in a.chain:
 335 |          role, backend = x.split("=", 1)
 336 |          chains.setdefault(role, []).append(backend)
 337 | -    A._router = P.Router(env_path=A.ENV, record_dir=A.RECORD, spend_path=A.SPEND, chains=chains or None,
 338 | -                         limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")))     # the phase-2 guard
 339 | +    A._router = A.make_router(chains=chains or None)    # the harness's own configuration (the orchestrator's 09:03
 340 | +    #   order: heimdall_first, vendor-reported dollars, the exam's own ledger), so its replay walks these chains
 341 |      os.makedirs(a.out, exist_ok=True)
 342 |      log = []
 343 |      for corpus, gate in GATES:
 344 | diff --git a/tests/package/test_exam_adapter.py b/tests/package/test_exam_adapter.py
 345 | new file mode 100644
 346 | index 0000000..12078e9
 347 | --- /dev/null
 348 | +++ b/tests/package/test_exam_adapter.py
 349 | @@ -0,0 +1,165 @@
 350 | +#!/usr/bin/env python3
 351 | +"""pp-tests' REQUESTS R-29 and the exam's router (the orchestrator's 09:03 ET Nov 14 order: "R-29: FIX IT NOW";
 352 | +"THE EXAM: APPROVED ... heimdall_first, bound $5.00 vendor-reported, on its OWN ledger"):
 353 | +pipeline/moments_gate_adapter.py, the one adapter of pp-tests' moments exam, predated vo_fidelity v1.1. Its
 354 | +vo_fidelity() passed no title and no current price levels from the case's universe, so the must-fail cases built on
 355 | +them were never judged on them. Now: the title is judged like a line (as the packager passes it); the universe's news
 356 | +gives the current levels the way package.current_levels reads sources; v1 cases are unchanged; one router
 357 | +configuration serves the live recording and the offline replay."""
 358 | +import os
 359 | +import shutil
 360 | +import sys
 361 | +import tempfile
 362 | +import unittest
 363 | +from unittest import mock
 364 | +
 365 | +HERE = os.path.dirname(os.path.abspath(__file__))
 366 | +REPO = os.path.dirname(os.path.dirname(HERE))
 367 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 368 | +sys.path.insert(0, HERE)
 369 | +import moments_gate_adapter as A  # noqa: E402
 370 | +import vo_fidelity as VF  # noqa: E402
 371 | +
 372 | +PASS = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "fake",
 373 | +        "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 374 | +        "verdict": {"ok": True, "violations": [], "classes": {}, "claims": []}}
 375 | +SEGS = [{"label": "A", "channel": "Coin Bureau", "video_id": "va", "speaker": None,
 376 | +         "sentences": [{"n": 0, "text": "Bitcoin closed just under 76K on the day."}]},
 377 | +        {"label": "B", "channel": "Swan Bitcoin", "video_id": "vb", "speaker": None,
 378 | +         "sentences": [{"n": 0, "text": "We were around $76,000 by the U.S. close."}]}]
 379 | +LINES = [{"slot": "intro", "text": "Coin Bureau, then Swan Bitcoin.", "cites": ["A", "B"], "after": None},
 380 | +         {"slot": "signoff", "text": "That's Pulse Check.", "cites": [], "after": "B"}]
 381 | +# the real stale_price_title__01's title and universe (pp-tests' corpus, v1.1): its $73,500 news is 38 h old
 382 | +UNIVERSE = {"built_at": "2026-11-12T05:06:13.234375+00:00", "date": "2026-11-12", "use": "staleness only",
 383 | +            "news": [{"headline": "Bitcoin Price Trades Down Near $73,500 After Hot CPI Print Lifts Fed Hike Bets",
 384 | +                      "published_at": "2026-11-10T14:28:12.195473+00:00",
 385 | +                      "summary": "Bitcoin price slipped to $73,500 Tuesday morning."},
 386 | +                     {"headline": "Stablecoin Drain, ETF Outflows Leave Bitcoin 'Running on Empty'",
 387 | +                      "published_at": "2026-11-11T21:46:12.195473+00:00",
 388 | +                      "summary": "Stablecoin supply fell $14.2 billion in 30 days."}]}
 389 | +
 390 | +
 391 | +def v11(**over):
 392 | +    return dict({"schema": "pp.vo_case/1.1", "id": "case-x", "segments": SEGS, "lines": LINES,
 393 | +                 "manifest": {"show": "Pulse Check", "date": "2026-11-12", "channels": ["Coin Bureau", "Swan Bitcoin"]},
 394 | +                 "title": "Bitcoin ran from 16K to 126K", "universe": UNIVERSE}, **over)
 395 | +
 396 | +
 397 | +class Capture:
 398 | +    """VF.check as the adapter calls it: the arguments kept, a measured pass returned."""
 399 | +
 400 | +    def __init__(self):
 401 | +        self.calls = []
 402 | +
 403 | +    def __call__(self, router, segments, lines, writer_vendor=None, manifest=None, current_levels=None, **k):
 404 | +        self.calls.append({"segments": segments, "lines": lines, "manifest": manifest, "levels": current_levels})
 405 | +        return PASS
 406 | +
 407 | +
 408 | +class TestR29(unittest.TestCase):
 409 | +    def run_case(self, case):
 410 | +        cap = Capture()
 411 | +        with mock.patch.object(A.VF, "check", cap), mock.patch.object(A, "router", lambda: object()):
 412 | +            out = A.vo_fidelity(case)
 413 | +        return out, cap.calls
 414 | +
 415 | +    def test_the_title_is_judged_like_a_line_and_the_universe_gives_the_levels(self):
 416 | +        out, calls = self.run_case(v11())
 417 | +        self.assertEqual(out["verdict"], "pass")
 418 | +        lines = calls[0]["lines"]
 419 | +        self.assertEqual(lines[-1], {"slot": "title", "text": "Bitcoin ran from 16K to 126K", "cites": []})
 420 | +        self.assertEqual([x["slot"] for x in lines], ["intro_0", "signoff_1", "title"])
 421 | +        self.assertEqual(calls[0]["levels"], [])           # measured: no level inside 24 h (not None: not measured)
 422 | +
 423 | +    def test_a_v1_case_is_unchanged(self):
 424 | +        case = {k: v for k, v in v11().items() if k not in ("title", "universe")}
 425 | +        _, calls = self.run_case(case)
 426 | +        self.assertEqual([x["slot"] for x in calls[0]["lines"]], ["intro_0", "signoff_1"])
 427 | +        self.assertIsNone(calls[0]["levels"])               # as before: price_now not measured without a universe
 428 | +
 429 | +    def test_explicit_current_levels_still_win(self):
 430 | +        _, calls = self.run_case(v11(current_levels=[90000.0]))
 431 | +        self.assertEqual(calls[0]["levels"], [90000.0])
 432 | +
 433 | +    def test_the_universe_reads_like_package_current_levels(self):
 434 | +        fresh = {"headline": "Bitcoin is trading at $73,500 this morning.", "summary": "",
 435 | +                 "published_at": "2026-11-12T01:00:00+00:00"}
 436 | +        u = dict(UNIVERSE, news=UNIVERSE["news"] + [fresh])
 437 | +        self.assertEqual(A.universe_levels(u), [73500.0])   # inside 24 h of built_at; the 38 h old one is not
 438 | +        not_btc = dict(fresh, headline="Ethereum is trading at $73,500 this morning.")   # a level, but not Bitcoin's
 439 | +        self.assertEqual(VF.current_level_values(not_btc["headline"]), [73500.0])
 440 | +        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[not_btc])), [])
 441 | +        unreadable = dict(fresh, published_at="yesterday")
 442 | +        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[unreadable, fresh])), [73500.0])   # skipped
 443 | +        zoneless = dict(fresh, published_at="2026-11-12T01:00:00")
 444 | +        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[zoneless])), [])   # no zone, no measurement
 445 | +        late = dict(fresh, published_at="2026-11-12T09:00:00+00:00")   # after built_at: inside (as for sources)
 446 | +        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[late])), [73500.0])
 447 | +
 448 | +    def test_an_unreadable_case_is_the_harness_error_never_a_guess(self):
 449 | +        for bad in (v11(title=""), v11(title=5), v11(universe=dict(UNIVERSE, built_at="2026-11-12")),
 450 | +                    v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13")), v11(universe={"news": []}),
 451 | +                    v11(universe=dict(UNIVERSE, news="none"))):
 452 | +            with self.assertRaises(A.GateNotMeasured, msg=str(bad.get("title"))):
 453 | +                self.run_case(bad)
 454 | +        with self.assertRaisesRegex(A.GateNotMeasured, "not a zoned time"):           # said plainly, never a guess
 455 | +            self.run_case(v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13")))
 456 | +
 457 | +    def test_the_real_stale_title_case_now_fails_on_its_title_deterministically(self):
 458 | +        """No model: the deterministic layer on the lines the adapter now passes (the 16K / 126K title against the
 459 | +        clips' 76K, with the universe's measured [] levels)."""
 460 | +        _, calls = self.run_case(v11())
 461 | +        c = calls[0]
 462 | +        det = VF.check_deterministic(c["segments"], c["lines"], c["manifest"], c["levels"])
 463 | +        rules = {v["rule"] for v in det["violations"] if v["slot"] == "title"}
 464 | +        self.assertTrue({"NUMBER", "PRICE_NOW"} <= rules, rules)
 465 | +        old = [x for x in c["lines"] if x["slot"] != "title"]   # the old adapter's lines: the title never judged
 466 | +        self.assertFalse([v for v in VF.check_deterministic(c["segments"], old, c["manifest"], None)["violations"]
 467 | +                          if v["slot"] == "title"])
 468 | +
 469 | +
 470 | +class TestExamRouter(unittest.TestCase):
 471 | +    def setUp(self):
 472 | +        self.d = tempfile.mkdtemp()
 473 | +        self.p = [mock.patch.object(A, "SPEND", os.path.join(self.d, "SPEND.json")),
 474 | +                  mock.patch.object(A, "RECORD", os.path.join(self.d, "replies"))]
 475 | +        for p in self.p:
 476 | +            p.start()
 477 | +
 478 | +    def tearDown(self):
 479 | +        for p in self.p:
 480 | +            p.stop()
 481 | +        shutil.rmtree(self.d, ignore_errors=True)
 482 | +
 483 | +    def test_heimdall_first_on_vendor_reported_dollars_bounded_at_5(self):
 484 | +        with mock.patch.dict(os.environ, {}, clear=False):
 485 | +            for k in ("PP_GATES_ROUTING", "PP_GATES_LIMIT_USD", "PP_GATES_LIMIT_BASIS", "PP_GATES_REPLAY"):
 486 | +                os.environ.pop(k, None)
 487 | +            r = A.make_router()
 488 | +        self.assertEqual((r.routing, r.limit_basis, r.limit_usd), ("heimdall_first", "reported", 5.0))
 489 | +        self.assertEqual(r.chain("context_verdict", "step_c")[0], "xai:grok-4.20-0309-reasoning")   # routed lists
 490 | +        with mock.patch.dict(os.environ, {"PP_GATES_ROUTING": "today", "PP_GATES_LIMIT_USD": "4.00",
 491 | +                                          "PP_GATES_REPLAY": "1"}):
 492 | +            r = A.make_router()
 493 | +        self.assertEqual((r.routing, r.limit_usd, r.replay), ("today", 4.0, True))
 494 | +
 495 | +    def test_the_recorder_and_the_harness_share_one_router(self):
 496 | +        import run_exam_record as RX
 497 | +        made = []
 498 | +
 499 | +        def fake(chains=None):
 500 | +            made.append(chains)
 501 | +            return mock.Mock(notices=[])
 502 | +
 503 | +        def no_network(*a, **k):
 504 | +            raise AssertionError("no network in this test")
 505 | +        corpus, out = os.path.join(self.d, "corpus"), os.path.join(self.d, "out")
 506 | +        os.makedirs(corpus)
 507 | +        with mock.patch.object(A, "make_router", fake), mock.patch("urllib.request.urlopen", no_network):
 508 | +            self.assertEqual(RX.main(["--corpus", corpus, "--out", out]), 0)
 509 | +            self.assertEqual(RX.main(["--corpus", corpus, "--out", out, "--chain", "context_verdict=xai:x"]), 0)
 510 | +        self.assertEqual(made, [None, {"context_verdict": ["xai:x"]}])
 511 | +
 512 | +
 513 | +if __name__ == "__main__":
 514 | +    unittest.main()
 515 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 516 | index 7a7d327..a678b34 100644
 517 | --- a/tests/package/test_spotlight.py
 518 | +++ b/tests/package/test_spotlight.py
 519 | @@ -283,25 +283,111 @@ class TestSourceTest(unittest.TestCase):
 520 |      def lay(self, kind):
 521 |          return {"measured": True, "layout": kind, "why": "w", "backend": "b", "replayed": False}
 522 |  
 523 | +    UNMARKED = {"measured": True, "marked": False}
 524 | +
 525 | +    @staticmethod
 526 | +    def marked(tpm, near, one_turn=True):
 527 | +        return {"measured": True, "marked": True, "turns": 10, "minutes": 10.0, "turns_per_min": tpm,
 528 | +                "changes_near": near, "one_turn": one_turn}
 529 | +
 530 |      def test_conversation_or_first_hand_pass_and_recap_reaction_other_fail(self):
 531 | -        unmarked = {"measured": False, "unmarked": True}
 532 |          for kind, want in (("conversation", True), ("first_hand", True), ("recap", False), ("reaction", False),
 533 |                             ("other", False)):
 534 | -            self.assertEqual(SPOT.source_test(unmarked, self.lay(kind))[0], want, kind)
 535 | +            self.assertEqual(SPOT.source_test(self.UNMARKED, self.lay(kind))[0], want, kind)
 536 |  
 537 |      def test_an_unmeasured_layout_is_never_a_pass(self):
 538 | -        ok, why = SPOT.source_test({"measured": True, "turns": 30, "minutes": 10, "turns_per_min": 3.0},
 539 | -                                   {"measured": False, "why": "no sheet"})
 540 | +        ok, why = SPOT.source_test(self.marked(3.0, 4), {"measured": False, "why": "no sheet"})
 541 |          self.assertFalse(ok)
 542 |          self.assertIn("not measured", why)
 543 |  
 544 | -    def test_the_markers_only_make_it_stricter(self):
 545 | -        solo = {"measured": True, "turns": 8, "minutes": 16.5, "turns_per_min": 0.48}     # Nov 13: L6H7538ogGs
 546 | -        talk = {"measured": True, "turns": 20, "minutes": 16.8, "turns_per_min": 1.19}    # Nov 13: 3kV3nWC5SAY
 547 | -        self.assertFalse(SPOT.source_test(solo, self.lay("conversation"))[0])
 548 | -        self.assertTrue(SPOT.source_test(talk, self.lay("conversation"))[0])
 549 | -        self.assertTrue(SPOT.source_test(solo, self.lay("first_hand"))[0])       # a keynote is one voice
 550 | -        self.assertFalse(SPOT.source_test(talk, self.lay("recap"))[0])
 551 | +    def test_ruling_92_amended_the_layout_decides_and_the_1_0_line_is_retired(self):
 552 | +        """09:03 Nov 14: the 1.0 line was drawn from one solo recap at 0.48 and refused real interviews (Bitcoin
 553 | +        Magazine's, CoinDesk's, Pompliano at 0.97). Turns a minute are evidence now, never a refusal line."""
 554 | +        for tpm in (0.48, 0.61, 0.97, 1.19):
 555 | +            self.assertTrue(SPOT.source_test(self.marked(tpm, 2), self.lay("conversation"))[0], tpm)
 556 | +            self.assertFalse(SPOT.source_test(self.marked(tpm, 2), self.lay("recap"))[0], tpm)
 557 | +        self.assertTrue(SPOT.source_test(self.marked(0.3, 1, one_turn=False), self.lay("first_hand"))[0])
 558 | +
 559 | +    def test_the_markers_refuse_alone_only_with_zero_changes_in_the_10_minutes_around_the_clip(self):
 560 | +        ok, why = SPOT.source_test(self.marked(2.5, 0), self.lay("conversation"))
 561 | +        self.assertFalse(ok)                                   # even a conversation layout: zero changes near the clip
 562 | +        self.assertIn("no speaker change in the 10 minutes around the clip", why)
 563 | +        self.assertTrue(SPOT.source_test(self.marked(0.2, 1), self.lay("conversation"))[0])   # one change: the layout
 564 | +        for unknown in (self.UNMARKED, {"measured": False, "marked": None, "why": "unreadable"}, None, {}):
 565 | +            self.assertFalse(SPOT.markers_refuse(unknown), unknown)    # no evidence is never a refusal
 566 | +            self.assertTrue(SPOT.source_test(unknown, self.lay("conversation"))[0], unknown)
 567 | +        self.assertFalse(SPOT.markers_refuse(dict(self.marked(1.0, 0), measured=False)))   # unmeasured counts nothing
 568 | +
 569 | +
 570 | +class TestCaptionEvidence(unittest.TestCase):
 571 | +    """RULING 92 AMENDED (09:03 Nov 14): the caption markers read as EVIDENCE for the layout judge."""
 572 | +    UNITS = [(0.0, "a", True), (100.0, "b", False), (400.0, "c", True), (900.0, "d", True), (1500.0, "e", False)]
 573 | +
 574 | +    def ev(self, start, end, units=None):
 575 | +        return SPOT.caption_evidence("v", start, end, captions_for=lambda vid: (
 576 | +            self.UNITS if units is None else units, {"file": "f", "sha256": "s"}))
 577 | +
 578 | +    def test_turns_a_minute_changes_near_the_clip_and_one_unbroken_turn(self):
 579 | +        e = self.ev(420.0, 440.0)                  # markers at 0, 400, 900; the 10 minutes around it: 120-740 s
 580 | +        self.assertEqual((e["marked"], e["turns"], e["minutes"], e["turns_per_min"]), (True, 3, 25.0, 0.12))
 581 | +        self.assertEqual((e["changes_near"], e["one_turn"]), (1, True))
 582 | +        self.assertFalse(SPOT.markers_refuse(e))
 583 | +        e = self.ev(890.0, 910.0)                  # the 900 s marker falls inside the clip
 584 | +        self.assertEqual((e["changes_near"], e["one_turn"]), (1, False))
 585 | +        e = self.ev(1300.0, 1320.0)                # 1000-1620 s: no marker
 586 | +        self.assertEqual(e["changes_near"], 0)
 587 | +        self.assertTrue(SPOT.markers_refuse(e))
 588 | +        self.assertEqual(self.ev(899.5, 920.0)["one_turn"], True)   # a marker within MARKER_TOL_S of an edge is not in
 589 | +
 590 | +    def test_unmarked_or_unreadable_captions_are_no_evidence(self):
 591 | +        e = SPOT.caption_evidence("v", 1.0, 2.0, captions_for=lambda vid: (None, None))
 592 | +        self.assertEqual((e["measured"], e["marked"]), (True, False))
 593 | +        self.assertFalse(SPOT.markers_refuse(e))
 594 | +
 595 | +        def boom(vid):
 596 | +            raise OSError("disk")
 597 | +        e = SPOT.caption_evidence("v", 1.0, 2.0, captions_for=boom)
 598 | +        self.assertEqual((e["measured"], e["marked"]), (False, None))
 599 | +        self.assertFalse(SPOT.markers_refuse(e))
 600 | +
 601 | +    def test_a_record_that_cannot_be_counted_is_no_evidence_never_a_refusal_never_a_crash(self):
 602 | +        """Audit 0915 C1: the counting sits inside the guard. A NaN time compares False with every bound, so it would
 603 | +        read as 'zero changes near the clip' and refuse; a time that is not a number would crash the build."""
 604 | +        nan = [(float("nan"), "a", True), (100.0, "b", True), (2500.0, "c", False)]
 605 | +        for units in (nan, [("noon", "a", True), (60.0, "b", False)], [(1.0,), (2.0,)], [(1.0, "a", True), None]):
 606 | +            e = self.ev(2000.0, 2020.0, units)
 607 | +            self.assertEqual((e["measured"], e["marked"]), (False, None), units)
 608 | +            self.assertFalse(SPOT.markers_refuse(e), units)
 609 | +            self.assertEqual(SPOT.evidence_text(e), "the captions could not be read (no evidence either way).")
 610 | +        e = self.ev(2000.0, 2020.0, [(0.0, "a", True), (100.0, "b", True), (2500.0, "c", False)])  # the same, read
 611 | +        self.assertEqual((e["measured"], e["changes_near"]), (True, 0))                          # cleanly: refused
 612 | +        self.assertTrue(SPOT.markers_refuse(e))
 613 | +
 614 | +    def test_the_layout_judge_reads_the_evidence_and_its_cache_keys_on_it(self):
 615 | +        import hashlib
 616 | +        d = tempfile.mkdtemp()
 617 | +        try:
 618 | +            sheet = os.path.join(d, "sheet.jpg")
 619 | +            with open(sheet, "wb") as f:
 620 | +                f.write(b"jpeg-bytes")
 621 | +            vrec = {"measured": True, "sheet": {"path": sheet, "sha256": hashlib.sha256(b"jpeg-bytes").hexdigest(),
 622 | +                                                "times": [0.0, 1.0]}}
 623 | +            ans = '{"layout": "conversation", "people_on_screen": 2, "why": "two people"}'
 624 | +            r = Router(visual_check=[ans, ans])
 625 | +            seen, inner = [], r.call
 626 | +            r.call = lambda role, prompt, *a, **k: (seen.append(prompt["text"]), inner(role, prompt, *a, **k))[1]
 627 | +            cache, m = os.path.join(d, "LAYOUT_CACHE.json"), {"moment_id": "m1", "text": "We talked about it."}
 628 | +            e1 = self.ev(420.0, 440.0)
 629 | +            self.assertEqual(SPOT.layout_for(r, m, vrec, cache, evidence=e1)["layout"], "conversation")
 630 | +            self.assertIn("0.12 speaker turns a minute across the episode (3 in 25.0 min)", seen[0])
 631 | +            self.assertIn("1 speaker change(s) in the 10 minutes around this clip", seen[0])
 632 | +            self.assertIn("inside one unbroken turn: yes", seen[0])
 633 | +            self.assertTrue(SPOT.layout_for(r, m, vrec, cache, evidence=e1).get("cached"))     # same evidence: cached
 634 | +            SPOT.layout_for(r, m, vrec, cache, evidence={"measured": True, "marked": False})  # other evidence: asked
 635 | +            self.assertEqual(len(seen), 2)
 636 | +            self.assertIn("no speaker-change markers (no evidence either way)", seen[1])
 637 | +        finally:
 638 | +            shutil.rmtree(d, ignore_errors=True)
 639 |  
 640 |  
 641 |  class TestContracts(unittest.TestCase):
 642 | @@ -456,7 +542,7 @@ class TestRuling94And95(unittest.TestCase):
 643 |                   "moment_id": "o1", "episode": {"turns_per_min": 2.0}, "mined": {"pass": "hook",
 644 |                                                                                  "prompt_version": "mine-hook/2"}},
 645 |                  {"video_id": "new", "channel_name": "Solo", "published_at": "2026-11-13T22:00:00+00:00",
 646 | -                 "moment_id": "n1", "episode": {"turns_per_min": 0.4}, "mined": {"pass": "moment",
 647 | +                 "moment_id": "n1", "episode": {"turns_per_min": 0.0}, "mined": {"pass": "moment",
 648 |                                                                                  "prompt_version": "mine/2"}},
 649 |                  {"video_id": "mid", "channel_name": "Panel", "published_at": "2026-11-13T20:00:00+00:00",
 650 |                   "moment_id": "m1", "episode": {"turns_per_min": 1.5}, "mined": {"pass": "hook",
 651 | @@ -470,7 +556,18 @@ class TestRuling94And95(unittest.TestCase):
 652 |                           ("mid", "2026-11-13T20:00:00Z", "2026-11-14T08:00:00Z"))
 653 |          self.assertEqual((c["rows"], c["word_pass_ready"], c["word_pass_waiting"]), (2, 1, 1))
 654 |          self.assertEqual(c["passes"], {"hook/mine-hook/2": 1, "moment/mine/2": 1})
 655 | -        self.assertEqual(na["newest_upload"]["video_id"], "new")           # newer, but not a conversation
 656 | +        self.assertEqual(na["newest_upload"]["video_id"], "new")           # newer, but marked with ZERO turns
 657 | +        newer = {"video_id": "int", "channel_name": "Interview", "published_at": "2026-11-13T23:00:00+00:00",
 658 | +                 "moment_id": "i1", "episode": {"turns_per_min": 0.4}, "mined": {"pass": "hook",
 659 | +                                                                                "prompt_version": "mine-hook/3"}}
 660 | +        self.assertEqual(SPOT.next_attempt(rows + [newer], {}, NOW)["conversation"]["video_id"], "int")   # 92 amended:
 661 | +        #   0.4 turns a minute is evidence now, not under a line: an interview at 0.4 counts (the layout decides)
 662 | +        unmarked = {"video_id": "um", "channel_name": "Show", "published_at": "2026-11-13T23:30:00+00:00",
 663 | +                    "moment_id": "u1", "episode": {"turns_per_min": 0.0, "unmarked": True},   # pp-ingest's shape for
 664 | +                    "mined": {"pass": "hook", "prompt_version": "mine-hook/3"}}              # an unmarked episode
 665 | +        u = SPOT.next_attempt(rows + [unmarked], {}, NOW)["conversation"]                  # (audit 0915 C1):
 666 | +        self.assertEqual((u["video_id"], u["unmarked"], u["turns_per_min"]), ("um", True, 0.0))   # unknown, not solo
 667 | +        self.assertFalse(SPOT.next_attempt(rows, {}, NOW)["newest_upload"]["unmarked"])   # 'new' is MARKED, zero turns
 668 |          self.assertEqual(c["age_h"], round((NOW - datetime(2026, 11, 13, 20, 0, tzinfo=timezone.utc)).total_seconds()
 669 |                                             / 3600, 1))
 670 |          self.assertIsNone(SPOT.next_attempt([], {}, NOW)["conversation"])
 671 | @@ -561,7 +658,7 @@ class TestBuild(unittest.TestCase):
 672 |      """The stages in order on stubs: each stage's failure is recorded with how far the moment got."""
 673 |  
 674 |      def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None, visual=None,
 675 | -                  onset=None):
 676 | +                  onset=None, evidence=None):
 677 |          ctx = E.Context(NOW, REG)
 678 |          calls = {}
 679 |  
 680 | @@ -591,8 +688,10 @@ class TestBuild(unittest.TestCase):
 681 |                   (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
 682 |                   (VP, "visual_for", lambda r, m, w, c: dict({"measured": True, "flags": [], "burned_in": [],
 683 |                                                                "backend": "fake:vis"}, **(visual or {}))),
 684 | -                 (SPOT, "layout_for", lambda r, m, v, c: {"measured": True, "layout": layout, "why": "w"}),
 685 | -                 (SPOT, "episode_turns", lambda vid, c=None: {"measured": False, "unmarked": True}),
 686 | +                 (SPOT, "layout_for", lambda r, m, v, c, **k: (calls.setdefault("layout", []).append(
 687 | +                     (m["moment_id"], k.get("evidence"))), {"measured": True, "layout": layout, "why": "w"})[1]),
 688 | +                 (SPOT, "caption_evidence", lambda vid, s, e, c=None: evidence or {"measured": True,   # 92 amended
 689 | +                                                                                   "marked": False}),
 690 |                   (SPOT.P, "exclusion_for", lambda r, m, s, c: {"verdict": "keep"}),
 691 |                   (SPOT.P, "_writers", lambda r: (set(), set()))]
 692 |          patches = [mock.patch.object(o, n, f) for o, n, f in stubs]
 693 | @@ -617,6 +716,24 @@ class TestBuild(unittest.TestCase):
 694 |          self.assertIn("ALONE scorer: 3.0", out["moments"]["c"]["out"])
 695 |          self.assertIsNotNone(out["package"])
 696 |  
 697 | +    def test_ruling_92_amended_zero_changes_near_the_clip_stops_before_any_vision_call(self):
 698 | +        """09:03 Nov 14: the markers refuse alone only when the episode is marked and shows ZERO speaker changes in the
 699 | +        10 minutes around the clip; then the layout judge (a paid vision call) is never asked. Any other evidence goes
 700 | +        to the judge WITH the evidence, and the layout decides."""
 701 | +        ms = [moment(mid="a", channel="A")]
 702 | +        quiet = {"measured": True, "marked": True, "turns": 5, "minutes": 30.0, "turns_per_min": 0.17,
 703 | +                 "changes_near": 0, "one_turn": True}
 704 | +        out, calls = self.run_build(ms, {"a": 4}, alone=[4.0], evidence=quiet)
 705 | +        self.assertIsNone(out["package"])
 706 | +        self.assertNotIn("layout", calls)                                  # no vision call was paid
 707 | +        self.assertIn("no speaker change in the 10 minutes around the clip", out["moments"]["a"]["out"])
 708 | +        talk = dict(quiet, turns_per_min=0.61, changes_near=3)             # Stephan Livera's 0.61: under the old line
 709 | +        out, calls = self.run_build(ms, {"a": 4}, alone=[4.0], evidence=talk)
 710 | +        self.assertEqual(calls["layout"], [("a", talk)])                   # the judge sees the evidence
 711 | +        self.assertIsNotNone(out["package"])                               # the layout (conversation) decides
 712 | +        self.assertIn("layout 'conversation'", out["moments"]["a"]["source"])
 713 | +        self.assertIn("0.61 speaker turns a minute", out["moments"]["a"]["source"])
 714 | +
 715 |      def test_it_waits_for_the_alone_scorer_and_reports_the_nearest(self):
 716 |          ms = [moment(mid="a", channel="A")]
 717 |          later = {"a": sv(TEXT, 4.0)}
 718 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff; if uncertain, say so; do not guess. Be specific: file:line and a concrete input that breaks it.

BACKGROUND (static):
- pipeline/moments_gate_adapter.py is the ONE adapter of another team's exam (pp-tests: corpora of hostile must-fail
  and must-pass cases for three gates: context integrity, VO fidelity, exclusion). The harness strips the expected
  answer and calls the adapter's functions. Live model replies are recorded by tests/package/run_exam_record.py; the
  harness then replays them OFFLINE (PP_GATES_REPLAY=1), and the router serves the first back-end in its chain that
  has a recording, so the replay must walk the same chains as the recording.
- VO fidelity (vo_fidelity.check) judges each VO line, the title and caption: a deterministic layer (NUMBER, NEEDS_SOURCE,
  PRICE_NOW ...) then a model verdict. PRICE_NOW: with current_levels a list, a line stating a price as current that
  matches no level (5 % tolerance) fails; with current_levels None, PRICE_NOW is not measured. package.current_levels
  (the packager) reads levels from sources: each sentence naming Bitcoin, from sources <= 24 h old, through
  vo_fidelity.current_level_values.
- The SPOTLIGHT (ruling 90) is a one-moment video; ruling 92 is its source test ("conversation, not reaction"): a
  vision judge classifies the clip's contact sheet (layout_for: conversation / first_hand / recap / reaction / other);
  the episode's caption speaker-change markers ('>>') were also used.

THE ORCHESTRATOR'S RULINGS (09:03 ET Nov 14), verbatim:
- "R-29: FIX IT NOW, while the pool is empty (about 20 lines, tests, two cycles). An exam whose must-fail cases pass
  by construction is worse than no exam."
  R-29 (pp-tests): the adapter's vo_fidelity() never passed v1.1's `title` (judged like a line) and derived no current
  price level from v1.1's `universe` (tonight's news). Minimal fix: the title as a line; current_levels from
  universe.news the way package.current_levels does from sources (published <= 24 h before the universe's date).
- "THE EXAM: APPROVED to run after R-29 and the integrator's merge of pp-tests, heimdall_first, bound $5.00
  vendor-reported, on its OWN ledger (not the $20 batch cap); stop and tell me at $4."
- "RULING 92 AMENDED (...): the 1.0 line was drawn from one solo recap at 0.48 and refuses real interviews. FROM NOW:
  the LAYOUT verdict decides the source test alone (CONVERSATION or FIRST_HAND pass; RECAP, REACTION, OTHER fail;
  unmeasured never passes). The caption markers are EVIDENCE shown to the layout judge (turns a minute, and whether
  the clip's own span sits inside one unbroken turn), not a refusal line; they refuse by themselves only when the
  episode is marked and has ZERO speaker changes in the 10 minutes around the clip. Audit as one small change with
  R-29 or after it."

THE CHANGE (the diff follows):
1. moments_gate_adapter.vo_fidelity: a v1.1 case's title is appended as a line {"slot": "title", "text": ..., "cites":
   []}; when the case has a universe (and no explicit current_levels), current_levels = universe_levels(universe):
   each sentence of a news item's headline / summary that names Bitcoin, from items published <= 24 h before the
   universe's clock (built_at, zoned; an item with an unreadable time skipped, as package.current_levels skips such a
   source), through current_level_values. [] is a measurement. A title that is not a non-empty string, a universe with
   no zoned clock or no news list: ValueError -> GateNotMeasured (the harness's ERROR). v1 cases are unchanged.
   Measured on the real corpus: both stale-title cases now fail on their title (NEEDS_SOURCE, NUMBER, PRICE_NOW); their
   $73,500 news is 38-45 h old, so their levels are [] (the 5 % tolerance would have accepted the stale $76,000 line
   against $73,500).
2. make_router(): ONE router configuration for the recorder and the replay: PP_GATES_ROUTING (default
   heimdall_first), PP_GATES_LIMIT_USD (default 5.00), PP_GATES_LIMIT_BASIS (default "reported"), PP_GATES_SPEND (the
   exam's own ledger). run_exam_record.py now calls it instead of building its own Router (no routing, $64.28,
   estimate basis).
3. spotlight.py, ruling 92 amended: caption_evidence() (turns a minute; speaker changes in NEAR_CLIP_S = 300 s each
   side of the clip; one unbroken turn = no marker more than MARKER_TOL_S inside the clip); markers_refuse() (marked
   AND zero changes near); source_test(evidence, layout) (the layout decides; the 1.0 line, CONVERSATION_TPM, retired);
   layout_for(..., evidence) shows the evidence in the prompt and keys its cache on it; the build skips the vision
   call when the markers refuse; the ruling-95 report counts any upload whose captions do not refuse it.
4. Tests: tests/package/test_exam_adapter.py (new, 8) and test_spotlight.py (amended). 17 mutations, each killed.
   20 suites, 559 tests.

ATTACK:
(a) R-29: can a v1.1 must-fail case still pass by construction (the title or the universe not reaching the gate)?
    Does anything change for v1 cases? Is the 24 h window on built_at the right reading of "24 h before the
    universe's date", and is skipping an unreadable item right?
(b) The router: can the replay walk different chains than the recording? Can the exam spend past $5 vendor-reported,
    or touch the $20 batch ledger (SPEND_LY.json)? Can it reach a GPU (local:) or a frozen vendor leg?
(c) Ruling 92 amended: can a marked episode with a speaker change near the clip be refused by the captions? Can an
    unmarked or unreadable caption record refuse? Can an unmeasured layout pass? Is "the 10 minutes around the clip"
    read sensibly? Can a cached layout verdict be reused under different evidence?
(d) Anything else that could seal a wrong spotlight pin or score the exam wrongly.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario), then
"SHIP: yes / no / yes with conditions".


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
