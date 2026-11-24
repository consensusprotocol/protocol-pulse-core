# Batch 124, cycle 2
Seats: glm PASS 0.75 (2 notes); qwen27b (medium) FAIL 0.82 (1 medium, 1 low); gemma FAIL (1 high).
- gemma (high), "the edge block reuses the identity's omission_adjudication instead of checking the audio": DISPROVED.
  It is the IDENTICAL measurement (sentence_law.span_fidelity, the same prepared clip, source, window and pad), reused
  only when it said "same". When it said "not same", identity stays non-empty and the edge block, guarded by
  `not row["identity"]`, never runs. When no identity check ran, the block measures it itself.
- glm (medium), "edge ops are picked by the expected side's indices only": NO WRONG PASS. A clipped or shifted cut
  always aligns as an insert or delete somewhere touching the edges (cycle 1's runs), and those return False. With
  identity empty, heard equals the reference (the lock text, or for an unadjudicated lock the source span's decode),
  so the only edge differences left are the lock text against two agreeing decodes, which the audio then decides.
- glm (low), "no differences returns False": the branch runs only with edges non-empty: harmless.
- qwen (medium), "a cut mid-word read as a same-length word": BY DESIGN, as in cycle 1. G17c (the edge words' own
  audio) is REQUIRED and review-blocked; G18's edge check never was the mid-word detector.
- qwen T2 (low): confirms an uncleared identity can never coexist with cleared edges.
No change.
