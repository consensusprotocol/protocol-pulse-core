# glm-5.3-flash (z-ai/glm-5.3-flash) 78 s finish=stop usage in 6151 / out 2825 usd~0.061 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-1138b (final review)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against the three Cycle 1 outputs:

- **GLM's verification note on the placement of the `why` chain inside the `try`** — I did not explicitly trace whether the `why = (...)` chain (diff lines 18–23) sits inside or outside the `try`. GLM resolved it from the hunk header (old `except` at ~1018 immediately follows the chain's last line at ~1017) and concluded the chain is inside, so a non-dict `sc` raising `AttributeError` at `sc.get("kind")` is caught. That placement question is the linchpin of the whole fail-closed argument and I should have stated it. **Missed.**
- **GLM's note that the `why` string format changed** (now prefixed `stage: `) and that any downstream consumer doing exact-match or regex on the old format would break — I did not raise the format-compatibility question at all. The tests only use `startswith`, which is safe, but the consumer-compat question was legitimately raised and I missed it. **Missed.**
- **QWEN's P2-2: the `why`-chain record (lines 31–33) lacks `path`** while the except branch now records it — an asymmetry between the two failure paths. I did not notice the inconsistency. **Missed.**
- **QWEN's P2-3/P2-4** (the `startswith("open: FileNotFoundError")` assertion is valid; the missing-`verdicts` test asserts the scorer fields are kept) — these are confirmations, not findings; nothing to miss.
- **GROK** returned no findings; nothing to miss there.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| GLM: `why` chain inside `try` (verification note, not a finding) | **Agree** | The hunk header arithmetic (chain ends ~1017, old `except` at ~1018) supports it; also the *new* test at diff lines 52–56 empirically proves it: `{"scorer": ["moments"], "verdicts": {}}` → `sc` is a list, `sc.get("kind")` at line 18 raises `AttributeError`, and the test asserts the record's `why` starts `"shape: AttributeError"` — which only happens if the chain's exception was caught by the `except`. The test is itself the proof. |
| GLM P1-1: no test exercised a non-dict `"scorer"` (the case the `isinstance` guard exists for) | **Agree — and it is now fixed** | The increment adds exactly that test (diff lines 52–56): `{"scorer": ["moments"], "verdicts": {}}` → asserts `idx == {}`, `read` False, `"kind" not in rec` (guard correctly omits the fields), `why` starts `"shape: AttributeError"`. This closes the coverage gap precisely. |
| GLM: `why` format change could break exact-match consumers | **Partially agree** | Real risk in principle, but not verifiable from the diff — I cannot see the consumers. The tests shown use `startswith`. Recorded as a P2 verification note, not a blocker. |
| QWEN P1-1 (retracted in its own text): `sc.get` on non-dict escapes the except | **Agree with the retraction** | The conditional expression `**({...} if isinstance(sc, dict) else {})` evaluates the condition first; when `sc` is a list/str/None, `sc.get` is never called. Also, when `sc` is a non-dict, the *chain* (line 18) raises before the except, and the chain is inside the try (see above), so the except's guard is doubly redundant-but-correct. QWEN's self-correction is accurate. |
| QWEN P2-2: `why`-chain record lacks `path` | **Agree** | Diff lines 31–33 record `kind/event/scorer_sha/render_scorer_sha/threshold` but not `path`. The except branch records `path`. Inconsistent diagnostic completeness; the `why`-chain failure is the *more likely* failure in practice (wrong kind/sha/threshold), so its record arguably needs `path` more. P2 — the caller obviously knows the path it passed, so it's diagnostic redundancy, not correctness. |
| QWEN P2-1: `stage = "open"` before `try` is correct | **Agree** | If `open()` raises, `stage` is still `"open"`; `parse` is set before `json.load`; `shape` before the key reads. Stage attribution is accurate on every path. |
| GLM G1–G4 (recorded, no change) | **Agree, correctly recorded** | G2 (a recorded threshold can be non-numeric) is right: the record is informational; the gate (`stand_alone.affirmed` / the `num()` check in the chain) refuses it independently. G3: the non-ASCII test (diff lines 64–67) checks the pin through `affirmed_verdict` and separately asserts `PK.text_sha(t) == hashlib.sha256(t.encode("utf-8")).hexdigest()` — that *is* a direct check of the pin's sha convention against the build's, on a text with curly quotes, accents, an em dash, and an emoji (multi-UTF-16-unit, so it also exercises any surrogate-pair mishandling). Adequate. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-N1 — `tests/package/test_medley.py:46–51`: the "missing verdicts" test's `odd_shape` fixture is reused and overwritten, but the *first* write (line 47–48) omits `"verdicts"` while the second (lines 52–53) includes it — the second test's `why` assertion depends on the *first* test's file having been rewritten, which it is (line 52, `open(odd_shape, "w")` truncates).** Verified: the second `open(..., "w")` truncates, so no cross-test contamination. No finding — recorded as a check that passed.

**P2-N2 — `pipeline/package.py:29–30`: the except-branch record's scorer fields use `sc.get(k)`, which can yield `None` for a *present-but-None* key, indistinguishable in the record from an absent key.** Concrete scenario: `{"scorer": {"kind": "moments", "event": None, ...}, "verdicts": <malformed>}` → the record shows `"event": None` both when the key is absent and when it is explicitly null. The `why`-chain path (line 19) has the same convention (`sc.get("event", "absent")` distinguishes, but the *record* does not). Cosmetic; the record is diagnostic, not a gate. Nobody flagged this in Cycle 1; it is the only genuinely new (if minor) observation.

**P2-N3 — `pipeline/package.py:27`: the 160-char truncation now applies only to the message, but the *stage prefix and exception type* are prepended outside it, so the total `why` length is unbounded only by those additions (~10–30 chars) — fine. However, `str(e)` for `OSError`/`UnicodeDecodeError` can embed the full path, and the record *also* carries `path` separately, so the message can duplicate the path and eat the 160 budget.** Concrete: a deeply nested path + `UnicodeDecodeError` (which includes position/byte info) → the message's useful tail (the actual decode error) can be truncated. Purely diagnostic; the stage + exception type survive. P2, informational.

Nothing rises above P2. In particular, verified yet again, independently:

- **Fail-closed:** every failure path returns `{}` as the first element — the except branch (line 27) and the `why` chain (lines 31–33). No path returns a verdict derived from a file that failed any check. The success path is unchanged by this diff (only the failure record and the reads' splitting changed; the chain's conditions, lines 18–23, are byte-identical in logic).
- **No exception escapes the except:** `stage`/`sc` are initialised before the `try` (line 9); the only operations in the except are `f`-string formatting of `stage`/`type(e).__name__`/`str(e)[:160]`, `path`, `code_sha`, and the guarded comprehension. `str(e)` cannot raise for these exception types. The `**`-unpack of a conditional expression is valid Python 3.5+.
- **Split reads:** `sc = d["scorer"]` (line 16) then `vs = d["verdicts"]` (line 17) — if `"verdicts"` is missing, `sc` is already populated, which is exactly what the new record's guard exploits, and the new test (lines 49–51) proves the scorer fields survive.
- **Tests:** the three new/extended assertions (lines 43–45, 46–51, 52–56) each exercise one distinct failure mode (missing file → stage "open" + path + sha; missing "verdicts" → stage "shape" + scorer fields kept; non-dict "scorer" → guard drops fields, no escape). The non-ASCII test (lines 64–67) covers the sha agreement. All assertions match the code's actual behavior as traced.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Fail-closed correctness (`pipeline/package.py:9–33`) | PASS | PASS | Unchanged; re-verified independently. The diff touches only the failure record, not the verdict logic. |
| Except-branch safety (no escape) | PASS | PASS | GLM's placement analysis + the new non-dict-`scorer` test close the one open question (chain inside try) with empirical proof. |
| Diagnostic record completeness | (not scored) | PASS− | Except branch now rich; the `why`-chain record still lacks `path` (QWEN P2-2) — the only asymmetry. |
| Test coverage | (not scored) | PASS | All three cycle-1 coverage gaps (missing-file record, missing-`verdicts` retention, non-dict-`scorer` guard) now have tests; non-ASCII sha test added. |
| Consumer compatibility of the `why` format | (not scored) | PASS− | Format changed (`stage: ` prefix); unverifiable from the diff; tests use `startswith`. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none.

**P2 MEDIUM:**
1. `pipeline/package.py:31–33` — the `why`-chain failure record omits `path` (and, unlike the except branch, cannot; add `"path": path` for symmetry). (QWEN P2-2, agreed.)
2. `pipeline/package.py:29–30` — `sc.get(k)` yields `None` for both absent and explicitly-null keys; consider a sentinel if the distinction matters to the integrator's diagnostics. (New, minor.)
3. `pipeline/package.py:27` — `why`-format change (`stage: ` prefix): confirm no downstream consumer exact-matches the old format. (GLM, unverifiable from diff.)
4. `pipeline/package.py:27` — path duplication between the `why` message and the `path` key can waste the 160-char message budget on long paths. (New, informational.)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add `"path": path` to the `why`-chain record at `pipeline/package.py:31–33` — it is the one remaining asymmetry between the two failure paths, it is a one-token change, and the `why`-chain failure (wrong kind/sha/threshold) is the more probable failure in production.

## 7. PRODUCTION READY?

**Yes.** Conditions (all P2, none blocking): (a) add `path` to the `why`-chain record for diagnostic symmetry; (b) confirm no downstream consumer exact-matches the old `why`-string format. The fail-closed contract holds on every path, no exception can escape the except branch (now proven by the non-dict-`scorer` test, not just argued), the record's keys match the tests, and the tests cover every failure mode this increment touches.