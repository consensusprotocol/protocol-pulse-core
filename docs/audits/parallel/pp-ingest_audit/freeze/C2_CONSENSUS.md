# pp-ingest FREEZE change, audit cycle 2 (cross-validation of the fixed code): consensus and dispositions

Package: c2/PACKAGE.md (the code after the cycle-1 fixes, its diff since 9500030f, CONTEXT.md) + every cycle-1 review
+ C1_CONSENSUS.md. Reviewers: qwen3.8-27b (153 s, $0.007), glm-5.3-flash (248 s, $0.004; reply limit raised to 24,000
tokens), muse-spark-open-816b (502 s, $0.023), all served by Heimdall; OpenAI, xAI and Google not called (spend
freeze); minimax not re-run (empty twice in cycle 1).

VERDICTS: all three "Yes, with conditions"; no P0 from any of them. glm: "the orchestrator's 05:30 order is implemented
exactly ... B1-B4 verified fixed with named tests ... The 'nothing is dropped' promise, which the integrator called
false in cycle 1, is now true and tested." muse: "No P0 remaining. All 4 blocking findings (B1-B4) are resolved." qwen:
its cycle-1 P0 (the bisection) withdrawn ("refuted by the consensus ... the bisection is now safe").

## Consensus (>= 2 reviewers) IMPLEMENTED

| point | reviewers | fix | proof |
|---|---|---|---|
| a partial video's `moments` was the last pass's count, not the ledger's | qwen (P0), glm N2, muse N4 (P1) | a video with any earlier pass counts its distinct moment ids in the ledger (`ledger.video_moment_ids`, read from a day before its discovery) | test_service.py `test_a_partial_videos_count_is_its_distinct_moments_in_the_ledger` |
| a repeated range keeps the first observation's scores | muse (P2, c1 + c2), glm (P2) | the better-ranked observation gives scores and reason (the first on a tie); the flags stay the fail-closed union | test_mine.py `test_a_range_seen_twice_keeps_every_observations_flags` (now also the better scores) |

## Single-reviewer findings IMPLEMENTED (verified against the code)

| finding | reviewer | fix | proof |
|---|---|---|---|
| N8 a transcript of huge sentences walked one sentence per window (O(n) windows re-sending the same text; no ceiling in the service) | glm | the overlap is at most half a window: each sentence is in at most two windows. Not a window cap (that would drop content). Measured: 0 of the staging store's 1,208 windows change (all have >= 12 sentences), so no stored reply is invalidated; on 60 sentences of 250 words: 58 windows / 3 sends per sentence before, 30 / 2 after | test_mine.py `test_windows_of_huge_sentences_never_walk_one_sentence_at_a_time` |
| N1 releasing the local model on every quiet 5 s reloads it on the next video; its cold load was outside the call's latency | glm | released after IDLE_RELEASE_S = 120 s with no mining due; the load is timed with the call | test_service.py `test_the_local_model_is_released_only_after_an_idle_spell` |
| N2 the reply cache was gated on `enabled()`, which for the local back-end is the GPU0 lease | muse | a stored validated reply is re-read whenever the back-end is enabled in the config (no call, no GPU, no spend) | test_providers.py `test_a_stored_reply_is_reused_when_the_back_end_is_enabled_but_not_callable_now` |
| N4 the 8-character redaction threshold could leave a short key in error text | glm | a back-end's own keys are redacted at any length (other env values from 8 characters) | test_providers.py `test_a_back_ends_own_key_is_redacted_whatever_its_length` |
| N5 the STATE file's temporary copy was named per process only | glm | per process and thread | (the only writer is the health thread; robustness) |
| disclosures: a future-dated publish is outside coverage until that time; the all-time spend read is one indexed aggregate a minute | glm | stated in coverage.py and stats.py | - |

## REFUTED / BY DESIGN, with evidence

| finding | reviewer | evidence |
|---|---|---|
| "a retry with different moments and the same failure count is not appended" (P0) | qwen | describes the code before cycle 1's fix: every partial pass that mined windows appends (`if lines: ledger.append(...)`); muse c2 confirms ("C2 is fixed in this diff") |
| Short detection by `/shorts/` only; "add duration < 60" | muse, qwen | YouTube Shorts can be up to 3 minutes, so a duration rule would misfile long-form uploads; the probe's media_type is authoritative; a mis-listed Short costs one probe |
| a future-dated publish time is mined | qwen, muse | harmless: the adapter excludes a line whose publish time is in the future until it arrives; coverage disclosure above |
| `mine_once` reads `due()` outside the lock | muse N1 | one mine-loop thread is the only claimer; with the idle spell (above) a briefly early release cannot thrash |
| the judge is chosen by model string, not back-end id | muse N5 | law L-x: "generator and judge must be different models": the model string is the rule (glm: "stricter than the law. Compliant") |
| "enable local_gemma to satisfy L-x" | qwen | it needs the GPU0 lease (law L-r), which this session never holds; the integrator enables it (REQUESTS R6.4) |
| A/B budget checked per video, not per window | glm N6 | overshoot of at most one video's windows ($0.0008 each on the gateway) |
| a per-day accumulator for the all-time spend read | glm N10 | deferred: ~1,000 calls a day, indexed (`calls_backend`); disclosed in stats.py |

## Conditions the reviewers set, and where they stand
- glm: before the next A/B, configure a judge of an unfrozen model family or record that its quality dimension is
  unmeasured -> STATE + REQUESTS R9 (the integrator's call; glm and muse are measured candidates).
- glm: the window ceiling -> answered at the root (N8 above) without dropping content.
- glm: the disclosures -> done.
- muse: the partial count and the local cache -> done; the stamp overwrites `mined.at` under the lock -> verified by
  muse and by `test_the_service_stamp_puts_the_file_in_mined_at_order`.

Tests after cycle 2: tests/ingest 166 passed.
