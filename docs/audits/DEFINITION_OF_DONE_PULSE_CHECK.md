# DEFINITION OF DONE — PULSE CHECK (living document, started 2026-11-11 02:52 ET)

Every PBX rule mapped to the check that enforces it and the must-fail test that proves the check
works. A rule with no check is listed as **UNENFORCED** (in red), never left out. Updated as the work
lands; the commit that changes a row is named in it.

Legend: G = gate (runs in run_fresh.stage_gates / pre-render stage), T = must-fail test file.

## 07:23 ET PRE-CHECK (ruling 07:25) ON clip_02 -> 'does.': NOT CLEAN; no clean sentence end after it within 20 s

- The cutter's own geometry (main, acquired window runs/pinned_20261112_120225) places 'does.''s OUT at 30.82 (pause and neighbour-clear OK), but the clip's tail then carries the HOST's backchannel "Mm." (second recogniser speaker_1, 29.92-30.04; audible 29.89-30.12): another speaker inside the clip, and a likely prepare edge-word failure ('Mm' heard last). A clean pause exists at 29.64-29.88, but the cutter does not aim there (the primary decode times 'But' 0.5 s early, so its pause search spans the 'Mm').
- After 'does.': 'mass.' = 22.45 s (> 20 s) with the 'Mm' inside. The only clean end in this moment is 'existed.' (YouTube 535.62; cut 7.02 s; R4 runtime estimate then about 59.7 s unless the VO grows by about 1 s). Written to docs/audits/parallel/integrator_RULING7_FACTS.md for the builder. No render spent.

## TONIGHT'S MOMENTS-FIRST VIDEO, RE-SEALED PIN f409e9d9 (GO 07:03): RESULT 07:07 ET = HOLD AT STAGE `prepare`, NOT DELIVERED

- Run runs/pinned_20261112_120225 (HEAD 3db3e96a; pin data/moments_pins/MOMENTS_PIN_065928.json, checked on its own content). Passed: preflight (after the 07:00 false start, bible E-FAIL-057), env, pinned, review, validate (R4 moments 30.49 % of 64.94 s; editorial laws; stand-alone), cut (all three ACCEPT under the existing rule: ruling 7 not needed), sentence_law G16 (all PASS), voice.
- STAGE `prepare` HOLD, real cause (CLIP_CONTRACT.json): clip_02 (Natalie Brunell, wdk5JZ9hPzs) edge-word check on the PREPARED clip: expected last word 'emerges.', re-transcription hears 'emerged' (tail '... and that's what emerged.'). The cut OUT is 26.93 s while the primary decode ends 'emerges.' at 27.00 s: the cut most likely sits inside the word's low-energy '-s' tail (a clipped edge word: integrity, L-o (2)); the gate failed closed. hook and clip_01 passed (edges 'Bitcoin'/'that.' and 'I'/'US.'). Nothing was loosened or sent; GPU0 released by the run.
- EVIDENCE (07:08, the acquired source, 10 ms frames): 'emerges.' 26.28-26.84, 'And' 26.98: the voiced part ends about 26.92; the cutter's quiet run (26.92-26.93) sat BEFORE the word's final sibilant, a 40 ms burst above 4 kHz at 26.94-26.97 that abuts 'And' at 26.98. No pause: the speaker runs 'emerges-and' together (the continuation the second recogniser heard: 'emerges, and it doesn't matter ...'). The gate was right: the clip's last sound was cut off. RECOMMENDATION (builder's call, nothing changes in the checks): end clip_02 at 'does.' (14.42 s, YouTube 528.88-543.30; both recognisers end the sentence there; the source is quiet in both bands from 29.61 s, file time, after a short sound at 29.23-29.60 that is likely the host's 'Mm' backchannel: the cutter's neighbour-clear decides). The builder's CUTTABLE gate checked recogniser punctuation only; ruling C asks for the renderer's own sentence lock and cut geometry (pause, neighbour-clear) on the window, which would have caught this before sealing.
- CORRECTION (07:08): the Heimdall audit legs this session reported as 'no findings' did not all review. deepseek returned NO ANSWER in every Heimdall run tonight (reasoning hit max_tokens 16384, content null); qwen27b answered PASS (confidence 0.92) on batch24 c1 and batch25 c1 / c2 only, and returned no answer on E cycles 8 and 9 and on ruling 7 cycle 1. So: the subject change and R4 were reviewed by claude-fable-5-2 (two cycles each) plus one Heimdall model; E cycles 8 / 9 by claude-fable-5-2 only; ruling 7 by NONE yet (its fable leg died with the stopped shell, then Anthropic answered 'credit balance is too low' at 07:02; OpenAI has been out of credit since 04:37). Ruling 7 is not merged (the 07:07 render did not need it: every cut was accepted under the existing rule); it is re-audited in two smaller parts before any merge (bible E-FAIL-059).

## TONIGHT'S MOMENTS-FIRST VIDEO (orders '06:00' / '06:22'): RESULT 06:34 ET = HOLD AT STAGE `cut`, NOT DELIVERED

- Run runs/pinned_20261112_113058 (HEAD a5ec0f17; pin data/moments_pins/MOMENTS_PIN_062925.json sha256 12eff4b2..., package_sha256 add8c732..., the seal recomputed and every sealed gate PASS; started 06:30:16, ended 06:34:05, run_fresh exit 3). Passed: env, pinned (3 windows acquired + transcribed on GPU0), review (gemma3:27b), validate (R1-R10 incl. the new R4 moments: VO 19.80 s = 30.79 % of an estimated 64.30 s; editorial laws L0 + 1-4 PASS; stand-alone all PASS).
- STAGE `cut` HOLD, real cause (CUT_ACCEPTANCE.json): the sentence lock (integrity, L-o (1)-(2), fail closed) found no sentence boundary in OUR Whisper transcript at two locked edges: clip_01 (What Bitcoin Did, c1JGheQBPH4) IN 'unpunctuated transcript stretch: no sentence evidence' and OUT 'bitcoin' does not end a sentence; clip_02 (Natalie Brunell, wdk5JZ9hPzs) OUT 'secure,' does not end a sentence. The package's approved text ends both on a full stop (its store transcript's punctuation); the transcript this render acquired does not. Nothing was loosened; nothing was sent to Telegram. GPU0 left as found (the run released it).
- EVIDENCE (runs/pinned_20261112_113058/transcripts, the acquired verbatim decode): clip_02 is a REAL mid-sentence cut: the speaker goes on '... all it has to do, is stay decentralized and secure, | and that's what emerges.' (the store's caption punctuation put a full stop after 'secure'): the integrity rule caught a package edge that is not a sentence end. clip_01: the IN sits in a restart, '... with some of these hacks like it's it's not | it's not Bitcoin that's getting hacked' (no punctuation in that stretch: the prompted reference decode transferred 7 marks to this transcript, none there), and the OUT runs on, '... the unique nature of bitcoin | um so if there's any um uh you know, targeting ...' with no full stop. The hook (Saifedean Ammous) passed: '... very fundamental. | Bitcoin ... chose to do that. | Your friends chose ...'.
- WHAT WOULD MAKE IT RENDERABLE (the packager's call, nothing changes in the checks): clip_02 to its real sentence end ('... and that's what emerges.', about 1.5 s longer, still <= 20 s, estimated runtime about 66 s); clip_01 to edges our transcript proves (or another moment). Request for pp-selectid / pp-ingest (bible E-FAIL-056): before sealing, check every moment's two edges with the cutter's own sentence evidence on the word-timed decode the render will acquire (sentence_law on Whisper words), not on caption punctuation. GPU0 stays free for the corrected pin (nothing else started).
- MEASURED ON THE ACQUIRED DECODE (06:37; sentence_law.is_terminal, the cutter's own test): clip_02's nearest proven sentence span is 'Bitcoin is a new system of measure ... stay decentralized and secure, and that's what emerges.' = 11.96 s (YouTube wdk5JZ9hPzs 528.88-540.84; after 'now?'): renderable once the package carries that span (its gates re-run on the new words). clip_01 cannot be cut from this source with sentence evidence: the decode of c1JGheQBPH4's window is verbatim and unpunctuated from the window start to 'focused.' at 35.88 s ('i i don't think that bitcoin itself is is going to be uh viewed with suspicion ...'), so it needs another moment (R5 still needs >= 2 clips). A READY line with a NEW package_sha256 is rendered the moment it is readable (watcher re-armed; the add8c732 line is ignored).
- 06:42 RULINGS '06:45' FACTS (docs/audits/parallel/integrator_RULING7_FACTS.md; scribe_v1 on the acquired windows, $0.016): clip_01 FAILS ruling 7 condition (1) at its IN (scribe: '... like it's, it's not, it's not Bitcoin that's getting hacked, it's, um ...': no boundary; the sentence began at 'And in fact ...'): the builder supplies the next-best moment. clip_02: the decoders DISAGREE at 'emerges' (primary 'emerges.' terminal; scribe 'emerges, and it doesn't matter what the other system does.'): to 'emerges.' 11.96 s locks under the existing rule; to 'does.' 14.42 s (YouTube 528.88-543.30) is the end BOTH recognisers agree on. The original 'secure,' OUT continues in both (ruling 7's must-fail holds).
- 06:44 TIMING: the render path measured 51.3 min tonight; a pin re-sealed at about 07:00 reaches Telegram at about 07:55 (no stage skippable). Ruling 7 is being implemented in a scratch copy (main's pipeline tree must stay clean for the render's preflight); it lands with its must-fail tests and audit after this delivery, since clip_01 fails it on the facts.

## PAID OUTSIDE-MODEL SPEND TONIGHT, BY VENDOR (orchestrator order 05:30 ET; read 05:37 ET from each session's own STATE and ledgers; SPEND FREEZE since 05:30)

Window: 2026-11-11 18:00 ET to 05:37 ET. "Recorded" = a ledger or a usage line per call, priced as that ledger prices it; "est." = a tool that keeps no usage. Prices used where this record priced usage itself: claude-fable-5-2 $8/$40, claude-opus-5-5 $4/$20, claude-sonnet-5-5 $2/$10 per 1M input/output tokens (Anthropic list, the claude-api reference cached 2026-11-03); gpt-6.1-sol $15/$120 (the price pp-tests and pp-selectid used; pp-selectid calls it an upper bound); grok-4.20 $5/$25 (pp-selectid's assumption).

| session | Anthropic | OpenAI | xAI | Google | Heimdall | recorded total | est. (no usage kept) | source |
|---|---|---|---|---|---|---|---|---|
| integrator (this session: audits only; renders and editorial ran on GPU0 at $0) | 47.23 (32 claude-fable-5-2 reviews) | 36.56 (26 gpt-6.1-sol reviews; 6 refused for no credit, unbilled) | in the shared gateway line | - | in the shared counter | **83.79** | ~3-5 (cross-LLM tool legs: gemini, gpt-4o, grok) | usage line of every FRONTIER_*.md since 18:00 (68 files, 4 duplicates counted once) |
| pp-selectid | 29.96 (phase 1 fable 10.51 + opus 1.28; phase 2 1.44; audit reviews 16.74) | 23.18 (phase 1 ~2.97 = ledger total minus its per-model rows; phase 2 20.21) | 34.70 (grok-4.20: phase 1 13.36, phase 2 20.21, audit 1.13) | - | 1.72 (priced at an assumed $3/$15; the gateway meters far less) | **89.56** | - | tests/select_by_id/proof/SPEND.json (28.11), tests/moments/proof/SPEND.json (43.58 at 05:29), audit usage lines (17.87) |
| pp-backtest | 45.35 (oracle 35.01 + audit reviews 10.34) | 19.08 | 3.22 | - | 0.09 | **67.74** | ~3.2-3.7 | its STATE, top (05:33) |
| pp-tests | 11.31 | 5.76 | - | 3.17 | - | **20.23** | ~6.50 | its STATE, top (05:31) |
| pp-ingest | 10.28 (claude-opus-5-5: watcher 7.17, of which 6.69 was the outage drill; A/B 3.11) | - | 3.31 (A/B blind judge grok-4.20 3.22; audit 0.09) | - | 0.20 | **13.79** | ~1 (audit legs gpt-4o, gemini-3.1-pro) | data/editorial/ingest/queue.sqlite calls, ab/attempts.jsonl, audit results.json (it has not yet written its own 05:30 line) |
| shared xAI audit gateway (all sessions' cross-LLM grok legs) | | | 1.06 (59 requests; 96 refused at its $1/day cap) | | | 1.06 | | data/xai_budget.json (UTC day 2026-11-12) |
| **all** | **144.13** | **84.58** | **42.29** | **3.17** | **2.01** | **~276** | **~14-16** | **~$290 in all** |

- The two largest lines: pp-selectid's stand-in writing and verdicts (~$90) and this session's own frontier audit reviews (~$84: fable $47, gpt-6.1-sol $37). PBX's "about $95" is about one third of the recorded total.
- Heimdall's own credit counter moved 33.69 -> 34.23 over the night (pp-backtest's reading; shared by all sessions): about $0.54 actually metered. pp-selectid's 1.72 is that session's upper-bound price, not a metered amount.
- Overlap: pp-backtest's grok-3 (~1.77) and pp-tests' grok (~0.95) audit-tool estimates may include calls on the shared gateway line, so the xAI total can be high by up to ~2.
- Not in dollars: ElevenLabs (TTS for renders and one STT call at 0.002): subscription characters; no per-call dollars recorded.
- FROM 05:30 (this session): a paid audit leg only where a commit strictly requires one, each under $2: Heimdall and local legs first; a claude-fable-5-2 leg only with its output capped so input x $8 + max_tokens x $40 per 1M stays under $2; gpt-6.1-sol is out of credit (HTTP 429). No other paid call.

## LIVE STATE (updated 2026-11-12 06:22 ET; newest first)

- 06:22 ORDERS '06:00' + '06:22' (blocking tonight's video): (1) EDL rule R4 re-set for packages of type 'moments' ONLY (law L-q; a TASTE rule, recorded under L-o / L-q in PIPELINE_LAWS.md, the gospel and the bible): VO share <= 40 % of the TOTAL estimated runtime ('06:22'); one VO line per slot: after the hook, after each clip, after the LAST clip (the takeaway); the estimated runtime (hook + clips + VO + 14.30 s tail) HARD inside 60-70 s; word caps unchanged; story-type / untyped pins keep the old R4 (edl_rules._r4_moments; pinned.moments_vo allows after_clip == last for type 'moments' only; build_edl records package_type). Renderers read, not changed: render16 and render_vertical place a line after the last clip before the shout-out and render a VO line of any length (still frame + 1.0 s pre-roll + the wav); to be verified on the real render. Fail closed (audit cycle 1, claude-fable-5-2 $0.41, Heimdall $0.009 no findings): a 'moments' EDL without a validated package, an unmeasured duration, bad clip indexes, an empty line; limits on exact values. Must-fail tests (test_edl_rules TestR4Moments, test_pinned takeaway test, end to end from build_edl): VO share 41 / 40.5 / 40.1 % rejected, 40 % passes; runtime 59.9, 59.996, 70.004 and 70.1 rejected, 60.0 / 70.0 pass; a line with no slot rejected; mutations (limit 0.404, rounded runtime, no package binding, missing duration as 0, empty line allowed, no slot check, no runtime check, moments rule for every EDL) each fail a test. Cycle 2 audit runs after this commit (it cannot move HEAD during the render). (2) THE STAND-ALONE SUBJECT of a moments-first package is its label 'bitcoin' (R7 item 4), never its written title (E-FAIL-055; batch24, two cycles: fable $0.12 + $0.17, Heimdall no findings). (3) GPU0 FREED at 06:18:52 for the render (order '06:22': it showed 23.9 GB held by Ollama): this session's R5 A/B stopped by SIGTERM (the judge row was done; the witness row stopped at 6852 s with no result recorded), gemma3:27b unloaded, GPU0 at 18 MiB with no compute process. Nothing else starts on GPU0 until the package is delivered. (4) A READY watcher on pp-selectid's STATE first line freezes the pin (copy + sha256 under data/moments_pins/). Regressions on this commit: regression_test.sh 0 FAIL, pipeline/regression.sh PASS (the preview reference reproduced).
- 05:38 ORDER '05:30' (SPEND FREEZE; one priority: render pp-selectid's rebuilt package the moment it lands, REVIEW ONLY): READY. (1) A watcher is running since 05:33:41: it polls the pp-selectid worktree every 15 s for a MOMENTS_PIN*.json written after 05:25 and checks it on CPU (scratchpad check_moments_pin.py: the top package must carry a blind coherence verdict with every rating >= 4 and a through-line, so a plain-VO fallback is not ready; the pin's package_sha256 must be that package's hash, by package_pin.py's own formula; main's pinned.validate_schema and the strict R7 moments_vo must accept it; tested on the 03:25 package and on synthetic pass, low-rating, no-through-line and wrong-package cases). (2) On READY it freezes the pin and package (copy + sha256 under data/moments_pins/), SIGTERMs this session's own R5 A/B (pid 3913594: it stops its child, unloads gemma3:27b, verifies it gone, releases the lease), waits until the GPU0 Ollama is empty (it unloads only gemma3:27b, the model the A/B loaded; anything else stops the start), then runs scripts/pulse_check_run.sh --foreground --no-telegram --pinned <frozen pin> (both formats, every gate). Delivery: presend_check.py, the contact sheets by eye, then deliver_moments.py (REVIEW ONLY label, the L-w 5 card with per-clip source links). No commit to this branch while that render runs (a moved HEAD holds a run). (3) Spend table at the top of this file. (4) Correction: the status lines this session wrote 05:28-06:10 carried estimated times, not `date` output (the clock read 05:37 when the last of them said 06:10): every time is read from `date` again.
- 05:15 HARDENING (behind the others): the worktree's superseded GPU0 draft (batch 20) is taken out (files moved to the scratchpad; preflight / run_fresh / backtest / render16 / render_vertical / pulse_check_run.sh / test_preflight reverted; the claim hunks removed from story_semantics and qa_gates, whose module guard now equals main's), leaving only batch C (18) and batch E (19). E cycle-7 tests added (27 pass); C and E CPU files 74 pass. INCIDENT E-FAIL-054 (bible): a pre-L-r test file (test_g3b_majority) tried to load Whisper on GPU0 without the lease while the R5 A/B held it: OOM x5, nothing loaded, the A/B unharmed; rule: only named pure-CPU files run in a pre-L-r branch. Main: L-r follow-up 2 c14a339e (render_vertical and qa_gates guarded too, AST + behaviour tests). R5 local A/B, judge row: gemma3:27b agreed on 10 of 25, caught 0 of 8 must-fail swaps (the bar needs all 8): the judge stays frontier; witness running.
- 05:02 MERGE (priority 4): pp-ingest DONE at 753dec1d audited by the integrator, cycle 1 (claude-fable-5-2; gpt-6.1-sol out of credit): 4 BLOCKING (the 90 % Heimdall tripwire halts the leg instead of notifying, law L-x; an ~80 min outage turns into silent permanent loss of moments counted as mined; one age-gated video stalls all YouTube access; the local leg's GPU0 'lease' is an env string, closed on merge by main's L-r LocalLLM.require). NOT MERGED; findings in ~/worktrees/pp-ingest/docs/audits/parallel/pp-ingest_INTEGRATOR_AUDIT.md.
- 05:00 NO MOMENTS-FIRST PACKAGE TO RENDER: pp-selectid HELD AT ITS SPEND GUARD at 05:00 ($39.28 of $40; OpenAI out of credit again since 04:37, its L-x failover moved the writer to claude-fable-5-2). Four angle-first rebuilds, ~30 write-and-gate attempts over 12 angles, produced no package passing every gate; the integrity gates held (no unsupported claim, false relation or stale price reached a package). Blockers: context step C 'stronger certainty' (the VO firming a hedged clip) and the fidelity judge's 'uncertain' on PBX MAX's own synthesis lines. Its options for the orchestrator (it takes none itself): (a) calibrate each gate's false-reject rate on pp-tests' exam; its local leg (gemma3:27b) is the integrator's, free, under the GPU0 lease; (b) more frontier budget (~$2-3 per passing package); (c) a quote-led VO style. The render path is READY and stays ready at f7a26b4e (L-r, R7 strict, L-o R5). Meanwhile on GPU0 under the lease: the R5 local A/B rows (judge done, witness running, then grouping), then the L-r back-to-back double run. The integrator offers to run (a)'s local leg on GPU0 as soon as the orchestrator says so.
- 04:47 MERGE (priority 4): pp-tests DONE at c35a2bde audited by the integrator, cycle 1 (claude-fable-5-2; the gpt-6.1-sol leg failed: OpenAI HTTP 429 credit_balance_exhausted again): 4 BLOCKING (F3 family can vanish as a skip via importorskip; the F2 template contradicts its own R-23 so strict xfails would XPASS for the wrong reason; REQUESTS R-19 loosens the quote check; R-02 / R-03 as written verify an empty quote). NOT MERGED; findings written to ~/worktrees/pp-tests/docs/audits/parallel/pp-tests_INTEGRATOR_AUDIT.md. pp-ingest DONE at 753dec1d (new pipeline/ingest/*, 14k lines): its merge audit follows. Still waiting on pp-selectid's rebuilt package (attempt 3 at 04:20); main ready at f7a26b4e; the R5 local A/B: judge done (2226 s), witness running.
- 04:16 L-o WIRED AT edl_rules R5 (pp-selectid REQUESTS R6 item 2; so a moments-first package's short punchline clip does not HOLD at validate): INTEGRITY kept as failures: >= 2 clips from >= 2 distinct named channels, every clip with a measured positive finite duration (0, negative, NaN, inf, None, strings, bools, overflowing ints, a missing duration or channel: FAIL); TASTE: a clip outside L-o's 12-20 s target is a recorded deviation with its size (into PROVENANCE through run.prov['edl_validation']), never a rejection; the per-channel >= 8 s floor removed (L-o names none). Audit batch23_L-o_r5: two cycles (gpt-6.1-sol, claude-fable-5-2), every finding fixed; tests 71 + 14 subtests; regression_test.sh 26 / 0 / 4; pipeline/regression.sh exit 0 (preview reference reproduced). Remaining L-o sites (select_passages:333 duration and the AUTO selector's windows) are not on the pinned / moments path.
- 04:03 L-r COMMITTED: 4867a74a (pushed) + follow-up 34ba7726 (pushed). Audits on the actual diff, three cycles (batch21_L-r_gpu0): cycle 1 BLOCK (fable, gpt-6.1-sol), cycle 2 BLOCK (fable, gpt-6.1-sol; gemini and heimdall no defects), cycle 3 verification (fable, gpt-6.1-sol): every finding fixed or accepted with its reason. Tests: test_gpu0 40 (five mutation-proven must-fails), test_gpu0_live 6/6 on GPU0 (the Nov 12 incident replayed both ways; a real OOM caused by a resident Whisper recovered), CPU suite by file 39/45 clean with the 6 GPU files passing 57/57 in a GPU session, regression_test.sh 26 PASS / 0 FAIL / 4 WARN, pipeline/regression.sh exit 0 (preview reference reproduced). Pending: the back-to-back double run (PP_GPU0_LIVE=1, ~2 x 50 min of GPU0) after tonight's render; the live re-run of 34ba7726's follow-ups when GPU0 is free. R7 item 1 committed next (below); R5 local A/B rows running on GPU0 under the lease (judge first), to be stopped when the rebuilt package lands.
- 03:42 NOTE '03:40' (pp-selectid's first moments-first package was rejected on quality, no angle and a misleading title; a rebuilt one is due within the hour): READY-TO-RENDER plan. R7 item 1 (pipeline/pinned.py: the package's VO intro + one bridge after each clip but the last, its ONE title and caption, its sha256 and gate verdicts into the EDL; a package without BOTH VO-fidelity and context-integrity passes, or with a bridge the renderer cannot place, is refused) is APPLIED IN THE MAIN TREE, not the hardening worktree, and audited there (batch22_R7_moments_pin): DECISION (logged, not asked): tonight's render runs from the main tree, where law L-r's GPU0 plumbing lives; the hardening worktree carries batches C / E still mid-audit, and the 00:05 order forbids rushing hardening into a video; R7 joins hardening-redteam at its merge. Tests: test_pinned TestMomentsPackage (3; the refusal proven load-bearing by mutation). Local A/B rows of pp-backtest's REQUESTS R5 run on GPU0 under the lease once L-r is committed and until the rebuilt package lands; then: render both formats through every gate, deliver REVIEW ONLY with per-clip source links (~30 s before each clip), flagged risks, both file hashes, the one title and caption (law L-w 5).
- 02:48 NOTE '02:45' (PBX: off any one LLM, onto Ultron, fully autonomous): law L-x NO SINGLE MODEL, ULTRON FIRST written (PIPELINE_LAWS.md, gospel, this DoD's law table, bible): one provider interface per model role with >= 2 back-ends, local gemma3:27b the default wherever it meets the bar (blind A/B per role on saved data: local under the GPU0 lease by the integrator vs frontier vs Heimdall, re-run so roles migrate local), no vendor or model name outside the provider config, generator != judge, Heimdall 90% spend tripwire = NOTIFY ('HEIMDALL SPEND AT 90%' at the top of STATE) with fallback, never a halt. The hardening branch's drafted E law moves to letter L-y.
- 02:47 BTC IN DC TAKEDOWN (orchestrator order 02:45; the organiser wrote that no partnership agreement exists): DONE, commit 38ef9ff4 (pushed). Every public reference is behind one reversible Jinja flag per template, show_btc_in_dc = false, noted 'Restore when the BTC in DC partnership agreement is signed: set show_btc_in_dc = true' (no design deleted). REMOVED: /events title, meta description, og:title, og:description, the hero's 'Two flagship events' (now 'Our flagship event.'), the countdown's 'Coming Next: BTC in DC - Kennedy Center', the BTC in DC flagship card (Sponsor This Event / Get Notified; senators / White House highlights) and its countdown script line; /sponsors (= /advertise, /media-kit) the 'BTC in DC - Kennedy Center - Date TBD' block with 'Inquire About Sponsorship'; the /map pin (and the unused core/templates copy); the sponsor-outreach email prompts' 'BTC in DC at the Kennedy Center' (core/services and services sponsor_outreach_service.py, sponsor_radar.py; original kept in a restore comment). Stale years fixed where trivially safe: /events badge 'Live Events - 2025-2026' -> 'Live Events', BitcoinDay Naples 'Date TBD - 2025' / 'TBD 2025' -> 'Date TBD' / 'TBD'; /sponsors badge 'Media Kit - 2025-2026' -> 'Media Kit', Naples 'Date TBD - 2025' -> 'Date TBD' (no new date claimed). DEPLOYED: Waitress on :5000 (the process cloudflared maps protocolpulse.io / www to) restarted alone, same command, directory and environment (old pid 1386251 since Nov 7 -> new pid 2903746); nothing else restarted. VERIFIED LIVE from outside (curl -A 'Mozilla/5.0' https://protocolpulse.io/...): /events 200 (57027 bytes, title 'Events — BitcoinDay Naples | Protocol Pulse'), /sponsors 200, /advertise 200, /media-kit 200, /map 200, / 200: 0 matches each for BTC in DC | BTCinDC | btcindc | Kennedy Center (before the restart: /events 11, /sponsors 3). LEFT, and why: code docstrings never rendered (core/routes_pages.py:3111, routes.py:9504 'Events hub — BitcoinDay Naples + BTC in DC'); backup files not served (core/routes_pages.py.bak.faye, core/routes.py.bak); internal docs (SESSION_3_ALLIN_PLAYBOOK_BUILD.md, docs/archive/ copy); scraped third-party tweets (data/tweet_study/raw_tweets.json); the site-wide structured data 'foundingDate': '2025' (a fact, not an event date). Past coverage for PBX to decide: NONE found (the site DB instance/protocol_pulse.db, every text column, and core/data/articles: 0 matches).
- 02:31 NOTE '02:35' (PBX decisions on the strategy audit), recorded: (1) LAUNCH CADENCE = 2 videos/day to start (law L-p: 3-5 h stays the later target; step up on approved-without-edit evidence). (2) frontier-model spend for writing and checking APPROVED ($100/month fine, up to $300+/month if the videos drive engagement): use the frontier model wherever it buys quality (angle, VO, title, fidelity, context) and report dollars per video. (3) partner written opt-in: SKIP (no outreach is built); the per-channel caps (L-u) stay, plus a simple opt-out registry file the selector honours. (4) a fifth session, pipeline_pp_ingest (branch pp-ingest), builds continuous ingest + first-pass moment mining on Heimdall with a fallback, feeding an append-only moment ledger; packaging reads 'best unused moments since T' from that ledger; pp-selectid publishes its moments / package input contract early in its STATE so pp-ingest can match it. VOCABULARY: PBX found 'legal line-up' confusing: in everything PBX may read (captions, reports, STATE summaries) say 'a line-up that passes our rules', never 'legal'; tonight's law texts (L-n, L-o, L-p) and the request to pp-backtest are reworded accordingly (history entries of earlier days are left as written).
- 02:25 ORDER '02:30' (strategy audit; all four reviews read in full: /home/ultron/heimdall_probe/pp_redteam/strategy/claude.md, gpt.md, grok47.md, grok420r.md): laws L-s CONTEXT INTEGRITY, L-t ALL AUDIENCE-FACING TEXT IS UNDER THE GATES, L-u HARD EXCLUSIONS AND SCORING, L-v SPEAKER AND TRANSCRIPT TRUTH, L-w OPERATING RULES written into PIPELINE_LAWS.md (LAW 26 family), the gospel, this DoD's law table and the bible, with the amendments they make: L-n by L-w (6) (reported numbers; the oracle on selector holds only, its witness under L-s / L-u / fidelity), L-o by L-s and L-t, L-q by L-w (3) (story-first kept as a preferred package type). The hardening branch's drafted E law moves to letter L-x. Builder: pp-selectid phase 2 (nothing DONE without L-s..L-w); pp-backtest asked (its REQUESTS file) for the story-first-with-bent-taste vs moments-first vs frontier comparison. L-r (priority 2) IN PROGRESS, uncommitted: pipeline/gpu0.py (lease, require, swap_to with measured requirements, one Model per key, Gpu0Stop stops as BaseException, PeakSampler); loaders wired (Whisper in select_passages / cut_accept / word_diff / transcript_store / qa_gates, resemblyzer, the Embedder, Ollama, 18 NVENC functions); run_fresh (lease at env, foreign HOLD, one OOM retry with both attempts in PROVENANCE, per-stage peak table in REPORT.md), replay, preflight (holds the lease, leaves GPU0 as found), backtest, the wrapper's fd 8, pytest conftest; CPU tests so far green (test_gpu0 18; punct / pinned 43), the E-FAIL-052 must-fail proven load-bearing. GPU0 requirements measured by pipeline/measure_gpu0.py (600 s of speech; peak MiB above an 18 MiB idle): ollama:gemma3:27b 19241 (20559 seen resident), whisper:large-v3 5657, large-v3 batched 9145, distil-large-v3 batched 5401, medium 2649, embedder 1379, resemblyzer 775, nvenc 536. Next: the full CPU suite, the GPU live tests, the GPU0 path list (file:line, wired), two audit cycles, regression, commit.
- 01:58 LAWS L-n, L-o, L-p, L-q, L-r WRITTEN (orders 01:50, 01:55, 01:55 B, 01:58; PBX 01:43 'pls lock these changes into law'): PIPELINE_LAWS.md (LAW 26 family), the gospel (docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md), this DoD's law table and the bible. Letters: L-l / L-m are hardening-redteam's (batches B / C, arriving with its merge); its drafted E law becomes L-s; its uncommitted GPU0 draft (batch 20) is superseded by L-r. The evidence the 01:50 order asked for is in the law text: L-o (the windows are measured on sentence-locked Whisper word timing, never caption timing; approved passages span 9.02-18.70 s; the approved preview's finals run 71.08 s; proposal: no fixed per-passage bound, the line-up total checked against the 60-70 s format before render) and L-p (editorial 70.2 min = ~50 min gemma3:27b calls + ~19 min in three Whisper swaps; render path 51.3 min = render 17.9 + gates 15.6 + verify 13.4; a cycle is about 2 h). pp-backtest asked through its REQUESTS file for the distinct developments per day with a line-up that passes our rules (L-p (2)).
- 01:58 ORDER (PBX: 'pls drop the old video and start this new process'): part A cancelled. The rerun launched at 01:55:14 from 456a440f (wrapper log logs/pulse_check/run_20261112_065514.log) was stopped in its preflight at 01:55:58 by SIGTERM to its own process group: run_fresh never started, no run dir exists, nothing was sent; the GPU0 lease lock is free and its holder record cleared; the preflight's Ollama check had loaded gemma3:27b on GPU0 (20559 MiB) and it was unloaded (keep_alive 0): GPU0 at 18 MiB again. That is the L-r (2) defect seen live: the preflight does not leave GPU0 as it found it. The story-first product is retired: no more runs of the old selector. Priorities: (1) laws committed (this entry); (2) L-r plumbing through audit, in place before the first moments-first render; (3) moments-first wiring as pp-selectid lands (select_by_id / eligibility now, then moments.py, package.py, trend_brief.py and the VO-fidelity checker; run_fresh ready to render its top package through the existing word pass / sentence lock / render / gates and deliver it as REVIEW ONLY 'first moments-first package; selection + VO by the new path, not yet merged/audited' with the L-o deviations; the same-event / topic line-up gates are replaced by the VO-fidelity gate only for moments-first runs and only once that gate exists with its must-fail corpus passing); (4) merge the parallel branches on DONE; hardening 18 / 19 continue behind.
- 01:55 B ORDER (PBX on the out-of-memory: 'let's make sure that never happens again. what can we do rn to fix this??'): law L-r GPU0 NEVER SURPRISES A RUN (one owner, swap_to, bounded self-heal, foreign processes HOLD, tests + per-stage peak GPU0 table in every REPORT.md). Implementation is priority 2.
- 01:55 ORDER (PBX 01:48 strategy change): law L-q MOMENTS FIRST, THEN PACKAGE, and L-o amended: 'same development from >= 2 channels' leaves the integrity class; VO fidelity joins it. Build assigned: pp-selectid (miner + packager), pp-backtest (supply under L-q); the integrator wires and audits on DONE.
- 01:50 ORDER (PBX 01:43): laws L-n DELIVERY IS THE MEASURE, L-o INTEGRITY IS HARD / TASTE BENDS, L-p CADENCE (one new video every 3-5 h once operational; no schedule without PBX).
- 01:55 PINNED RERUN of line-up 1 (order 01:55 A: 'GPU0 is empty (18 MiB). Re-run ... immediately with your stage_pinned release fix'): launched from the commit that carries this line (stage_pinned releases GPU0 before Whisper, E-FAIL-052; must-fail test proven: without the line the order is ['prepare']; test_pinned 16 passed; regression_test.sh 26 PASS / 0 FAIL / 4 WARN; pipeline/regression.sh exit 0). Audit legs still running at launch (claude-fable-5-2, heimdall deepseek + qwen27b); gpt-6.1-sol UNAVAILABLE (OpenAI HTTP 429 credit_balance_exhausted); Grok refused by the xAI daily cap until 19:00 ET. Their findings are applied after the run. Same PIN (sha256 unchanged), every gate as is. Outcome to follow at the top. Laws L-n..L-r (orders 01:50 / 01:55) are being written; committed after the run (a commit during the run moves HEAD and HOLDs it).
- 01:44 PINNED REVIEW RUN RESULT runs/pinned_20261112_064032 (order 01:45, line-up 1): HOLD at stage `pinned` after 110.5 s, ended 01:42:29 ET, run_fresh exit 3: 'pinned decision rejected: R-iKNbc7-zk: transcription failed'. The cause is NOT a law: Whisper raised 'CUDA failed with error out of memory' on GPU0 while transcribing the hook's source (R-iKNbc7-zk) because the editorial model gemma3:27b was still resident on GPU0 (ollama pid 2066372, 20548 MiB of 24564 MiB, loaded by preflight's ollama check). Pin validation never reached the sentence lock, so no line-up was judged; nothing rendered; NOTHING SENT (release_auth has no review-only path for an unrendered run). Next: root cause (does the pinned stage release the editorial model before Whisper the way the auto path does?) then line-up 1 again on the same pin, no gate touched.
- 01:40 EVIDENCE (order 01:45 item 5; evidence, not action: no window was changed). (a) Tonight's coverage-qualified candidates, the rule that stopped each at clip quality and its closest margin: BlackRock ETF outflows: every hook scoring >= 4.0 failed the stand-alone/topic rule (closest window miss: What Bitcoin Did hook 12.12 s > 12.0 s, by 0.12 s); falling oil / borrowing costs: no hook scored >= 4.0 (Altcoin Daily hook 12.74 s > 12.0, by 0.74 s); public enthusiasm: no hook >= 4.0 (Natalie Brunell clip 11.9 s < 12.0, by 0.1 s; her hook starts 'And'); BTC at $73-75k: no hook >= 4.0 (Stephan Livera 6.14 s < 8.0, by 1.86 s; Coin Bureau hook starts 'And'); Fed holding / raising: no hook >= 4.0 (Coin Bureau hook 7.88 s < 8.0, by 0.12 s); mining tax benefit: 0 usable clips across 1 channel (passages scored 5.0 but one channel; BTC Sessions clip 8.74 s < 12.0, by 3.26 s); BitGo custody: 0 usable clips across 1 channel (Saifedean Ammous clip 11.02 s < 12.0, by 0.98 s; his hook starts 'And'); sell-off after the elections: no quote-anchored window (Natalie Brunell 7.0 s < 8.0, by 1.0 s; Coin Bureau starts 'So,'); BTC near $73,500 after hot CPI (merge of 3, 4 layout-eligible): no hook >= 4.0 (Altcoin Daily clip 11.14 s < 12.0, by 0.86 s; its hook starts 'And'; Yahoo Finance's quote did not align). (b) The 8-12 s hook / 12-20 s clip windows (editorial_select.py:49-50, applied in expanded_window via :1180) are measured on SENTENCE-LOCKED WHISPER WORD timing: the clip-quality words come from transcript_store.acquire(prefer_words=True) (editorial_select.py:880) and only a sentence_ready record counts, i.e. transcript_method 'whisper_words' / 'whisper_words_punct' (transcript_store.py:404-410); caption timing is never used for them. The oracle's durations are caption-line timing (YouTube auto captions): a different clock. (c) Durations in the protected references (locked word span; the final's segment in brackets): approved Nov 11 preview hook 9.08 s (9.58), clips 12.34 (12.50), 18.70 (19.21), 16.66 (16.88); v2f hook 9.02 (9.54), clips 10.70 (11.09), 11.54 (12.12), 14.44 (13.83): v2f's first two clips are below today's 12.0 s clip minimum (v2f predates the 12-20 s rule of 2026-11-11 '1d').
- 01:39 PINNED REVIEW RUN STARTED (orchestrator order 01:45 ET): PIN built from the blind oracle's line-up 1 (ORACLE.json sha256 e923e91fa3d05621844449244100ded681c916bf8d06d0aa4a7ec3f9e64bc77a, JUDGE_L1.json sha256 4b636d47accc6ba0cca038b8f0477ab8da747c719f18bb03c26d11758913ca76, /home/ultron/heimdall_probe/pp_redteam/oracle/20261112_050611/): hook R-iKNbc7-zk:5 Altcoin Daily, clips UJFQBaMh3yg:74-76 and :81-83 Coin Bureau, f22H17BKYRw:85 The Bitcoin Layer; sentences verbatim, caption timing as locator only, machine_cuts (Whisper words + sentence lock); provenance in the PIN's approved_by / approval_ref / decision_provenance (copied to PROVENANCE). Wrapper --pinned --no-telegram --foreground, log logs/pulse_check/run_20261112_063858.log, HEAD f9176b91 (= f2840fac pipeline code; f9176b91 adds DoD text only), GPU0 lease held for the whole run; every gate live and unchanged. Delivery, if every REQUIRED gate passes on the final bytes: REVIEW ONLY through the release authorisation.
- 01:17 LIVE RUN RESULT runs/fresh_20261112_050611: HOLD at editorial ('no candidate is producible'), run_fresh exit 3, wrapper exit 3 at 01:16; GPU0 lease released; nothing rendered, so nothing could be sent, not even as REVIEW ONLY (order 00:05 item 3 presumes a render). Item 2 (next candidate in the SAME run) is what the selector already does: it evaluated every candidate of all three pools (48 h clusters: 22 candidates, 3 at coverage 2; 72 h: 7, 1 at coverage 2; wire headlines: 14, 4 at coverage 2 incl. a same-event merge of 3 wire stories, 'Bitcoin Price Trades Down Near $73,500 After Hot CPI Print Lifts Fed Hike Bets', coverage 5 channels / 4 layout-eligible). Every coverage-qualified candidate stopped at clip quality, on the LAWS, never on a defect: the 8-12 s hook / 12-20 s clip windows missed by fractions of a second (11.78 s, 12.12 s, 12.74 s, 7.88 s, 7.58 s, 11.9 s, 11.14 s, 11.02 s, 6.92 s), sentence starts on 'And' / 'So,', the 4.0 hook-score floor and the stand-alone rule; two stories with 5.0-scored passages (mining-equipment tax benefit; BitGo custody) had ONE usable channel (R5 needs >= 2); for the CPI merge, Yahoo Finance's verified quote did not align to its word timestamps ('no window'). Nothing was changed to make a candidate pass (forbidden). DECISIONS FOR THE ORCHESTRATOR / PBX (work continues meanwhile): (a) a re-run when new videos land (the 72 h universe barely moves overnight: a re-run now would see the same candidates); (b) the windows / continuation rule / one-channel rule are PBX's laws, with the near-miss numbers above as evidence. Order 00:40 item 4 (merge hardening into main, re-render both references) is conditioned on a delivered run: held until the orchestrator says otherwise; hardening continues in ~/worktrees/hardening, its GPU regressions now that the lease is free.
- 00:37 SPLIT (orchestrator note 00:40 ET, recorded so it survives compaction). PBX relaxed one-session-per-repo. Three more sessions, each in its own worktree branched from hardening c1451047, CPU/API only, never GPU0, the main tree or an existing pipeline file: pipeline_pp_backtest (branch pp-backtest, ~/worktrees/pp-backtest: universe export + blind frontier oracle + availability / recall / precision; owns pipeline/oracle/, tools/backtest_oracle.py, tests/oracle/), pipeline_pp_tests (branch pp-tests: adversarial test wall under tests/adversarial/; defects arrive as strict xfails + docs/audits/parallel/pp-tests_REQUESTS.md), pipeline_pp_selectid (branch pp-selectid: ID-constrained selection + one eligibility predicate as NEW modules pipeline/select_by_id.py, pipeline/eligibility.py, wiring patch in docs/audits/parallel/pp-selectid_REQUESTS.md). DROPPED from this session's list: the backtest oracle / supply export (pipeline/backtest.py keeps only the GPU0 lease wiring), fuzz tests and the five test families, batch D. THIS session is the integrator: the only one that edits existing pipeline files, the laws, the bible and the DoD, and the only one that merges. Priority: (1) tonight's live run to Telegram exactly as /tmp/go_live.txt orders (outranks everything); (2) finish batch 18 (C, vacuity), batch 19 (E, cache metadata) and the GPU0 lease wiring in ~/worktrees/hardening; (3) when a parallel branch's docs/audits/parallel/<branch>_STATE.md says DONE: audit its diff myself (two cycles), apply its REQUESTS, fold its BIBLE_ADDITIONS into the QWEN bible, merge into hardening-redteam, regression 0 FAIL, push; (4) after the live run has delivered: merge hardening-redteam into the main branch and re-render both protected references identically before any further live run. Live run state at 00:36: the 48 h pool's three coverage-2 candidates (public enthusiasm; Bitcoin at $73,000-75,000; the Fed holding / raising rates) were rejected at clip quality ('no hook passage scored >= 4.0'); selection continues on the 72 h tier (the code's own next-candidate path, same run).
- LIVE RUN STARTED 00:06 ET 2026-11-12 runs/fresh_20261112_050611 (orchestrator order 00:05 ET: PBX wants a video tonight). HEAD f2840fac (batch 16 committed and pushed: the fail-closed release authorisation, law L-j, IS in this code), main tree cleaned to HEAD (the uncommitted hardening work moved byte-identical to worktree ~/worktrees/hardening, branch hardening-redteam; batch 17 committed there as c1451047, pushed; merges after this run). Wrapper scripts/pulse_check_run.sh --foreground --no-telegram in tmux pipeline_pulse_check_live_20261112_050532, log logs/pulse_check/run_20261112_050532.log; GPU0 lease /tmp/pulse_gpu0.lease held for the whole run (flock; nothing else on GPU0). Preflight 9/9 PASS. The orchestrator's 'fresh_20261112_014204' does not exist; the run it describes is runs/fresh_20261112_013452 (20:34 ET; its four coverage-2 candidates: advisers' allocation, tax treatment, volatility, public enthusiasm). This run ingests the current 72 h universe ('today's universe') and reuses that run's transcripts, embeddings and validated-reply cache through the shared store data/editorial (HEAD has no option to pin another run's universe; no code was changed for tonight). Delivery after the by-hand pre-send checks, through pipeline/telegram.py.
- 23:16 PLAN (recorded for continuity; order of work unchanged): batch 16 commits when its final CPU suite, its GPU-gated
  suite and the live vision fixtures are green (running). Then, each audited + committed separately: B (strict model
  schemas: patch staged), C (gates reject vacuous input before any model: patch staged incl. G1 against a FIXED
  enrolled sample of the approved voice = v2f's three cbQ4bUP6OYwI7yEUTYaM stems; pass fixture the preview's sign-off,
  fail fixture the legacy 'Connery' bridge), E (cache section metadata: done, tests staged), D (anchors never change a
  negation / number / sign / unit / name; SELECT = hook + >= 2 clips + the required channels; one eligibility
  predicate incl. the hook's 80 ms lead; merged candidates re-adjudicated), the GPU0 lease wired into run_fresh / the
  backtest / GPU test sessions / preflight, the backtest's supply export (item 1: runs_backtest/<day>/
  BITCOIN_STATEMENTS.jsonl before selection decides) and its availability / recall / precision columns. Item 3
  (constrained selection) design: label_cluster and adjudicate see their excerpts as NUMBERED sentences and return
  sentence IDs (the cluster's claim = the chosen sentence verbatim; the evidence = the chosen sentences verbatim, their
  chunk bound by construction); a wire item's event text = its headline verbatim (the model's derivation kept as
  labels); free model text only as labels. Prompt changes invalidate the cached replies: the backtest re-runs cold on
  the final code.

- 23:12 COLD BACKTEST STOPPED by me (exit 143) after Nov 10 (0 producible: the 22:20 entry below) and part of
  fresh_20261112_013452: it ran the OLD selection code (394ffe5a) and held GPU0, which the GPU-gated checks of batch 16's
  changed REQUIRED gates (G18 / G3b on the real Nov 10 fixtures) need (they ran out of memory beside it: 'one owner
  for GPU0'); hardening B / D change validators and prompts, so the backtest is re-run on the final code. GPU0's model
  unloaded (18 MiB used). Batch 16's GPU-gated suites and its final CPU suite are running before the commit.

- 22:51 ADDENDUM '22:15' ITEM 2 (ONE OWNER FOR GPU0), first parts: pipeline/gpu0.py (new; test_gpu0.py 3 pass): the
  GPU0 lease = an exclusive flock on /tmp/pulse_gpu0.lease, re-entrant in a process, the holder written into it so a
  refusal names it, released when the holder dies; wiring into run_fresh (the whole run), the backtest, GPU test
  sessions and preflight (refuse while another process holds it) lands after batch 16 is committed. CONFIRMED (code):
  editorial model calls cannot land on the GPU1 Ollama: story_semantics.LocalLLM checks its runner's GPU placement on
  the first call and raises 'LLM runner not on GPU0 only' (gpu_placement via the GPU0 instance's listener pid).
  Wall time per stage, all saved runs (status.json, passed stages; editorial from the auto runs, all HOLD):
  | stage | n | P50 s | P95 s |
  |---|---|---|---|
  | editorial (auto) | 8 | ~2,900 | ~3,450 |
  | pinned | 29 | 148 | 159 |
  | review | 23 | 33 | 45 |
  | cut | 17 | 12 | 322 |
  | sentence_law | 6 | 8 | 12 |
  | voice | 17 | 22 | 29 |
  | prepare | 10 | 47 | 81 |
  | layout | 4 | 58 | 70 |
  | render | 5 | 1,071 | 1,208 |
  | gates | 4 | 618 | 910 |
  | verify | 2 | 661 | 791 |
  A full successful auto run therefore needs ~50-58 min of selection (cold) + ~45-50 min of render / gates / verify.

- 22:40 BATCH 16 (red-team A + the 21:10 canonical form / backtest / preflight) AUDITED on its actual diff:
  gpt-6.1-sol 8 HIGH and claude-fable-5-2 8 findings (docs/audits/pulse-sentence-law/batch16_redteam_A/
  AUDIT_RESPONSE.md), every one confirmed and fixed except fable #3's 'anchor lost its edge-word equality' (the window
  search enforces it); Grok + Heimdall per chunk (the whole-diff Grok run saw NO code: cross_llm_audit.py drops a
  diff >= 220,000 bytes; recorded, re-run per chunk). Fixes include: evidence required (absent = blocker), the
  exact hashed bytes uploaded, a durable in-flight checkpoint before every send, canonical tokens spanning their
  words (a lock on 'seventy four thousand' ends on 'thousand'), 'one and two' != 'one two', every sign layout kept,
  ordinals their own token, the headline's numbers checked with sign + unit against G18's readings of the FINAL,
  pipeline modules identified by name. REQUIRED / MONITORING after the fixtures landed: V1_visual_checklist
  REQUIRED (TestVisionMustPass GREEN: the PBX-approved preview passes V1 in both formats with the current code,
  22:34), vertical_silent_fallback REQUIRED, G14_audio_offset (9:16) REQUIRED with its new fixtures
  (TestG14AudioOffsetVertical GREEN 22:43: the corrected cut's vertical passes, a real 2-frame slip fails, < 3 conclusive samples HOLD). Still MONITORING: G1, G2, G3, G4, G4 per shot, G6, G10, G13, G11, G14c
  (the table below is updated). The drop's first caption line names any MONITORING row that did not pass.
  regression_test.sh 26 PASS / 0 FAIL, pipeline/regression.sh PASS incl. the protected preview REPRODUCED (before
  the span fix; re-checking after it).

- 22:20 BACKTEST (cold, worktree backtest-run = 394ffe5a + harness) Nov 10 DONE: 3,224 s (54 min cold), 427 LLM
  calls (now cached). Universe 95 videos / 87 transcripts, 214 clusters, Bitcoin screen 24 (48 h) / 13 (72 h),
  4 coverage-qualified, 0 PRODUCIBLE. The protected preview's story (Bitcoin below $74,000: DataDash / Natalie
  Brunell / Yahoo Finance) came only as the wire headline 'Bitcoin Price Drops Below $74,000 as Nvidia Probe ...'
  and stopped at 'inconclusive: currentness missing: no verified transcript evidence of a current development';
  the best channel cluster (institutional allocation, 3 channels) stopped at 'only 1 layout-eligible channel'.
  => the go-live bar's Nov 10 condition is NOT met at 394ffe5a: a selector-recall miss on a day with a known legal
  lineup (the PBX-approved preview). D work. The pass continues on fresh_20261112_013452.
  Claude-gates #5 ANSWERED (measured, docs/audits/pulse-sentence-law/batch16_redteam_A/g8_v2f_production_wiring.json):
  through the production wiring (run_fresh.stage_gates: 16:9 sources = prepared clips, 9:16 = reframed vertical
  clips) the approved v2f PASSES G8 in both formats: 16:9 ratios hook 1.012 / clip_01 0.963 / clip_02 0.990 /
  clip_03 0.980; 9:16 1.057 / 1.016 / 1.038 / 1.080, and 9:16 clip_03's median is 10.84 = the calibrated floor
  (zero margin: Claude-gates A5). The 'long-recorded 9:16 G8 fail' is the Law 22 re-render harness's own QA
  (runs/v2f_20261111_232758 qa/gate_results_*.json): it calls the gates WITHOUT G8 source clips (src_median 0.0,
  ratio 0.0), so G8 reads FAIL in BOTH formats there; Law 22 asserts byte identity, not that QA. Not a release
  blocker; the harness wiring is recorded (run_isolated is pinned, untouched).

- 22:01 ORCHESTRATOR ADDENDUM '22:15' RECEIVED (forecast review by gpt-6.1-sol, grok-4.7, grok-4.20 in
  /home/ultron/heimdall_probe/pp_redteam/assess/). Order of work unchanged; four additions to the hardening phase:
  1 SUPPLY VS SELECTOR: for every saved day the backtest exports, BEFORE selection decides anything,
    runs_backtest/<day>/BITCOIN_STATEMENTS.jsonl: every Bitcoin-screened, sentence-complete statement in the 72 h
    window (channel, video id, start/end, text, layout eligibility). An independent frontier model builds a lineup
    (or declares none) from that file alone, blind to the selector. The table reports per day: availability (an
    independent lineup exists), selector recall (selector found one when one exists), precision (the selector's
    lineup is legal). Go-live bar = recall and precision; availability is reported to PBX as a fact of the format.
  2 ONE OWNER FOR GPU0: one queue / lock every pipeline GPU job goes through (editorial model, Whisper, face
    detection, NVENC render, test suites), explicit load / unload between stages; preflight refuses to start if
    anything else holds GPU0 memory; confirm editorial calls never land on the GPU1 Ollama; record P50 / P95 wall
    time per stage of a full run.
  3 CONSTRAINED SELECTION: where a model picks a story claim, a hook or a clip it chooses among numbered,
    source-backed statements and returns IDs; it never writes claim text that is later matched back to
    transcripts. Model free text is for labels only (removes the class behind E-FAIL-038 and the fuzzy-alignment
    findings).
  4 A gate stays in the REQUIRED (release-deciding) inventory only with (a) a real passing fixture, (b) a realistic
    failing fixture, (c) a defined answer to missing evidence. Gates without all three are listed here as
    MONITORING (reported, not release-deciding) until they have them. No gate is deleted.
  Effect on A: release_auth's inventory becomes REQUIRED + MONITORING per this rule; the per-gate table (fixture
  pass / fixture fail / missing-evidence answer) is written into this doc when A lands.

- 21:53 ORCHESTRATOR ADDENDUM '22:00' RECEIVED (same hardening batch): openai_r2_cut.md (gpt-6.1-sol, F01-F31) and
  anthropic_r2_gates.md (claude-fable-5-2, T/D/M/C/X/A/V/P/S) read in full and added to REDTEAM_2026-11-11.md
  (anthropic_r2_select.md stopped after one finding, anthropic_r2_cut.md empty: thinking took the budget). Three models
  put first: "all gates passed" does not require that the gates ran, ran unwaived, or ran on these bytes = item A.
  Named answers owed in the ledger: GPT-cut F03 (L-c / DEC-12f: the override proof must be measured on the FINAL
  rendered audio of the exact approved file, never the prepared clip; else the dissent stands and the run HOLDS),
  F07 (G17c zero compared samples = perfect), F04 (G18 canonicaliser erases units / signs: 5% vs $5 vs +5%), F05
  (repetition removal hides concat repeats), F06 (approximate anchor loses a negation), F08 (critical lock mismatch
  report-only), F12 (hook eligibility vs the later 80 ms G17a lead); Claude-gates #2 (voice / VO gates tautological
  or empty: the voice reference must be a FIXED enrolled sample of the PBX voice), #3 (substring + one-word
  tolerance in cut checks), #4 (a fade satisfies G3c; G14 forgives 0.5 s), #5 (does the approved reference still
  fail 9:16 G8 through the public entry point? measured numbers, before the next run), #8 (stale / teaser /
  third-party content, unvalidated headline), #9 (wrong checkout's code, stale artefacts). Both 'five cheapest
  tests' lists adopted into F.
  EVIDENCE ALREADY IN HAND (Claude-gates V1-V3 / GPT-gates F05, F06, F19 CONFIRMED on a real run): in
  runs/pinned_20261111_172202_replay_cut1329 qa/gate_results_16x9.json, G1_voice PASS with 0 table rows, G6_preroll
  PASS with 0 rows, G13_vo_audible PASS with 0 rows: this format's only VO is the sign-off inside the 'shoutout'
  segment, so vo_regions is empty, and G13's sign-off block needs edl['vo']['signoff'], which the EDL does not carry
  (the text is in vo_audio/VO_MANIFEST.json). Under A every required row needs samples >= 1, so these three rows
  block release until C makes them measure the sign-off (G1 against a fixed enrolled PBX-voice sample).
  WORK ORDER NOW: A (pipeline/release_auth.py written: exact inventory v1, verdicts PASS/FAIL/HOLD/SKIPPED/LIMITED,
  evidence per row, ATTESTATION.json binding the sha256 of both finals, EDL, both manifests, GATE_REPORT,
  VERIFICATION, both contact sheets; authorise() re-derives and re-hashes before the first send) -> wire run_fresh
  (exact verdicts + notes + evidence, measured digests at gate start, attestation after provenance so holds =>
  HOLD), verify_pack (strict panel inventory, vision required, every frame present), telegram (authorise or nothing
  is sent; no REVIEW ONLY sends; checkpointed, resumable, no duplicates; payload limits checked before the first
  send; legacy send_telegram_preview removed), the L-c final-audio rule, the wrapper exit codes -> B -> C.

- 21:41 ORCHESTRATOR ORDER '21:55' (RED-TEAM FINDINGS) RECEIVED: joins the 21:10 order as ONE HARDENING PHASE that
  finishes before the next unattended run. Read in full: /home/ultron/heimdall_probe/pp_redteam/frontier/
  openai_select.md (F01-F36), openai_gates.md (F01-F38), xai_select.md, xai_cut.md, xai_gates.md, and as they appear
  anthropic_r2_*.md, openai_r2_cut.md, panel_*/audit.md, pi_*.md (audit read 394ffe5a; mark FIXED with commit).
  Orchestrator verified five as real: (1) story_semantics ~649-654 support verifier fails open (only False / 'past'
  downgrade); (2) telegram.gate_status: 'PASS...' prefix passes, '(run_gates)' rows exempt, no gate inventory,
  legacy truthy all_pass; (3) verify_pack ~124-128 recomputes ok over rows, zero rows = True, {"ok": "false"}
  truthy; (4) select_passages cached sources/<id>.mp4 returned with a NEW dl_start; (5) qa_gates ~1705 empty /
  unknown-type manifest makes gates no-ops. PRINCIPLE: FAIL CLOSED; one authorisation function for "may this exact
  file be sent as passing", used by every send path. A: versioned exact gate inventory per format, enumerated
  verdicts, rows record execution + sample counts, sha256 of both finals / EDL / manifests bound into the
  attestation, delivery verifies digests before the first send, legacy paths removed or routed, no waiver strings.
  B: strict schemas for every model call feeding a decision (missing / mistyped field = failed call -> retry ->
  HOLD). C: gates reject empty manifests, unknown segment types, zero-sample checks, empty expected values before
  any model loads. D: ONE eligibility predicate for primary pick and every fallback; SELECT success = hook + >= 2
  clips + required channels after replacements; merged candidates re-adjudicate inherited verdicts; alignment
  preserves negation / numbers / names / dates exactly. E: cached media carries + checks its section metadata;
  reply caches keyed by everything that affects the answer. F: the 'five cheapest test families' of both GPT
  reports + the backtest = the regression suite. One line per finding in docs/audits/REDTEAM_2026-11-11.md
  (CONFIRMED-FIXED / CONFIRMED-DEFERRED / NOT REPRODUCED). Audit panel may add gpt-6.1-sol and claude-fable-5-2.
  ORDER: A, B, C first; then canonicaliser + fuzz, D, E, backtest, preflight; then the backtest bar; then live.
  STATE OF THE 21:10 WORK AT THIS POINT (uncommitted in the main tree): pipeline/backtest.py + select_story hooks
  (transcript_fn, words_fn) + test_backtest.py (4 pass); the cold backtest pass runs from worktree backtest-run
  (394ffe5a + harness) since 21:07, still on fresh_20261110_093150 (cold LLM); pipeline/preflight.py + wrapper call
  + test_preflight.py (6 pass; found nothing broken; Michael Saylor avatar missing but the channel is disabled);
  pipeline/canon.py + test_canon.py (16 pass incl. 200-sentence fuzz; apostrophes kept: "it's" != "its", cross-LLM
  M1) routed into story_semantics._norm, gates._g20_norm, editorial_gate._norm, qa_gates G3 / G3b (expected word
  read in its lock context), word_diff.norm (G18 keeps its two tolerances), cut_accept, stand_alone (contraction
  heads), editorial_select (_tok, align_quote via canon_aligned, _lc_words heads, _numbers), punctuation._key
  (+ the '$74,000' = '74,000' alignment tolerance), sentence_law.tokens / anchor (canon_aligned; lock boundaries by
  token ownership). Protected preview REPRODUCED after the anchor change. GPU-gated G18 tests pending a free GPU0.

- 21:04 ORCHESTRATOR ORDER '21:10' (PBX, direct: "stop finding problems the hard way") RECEIVED. Batch 15 is landed
  (394ffe5a, pushed 20:34). The rerun at 394ffe5a (runs/fresh_20261112_013452) was STOPPED by me at 21:03 in its
  48 h pool coverage (4 coverage-qualified so far: financial advisers' Bitcoin allocation, tax treatment, price
  volatility, public enthusiasm); its validated replies are cached, so the backtest of its universe recovers it.
  Order, in this sequence: (1) BACKTEST HARNESS pipeline/backtest.py + test: every saved universe (runs/fresh_*
  with a universe / transcripts) through editorial selection only (clusters -> coverage -> clip quality ->
  stand-alone -> sentence law on the chosen windows; no download, no render), cached transcripts / embeddings /
  validated replies, 'today' pinned to that run's date; one table (day, universe, clusters, Bitcoin-screened,
  coverage-qualified, producible lineups or the gate that stopped each of the top 5); < 20 min warm; from now on
  the selection regression suite (fewer producible days = HOLD on the change). Bar for live again: >= 4 saved days
  produce a legal lineup AND Nov 10 produces the DataDash / Natalie Brunell / Yahoo Finance style lineup of the
  protected preview. (2) TEXT-EQUIVALENCE: one canonicaliser for EVERY comparison (quote verification, edge words,
  G3b, G18, sign-off names, text cache keys), property tests on 200 real sentences x mutations (entities, unicode
  quotes / dashes / ellipsis / nbsp, split tokens, currency / percent, digits vs number words to trillions,
  decimals, ordinals, k/M/B, casing, trailing punctuation, hyphenation, apostrophes) = equal; real differences
  (number, dropped word, name) = unequal; a grep test fails any comparison site not using it. (3) PREFLIGHT in the
  wrapper (seconds; a failure is a HOLD with the reason): GPU0 free / no other job, Ollama model loadable, yt-dlp on
  one known video, ElevenLabs reachable with quota, Telegram bot reachable, disk, clean git tree at a pushed commit,
  no other run (flock), brand assets + registry. A hostile read-only audit runs in parallel (orchestrator); do not
  wait. Then a live run only after the backtest bar is met; keep HEAD stable after that for the three-in-a-row.

- 20:34 BATCH 15 IN (394ffe5a, pushed): laws L-h (text read as spoken: caption entities decoded, split Whisper
  tokens joined, for chunks and quote checks; embedding cache t2) and L-i (a cluster's claim is its event: derived
  from the claim alone, underlying_event = the claim); E-FAIL-036 / 037 / 038. Audit: cross-LLM all three models
  READY, zero defects; Heimdall 0 consensus (one qwen27b point taken: _norm joins split tokens too). Suites 106
  passed / 12 GPU-skipped; regression_test.sh 26 / 0; pipeline/regression.sh PASS incl. preview REPRODUCED. Real
  model: TestLayoutGate still fails 'no hook >= 4.0' = the pre-existing failure recorded in batch 8b, reproduced at
  4ca4b426 and with its date pinned (the cluster path ran end to end in it). RERUN STARTED 20:34 at 394ffe5a:
  runs/fresh_20261112_013452 (log logs/pulse_check/run_20261112_013452.log).

- 20:13 FRESH RUN STOPPED BY ME (runs/fresh_20261112_001448, 5dde8179): both cluster pools were evaluated to the
  end and HELD with full ledgers (48 h: 18 candidates, 72 h: 12; one coverage-qualified, BitGo custody, rejected
  in clip quality: Saifedean Ammous's quote sentence 2.32 s with no verified neighbour, so 1 channel with clips);
  the wire pool (15 live headlines) was in coverage when I stopped it, because three PIPELINE DEFECTS found in the
  ledger make every remaining verdict on this code suspect and a fix cannot be applied under a running process:
  E-FAIL-036 caption text keeps HTML entities (391 of 586 caption records; 'S&amp;P' never matches a correct
  'S&P' quote); E-FAIL-037 word-level records join split Whisper tokens with spaces ('$81 ,000', 'U .S.'), so
  Natalie Brunell's verbatim "It went from above $81,000 after the election to below $75,000 by the weekend."
  failed verification; E-FAIL-038 query derivation re-read the channels' claims as other events (the election
  sell-off / ETF-outflow claim became "the US held its elections on November 8th" (an invented date; the Coin
  Bureau quote on November 3rd was then ruled TOPIC_ONLY); the $88K -> $74K claim became a Schwab listing from
  the label summary). Checked on the real model (4 calls): with the claim as the event and the text read as
  words, Natalie Brunell AND Coin Bureau both COUNT for the election sell-off / ETF-outflow cluster (the
  conversation DEC-13 named). Batch 15 (prepared in worktree batch15-entities): read_text (entities decoded,
  split tokens joined) for chunks, _norm decodes entities, embedding cache t2, a cluster's query derived from the
  claim alone and its underlying_event = the claim. Next: laws, audit, regressions, commit, rerun.

- 19:15 FRESH RUN (DEC-13) STARTED at 5dde8179 (batches 13 + 14 committed and pushed: 8df19dc4, 1b345d9d,
  5dde8179; the 3-in-a-row count restarts here): `bash scripts/pulse_check_run.sh` (auto, no PIN) ->
  runs/fresh_20261112_001448 (log logs/pulse_check/run_20261112_001448.log). Universe 117 videos (97 with
  transcripts), 3,717 chunks; 229 clusters with >= 2 channels; Bitcoin screen 38 in the 48 h tier, 19 in the
  72 h tier, 172 stopped with no model call. At 19:22: 28 of 38 labelled, 15 cluster candidates (Bitcoin ->
  AI rotation, Bitcoin near $70.5K, US strategic-reserve talk, mining bonus depreciation, hot inflation data,
  Binance security incident, ...). Batch 14's audit closed (AUDIT_RESPONSE.md: the panel's 7 consensus items =
  the fixes in 5dde8179).

- 19:05 BATCH 14 (law L-g, before the fresh run): the 18:27 Law 22 re-render, byte-identical, ended exit 1
  because its own QA failed G3b on the approved v2f's 9:16 clip_02 (last word 'dollars'; readings 'above $40
  trillion | above $40 trillion | above $40 trillion dollars', 1/3) plus the long-recorded 9:16 G8_sharpness;
  earlier re-proofs today predate DEC-12f's majority vote. The word was heard and written as '$': a written-form
  defect that would falsely HOLD any clip ending on an amount. Fix: qa_gates._g3b_words reads symbols as spoken
  words in spoken order, for readings, the EDL's last word and next word alike; vote rule and thresholds
  unchanged. GPU tests: test_g3b_majority 6 passed (v2f 9:16 clip_02 now passes; Natalie 'week.' run-on and a cut
  250 ms into 'rally' still fail), test_round2_mustfail 15 passed. Law L-g in the four documents (E-FAIL-035).
  Audit running (docs/audits/pulse-sentence-law/batch14_g3b_written_forms); then commit + push, then the wrapper.
  (The mediapipe 'NoneType is not callable' traceback in that log is FaceDetector.__del__ at interpreter exit.)

- 18:57 LAW 22 PROVEN at 8df19dc4's code (the render ran 18:27-18:53 with batch 13 in the tree; the batch does not
  touch the render path): runs/v2f_20261111_232758/out segment.mp4 472938134157b649..., segment_vertical.mp4
  5545a261feedd8c1..., byte-identical to references/v2f_2026-11-06/SHA256SUMS (also owed from 4ca4b426: closed).

- 18:56 BATCH 13 COMMITTED (see git log; pushed): DEC-13 + laws L-e / L-f + the validated-reply cache, audit
  dispositions in docs/audits/pulse-sentence-law/batch13_dec13/AUDIT_RESPONSE.md (implemented: case transfer
  where both decodes end a sentence, plural Bitcoin terms, one Whisper model on GPU0 at a time, the model digest
  in the cache key, per-process cache temp files, ledger channels by id; rejected with evidence: U-2 and the
  rest). Verified at commit: batch suites 102 passed / 12 GPU-skipped; regression_test.sh 26 PASS / 0 FAIL;
  pipeline/regression.sh PASS incl. step 6 PULSE PREVIEW REFERENCE: REPRODUCED. Also fixed two stale tests red
  since 4ca4b426 / ae965c95 (DEC-12a G9 floors; run_isolated.py pinned to the tag or the audited DEC-10
  version): both were among the six 15:55 batch-12 failures I reported as CUDA out-of-memory; that report was
  wrong for these two. STILL RUNNING at commit: Law 22 v2f re-render (GPU0, started 18:27), the full CPU suite,
  three Heimdall cross-examination rounds; then the GPU-gated tests alone on GPU0; then the wrapper.

- 18:30 DEC-13 BATCH BUILT (uncommitted; audits + regressions running): (b) ANSWERED: the same-event merge DID
  run inside the wrapper (editorial step 5b, all 19 evaluated candidates) and made zero groups, because no two
  candidates shared a counted statement (BlackRock outflows rested only on Stephan Livera, the $74K headline
  only on Bloomberg, Tavi Costa only on Altcoin Daily); not a defect. Measured on today's universe (4,284
  chunks): the old cluster rule (>= 3 channels, the 8 widest) kept 8 evergreen / off-brand topic clusters and
  put NONE of the $74K-pullback or ETF-outflow statements in any cluster; with >= 2 channels there are 252
  clusters, 58 pass a free Bitcoin screen (43 inside 48 h); the $74K-pullback statements form one 4-channel
  cluster (Coin Bureau "Bitcoin's recent drop stalled just above the line traders use to separate a pullback
  from a bear market", Altcoin Daily, Bitcoin Magazine, Marty Bent; 48 h tier) and the ETF-outflow statements a
  2-channel cluster (Coin Bureau, Bitcoin Magazine; 72 h tier: Bitcoin Magazine's is 50 h old). They are two
  clusters, not one, at the unchanged clustering threshold (0.22). No LLM verdict cache existed ("as now"):
  added. Built: pools channel_clusters_48h -> channel_clusters_72h -> wire_headlines (lazy, a pool runs only
  if no earlier pool produced); cluster_entry screen before any model call; a cluster's coverage adjudicates
  its own statements; per-cluster ledger (channels, statements, claim, counted quotes, gate); label = one
  sentence from the shared statements; validated-reply cache sha256(model, ctx, max_tokens, prompt). Plus law
  L-e (word pass punctuation: whisper_words_punct from a large-v3 batched prompted reference; Altcoin 373 ->
  112 unpunctuated words, quote sentence 35.28 s -> 8.94 s). Laws L-e, L-f in the gospel, PIPELINE_LAWS LAW
  26, this doc, the bible (E-FAIL-033 / 034). Tests: test_dec13_clusters.py (10, real fixture
  tests/fixtures/dec13_20261111), test_punct_word_pass.py (5, fixture tests/fixtures/punct_20261111);
  editorial suites 87 passed. Audit: docs/audits/pulse-sentence-law/batch13_dec13 (cross-LLM + Heimdall).
  Law 22 (v2f identity) re-render running alone on GPU0 (also owed from 4ca4b426).

- 18:02 DEC-13 RECEIVED (orchestrator 18:00, binding): candidates come from the channels' own conversation
  FIRST. a) primary candidates = emergent clusters over the last 48 h (72 h max) of transcripts, >= 2
  independent approved channels on the same development, the claim written from the shared statements (one
  sentence, the event itself), supporting quotes attached; wire / story-engine headlines only name, date or
  enrich a cluster, or stand alone after every cluster is exhausted. b) the same-event merge runs BEFORE the
  coverage count on every run (auto since 55eb579b): confirm it executed in runs/fresh_20261111_213954 and on
  which candidates; if it did not run inside the wrapper, that is the defect; merge rule, MIN_COVERAGE_CHANNELS
  2, hook >= 4.0, stand-alone, topic and sentence laws unchanged. c) the Bitcoin-only screen (BTC_RELEVANCE_MIN
  as is) applies to clusters before any model call. d) the ledger names, per cluster, the channels, the shared
  claim, the quotes and the exact gate that stopped it. e) reuse this run's universe, transcripts, embeddings
  and verdict cache (keyed by prompt sha): minutes, not an hour. Tests: a fixture from today's saved universe in
  which the BlackRock-outflow / $74K / midterms statements form one cluster with >= 2 channels (must produce a
  candidate); two channels on different events must NOT merge. Audit, regressions, both references, commit +
  push (the 3-in-a-row count restarts there). Then the wrapper on today's universe; first clean pass to
  Telegram as ordered at 15:30; else the three nearest misses and what each lacked. Still owed after the
  fresh video: the B/C verification render (Natalie 'rally' whole) alone on GPU0.
- 17:34 FRESH RUN HELD (ledger-backed): runs/fresh_20261111_213954 at 4ca4b426 (16:39-17:34, selection
  3,282 s): "HOLD: no candidate is producible". 24 candidates: 13 currentness inconclusive (11 missing, 2
  conflict), 3 coverage 1 < 2 (BlackRock ETF outflows, OKX / ICE, Bitcoin near $74K), 5 importance gate
  (bitcoin_relevance < 3), 3 window stage: the Fed (Bloomberg's caption quote is not in the Whisper words;
  Natalie 7.15 s; TheStreet a question / 11.79 s), the AI sell-off (no hook >= 4.0), US midterms (Bloomberg's
  caption quote is not in the Whisper words; Altcoin Daily's quote 'sentence' 35.28 s).
- 17:45 DEFECT FOUND (gospel SENTENCE LAW, "punctuation is added at transcription time"): the editorial word
  pass (transcript_store.acquire prefer_words -> distil-large-v3 batched) never applies pipeline/punctuation.py;
  only select_passages does. 29 of the 44 stored word records have unpunctuated stretches; Altcoin Daily
  Ov5jg52HqIY: 373 words, so its quote sentence read 134.80-170.08 (35.28 s). Not outcome-changing today (US
  midterms' second channel, Bloomberg, cannot anchor at all: its manual captions paraphrase the speech, fail
  closed by design), but a law gap. Fix (uncommitted, joins the DEC-13 batch): a whisper_words_punct record
  (immutable; the verbatim record is kept), punctuation from a prompted reference decode onto aligned words
  only. Measured on Altcoin: distil batched + prompt moved 39 marks but NOT into the quote stretch; large-v3
  sequential + prompt restored it (169 s); large-v3 batched + prompt restored it in 22.8 s (92 marks, 373 ->
  112 unpunctuated words) -> the reference is large-v3 batched. (Then OPEN: transfer copied punctuation only, so
  a sentence start inside a restored stretch stayed lower-case and the editorial start_is_boundary rejected it;
  CLOSED 18:33 by the batch-13 audit's unanimous U-1: the sentence-initial capital is transferred with the
  mark in the editorial word pass only; start_is_boundary itself is unchanged.)

- 16:40 BATCH IN: 4ca4b426 pushed (DEC-12 a/c/d/e/f + B + C + laws L-a..L-d + delivery kit; audits batch12_dec12,
  batch12b_dec12_final, heimdall_telegram; suites green, GPU set re-run alone 26 passed; regression_test.sh 26/0;
  pipeline/regression.sh PASS incl. step 6 REPRODUCED). E STARTED: the wrapper (auto) on a fresh story at
  4ca4b426: runs/fresh_20261111_213954 (log logs/pulse_check/run_20261111_213954.log). 4b count: 1 of 3 if
  HEAD stays 4ca4b426 (no commits until the third run; this doc stays uncommitted meanwhile).
  B/C verification replay of the Nov 10 cut (runs/pinned_20261111_172202_replay_verifybc): the voice stage
  generated "Big thanks to DataDash, Natalie Brunell, Yahoo Finance, and Bitcoin Magazine for the clips
  today. Follow them all, links below." (all four, passed the L-a pre-render check); its render then HELD on
  NVENC CUDA_ERROR_OUT_OF_MEMORY (GPU0 shared with the test suite at the time): to be re-run alone after the
  fresh run. Law 22 re-proof at 4ca4b426: after the fresh run (GPU0 one job at a time).

- 15:38 FULL STATE (handoff-grade; CURRENT_STATE.md top mirrors it).
  LOCK (A) DONE: annotated tag ref-pulse-preview-2026-11-11 on 5c17e9b3 (pushed); side branch
  ref-pulse-preview-2026-11-11-replay-state = 33fb77e1 (the replay's exact dirty start tree: 9b459ec6 + DEC-11
  v1 gate edits); references/pulse_preview_2026-11-11/ read-only, 62 files + SHA256SUMS (finals without the
  PREVIEW label, decisions, PIN, prepared clips, sign-off VO, frozen sources + transcripts, contact sheets);
  docs/references/REFERENCE_PULSE_PREVIEW_2026-11-11.md; pipeline/check_preview_reference.py + regression.sh
  step 6 (selection locks, cut points +-1 hop, 9:16 layout must reproduce): REPRODUCED on the current tree.
  Defect B cause FOUND: the sign-off text lists the CLIPS' channels only ("Clips today from Natalie Brunell,
  Yahoo Finance, and Bitcoin Magazine...") and leaves out DataDash, whose only segment is the hook; the card
  lists hook + clips. Not a stale cache.
  UNCOMMITTED (the one batch, audit not yet run on its final form): DEC-12 a (segment_v1/qa_gates.py G9 floors
  from docs/audits/pulse-sentence-law/dec12a_g9_spread/spread.json; test_g9_floor.py), b (sentence_law: 83 ms on
  every machine edge, TO BE AMENDED per C / law L-b), d (editorial_select.layout_eligible: has_chyron never
  supplies a clip; test_editorial TestChyronChannels), e (gates.gate_g14 speech sampling, retake, >= 3
  conclusive; run_fresh passes words, 9:16 frames=False; test_g14_sampling.py), f (qa_gates.gate_g3b 3
  readings + 1.5 s context; test_g3b_majority.py), test_g14_g15 G15 channel fix (DEC-11 follow-up), the
  lock's check script + regression step. TODO in this batch: B (sign-off from the FINAL EDL incl. the hook's
  channel; VO cache keyed by text + voice + model; gate G20 SIGNOFF_NAMES_ALL; must-fail: the preview), C
  (fades never overlap edge words, >= 10 ms inside the gap; G17 edge-word comparison with the source within
  1 dB; a dissenting G3b reading triggers it, HOLD unless it passes; must-fail: the preview's 'rally'), laws
  L-a..L-d written into the gospel, PIPELINE_LAWS Pulse Check section, this doc and the bible; then one audit
  (cross-LLM + Heimdall), suites, regression_test.sh, pipeline/regression.sh, Law 22 (v2f identity),
  commit + push; then E: the wrapper (auto) on a fresh story from today's universe; Telegram only on a clean
  pass (+ title, description with every source credited and linked, first-comment credit line: "credits:",
  every creator's @handle, a line break, the orange heart on its own line). Publishing and the schedule wait
  for PBX. Batch-12 audit of the pre-B/C diff ran at 15:22 (docs/audits/pulse-sentence-law/batch12_dec12):
  read it, then audit the final diff.

- 15:32 ORCHESTRATOR ORDER 15:30: PBX watched the preview (67640 / 67641): "genuinely blown away ... amazing
  video ... nearly perfect ... I would publish it right now". Order: A lock the preview's logic (tag
  ref-pulse-preview-2026-11-11, references/pulse_preview_2026-11-11/, reference doc, second protected
  reference in pipeline/regression.sh); F full state to this doc + CURRENT_STATE.md; then ONE audited batch:
  DEC-12 a / c / d / e (kept) + B (sign-off VO named 3 channels, card showed 4: fix generation / caching, new
  gate G20 SIGNOFF_NAMES_ALL) + C (Natalie's last word 'rally' clipped by the edge fade: DEC-12b AMENDED, an
  edge fade never overlaps the edge word, shortens down to 10 ms inside the gap; G17 last / first word 100 %
  at full level within 1 dB of the source; a dissenting G3b decode triggers that comparison, HOLD unless it
  passes; DEC-12f stands); then E: the wrapper (auto, no PIN) on a FRESH Bitcoin story from today's universe,
  Telegram only on a clean pass (+ title, description crediting every source with links, first-comment
  credit line). In progress when the order came (uncommitted, part of the batch): DEC-12 a (G9 floors from
  the measured spread 0.0438 / 0.0335 -> 14.2857 / 14.7315), b (83 ms on every machine edge: to be AMENDED
  per C), d (has_chyron channels never supply a clip), e (G14 speech sampling + retake + >= 3 conclusive),
  f (G3b 3 readings with 1.5 s context); a DataDash replacement for Bitcoin Magazine in the Nov 10 PIN was
  dropped (the Nov 10 story is stale; it is only the verification replay now).

- 14:47 PBX PREVIEW SENT (DEC-12, orchestrator's caption verbatim, approval chat via pipeline/telegram.py's
  sender): Telegram message ids 67640 (16:9 video), 67641 (9:16 video), 67642 (16:9 contact sheet, photo),
  67643 (9:16 contact sheet, photo). Source: runs/pinned_20261111_172202_replay_cut1329 (the corrected Nov 10
  cut, Natalie out at 80.84); its 9:16 predated the colour fix, so only the vertical was re-rendered from the
  prepared clips in runs/pinned_20261111_172202_replay_cut1329_replay_preview (both finals bt709, 71.08 s);
  small top-left "PREVIEW" label burned on copies (PREVIEW/preview_*.mp4); record TELEGRAM_PREVIEW.json.
  Not a release candidate. Next: the DEC-12 batch.

- 14:37 DEC-12 received (stamped 14:45): appended to the decisions above. The restarted 4b run 1 (5c17e9b3,
  runs/fresh_20261111_192645, still in editorial) and the Law 22 run at 5c17e9b3 are stopped: DEC-12 changes
  the HEAD, so neither can count. Order now: PBX preview of the corrected Nov 10 cut -> DEC-12 batch (one
  audit, regressions, v2f identity) -> one replay of the Nov 10 cut -> 4b. OD-8 / OD-9 / OD-10 (written 14:31)
  are decided by DEC-12 b / d / f; OD-4 by 12a; OD-7's addendum by 12e.

- 14:04 4b RUN 1 HELD (pipeline defect, DEC-8: fix, audit, the count restarts): editorial crashed in
  story_semantics.emergent_clusters on sorted({None, ...}): four whisper_words records hand-made 2026-11-10
  ~05:28 ET outside the writer (qo8rDU3bbMo Simply Bitcoin, jbDqdLytkNM Bitcoin Magazine, eEB0nt6jvEw Marty
  Bent, RXTVaDsN11M DataDash) carry channel_id / channel_name None; their meta.json has both. Fix (batch 11,
  audit running): chunks take missing identity from meta.json, none anywhere = no chunks; the writer refuses
  an identity-less meta. The four records now chunk with their channels (22 / 34 / 32 / 69 chunks). Bible
  E-FAIL-030. The Law 22 run at 36e769d0 was stopped (superseded); 4b restarts at the batch-11 HEAD with a
  Law 22 re-proof there.
  Replay of recut #2 finished (runs/pinned_20261111_172202_replay_cut1329): G12 / G15 PASS both formats
  (DEC-11); G3c clip_01 PASS; still not passing: G9 both, G10 16:9, G14 (t=24.083, peak 0.174, same pause),
  G3c hook, and NEW 16:9 G3b clip_01: the final's context-free tail ASR heard 'in the monday route.' for
  '... rally.' (9:16 G3b PASS; prepare's edge check heard 'rally.'; G17b and G18 PASS): the 83 ms DEC-10 fade
  at the true minimum 80.84 ends 35 ms after the word, and one ASR decode under the bed misheard it (OD-6
  class: single-word ASR; nothing changed).

- 14:03 4b STARTED at HEAD 36e769d0 (pushed): run 1 via the wrapper (auto), runs/fresh_20261111_190259;
  Law 22 re-proof at the same HEAD running alongside. Commits since the 13:15 note, each audited: 9b459ec6
  (8d valley search inside the transcript gap), af5447c6 (DEC-11 credit rings + registered-avatar discs;
  G15 fails closed), 36e769d0 (batch 10: the 9:16 safe frame keeps its input's colour matrix).
  Replay of recut #2 from the cut with 8d (runs/pinned_20261111_172202_replay_cut1329; scratch driver: the
  replay harness's copy + production stage_cut / stage_sentence_law, then run_tail; vision off): Natalie cut
  68.38-80.84; G3c clip_01 tail -33.7 vs limit -31.7 PASS (was -22.4: the kept 'Bu'), clip_02 head onset N
  PASS, clip_03 PASS; G3c still FAILS only on the HOOK tail -42.7 vs -43.9 (16:9) / -42.8 vs -44.1 (9:16):
  the 340 ms pause after 'take.' holds no next word; DataDash's room tone sits 10.4 dB under his quiet speech
  (-32.3), G3c asks 11.63: the gate measures the source's ratio, not a cut into a neighbour (OD-5 class; an
  envelope-minimum cut with the 2-frame fade would pass it but is a cutter-wide change: not made during 4b).
  G9 in the replay: 16:9 14.3 / 9:16 14.5 (its vertical render predates batch 10). Nov 10 story: NOT sent;
  blockers G9 (OD-4 residual 0.03 both formats), G10 (16:9 BM lower third: needs a 16:9 framing decision for
  has_chyron channels), G14 (pause under the bed), G3c hook (source ratio).

- 13:32 ORCHESTRATOR NOTE 13:15 (time box 14:30) on recut #2 runs/pinned_20261111_172202 (HEAD 29299ea5,
  71.17 s both formats, not delivered). Gate rows: G16 / G17 / G18 / G19 PASS both formats; NOT PASS: 16:9
  G3c, G9, G10, G14 (inconclusive), G15; 9:16 G3c, G9, G14 (inconclusive), G15. Per item:
  1a G9 (not a rounding / equality failure; the reference passes its own floor): sampled at identical offsets
     from the end, ours 16:9 14.3021 (14.1194 / 14.3162 / 14.4707) vs floor 14.33 (v2f 14.3357); 9:16 14.4652 vs
     14.77 (v2f 14.7715). Two causes: (i) RENDER DEFECT found: our 9:16 final carries color_space=unknown (v2f's
     9:16 and both 16:9 files: bt709), so the decoder converts with BT.601: decoded as bt709 our 9:16 reads
     14.7418, and v2f decoded as BT.601 reads 14.4971; the vertical path loses the tag when the first segment
     is a safe-frame layout (fix pending, Law 22 re-proof needed). (ii) the remaining ~0.03 in BOTH formats
     (14.3021 vs 14.3357; 14.7418 vs 14.7715) is the same locked outro (12.69 decoded directly) lifted
     differently by the final re-encode = OD-4 (floor 0.006 under v2f, encode-to-encode spread 0.03). No
     constant changed: G9 cannot pass on this render until OD-4 is decided.
  1b G3c (limit = segment speech median - 11.63 dB in the last 60 ms; head = no 10 ms jump from < -35 to
     > -30 dBFS): hook tail -42.7 vs -43.9 (DataDash's room tone after 'take.' is only 10.4 dB under his
     quiet speech, -32.3; the tail holds no next word: 340 ms pause before it); clip_01 tail -22.4 vs -31.7 =
     a REAL defect: the cut at 80.93 kept 'Bu' of 'But' (fixed in 9b459ec6, batch 8d: the minimum search left
     the transcript gap by 80 ms; the true minimum is 80.84, -22 dB); clip_02 head onset (the 83 ms DEC-10 fade
     from the shallow minimum between abutting 'days.' | 'Of' at 38.20, -20 dB vs speech -13.2, crosses
     -35 -> -30 dBFS inside 10 ms in the final). Replay from the cut with the 8d fix running for the exact
     clip_01 number. Expected conflict (to confirm): G3c's 11.6 dB-deep 60 ms tail and its head rule cannot be
     met by a 2-frame fade at a minimum only 2-7 dB under speech (abutting words): OD-8 below if confirmed.
  2  G14 inconclusive at t=24.167 (clip_02 +2.0 s = source 40.195-40.695): NOT a transition (the only dissolve
     is after clip_02, ~41.2 s) and NOT a VO freeze (no body VO). The window is a 0.6 s PAUSE inside Yahoo's
     sentence (source -44 .. -84 dB after a syllable ending 40.17; 'massively' starts 40.90; Whisper stretches
     'pretty' over it), so the final holds only the music bed (-38 .. -45 dB) there: xcorr peak 0.154 < 0.3.
     Conclusive needs source speech in the 0.5 s window. The authorised sampling skip (declared transition /
     VO-freeze intervals) does not cover it; nothing changed (same class as OD-7).
  3  DEC-11 implemented (pipeline/credit_rings.py; G12 in segment_v1/qa_gates.py, G15 in pipeline/gates.py;
     run_fresh passes the credited channels): ring = brand-red mask contour of ring size, ellipse fitted to it,
     aspect >= 0.95 unchanged, count == EDL channels at the layout positions. MEASURED: yesterday's card's RINGS
     are round (0.999-1.000, at the layout positions); its D4 defect was the 1280x720 thumbnail squashed into
     each disc. To keep DEC-11's must-fail, G15 also requires each disc to be the credited channel's registered
     avatar (correlation r >= 0.90; measured 0.999-1.000 on every v2f and Nov 11 node, yesterday 0.297 / -0.030
     / -0.142). Tests: yesterday fails G15 (avatars) with round rings; v2f + today's card pass G12 + G15 both
     formats; a card squeezed to 80 % fails on ring aspect; 3 rings for 4 channels fails G12. Audit batch 9
     running.
  4  clip_03 sentence start confirmed: lock first word 'Last' (word 45; previous 'Bitcoin.' 14.18-14.38, heard
     until 14.67); silence 14.68-14.88, breath 14.89-15.13 (-35 .. -46 dB), 'Last' 15.20-15.37, 'night' from
     15.42. The cut 14.94 sits in the breath, 260 ms before 'Last'; G3 heard 'last'; G16 / G18 PASS. No fix.
  NOT in the 13:15 list: G10 16:9 clip_03 FAIL is REAL: the 16:9 frame shows Bitcoin Magazine's burned-in
     lower third (sponsor bar, stock + BTC tickers, 'ORACLE REMINGTON ... | BMTV' name chyron); bottom-12 %
     edge density 0.0846-0.0854 vs 0.08, 0.084 even without the watermark strip. The 16:9 path has no chyron
     crop (has_chyron only routes the channel to G10); the 9:16 safe frame blurs it (PASS). Needs a decision:
     a 16:9 framing for has_chyron channels (crop / safe frame) or a BM window without the lower third.
  Verdict: no clean pass is possible on this story before OD-4 (G9) and the G10 framing are decided; nothing
  sent. After batch 9 + the replay numbers: 4b.

- 12:03 DEC-10 recut #1 (wrapper, HEAD ae965c95; runs/pinned_20261111_170153) HELD at stage cut, before any
  render: run_fresh.stage_cut's M19-era cut acceptance (cut_accept) rejected exactly the two edges the
  sentence-law cutter placed at the envelope minimum: clip_01 Natalie OUT 80.93 "cut_out not inside a
  genuine pause with >= 60 ms ahead" (the old 60 ms guard; DEC-10 b: 0 ms) and clip_02 Yahoo IN 38.20
  "inside continuous speech (no boundary dip in prior 100 ms)", lookback min -18.4 dB vs loud -25.6 (the
  words 'days.' | 'Of' abut; the minimum between them is -19.5 dB). hook and clip_03 ACCEPT. Not delivered.
  Root cause: my DEC-10 implementation changed the cutter but missed this second edge check. DEC-10 d: "a
  clip is rejected for edges only if (i), (ii) or (iii) cannot be met"; the M19 quotas are none of them.
  Change (batch 8c, audit running): for an edge flagged valley_in / valley_out in cuts_final.json (set only
  by sentence_law.accepted_cut; a human PIN's table never carries it), stage_cut keeps the M19 reading in
  CUT_ACCEPTANCE.json (as "m19") and leaves the verdict to the next stage, G16 (legal range +
  neighbour_clear with the cut's own fades, HOLD before any render). Every other edge unchanged. Tests:
  valley edge left to G16 with its M19 reading kept; a normal edge failing M19 still holds; no flag = no
  change. The prepare clip contract (first 5 ms >= 9 dB under 25-45 ms) is expected to pass an 83 ms
  linear fade (~20 dB).

- 11:36 DEC-10 batch 8 answered (docs/audits/pulse-sentence-law/batch8_dec10_edge_timing/AUDIT_RESPONSE.md):
  gospel + docstrings ratify the recalibration; VALLEY_FADE_S = 2 video frames at 24 fps = 83 ms; valley test
  rewritten (was vacuous). Follow-up 8b (audit running on its own diff): (1) the quiet run is searched between
  the two words' midpoints (the rewritten fixture caught a tie with the neighbouring junction); (2) DEC-10 d
  made explicit: an edge whose quiet run is < 80 ms (in) / < 140 ms (out) (the 01:50 legality minimums, now
  choosing only the METHOD) is cut at its envelope minimum with the 83 ms fade; (3) Heimdall F2: an edge NOT
  at a minimum must pass cut_accept's unchanged checks also when the other edge is at one (mocked tests both
  ways). Lineup re-measured with (1)-(3), unchanged: hook 0.03-9.33 (+0.25 s pad, 20/30), Natalie
  68.38-80.93 (in 20 ms; out at the minimum, 83 ms), Yahoo 38.20-57.37 (in at the minimum, 83 ms; out 30),
  Bitcoin Magazine 14.94-31.79 (20/30, quiet run out exactly 140 ms -> standard). 58.1 s of clips; every
  neighbour_clear row below the valley threshold (worst -34.9 dB vs -25.4).
  Law 22 re-proof with batch 8 in the tree: runs/v2f_20261111_160348 byte-identical (472938134157b649 /
  5545a261feedd8c1). Next: suites + regressions, commit + push, then the DEC-10 recut via the wrapper.
- 11:05 DEC-10 implemented (sentence_law: timing minimums 0 = v2f worst; legal cut range = the HEARD gap
  (previous word's offset .. next word's onset at speech - 6 dB); neighbour side ends at the envelope
  minimum; abutting words cut at that minimum with a 2-frame fade; NEW neighbour_clear (c-ii): no frame of
  the neighbour above speech - 12 dB after the fade; D1 file-head / hook rule unchanged at 80 ms; per-cut
  fades through prerender, v2f's 20 / 30 unchanged). Tests: v2f must-pass on 5 of its 8 edges; 3 recorded,
  each by measurement: hook head (D1 head rule: 70 ms, no pad, same side as yesterday's D1), clip_01 OUT
  (PBX's own one-time exception; cut at 249.63 inside the soft "So"), clip_02 IN (cut at 624.63 inside a
  110 ms voiced stretch at speech level, -20..-26 dB): (c-ii) fails them, so (c-ii) is not loosened.
  Yesterday's D1 / D2 / D3a / D3b still FAIL (D2 now "outside the legal range": the 120 ms pause after
  'week.' became legal, yesterday's cut is 2.3 s past it). Audit batch8 + Law 22 re-proof running.
- 11:08 DEC-10e lineup on the PIN's frozen sources, exact measurements:
    hook DataDash 0.00-9.08 "Bitcoin has now seen a 16 % decline ... give or take." LEGAL: cut 0.03-9.33 +
      the 0.25 s D1 pad (60 ms genuine lead at the file head), fades 20/30; scorer 4.0.
    Natalie as written "It went ... how the market shapes up this week." CUTTABLE (68.38-85.41) but 5
      sentences > the 1-3 sentence law -> REJECTED by that measure. Its first 3 sentences "It went ...
      Monday rally." LEGAL: cut 68.38-80.93 (12.55 s; out at the envelope minimum after 'rally.', 83 ms
      fade); scorer 5.0. ("Bitcoin also wasn't spared ... last week." is legal too but 11.78 s < the 12 s
      clip minimum.)
    Yahoo "Of course, Bitcoin dropped ... many times." LEGAL: cut 38.20-57.37 (19.17 s; in at the envelope
      minimum between abutting 'days.' | 'Of', 83 ms fade); scorer 5.0.
    G5: those three = 41.3 s of content + ~9 s credits + 4.46 s outro = ~54.7 s < 60 (G5 FAIL by ~5 s).
    Decision (logged): a 4th segment from a 4th channel, as v2f had: Bitcoin Magazine 14.68-31.34 "Last
      night was Bitcoin's first weekly close below the 50-week moving average since September. The 50-week
      was around $75,500, and Bitcoin closed around $74,700, just 1 % below the line. But one percent is
      still a miss." (legal; scorer 4.0 in one batch, 3.0 in the lineup batch: the scorer moves with its
      batch). PIN: pipeline/PIN_RECUT_NOV10_DEC10_20261111.json (~72 s).
  Still expected to fail by construction: G9 (OD-4), G15 with "Natalie Brunell" on the card (OD-1).

- 10:25 LINEUP SEARCH RESULT for the Nov 10 story (direction 1), every rule unchanged. Sources searched:
  full Bitcoin Magazine "Bitcoin Loses Key Moving Average" (104/130 budget windows legal), full DataDash
  (89/218), full Yahoo (133/158), CoinTelegraph (118/140), Marty Bent 0-7 min (22/30; his 50-week sentence
  is later in a 44-min show, not fetched), Natalie (no legal Bitcoin window). Production scorer on the event
  "Bitcoin fell sharply ... losing its 50-week moving average ... below about $74,000 ... tech selloff":
    hooks >= 4.0 that pass the stand-alone/topic rule: ONE: Bitcoin Magazine 269.45-281.38 "From the COVID
      era, the continued outflows and broad spot sellers pushing our closes down week by week has us
      rhyming with 2012. We want to see Bitcoin reclaim the 50-week urgently." (4.0) - its first sentence is
      a punctuation split (the audio reads "...eventual bailout from the COVID era." as the previous
      sentence's end), so to a listener it starts mid-thought. Every other legal hook scores 1-3 (history,
      Saylor's purchase, Scaramucci's $200K).
    clips >= 3.5: Bitcoin Magazine 14.94-31.95 "Last night was Bitcoin's first weekly close below the
      50-week moving average since September. The 50-week was around $75,500, and Bitcoin closed around
      $74,700, just 1 % below the line. But one percent is still a miss." (4.0; 16.66 s: no legal boundary
      after its first two sentences, so it cannot be the 8-12 s hook) and DataDash 143.62-161.67 "But we've
      seen a really nice decline here on Bitcoin, okay? 16 % so far ..." (5.0). Every other legal clip <= 3.0.
    best legal lineup: 11.20 + 16.66 + 17.64 = 45.5 s of content + ~9 s credits + 4.46 s outro = ~59 s:
      G5 duration (60-120 s) fails by ~1 s; body VO is off by default (Editorial Law 2 / M20); and gates
      in the open decisions would still fail a correct render (OD-4 G9 always; OD-1 G15 with some names;
      OD-5 G17a and OD-6 G3 on DataDash's gated "But").
  => A clean pass of the Nov 10 story is not reachable with the current laws and gates. Decisions that
  would unblock it (orchestrator / PBX): OD-4 (G9 on a locked black-ending outro), OD-1 (G15 on glyphs),
  OD-5/OD-6 (G17a gated silence, G3 single word), and either a VO intro with a declared job or a hook
  budget > 12 s for a story whose event sentence runs 16.7 s. Meanwhile: land batches 6-7, then 4b
  (fresh stories search every channel and story, where the same laws may find cleaner material).
- 10:20 V1 batch (batch 7) audited; consensus implemented (stand-alone empty subject fails closed, vacuous
  panel verdict, test strengthening); G19 rows in both formats.

- 09:45 replay of run 6 from prepare (runs/pinned_20261111_123750_replay_20261111_134458, batch-6 code)
  proved on real data: G18 PASS on every segment, both formats (decimal canonicaliser); prepare's shot snap
  held clip_02's last 3 frames on Natalie's own shot; 9:16 V1 PASS (incl. next shot, credits, per-shot
  letterbox). 16:9 V1 FAIL only because qwen's reply lacked its final '}' (all six answers present: 6 x
  "missing"). Remaining rows are the diagnosed set: G3, G5, G9, G14, G15, G17 (OD-1, OD-4..OD-7 below).
- 09:45 V1 batch (in the working tree, audit next): the credits question gets the EDL's channel list (a
  9:16 crop can hide a show's branding: qwen called Yahoo "absent" on run 6); the next-shot line is answered
  ONE CUT AT A TIME from the cut's -3f/+3f frames side by side (on run 6 the whole-sheet answer misread tile
  labels and neither model saw the real defect), the sheet answer kept as advisory; a reply missing only
  its final braces is closed (max 3, nothing else repaired); NEW deterministic G19 EDGE SHOTS on both finals
  (no hard shot change inside a talking head outside its speech): must-fail on run 6's own final (clip_02
  at 41.1-41.3 s), must-pass on the snapped replay.
- 09:30 wider sources transcribed: Bitcoin Magazine "Bitcoin Loses Key Moving Average" (104 of 130 budget
  windows legal: clean pauses), DataDash full (89), Yahoo full (133), CoinTelegraph; Marty Bent's crashed on
  CUDA OOM (GPU0 shared by three of my jobs: my error, serialised since). Full videos fetched natively;
  the mp4 audio is bit-identical to the transcribed m4a (PCM sha). Lineup search (65 windows pass the
  opener/topic screen) is being scored by the production scorer now.

- 08:53 batch for the 08:30 note staged + in audit (batch6_orch0830): replay harness (run_fresh.run_tail +
  pipeline/replay.py), stand-alone + topic rule (pipeline/stand_alone.py at validate for every run, and at
  auto selection on final windows), G18 canonicaliser (decimal = one token), shot_snap (V1 next shot),
  wrapper sends Telegram only on a clean pass. Replay of run 6 from prepare running with these: prepare
  snapped clip_02 "tail: frames 315-317 were the next shot, held on frame 314" (audio untouched).
- 08:50 lineup search widened (direction 1, decision above): full audio of Bitcoin Magazine jbDqdLytkNM
  ("Bitcoin Loses Key Moving Average"), Marty Bent eEB0nt6jvEw, DataDash RXTVaDsN11M, Yahoo 36HPi9UZPOc,
  CoinTelegraph LGzfQjA2SHA in runs/recut_sources_20261111b (whisper large-v3 words + punctuation running);
  video only for the chosen windows afterwards. Run 6 REPORT.md has the six-window table (proposed windows
  score 4.0 / 4.0 / 5.0 and pass stand-alone; each is blocked by a measured edge pause under the law).

- 08:38 4b landed on this branch (55eb579b + 376c4127, audited: batch4 AUDIT_RESPONSE.md). Suites 166
  passed; the one failure is the documented pre-existing live-LLM test (test_editorial_robust
  positive_control_real_midterms: story_semantics only, byte-identical before/after 4b);
  regression_test.sh 26 PASS / 0 FAIL; regression.sh PASS (0.041 s).
- 08:30 ORCHESTRATOR NOTE (do not send failing cuts; four directions). Run 6 had ALREADY been delivered
  at 08:20 as REVIEW ONLY by the wrapper (msgs 67570/67571 videos, 67572/67573 contact sheets), before the
  note: the wrapper sent REVIEW ONLY drops by design. Changing: Telegram only on a clean pass.
  Evidence so far (verified, not assumed):
  * G9: tail = the hash-identical locked outro; luma run 6 16:9 14.3058 / v2f 14.3357 (floor 14.33),
    9:16 14.7430 / 14.7715 (floor 14.77); the conformed outro itself 12.69. Encode-level 0.03 on a
    black-ending card vs a floor 0.006 under the reference: calibration margin question (OD-4), gate kept.
  * G5: duration 54.83 s < 60 (hook 10.1 + clips 18.1 + 13.3 = 41.4 s of content); loudness -15.6 LUFS
    (target -14 +- 1): per segment hook -13.3, clip_01 DataDash -21.6, clip_02 -15.0, shoutout -15.3,
    outro -13.1; v2f whole -14.6. The DataDash segment is 8 LU under the rest.
  * G14: NOT the dissolve offset: 16:9 frame_sim >= 0.99 on every sample incl. all of clip_02 after the
    dissolve (reference 28.133 s = source 24.695 s = cut_in + 45 ms); the 0.00-0.04 values are the 9:16
    crop-vs-source comparison, which the gate itself marks LIMITED (unscored). The one scored failure is a
    0.5 s audio window in DataDash's clip (t = 12.08 s): speech at -39 dB median (quieter than his -28..-32)
    matched 4.6 s away at xcorr 0.42 (>= 0.3, so not "inconclusive").
  * G15 (OD-1 evidence, docs/audits/pulse-sentence-law/od1_g15_evidence/): the three avatar rings measure
    round; the only "squished ring" is the capital N of "Natalie Brunell" (contour bbox 31 x 36 px; its
    fitted ellipse 122 x 212 passes G15's size filter, which tests the ellipse, not the contour). G15 kept.
  * G17a clip_01 lead 60 ms: DataDash's source is noise-gated: the 320 ms before "But" is mostly below
    the -100 dBFS digital floor, which G17a does not count as genuine quiet; only 60 ms is above it.
    Moving the in-point or the room-tone pad cannot change that measurement (OD question, gate kept).
  * G3: heard 'bye!' / 'no' for 'But' (hook, clip_01); G18 edges (first two words, full-context ASR)
    and G17b first_word_ratio 0.98 / 0.95 say the words are intact.
  * G18: one real comparator hole found while fixing it: '5.5 %' became tokens '5 5' and the
    repeat-collapser merged them to '5', so 5.5 % and 5 % compared EQUAL. Fix: a decimal is one token;
    'one point three' / 'five and a half' map to it; tests both directions.
  * V1 next shot: real defect: Natalie's source cuts to an NVIDIA/AMD/MICRON graphic inside the pause
    before "Nvidia" (37.94); our out-point 37.86 keeps those frames.
  * Lineup (direction 1): the better windows are excluded by MEASURED audio under the unchanged law, not
    by a bug or a budget: DataDash 0.00-9.08 hook: file-head in-edge fine (0.25 s pad declared), but after
    "give or take." the genuine quiet run is 9.30-9.39 before a breath, so the law's tail (pause start +
    80 ms = 9.37) and cut_accept's run (9.33 with its 60 ms margin) never meet. Natalie "Bitcoin also
    wasn't spared ... last week." (3 sentences, 11.78 s): out-pause 120 ms < 80 ms tail + 60 ms guard;
    her 5-sentence window breaks the 1-3 sentence law and "rally." has no pause. Yahoo "Of course, Bitcoin
    dropped ...": no >= 80 ms pause before it (nor before the two sentences ahead of it). Under the
    stand-alone + topic rule, the frozen 5-min sources hold NO legal lineup for this story: Natalie has no
    legal Bitcoin window; DataDash no legal topical hook. Decision (logged): widen the search (full-length
    sources of the three videos + the approved channels that quoted the same price drop on Nov 10, e.g.
    Marty Bent, Bitcoin Magazine), never relax the law.

- 07:23 recut run 5 (runs/pinned_20261111_120910, HEAD b74c3b6c) HELD at render after 642 s:
  env..layout PASS (clip_02 fade retry 37.86 PASS; all six edges PASS). ffmpeg refused the transition
  graph: "First input link main timebase (1/1000000) do not match ... xfade timebase (1/24)": no room
  for a dissolve at hook->clip_01 (hard cut = concat filter), dissolve at clip_01->clip_02 (2 frames,
  bounded by measured non-speech) took the concat output as its first input. Phase 3 tests only dissolved
  at the first junction. Fix: settb=1/24 on xfade's running input; reproduced on the real graph (1290
  frames = 53.75 s, A/V equal) and by a new A,A,B test that fails on the old code with the production
  message (E-FAIL-025). Audit (batch5_xfade_timebase) + regressions running; then commit, push, run 6.
  Nothing delivered for run 5 (no finals).

- 07:15 4b on branch pulse-4b-wip (a2b56e53, worktree ~/worktrees/pulse-4b, pushed): same-event merge,
  DEC-9 story ledger (+ wrapper hook), letterbox one frame per shot, runbook, bible E-FAIL-023/024. Batch
  audit 4 (b74c3b6c..pulse-4b-wip) running; lands on this branch after run 5 + options, then Law 22
  re-proof at that HEAD, then the three fresh runs.
- 07:09 recut run 5 at HEAD b74c3b6c (pushed): runs/pinned_20261111_120910 via scripts/pulse_check_run.sh
  (foreground: this session lives in tmux pipeline_pp_dod). env..prepare PASS (clip_02 fade retry ->
  37.86 PASS; all edges PASS), layout done, render in progress.

- 07:05 batch 3 audit answered (AUDIT_RESPONSE.md): 9 fixes, each with a test failing on the audited code
  (review index `true`, vacuous second-edge move in the fade retry, stale contact sheet in copied runs,
  vision route retries, malformed answer line, key error, `_parse`, photo limits); rejections with evidence.
- 06:38 batch 3 (render fix + 06:20 contact sheet/visual checklist + batch-2 consensus) staged for ONE audit
  (deepseek,qwen27b + cross-LLM), then commit + push + recut run 5 via scripts/pulse_check_run.sh.
  Run 4 (runs/pinned_20261111_111252) passed env..layout and HELD at render: `module 'transitions' has no
  attribute 'plan'` = pipeline/transitions.py shadowed by video_pipeline_v3/transitions.py (render16 puts
  that folder first on sys.path) -> renamed pipeline/pulse_transitions.py + fresh-interpreter import-order
  test (E-FAIL-021). Suites 111 pass; regression_test.sh 26 PASS / 0 FAIL; regression.sh PASS (0.041 s).
- 06:40 vision panel (qwen3.8-27b + nemotron-3.5-super-vl) on yesterday's 9:16 sheet: HOLD, both name the
  credits thumbnails (D4); BOTH miss the letterboxed Melker/Brunell talking heads (D5) although the sheet
  shows them plainly (I read it). The vision line is an extra check; letterbox is caught by G4s, not by
  vision (E-FAIL-022 "still open").
- 06:50 vision follow-up (NOT in batch 3; lands before the 4b runs): asked ONE frame at a time ("is the
  sharp picture only a band with a blurred copy above and below?"), both models answer correctly on
  yesterday's frames: Melker clip_02 yes, DataDash chart hook yes (a screen: allowed), credits no. Plan:
  one full-res frame per SHOT of every 9:16 talking-head segment (VERTICAL_LAYOUT.json classes), any
  non-screen shot called letterboxed by either model (or unanswered) = V1 FAIL; must-fail on the
  fixture's Melker panel.
- 06:48 4b same-event merge (scratch copy, 7 tests pass; lands after run 5): link = the same counted
  STATEMENT (same video, shared supporting chunk, >= 5 consecutive shared words in the evidence quotes);
  a shared chunk alone is not enough (roundup shows). Real Nov 10 record: links exactly #13 "ETFs shed
  $1.3B" + #20 "Falls amid tech selloff" (identical Yahoo quote); #4 "below $74K" had NO counted verdict,
  #13 alone already had 2 channels and failed on hook quality (my earlier "each fell short on coverage"
  was wrong). Re-judge budget goes to not-counted verdicts by retrieval score. The tests caught a real
  NameError (`_decide_coverage` lost its local story_semantics import when moved out).
- DEC-9 decision (logged, not asked): the 72 h universe means runs 3 h apart still share most stories,
  so "genuinely different" is enforced by a delivered-story LEDGER (same event identity as the merge);
  each run takes the engine's top story not already delivered. A "no producible story" HOLD (with its
  rejection ledger) neither counts nor resets; then the next run waits for new stories.
- ORCHESTRATOR NOTE 06:45: after run 5 renders, REPORT.md gets the full text of every segment and the
  clip scorer's stand-alone score + reason (hook opens "I don't check it", clips open "But"/"And");
  selection is NOT changed now.
- 06:42 the production scorer (story_semantics.rate_passages, gemma3:27b, one batch as auto mode calls it)
  on the PIN text: hook Yahoo 3.0 "starts_mid_thought" (HOOK_MIN_SCORE 4.0: BELOW the auto floor);
  clip_01 DataDash 5.0 none; clip_02 Natalie 4.0 none (CLIP_MIN_SCORE 3.5). The auto window-start rule
  (editorial_select.start_is_boundary, CONTINUATION_OPENERS) rejects ALL THREE starts ("But", "But",
  "And"). The PIN path checks neither: I chose its windows by the sentence law alone. Not changed (06:45
  note); reported in run 5's REPORT.md. Evidence: scratchpad recut/standalone_scores.json.

- 06:12 recut run 4 at HEAD 8d10fcb7 (runs/pinned_20261111_111252) in progress, delivery to the approval
  chat by scripts/pulse_check_run.sh; then A/B/C (pipeline/transition_options.py) on the same cut.
- Recut runs so far, each HOLD fixed at the root cause, gates unchanged:
  run 1 05:45 (HEAD 497d8224) editorial gate LAW_1 "clip 2 missing": the review validator RETURNED its error
  (chat_json only reacts to exceptions) -> 99d20fb5 (E-FAIL-019);
  run 2 05:49 (99d20fb5) prepare: clip_02 fade-out (cut 37.87 on a tick inside the legal pause; real
  prepare at 37.84/37.80 passes) -> 9a0307c8 retry the failing edge at the next legal point (E-FAIL-020);
  run 3 06:03 (9a0307c8) prepare: CUDA OOM (another session's 22 GB model on the shared GPU0 Ollama) ->
  8d10fcb7 Whisper stages release GPU0 first (editorial-stage convention).
- Batched audit 1 (a1e732e1..497d8224) answered in 8d10fcb7 (AUDIT_RESPONSE.md); batched audit 2
  (497d8224..8d10fcb7) running. Its Grok call tripped the shared xAI $1/day ceiling at 05:49 and the gateway
  posted one "[xAI BUDGET]" alert to Telegram; audit wrappers now blank TELEGRAM_*; Grok blocked today.
- Law 22 re-proven with Phase 2+3+4a in the tree (runs/v2f_20261111_103004 byte-identical).
- 4b plan (read-only map, 05:47): (A) same-event MERGE after the coverage loop in editorial_select
  (~:802, before the word pass): group candidates of one event, one merged query (derive_story_query),
  pool verdicts deduped by video, RE-JUDGE the uncounted CURRENT_EVENT verdicts on their stored excerpts
  against the merged event (pooling alone would not have rescued Nov 10: only Yahoo + Natalie counted;
  the hand fix upgraded DataDash by re-judging), recompute coverage/currentness/decision. (B) widen the
  word-timestamp pass (`need`, ~:805-810) to every newly counted layout-eligible video, inside the one GPU0
  swap. Tests: test_window_review RoutedLLM + test_editorial_robust Orchestration fakes; a Nov 10
  story-split fixture from runs/fresh_20261110_093150. DEC-9 story ledger uses the same event identity.
- ORCHESTRATOR NOTE 05:40: deliver the corrected Nov 10 re-cut (gated + Telegram) and the A/B/C options
  before any further Phase 1 refinement; heimdall panel = deepseek + qwen27b (+ Grok via cross-LLM);
  batch related diffs into one audit. In progress: Phase 2 + Phase 3 + 4a code audited as ONE batch
  while the 4a PIN run renders; then 2 commits (Phase 2 vertical; Phase 3 + 4a).
- 4a PIN (frozen local 5-min windows, runs/recut_sources_20261111, sha-pinned, machine cuts by the law):
  hook Yahoo 47.31-57.37 ("...bounced very nicely ... around $74,000 ... 50-weekly MA ..."),
  clip_01 DataDash 143.62-161.67 ("...really nice decline here on Bitcoin, okay? 16 % so far ..."),
  clip_02 Natalie 24.65-37.87 ("...NASDAQ fell even harder, dropping 5.5 % ... concentrated in AI.").
  Her ETF/price sentences have no >= 140 ms pause anywhere in her first 5 min (not cuttable).
- Committed + pushed: 1a b6e7d436, 1b+1c 99add647, 1e 3641440f, 1d 9ad93344, DEC-1 9aa4fdb2,
  1d follow-up 0449a3ce, DEC-1 follow-up d10832cb, 1b fix a1e732e1 (model adjudicator removed: it
  rubber-stamped 19/19 Yahoo gaps; punctuation from a second ASR decode, E-FAIL-013).
- Working tree, uncommitted: Phase 2 (vertical auto layout, SCRFD pinned, G4s band-correlation safe-frame
  test, stack band_cy, caption note), Phase 3 (transitions; ffmpeg 4.4.2 xfade put the dissolved-into
  clip's picture 1 frame behind its sound; fixed + content test), 4a (G18 word_diff edges+identity,
  verify_pack stage, telegram.deliver_run, transition_options, scripts/pulse_check_run.sh, RUNBOOK).
- Law 22 re-render with all of the above in the tree: running (runs/v2f_20261111_103004).
- Full suite: 284 passed; 2 failures pre-existing LLM editorial tests (same failure at 3641440f).

## REQUIRED / MONITORING gate inventory (addendum '22:15' item 4; pipeline/release_auth.py inventory v1, 2026-11-11 22:12)

A row DECIDES release (REQUIRED) only with a real passing fixture, a realistic failing fixture and a defined answer
to missing evidence. Release-level answer to missing evidence for every REQUIRED row: no execution evidence
(executed True and samples >= 1, written by run_fresh / verify_pack into GATE_REPORT.json) = blocker. MONITORING
rows must be present with an exact verdict (they are reported in the drop's caption) but do not decide release.
No gate is deleted; a row moves to REQUIRED when its missing fixtures land (test named in the row).

| row | real passing fixture | realistic failing fixture | missing evidence (gate level) | class |
|---|---|---|---|---|
| G1_voice | none for this format: its only VO is the sign-off inside 'shoutout', so 0 regions are measured (pinned_20261111_172202_replay_cut1329: 0 rows, PASS) | none | 0 regions = PASS (vacuous; C fixes) | MONITORING |
| G2_watermark | none | none | - | MONITORING |
| G3_cuts | none real (synthetic 'magnitude' only) | synthetic only | empty transcript = FAIL (test_round2) | MONITORING |
| G3b_cut_out_clean | corrected Nov 10 cut tails, v2f vertical '$' tail (test_g3b_majority) | Nov 10 Natalie tail, a cut inside the last word | (C: no reading / no last word = FAIL) | REQUIRED |
| G3c_acoustic_tail | v2f finals (test_dec1_calibration) | v2f tail made just shallower (test_dec1) | - | REQUIRED |
| G4_faces | none (source-inspection test only) | none | - | MONITORING |
| G4_faces_per_shot | none | none | - | MONITORING |
| G4s_layout_truth | Nov 10 prepared clips, correct labels (test_vertical_layout) | mislabelled talking head / screen | unmeasured shot reported | REQUIRED |
| G5_tech | v2f (test_dec1), approved 102 s vertical (test_round2) | just beyond (test_dec1), 50 s / 130 s (test_round2) | - | REQUIRED |
| G6_preroll | none | none | 0 regions = PASS (vacuous; C fixes) | MONITORING |
| G8_sharpness | v2f (test_dec1) | just beyond (test_dec1) | no source clips = FAIL (test_round2) | REQUIRED (Claude-gates #5 being measured) |
| G9_tail | v2f finals, another encode of the locked outro (test_g9_floor) | a tail one luma code darker | - | REQUIRED |
| outro_locked | v2f | a conform fallback, an outro that is not the locked one (test_g9_floor, test_dec1) | - | REQUIRED |
| G10_chyron | none | none | - | MONITORING |
| G11_parity | none | none (its segment count compares the manifest with itself, GPT-gates F31) | - | MONITORING |
| G12_credits | v2f card, today's four-avatar card (test_pulse_20261110_mustfail) | three rings for four channels | - | REQUIRED |
| G13_vo_audible | none | none | empty sign-off text = PASS (vacuous; C fixes) | MONITORING |
| G14_av_alignment (16:9) | current 16:9, corrected Nov 10 cut (test_g14_g15, test_g14_sampling) | v2e 3.5 s lag, a two-frame slip | < 3 conclusive samples = HOLD | REQUIRED |
| G14_audio_offset (9:16) | the corrected Nov 10 cut's vertical (test_g14_sampling TestG14AudioOffsetVertical) | a real 2-frame audio slip | < 3 conclusive samples = HOLD | REQUIRED |
| G14c_duration_parity | current parity (test_g14_g15) | none | - | MONITORING |
| G15_credits | v2f card, today's card | Nov 10 squashed avatars, a squeezed card | no credited channels = FAIL | REQUIRED |
| G16_sentence_boundary | Nov 10 control edges (test_pulse_20261110_mustfail) | Nov 10 D1 / D3 defects | - | REQUIRED |
| G17_onset_tail | a faithful render | a render that eats the opening word, a head without lead | - | REQUIRED |
| G18_word_for_word | Nov 10 hook words intact (test_word_diff) | Nov 10 clip_01 / clip_02 | missing selection lock = FAIL | REQUIRED |
| G19_edge_shots | run 6 snapped replay (test_edge_shots) | run 6 final (next shot in clip_02) | no speech record = FAIL | REQUIRED |
| G20_signoff_names_all | v2f sign-off (test_g20_signoff) | the preview's sign-off misses the hook channel | no shoutout / no credits = FAIL | REQUIRED |
| V1_visual_checklist | TestVisionMustPass: the PBX-approved preview passes V1 in both formats (green 22:34) | Nov 10 vertical sheet, a letterboxed talking head (TestVisionMustFail) | no sheet / empty or partial panel = FAIL, vision off = SKIPPED | REQUIRED |
| vertical_silent_fallback | every real run's render log + vertical dimensions (no fallback) | the real reframe-failure log line (test_fresh test_fallback_regex) | no provenance record = KeyError = HOLD; samples = the vertical clips checked | REQUIRED |
| G14_frame_similarity (9:16) | - | - | - | NONBLOCKING: LIMITED only (not valid for a crop) |

## OPEN DECISIONS FOR THE ORCHESTRATOR (evidence; work continues meanwhile)

**OD-L-c (2026-11-11 23:06, batch 16) The amended L-c proof cannot be made on real finals; the approved preview would
HOLD on G3c.** Measured on runs/pinned_20261111_172202_replay_cut1329 and references/pulse_preview_2026-11-11 (both
formats): the final's gain against the source drifts along a clip (loudnorm + the music bed; 1 s windows 1.65-2.03 dB
on the hook, 2.23-7.25 dB on clip_01), so the gain next to an edge is not steady (IQR > 1 dB) for hook / clip_01 /
clip_02, and clip_03's first word is 9.1 / 9.2 dB below the source in the final (it sits inside the clip_02 -> clip_03
dissolve: a possible real L-b defect in the approved preview, which the prepared-clip proof could not see). With
G17c's unchanged 1 dB criterion no edge of either run can be proved on the final, so every G3c edge failure and every
G3b dissent now stands. The corrected cut fails G3c on the hook's tail (REQUIRED) => it would HOLD. Options (none
taken: each changes what a check accepts): (a) G3c to MONITORING; (b) a final-audio proof criterion calibrated on real
finals (like DEC-12a's measured G9 spread); (c) keep (fail closed: such runs HOLD). The dissolve-over-the-first-word
finding on clip_03 is evidence either way.

**OD-1 G12/G15 misfire on correct credit cards (DEC-7).** With the render fixed (real square
avatars from the registry; rings measured 0.999), the UNCHANGED gates still fail the rebuilt Nov 10
card: 16:9 G12 counts 5 "circles" — the extra ones sit on Natalie Brunell's real avatar's ORANGE
background (G12's red mask R>100, R>G+40, R>B+40 includes orange); 9:16 G15 fits a 0.457 ellipse at
(481, 1076) = the middle channel's NAME LABEL text, not a ring. Yesterday's 9:16 G15 failure was the
same label contour. So G12/G15 are content-sensitive; a story crediting such a channel cannot pass
them unchanged. Not changed (mission 1e, DEC-7, M2). If re-specified, the rings-only measurement
would no longer see warped avatar CONTENT, so D4 is now guarded deterministically before render
(shoutout.validate_avatar: square + registry sha prefix; tests in pipeline/test_pulse_20261110_mustfail.py).
Evidence: scratch renders of the rebuilt card, g12_circles overlay (circles on the orange background).

**OD-2 G16/G17 not calibrated to v2f (DEC-1 applied to G3c/G5/G8/G9 only).** v2f predates the
sentence law and fails it on all four segments (table below). Calibrating would set lead/tail to 0 ms
and admit mid-sentence starts, i.e. re-admit D1-D3; PBX's own v2f record calls clip_01's out edge a
ONE-TIME exception with "the 60 ms rule unchanged". New renders must meet the law; v2f stays the
approved legacy reference for everything else.

**OD-3 Prepare-stage picture fidelity is ungated (late Heimdall finding on DEC-1, measured).** G8
compares the final against the PREPARED clip (its pre-DEC-1 approved "relative reference"), so it
measures the render stage only. Measured at G8's own sample instants: on the approved v2f, prepare
(lanczos to 1920x1080, NVENC QP 20) keeps only 0.696 (clip_02) / 0.760 (hook) of the original
download's Laplacian variance (largely grain removal); Nov 10 keeps 0.985-1.040. With the original
download as G8's source the APPROVED reference would fail the unchanged 0.85 ratio (0.689 / 0.770), so
that wiring would need a ratio calibration (an acceptance change) — not taken. Decision for the
orchestrator: gate prepare fidelity (and against what), or accept it as part of the approved look.
Evidence: docs/audits/pulse-sentence-law/dec1_calibration/HEIMDALL_RUN_FRESH_RESPONSE.md.

**OD-1 (addendum, run 6, 2026-11-11 08:40).** Same class again: 16:9 G15's only "squished ring" is the
capital N of "Natalie Brunell" (contour bbox 31 x 36 px; fitted ellipse 122 x 212 passes the size filter,
which tests the ellipse not the contour); 9:16 at (324,1515) the same glyph. Overlays:
docs/audits/pulse-sentence-law/od1_g15_evidence/. Any card crediting "Natalie Brunell" fails G15 unchanged.

**OD-4 G9 tail luma measures encoder lift on a black-ending card, not the content.** The tail is the
hash-identical locked outro. Decoded directly, its last second has luma 12.69; finals measure 14.31
(run 6) / 14.34 (v2f) / 14.74 / 14.77 (9:16) because the final re-encode lifts near-black. DEC-1 set the
floor 0.006 under v2f's own value (14.33 / 14.77), smaller than the 0.03 encode-to-encode difference, so a
correct render passes or fails by encoder state; a lossless outro would fail outright (12.69). Decision:
what G9 should measure on a locked black-ending outro (e.g. hash/identity of the outro region, or the
floor with an encode margin). Not changed.

**OD-5 G17a counts noise-gated digital silence as "not genuine".** DataDash's source pauses sit below the
-100 dBFS digital floor (noise gate). Run 6 clip_01 has 320 ms of silence before "But", of which 60 ms is
above -100 dBFS, so G17a reads lead 60 ms < 80. Moving the in-point or the room-tone pad cannot change
that reading. Decision: is gated digital silence inside a source pause (not at a file head, where D1
lives) genuine quiet for G17a? Not changed; selection avoids such edges meanwhile.

**OD-6 G3 judges ONE first word from a context-free ASR of the clip head.** Run 6: 'bye!' / 'no' for
"But" (hook, clip_01) while G18's word-for-word edges (full-context ASR) and G17b's first-word acoustic
ratio (0.98 / 0.95) show the word intact. Short function words fail G3 by ASR, not by render. Decision:
keep G3 as is (selection then avoids conjunction-opening clips), or measure the first word with context.
Not changed.

**OD-7 G14 0.5 s audio windows under the music bed.** Run 6's one scored G14 miss is a window in
DataDash's quiet passage (speech -39 dB median vs his -28..-32 elsewhere) matched 4.6 s away at xcorr
0.42 (>= the 0.3 'conclusive' bar); every other sample of the 16:9 matched exactly. A quiet source under
the bed weakens the correlation. Not changed; G5 loudness work (segment levels) would also raise the
speech-to-bed ratio there.
Addendum (recut #2, 2026-11-11 13:30): one G14 sample at clip_02 +2.0 s lands in a 0.6 s PAUSE inside
Yahoo's sentence (source -44 .. -84 dB from 40.17 to 40.90; the final holds only the bed there, -38 .. -45
dB): xcorr 0.154 / 0.174 < 0.3 = HOLD(inconclusive). Not a transition or VO freeze, so the authorised
sampling skip does not apply. Decision: may a sample whose SOURCE window is below the source's quiet level
move to the nearest window with source speech (threshold unchanged; must-fail: a 2-frame slip elsewhere)?

**OD-8 G3c on a quiet source's room tone.** After the 8d fix G3c fails only the DataDash hook tail: the
last 60 ms (room tone in a 340 ms pause, no next word) read -42.7 dB vs the limit speech - 11.63 = -43.9;
DataDash speaks at -32.3 dB over a -42.7 dB room: 10.4 dB, so any cut in that pause with the 30 ms fade
fails it. An envelope-minimum cut with the 2-frame fade (DEC-10 d's method) would pass but is a cutter-wide
change for long pauses. Decision: apply DEC-10 d's method to every out edge, or treat a tail with no
neighbour word by its neighbour rule (c-ii) only.

**OD-9 G10 in 16:9 for has_chyron channels.** Recut #2's 16:9 shows Bitcoin Magazine's burned-in lower
third (sponsor bar, stock + BTC tickers, speaker chyron): bottom-12 % edge density 0.0846-0.0854 vs 0.08,
0.084 without the watermark strip. The 16:9 path has no chyron framing (has_chyron only routes the channel
to G10); the 9:16 safe frame blurs it. Decision: a 16:9 framing for has_chyron channels (crop above the
lower third / safe frame), or selection avoids windows with a lower third.

**OD-10 G3b single-word ASR under the bed.** Replay of recut #2: the 16:9 final's context-free tail decode
heard 'in the monday route.' for '... rally.' (the 83 ms DEC-10 fade ends 35 ms after the word at the true
minimum); 9:16 G3b, prepare's edge check ('rally.'), G17b (>= 85 %) and G18 word-for-word all pass. Same
class as OD-6 (G3 on one word). Decision as OD-6.

## 1f — the gate suite on the frozen v2f reference (2026-11-11, scratch copy, production stage_gates)

| gate | format | v2f measured | threshold | approved video shows the defect, or gate stricter than approved? |
|---|---|---|---|---|
| G3c acoustic tail | both | hook: tail rise to −31.4 dB vs speech −21.7 dB → "onset"; passes at depth ≤ 11.63 dB (16:9) / 11.65 dB (9:16) | valley ≤ speech−12 dB, no sustained rise | stricter than approved (REFERENCE_v2f: output fades to −87 dB at 9.52, next word 9.60) → DEC-1 |
| G5 true peak | 9:16 | −1.3 dBFS | ≤ −2.0 | stricter (REFERENCE: "9:16 peak −1.3 dB, approved as reviewed") → DEC-1 |
| G8 sharpness floor | 16:9 / 9:16 | worst segment medians 27.56 (hook) / 10.84 (clip_03) | ≥ 60 | stricter (soft source cameras, approved) → DEC-1 |
| G9 tail luma | 16:9 / 9:16 | 14.3357 / 14.7715 | > 20 | stricter (locked PBX outro ends on black, approved) → DEC-1 |
| G16 sentence boundary | both | hook lead 40 ms genuine, no pad; clip_01 in 238.55 is 80 ms after the pause before 'The', out has no ≥80 ms pause before 'So'; clip_02 no pause before 'One'; clip_03 starts mid-sentence ('of \| a prison'), out 20 ms after 'have.' | sentence law (2026-11-11) | approved video SHOWS the defects the new law prohibits → not calibrated (OD-2) |
| G17a onset/tail | — | leads 40/40/0/190 ms, tails 150/40/190/0 ms | ≥ 80 ms | same → not calibrated (OD-2) |
| G17b edge words | both | PASS (render faithful) | ≥ 85 % | — |
| G1-G2, G3, G3b, G4, G6, G10-G15 | both | PASS | unchanged | — |

## Rule → check → proof

| PBX rule | Enforcing check (code) | Must-fail proof | State |
|---|---|---|---|
| Clip starts on the first word of a sentence | G16 SENTENCE_BOUNDARY IN edge (pipeline/sentence_law.py gate_g16, pre-render stage `sentence_law` + final gate row) | T pulse_20261110: D3a clip_01 '81', D3b clip_02 'days' | enforced (99add647) |
| Clip ends on the last word of a sentence | G16 OUT edge | T pulse_20261110: D2 clip_01 runs into "All right…" | enforced (99add647) |
| Expected words fixed at selection, never recomputed | G16 selection-lock check (sha-sealed lock in edl.json vs cuts_final expected words) | T pulse_20261110: TestTautology | enforced (99add647) |
| A sentence boundary needs evidence: punctuation from the audio, never a model's opinion of one gap | sentence_law.boundary (an unpunctuated stretch has no boundary, fail closed); pipeline/punctuation.py (marks from a second, prompted ASR decode of the same audio onto aligned verbatim words) | T pulse_20261110: TestUnpunctuatedTranscript (the 19/19 'sentence ends' of the removed adjudicator, 'the | Wolf' etc., are rejected), TestPunctuationLayer | enforced (1b fix) |
| A cut never adds/drops a word; snapping only inside the gap | sentence_law.write_lock_cut_table (cuts placed only inside the locked sentence's heard gap, DEC-10; cut_accept unchanged on every edge not cut at the envelope minimum); ±2 s snap + recompute removed | T: test_run_fresh_has_no_recompute_sync_or_wide_snap | enforced (99add647) |
| No clipped onset at the start of playback (file head / hook: ≥ 80 ms genuine lead-in or the room-tone pad; D1, unchanged by DEC-10) | G17a hook lead (HEAD_LEAD_MIN_S); G16 file-head pad rule | T pulse_20261110: D1 hook (60 ms genuine lead-in) | enforced (99add647) |
| Edge timing inside the video calibrated to the approved v2f, not a silence quota (DEC-10 a-b) | LEAD_MIN_S / TAIL_MIN_S / PAUSE_MIN_S / GUARD_S = 0 ms (v2f's measured worst, DEC-10a table); G16 legal range = the heard gap | T test_dec10_edges: every v2f edge passes (3 recorded by measurement must fail) | enforced (ae965c95) |
| No audible part of the neighbouring word (DEC-10 c-ii); a short gap is cut at the envelope minimum with a 2-frame fade (DEC-10 d) | sentence_law.neighbour_clear in accepted_cut and in G16 with the cut's own fades; run_fresh.stage_cut defers an edge cut at the minimum to G16 instead of cut_accept's M19 quota | T test_dec10_edges: a cut inside a word is audible; v2f clip_01 OUT / clip_02 IN fail; valley fixture; stage_cut deferral; T pulse_20261110 D2 (Natalie run-in) fails | enforced (ae965c95, 29299ea5) |
| Edge words keep ≥ 85 % in the render | G17b on both finals | T: TestG17bRenderedEdges (muted onset fails, 20 ms fade passes) | enforced (99add647) |
| L-a SIGN-OFF NAMES ALL: the sign-off voiceover names every channel on the credits card, and the spoken set, the card set and the clips used are identical. | run_fresh.stage_voice HOLDs before render unless the script names exactly credit_rings.credit_channels(edl) (hook first, then clips); G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off and requires spoken == credited (registry names + aliases); VO stems are keyed by hash(text, voice, model). Must-fail: the 2026-11-11 preview (DataDash missing). Must-pass: v2f. | see Check | enforced (DEC-12 batch, 2026-11-11) |
| L-b EDGE WORDS WHOLE: a fade never overlaps an edge word: the first and last word of every clip are heard whole, at full level, with their natural decay. | sentence_law.edge_fades places each machine-cut fade (2 frames, shortened down to 10 ms) inside the gap next to the cut, measured from the cut point's level; G17c (sentence_law.gate_g17_edges) requires every frame of both edge words within 1 dB of the unfaded source. Must-fail: the preview's Natalie Brunell tail ('...participated in the Monday rally.'). Must-pass: the L-b re-cut of it; v2f's edges except its two recorded legacy edges. | see Check | enforced (DEC-12 batch, 2026-11-11) |
| L-c DISSENT IS RIGHT UNTIL DISPROVED: a check that disagrees with the others on an edge word is treated as right until an acoustic comparison against the source proves otherwise. | run_fresh.stage_gates: a dissenting G3b reading (DEC-12f) or a G3c head / tail failure on an edge stands (HOLD / FAIL) unless G16's neighbour_clear passes and G17c, MEASURED ON THE FINAL FILE OF THAT FORMAT (sentence_law.edges_on_final: the bytes being approved, their constant gain removed, every frame of the edge word compared), passes for that edge; a proof from the prepared clip is never accepted (amended by the orchestrator addendum 2026-11-11 '22:00', GPT-cut F03). Test: test_release_auth / test_word_diff TestSpanMatches; sentence_law.edge_word_fidelity refuses an alignment that leaves a word frame uncompared (GPT-cut F07). | see Check | enforced (DEC-12 batch; amended batch 16, 2026-11-11) |
| L-d PROTECTED PREVIEW: the PBX-approved preview of 2026-11-11 is a protected reference. | pipeline/regression.sh step 6 (pipeline/check_preview_reference.py): its selection locks, cut points and 9:16 layout must reproduce with the current code; tag ref-pulse-preview-2026-11-11; references/pulse_preview_2026-11-11 (read-only, SHA256SUMS). | see Check | enforced (DEC-12 batch, 2026-11-11) |
| L-e PUNCTUATED BEFORE READ: every word transcript the sentence law reads, the editorial word pass included, has its sentence punctuation restored from a prompted second decode of the same audio before any sentence is read. | transcript_store.acquire(prefer_words) returns only a sentence_ready record: the verbatim decode where no stretch reads unpunctuated, else a whisper_words_punct record (marks from a large-v3 batched reference decode with punctuation.PROMPT, onto aligned words only, plus a sentence-initial capital where both decodes end a sentence right before the word, so editorial start_is_boundary reads the reference's own evidence; word keys and timings unchanged; the verbatim record kept; one Whisper model on GPU0 at a time); editorial_select's word pass treats any other record as failed. Must-fail: Altcoin Daily Ov5jg52HqIY's verbatim record (its quote read as one 35.28 s sentence). Must-pass: its restored record (the quote's sentence 161.14-170.08, "Even thinking about the seasonality, ... the midterms.", a valid 8.94 s hook window). Test: pipeline/test_punct_word_pass.py. | see Check | enforced (DEC-13 batch, 2026-11-11) |
| L-f CHANNELS FIRST (DEC-13): story candidates come from the channels' own conversation first: clusters of statements by at least two independent channels, screened for Bitcoin before any model call, with the claim written from their shared statements and their quotes attached; wire headlines are evaluated only after every cluster is exhausted. | editorial_select pools channel_clusters_48h -> channel_clusters_72h -> wire_headlines (a pool runs only when every earlier one produced nothing); cluster_entry (>= 2 channels with a Bitcoin statement, 48 h tier then 72 h max, else stopped with no model call; one statement per channel); a cluster's coverage adjudicates its own statements; every cluster's ledger entry names its channels, claim, statements, counted quotes and the gate that stopped it; a validated model reply is cached by sha256(model, its Ollama digest, context, max_tokens, prompt). MIN_COVERAGE_CHANNELS 2, hook >= 4.0, stand-alone, topic and sentence laws unchanged. Must-produce: today's $74K-pullback statements (4 channels) and ETF-outflow statements (2 channels) reach the model (under the old rule they were in no cluster). Must-not: Bloomberg's Fed-hike and Natalie Brunell's ETF-outflow statements never share a cluster. Test: pipeline/test_dec13_clusters.py. | see Check | enforced (DEC-13 batch, 2026-11-11) |
| L-g WRITTEN FORMS: a check that reads speech counts a word the ASR wrote as a symbol as the spoken word ('$40 trillion' = '40 trillion dollars', '50%' = '50 percent'), and reads the expected word the same way. | segment_v1/qa_gates._g3b_words: G3b's readings, the EDL's last word and its next word are read with the same rules (symbols spelled out in spoken order, abbreviated scales too ('$40M' = '40 million dollars'), a 'dollars' the ASR also wrote never doubled; thousands separators and trailing full stops dropped, other commas split words, decimals kept; a leak is any word of the next source word heard after the last word); vote rule and thresholds unchanged; G17c still compares every edge word with the source. Must-pass: the approved v2f's 9:16 clip_02 '... above 40 trillion dollars.' (read 'above $40 trillion' twice). Must-fail unchanged: Nov 10's Natalie tail against 'week.'; a cut 250 ms into 'rally'. Test: pipeline/test_g3b_majority.py. | see Check | enforced (batch 14, 2026-11-11) |
| L-h TEXT READ AS SPOKEN: transcript text is read as the words it stands for before any chunk, quote check or model sees it: caption HTML entities are decoded ('S&amp;P' = 'S&P') and a Whisper word split into tokens is read whole ('$81 ,000' = '$81,000'); the stored record is never rewritten. | transcript_store.read_text builds every chunk's text; story_semantics._norm decodes entities and joins split tokens for quote checks; the embedding cache is versioned (t2) so vectors match the read text. Must-fail / must-pass: Altcoin Daily's 'S&P 500' quote and Natalie Brunell's '$81,000' quote against their real excerpts (pipeline/test_caption_entities.py). | see Check | enforced (batch 15, 2026-11-11) |
| L-i THE CLAIM IS THE EVENT (DEC-13 a): a channel cluster's claim is the event its coverage is judged against: its query is derived from the claim alone and the model never re-reads it as another event. | story_semantics.derive_story_query: a transcript_cluster item is derived from the claim with CLUSTER_NOTE (no label summary) and its underlying_event is the claim verbatim (the model's reading kept as underlying_event_derived); wire items byte-identical. Test: test_caption_entities TestClusterClaimIsTheEvent; real model (DoD 20:13): Natalie Brunell and Coin Bureau then both count for the election sell-off / ETF-outflow claim. | see Check | enforced (batch 15, 2026-11-11) |
| L-j RELEASE IS AUTHORISED ON THESE BYTES (red-team order 2026-11-11 '21:55', A): 'all release gates passed' means every REQUIRED gate ran, on samples, unwaived, on exactly the bytes that are sent. | pipeline/release_auth.py is the one authorisation every send path uses: exact gate inventory v1 (REQUIRED rows exactly 'PASS' with evidence executed and samples >= 1; MONITORING rows present with an exact verdict, reported, not deciding: addendum '22:15' item 4; any other or missing row = blocker); run_fresh writes ATTESTATION.json last (holds anywhere = HOLD; executed code at the launch revision; the finals and manifests must be the bytes the gates measured); authorise() re-hashes both finals, EDL, manifests, gate report, verification pack and sheets before the first send; telegram.deliver_run checks each file's digest again before its send, checkpoints every message, never resends an unknown outcome; the legacy send_telegram_preview is removed; replays are never deliverable. Tests: test_release_auth.py (the fail-closed mutation family), test_telegram_delivery.py, test_failure_blocks.py. | see Check | enforced (batch 16, 2026-11-11) |
| L-k ONE CANONICAL FORM (orchestrator 2026-11-11 '21:10'): every text comparison in the pipeline uses pipeline/canon.py; two strings a listener hears as the same words compare equal, and a different number, unit, sign, name, negation or dropped word never does. | canon.canon_tokens / canon_aligned / same (entities, unicode, split tokens, numbers as values, currency and percent spoken order, signs, apostrophes kept); routed into quote verification, selection anchors, edge words, G3 / G3b, G18 (word_diff keeps units and signs; a repeat-only difference is decided by the audio, sentence_law.span_matches: GPT-cut F04 / F05), G20, G1 / G13 (token runs, never substrings), PIN approved text. Tests: test_canon.py (200 real sentences x mutations equal; real differences unequal; TestSites fails any ad-hoc normaliser outside canon.py). | see Check | enforced (batch 16, 2026-11-11) |
| L-n DELIVERY IS THE MEASURE (orchestrator 2026-11-12 '01:50'; PBX 01:43: "pls lock these changes into law"): the pipeline exists to deliver publishable videos, and the one number reported to PBX is videos delivered per day. A HOLD on a day when a line-up that passes our rules existed in the sources is a DEFECT of the selector (a miss), not a safe outcome. | every HOLD at editorial (or, under L-q, at mining / packaging) runs the blind oracle + judge on that run's universe (pipeline/oracle, branch pp-backtest, once merged); when it finds an accepted line-up the miss is logged with the first stage that lost it (MISS record in the run dir) and goes to the bible. Not yet wired. Tonight's instance: fresh_20261112_050611 HELD at editorial while the oracle's line-up 1 was judged to pass our rules (ORACLE.json sha256 e923e91fa3d05621844449244100ded681c916bf8d06d0aa4a7ec3f9e64bc77a): a miss (E-FAIL-043 family). | see Check | law recorded 2026-11-12; wiring pending (pp-backtest merge) |
| L-o INTEGRITY IS HARD, TASTE BENDS (orchestrator 2026-11-12 '01:50', amended '01:55' with L-q): two classes of rule, never mixed. INTEGRITY (hard, fail closed, never relaxed to ship): (1) every clip is verbatim whole sentences, what is spoken matching the locked sentences word for word (G16 / G18); (2) intact edges: no clipped or faded edge word (G17, L-b); (3) each clip stands alone, or is made to stand by the VO line before it WITHOUT changing its meaning; (4) Bitcoin-only; (5) >= 2 channels per video; (6) recent content (currentness); (7) credits card = EDL set = spoken sign-off set (G12 / G15 / G20, L-a); (8) release authorisation bound to the exact bytes (L-j); (9) nothing measured is never a pass (L-m, branch hardening-redteam); (10) the partner / guest source rule; (11) VO FIDELITY (new, '01:55'): the VO never puts words in a speaker's mouth: it may not attribute to a speaker a claim, stance or number that is not in that speaker's clip, may not imply two speakers were answering each other when they were not, and every fact the VO itself asserts is supported by a clip in the video or a verified source in PROVENANCE; a VO-fidelity check with must-fail fixtures must exist before any moments-first video is labelled a pass. REMOVED from integrity by the '01:55' amendment: 'same development from >= 2 channels' (now one packaging style among several, L-q). TASTE (targets that RANK candidates, never reject one when nothing better exists): the 8-12 s hook and 12-20 s clip duration windows; the hook / clip score floors; a sentence opening on a conjunction ('And', 'So', 'But') when it still stands alone in context. A whole sentence always beats a duration window: selection prefers passages inside the targets, and when no line-up fits inside them it takes the best line-up that passes our rules outside them and records each deviation and its size in PROVENANCE and in the Telegram caption. The only hard duration rule is the format: total runtime 60-70 s (PBX's format). | EVIDENCE asked by the '01:50' order (no number invented): CLOCK: the windows are measured on SENTENCE-LOCKED WHISPER WORD timing, never caption timing (editorial_select.py:49-50 define them, :1180 applies them; the words come from transcript_store.acquire(prefer_words=True), editorial_select.py:880, and only a sentence_ready record, whisper_words / whisper_words_punct, transcript_store.py:404-410, counts); the blind oracle's durations are caption-line timing, another clock, which a pinned run re-measures on locked words. APPROVED PASSAGES (locked word span): Nov 11 preview hook 9.08 s, clips 12.34 / 18.70 / 16.66 s; v2f hook 9.02 s, clips 10.70 / 11.54 / 14.44 s: PBX approved every length from 9.02 to 18.70 s, two clips under today's 12 s minimum among them; tonight's near-misses missed a window by 0.10-1.86 s (hooks 12.12, 12.74, 7.88, 7.0, 6.14 s; clips 11.9, 11.14, 11.02, 8.74 s). FORMAT: the approved preview's finals run 71.08 s (both formats), 1.08 s over 70; its four passages fill 58.17 s of the final, leaving 12.91 s of VO, cards and transitions. PROPOSAL: no fixed per-passage outer bound (no evidence supports one: nothing was ever rejected for a passage's length, and the approved range already spans 9.02-18.70 s); the one hard bound is the line-up total, checked BEFORE render where the line-up is chosen (selector / packager): passages + VO + fixed cards inside the 60-70 s format, i.e. at the preview's measured 12.91 s of non-passage time, passages totalling about 47-57 s; any per-passage limit is then arithmetic (70 s minus the fixed time minus the other passages), never a constant. For PBX: the approved preview itself ran 71.08 s; whether the format is checked on the final's runtime with a tolerance is PBX's call. WIRING (code change; two audit cycles; must-fail tests proving every INTEGRITY rule still rejects): into the moments-first miner / packager (L-q) and the shared validation (sentence lock, pinned validation); the story-first selector is retired ('01:58'). Until wired, the existing code still applies the windows and floors as hard filters. | see Check | law recorded 2026-11-12; wiring pending (L-q build) |
| L-p CADENCE (orchestrator 2026-11-12 '01:50'; PBX 01:43: "i need one new video every few hrs once this thing is live and operational. ideally every 3-5 hrs"): once operational the target is one NEW video every 3-5 hours; it supersedes the daily target as the goal, and the daily rate remains the first milestone. No schedule is installed without PBX. | design consequences, requests and notes, no code yet: (1) NOVELTY: a video is NEW when its development differs from every video delivered in the previous 24 h, or it carries a materially new fact on the same development; the story ledger enforces it (integrity class). Under L-q the proposed reading is: none of its sentence ids was delivered in the previous 24 h and its angle differs from every delivered video's, or it carries a materially new fact (open for the orchestrator). (2) SUPPLY: the 72 h universe barely moves in 3-5 h, so each cycle ingests what was published since the last one and the channel universe must be wide enough; pipeline_pp_backtest is asked (its REQUESTS file) for the DISTINCT developments per day with a line-up that passes our rules, as the oracle finds them in the saved universes. (3) RUN TIME: a full cycle must fit comfortably inside 3 h on GPU0 alone. Measured: tonight's editorial stage took 70.2 min (fresh_20261112_050611, 4213 s): about 50 min of gemma3:27b calls (397 calls, 230 cache hits; reply-cache writes from +1.4 to +70.2 min), about 19 min in three Whisper word passes, each a GPU0 swap (48 h pool +20 to +29 min, 72 h pool +33 to +39, wire pool +64 to +67), under 1 min universe + embeddings (cached). The last complete render path (pinned_20261111_172202) took 51.3 min after selection: render 17.9, gates 15.6, verify 13.4, prepare 1.6, layout 1.2, cut + sentence law + voice 1.1, review 0.6 min. A cycle is about 2 h: inside 3 h, not comfortably (no room for a second candidate after a HOLD). The time goes to model calls (~50 min), render + gates + verify (~47 min) and Whisper swaps (~19 min). | see Check | law recorded 2026-11-12; target only (no schedule) |
| L-q MOMENTS FIRST, THEN PACKAGE (orchestrator 2026-11-12 '01:55'; PBX 01:48: "i want you to start looking for the stuff that is most social media and engagement friendly. not all segments you clip need to be 100% same exact topic so long as any PBX MAX VO can stitch the two in a logical clever way that actually allows for points to be made etc. perhaps we analyze best of moments across every few hrs new content first.. then decide how to package it and how to optimzie for views etc. now THIS is the strategy"; '01:58': "pls drop the old video and start this new process"): moments-first selection is the product; story-first selection is retired, and the DEC-13 clusters (L-f) become one input, not the gate. STEP 1 MINE: each cycle, over the content published since the last cycle (plus the recent window), find the best MOMENTS: whole stand-alone sentences from partner / guest sources, scored for social engagement (a strong opinion, a surprising number, a quotable line, a named figure, stakes, emotion, a clean hook in the first 2 s), by sentence id, never rewritten. STEP 2 PACKAGE: choose the set of moments that makes the best video and the angle that ties them; the moments need not be the same development: the PBX MAX voiceover stitches them with bridges that make a point, logically and cleverly. STEP 3 OPTIMISE: hook choice, order, title / caption for views. Integrity is L-o's amended class, VO fidelity included. | a moments-first run replaces the gates that assumed one development (any same-event / topic check on the line-up) with the VO-fidelity gate, ONLY for moments-first runs and only once that gate exists with its must-fail corpus passing; every other integrity gate is unchanged ('01:58'). Build: pipeline_pp_selectid builds the miner and packager (pipeline/moments.py, package.py, trend_brief.py, the VO-fidelity checker) on its ids-only contract (pipeline/select_by_id.py, eligibility.py); pipeline_pp_backtest measures supply under this rule; the integrator wires and audits them when they report DONE. The first delivery goes to Telegram as REVIEW ONLY ('first moments-first package; selection + VO by the new path, not yet merged/audited') with its duration deviations listed per L-o. Not yet built. | see Check | law recorded 2026-11-12; build assigned (pp-selectid, pp-backtest) |
| L-r GPU0 NEVER SURPRISES A RUN (orchestrator 2026-11-12 '01:55' B; PBX on the pinned run's out-of-memory: "let's make sure that never happens again. what can we do rn to fix this??"): (1) ONE OWNER: every code path that loads anything on GPU0 (gemma via Ollama, Whisper, the face detector / vision gates, NVENC, the preflight's own model checks, GPU test sessions, the backtest) takes the gpu0.py lease first: no lease, no load; (2) ONE MODEL AT A TIME by construction: one function swap_to(model) unloads whatever is resident (Ollama keep_alive=0 confirmed via the GPU0 listener, torch empty_cache, the Whisper object deleted), then VERIFIES by nvidia-smi that GPU0's free memory is at least the incoming model's known requirement plus margin before loading; every stage calls it, nothing calls a loader directly; the preflight leaves GPU0 as empty as it found it and asserts that; (3) BOUNDED SELF-HEAL, not a silent retry: on CUDA out-of-memory, release everything this run owns, wait until nvidia-smi shows the memory free (timeout), retry the SAME step ONCE, both attempts in PROVENANCE; a second failure is a HOLD naming every process on GPU0 (pid, name, MiB); an out-of-memory never surfaces as a different error: the HOLD reason carries the real cause; (4) FOREIGN PROCESSES: at run start and before every swap, a process using GPU0 memory without the lease HOLDs the run at once, named; nothing is killed that the run did not start; GPU1 stays quarantined and untouched; (5) TESTS: a must-fail that loads a dummy allocation on GPU0 before each stage and proves the stage refuses or recovers as specified, and a test that runs env -> pinned -> render -> gates back to back twice and shows peak GPU0 memory per stage in a table, which every REPORT.md carries from now on. | in progress; it outranks hardening batches 18 / 19 and must be in place before the first moments-first render ('01:58'). Done so far: stage_pinned releases GPU0 before Whisper (456a440f, E-FAIL-052). The GPU0 paths are enumerated in the DoD (file:line, wired or not). It supersedes branch hardening-redteam's uncommitted GPU0 lease draft (batch 20), which is rebuilt to this law. | see Check | IMPLEMENTED 2026-11-12: 4867a74a + follow-up 34ba7726 (audit: 3 cycles, claude-fable-5-2, gpt-6.1-sol, gemini, heimdall); live GPU0 tests 6/6; back-to-back double run pending GPU0 |
| L-s CONTEXT INTEGRITY (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md; a new HARD gate, separate from VO fidelity; the reviewers' unanimous #1 blind spot): a verbatim whole sentence can still misrepresent its speaker once lifted. For every selected moment the inputs are the source's speaker-turn-aware transcript from at least 90 s before (back to the start of the question / turn) to 60 s after, the video's title and description, the selected sentence ids, and the finished package (order, adjacent clips, VO, title, caption). STEP A (context only, the package hidden): a model from a different vendor than the writer states who is speaking; whose view it is (own sincere / attributed to someone else / hypothetical / conditional / sarcastic / question / reading aloud / ad read); the referent of every pronoun and of 'this / that / today'; any governing condition or time frame; any retraction or qualification in the window. STEP B (the package only): what an ordinary viewer concludes the speaker asserts. PASS only if: the speaker's own sincere assertion; every referent inside the clip; no unmet condition and no reversal; the in-context proposition entails the viewer takeaway with the same polarity and no stronger certainty; no implied relation (agreeing / answering / rebutting) between speakers who were not in the same source video, whether by sequence, bridge or title, not only by banned words. Any 'uncertain' is a FAIL. Repair is ONLY extending the clip by whole locked sentences and re-checking, or dropping the MOMENT and repacking; never writing the missing context into the VO. | must-fail corpus >= 40 (steelman, quoting an opponent, sarcasm, a conditional split across sentences, an unresolved pronoun, 'some people say', a stale 'today / just', an answer without its question, a later retraction, false dialogue by sequence, the wrong speaker) AND a must-pass corpus >= 20 with the false-reject rate reported (a checker that rejects everything is a broken selector). Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built. | see Check | law recorded 2026-11-12 02:30; build assigned (pp-selectid phase 2) |
| L-t ALL AUDIENCE-FACING TEXT IS UNDER THE GATES (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): the title, the caption and any on-screen text are free text exactly like the VO: every number, name and claim is audible in a clip of this video; quotes are verbatim; no stronger certainty; the framing verbs destroys / slams / exposes / admits / confirms / caught are banned unless they are the source's own word; no name of a person who does not appear; no second-person financial imperative. ONE title and ONE caption go through VO fidelity and context integrity (L-s) with the video, and are bound into the release authorisation (L-j) with BOTH files: one manifest holds both renders, the title, the caption, the source intervals, the credits and the gate results; any change after the gates re-runs them. | release_auth's attested set grows by the title, caption and manifest; telegram.deliver_run sends that one title and caption. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built. | see Check | law recorded 2026-11-12 02:30; build assigned (pp-selectid phase 2; release_auth wiring by the integrator) |
| L-u HARD EXCLUSIONS AND SCORING (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md; engagement scoring otherwise selects exactly what burns partners): never auto-selected: accusations of crime / fraud / insolvency / dishonesty against a named person or company; one partner attacking another; buy / sell / leverage imperatives and guaranteed-return claims; single-source 'breaking' factual claims; ad reads and sponsor segments; third-party media played inside a partner's video. Down-weighted and capped: price predictions (at most one per video, always framed as that speaker's prediction, never as fact in the title), doom, politics not about Bitcoin policy. 'Named figure' stops being a positive axis on its own; contempt / outrage is a penalty, not a boost. Per-channel fairness: at most ONE clip per channel per video, at most 20 s per source video, per-channel daily and weekly appearance caps (numbers proposed from the saved universes), topic and speaker cooldowns beyond the 24 h moment rule. | exclusions in code, before any score (a rank weight is not an exclusion); the cap numbers come from the saved universes (pp-backtest). Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built. | see Check | law recorded 2026-11-12 02:30; build assigned (pp-selectid phase 2; caps from pp-backtest) |
| L-v SPEAKER AND TRANSCRIPT TRUTH (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): (1) WHO IS SPEAKING: a moment may not span a speaker change; a person is NAMED in VO / title only when verified (title / description metadata, or diarisation above a stated confidence), otherwise the show is credited. (2) every gate today trusts one Whisper transcript: for the selected sentences only, a second independent recognition pass (a different model / settings) runs against the SOURCE audio; any disagreement on a number, a name or a negation makes that token unusable in VO / title or drops the moment. (3) time-sensitive language ('just', 'today', price levels) requires the source's original publish time inside the window; re-uploads are excluded. | the second pass is a GPU0 load (law L-r: through gpu0.swap_to); diarisation confidence threshold stated with its evidence. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built. | see Check | law recorded 2026-11-12 02:30; build assigned (pp-selectid phase 2) |
| L-w OPERATING RULES (orchestrator 2026-11-12 '02:30'; unanimous finding of the four frontier strategy reviewers, /home/ultron/heimdall_probe/pp_redteam/strategy/{claude,gpt,grok47,grok420r}.md): (1) DIVISION OF LABOUR: the local gemma mines and scores by id; CODE does the duration packing (VO length and the credits absorb the slack, so 60-70 s is met by arithmetic, not by the model); a FRONTIER model picks the angle and writes VO / title / caption; a different vendor rules fidelity and context; measured dollars per video are reported. (2) NO ZERO-VIDEO NIGHTS FROM THE CHECKER: on a VO reject, regenerate once, then fall back to a plain factual VO ('Next, <show> on <topic>.') rather than dropping the package; a package is dropped only for a context-integrity or exclusion failure, and then repacked from the next moments. (3) STORY-FIRST IS KEPT as a preferred package TYPE when >= 2 channels cover one development (the safest format); the packager chooses the type. (4) the trend brief runs in SHADOW first (logged, zero weight) next to a free baseline signal from our own corpus (topic frequency across partner channels, last 24 h); when enabled its weight is capped at ~10-15% of the score, its output forced into a closed Bitcoin topic taxonomy, raw post text never enters any prompt, and a person-trend may boost only moments where that person is the speaker. (5) the Telegram approval message carries, per clip, a link to the source video ~30 s before the clip, the flagged risks, both file hashes, the one title and caption. (6) REPORTED NUMBERS: generated, delivered, approved-without-edit, published, rejected with reason, corrected / challenged; not delivered alone. A hold is a selector defect only when the blind oracle's witness package ALSO passes context integrity, exclusions and fidelity; the oracle runs on selector holds only (not ingestion / GPU holds). No integrity rule is ever demoted to ranking without PBX in writing. | amends L-n (the reported numbers; the oracle on selector holds only, its witness under L-s / L-u / VO fidelity) and L-q (story-first kept as a package type). The backtest session is asked separately to compare, on the same saved universes, story-first with bent taste rules vs moments-first vs frontier packaging, blind-judged for publishability. Builder: pipeline_pp_selectid, phase 2 (none of its phase-2 output is DONE without this law); the integrator wires and audits it on DONE. Not yet built. | see Check | law recorded 2026-11-12 02:30; build assigned (pp-selectid phase 2; comparison pp-backtest) |
| L-x NO SINGLE MODEL, ULTRON FIRST (orchestrator note 2026-11-12 '02:45'; PBX: "work this video pipeline to get us off of any one llm and onto ultron and to be fully autonomous and top notch"): every model role (mining, scoring, packaging / angle, VO / title writing, fidelity verdict, context verdict, trend brief) sits behind ONE provider interface with at least two interchangeable back-ends, and the run continues when any one vendor is down or out of credit (OpenAI ran dry mid-run on Nov 12). The DEFAULT back-end of each role is the local model on Ultron wherever it meets the quality bar; a frontier model or Heimdall is used only where a measured comparison shows local is not good enough, and that comparison is re-run so roles migrate to local as it improves. No role hard-codes a vendor or a model name outside the provider config. Generator and blind judge are always different models. | per role, a blind A/B on saved data: local gemma3:27b (run by the integrator under the GPU0 lease, law L-r; the builders provide the harness and prompts) vs frontier vs Heimdall: quality verdict, failures, latency, dollars. Heimdall spend: the 90% tripwire is a NOTIFY ('HEIMDALL SPEND AT 90%' at the top of the session's STATE) and the role falls back to its other back-ends; work never halts for the cap. Not yet built (pp-selectid phase 2 and pp-ingest build behind the interface; the integrator runs the local legs). | see Check | law recorded 2026-11-12 02:45; build assigned (pp-selectid, pp-ingest); A/B per role pending |
| AMENDMENTS 2026-11-12 '02:30': L-n by L-w (6) (reported numbers: generated / delivered / approved-without-edit / published / rejected with reason / corrected or challenged; the blind oracle runs on selector holds only, and a hold is a selector defect only when its witness package also passes L-s, L-u and VO fidelity); L-o by L-s and L-t (context integrity and all audience-facing text join the integrity class; an integrity rule is never demoted to ranking without PBX in writing, L-w (6)); L-q by L-w (3) (story-first is kept as a preferred package type when >= 2 channels cover one development; the packager chooses the type). | see the amended laws | - | recorded |
| Round credit avatars of the channels actually used | G12 (count), G15 (ring aspect, continuity), R6 (credits == EDL channels, unique avatar hashes), shoutout.validate_avatar + registry-only avatars | T: TestD4Credits (yesterday's card fails G12/G15; thumbnail refused; v2f passes) | enforced (3641440f) |
| On-brand transitions between channels only | pipeline/pulse_transitions.plan (different channels only, never at the open, overlap only inside measured non-speech) + concat (frame-locked xfade/acrossfade); G14/G11/loudness gates on the final | T: test_transitions (planner rules; dissolve over silence only; picture and sound of the dissolved-into clip start together; C insert 8 frames < 0.35 s, red line on black) | enforced (Phase 3) |
| Speaker-centred vertical; safe frame only for screen / unidentifiable speaker, flagged | stage `layout` (vertical_layout.classify: SCRFD-10G, sha-pinned; per-shot classes) -> render_vertical.reframe_auto; G4s LAYOUT TRUTH (each shot label = the re-measured majority class; a 9:16 shot is the safe frame iff labelled screen/uncertain, band correlation >= 0.90); G4 per shot (unchanged gate_g4 rules); EDL `vertical_layout`; caption `vertical_layout.layout_note` | T: TestSafeFrameTruth (D5: Yahoo's talking head as safe frame fails), TestLayoutTruth (talking head mislabelled as screen fails, DEC-2), TestCaptionNote, TestStackGeometry, test_pinned auto for every channel status | enforced (Phase 2); caption wired in 4a |
| Sparse VO with 1 s lead-in | G6 pre-roll (onset ≥ 0.95 s), R4 VO ≤ 25 %, M20 editorial gate | existing tests (test_round2_mustfail, test_editorial_gate) | enforced (pre-existing) |
| No brand sting at the open | pulse_transitions.plan never adds anything before the first segment; C is an insert BETWEEN channels only | T: test_transitions TestConcat C timeline starts with the hook at 0.0 | enforced (Phase 3) |
| 1080p (1920x1080 / 1080x1920) | G5 tech (dims, SAR, fps), clip_contract | test_round2_mustfail G5 | enforced (pre-existing) |
| Transcript of the final == intended sentences, word for word | G18 (pipeline/word_diff.py): each clip's first/last two words == its lock's, and its words == the source span's (same ASR, canonicalised numbers/repeats); full diff vs the lock reported | T: test_word_diff (yesterday's clip_01 fails edges + identity, clip_02 fails the start edge) | enforced (4a) |
| The finished video LOOKS right: credits avatars round and the channels used; speakers centred or layout=screen flagged; no letterbox on talking heads; no frozen/black/duplicate frames at joins; watermark present; nothing of the next shot before a transition | verify stage: qa/contact_sheet_<fmt>.jpg (2 s stills, +-3 frames at every boundary, full-resolution credits and 9:16 first frames) + the fixed checklist answered FROM the sheet by the Heimdall vision panel (qwen3.8-27b + nemotron-3.5-super-vl; any no or missing = V1_visual_checklist FAIL = HOLD); supervised sessions also read the sheet themselves (REPORT.md) | T: test_visual_check (verdict rules, sheet contents, live must-fail on yesterday's vertical sheet) | enforced (orchestrator note 06:20) |

## Findings recorded so far (evidence, 2026-11-11)

- **The 1b per-gap model adjudicator was a rubber stamp** (found 2026-11-11 while enumerating the Nov 10 recut windows): gemma3:27b called 19 of 19 Yahoo Finance gaps sentence ends ('the | Wolf', 'of | all', 'is | up'), each with a real 90-770 ms pause, so G16 would have passed mid-sentence cuts in any unpunctuated source. Removed; punctuation now comes from the ASR (E-FAIL-013). With it, Yahoo's window has exactly two cuttable sentence ends ('hack.' 770 ms, 'times.' 350 ms), and the Nov 10 clip_02 start ('of course' | 'of course') is not a sentence start at all.
- D3's third edge (clip_02 out 34.36) is **not** a defect: pause 34.08-34.43 (75 dB deep), the 'I' onset
  is at 34.44; whisper on the prepared clip ends "...many times." The transcript word 'i' 33.92-34.46 is
  a whisper timestamp error. 4 of 6 edges broke the sentence law, not 5.
- D1 is a **source lead-in** problem, not the render: the 'B' onset sits at 85-90 ms in every stage,
  level-identical to the source; the source has 33 ms of codec zero then ~50 ms of room tone.
- D2/D3 root causes: (1) `_download_window` requested `*54-100` but recorded offset 53.57 (and 23 vs
  23.38): every canonical->file time was shifted 0.38-0.52 s; (2) `_find_word_boundaries` picked the
  nearest word, not a sentence start; (3) the ±2 s snap + edge-word recompute (ad7295ea/4cf5a31a)
  validated whatever the moved cut contained; (4) R9/R10 never ran in production (validate_edl was
  called without transcripts; R10 is advisory and always returns True).
- D4 root cause: shoutout._fetch_avatar_on_demand fell back to the 1280x720 VIDEO thumbnail; the frozen
  renderer resizes every avatar to a square. G12/G15 caught it; the QA_GATE_HOLD reclassification was
  wrong. 70 of 75 registry channels had no verified avatar.
- cut_accept (unchanged) uses a fixed speech-25 dB quiet line: on music-bedded sources (DataDash, bed
  ~24 dB under speech) it reads the bed as speech, so the Nov 10 hook's out edge can satisfy either the
  80 ms tail rule or cut_accept, never both -> that window is rejected (fail closed), not forced.

## Decisions (orchestrator, delegated by PBX 2026-11-11)

Received 02:50 ET. Recorded verbatim in substance; implementation status tracked above and below.

- **DEC-1 Reference calibration.** PBX's approved v2f (16:9 and 9:16) is by definition passing (Law 22).
  For any gate the frozen v2f reference outputs FAIL today: show measured vs threshold on the reference,
  then set that gate's threshold to exactly the reference's measured worst value (no extra margin), in a
  named constant citing the reference file and measurement, plus a test asserting the reference passes
  and a must-fail fixture just beyond it. The ONLY permitted change to gate acceptance; only for gates
  the approved reference fails; audited. Each calibrated gate, old and new value, listed here.
- **DEC-2 Screen-share hooks allowed.** Deterministic layout class "screen" (largest detected face under
  a fixed fraction of frame area across samples, or no face), recorded in the EDL. G4 as written for
  talking-head layouts; for "screen": content is the shared screen, vertical uses the wide safe frame,
  caption/EDL say layout=screen. Must-fail test: a talking-head clip mislabelled as screen.
- **DEC-3 Soft cameras.** Covered by DEC-1 if the reference is equally soft; otherwise prefer the sharper
  window when two legal windows score within 0.5; do not reject a clip for source softness alone when
  render/source sharpness ratio >= 0.85.
- **DEC-4 Transition default.** Sentence-aligned cuts with a 6-frame cross-dissolve and matching audio
  crossfade between segments from different channels (variant B without the thump). Still build A, B
  (soft pulse) and C (red pulse-line wipe) once on the corrected Nov 10 cut; send the three to Telegram
  labelled as options; do not block on the answer.
- **DEC-5 Vertical.** Speaker-centred reframe default; stacked bands for 2-3 person layouts; safe frame
  only for layout=screen or when the speaker cannot be identified, flagged in EDL and caption.
- **DEC-6 Sources.** Approved partner channels only (the pipeline/channels.json registry). No guest
  sources until the radar exists.
- **DEC-7 Credits rings.** The gate was right; fix the render.
- **DEC-8 Done means:** (a) the corrected Nov 10 story passes every gate with no waiver and its transcript
  diff is exact; (b) THREE fresh stories in a row via one command (run_fresh.py, auto mode, no pinned
  file, no hand step) at one identical git HEAD, each passing every gate, each delivered to Telegram as
  "HOLD FOR APPROVAL - all gates passed, no waivers"; (c) docs/RUNBOOK_PULSE_CHECK.md; (d) a cron-ready
  wrapper scripts/pulse_check_run.sh (flock, logging, pipeline_ tmux-safe), NOT installed in cron. A HOLD
  for "no producible story" is valid only with a full rejection ledger; it neither counts nor resets. A
  HOLD from a pipeline defect: fix, audit, the count restarts.
- **DEC-9 Stories.** The engine's own top Bitcoin story each time, runs >= 3 hours apart or on different
  story universes so they are genuinely different stories.
- **DEC-10 Edge timing (orchestrator 10:35 ET).** The sentence law's TIMING constants are calibrated to the
  approved v2f reference and to what a listener hears, not to a silence quota (the 80 ms lead / tail /
  pause minimums of the 01:50 order were picked without evidence). (a) Measure on frozen v2f, both formats,
  every segment edge: the source gap between the kept edge word and its neighbour, the rendered lead before
  the first onset and tail after the last offset, the edge-word duration ratio; table here. (b) PAUSE_MIN_S,
  LEAD_MIN_S, TAIL_MIN_S = the reference's measured worst (named constants citing the measurement), DEC-1
  mechanism + audit; must-pass: every v2f edge. (c) Stays strict: (i) first/last word >= 85 % of its
  transcript duration in the render; (ii) NO audible part of the neighbour word in the kept lead/tail
  (neighbour energy below the valley threshold; the cut at the envelope minimum between the two words);
  (iii) sentence-complete first/last word locked at selection; (iv) G18 word-for-word. Yesterday's three
  defects (half "Bitcoin", Natalie into "All right, you've probably seen people celebrating", a clip
  starting on "81") must still FAIL. (d) A short inter-sentence gap: cut at the envelope minimum with a
  2-frame audio fade in/out instead of rejecting; reject for edges only if (i)-(iii) cannot be met. (e)
  Re-run the Nov 10 lineup: expected hook DataDash 0.00-9.10, clip Natalie "It went from above 81,000 ...
  this week.", clip Yahoo from the true start of the "bitcoin dropped pretty massively" sentence to "...many
  times."; report the exact failing measurement for any that still fails. (f) Render, all gates, sheets,
  Telegram ONLY on a clean pass, plus options A/B/C. TIME BOX 13:00 ET: then write what blocked it and go to
  4b on a fresh story with the same code.

- **DEC-11 Credits rings (orchestrator 13:15 ET).** G12 / G15 measure the ring the renderer draws (brand-red
  mask at the card layout; ellipse fitted to that mask; aspect tolerance and count rule unchanged). Must-fail
  yesterday's card; must-pass v2f and the Nov 11 four-avatar card. Implemented af5447c6 (+ registered-avatar
  disc check, because yesterday's rings are round and its defect was the squashed avatars).
- **DEC-12 (orchestrator 14:45 ET): the parked gate items decided; one audited batch with tests, then 4b.**
  In every case the gate keeps its purpose and its must-fail tests; what changes is an instrument error or
  the render. (a) G9 floor per format = v2f's measured value minus the MEASURED re-encode spread (encode the
  locked outro through the final-encode path 5 times, max - min, rounded up, 0.05 at most); named constants
  citing both; outro_locked stays the hard row; must-fail: a tail that is not the locked outro, a tail 1.0
  luma away. (b) Every MACHINE-cut segment gets a 2-frame (83 ms) fade-out ending at cut_out and a 2-frame
  fade-in from cut_in, inside the kept lead / tail so the edge words keep >= 85 % (G17); human-approved PINs
  untouched (Law 22: prove v2f identical); a tail still failing G3c with the fade is reported with numbers.
  (c) G3c head onset on abutting words: try the 12b fade, then a sentence-legal earlier / later start for the
  same statement, then the next-ranked legal window; never ship a failing head. (d) G10: a segment failing G10
  is replaced by the next-ranked legal window (a 4th segment is optional: dropping it is allowed); record
  has_chyron per channel in the registry so selection knows before render. (e) G14 samples only where the
  transcript has speech (a word within +-0.25 s) and outside declared transition / VO-freeze intervals; an
  inconclusive sample is re-taken at the nearest speech point in the same segment; a segment passes with >= 3
  conclusive matching samples and zero conclusive mismatches; must-fail: a real 2-frame AV slip; < 3
  conclusive samples = HOLD; threshold unchanged. (f) G3b decodes the tail three times with 1.5 s of leading
  context and takes the majority; the expected last word must be in the majority; must-fail: yesterday's
  Natalie tail ("...celebrating") and a tail cut mid-word. The 9:16 colour-tag fix (36e769d0) stands.
  Before the batch: send PBX a PREVIEW of runs/pinned_20261111_172202_replay_cut1329 (small top-left
  "PREVIEW" tag on copies; both formats + both contact sheets; the given caption); log message ids here.
  After the batch: replay the Nov 10 cut once; if clean send "HOLD FOR APPROVAL - all gates passed, no
  waivers" with transition options A/B/C; then 4b.

- **ORDER 15:30 + PBX ADDENDUM 15:35 (2026-11-11).** PBX approved the preview; lock it (L-d); fix the two
  defects he named (sign-off named 3 of 4 channels -> L-a + G20; Natalie's 'rally' clipped by the fade ->
  DEC-12b AMENDED: L-b, G17c, L-c); then a fresh story today. PBX standing rule: an obvious correction is
  applied and written into the laws (gospel, PIPELINE_LAWS LAW 26, this doc, the bible) in the same batch,
  each law one plain sentence plus its check; only publishing and installing the schedule wait for him.
  L-a SIGN-OFF NAMES ALL: the sign-off voiceover names every channel on the credits card, and the spoken set, the card set and the clips used are identical.
  L-b EDGE WORDS WHOLE: a fade never overlaps an edge word: the first and last word of every clip are heard whole, at full level, with their natural decay.
  L-c DISSENT IS RIGHT UNTIL DISPROVED: a check that disagrees with the others on an edge word is treated as right until an acoustic comparison against the source proves otherwise.
  L-d PROTECTED PREVIEW: the PBX-approved preview of 2026-11-11 is a protected reference.

- **DEC-13 (orchestrator 2026-11-11 18:00).** Candidates come from the channels' own conversation first
  (emergent clusters, >= 2 independent channels, last 48 h, 72 h max; the claim from the shared statements,
  quotes attached); wire headlines only name / date / enrich or stand after every cluster is exhausted; the
  same-event merge before the coverage count every run; a Bitcoin screen before any model call; a per-cluster
  ledger; reuse of universe, transcripts, embeddings and verdicts. Rule unchanged: the same-event verifier,
  MIN_COVERAGE_CHANNELS 2, hook >= 4.0, stand-alone, topic and sentence laws. Laws added with it:
  L-e PUNCTUATED BEFORE READ: every word transcript the sentence law reads, the editorial word pass included, has its sentence punctuation restored from a prompted second decode of the same audio before any sentence is read.
  L-f CHANNELS FIRST (DEC-13): story candidates come from the channels' own conversation first: clusters of statements by at least two independent channels, screened for Bitcoin before any model call, with the claim written from their shared statements and their quotes attached; wire headlines are evaluated only after every cluster is exhausted.

### DEC-10a — v2f edge timing, measured (2026-11-11 10:45, sentence_law's own level/onset functions)

Source (runs/v2f_20261111_103004 sources/transcripts/cuts; valley threshold = local speech - 12 dB):
| segment | edge | kept word / neighbour | acoustic gap | longest quiet run | kept (lead / tail) | cut to neighbour |
|---|---|---|---|---|---|---|
| hook | in (file head) | "The" | - | 70 ms | 70 ms | - |
| hook | out | "Today," / "I'm" | 240 ms | 10 ms | 160 ms | 80 ms |
| clip_01 | in | "The" / "Yeah." | 30 ms | 30 ms | 40 ms | -10 ms (cut inside "Yeah."'s decay) |
| clip_01 | out | "magnitude." / "So" | 60 ms | 10 ms | 20 ms | 40 ms |
| clip_02 | in | "One" / "approximately." | -10 ms (abutting) | 0 ms | 0 ms | -10 ms |
| clip_02 | out | "Now," / "10" | 330 ms | 300 ms | 210 ms | 120 ms |
| clip_03 | in | "prison" / "a" (mid-sentence) | 280 ms | 230 ms | 190 ms | 90 ms |
| clip_03 | out | "have." / "It's" | 440 ms | 360 ms | 10 ms | 430 ms |
Prepared clips (G17a): lead 40 / 40 / 0 / 190 ms, tail 150 / 40 / 190 / 0 ms. Edge-word ratio (G17b): PASS
(>= 0.85) on every edge (1f). => worst: pause 0 ms, lead 0 ms, tail 0-10 ms, gap -10 ms: the timing
minimums calibrate to 0; DEC-10 (c)(i)-(iv) carry the protection.
Conflict recorded: v2f's hook (file head, 70 ms genuine quiet in the source, 40 ms in the prepared clip, no
pad) and yesterday's D1 hook (file head, 60 ms, no pad: "half Bitcoin") are on the same side of any lead
threshold, and G17b passes yesterday's render; so D1 keeps failing on the FILE-HEAD pad rule
(HEAD_LEAD_MIN_S = 80 ms, separate constant; the D1 fix PBX heard) and v2f's hook head is the one approved
edge that rule fails (as recorded in 1f / OD-2). Every other v2f edge must pass.
G5 note for DEC-10e: hook 9.08 s + 0.25 s pad + Natalie (as written: 5 sentences, 16.76 s) + Yahoo 18.70 s
= 44.8 s of content; with the credits card (~9.0 s) and the outro (4.46 s) ~58.3 s < G5's 60 s.

### Calibrated gates (DEC-1)

| gate | constant (segment_v1/qa_gates.py) | old value | new value (= v2f measured worst, per format) | reference measurement | commit |
|---|---|---|---|---|---|
| G3c acoustic tail | G3C_VALLEY_DEPTH_DB | 12.0 dB | 16:9 11.63, 9:16 11.65 | strictest depth at which the v2f hook tail passes: 11.6301 / 11.6543 | DEC-1 commit |
| G5 true peak | G5_TRUE_PEAK_MAX_DBFS | -2.0 dBFS | 16:9 -2.0 (unchanged, passed at -2.2), 9:16 -1.3 | segment_vertical.mp4 ebur128 true peak -1.3 | DEC-1 commit |
| G8 sharpness floor | G8_SHARPNESS_FLOOR | 60 | 16:9 27.56, 9:16 10.84 | worst segment medians: 16:9 hook 27.56, 9:16 clip_03 10.84 | DEC-1 commit |
| G9 tail luma | G9_LUMA_FLOOR | 20 (strict >) | 16:9 14.33, 9:16 14.77 (strict > kept) | 14.3357 / 14.7715 (locked outro ends on black) | DEC-1 commit |

Also in the DEC-1 commit (measurement wiring, not acceptance): G8 was never given source clips in
production, so it ALWAYS failed "no_source" and was waived as FLAG. It now gets the prepared clips
(16:9) and the reframed vertical clips (9:16) - the reference then fails only the floor, which is what
was calibrated. DEC-3 (soft source judged by render/source ratio >= 0.85 alone) is inside gate_g8.
The G8 FLAG and the G9 "approved known exception" rows are gone (DEC-8: no waivers).

## L-r GPU0 PATHS (law L-r item 1: every code path that loads anything on GPU0, by grep, 2026-11-12; file:line at the L-r commit)

| path | loads | file:line | wired |
|---|---|---|---|
| run wrapper | the GPU0 lease for the whole run (fd 8; preflight and run_fresh inherit it) | scripts/pulse_check_run.sh:78 | YES (lease) |
| run_fresh | the lease (custody of fd 8, else its own) to the end of main; foreign process at the start = HOLD; per-stage peak sampler | pipeline/run_fresh.py:287 (stage_env) | YES |
| replay | the lease + sampler for a replayed tail | pipeline/replay.py:79 | YES |
| preflight | the lease; the editorial model check through swap_to with keep_alive 0; GPU0 asserted left as found (row gpu0_left) | pipeline/preflight.py:67, :177 | YES |
| backtest | the lease for the whole backtest | pipeline/backtest.py:216 | YES |
| pytest GPU sessions | the lease for the session (CPU sessions take nothing and cannot load) | pipeline/conftest.py:24 | YES |
| requirement measurement | the lease; children inherit it | pipeline/measure_gpu0.py | YES |
| Ollama gemma3:27b (editorial, review, backtest) | swap_to('ollama:gemma3:27b') before a request whenever GPU0's resident set moved; an Ollama out-of-memory leaves as GpuOOM | pipeline/story_semantics.py:198 (LocalLLM._post) | YES |
| Ollama gemma3:27b (preflight check) | swap_to + keep_alive 0 | pipeline/preflight.py:67 | YES |
| Embedder (bge-base fp16) | gpu0.model('embedder'): loaded through swap_to, encode inside guard | pipeline/story_semantics.py:80 | YES |
| Whisper word-pass release | swap_to('whisper:large-v3:batched') | pipeline/story_semantics.py:320 | YES |
| Whisper distil-large-v3 / large-v3 batched (word pass, punctuation reference) | gpu0.whisper(name, batched=True) | pipeline/transcript_store.py:316 | YES |
| Whisper large-v3 (pinned acquire / select) | gpu0.whisper('large-v3'); a raw out-of-memory re-raised, never 'transcription failed' | pipeline/select_passages.py:91 | YES |
| Whisper large-v3 (cut acceptance, edge words) | gpu0.whisper('large-v3') | pipeline/cut_accept.py:158 | YES |
| Whisper large-v3 (G16 / G18) | gpu0.whisper(ASR model) | pipeline/word_diff.py:74 | YES |
| Whisper medium (G1 / G3b / G17b / G20) | gpu0.whisper('medium') | segment_v1/qa_gates.py:64 | YES |
| resemblyzer (G1 voice identity) | gpu0.model('resemblyzer') | segment_v1/qa_gates.py:154 | YES |
| stage-level Whisper swaps | free_gpu0_for_whisper -> swap_to | pipeline/run_fresh.py:327 (pinned), :666 (prepare), :864 (gates) | YES |
| NVENC (h264_nvenc ffmpeg) | swap_to('nvenc') at the top of each of the 18 functions that encode: config.conform_outro :139; render16.render_vo_visual :58, apply_watermark_alpha :199, render_16x9 :231; run_isolated.prerender_clips (a protected file, Law 22: swapped at its one caller, run_fresh.stage_prepare's prerender_clips wrapper; run_isolated's own legacy main is not wired); pulse_transitions.render_wipe :155, concat :187; render_vertical.reframe_fixed_crop :68, reframe_stack2 :141, reframe_grid :211, reframe_single :280, reframe_letterbox :322, reframe_auto :409, render_vo_visual_vert :444, apply_watermark_alpha_vert :641, render_9x16 :678; shot_snap.apply :52; sentence_law.apply_lead_in_pad :817; an NVENC out-of-memory in the outro conform is re-raised, never a fallback (render16 / render_vertical _find_outro) | pipeline/*.py as listed | YES |
| face detector (SCRFD) | onnxruntime CPUExecutionProvider on purpose | pipeline/face_scrfd.py:34 | NOT GPU0 (CPU) |
| mediapipe face crops | mediapipe tasks, default CPU delegate (no GPU delegate set) | pipeline/render_vertical.py (reframe_fixed_crop) | NOT GPU0 (CPU) |
| vision checklist (V1) | Heimdall gateway API (remote models) | pipeline/visual_check.py:23-25 | NOT GPU0 (remote) |
| VO | ElevenLabs API | pipeline/vo.py | NOT GPU0 (remote) |
| legacy segment_v1 renderers / transcribers (tracked): render_v10, render_v10_vertical, render_v11, render_v11_vertical, render_v12, render_v12_vertical, render_v15_vertical, render_v16_vertical, render_v17_vertical, render_v4_pbx, render_vo_visual, transcode_and_transcribe, transcribe, transcribe_chunked_5rip, transcribe_final, transcribe_v2, transcribe_v3 | Whisper / NVENC / mediapipe directly | segment_v1/*.py | NOT WIRED: imported by no entry point (run_fresh, preflight, replay, backtest); running one by hand is a GPU0 load without the lease. Flagged (K2), not deleted: proposal to retire them to an attic, for the orchestrator |
| systems outside the Pulse Check pipeline on this host: video_pipeline_v3 (daily_producer, assembler_common, channel_scanner, utils/live_monitor, utils/channel_daemon, voices/*), services (video_engine/local_whisper, video_engine/shorts_creator, clip_service, video_analyst, viralmoments, viral_agent, medley_assembler, kokoro_tts_daemon), spaces_scraper/transcriber, medley_director, overnight_render_loop, medley_engine, gen/LTX-2, the oracle avatar service (GPU1, protected) | GPU work of other products | various | NOT WIRED (outside this pipeline): on GPU0 during a run they are FOREIGN (item 4): the run HOLDs at its start or before the next swap, naming pid / name / MiB; nothing is killed |
