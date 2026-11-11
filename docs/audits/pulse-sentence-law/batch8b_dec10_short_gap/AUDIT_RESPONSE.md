# Batch 8b (DEC-10 d short gap, midpoint quiet-run search, Heimdall F2, named fades): dispositions

Audited: the working-tree diff on top of staged batch 8 (sentence_law.py, the run_isolated.py docstring,
test_dec10_edges.py). Cross-LLM GPT-4o + Gemini (Grok blocked by the xAI ceiling): no P0 / P1, "correct and
production-ready", two P2. Heimdall deepseek + qwen27b per file (heimdall/), re-run on the final diff after the
P2 edits (heimdall_r2/).

## Implemented
- Cross-LLM P2 [both]: the 20 / 30 ms default fades are named constants (DEFAULT_FADE_IN_S /
  DEFAULT_FADE_OUT_S) in accepted_cut.
- Cross-LLM P2 [Gemini]: the point guard in accepted_cut is commented: it is reachable for a file head /
  file end edge (no point), which cut_candidates marks a valley when cut_accept clears none of its
  candidates; the plan's cut is kept there.

## Rejected, with evidence
- Heimdall deepseek, first pass (its reply hit the 16k-token limit; the finding survives only in its
  reasoning): "the short-gap path skips check_cut_acoustics for that edge; always run it, or validate that
  the point is in the legal range and not inside the kept word". DEC-10 c-d: an edge is rejected only if
  (i) 85 % of the edge word, (ii) no audible neighbour or (iii) the sentence lock cannot be met; cut_accept's
  M19-era checks are not among them, and an edge cut at its minimum is by definition one cut_accept does not
  clear (running it would reject every valley cut DEC-10 d orders). The point lies inside the heard gap by
  construction (boundary_geometry: last_offset(end=point) <= point <= first_onset(start=point); cut_lo =
  gap.start, cut_hi = gap.end - 0); G16 re-checks the range and neighbour_clear on the final table, and G17b
  measures the kept word on the render.
- Heimdall r2 deepseek F1 [high, agree 1] "TestMixedEdgeAcoustics is vacuous: it passes on the pre-change
  code": run against the pre-F2 condition (`if not (v["in"] or v["out"]) and not check_cut_acoustics(...)[0]`)
  test_a_normal_edge_failing_cut_accept_rejects_the_clip FAILS ("{'cut_in': 1.0, ...} is not None"); it
  passes only with the change.
- Heimdall r2 deepseek F2 [critical, agree 0] "accepted_cut uses the first return value, so the minimum-edge
  test must fail": the code reads the per-edge results (`check_cut_acoustics(...)[1]`, edges NOT at a minimum
  only); both tests pass.

## Recorded, not changed
- Stricter than DEC-10 requires: with one edge at a minimum, the other edge's cut_accept check uses the
  pair's speech median; a candidate that passed with the plan targets' median but fails with the pair's
  rejects the clip where DEC-10 would cut that edge at its minimum too. Rare; the Nov 10 lineup is
  unaffected (re-measured with this code, 11:32 ET).
- deepseek could not answer on sentence_law in this batch: r2 and a re-ask on the two accepted_cut hunks
  alone both ended at the 16k-token limit with empty content (finish_reason "length"). qwen27b: PASS (0.82)
  on the batch diff and on the final diff. The cross-LLM pair reviewed the same code.
- Pre-existing, outside the diff: pipeline/test_editorial.py::TestLayoutGate (live GPU + LLM; not in the
  established verification set) fails with "rejected: no hook passage scored >= 4.0": the LLM clip scorer
  rates the synthetic fixture's hook passages below HOOK_MIN_SCORE (editorial_select.py:1171) before any
  edge_plan call; DEC-10 does not touch that path.
