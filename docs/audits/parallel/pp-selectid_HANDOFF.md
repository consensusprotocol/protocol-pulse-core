# pp-selectid HANDOFF (updated 01:10 ET Nov 24; Nov 23's text below is history)

## RULING 159 (23:42 ET Nov 23): THE VERIFIER'S ROWS, NIGHT OF NOV 23-24
0. NO PAID BUILD TONIGHT. Pin afd8977d143e is NOT TO BE PUBLISHED (ruling 158: the Digital Asset News clip shows the Kraken
   banner and the iTrustCapital panel). The verifier re-runs its whole table and the end-to-end drill at 10:30 ET on the
   PUSHED code; the 12:00 build runs only on code it re-checked. Its report: /home/ultron/protocol_pulse/docs/audits/
   FIX_VERIFICATION_2026-11-23.md.
1. ROWS BUILT TONIGHT (each with tests that fail without it; every mutation killed; suites 42 files, 0 failing):
   - the 12 h exception switch REMOVED (driver: no --pbx-exception, --hours <= 12, the adapter on the render clock;
     package_pin: no pbx_exception soft gate, no cap of 5); the per-package kinds_cap row REMOVED (flags_cap = 3);
   - TestRuling121Reserve: checks the reserve the guard really holds against every recorded Grok bill (895, none over);
   - 156's 4 writes: a test that fails at 3 and 5; the trim come-back: a build-level test;
   - RULING 152 (1): proof_ly.WRITERS qwen, deepseek, gpt-oss, gemma, minimax, glm, then Grok; WRITER_DEADLINE_S 120;
     proof_ledger.writer_probe before every build (a replayed run probes nothing);
   - RULING 154 (2): an unrated opener (no rating ON the calibrated bar) opens flagged in the never-empty pass, at most 2;
   - RULINGS 154 (1) / 152 (2): providers.Router.call's stand-in judges in the never-empty pass (a Heimdall family that
     did not write, then any Heimdall family, then Grok; never a writer, a probe or a panel seat; glm never judges), the
     reply marked lx_soft, ONE soft "judge" row naming the checks; coherence_by_panel fills the seats a writer emptied;
   - RULING 158 (2): visual_pin visual-4 (question 5, advertising, on every clip), ad_block (question 5, offer phrases,
     "IRA" on a logo or banner; never a caption), HARD in every role and format, never 146 (1)'s 16:9 softening; the
     inventory's visual row FAILS an ad; fixtures tests/package/fixtures/visual_ads (the DAN frames, real answers);
   - THE AD-READ GAP: step A's view "ad_read" is its own HARD code AD_READ (never soft);
   - RULING 155 (2) ADOPTED: REFERENT_OUTSIDE is information on the pin unless the referent changes the claim
     (explicit "yes") AND step C does not find it entailed; the search counts step A's soft codes as ONE kind (157 (5));
   - RULING 143 AT SELECTION: a words-only L-v 2 failure waits for its line-up's lock pre-check (pass / adopt settles
     it; a hold drops it); Simply Bitcoin 513842ff (fixtures/lv2_513842ff.json) is the real case;
   - A BUG FOUND AND FIXED: ruling 156's plain lines sealed a line-up the lock held, whose frames were refused, or with no
     lock verdict (the write count set spent with no write made); audit A2's three fallback_fields findings fixed.
   - A SECOND ONE: a stand-in judge for step A's second screen could only be the first screen's own family (a hold made
     a refusal): step A takes only step 1 (a family that did not write or judge). And ruling 107 (1): a build whose word
     checks, hook onsets or trimmed cuts were NOT MEASURED leaves that work undone (never NOTHING NEW after it).
2. AUDITS (heimdall-audit, effort HIGH, 65,536 tokens; gpt-oss never answers in contract at that effort: 2 of 3 seats):
   docs/audits/parallel/pp-selectid_audit_20261124_0016_* (71d A2 / B2, C_judge, D_writers_hooks), _0047_E_ads,
   _0101_F_rows, _0106_G_c2fix, _0109_H_undone, _0129_I_fixes (cycle 2 of every fix); refutations in each folder's
   REFUTED.md. The 23:48 runs (32,768 tokens) were void: 1 seat answered.
4. THE VERIFIER'S OFFLINE DRILL: visual-4 asks every clip again, so a replay holds no recorded vision answer until a live
   build records them (a replayed run stops at vision); the writer probe does nothing in a replayed run.
3. NOT IN CODE: ruling 127 (1)'s by_hand_build.py (Nov 16, a Heimdall-only second screen); no build uses it. The record
   script build_and_record.sh and the three daily windows are still scratch tools, outside git.

## (history) TONIGHT, NOV 23 (updated 22:42 ET): THE FIRST VIDEO SINCE NOV 13 WAS SEALED (NOW: DO NOT PUBLISH)
1. SEALED: pin moments-ledger_20261124_033614-afd8977d (package_sha256 afd8977d143e), build 167, story 'Bitcoin hits
   two-year low, then bounces off the bottom': Simply Bitcoin (hook) + Digital Asset News + Yahoo Finance, 35.6 s of
   clips; our lines the plain fallback; 5 flag kinds (this pin's cap 5 by ruling 157 (1)). The integrator renders it
   since 22:39 (run 20261124_033913, about 50 min) and sends the Telegram ids or the exact gate.
2. LIVE (pushed, 71d3d0363 and before): rulings 150, 146 (3), 153 (143's mirror, DECODER 9326604699a7), 155 (1)
   (kinds), 156 (plain fallback lines, audited), and BY HAND tonight (tests 331; audit 20261123_2240_hand running):
   the line-up stage's soft edge, context_soft (step A's soft codes on clips in the context check), 157's one step A
   sentence and one our-lines kind, fallback_vo_soft, the sealed kinds_cap row (one package; the standing cap 3).
3. NOT IN CODE YET: ruling 152 (1)'s writer chain + probe (built in dev59, not landed: the order question vs the
   coherence panel, 19:44); 152 (2) / 154 (1) (the judge fallback when the writer's vendor is the only judge); 154 (2)
   (an unrated opener); 155 (3) (an angle that breaks the contract retried with the contract quoted). Tonight these ran
   BY HAND: scratch r23/by_hand_166.py (writers probed, qwen first, 120 s; gemma + glm extra coherence-panel seats;
   KINDS_CAP / STEP_A_SCOPE for that one package). For a new attempt copy by_hand_155.py (no cap override).
4. THE SHARED HEIMDALL HEALTH can fall to plan_b when no build runs (deepseek 503 all evening): before a build, if
   tests/package/proof/HEIMDALL_HEALTH.json says plan_b, run scratch r23/probe87_now.py (ruling 87's own probe loop).
5. NEXT: (a) the integrator's delivery; (b) ruling 155 (2): the per-code step A rates on line 1, the orchestrator
   rules on the checker tomorrow; (c) land 152 (1)/(2), 154 (1)/(2), 155 (3) audit-first; (d) the three daily windows
   (12:00, 15:30, 19:30 ET) without cron: the story-first chain (routine build -> story fit -> lock pre-check of the
   best story's spans that do not expire within ~2 h -> the paid attempt with the by-hand wrapper) as one scheduled
   script, which does not exist yet.

## (history) PAUSED BY PBX (10:51 ET Nov 18): resume only on the orchestrator's RESUME
1. LIVE (pushed on pp-selectid): ed9df3f28 batch 114 mirror (decoder 50fa01b400bd) + package_pin.flags_cap (5 on the pbx_exception pin); 1be22777c STAND_ALONE come-back beside a trim variant; d2477a02f attest.class_131 compares the merged reading as tokens (the '24 7 365' false hold); d0147dc6e the standing 30 s floor + 'runs short' flag (never-empty pass; 'runtime' in SOFT_GATES). Integrator: batch 114 merged; its batch 115 (G5/R4 follow the runtime row) was landing; its 113 + 139 decoder lockstep waits.
2. IN PROGRESS, NOT LANDED (scratch dev copies under /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad): (a) ruling 150 (1) BY HAND in dev61: package.VALUE_SOFT_LINE + driver --value-soft-line (only that exact line's MEASURED value LOST, never-empty pass, goes on to fidelity), takeaway_value row FLAGGED 'The closing line may mostly restate the clips: "<line>"', SOFT_GATES += takeaway_value; tests pass, mutations 6 of 6, suites 42 files / 944; audit pp-selectid_audit_20261118_1044: C1 qwen + gemma no P0/P1 (gpt-oss no verdict), C2 qwen + gpt-oss no P0/P1 (gemma no answer). (b) ruling 151 (10:52): this pin's cap 6 (package_pin.PBX_EXCEPTION_CAP 5 -> 6; standing cap 3): NOT started. (c) ruling 146 (3) (sponsor-before soft, the exclusion model judges) in dev59: tests pass, mutations 8 of 9 (S8: gate_problems never checks the extra 'sponsor' row), no audit.
3. NEXT ON RESUME: land (a) + (b) (its test: 6 seals, 7 refuses; one clean audit cycle on (b)); then build 151: LOCK=on bash /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/build_and_record.sh 151 "RULINGS 150/151: build 150's line-up, write 1" --only /tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/r144/ONLY_144.json --stop-usd 1.39 --hours 26 --pbx-exception "PBX exception Nov 18: these clips are older than 12 hours (allowed for this one video only)" --value-soft-line "<write 1's exact text from build 150's record ledger_20261118_150615>"; seal -> READY to protocol-pulse-68 (pin path + package_sha256[:12]). THE 30 h EXCEPTION WINDOW for feb4b72f / 20cac687 closes about 15:56 ET Nov 18: after it, this pin needs a new ruling. Then today's pool (cap 3, the floor), the integrator's 113 + 139 decoder mirror, (c)'s audit.

## RULING 148 / 149 (updated 10:25 ET Nov 18): three lines for a compaction
1. WHAT IS LIVE (pushed on pp-selectid): ed9df3f28 = the batch 114 mirror (decoder 50fa01b400bd) + package_pin.flags_cap (5 on the one pin with the pbx_exception row, 3 elsewhere); 1be22777c = the STAND_ALONE come-back beside a trim variant; d2477a02f = attest.class_131 compares the merged reading as its tokens (the '24 7 365' false hold, rulings 148 (3) / 149); d0147dc6e = the STANDING 30 s floor: never-empty pass only, clips >= 30.0 s, under 36.7 s the sealed gates.runtime row FLAGGED 'This video runs NN seconds, shorter than usual.' (counts toward the cap), 'runtime' in SOFT_GATES (the integrator's batch 115 makes its G5 / R4 follow the row). The scratch recorder (build_and_record.sh) now quotes the never-empty pass's reason on line 1.
2. YESTERDAY'S BATCH IS STOPPED (148 (6) / 149): (a) the sell-off: 3 channels but 25.1 s, under the floor; (b) Natalie Brunell 6e79ceaa is the opening line of The Bitcoin Way's ad read (sponsor material: never in); build 150 (ledger_20261118_150615: 20cac687 + f0a51c45 + feb4b72f, 37.2 s) passed the lock but ruling 91 refused the takeaway (HARD: write 1 restated, its rewrite failed VO fidelity COMMENTARY + context, write 3 NEEDS_SOURCE, write 4 missed; no no-voice line-up). Router $0.85 of the $1.39 stop, plus the lock pre-checks' Scribe.
3. NEXT: the 12:00 ET build on TODAY's pool (the full new process, the cap of 3, the 30 s floor with its flag; no --pbx-exception). Mirror the integrator's ONE decoder lockstep for batch 113 (ruling 143) + ruling 139's render-lock half when it sends the files and DECODER (target before 11:30 ET): byte-identical, my side READY unpushed, it merges and pushes, then I push. Then ruling 146 (3) in code (a sponsor mention in the sentence BEFORE is SOFT, flagged 'The clip (X) comes right after a sponsor mention.'; the clip's own words in the ad stay HARD).

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
