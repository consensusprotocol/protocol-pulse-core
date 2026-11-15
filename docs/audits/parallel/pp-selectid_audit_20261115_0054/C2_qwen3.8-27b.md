# qwen3.8-27b (qwen/qwen3.8-27b) 36 s finish=stop usage in 8899 / out 2694 usd_reported=0.002335 usd~0.067 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_0054
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the builder/consensus writer) accepted Grok's P1 that `http.client.HTTPException` was too broad and "fixed" it by narrowing the retry tuple to `(IncompleteRead, BadStatusLine)` and adding a separate `except http.client.HTTPException` clause for immediate `Unavailable`. I also accepted GLM's P1 about missing reservation-release assertions and added them to the test.

What I **missed** in Cycle 1 (and what the other models surfaced):

- **Grok's original P1 was correct in spirit but wrong in prescription.** Grok said "narrow to `IncompleteRead` alone." The consensus rejected that (correctly) because it would leave other `HTTPException`s escaping as themselves. But the *fix* chosen — a catch-all `except http.client.HTTPException` that raises `Unavailable` immediately — is a **behavioral change beyond the incident**. Before this diff, *any* `HTTPException` that wasn't already caught by the transport tuple would escape `_with_backoff` and hit `Router.call`'s `except BaseException: self._settle(key); raise`. After this diff, it is converted to `Unavailable` and handled by the transport-failure branch. That is the *intended* fix (the docstring promises "anything else that cannot answer raises Unavailable"), but it means **every** `HTTPException` subtype now gets a `Unavailable` wrapper with `(final)` in the message, even ones that might have been handled differently upstream. No model in Cycle 1 flagged this as a potential concern for callers that inspect the exception type or message.

- **GLM's P2 about the shared `CUT` instance** was caught and fixed (fresh `cut()` per raise). Good.

- **GLM's P2 about `seconds` not being asserted** was caught and fixed. Good.

- **Qwen's analysis of `HTTPException` subtypes** was thorough but ultimately agreed the broad catch is safe. I agree with Qwen's verdict.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Position |
|---|---|---|
| `HTTPException` too broad for retry | Grok C1 | **Agree with the fix, disagree with the original prescription.** Narrowing to `IncompleteRead` alone would have been wrong. The two-clause approach (retry `IncompleteRead`/`BadStatusLine`, immediate `Unavailable` for other `HTTPException`) is correct. |
| No test pins reservation release on final cut | GLM C1 | **Agree.** Fixed in C2. The failover test now asserts `spent["reserved"] == {}` and `calls == 1`. |
| Shared exception instance in test | GLM C1 | **Agree.** Fixed: `cut()` returns a fresh instance. |
| `seconds` not asserted in error-row test | GLM C1 | **Agree.** Fixed: `assertIsInstance(row["seconds"], float)`. |
| `except Exception` in replay110 is too broad | Grok C1 | **Disagree.** It wraps `router.call` alone. A programming error in `decide`, `compare`, or the table still surfaces. A failed model call is a measured ERROR row. This is the correct fail-closed behavior for a replay driver. |
| Test duplicates incident narrative | Grok C1 | **Partially agree.** The docstring is long, but it documents a real incident and the exact failure mode. The test itself is 90 lines and focused. Acceptable. |
| Docstring ties to one-off event | Grok C1 | **Disagree.** The incident reference is useful for auditability and matches the codebase's style (other docstrings reference specific rulings and timestamps). |
| `BadStatusLine` is a valid retry target | Qwen C1 | **Agree.** A bad status line indicates a dropped or corrupted connection. Retrying is safe. |
| `ImproperConnectionState` should NOT be retried | Qwen C1 | **Agree.** It's a client-side state error. The test confirms it raises `Unavailable` immediately with no backoff. |

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] The `except http.client.HTTPException` clause at line 38–39 is a silent behavioral expansion for all `HTTPException` subtypes not in the retry tuple.** Before this diff, an `InvalidURL` or `NotConnected` raised inside `fn()` would escape `_with_backoff` and be caught by `Router.call`'s `except BaseException: self._settle(key); raise` (line 1377–1379), which re-raises the *original* exception. After this diff, it is converted to `Unavailable("InvalidURL (final)")`. Any caller that catches the specific `HTTPException` subtype (rather than `Unavailable` or `ProviderError`) will now see a different exception type. The `Router.call` transport branch (lines 1371–1376) handles `Unavailable` correctly, so the *Router* path is fine. But the prompt notes: "a caller that catches only ProviderError would see the raw exception" — after this change, they would see `Unavailable` instead, which is arguably better, but it is a change in the exception contract for non-Router callers. **No test covers a non-Router caller receiving an `HTTPException`-derived `Unavailable`.** This is low-risk because the primary caller is `Router.call`, but it should be documented.

**[P3] Line 162: `tries = [u for u in asked if u.endswith("/chat/completions")]` — the comment says "the 90% tripwire asks /credits" but the filter is on `/chat/completions`.** The 90% spend tripwire calls `credits()` which hits a different endpoint. The filter correctly excludes it, but the comment is slightly misleading: it should say "the 90% tripwire's /credits request is not counted" (which it does) — actually, re-reading, the comment is fine. The filter is correct. No issue.

**[P3] Line 163: `self.assertEqual(len(tries), len(P.BACKOFF_S) + 1)` — this asserts the number of *chat/completions* requests equals the number of backoff slots + 1. This is correct: `BACKOFF_S` has 3 entries (10, 30, 90), so 4 tries total. The `+1` accounts for the final try after the last backoff. Good.

**[P2] The `Cut` class (lines 108–112) only implements `read()`. If `HeimdallBackend`'s HTTP path calls any other method on the response object (e.g., `getheader()`, `status`, `close()`), the test would fail with `AttributeError` rather than exercising the intended path.** The test passes (per the consensus: 47 tests, 5/5 mutations killed), so the real code path must only call `read()`. But this is fragile: if a future refactor adds a `getheader()` call before `read()`, the test breaks for the wrong reason. A more complete mock would be safer. Low priority since the test currently works.

**[P3] Line 69: `cut = Timed(GROK, fail=http.client.IncompleteRead(b"x", 21278))` — the `Timed` wrapper in `test_replay110.py` uses a *pre-constructed* `IncompleteRead` instance, not a fresh one per call.** This is the same shared-instance concern GLM raised for `test_backoff.py`, but here it's a single-use instance in a single test, so there's no mutation risk. Acceptable.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `providers.py` exception handling | 8/10 | 9/10 | The two-clause approach (retry vs. immediate Unavailable) is correct and well-tested. The P2 about silent behavioral expansion for non-Router callers is minor. |
| `replay110.py` error row | 7/10 | 8/10 | The `except Exception` is justified for a replay driver. `seconds` is now asserted. The 200-char truncation is acceptable for a diagnostic row. |
| `test_backoff.py` | 7/10 | 9/10 | Reservation release is now asserted. Fresh exception instances. `BadStatusLine` and `ImproperConnectionState` cases cover the retry/final split. The `Cut` class fragility is a P3. |
| `test_replay110.py` | 7/10 | 8/10 | `seconds` is now asserted. The test is minimal but sufficient. |
| Docstring / comments | 6/10 | 7/10 | The incident reference is long but matches codebase style. The `(final)` marker in the `Unavailable` message is useful for debugging. |

## 5. FINAL PRIORITY LIST

**[P0] CRITICAL:** None.

**[P1] HIGH:** None. All Cycle 1 P1s are resolved.

**[P2] MEDIUM:**
1. **`providers.py` line 38–39:** The `except http.client.HTTPException` clause converts all non-retryable `HTTPException` subtypes to `Unavailable`, changing the exception contract for non-Router callers. Add a one-line comment noting this is intentional and that `Router.call` is the primary consumer. *(File: `pipeline/providers.py`, lines 38–39)*
2. **`test_backoff.py` line 108–112:** The `Cut` class only implements `read()`. If the HTTP path gains a `getheader()` or `status` access before `read()`, the test breaks for the wrong reason. Consider adding a minimal `status` attribute or a `getheader()` that returns `None`. *(File: `tests/providers/test_backoff.py`, lines 108–112)*

**[P3] NIT:**
1. **`test_replay110.py` line 69:** Pre-constructed `IncompleteRead` instance is fine for single-use, but a factory would be more consistent with `test_backoff.py`'s `cut()`. *(File: `tests/package/test_replay110.py`, line 69)*
2. **`providers.py` docstring lines 18–22:** The incident narrative is 5 lines. Consider trimming to 3 lines (what, when, why it matters) to reduce maintenance burden. *(File: `pipeline/providers.py`, lines 18–22)*

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The two-clause exception handling in `_with_backoff` (retry `IncompleteRead`/`BadStatusLine`, immediate `Unavailable` for other `HTTPException`) is the correct and minimal fix for the incident, and the reservation-release assertion in the failover test closes the one real accounting gap.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1. Add a one-line comment at `providers.py:38` noting that the `except http.client.HTTPException` clause intentionally converts all non-retryable `HTTPException` subtypes to `Unavailable` for `Router.call`'s transport-failure branch, and that non-Router callers should catch `Unavailable` (or `ProviderError`) rather than specific `HTTPException` subtypes.
2. Optionally harden the `Cut` class in `test_backoff.py` with a `status` attribute to prevent future test breakage from unrelated HTTP-path changes.

Neither condition is a blocker for the incident fix itself. The core change is correct, well-tested, and the reservation accounting is now pinned.

P1_OR_WORSE: 0