# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 29 s finish=stop usage in 8688 / out 384 usd~0.053 (upper-bound price)

**P2: pipeline/providers.py:30** (and test at tests/providers/test_providers.py:154)  
The reported basis computes `usd_reported + usd_unreported_estimate` (or falls back to `usd_estimate` for the default "estimate" basis). The diff verifies that every exercised call is counted exactly once under the chosen basis, that a paid call is never charged zero, that the file lock + reservation logic is untouched, and that the guard can only stop early. However, `_settle` (which writes the three ledger fields) is not present in the diff, so correct population for every vendor reply path cannot be verified here.

**P2: tests/package/proof_ledger.py:70** (`if spent0 >= PL.LY_STOP_USD`)  
Implements "at $10 reported stop" by refusing to *start* a build (exit 3, no paid calls) while the hard Router cap remains $12 on the reported basis. A build started below $10 can still spend up to the $12 cap (subject to its own per-build budget). The ruling text is satisfied by this reading; I do not read it differently from the diff + supplied orchestrator wording.

**P2: tests/package/proof_ly.py:116**  
LY_LIMIT_USD / LY_LIMIT_BASIS / LY_STOP_USD constants and all Router construction sites are updated consistently with the new ruling (including the spend_ruling_48 record written to package.json). No other call sites outside the spend-guard path are altered.

No P0 or P1 findings. All other callers retain the old "estimate" default; validation rejects unknown basis values; the test exercises the exact scenario described in Ruling 48 (old estimate 39.5 refused, reported 5.27 allowed, mix of reported/unreported calls counted once, reservations cleared).

**SHIP: yes**