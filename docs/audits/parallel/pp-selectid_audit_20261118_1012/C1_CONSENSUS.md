# Cycle 1 consensus (pp-selectid_audit_20261118_1012, rulings 148 (1) / 149: the 30 s floor and its flag)

SEATS ANSWERED: 3 of 3. qwen3.8-27b and gemma-4-31b-it: P0/P1 none. gpt-oss-20b: one P1, REFUTED for this code base:
gpt-oss [P1] "the module-level _FLOOR can leak between concurrent build() calls": REFUTED. No process calls build()
concurrently. The one driver, tests/package/proof_ledger.py, calls PK.build in sequence (lines 607, 626, 638; no thread,
no pool anywhere in the file), then SPOT.build (648) after it. No other module calls package.build (grep). spotlight.py
reads none of ly_lo / runtime_short / takeaway_budget / lineup_ok / lineup_for. Each build is its own process
(build_and_record.sh), so a global is per build. Inside the never-empty pass the floor MUST be visible to the pass's own
worker threads (step A and the writes run on pools), which a thread-local or a context variable would not give (a pool
does not copy the context): the module global, set and cleared in build()'s try/finally, is the mechanism that does.
The clean pass has finished before it is set; the test asserts it is cleared after the pass.
P2/P3 notes: style only.

## No change from cycle 1 to cycle 2.
