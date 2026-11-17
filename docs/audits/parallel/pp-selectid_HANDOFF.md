# pp-selectid HANDOFF (written 14:06 ET Nov 17; rulings 139-141)

## LIVE (pushed)
- Rulings 131 / 135: the word lock and the comparison canon. Decoder b52c9354d604 on both sides.
- The hard/soft switch, in the never-empty pass. package.build runs the clean pass; only if it seals nothing, and the day allows (FLAGGED_DAY_MAX 2), it runs _build(soft=True).
  - Flags: one plain sentence each, at most 3 (REVIEW_FLAGS_MAX). package_pin.SOFT_GATES = {context_a, cuttable, medley, stand_alone}.
  - Stage 1: step A's first screen.
  - Stage 2a (ca9b5e16): the second family's soft step-A refusals; CUTTABLE's sentence edge (ruling 139).
  - Stage 2b, the hook bar (2b939b99): a hook under the calibrated bar, rated by its own rater, opens flagged. At most the best 2 (HOOK_SOFT_MAX), marked hook_bar_soft.
  - RULING 141 (2), STAND_ALONE soft (264d740a): a moment left out only by the opener rule comes back as a clip.
    - Flag: "The clip (<channel>) may not stand alone: <reason>." The integrator's batch 107 matches this exact prefix.
    - The topic rule, the medley naming Bitcoin and a hook's opener stay HARD.
- Ruling 107 (1)'s guard fix (71ff97fc): a call refused for money is work left undone. Seen working in builds 136 and 137.
- Integrator: batches 106 and 107 are live. A pin renders the moment READY arrives; the note lists "REVIEW FLAGS:" one per line.

## RULING 141 (13:40): IN FORCE
- The kept line-up (ca660f22 ...) is DROPPED; the clips-alone checker found no through-line.
- Stage 2b order:
  1. STAND_ALONE (DONE);
  2. the line-up chain as kept candidates, per the approved R136 design (2): clips-alone + joins + the question hook + coherence + writes / value;
  3. the hook bar (DONE early);
  4. the hook's non-crop frames. Ruling 70's third person is soft by design; ruling 93's crop through burned text is HARD.
- Money: ceiling $1.65 all-in today. One purpose only: a NEW line-up with a THROUGH-LINE, built from ONE story (stories/latest.json), story-first (ruling 118 (4)).
  - Lock pre-check first; step A only on that story's moments. Price before the first paid call.
  - If no story has 3 channels, say so on line 1 and re-check on each ledger change (scratch r141/story_fit.py, free).

## THE STORY ATTEMPT, NOW
- The story: S-196c50f1 "Self-custody and security risks". It has 3 channels only with STAND_ALONE soft: Yahoo Finance f0a51c45 has no scorer verdict.
- The set: /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/r141/ONLY_SELFCUSTODY.json, 7 moments: 6e79ceaa, ab69874e, feb4b72f (Natalie Brunell); 84884c9f, d427b949, 20cac687 (Bitcoin Magazine); f0a51c45 (Yahoo Finance).
- Step 1, the lock pre-check: r141/precheck_story.py, request pp-selectid.story141.*, started about 14:05. Drop any held span from the set.
- Step 2, the build: LOCK=on bash /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/build_and_record.sh 138 "RULING 141 (4): the self-custody story" --only /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/r141/ONLY_SELFCUSTODY.json --stop-usd 1.49
  - The stop keeps all-in <= $1.65.
  - Price: about $0.42 with 2 hooks passing; up to about $0.60 with 4.
- If it seals: SendMessage protocol-pulse-68 READY with the pin path (record dir MOMENTS_PIN_LEDGER.json) and the seal prefix (package_sha256[:12]).

## LOCKSTEP IN FLIGHT (ruling 142), written before any later section
- Local, UNPUSHED: 45ad6040 (the 142 mirror: canon.py byte-identical sha256 88e45f13..., attest.class_131 word_form
  exemption, RULES + ruling 142, DECODER fe809cb4e680) and b1216504 (the line-up chain phase A) on top.
- The integrator merges 45ad6040 exactly, after its batches 108 + 109 and its merged-tree run, then pushes; THEN I push
  (git push origin pp-selectid, a command of its own). Until then: NO build, NO watcher (the decoder would not match).
- After the push: the integrator re-judges f0a51c45 (Yahoo) and feb4b72f (Natalie) from cache; batch 111 (post_live
  fallback for MeC8YEmUx_w, format 140 audio + 137 video) is a SECOND sha move later; then re-send the Bitcoin Magazine
  spans one per request; when f0a51c45 + one Bitcoin Magazine span pass: price and GO the self-custody line-up
  (r141/ONLY_SELFCUSTODY.json, LOCK=on, --stop-usd 1.49) inside $1.65 (day $1.11 before it).
- Then re-arm the watcher; routine builds; r141/story_fit.py after each.

## MONEY
- Before the attempt: router $1.014, Scribe $0.096, all-in $1.11.
- The keeper day118.py prints a $1.40 cap; ruling 140 / 141 make it $1.65 today. From 21:10 ET: $1.50 a day.

## ROUTINE
- The ledger watcher is armed (watch_ledger.py --watch 300 1800). On CHANGED: bash /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/build_and_record.sh N "routine: ..." (free), then python3 -B /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/r141/story_fit.py, then re-arm.
- Build windows from Nov 18: 12:00, 15:30 and 19:30 ET.
