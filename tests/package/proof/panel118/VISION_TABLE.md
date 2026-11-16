# RULING 118 (3): NEMOTRON ON OUR CONTACT SHEETS (free; seeds 7 and 8)

nvidia/nemotron-3.5-super-vl on Heimdall was asked every contact sheet Grok judged (tests/package/proof/VISUAL_CACHE.json,
29 sheets; 3 skipped: their bytes changed or their moment's text is gone), the prompt rebuilt exactly as visual_pin builds it
(replay85.run_visual's construction), its answer read by visual_pin.check / flags / layout_block. Rows: VISION.jsonl.

| measure (the 11 sheets whose Grok record is today's prompt version, visual_pin.VERSION) | result |
|---|---|
| answers | 18 (2 no answer) |
| the block (layout_block: may the clip be on screen?) agrees, where nemotron answered | 16 of 16 (all passes) |
| the flags (kind, item, place in the 9:16 frame) agree | 8 of 16 |
| Grok's flags that are not blocks, kept by nemotron | 4 of 12 answers |
| THE ONE CONTENT BLOCK ON RECORD: 94a613f3 (DAN; a lower third and a bug the 9:16 crop cuts mid-word) | NO ANSWER at both seeds (an empty reply): fail closed in production (law L-m), but no evidence nemotron catches a block |

The other 18 sheets' Grok records are earlier prompt versions (no burned-in question, or visual-2): their "block" is the
record's version, not the sheet's content, so they are not compared on the block.

READING: not yet. Nemotron agrees on every pass it answered, but matches Grok's flags only half the time and gave no answer on
the one recorded block. Vision checks stay on Grok until nemotron reads a recorded block correctly; each new Grok-blocked
sheet is a new case to test it on, free.
