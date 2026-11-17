# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1351
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 204 s finish=stop usage in 12911 / out 4203 usd_reported=0.000921 usd~0.102 (upper-bound price)

The code implements RULING 141 (2), transitioning the `STAND_ALONE` gate to a "SOFT" failure mode during the "never-empty" pass of the medley builder.

### Analysis

**1. Logic for "Soft" Recovery (`_build`)**
In `pipeline/package.py`, the `_build` function now identifies moments that were rejected solely by the `STAND_ALONE` opener rule. 
- It checks `no_topic(m) is None` and ensures no affirmed trim variant exists.
- These moments are added back to the pool via `stand_back` and marked with `m["stand_soft"]`.
- The `m.pop("stand_soft", None)` at the start of `_build` correctly prevents marks from leaking between passes.
- The hook is protected: `_can_open` (referenced in the prompt) and the `stand_soft_rows` logic ensure the hook remains a HARD gate.

**2. Gate Adjudication (`stand_soft_rows` & `stand_ok`)**
The `stand_soft_rows` function is the core validator. It correctly implements the "fail-closed" requirement for hard failures:
- **Hard Failures (Return `None`):** If the hook fails, if any clip is unmarked (`not m.get("stand_soft")`), if the topic rule fails, or if the medley fails to name Bitcoin.
- **Soft Failures (Added to `out`):** If a clip is marked, is not the hook, passes the topic rule, but fails the opener rule.
- **Passes:** Rows that pass are skipped via `continue`.
This ensures that a medley is only "SOFT" if *every* failure in the `STAND_ALONE` check is a marked opener failure.

**3. Integration and Line-up**
- `lineup_ok` and `lineup_for` now use `stand_ok`, which allows medleys containing only soft failures to proceed.
- `inventory` correctly applies the `FLAGGED` status and the exact required prefix: `"The clip ({channel}) may not stand alone: "`.
- `package_pin.py` correctly adds `"stand_alone"` to `SOFT_GATES`, allowing the pin stage to accept these flags.

**4. Test Coverage**
The new tests in `test_ruling_137.py` are comprehensive:
- `test_the_reason_in_plain_words` verifies the regex mapping of internal reasons to plain English.
- `test_only_marked_clips_failing_only_the_opener_are_soft` rigorously tests the hard-failure boundaries (hook, topic, unmarked, Bitcoin).
- The end-to-end `Rig` test confirms that the clean pass rejects the medley while the never-empty pass seals it as `FLAGGED`.

### Findings

No violations of the Governing Laws or the specific RULING 141 (2) requirements were found. The implementation is precise, maintains the integrity of the clean pass, and adheres to the required string formats for the integrator.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 315 s finish=stop usage in 12181 / out 12301 usd_reported=0.011081 usd~0.221 (upper-bound price)



# Code Audit — pp-selectid / RULING 141 (2): STAND_ALONE SOFT

## Scope

Reviewed the 271-line diff across `pipeline/package.py`, `pipeline/package_pin.py`, and `tests/package/test_ruling_137.py` implementing RULING 141 (2): in the never-empty (soft) pass, a moment left out *only* by the render's STAND_ALONE opener rule is admitted back as a clip, flagged with the exact prefix the integrator matches. The topic rule (ruling 34), the hook row, the medley-names-Bitcoin check, and unmarked clips remain hard.

---

## Findings

### [P2] `stand_plain` regex fallback silently degrades the flag text

**Location:** `package.py` lines 22–30 (`stand_plain`)

The two `re.match` calls parse the human-readable string returned by `SA.opener("clip", …)`. If the upstream format ever shifts (a reworded conjunction, an added clause, a different fault label), *both* regexes miss and the function falls through to `return why` — the raw `SA.opener` string. The flag is still well-formed (the prefix is prepended by `inventory`), so the integrator's prefix match still works and no gate is bypassed. However, the plain-language reason the reviewer sees in the pin record would be the internal `SA.opener` phrasing rather than the intended "it opens on 'but' and the clip scorer has no verdict for it" sentence, and the test `test_the_reason_in_plain_words` would not catch the regression because it tests the happy path.

**Suggestion:** Add a `test_the_reason_falls_back_to_raw_when_format_shifts` case that monkey-patches `SA.opener` to return an unexpected string and asserts `stand_plain` returns it verbatim (documenting the fallback contract). Alternatively, raise/log a warning when neither regex matches so a format drift is visible in the build log.

---

### [P2] No end-to-end test for `soft=True` with a *hard* stand_alone failure in the pin row

**Location:** `tests/package/test_ruling_137.py`, `TestRuling141StandAloneSoft`

`test_the_row_flags_only_in_the_soft_pass` covers `soft=True` *with* soft rows (→ FLAGGED) and `soft=False` (→ FAIL). The end-to-end rig test covers the topic-rule moment "w" staying in `no_role`, but there is no test that drives the *pin inventory* with `soft=True` and a stand_alone check that fails on a **hard** condition (e.g. the hook row fails, or the medley doesn't name Bitcoin) and asserts the row status is `"FAIL"` (not `"FLAGGED"`) and that `gate_problems` is **non-empty** (i.e. the seal is blocked).

This matters because `"stand_alone"` is now in `SOFT_GATES`. The safety net is that `stand_with_soft` omits `soft_rows` when `stand_soft_rows` returns `None`, so the inventory's `if soft and stand.get("soft_rows")` guard prevents the FLAGGED status. But that guard is the *only* thing keeping a hard failure from being silently downgraded to a flag by the pin's soft-gate handling. A regression in `stand_with_soft` (e.g. always emitting `soft_rows={}`) would turn a hard FAIL into a FLAGGED with an empty flag list, and no existing test would catch it.

**Suggestion:** Add a test that calls `PK.inventory(…, stand=stand_with_soft(segs_with_hook_failure), soft=True, …)` and asserts `status == "FAIL"` and that the gate is a problem.

---

### [P2] `stand_soft_rows` couples segment order to `labels()` positionally

**Location:** `package.py` line 41

```python
by, out = dict(zip(labels(len(segs)), segs)), {}
```

The mapping from label → segment is purely positional: `segs[0]` is "hook", `segs[1]` is "clip_01", etc. This is correct today because `stand_alone_check` and the lineup builder always produce segments in that order. But the function's contract is "given a check result and the segments it checked, find the soft rows." If a future caller passes segments in a different order (or a subset), the mapping silently misaligns and a moment's `stand_soft` mark could be attributed to the wrong label, causing either a false soft (a hard failure treated as soft) or a false hard (a soft failure treated as hard).

**Suggestion:** Either (a) document the positional invariant in the docstring with an explicit `# INVARIANT: segs must be in label order`, or (b) build the map from each segment's own identity if one is available (e.g. `m.get("label")`), making the function order-independent.

---

### [P3] Double period when `SA.opener`'s raw string ends with "."

**Location:** `package.py` line 156 (inventory)

```python
STAND_SOFT_PREFIX.format(channel=…) + f"{why}."
```

If the fallback path in `stand_plain` returns a raw `why` that already ends with a period, the flag reads `"…may not stand alone: some reason.."`. Cosmetic only; the integrator matches the prefix, not the tail.

---

### [P3] `stand_back` dict-comprehension is dense

**Location:** `package.py` lines 101–102

```python
stand_back = {m["moment_id"]: p for m in ms if soft and m["moment_id"] in no_role and m["moment_id"] not in trim

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1351, ruling 141 (2): STAND_ALONE soft, the builder's half)

SEATS ANSWERED: 2 of 3. qwen3.8-27b: P0/P1 none (three P2s, two P3s). gemma-4-31b-it: P0/P1 none. gpt-oss-20b: its
32,000-token cap ran out with no answer.

## qwen's findings
- [P2] stand_plain's fallback to the raw reason "silently degrades" the flag: BY DESIGN, DECLINED. The two patterns
  are stand_alone.opener's own clip wordings (stand_alone.py:98 and :101); any other wording is shown as the render
  gives it. That is still the render's reason in the sentence, never an empty or wrong flag.
- [P2] no end-to-end case of a soft pass whose pin row has a HARD failure: COVERED below the end-to-end level. Every
  hard case of stand_soft_rows has a unit test: the hook's row (marked or not), a topic row, an unmarked clip, the
  medley not naming Bitcoin or that record missing. lineup_ok refuses an unmarked conjunction clip. The end-to-end
  pool's topic-refused moment w stays out. Mutations S6-S9 are killed.
- [P2] stand_soft_rows maps rows to segments by labels() position: BY DESIGN. stand_alone_check builds its EDL from the
  same segs in the same order (the hook, then clip_01...: package.py:1221-1248), and check_edl labels its rows so
  (stand_alone.py:186).
- [P3] a double period if a raw reason ends with ".": none of opener's clip wordings does. DECLINED.
- [P3] the dense comprehension: DECLINED (cosmetic).

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1351/C2_STEP.diff (271 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 68e6942..7f0bbe1 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1569,6 +1569,64 @@ def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name, ex
   6 |      return {"index": index, "record": rec}
   7 |  
   8 |  
   9 | +STAND_SOFT_PREFIX = "The clip ({channel}) may not stand alone: "   # RULING 141 (2): the integrator's render matches
  10 | +#   this prefix exactly (it then skips its own flag for that channel's clip)
  11 | +
  12 | +
  13 | +def stand_plain(m):
  14 | +    """RULING 141 (2): the render's STAND_ALONE opener refusal of moment m as a CLIP, in plain words (the clip scorer's
  15 | +    reason), e.g. "it opens on 'but' and the clip scorer has no verdict for it"; None when the clip role passes."""
  16 | +    import stand_alone as SA
  17 | +    v = verdict_of(m)
  18 | +    ok, why = SA.opener("clip", m.get("text") or "", v["score"] if v else None, v["fault"] if v else None,
  19 | +                        moments=True)
  20 | +    if ok:
  21 | +        return None
  22 | +    x = re.match(r"clip opens on (.+?) and no clip-scorer verdict is available", why)
  23 | +    if x:
  24 | +        return f"it opens on {x.group(1)} and the clip scorer has no verdict for it"
  25 | +    x = re.match(r"clip opens on (.+?); the clip scorer does not affirm it stands alone \(([^,]+), fault (.+)\)$", why)
  26 | +    if x:
  27 | +        f = x.group(3).replace("_", " ")
  28 | +        return f"it opens on {x.group(1)} and the clip scorer rated it {x.group(2)} of 5" + \
  29 | +            (f" ({f})" if f not in ("None", "none", "") else "")
  30 | +    return why
  31 | +
  32 | +
  33 | +def stand_soft_rows(stand, segs):
  34 | +    """RULING 141 (2) (STAND_ALONE soft in the never-empty pass): {label: plain reason} for the CLIP rows of a check_edl
  35 | +    result `stand` (stand_alone_check(segs)) that fail ONLY its opener rule, each on a moment that pass brought back
  36 | +    (its "stand_soft" mark); None when the check passes or any other failure stands: the hook's row, any topic row
  37 | +    (ruling 34), the medley not naming Bitcoin, a failing row of an unmarked clip (these stay HARD)."""
  38 | +    if not isinstance(stand, dict) or stand.get("ok") is True or \
  39 | +            (stand.get("medley_names_bitcoin") or {}).get("pass") is not True:
  40 | +        return None
  41 | +    by, out = dict(zip(labels(len(segs)), segs)), {}
  42 | +    for r in stand.get("rows") or []:
  43 | +        if r.get("pass") is True:
  44 | +            continue
  45 | +        m = by.get(r.get("segment"))
  46 | +        if r.get("segment") == "hook" or m is None or not m.get("stand_soft") or \
  47 | +                (r.get("topic") or {}).get("pass") is not True or (r.get("opener") or {}).get("pass") is not False:
  48 | +            return None
  49 | +        out[r["segment"]] = m["stand_soft"]
  50 | +    return out or None
  51 | +
  52 | +
  53 | +def stand_ok(segs):
  54 | +    """The render's STAND_ALONE on a line-up for the line-up rules (lineup_ok, lineup_for): it passes, or RULING 141 (2),
  55 | +    its only failures are clips the never-empty pass brought back failing only the opener rule (stand_soft_rows)."""
  56 | +    st = stand_alone_check(segs)
  57 | +    return st["ok"] is True or bool(stand_soft_rows(st, segs))
  58 | +
  59 | +
  60 | +def stand_with_soft(segs):
  61 | +    """The pin stage's STAND_ALONE (stand_alone_check) with RULING 141 (2)'s soft rows when there are any."""
  62 | +    st = stand_alone_check(segs)
  63 | +    sr = stand_soft_rows(st, segs)
  64 | +    return dict(st, soft_rows=sr) if sr else st
  65 | +
  66 | +
  67 |  def no_topic(m):
  68 |      """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
  69 |      fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
  70 | @@ -1800,7 +1858,7 @@ def lineup_ok(segs, crange=None, repeat_ok=False):
  71 |      dur = sum(m["duration_s"] for m in segs)
  72 |      if not lo <= dur <= hi:
  73 |          return False, f"{dur:.1f} s outside {lo}-{hi} s"
  74 | -    if not stand_alone_check(segs)["ok"]:
  75 | +    if not stand_ok(segs):                                   # RULING 141 (2): only marked clips' openers flag
  76 |          return False, "the render's STAND_ALONE"
  77 |      return True, "ok"
  78 |  
  79 | @@ -1937,7 +1995,7 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  80 |                      continue
  81 |                  if accept is not None and not accept([h] + order):       # the caller's own condition (pool_fill)
  82 |                      continue
  83 | -                if need_stand_alone and not stand_alone_check([h] + order)["ok"]:
  84 | +                if need_stand_alone and not stand_ok([h] + order):     # RULING 141 (2): marked clips flag
  85 |                      continue
  86 |                  key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
  87 |                  if now is not None:                       # ruling 57: a fresh clip first, then the newest clips,
  88 | @@ -3198,6 +3256,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  89 |      scorer = scorer_pass(ms, sources, ctx, scorer_verdicts_path, scorer_candidates_path, build_name,   # ruling 56
  90 |                           extra=scorer_extra)                                                       # ruling 90
  91 |      ms = [with_verdict(m, scorer["index"]) for m in ms]
  92 | +    for m in ms:                                       # RULING 141 (2)'s soft mark is this pass's own, never carried in
  93 | +        m.pop("stand_soft", None)
  94 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
  95 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
  96 |      admitted = sorted(m["moment_id"] for m in ms if verdict_of(m) and m["moment_id"] not in no_role)   # ruling 56
  97 | @@ -3206,6 +3266,16 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  98 |               for v in [trim_variant(m, sources)] if v}                      # joins the pool (the original stays a clip)
  99 |      trim_out = {k: why for k, v in trims.items() for why in [trim_refused(v)] if why}   # ruling 56: never sealed
 100 |      trims = {k: v for k, v in trims.items() if k not in trim_out}
 101 | +    stand_back = {m["moment_id"]: p for m in ms if soft and m["moment_id"] in no_role and m["moment_id"] not in trims
 102 | +                  and no_topic(m) is None for p in [stand_plain(m)] if p}   # RULING 141 (2): STAND_ALONE SOFT in the
 103 | +    for m in ms:                                                            # never-empty pass: a moment left out ONLY
 104 | +        if m["moment_id"] in stand_back:                                    # by the opener rule (no topic refusal, no
 105 | +            m["stand_soft"] = stand_back[m["moment_id"]]                    # affirmed trim) comes back as a clip,
 106 | +    if stand_back:                                                          # flagged; it never opens (the hook rule)
 107 | +        log(f"  RULING 141 NEVER EMPTY (STAND_ALONE soft): {len(stand_back)} moment(s) left out only by the render's "
 108 | +            f"STAND_ALONE opener rule come back as clips, flagged: " +
 109 | +            ", ".join(f"{mid[:8]} ({p})" for mid, p in stand_back.items()))
 110 | +    no_role = {k: v for k, v in no_role.items() if k not in stand_back}
 111 |      ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42);
 112 |      #   a variant of a moment that keeps its own place (ruling 94 a) sits beside it: one line-up never takes both (one
 113 |      #   video at most once, L-y 4)
 114 | @@ -3248,6 +3318,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 115 |      cleared, back = cleared_pool(ms, a_by, fails, soft)  # RULING 137 stage 1: the never-empty pass adds back, flagged
 116 |      levels = current_levels(sources.values(), ctx)
 117 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 118 | +           **({"soft_stand": stand_back} if stand_back else {}),          # RULING 141 (2): back, flagged
 119 |             "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
 120 |             "reposted": reposted,
 121 |             "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
 122 | @@ -3717,7 +3788,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 123 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 124 |                                  shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 125 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 126 | -                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 127 | +                                stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 128 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 129 |                                  last_resort=pin_last_resort(pk), soft=soft,   # RULING 102; RULING 137 stage 1
 130 |                                  who={sg["label"]: sg.get("channel") for sg in pk["segments"]},   # RULING 138 (3)
 131 | @@ -4206,7 +4277,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 132 |                                              ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 133 |                                              style=HS.lint_lines(pk["lines"]),
 134 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 135 | -                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 136 | +                                            stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 137 |                                              visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 138 |                                              value=val,                       # ruling 91: the takeaway earned its place
 139 |                                              last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 140 | @@ -4327,7 +4398,7 @@ def build(*args, never_empty=False, flagged_today=0, **kw):
 141 |      soft = _build(*args, soft=True, **kw)
 142 |      info = {"stage": "2b", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 143 |              "soft_back": (soft.get("prescreen") or {}).get("soft_back"),
 144 | -            "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried")}}   # the pass's own record
 145 | +            "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried", "soft_stand")}}   # its record
 146 |      return dict(soft, never_empty=info) if soft.get("package") else dict(out, never_empty=info)
 147 |  
 148 |  
 149 | @@ -4438,7 +4509,10 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 150 |                                      "affirming one a conjunction, reply-fragment or trimmed opener fails closed)"),
 151 |                                  rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 152 |                                        f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 153 | -                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 154 | +                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"),
 155 | +                                **({"status": "FLAGGED", "flags": [           # RULING 141 (2): one plain sentence a clip
 156 | +                                    STAND_SOFT_PREFIX.format(channel=(who or {}).get(lb) or "its channel") + f"{why}."
 157 | +                                    for lb, why in stand["soft_rows"].items()]} if soft and stand.get("soft_rows") else {}))}
 158 |             if stand is not None else {}),
 159 |          **({"visual": dict(row(bool(visual) and all((v or {}).get("measured") is True for v in visual),
 160 |                                 sorted({str((v or {}).get("backend")) for v in visual}) or None,
 161 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 162 | index 1fb3855..727abc7 100644
 163 | --- a/pipeline/package_pin.py
 164 | +++ b/pipeline/package_pin.py
 165 | @@ -37,8 +37,10 @@ MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"
 166 |  SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's soft codes
 167 |                          "cuttable",                        # stage 2a: a sentence edge at a word boundary (L-v 2's
 168 |                          #   word check, "second_pass", stays HARD)
 169 | -                        "medley"})                         # stage 2b: the hook under the calibrated bar (its own
 170 | -#   rater's rating; no calibration or another rater stays HARD)
 171 | +                        "medley",                          # stage 2b: the hook under the calibrated bar (its own
 172 | +                        #   rater's rating; no calibration or another rater stays HARD)
 173 | +                        "stand_alone"})                    # RULING 141 (2): a clip's STAND_ALONE opener (the topic
 174 | +#   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 175 |  REVIEW_FLAGS_MAX = 3
 176 |  
 177 |  
 178 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 179 | index f61260a..fe400ca 100644
 180 | --- a/tests/package/test_ruling_137.py
 181 | +++ b/tests/package/test_ruling_137.py
 182 | @@ -290,6 +290,88 @@ class TestStage2bHookBar(unittest.TestCase):
 183 |          self.assertEqual(PK.HOOK_SOFT_MAX, 2)
 184 |  
 185 |  
 186 | +class TestRuling141StandAloneSoft(unittest.TestCase):
 187 | +    """RULING 141 (2): STAND_ALONE SOFT in the never-empty pass (the builder's half; the integrator's render already only
 188 | +    flags an opener refusal and holds on the topic rule and the medley naming Bitcoin). A moment left out ONLY by the
 189 | +    render's STAND_ALONE opener rule comes back as a clip, flagged "The clip (<channel>) may not stand alone: <reason>."
 190 | +    (the integrator matches that prefix); it never opens; the topic rule, the hook's row, an unmarked clip and the medley
 191 | +    naming Bitcoin stay hard."""
 192 | +
 193 | +    def m(self, text, verdict=None):
 194 | +        x = {"moment_id": "q", "text": text}
 195 | +        return dict(x, scorer_verdict=dict(verdict, text_sha256=PK.text_sha(text))) if verdict else x
 196 | +
 197 | +    def test_the_reason_in_plain_words(self):
 198 | +        self.assertEqual(PK.stand_plain(self.m("But Bitcoin q x.")),
 199 | +                         "it opens on 'but' and the clip scorer has no verdict for it")
 200 | +        self.assertEqual(PK.stand_plain(self.m("And Bitcoin q x.", {"score": 2.0, "fault": "starts_mid_thought",
 201 | +                                                                     "reason": "r"})),
 202 | +                         "it opens on 'and' and the clip scorer rated it 2.0 of 5 (starts mid thought)")
 203 | +        self.assertIsNone(PK.stand_plain(self.m("Bitcoin q x.")))
 204 | +        self.assertTrue(PK.STAND_SOFT_PREFIX.format(channel="X").startswith("The clip (X) may not stand alone: "))
 205 | +
 206 | +    def test_only_marked_clips_failing_only_the_opener_are_soft(self):
 207 | +        segs = [{"moment_id": "h", "stand_soft": "why h"}, {"moment_id": "a", "stand_soft": "why a"},
 208 | +                {"moment_id": "b"}]                                     # a mark on the hook never softens its row
 209 | +        row = lambda seg, o, t=True: {"segment": seg, "pass": o and t, "opener": {"pass": o}, "topic": {"pass": t}}
 210 | +        st = {"ok": False, "rows": [row("hook", True), row("clip_01", False), row("clip_02", True)],
 211 | +              "medley_names_bitcoin": {"pass": True}}
 212 | +        self.assertEqual(PK.stand_soft_rows(st, segs), {"clip_01": "why a"})
 213 | +        for bad in ([row("hook", False), row("clip_01", False), row("clip_02", True)],      # the hook's own row
 214 | +                    [row("hook", True), row("clip_01", False, False), row("clip_02", True)],   # its topic too
 215 | +                    [row("hook", True), row("clip_01", False), row("clip_02", False)]):     # an unmarked clip
 216 | +            self.assertIsNone(PK.stand_soft_rows(dict(st, rows=bad), segs), bad)
 217 | +        self.assertIsNone(PK.stand_soft_rows(dict(st, medley_names_bitcoin={"pass": False}), segs))
 218 | +        self.assertIsNone(PK.stand_soft_rows(dict(st, medley_names_bitcoin=None), segs))   # unmeasured: hard
 219 | +        self.assertIsNone(PK.stand_soft_rows(dict(st, ok=True), segs))
 220 | +
 221 | +    def rig(self, never_empty, carry=False):
 222 | +        import test_medley as TM
 223 | +        from test_moments import pm
 224 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), dict(pm("z", "C", 13.0), text="But Bitcoin z x."),
 225 | +              dict(pm("w", "D", 13.0), text="But nothing here at all.")]   # w: the topic rule (ruling 34) too
 226 | +        ms = [dict(m, stand_soft="carried in") for m in ms] if carry else ms
 227 | +        r = TM.Rig(ms, ["h", "x", "z"], [(True, [], None, TM.Rig.LINE)], [None])
 228 | +        r.build_kw = {"never_empty": never_empty}
 229 | +        return r.run()
 230 | +
 231 | +    def test_a_clip_left_out_only_by_the_opener_rule_seals_flagged_only_in_the_never_empty_pass(self):
 232 | +        clean = self.rig(False)
 233 | +        self.assertIsNone(clean["package"])
 234 | +        self.assertIn("z", clean["no_role"])                        # the clean pass: 2 channels, no paid verdict
 235 | +        out = self.rig(True)
 236 | +        pk = out["package"]
 237 | +        segs = {s["moment_id"]: s for s in pk["segments"]}
 238 | +        self.assertEqual((set(segs), pk["segments"][0]["moment_id"]), ({"h", "x", "z"}, "h"))   # never the hook
 239 | +        want = [f"The clip ({segs['z']['channel']}) may not stand alone: it opens on 'but' and the clip scorer has no "
 240 | +                f"verdict for it."]
 241 | +        self.assertEqual((pk["gates"]["stand_alone"]["status"], pk["gates"]["stand_alone"]["flags"]), ("FLAGGED", want))
 242 | +        self.assertEqual(PP.review_flags_of(pk["gates"]), want)
 243 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])   # the seal's own check takes it
 244 | +        self.assertEqual(out["soft_stand"], {"z": "it opens on 'but' and the clip scorer has no verdict for it"})
 245 | +        self.assertIn("w", out["no_role"])                              # the topic rule stays HARD: never back
 246 | +
 247 | +    def test_a_mark_carried_in_is_never_read(self):
 248 | +        self.assertIsNone(self.rig(False, carry=True)["package"])
 249 | +
 250 | +    def test_the_line_up_rules_take_a_marked_clip_and_refuse_an_unmarked_one(self):
 251 | +        from test_moments import pm
 252 | +        h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})
 253 | +        z = dict(pm("z", "C", 13.0), text="But Bitcoin z x.")
 254 | +        segs = [h, pm("x", "B", 14.0), z]
 255 | +        self.assertEqual(PK.lineup_ok(segs), (False, "the render's STAND_ALONE"))
 256 | +        self.assertEqual(PK.lineup_ok([h, segs[1], dict(z, stand_soft="it opens on 'but'")]), (True, "ok"))
 257 | +
 258 | +    def test_the_row_flags_only_in_the_soft_pass(self):
 259 | +        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
 260 | +        st = {"ok": False, "rows": [], "medley_names_bitcoin": {"pass": True}, "soft_rows": {"clip_02": "why z"}}
 261 | +        row = lambda soft: PK.inventory(**TestStage2a().base(t), stand=st, soft=soft, who={"clip_02": "Yahoo Finance"})[
 262 | +            "stand_alone"]
 263 | +        self.assertEqual((row(True)["status"], row(True)["flags"]), (
 264 | +            "FLAGGED", ["The clip (Yahoo Finance) may not stand alone: why z."]))
 265 | +        self.assertEqual((row(False)["status"], "flags" in row(False)), ("FAIL", False))
 266 | +
 267 | +
 268 |  class TestTheDayCount(unittest.TestCase):
 269 |      def test_counted_per_day_ledger(self):
 270 |          with tempfile.TemporaryDirectory() as d:
 271 | 
```

---

pp-selectid: RULING 141 (2) (orchestrator 13:40 ET Nov 17): STAND_ALONE becomes SOFT, the first item of stage 2b; the
builder's half. Context: the never-empty pass (package.build runs _build(soft=True) only when the clean pass sealed
nothing) flags soft gates in one plain sentence each; at most 3 flags seal (package_pin.REVIEW_FLAGS_MAX). STAND_ALONE
left out 77 of 110 usable moments today. The integrator's side needs no change: since its batch 105 (11:51 ET) its
render's validate re-asks every opener and only FLAGS an unaffirmed / unrated / conjunction opener; it HOLDS only on the
topic rule (ruling 34), the medley naming Bitcoin, and a malformed ruling-119 floor mark. Its next batch skips its own
flag for a channel whose pin already carries "The clip (<channel>) may not stand alone:", so that prefix must be exact.
Files: pipeline/package.py, pipeline/package_pin.py, tests/package/test_ruling_137.py.

THE CHANGE (never-empty pass only; the clean pass is unchanged):
(a) _build: no_role (package.py:3261: no_role_on_screen :1640, the opener rule; no_topic :1630, the topic rule) still
    leaves out what it did. In the soft pass, a moment left out ONLY by the opener rule (no_topic None) and with no
    affirmed trim variant (trims, :3264, the clean path, kept first) comes back (stand_back, :3269), carrying its plain
    reason as the mark "stand_soft" (stand_plain :1576: "it opens on 'but' and the clip scorer has no verdict for it" /
    "... rated it 2.0 of 5 (starts mid thought)"). The mark is popped after with_verdict, so it never carries in. It
    never opens: the hook role still needs SA.opener("hook") in _can_open (:1809), which every conjunction fails.
(b) stand_soft_rows(stand, segs) (:1596): the clip rows of check_edl (stand_alone.py:176-222: one row a segment, the
    opener and topic results, plus medley_names_bitcoin) that fail ONLY the opener, each on a marked moment. None if
    the check passes, the hook's row fails (even marked), any topic row fails, an unmarked clip's row fails, or the
    medley does not name Bitcoin (also when that record is missing).
(c) stand_ok(segs) (:1616) = the check passes, or only (b)'s rows fail. It replaces the bare check in lineup_ok (:1861)
    and in lineup_for's picker (:1998). stand_with_soft (:1623) adds the soft rows to the pin stage's check at both
    inventory call sites.
(d) inventory: the "stand_alone" row is FLAGGED with "The clip (<channel>) may not stand alone: <reason>." for each soft
    row (STAND_SOFT_PREFIX :1572, the integrator's exact prefix), only when soft. package_pin.SOFT_GATES adds
    "stand_alone". The record keeps out["soft_stand"].

TESTS (test_ruling_137, 7 new): the plain reason; (b)'s every hard case; END TO END through test_medley's Rig: a 3-moment
pool whose third channel opens on "But": the clean pass leaves it out and stops at 2 channels; the never-empty pass seals
with the stand_alone row FLAGGED in the exact sentence, review_flags_of equal to it, gate_problems() empty, the hook not
the flagged clip; a moment failing the topic rule too stays out. lineup_ok takes a marked clip and refuses an unmarked
one. The row flags only in the soft pass. Mutations: 11 of 14 killed. Survivors: S13 (the pop of a carried mark) and
S14 (the explicit opener check) are equivalent today; S3, preferring an affirmed trim, is NOT UNIT-TESTED: please read
:3269's "not in trims".

PLEASE CHECK: (1) can anything the topic rule, the medley-names-Bitcoin rule or the hook rule refuses get through? (2) the
clean pass unchanged; (3) lineup_ok / lineup_for / the pin row agree; (4) the exact prefix; (5) the tests.


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
