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
