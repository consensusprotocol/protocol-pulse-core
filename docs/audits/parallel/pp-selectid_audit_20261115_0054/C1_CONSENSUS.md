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
