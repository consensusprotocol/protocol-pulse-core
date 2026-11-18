# pp-selectid HANDOFF (written 07:03 ET Nov 18, after the usage-limit stop at 16:13 ET Nov 17)

## RULING 148 (09:38 ET Nov 18): three lines for a compaction
1. WHAT IS LIVE (pushed on pp-selectid): ed9df3f2 = the batch 114 mirror (decoder 50fa01b400bd, lockstep with the integrator's merge) + package_pin.flags_cap (5 flags on the one pin carrying the pbx_exception row, 3 on every other); 1be22777 = the STAND_ALONE come-back beside a trim variant. NOT BUILT: ruling 146 (3) (sponsor mention SOFT), ruling 148 (1) (the 30 s floor + its flag), and a fix for this side's word re-check attest.class_131, which in build 149 held Yahoo Finance f0a51c45 on '24 -7, 365' ('7 365' against '7365') although the render's lock adopts it under ruling 131 (A).
2. THIS PIN (PBX exception Nov 18, 16:9 only, cap 5, 30 s floor), two candidates: (a) SELL-OFF from ca660f2277836c085860, 91143945fbb6fdd6ae48, c5746c57869f9bc2ca60, 065871735af70e8c4714 (scratchpad r144/ONLY_SELLOFF2.json): 3 of them cleared both step-A screens in build 148 (tests/package/proof/ledger_20261118_140653); it goes only if those 3 span 3 channels and reach 30 s. (b) SELF-CUSTODY: Bitcoin Magazine hook 20cac687560642251d37 + Natalie Brunell 6e79ceaa8e76f34f4117 (ruling 146 (3) BY HAND: her own words read, flag 'The clip (Natalie Brunell) comes right after a sponsor mention', the admission logged in the build record) + Yahoo Finance f0a51c45830936b3a3c1.
3. NEXT: one audited change (dev copy, two cycles): the 30 s floor with 'This video runs NN seconds, shorter than usual.' (counts toward the 5), the by-hand admission of 6e79ceaa (a driver option naming that one moment, logged), the class_131 fix; then (b) from cache (and (a) if it qualifies); no new paid call unless a clip has no verdict ($0.68 of outside budget left today). Seal -> READY to protocol-pulse-68 with the pin path + seal prefix. Both refused by a HARD gate -> line 1 names the gate, STOP on yesterday's batch; the 12:00 ET build on today's pool runs with cap 3 + the 30 s floor and its flag.

Worktree /home/ultron/worktrees/pp-selectid, branch pp-selectid, clean, in sync with origin at 957bec5d. Scratchpad
(tools): /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad

## LIVE (pushed)
- THE HARD/SOFT SWITCH (rulings 136-141), in the never-empty pass only (package.build runs the clean pass first).
  - package_pin.SOFT_GATES = {context_a, cuttable, medley, stand_alone, coherence, ly_shape}. At most 3 flags; at most 2 flagged packages a day.
  - Stage 1: step A's first screen.
  - 2a (ca9b5e16): the second family's soft step-A codes; CUTTABLE's sentence edge (ruling 139).
  - 2b (2b939b99): the hook bar soft (at most 2 hooks).
  - STAND_ALONE soft (264d740a, ruling 141 (2)). Exact flag prefix, which the integrator matches: "The clip (<channel>) may not stand alone: ".
  - THE LINE-UP CHAIN, PHASE A (b1216504): kept candidates (clip ratings, joins past the bridge, the question hook's join), the best retried once, coherence ratings accepted for it. HARD: the through-line, the hook's own bar.
- Ruling 107 (1)'s guard (71ff97fc): a call refused for money is work left undone.
- RULING 142 mirrors, landed in lockstep:
  - 45ad6040 (batch 110: canon '24 -7', word_form, attest.class_131's exemption);
  - e88a1e51 (batches 111 + 112: canon_spans, the contraction). lock_precheck DECODER = fc204e4a4385; RULES end "+ ruling 135 + ruling 142".
- The POST_LIVE fallback on my side (957bec5d): transcript_truth.audio_window and visual_pin.fetch cut from the whole stream (the integrator's read-only cache data/post_live_cache/<video>/ first) when a section download is empty.

## MID-BUILD / NOT DONE
- RULING 143 (the material-words lock): the integrator's batch 113 values came at 16:0x Nov 17 (branch r143-material 7e7f6436).
  - Its values: DECODER 93e7d01c39f5e4a4beee7bc47d0378876290a81bf894a5dc916f45a26bddac70; RULES "+ ruling 143"; canon.py unchanged.
  - The new adjudicate_lock: material pair = not word_form and a critical token (now a TICKER too) -> run if the second reading agrees, else HOLD; non-material -> approved if the second reads it, else run (never a hold); wrong audio HOLD when share < 0.85 and > 3 tokens missing; records transcript_corrected / small_words_unsettled; as_spoken holds only on wrong audio or a material difference.
  - MY MIRROR (attest.class_131 / class_84, lock_precheck.decide) IS NOT STARTED.
- No attempt ran on Nov 17. The day ended at $1.17 all-in (of $1.65). Every Nov 17 candidate is past its 12 h now.
- Not built: the chain phase B (writes / value soft; the integrator's batch 108 already accepts a FLAGGED takeaway_value) and the hook's non-crop frames. P2 follow-up: a per-video lock in transcript_truth.whole_stream.
- The ledger watcher is NOT running.

## THE NEXT THREE STEPS
1. ASK THE INTEGRATOR whether batch 113 is live and its DECODER. Until my lock_precheck.DECODER equals the live one, no build can read its answers. If it is live, build the 143 mirror audit-first, in lockstep: READY unpushed, they push, I push.
2. Then re-arm the watcher (python3 -B /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/watch_ledger.py --watch 300 1800):
   - routine builds: bash /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/build_and_record.sh N "routine: ...";
   - then the free story fit: python3 -B /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/r141/story_fit.py;
   - pre-check the best 3-channel story ONE SPAN A REQUEST (python3 -B /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/r141/precheck_one_each.py ONLY.json TAG);
   - price it, and GO inside today's $1.50: LOCK=on bash /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/build_and_record.sh N "..." --only ONLY.json --stop-usd X;
   - READY to protocol-pulse-68 with the pin path and the seal prefix.
   - Build windows: 12:00, 15:30 and 19:30 ET.
3. Stage 2 remainder, each audit-first: the chain phase B (writes / value) and the hook's non-crop frames. Then the 133 batch.
