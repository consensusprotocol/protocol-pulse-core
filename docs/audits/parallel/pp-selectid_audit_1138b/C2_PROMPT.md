# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1138b
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 112 s finish=stop usage in 5782 / out 2433 usd~0.054 (upper-bound price)

# Audit: pp-selectid-1138b — C1_STEP (scorer_verdicts failure diagnostics)

## Scope of what I can verify
Only the 66-line diff is provided. I have not seen the surrounding `package.py` (e.g. whether `sc` is referenced after the `try`, what `self.file()` defaults to, what `sv()`/`fv()` build, whether `text_sha`/`affirmed_verdict`/`scorer_problems` are as assumed). Findings are limited to what the diff itself shows.

## Trace of the failure paths

**Except branch (lines 26–30).** `stage` is initialised to `"open"` before the `try` (line 9), so an `open()` failure reports `stage="open"` correctly. `parse` is set before `json.load` (line 12), `shape` before the key reads (line 15). `sc` is initialised to `None` (line 9), so the guard `if isinstance(sc, dict)` (line 30) is safe when the failure happens before `sc = d["scorer"]` — no exception can escape the except branch via the `sc.get` comprehension. The `**{...} if isinstance(sc, dict) else {}` conditional-expression-in-`**`-unpacking form is valid Python 3.5+; on 3.12 it unpacks correctly. The except branch still returns `{}` as the first element, so no failure path can yield a usable verdict — the fail-closed contract is preserved. Note: `json.load` can also raise `UnicodeDecodeError` (a `ValueError` subclass) — caught. `d["scorer"]`/`d["verdicts"]` raising `KeyError` is caught; `TypeError`/`AttributeError` are caught if `d` is, say, a list (then `d["scorer"]` → `TypeError`, caught; `sc` stays whatever it was — if `d` is a list, `sc` is still `None`, guard holds).

**"Why" chain (lines 18–23, 31–33).** Unchanged in logic; the split of `sc, vs = d["scorer"], d["verdicts"]` into two statements means a missing `"verdicts"` key now reaches the except with `sc` populated — which is exactly the intended improvement, and the `isinstance(sc, dict)` guard covers the case where `"scorer"` itself was present but not a dict (e.g. `{"scorer": 5}` → `sc=5`, then `sc.get` in the why-chain would raise `AttributeError` — but that's in the *try* block, line 18, caught? No: lines 18–23 are inside the `try`? Let me re-read.

Looking at the diff: the `try:` at line 10 opens the file; lines 12–23 (including the `why = (...)` chain, which calls `sc.get(...)`) appear to be inside the `try` — the `except` at line 24/26 follows them. If so, an `AttributeError` from `sc.get` on a non-dict `sc` (e.g. `{"scorer": 5, "verdicts": {}}`) is caught by the except, and the new record's guard `isinstance(sc, dict)` correctly omits the fields. If instead the `why` chain sits *after* the `try/except` (the diff context is ambiguous — the `if why:` at line 31 is clearly outside), then `{"scorer": 5, "verdicts": {}}` would raise `AttributeError` *outside* the try. **I cannot resolve this from the diff alone** — the hunk header `@@ -1000,18 +1000,25 @@` shows the `why` chain's last line at old line ~1017 and the `except` at old ~1018, and the `if why:` at new ~1031, which is consistent with the `why` chain being *inside* the try (old code had `except` immediately after the chain). Given the old code's line 24 `except` directly follows line 23 (end of the chain), the chain is inside the `try`, and the non-dict-`scorer` case is caught. Flagging as a verification note, not a finding.

**Record keys.** Except-branch record: `read`, `why` (now prefixed `stage: ExcType: msg`), `path`, `render_scorer_sha`, and conditionally `kind`/`event`/`scorer_sha`/`threshold`. Why-chain record (line 32–33): unchanged keys. Consumers of the record see a *superset* of the old keys on the except path; the `why` string format changed (now prefixed with `stage: `). If any downstream consumer matched the old `why` format exactly (e.g. a regex or equality), it would break — not verifiable from the diff; the tests shown only use `startswith`, which is safe.

## Findings

**P1-1 — `tests/package/test_medley.py:48–51` (new test): the "shape" test's `why` assertion is brittle and the test's premise partially overlaps the wrong branch.** The test writes a dict *without* `"verdicts"` and asserts `rec["why"].startswith("shape: KeyError")`. That works. But the test also relies on `self.file()` producing a path the function can open — if `self.file()` (line 46, called with no args) has required positional parameters, this fails at test-collection; not verifiable from the diff. Additionally, the test never exercises the case the reviewers' P1 actually named as most dangerous: `{"scorer": <non-dict>}` (e.g. a list or number), which is the case the new `isinstance(sc, dict)` guard exists for. Concrete scenario: a future refactor makes `d["scorer"]` a list; the guard silently drops the fields, no test notices, and the record loses diagnostics without a failing test. Severity: P1 (test-coverage gap on the exact guard added), not a code defect.

**P2-1 — `pipeline/package.py:27` (except-branch `why`): the stage prefix can mislabel

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 44 s finish=stop usage in 5913 / out 113 usd~0.032 (upper-bound price)

**P0/P1/P2 findings:** none verifiable from diff  
(returns {} on every failure path (except + if-why); except block cannot raise (stage/sc init, isinstance guard on sc.get, all values from params or caught types); record keys match added tests (stage in why, path/render_scorer_sha always on error, scorer fields only when dict read); non-ASCII test confirms identical sha256(utf8) and affirmed_verdict acceptance; split assignments + stage var exactly as described for partial diagnostics).  

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 65 s finish=stop usage in 6218 / out 2428 usd~0.055 (upper-bound price)

# Audit: pp-selectid_audit_1138b / C1_STEP.diff

## Findings

### P1-1: `sc.get` on a non-dict `sc` raises `AttributeError` inside the `except` handler (File: `pipeline/package.py`, diff lines 26–30)

The `except` block is intended to be a fail-closed sink that *never* raises. However, the new diagnostic code calls `sc.get(...)` unconditionally inside the `except` handler:

```python
except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
    return {}, {"read": False, "why": f"{stage}: {type(e).__name__}: {str(e)[:160]}", "path": path,
                "render_scorer_sha": code_sha,
                **({k: sc.get(k) for k in ("kind", "event", "scorer_sha", "threshold")}
                   if isinstance(sc, dict) else {})}
```

The guard `if isinstance(sc, dict) else {}` protects the *dict comprehension*, but it does **not** protect the `sc.get` call itself if `sc` is a non-dict, non-None object that was successfully assigned before the exception.

**Concrete scenario:**
1. `json.load(f)` succeeds, so `stage = "parse"` is set.
2. `sc = d["scorer"]` succeeds, so `stage = "shape"` is set. Suppose `d["scorer"]` is a **string** (e.g., `"scorer": "moments"`). `sc` is now a `str`.
3. `vs = d["verdicts"]` raises `KeyError` (or any other exception in the tuple).
4. Control enters the `except` block.
5. `isinstance(sc, dict)` is `False`, so the dict comprehension is skipped. **However**, the code as written in the diff is:
   ```python
   **({k: sc.get(k) for k in ...} if isinstance(sc, dict) else {})
   ```
   Wait — re-reading the diff carefully: the `isinstance(sc, dict)` check *is* present. If `sc` is a `str`, `isinstance(sc, dict)` is `False`, so the comprehension is **not** evaluated, and `sc.get` is **not** called. The `else {}` branch is taken.

   Let me re-examine. The expression is:
   ```python
   **({k: sc.get(k) for k in ("kind", "event", "scorer_sha", "threshold")}
      if isinstance(sc, dict) else {})
   ```
   Python evaluates the condition `isinstance(sc, dict)` first. If `False`, it evaluates `{}` and never touches `sc.get`. So `sc.get` is **not** called when `sc` is not a dict.

   **Correction:** The `isinstance` guard *does* prevent `sc.get` from being called on a non-dict. The `AttributeError` risk I initially identified is **not present** in the code as written.

   However, there is a subtler issue: what if `sc` is a dict-like object that is *not* a `dict` (e.g., a `collections.defaultdict` or a custom mapping)? `isinstance(sc, dict)` would be `False` for a `defaultdict`? No — `defaultdict` is a subclass of `dict`, so `isinstance` returns `True`. A custom `Mapping` that is not a `dict` subclass would return `False`, and `sc.get` would not be called. This is safe.

   **Verdict on P1-1: Retracted.** The `isinstance(sc, dict)` guard correctly prevents `sc.get` from being called on non-dict values. No exception can escape the `except` handler due to `sc.get`.

### P2-1: `stage` variable is set to `"open"` before the `try` block, but the `open()` call is inside the `try` (File: `pipeline/package.py`, diff lines 9–12)

```python
stage, sc = "open", None
try:
    with open(path) as f:
        stage = "parse"
        d = json.load(f)
```

This is correct: if `open()` raises, `stage` is still `"open"`. If `json.load()` raises, `stage` is `"parse"`. If `d["scorer"]` or `d["verdicts"]` raises, `stage` is `"shape"`. The stage tracking is accurate. No issue.

### P2-2: The `why`-chain path (diff lines 31–33) does not include `path` or `render_scorer_sha` in the record

The `except` branch now records `path` and `render_scorer_sha`, but the `if why:` branch (lines 31–33) does not:

```python
if why:
    return {}, {"read": False, "why": why, "kind": sc.get("kind"), "event": sc.get("event"),
                "scorer_sha": sc.get("scorer_sha"), "render_scorer_sha": code_sha, "threshold": sc.get("threshold")}
```

It does include `render_scorer_sha` (as `code_sha`), but not `path`. This is a minor inconsistency in diagnostic completeness between the two failure paths. The `except` branch records `path`; the `why`-chain branch does not. This is a P2 (cosmetic/diagnostic completeness), not a correctness issue.

### P2-3: Test at diff line 45 asserts `rec["why"].startswith("open: FileNotFoundError")`

This is correct for a missing file. The `open()` call raises `FileNotFoundError`, `stage` is `"open"`, and the `why` string is `"open: FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/latest.json'"`. The `startswith` check is valid.

### P2-4: Test at diff lines 46–51 (missing `"verdicts"` key)

```python
odd_shape = self.file()
with open(odd_shape, "w") as f:
    json.dump({"scorer": {"kind": "moments", "event": None, "scorer_sha": "s" * 64, "threshold": 3.5}}, f)
idx, rec = PK.scorer_verdicts(odd_shape, "s" * 64)
self.assertEqual((idx, rec["kind"], rec["scorer_sha"]), ({},

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1138b (audit 1138's cycle-2 consensus P1, the increment): cycle 1 consensus

- **Run:**
  - grok: no finding, "SHIP: yes".
  - qwen: its P1 (sc.get on a non-dict) is retracted in its own text, because the isinstance guard covers it; "SHIP:
    yes with conditions".
  - glm: "SHIP: yes", one P1 (a missing test).
- No P0 or P1 holds against the code.

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | glm P1-1 / qwen (its condition): no test exercises a "scorer" that is not an object, the case the isinstance guard exists for | One more case in test_the_verdicts_file_is_used_only_when_every_check_holds: {"scorer": ["moments"], "verdicts": {}}. It yields {} and read False, the why starts "shape: AttributeError", and no scorer field is recorded. No exception escapes. |

## Recorded (P2, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P2-1: the "stage: " prefix spends a few of the 160 message characters | Cosmetic. The exception type and the stage are what a reader needs. |
| G2 | glm P2-2: a recorded threshold can be a non-numeric value | The same as the "why"-chain path. It is a record, never a gate (the gate refuses it). |
| G3 | glm P2-3: the non-ASCII test checks the pin through affirmed_verdict, not separately | affirmed_verdict computes the pin's own sha256 inline (package_pin.py), and the test checks both against the same hashlib call. |
| G4 | glm P2-4: a statement inserted later between `try:` and `stage = "parse"` could be mislabelled | Informational; no such statement exists. |

## Verification

- test_medley 113 OK on the scratch copy (dev19). The increment is diffed against the cycle-2-audited state of audit
  1138 (a scratch commit), so this review sees only these lines.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1138b/C2_STEP.diff (71 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index bd24d36..278b93a 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1000,18 +1000,25 @@ def scorer_verdicts(path, code_sha):
   6 |      (stand_alone.affirmed(score, fault, moments=True): the score alone) is no verdict."""
   7 |      import stand_alone as SA
   8 |      num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
   9 | +    stage, sc = "open", None
  10 |      try:
  11 |          with open(path) as f:
  12 | +            stage = "parse"
  13 |              d = json.load(f)
  14 | -        sc, vs = d["scorer"], d["verdicts"]
  15 | +        stage = "shape"
  16 | +        sc = d["scorer"]
  17 | +        vs = d["verdicts"]
  18 |          why = ("a kind other than 'moments' (ruling 60)" if sc.get("kind") != SCORER_KIND else
  19 |                 "an event (ruling 60: a moments verdict carries none)" if sc.get("event", "absent") is not None else
  20 |                 "the render's scorer code could not be read" if not code_sha else
  21 |                 "a scorer_sha that is not the render's scorer code now" if sc.get("scorer_sha") != code_sha else
  22 |                 "another threshold" if not num(sc.get("threshold")) or sc["threshold"] != SA.CLIP_MIN_SCORE else
  23 |                 "no verdicts" if not isinstance(vs, dict) else None)
  24 | -    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
  25 | -        return {}, {"read": False, "why": f"{type(e).__name__}: {str(e)[:160]}"}
  26 | +    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:   # audit 1138 C2 (qwen, glm): the
  27 | +        return {}, {"read": False, "why": f"{stage}: {type(e).__name__}: {str(e)[:160]}", "path": path,   # record
  28 | +                    "render_scorer_sha": code_sha,                  # says what failed, where, and what it read
  29 | +                    **({k: sc.get(k) for k in ("kind", "event", "scorer_sha", "threshold")}
  30 | +                       if isinstance(sc, dict) else {})}
  31 |      if why:
  32 |          return {}, {"read": False, "why": why, "kind": sc.get("kind"), "event": sc.get("event"),
  33 |                      "scorer_sha": sc.get("scorer_sha"), "render_scorer_sha": code_sha, "threshold": sc.get("threshold")}
  34 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  35 | index 4b5f5f7..1d76c65 100644
  36 | --- a/tests/package/test_medley.py
  37 | +++ b/tests/package/test_medley.py
  38 | @@ -1325,7 +1325,20 @@ class TestRuling56Scorer(unittest.TestCase):
  39 |          idx, rec = PK.scorer_verdicts(self.file({"f": fv("x", 4.0, "starts_mid_thought")}), "s" * 64)
  40 |          self.assertTrue(idx["f"]["affirmed"])                           # ruling 60: the score alone
  41 |          idx, rec = PK.scorer_verdicts("/nonexistent/latest.json", "s" * 64)
  42 | -        self.assertEqual((idx, rec["read"]), ({}, False))
  43 | +        self.assertEqual((idx, rec["read"], rec["path"], rec["render_scorer_sha"]),
  44 | +                         ({}, False, "/nonexistent/latest.json", "s" * 64))
  45 | +        self.assertTrue(rec["why"].startswith("open: FileNotFoundError"))   # audit 1138 C2: what failed, and where
  46 | +        odd_shape = self.file()
  47 | +        with open(odd_shape, "w") as f:
  48 | +            json.dump({"scorer": {"kind": "moments", "event": None, "scorer_sha": "s" * 64, "threshold": 3.5}}, f)
  49 | +        idx, rec = PK.scorer_verdicts(odd_shape, "s" * 64)                # no "verdicts" key
  50 | +        self.assertEqual((idx, rec["kind"], rec["scorer_sha"]), ({}, "moments", "s" * 64))
  51 | +        self.assertTrue(rec["why"].startswith("shape: KeyError"))
  52 | +        with open(odd_shape, "w") as f:                                  # audit 1138b C1 (qwen, glm): a "scorer"
  53 | +            json.dump({"scorer": ["moments"], "verdicts": {}}, f)        # that is not an object
  54 | +        idx, rec = PK.scorer_verdicts(odd_shape, "s" * 64)
  55 | +        self.assertEqual((idx, rec["read"], "kind" in rec), ({}, False, False))
  56 | +        self.assertTrue(rec["why"].startswith("shape: AttributeError"))
  57 |          bad = self.file()
  58 |          with open(bad, "w") as f:
  59 |              f.write("{not json")
  60 | @@ -1486,6 +1499,10 @@ class TestRuling56Scorer(unittest.TestCase):
  61 |              segs[i]["scorer_verdict"] = sv(t, 4.0)
  62 |          self.assertEqual(package_pin.scorer_problems(segs), [])
  63 |          self.assertEqual(package_pin.scorer_problems([{"approved_text": self.OPENER}]), [])   # a hook: the gate's
  64 | +        import hashlib
  65 | +        t = "And Bitcoin\u2019s caf\u00e9 \u2014 na\u00efve \u201choldlers\u201d win \U0001F680"   # audit 1138 C2 (glm
  66 | +        self.assertTrue(package_pin.affirmed_verdict({"approved_text": t, "scorer_verdict": sv(t, 4.0)}))   # P2-2):
  67 | +        self.assertEqual(PK.text_sha(t), hashlib.sha256(t.encode("utf-8")).hexdigest())   # one sha, build and pin
  68 |  
  69 |  
  70 |  class TestOrder0622StepAFromBothVendors(unittest.TestCase):
  71 | 
```

---

You are auditing a SMALL INCREMENT on branch pp-selectid, made after the second review cycle of a larger change
(audit 1138: the builder reads the integrator's clip-scorer verdicts, fail closed). Only state what you can verify from
the diff provided. If uncertain, say so; do not guess.

Background: scorer_verdicts(path, code_sha) reads the integrator's verdicts file (read only) and returns ({pid: verdict},
a record of the read). Every failure uses NOTHING from the file (fail closed): a missing, unreadable or malformed file
(the except branch), a wrong kind / event / sha / threshold (the "why" chain). The record is written into the build's
output so the integrator and the orchestrator can see why no verdict was used.

The two cycle-2 reviewers agreed on ONE P1 (qwen P1-NEW-1, glm P1-1): the except branch returned only
{"read": False, "why": "<exception>"}, losing the diagnostics the "why"-chain path records. This increment:
1. records the stage that failed ("open" / "parse" / "shape"), the path, the render's recomputed sha (code_sha), and,
   when the "scorer" object was already read as a dict, its kind / event / scorer_sha / threshold. To keep "scorer"
   available when "verdicts" is missing, the two reads are split into two statements.
2. tests: the missing-file record (stage, path, sha) and a file whose "verdicts" key is missing (stage "shape", the
   scorer fields kept); and (glm P2-2) one test that the build's text_sha and the pin's inline sha256 agree on a
   non-ASCII text (curly quotes, accents, an em dash, an emoji), with the pin's affirmed_verdict accepting it.

Check: that nothing here can make a verdict usable on any failure path (the except branch still returns {} first);
that no exception can escape the except branch (e.g. sc.get on a non-dict); the record's keys; the tests.
Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


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
