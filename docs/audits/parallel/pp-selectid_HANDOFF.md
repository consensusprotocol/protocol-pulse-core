# pp-selectid HANDOFF (written 13:13 ET Nov 17; rulings 139 / 140)

## LIVE (pushed)
- Rulings 131 / 135: the word lock's two of three readings, the currency canon and the comparison canon. Decoder b52c9354d604 on both sides.
- Rulings 136 / 137 / 138 / 139, the hard/soft switch:
  - STAGE 1: never-empty for step A's first screen.
  - STAGE 2a (ca9b5e16): the second family's soft step-A refusals and the re-screen's are flagged. CUTTABLE's sentence edge at a word boundary is flagged (ruling 139). "cuttable" is in package_pin.SOFT_GATES. The soft pass's own record is kept (never_empty.soft_record).
  - Flags: one plain sentence a clip, at most 3. review_flags go on the pin. At most 2 flagged packages a day (FLAGGED_DAY.json).
- Ruling 107 (1)'s guard fix (71ff97fc, audit 20261117_1305):
  - Router.spend_refused names every paid call refused for money.
  - open_work counts those calls, and the never-empty pass's own holds, as work left undone.
  - Why: build 134 had asked nothing after free build 133.
- The integrator's check_pin_only calls package_pin.gate_problems live. Their batch 106 (ETA about 13:30 ET) must be live before any pin renders; a pin that arrives earlier waits (their ruling 140 (1)).

## THE ATTEMPT (ruling 140: may run to $1.65 all-in)
- Build 135 started 13:12 ET: router stop $1.50 + Scribe $0.096 + at most $0.032 for a swap's pre-check. The log is /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/build135_*.log.
- The kept line-up: ca660f2277836c085860 (hook, Scott Melker), 8dbc30ee3ad91f82552d (DataDash), 372f6afd8ff42ea6a597 (Natalie Brunell), e06e9566dbe3ea80c568 (Coin Bureau).
  - Swaps: cae5123f9ff683c8b965, 700df83644274f6981d4, f4bad490a7d8f7f7e89d, c79b7f6d3b7dd2a9d9ea.
  - --only file: /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/r131/r134/ONLY_C.json.
- Expected flags, 3 (the cap):
  - the hook's NOT_OWN_SINCERE (Grok only);
  - DataDash's IN sentence edge;
  - Coin Bureau's REFERENT_OUTSIDE (both families).
- THE CAP BINDS: one more soft refusal (clips-alone, joins, a non-crop visual flag, the writes, value, coherence) would be a 4th flag, which the seal refuses. Only a swap to a cleaner clip or a ruling on the cap helps then. Say so on line 1.
- If it seals: SendMessage protocol-pulse-68 READY with the pin path (the build's record dir, MOMENTS_PIN_LEDGER.json) and the seal prefix (package_sha256[:12]).
- If a not-yet-switched SOFT gate refuses (ruling 140):
  1. Write the gate on line 1 and hold the line-up.
  2. Switch that one gate audit-first.
  3. Run again from the cached answers while inside 12 h.
- Expiries: DataDash 20:00 ET; Coin Bureau 21:00; the hook ca660f22 21:01; Natalie 21:56.
- After this attempt: no outside call until 21:10 ET, except to finish this same line-up.

## MONEY
- Before build 135: the router $0.977, Scribe $0.096. Today's stop for this attempt is $1.65 all-in. From 21:10 ET: $1.50 a day.
- The keeper day118.py prints today's cap as $1.40; ruling 140 raised it to $1.65 for this attempt only.

## NEXT
- The ledger watcher is NOT armed. After the attempt, run a routine build_and_record.sh, then re-arm watch_ledger.py --watch 300 1800.
- Stage 2b before 21:10: the remaining soft gates.
- The 21:10 list: ranked and pre-checked, first paid call at 21:10:01.
- Then the 133 batch: the price cap (dev55 started), the head-side variant, and S4.
- Build windows from Nov 18: 12:00, 15:30 and 19:30 ET.
