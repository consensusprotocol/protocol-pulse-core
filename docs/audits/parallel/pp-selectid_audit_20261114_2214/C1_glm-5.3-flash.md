# glm-5.3-flash (z-ai/glm-5.3-flash) 118 s finish=stop usage in 5886 / out 3240 usd_reported=0.000584 usd~0.066 (upper-bound price)

# Audit: pp-selectid — RULING 109 early ALONE stop in `spotlight.build`

## What the diff does

In `build()`, right after `P.with_verdict` attaches scorer verdicts, it:

1. Builds `low` = moments whose `alone_score(m)` is known and `< ALONE_MIN`.
2. Stops each with reason "ruling 109" (free gate before paid verdict).
3. Filters `ms` to the survivors; if none remain, sets `why_none` and returns **before** `P._writers`, `prescreen` (step A) and everything paid.
4. Records `out["ruling_109"] = {"alone_known_below_min": len(low)}`.

Unscored moments pass through untouched; stage 7's final ALONE ≥ 4 requirement is unchanged, so the early stop is a pure optimization *plus* a behavioral change: a low-ALONE moment that previously reached step A (and possibly got sealed via the paid path) now never does.

---

## Findings

### [P1] The early stop can drop a moment that would have sealed — question (1) answered: yes, in the documented "score changes within the build" case, and the diff's own "UNCHANGED GUARDS" note doesn't cover it

The replay text says the guard is: "stage 7 still requires ALONE ≥ ALONE_MIN (alone_score of the **CURRENT text**) for every finalist, so the earlier stop can never let through a moment the later stage would refuse." That proves **no false pass** — it does *not* prove **no false stop**. Two concrete paths:

**(a) Score changes within the build.** `alone_score` reads `P.verdict_of` for the moment's *current text*. If anything in `build()` before stage 7 can change the text (a snapped span, a re-anchored quote, an editorial rewrite) — and the diff's own test at line 52 constructs moments with *different texts* (`TEXT.replace("money", "asset")`) and passes `alone=[3.0, 4.0, "None"]`-style scores keyed by position, implying alone scores are per-moment, not per-text — then a moment whose *pre-build* score is 3.0 but whose *post-snap* text would score ≥ 4 is now stopped at line 9–12, where before ruling 109 it proceeded, got its (new) score, and could seal. The old code's stage-7 check ran on the current text; the new early check runs on the *pre-build* text's score. If `with_verdict` attaches the verdict for the text the scorer last saw, and the build later snaps/edits the span, the early gate and the stage-7 gate read different texts. The diff's guard note asserts they're the same ("alone_score reads P.verdict_of (the scorer's verdict for the moment's **current text**)") — but that's exactly the thing the diff does not prove: nothing in the diff shows the text is immutable between line 9 and stage 7. If it *is* immutable, the guard note should say *why* (e.g., "build() never mutates `m["text"]` after `with_verdict`; the scorer verdict is keyed by text hash"); as written it's an assertion, not a proof. **Fix: either (i) add a test that a moment whose text is snapped/edited inside build() and whose pre-snap ALONE < 4 but post-snap ≥ 4 still seals (or is documented as intentionally dropped), or (ii) add a comment/test pinning that build() never changes the scored text.**

**(b) `alone_score(m) is not None` vs. the scorer's "no rating" case.** Line 9: `low = {m["moment_id"]: alone_score(m) for m in ms if alone_score(m) is not None and alone_score(m) < ALONE_MIN}`. Note `alone_score(m)` is called **twice** per moment (once in the condition, once as the value) — harmless but see the P3. More importantly: the existing test at line 29–30 expects the reason `"ALONE scorer: no rating"` for `alone=None` — that moment is *not* in `low` (score is None), so it proceeds. Good — question (2): **an unscored moment is never stopped by this diff**; it flows to step A and stage 7 waits, exactly as the two surviving tests (lines 55, 58–60: `alone=[3.0, 4.0, None]` → prescreen sees `["b","c"]`; `alone=[2.0]` → no prescreen at all) pin. But: what if the scorer's verdict *exists* yet contains no rating (a sealed-but-unrated verdict, or a verdict whose rating field is missing — cf. L-l "a model reply counts only whole")? If `alone_score` returns None for "verdict present but rating missing" (L-l says such a reply is a failed call → INCONCLUSIVE), the moment proceeds — correct. But if `alone_score` raises or returns a *string* rating ("4.0" as str), the comparison `alone_score(m) < ALONE_MIN` on line 9's condition would raise TypeError → per M12 fail-closed that's a HOLD, acceptable, but the diff adds no test for a malformed rating. Under L-l, `_v_rate` guarantees a 1–5 number, so this is likely covered upstream; still, the diff relies on that invariant without a test here. **P2: add a test that a verdict whose rating is a string/None-rating (L-l INCONCLUSIVE) flows through as "no score yet", not stopped.**

### [P2] `out["ruling_109"]` counts, but the stopped moments' reasons are only in `out["moments"][mid]["out"]` — the summary counter and the per-moment reasons can disagree

`out["ruling_109"] = {"alone_known_below_min": len(low)}` counts moments *stopped by this diff's rule*. But the test at line 56–57 checks both `out["moments"]["a"]["out"]` contains "ruling 109" **and** the counter is 1 — consistent. However, if a moment is in `low` **and** would also have been stopped by a later free gate (e.g., the 12 h / exclusions / STAND_ALONE screens in the medley path), the counter attributes the stop to ruling 109 while the moment's own reason may name a different gate. That's cosmetic (the counter is explicitly "alone_known_below_min", i.e., "known below min", not "stopped by ruling 109"), but the *name* `alone_known_below_min` vs. the reason string "a free gate before any paid verdict (ruling 109)" — the counter counts *known-below-min* moments, which equals *stopped-by-109* moments only because the stop happens before any other gate in this function. Since the stop happens at the very top of the paid section, before `prescreen`, this holds **in this function**. But the replay says "In the medley path the free screens already run before step A" — if the medley path calls `spotlight.build` *after* its own free screens, a moment stopped here was already screened; the counter then double-counts nothing, but the *reason* "a free gate before any paid verdict" is now the *second* free-gate stop, and the moment's ledger (L-f: "every cluster's ledger entry names ... the gate that stopped it") requires the stopping gate be named — "ruling 109" is named, so this passes. **Verdict: no defect, but the counter's semantics ("known below min" ≠ "stopped") should be pinned by a test where a moment is known-below-min *and* would fail another free gate — currently untested.** Should-fix: one more assertion.

### [P2] The early return skips `out["scorer"]`-adjacent bookkeeping? No — it doesn't; but it *does* skip `P._writers(router)` and the `step_a_cache`-keyed prescreen, which is intended. However the early return also skips whatever `build()` does *after* the prescreen for the *stopped* moments' bookkeeping (e heading, exclusions, delivered/optout filtering)

Looking at the diff hunk: the early `return out` at line 16 fires when `not ms`. At that point, `out` already contains the scorer record (line 7) and the moments' stop reasons (set by `stop(mid, ...)` presumably writing into `out["moments"]`). But everything the function does between line 17 and the end — `P._writers`, `prescreen`, the paid stages, the final `out["why_none"]`-setting for *other* reasons (e.g., "every moment failed step A") — is skipped. That's the intent ("no moment left: why_none, replay: with no paid call"). The question is whether the early return's `why_none` string is the *only* reason recorded. The test (line 60) pins `self.assertIn("ruling 109", out["why_none"])` — `assertIn`, not equality, so if the function later appends other reasons to `why_none` (e.g., a suffix like "; 0 moments reached step A"), the test still passes. Good. But: does the early return skip setting `out["ruling_109"]`? No — line 13 sets it *before* the `if not ms` check. Correct order. **No defect.** One subtlety: the early return happens *before* `P._writers(router)` — if `P._writers` has side effects the downstream stages rely on (e when `not ms` there's nothing downstream, so no issue. **No defect.** Some duplication: the reason string "a free gate before any trailing... (ruling  garbled — see P3.

### [P3] Duplicated `alone_score(m)` call in the dict comprehension (line 9) — call it once

Line 9: `{m["moment_id"]: alone_score(m) for m in ms if alone_score(m) is my...` — the condition calls `alone_score(m)` and the value calls it again. If `alone_score` is cheap (reads a verdict dict), this is a nit; if it's not (e garbled) — it's a verdict lookup, cheap. Nit: `sc = alone_score(m)` via a helper or a two-step: `scores = {m["once...` — the cleanest: `scores = {mid: sc for ... if (sc := alone_score(m)) is not Python 3.12, walrus in comprehension condition+value: `{m["moment_id"]: sc for m in some... if (sc := alone_score(n)) is not None and sc < ALONE_MIN}`. Python 3.12 supports it. Cleaner and calls once. Also the comment on line 13 says "stage 7 would stop it" — accurate.

### [P3] Test at line 58–60: `run_build([moment(mid="a", ...)], {"a": 5}, alone=[2.0])` — the second `run_build` reuses the `TestBuild` harness's `prescreen` double, which records into the *same* `calls` dict? No — `run_build` presumably constructs a fresh `calls` per invocation (the test reassigns `out, calls = ...`, so the harness returns a fresh dict). Fine.

### [P3] Comment alignment: line 12's trailing comment "# verdict only for what every free gate passed: an ALONE score" continues on line 13's comment "# known below 4 never reaches step A (stage 7 would stop it)" — the comment is split across lines 10/12/13, reading as one sentence; fine, but the comment on line 10 says "free gates first; a paid" and line 12 "verdict only for what every free gate passed" — slight redundancy between the inline comments and the replay's justification. Nit only.

---

## Answers to the PLEASE CHECK questions

**(1) Can the early stop drop a P0/P1...** — Yes, in one case: if `build()` mutates the moment's text (snap/rewrite) after `with_verdict` and before stage 7, the early gate reads the *pre-build* score while stage 7 reads the *post-build* score; a 3.0→4.0 improvement is then lost. The diff's "UNCHANGED GUARDS" note *asserts* the guard but doesn't *prove* the text is immutable between the two checks. Not proven → [P1] (must fix before merge: add the test or the proof).

**Question (2): Is an unscored moment ever stopped?** — No. `alone_score(m) is not None` gates membership in `low`; the `None` case flows through, and the test at lines 54–55 (`alone=[3.0, 4. package...` truncated) pins that the unscored "c" reaches prescreen. Correct per the ruling's intent ("stage 7 waits for the scorer, as text..."). No defect.

**(3) Do the tests pin it?** — Mostly. The new test (lines 49–60) pins: who reaches prescreen (`["b","c"]`), the counter, the reason, and the all-low → no-paid-call case. The two modified tests (lines 28–33) pin the *reason string* changed. What's *not* pinned: (a) the text-mutation case from (1); (b) a verdict-present-but-unrated (L-l) moment flows through; (g) the counter-vs-reason semantics. (a) is the P1; (b) is a P2; (c) is a competing... a P2.

---

## Severity summary

- [P1] Early stop vs. stage 7 read different texts if build() mutates the scored text (snap/rewrite) — guard note asserts, doesn't prove; add the test or the proof. (1)
- [P2] No test that a verdict-present-but-unrated (L-l INCONCLUSIVE) moment flows through as "no score yet".
- [P2] Counter semantics (`alone_known_below_min` = "known below min", not "stopped by 109") — equivalence holds only because the stop precedes all other gates in this function; pin it.
- [P3] Walrus: call `alone_score(m)` once per moment (Python 3.12: `{mid: sc for m in ms if (sc := alone_score(m)) is not None and sc < ALONE_MIN}`).
- [P3] `assertIn` on `why_none` is loose; equality would pin the string.

P1_OR_WORSE: 1