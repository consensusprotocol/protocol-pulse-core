# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1426
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 342 s finish=stop usage in 12734 / out 10231 usd~0.192 (upper-bound price)

<medium> **(a) `test_lock_precheck.py:180` now depends on `LP.DECODER` — the old-decoder test at :195 still hard-codes the new one.** Not a bug, just asymmetry: `test_an_answer_in_the_old_decoders_file_is_never_read` writes files for the four *old* decoders and asserts `LP.answer` is None, which is correct only because the current `DECODER` literal (`lock_precheck.py:43`, `d1e155c642a6`) is not in that list. If a future ruling bumps `DECODER` again, the test silently stops covering the "current decoder's file IS read" half. The ruling-103 test file covers the rules half (`test_ruling_103.py:240-245`) but nothing asserts a *current-decoder* file *is* read with the *current* RULES except `test_check` at :179, which now uses the f-string, so it would pass trivially if `DECODER` were wrong. Concrete: if `DECODER` were set to `c705b20ed800` by mistake, `test_check` still passes (it compares against `LP.DECODER`), the old-decoder test still passes (c705b20ed800 is now in the never-read list — wait, it's written *and* asserted unread, so it would fail). Actually the f-string at :180 weakens the ruling-90-era literal check; the :195 loop still catches it. Downgrade: informational. </medium>

<medium> **(a) `lock_precheck.py:59` — `relisten_of` is applied to the *entry* `e`, but `check()` zips `req` with `got`; when the service returns fewer entries than requests, `got` can be shorter and `e` is None.** The diff at :58-62 shows `rows.append(dict(s, **d, relisten=relisten_of(e), entry=None if e is None else {...}))` — the guard is there, so a missing entry yields `relisten=None` on the row, and `apply()` at :82-83 only copies when `isinstance(r.get("relisten"), dict)`. Fail-closed, consistent with M12. No break found. </medium>

<medium> **(c) `canon.py:19-25` — the plan-branch runs *before* `_NUM.match(t)`, and its two-token case requires `len(toks[i+1]) == 1`.** Sequence: tokens `["401", "k"]` → plan = `"401k"` (in `_PLANS`), one token, spans both. But `["401", "k", "plan"]` — the test at test_canon.py:146-147 asserts `canon_spans(["a","401","k","plan"])` contains `("401k", 1, 2)`. For that to hold, the plan branch must consume both tokens and the span must be (1,2) — i.e. the *end index* of the second token. If `canon_spans` derives spans from the trips' third element (the end offset), the appended trip is `(plan, trips[i][1], trips[last][2])` = `("401k", trips[1][1], trips[2][2])`, so the span's *end* is the second token's end. That matches the test. However: the single-token case `t in _PLANS` (e.g. token `"401k"` itself) — the test `test_amounts_are_unchanged` asserts `canon_tokens("401 kilos")` → `["401", "kilos"]`, which requires the two-token join to require the *letter* `k`/`b` exactly, and `"kilos"` (5 chars) fails `len==1`, so it falls through to `_NUM`. Consistent. But what about `"401b"`? Not in `_PLANS` (`("401k","403b","457b")`), so token `"401b"` → `_NUM` → 401000? No — `_NUM` presumably matches digits; `"401b"` — depends on `_NUM`'s pattern, not shown. If `_NUM` doesn't match `"401b"`, it's passed through as a word token `"401b"`, and `C.same("a 401b", "a 401(b)")` would be False — a plan spelling the fix misses. Not in the ruling's scope (ruling names 401k/403b/457b only), so informational. </medium>

<medium> **(b) `lock_precheck.py:82-83` — `apply()` copies `r["relisten"]` onto the segment *by reference* from the parsed entry, not a copy.** The entry dict comes from `json.load` of the results file; the row's `relisten` (from `relisten_of(e)`) and the segment's `relisten` (from `r.get("relisten")` in `apply`) are the *same object* if the caller passes the same `pre` report to `apply` twice, or if the report's rows and the entry share the dict. In `test_ruling_103.py:259-265` the test deep-copies RELISTEN into the entry, then `LP.apply(self.pk(), pre)` — the segment's `relisten` *is* the row's `relisten` *is* the entry's `relisten` (all one object, since `relisten_of` returns `r` itself, not a copy). If any later stage mutates `pk["segments"][0]["relisten"]` (e shared-mutable state), the pin's sealed bytes change without the entry file changing. Concrete: a later ruling adds a key to the record in place → the seal changes silently. Today, with no mutation, the seal is computed after `apply`, so the bytes sealed are the bytes present. Not a break today; a fragility. </medium>

<medium> **(b) `package_pin.py:104-108` — `to_pin` carries `relisten` via `**{k: s[k] for k in (...) if k in s}`; the diff shows the `if k in s` guard applies to the whole starred dict.** The diff at :104-108 shows:

```python
**{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual",
                     "attested", "relisten")
   if k in s},
```

The `if k in s` guard covers all six keys, so a segment without `relisten` seals exactly as before — the "a pin without one seals as before" t

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 30 s finish=stop usage in 12586 / out 140 usd~0.066 (upper-bound price)

<medium>none: no violations of laws L-j/L-k/L-l, no attack (a-e) sequences verifiable in diff+facts (e.g. lock_precheck:59-72 + test_ruling_103:259-272 guards non-dict relisten; package_pin:104-107 + test:277-288 preserves old-pin seal; canon:19-25 + test_canon:139-143 leaves $401k/40k/401 kilos unchanged; RULES/DECODER+old-list updates + test_lock_precheck:194-201 blocks c705b20ed800/old-rules reads; landing order per ruling prevents (d)).</medium>
SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 49 s finish=stop usage in 14301 / out 1406 usd~0.064 (upper-bound price)

I have reviewed the diff, the governing laws, and the background facts. Here is the audit.

### Findings

**<critical> None**

**<high> None**

**<medium> None**

**<low> (Informational / Verification Notes)**

1.  **Landing Order & Decoder Mismatch (Attack d):**
    The background states: *"The builder commits this change and says READY with no build running. The integrator merges to main and pushes. Only then does the builder push, so no pre-check of the builder's waits on a sha it cannot read."*
    *   **Verification:** The code in `lock_precheck.py` updates `DECODER` to `d1e155c642a6`. If a build were to run *before* the integrator's merge, the builder would look for files named `*.d1e155c642a6.json`. The integrator's service (still on the old code) would produce files named `*.c705b20ed800.json` (or whatever the previous decoder was).
    *   **Result:** `lock_precheck.answer()` would return `None` for all segments because the file names wouldn't match. `check()` would then raise a `ValueError` or return a failure state (depending on `check`'s error handling for missing answers, which is described as "waits for its own" in tests, implying a retry or hold).
    *   **Conclusion:** This is a **fail-closed** behavior. It blocks the build rather than sealing a wrong pin. This complies with **M12 FAIL CLOSED**. The landing order described in the background prevents this state from occurring in practice, but even if it did, the system would not produce an incorrect output; it would simply halt.

2.  **Relisten Record Sealing (Attack b):**
    *   **Code:** `lock_precheck.apply()` copies `r["relisten"]` to `s["relisten"]` only if `isinstance(r.get("relisten"), dict)`.
    *   **Code:** `package_pin.to_pin()` includes `"relisten"` in the `SEALED_LATER` loop: `**{k: s[k] for k in ... "relisten" if k in s}`.
    *   **Verification:** The record is passed "as it stands" (no re-shaping). If the integrator provides a valid dict, it is sealed. If it provides `null` or a non-dict, it is excluded from the segment dict, and thus excluded from the seal.
    *   **Tampering:** `test_ruling_103.py` verifies that tampering with `second_reading` changes the `pin_seal`. This confirms the record is part of the cryptographic integrity check.
    *   **Conclusion:** Compliant. A pin delivered before this change (without `relisten`) will recompute correctly because `relisten` is not in `s`, so it is not added to the body.

3.  **Canon Changes (Attack c):**
    *   **Code:** `canon.py` adds `_PLANS = ("401k", "403b", "457b")`.
    *   **Logic:** In `_canon_seq`, if a token is in `_PLANS` (or a split form like `401` + `k`), it is treated as a single name token, *unless* `owed` is not `None` (i.e., a currency symbol `$` was seen).
    *   **Verification:**
        *   `C.canon_tokens("$401k")` -> `["401000", "dollars"]` (Amount preserved).
        *   `C.canon_tokens("a 401k")` -> `["a", "401k"]` (Name preserved).
        *   `C.same("a 401k", "a 401,000")` -> `False` (Correctly distinguishes name from number).
    *   **Impact on Gates:** Law **L-k** states "a different number... never does [compare equal]". Previously, `401k` might have been parsed as `401000` (if the suffix logic applied) or `401` + `k` (if not). The fix ensures `401k` is a distinct token from `401000`. This aligns with the "Written Forms" law (L-g) and the specific ruling. It does not change comparisons for non-plan names or amounts with `$`.
    *   **Conclusion:** Compliant. The change is scoped to retirement plan names.

4.  **Old Decoder/Rules Reuse (Attack a):**
    *   **Code:** `lock_precheck._matches()` checks `rules == RULES` and file name contains `DECODER`.
    *   **Verification:** `RULES` is updated to include `ruling 103`. `DECODER` is updated to `d1e155c642a6`.
    *   **Test:** `test_an_answer_in_the_old_decoders_file_is_never_read` explicitly tests that files with old decoder hashes (`c705b20ed800`, etc.) are ignored.
    *   **Conclusion:** Compliant. Old answers are fail-closed (ignored).

5.  **Laws Compliance:**
    *   **M12 FAIL CLOSED:** Missing data (no matching decoder file) results in no answer, which blocks the pre-check.
    *   **L-k ONE CANONICAL FORM:** The canon fix ensures `401k` is treated consistently as a name, not a number, across both builder and render sides (byte-identical files).
    *   **L-j RELEASE IS AUTHORISED ON THESE BYTES:** The `relisten` record is sealed into the pin. Any tampering with the record invalidates the pin seal.

### SHIP: yes

The change is minimal, fail-closed, and correctly implements Ruling 103 and the Canon fix. The landing order ensures that the builder's code (expecting the new decoder) is only deployed after the integrator's service (producing the new decoder) is live. The sealing logic correctly includes the new `relisten` field when present and excludes it when absent, maintaining ba

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 20261114_1426 (the ruling-103 landing: DECODER / RULES, the relisten record sealed, canon-401k), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes. No finding.
- qwen3.8-27b: SHIP yes. No <critical>, <high> or <medium>.
- glm-5.3-flash (342 s): no <critical> or <high>. Its <medium> notes are fragility and consistency notes, each ending
  "not a break". One is taken.

## Taken

- **glm (b), the record is shared by reference.** apply() put the parsed entry's own dict on the segment. A later
  in-place edit of either would then move the sealed bytes without the entry file changing. apply() now seals a COPY,
  as it stands (a JSON round trip, so the record's types are kept). The test asserts that the copy is equal and is not
  the same object.

## Documented, no change

- **glm (c), canon's plan-name rules** ("401b", an "owed" number before a plan, the split form). canon.py and
  test_canon.py are the integrator's audited code (batches 79 and 80), taken byte-identical so that both sides keep one
  canonical form. Questions on its rules go to its owner; this change neither adds nor removes a rule.
- **glm (b), the edge form {token, against, verdict "hold", why}.** It rides only on a HOLD entry. A held segment never
  reaches apply() (pre-check ok is False), so the edge form is never sealed. A sealed record is always a passing
  re-listen's full form, as it stands.
- **glm (d), the landing order.** Builds are this side's own: no build runs between READY and the integrator's push,
  and this side pushes only after it, as agreed.
- **glm (a)/(e), the test literals, the history comment, attested()'s default rule text.**
  - The literal file-name assertion pins the integrator's contract (the 12-hex decoder in the file name).
  - The plumbing assertion uses LP.DECODER.
  - attested() records an ADOPTED text (ruling 84's class), which ruling 103 does not change.

Verification: 8 of 8 mutations killed. test_ruling_103 and test_lock_precheck pass. The copy is checked by a new
assertion.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_1426/C2_STEP.diff (304 lines)
```
   1 | diff --git a/pipeline/canon.py b/pipeline/canon.py
   2 | index c977a6a..6564cd6 100644
   3 | --- a/pipeline/canon.py
   4 | +++ b/pipeline/canon.py
   5 | @@ -29,6 +29,9 @@ _UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eig
   6 |  _TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
   7 |  _SCALES = {"hundred": 100, "thousand": 10 ** 3, "million": 10 ** 6, "billion": 10 ** 9, "trillion": 10 ** 12}
   8 |  _SUFFIX = {"k": 10 ** 3, "m": 10 ** 6, "mn": 10 ** 6, "b": 10 ** 9, "bn": 10 ** 9, "t": 10 ** 12, "tn": 10 ** 12}
   9 | +# US retirement plans are NAMES: '401k' = '401(k)' (tokenised '401', 'k') is never 401000 (L-k: a different number never
  10 | +# compares equal; the 2026-11-14 pre-check finding). With a '$' before it, '$401k' stays the amount $401,000.
  11 | +_PLANS = ("401k", "403b", "457b")
  12 |  _ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
  13 |          "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
  14 |          "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
  15 | @@ -157,6 +160,13 @@ def _canon_seq(trips, heads=False):
  16 |              i += 1
  17 |              continue
  18 |          num, s0 = None, i
  19 | +        plan = t if t in _PLANS else (t + toks[i + 1] if i + 1 < len(toks) and len(toks[i + 1]) == 1
  20 | +                                      and t + toks[i + 1] in _PLANS else None)     # '401', 'k': only the letter
  21 | +        if plan is not None and owed is None:        # a plan's name, one token over every word it spans
  22 | +            last = i if plan == t else i + 1
  23 | +            out.append((plan, trips[i][1], trips[last][2]))
  24 | +            i = last + 1
  25 | +            continue
  26 |          m = _NUM.match(t)
  27 |          if m:
  28 |              try:
  29 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
  30 | index e7095b4..1c650a3 100644
  31 | --- a/pipeline/lock_precheck.py
  32 | +++ b/pipeline/lock_precheck.py
  33 | @@ -40,14 +40,18 @@ from datetime import datetime, timezone
  34 |  
  35 |  import attest as AT
  36 |  
  37 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84"   # RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  38 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103"   # RULING 103 (orchestrator 14:12 Nov 14): the
  39 | +#   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
  40 | +#   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  41 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
  42 | -DECODER = "c705b20ed800"                      # side): the render's own cut placement joins the pre-check (a passing
  43 | +DECODER = "d1e155c642a6"                      # side): the render's own cut placement joins the pre-check (a passing
  44 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  45 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  46 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  47 |  #   spotlight branches in pinned.py, merged fd5c9cc4 at 23:16 ET Nov 13; RULES unchanged; every medley span's decode,
  48 |  #   lock and class unchanged, entries under the old sha not reused): c705b20ed80025af629856e6c34eb609834fef3f708b8614ca26749a4fc8088c
  49 | +#   RULING 103 with the canon-401k fix (law L-k: '401k' is a plan's name, never 401000), landed together on the
  50 | +#   integrator's side (canon-401k 373d0fed + 077407dc, audited batches 79 and 80): d1e155c642a6aaacd578ac5ad2f47c9cd1d71594c9913dc4f0f231fd6b2258ce
  51 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  52 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  53 |                          "lock_requests")      # this worktree's; the service only reads it
  54 | @@ -174,7 +178,7 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
  55 |      rows = []
  56 |      for s, e in zip(req, got):
  57 |          d = decide(s, e)
  58 | -        rows.append(dict(s, **d, entry=None if e is None else {
  59 | +        rows.append(dict(s, **d, relisten=relisten_of(e), entry=None if e is None else {
  60 |              "request_id": e.get("request_id"), "at": e.get("at"), "outcome": e.get("outcome"),
  61 |              "lock_sha256": (e.get("lock") or {}).get("sha256") if isinstance(e.get("lock"), dict) else None,
  62 |              "file": os.path.basename(result_file(s, results_dir))}))
  63 | @@ -183,6 +187,14 @@ def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_
  64 |              "error": "; ".join(errs)[:600] or None}
  65 |  
  66 |  
  67 | +def relisten_of(e):
  68 | +    """RULING 103: the entry's targeted re-listen record as it stands (one per segment: the lock's token, its short
  69 | +    window, both short readings, the verdict, scribe's cost), or None when no re-listen ran (the entry's null, a missing
  70 | +    key, or anything that is not an object). It is sealed onto the segment as it stands (apply; package_pin)."""
  71 | +    r = (e or {}).get("relisten") if isinstance(e, dict) else None
  72 | +    return r if isinstance(r, dict) else None
  73 | +
  74 | +
  75 |  def attested(row, run_rule="ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"):
  76 |      """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it."""
  77 |      return {"rule": run_rule, "was": row["approved_text"], "differences": row["differences"],
  78 | @@ -217,6 +229,8 @@ def apply(pk, pre):
  79 |              if q:
  80 |                  raise ValueError(f"ruling 67: these lines quote the changed words of {s['video_id']}: {q}")
  81 |              s["text"], s["attested"] = r["spoken_text"], attested(r)
  82 | +        if isinstance(r.get("relisten"), dict):          # RULING 103: "Record both short readings on the pin"
  83 | +            s["relisten"] = json.loads(json.dumps(r["relisten"]))   # a copy as it stands (sealed: SEALED_LATER)
  84 |      pk["hook_first_words"] = " ".join(segs[0]["text"].split()[:8])      # as package._package derives it
  85 |      pk["precheck"] = {"ok": True, "request_id": pre.get("request_id"),
  86 |                        "segments": [dict({k: r.get(k) for k in ("video_id", "start", "end", "role", "verdict", "outcome",
  87 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  88 | index fc96df7..db852b6 100644
  89 | --- a/pipeline/package_pin.py
  90 | +++ b/pipeline/package_pin.py
  91 | @@ -146,7 +146,8 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
  92 |                                                             # retired by ruling 56: kept so its pins still recompute)
  93 |                  "scorer_verdict",                          # ruling 56: the clip scorer's affirmation, only when sealed
  94 |                  "attested",                                # ruling 67: the attested-text re-seal's record (re-sealed)
  95 | -                "visual")                                  # ruling 70: the clip's visual record (flags, sheet sha)
  96 | +                "visual",                                  # ruling 70: the clip's visual record (flags, sheet sha)
  97 | +                "relisten")                                # ruling 103: the targeted re-listen's two short readings
  98 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
  99 |                                                             # separate constant (a test holds them equal): the
 100 |                                                             # integrator's check_pin_only imports this module, which
 101 | @@ -439,7 +440,8 @@ def to_pin(pk, run_name):
 102 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 103 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 104 |                       **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual",
 105 | -                                          "attested")      # rulings 68 / 72: an adopted spoken text, sealed
 106 | +                                          "attested",      # rulings 68 / 72: an adopted spoken text, sealed
 107 | +                                          "relisten")      # ruling 103: only when a re-listen ran, sealed
 108 |                          if k in s},
 109 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 110 |      edl_vo = {"intro": pk["vo"]["intro"],
 111 | diff --git a/pipeline/test_canon.py b/pipeline/test_canon.py
 112 | index 2ed80aa..1ea065c 100644
 113 | --- a/pipeline/test_canon.py
 114 | +++ b/pipeline/test_canon.py
 115 | @@ -264,5 +264,36 @@ class TestSites(unittest.TestCase):
 116 |          self.assertFalse(missing, missing)
 117 |  
 118 |  
 119 | +class TestRetirementPlans(unittest.TestCase):
 120 | +    """L-k (a different number never compares equal), the 2026-11-14 pre-check finding on 7BqLu-wzbU0: a US
 121 | +    retirement plan is a NAME. '401k' read as 401000 made 'a 401k' equal 'a 401,000'; '401(k)' read as 401 + 'k'
 122 | +    made the plan's two spellings differ. Both spellings are now one token; a '$' keeps an amount an amount."""
 123 | +
 124 | +    def test_a_plan_is_never_the_number(self):
 125 | +        for plan, amount in (("a 401k", "a 401,000"), ("a 401k", "a 401 thousand"), ("a 401(k)", "a 401,000"),
 126 | +                             ("my 403(b)", "my 403 billion"), ("a 457b", "a 457,000,000,000")):
 127 | +            self.assertFalse(C.same(plan, amount), (plan, amount))
 128 | +
 129 | +    def test_the_plans_spellings_are_one_name(self):
 130 | +        for a, b in (("I don't have a 401k.", "I don't have a 401(k)."), ("a 401K", "a 401(k)"),
 131 | +                     ("my 403b", "my 403(b)"), ("a 457(b) plan", "a 457b plan")):
 132 | +            self.assertTrue(C.same(a, b), (a, b))
 133 | +        self.assertEqual(C.canon_tokens("I don't have a 401(k)"), ["i", "don't", "have", "a", "401k"])
 134 | +
 135 | +    def test_the_pre_check_case_still_differs(self):
 136 | +        self.assertFalse(C.same("I don't have a 401k", "I don't have a 401 ,"))     # the second recogniser's reading
 137 | +
 138 | +    def test_amounts_are_unchanged(self):
 139 | +        self.assertEqual(C.canon_tokens("$401k"), ["401000", "dollars"])           # a '$' keeps it an amount
 140 | +        self.assertEqual(C.canon_tokens("40k"), ["40000"])
 141 | +        self.assertTrue(C.same("74k", "seventy four thousand"))
 142 | +        self.assertEqual(C.canon_tokens("401,000"), ["401000"])
 143 | +        self.assertEqual(C.canon_tokens("401 kilos"), ["401", "kilos"])           # only the single letter joins
 144 | +
 145 | +    def test_the_split_form_spans_both_words(self):
 146 | +        spans = C.canon_spans(["a", "401", "k", "plan"])
 147 | +        self.assertIn(("401k", 1, 2), [tuple(s) for s in spans])
 148 | +
 149 | +
 150 |  if __name__ == "__main__":
 151 |      unittest.main()
 152 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 153 | index 299098c..1c8a870 100644
 154 | --- a/tests/package/test_lock_precheck.py
 155 | +++ b/tests/package/test_lock_precheck.py
 156 | @@ -58,7 +58,7 @@ class TestRequest(Dirs):
 157 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 158 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 159 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 160 | -                         "DcUbBkyeh9M.216.054-228.674.c705b20ed800.json")             # ruling 90's decoder
 161 | +                         "DcUbBkyeh9M.216.054-228.674.d1e155c642a6.json")             # ruling 103's decoder
 162 |  
 163 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 164 |          segs = LP.segments_of([HOOK, CLIP])
 165 | @@ -133,7 +133,8 @@ class TestRuling84(unittest.TestCase):
 166 |      s = LP.segments_of([BREEDLOVE])[0]
 167 |  
 168 |      def test_the_rules_string_is_the_integrators(self):
 169 | -        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84")
 170 | +        """RULING 103 (14:12 Nov 14) joined the integrator's rules string (its message of 14:3x Nov 14)."""
 171 | +        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103")
 172 |  
 173 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 174 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 175 | @@ -180,7 +181,7 @@ class TestCheck(Dirs):
 176 |              self.put(s, entry(s))
 177 |          rep, sleeps = self.run_check([HOOK, CLIP])
 178 |          self.assertEqual((rep["ok"], rep["request_id"], sleeps, os.path.exists(self.req)), (True, None, [], False))
 179 | -        self.assertEqual(rep["segments"][0]["entry"]["file"], "DcUbBkyeh9M.216.054-228.674.c705b20ed800.json")
 180 | +        self.assertEqual(rep["segments"][0]["entry"]["file"], f"DcUbBkyeh9M.216.054-228.674.{LP.DECODER}.json")
 181 |  
 182 |      def test_a_missing_answer_asks_the_whole_line_up_and_waits_for_its_own(self):
 183 |          segs = LP.segments_of([HOOK, CLIP])
 184 | @@ -204,15 +205,16 @@ class TestCheck(Dirs):
 185 |  
 186 |      def test_an_answer_in_the_old_decoders_file_is_never_read(self):
 187 |          """Audit 1845 C2 (glm): ruling 73 changed the decoder, ruling 84 changed it again, and ruling 90 (the
 188 | -        integrator's spotlight branches) again; a file named for an older decoder (25cd6f15e6c9, 8a101f222598,
 189 | -        962353613cb0) is never opened, even with a matching, newer entry under the current rules."""
 190 | +        integrator's spotlight branches) again, and ruling 103 with the canon-401k fix again (14:3x Nov 14); a file
 191 | +        named for an older decoder (25cd6f15e6c9, 8a101f222598, 962353613cb0, c705b20ed800) is never opened, even
 192 | +        with a matching, newer entry under the current rules."""
 193 |          s = LP.segments_of([HOOK])[0]
 194 | -        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0"):
 195 | +        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0", "c705b20ed800"):
 196 |              old = LP.result_file(s, self.res, decoder=dec)
 197 |              with open(old, "w") as f:
 198 |                  json.dump([entry(s, "no_difference", at="2026-11-14T02:00:00Z")], f)
 199 |              self.assertTrue(old.endswith(f".{dec}.json"))
 200 | -        self.assertIsNone(LP.answer(s, self.res))                                         # only c705b20ed800's file
 201 | +        self.assertIsNone(LP.answer(s, self.res))                                         # only LP.DECODER's file
 202 |  
 203 |      def test_ruling_73_holds_a_span_the_render_cannot_cut(self):
 204 |          segs = LP.segments_of([HOOK, CLIP])
 205 | diff --git a/tests/package/test_ruling_103.py b/tests/package/test_ruling_103.py
 206 | new file mode 100644
 207 | index 0000000..10eaad6
 208 | --- /dev/null
 209 | +++ b/tests/package/test_ruling_103.py
 210 | @@ -0,0 +1,93 @@
 211 | +#!/usr/bin/env python3
 212 | +"""RULING 103 (orchestrator 14:12 ET Nov 14), the builder's side, landed with the integrator's canon-401k fix (one
 213 | +decoder-sha move): the pre-check's rules and decoder; the targeted re-listen's record ("Record both short readings on
 214 | +the pin") carried from the pre-check entry onto the segment as it stands and sealed (package_pin.SEALED_LATER), only when
 215 | +a re-listen ran, so every pin without one seals as before; canon's '401k' is a plan's name (pipeline/test_canon.py, the
 216 | +integrator's tests, byte-identical). Offline: temporary requests and results directories."""
 217 | +import copy
 218 | +import json
 219 | +import os
 220 | +import sys
 221 | +import unittest
 222 | +
 223 | +HERE = os.path.dirname(os.path.abspath(__file__))
 224 | +REPO = os.path.dirname(os.path.dirname(HERE))
 225 | +for _p in ("pipeline", "tests/package"):
 226 | +    sys.path.insert(0, os.path.join(REPO, _p))
 227 | +import canon as C  # noqa: E402
 228 | +import lock_precheck as LP  # noqa: E402
 229 | +import package_pin  # noqa: E402
 230 | +import test_angles as TA  # noqa: E402
 231 | +from test_lock_precheck import CLIP, HOOK, Dirs, entry  # noqa: E402
 232 | +
 233 | +RELISTEN = {"token": "401k", "against": "", "window": [14.84, 18.38], "source_window": [14.84, 18.38],
 234 | +            "decoder_reading": "IRA. I don't have a 401k. I don't own a single",
 235 | +            "second_reading": "Roth IRA. I don't have a 401k. I don't own a single", "verdict": "pass",
 236 | +            "scribe_usd": 0.0007}
 237 | +
 238 | +
 239 | +class TestTheRules(Dirs):
 240 | +    def test_an_entry_under_the_rules_before_103_is_never_read(self):
 241 | +        s = LP.segments_of([HOOK])[0]
 242 | +        self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84", at="2026-11-14T19:00:00Z"))
 243 | +        self.assertIsNone(LP.answer(s, self.res))
 244 | +        self.put(s, entry(s, at="2026-11-14T19:01:00Z"))                     # the same answer under ruling 103's rules
 245 | +        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")
 246 | +
 247 | +
 248 | +class TestTheRecordReachesTheSeal(Dirs):
 249 | +    def check(self, relisten):
 250 | +        segs = LP.segments_of([HOOK, CLIP])
 251 | +        self.put(segs[0], entry(segs[0], relisten=relisten))
 252 | +        self.put(segs[1], entry(segs[1], relisten=None))
 253 | +        return LP.check([HOOK, CLIP], "r", self.req, self.res, log=lambda m: None)
 254 | +
 255 | +    def pk(self):
 256 | +        return {"segments": [{"video_id": m["video_id"], "start": m["start"], "end": m["end"], "text": m["text"]}
 257 | +                             for m in (HOOK, CLIP)], "lines": [], "hook_first_words": ""}
 258 | +
 259 | +    def test_a_relisten_record_is_carried_as_it_stands_and_only_when_one_ran(self):
 260 | +        pre = self.check(copy.deepcopy(RELISTEN))
 261 | +        self.assertTrue(pre["ok"])
 262 | +        self.assertEqual([r["relisten"] for r in pre["segments"]], [RELISTEN, None])
 263 | +        pk = LP.apply(self.pk(), pre)
 264 | +        self.assertEqual(pk["segments"][0]["relisten"], RELISTEN)                 # as it stands,
 265 | +        self.assertIsNot(pk["segments"][0]["relisten"], pre["segments"][0]["relisten"])   # a copy (glm C1)
 266 | +        self.assertNotIn("relisten", pk["segments"][1])                           # null: no key
 267 | +        for odd in ("pass", ["401k"], 7):                                           # not an object: no record
 268 | +            self.tmp.cleanup()
 269 | +            self.setUp()
 270 | +            pre = self.check(odd)
 271 | +            self.assertIsNone(pre["segments"][0]["relisten"], odd)                 # the row's contract: None
 272 | +            pk = LP.apply(self.pk(), pre)
 273 | +            self.assertNotIn("relisten", pk["segments"][0], odd)
 274 | +
 275 | +    def test_the_record_is_sealed_and_a_pin_without_one_seals_as_before(self):
 276 | +        base = TA.TestPinAndTruth.pk(None)
 277 | +        plain = package_pin.to_pin(copy.deepcopy(base), "r")
 278 | +        self.assertNotIn("relisten", plain["segments"][0])
 279 | +        with_r = copy.deepcopy(base)
 280 | +        with_r["segments"][0]["relisten"] = copy.deepcopy(RELISTEN)
 281 | +        pin = package_pin.to_pin(with_r, "r")
 282 | +        self.assertEqual(pin["segments"][0]["relisten"], RELISTEN)
 283 | +        sha = pin["moments_package"]["package_sha256"]
 284 | +        self.assertEqual(package_pin.pin_seal(pin), sha)                           # the integrator's recompute
 285 | +        self.assertNotEqual(sha, plain["moments_package"]["package_sha256"])      # the record is inside the seal
 286 | +        tampered = copy.deepcopy(pin)
 287 | +        tampered["segments"][0]["relisten"]["second_reading"] = "Roth IRA. I don't have a 401. I don't own a single"
 288 | +        self.assertNotEqual(package_pin.pin_seal(tampered), sha)
 289 | +        self.assertEqual(package_pin.pin_seal(plain), plain["moments_package"]["package_sha256"])
 290 | +
 291 | +
 292 | +class TestCanonOnThisSide(unittest.TestCase):
 293 | +    """The integrator's canon fix, taken byte-identical (its own tests: pipeline/test_canon.py TestRetirementPlans):
 294 | +    this side's step-A and attest code read the same canonical tokens as the render's lock."""
 295 | +
 296 | +    def test_the_plan_is_a_name_here_too(self):
 297 | +        self.assertFalse(C.same("a 401k", "a 401,000"))
 298 | +        self.assertTrue(C.same("I don't have a 401k.", "I don't have a 401(k)."))
 299 | +        self.assertFalse(C.same("I don't have a 401k", "I don't have a 401 ,"))     # Blockware's hold stands
 300 | +
 301 | +
 302 | +if __name__ == "__main__":
 303 | +    unittest.main()
 304 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- Before a line-up is written and before its pin is sealed, the builder asks the integrator's service to run the
  render's own lock on each segment (the "lock pre-check", pipeline/lock_precheck.py, rulings 68 / 72).
  - Requests go to this worktree's lock_requests dir. Answers are list-of-entry files named
    <video>.<start>-<end>.<DECODER>.json in the integrator's results dir (read only here).
  - An entry is read only when its "rules" string equals RULES and its file is named for DECODER: an answer under any
    other rules or decoder is not valid for the render's code.
- A pin (package_pin.to_pin) seals a sha256 over the gated bytes. Per segment: video, start, end, text, transcript sha,
  plus each SEALED_LATER field the segment carries, so a field enters the body only when present.
  - The integrator's check imports THIS worktree's package_pin.py and recomputes every pin's seal (pin_seal).
  - Every pin already delivered must recompute unchanged.
- canon.py is the one canonical text form both sides compare with (law L-k: a different number never compares equal).
  This worktree's copy was byte-identical to the render's.

THE ORCHESTRATOR'S RULING (14:12 ET Nov 14), verbatim:
"RULING 103, THE TARGETED RE-LISTEN (for a hold where the two independent readings differ on ONE number or name token,
as '401k' against '401' on Blockware 06d34e15). The hold stands as the default: a number or name disagreement is never
waved through. But one long-span reading against another is weak evidence about one token. Before the hold is final,
BOTH recognisers are asked again on a SHORT window cut around that token alone (the token's word times, 1.5 s either
side, the same audio the cut will use). The lock passes on that token only if BOTH short-window readings give the
lock's token (after the canon, with the 401k fix: a plan's name is not the number 401000). If either short reading still
differs, or the two differ from each other, the hold is final and the clip may only be saved by a variant that leaves
the token out. Record both short readings on the pin. Scribe's cost for 4 s is nothing; say it.
ORDER OF WORK: ... (2) with the integrator, land the canon-401k fix and ruling 103 together so the decoder sha moves
once ..."

THE INTEGRATOR'S SIDE (its messages of 14:2x-14:3x ET Nov 14; facts, not in this diff):
- Branch canon-401k 077407dc = 373d0fed (canon: '401k' / '401(k)' / 403(b) / 457(b) are one NAME token, never 401000;
  a '$' keeps an amount an amount) + ruling 103 in the render's adjudicate_lock. Audited batches 79 and 80, two cycles
  each, clean.
- The final decoder_sha is d1e155c642a6aaacd578ac5ad2f47c9cd1d71594c9913dc4f0f231fd6b2258ce. RULES becomes
  "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103"; entries under the old RULES are never reused.
- The relisten record sits on each result entry, key "relisten", ONE per segment (a span decides at most one token).
  - It is null when no re-listen ran. Otherwise it is an object {token, against, window [f, f], source_window [f, f],
    decoder_reading, second_reading, verdict "pass" | "hold", scribe_usd}, or the edge form
    {token, against, verdict "hold", why}.
  - Only outcome "hold" or a passing lock carries a non-null record. relisten.verdict is the re-listen's own verdict,
    never an outcome.
- Ruling 103 added and renamed NO outcome. The set is "decoded", "no_difference", "adopted", "two_readings",
  "adopt_spoken", "hold", "error".
  - "decoded" is only for a decode-only request without approved_text. The builder's requests always carry it, and
    its decide() fails closed on "decoded", as it should.
  - A re-listen pass keeps the normal outcome (no_difference / adopted / two_readings), with spoken_text null.
- Landing: the builder commits this change and says READY with no build running. The integrator merges to main and
  pushes. Only then does the builder push, so no pre-check of the builder's waits on a sha it cannot read.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- lock_precheck.decide(): PASS = {"no_difference", "adopted", "two_readings"} passes; "adopt_spoken" adopts only after
  this side's own class_84 check; "hold" holds; anything else (including "decoded" and "error") is no verdict, never a
  pass.
- lock_precheck._matches(): rules == RULES, the window equals the segment's [start, end], and role, approved_text and the
  trim fields are equal.
- package_pin.seal() / pin_seal(): unchanged; body_of() adds `{k: s[k] for k in SEALED_LATER if k in s}`.

THE CHANGE (the diff follows):
1. lock_precheck.py:
   - RULES and DECODER updated (with the full sha in the history comment).
   - relisten_of(e): the entry's "relisten" when it is an object, else None.
   - check() puts it on each row ("relisten").
   - apply() copies a row's object record onto the package segment ("relisten") as it stands. Absent otherwise.
2. package_pin.py: SEALED_LATER gains "relisten", and to_pin carries "relisten" from the segment when present.
3. canon.py and test_canon.py: the integrator's fixed files, byte-identical (git show 077407dc:pipeline/canon.py). This
   side's copies were byte-identical to theirs before the fix.
4. Tests:
   - test_ruling_103.py (new, 5):
     - an entry under the old RULES is never read;
     - the record is carried as it stands, only when one ran;
     - a non-object is never carried, in the row or on the segment;
     - the record is inside the seal and pin_seal recomputes it, and a tampered reading changes the seal;
     - a pin without a record seals as before;
     - canon's plan-name cases on this side.
   - test_lock_precheck.py: its decoder literals and old-decoder list updated (c705b20ed800 joins the never-read list).
   - 8 mutations, each killed.
   - pipeline/test_canon.py TestSites::test_no_ad_hoc_normaliser_outside_canon already fails at HEAD (pipeline/
     speakers.py's own normalisers), before and after this change; it is not in this change's scope.

ATTACK:
(a) Can any answer under the old decoder or the old RULES still be read? Can a valid new answer be missed (a pass read
    as no verdict)?
(b) The relisten record: can a non-null record reach a pin that the render would refuse, or a null or odd one reach
    it? Is it sealed as it stands (no re-shaping)? Can a pin delivered before this change fail its recompute?
(c) canon: does the fix change any comparison the builder's own gates make, beyond '401k'-class plan names (an amount
    with '$', '40k', '401 kilos')?
(d) The landing order: can a build of the builder's run while the decoder it reads is not the one the service serves?
(e) Anything else that could seal a wrong pin or block every pre-check.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
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
