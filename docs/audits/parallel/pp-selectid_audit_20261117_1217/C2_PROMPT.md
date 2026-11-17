# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1217
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 115 s finish=stop usage in 12763 / out 17538 usd_reported=0.002569 usd~0.301 (upper-bound price)

**Findings**

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | `soft_second` does not add flags to the cleared moments | **P0** | The test `TestStage2a.test_soft_codes_and_the_second_family` expects `cleared["b"].get("step_a_flags")` to be set, but `soft_second` only returns a dict and never mutates `cleared`. |
| 2 | `inventory` uses the wrong condition for the `context_a` gate | **P0** | The status of `context_a` is computed with `all((t.get("edges") or {}).get("cuttable") is True or (soft and soft_edges(t)) for t in truth.values())`, which makes the gate PASS for the test data. It should be based on `soft_a` (all step‑A codes are soft). |
| 3 | `inventory` builds `lab_codes` using the keys of `a_by` (moment IDs) instead of clip labels | **P1** | In the real pipeline `a_by` keys are moment IDs, while `seg_flags` and `who` are keyed by clip labels. This mismatch means the second‑family soft codes are never merged into the context‑A flags. |
| 4 | `inventory` constructs `context_a` flags with the wrong label (`mid` instead of the clip label) | **P1** | The flag sentence uses `lb` (moment ID) as the clip label, producing incorrect wording and wrong channel names. |
| 5 | `inventory` passes the wrong key to `who` when building `context_a` flags | **P1** | Because `lb` is a moment ID, `(who or {}).get(lb)` returns `None`, so the channel name is omitted from the flag sentence. |
| 6 | `inventory` uses `lab_codes[lb]` where `lb` may be a moment ID, not a label | **P1** | The flag list is empty or wrong when `a_by` keys are moment IDs, leading to missing or incorrect flags. |
| 7 | `soft_step_a` is defined but never used in `_build` | **P2** | While not currently exercised, the function is dead code and could cause confusion or future regressions. |
| 8 | `soft_step_a` uses `fails.get(m["moment_id"])` but `fails` may be `None` | **P2** | If `fails` is `None`, the function will raise an exception. |
| 9 | `soft_step_a` returns a new dict but does not preserve other keys of the moment | **P2** | The returned moment loses any existing data that might be needed downstream. |
| 10 | `soft_edges` requires `t.get("ok") is True` but the test data sometimes has `ok` missing | **P2** | This could silently drop valid soft‑edge cases. |

**P1_OR_WORSE: 6**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 333 s finish=stop usage in 13950 / out 12393 usd_reported=0.011378 usd~0.228 (upper-bound price)



# Code Audit: pp-selectid-20261117_1217 (RULING 137 Stage 2a)

## Scope Reviewed
`pipeline/package.py`, `pipeline/package_pin.py`, `tests/package/test_ruling_137.py` — the soft/soft gate switch for the never-empty pass (second-family step-A refusals + CUTTABLE sentence-edge run-on).

---

## Findings

### [P3] Redundant `soft_codes` evaluation in the re-screen branch (package.py, diff line 130–132)

```python
elif soft and got_a.get(mid) is not None and soft_codes(fails_a.get(mid)):
    add_flags(m, soft_codes(fails_a[mid]))       # second call, same input
    a_by[mid] = got_a[mid]
```

`soft_codes` is a pure function; the second call recomputes the same sorted set. Not a correctness issue, but a reader (or a future mutation) could be confused about whether the two calls could diverge. Storing the result in a local before the `elif` body would make the intent explicit.

### [P3] `cuttable` row override condition omits the `soft and` guard (package.py, diff line 209)

```python
# base row:
all((t.get("edges") or {}).get("cuttable") is True or (soft and soft_edges(t)) for t in truth.values())
# override condition:
all((t.get("edges") or {}).get("cuttable") is True or soft_edges(t) for t in truth.values())
```

Harmless in practice: the override is gated on `edge_fl` being non-empty, which itself requires `soft` to be True (the `edge_fl` comprehension has `if soft and …`). But the asymmetry is a latent trap if someone later restructures the `edge_fl` computation. Adding `soft and` to the override condition would make the two expressions structurally identical and self-documenting.

### [P3] `soft_second` mutates `cleared`'s moment dicts in place via `add_flags` before the filter re-binds `cleared` (package.py, diff lines 55–64, 110)

```python
def soft_second(cleared, a_two, off_fail):
    ...
    add_flags(m, c)          # mutates m in place
    ...
cleared = {mid: m for mid, m in cleared.items() if mid in a_two or mid in soft_two}
```

The filter creates a new dict but the values are the same (now-mutated) dicts. This is consistent with the re-screen's `add_flags(m, …)` pattern and with how `cut_soft` sets `cleared[mid]["edge_flags"]`. No bug, but a reader scanning for "where does `step_a_flags` get set?" must follow the mutation rather than a return value. A brief comment at the `add_flags` call site noting "mutates the moment so the flag is visible to inventory" would help the next auditor.

---

## Verification of the Five Requested Checks

### (1) Nothing HARD can pass

| Hard condition | Where it's enforced | Verdict |
|---|---|---|
| Word mismatch (`ok` is not True) | `soft_edges` line 29: `t.get("ok") is not True` → return None | ✓ stays hard |
| Error / missing edges | `soft_edges` line 29: `t.get("error")` / `not isinstance(t.get("edges"), dict)` → None | ✓ |
| Non-run-on edge reason | `soft_edges` line 33: `startswith(EDGE_SOFT[k])` must match for **every** bad edge | ✓ |
| Window-edge edge ("no word before/after it") | Test line 274–282: `soft_edges` returns None | ✓ |
| Trimmed word | Test line 276: "the recogniser does not hear the trimmed word…" → None | ✓ |
| Hard step-A code (STALE_TIME, SPEAKER_CHANGE, RETRACTION) | `soft_codes` line 46: `all(str(c) in STEP_A_SOFT)` → False → None | ✓ |
| Held moment | `soft_codes` line 46: `not is_held(f)` → False → None | ✓ |
| No verdict (re-screen) | Line 130: `got_a.get(mid) is not None` required | ✓ |
| FLAGGED `second_pass` at the pin | `SOFT_GATES` does not include `"second_pass"`; test line 315–317 raises `PinRefused` | ✓ |
| `L-v 2` word check (`second_pass` row) | Never in `SOFT_GATES`; inventory row unchanged | ✓ |

**No hard path can be converted to soft.** Fail-closed (M12) is maintained: missing data, errors, and unmeasured edges all return None from the soft helpers, keeping the moment out.

### (2) Clean pass is unchanged

Every new code path in `_build` is gated on `soft` (a parameter defaulting to False):
- `cut_soft = {…} if soft else {}` (line 87)
- `soft_two = soft_second(…) if soft else {}` (line 105)
- Re-screen: `elif soft and …` (line 130)
- `inventory`: `if soft and …` in `edge_fl` and the `cuttable` override (lines 175, 203, 209)
- `soft_a` requires `soft` (line 183)

The clean pass calls `_build` without `soft=True`; all new branches are dead code. The `soft_step_a` refactor (lines 72–78) is behaviourally identical to the old inline check (verified by the existing stage-1 tests). **Clean pass is byte-for-byte unchanged in behaviour.** ✓

### (3) The three `_build` call sites

| Site | What it does | Correct? |
|---|---|---|
| CUTTABLE filter (lines 87–96) | Computes `cut_soft` for non-cuttable moments whose only failure is a run-on edge; sets `edge_flags` on the moment; keeps them in `cleared` | ✓ — `soft_edges` is the sole gate; `cut_ok` still applies to all other moments |
| Second-family filter 

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1217, stage 2a)

SEATS ANSWERED: 2 of 3. qwen3.8-27b: P0/P1 none, a traced review. gpt-oss-20b: 6 P0/P1 claimed, every one refuted below
from the code. gemma-4-31b-it: its 24,000-token cap ran out with no answer.

## gpt-oss's claims, checked against the code (the unchanged lines below were outside cycle 1's diff hunks)
1. [P0] "soft_second never mutates cleared": REFUTED. soft_second (package.py:528) calls add_flags(m, c) (:536), and
   add_flags (:522) sets m["step_a_flags"] on the moment object held in cleared. The test asserts
   cleared["b"]["step_a_flags"] == ["REFERENT_OUTSIDE"], and mutation E4 (add_flags removed) is killed.
2. [P0] "context_a's status uses the cuttable expression": REFUTED. context_a is row(bool(a_rows) and (not a_codes or
   soft_a), ...). The expression quoted belongs to the separate "cuttable" row.
3-6. [P1 x4] "inventory's a_by is keyed by moment id, so lab_codes, who and seg_flags miss": REFUTED. Both call sites
   pass a_by = a_lab, built UNCHANGED as {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]} (package.py:3685
   and :4173): keyed by LABEL, like who and seg_flags. Only truth and exc are keyed by moment id, which is why the
   cuttable flags map through mids. The tests feed a_by={"clip_01": ...}, as the pipeline does.
7. [P2] "soft_step_a is never used in _build": REFUTED. cleared_pool calls it (:556), and _build calls cleared_pool
   (:3227). Stage 1, live.
8. [P2] "fails may be None": DECLINED. prescreen (:649) always returns a dict of failures.
9. [P2] "soft_step_a's copy drops the moment's keys": REFUTED. dict(m, step_a_flags=c) keeps every key of m.
10. [P2] "soft_edges needs ok True": BY DESIGN. A missing ok is an unmeasured word check, and unmeasured is never a
   pass (law L-m), so it stays hard.

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1217/C2_STEP.diff (323 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index f26688d..5b9ed6d 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -96,9 +96,32 @@ CLIP_PLACE = {"hook": "The opening clip", "clip_01": "The second clip", "clip_02
   6 |                "clip_03": "The fourth clip", "clip_04": "The fifth clip"}
   7 |  
   8 |  
   9 | +# RULING 137 stage 2a (line 1, 12:12 ET, default SOFT): CUTTABLE's sentence-edge part is soft. Only these two reasons
  10 | +# of transcript_truth.edges (the sentence running on at a word boundary) flag; every other edge failure stays HARD.
  11 | +EDGE_SOFT = {"in": "the recogniser runs on into the clip", "out": "the recogniser's sentence continues past the clip"}
  12 | +EDGE_WORDS = {"EDGE_IN": "the checker heard the sentence run on into the clip's first word, so it may start "
  13 | +                         "mid-sentence",
  14 | +              "EDGE_OUT": "the checker heard the sentence carry on past the clip's last word, so it may end "
  15 | +                          "mid-sentence"}
  16 | +
  17 | +
  18 |  def flag_sentence(label, channel, code):
  19 |      """RULING 138 (3): one flag as PBX reads it: the clip's place and channel, then what the checker doubted."""
  20 | -    return f"{CLIP_PLACE.get(label, 'A clip')} ({channel or 'its channel'}): {STEP_A_SOFT[code]}."
  21 | +    return f"{CLIP_PLACE.get(label, 'A clip')} ({channel or 'its channel'}): " \
  22 | +           f"{STEP_A_SOFT.get(code) or EDGE_WORDS[code]}."
  23 | +
  24 | +
  25 | +def soft_edges(t):
  26 | +    """RULING 137 stage 2a: a moment's CUTTABLE failure is soft only when its words match (law L-v 2 ok, measured, no
  27 | +    error) and EVERY failing edge failed for the sentence running on at a word boundary (EDGE_SOFT); a word not found,
  28 | +    a trimmed word, an unmeasured edge stay hard. -> ["EDGE_IN" / "EDGE_OUT"] or None."""
  29 | +    if not isinstance(t, dict) or t.get("error") or t.get("ok") is not True or not isinstance(t.get("edges"), dict):
  30 | +        return None
  31 | +    e = t["edges"]
  32 | +    bad = [k for k in ("in", "out") if (e.get(k) or {}).get("ok") is not True]
  33 | +    if not bad or not all(str((e.get(k) or {}).get("why") or "").startswith(EDGE_SOFT[k]) for k in bad):
  34 | +        return None
  35 | +    return ["EDGE_" + k.upper() for k in bad]
  36 |  FLAGGED_DAY_MAX = 2
  37 |  SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
  38 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
  39 | @@ -490,15 +513,39 @@ def is_held(why):
  40 |      return bool(why) and all(str(w).startswith(HELD) for w in why)
  41 |  
  42 |  
  43 | +def soft_codes(f):
  44 | +    """RULING 137: a step-A refusal's codes when every one is SOFT (STEP_A_SOFT) and it is a refusal, not a held
  45 | +    moment (ruling 102), else None (a hard code, a hold, or no refusal keeps it as it was)."""
  46 | +    return sorted({str(c) for c in f}) if f and not is_held(f) and all(str(c) in STEP_A_SOFT for c in f) else None
  47 | +
  48 | +
  49 | +def add_flags(m, codes):
  50 | +    """RULING 137: the moment carries every soft step-A code any screen gave it (each becomes one plain sentence)."""
  51 | +    m["step_a_flags"] = sorted(set(m.get("step_a_flags") or []) | set(codes))
  52 | +    return m
  53 | +
  54 | +
  55 | +def soft_second(cleared, a_two, off_fail):
  56 | +    """RULING 137 STAGE 2a: the moments the SECOND family refused for soft codes only stay, flagged (the same step-A
  57 | +    rule as the first screen's: soft_codes). -> {moment_id: codes}; the moments in cleared carry them."""
  58 | +    out = {}
  59 | +    for mid, m in cleared.items():
  60 | +        c = soft_codes(off_fail.get(mid)) if mid not in a_two else None
  61 | +        if c:
  62 | +            out[mid] = c
  63 | +            add_flags(m, c)
  64 | +    return out
  65 | +
  66 | +
  67 |  def soft_step_a(ms, a_by, fails):
  68 |      """RULING 137 STAGE 1: the moments step A refused for SOFT codes only (STEP_A_SOFT): a step-A answer on file, a
  69 |      refusal (never a held one, ruling 102), and every code soft (one hard code keeps it out). -> {moment_id: a copy of
  70 |      the moment carrying "step_a_flags", its codes}."""
  71 |      out = {}
  72 |      for m in ms:
  73 | -        f = fails.get(m["moment_id"])
  74 | -        if m["moment_id"] in a_by and f and not is_held(f) and all(str(c) in STEP_A_SOFT for c in f):
  75 | -            out[m["moment_id"]] = dict(m, step_a_flags=sorted({str(c) for c in f}))
  76 | +        c = soft_codes(fails.get(m["moment_id"])) if m["moment_id"] in a_by else None
  77 | +        if c:
  78 | +            out[m["moment_id"]] = dict(m, step_a_flags=c)
  79 |      return out
  80 |  
  81 |  
  82 | @@ -3223,7 +3270,16 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  83 |          mid: "PASS" if cut_ok(t) else ("NOT MEASURED: " + t["error"] if t.get("error") else
  84 |                                         "L-v 2 FAIL" if not t.get("ok") else "not cuttable at an edge (ruling C / 7)")
  85 |          for mid, t in tru.items()}
  86 | -    cleared = {mid: m for mid, m in cleared.items() if cut_ok(tru.get(mid) or {})}
  87 | +    cut_soft = {mid: e for mid in cleared if not cut_ok(tru.get(mid) or {})       # RULING 137 stage 2a: a sentence
  88 | +                for e in [soft_edges(tru.get(mid) or {})] if e} if soft else {}    # edge at a word boundary flags
  89 | +    for mid, e in cut_soft.items():
  90 | +        cleared[mid]["edge_flags"] = e
  91 | +    if cut_soft:
  92 | +        out["prescreen"]["soft_edges"] = cut_soft
  93 | +        log(f"  RULING 137 NEVER EMPTY (stage 2a): {len(cut_soft)} moment(s) whose words match fail CUTTABLE only at a "
  94 | +            f"sentence edge (the recogniser runs on at a word boundary) stay, flagged: "
  95 | +            + ", ".join(f"{mid[:8]} {e}" for mid, e in cut_soft.items()))
  96 | +    cleared = {mid: m for mid, m in cleared.items() if cut_ok(tru.get(mid) or {}) or mid in cut_soft}
  97 |      out["prescreen"]["cuttable"] = len(cleared)
  98 |      log(f"  {len(cleared)} of them pass the second recognition pass and CUTTABLE ({time.time() - t0:.0f} s)")
  99 |      hk = {}
 100 | @@ -3320,7 +3376,12 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 101 |          log(f"  RULING 102: held for this build (no leg answered; retried next build): {len(h['first'])} at the first "
 102 |              f"screen, {len(h['second'])} at the second {h['second']}; the local judge (ruling 87's last resort) gave "
 103 |              f"{len(out['prescreen']['last_resort_87'])} step-A verdict(s): {sorted(out['prescreen']['last_resort_87'])}")
 104 | -    cleared = {mid: m for mid, m in cleared.items() if mid in a_two}
 105 | +    soft_two = soft_second(cleared, a_two, off_fail) if soft else {}   # RULING 137 stage 2a: flagged, kept
 106 | +    if soft_two:
 107 | +        out["prescreen"]["soft_second"] = soft_two
 108 | +        log(f"  RULING 137 NEVER EMPTY (stage 2a): {len(soft_two)} moment(s) the second family refused for soft codes "
 109 | +            f"only stay, flagged: " + ", ".join(f"{mid[:8]} {c}" for mid, c in soft_two.items()))
 110 | +    cleared = {mid: m for mid, m in cleared.items() if mid in a_two or mid in soft_two}
 111 |      log(f"  {len(cleared)} of them clear step A from both vendors too (order 06:22 item 45: whichever vendor writes, "
 112 |          f"a verdict off it exists) ({time.time() - t0:.0f} s)")
 113 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 114 | @@ -3629,7 +3690,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 115 |                                  stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 116 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 117 |                                  last_resort=pin_last_resort(pk), soft=soft,   # RULING 102; RULING 137 stage 1
 118 | -                                who={sg["label"]: sg.get("channel") for sg in pk["segments"]})   # RULING 138 (3)
 119 | +                                who={sg["label"]: sg.get("channel") for sg in pk["segments"]},   # RULING 138 (3)
 120 | +                                seg_flags={sg["label"]: (cleared.get(sg["moment_id"]) or {}).get("step_a_flags")
 121 | +                                           for sg in pk["segments"]},                          # RULING 137 stage 2a
 122 | +                                mids={sg["moment_id"]: sg["label"] for sg in pk["segments"]})
 123 |          import package_pin
 124 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 125 |          if problems:
 126 | @@ -3944,6 +4008,9 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 127 |                              if got_a.get(mid) is not None and not fails_a.get(mid):
 128 |                                  a_by[mid] = got_a[mid]
 129 |                                  a_two.setdefault(mid, []).append(got_a[mid])
 130 | +                            elif soft and got_a.get(mid) is not None and soft_codes(fails_a.get(mid)):   # RULING 137
 131 | +                                add_flags(m, soft_codes(fails_a[mid]))       # stage 2a: a soft refusal off the writer
 132 | +                                a_by[mid] = got_a[mid]                        # stays, flagged
 133 |                              else:                              # no verdict off the writers is never a pass (L-m)
 134 |                                  bad[mid] = list(fails_a.get(mid) or [f"{HELD}: no verdict off the writers (law L-m);"
 135 |                                                                       f" held for this build, retried next build"])
 136 | @@ -4114,7 +4181,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 137 |                                              value=val,                       # ruling 91: the takeaway earned its place
 138 |                                              last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 139 |                                              soft=soft, who={sg["label"]: sg.get("channel")   # RULING 137 / 138 (3)
 140 | -                                                            for sg in pk["segments"]})
 141 | +                                                            for sg in pk["segments"]},
 142 | +                                            seg_flags={sg["label"]: (cleared.get(sg["moment_id"]) or {}).get(
 143 | +                                                "step_a_flags") for sg in pk["segments"]},    # RULING 137 stage 2a
 144 | +                                            mids={sg["moment_id"]: sg["label"] for sg in pk["segments"]})
 145 |                      if not ok_c:
 146 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 147 |                          cfl = coh.get("floors") or STANDARD_LINEUP["coherence"]   # ruling 116: its own bar
 148 | @@ -4225,8 +4295,9 @@ def build(*args, never_empty=False, flagged_today=0, **kw):
 149 |      (kw.get("log") or print)(f"  RULING 136 (2) NEVER EMPTY: the clean pass sealed nothing ({out.get('why_none')}); "
 150 |                               f"the second pass lets step A's soft refusals back, flagged (stage 1)")
 151 |      soft = _build(*args, soft=True, **kw)
 152 | -    info = {"stage": 1, "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 153 | -            "soft_back": (soft.get("prescreen") or {}).get("soft_back")}
 154 | +    info = {"stage": "2a", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 155 | +            "soft_back": (soft.get("prescreen") or {}).get("soft_back"),
 156 | +            "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried")}}   # the pass's own record
 157 |      return dict(soft, never_empty=info) if soft.get("package") else dict(out, never_empty=info)
 158 |  
 159 |  
 160 | @@ -4240,7 +4311,8 @@ def _spent(spend):
 161 |  
 162 |  
 163 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 164 | -              hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None):
 165 | +              hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None,
 166 | +              seg_flags=None, mids=None):
 167 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 168 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 169 |      value: ruling 91's value verdict on the medley's takeaway (takeaway_value) -> the "takeaway_value" row, its "text"
 170 | @@ -4262,9 +4334,14 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 171 |          return None if any(not isinstance(x, bool) for x in values) else any(values)
 172 |      det = fid["deterministic"]
 173 |      viol = {v["rule"] for v in ctx_.get("violations") or []}
 174 | +    lab = lambda mid: (mids or {}).get(mid, mid)                      # truth is by moment id; flags name the clip
 175 | +    edge_fl = [flag_sentence(lab(mid), (who or {}).get(lab(mid)), c) for mid, t in (truth or {}).items()   # RULING
 176 | +               if soft and (t.get("edges") or {}).get("cuttable") is not True for c in (soft_edges(t) or [])]   # 137 2a
 177 |      a_rows = list((a_by or {}).values())
 178 | -    a_codes = sorted({str(c) for a in a_rows for c in CI.a_failures(a)})   # RULING 137 stage 1: step A's codes; in the
 179 | -    soft_a = bool(soft and a_codes and all(c in STEP_A_SOFT for c in a_codes))   # never-empty pass, soft ones FLAG
 180 | +    lab_codes = {lb: sorted({str(c) for c in CI.a_failures(a)} | set((seg_flags or {}).get(lb) or []))   # RULING 137:
 181 | +                 for lb, a in (a_by or {}).items()}       # each clip's step-A codes, its verdict's and every screen's soft
 182 | +    a_codes = sorted({c for cs in lab_codes.values() for c in cs})   # ones (stage 2a); in the never-empty pass, soft
 183 | +    soft_a = bool(soft and a_codes and all(c in STEP_A_SOFT for c in a_codes))   # ones FLAG
 184 |      return {
 185 |          "vo_fidelity_deterministic": row(det["ok"], "code (vo_fidelity.check_deterministic)"),
 186 |          "vo_fidelity_verdict": dict(row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"),
 187 | @@ -4281,8 +4358,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 188 |                                sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 189 |                                n=len(a_rows)),
 190 |                            **({"status": "FLAGGED",            # RULING 137 stage 1; 138 (3): a sentence a clip
 191 | -                              "flags": [flag_sentence(lb, (who or {}).get(lb), c) for lb, a in (a_by or {}).items()
 192 | -                                        for c in sorted({str(x) for x in CI.a_failures(a)})]}
 193 | +                              "flags": [flag_sentence(lb, (who or {}).get(lb), c) for lb in (a_by or {})
 194 | +                                        for c in lab_codes[lb]]}
 195 |                               if soft_a and len(a_rows) >= 1 else {}),
 196 |                            **({"last_resort": last_resort} if last_resort else {})),   # RULING 102: the local judge
 197 |          "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
 198 | @@ -4299,10 +4376,14 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 199 |          "second_pass": row(all(t.get("ok") for t in truth.values()), sorted({str(t.get("model")) for t in truth.values()}),
 200 |                             rep(t.get("replayed") for t in truth.values()), n=len(truth),
 201 |                             measured=all("error" not in t for t in truth.values())),
 202 | -        "cuttable": row(all((t.get("edges") or {}).get("cuttable") is True for t in truth.values()),
 203 | +        "cuttable": dict(row(all((t.get("edges") or {}).get("cuttable") is True or (soft and soft_edges(t))
 204 | +                                 for t in truth.values()),
 205 |                          "transcript_truth.edges: the independent recogniser's sentence boundary at every IN and OUT "
 206 |                          "(orchestrator 06:45 ruling C / 7)", rep(t.get("replayed") for t in truth.values()), n=len(truth),
 207 |                          measured=all("edges" in t for t in truth.values())),
 208 | +                         **({"status": "FLAGGED", "flags": edge_fl}       # RULING 137 stage 2a: a sentence edge
 209 | +                            if edge_fl and truth and all((t.get("edges") or {}).get("cuttable") is True or soft_edges(t)
 210 | +                                                         for t in truth.values()) else {})),
 211 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 212 |                            **votes_of(coh)),
 213 |          **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
 214 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 215 | index 5fb02f2..180aba9 100644
 216 | --- a/pipeline/package_pin.py
 217 | +++ b/pipeline/package_pin.py
 218 | @@ -34,7 +34,9 @@ MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"
 219 |  # RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17): a SOFT gate scores and FLAGS. Its row may say "FLAGGED"
 220 |  # with "flags", plain words, sealed with the gates; the pin's moments_package "review_flags" is derived from them
 221 |  # (review_flags_of), at most REVIEW_FLAGS_MAX. STAGE 1: step A's row only. A HARD gate still needs exactly PASS.
 222 | -SOFT_GATES = frozenset({"context_a"})
 223 | +SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's soft codes
 224 | +                        "cuttable"})                       # stage 2a: a sentence edge at a word boundary (L-v 2's
 225 | +#   word check, "second_pass", stays HARD)
 226 |  REVIEW_FLAGS_MAX = 3
 227 |  
 228 |  
 229 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 230 | index bc71226..c322e28 100644
 231 | --- a/tests/package/test_ruling_137.py
 232 | +++ b/tests/package/test_ruling_137.py
 233 | @@ -114,8 +114,9 @@ class TestTheTwoPasses(unittest.TestCase):
 234 |          none, sealed = {"package": None, "why_none": "x"}, {"package": {"p": 1}}
 235 |          calls, out = self.run_build(sealed, sealed, never_empty=True)
 236 |          self.assertEqual((calls, "never_empty" in out), ([False], False))            # a clean package: one pass
 237 | -        calls, out = self.run_build(none, sealed, never_empty=True)
 238 | +        calls, out = self.run_build(none, dict(sealed, prescreen={"soft_back": {}}), never_empty=True)
 239 |          self.assertEqual((calls, out["package"], out["never_empty"]["clean_why_none"]), ([False, True], {"p": 1}, "x"))
 240 | +        self.assertEqual(out["never_empty"]["soft_record"]["prescreen"], {"soft_back": {}})   # the soft pass's record
 241 |          calls, out = self.run_build(none, dict(none, why_none="y"), never_empty=True)
 242 |          self.assertEqual((calls, out["package"], out["never_empty"]["soft_why_none"]), ([False, True], None, "y"))
 243 |          self.assertEqual(self.run_build(none, sealed)[0], [False])                   # never_empty off: as before
 244 | @@ -134,6 +135,78 @@ class TestTheTwoPasses(unittest.TestCase):
 245 |          self.assertEqual(calls, [["lineups", "log"], ["lineups", "log", "soft"]])
 246 |  
 247 |  
 248 | +class TestStage2a(unittest.TestCase):
 249 | +    """RULING 137 STAGE 2a: the second family's soft step-A refusals, and the re-screen's after the writes, flag like the
 250 | +    first's (soft_codes); CUTTABLE's sentence-edge part flags (line 1 12:12 ET, default SOFT) while L-v 2's word check
 251 | +    and every other edge failure stay hard. DataDash 8dbc30ee's real record (replayed 12:1x ET): IN runs on from
 252 | +    'line:', 100 ms, the words match."""
 253 | +    DATADASH = {"ok": True, "model": "elevenlabs_stt:scribe_v1", "replayed": False,
 254 | +                "edges": {"in": {"ok": False, "word": "Bitcoin", "before": "line:", "pause_ms": 100,
 255 | +                                 "why": "the recogniser runs on into the clip ('line:', 100 ms before it)"},
 256 | +                          "out": {"ok": True, "word": "holdings.", "after": "The",
 257 | +                                  "why": "a sentence ends at the clip's last word"}, "cuttable": False}}
 258 | +
 259 | +    def test_soft_codes_and_the_second_family(self):
 260 | +        self.assertEqual(PK.soft_codes(["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"]), ["NOT_OWN_SINCERE", "REFERENT_OUTSIDE"])
 261 | +        for f in (["REFERENT_OUTSIDE", "STALE_TIME"], [PK.HELD + " x"], [], None, ["SPEAKER_CHANGE"], ["RETRACTION"]):
 262 | +            self.assertIsNone(PK.soft_codes(f), f)
 263 | +        cleared = {"a": {"moment_id": "a"}, "b": {"moment_id": "b"}, "c": {"moment_id": "c"}, "d": {"moment_id": "d"}}
 264 | +        got = PK.soft_second(cleared, {"a": [{}]}, {"b": ["REFERENT_OUTSIDE"], "c": ["STALE_TIME"], "d": [PK.HELD]})
 265 | +        self.assertEqual(got, {"b": ["REFERENT_OUTSIDE"]})
 266 | +        self.assertEqual((cleared["b"].get("step_a_flags"), "step_a_flags" in cleared["c"]), (["REFERENT_OUTSIDE"], False))
 267 | +
 268 | +    def test_only_a_sentence_running_on_at_a_word_boundary_is_soft(self):
 269 | +        import copy
 270 | +        self.assertEqual(PK.soft_edges(self.DATADASH), ["EDGE_IN"])
 271 | +        both = copy.deepcopy(self.DATADASH)
 272 | +        both["edges"]["out"] = {"ok": False, "word": "x", "after": "y", "why": "the recogniser's sentence continues past the clip"}
 273 | +        self.assertEqual(PK.soft_edges(both), ["EDGE_IN", "EDGE_OUT"])
 274 | +        for why_in in ("the recogniser has no 'bitc' within 0.6 s of the clip's start", "no word timing from the recogniser",
 275 | +                       "the window starts at the clip: no word before it",
 276 | +                       "the recogniser does not hear the trimmed word 'And' right before the clip (ruling 33 part 2)"):
 277 | +            t = copy.deepcopy(self.DATADASH)
 278 | +            t["edges"]["in"]["why"] = why_in
 279 | +            self.assertIsNone(PK.soft_edges(t), why_in)
 280 | +        end = copy.deepcopy(self.DATADASH)
 281 | +        end["edges"]["out"] = {"ok": False, "why": "the window ends at the clip: no word after it"}
 282 | +        self.assertIsNone(PK.soft_edges(end))
 283 | +        for bad in (dict(self.DATADASH, ok=False), dict(self.DATADASH, error="x"), dict(self.DATADASH, edges=None)):
 284 | +            self.assertIsNone(PK.soft_edges(bad))
 285 | +
 286 | +    def base(self, truth, a=None):
 287 | +        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 288 | +               "verdict": {"ok": True}, "backend": "b", "replayed": False, "measured": True}
 289 | +        ctx = {"ok": True, "violations": [], "backends": {"B": "b", "C": "b"}, "replayed": False, "measured": True}
 290 | +        return dict(fid=fid, dup=[], rt_ok=True, r4_res=(True, "ok"), ctx_=ctx, a_by={"clip_01": a or answer()},
 291 | +                    exc={"m": {"verdict": "keep", "backend": "b", "replayed": False, "measured": True}},
 292 | +                    truth={"m": truth}, coh_ok=True, coh={"backend": "b", "replayed": False, "measured": True})
 293 | +
 294 | +    def test_the_rows_flag_with_the_clip_named(self):
 295 | +        kw = dict(who={"clip_01": "DataDash"}, mids={"m": "clip_01"})
 296 | +        self.assertEqual(PK.inventory(**self.base(self.DATADASH), **kw)["cuttable"]["status"], "FAIL")   # clean pass
 297 | +        row = PK.inventory(**self.base(self.DATADASH), soft=True, **kw)["cuttable"]
 298 | +        self.assertEqual((row["status"], row["flags"]), ("FLAGGED", [
 299 | +            "The second clip (DataDash): the checker heard the sentence run on into the clip's first word, so it may "
 300 | +            "start mid-sentence."]))
 301 | +        hard = dict(self.DATADASH, edges=dict(self.DATADASH["edges"], **{"in": {"ok": False, "why": "no word timing from the recogniser"}}))
 302 | +        self.assertEqual(PK.inventory(**self.base(hard), soft=True, **kw)["cuttable"]["status"], "FAIL")
 303 | +        ok = dict(self.DATADASH, edges=dict(self.DATADASH["edges"], cuttable=True, **{"in": {"ok": True, "why": "ok"}}))
 304 | +        a = PK.inventory(**self.base(ok), soft=True, seg_flags={"clip_01": ["REFERENT_OUTSIDE"]}, **kw)["context_a"]
 305 | +        self.assertEqual((a["status"], a["flags"]), ("FLAGGED", [                     # the second family's doubt
 306 | +            "The second clip (DataDash): the checker thought it points back to something said before the clip starts."]))
 307 | +        stale = PK.inventory(**self.base(ok, answer(time_ok="no")), soft=True, seg_flags={"clip_01": ["REFERENT_OUTSIDE"]},
 308 | +                             **kw)["context_a"]
 309 | +        self.assertEqual(stale["status"], "FAIL")                                   # a hard code still fails
 310 | +
 311 | +    def test_the_pin_takes_a_flagged_sentence_edge_never_a_flagged_word_check(self):
 312 | +        pk = TestThePin().pk(cuttable={"status": "FLAGGED", "by": "x", "replayed": False, "n": 1, "flags": ["The second "
 313 | +                                       "clip (DataDash): the checker heard the sentence run on."]})
 314 | +        self.assertEqual(len(PP.to_pin(pk, "r")["moments_package"]["review_flags"]), 1)
 315 | +        with self.assertRaises(PP.PinRefused):
 316 | +            PP.to_pin(TestThePin().pk(second_pass={"status": "FLAGGED", "by": "x", "replayed": False, "n": 1,
 317 | +                                                   "flags": ["a word differs"]}), "r")
 318 | +
 319 | +
 320 |  class TestTheDayCount(unittest.TestCase):
 321 |      def test_counted_per_day_ledger(self):
 322 |          with tempfile.TemporaryDirectory() as d:
 323 | 
```

---

pp-selectid: RULINGS 136 / 137 / 138, STAGE 2a of the hard/soft switch (stage 1, never-empty for step A's first
screen, is LIVE: audit 20261117_1135). Approved design: HARD = the words the cut carries (L-v 2), a cut mid-word,
speaker credit, a factual or stale-time step-A refusal by BOTH families, exclusion, 12 h, never-reused, channel count,
runtime, spend; SOFT (flag, never refuse) = everything else; NEVER EMPTY seals the best line-up that passes every hard
gate with at most 3 flags, each one plain sentence naming the clip (ruling 138 (3)). Stage 1's step-A reading (ruling
138 (1)): SOFT = NOT_OWN_SINCERE, REFERENT_OUTSIDE, CONDITION_OUTSIDE, UNCERTAIN; HARD = STALE_TIME, SPEAKER_CHANGE,
RETRACTION (kept hard here even from one family). Files: pipeline/package.py, pipeline/package_pin.py,
tests/package/test_ruling_137.py. Today's evidence: build 131's soft pass lost DataDash 8dbc30ee at CUTTABLE (its words
match; the second recogniser runs on from 'line:' into its first word, 100 ms) and three moments at the SECOND step-A
screen for soft codes only.

THE CHANGE (only in the never-empty pass, soft=True; the clean pass is unchanged):
(a) soft_codes(f): a refusal's codes when all are soft and it is not held, else None; add_flags; soft_step_a (stage 1)
    now uses soft_codes. soft_second(cleared, a_two, off_fail): the moments the SECOND family refused for soft codes
    only stay, carrying the codes as "step_a_flags"; in _build they join cleared beside the moments it passed. The
    re-screen off the writer's family after the writes: a soft-only refusal keeps the clip, flagged, instead of
    dropping it (a hard code or no verdict still drops it, as before).
(b) CUTTABLE's sentence-edge part (line 1, 12:12 ET, default SOFT): soft_edges(t) returns the failing sides only when
    L-v 2's words match (ok True, no error, edges measured) and EVERY failing edge failed for exactly
    transcript_truth.edges' run-on reasons ("the recogniser runs on into the clip" / "the recogniser's sentence
    continues past the clip"); a word not found, a trimmed word, an unmeasured or window-edge edge stay HARD. Such
    moments stay in the soft pass (edge_flags). L-v 2's "second_pass" row stays HARD.
(c) inventory: context_a's codes are each clip's verdict codes plus every screen's soft codes (seg_flags), FLAGGED only
    when all are soft; "cuttable" is FLAGGED with one sentence per failing edge when every non-cuttable segment's
    failure is soft; both name the clip (who, mids: truth is keyed by moment id). package_pin.SOFT_GATES adds
    "cuttable" ("second_pass" never).
(d) the wrapper keeps the soft pass's own record (never_empty.soft_record: prescreen, hook_pool, tried).

TESTS (test_ruling_137: 11): soft_codes and the second family; only the run-on reasons are soft (DataDash 8dbc30ee's real
record), every other edge reason and a failed word check stay hard; both rows flag with the clip named, a hard code
still fails; the pin takes a FLAGGED cuttable, never a FLAGGED second_pass; the soft record. Mutations: 23 of 23
effective ones killed. NOT UNIT-TESTED, PLEASE READ: the three call sites inside _build (the second screen's
cleared filter, the re-screen's new branch, the cut_soft filter): they only call the tested helpers.

PLEASE CHECK: (1) that nothing HARD can pass: a hard code, a held moment, no verdict, a word mismatch, any non-run-on
edge failure, a FLAGGED word check; (2) that the clean pass is unchanged; (3) the three _build call sites; (4) that
every flag names its clip in one sentence; (5) the tests.


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
