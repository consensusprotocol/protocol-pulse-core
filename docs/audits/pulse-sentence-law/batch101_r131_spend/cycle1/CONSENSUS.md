# Batch 101 (ruling 131's spend part), cycle 1: consensus

Heimdall only. Each seat was run on its own at `HEIMDALL_AUDIT_EFFORT=medium`.

| Seat | Verdict | Findings | Completion tokens | Trace |
|---|---|---|---|---|
| qwen27b | PASS | 0 | 9,241 | S1-S6 traced against the code |
| gptoss | PASS | 0 | 1,377 | Short. Each of S1-S6 is traced: the record call sites after success; ticks / 1e10 with a bool rejected; the OSError path; the window; the glob prefix, offset and ratio; no payment when reused. |

**Consensus:** no finding.

**Recorded:** the question's FACTS said a re-download "never" byte-matches an earlier reading. The 09:30 ET replay's four downloads DID match. The wording is corrected in 9c7b4d5c. The reuse never depends on it: it matches by window, offset and words.
