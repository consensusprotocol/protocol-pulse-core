# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 17 s finish=stop usage in 13290 / out 1106 usd_reported=0.023226 usd~0.094 (upper-bound price)

**CYCLE 2 AUDIT: pp-selectid / RULING 110 (replay110.py + test)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
In my Cycle 1 I focused on the brittle timeout string match, the non-atomic spend check, and the repeated incumbent() parse. I missed Qwen's deeper dive into source_records deduplication ordering (the seen.add before JSON load is correct and prevents duplicates). I also under-weighted how thoroughly the added comments now pin the Router contract (providers.py:1410 ProviderError format and the exact abandonment message). The test_no_answer_by_the_cap_is_a_timeout_with_no_decision exercising the live Router abandonment path was noted by both but I did not explicitly verify it forces the "abandoned at the deadline" string.

2. WHERE DO YOU AGREE OR DISAGREE?
- Timeout string match (Qwen [P1], Grok [P2]): Partially agree. It remains brittle in isolation, but the new comment + test that runs the actual Router abandonment path make it a pinned contract, not undefined behavior. The "fail closed" law is satisfied because a changed message would break the test, forcing an update. Consensus correctly downgraded it.
- Spend stop non-atomicity (Qwen P0/P1, Grok P2): Agree with consensus. The design (check at start, in-flight calls finish, tiny per-call cost) plus explicit docstring now stating the bound is acceptable for a $0.75 test-only replay. A lock would serialize the entire run and is worse engineering.
- source_records dedup (Qwen [P1]): Disagree with Qwen. seen.add(rel) precedes the file read and type check; the test confirms duplicates are impossible and missing records are correctly segregated.
- Docstring vs GATEWAY_MODELS.json (Grok [P3]): Agree. The file is referenced for historical record but never written by this driver; the ids are hard-coded. Pure documentation nit, now clearer.
- incumbent() re-parse and router.down.pop undocumented (Grok [P3]): Agree both are minor; the comment at line 130 now explains intent.

3. NEW FINDINGS FROM THIS REVIEW
- **[P3]** replay110.py:247 – summary() builds "deadline_100_s": sorted({…}, key=str). With two models sharing the same 120 s gateway default today this is harmless, but if deadline_table ever diverges per-model the set loses ordering stability and the rendered comma-separated list becomes non-deterministic.
- **[P3]** replay110.py:186 – round-robin by_type pop(0) on lists is O(n); with 319 records negligible, but a collections.deque would be cleaner and is the sort of test-driver cleanup that should have been caught in Cycle 1.
- **[P3]** test_replay110.py:398 – test helper hard-codes routing="heimdall_first" and then mutates r.config["routing"] after router() construction. Matches production path but the double-write is undocumented.

No logic defects, no production state mutation, no routing change, no new spend outside the isolated ledger.

4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Deadline / outcome classification | P2 | P3 | Added Router-contract comment + live test path removes brittleness concern |
| Spend control & ledger | P2 | P2 | Consensus confirmed acceptable; docstring now explicit on bound |
| Record selection & dedup | P3 | P3 | Qwen's P1 was incorrect; my Cycle 1 missed the ordering but logic was already sound |
| Table / summary arithmetic | P3 | P3 | No change; p50/p90 over answers only, missed = late+timeout, all tests pass |
| Isolation (no prod write/routing) | P3 | P3 | Confirmed by both reviewers; new comments strengthen it |

5. FINAL PRIORITY LIST
- **[P3]** replay110.py:247 – replace set+key=str with list+sort for stable deadline rendering (tests/package/replay110.py:247)
- **[P3]** replay110.py:186 – use collections.deque for by_type round-robin (tests/package/replay110.py:186)
- **[P3]** test_replay110.py:398 – document the post-construction routing mutation or move config into router() call (tests/package/test_replay110.py:398)
- **[P3]** replay110.py:10-14 – either write GATEWAY_MODELS.json or remove the claim it is recorded by the script (tests/package/replay110.py:10)

P1_OR_WORSE: 0

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Make the Router expose a typed Timeout exception instead of embedding "abandoned at the deadline" in the ProviderError message; that single upstream change would let every replay script drop the string match while preserving the exact test semantics.

7. PRODUCTION READY?
Yes with conditions: the three [P3] wording / stability cleanups above must be applied (none alter behavior); the existing test suite already exercises every ruling-100 branch, spend stop, guard refusal, and out-of-contract path. No production code, no routing change, no gate bypass. Ship after the nits.