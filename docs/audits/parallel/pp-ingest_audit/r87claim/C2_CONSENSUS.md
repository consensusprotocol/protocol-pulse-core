# Ruling 87, the builder's probe claim taken up: cycle 2 (cross-validation) consensus

Reviewers (Heimdall): glm-5.3-flash (168 s, $0.004): "P0 CRITICAL: none. P1 HIGH: none. P2 MEDIUM: none ... Production
ready: yes, with one condition"; muse-spark-open (241 s, $0.025): "P0 CRITICAL - none. P1 HIGH - none ... Yes - ready
for production. Deploy on next restart. Conditions: None"; qwen3.8-27b (191 s, $0.020): "P0 CRITICAL: None. P1 HIGH:
None ... Production ready: Yes". No reviewer disagreed with another's cycle-1 verdict. Cycle 2: $0.049; this audit,
both cycles: $0.104 (Heimdall).

## glm's one condition: IMPLEMENTED
- When the module loads but its probe_due takes no `who` (a module older than pp-selectid 11ed255f, or a probe_due
  whose signature cannot be read: wrapped without functools.wraps, positional-only), the watcher now says so once in
  its log at start; before, the graceful fallback (probes without a name) left only `probe_claimed_as: null` in
  live.json. Tests: the old-module and unreadable-signature tests assert the line; the claim test asserts its absence.

## Taken as comments (qwen P2, muse P3, glm N1)
- `probe_claimed_as` is the name this watcher's claims carry; the state's `last_probe_by` names whoever won the
  latest slot (a different name there is not a defect).
- A slot this watcher claims and then cannot probe (every probe back-end skipped) sends no probe_result and stays
  spent from its claim: the builder's semantics.

## Refuted
- glm N3 "the watcher's tests stub the module; nothing pins the real pair": tests/ingest/test_signal.py loads the
  builder's REAL module from its path (`MODULE`, now 11ed255f) for every DownSignal test, against the real router with
  fake back-ends; only the old-version test (125e7381 from git) and the unreadable-signature test use modified copies.
  The claim test calls the real 11ed255f probe_due as the other prober.

## Recorded for the builder's next audit (glm N2)
- "probe_due returned True" and "the slot is stamped" are now one step under the flock (stamp, save, return); a
  future module that stamps and then raises would cost one probe slot per incident, unseen here.

Tests: tests/ingest 271 passed (27 in test_signal.py).
Verdict: no P0 / P1 / P2 in either cycle; the condition is in. Deploy: a restart takes up 11ed255f.
