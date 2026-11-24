# Batch 123, cycle 2 (the change as it stands, with the guard after the 23:44 ET incident)
Seats: gemma (medium): PASS. gpt-oss (medium): FAIL, 3 findings, "KeyError on f['what'] and paths['log']": DISPROVED:
every finding is built by finding(), which always sets "what"; every paths map run_pass works with has "log" (run_pass
itself writes paths["log"] unconditionally, and the production PATHS defines it). qwen27b (high): no answer in time
(recorded). Mutations 9 of 9 (with the guard mutant R7).
