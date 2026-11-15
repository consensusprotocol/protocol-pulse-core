# glm-5.3-flash (z-ai/glm-5.3-flash) 69 s finish=stop usage in 8172 / out 2243 usd_reported=0.000531 usd~0.058 (upper-bound price)

# C2 AUDIT — pp-selectid-20261115_0054 (cycle 2, final)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Being honest, three things:

- **Grok's breadth argument on `http.client.HTTPException`.** I treated the broad catch as the obvious minimal fix and didn't enumerate the subclasses. Grok was right that `InvalidURL`, `ImproperConnectionState`, `NotConnected`, `HTTPVersionNotSupported` are not transient — and the builder's resolution (retry only `IncompleteRead` + `BadStatusLine`; everything else `Unavailable` at once) is *better* than Grok's proposed narrowing to `IncompleteRead` alone, because it also stops the residual defect class (any other `HTTPException` escaping as itself, which is exactly what bit at 00:46). I missed that the two-level structure was available.
- **glm's reservation-release test gap.** I noted the settle path question but didn't demand a ledger assertion. The fix (spend ledger: `reserved == {}`, `by_backend == ["heimdall:qwen"]`, `calls == 1`) is exactly the right pin — it kills the double-settle / no-settle mutant class that check (2) of the prompt asks about.
- **glm's `seconds` assertion.** Trivial, but the error row's `seconds` field was unasserted; downstream ruling-110 reporting reads it. Fixed in the diff (line 73).

## 2. AGREE / DISAGREE

- **Grok P1 (broad catch) — AGREE, and the resolution is correct.** The two-clause structure (lines 31–39) retries exactly the two transient shapes and finals the rest. One subtlety worth stating: `BadStatusLine` is a subclass of... actually it's a direct subclass of `HTTPException`, and `RemoteDisconnected` subclasses both `BadStatusLine` *and* `ConnectionResetError` — so `RemoteDisconnected` hits the *first* clause (OSError) and is retried, which is correct and consistent. The ordering of the except clauses makes this work; no issue.
- **glm P1 (reservation) — AGREE, resolved.** The ledger assertion at lines 167–169 is the strongest test in the diff. It also implicitly pins that the *cut* tries book nothing (check 2 of the prompt).
- **glm P2 (shared `CUT` instance) — AGREE, resolved** (line 104–105: `cut()` returns a fresh instance). The fixture's 10/21,278 vs. the incident's 43,669/21,278 mismatch remains — [P3], cosmetic; the *shortfall* (21,278) does match, only the partial differs.
- **Grok P2 (broad `except Exception` in replay110) — PARTIALLY AGREE, no change needed.** It wraps only `router.call`; the consensus note confirms `SpendLimit`/`ProviderError` clauses precede it, so it's the last-resort "the Router doesn't name this" row — which is precisely the incident's failure mode (an exception the Router's clauses didn't name). Narrowing it would recreate the 113-lost-calls defect. Disagree with tightening.
- **Grok P2 (test verbosity) / P3 (docstring incident timestamp) — DISAGREE.** The narrative in the test docstring is the audit trail; this project's convention (visible in every docstring shown) is incident-anchored prose. Condensing it would be a regression in this codebase's style, not an improvement.
- **qwen's analysis — AGREE.** Its conclusion that the broad catch is "likely safe" and its reservation reasoning match the final code; its unanswered [P1]-tagged question (does `Unavailable` inherit `ProviderError`?) is moot: `Router.call` handles `Unavailable` in its own branch before the `BaseException` catch-all, and the failover test proves it.

## 3. NEW FINDINGS (cycle 2)

- **[P2] `test_backoff.py` line 128: the retry-count assertion is weaker than it looks.** `self.assertEqual((len(tries), waits), (2, [P.BACKOFF_S[0]]))` pins that exactly one wait of `BACKOFF_S[0]` happened — good — but nothing pins that the *second* try's success is what returned, vs. the loop falling through. Add `self.assertEqual(tries, [1, 1])`-style ordering or assert the returned value came from the second call (it does, via `{"ok": 1}`, but a mutant that returns the *first* try's result would need the first try to succeed). Minor; the mutation C1/C5 coverage presumably covers it. Downgrade to [P3] if mutation testing already kills it.
- **[P2] `Cut.read()` (line 111–112) raises, but `_http_json` presumably calls `read()` then `json.loads`.** The `Cut` fake never returns bytes, so the success path of `_http_json` is never exercised through this fake — fine, because `Cut` is only used in the always-fails test. But note `HeimdallBackend`'s 90% tripwire calls `/credits` (line 162's comment) — that request also gets a `Cut()` response, meaning the tripwire's `IncompleteRead` is swallowed by `credits()`'s `except Exception` (UNCHANGED, :428–436). That's *correct* (the comment says the tripwire isn't counted), but it means the test silently depends on `credits()`'s breadth. If someone later narrows `credits()`'s catch, this test's `asked`-count assertion (line 163) breaks in a confusing way. [P3] — add a comment noting the dependency. Actually the comment at line 162 already says it; [P3] at most.
- **[P2] `replay110.py` line 51: the new clause's `outcome` is hardcoded `"error"`, while the preceding clause computes `outcome="timeout" if "abandoned at the deadline" in str(e)`.** If a *timeout* ever surfaces as a non-`ProviderError` exception (e.g., a `TimeoutError` variant the Router's earlier clauses don't name), the new clause would mislabel it `"error"` instead of `"timeout"`. Today the preceding clause catches it, so this is latent, not live. [P3]→[P2] borderline; I'll call it [P3] since the preceding clause demonstrably handles the deadline case (the existing test at lines 62–64 asserts the timeout path).
- **[P3] `test_replay110.py` line 69: `IncompleteRead(b"x", 21278)`** — one byte read, vs. the incident's 43,669. Same fidelity nit glm raised for the other fixture; consistent, harmless.
- **[P3] `providers.py` line 38's comment** ("no retry helps: it cannot answer") duplicates the docstring's rationale. Harmless; the inline comment earns its keep at the clause.

Nothing here rises to P1. The cycle-1 fixes landed correctly and the two-clause structure is the right final shape.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| providers.py `_with_backoff` | Good, breadth unproven | **Strong** | Two-clause structure resolves Grok's P1 *and* keeps the docstring's "anything else → Unavailable" promise; clause ordering correctly routes `RemoteDisconnected` to the OSError/retry path |
| Spend/reservation accounting | Untested (glm's gap) | **Strong** | Ledger assertion (lines 167–169) pins release-once, book-once, reserve-zero |
| replay110.py error row | Broad catch, unproven reachability | **Good** | Clause ordering confirmed (SpendLimit → ProviderError → Exception); `seconds` now asserted; `outcome` mislabeling is latent-only |
| Test fidelity | Fixture numbers ≠ incident | **Good** | Fresh-exception fix landed; 10-vs-43,669 partial mismatch remains, cosmetic |
| Mutation coverage | 3/3 claimed | **5/5 claimed** | C5 (dropped connection) added; the two-clause split is exactly what C2/C3 needed to be killable |

## 5. FINAL PRIORITY LIST

- **[P2] tests/providers/test_backoff.py:128** — strengthen the retry-order assertion (or confirm C1/C5 mutants die only via the success-value check; if so, note it). Should fix, not blocking.
- **[P3] tests/providers/test_backoff.py:105** — fixture partial (10) ≠ incident partial (43,669); the shortfall (21,278) matches. Either use 43,669 or comment "minimal fixture".
- **[P3] tests/package/test_replay110.py:69** — same fidelity nit, `b"x"`.
- **[P3] tests/package/replay110.py:51–54** — latent `outcome` mislabel if a non-`ProviderError` timeout ever reaches this clause; the preceding clause currently owns the deadline case.
- **[P3] tests/providers/test_backoff.py:162** — the tripwire-count assertion silently depends on `credits()`'s broad `except Exception`; the existing comment nearly covers it.

No P0, no P1.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The two-clause except structure in `providers.py:31–39` — it is the entire defect fix, it satisfies both Grok's narrowing argument and the docstring's promise, and the ledger test proves the money path; everything else in this diff is witness.

## 7. PRODUCTION READY?

**Yes.** Conditions (none blocking, all should-fix): (a) strengthen or annotate the line-128 retry-order assertion; (b) either match the fixture's partial to 43,669 or add the "minimal fixture" comment; (c) leave replay110's broad clause as-is — narrowing it would reintroduce the 113-lost-calls failure.

P1_OR_WORSE: 0