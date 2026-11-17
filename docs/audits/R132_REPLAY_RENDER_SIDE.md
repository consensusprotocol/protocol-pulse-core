# RULING 132: THE END-TO-END REPLAY, RENDER SIDE (integrator's half)

**Written 09:47 ET Nov 17; updated as the last replays finish (see "Running").**

The builder merges this half into the one table on its STATE line 1.

## How this was run

**The code.** TODAY's pipeline: main at 5af2206b, with ruling 131 (A)/(B) (batch 100) and batch 101 (the day ledger and the Scribe reuse).

**FREE ONLY.** Nothing was paid: the outside-spend ledger has no line from this replay. What was used:
- GPU0 decodes;
- the local scorer;
- Heimdall vision;
- cached outside answers only. The second recogniser was read only from a cached reading of the same window. With none cached, the gate is marked UNTESTED.

**Ignored as ruled:** the 12-hour age rule and the registry's never-re-form rule. **Also ignored, and I am saying so:** L-v 3's 24 h recency of time-sensitive sources (stage pinned). It is an age rule of the same kind and would refuse every package here for its age alone. Rule that it applies and I will mark those cells.

**How each block was replayed:**
- **Lock gates (rulings 72 onward, the pin stage, which runs the render's own lock code):**
  - The pre-check's own code ran in a scratch root, never the live results the builder reads, on fresh downloads and decodes of each window.
  - Second readings came from the live cache. For c1JGheQBPH4 the cached reading is pipeline/fixtures/ruling17/c1JGheQBPH4.scribe.json: scribe_v1, paid Nov 12, the same window at the same offset of 2388.0.
- **Validate:** run_fresh.stage_validate on a copy of each run's EDL.
- **Gates + verify:** pipeline/replay.py --from gates, which runs today's gate code on each run's own final. The renders themselves were NOT re-made, so the voice, prepare, layout and render rows are the original runs'. A full re-render is about 50 min of GPU0 per package, plus TTS and sign-off calls that cost outside dollars.
- **build 114** was never sealed: it was held at the lock last night. Its moments have since expired and the registry has closed the line-up (the builder). Only its lock rows can be replayed.

## THE TABLE (render side, in pipeline order)

Cells are PASS / REFUSE (why) / UNTESTED (why). "x3" means every segment.

| # | Gate (ruling) | 0c68b589 | 41f29b1f | 37c5b5f5 | 3f481f5a | build 114 |
|---|---|---|---|---|---|---|
| 1 | Pin record: seal L-t, schema, formats r93, bar marks r115/116/119, VO L-q/r90/91 (check_pin_only) | REFUSE: sealed r70/r91 rows absent * | REFUSE: five later sealed rows absent * | REFUSE: sealed r91 takeaway row absent * | PASS | UNTESTED: never sealed |
| 2 | r17 / L-v 2: a number, name or negation differs (holds before any vote) | PASS x3 | PASS x3 | PASS x3 | PASS | PASS x4 |
| 3 | Render lock: r17, r18, r84 (b), **r131 (A)/(B)** | PASS x3 (no difference) | PASS x3 (c1JG: r18 two readings; Sjb6: **currency, r131 (B)**) | PASS x3 (c1JG: r18 two readings) | PASS (no difference) | PASS x4 (d6adeb54: **r131 (A)**; 93cfa865: **r131 (B)**) |
| 4 | r72/r84: lock against the second recogniser's reading | UNTESTED: no cached reading | c1JG PASS (adopts fillers); hook, Sjb6 UNTESTED: no cached reading | c1JG PASS (adopts fillers); hook, wdk5 UNTESTED: no cached reading | SPLIT: 23:17Z reading PASS; 18:51Z reading REFUSE "401k" vs "401" | PASS x4 (d6adeb54 adopts one "uh") |
| 5 | r103: re-listen of one number or name | not reached | not reached | not reached | UNTESTED: needs a new paid reading (18:51Z case) | not reached |
| 6 | r105: readings across passes | not reached | not reached | not reached | not reached (its history matches source bytes) | not reached |
| 7 | r131 (A): the sealed text re-locked by the render's lock | n/a | n/a | n/a | n/a | PASS (d6adeb54 adopt_spoken) |
| 8 | r73 (c): the render's cut placement | PASS x3 | PASS x3 | PASS x3 | PASS | PASS x4 |
| 9 | L-v 3: 24 h recency | ignored (age) | ignored | ignored | ignored | ignored |
| 10 | E-FAIL-052: acquire; approved text >= 0.8 | PASS x3 | PASS x3 | PASS x3 | PASS | PASS x4 |
| 11 | edl_rules R1-R11 (r9/10/37/90/91/93, L-o/q/y/ab) | PASS | PASS | **REFUSE: R11 L-y, two VO lines** | PASS | UNTESTED: never sealed |
| 12 | r91: takeaway value (its sealed verdict) | REFUSE: no sealed value verdict * | REFUSE: no sealed value verdict * | REFUSE: no sealed value verdict * | PASS | UNTESTED |
| 13 | Editorial law gate (laws 1-4, r90/91) | PASS | PASS | PASS | PASS | UNTESTED |
| 14 | Stand-alone + floor (r33/34/60/94/119/120) | PASS | PASS | PASS | PASS | UNTESTED |
| 15 | Layout compatibility (DEC-5); v2f guard | PASS | PASS | PASS | PASS | UNTESTED |
| 16 | Cut acceptance (r28/33/73, L-14c); G16 before the render | the original run's: PASS | original: PASS | original: PASS | original: PASS | UNTESTED |
| 17 | Voice: TTS + sign-off (L-a, r27) | original (outside $) | original | original | original | UNTESTED |
| 18 | Prepare, layout, render (r29/30/71/93) | original final | original final | original final | original final | UNTESTED |
| 19 | REQUIRED gate rows (G3b, G3c, G5, G8, G9 + outro, G12, G14, G15, G16, G17, G18, G19, G20, G4s, 9:16 fallback): today's code on the final | running (replay on its final) | running (replay on its final) | running (replay on its final) | PASS, every row, both formats | UNTESTED |
| 20 | V1 vision checklist (r20/23), Heimdall, two models | running (replay on its final) | running (replay on its final) | running (replay on its final) | **REFUSE: 9:16 "watermark" row, one model** | UNTESTED |
| 21 | Attestation, authorisation, Telegram plan and send (RA, M16, T13) | delivered Nov 13 (its own run) | never reached (held at row 19) | never reached | never reached (held at row 20) | UNTESTED |

\* The row did not exist when the package was sealed: visual is r70; takeaway_value is r91; house_style, hook_onset and stand_alone came later. Re-formed today, these verdicts are the builder's rows (its half). Rows 13-15 were judged with r91 (and L-y for 37c5b5f5) set aside, so they would not go unjudged behind the first refusal.

**Running at the time of writing:** today's gates + verify on 41f29b1f, 37c5b5f5 and 0c68b589's runs (rows 19-20; about 15 min each). They waited until the cron transcript pass ended (see failure mode 1 below).

## REFUSALS OF PBX-APPROVED PACKAGES, AND THE CALIBRATED FIX (nothing changed without your ruling)

1. **Rows 1 / 12, the sealed-row gap (0c68b589, 41f29b1f, 37c5b5f5).** Not a calibration: these rows postdate the packages. The builder's replay judges them.
   - **Fix: none.**

2. **Row 11, R11 law L-y (37c5b5f5).** L-y IS PBX's verdict on this very video: "you added too much voiceover" (Telegram 67806/67807, run pinned_20261112_165629).
   - **Fix: none.** It refuses what PBX told us to change.

3. **Row 20, V1 "watermark_present" (3f481f5a; it held the Nov 15 run too).** The question reads "The channel watermark / logo is visible on the content stills before the credits." It does not say WHOSE mark.
   - qwen3.8-27b judged the SOURCE's mark ("no Blockware channel watermark/logo is visible") and answered no.
   - nemotron judged ours (the red pulse logo, lower right, visible on the 9:16 still) and answered yes.
   - **Fix:** name the mark in the question ("the Protocol Pulse red pulse-line logo in the lower-right corner").
     - It would pass: 3f481f5a; its logo is on every 9:16 still checked.
     - It still refuses: a final whose own logo is missing or covered. G2's red-blob probe measures that too.

4. **Row 4, two cached readings of the same audio disagree on one number (3f481f5a's "401k").** The 18:51Z reading has "401"; the 23:17Z reading has "401k,". Ruling 105 exists for this, but its history matches source BYTES, and ruling 77's purge means a re-download need not match. So the two readings are never weighed together, and the one in the cache decides alone.
   - **Fix:** key ruling 105's history by window (video, window, download offset), as batch 101 now does for reuse.
     - It would pass: 3f481f5a (one reading agrees with the lock's "401k"; the other dropped a letter).
     - It still refuses: a token that every reading disputes.

5. **Found while building 131, a lock refusal mode (unchanged).** pinned._token_word fails closed on any span holding a multi-word number ("2 billion"). So ONE function-word split anywhere in such a span HOLDS: "the split function word cannot be located".
   - **Fix:** locate the word through canon.canon_spans, which already maps "2 billion" to its two words.
     - It would pass: one function-word split in a "$2 billion" span.
     - It still refuses: two such splits (ruling 84 (b)), and a word that truly cannot be located.

6. **Rows 19-20 for 41f29b1f, 37c5b5f5, 0c68b589:** pending the running replays.
   - Their original runs held on: 41f29b1f G20, G8 9:16, G9 9:16; 37c5b5f5 G18, G3c, V1.
   - What was measured then:
     - G20: Whisper heard the TTS's "Stephan Livera" as "stefan lavera".
     - G9 9:16: the hash-identical locked outro measured luma 13.6 against a floor of 14.73.
   - Today's results and fixes are added here when the replays finish.

## EVERY REMAINING WAY A FULLY PASSING LINE-UP CAN STILL MISS PBX's TELEGRAM, AND THE GUARD

1. **A yielded transcript pass blocks GPU0 (FOUND TODAY; my batch 97).**
   - The cron Whisper pass gives GPU0 back at a file boundary when a want is up. Its process then stays alive, holding a 394 MiB CUDA context. A render, the scorer or a replay then waits 600 s and HOLDs as Gpu0Foreign.
   - It killed the stand-alone SCORER service at 15:26 ET Nov 16, which was down until 09:46 today (restarted in a restart loop) and held two of my replays this morning.
   - Guard: batch 102 (next), where the pass ENDS when it yields, so its context dies with it, and the services survive a Gpu0Stop.
2. **The render lock is held (another run):** the launcher exits 75 and nothing queues. Guard: the next attempt.
3. **The GPU0 lease is held by a service batch:** exit 75. Guard: services take it per batch (seconds), and the launcher can retry. The render raises no want.
4. **The source is pulled, or yt-dlp fails at render:** PinError, HOLD. Guard: the pre-check downloaded the same window that day.
5. **The render's decode or Scribe disagrees with the pre-check's:** a HOLD at the lock. Guard: one code path (decoder sha lockstep). What remains is recogniser non-determinism (item 4 above).
6. **Scribe, ElevenLabs or Ollama is down mid-run:** HOLD. Guard: preflight checks Ollama and the ElevenLabs quota, but not Scribe and not Heimdall.
7. **Heimdall is down, or a vision model says no:** V1 FAIL, HOLD. Guard: none in preflight. **Proposed:** a Heimdall probe in preflight; and fix 3.
8. **The stand-alone floor is switched off by a scorer_sha change:** a marked clip HOLDs at validate. Guard: the scorer_sha is bound to the floor; code is changed only in lockstep.
9. **A commit to pipeline/, scripts/ or segment_v1/ during a render:** the attestation fails. Guard: the E-FAIL-078 rule and the render-lock check before every commit.
10. **The channel registry is edited after attestation, or a credited channel lacks its handle or url:** delivery STOPs. Guard: the registry sha is bound at authorise.
11. **An attested or bound file changes:** exit 70. Guard: the snapshot re-hash.
12. **Telegram refuses, or the outcome is unknown:** recorded; a rerun refuses until reconciled. Guard: TELEGRAM_DELIVERY.json, reconciled by hand.
13. **A final over 49 MB, a kit over 4096 characters, or a headline number not heard in the final:** STOP before sending. Guard: the plan checks.
14. **Spend:** the render had no spend guard of its own. Guard now: batch 101 writes its Scribe, TTS and sign-off calls to the day ledger the builder reads. TTS is UNPRICED until you rule on its rate (the DoD 09:41 question).
15. **Ageing during the render:** the 12 h rule is not re-checked at render, and L-v 3 is checked once at stage pinned, so nothing is refused for ageing mid-render.
16. **The session watchdog does not see a dead service inside a live tmux session** (it missed the scorer for 18 h). **Proposed:** the watchdog checks each service's process, not only its session.
