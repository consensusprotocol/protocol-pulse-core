# Integrator facts for pp-selectid (orchestrator rulings 06:45 ET, A and B) — written 06:42 ET Nov 12

Second recogniser: ElevenLabs scribe_v1 on the SOURCE audio of the windows the held render acquired
(runs/pinned_20261112_113058/sources; raw responses runs/pinned_20261112_113058/RULING7/*.scribe.json; $0.016).
Primary decode: runs/pinned_20261112_113058/transcripts (faster-whisper large-v3, verbatim).

## B. clip_01 (What Bitcoin Did, c1JGheQBPH4) FAILS ruling 7 on the facts (condition 1, at the IN)
- scribe: "... with some of these hacks, like it's, it's not, it's not Bitcoin that's getting hacked, it's, um, you know, it's,
  it's other, uh, uh, intermediaries." No sentence boundary before "it's not Bitcoin": the sentence began at "And in fact, you
  know, you look at ...". The IN is mid-sentence in BOTH decoders. Per the ruling: no further bending; supply the next-best
  moment (pre-checked as in C).
- (For the record: the OUT "... the unique nature of Bitcoin. Um, so if there's any ..." would meet conditions 1 and 4.)

## A. clip_02 (Natalie Brunell, wdk5JZ9hPzs): the two decoders DISAGREE at "emerges"
- primary (Whisper): "... stay decentralized and secure, and that's what emerges. And it doesn't matter what the other system
  does. But the ..." -> "emerges." is terminal: the existing rule locks it (ruling 7 is not involved).
- scribe: "... stay decentralized and secure, and that's what emerges, and it doesn't matter what the other system does. Mm. But
  the other system ..." -> a COMMA after "emerges": the speaker may continue the sentence.
- Spans measured on the primary decode (IN after "right now?" = YouTube 528.88):
  - to "emerges." : 11.96 s, YouTube 528.88-540.84 (primary: end; scribe: continues)
  - to "does."    : 14.42 s, YouTube 528.88-543.30 (BOTH decoders: end) <- the boundary both recognisers agree on
- The original OUT "secure," + "and that's what emerges" is a continuation in BOTH decoders: ruling 7's must-fail holds.

## Ruling 7 status in the renderer
Being implemented now in pipeline/sentence_law.py with its must-fail tests (not yet in main). Until it lands, only an
edge with terminal punctuation in the PRIMARY decode locks. A replacement moment for tonight should be chosen with edges
that lock under the existing rule (terminal punctuation in the primary Whisper decode at both edges), or wait for ruling 7.

## Timing (for the 07:20 target), 06:44 ET
The render path from a pin to the gated finals measured 51.3 min tonight (DoD, law L-p evidence: cut, sentence law,
voice, prepare, render 16:9 + 9:16, the gates, verify). A pin re-sealed at about 07:00 reaches Telegram at about
07:55; nothing in that path is skippable (every gate runs). The held run reached `cut` in 3 min 49 s, so a bad edge
shows within about 4 minutes of the start. GPU0 is free and reserved for this pin.

## 07:08 ET: the re-sealed pin f409e9d9 HOLD at prepare (clip_02 'emerges' clipped)
- The speaker runs 'emerges-and' together: the final sibilant (26.94-26.97 s, file time) abuts 'And' (26.98); the cutter's quiet run sat
  before it; the prepared clip was heard as '... and that's what emerged.' (CLIP_CONTRACT.json). No pause = no cuttable end at 'emerges'.
- Recommendation: end clip_02 at 'does.' (14.42 s, YouTube 528.88-543.30): both recognisers end the sentence there, and the source has a
  quiet run from 29.61 s (file time; a short sound at 29.23-29.60, likely the host's 'Mm', which the cutter's neighbour-clear will judge).
- Ruling C: the CUTTABLE gate should run the renderer's own sentence lock AND cut geometry (pause, neighbour-clear) on the window; the
  recogniser's punctuation alone passed an edge with no pause.

## 07:23 ET: the integrator's cut-geometry pre-check on clip_02 -> 'does.' (ruling 07:25): NOT CLEAN
Window and decode: runs/pinned_20261112_120225 (wdk5JZ9hPzs, file time = YouTube - 514.0). The cutter's own code (main, edge_plan +
accepted_cut, unchanged):
- 'does.' : the cutter places OUT at 30.82 (pause 30.56-30.88, neighbour-clear OK, -69.3 dB). BUT the second recogniser hears the HOST
  ('speaker_1') say "Mm." at 29.92-30.04, audible in the source at 29.89-30.12 (low band +18 dB): the clip's tail between 'does' (which
  really ends ~29.60: its /z/ is at 29.45-29.60) and the cut carries ANOTHER SPEAKER's voice, and the prepared clip's edge-word check may
  hear 'Mm' as the last word. A clean pause exists at 29.64-29.88 (after 'does', before 'Mm'), but the cutter does not aim there: the
  primary decode times 'But' at 30.38 (it starts at 30.88), so the cutter's pause search spans the 'Mm' and picks the later pause.
- Nearest sentence end AFTER 'does.': 'mass.' (YouTube 550.66): cut 15.02-37.47 = 22.45 s (> 20 s, L-u) and the host's 'Mm' still inside.
  -> NO clean sentence end after 'does.' in this moment within 20 s.
- The only clean end in this moment: 'existed.' (YouTube 535.62): cut 15.02-22.04 (7.02 s), pause + neighbour-clear OK, one speaker.
  Text: "Bitcoin is a new system of measure that's measuring the first free market that's ever existed." Runtime note: with the
  current VO, R4's estimate drops to about 59.7 s (< 60, R4 hard) unless the VO grows by about 1 s.
- 'emerges.' passes this geometry check but is known bad (the 07:07 prepare HOLD: its final sibilant runs into 'And').

## 07:36 ET: the RENDERER's cut placement at 'does.' is NOT the builder's M19 reading (answer to REQUESTS R11)
- The builder's check (cut_accept.check_cut_out, M19) finds legal cut_out points 29.62-29.83 inside the pause 29.64-29.89. The renderer
  does not place the cut with M19: stage_cut -> sentence_law.write_lock_cut_table -> edge_plan + accepted_cut. On the acquired window that
  geometry reports the heard gap after 'does.' as 30.02-30.89 (the host's "Mm" at 29.89-30.12 is inside the junction it measures, and
  the primary decode times the next word 'But' at 30.38), so its legal OUT range is 30.02-30.89 and accepted_cut returns cut_out 30.82.
  The rendered clip_02 would therefore END after the host's "Mm" (speaker_1), not at 29.6-29.9.
- Reproduce (CPU, read-only): edge_plan(SourceAudio(<run>/sources/wdk5JZ9hPzs.mp4), words, 31, 70) -> OUT cut range 30.02-30.89;
  accepted_cut(...) -> cut_in 15.02, cut_out 30.82 (runs/pinned_20261112_120225; words = its transcripts/wdk5JZ9hPzs.json).
- So, unchanged from 07:23: 'does.' is not a clean end for the render as it stands; the cut geometry is integrity code and is not
  changed tonight. Clean in this moment: 'existed.' only.

## 07:41 ET: 'existed.' measured for the 07:42 decision (on disk; committed after the render: a commit during a render holds it)
- Primary: 'existed.' 21.18-21.62, next 'And' 21.94. Cutter (main): cut 15.02-22.04, pause + neighbour-clear OK, one speaker.
- Audio: the '-st' sibilant 21.43-21.47 and the '-ed' release 21.57-21.63 end 0.41 s BEFORE the cut (22.04, in quiet): the final
  consonant is not cut (unlike 'emerges'). A short voiced blip at 21.68-21.76 (likely a breath) lies in the tail.
- The second recogniser hears "... ever existed, and it- all it has to do ..." (a COMMA; the speaker goes on with a coordinated clause).
  The clause "the first free market that's ever existed" is complete; under the existing rule the primary's full stop locks the edge.
  Stated so the decision is made on all the facts; not a blocker by the existing rule.

## 08:18 ET: integrator pre-check on moment f216541b (clip_02, decision 08:18 item 3): CLEAN, one thing named
1. Window acquired exactly as the render will (select_passages._download_window + _whisper_transcribe, GPU0 under the lease, left as
   found): wdk5JZ9hPzs 3203-3237 (offset 3203.0); the moment is found verbatim (align 1.00) at YouTube 3217.94-3221.58.
2. OUT 'ever.': pause 520 ms (18.71-19.23 file), cutter cut_out 19.01, neighbour-clear OK (-57.8 dB); nothing until the host's
   'Okay, so let's wrap this up' after the cut; no backchannel in the tail. CLEAN.
3. IN after 'path.' (terminal in the primary decode): pause 260 ms (14.37-14.63), cutter cut_in 14.38, neighbour-clear OK (-47.9 dB).
   Named: the clip head carries the guest's own faint false start 'It w-' (14.64-14.84, about 15-20 dB below speech; the second
   recogniser hears 'path. It w- Bitcoin imposes ...', the primary decode does not). Same speaker, not a backchannel.
4. The render's own prepare edge-word check (cut_accept.check_edge_words, large-v3) on a clip cut exactly like prepare (14.38-19.01,
   fade-in 10 ms, fade-out 60 ms): PASS, heard first 'bitcoin', last 'ever' (head 'Bitcoin imposes a global free market.').
5. Evidence: scratchpad precheck_f216541b (window, decode, scribe_v1 $0.007, PRECHECK.json); this is the window and decode the render
   acquires for this pin.

## 08:36 ET: the VO 3 word cap (builder's blocker, 08:32), by the deployed R4's own arithmetic
- R4 (moments) = word caps unchanged (config: intro 30, bridge 20; the takeaway after the last clip is a bridge) + share <= 45 % +
  runtime 60-70 s, runtime = word spans (8.38 + 9.62 + 3.64 = 21.64 s) + each VO line (words / 2.5 + 1.0 s pre-roll) + 14.30 s tail.
- VO 1 13 words (6.2 s), VO 2 18 words (8.2 s):
  - VO 3 24 words (10.6 s): runtime 60.94 s, share 41.0 %: passes share and runtime, FAILS the bridge cap (24 > 20).
  - VO 3 20 words (9.0 s):  runtime 59.34 s: FAILS runtime (< 60).
- Within the rules as deployed: VO 1 has room (cap 30, now 13): +2 words (+0.8 s) lands about 60.1 s with VO 3 at 20 words (the
  builder's fidelity gate judges any new wording). Or a ruling: a moments takeaway cap >= 24 words (TASTE, R4 moments only; the
  renderers place any length).

## 08:42 ET: RULING 10's question, answered in ONE list: every limit in the deployed render path, on THIS exact package
(Dry run of pinned.build_edl + edl_rules.validate_edl + stand_alone + the layout check on the acquired windows; render-time
limits read from the code; G14 simulated with its own sampling and clearance logic.)
 1. R4 moments (with ruling 10's takeaway cap): PASS. VO 25.00 s = 40.44 % of an estimated 61.82 s; intro 13 <= 30, VO 2 18 <= 20,
    takeaway 24 <= 30; every line in its slot.
 2. R1 / R2 / R3 / R6 / R8 PASS; R5 PASS with two recorded taste deviations (clip_01 10.34 s, clip_02 3.64 s); R7 / R9 / R10 skip
    as in every run.
 3. Stand-alone: all three segments PASS (subject 'bitcoin').
 4. Vertical layout: all three channels registered, 'auto' per-shot plan, status 'pending' (letterbox fallback): passes validate.
 5. Cut + G16: clip_02's IN and OUT clean (08:18 pre-check); hook and clip_01 accepted by the 07:07 run on the same windows.
 6. Prepare edge words: clip_02 PASS (simulated); hook / clip_01 passed at 07:07.  7. G18: PASS (simulated, ruling 8).
 8. Sign-off for three channels: 19 words (validator minimum 18), as at 07:07.  9. Credits card / shout-out with three channels:
    as in every three-channel run tonight.  10. ElevenLabs: 359,926 characters left (preflight needs 2,000).
11. **G14 AV alignment (REQUIRED in BOTH formats: 16x9 G14_av_alignment, 9x16 G14_audio_offset): REFUSES BY CONSTRUCTION.** A
    talking-head segment needs >= 3 conclusive samples, taken at 0.2 s and every 2 s inside, outside every VO segment and every
    dissolve overlap (gates.py:195-196, 250-262, 330-357). clip_02's 4.63 s cut sits between VO 2 and VO 3 (6-frame dissolves):
    its sample points 0.2 / 2.0 / 4.0 / 4.03 leave ONE clear point (2.0) -> HOLD (< 3) on a required row, after the full render.
    The shortest talking-head segment that can reach 3 clear samples between two VO lines is 6.75 s (cut). Hook and clip_01 have
    4-5 clear points.
12. G5 final duration window 60-120 s: R4's estimate is 61.82 s (about 1.8 s of margin; the final is measured).
