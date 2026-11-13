# pp-selectid audit 1330 (RULING 66: a passed line-up is kept; --from-candidate): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", no findings.
  - glm: "SHIP: yes with conditions": P1-3 (the seeds after a swap), P1-4 (angle_reply's other attributes), and
    P1-1 (ValueError on a malformed entry).
  - qwen: "SHIP: No", on one P1: n_lineup is 0-based, so the seeds would be one less than the recorded ones.
- No P0. Neither P1 holds against the code, and glm's P1-4 is answered by grep.
- **Nothing changes in the code**; cycle 2 reviews the same diff.

## The strongest evidence: an OFFLINE dry run on the real record (no live call, nothing spent)

- **How it ran.**
  - dev22's code, with the router in REPLAY mode: it serves only the recordings, which are keyed by sha256(role,
    back-end, prompt, max_tokens, seed, system).
  - It read the worktree's recordings only. The caches and the spend ledger were scratch copies, no scorer candidates
    file was written, and the record went into the scratchpad.
  - The candidate came from the 12:22 record (ledger_20261113_172217, tried[0]).
- **Result.**
  - "ruling 66: the candidate ... tried[0] (angle 1 line-up 1), as judged: its angle from
    heimdall:deepseek/deepseek-v4.1-flash, no angle asked".
  - SERVED from their recordings:
    - the clips-alone verdict, PASS {'hook': 4, 'clip_01': 4, 'clip_02': 4}, flagged [];
    - the three exclusion verdicts;
    - write 1 (heimdall:deepseek, the same 18-word takeaway, 61.82 s);
    - its fidelity verdict, both viewer_takeaway calls and the context verdict: "fidelity FAIL (takeaway PASS),
      context PASS", as at 12:22.
  - The FIRST unrecorded call was ruling 65's caption-only write (angle_write).
- **This proves the seeds.** Every recorded call was served, so its seed equals the recorded one. It also proves the
  same bytes and the same L-x routing. The candidate path is exactly the 12:22 line-up up to the new calls.
- **Where the dry run stopped.** It then stopped in the fixed caption's context check, on ReplayMiss.
  - ReplayMiss exists only in replay (providers.py:781-782).
  - A live router raises ProviderError when every back-end is unavailable (providers.py:783), and
    context_integrity.check_contexts catches that and fails closed (CONTEXT_UNAVAILABLE).
  - So this is a replay-only stop, not a live path.

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P1: n_lineup is set to the recorded number - 1, so the seeds are one less than recorded | The unchanged loop increments n_lineup (package.py:2412) after the tried entry is appended (2408) and the `segs is None` break (2409), and BEFORE the verdict call. The call uses `seed=7 + n_lineup + 10 * ai` (2423); the writes use `7 + w_used + 10 * ai + 100 * n_lineup` (2497, 2603). Starting at n - 1, the first iteration judges with n: exactly the recorded seed. The tests assert the seeds as the Rig receives them: (8, 108) for angle 1 line-up 1, (19, 218) for angle 2 line-up 2. The dry run above shows it on the real record: every recorded call was served. |
| R2 | glm P1-3: after a ruling-41 swap, a swapped line-up may not get its own tried entry, so the reconstructed number could be wrong | Every iteration of the while loop appends its OWN entry: `rec = {...}; out["tried"].append(rec)` (2404-2408). That covers a swapped, reordered (63), retried (62), pool-filled or re-asked line-up. n_lineup is incremented exactly when that entry's line-up is not None (2409-2412). So "this angle's entries with a line-up, up to the index" IS the loop's counter. The 12:22 record shows it: angle 2's seven swapped line-ups are seven tried entries. |

## Answered

| # | finding | the answer |
|---|---|---|
| A1 | glm P1-4: does unchanged code read another attribute of angle_reply? | grep: angle_reply is read only for .backend (2235, 2252, 2254, 2364, 2661), .tried (2235), .vendor (2236, 2251) and .family (2236). The SimpleNamespace carries all four. The dry run ran the real build past every one of those reads. |
| A2 | glm P2-1: `filled` per angle changes normal builds | It does not. In a normal build every angle starts with swapped None, so its first iteration takes the else branch, which assigns `filled = None` (2398) and pool_fill's result. Later iterations inherit it exactly as before. Only a candidate's first iteration takes the swapped branch, where `filled` was never set (a NameError without the init). |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-1: a malformed tried entry (e.g. lineup a string) raises TypeError / IndexError, not ValueError | Records are build()'s own JSON. lineup is always `[m["moment_id"] for m in segs]` or None (2404), and angle is `ai + 1`, an int. The one caller (proof_ledger) catches OSError, ValueError, KeyError and TypeError, and refuses (exit 2) before anything is written. |
| G2 | glm P1-2: the recorded supply_exception decides repeat_ok against today's pool | The candidate's clips are fixed, and L-y 4's exception was the reason that line-up was allowed. The build still recomputes the reason for its own record (supply_exception, in the swapped branch). The 12:22 candidate has none (3 channels). Noted for the standing registry. |
| G3 | glm P2-4: no Rig test of the hook-cannot-open closure, nor of a candidate reaching ruling 65 | The dry run on the real record shows the candidate path reaching ruling 65's caption-only write as its first new call. The hook branch is one can_open() call. |
| G4 | glm P2-5 / P2-2 / P2-3; qwen P2s | A build that raises writes no record at all (proof_ledger does not catch it). A trailing ':' fails to open and is refused. Cosmetic otherwise. |

## Verification

- test_medley 131 OK (6 new: TestRuling66Candidate) on dev22, base 2849d971.
