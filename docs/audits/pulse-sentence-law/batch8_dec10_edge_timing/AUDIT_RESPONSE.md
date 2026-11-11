# Batch 8 (DEC-10 edge timing: v2f-calibrated constants, heard gap, envelope-minimum point, valley cut with a 2-frame fade, neighbour_clear): dispositions

Audited: the staged DEC-10 diff (STEP.diff). Cross-LLM GPT-4o + Gemini (Grok blocked by the xAI $1/day
ceiling); Heimdall deepseek + qwen27b, one chunk per file. The follow-up (batch 8b) carries the fixes below
that touch code and is audited separately on its own diff.

## Implemented
- U1 / U2 [P0, both models]: the gospel (docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md) now states the old rule
  (80 ms pause / lead / tail, 60 ms guard), the new values (0 ms = v2f's measured worst; DEC-10a table in
  docs/audits/DEFINITION_OF_DONE_PULSE_CHECK.md), the unchanged D1 head rule (the file head and the hook keep
  >= 80 ms of genuine quiet or get the room-tone pad), the valley cut, neighbour_clear and the authority
  (orchestrator DEC-10, 2026-11-11 10:35 ET). gate_g17_prepared states the two tiers in its docstring and at
  the hook branch.
- U3 [P2]: the prerender_clips docstring documents fade_in_ms / fade_out_ms (milliseconds, from
  cuts_final.json; absent = 20 / 30, the M19 defaults). v2f's table declares 20 / 30, so its render is
  unchanged (Law 22 re-proof below).
- UNIQUE-1 [P1, Gemini]: VALLEY_FADE_S = 2 / 24 is 2 VIDEO frames at the 24 fps timeline = 83 ms, as DEC-10 d
  orders ("a 2-frame audio fade"); the constant's comment and the gospel now say so. 20 ms (2 audio hops)
  would be the M19 default fade-in, not the DEC-10 d fade.
- UNIQUE-2 [P2, GPT-4o]: the new paths are tested: a short / abutting gap is cut at its minimum with the
  83 ms fade (TestValleyCut), a given cut inside the neighbour word fails neighbour_clear, v2f clip_01 OUT and
  clip_02 IN fail neighbour_clear (recorded must-fails), and (8b) a normal edge that fails cut_accept rejects
  a cut whose other edge is at a minimum.
- Heimdall test_dec10_edges [high / medium, consensus]: the valley test was vacuous (an or-condition and
  20 ms tolerances). Rewritten: abutting sin^2-enveloped words; the boundary's pause must be short; valley_in
  must be True unconditionally; the fade must be 83 ms; the cut within one 10 ms hop of the junction.
- Heimdall sentence_law F2 [high, qwen27b; not agreed]: accepted. cut_accept's unchanged checks now run on
  every edge NOT cut at a minimum, also when the other edge is (8b; mocked tests both ways).
- Found by the rewritten fixture (8b): boundary() searched the quiet run over both words' full extents, which
  also cover the junctions with the words before and after them and could win a tie; the search now runs
  between the two words' midpoints.
- DEC-10 d "short gap" made explicit (8b): an edge whose quiet run is shorter than 80 ms (in) / 140 ms (out),
  the 01:50 legality minimums, now choosing only the METHOD, is cut at its envelope minimum with the 2-frame
  fade; neighbour_clear still decides acceptance.

## Rejected, with evidence
- Heimdall sentence_law F1 [critical, qwen27b only] "VALLEY_BELOW_SPEECH_DB is never defined: NameError": it
  is defined at sentence_law.py:68 (unchanged, outside the diff) and used by SourceAudio.levels(); the DEC-10
  suites call neighbour_clear on real audio (53 + 2 tests pass).
- F3 [medium, qwen27b only] "the cut_candidates fallback turns must-fail cases into passes": that is DEC-10 d
  by order ("cut at the envelope minimum with a 2-frame audio fade rather than rejecting the clip; a clip is
  rejected for edges only if (i), (ii) or (iii) cannot be met"). (ii) neighbour_clear is applied to that very
  cut, G16 re-applies it with the cut's own fades, and G17b (85 %) and G18 run on the render. Yesterday's
  three defects keep failing (pipeline/test_pulse_20261110_mustfail.py).
- F4 [medium, qwen27b only] "TAIL_MIN_S = 0 makes the G17a tail check vacuous": DEC-10 b sets it to v2f's
  measured worst (0 ms, v2f clip_03's prepared tail). The clipped-last-word protection is G17b (>= 85 % of the
  word, unchanged) plus neighbour_clear.
- Cross-LLM verdict "not production-ready until P0 + P1": both are done above.

## Law 22
Re-rendered with the batch-8 code in the tree (runs/v2f_20261111_160348, 11:34 ET, run_isolated.py
--clip1-out 249.63 --allow-clip1-gap-ms 20): out/segment.mp4 sha256 472938134157b649...cefd and
out/segment_vertical.mp4 5545a261feedd8c1...6c57, byte-identical to references/v2f_2026-11-06/SHA256SUMS
(the legacy G1-G13 verdict is FAIL on G8_sharpness of the vertical, exactly as in the 08:19 and 10:30
re-proofs runs/v2f_20261111_081935 and _103004; the proof is the bytes).
run_isolated.py never calls edge_plan / cut_candidates / accepted_cut (grep: no match), and v2f's
cuts_final.json declares 20 / 30 ms on every segment, so the 8b changes cannot reach this render.
