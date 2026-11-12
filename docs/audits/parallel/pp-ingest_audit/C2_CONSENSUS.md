# pp-ingest audit, cycle 2 (cross-validation on the fixed code): consensus and dispositions

Reviewers: gpt-4o, grok-4.20-0309-reasoning, gemini-3.1-pro-preview, qwen3.8-27b (Heimdall); each saw the other
reviewers' cycle-1 outputs, C1_CONSENSUS.md and the fixed code (c2/PACKAGE.md: the Gemini schema change at
providers.py:332 and the bounded ledger read are in it).

## Consensus IMPLEMENTED
| finding | reviewers | fix | proof |
|---|---|---|---|
| `fetch.text_fingerprint` hashed only the first 400 canonical tokens (about 2-3 min of speech) | grok (c1 + c2: misses edited re-uploads), gemini (c2 P0: FALSE POSITIVES: every video of a channel with a long standard intro or sponsor read becomes a "re-upload" of its first one and is never mined), qwen (c2 P1) | the fingerprint covers the whole record read as spoken; title + duration remains the second rule | tests/ingest/test_watch_fetch.py `test_a_shared_long_intro_is_not_a_reupload_but_the_same_speech_is` (fails on the old prefix fingerprint: verified by swapping it back in); measured before the fix: 0 collisions among 600 main-store and 113 staging caption records with either fingerprint, so no video had been wrongly dropped |

## Two reviewers on one point, REFUTED with evidence
| finding | reviewers | evidence |
|---|---|---|
| "a crash between ledger.append and set_state re-appends a video's moments: make it idempotent" | qwen (c1, c2), grok (c2 P1); gemini (c2) disagrees: "a robust at-least-once delivery design" | the pp.moment/1 contract defines the read as de-duplicated by moment_id, the latest line wins; `best_unused_moments` does exactly that (test `test_the_latest_line_wins_and_order_is_by_rank`); the duplicate lines are byte-identical answers from the reply cache (re-mining asks no model: `test_a_restart_recovers_and_reuses_validated_replies`); the growth is bounded by crash count x 3 videos |

## Single-reviewer claims REFUTED with evidence
| finding | reviewer | evidence |
|---|---|---|
| "Anthropic `output_config` is not a messages.create parameter" (P0) | qwen (c2), gpt-4o (c2) repeating gemini c1 | gemini itself withdrew it in c2 ("I accept that SDK 0.84.0 supports output_config"); the installed SDK signature has it; 284 + 10 valid live Anthropic calls with it (outage drill 08:36-08:43 UTC; single-window proof) |
| "GeminiBackend ignores the schema" (P0, c2) | qwen | c2/PACKAGE.md line 867 shows providers.py:332 passing `response_json_schema=schema` |
| "semaphore leak in Router._try" (P0) | grok | gemini and qwen (c2) disagree with reasons; the `with` encloses the `try`, so both semaphores are released on any exception; every client exception is converted to BackendError inside the block |
| "mine_video does file I/O while holding a video slot" (P2) | grok | gemini (c2) disagrees: the slot is one of three threads of a dedicated executor; model calls run in the separate window executor |
| "AnthropicBackend sends effort in output_config without a schema" | grok | `effort` is a valid output_config field on its own (Claude API reference); every role passes a schema |
| "RSS canary uses one channel" (P2) | qwen | correctness does not depend on it: a channel whose RSS fails falls back to its uploads playlist inside `poll_channel`; the canary only chooses the cheaper first try |
| "key rotation should skip keys on 429" (P2) | qwen | Heimdall's 429 is the provider's capacity, not a key's: "more keys will not raise" (fleet probe 13_rate_limit_behavior.json); the throttle pauses the whole back-end instead |
| "ledger compaction" (P2) | grok | a future roadmap item at the measured growth (about 800 lines a day); the bounded read keeps the adapter's cost at the recent tail |
| gpt-4o c2 P0/P1 list | gpt-4o | restates refuted claims (Anthropic / Gemini) and the already-implemented ledger read; names no new file:line defect |

## Verdicts
grok: "Yes with conditions" (its conditions: the refuted semaphore claim, the refuted duplicate-append point, and
observing the bisection in production: the live watcher uses it from this commit). gemini: ready once the fingerprint
is fixed (done). qwen / gpt-4o: "No" on the refuted Anthropic / Gemini claims. No reviewer reported a law violation in
either cycle.

## Changes made after the c2 package was built (not reviewed by cycle 2; the integrator's audit covers the merge)
- fetch.text_fingerprint over the whole record (the c2 consensus above) + its must-fail test.
- coverage: an unlisted upload younger than the 10-min poll + YouTube's 15-min RSS cache is reported "inside the
  discovery window" (INGEST-FAIL-07) + test.
- ab: approved-passage recall counted only where the approved sentence lies in the offered windows; `--report-only`.
- tests/ingest/xllm_audit.py: Heimdall deepseek dropped after two empty replies; Gemini review budget 48,000.
