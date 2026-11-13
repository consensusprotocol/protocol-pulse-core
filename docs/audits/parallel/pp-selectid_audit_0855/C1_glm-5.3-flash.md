# glm-5.3-flash (z-ai/glm-5.3-flash) 68 s finish=stop usage in 6211 / out 1886 usd~0.047 (upper-bound price)

# Audit: pp-selectid-0855 — placement() markings vs lineup_for

## Verification of the three markings against the stated rules

The rules given: hook needs hook eligibility AND passed hook onset (G17a); a clip under SHORT_CLIP_S may play only LAST among the clips after the hook (`order[:-1]` over clips after the hook; `clips[:-1]` in lineup_ok with `clips = segs[1:]`). So a short clip may be the hook, and a short clip may be last; it may not sit mid-line-up.

New placement() (package.py:30-38):

- `opens = hook.eligibility.ok AND hook_onset.pass is True` — matches the hook rule, including the `is True` strictness (a truthy non-True, e.g. `"yes"`, would count as not-opens; the diff's test at test_medley.py:57-58 uses `{"pass": True}` so the strict comparison is exercised for the True case only — I cannot verify from the diff whether any caller stores a truthy non-boolean, but the old code used the identical expression, so behavior is unchanged there).
- Short + opens → `" | under 8 s: only the hook or the LAST clip"` — correct: hook allowed (hook is exempt from the short rule since the rule applies to `order[:-1]` of the clips after the hook), LAST allowed, mid not. Matches.
- Short + not opens → `" | under 8 s: only the LAST clip"` — correct: cannot be hook (no onset/eligibility), cannot be mid (short), only LAST remains. Matches.
- ≥8 s + not opens → `" | cannot open (never the hook)"` — correct: a long clip has no placement restriction other than the hook rule. Matches.
- ≥8 s + opens → `""` — correct.

Edge: short + not-opens previously produced two markings ("may only play LAST | cannot open"); now one. Since "only the LAST clip" logically implies "cannot open", no information is lost. The prompt sentence (package.py:12-14) now names all three markings, so the proposer sees the same constraint set. Consistent.

Boundary semantics: "under 8 s" is `< SHORT_CLIP_S` in both placement() (line 32) and the stated lineup rule; the prompt says "under 8 s" via the f-string `{SHORT_CLIP_S:.0f}` — if SHORT_CLIP_S were ever not exactly 8.0, the rounding `:.0f` could print e.g. "under 8 s" while the code tests `< 7.6`. Pre-existing pattern (old code had the same `:.0f`), not introduced here. P2 at most; not verifiable from the diff whether SHORT_CLIP_S is exactly 8.

## "Nothing else changed"

The diff touches only the PLACEMENT LIMITS prompt sentence (package.py:9-15), placement() (package.py:22-38), and the test. Within the prompt hunk, the trailing `Give as many good angles as the clips allow (aim for {k}); for` is preserved across the rewrap (lines 11/14-15) — the stray `; for` continuation is unchanged, so no accidental prompt-text loss. The `swap_lineup` context lines are context only. No other hunks.

## Test hunk review (test_medley.py:46-62)

- Line 51: `id=s | C | 6.9 s | under 8 s: only the LAST clip` — s is 6.9 s, no_hook={"s","y"} so not-opens → short+not-opens marking. Correct, and it also verifies the old "may only play LAST (under 8 s) | cannot open" double marking is gone.
- Line 52: y, 13.8 s, no_hook → "cannot open (never the hook)". Correct.
- Line 53: z, 9.5 s, no restriction → `| "`. Correct (9.5 ≥ 8, opens).
- Line 55: prompt-text assertion updated to the new wrapped wording; I cannot verify the exact wrap position in the rendered prompt from the diff alone (the assertion spans a line break: `"only the hook or the LAST\nclip"`), so this depends on the prompt's actual wrapping at ~the same column as the old assertion. If the wrap column differs, the test fails, not the code — the suite reportedly passes (90 OK), which is the only evidence the wrap matches. Flag as trust-the-suite, not independently verifiable.
- Lines 57-62: the 08:46 regression. `short_opener` = 7.3 s, hook_onset pass → placement() == " | under 8 s: only the hook or the LAST clip" (asserted, line 58). Then a 4-clip lineup b(7.3, hook) + c(13.9) + w(9.5) + a(6.9, not-opens) = 37.6 s, fed to the real `PK.lineup_for` with `need_onset=True`, asserting the order survives. This exercises: short clip as hook (the defect), short clip last (a, 6.9 s, in `clips[:-1]`... wait — a is LAST, so it is in `clips[-1]`, i.e. exempt; the mid positions are c and w, both ≥8 s). Good: the mid-positions are all long, so the lineup is formable, which is the 08:46 shape. One nuance: the test never asserts a short clip FAILS mid-line-up (i.e., that lineup_for rejects e.g. b,c,a,w). That negative case is the other half of the rule; it is presumably covered by the pre-existing lineup_for tests, not by this diff. P2: the corrective test proves the marking matches a formable lineup but not that the marking's "never in between" claim is enforced — acceptable, since the enforcement (lineup_for) was not changed.

Arithmetic: 7.3+13.9+9.5+6.9 = 37.6 ✓ (comment says 37.6 s). The 08:46 ledger figures 7.26+13.94+9.46+6.93 = 37.59 ✓, and the test's 7.3/13.9/9.5/6.9 are those rounded — faithful reproduction, with 6.9 < 8 so the short-last condition holds, and 7.3 < 8 so the hook-exception condition holds. Both sides of the defect's geometry are inside the test.

## Findings

- **P2** — package.py:37-38: the short+not-opens case now returns one marking where the old code returned two; the prompt sentence (package.py:12-14) enumerates "only the hook or the LAST clip" and "only the LAST clip" but a reader must infer that "only the LAST clip" also implies cannot-open. Scenario: a future maintainer adds a fourth independent limit (e.g. "cannot follow X") to the not-opens short case and forgets the implied cannot-open. Cosmetic/robustness only; no behavioral defect. No action required for this merge.
- **P2** — package.py:37: `f"under {SHORT_CLIP_S:.0f} s"` rounds the threshold for the prompt while the code compares `< SHORT_CLIP_S`. If SHORT_CLIP_S ≠ 8.0 exactly, prompt and enforcement could disagree by the rounding. Pre-existing pattern; not verifiable from the diff whether SHORT_CLIP_S == 8.0. Confirm once, or ignore.
- **P2** — test_medley.py:55: the prompt-wrap assertion (`"only the hook or the LAST\nclip"`) is only verifiable via the reported green suite; the diff alone cannot confirm the wrap column. If the suite genuinely ran (90 OK), this is fine.
- **P2 (coverage note, not a defect)** — test_medley.py:59-62: no negative assertion that a short clip mid-line-up is rejected by lineup_for. The diff doesn't change lineup_for, so this is out of scope, but noting it since the marking's "never in between" clause rests on it.

No P0/P1 found. The three markings exactly match the stated lineup_for/lineup_ok semantics, including the short-clip-may-be-hook exception that the committed code got wrong; the 08:46 failure shape (short opener, short last, 37.6 s) is reproduced and asserted through the real lineup_for; the prompt sentence names all three markings; the diff is otherwise confined to the rewrapped prompt text and the test.

**SHIP: yes**