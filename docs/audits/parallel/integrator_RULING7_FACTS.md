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
