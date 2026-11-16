# C2 CONSENSUS — pp-selectid audit 20261116_1126 (RULING 121 (1): the reserve and the xAI output cap)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: qwen 0,
gemma 0, mimo 0. The whole audit $0.0129 of Heimdall, not capped. No P1 in either cycle. CLEARED.
On dev43: all 40 suite files pass; mutations R1-R7 after a control run: 7 of 7 killed. It lands on the 11:41 ET default
of the STATE question (APPLY, audit-first) unless the orchestrator answers otherwise; FINAL.diff at landing.

AFTER CYCLE 2, A REAL DEFECT (found at landing, 11:47 ET): tests/providers/test_reserve_wait.py sized its scenarios with
U = the OLD bound of the Fake's one-character call ($0.10201); under ruling 121's reserve it is 1.25 x that ($0.12751), so
its four tests (six workers with room for four, ...) failed: the threads never got their room. My suite loop read only
pytest's LAST output line, which was a thread traceback, so it reported no failing file (the total, 831 not 835, gave it
away). FIX: U is now the Fake's reserve as the code computes it (Fake.upper_usd("p", 1000)); the four pass. The suite
runner now judges every file by pytest's exit code. Cycle 3 checks this fix (DEFECT).
