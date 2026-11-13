# glm-5.3-flash (z-ai/glm-5.3-flash) 95 s finish=stop usage in 5294 / out 2464 usd~0.053 (upper-bound price)

# Audit: pp-selectid-0335 — T9 retirement (ruling 35)

## Scope of what I can verify
The diff touches exactly two files: `pipeline/eligibility.py` (the `_span` function, lines 437–444 region) and `tests/eligibility/test_eligibility.py` (TestSpan, lines 258–265 region). Everything below is judged from the diff plus the stated context; where the diff doesn't show a file, I say so.

## What the diff actually does

**eligibility.py, hunk 1 (line 9–10):** comment-only change on the `MAX_WINDOW_SENTENCES = 3` line. The constant's value is unchanged. The added comment says "recorded only since ruling 35" and the test mirrors the constant against `editorial_select.py` — consistent with the stated intent that the constant stays.

**eligibility.py, hunk 2 (lines 18–22):** the `elif n > MAX_WINDOW_SENTENCES:` branch previously called `R("too_many_sentences", ...)`; now it appends a string to `targets`. From the diff I can see:
- `R(...)` presumably adds to a reasons collection (the test asserts `names()` no longer contains it), and `targets` presumably feeds `facts["targets_missed"]` (the test asserts `facts["targets_missed"]` contains the string). Both are inferred from the test, not shown in the diff — but the test is the contract, and it exercises exactly this.
- The new string is `f"{n} sentences > {MAX_WINDOW_SENTENCES} (T9, retired by ruling 35: the 20 s clip limit and the per-source limit govern length)"`.
- The `n == 0` → `R("no_content", ...)` branch is untouched and still a reason (test line 41 confirms `no_bitcoin` reasons still work; `no_content` itself isn't re-asserted in the diff, but the code line is unchanged).

**test change:** the 4-sentence fixture (`Span(four, 0, 3)`) now asserts (a) `too_many_sentences` NOT in `names()`, (b) a `targets_missed` entry starting `"4 sentences > 3 (T9, retired by ruling 35"`. The `assertTrue(any(...))` with a `facts` failure message is good practice.

## Findings

### P1-1 — The recorded string's wording is now load-bearing in a test, and it's brittle to the constant's value
`tests/eligibility/test_eligibility.py:37` asserts the literal substring `"4 sentences > 3 (T9, retired by ruling 35"`. This hard-codes both the count (4) and the constant (3) in prose. If `MAX_WINDOW_SENTENCES` ever changes (the comment at eligibility.py:9 says the constant is kept and mirrored against `editorial_select.py:52`), this test breaks even though the behavior is correct. Minor, but it's exactly the kind of duplicated constant the diff's own comment warns about. **Suggestion:** build the expected string from `E.MAX_WINDOW_SENTENCES` and the fixture's sentence count, or at least assert only the stable prefix `"4 sentences > 3 (T9, retired by ruling 35"`. (Actually the assertion already uses a prefix via `in`, so only the "3" is duplicated — downgrade to P2 if you weigh the `in`-prefix.)

*Regrade: this is really P2; I list it under P1 only because the section asks for severity-ordered findings. Treat as P2.*

### P2-1 — `targets_missed` semantics: retired rule now shares the "missed target" channel with live targets
`eligibility.py:20–22` puts the retired T9 count into `facts["targets_missed"]`, the same list that carries L-o's *live* length targets (HOOK_S/CLIP_S, per lines 23–25 of the diff, which remain reasons-adjacent: the comment says "a target (law L-o); not measured = fail closed"). The ruling says T9 is "recorded only" — that's satisfied — but readers of `targets_missed` now cannot distinguish a *retired, informational* entry from a *live, governing* target without parsing the parenthetical. The stated readers are:
- `moments.py` — copies it into the moment's eligibility record (informational; no behavior change claimed),
- `eligibility.py:621` — appends to it (not shown in the diff; I cannot verify what it appends or whether it, e.g., dedupes or formats).

**Scenario:** a future reader (or a dashboard) treats "targets_missed" as "things that governed the decision" and surfaces the T9 note as a rejection cause. Not a defect today; a documentation/semantics cost. If you want it airtight, the ruling-35 note could live in a separate facts key (e.g. `facts["retired_targets"]`) — but that's a larger diff than "smallest diff" (M1) warrants. Note, don't fix.

### P2-2 — Coverage: only the 4-sentence case is tested; the 3-sentence boundary and the n==0 interaction are not re-verified in this diff
The test exercises `n = 4 > 3` (retired → recorded). Not shown/changed:
- `n == 3` (exactly at the limit): previously no reason, now no reason and — presumably — no `targets_missed` entry. If the new `elif` were accidentally converted to a bare `if` + unconditional append, or if the `elif` chain were disturbed, the 3-sentence case would silently gain a spurious target. The diff shows the `elif` preserved, so this is likely fine, but no test pins it. Pre-existing gap, not introduced here.
- `n == 0` (`no_content`): the branch is unchanged in the diff, and the test at line 41 (`no_bitcoin`) shows the reasons mechanism still works, but nothing in this diff re-asserts that `no_content` still *is* a reason (i.e., that the `R(...)` call survived the hunk). It did — the diff shows the `R("no_content", ...)` line as context, unchanged. So: verified from the diff, no finding, just noting the test doesn't cover it.

### P2-3 — "Nothing else in eligibility changes" — verified within the diff, with one caveat
The diff shows only these two hunks in eligibility.py. Within what's shown: no constant changed, no other reason added/removed, the L-o target logic (lines 23–25) is untouched context, and the `elif`→recorded-only conversion preserves the branch structure. The caveat: I can only see the hunks, not the whole file. If `R()` or `targets`/`facts` wiring changed elsewhere (e.g., `R` no longer called for this case means `names()` derives purely from `R` calls — consistent with the test), it's outside the diff. The test's `assertNotIn` + `assertTrue(any(...))` pair is the operative proof, and it passes only if `R`-reasons and `targets_missed` are indeed separate channels. I flag this as *verified-by-test, not verified-by-reading*.

### P2-4 — "No other hard length rule depends on this reason" — cannot fully verify from the diff
The ruling states the hard rules live in `package.usable()` (SEG_MAX_S = 20 s, L-u) and the 60–70 s runtime (L-o), neither touched. The diff itself shows no other consumer of the `"too_many_sentences"` *string*. But the diff cannot prove no other module greps for that reason string (e.g., a QA gate or a report that counts reasons). The stated readers of `targets_missed` (moments.py, eligibility.py:621) are asserted, not shown. If any other module matched on `"too_many_sentences"` exactly, it would now never see it. **Recommend:** a repo-wide grep for `too_many_sentences` before merge — cheap, and the only residual risk this diff carries. If the grep comes back clean (only eligibility.py + the test), this is a clean ship.

### P2-5 — Comment accuracy (trivial)
`eligibility.py:20` says "ruling 35 (03:12 ET Nov 13)" while the header of the task says 03:12 ET Nov 13 — consistent. The comment "recorded only since ruling 35" on line 10 vs. the fuller note on line 20–22: the duplication of the ruling reference in two places (line 10 and line 20) is mild redundancy; if the constant's comment drifts from the branch's behavior, the branch comment (line 20) is the authoritative one. No action.

## Law compliance (what's checkable from the diff)
- **LAW 20 / M2 (thresholds are constants; never change what a check accepts):** the change *retires* a rule by ruling, which is the sanctioned way to change what a check accepts — the ruling is the authority, the constant stays, and the test mirrors it. Compliant.
- **M12 FAIL CLOSED:** the `n == 0` → `R("no_content")` path is unchanged; the L-o "not measured = fail closed" comment (line 23) is untouched. The retired branch now *adds information* (a targets entry) where it previously *added a reason* — no path loses its fail-closed behavior. Compliant. One nuance: if `targets.append` could throw (it can't, it's a list append on an existing list — assuming `targets` is always initialized, which the L-o code at line 24–25 already relies on), nothing new. No new failure mode.
- **Smallest diff (M1):** two hunks, one of them comment-only. Compliant.
- **L-o consistency:** the diff explicitly models the T9 retirement on L-o's "recorded, ranks nothing, rejects nothing" pattern (the ruling says so, and the code now literally does what L-o does: append to `targets`). Consistent.

## Residual risks (ranked)
1. An unseen consumer of the literal string `"too_many_sentences"` (P2-4). Mitigate with a grep.
2. Test brittleness on the "3" in the expected string (P1-1/P2-1). Cosmetic.
3. `targets_missed` now mixes retired + live targets (P2-2). Semantics, documented in the string itself.

## Verdict

**SHIP: yes** — conditional on one cheap check: grep the repo for `too_many_sentences` to confirm no third consumer of the reason string exists outside eligibility.py and the test (P2-4). Everything the diff shows is correct, minimal, fail-closed, and mirrors the L-o pattern the ruling cites. The test correctly pins the new behavior both negatively (`assertNotIn`) and positively (the recorded target), and the `n == 0` / L-o paths are untouched.

If the grep finds a third consumer, it's still likely a P2 (a report or counter, not a gate — the ruling says the hard rules are elsewhere), but it would need a look before merge.