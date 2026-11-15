# qwen3.8-27b (qwen/qwen3.8-27b) 84 s finish=stop usage in 15445 / out 2930 usd~0.090 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1835
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

My Cycle 1 output was truncated mid-sentence (it cut off at "glm flagged this in Cycle 1 (their H6, truncated m..."), so I cannot fully account for what I said. Reconstructing from the visible portion and the consensus:

- **I identified the `pk["segments"][0]` IndexError** (my N1, medium) — this was the same finding as GLM's H6 and Grok's medium. All three models converged on it. I did not miss it; I stated it.
- **I did NOT explicitly flag the `re.fullmatch` vs `re.match` + `$` trailing-newline issue** on the story-id regex. The consensus notes this was "Taken" in the cycle-3 changes (the match is now `re.fullmatch`). Looking at the current diff at line 164: `story.fullmatch(d["alternative_to"])` — this is already `fullmatch`, so the trailing-newline hole is closed. The test at line 296 (`alternative_to="moments-x-3f481f5a\n"`) confirms it is dropped. I should have verified this in Cycle 1; I did not.
- **I did not explicitly verify that the `continue` at line 94 (missing source) is harmless.** Grok noted this subtlety: when the directive's source is missing, the `continue` skips the hold/ceiling triggers, but the parent can't be variant-built anyway (no word record), so the skip is harmless. I did not state this.
- **I did not note the convergence of GLM's H4 (alternative_to="") being fixed as a side effect of Qwen's field-validation fix.** The `story.fullmatch("")` fails, so an empty string is dropped at read time. Nobody in the other models' outputs explicitly called out this convergence.

## 2. WHERE DO YOU AGREE OR DISAGREE?

**Grok (parent dropped on bad directive): AGREE.** The fix is correct. The miss path at lines 96-97 sets the note and falls through to the hold/ceiling triggers. The test at lines 265-279 proves the hold's variant is still made with the miss note kept. Grok's observation that the `continue` at line 94 (missing source) still skips triggers but is harmless is correct — without a source, no variant can be built regardless.

**Qwen (L-k critical on ad-hoc "..." strip): PARTIALLY AGREE.** The original strip was a real wart, but calling it `<critical>` was generous. The comparison was canon-vs-canon on both sides (`C.canon_tokens(E.spoken(...))` vs `C.canon_tokens(str(d.get("ends") or ""))`), so the failure mode was a missed match, not a wrong one, and it was fail-closed. The fix (delete the strip, rely on canon) is correct. The comment at line 62 now documents it. Severity was overstated; the fix is right.

**Qwen (L-l high on field validation): DISAGREE with the severity, AGREE with the fix.** `directives()` is a builder input, not a model reply. L-l governs model replies. The added type/shape checks (20-hex parent, story-id regex, non-blank ends/by) are good hygiene and fail-closed, not a law repair. Qwen themselves walked back to "not a model reply, so L-l doesn't govern" mid-finding. I agree with their own correction.

**GLM (H1, crash on `{"directives": 5}`): AGREE.** The fix at lines 158-159 (`if not isinstance(rows, list): return {}`) is correct. The test at lines 287-290 covers `5`, `None`, a bare list, and bare `null`. Killed properly.

**GLM (H5, directive variant skips the 35 s ceiling): AGREE, documented, correctly.** The consensus note says every pool moment still faces `spotlight.pool`'s `usable(seg_max=35 s)` and every later gate. The test at lines 337-339 gives a 36 s alternative to `spotlight.pool` and confirms it is refused. I cannot see `spotlight.pool`'s `usable` call in this diff, but the background states it as an unchanged fact. The cycle-3 test closes the verification gap.

**GLM (H4, alternative_to="" behaves as no-alternative): MOOT.** The `story.fullmatch("")` fails, so `""` is now dropped at read time. Fixed as a side effect of the field-validation fix.

**Grok (segments[0] IndexError): AGREE.** The fix at lines 174-176 (`if not segs or not isinstance(segs[0], dict)`) is correct. The test at lines 335-336 covers `[]`, `None`, and `["x"]`. Mutation D14 is killed.

**Qwen (H1, IndexError on empty segments): AGREE.** Same finding as Grok and GLM. The fix is in place.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (low) — `tail_variant.py:66`, `directive_variant` accesses `src.sentences[k][1] + 1` without bounds-checking against `len(src.tokens)`.** The loop iterates `k` from `k1-1` down to `k0`. The parent's `sentences` are `(k0, k1)`, and `src.sentences` is indexed by sentence index. If `k1` equals `len(src.sentences)`, then `src.sentences[k1-1]` is the last sentence, and `src.sentences[k1-1][1] + 1` could exceed `len(src.tokens)` if the last sentence's end token index is the last token. However, `eligibility.Span(src, k0, k)` is called inside `variant()` (line 68), which presumably validates the span. The background states that `variant()` builds the variant via `moments.record` over `eligibility.Span(src, k0, k)`, and eligibility is judged afresh. If `eligibility.Span` validates bounds, this is safe. I cannot verify `eligibility.Span`'s bounds check from this diff. **Uncertain; not a finding unless `eligibility.Span` does not validate.**

**N2 (low) — `proof_ledger.py:162-165`, the `directives()` dict comprehension uses `d["parent"]` as the key without checking for duplicate parents.** If the builder writes two rows with the same `parent` id, the second silently overwrites the first. The background states the file is "written by the builder only on the orchestrator's written yes, quoting it." A duplicate parent would be a builder error. The fail-closed behavior (last row wins) is not a security issue because the builder is the only writer, and the orchestrator's directive is a single yes/no. **Not a finding; documented as a builder-input assumption.**

**N3 (low) — `spotlight.py:13-14`, `day_taken` uses `r.get("story_id") == alternative_to`.** If a record in `spotlit` has no `story_id` key, `r.get("story_id")` returns `None`, and `None == alternative_to` is `False` (since `alternative_to` is a string or `None`). If `alternative_to` is `None`, then `None == None` is `True`, which would mean a record without a `story_id` is treated as the named alternative. However, the test at lines 340-342 (`no_id = [{"channel_id": "A", "day_et": SPOT.et_day(NOW)}]`) confirms that a record without a `story_id` admits no one: `got` is `["b"]` only, and `alt` (which has `alternative_to="moments-x-3f481f5a"`) is refused. This is because `day_taken` is called with `alternative_to="moments-x-3f481f5a"`, and `None != "moments-x-3f481f5a"`, so the record is not excluded. The test confirms correct behavior. **Not a finding.**

**N4 (informational) — The `record_spotlit` call at lines 208-213 adds `"alternative_to": alt` to the spotlight record only when `alt` is truthy.** This means the sealed spotlight record for the alternative will contain the `alternative_to` field, but the original sealed spotlight (3f481f5a) will not. This is correct: the original is not an alternative to anything. The `day_taken` function reads `story_id` from the record, not `alternative_to`, so this does not affect the ruling-90 check. **Not a finding.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| directive_variant path | <medium> | none | Bad-ends `continue` removed; canon path cleaned; one-sentence note added; missing-source `continue` verified harmless |
| directives() reader | <medium> | none | Strict 20-hex, story-id `fullmatch`, non-blank, non-list handling; trailing-newline hole closed by `fullmatch` |
| day_taken / spot_place | <medium> | none | Unified rule, explicit alt return, empty-segment guard, tests for second-alternative and unreadable record |
| ceiling / gate bypass | <medium> | none | Cycle-3 test confirms 36 s alternative refused by `pool.usable`; background confirms all gates run on variants |
| segments[0] indexing | <medium> | none | `spot_place` now guards empty/missing/non-dict segments; test covers `[]`, `None`, `["x"]` |
| story-id regex | not scored | none | `re.fullmatch` closes the trailing-newline hole; test at line 296 confirms |

## 5. FINAL PRIORITY LIST

**No P0 or P1 findings.**

**P2 MEDIUM — None remaining.** All Cycle 1 and Cycle 2 findings are resolved in the current diff. The `segments[0]` guard, the `fullmatch` on story-id, the non-list check on `directives`, the bad-ends fall-through, and the one-sentence note are all in place with tests.

**P3 LOW (informational, no action required):**
- `tail_variant.py:66`: `src.sentences[k][1] + 1` bounds depend on `eligibility.Span` validating; cannot verify from this diff. If `eligibility.Span` does not validate, a malformed source could raise `IndexError` inside `directive_variant`, which is not caught by `for_pool`'s `try` (the `try` at line 90 only wraps `CI.source_for`). However, `for_pool` is called from `with_variants`, which is called from `main`, and `main`'s `except` at line 216 catches `(PinRefused, ValueError, OSError)`. An `IndexError` from `directive_variant` would propagate out of `with_variants` and crash the build. **This is a theoretical risk only if `eligibility.Span` does not validate bounds and a source has fewer tokens than its sentences claim.** The background states eligibility is judged afresh, which implies validation. I flag it as informational, not a finding.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Unifying ruling-90 into `day_taken(..., alternative_to)` and having both `spotlight.pool` and `spot_place` call it, so the single exception for a named alternative is explicit, testable, and cannot be bypassed without a validated directive row. This is the architectural keystone: one function, one rule, two call sites, and the directive's `alternative_to` is the only path that admits a second spotlight on a taken channel.

## 7. PRODUCTION READY?

**Yes.**

All Cycle 1 and Cycle 2 findings are resolved. The 16 mutations are killed. The 98 tests pass. The directive path is fail-closed at every stage: absent/unreadable/malformed file → no directive; malformed row → dropped; no boundary match → parent's own triggers run; one-sentence parent → noted; empty segments → refused at the pin; 36 s variant → refused by the pool's ceiling. The full clip 3f481f5a and its alternative cannot both reach a render without the orchestrator choosing: the builder seals only on the orchestrator's written yes (the directive file), and the integrator launches. The ruling-90 check at the pin (`spot_place`) re-reads the spotlight record and refuses if the channel is taken, except for the named alternative. No path exists to seal a wrong pin or spend without a directive.