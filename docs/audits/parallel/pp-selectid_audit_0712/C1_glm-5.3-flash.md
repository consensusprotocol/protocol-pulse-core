# glm-5.3-flash (z-ai/glm-5.3-flash) 85 s finish=stop usage in 9593 / out 2479 usd~0.066 (upper-bound price)

# Audit: TRIMMED-CLIP SEALING (Ruling 49) — reviewer pass

Scope: I verified only what the diff shows. I did not see `stand_alone_check`, `trim_variant`, `to_pin`'s schema check, `pinned.validate_schema`, or the swap paths' bodies; where that matters I say so.

## P0

None.

## P1

**P1-1 — `package.py:41-44` (lineup_ok) vs. `package_pin.trim_problems` (package_pin.py:89-92): the two "at most one" checks count differently, so a pin can be refused for a line-up the builder already accepted.**
`lineup_ok` counts `bool(m.get("trimmed_leading"))` — a segment with `trimmed_leading` but no `untrimmed_start` (or vice versa) counts as trimmed. `trim_problems` counts `"trimmed_leading" in s or "untrimmed_start" in s` — same. But `trim_problems` also independently requires `scorer_pending is True` on every trimmed segment, while `lineup_ok` never looks at `scorer_pending`. Concrete scenario: a segment carries `trimmed_leading`/`untrimmed_start` but no `scorer_pending` key (e.g. an older moment dict produced before this diff, or a path that builds the row without it — I cannot verify from the diff that every producer of the trimmed row sets it; the only producer shown is the `**{...}` literal at package.py:31-33, which does set it). `lineup_ok` passes it, the pin's `trim_problems` refuses it. That is fail-closed, not a correctness bug — but it means the builder's line-up acceptance and the pin's acceptance can disagree, and the diff's own test (test_medley.py:158) only exercises `lineup_ok`'s message, not the disagreement case. Severity: P1 because the ruling's condition (a) is enforced only at the pin, not where the line-up is chosen; if any other producer of trimmed rows exists outside this diff, it silently breaks.

**P1-2 — `package.py:31-33`: `scorer_pending: True` is written unconditionally inside the conditional-spread, but the spread's condition is `m.get("trimmed_leading")` while the pin's "belongs to a trimmed clip" test is presence of `trimmed_leading` OR `untrimmed_start`.**
If a moment dict ever carries `untrimmed_start` without `trimmed_leading` (the diff's own `trim_problems` treats that as malformed, package_pin.py:102-103, so it would be refused — but only at the pin, with a *different* message), the package row would carry `untrimmed_start` with no `scorer_pending`, and the pin's ruling-49(a) check (`s.get("scorer_pending") is not True` fires whenever either key is present, package_pin.py:93-101) would refuse it with the *pending* message rather than the *pairing* message. Fail-closed, but the diagnostic points at the wrong ruling. Minor, diagnostic-only. Could be P2; I list it here because the two presence tests (`m.get("trimmed_leading")` truthiness vs. key presence) are subtly different — a moment with `trimmed_leading: ""` (falsy) would get no `scorer_pending` in the package row yet count as trimmed in `trim_problems`'s `n` count (key presence, not truthiness). That is a real, if unlikely, divergence: **`trimmed_leading: ""`** → package row: no scorer_pending; pin: counted as trimmed, then refused for missing scorer_pending. Fail-closed either way.

## P2

**P2-1 — `package.py:14-21` / `package_pin.py:75`: the two constants are equal only by convention, enforced by a test, not by code.**
`TRIMMED_PER_LINEUP_MAX = 1` (package.py) and `TRIMMED_PER_PIN_MAX = 1` (package_pin.py) are separate literals; the test asserts equality (test_medley.py:152) but nothing in the code does. If one changes, the other drifts. `package_pin` already imports nothing from `package` here — I cannot see whether a circular-import constraint prevents `TRIMMED_PER_PIN_MAX = package.TRIMMED_PER_LINEUP_MAX`. If importable, prefer the single source. (The test at line 152 does catch drift, so this is P2.)

**P2-2 — `package_pin.py:99-101`: the ruling-49(a) check runs before the pairing check, so a segment with `scorer_pending` but neither trim key gets *two* problems appended in some orderings — actually no: it's guarded correctly.** On re-reading: the `scorer_pending`-on-untrimmed case is caught at package_pin.py:96-97 (inside the `not has_w and not has_s` branch) and the missing-`scorer_pending` case at 99-101 (inside the has-either branch). Both are correct; the only residual is that a segment with `trimmed_leading` present but `untrimmed_start` absent *and* `scorer_pending: true` gets the pairing refusal (line 102-103) and correctly no ruling-49(a) refusal — good. No finding; noted for completeness.

**P2-3 — `package.py:55-61` (the no-voice path, build): the added-clip rule is duplicated inline rather than calling `lineup_ok`.**
The no-voice path re-encodes the line-up rules (length, price predictions, now trimmed count, duration window) as an inline `if ... continue`. This is the third copy of the trimmed-count rule (lineup_for's inline, lineup_ok, and here). Any future change to TRIMMED_PER_LINEUP_MAX semantics (e.g. "2 after first affirmation") must be made in three places; the diff's test covers `lineup_for` and `lineup_ok` but I see no test exercising the no-voice path's trimmed-count. Fail-closed risk is low (the inline rule matches), but the duplication is the kind that drifts. Also: I cannot verify from the diff whether the no-voice path's `cand` segments carry `scorer_pending` — they come from `segs`, which presumably went through the same row-building, but the diff does not show it.

**P2-4 — "nothing claims the scorer affirmed anything": verified, with one caveat.**
The package row says `scorer_pending: True` (package.py:31-33), the sealed STAND_ALONE row says "PENDING AT THE RENDER" (test asserts it, test_medley.py:135), and the pin copies the key (package_pin.py:110). I see no boolean like `scorer_affirmed` anywhere. Caveat: the ruling says "If you can call the same scorer ... at the pin stage inside budget, do that instead and seal its verdict: say which you did." The answer "pending at the render" is stated in the diff's prose and in the comment at package.py:14-18, but I cannot verify from the diff that no *other* code path (e.g. a later ruling-41/44 swap or the integrator's check) seals an affirmed verdict; the diff shows only these files. Within what is shown, the claim holds.

**P2-5 — SEALED_LATER contract, verified.**
`scorer_pending` added to SEALED_LATER (package_pin.py:73-74) alongside the existing `trimmed_leading`/`untrimmed_start` keys: it enters the seal only when present on the segment, so a pin with no trimmed clip seals byte-identically (the `**{k: s[k] for k in (...) if k in s}` at line 110 adds nothing). The test at test_medley.py:174 asserts `scorer_pending` absent on the untrimmed segment, and the seal-equality tests (177-180, 182-183) confirm the key is inside the seal. One residual: the diff does not show `pinned.validate_schema`'s key list; if the integrator's schema check enumerates allowed keys strictly, an older integrator copy without `scorer_pensding`... (typo mine) — without `scorer_pending` in its allowed set would refuse the new pin. The background says the integrator's `check_pin_only` imports *this branch's* `package_pin.py` and the render's `validate_schema` "ignores unknown ones", so this is covered by the stated static facts; no finding.

**P2-6 — test_medley.py:161-163: the two-trimmed-clip pin refusal test asserts only the first problem string.**
`trim_problems` returns a list; the test checks `assertIn("2 trimmed clips", ...[0])`. Since the count check is appended before the per-segment loop (package_pin.py:89-92), index [0] is indeed the count problem — correct as written, but it couples the test to the ordering of `out` (the count check must stay first). If someone later moves the count check after the loop, the test breaks spuriously. Cosmetic.

## What I could NOT verify from the diff

- That every producer of a trimmed segment row sets `scorer_pending` (only the one literal at package.py:31-33 is shown; the no-voice path's segments and any ruling-41/44 swap output inherit from `segs`, presumably the same rows — presumed, not proven).
- Whether `stand_alone_check`'s "PENDING AT THE RENDER" string and `scorer_pending` recording are exactly as described (code not in diff; the tests assert the behavior, and 81 tests pass).
- Whether `to_pin`'s schema/`validate_schema` interplay admits `scorer_pending: false` — the test at line 184-185 expects `PinRefused` for it, which requires `trim_problems`'s `is not True` check to fire; it does (package_pin.py:99), consistent.
- Whether the "first trimmed clip affirmed at validate once" state (the "until" in ruling 49(b)) is tracked anywhere; the diff implements a constant 1 with a comment saying "the integrator says when". If the integrator later flips it to 2, both constants and the three inline copies must change. Not a defect; a maintenance note.

## SHIP: yes with conditions

1. Confirm (outside this diff, one sentence in the PR) that the package-row literal at package.py:31-33 is the *only* producer of `trimmed_leading`/`untrimmed_start` on segment rows, so the pin's ruling-49(a) check can never see a trimmed row without `scorer_pending`.
2. Either derive `TRIMMED_PER_PIN_MAX` from `package.TRIMMED_PER_LINEUP_MAX` (if importable without a cycle) or keep the equality test as the guard — state which.
3. Add (or point to) a test exercising the no-voice path's trimmed-count rule, since it is a third, hand-copied copy of the rule.

No P0s; the fail-closed direction holds on every path I could trace, the SEALED_LATER contract is preserved, and the "pending, not affirmed" claim is consistent across package row, pin, and tests.