# Ruling 80 (hook pass) cycle 1 + ruling 77 cycle 2: consensus and dispositions

Reviewers (Heimdall-served; frozen vendors skipped): glm-5.3-flash (441 s, $0.005), muse-spark-open-816b (680 s,
$0.029), qwen3.8-27b (706 s, $0.009). Verdicts: glm "production-ready now for the current scale ... the fail-closed
discipline, prompt-injection hygiene and concurrency design (wlock + carry_forward + flock) are genuinely better than
what most teams ship"; muse "ready for production after one fix"; qwen "production-grade". Ruling 77's cycle-1 fixes:
cross-validated by glm and muse (the corrupt-record path closed; the notice shared with the other STATE notices).

## IMPLEMENTED
| finding | reviewer | fix | proof |
|---|---|---|---|
| carry_forward read an earlier MISSING altcoin as True (and could turn a measured value into its opposite) | muse P0 | an earlier missing value adds nothing; a missing value of the new line stays missing (the adapter refuses it, L-m); True / False from either side as before | test_ledger_coverage `test_an_earlier_missing_value_adds_nothing...` |
| the hook pass's windows shared the back-end's 12 slots with new uploads' moment passes: a long VOD's backfill could starve them | glm P1 | the hook passes have their own window pool of 4 (HOOK_WINDOWS): at most 4 hook calls in flight together; the moment passes keep the rest (newest uploads first, ruling 77 item 4) | service.HOOK_WINDOWS; the hook pass runs on `self.hook_windows` |
| hook_cost_usd is the video's cumulative hook cost, printed as the pass's | glm P1 | the log says "for the video's hook passes so far"; the column is documented as cumulative | service.hook_video |
| hook_due has no index | glm | `videos_hook (state, published_ts)` | queue.py |
| a STATE file that cannot be written raised out of the purge's bookkeeping | glm | the notice write is guarded and logged | service._purge_blocked |
| which candidate lengths the 4-14 s rule drops | glm (with its P0 below) | every dropped length is in the pass report and the log (`dropped_s`) | mine.mine_video |

## REFUTED / BY DESIGN, with evidence
| finding | reviewer | evidence |
|---|---|---|
| P0 "measure the 4-14 s on the spoken span: the caption segment's end overruns systematically" | glm | measured on the 2,588 caption-timed rows of the ledger: the caption estimate is a MEDIAN 2.3 s SHORTER than a 2.6 words/s estimate (p10 -6.9 s, p90 +1.3 s): no systematic overrun; the estimate is approximate both ways. The ruling's 4-14 s is applied to the best measure the miner has (word timing when present, else the caption estimate); the builder re-judges every row with word timing (its own target 8-12 s). The dropped lengths are now recorded, so the edges can be measured |
| P0 "a moment line must not inherit role_hint 'hook' from an earlier hook line" | qwen | the hint records that the hook pass picked the span; a later pass (a re-mine of the moments) does not un-pick it. Dropping it would hide a hook candidate from the builder; the builder's gates decide (the ruling: "nothing is waived"). The flags travel the same way |
| P1 "flock the video_lines read" | muse | one writer: one service per store (the store lock); in it, every append holds `wlock` across the read and the append (service._append). The CLI never writes the ledger |
| P1 observability (coverage / outage / hook quality alerts) | muse | the outage and purge notices go to line 1 of STATE; coverage is reported daily; the hook pass is in live.json `hooks_12h` and `tools/ingest_watch.py hooks` |
