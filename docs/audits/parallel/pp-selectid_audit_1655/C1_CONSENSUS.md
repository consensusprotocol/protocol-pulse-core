# pp-selectid audit 1655 (ruling 66: the search leaves every registered line-up to the registry): cycle 1 consensus

Cycle 1: grok "SHIP: yes"; qwen "SHIP: yes"; glm "SHIP: yes" (P1-1 to be confirmed by the author). No P0.

## Consensus, implemented

**C1 (grok P2-1, glm P1-1): does EVERY path that forms a line-up meet the check?**
- Traced in the full package.py, beyond the diff. Line-ups are judged by medley() at exactly two sites:
  - the main loop, after the check;
  - ruling 3's no-voice fallback (no_voice). It adds one clip to a passing line-up whose takeaway failed twice,
    then judges the new line-up (`ok2, nv_med = medley(router, order, ...)`).
- The no-voice site did NOT meet the check. A registered H+A+B+C could be judged, and shipped with no voice, after
  the search's H+A+B failed its writes. The reviewers' doubt was right.
- Fixed:
  - one map, held_map (registered; empty for a build from a candidate), is read at both sites;
  - no_voice never adds the clip that would form a registered line-up. It records note["registered_skipped"] and
    names it in why_not.
- The other sites form nothing new:
  - rewrite_alone (ruling 65) re-assembles the same line-up;
  - write_takeaway, coherence and assemble_medley work on a line-up that already met the check.
- Every way the main loop forms a line-up assigns `segs` at the top of the loop, before the check:
  - first formed (lineup_for, with its repeat_ok retry);
  - the pool fill (PROPOSAL 1);
  - `swapped`, which covers the swaps, ruling 62's drop of the last clip and ruling 63's reorder.
- New tests:
  - test_the_no_voice_fallback_never_adds_the_clip_that_forms_a_registered_line_up;
  - test_a_reordered_or_pool_filled_line_up_is_skipped_too. It covers ruling 63's reorder and the pool fill (an
    OPEN entry), and asserts the all-skipped why_none.
- Mutation runs (Rig only, no network): with the main-loop check removed, both skip tests fail; with the no-voice
  check removed, the no-voice test fails.

## Recorded, no change (with the evidence)

- **grok P2-2** (key() is not in the diff): candidates.key is at pipeline/candidates.py:28 (`"+".join(lineup)`).
- **qwen P2-1** (registered is silently ignored with a candidate): by design, and in build()'s docstring ("A build
  from a candidate ignores it"). The driver's try_one never passes it.
- **qwen P2-2 / glm P2-2** (os.makedirs is patched within the guard's block; pathlib would bypass it):
  - the driver's first write is `os.makedirs(out_dir)` (proof_ledger.py:135), right after the refusal block;
  - the driver uses no pathlib;
  - the refusal path only reads;
  - the guard is meant to be strict (glm agrees).
- **qwen P2-3** (lu!r in the message): the registry is this branch's own JSON, and the value is a short list.
- **glm P1-2** (ordering fragility): the driver computes registered AFTER run_due, by design (commented). No defect.
- **glm P1-3** (the shape of an all-skipped build): build returns its normal out:
  - package None;
  - why_none "no angle gave a package: angle 1: ruling 66: a registered candidate ...";
  - the driver's `elif res is None` branch only covers "no judged line-up left".
  This is now asserted (the pool-fill case).
- **glm P2-1** (one line-up under two keys, last one wins): impossible after registered()'s check `key(lu) == k`.
  A line-up has exactly one key.
- **glm P2-3** (the open state is untested in the search): the skip reads no state. The pool-fill test now uses an
  open entry.

## Suites after the fix (scratch copy at HEAD 0bf62556 + this diff)

All 14 OK:

| suite | tests |
|---|---|
| medley | 141 |
| candidates | 10 |
| ledger_build | 35 |
| visual_pin | 11 |
| attest | 7 |
| speakers | 23 |
| providers | 16 |
| gates | 18 |
| angles | 28 |
| moments | 7 |
| eligibility | 30 |
| hook_onset | 9 |
| house_style | 23 |
| select_by_id | 27 |
