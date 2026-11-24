# Batch 117 (ruling 133 R16, service heartbeats), cycle 2

Seats: qwen27b (Heimdall, effort medium, 251.8 s) and gptoss (Heimdall, effort medium, 92.1 s). No Grok (Heimdall only).

- gptoss: PASS, no findings, confidence 0.0: recorded, carries no weight (as in cycle 1).
- qwen27b F1 (medium), session_watchdog.py heartbeat_findings: Python's json reads NaN and Infinity, so a heartbeat
  file with {"at": NaN} parsed, left the guarded read, and round(now - at) raised outside it: every heartbeat check of
  that pass lost. ACCEPTED, fixed: every time read is checked 0 < t < 1e11 inside the guarded read (NaN, inf, a
  string and an out-of-range time all read as an unreadable record, the missing path). Test extended (NaN / Infinity,
  and a 1e300 pass_at). Mutation M14 (the guard removed) is killed.
- Cycle 1's F1 and F2 are confirmed fixed by the same seat (it raised nothing on them).

Mutations: 14 of 15 killed. M15 (pass_at read raw, outside the float()) SURVIVES as an equivalent mutant: the cycle-2
range guard compares it inside the guarded read, so a string raises TypeError there and reads as missing, the same
behaviour.

Suites importing the changed modules (19 files, the worktree): 595 passed; one failure, test_fresh.py::TestVerifyVoVoice::
test_v2f_manifest_same_voice, which passes on the live tree (the worktree lacks the untracked v2f run files: the known
worktree limit). Must-fail: the new test file cannot even be collected on the old code (no heartbeat module).
