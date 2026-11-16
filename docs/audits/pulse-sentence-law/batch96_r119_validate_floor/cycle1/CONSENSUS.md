# Batch 96, cycle 1 (first attempt): NO EVIDENCE from any seat

The diff: c7051ce1..b7fd82de, five code files. The question is QUESTION.txt, six open questions on a long background.

| Seat | Effort / budget | Result | Cost |
|---|---|---|---|
| qwen27b (qwen/qwen3.8-27b) | none / 24576 | 300.7 s, all 24,576 tokens spent thinking aloud inside the JSON "issue" field; no parseable reply | $0.0179 |
| gemma (google/gemma-4-31b-it) | none / 24576 | 17.4 s, a bare `{"verdict":"PASS","findings":[],"confidence":1.0}` (21 tokens): no review | $0.0003 |
| deepseek (deepseek-v4.1-flash), deepseek_none/ | none / 24576 | 529.3 s, 87,951 characters of reasoning "going in circles", finish "length", content null | $0.0050 |
| gemma, gemma_medium/ | medium / 24576 | killed by `timeout 900` with no reply (exit 124). Another session's audit held the same seats at the time. | n/a |

Cycle-1 Heimdall cost: $0.0232 (not capped).

**What the readable text said, checked by the integrator against the code:**
- qwen's one concrete worry was `SA.opener(..., SA.CLIP_MIN_SCORE, fault, True)`. It took CLIP_MIN_SCORE to be passed as a threshold. It is passed as the SCORE: the opener is asked again AT the bar, so the only thing tested is whether the refusal was the score's. No change.
- qwen also noted that an exception other than ValueError (a missing `hook`, scorer_sha raising) propagates out of stage_validate. That stops the run (no render), so it fails closed. No change.
- deepseek's reasoning raised no defect it could name before its budget ran out.

**Found by the integrator's own review in the meantime:** `apply` read the pin record's `segments` even for an unmarked pin, so a record without them would HOLD a run that never uses the floor. Fixed in 7487c0f3: segments are read only for a marked pin. The new test fails on the old apply.

**Next:** cycle 1 again, on the final code (c7051ce1..7487c0f3), in `../cycle1_retry/`. It asks a short question with five concrete checks and quoted code required. Three seats run separately at the settings each is known to answer at: qwen27b none, gemma medium, gpt-oss medium.
