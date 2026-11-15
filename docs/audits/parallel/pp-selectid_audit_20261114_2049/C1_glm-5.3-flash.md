# glm-5.3-flash (z-ai/glm-5.3-flash) 182 s finish=stop usage in 13081 / out 5452 usd_reported=0.001082 usd~0.121 (upper-bound price)

# Audit: pp-selectid, RULING 105 builder side (lock_precheck / package_pin)

Scope: the 369-line diff only. I traced `ruling_105_fails` against the ruling's three tests, the decide/apply flow, the seal path, and the test coverage. Findings, worst first.

---

## [P1] (1) `_truncation` rejects a comma-formatted token the integrator rightly passes

The ruling's example is `'401' of '401k'` — "a prefix of the same term". The integrator's field shape carries the token as the lock wrote it; the ruling's own must-fail list speaks of `'68,000' / '86,000'` with commas, so the record's token may legitimately be a formatted number. `_truncation`:

```python
return (isinstance(r, str) and bool(r) and r != token and token.startswith(r) and any(ch.isdigit() for ch in r)
        and not any(ch.isdigit() for ch in token[len(r):]))
```

requires `token.startswith(r)` — a **strict character-prefix**. If the lock's token is `401k` but the second recogniser writes the same spoken term as `401,000` or `401K` (case), the ruling-105 pass is turned into a hold. Same for `'$40,000'` vs `'$40'`-style readings. The ruling says "a prefix of the same term", not "a character-prefix of the raw token string"; the builder's own test `test_a_dropped_token_or_a_digit_cut_off_is_no_truncation` even asserts `("4015", ("401", "4015"))` is a hold because "a digit cut off: another number" — correct — but nothing in the ruling says `401K`/`401,000` must hold, and the ruling's own must-fail list uses comma forms, implying the record may carry them.

**Fix:** compare canonically (law L-k: every text comparison in the pipeline uses `pipeline/canonical.py`... `canon.py`), e.g. strip separators/case before the prefix test, or document that the record's tokens are the lock's raw spelling and enforce that in the record's own tests. As written, a legitimately-passing record can be refused — a real defect, but not a wrong result (it fails closed, so P1, not P0).

Note the ruling's own must-fail case `'68,000' / '86,000'` — the test uses `86000`/`68000` without commas, so the comma path is untested. That's part of the same finding.

---

## [P1] (1) `ruling_105_fails` never checks that the second readings' `token` fields are strings at all — a non-string reading passes the (2)/(3) checks silently in one path

Look at the flow for `st`:

```python
st = [x.get("token") if isinstance(x, dict) else None for x in sec]
if len(set(st)) >= 2 and tok in st:   # (2)
```

Wait — actually the code is:

```python
if len(set(st)) < 2 or tok not in st:
    return f"(2) ..."
```

`set(st)` with `None` entries: if `sec = [{"token": "401"}, "notadict", {"token": "401k"}]` → `st = ["401", None, "401k"]`. Then (2) passes (`len(set) >= 2`, `tok in st`), and (3): `odd = [x for x in st if x != tok and not _truncation(x, tok)]` — `_truncation(None, "401k")` returns False (isinstance check), so `None` lands in `odd` → hold. Good, that path fails closed. **But** consider `sec = [{"token": "401"}, {"token": "401k"}, {"token": "401k"}]` where one element is `{"token": 401}` (an int). `st = ["401", 401, "401k"]` — `401 != "401k"`, `_truncation(401, "401k")` → `isinstance(401, str)` False → hold. Fails closed. So the only gap: `st` containing `None` from a **non-dict** element where the *other* readings satisfy (2) and (3) — no, that also lands in `odd`. Actually the real gap: **`dec` (decoder readings) elements that are not dicts**. `dt = [x.get("token") if isinstance(x, dec) else None ...]` — if a decoder reading is a bare string `"401k"` instead of `{"token": "401k"}`, `dt` gets `None`, (1) fails → hold. Fails closed. So: no P0 here; the non-string paths all fail closed. Downgrade: this is a **P2** — the error messages will say `(1) the decoder is not stable: [None, ...]` which is misleading (the readings were present, just malformed), and the record's own `tests` dict is trusted for `decoder_stable` etc. without the readings being validated to the field shape. The ruling's field shape says each reading is `{"at", "source", "token"}`; the builder's check never validates `at`/`source` presence or that `token` is a str. A record with `{"token": 401}` (int) that the integrator seals as pass will be held by this side — defence in depth, but the ruling says the *shape* is agreed; not validating it means the "this side's own check" can disagree with the integrator on shape, not substance. Should fix: validate the agreed field shape, or explicitly document that only `token` is read.

---

## [P1] (1) The `tests` re-check trusts the record's own booleans without recomputing them from the readings

`ruling_105_fails` ends:

```python
tests = u.get("tests")
if not (isinstance(tests, dict) and all(tests.get(k) is True for k in
                                        ("decoder_stable", "second_unstable", "truncations_only"))):
    return f"the record's own tests do not all hold: {extra}"
```

It requires the record to *assert* the three booleans, but the function has already computed (1), (2), (3) from the readings themselves. So the record's `tests` are **redundant** — they add no independent information, they're the integrator's self-attestation. That's fine as defence in depth (a record whose tests say `truncations_only: False` while its readings pass (1)-(3) is held — the test `test_the_records_own_tests_and_verdict_must_agree` pins this). But the converse gap: the record's `tests` could say all-True while the readings say otherwise — that IS caught by (1)-(3) checks. So the design is: readings are the source of truth, `tests` must merely agree. Consistent. However — the `verdict` check:

```python
if "tokens" in u or u.get("verdict") early-exit...
```

Actually:

```python
if "tokens" in u or u.get("verdict") != "pass":
    return f"the record's verdict is {u.get('verdict)!r}" + (f" ({u.get('why')})" if u.get("u.get("why")") else "")
```

The edge form `{"tokens": [...], "verdict": "hold", "why": ...}` is rejected because `"tokens" in u` — but the ruling says the edge form is a **hold** verdict, and `decide()` only calls `ruling_105_fails` when `out in PASS`. So an edge-form record under a PASS outcome is malformed (the integrator said pass but the record says hold) → hold. Correct fail-closed. But note: the edge form's `why` is surfaced in the message via `u.get("why")` — good. One subtlety: a record with BOTH `tokens` and `token` keys — `"tokens" in u` catches it → hold. Fine. **The gap:** a record with `verdict: "pass"` and NO `tests` key at all → `tests` is None → "the record's own tests do not all hold" → hold. Is that right? The ruling's field shape lists `tests` as a required member of the object. So a pass without `tests` is malformed → hold. Fail-closed, correct. But the error message says "the record's own tests do not all hold: None" — accurate. OK.

So this finding reduces to: the `tests`/`verdict`/`why` handling is correct but the *error messages* conflate "missing" with "false". **P3.**

---

## [P2] (2) `decide()`'s ruling-105 branch runs before the hold branch — verify a hold outcome is never turned into a pass

`decide()`:

```python
u = (e or {}).get("unstable_second_reading") if isinstance(e, out) else None
if out in PASS and u is not PASS:  # roughly
    bad = ruling_105105_fails(u)
    only when bad: return hold
if out in PASS: return pass
if out == "hold": return hold
```

The ruling-105 check only *downgrades* PASS→HOLD. A hold outcome: `u is not None` → `if out in PASS and u is not None` — the condition `out in PASS` is False, so the ruling-105 check is skipped entirely; the hold branch returns hold. So a hold outcome carrying a *perfect* record stays a hold — the ruling says "A ruling-105 pass leaves the normal outcome; a ruling-105 hold is 'hold'". But: **a hold outcome with a record whose verdict is "pass" and whose readings are perfect** — the ruling's field shape allows `verdict: "pass"` in the record; the integrator's outcome is hold for some *other* reason (e. g. the lock's own hold). The builder's decide returns hold. Correct per ruling ("Anything else stays a final hold"). No defect. However, the test `test_a_ruling_105_hold_stays_a_hold` uses `record(second=("401","401","401"), verdict="hold"), outcome="hold"` — it never tests **hold outcome + perfect record**. That combination is the one where a careless refactor (e.g. someone later "helpfully" promoting holds to passes when the record passes) would break. **P2: add the missing test** — hold outcome + BLOCKWARE record must stay hold.

Hold outcome + perfect record stays hold — correct behavior, untested. That's the finding.

---

## [P2] (3) Seal compatibility: `unstable_second_reading` joins SEALED_LATER — the frozen 3f481f5a pin

`package_pin.SEALED_LATER` gains the key; `to_pin` copies it only `if k in s`. A pin without the key seals as before — the test `test_the_record_is_sealed_and_a_pin_without_one_seals as before` proves the *mechanism* on a synthetic pin, and `test_the_spotlight_now_rendering_still_recomputes_to_its_own_seal` proves the frozen 3f ruling-105-free pin `3f481f5a` still recomputes. Since the frozen pin predates ruling 105, it carries no `unstable_second_future` key, so its body is unchanged → its seal is unchanged. The only way an existing pin's recompute changes: if some *existing* segment already carried a key named `unstable_second_reading` before this diff (name collision). Nothing in the diff shows a collision; the name is ruling-105-specific. **No defect.** But: `apply()` in lock_precheck copies the record onto the segment via `json.loads(json.dumps(...))` — a deep copy "as it stands". `to_pin` then copies it by reference into the pin body, and `pin_seal` hashes it. Since `apply` deep-copied, no aliasing between the pre-check row and the pin. But `to_pin`'s dict-comprehension `{k: s[k] for k in (...) if k in s}` — the *same* dict object is shared between `s` (the package segment) and the pin. If any later stage mutates the pin's segment dict in place, the package's segment changes too (or vice versa) — the same aliasing already exists for `relisten` (ruling 103, shipped), so it's a pre-existing pattern, not introduced here. **P3.** The real question: does `pin_seal` hash the record *canonically* (sorted keys) so that a key-order change doesn't change the seal? That's pre-existing `pin_seal` behavior, not in this diff. Out of scope, but note: the test does `tampered[...]["second_readings"][2]["token"] = "401"` and asserts the seal changes — good, the record is inside the seal. And `assertIsNot(...)` in `test_the_record_is_carried_as_it_not...` proves the deep copy. Solid.

No P0/P1 on the seal path. The frozen-pin test hardcodes `startswith("3f481f5a")` — if the integrator's frozen pin is ever legitimately re-issued, this test breaks; it's a proof pin, intended. P3.

---

## [P2] (4) Test coverage: the comma/case truncation path is untested, and the "adopt" outcome path is untested

Enumerate `ruling_comma_fails`'s branches vs. the 16 tests:

| Branch | Pinned by |
|---|---|
| not a dict → hold | `test_the_records_own_tests_and_verdict_mut...` (`odd in ("pass", ["401k"], 7)`) |
| `"tokens" in u` / verdict≠pass | `test_the_records_own_tests_and_verdict_must_agree` (many-form, verdict="hold") |
| token not a number | `test_must_fail_a_different_name` (Saylor) — but only via the *name* path; a record with `token=""` or `token=None` under a pass outcome is **untested** |
| too few readings | `test_too_few_readings` — but `dec=()` gives `dec` an **empty list** → the `isinstance(dec, list) and dec` check: `()` → `list(())`... wait, `record(decoder=())` → `decoder_readings = []` (empty list, since `enumerate(())` yields nothing) → `isinstance([], list) and []` → falsy → "too few readings" → hold. And `decoder=("401k",)` → one reading → (1) `any(x != tok for x in dt)` — `dt = ["401k"]`, all equal → (1) passes, then (2): `st = ["401k"]` → `len(set(st)) < 2` → "(2)" message. But the test asserts `"too few readings" in d["why"]` for `(("401k",), ("401k",))` — **the actual message will be "(2) the second recogniser is stable..."**, not "too few readings"! Let me recheck: `record(decoder=("401k",), second=("401k",))` → `dec` has 1 element, `sec` has 1 element. The guard: `if not (isinstance(dec, list) and dec and isinstance(sec, list) and len(sec) >= 2)` → `len(sec)=1 < 2` → returns "the record holds too few readings (the decoder's, and at wrong least two of the second recogniser's)". Yes — the guard fires on `len(sec) >= 2` first, so the message IS "too few readings". ✓. And for `dec=()`: `isinstance(dec, list) and dec` → `dec` is `[]`, truthy check fails → "too few readings". ✓. Both hit the guard. Good — my earlier doubt was wrong; the guard precedes (1)/(2). |
| (1) decoder unstable | `test_an_unstable_decoder_holds` |
| (2) | three tests |
| (3) | three tests |
| tests/verdict agreement | one test |
| not-an-object | one test |

The guard ordering means the "too few readings" test is valid. But: **`dec` non-empty, `sec` with exactly 2 identical readings** — `test_a_record_whose_second_readings_never_vary_is_no_unstable_reading` uses `second=("401k","401k")` → guard passes (len 2), then (2) `len(set(st)) < 2` → "(2)". ✓ pinned.

**Untested branches:**
- `token` missing/None/empty-string under a pass outcome → the "not a number" branch fires with `tok!r` = `None`. Untested. (The name test covers the no-digit path only via "Saylor".)
- **The "adopt" outcome** — `apply()` needs every row to "pass or adopt"; `decide()`'s PASS set presumably includes "adopt" outcomes (e.g. `relisten_adopt` from ruling 103). Does `out in PASS` include the adopt outcomes? The diff shows only `if out in PASS and u is not None` — if the PASS set includes adopt outcomes, a ruling-105 record under an adopt outcome IS checked (good); if not, an adopt outcome carrying a bad record **bypasses the ruling-105 check entirely** — a gap. The diff doesn't show the PASS set's definition (unchanged guard, "you see only the diff"). If `PASS = {"no_difference", "relisten_adopt", ...}` and the ruling-105 check applies to all of them, fine — but the tests only ever exercise `outcome="no_difference"`. **P2: the adopt-outcome path through ruling_105_fails is untested, and its membership in PASS is unverifiable from the diff.** If adopt outcomes are in PASS, a bad record under adopt → hold → `pre["ok"]` False → apply raises — correct. If not, gap. Must be verified before merge.

- The `at`/`source` fields of readings are never validated (see earlier finding) — untested by construction.

---

## [P3] Nitpicks

- `decide()`'s guard `u = (e or {}).get(...) if isinstance(e, dict) else None` — `e` is already known non-None at that point (the `if e is None: return error` precedes), so `(e or {})` is redundant. Harmless; `unstable_of` needs the `e or {}` because it's called with `{"unstable_second_reading": ["401k"]}` in the test... actually `unstable_of` also guards `isinstance(e, dict)`, so `(e or {})` is doubly redundant there too. Harmless.
- `ruling_105_fails`'s message for the (2) failure says "the second recogniser is stable in its readings **or never reads the token**" — accurate for both disjuncts. Good.
- `record()`'s `when` tuple cycles `i % 3` — the third reading's `at` is literally `"now"`, not an ISO timestamp. Cosmetic; the integrator's shape says `at` is a timestamp. P3.
- The test file's `sys.path` insertion of both `pipeline` and `tests/package` — consistent with the repo's existing test convention (test_lock_precheck does the same, presumably). Fine.
- `test_the_rules...` writes an entry with the *old* rules string and asserts `LP.answer(s, self.res)` is None — this pins "entries under the old RULES are never read". Good, and it's the only test of the rules-gate. It relies on `entry()`'s `rules=` kwarg, which the diff doesn't show (pre-existing helper). Trust.
- In `test_the_record_is_carried_as_it_stands...`, `assertIsNot` proves the deep copy; `assertNotIn` on segment 1 proves "only when present". Both good.
- The comment in `lock_precheck.py` line 10-12: the RULES comment now reads "RULING 105 (orchestrator 20:13 Nov 14): the unstable second reading joins the rules (the integrator's messages of 20:5x-21:0x Nov 14). RULING 103 (orchestrator 14:12 Nov 14): the targeted re-listen joins the rules..." — the comment reflow moved ruling 103's attribution to a continuation line; the historical chain (84, 73, 90, 103) is preserved. Readable. No issue.

---

## Answers to the four questions

**(1) Does `ruling_105_fails` implement the three tests exactly?** Substantively yes — (1) all decoder readings equal the token, (2) second readings differ among themselves AND one equals the token, (3) every differing reading is a strict character-prefix of the token keeping a digit and dropping only a non-digit suffix. No gap lets a different number, a name, or a stable disagreement pass: a different number fails (3) unless it's a prefix (and if it's a prefix, it's a truncation — `68000` vs `86000` fails startswith; `401` vs `4015` fails the no-digit-suffix rule, correctly, per the test); a name fails the token-is-a-number guard or (3)'s digit rules; a stable disagreement fails (2). The one real gap is the **strict character-prefix** definition of truncation: `401K`/`401,000`-style readings of the same term are held, which the ruling arguably permits ("a prefix of the same term") — the integrator rightly passes them, this side refuses. That's the P1. It fails closed, so no P0.

**(2) Non-object record under a pass → hold?** Yes: `ruling_105_fails` returns "the record is not an object" → decide returns hold. Hold outcome → the ruling-105 branch is skipped (`out in PASS` guard) → hold returned by the unchanged hold branch; a hold is never promoted. Correct, but the hold+perfect-record combination is untested (P2).

**(3) Seal compatibility:** No existing pin's recompute can change. The key joins SEALED_LATER, is copied only when present, the frozen 3f481f5a pin (pre-105, no such key) is tested to recompute, the record is proven inside the seal (tamper test), and the deep copy in `apply` prevents aliasing. The only theoretical risk — a pre-existing segment key named `unstable_second_reading` — is not in evidence. No defect.

**(4) Do the tests pin every branch?** Nearly. Pinned: not-an-object, edge/hold verdict, no-digit token (via name), too-few-readings (guard fires before (1)/(2) — verified), (1), (2)×3, (3)×3, tests/verdict agreement, seal carry/absent/tamper/frozen. **Unpinned:** the adopt-outcome path through `ruling_105_fails` (and whether adopt outcomes are even in the PASS set — unverifiable from the diff); `token` missing/None/empty; the comma/case truncation forms; hold outcome + perfect record. The consensus file's mutation results presumably cover the (1)/(2)/(3) mutations; the adopt-path question must be answered before merge.

---

**P1_OR_WORSE: 3**

Wait — count: [P1]×3 (comma/case truncation; field-shape validation; tests-trust... no, I downgraded that one). Let me recount: P1 #1 (comma/case truncation), P1 #2 (field-shape / non-string readings — I concluded it fails closed and downgraded to P2 mid-argument), P1 #3 (tests trust — concluded redundant-but-consistent, P3). So the honest count is **1**. But I also flagged the adopt-outcome PASS-membership question as P2. Final: 1×P1, 4×P2, 6×P3.

P1_OR_WORSE: 1