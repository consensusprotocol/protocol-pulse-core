# pp-selectid audit 1420b (the increment: audit 1420's cycle-2 consensus): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes with conditions": a malformed-found_at test, and confirm due() refuses before any write.
  - qwen: "SHIP: yes with conditions". Its P1 is self-refuted ("The clamp logic is sound").
  - glm: "SHIP: yes with conditions": P1-1 (the registry flag), P1-2 (glm: P2), P1-3 (unverifiable from the
    increment).
- No P0.

## Applied (consensus: tests only)

| # | finding | the change |
|---|---|---|
| C1 | grok and glm (4): a test for a zoneless and a malformed found_at | test_candidates: test_a_found_at_without_a_zone_is_utc_and_a_malformed_one_raises. A zoneless found_at sorts as UTC (20:00 before 19:00Z); "tomorrow" raises ValueError. |
| C2 | grok (condition), qwen P2, glm P1-3: confirm a malformed stored time refuses the run before anything is written | The driver evaluates `CA.due(reg, now)` inside its refusal block (tests/package/proof_ledger.py:127, audit 1420 C1), before out_dir exists. The registry does not change between that call and run_due's, so run_due's due() reads the same, already-read times. New driver test: test_a_malformed_candidate_registry_refuses_the_run_before_anything_is_written (test_ledger_build). It points REGISTRY at a temp file with found_at "tomorrow" and asserts exit 2, "registry" named on stderr, the file not rewritten, and no new ledger_* dir or CANDIDATES.json. |

## Answered

| # | finding | the answer |
|---|---|---|
| A1 | glm condition (2): does the final log line read keys missing from the minimal no-package dict? | It reads res.get('why_none'), res['usable'] and res['prescreen'].get('cleared'). The minimal dict carries "usable": None and "prescreen": {}, plus package None, packages [] and why_none. |
| A2 | glm condition (3): does outcome "budget" leave the candidate as it was? | Yes. outcome() changes the state only for "package" / "clip" (closed) and "line" (resting or closed), and raises on any class but "budget". test_the_14_02_rules asserts "budget" leaves an open candidate open. |
| A3 | grok P1 (F3): are all new paths non-crashing? | try_one catches a build exception (no outcome, every line-up left charged). The minimal dict covers a run with no try's out. The post-write block guards the registry's outcome, seed and save. The refusal block catches OSError, ValueError, KeyError and TypeError around the read, seed and due(). |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-1: res["registry"] = True is written even if the registry save then fails | It matters only for a --from-candidate record, the only kind with a top-level "candidate". Its lost outcome leaves that candidate as it was, and it is tried again. A due-path record's tries are never re-read from the record. The failure is logged in the run's log. |
| G2 | glm P1-2 (glm: P2), qwen and grok P2s | The clamp holds the 8 (its tests); the rest is informational. |
