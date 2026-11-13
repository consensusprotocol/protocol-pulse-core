# glm-5.3-flash (z-ai/glm-5.3-flash) 59 s finish=stop usage in 6243 / out 1587 usd~0.043 (upper-bound price)

# Audit: pp-selectid — ruling 73 switch (RULES + DECODER)

## What the diff shows

Two files, 77 lines:

1. **`pipeline/lock_precheck.py`** — `RULES` changes from `"ruling 17 + ruling 72"` to `"ruling 17 + ruling 72 + ruling 73"`; `DECODER` changes from `"25cd6f15e6c9"` to `"8a101f222598"`. The docstring is updated to state the new rules string, the 18:43 Nov 13 live time, the merged 585b6da5, the full new decoder_sha, and the ruling-73 semantics (a passing entry carries `"cut"`; a span the render cannot cut holds with `"ruling 73: the render cannot cut this span: ..."`). The comment on the old DECODER line ("unchanged by ruling 72") is correctly dropped.

2. **`tests/package/test_lock_precheck.py`** — three changes:
   - Two expected result-file names updated to the new decoder (`...8a101f222598.json`).
   - In `TestAnswer.test_...`: an entry under the old rules string, **newer** (`2026-11-14T01:00:00Z`) than the adopted one, is asserted to still yield `no_difference` — i.e. the old-rules entry is never read even when it is the newest. This is the key "old answers are never read" proof.
   - New test `test_ruling_73_holds_a_span_the_render_cannot_cut`: a ruling-73 hold (with the reason string) on the hook + a passing entry carrying a full `cut` dict on the clip → asserts `(ok=False, verdicts=("hold", "pass"))` and the reason string in `why`.

All 15 suites reported OK.

## Verification against the stated checks

**1. No answer under the old decoder or rules can be read.**

- *Old rules:* Verified by test. The old-rules entry is inserted at `2026-11-14T01:00:00Z`, strictly newer than the adopted `23:00:00Z` entry, and the test asserts the answer is still `no_difference` — so the newest-entry selection filters on `rules == RULES` before recency, exactly as the background states. Since `RULES` is a module constant compared by equality, the old string cannot match. ✔
- *Old decoder:* Verified only indirectly, via the two renamed expected filenames. The decoder enters through `LP.result_file(...)` (name construction) and, per the background, through the read path. The diff does not show the read/glob side of `lock_precheck.py` — only the constants and docstring. If the read side derives the filename from the `DECODER` constant (as the naming convention and the passing tests imply), the old decoder's files are unreachable. **I cannot verify the glob/read implementation from this diff**; the passing 15 suites are the evidence here, not the diff. (P2, see below.)

**2. A ruling-73 hold can never pass.** Verified by the new test at the `answer`/`check` level: a hold entry yields `verdict "hold"`, `ok=False`, and the reason surfaces in `why`. That the hold is *reported* rather than swallowed is asserted. Whether a hold can pass *downstream* (in the line-up writer / render) is outside this diff — the background says "no answer is never a pass", and the test confirms the hold is not `ok`, but the render-side consumption of `verdict` is not in the diff. Within the audited scope: ✔.

**3. Nothing else changes.** The diff touches only the two constants, the docstring/comment, and the tests. No logic, no thresholds, no other constant. ✔ — with one caveat: the docstring now documents ruling-73 semantics (`"cut"` field, hold reason) that the *production* code in this diff does not implement; the diff assumes the integrator's service (merged 585b6da5) produces those. That is consistent with the notice, but the production side of ruling 73 (the render's own cut placement joining the pre-check) is not in this diff — presumably it lives in the integrator's service, not here. If the render's cut-placement code were supposed to change in this worktree too, it is not here. **Uncertain; flagging, not guessing.**

## Findings

**P0** — none.

**P1** — none.

**P2-1.** The docstring documents ruling-73 semantics ("a passing entry carries `cut`", the hold reason) but the only production change is the two constants. If the integrator's service is the sole producer of those fields, this is correct; the diff alone cannot confirm the consumer side (`answer()`/`check()`) needs no change to *read* the `cut` field — the new test's passing entry includes `cut` and passes, which suggests the consumer treats unknown/extra fields as pass-irrelevant, but that behavior is pre-existing and not shown. Low risk; the test covers the observable behavior.

**P2-2.** The old-decoder exclusion rests on the read path deriving filenames from the `DECODER` constant. The diff shows only the constant and the *expected* names in tests; the actual glob/read code is not in the diff. If any code path hard-codes `25cd6f15e6c9` elsewhere (e.g., another module, a cleanup routine, docs), it would silently read stale answers. Not verifiable from this diff; the 15 green suites suggest not, but a repo-wide grep for `25cd6f15e6c9` would close it.

**P2-3 (minor).** In the new test, the hold entry's reason string is asserted via `assertIn` on `rep["segments"][0]["why"]` — good — but the test does not also assert that the passing segment's entry *file* uses the new decoder, nor that the hold's `outcome`/`ok` distinction (hold vs error) is preserved for ruling-73 holds specifically. The adjacent `test_a_hold_is_not_ok_and_is_not_an_error` presumably covers the general case; the ruling-73 test asserts `ok=False` but not the error/hold distinction explicitly (it does assert `verdict == "hold"`, which implies it). Cosmetic.

**P2-4 (nit).** The comment "RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's side)" — the parenthetical trails onto the next line's comment; readable, no issue.

## SHIP

**SHIP: yes**

The change is the minimal, correct switch: both constants, documented, with the three required behaviors proven by tests (new-decoder filenames, old-rules-never-read-even-when-newer, ruling-73 hold-not-pass). No logic changed; fail-closed behavior (no answer = not a pass) is untouched. The P2s are verification-hygiene items, not defects: confirm by grep that no other reference to the old decoder/rules survives, and confirm (outside this diff) that the consumer side needs no change for the `cut` field.