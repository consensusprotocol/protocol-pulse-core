# C1 CONSENSUS — pp-selectid audit 20261116_0536 (RULING 118: the day cap, the guard before the free panel)

Seats (ruling 118: Heimdall only, no Grok seat): qwen3.8-27b, deepseek-v4.1-flash, gemma-4-31b-it; glm's breaker is
open. SEATS ANSWERED: 2 of 3 (deepseek was cut off at its 32,000-token cap with no answer, finish=length). qwen
P1_OR_WORSE 0; gemma 1. Cycle 1: $0.0106 of Heimdall, vendor-reported, not capped.

gemma [P0] "spent() uses an undefined `b` and returns None": REFUTED by the code. The changed line `if not
self.spend_path or b.free() or not self._capped(b.name):` is in `def _reserve(self, b, upper)` (dev38
pipeline/providers.py:914, the line at :928), where `b` is the parameter; `def spent(self)` (:907-912) is unchanged and
returns `self._basis_total(...)`, a float (0.0 with no ledger). The diff hunk showed spent()'s lines as context just
above the change. The tests call spent() and pass (test_ruling_118_heimdall_is_recorded_but_never_capped: 0.95, 0.96).

qwen's two "[P1] Check:" headings are checks it states and answers (P1_OR_WORSE: 0), not findings.

P2 / P3 noted, not changed: gemma "the first day's file is keyed to the literal date 20261115": deliberate; that one
day's ledger already exists (batch 4's), every later day is named by its own date, and the test pins both.

CHANGED AFTER CYCLE 1: nothing.
