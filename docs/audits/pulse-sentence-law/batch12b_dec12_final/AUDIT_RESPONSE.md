# Batch 12 (DEC-12 a / c / d / e / f + order 15:30 B and C + PBX laws L-a..L-d + delivery kit): dispositions

One batch, as ordered. Audits: batch12_dec12 (the pre-B/C diff, 15:22) and batch12b_dec12_final (the whole
batch, 15:55: cross-LLM GPT-4o + Gemini, Grok blocked; Heimdall deepseek + qwen27b, one chunk per file) and a
Heimdall pass on the later delivery change (heimdall_telegram/).

## Implemented (from both audits)
- Heimdall [high] check_preview_reference: zip() could truncate silently -> the EDL / PIN / cuts segment counts
  must agree; [medium] the layout reference must cover exactly the cut's segments.
- Heimdall [high] regression.sh: step 6 failed only on exit 1 -> any non-zero exit except 2 (reference not
  on this machine = SKIP) fails the regression.
- Heimdall [critical] sentence_law "edge_word_fidelity fails open when no frame is above the gap level" ->
  an empty word window fails closed.
- Heimdall [medium] vo.py: a cached stem is reused only if it reads as a WAV with >= 0.5 s of frames.
- Heimdall tests: the chyron test covers EVERY has_chyron channel; the G9 test asserts the spread equals the
  rounding rule exactly; the G14 test's skip guard checks sources and transcripts; the v2f G17c test asserts
  both sides are present; the G3b must-pass asserts every segment's last word found.
- Batch12 audit: measure_g9_spread raises on a missing real final (no silent skip); comments on the G9
  spread's GOP-phase cause and on VALLEY_MARGIN_S as a tightening.

## Rejected, with evidence
- Heimdall [critical] "edge_word_bounds is wrong when the cut point is inside a word": machine cuts come only
  from G16-legal points (the heard gap or the valley minimum) and G16 HOLDs before any render; a cut inside
  a word also fails G17b and G18 on the render. A speech-level guard was tried and removed: it failed
  legitimate shallow valleys between abutting words (Natalie at 80.84: 2 dB under speech) and v2f's
  recorded clip_02 IN.
- Heimdall [high] "edge_fades keeps a 10 ms minimum even when the gap is smaller": the orchestrator's rule
  ("the fade shortens down to 10 ms"); the frames it covers are, by construction, within 3 dB of the cut
  point's level (the gap run), and G17c verifies the word frames.
- Heimdall [high] run_fresh "L-c ignores a dissent when last_found is false": then the majority missed the
  word and the G3b row is already FAIL from the gate itself.
- Heimdall [medium] "G3c FAIL can come from other criteria": G3c's verdict per segment is exactly
  tail_ok and head_ok, which are the edges L-c examines.
- Heimdall [high] test_edge_words "midpoint i0 / i1 can drop a straddling word": edge_word_bounds measures from
  the cut points' levels, not from i0 / i1.
- Heimdall [medium] vo.py "fallback IndexError with an empty channel list": the fallback sits inside
  `if channels_list:`.
- Heimdall [high] (batch12) test_dec10_edges "a human PIN edge expects 83 ms": accepted_cut serves machine cuts
  only; human PIN tables keep 20 / 30 (pinned.py; test_pinned asserts it).
- Cross-LLM (both audits): no P0 / P1; P2 comments only (the L-c block and VALLEY_MARGIN_S carry them).

## Recorded
- v2f G17c: 6 of 8 edges at full level; clip_01 OUT (PBX's one-time exception, 2.63 dB) and clip_03 IN (v2f's
  pre-law mid-sentence start on 'a', 1.93 dB) are recorded must-keep-failing legacy edges.
- G3c on the DataDash hook tail (room tone 10.4 dB under his speech, limit 11.63): with L-b the fade there is
  10 ms (the cut sits 40 ms into the pause, where cut_accept put it; moving it would change the protected
  reference's decision); by L-c a G3c edge failure stands unless G17c and G16 prove the edge.
- The full suite's 6 failures at 15:55 were CUDA out-of-memory (it ran beside the verification replay); re-run
  alone on a free GPU0: 26 passed.
