# C2 CONSENSUS — pp-selectid audit 20261115_1418 (ruling 114's x-bf-tunnel-instance replay)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 1) and glm-5.3-flash (P1_OR_WORSE: 0 in its count; it tags F1 / F3 as P1 in the
text). They disagree on a P1, so Grok was asked (P1_OR_WORSE: 2). Cycle 2: $0.0369; the audit $0.0431 so far,
vendor-reported.

THE P1 (qwen F1, Grok's first and second): "the spend ledger reads usage['usd_reported'], but Heimdall's reply
carries 'cost': the ledger never increments and the cap never stops the run". REFUTED, with the run:
- The `usage` ask() reads is FormatBackend.complete's third return, not the raw reply: replay111.FormatBackend.complete
  returns dict({"in", "out"}, **P._reported(u.get("cost"))) (tests/package/replay111.py:84-86, UNCHANGED), and
  providers._reported(usd) is {"usd_reported": round(float(usd), 8)} when the reply carries a cost
  (pipeline/providers.py:396-399, UNCHANGED). So Heimdall's cost reaches the row as usd_reported.
- The test proves the whole path: its fake gateway returns ONLY "cost": 0.0001 in the raw usage, and after 6 calls
  the ledger holds exactly 0.0006 (test_both_legs_alternating_resumed_and_stopped_at_the_cap,
  assertAlmostEqual(RT.spent(spend), 0.0006): PASSES); the cap then stops the third run before any call.
- HARDENED anyway, for a reply with NO cost at all: such a call is counted at UNREPORTED_USD ($0.002, an upper bound:
  replay111's v4 calls were a median $0.00006, at most $0.0011) on its own ledger line, usd_unreported_estimate
  (batch3.py reads both lines), so the stop never reads an unpriced call as $0. New test.

glm's P1-tagged items:
- F1 "a changed SOURCE file on resume": the source is replay111's committed OUT_OF_CONTRACT.jsonl; the pick is
  deterministic over it. No change.
- F3 "report() crashes on an empty or missing RESULTS.jsonl": an empty file already gave a zero report; a MISSING one
  (a run stopped before its first call) raised. FIXED: an empty report is written. Tested.

P2s acted on: glm F4 "the report never shows out_tokens": the table now gives the median out_tokens per leg and for
the unclosed answers (each call's figure is in RESULTS.jsonl). Not changed: glm F5 (`leg` is what the driver sent:
the header is set from it in one place), F6 (the report's sum is over its rows, the ledger is the stop's figure; both
are shown), Grok's P2 on report()'s `record` key (every row run() writes carries it), the P3s.

THE FINAL DIFF is FINAL.diff (written at landing). Tests: 7 offline, network blocked, all pass; the real ledger is
never touched by them. No third cycle: cycle 2 found no real defect (its P1 is refuted above by the passing test).
