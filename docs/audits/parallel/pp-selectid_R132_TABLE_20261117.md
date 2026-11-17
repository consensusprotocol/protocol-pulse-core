# RULING 132: THE END-TO-END REPLAY, ONE TABLE (the builder's merge of both halves)

Sources: the selection side, mine (pp-selectid_R132_SELECTION_SIDE_20261117.md in this folder, written 08:48 ET, $0.00);
the render side, the integrator's (main tree docs/audits/R132_REPLAY_RENDER_SIDE.md, commit 238cfea2, written 09:47 ET,
$0.00). FREE ONLY on both sides: cached outside answers, GPUs and Heimdall; no outside call was made.

As ruled, two rules were ignored: the 12-hour age rule (rulings 76/77) and the registry's never-re-form rule (ruling 66).
- Novelty (L-p) is read as never delivered.
- L-v 3, the 24 h recency of time-sensitive sources, is NOT an age rule ruling 132 named.
  - The selection side judged it at each package's own build clock ("as if new today"): PASS for all.
  - The render side did not re-run its stage-pinned check (the integrator's row 9).
  - Treated as new today, it passes by construction. Marked so below; rule otherwise and it is re-run.

Cells: P PASS, R REFUSE (why), U UNTESTED (why), - n/a, I ignored as ruled, ~ still running, x3 = every segment.
Columns: 0c68b589 (published), 41f29b1f (published), 37c5b5f5 (review), 3f481f5a (PBX posted it), B114 (build 114's
line-up, never approved: 4d14201f, 185e37a6, d6adeb54, 93cfa865).

## THE TABLE, in today's pipeline order

| # | Gate (ruling) | 0c68b589 | 41f29b1f | 37c5b5f5 | 3f481f5a | B114 |
|---|---|---|---|---|---|---|
| 1 | Ledger adapter: the approved span is a moment today | P | R: 3.5 s hook inside a passage | R: approved spans not ledger moments | P | P |
| 2 | Ruling 104 tail variants | P | P | P | P | P |
| 3 | usable: L-u, exclusion, opt-out, 20 s/source, L-v 1, L-v 3 at its own clock (age I) | P | P | P | P | P |
| 4 | Ruling 53, a re-posted speech once | P | P | P | P | P |
| 5 | Rulings 56/60/33/94 (a): clip scorer, STAND_ALONE opener, topic | P | P | P | P | P |
| 6 | Exclusion's free part (ad-read) | P | P | P | P | P |
| S1-S2 | Spotlight pool/snap/opener; ALONE >= 4 (ruling 90) | - | - | - | P; U: no scorer verdict | - |
| 7 | Ruling 109: 3 channels after the free stages | P | P | P | - | P |
| 8 | Step A first screen (58/85/101/102/126 (1)/127 (2)) | P | U: no cached verdict | U: no cached verdict | P | P |
| 9 | 3 channels cleared step A | P | U | U | - | P |
| 10 | L-v 2 second recognition + CUTTABLE | P | U: audio not on disk | U: audio not on disk | P | P |
| 11 | G17a hook onset; ruling 33 (a) | P | U | U | P | P |
| 12 | Hook eligibility + the render's STAND_ALONE hook rule | P | P | P | P | P |
| 13 | Rulings 59/61/115: the calibrated hook bar | U: prompt changed | U: never rated | U: never rated | U: no cached rating | P (3/5/4) |
| 14 | Rulings 70/93/123 (2): the hook's frames | U: never seen | U | U | U: visual-2 cached, today visual-3 | P |
| 15 | Second screen (82/102/127) | P | U | U | P | P |
| S4 | Spotlight source test (ruling 92) | - | - | - | U: needs row 14 | - |
| 16 | 3 channels after the second screen | P | U | U | - | P |
| 17 | Angle writer (a write) | - | - | - | - | - |
| 18 | Ruling 117 join table | U: no cached joins | U | U | - | P (1 of 3 flagged) |
| 19 | Line-up rules (L-u/L-y 4, price cap, seconds, STAND_ALONE) | P (39.3 s) | R: two price-prediction clips, cap one | R: 21.5 s clips, needs 36.7 | - | P (37.9 s) |
| 20 | Ruling 66 registry, never re-formed | I | I | I | I | I |
| 21 | Ruling 116 clips-alone verdict | U: hook slot unrated (clips 4/4) | U | U | - | P (3/5/3/4) |
| 22 | Ruling 37, a question hook | P | P | P | - | P |
| 23a | Lock: r17 / L-v 2, a number, name or negation differs | P x3 | P x3 | P x3 | P | P x4 |
| 23b | Lock: r17, r18, r84 (b), r131 (A)/(B) | P x3 | P x3 (r18; Sjb6 r131 (B) currency) | P x3 (r18) | P | P x4 (d6adeb54 r131 (A); 93cfa865 r131 (B)) |
| 23c | Lock: r72/r84, the second recogniser | U: no cached reading | P c1JG; U hook, Sjb6 | P c1JG; U hook, wdk5 | SPLIT: one reading R "401k"/"401" | P x4 (d6adeb54 adopts one "uh") |
| 23d | Lock: r103 re-listen; r105 readings across passes | - | - | - | U: needs a new paid reading | - |
| 23e | Lock: r131 (A) sealed text re-locked; r73 (c) cut placement; E-FAIL-052 acquire | P x3 | P x3 | P x3 | P | P x4 |
| 23f | L-v 3 24 h recency at stage pinned (render side not re-run) | P as if new | P as if new | P as if new | P as if new | P as if new |
| 24 | Rulings 70/93: every clip's frames | U: never seen | U | U | (row 14) | P (flags only) |
| 25 | Exclusion verdict | P (recorded) | P (recorded) | P (recorded) | P (recorded) | P (recorded) |
| 26 | The writes (a write, not a gate) | - | - | - | - | - |
| 27 | Cheap line gates: fidelity rules, runtime, R4, L-y shape, house style, recency | P (61.8 s) | R: six house-style faults (own lines) | U: VO-led, no L-y form | R: caption calls speaker "guest" | - |
| 28 | Ruling 91 value verdict | U: none recorded | U | U | U | - |
| 29 | VO fidelity verdict | U | P (recorded) | U | U | - |
| 30 | Context integrity | P (recorded) | P (recorded) | U | U | - |
| 31 | Coherence: the free panel (118 (2)/130 (4)) | U: panel never asked | U | U | - | - |
| 32 | The seal (every required row PASS) | follows the U rows | follows rows 1, 19, 27 | follows rows 1, 19 | follows row 27 | not reached (23, last night) |
| R1 | Pin record at the render (check_pin_only: seal, schema, formats, bar marks, VO) | R: sealed r70/r91 rows absent * | R: five later rows absent * | R: sealed r91 row absent * | P | U: never sealed |
| R2 | edl_rules R1-R11 | P | P | R: R11 L-y, two VO lines | P | U |
| R3 | r91 takeaway value (sealed verdict) | R: no sealed value verdict * | R: same * | R: same * | P | U |
| R4 | Editorial law gate (laws 1-4) | P | P | P | P | U |
| R5 | Stand-alone + floor (33/34/60/94/119/120) | P | P | P | P | U |
| R6 | Layout compatibility; v2f guard | P | P | P | P | U |
| R7 | Cut acceptance; G16 before the render | P (original) | P (original) | P (original) | P (original) | U |
| R8 | Voice; prepare, layout, render | original run | original | original | original | U |
| R9 | REQUIRED gate rows (G3b ... G20, 9:16 fallback), today's code on the final | ~ running | ~ running (original: G20, G8/G9 9:16 held) | ~ running (original: G18, G3c held) | P every row, both formats | U |
| R10 | V1 vision checklist (two Heimdall models) | ~ running | ~ running | ~ running | R: 9:16 "watermark" row, one model | U |
| R11 | Attestation, authorisation, Telegram | delivered Nov 13 | never reached | never reached | never reached | U |

\* The row did not exist when the package was sealed (visual r70, takeaway value r91, house style, hook onset,
stand-alone came later); re-formed today these are the builder's rows 13-14, 24, 28 (UNTESTED there: no cached answer
for today's prompts).

## EVERY REFUSAL OF A PBX-APPROVED PACKAGE, AND THE RECOMMENDED CALIBRATED FIX (nothing changes without your ruling)

1. **Row 19, the price-prediction cap (41f29b1f).**
   - Today's miner tags two clips: What Bitcoin Did ("price-wise ... tends to do pretty well", no figure) and Stephan Livera ("$1.5, $1.4 million per Bitcoin").
   - FIX: count a clip toward the cap only when its own words state a price figure (a number with a currency or price unit, a multiple, "zeros").
   - PASSES 41f29b1f.
   - STILL REFUSES two clips that each state a price in one line-up.
   - Measured: 243 of 372 tagged ledger moments state no figure, so they would leave the count.
2. **Row 1, the ledger adapter's spans (41f29b1f's 3.5 s hook; 37c5b5f5's cuts).** Supply, not a bar: the ledger mines whole passages.
   - FIX (a new free variant, needs a ruling): a head-side sentence variant, the moment without its leading sentence(s) when the parent cannot open, the mirror of ruling 104's tail variant. Every gate runs again on it.
   - FORMS 41f29b1f's and 37c5b5f5's hooks.
   - STILL REFUSES any cut off a sentence edge.
3. **Rows 19 / R2, the medley seconds and L-y (37c5b5f5).** It is the older VO-led shape, and L-y is PBX's own verdict on this very video ("you added too much voiceover").
   - FIX: none.
4. **Row 27, house style (41f29b1f) and the ROLE rule (3f481f5a's caption "guest").** Both rules came after PBX approved; the line is rewritten and the clips are kept.
   - FIX: none.
5. **Rows R1 / R3, the sealed-row gap (0c68b589, 41f29b1f, 37c5b5f5).** The rows postdate the packages.
   - FIX: none.
6. **Row R10, V1 "watermark_present" (3f481f5a; it held the Nov 15 run too).** The question does not say WHOSE mark: one model judged the source's, the other ours.
   - FIX (integrator): name the mark ("the Protocol Pulse red pulse-line logo in the lower-right corner").
   - PASSES 3f481f5a.
   - STILL REFUSES a final whose own logo is missing or covered.
7. **Row 23c, two cached Scribe readings of one window disagree on "401k" (3f481f5a).**
   - FIX (integrator): key ruling 105's history by window (video, window, download offset), not by bytes, as batch 101 does for reuse.
   - PASSES 3f481f5a.
   - STILL REFUSES a token every reading disputes.
8. **Pending:** rows R9-R10 for 0c68b589, 41f29b1f and 37c5b5f5 are still running on the integrator's side; they are added when they land.
9. **Found on the way (no approved package refused by it):** pinned._token_word fails closed on a span holding a multi-word number ("2 billion"), so ONE function-word split there holds.
   - FIX (integrator): locate the word through canon.canon_spans.
   - STILL REFUSES two such splits (ruling 84 (b)).

## EVERY REMAINING WAY A FULLY PASSING LINE-UP CAN STILL MISS PBX's TELEGRAM, AND ITS GUARD (one line each)

Selection side (the builder):
- S1 Spend guard: a paid call that does not fit raises SpendLimit (no failover). Guard: ruling 131's fit check before the first paid call; `start_refused`; the router's stop is the day's cap LESS the Scribe it never sees.
- S2 Vision reserve (0.6 of list, about $0.178 a call, one call per unseen moment, the clips' calls at once). Guard: the same fit check (r131/fit131.py); the over-held tripwire.
- S3 Search and package budgets (ruling 41 / 5): a stop mid-writes leaves a "budget" candidate. Guard: the registry retries open candidates first.
- S4 Registry closure (ruling 66): a line-up closed by a gate is never re-formed, even after a ruling changes that gate (build 114 under ruling 131). Guard: NONE automatic. PROPOSED: a ruling that changes a gate re-opens the candidates it closed (by hand, `--from-candidate`).
- S5 Expiry (12 h): a line-up found late can expire before or during the render. Guard: fresher line-ups rank first (ruling 57); the seal checks the window; render-time expiry is not re-checked (render side R15).
- S6 Grok-only verdicts (hook, joins, clips-alone): Grok down means no rating, so no hook (law L-m). Guard: the next build only.
- S7 Heimdall down or slow: the second screen HOLDS the moment (ruling 102). Guard: a held moment is retried next build.
- S8 The lock pre-check left off (scratch default, for Scribe dollars). Guard: ruling 131's attempt order runs it first with `--lock-precheck on`.
- S9 Nothing new (ruling 107): a same-fingerprint build asks no model. Guard: a build that left open work never stands in for a later one.
- S10 The stand-alone SCORER down (it was, 15:26 ET Nov 16 to 09:46 ET Nov 17): moments needing a verdict fail closed (34 moments and 25 trim variants refused for that alone in every whole-pool build from 18:24 ET to 21:00 ET Nov 16; build records are named in UTC). Guard: the integrator's restart loop and batch 102; NEW on my side: the build line flags SCORER STALE when my candidates wait unscored over an hour.
- S11 Word pass: a moment without a sentence-ready word record is not in the pool. Guard: the watcher fires on newly word-ready moments.
- S12 The seal (gate inventory, replayed flags): refused at write. Guard: recorded, never a pass; the build line names the row.
- S13 A build during a render, or two at once. Guard: build_and_record refuses both.
- S14 A question on line 1 holding a build. Guard: ruling 123's 20-minute default.

Render side (the integrator, its file's items 1-16, one line each):
- R1 A yielded transcript pass holding GPU0 (killed the scorer at 15:26 ET Nov 16). Guard: batch 102, where the pass ends when it yields and services survive a Gpu0Stop.
- R2 The render lock held by another run (exit 75, nothing queues). Guard: the next attempt.
- R3 The GPU0 lease held by a service batch (exit 75). Guard: per-batch leases; the launcher can retry.
- R4 The source pulled, or yt-dlp failing at render. Guard: the pre-check downloaded the same window that day.
- R5 The render's decode or Scribe disagreeing with the pre-check's. Guard: one code path (the decoder-sha lockstep); recogniser non-determinism is fix 7 above.
- R6 Scribe, ElevenLabs or Ollama down mid-run. Guard: preflight checks Ollama and the ElevenLabs quota, NOT Scribe or Heimdall.
- R7 Heimdall down, or a vision model saying no (V1). Guard: NONE in preflight. PROPOSED: a Heimdall probe in preflight; fix 6.
- R8 The stand-alone floor switched off by a scorer_sha change. Guard: the sha is bound to the floor; lockstep changes only.
- R9 A commit to pipeline/scripts/segment_v1 during a render (attestation fails). Guard: E-FAIL-078; the render-lock check before every commit.
- R10 The channel registry edited after attestation, or a credited channel without a handle or url. Guard: the registry sha bound at authorise.
- R11 An attested or bound file changing (exit 70). Guard: the snapshot re-hash.
- R12 Telegram refusing, or an unknown outcome. Guard: TELEGRAM_DELIVERY.json, reconciled by hand.
- R13 A final over 49 MB, a kit over 4096 characters, or a headline number not heard. Guard: the plan's checks STOP before sending.
- R14 Spend at render (none of its own before today). Guard: batch 101's day ledger; TTS UNPRICED until you rule its rate.
- R15 Ageing during the render (12 h not re-checked; L-v 3 checked once at stage pinned). Guard: none needed (nothing refused mid-render).
- R16 The session watchdog blind to a dead service in a live tmux session (missed the scorer for 18 h). Guard: NONE yet. PROPOSED: the watchdog checks each service's process.
