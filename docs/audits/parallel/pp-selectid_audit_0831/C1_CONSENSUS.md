# pp-selectid audit 0831 (order 08:06 item 55: the missed-deadline evidence log): cycle 1 consensus

**Run.** No P0 or P1 that holds. Verdicts:
- grok: "yes with conditions";
- qwen: "yes with conditions";
- glm: "SHIP: yes".

## The conditions, answered from the code (no change)

| # | condition | the code |
|---|---|---|
| A1 | grok / qwen: are json, os and time imported at module level? (If time were missing, the logger would raise inside call()) | pipeline/providers.py lines 33-35: `import json`, `import os`, `import time`. time.strftime is already used by _record (line 709). |
| A2 | grok: one Router per process for the lock | _log_lock is per Router. A build constructs ONE Router (proof_ledger / proof_ly). Its thread pool shares that instance, so the lock serialises every line in the build. Each line goes out in one small append (well under a page), so two builds' lines cannot interleave inside a line either. |
| A3 | glm P1-1: the slow log fires even for an empty reply | Intended: a call that took >= slow_log_s is evidence whatever it returned, and the line carries its in / out tokens. |

## Verification

- test_providers 16 OK; every other suite OK.
