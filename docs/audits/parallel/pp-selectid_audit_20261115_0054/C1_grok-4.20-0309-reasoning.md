# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 25 s finish=stop usage in 7167 / out 767 usd_reported=0.017567 usd~0.055 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_0054 (C1_STEP.diff)**

**Summary**: The patch addresses a real transport failure (http.client.IncompleteRead raised 43,669 bytes into a Heimdall deepseek reply at 00:46 ET Nov 15) that escaped `_with_backoff`, bypassed Router failover, and terminated replay110's thread pool. The fix makes the exception retryable, updates the replay driver to emit an ERROR row instead of crashing the run, and adds a targeted test. The change is narrowly scoped to robustness of model calls used by editorial_select / story_semantics (L-f, L-l, L-j). No direct edits to sentence_law, editorial_select, gates, rendering, or release_auth.

**Findings**:

- **[P1]** Catching the broad `http.client.HTTPException` (new except clause) is overly permissive. The base class includes non-transient errors such as `InvalidURL`, `NotConnected`, `ImproperConnectionState`, and `HTTPVersionNotSupported`. Only `IncompleteRead` (and perhaps `RemoteDisconnected`) matched the incident; a narrower tuple `(..., http.client.IncompleteRead)` would be the smallest diff, would avoid retrying permanent configuration/protocol errors, and would better satisfy LAW 20/M2 ("never change what a check accepts") and "Smallest diff" (M1). The new test only exercises `IncompleteRead`. This is a real behavioral expansion that should be tightened before merge.

- **[P2]** `replay110.py:41` `except Exception as e: # noqa: BLE001` is a broad catch in test harness code that can swallow unexpected programming errors (only the first 200 chars of the message are kept). Although the comment explains the intent and the test added for it passes, this pattern conflicts with the fail-closed culture expressed in M12 and L-j. Prefer a more specific set of exceptions or let the outer test runner handle unexpected failures with full tracebacks.

- **[P2]** The new `test_backoff.py` (145 lines) is thorough and correctly uses the real `HeimdallBackend` + `Router` with mocked `urlopen`, but it duplicates large parts of the incident narrative already present in the commit message and providers.py docstring. This increases long-term maintenance cost for a narrow edge case. The test could be condensed while still killing the three mutations (C1–C3).

- **[P3]** Nit: `providers.py` docstring now mentions the exact incident timestamp and byte count. This is useful but ties the production comment to a one-off event; a more general statement about mid-body cuts would age better.

- **[P3]** `CUT = http.client.IncompleteRead(b"{" * 10, 21278)` in the test uses arbitrary values. While sufficient to trigger the exception, it does not match the real 43,669-byte incident size. No functional impact, but reduces fidelity of the regression test.

- **[P3]** No index changes, no DB alterations, no renderer/compositor/selector additions, no new external service calls, GPU0-only path untouched — complies with technology constraints and M1.

- **[P3]** All new test paths exercise fail-closed behavior (Unavailable → failover or ERROR row) and do not relax any gate. No violation of SENTENCE LAW, SELECTION LOCK, L-a through L-l, LAW 20/M2, M12, or v2f byte-identity requirements detected in the diff.

The core intent is sound and the regression test coverage for the exact failure mode is strong. The P1 above must be resolved (narrow the exception) for a clean merge.

**P1_OR_WORSE: 1**