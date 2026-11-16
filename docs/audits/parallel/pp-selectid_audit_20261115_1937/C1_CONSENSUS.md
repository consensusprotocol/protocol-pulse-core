# C1 CONSENSUS — pp-selectid audit 20261115_1937 (BATCH 4's own build ledger)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and deepseek-v4.1-flash (2); they disagree on a P1, so Grok was asked (1).
glm's breaker is open. Cycle 1: $0.0185 vendor-reported. Each P1 checked against the code: none is a defect.

1. deepseek [P1] "SPEND moves to SPEND_B4.json unconditionally; landed before 21:10 ET, a batch-3 build would charge
   batch 4; hold it until 21:10 or gate it by time": HELD, its own first remedy. The change is not in the worktree
   until 21:10 ET; it lands then, in one commit whose time shows it. Every build is started by this builder (the
   ledger watcher only notifies), and none starts between 21:10 and the landing. A build started before 21:10 has
   already imported proof_ly with SPEND_B3.json and keeps charging batch 3 to its end. A time gate would leave code
   that is dead from 21:10 on; holding needs none.
2. deepseek [P1] "os may not be imported in test_ruling_102.py": REFUTED: tests/package/test_ruling_102.py:10
   `import os`; the test passes (18 in the file; all 40 suite files, 813 tests).
3. Grok [P1] "the diff implements none of the governing laws (D1-D6, the protected preview, ...)": OUT OF SCOPE: this
   audit is the one-file-name ledger switch the QUESTION names; the laws' gates live in code this diff does not
   touch, and nothing here claims to change them.

P2s / P3s noted, not changed: deepseek "grep for any other SPEND_B3.json writer": done before the audit (git grep:
only proof_ly.py and this test name it; proof_ledger.py:221 is the only reader of PL.SPEND). The redundant
assertNotIn (deepseek, qwen): kept: it states the closed ledgers by name. Grok: a helper for the file name, and the
dated comments: left as they are (one constant per batch, as ruling 108 did).

CHANGED AFTER CYCLE 1: nothing.
