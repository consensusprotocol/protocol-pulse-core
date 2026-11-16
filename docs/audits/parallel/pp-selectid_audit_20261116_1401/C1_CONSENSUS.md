# C1 CONSENSUS — pp-selectid audit 20261116_1401 (RULING 123 (1): Grok's reserve at 25 % of list, the tripwire)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: gemma 0,
mimo 0, qwen 1. Cycle 1 $0.0072 of Heimdall, not capped.

qwen's P1 ("the write to reserve_tripped in _settle is not protected by self._lock()"): NOT SO. _settle (dev46
providers.py:1014, unchanged but for the tripwire) does all its work inside "with self._lock():" (:1020, unchanged): it
reads the ledger, pops the reservation, accounts the call, writes the trip (:1038) and saves (:1060) under that one lock,
as every ledger write; _reserve_fraction (:1002) reads under the same lock. The hunk did not show the with line.
What IS true (said, not changed): a call that read the fraction (25 %) an instant before another call's trip, and
reserves after it, still reserves at 25 %: the calls deciding at that instant, each decided before the trip existed.
The ruling accepts that tail ("the worst case is one call's overshoot"); with the build's parallel step-A batches it is
at most the calls in flight then. No change.
