# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2049
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 182 s finish=stop usage in 13081 / out 5452 usd_reported=0.001082 usd~0.121 (upper-bound price)

# Audit: pp-selectid, RULING 105 builder side (lock_precheck / package_pin)

Scope: the 369-line diff only. I traced `ruling_105_fails` against the ruling's three tests, the decide/apply flow, the seal path, and the test coverage. Findings, worst first.

---

## [P1] (1) `_truncation` rejects a comma-formatted token the integrator rightly passes

The ruling's example is `'401' of '401k'` — "a prefix of the same term". The integrator's field shape carries the token as the lock wrote it; the ruling's own must-fail list speaks of `'68,000' / '86,000'` with commas, so the record's token may legitimately be a formatted number. `_truncation`:

```python
return (isinstance(r, str) and bool(r) and r != token and token.startswith(r) and any(ch.isdigit() for ch in r)
        and not any(ch.isdigit() for ch in token[len(r):]))
```

requires `token.startswith(r)` — a **strict character-prefix**. If the lock's token is `401k` but the second recogniser writes the same spoken term as `401,000` or `401K` (case), the ruling-105 pass is turned into a hold. Same for `'$40,000'` vs `'$40'`-style readings. The ruling says "a prefix of the same term", not "a character-prefix of the raw token string"; the builder's own test `test_a_dropped_token_or_a_digit_cut_off_is_no_truncation` even asserts `("4015", ("401", "4015"))` is a hold because "a digit cut off: another number" — correct — but nothing in the ruling says `401K`/`401,000` must hold, and the ruling's own must-fail list uses comma forms, implying the record may carry them.

**Fix:** compare canonically (law L-k: every text comparison in the pipeline uses `pipeline/canonical.py`... `canon.py`), e.g. strip separators/case before the prefix test, or document that the record's tokens are the lock's raw spelling and enforce that in the record's own tests. As written, a legitimately-passing record can be refused — a real defect, but not a wrong result (it fails closed, so P1, not P0).

Note the ruling's own must-fail case `'68,000' / '86,000'` — the test uses `86000`/`68000` without commas, so the comma path is untested. That's part of the same finding.

---

## [P1] (1) `ruling_105_fails` never checks that the second readings' `token` fields are strings at all — a non-string reading passes the (2)/(3) checks silently in one path

Look at the flow for `st`:

```python
st = [x.get("token") if isinstance(x, dict) else None for x in sec]
if len(set(st)) >= 2 and tok in st:   # (2)
```

Wait — actually the code is:

```python
if len(set(st)) < 2 or tok not in st:
    return f"(2) ..."
```

`set(st)` with `None` entries: if `sec = [{"token": "401"}, "notadict", {"token": "401k"}]` → `st = ["401", None, "401k"]`. Then (2) passes (`len(set) >= 2`, `tok in st`), and (3): `odd = [x for x in st if x != tok and not _truncation(x, tok)]` — `_truncation(None, "401k")` returns False (isinstance check), so `None` lands in `odd` → hold. Good, that path fails closed. **But** consider `sec = [{"token": "401"}, {"token": "401k"}, {"token": "401k"}]` where one element is `{"token": 401}` (an int). `st = ["401", 401, "401k"]` — `401 != "401k"`, `_truncation(401, "401k")` → `isinstance(401, str)` False → hold. Fails closed. So the only gap: `st` containing `None` from a **non-dict** element where the *other* readings satisfy (2) and (3) — no, that also lands in `odd`. Actually the real gap: **`dec` (decoder readings) elements that are not dicts**. `dt = [x.get("token") if isinstance(x, dec) else None ...]` — if a decoder reading is a bare string `"401k"` instead of `{"token": "401k"}`, `dt` gets `None`, (1) fails → hold. Fails closed. So: no P0 here; the non-string paths all fail closed. Downgrade: this is a **P2** — the error messages will say `(1) the decoder is not stable: [None, ...]` which is misleading (the readings were present, just malformed), and the record's own `tests` dict is trusted for `decoder_stable` etc. without the readings being validated to the field shape. The ruling's field shape says each reading is `{"at", "source", "token"}`; the builder's check never validates `at`/`source` presence or that `token` is a str. A record with `{"token": 401}` (int) that the integrator seals as pass will be held by this side — defence in depth, but the ruling says the *shape* is agreed; not validating it means the "this side's own check" can disagree with the integrator on shape, not substance. Should fix: validate the agreed field shape, or explicitly document that only `token` is read.

---

## [P1] (1) The `tests` re-check trusts the record's own booleans without recomputing them from the readings

`ruling_105_fails` ends:

```python
tests = u.get("tests")
if not (isinstance(tests, dict) and all(tests.get(k) is True for k in
                                        ("decoder_stable", "second_unstable", "truncations_only"))):
    return f"the record's own tests 

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 77 s finish=stop usage in 14767 / out 2610 usd_reported=0.003900 usd~0.083 (upper-bound price)

I have reviewed the diff for `pp-selectid` (RULING 105 implementation). Below are my findings based on the Governing Laws and the specific code changes.

### Findings

**1. [P1] `ruling_105_fails` fails closed on valid numeric tokens with formatting (e.g., commas)**
The function `ruling_105_fails` (lines 65-94 in `pipeline/lock_precheck.py`) enforces strict string matching for the "truncation" logic.
- **The Issue:** The check `token.startswith(r)` and the definition of `_truncation` (lines 57-62) operate on raw strings. If the lock's token is a formatted number like `"86,000"` and the second recogniser reads it as `"86,00"` (a truncation of the visual string) or `"86000"` (a different format), the logic may behave unexpectedly or fail closed.
    - Specifically, if `token` is `"86,000"` and `r` is `"86,00"`, `token.startswith(r)` is True. `_truncation` checks if the suffix `token[len(r):]` contains digits. The suffix is `"00"`, which contains digits. So `_truncation` returns `False` (it is NOT a valid truncation because the dropped part has digits). This is correct for "86,00" vs "86,000" (dropping a digit).
    - However, consider the case where the token is `"1,000"` and the reading is `"1000"`. `token.startswith("1000")` is False. So it fails.
    - Consider the case where the token is `"401k"` and the reading is `"401"`. `token.startswith("401")` is True. Suffix is `"k"`. No digits in suffix. `_truncation` returns True. This is the intended "401k" case.
    - **The Critical Gap:** The law L-g (WRITTEN FORMS) and L-k (ONE CANONICAL FORM) state that text comparisons should use `pipeline/canon.py` to handle numbers, units, and formatting. `ruling_105_fails` performs **raw string comparison** (`x != tok`, `token.startswith(r)`). It does **not** use `canon.canon_tokens` or `canon.same`.
    - If the integrator's pre-check (which uses the decoder) normalizes numbers (e.g., via canon) before storing the `token` in the record, but this side's `ruling_105_fails` expects the raw string, there is a mismatch.
    - More importantly, if the `token` in the record is `"86,000"` (with comma) and the second reading is `"86000"` (no comma, same value), `token.startswith("86000")` is False. The check fails closed (Hold). This is **safe** (fail closed), but it might reject a valid pass if the integrator's logic considers them equivalent.
    - However, the prompt asks: *"Can it refuse a record the integrator rightly passes, such as a token with a comma or other formatting?"*
    - If the integrator's decoder outputs `"86,000"` and the second recogniser outputs `"86,000"` (stable), it passes.
    - If the integrator's decoder outputs `"86,000"` and the second recogniser outputs `"86000"` (unstable, but same value), the integrator might pass it (if it uses canon). This side's `ruling_105_fails` will see `token="86,000"`, `r="86000"`. `token.startswith(r)` is False. It returns a failure string. `decide()` turns the PASS into a HOLD.
    - **Verdict:** This is a **P1** because it creates a divergence between the integrator's pass and the builder's hold. While "fail closed" is a governing law (M12), the specific instruction for RULING 105 is that the builder's check is a "defence in depth" re-check of the *record*. If the record is valid per the integrator's rules (which likely use canon for number equivalence), the builder should not reject it based on raw string mismatch if the values are canonically equal. The code should use `canon.same` or similar to compare tokens, or at least normalize them, to ensure it doesn't reject valid canonical matches. Currently, it rejects any formatting difference, which may be overly strict and cause unnecessary holds on valid content.

**2. [P2] `_truncation` logic is brittle for multi-digit suffixes**
The `_truncation` function (lines 57-62) defines a truncation as a prefix that drops only a **non-digit** suffix.
- Example: Token `"1234"`. Reading `"123"`. Suffix `"4"` has a digit. `_truncation` returns False. Correct (dropping a digit is not a truncation of a "term" like '401k').
- Example: Token `"123k"`. Reading `"123"`. Suffix `"k"` has no digit. `_truncation` returns True. Correct.
- Example: Token `"123.45"`. Reading `"123"`. Suffix `".45"` has digits. `_truncation` returns False.
- This logic seems consistent with the "401k" example. However, it relies on the token being a single "term". If the token is a complex number like `"1,234.56"`, the logic might not handle it well, but since it fails closed, it's not a P0. It's a P2 because it's a heuristic that might not cover all "truncation" cases defined by the orchestrator, but it's safe.

**3. [P3] Test coverage for `unstable_of` with non-dict entries**
`unstable_of` (lines 97-101) handles `e` being `None` or not a dict. It returns `None` if `r` is not a dict. This is correct. The test `test_the_record_is_car

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus: pp-selectid audit 20261114_2049 (RULING 105, the builder's side)

Reviewers under ruling 107 (2): qwen3.8-27b and glm-5.3-flash. Each raised one P1, the same one, so they agree and
Grok was not asked. Cost: $0.0050 vendor-reported (qwen $0.0039, glm $0.0011); the list-price upper bound was $0.204.

THE P1, raised by both, is IMPLEMENTED. ruling_105_fails compared raw strings, so a formatted token the integrator
rightly passes ('401K', '401(k)', '68,000', 'forty-five') could hold on this side (law L-k: every comparison goes
through canon).
- Every token (the record's token, each decoder reading, each second reading) is now read through canon.canon, the
  integrator's canon, byte-identical. A non-string reading, or one with no token, is None, and so no match and no
  truncation: it fails closed.
- The digit test (a name never qualifies) and the truncation test run on the canonical forms.
- Test: test_formatting_is_read_through_canon_on_both_sides. '401K' / '401(k)' with '401' readings passes; '86,000'
  against '68,000' still holds as (3); a None, empty or blank token holds.

IMPLEMENTED (glm P2): decide() ran the re-check only for the PASS outcomes, so an adopt_spoken entry carrying a record
went unchecked. The re-check now runs for PASS and adopt_spoken alike: a bad record holds, a good one lets the adoption
go on. Test: test_an_adoption_that_rests_on_the_record_is_checked_too. The redundant (e or {}) guard is gone (e is
non-None there).

CONFIRMED, no change:
- glm (2): a hold outcome is never turned into a pass. The re-check can only turn a pass into a hold, and a "hold"
  outcome goes on to the unchanged hold branch.
- glm (3): seal compatibility. The key enters the seal only when a segment carries it, and the frozen 3f481f5a pin is
  tested to recompute.
- glm's other two P1s, downgraded in its own text: a non-string reading fails closed; the record's own tests are
  re-derived anyway.
- qwen's P2s (the truncation helper fails closed on unusual suffixes; the row and imports) need no change.

Tests: 19 for ruling 105, 109 with the pre-check suites. Mutations: 19 (17 before, plus raw strings with no canon,
and an adoption left unchecked); results with cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_2049/C2_STEP.diff (399 lines)
```
   1 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
   2 | index 1c650a3..8eea07a 100644
   3 | --- a/pipeline/lock_precheck.py
   4 | +++ b/pipeline/lock_precheck.py
   5 | @@ -39,12 +39,15 @@ import time
   6 |  from datetime import datetime, timezone
   7 |  
   8 |  import attest as AT
   9 | +import canon as C
  10 |  
  11 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103"   # RULING 103 (orchestrator 14:12 Nov 14): the
  12 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105"   # RULING 105 (orchestrator
  13 | +#   20:13 Nov 14): the unstable second reading joins the rules (the integrator's messages of 20:5x-21:0x Nov 14).
  14 | +#   RULING 103 (orchestrator 14:12 Nov 14): the
  15 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
  16 |  #   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  17 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
  18 | -DECODER = "d1e155c642a6"                      # side): the render's own cut placement joins the pre-check (a passing
  19 | +DECODER = "a4c307f78c94"                      # side): the render's own cut placement joins the pre-check (a passing
  20 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  21 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  22 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  23 | @@ -52,6 +55,8 @@ DECODER = "d1e155c642a6"                      # side): the render's own cut plac
  24 |  #   lock and class unchanged, entries under the old sha not reused): c705b20ed80025af629856e6c34eb609834fef3f708b8614ca26749a4fc8088c
  25 |  #   RULING 103 with the canon-401k fix (law L-k: '401k' is a plan's name, never 401000), landed together on the
  26 |  #   integrator's side (canon-401k 373d0fed + 077407dc, audited batches 79 and 80): d1e155c642a6aaacd578ac5ad2f47c9cd1d71594c9913dc4f0f231fd6b2258ce
  27 | +#   RULING 105 (the integrator's branch ruling105 d5bf9674, audited batch 84; both sides land in lockstep as with 103):
  28 | +#   a4c307f78c94d1c4ee068b5c27862c79a90900880bb885fee68da616ce2a20d6
  29 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  30 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  31 |                          "lock_requests")      # this worktree's; the service only reads it
  32 | @@ -138,6 +143,12 @@ def decide(seg, e):
  33 |      if e is None:
  34 |          return {"verdict": "error", "outcome": None, "why": "no answer from the render's lock in time (law L-m)"}
  35 |      out, why = e.get("outcome"), str(e.get("reason") or "")[:400]
  36 | +    u = e.get("unstable_second_reading")
  37 | +    if u is not None and (out in PASS or out == "adopt_spoken"):   # RULING 105: a pass (or an adoption) that rests
  38 | +        bad = ruling_105_fails(u)                                  # on the readings across passes (glm, audit 2049 C1)
  39 | +        if bad:                                       # this side's own check of the record disagrees: fail closed
  40 | +            return {"verdict": "hold", "outcome": out, "why": f"ruling 105 (this side's check of the pre-check's "
  41 | +                                                              f"record): {bad}"}
  42 |      if out in PASS:
  43 |          return {"verdict": "pass", "outcome": out, "why": why}
  44 |      if out == "hold":
  45 | @@ -178,7 +189,8 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
  46 |      rows = []
  47 |      for s, e in zip(req, got):
  48 |          d = decide(s, e)
  49 | -        rows.append(dict(s, **d, relisten=relisten_of(e), entry=None if e is None else {
  50 | +        rows.append(dict(s, **d, relisten=relisten_of(e), unstable_second_reading=unstable_of(e),
  51 | +                         entry=None if e is None else {
  52 |              "request_id": e.get("request_id"), "at": e.get("at"), "outcome": e.get("outcome"),
  53 |              "lock_sha256": (e.get("lock") or {}).get("sha256") if isinstance(e.get("lock"), dict) else None,
  54 |              "file": os.path.basename(result_file(s, results_dir))}))
  55 | @@ -187,6 +199,61 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
  56 |              "error": "; ".join(errs)[:600] or None}
  57 |  
  58 |  
  59 | +def _canon(x):
  60 | +    """A reading's canonical form through canon (the integrator's canon, byte-identical): '68,000' -> '68000', '401K'
  61 | +    and '401(k)' -> '401k', 'forty-five' -> '45'. None for a non-string or a reading with no token (audit 2049 C1,
  62 | +    qwen and glm: never a raw-string comparison, law L-k)."""
  63 | +    return (C.canon(x) or None) if isinstance(x, str) else None
  64 | +
  65 | +
  66 | +def _truncation(r, token):
  67 | +    """RULING 105 (3): r is the lock's NUMBER token cut short: a prefix of it that keeps a digit and drops only a
  68 | +    NON-DIGIT suffix ('401' of '401k'). A name (a token with no digit) never qualifies, nor does a dropped token ("")
  69 | +    or a different number ('68000' of '86000')."""
  70 | +    return (isinstance(r, str) and bool(r) and r != token and token.startswith(r) and any(ch.isdigit() for ch in r)
  71 | +            and not any(ch.isdigit() for ch in token[len(r):]))
  72 | +
  73 | +
  74 | +def ruling_105_fails(u):
  75 | +    """RULING 105 (orchestrator 20:13 Nov 14), checked on THIS side from the record the pre-check sealed
  76 | +    ("unstable_second_reading"), every token read through canon: the token is adjudicated as the lock's only when
  77 | +    (1) the decoder read it the same on
  78 | +    every pass, (2) the second recogniser's repeated readings of the same audio differ among themselves and one of
  79 | +    them IS the token, and (3) every differing reading is a truncation of it. -> None when the record's pass holds on
  80 | +    its own readings; else why not (a record that is not an object, the many-token form, a hold verdict, or any of the
  81 | +    three not met: every one a hold, never a pass)."""
  82 | +    if not isinstance(u, dict):
  83 | +        return f"the record is not an object ({type(u).__name__})"
  84 | +    if "tokens" in u or u.get("verdict") != "pass":
  85 | +        return f"the record's verdict is {u.get('verdict')!r}" + (f" ({u.get('why')})" if u.get("why") else "")
  86 | +    tok, dec, sec = _canon(u.get("token")), u.get("decoder_readings"), u.get("second_readings")
  87 | +    if not (tok and any(ch.isdigit() for ch in tok)):
  88 | +        return f"the token {u.get('token')!r} is not a number (a name never qualifies)"
  89 | +    if not (isinstance(dec, list) and dec and isinstance(sec, list) and len(sec) >= 2):
  90 | +        return "the record holds too few readings (the decoder's, and at least two of the second recogniser's)"
  91 | +    dt = [_canon(x.get("token")) if isinstance(x, dict) else None for x in dec]       # every token canonical
  92 | +    st = [_canon(x.get("token")) if isinstance(x, dict) else None for x in sec]
  93 | +    if any(x != tok for x in dt):
  94 | +        return f"(1) the decoder is not stable: {dt}"
  95 | +    if len(set(st)) < 2 or tok not in st:
  96 | +        return f"(2) the second recogniser is stable in its readings or never reads the token: {st}"
  97 | +    odd = [x for x in st if x != tok and not _truncation(x, tok)]
  98 | +    if odd:
  99 | +        return f"(3) a differing reading is not a truncation of {tok!r}: {odd}"
 100 | +    tests = u.get("tests")
 101 | +    if not (isinstance(tests, dict) and all(tests.get(k) is True for k in
 102 | +                                            ("decoder_stable", "second_unstable", "truncations_only"))):
 103 | +        return f"the record's own tests do not all hold: {tests}"
 104 | +    return None
 105 | +
 106 | +
 107 | +def unstable_of(e):
 108 | +    """RULING 105: the entry's unstable-second-reading record as it stands, or None (the entry's null, a missing key,
 109 | +    or anything that is not an object). It is sealed onto the segment as it stands (apply; package_pin)."""
 110 | +    r = (e or {}).get("unstable_second_reading") if isinstance(e, dict) else None
 111 | +    return r if isinstance(r, dict) else None
 112 | +
 113 | +
 114 |  def relisten_of(e):
 115 |      """RULING 103: the entry's targeted re-listen record as it stands (one per segment: the lock's token, its short
 116 |      window, both short readings, the verdict, scribe's cost), or None when no re-listen ran (the entry's null, a missing
 117 | @@ -231,6 +298,8 @@ def apply(pk, pre):
 118 |              s["text"], s["attested"] = r["spoken_text"], attested(r)
 119 |          if isinstance(r.get("relisten"), dict):          # RULING 103: "Record both short readings on the pin"
 120 |              s["relisten"] = json.loads(json.dumps(r["relisten"]))   # a copy as it stands (sealed: SEALED_LATER)
 121 | +        if isinstance(r.get("unstable_second_reading"), dict):     # RULING 105: "All readings are recorded on the
 122 | +            s["unstable_second_reading"] = json.loads(json.dumps(r["unstable_second_reading"]))   # pin" (sealed)
 123 |      pk["hook_first_words"] = " ".join(segs[0]["text"].split()[:8])      # as package._package derives it
 124 |      pk["precheck"] = {"ok": True, "request_id": pre.get("request_id"),
 125 |                        "segments": [dict({k: r.get(k) for k in ("video_id", "start", "end", "role", "verdict", "outcome",
 126 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 127 | index db852b6..bfbed07 100644
 128 | --- a/pipeline/package_pin.py
 129 | +++ b/pipeline/package_pin.py
 130 | @@ -147,7 +147,8 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
 131 |                  "scorer_verdict",                          # ruling 56: the clip scorer's affirmation, only when sealed
 132 |                  "attested",                                # ruling 67: the attested-text re-seal's record (re-sealed)
 133 |                  "visual",                                  # ruling 70: the clip's visual record (flags, sheet sha)
 134 | -                "relisten")                                # ruling 103: the targeted re-listen's two short readings
 135 | +                "relisten",                                # ruling 103: the targeted re-listen's two short readings
 136 | +                "unstable_second_reading")                 # ruling 105: every reading across the passes, when it ran
 137 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
 138 |                                                             # separate constant (a test holds them equal): the
 139 |                                                             # integrator's check_pin_only imports this module, which
 140 | @@ -441,7 +442,8 @@ def to_pin(pk, run_name):
 141 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 142 |                       **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual",
 143 |                                            "attested",      # rulings 68 / 72: an adopted spoken text, sealed
 144 | -                                          "relisten")      # ruling 103: only when a re-listen ran, sealed
 145 | +                                          "relisten",      # ruling 103: only when a re-listen ran, sealed
 146 | +                                          "unstable_second_reading")   # ruling 105: only when it ran, sealed
 147 |                          if k in s},
 148 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 149 |      edl_vo = {"intro": pk["vo"]["intro"],
 150 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 151 | index 1c8a870..fb087af 100644
 152 | --- a/tests/package/test_lock_precheck.py
 153 | +++ b/tests/package/test_lock_precheck.py
 154 | @@ -58,7 +58,7 @@ class TestRequest(Dirs):
 155 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 156 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 157 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 158 | -                         "DcUbBkyeh9M.216.054-228.674.d1e155c642a6.json")             # ruling 103's decoder
 159 | +                         "DcUbBkyeh9M.216.054-228.674.a4c307f78c94.json")             # ruling 105's decoder
 160 |  
 161 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 162 |          segs = LP.segments_of([HOOK, CLIP])
 163 | @@ -133,8 +133,9 @@ class TestRuling84(unittest.TestCase):
 164 |      s = LP.segments_of([BREEDLOVE])[0]
 165 |  
 166 |      def test_the_rules_string_is_the_integrators(self):
 167 | -        """RULING 103 (14:12 Nov 14) joined the integrator's rules string (its message of 14:3x Nov 14)."""
 168 | -        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103")
 169 | +        """RULING 103 (14:12 Nov 14) and RULING 105 (20:13 Nov 14) joined the integrator's rules string (its messages
 170 | +        of 14:3x and 20:5x Nov 14)."""
 171 | +        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105")
 172 |  
 173 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 174 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 175 | @@ -205,11 +206,11 @@ class TestCheck(Dirs):
 176 |  
 177 |      def test_an_answer_in_the_old_decoders_file_is_never_read(self):
 178 |          """Audit 1845 C2 (glm): ruling 73 changed the decoder, ruling 84 changed it again, and ruling 90 (the
 179 | -        integrator's spotlight branches) again, and ruling 103 with the canon-401k fix again (14:3x Nov 14); a file
 180 | -        named for an older decoder (25cd6f15e6c9, 8a101f222598, 962353613cb0, c705b20ed800) is never opened, even
 181 | -        with a matching, newer entry under the current rules."""
 182 | +        integrator's spotlight branches) again, ruling 103 with the canon-401k fix again (14:3x Nov 14), and ruling 105
 183 | +        again (20:5x Nov 14); a file named for an older decoder (25cd6f15e6c9, 8a101f222598, 962353613cb0, c705b20ed800,
 184 | +        d1e155c642a6) is never opened, even with a matching, newer entry under the current rules."""
 185 |          s = LP.segments_of([HOOK])[0]
 186 | -        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0", "c705b20ed800"):
 187 | +        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0", "c705b20ed800", "d1e155c642a6"):
 188 |              old = LP.result_file(s, self.res, decoder=dec)
 189 |              with open(old, "w") as f:
 190 |                  json.dump([entry(s, "no_difference", at="2026-11-14T02:00:00Z")], f)
 191 | diff --git a/tests/package/test_ruling_105.py b/tests/package/test_ruling_105.py
 192 | new file mode 100644
 193 | index 0000000..0b8d8b9
 194 | --- /dev/null
 195 | +++ b/tests/package/test_ruling_105.py
 196 | @@ -0,0 +1,202 @@
 197 | +#!/usr/bin/env python3
 198 | +"""RULING 105 (orchestrator 20:13 ET Nov 14), the builder's side, landed in lockstep with the integrator's pre-check
 199 | +(branch ruling105 d5bf9674, decoder a4c307f78c94): the rules and decoder; the record "unstable_second_reading" ("All
 200 | +readings are recorded on the pin") carried from the pre-check entry onto the segment as it stands and sealed
 201 | +(package_pin.SEALED_LATER), only when present, so every pin without one seals as before; and THIS side's own check of a
 202 | +pass that rests on it (lock_precheck.ruling_105_fails): the decoder stable, the second recogniser unstable with one
 203 | +reading equal to the lock's token, every differing reading a truncation of a NUMBER token. Anything else is a hold:
 204 | +a stable disagreement, a different number ('68,000' / '86,000'), a different name (the must-fail cases). Offline."""
 205 | +import copy
 206 | +import os
 207 | +import sys
 208 | +import unittest
 209 | +
 210 | +HERE = os.path.dirname(os.path.abspath(__file__))
 211 | +REPO = os.path.dirname(os.path.dirname(HERE))
 212 | +for _p in ("pipeline", "tests/package"):
 213 | +    sys.path.insert(0, os.path.join(REPO, _p))
 214 | +import lock_precheck as LP  # noqa: E402
 215 | +import package_pin  # noqa: E402
 216 | +import test_angles as TA  # noqa: E402
 217 | +from test_lock_precheck import CLIP, HOOK, Dirs, entry  # noqa: E402
 218 | +
 219 | +
 220 | +def record(token="401k", decoder=("401k", "401k", "401k"), second=("401", "401", "401k"), verdict="pass", tests=None):
 221 | +    """The integrator's field shape (its message of 20:5x Nov 14), as Blockware 06d34e15's readings fill it."""
 222 | +    when = ("2026-11-14T18:51:07Z", "2026-11-14T19:16:06Z", "now")
 223 | +    return {"token": token,
 224 | +            "decoder_readings": [{"at": when[i % 3], "source": "re-listen" if i == 1 else "lock (long window)",
 225 | +                                  "token": t} for i, t in enumerate(decoder)],
 226 | +            "second_readings": [{"at": when[i % 3], "source": "re-listen" if i == 1 else "long window", "token": t}
 227 | +                                for i, t in enumerate(second)],
 228 | +            "tests": tests if tests is not None else {"decoder_stable": True, "second_unstable": True,
 229 | +                                                      "truncations_only": True},
 230 | +            "verdict": verdict}
 231 | +
 232 | +
 233 | +BLOCKWARE = record()
 234 | +
 235 | +
 236 | +class TestTheRules(Dirs):
 237 | +    def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
 238 | +        self.assertTrue(LP.RULES.endswith("+ ruling 103 + ruling 105"))
 239 | +        self.assertEqual(LP.DECODER, "a4c307f78c94")
 240 | +        s = LP.segments_of([HOOK])[0]
 241 | +        self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
 242 | +                          at="2026-11-14T21:00:00Z"))
 243 | +        self.assertIsNone(LP.answer(s, self.res))                                 # ruling 103's rules: never read
 244 | +        self.put(s, entry(s, at="2026-11-14T21:01:00Z"))
 245 | +        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")
 246 | +
 247 | +
 248 | +class TestThisSidesCheck(unittest.TestCase):
 249 | +    s = LP.segments_of([HOOK])[0]
 250 | +
 251 | +    def decide(self, rec, outcome="no_difference"):
 252 | +        return LP.decide(self.s, entry(self.s, outcome, unstable_second_reading=rec))
 253 | +
 254 | +    def test_blockwares_readings_pass(self):
 255 | +        self.assertIsNone(LP.ruling_105_fails(copy.deepcopy(BLOCKWARE)))
 256 | +        self.assertEqual(self.decide(copy.deepcopy(BLOCKWARE))["verdict"], "pass")
 257 | +
 258 | +    def test_no_record_changes_nothing(self):
 259 | +        self.assertEqual(self.decide(None)["verdict"], "pass")
 260 | +        self.assertEqual(self.decide(None, "hold")["verdict"], "hold")
 261 | +
 262 | +    def test_must_fail_a_second_recogniser_stable_in_its_disagreement(self):
 263 | +        d = self.decide(record(second=("401", "401", "401")))              # even a record that says "pass"
 264 | +        self.assertEqual(d["verdict"], "hold")
 265 | +        self.assertIn("(2)", d["why"])
 266 | +
 267 | +    def test_a_record_whose_second_readings_never_vary_is_no_unstable_reading(self):
 268 | +        d = self.decide(record(second=("401k", "401k")))                   # nothing disputed: the record should
 269 | +        self.assertEqual(d["verdict"], "hold")                              # be null; one that says "pass" is
 270 | +        self.assertIn("(2)", d["why"])                                      # malformed, and fails closed
 271 | +
 272 | +    def test_must_fail_a_different_number(self):
 273 | +        d = self.decide(record(token="86000", decoder=("86000", "86000"), second=("68000", "86000")))
 274 | +        self.assertEqual(d["verdict"], "hold")                              # '68,000' is no truncation of '86,000'
 275 | +        self.assertIn("(3)", d["why"])
 276 | +
 277 | +    def test_must_fail_a_different_name(self):
 278 | +        for second in (("Taylor", "Saylor"), ("Say", "Saylor")):           # a name never qualifies, cut short or not
 279 | +            d = self.decide(record(token="Saylor", decoder=("Saylor", "Saylor"), second=second))
 280 | +            self.assertEqual(d["verdict"], "hold", second)
 281 | +            self.assertIn("a name never qualifies", d["why"])
 282 | +
 283 | +    def test_a_dropped_token_or_a_digit_cut_off_is_no_truncation(self):
 284 | +        for token, second in (("401k", ("", "401k")),                   # dropped
 285 | +                              ("4015", ("401", "4015")),                 # a digit cut off: another number
 286 | +                              ("401k", ("40", "401k"))):                 # '1k' cut off holds a digit
 287 | +            d = self.decide(record(token=token, decoder=(token, token), second=second))
 288 | +            self.assertEqual(d["verdict"], "hold", second)
 289 | +            self.assertIn("(3)", d["why"])
 290 | +
 291 | +    def test_formatting_is_read_through_canon_on_both_sides(self):          # audit 2049 C1 (qwen, glm)
 292 | +        self.assertIsNone(LP.ruling_105_fails(record(token="401K", decoder=("401(k)", "401k", "401K"),
 293 | +                                                     second=("401", "401", "401K"))))
 294 | +        d = self.decide(record(token="86,000", decoder=("86,000", "86000"), second=("68,000", "86,000")))
 295 | +        self.assertEqual(d["verdict"], "hold")                              # commas change nothing: still another
 296 | +        self.assertIn("(3)", d["why"])                                      # number
 297 | +        for tok in (None, "", "  "):
 298 | +            d = self.decide(record(token=tok, decoder=("401k", "401k"), second=("401", "401k")))
 299 | +            self.assertEqual(d["verdict"], "hold", tok)
 300 | +            self.assertIn("is not a number", d["why"])
 301 | +
 302 | +    def test_an_adoption_that_rests_on_the_record_is_checked_too(self):     # audit 2049 C1 (glm)
 303 | +        spoken = "Bitcoin launched in January of 2009. It's never been, uh, renamed."
 304 | +        d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken,
 305 | +                                    unstable_second_reading=record(second=("401", "401", "401"))))
 306 | +        self.assertEqual((d["verdict"], "(2)" in d["why"]), ("hold", True))
 307 | +        d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken,
 308 | +                                    unstable_second_reading=copy.deepcopy(BLOCKWARE)))
 309 | +        self.assertEqual(d["verdict"], "adopt")                             # a good record: the adoption goes on
 310 | +
 311 | +    def test_an_unstable_decoder_holds(self):
 312 | +        d = self.decide(record(decoder=("401k", "401")))
 313 | +        self.assertEqual(d["verdict"], "hold")
 314 | +        self.assertIn("(1)", d["why"])
 315 | +
 316 | +    def test_the_second_recogniser_must_read_the_token_at_least_once(self):
 317 | +        d = self.decide(record(second=("401", "40l")))
 318 | +        self.assertEqual(d["verdict"], "hold")
 319 | +        self.assertIn("(2)", d["why"])
 320 | +
 321 | +    def test_too_few_readings_hold(self):
 322 | +        for dec, sec in (((), ("401", "401k")), (("401k",), ("401k",))):
 323 | +            d = self.decide(record(decoder=dec, second=sec))
 324 | +            self.assertEqual(d["verdict"], "hold", (dec, sec))
 325 | +            self.assertIn("too few readings", d["why"])
 326 | +
 327 | +    def test_the_records_own_tests_and_verdict_must_agree(self):
 328 | +        d = self.decide(record(tests={"decoder_stable": True, "second_unstable": True, "truncations_only": False}))
 329 | +        self.assertEqual(d["verdict"], "hold")
 330 | +        self.assertIn("own tests", d["why"])
 331 | +        d = self.decide(record(verdict="hold"))                          # a hold record under a pass outcome: hold
 332 | +        self.assertEqual(d["verdict"], "hold")
 333 | +        many = {"tokens": ["401k", "45"], "verdict": "hold", "why": "more than one disputed token"}
 334 | +        d = self.decide(many)                                               # the edge form
 335 | +        self.assertEqual(d["verdict"], "hold")
 336 | +        self.assertIn("more than one disputed token", d["why"])
 337 | +        for odd in ("pass", ["401k"], 7):                                   # not an object
 338 | +            self.assertEqual(self.decide(odd)["verdict"], "hold", odd)
 339 | +
 340 | +    def test_a_ruling_105_hold_stays_a_hold(self):
 341 | +        d = self.decide(record(second=("401", "401", "401"), verdict="hold"), outcome="hold")
 342 | +        self.assertEqual(d["verdict"], "hold")
 343 | +
 344 | +
 345 | +class TestTheRecordReachesTheSeal(Dirs):
 346 | +    def check(self, rec):
 347 | +        segs = LP.segments_of([HOOK, CLIP])
 348 | +        self.put(segs[0], entry(segs[0], unstable_second_reading=rec))
 349 | +        self.put(segs[1], entry(segs[1], unstable_second_reading=None))
 350 | +        return LP.check([HOOK, CLIP], "r", self.req, self.res, log=lambda m: None)
 351 | +
 352 | +    def pk(self):
 353 | +        return {"segments": [{"video_id": m["video_id"], "start": m["start"], "end": m["end"], "text": m["text"]}
 354 | +                             for m in (HOOK, CLIP)], "lines": [], "hook_first_words": ""}
 355 | +
 356 | +    def test_the_record_is_carried_as_it_stands_and_only_when_present(self):
 357 | +        pre = self.check(copy.deepcopy(BLOCKWARE))
 358 | +        self.assertTrue(pre["ok"])
 359 | +        self.assertEqual([r["unstable_second_reading"] for r in pre["segments"]], [BLOCKWARE, None])
 360 | +        pk = LP.apply(self.pk(), pre)
 361 | +        self.assertEqual(pk["segments"][0]["unstable_second_reading"], BLOCKWARE)
 362 | +        self.assertIsNot(pk["segments"][0]["unstable_second_reading"], pre["segments"][0]["unstable_second_reading"])
 363 | +        self.assertNotIn("unstable_second_reading", pk["segments"][1])
 364 | +        self.assertIsNone(LP.unstable_of({"unstable_second_reading": ["401k"]}))     # not an object: no record
 365 | +
 366 | +    def test_a_pass_this_side_refuses_never_reaches_a_pin(self):
 367 | +        pre = self.check(record(second=("401", "401", "401")))
 368 | +        self.assertFalse(pre["ok"])
 369 | +        self.assertEqual(pre["segments"][0]["verdict"], "hold")
 370 | +        with self.assertRaises(ValueError):
 371 | +            LP.apply(self.pk(), pre)
 372 | +
 373 | +    def test_the_record_is_sealed_and_a_pin_without_one_seals_as_before(self):
 374 | +        base = TA.TestPinAndTruth.pk(None)
 375 | +        plain = package_pin.to_pin(copy.deepcopy(base), "r")
 376 | +        self.assertNotIn("unstable_second_reading", plain["segments"][0])
 377 | +        with_r = copy.deepcopy(base)
 378 | +        with_r["segments"][0]["unstable_second_reading"] = copy.deepcopy(BLOCKWARE)
 379 | +        pin = package_pin.to_pin(with_r, "r")
 380 | +        self.assertEqual(pin["segments"][0]["unstable_second_reading"], BLOCKWARE)
 381 | +        sha = pin["moments_package"]["package_sha256"]
 382 | +        self.assertEqual(package_pin.pin_seal(pin), sha)                           # the integrator's recompute
 383 | +        self.assertNotEqual(sha, plain["moments_package"]["package_sha256"])      # the record is inside the seal
 384 | +        tampered = copy.deepcopy(pin)
 385 | +        tampered["segments"][0]["unstable_second_reading"]["second_readings"][2]["token"] = "401"
 386 | +        self.assertNotEqual(package_pin.pin_seal(tampered), sha)
 387 | +        self.assertEqual(package_pin.pin_seal(plain), plain["moments_package"]["package_sha256"])
 388 | +
 389 | +    def test_the_spotlight_now_rendering_still_recomputes_to_its_own_seal(self):
 390 | +        import json
 391 | +        p = os.path.join(REPO, "tests", "package", "proof", "ledger_20261114_230148", "SPOTLIGHT_PIN.json")
 392 | +        pin = json.load(open(p))
 393 | +        self.assertEqual(package_pin.pin_seal(pin), pin["moments_package"]["package_sha256"])
 394 | +        self.assertTrue(pin["moments_package"]["package_sha256"].startswith("3f481f5a"))
 395 | +
 396 | +
 397 | +if __name__ == "__main__":
 398 | +    unittest.main()
 399 | 
```

---

pp-selectid, RULING 105 (the orchestrator, 20:13 ET Nov 14), the BUILDER's side. It lands in lockstep with the
integrator's pre-check: branch ruling105 d5bf9674, audited (its batch 84), FINAL decoder_sha a4c307f78c94..., RULES
"... + ruling 103 + ruling 105".

THE RULING: "when (1) the primary decoder's reading of the token is stable across its passes, (2) the second
recogniser's repeated readings of the SAME audio differ among themselves and at least one equals the lock's token,
and (3) every differing reading is a TRUNCATION of the lock's token (a prefix of the same term: '401' of '401k'), never
a different number or name, the token is adjudicated as the lock's and the clip may seal. All readings are recorded on
the pin (decoder passes, each scribe reading with its call id) under 'unstable_second_reading'. Anything else stays a
final hold: a second recogniser that is stable in its disagreement, a different number ('68,000' / '86,000'), a
different name. Must-fail tests for those three."

THE INTEGRATOR'S FIELD SHAPE (its message, 20:5x Nov 14): the result entry's key "unstable_second_reading" is null, or
{"token": str, "decoder_readings": [{"at", "source", "token"}], "second_readings": [{"at", "source", "token"}],
"tests": {"decoder_stable", "second_unstable", "truncations_only"}, "verdict": "pass" | "hold"}. The edge form for more
than one disputed token is {"tokens": [...], "verdict": "hold", "why": "..."}. A truncation is the token minus a
NON-DIGIT suffix only; names never qualify, nor does a dropped token. A ruling-105 pass leaves the normal outcome
(no_difference etc.); a ruling-105 hold is "hold".

THE CHANGE ON THIS SIDE:
- pipeline/lock_precheck.py:
  - DECODER and RULES as above.
  - _truncation(r, token) and ruling_105_fails(u): THIS side's own re-check of a pass that rests on the record (defence
    in depth, law L-j fail closed). decide() makes a PASS outcome a HOLD when the entry carries a record that does not
    hold on its own readings.
  - unstable_of(e): the record as it stands, or None when it is not an object.
  - check() rows carry it; apply() copies it onto the segment.
- pipeline/package_pin.py: SEALED_LATER and to_pin's carry gain "unstable_second_reading", only when present, so every
  pin without it seals as before.
- tests/package/test_lock_precheck.py: the literal decoder and rules; d1e155c642a6 joins the never-read decoders.
- tests/package/test_ruling_105.py (new): 16 tests, including the must-fail cases.

UNCHANGED GUARDS (you see only the diff):
- decide() handles a "hold" outcome after the PASS branch: it returns hold whatever the record says.
- apply() raises ValueError unless pre["ok"] is True, which needs every row to pass or adopt.
- package_pin.seal() adds a SEALED_LATER key to a segment's body only when the segment carries that key.
- The integrator's check_pin_only imports package_pin.py LIVE from this worktree, so the seal must stay backward
  compatible: the frozen 3f481f5a pin is tested to still recompute.

PLEASE CHECK:
(1) Does ruling_105_fails implement the three tests exactly, with no gap through which a different number, a name, or
    a stable disagreement passes? Can it refuse a record the integrator rightly passes, such as a token with a
    comma or other formatting?
(2) Is a pass outcome carrying a non-object record correctly a hold? Is a hold outcome never turned into a pass?
(3) Seal compatibility: can any existing pin's recompute change?
(4) Do the tests pin every branch? The mutation results are listed in the consensus file.


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
