# pp-selectid audit of the 22:40 rulings diff (R1 recency in the seal, R3 no-voice, R5 budget / deadline, R6 house style): cycle 1 consensus (synthesis by the pp-selectid session, 22:54 ET Nov 12)

**Run.** C1_STEP.diff is 83,798 bytes; the prompt is 113,741 bytes. Reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP yes with conditions; three P2s, no P0 / P1.
- qwen/qwen3.8-27b (Heimdall, effort none): SHIP no; four P0s, two of them withdrawn by qwen itself.
- z-ai/glm-5.3-flash (Heimdall, effort none): SHIP yes with conditions.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | "a no-voice package can ship with a join the clips-alone verdict flagged" (qwen P0-1, glm P0-1) | REFUTED on the code, and hardened anyway. build() calls no_voice() only when `ok_m and not med["flagged"]`. ly_shape compares the bridged joins (none in a no-voice package) with the flagged ones and fails any mismatch. Tests: test_no_voice_never_ships_a_join_the_blind_check_flagged; the flagged must-fail in test_a_no_voice_medley_needs_its_record_and_no_vo_line. Hardened: no_voice() now refuses by itself, at its first line, a clips-alone verdict that is not a measured pass with flagged == [] |

## Unique findings, evaluated

| finding | disposition |
|---|---|
| glm P1-5: take_failed counts one write twice (a cheap failure, then a fidelity failure) | REFUTED: the cheap-failure branch ends in `continue`, so the paid verdict never runs on that write. Each write adds at most once |
| glm condition (b): the budget is only checked when an angle ends, so a package can run past 15 min inside one angle | IMPLEMENTED: over_budget() runs before every line-up and every write, and the end-of-angle check stays. Test: test_the_budget_stops_on_the_reported_cost_or_the_estimate_ceiling (one stop after line-up 1, one before any call or write) |
| glm P0-3: _within double-settles, or leaks the reported cost | REFUTED: _settle pops the reservation and books the upper bound once. TestDeadline asserts one call, the upper bound, and no reservation left. A late answer is dropped unrecorded, never settled again; this asymmetry is on purpose (documented) |
| grok P2: paid_gates runs inside the no-voice pool's `with` and can race its shutdown | REFUTED: paid_gates submits both verdicts and waits for both (`.result()`) before it returns, all inside the `with` |
| grok P2: an abandoned thread mutates the ledger or the cache later | REFUTED: the thread runs only `b.complete()`; settling, recording and serving happen in Router.call, on the caller's side |
| grok P2: a quoted possessive slips past title-possessive | REFUTED by running it: "'Bitcoin's value is real'", the curly-quoted form and "(Bitcoin's) value" all fail title-possessive |
| qwen P0-2: house style is linted only for medleys | KEPT: build() makes only medleys (L-y). The v3 shape remains only for the orchestrator's given packages of Nov 11-12 |
| qwen P0-3 / glm P1-1: utc_z refuses a published time with no offset, but only at the pin | KEPT, fail closed as ruling 1 needs. Every moment the miner writes carries an offset; the refusal names the segment |
| qwen P1-1: titles and takeaways are not lowercased | KEPT: ruling 6 says lowercase for the CAPTION, and its own title example is "The market no government owns". The takeaway is spoken |
| qwen P1-3 / P2-5: the added clip's channel and uniqueness | REFUTED: the candidate must not be in the line-up and must not share a channel with any segment, the hook included |
| qwen P1-6 / P2-3 / P2-7 / P2-9: no_voice skips the clips-alone verdict, the runtime, an empty title, or empty segments | REFUTED: an added clip re-asks the clips-alone verdict. cheap_checks runs RUNTIME (60-70 s by the factory's estimate), L-y shape and house style. to_pin needs a non-empty title and caption. The segments are the line-up |
| glm P1-2: sentence_count and abbreviations | KEPT as documented: the single-letter-abbreviation rule is the module's declared reading |
| glm P1-6: the emoji ranges miss U+2B00-2BFF arrows (⬆ ➡) | KEPT as P2: the ruling's examples are covered; widening is cheap if PBX wants arrows banned |

## Decision recorded with the fixes

A takeaway whose point the blind coherence verdict rates under 4 (with every clip at 4 or more) has failed a gate of its
own. It now counts toward ruling 3's "fails its gates twice".
