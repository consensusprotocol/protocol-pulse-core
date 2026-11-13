# glm-5.3-flash (z-ai/glm-5.3-flash) 31 s finish=stop usage in 19900 / out 1860 usd~0.088 (upper-bound price)

# pp-selectid — CYCLE 2 FINAL REVIEW

## 1. What they caught that I missed

- **Grok's (a)–(e) verification matrix** — I did not systematically walk each tamper case against the exact error strings; their confirmation that every branch has a named test is more thorough than my Cycle 1 pass.
- **Qwen's layered-defense observation** on `window_source` (the redundancy between `still_unpunctuated is not False` and `E.sentence_ready`) — I treated the checks as a flat list, not as defense-in-depth.
- **The integrator's out-of-band answer** (render path never looks up the pin's record by sha; it decodes its own window and token-ratio-checks approved_text, failing closed) — this resolves the residual question I had about whether the pin needs the window record's provenance. It does not; I under-weighted that.

## 2. Agree / disagree

- **K1 (coverage measured, glm P0-2 / qwen P1): AGREE, resolved.** `caption_parts` (context_integrity.py:43-46) now checks `first <= t0 - before or first <= EDGE_TOL_S` and `last >= t1 + after or last >= dur - EDGE_TOL_S`, returning (None, None) on shortfall — fail-closed, and `covered` (lines 53-54) returns the achieved span, not the requested one. Test at test_ledger_build.py:597-611 exercises all three shortfall branches. This was the strongest Cycle 1 finding and it is correctly implemented.
- **K2 (ambiguous sha match, glm P0-1): AGREE, resolved.** `caption_source` (ledger_build.py:268-269) now fails closed on >1 match, with the matching names in the why. Test at 613-621. Correct disposition — ambiguity → no context, not "first sorted wins".
- **glm P2-10 (word starting exactly at t1 dropped): AGREE, resolved.** `post` now uses `t1 <= a` (line 48), so a word starting exactly at the selection's end is included.
- **glm P2-2 (StopIteration on empty selection): AGREE, resolved.** `context_around` line 65-67 guards `i is None`.
- **Grok's "no P0/P1/P2, SHIP yes": PARTIALLY AGREE.** I agree there are no P0s. I disagree that there is nothing: I have residual P1/P2 findings below.

## 3. New findings (this review)

**N1 (P1). `caption_parts` coverage check ignores the `pre`/`post` lists' actual content — the coverage check and the word selection can disagree.** context_integrity.py:43-48. The coverage gate uses `first`/`last` (the caption record's global first/last word times), but the *text* delivered is `pre`/`post` filtered by the window predicates. Scenario: the caption record's first word is at 0 s (passes `first <= t0 - 90`), but there is a dead stretch (music) from `t0-90` to `t0-30`. The gate passes, yet `pre` contains only words from `t0-30` — the judged context is 30 s, not 90 s, and nothing records it. The Cycle 1 consensus (K1) claimed "the coverage is MEASURED", but what is measured is the record's *extent*, not the *density* of words in the window. Whether this violates L-s depends on whether "judged from >= 90 s before" means the record reaches that far or words exist there; the law's wording ("judged inside its source's transcript from >= 90 s before") reads as the former, so this is arguably compliant — but the achieved-coverage report (`covered`) will still show ~30 s of actual words, and no test exercises a gapped caption. Flag as P1-conditional: compliant under the extent reading, untested under the density reading.

**N2 (P2). `caption_source` reads the *whole* full-video record into memory and tokenizes it for every window video, and its `found` scan silently swallows per-file errors.** ledger_build.py:256-265. A corrupt *second* transcript file (e.g. `transcript.whisper_words.json` unreadable) is skipped with `continue` — if the good one also matches, fine; but if the *only* matching record is the corrupt one, the why is "no record in the store matches the row's transcript_sha256", which is misleading (the record exists; it is unreadable). L-j says failures are counted, not silent; here the failure mode is conflated. Minor, but the why string is wrong in that case.

**N3 (P2). `window_source`'s `file_head` is `w0 == 0.0` exactly (ledger_build.py:237).** A window starting at 0.001 s (3-decimal rounding, the very thing WINDOW_TOL_S exists for) yields `file_head=False`. Consistency: the span check tolerates 0.01 s; the file_head check does not. Cosmetic-to-minor; affects only whatever downstream logic keys on file_head.

**N4 (P2). `build_inputs` window path: `report["window_records"][vid]` is written even when the video's rows all subsequently fail to re-anchor** (ledger_build.py:336) — the report says a window record was "used" when no moment came of it. The comment at line 341 acknowledges this for the full-video path ("whether a moment came of it: moments") but the window path's report entry is unconditional. Reporting-accuracy only.

**N5 (P2, uncertain). `caption_parts`'s `covered` when `pre`/`post` are empty** (context_integrity.py:53-54) falls back to `(t0, t1)` — the selection's own bounds. If the caption has words before but none after (and the end-edge check passed via `duration`), `covered[1]` reports `t1`, not the last caption word's end. The caller cannot distinguish "context reached t1+60" from "no post-words at all" from `covered` alone. Untested; low impact since the exclusion prompt still carries whatever exists.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| window_source claim checks | pass | pass | Grok's tamper matrix confirms; no change |
| caption coverage (L-s) | conditional pass | pass w/ N1 caveat | K1 implemented; density-vs-extent ambiguity remains (N1) |
| caption_source uniqueness | conditional | pass | K2 fail-closed ambiguity, tested |
| full-video path (d) | pass | pass | `context_around`/`_window_text` route only when `src.window` is set; unchanged otherwise |
| tests | pass | pass | Each named defect has a failing case; N1's gapped-caption case is the one gap |

## 5. Final priority list

- **P0:** none.
- **P1:** N1 — context_integrity.py:43-48: coverage gate checks the record's extent, not word density; a gapped caption yields <90 s of judged context that passes. Add a test with a dead stretch inside [t0-90, t0] and either fail closed or report the achieved density.
- **P2:** N2 (ledger_build.py:256-267, misleading why when the matching record is unreadable); N3 (ledger_build.py:237, `w0 == 0.0` exactness vs WINDOW_TOL_S); N4 (ledger_build.py:336, window_records report unconditional); N5 (context_integrity.py:53-54, `covered` fallback).

## 6. Single highest-leverage change

Make the L-s coverage check measure the words actually delivered in the window (or at least test a gapped caption), since "the coverage is MEASURED, never assumed" is the cycle's central claim and it is currently only half true.

## 7. Production ready?

**Yes with conditions:** (1) add the gapped-caption test and either enforce or report achieved word density (N1); (2) fix the unreadable-record why in `caption_source` (N2). The P2s may ship as-is.

SHIP: yes with conditions