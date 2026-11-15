# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1524
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 53 s finish=stop usage in 7581 / out 993 usd_reported=0.029107 usd~0.063 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1524 (C1_STEP.diff)**

**Summary of change**  
The diff implements STATE Q2 (15:04 ET 2026-11-15, default at 15:24): `hook_answer()` tolerates *only* a complete JSON object followed by trailing closing braces + whitespace (the exact Grok out-of-contract pattern observed in SHADOW86.jsonl and the alone-test). `json.loads` is tried first; `raw_decode` + explicit rest validation is used only on failure. Anything else (text, other punctuation, leading junk, partial object, etc.) still raises `ValueError` exactly as before. The hook contract checks, per-candidate error handling, cache semantics, and all other `json.loads` sites are untouched. A one-line test driver fix ensures `usd_reported` (ledger figure) is emitted instead of the price-table estimate. New unit test exercises the exact allowed/invalid cases plus the spend path.

**Verification against requested checks**  
(1) Nothing but a complete object followed *only* by closing braces/whitespace is accepted. The `not rest.strip() or rest.replace("}", "").strip()` guard + `rest.count("}")` is precise; all other suffixes raise.  
(2) Hook contract (`set(v) == {"hooks"}`, per-id dict shape, `HOOK_PARTS | {"why"}`, numeric ratings, string `why`, etc.) runs *after* `hook_answer` and still rejects malformed objects.  
(3) No other verdict path, cache, provider, or test was altered; only `hook_ratings.parse` and the new helper are affected.  
(4) `spent_reported()` reads the ledger's `usd_reported` line (rounded to 6 decimals); test writes a fixture containing both reported/estimate values and asserts the reported figure.  
(5) `test_q2_an_answer_whose_only_extra_is_trailing_closing_braces_is_read` + updated `test_hook115` cover happy path, note emission, clean JSON, all listed bad cases, and the spend correction. Mutation suite (braces ignored, text accepted, note omitted, estimate used) kills the 4 bad variants.

**Compliance with governing laws**  
- **SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, L-a through L-l, LAW 20/M2, M12 FAIL-CLOSED, L-d protected preview, v2f byte-identity**: No impact. This is isolated to hook-rating JSON ingest (editorial selection stage). No transcript, cut-point, fade, credit, sign-off, edge-word, claim, or render logic is touched. No gate threshold changed, no failing gate reclassified, no exception turned into a pass for non-JSON cases.  
- **L-k (ONE CANONICAL FORM)**: Irrelevant — this is provider response parsing, not content/word comparison. `canon.py` paths untouched.  
- **L-l (MODEL REPLY COUNTS ONLY WHOLE)**: Satisfied. `ValueError` from `hook_answer` is still treated as unrated (continues to next model per existing `except` block). Only *structurally valid* objects that also pass the full `HOOK_PARTS` contract are used; partial/malformed replies remain INCONCLUSIVE for that candidate.  
- **L-j (RELEASE AUTHORISED ON THESE BYTES)**: Unaffected; ATTESTATION, gate inventory, and `release_auth` logic not modified.  
- **Smallest diff / no new renderer / GPU0 only / M1**: Compliant.  

**Findings**  
[P3] Double invocation of `hook_answer(r.text)[1]` to obtain the dropped count is redundant (first parse could forward the tuple). Negligible cost but unnecessary string re-parsing.  
[P2] Model-specific tolerance for Grok's trailing-brace pattern, even though narrowly scoped and audit-first via STATE Q2, introduces a maintenance burden. Long-term fix should be at the provider/output layer rather than parser workaround. Does not breach any listed law but should be monitored.  
[P3] `BRACES_NOTE` and inline timestamps are hard-coded literals; future audit notes should pull date from a constant or generation header for consistency with regression/reference tagging.  
[P3] Test uses `self.canned(ok + extra)` with duplicated `bad, bad` arguments in the error case loop — style nit, does not affect correctness.  

All suites (medley, hook115, spotlight, hook_bar, release_auth, dec13_clusters, etc.) pass. No regression against v2f, protected preview, or must-fail fixtures. Change is safe to merge.

**P1_OR_WORSE: 0**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 146 s finish=stop usage in 8142 / out 5528 usd_reported=0.005319 usd~0.107 (upper-bound price)

I will analyze the provided diff against the governing laws and the specific questions asked.

### Analysis of `pipeline/package.py`

**1. `hook_answer` Logic (Lines 12-25)**
The function attempts to parse JSON. If `json.loads` fails, it uses `json.JSONDecoder().raw_decode` to parse the first valid JSON object. It then checks if the remaining string (`rest`) consists *only* of closing braces `}` and whitespace.

*   **Logic Check:**
    *   `t = (text or "").strip()`
    *   `try: return json.loads(t), 0` -> Handles standard valid JSON.
    *   `except ValueError:` -> Handles the "Extra data" case.
    *   `v, end = json.JSONDecoder().raw_decode(t)` -> Parses the first object. If the text doesn't start with a valid JSON object, this raises `ValueError`, which propagates up. This is correct behavior for "out of contract".
    *   `rest = t[end:]`
    *   `if not rest.strip() or rest.replace("}", "").strip():`
        *   `not rest.strip()`: If there is no rest, `json.loads` would have succeeded initially (unless the input was empty/whitespace, which `json.loads` also rejects). However, `raw_decode` on a string like `"{...}   "` would set `end` to the index after `}`, so `rest` would be `"   "`. `rest.strip()` is `""`, so `not rest.strip()` is `True`. The condition triggers `raise ValueError`.
        *   Wait, let's look closer. If `json.loads` failed, it means there was extra data. So `rest` cannot be empty or whitespace-only if `json.loads` failed?
        *   Actually, `json.loads` is strict. `json.loads('{"a":1} ')` succeeds in Python 3.12? Let's check. `json.loads` ignores trailing whitespace. So `json.loads('{"a":1} ')` returns `{"a":1}`. It does *not* raise `ValueError`.
        *   Therefore, the `except ValueError` block is only entered if there is non-whitespace extra data, OR if the JSON is malformed.
        *   If `json.loads` fails due to "Extra data", `raw_decode` will parse the first object. `rest` will contain the extra data.
        *   If `rest` is `" }"`, `rest.strip()` is `"}"`. `not rest.strip()` is `False`.
        *   `rest.replace("}", "").strip()` -> `"".strip()` -> `""`. `if not ""` is `True`.
        *   So `raise ValueError` is triggered?
        *   Let's re-read the condition: `if not rest.strip() or rest.replace("}", "").strip():`
        *   If `rest` is `" }"`:
            *   `rest.strip()` is `"}"`. `not "}"` is `False`.
            *   `rest.replace("}", "").strip()` is `""`. `if not ""` is `True`.
            *   So it raises `ValueError`.
        *   **BUG FOUND**: The logic is inverted or flawed. The goal is to *accept* answers with trailing braces. The code raises `ValueError` (rejects) when the rest is *only* braces.
        *   Let's check the test case in `test_medley.py` (Line 112-115):
            ```python
            for extra, n in (("}", 1), ("}}\n", 2), (" }", 1)):
                got, err = PK.hook_ratings(self.canned(ok + extra), ms, ctx(), set(), set())
                self.assertEqual((err, got["a"]["rating"], got["a"].get("answer_note")),
                                 (None, 4, f"{n} {PK.BRACES_NOTE}"), extra)
            ```
            The test expects `err` to be `None` (success) and `rating` to be 4.
            But my trace of `hook_answer` says it raises `ValueError`.
            Let's re-evaluate `json.loads` behavior.
            In Python, `json.loads('{"a":1}}')` raises `json.decoder.JSONDecodeError: Extra data: line 1 column 8 (char 7)`.
            So `json.loads` fails.
            `raw_decode('{"a":1}}')` returns `({'a': 1}, 7)`. `end` is 7.
            `rest` is `'}'`.
            Condition: `if not rest.strip() or rest.replace("}", "").strip():`
            `rest.strip()` is `'}'`. `not '}'` is `False`.
            `rest.replace("}", "").strip()` is `''`. `if not ''` is `True`.
            So it executes `raise ValueError(...)`.
            
            If it raises `ValueError`, `hook_ratings` catches it (Line 41: `except ... ValueError ...`).
            Line 42: `err = ...`.
            Line 43: `continue`.
            So `got` will be `{}` (empty dict) for that candidate.
            The test expects `got["a"]["rating"]` to be 4.
            **The code as written will FAIL the provided tests.**

            Let's look at the condition again.
            `if not rest.strip() or rest.replace("}", "").strip():`
            This condition is `True` if:
            1. `rest` is empty/whitespace (which shouldn't happen if `json.loads` failed, but maybe `raw_decode` consumed everything? No, `raw_decode` stops at the end of the first object. If the input was just `{"a":1}`, `json.loads` would have succeeded. So `rest` must have content).
            2. `rest` contains any character other than `}` or whitespace.
            
            The intent is: "If the rest is NOT (only braces and whitespace), raise."
    

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1524 (STATE Q2: the hook job reads an answer whose only extra is trailing closing braces; the hook115 spend read)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0); deepseek-v4.1-flash ran out of its 16,000 output tokens with no answer
(finish=length), so the driver asked Grok (0). Cycle 1: $0.0379 vendor-reported. No P1.

Grok [P2] "a model-specific tolerance is a maintenance burden; the long-term fix belongs at the provider / output
layer". Noted: it is scoped to the hook job only (every other verdict keeps json.loads), it reads nothing but a
complete object followed by closing braces, the contract's own checks still decide, and every rating read this way
says so in its record ("answer_note"), so its frequency is counted from the records. Ruling 106's default (Q2, 15:24
ET) asked for exactly this; a change at the provider layer would touch every verdict and is not ordered.

No change in this pass. Tests as in the QUESTION (281 pass; 4 of 4 mutations killed).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1524/C2_STEP.diff (126 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5bbda7a..1afb4a7 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -872,6 +872,25 @@ def hook_live_bar():
   6 |      return HB.bar(None, HOOK_VERSION, HOOK_SEED, path=HB.PATH)
   7 |  
   8 |  
   9 | +BRACES_NOTE = "trailing closing brace(s) dropped (STATE Q2, 15:04 ET Nov 15)"
  10 | +
  11 | +
  12 | +def hook_answer(text):
  13 | +    """STATE Q2 (15:04 ET Nov 15, default at 15:24): the hook job's answer as JSON. Grok's answers out of contract were
  14 | +    valid JSON followed by ONE extra closing brace; an answer whose only extra is trailing closing braces (and white
  15 | +    space) is read as the object before them. -> (object, how many braces were dropped). Anything else that is not one
  16 | +    JSON object raises ValueError: out of contract, as before (and the contract's own checks still apply)."""
  17 | +    t = (text or "").strip()
  18 | +    try:
  19 | +        return json.loads(t), 0
  20 | +    except ValueError:
  21 | +        v, end = json.JSONDecoder().raw_decode(t)        # ValueError when no object starts the answer
  22 | +        rest = t[end:]
  23 | +        if not rest.strip() or rest.replace("}", "").strip():
  24 | +            raise ValueError(f"hook answer: {rest.strip()[:40]!r} after the object") from None
  25 | +        return v, rest.count("}")
  26 | +
  27 | +
  28 |  def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=HOOK_SEED):
  29 |      """RULING 59 (a) / RULING 115: the hook question of ruling 52 (HOOK_QUESTION: scroll / alone / setup, each 1-5) asked
  30 |      of EVERY given moment ALONE: ONE call per candidate (ruling 115: the asking the calibration measured; a batch moved
  31 | @@ -907,7 +926,7 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
  32 |          return out, None
  33 |  
  34 |      def parse(text, ids):
  35 | -        v = json.loads(text.strip())
  36 | +        v, _ = hook_answer(text)                 # STATE Q2: an answer whose only extra is trailing closing braces
  37 |          h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
  38 |          if not isinstance(h, dict) or set(h) != set(ids) or any(
  39 |                  not isinstance(x, dict) or set(x) != set(HOOK_PARTS) | {"why"} or not isinstance(x["why"], str) or
  40 | @@ -926,9 +945,10 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
  41 |          except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # this candidate has no rating
  42 |              err = err or f"{type(e).__name__}: {str(e)[:200]}"       # (law L-m); the others are still asked
  43 |              continue
  44 | -        x = h[mid]
  45 | +        x, dropped = h[mid], hook_answer(r.text)[1]
  46 |          rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
  47 | -               "backend": r.backend, "rule": HOOK_OWN_RULE}           # the rating orders hooks; hook_own decides
  48 | +               "backend": r.backend, "rule": HOOK_OWN_RULE,           # the rating orders hooks; hook_own decides
  49 | +               **({"answer_note": f"{dropped} {BRACES_NOTE}"} if dropped else {})}   # said, when it was read so
  50 |          out[mid] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
  51 |          new[key(m)] = {r.backend: rec}
  52 |      _cache_put(cache, new)
  53 | diff --git a/tests/package/hook115.py b/tests/package/hook115.py
  54 | index b5458cf..09deef0 100644
  55 | --- a/tests/package/hook115.py
  56 | +++ b/tests/package/hook115.py
  57 | @@ -114,6 +114,15 @@ def verdict(rows, model=None):
  58 |      return {"passes": ok, "approved": a, "negatives": n}
  59 |  
  60 |  
  61 | +def spent_reported(path=None):
  62 | +    """The ledger's VENDOR-REPORTED total (its usd_reported line), never the price table's estimate."""
  63 | +    path = path or SPEND
  64 | +    if not os.path.exists(path):
  65 | +        return 0.0
  66 | +    with open(path) as f:
  67 | +        return round(float(json.load(f).get("usd_reported") or 0.0), 6)
  68 | +
  69 | +
  70 |  def run(models, now=None):
  71 |      """Every model, both variants, the ten each -> the result, also written to QUESTION_V2_TEST.json."""
  72 |      now = now or datetime.now(timezone.utc)
  73 | @@ -140,8 +149,7 @@ def run(models, now=None):
  74 |                        f"{rows[-1].get('error') or ''}; ${r.spent():.4f}", flush=True)
  75 |              res[variant] = {"rows": rows, **verdict(rows, MODELS[key])}
  76 |          out["models"][MODELS[key]] = res
  77 | -    out["spent_usd_reported"] = round(P.Router(env_path=R.ENV, spend_path=SPEND).spent(), 6) if \
  78 | -        os.path.exists(SPEND) else 0.0
  79 | +    out["spent_usd_reported"] = spent_reported()
  80 |      os.makedirs(OUT, exist_ok=True)
  81 |      with open(os.path.join(OUT, "QUESTION_V2_TEST.json"), "w") as f:
  82 |          json.dump(out, f, indent=1)
  83 | diff --git a/tests/package/test_hook115.py b/tests/package/test_hook115.py
  84 | index 5384fa4..c9c944e 100644
  85 | --- a/tests/package/test_hook115.py
  86 | +++ b/tests/package/test_hook115.py
  87 | @@ -83,7 +83,10 @@ class TestRate(unittest.TestCase):
  88 |                  mock.patch.object(X, "SPEND", os.path.join(d, "S.json")), mock.patch.object(X, "rate", rate), \
  89 |                  mock.patch.object(X, "build_router", R), mock.patch.object(X.H, "ref_moments", lambda: POS), \
  90 |                  mock.patch.object(X, "negatives", lambda: NEG), mock.patch.object(X.H, "registry", lambda: []):
  91 | +            with open(os.path.join(d, "S.json"), "w") as f:            # the report names the REPORTED figure,
  92 | +                f.write('{"usd_reported": 0.1, "usd_estimate": 1.0}')     # never the estimate (15:17 ET Nov 15)
  93 |              out = X.run(["grok", "qwen"])
  94 | +            self.assertEqual(out["spent_usd_reported"], 0.1)
  95 |              self.assertTrue(os.path.exists(os.path.join(d, "QUESTION_V2_TEST.json")))
  96 |              X.report()
  97 |              self.assertIn("by xai:grok-4.20-0309-reasoning", open(os.path.join(d, "REPORT.md")).read())
  98 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  99 | index 3fd7c13..33db082 100644
 100 | --- a/tests/package/test_medley.py
 101 | +++ b/tests/package/test_medley.py
 102 | @@ -1386,6 +1386,23 @@ class TestRuling59HookFirst(unittest.TestCase):
 103 |              got, _ = PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache, seed=PK.HOOK_SEED + 1)
 104 |              self.assertEqual((got["a"]["cached"], len(c.calls)), (False, 1))   # ... and never read
 105 |  
 106 | +    def test_q2_an_answer_whose_only_extra_is_trailing_closing_braces_is_read(self):
 107 | +        """STATE Q2 (15:04 ET Nov 15, default 15:24): Grok's out-of-contract hook answers were valid JSON and ONE extra
 108 | +        closing brace; such an answer is read and its record says so; any other extra stays out of contract, and the
 109 | +        contract's own checks still apply."""
 110 | +        ms = [pm("a", "A", 12.0)]
 111 | +        ok = '{"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}'
 112 | +        for extra, n in (("}", 1), ("}}\n", 2), (" }", 1)):
 113 | +            got, err = PK.hook_ratings(self.canned(ok + extra), ms, ctx(), set(), set())
 114 | +            self.assertEqual((err, got["a"]["rating"], got["a"].get("answer_note")),
 115 | +                             (None, 4, f"{n} {PK.BRACES_NOTE}"), extra)
 116 | +        got, err = PK.hook_ratings(self.canned(ok), ms, ctx(), set(), set())
 117 | +        self.assertEqual((err, "answer_note" in got["a"]), (None, False))
 118 | +        for bad in (ok + "} x", ok + "]", ok + ', "b": 1}', '{"hooks": {"a": {"scroll": 4}}}}', "} " + ok):
 119 | +            got, err = PK.hook_ratings(self.canned(bad, bad), ms, ctx(), set(), set())
 120 | +            self.assertEqual(got, {}, bad)                                   # out of contract: no rating
 121 | +            self.assertIn("Error", err)
 122 | +
 123 |      def test_a_candidate_left_unrated_never_stops_the_others_being_asked(self):
 124 |          """RULING 115: one call a candidate; a candidate whose chain is spent has no rating (law L-m), the others are
 125 |          still asked, and the first error is returned."""
 126 | 
```

---

pp-selectid: STATE Q2 (15:04 ET Nov 15; ruling 106's default at 15:24: YES, audit-first), THE HOOK JOB READS AN
ANSWER WHOSE ONLY EXTRA IS TRAILING CLOSING BRACES. And a one-line fix to ruling 115 (3)'s driver (the spend it
reports). Files: pipeline/package.py (hook_answer, hook_ratings' parse and record), tests/package/test_medley.py,
tests/package/hook115.py, tests/package/test_hook115.py.

THE QUESTION AS ASKED ON STATE LINE 1 (15:04 ET), verbatim: "Q2 GROK'S OUT-OF-CONTRACT HOOK ANSWER IS VALID JSON WITH
ONE EXTRA CLOSING BRACE (1 OF 10 TODAY; THE ALONE-TEST'S 2 WERE JSONDecodeErrors TOO, THEIR TEXT NOT KEPT, SO NOT
KNOWN TO BE THE SAME): ACCEPT AN ANSWER WHOSE ONLY EXTRA IS TRAILING CLOSING BRACES (AUDIT-FIRST)? RECOMMENDED: YES.
DEFAULT IN 20 MIN: YES." No answer came by 15:24, so the default is acted on.

THE EVIDENCE: build 11 (ledger_20261115_195152) kept Grok's refused hook answer in its shadow log (SHADOW86.jsonl, the
deciding text): '{"hooks": {"2bca1130b3eceac83ff8": {"scroll": 2, "alone": 3, "setup": 3, "why": "conversational
opener lacks punch"}}}}' -> json.loads: "Extra data: line 1 column 119". The object is complete; the last "}" is extra.
Ruling 115 (3)'s test lost one Grok rating per variant the same way (JSONDecodeError; text not kept).

THE CHANGE:
- package.hook_answer(text): json.loads first; only when that fails, json.JSONDecoder().raw_decode reads the object
  that STARTS the answer, and the rest must be closing braces and white space only (at least one brace) -> (object,
  braces dropped). Any other rest (text, "]", another key, nothing at all) raises ValueError: out of contract as
  before. hook_ratings' parse uses it; the contract's own checks are unchanged and still apply to the object (a
  partial object followed by braces is still refused). Only the hook job reads answers this way; every other verdict
  keeps json.loads.
- The record of a rating read this way says so: "answer_note": "<n> trailing closing brace(s) dropped (STATE Q2,
  15:04 ET Nov 15)" (the cache keeps it with the rating).
- hook115.py: the run's reported spend is read from the ledger's usd_reported line (spent_reported); its closing read
  had built a router on the estimate basis and written the price table's estimate ($1.0964 against $0.1062 reported:
  corrected by hand in the committed result file, c7775751).

UNCHANGED GUARDS: providers.call_parsed (pipeline/providers.py:690-716) moves on to the next model when parse raises
ValueError / TypeError / KeyError; hook_ratings catches the chain spent per candidate (law L-m: no rating);
_cache_put stores only records hook_ratings built.

TESTS: test_medley's new test: one, two (with a newline) or a spaced trailing brace is read, rating 4, and the
record carries the note; a clean answer carries none; "} x", "]", a further key, a partial object plus a brace, and a
brace BEFORE the object stay out of contract (no rating). test_hook115: the reported figure, never the estimate.
Suites: 281 pass (medley, hook115, spotlight, hook_bar). Mutations (after a control run): braces never accepted, any
trailing text accepted, the record not saying so, the estimate read as reported: 4 of 4 killed.

PLEASE CHECK: (1) that nothing but a complete object followed ONLY by closing braces is read; (2) that the hook
contract's checks still decide; (3) that no other verdict's parsing changes; (4) the spend fix; (5) the tests.


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
