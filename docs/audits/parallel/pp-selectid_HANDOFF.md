# pp-selectid HANDOFF (written 12:28 ET Nov 17 for a context compaction; ruling 139)

## LIVE (pushed)
- Ruling 131 (A)+(B), the word lock's two of three readings and the currency canon: decoder lockstep with the
  integrator, since superseded by 135.
- Ruling 135, the comparison canon (canon.same_words): decoder b52c9354d604 on both sides.
- Rulings 136 / 137 / 138, the hard/soft switch, STAGE 1: never-empty for step A's FIRST screen.
  - package.build is a wrapper: the clean pass, then a soft pass when nothing sealed and the day limit allows (FLAGGED_DAY_MAX 2).
  - Soft step-A codes: NOT_OWN_SINCERE, REFERENT_OUTSIDE, CONDITION_OUTSIDE, UNCERTAIN. Hard: STALE_TIME, SPEAKER_CHANGE, RETRACTION.
  - context_a is FLAGGED with one plain sentence a clip (ruling 138 (3)).
  - package_pin: SOFT_GATES {"context_a"}; review_flags derived from the sealed rows, at most 3.
  - proof_ledger: never_empty=True and flagged_today (tests/package/proof/FLAGGED_DAY.json); STOP_CEILING_USD 1.50.
  - Audit pp-selectid_audit_20261117_1135.
- The integrator's render switch is live: soft gates flag and never hold; "REVIEW FLAGS:" in the note. Its check_pin_only calls my package_pin.gate_problems live.

## BUILDING: STAGE 2a, dev copy /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/dev58 (base = worktree HEAD at 37ebfc50; pipeline/package.py, package_pin.py, tests/package/test_ruling_137.py)
- What it adds:
  - the second family's soft step-A refusals (soft_second), and the re-screen off the writer's (soft_codes), flagged;
  - CUTTABLE's sentence-edge part SOFT (soft_edges: only the run-on reasons; ruling 139 YES);
  - "cuttable" in SOFT_GATES;
  - seg_flags / mids in inventory;
  - never_empty.soft_record.
- Evidence so far: 11 tests pass; 23 of 23 effective mutations killed. Suites run to /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/dev58_suites.log. Heimdall audit pp-selectid_audit_20261117_1217, cycle 1 in flight (driver /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/audit_20261117_1217.py; cycle 2 = "python3 -B audit_20261117_1217.py 2 C1_CONSENSUS.md").
- LAND:
  1. Check the worktree's files equal dev58's base (git -C dev58 show HEAD:f).
  2. Copy the 3 files.
  3. py_compile.
  4. Run test_ruling_137, test_angles, test_medley, test_ledger_build.
  5. Commit (git add -f for the test) and push. There is no lockstep.

## THE KEPT LINE-UP (run it the moment 2a is live; ruling 139: 3 flags, the cap; inside $1.40)
- --only file: /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/r131/r134/ONLY_C.json
  - The line-up: ca660f2277836c085860 (hook, Scott Melker), 8dbc30ee3ad91f82552d (DataDash), 372f6afd8ff42ea6a597 (Natalie Brunell), e06e9566dbe3ea80c568 (Coin Bureau).
  - Swaps: cae5123f9ff683c8b965, 700df83644274f6981d4, f4bad490a7d8f7f7e89d, c79b7f6d3b7dd2a9d9ea.
- The expected flags:
  - the hook's step A NOT_OWN_SINCERE (Grok only; deepseek passed it);
  - DataDash's IN sentence edge (runs on from 'line:');
  - Coin Bureau's REFERENT_OUTSIDE (both families).
- Command: LOCK=on bash /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/build_and_record.sh 133 "RULING 139: the kept line-up under never-empty stage 2a" --only /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/r131/r134/ONLY_C.json --stop-usd STOP
  - STOP = floor((1.40 - the keeper's lock_precheck_scribe) * 100) / 100, about 1.30.
- If it seals: SendMessage protocol-pulse-68 READY with the pin path (the build's record dir, MOMENTS_PIN_LEDGER.json) and the seal prefix (package_sha256[:12]). It renders at once.
- First expiry: DataDash 8dbc30ee at 20:00 ET.

## MONEY / STATE
- Today: the router $0.98, Scribe $0.096, $1.07 all-in of $1.40. From 21:10 ET: $1.50 a day.
- The ledger watcher is NOT armed. After the attempt, run a routine build_and_record.sh and re-arm watch_ledger.py --watch 300 1800.
- Build windows from Nov 18 (ruling 138 (2)): 12:00, 15:30 and 19:30 ET.

## NEXT, after the kept line-up
- Stage 2b before 21:10: the remaining soft gates (the hook bar, joins / clips-alone, visual soft flags, line-up rules, the writes' gates, value, coherence, context_b/c).
- The 21:10 list ranked, pre-checked, first paid call at 21:10:01.
- Then the 133 batch: the price cap (dev55 started), the head-side variant, and S4 re-opening line-ups closed by a changed gate.
