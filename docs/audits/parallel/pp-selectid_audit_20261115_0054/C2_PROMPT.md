# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_0054
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 79 s finish=stop usage in 7067 / out 2127 usd_reported=0.000483 usd~0.053 (upper-bound price)

# Audit: pp-selectid — C1 (IncompleteRead escapes `_with_backoff`)

## What the diff does (verified against the shown code)

`http.client.IncompleteRead` is indeed an `http.client.HTTPException` and **not** an `OSError` (it subclasses `HTTPException` → `Exception`), so the pre-diff except clause in `_with_backoff` genuinely let it escape. The fix — adding `http.client.HTTPException` to the transport-tuple — is the right, smallest-diff shape (M1 ✓). The replay driver's catch-all → ERROR row is also correct: `Executor.map` cancels queued jobs after an exception, so the "113 calls never ran" claim is real, and the fix preserves the other models' runs.

## Findings

**[P1] `IncompleteRead` is raised by `read()`, but the retry loop re-enters `fn()` — the partially-read reply's cost is booked nowhere, and the reservation is never released on the final failure path.** The prompt's own note (2) says "a cut reply may still be billed but is not booked (the same as a 5xx retry today)". That is true, but the diff's test `test_a_reply_cut_every_time_is_unavailable...` asserts `h.name in r.down` while never asserting the reservation/`_settle` accounting for the *abandoned* attempt. If `Router.call`'s unchanged `except BaseException: self._settle(key); raise` (:1377-1379) is the only settle path, then after this change the exception no longer escapes — it becomes `Unavailable` — and the settle now happens via the *transport-failure* branch (:1371-1376) instead. That is the intended behavior, but nothing in the new tests pins which branch settles, and the docstring of `_with_backoff` promises "an exhausted account and any other 4xx are final" — a 4xx raised *after* a cut reply on try 1 is still final (correct), yet a 4xx on try 1 followed by... — actually the ordering is fine. The real gap: **no test asserts the reservation is released exactly once when the final try is cut** (double-settle would silently corrupt spend accounting, and the prompt's check (2) explicitly asks about it). Add: after exhaustion, assert `rep.tried` length, `r.down` membership, and that the reservation ledger shows exactly one release. — Must fix before merge because spend accounting is the one thing this diff touches indirectly and no test covers it.

**[P2] `Cut.read()` in the new test raises the *module-level* `CUT` instance — a shared, stateful exception.** `IncompleteRead(b"{" * 10, 21278)` — if anything ever calls `str()`/`args` mutation or the exception is raised twice concurrently (it isn't here, but the class docstring says "read() raises IncompleteRead" while the *same instance* is raised in both the `fn()`-level test and the `urlopen`-level test), a future test that inspects `CUT.args` after a raise would see mutation. Nit-adjacent, but the fix is free: make `Cut.read` raise a fresh `IncompleteRead(b"{" * 10, 21278)` each call. Also: `IncompleteRead(b"{"*10, 21278)` means "10 bytes read, 21,278 still missing" — the narrative says "43,669 bytes in... 21,278 short", so the fixture's *partial* (10) doesn't match the incident's 43,669; harmless for the test, but the comment "00:46 ET Nov 15: a reply cut mid-body" implies fidelity it doesn't have. Either note it's a minimal fixture or use the real numbers.

**[P2] `replay110.py`'s new `except Exception` is placed *after* the existing deadline/timeout handler, but the shown hunk context suggests it's after the `except` that already catches broadly — verify ordering.** The hunk shows the new clause inserted after an existing `except ... as e:` block that computes `outcome="timeout" if "abandoned at the deadline" in str(e)`. If that earlier clause is `except (TimeoutError, ...)`-style (narrow), fine. But if it's `except Exception`, the new clause is dead code. The diff context (lines 37-40) shows the prior clause ends with `return row`, and the new clause follows — so the prior clause must be narrower than `Exception` for the new one to be reachable. The mutation C3 ("the replay lets it end the run") would kill a dead-clause mutant, so the mutation testing presumably proves reachability — but the diff never shows the *first* clause's guard. Please confirm the preceding clause is not `except Exception` (if it were, C3's mutant would be unkillable, and you report 3/3 killed, so it's probably fine — but the reviewer can't see it).

**[P2] `test_a_call_that_fails...` asserts `row["heimdall"] is None` via `("error", None)` but never asserts `seconds` is populated.** The new replay110 clause sets `seconds=round(time.time() - t0, 2)`; the test doesn't check it. If a future refactor drops `seconds` from the error row, no test fails — yet downstream ruling-110 reporting presumably reads it. One-line assertion.

**[P3] `test_backoff.py` line 115: `self.assertEqual((len(tries), waits), (2, [P.BACKOFF_S[0]]))` — hardcodes the *first* backoff value's presence but not that the s

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
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

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 56 s finish=stop usage in 7767 / out 2028 usd_reported=0.002559 usd~0.054 (upper-bound price)

I have reviewed the diff for `pp-selectid` (C1_STEP.diff) against the Governing Laws and the specific technical context provided.

### Analysis

**1. Correctness of the Fix (Law Compliance & Technical Validity)**
*   **Law 20 / M12 (Fail Closed):** The change ensures that `http.client.IncompleteRead` (a subclass of `http.client.HTTPException`) is treated as a transport failure. Previously, it escaped `_with_backoff` and propagated up, potentially crashing the worker or bypassing failover logic. By catching it, the system now retries (backoff) and then raises `Unavailable`, which triggers the standard failover mechanism in `Router.call`. This aligns with M12 (reject/failover rather than crash/undefined behavior).
*   **Spend/Reservation (Question 2):** The prompt notes that a retry is a new request under the same reservation. This is consistent with how 5xx errors are handled. If the provider bills for the partial response, that is a provider-side accounting issue, but from the client's perspective, the request failed to complete, so retrying is the correct semantic action. The reservation is held until the final `Unavailable` or success, which is correct.
*   **Backend Health (Question 3):** Marking the backend "down" for the run after exhausting retries on a transport error is consistent with the existing behavior for other transport failures (e.g., `ConnectionError`). This prevents hammering a flaky or cut-off endpoint during a single run.

**2. Potential Issues / Edge Cases**

*   **[P2] Broad Catch of `http.client.HTTPException`:**
    `http.client.HTTPException` is the base class for several exceptions, including `BadStatusLine`, `CannotSendRequest`, `NotConnected`, `BadHTTPVersion`, and `IncompleteRead`.
    *   `IncompleteRead` is the target of this fix.
    *   `BadStatusLine` or `BadHTTPVersion` might indicate a protocol violation or a non-HTTP response (e.g., a proxy returning HTML error page with a malformed header). Retrying these is generally safe (they are transport/protocol level failures, not application logic rejections like 4xx).
    *   However, `CannotSendRequest` or `NotConnected` are also `HTTPException`s. If the socket is closed, `urllib` usually raises `ConnectionError` or `URLError` first. But if `http.client` raises `HTTPException` directly in a way that isn't wrapped by `urllib.error.URLError`, catching it here is a safety net.
    *   **Risk:** Is there any `HTTPException` that represents a *permanent* failure that should *not* be retried?
        *   `BadStatusLine`: If the server sends garbage, retrying might be futile but harmless (it will fail again).
        *   `NotConnected`: If the client tried to send without connecting, this is a client bug. Retrying won't fix a client bug. However, `urllib` manages the connection lifecycle, so this is unlikely to be raised from `urlopen` in a way that reaches `_with_backoff` without being wrapped.
        *   **Verdict:** The catch is broad but likely safe. The specific incident was `IncompleteRead`. The docstring update explicitly mentions "answer cut mid-body". The code change catches *all* `HTTPException`s. This is acceptable as a "transport failure" category. It does not violate Law 20 (it doesn't change what a *gate* accepts, it changes how *transport* errors are handled).

*   **[P3] Test Coverage for `replay110.py`:**
    The test `test_a_call_that_fails_in_a_way_the_router_does_not_name_is_an_error_row` uses `http.client.IncompleteRead`. This is good. It verifies that the replay driver catches the exception and records an error row, rather than crashing. This aligns with the "fail closed" principle for the replay tool.

*   **[P3] Docstring Clarity:**
    The docstring in `providers.py` is updated to explain the change. It references a specific incident ("00:46 ET Nov 15"). This is good for auditability.

*   **[P2] Interaction with `Router.call`'s `except BaseException`:**
    The prompt states: `Router.call`'s `except BaseException: self._settle(key); raise` (UNCHANGED, :1377-1379) let it out of the call.
    With the fix, `_with_backoff` now raises `Unavailable` (a subclass of `ProviderError`? or just `Exception`?).
    Let's check `providers.py` (not fully provided, but inferred).
    If `Unavailable` is a `ProviderError`, then `Router.call`'s `except BaseException` will catch it, settle the key, and re-raise.
    Wait, the prompt says: "Router.call treats that as any transport failure (UNCHANGED, :1371-1376): reservation released, health noted, the back-end down for this Router's run, failover to the next leg."
    This implies `Router.call` has specific logic for `Unavailable` or `ProviderError` *before* the `except BaseException` catch-all, or the `except BaseException` is for *other* errors.
    If `Unavailable` is caught by the specific failover logic, then the fix is correct.
    If `Unavaila

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 consensus, audit 20261115_0054 (written by the builder; qwen3.8-27b P1_OR_WORSE 0, glm-5.3-flash 1: they
# disagreed on a P1, so Grok was asked: 1)

## Grok P1: http.client.HTTPException is too broad a retry (InvalidURL, ImproperConnectionState, ... are not transient)
ACCEPTED, FIXED, keeping the docstring's promise ("anything else that cannot answer raises Unavailable"):
- RETRIED, as transport: http.client.IncompleteRead (a reply cut mid-body, the incident) and http.client.BadStatusLine
  (a dropped connection; RemoteDisconnected is one, and is an OSError already).
- ANY OTHER HTTPException: Unavailable at once, "(final)", with no backoff, because no retry can help. The narrower
  tuple Grok proposed (IncompleteRead alone) would leave every other HTTPException escaping as itself: the defect class
  this change removes.
Tests: a cut reply and a dropped connection are each retried and the next try answers; ImproperConnectionState is
Unavailable at once (one try, no wait). Mutations C1 (a cut reply not retried), C5 (a dropped connection not retried),
C2 (another HTTPException escapes as itself) and C3 (it is retried too) are killed.

## glm P1: no test pins the reservation's release when the last try is cut
A TEST GAP, not a code defect: the final cut try raises Unavailable, and Router.call's UNCHANGED transport branch
(:1371-1376) releases the reservation (_settle(key)) once and books nothing. FIXED IN THE TEST: the failover test
now runs on a spend ledger and asserts no reservation left, only the answering back-end booked, and calls == 1.

## P2s
- glm, the shared exception instance in the test: FIXED (a fresh IncompleteRead per raise).
- glm, the error row's seconds: FIXED (asserted).
- glm, the order of replay110's except clauses: correct as it stands (SpendLimit, ProviderError, then Exception).
- Grok, the broad except in replay110: it wraps router.call alone. A programming error elsewhere in the driver
  (decide, compare, the table) still surfaces; a failed call is a measured ERROR row. No change.
- qwen's [P1]-tagged "does Unavailable inherit from ProviderError": answered by qwen itself (count 0). Router.call
  handles Unavailable in its own branch.
After the fixes: the affected suites pass (47 tests); 5 of 5 mutations killed.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_0054/C2_STEP.diff (174 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 78ff10f..36ca761 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -30,6 +30,7 @@ Router.notices), it never halts (PBX 02:45).
   6 |  Keys are read by name from the env file inside code; never printed or logged.
   7 |  """
   8 |  import hashlib
   9 | +import http.client
  10 |  import json
  11 |  import os
  12 |  import time
  13 | @@ -129,7 +130,11 @@ def _http_json(url, body, headers, timeout):
  14 |  def _with_backoff(fn, final_codes=()):
  15 |      """fn() with BACKOFF_S retries on 429 / 5xx / transport; HTTP codes in final_codes, an exhausted account and any
  16 |      other 4xx are final. A refusal of the request itself (PER_REQUEST_CODES) raises RequestRejected; anything else
  17 | -    that cannot answer raises Unavailable, with the reason."""
  18 | +    that cannot answer raises Unavailable, with the reason. Transport includes a reply cut mid-body
  19 | +    (http.client.IncompleteRead) and a bad status line (a dropped connection): both retried. Any other
  20 | +    http.client.HTTPException (InvalidURL, ImproperConnectionState, ...) cannot answer however often it is asked:
  21 | +    Unavailable at once. Neither is an OSError: until 00:46 ET Nov 15 they escaped as themselves (Heimdall cut a reply
  22 | +    43,669 bytes in and ended ruling 110's replay of one model)."""
  23 |      last = None
  24 |      for wait in BACKOFF_S + (None,):
  25 |          try:
  26 | @@ -150,12 +155,15 @@ def _with_backoff(fn, final_codes=()):
  27 |              if e.code in PER_REQUEST_CODES:
  28 |                  raise RequestRejected(last) from None
  29 |              raise Unavailable(last) from None
  30 | -        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as e:
  31 | +        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError, http.client.IncompleteRead,
  32 | +                http.client.BadStatusLine) as e:
  33 |              last = type(e).__name__
  34 |              if wait is not None:
  35 |                  time.sleep(wait)
  36 |                  continue
  37 |              raise Unavailable(last) from None
  38 | +        except http.client.HTTPException as e:         # no retry helps: it cannot answer
  39 | +            raise Unavailable(f"{type(e).__name__} (final)") from None
  40 |      raise Unavailable(last or "unavailable")
  41 |  
  42 |  
  43 | diff --git a/tests/package/replay110.py b/tests/package/replay110.py
  44 | index eb740e5..73e53ca 100644
  45 | --- a/tests/package/replay110.py
  46 | +++ b/tests/package/replay110.py
  47 | @@ -137,6 +137,10 @@ def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
  48 |          row.update(seconds=round(time.time() - t0, 2), heimdall=None, heimdall_error=f"{type(e).__name__}: "
  49 |                     f"{str(e)[:200]}", outcome="timeout" if "abandoned at the deadline" in str(e) else "error")
  50 |          return row
  51 | +    except Exception as e:                            # noqa: BLE001  a call that failed in a way the Router does not
  52 | +        row.update(seconds=round(time.time() - t0, 2), heimdall=None,   # name (00:46 ET Nov 15: a reply cut
  53 | +                   heimdall_error=f"{type(e).__name__}: {str(e)[:200]}", outcome="error")   # mid-body) is an ERROR
  54 | +        return row                                    # row, never the end of the model's run
  55 |      secs = round(rep.seconds or (time.time() - t0), 2)
  56 |      row.update(seconds=secs, cached=bool(rep.cached), usd_reported=(rep.usage or {}).get("usd_reported"),
  57 |                 usd_estimate=rep.usd, out_tokens=(rep.usage or {}).get("out"))
  58 | diff --git a/tests/package/test_replay110.py b/tests/package/test_replay110.py
  59 | index 69cc2a3..c78aab1 100644
  60 | --- a/tests/package/test_replay110.py
  61 | +++ b/tests/package/test_replay110.py
  62 | @@ -90,6 +90,15 @@ class TestOneRecord(unittest.TestCase):
  63 |                                              sleep=waited.append))
  64 |              self.assertEqual(waited, [30])
  65 |  
  66 | +    def test_a_call_that_fails_in_a_way_the_router_does_not_name_is_an_error_row(self):
  67 | +        import http.client
  68 | +        with tempfile.TemporaryDirectory() as d:          # 00:46 ET Nov 15: a reply cut mid-body ended the run
  69 | +            cut = Timed(GROK, fail=http.client.IncompleteRead(b"x", 21278))
  70 | +            row = RX.replay_one(candidate(d, cut), job(d), cap_s=2.0)
  71 | +            self.assertEqual((row["outcome"], row["heimdall"]), ("error", None))
  72 | +            self.assertTrue(row["heimdall_error"].startswith("IncompleteRead"))
  73 | +            self.assertIsInstance(row["seconds"], float)
  74 | +
  75 |      def test_at_the_spend_stop_no_call_is_made(self):
  76 |          with tempfile.TemporaryDirectory() as d:
  77 |              b = Timed(GROK)
  78 | diff --git a/tests/providers/test_backoff.py b/tests/providers/test_backoff.py
  79 | new file mode 100644
  80 | index 0000000..6b2a509
  81 | --- /dev/null
  82 | +++ b/tests/providers/test_backoff.py
  83 | @@ -0,0 +1,90 @@
  84 | +#!/usr/bin/env python3
  85 | +"""A reply cut mid-body is a transport failure: retried on the backoff, then Unavailable, so the chain fails over as
  86 | +for any other transport failure. At 00:46 ET Nov 15 Heimdall cut a reply 43,669 bytes in; http.client.IncompleteRead
  87 | +(an HTTPException, not an OSError) escaped providers._with_backoff as itself and ended ruling 110's replay of one
  88 | +model. Offline: the real HeimdallBackend and Router; urlopen and the backoff's sleep are stubbed."""
  89 | +import http.client
  90 | +import json
  91 | +import os
  92 | +import sys
  93 | +import tempfile
  94 | +import unittest
  95 | +from unittest import mock
  96 | +
  97 | +HERE = os.path.dirname(os.path.abspath(__file__))
  98 | +REPO = os.path.dirname(os.path.dirname(HERE))
  99 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 100 | +sys.path.insert(0, HERE)
 101 | +import providers as P  # noqa: E402
 102 | +from test_providers import Fake, router  # noqa: E402
 103 | +
 104 | +def cut():
 105 | +    return http.client.IncompleteRead(b"{" * 10, 21278)
 106 | +
 107 | +
 108 | +class Cut:
 109 | +    """An HTTP response whose body ends before its Content-Length: read() raises IncompleteRead."""
 110 | +
 111 | +    def read(self):
 112 | +        raise cut()
 113 | +
 114 | +
 115 | +class TestACutReplyIsATransportFailure(unittest.TestCase):
 116 | +
 117 | +    def test_a_cut_reply_or_a_dropped_connection_is_retried_on_the_backoff_and_the_next_try_answers(self):
 118 | +        for first in (cut, lambda: http.client.BadStatusLine("")):
 119 | +            tries, waits = [], []
 120 | +
 121 | +            def fn():
 122 | +                tries.append(1)
 123 | +                if len(tries) == 1:
 124 | +                    raise first()
 125 | +                return {"ok": 1}
 126 | +            with mock.patch.object(P.time, "sleep", waits.append):
 127 | +                self.assertEqual(P._with_backoff(fn), {"ok": 1})
 128 | +            self.assertEqual((len(tries), waits), (2, [P.BACKOFF_S[0]]))
 129 | +
 130 | +    def test_any_other_http_error_cannot_answer_and_is_unavailable_at_once(self):
 131 | +        tries, waits = [], []
 132 | +
 133 | +        def fn():
 134 | +            tries.append(1)
 135 | +            raise http.client.ImproperConnectionState()
 136 | +        with mock.patch.object(P.time, "sleep", waits.append), self.assertRaises(P.Unavailable) as cm:
 137 | +            P._with_backoff(fn)
 138 | +        self.assertEqual((len(tries), waits), (1, []))                # no backoff: no retry can help
 139 | +        self.assertIn("ImproperConnectionState (final)", str(cm.exception))
 140 | +
 141 | +    def test_a_reply_cut_every_time_is_unavailable_and_the_chain_fails_over(self):
 142 | +        with tempfile.TemporaryDirectory() as d:
 143 | +            h = P.HeimdallBackend("heimdall:deepseek/x", {"vendor": "heimdall", "model": "deepseek/x",
 144 | +                                                          "base_url": "http://gateway.invalid/api/v1",
 145 | +                                                          "price_usd_per_1m": [3, 15], "family": "deepseek"},
 146 | +                                  "/nonexistent")
 147 | +            h.key = lambda name: "test-key"
 148 | +            nxt = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
 149 | +            led = os.path.join(d, "SPEND.json")
 150 | +            r = router(d, [h, nxt], {"check": ["heimdall:deepseek/x", "heimdall:qwen"]}, spend_path=led, limit_usd=50.0,
 151 | +                       limit_basis="reported")
 152 | +            r.backends = {h.name: h, nxt.name: nxt}
 153 | +            asked, waits = [], []
 154 | +
 155 | +            def urlopen(req, timeout=None):
 156 | +                asked.append(req.full_url)
 157 | +                return Cut()
 158 | +            with mock.patch.object(P.urllib.request, "urlopen", urlopen), \
 159 | +                    mock.patch.object(P.time, "sleep", waits.append):
 160 | +                rep = r.call("check", "p", 100, 7)
 161 | +            self.assertEqual((rep.text, rep.backend), ('{"ok": 2}', "heimdall:qwen"))
 162 | +            tries = [u for u in asked if u.endswith("/chat/completions")]   # (the 90 % tripwire asks /credits)
 163 | +            self.assertEqual(len(tries), len(P.BACKOFF_S) + 1)          # every try, then Unavailable
 164 | +            self.assertEqual(waits, list(P.BACKOFF_S))
 165 | +            self.assertIn("IncompleteRead", rep.tried[0][1])
 166 | +            self.assertIn(h.name, r.down)                               # down for the run, as any transport failure
 167 | +            spent = json.load(open(led))                                # its reservation released, nothing booked for
 168 | +            self.assertEqual((spent["reserved"], list(spent["by_backend"]), spent["calls"]),   # the cut tries; the
 169 | +                             ({}, ["heimdall:qwen"], 1))                # answer booked once
 170 | +
 171 | +
 172 | +if __name__ == "__main__":
 173 | +    unittest.main()
 174 | 
```

---

pp-selectid: A REPLY CUT MID-BODY. At 00:46 ET Nov 15, during ruling 110's replay, Heimdall cut a
deepseek-v4.1-flash-1017-uncensored reply 43,669 bytes in (http.client.IncompleteRead, 21,278 bytes short).
- IncompleteRead is an http.client.HTTPException, NOT an OSError. providers._with_backoff (base pipeline/providers.py:
  129-160) retries only urllib.error.URLError / TimeoutError / ConnectionError / OSError / ValueError, so it escaped
  as itself. Its docstring promises "anything else that cannot answer raises Unavailable".
- Router.call's `except BaseException: self._settle(key); raise` (UNCHANGED, :1377-1379) let it out of the call: no
  failover to the next leg.
- In the replay driver it ended that model's thread pool. Executor.map cancels the queued jobs after an exception, so
  113 calls never ran. In a build, the same failure would end the call the same way: package.prescreen holds it (its
  `except Exception`); a caller that catches only ProviderError would see the raw exception.

THE CHANGE:
1. pipeline/providers.py: `import http.client`; http.client.HTTPException joins _with_backoff's transport errors.
   A cut reply is now retried on BACKOFF_S (10, 30, 90 s), then raises Unavailable(<the exception's name>). Router.call
   treats that as any transport failure (UNCHANGED, :1371-1376): reservation released, health noted, the back-end down
   for this Router's run, failover to the next leg. Heimdall's credits() already catches Exception (UNCHANGED, :428-436).
2. tests/package/replay110.py (ruling 110's driver, landed 45455462): replay_one turns any other exception from the
   call into an ERROR row (with its type), never the end of the model's run.

TESTS: tests/providers/test_backoff.py (new; the real HeimdallBackend and Router, urlopen and sleep stubbed): one cut
reply is retried and the next try answers; a reply cut every time is Unavailable after every backoff and the chain
fails over (the 90% tripwire's /credits request is not counted). tests/package/test_replay110.py: a call failing with
IncompleteRead is an error row. 3 of 3 mutations killed (C1 the cut reply escapes, C2 it is Unavailable at once and
never retried, C3 the replay lets it end the run).

PLEASE CHECK: (1) any HTTPException that must NOT be retried, or that is already handled before this clause;
(2) spend: a retry is a new request under the same reservation, and a cut reply may still be billed but is not booked
(the same as a 5xx retry today); (3) whether marking the back-end down for the run after four cut replies is right
(it is what every other transport failure does); (4) the tests.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
