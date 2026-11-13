# glm-5.3-flash (z-ai/glm-5.3-flash) 69 s finish=stop usage in 5595 / out 1914 usd~0.045 (upper-bound price)

# Audit: pp-selectid — "exactly ONE canonical token" tightening

## What the diff does (verified from the diff)

Both production sites change the acceptance predicate identically:

- **package.py:689-690 (diff lines 9-12)** — old: `tok = canon.canon_tokens(word)[:1]` then `if w1 <= w0 or not tok or tok[0] not in TRIM_WORDS`. New: `tok = canon.canon_tokens(word)` then `if w1 <= w0 or len(tok) != 1 or tok[0] not in TRIM_WORDS`.
- **package_pin.py:128-129 (diff lines 24-29)** — same predicate change on `w` (guarded by `isinstance(w, str)`), plus the message now reads "must be ONE word, one of ...".

Both now match the render's `validate_schema` shape quoted in the brief: `len(tok) != 1 or tok[0] not in TRIMMABLE_LEADING → refuse`. The predicates are structurally identical (tokenize, require exactly one, require membership).

## P0 findings

None.

## P1 findings

None.

## P2 findings

**P2-1 — package.py:689 (diff line 11): the `[:1]`-to-`len!=1` change also silently changes behavior for the *empty/None* case, and the comment claims a guarantee the diff doesn't prove.** Old code: `not tok` caught the empty list. New code: `len(tok) != 1` catches empty, 2+, and — importantly — the case where `canon_tokens` returns more than one token for what looks like one word. That's the intended tightening, but note the diff relies on an unstated assumption: that `canon.canon_tokens` is total (never raises) on any string reaching these lines. In package.py, `word` comes from `toks[w0].get("word") or ""` — the `or ""` guarantees a str, so `canon_tokens("")` must return `[]` for the new predicate to behave like the old one on the empty path. If `canon_tokens("")` ever raised, the old code would have raised too (same call), so this is *not* a regression — but the diff's correctness for the empty-string path (`""` → `[]` → `len != 1` → `return None`) is asserted, not tested: the new test case list (test_medley.py:806-809, diff lines 39-42) adds "And/or" (2 tokens) but no empty-string or punctuation-only case (e.g. `"But,"` → `['but']`, which the brief says must still pass). **Concrete scenario:** if `canon_tokens` stripped punctuation to nothing for a punctuation-only trimmed_leading like `","`, the pin would now be refused where the render (same predicate) would also refuse it — consistent, so not a bug, but the "punctuation allowed as canon strips it" claim in the task is untested in this diff. Severity: P2 (consistency holds either way because both sides use the same function; only test coverage is thin).

**P2-2 — package_pin.py:129 (diff line 28): the `isinstance(w, str)` guard placement means a non-str `trimmed_leading` now produces a different (but still failing) reason, and the error message interpolates `w!r` — fine — but the *new* message text is a seal-relevant change.** `trim_problems` output feeds `package_pin.seal` (the diff's own test at test_medley.py:868-871, diff lines 46-54, asserts seal changes when segment fields change). If any stored/attested artifact (e.g. a pinned package's problem list, or a golden test) compares `trim_problems` strings, the wording change "is not one of" → "must be ONE word, one of" will break it. The diff updates the seal test's *inputs* (adds `{"trimmed_leading": "But so"}` and `{"trimmed_leading": "and/or"}`) but I cannot verify from the diff whether any other test or fixture pins the old message text. **Flag: verify no golden/attestation fixture asserts the old `trim_problems` reason strings.** Severity: P2 (test-only breakage if it exists; the diff author reports all suites OK, which suggests none, but that's their report, not the diff).

**P2-3 — test_medley.py:806 (diff line 41): the "And/or" case tests `trim_variant` returns None, but the brief's measured facts say `canon_tokens("and/or") == ['and', 'or']` — two tokens — so this exercises the `len != 1` branch. Good. However the *pin-side* counterpart for "and/or" is only tested via the `bad`-tuple loop (diff line 50), which asserts seal-inequality, not that `trim_problems` reports the ONE-word reason.** The new reason text ("must be ONE word") is therefore never asserted anywhere in the diff. If the message wording matters downstream (see P2-2), nothing catches a regression to the old wording. Severity: P2.

## Equivalence check: nothing valid-at-render now refused

Old acceptance: `tok[:1]` non-empty and `tok[0] in TRIM_WORDS`. New: `len(tok) == 1` and `tok[0] in TRIM_WORDS`.

- Anything with exactly one canonical token: accepted by both. ✔ (includes "But," → ['but'], since canon strips punctuation — per the brief's measured facts; the *code* doesn't need to handle it, canon does.)
- Anything with ≥2 tokens, first in TRIM_WORDS (e.g. "But so", "and/or"): accepted before, refused now. This is the intended tightening, and the brief confirms the render already refused these — so these are *not* valid-at-render losses. ✔
- Anything with 0 tokens: refused by both (`not tok` vs `len != 1`). ✔

So the only behavior change is exactly the intended one: multi-token trimmed_leading now fails here instead of failing later at the render's prepare. This is fail-early, consistent with M12 (a defect rejects, never passes) and with the one-canonical-form law (L-k: both sides read through canon.py, no ad-hoc normalizer introduced — the diff adds no second tokenization).

## "Nothing else changed" check

From the diff, the only other edits are:

- package.py:14 (diff line 14, context): unchanged logic, `E.MIN_STATEMENT_TOKENS` check — context only. ✔
- package_pin.py:30-32 (diff lines 30-32): the `num` lambda and the `untrimmed_start` check are context, unchanged. ✔
- test_medley.py:870-871 (diff lines 50-51): the `bad` tuple gains two entries; the loop body (context, lines 52-54) is unchanged. ✔

No new imports, no new module, no renderer/compositor/selector change (M1 ✔), no threshold constants touched (LAW 20 ✔), no canon.py change (L-k: single canonical form preserved ✔).

## Minor observations (not findings)

- The comment on package.py:690 (diff line 12) — `# exactly ONE canonical token, as the render's validate_schema` — duplicates the constraint in prose at the call site. Acceptable; the render's schema remains the source of truth, and this branch now mirrors it. If the render's `TRIMMABLE_LEADING` set ever diverges from this branch's `TRIM_WORDS`, both sides fail closed independently — acceptable, but worth noting there's no test here that the two word-sets are equal. That's pre-existing, not introduced.
- The `num = lambda` at package_pin.py:130 (diff line 30) is PEP8-discouraged (E731) but pre-existing.

## Verdict

The tightening is correct, minimal, symmetric across both enforcement points (the moment's own test and the pin's test), fail-closed, and the only behavior delta is the intended one (multi-token openers now rejected here, matching the render). Test additions cover the 2-token case on both the variant and the pin/seal side. Gaps are coverage-only: no punctuation-only/empty-string case, and the new reason wording is never asserted.

**SHIP: yes**

(Conditions, if you want them: (a) confirm no fixture/golden asserts the old `trim_problems` message text; (b) consider one more test case: `trimmed_leading: "But,"` → still accepted, locking the "punctuation allowed" behavior against future canon changes.)