# Batch 16 audit response (red-team hardening A + the 21:10 canonical form / backtest / preflight)

Panel on the actual diff (STEP.diff, 260 KB): gpt-6.1-sol and claude-fable-5-2 on the whole diff (PBX-approved spend,
orchestrator 21:55; FRONTIER_openai.md, FRONTIER_anthropic.md); the Grok leg of utils/cross_llm_audit.py and the
Heimdall panel (deepseek, qwen27b, glm) on five chunks (grok_<chunk>/, heimdall/out_<chunk>/). The first Grok run saw
no code: cross_llm_audit.py silently drops a diff of 220,000 bytes or more (grok_whole_diff_EMPTY_too_large/); it was
re-run per chunk.

## gpt-6.1-sol (8 findings, all HIGH, all confirmed and fixed)

| # | finding | fix | test |
|---|---|---|---|
| 1 | the whole `evidence` field absent / null skipped the evidence check; a malformed format entry crashed | `blockers(fmt, rows, evidence)` takes evidence as a required argument: None, a non-mapping or a non-mapping format entry is NO evidence (every REQUIRED row blocks); only an explicit `NO_EVIDENCE_CHECK` asks the rows-only question (unit tests of verdict rules) | test_release_auth test_a_report_with_no_or_malformed_evidence_holds |
| 2 | digest checked, then the sender reopened the path (TOCTOU) | deliver_run reads each file ONCE, hashes those bytes against the attestation and uploads exactly those bytes (`send(..., data=bytes)`; `_send_bot_api` refuses a file send without bytes) | test_telegram_delivery: every upload's bytes hash to the attested digest; test_a_final_changed_after_authorisation... |
| 3 | a kill after Telegram accepted a message, before the checkpoint, duplicated it on rerun | a durable (fsync + rename) IN-FLIGHT record before each request; success replaces it, a definite refusal clears it, anything else leaves it unknown; a rerun refuses in-flight / unknown; one delivery per run at a time (flock) | test_a_message_in_flight_at_a_crash_is_never_resent, test_one_delivery_at_a_time |
| 4 | a number phrase was owned by its first word, so a lock ending on 'seventy four thousand' ended on 'seventy' | canon_spans: every canonical token carries its first AND last source word; sentence_law.anchor and editorial_select.align_quote use the first word of the first token and the LAST word of the last | test_canon TestAuditBatch16 (spans; a lock on a spelled number ends on 'thousand'); protected preview re-checked |
| 5 | 'one and two' = 'one two' (the 'and' was consumed before the parser knew it could not extend the number) | 'and' is consumed only after hundred / a scale ('one hundred and two', 'two thousand and five') | test_canon TestAuditBatch16; fuzz inequality 'one and two' / 'one two' |
| 6 | '- 5%' = '+ 5%', '$-5' = '$+5' | a plus before a number is always 'plus'; a sign after '$' is read before it; a spaced minus opening a text / clause is 'minus'; U+2212 is 'minus'; ranges, dates and hyphens never become signs | test_every_sign_layout_keeps_its_sign |
| 7 | the headline check compared bare magnitudes with the lock text | numbers (and ordinals) as (sign, value, unit) claims against G18's READINGS OF THE FINAL'S AUDIO (both formats); 'percent' must be heard as percent, a reading without 'dollars' is whisper's '$' habit; no readings = nothing is said | test_a_headline_number_the_video_does_not_say_stops_the_drop |
| 8 | another checkout was caught only by its path spelling | first-party module NAMES (every *.py of pipeline/, segment_v1/, video_pipeline_v3/) loaded from outside this checkout are holds, whatever the path (and the path rule stays) | see run_fresh.record_assets |

## claude-fable-5-2 (8 findings)

| # | finding | disposition |
|---|---|---|
| 1 HIGH | MONITORING rows that FAIL still authorise under 'all release gates passed'; 9:16 had no deciding A/V gate; V1 qualifies as REQUIRED | V1 got its real passing fixture this batch (TestVisionMustPass: the PBX-approved preview passes V1 in both formats; green) and is REQUIRED; vertical_silent_fallback is REQUIRED (real log-line detector fixture test_fresh test_fallback_regex, real passing runs, missing provenance = KeyError = HOLD); G14_audio_offset (9:16) got its fixtures (test_g14_sampling TestG14AudioOffsetVertical: the corrected cut's vertical passes, a real 2-frame slip fails, < 3 conclusive samples HOLD) and is REQUIRED when they are green. The caption's FIRST line names any MONITORING row that did not pass ('... | N MONITORING check(s) NOT passed (not release-deciding)') and the next line lists them. G1 / G6 / G13 / G2 / G3 / G4 / G10 / G11 / G14c stay MONITORING by the orchestrator's item 4 (no fixtures yet). |
| 2 HIGH | evidence fail-open when absent (= GPT #1); evidence derived from the verdict; a six-key report literal = 6 samples | fixed with GPT #1; `_samples` counts MEASUREMENTS only (numbers, non-empty lists / objects), never labels, hashes or flags; outro_locked = the two hashes compared; vertical_silent_fallback = the vertical clips checked |
| 3 HIGH | anchor lost its edge-word equality; a lock ends on the wrong word | the span part = GPT #4 (fixed). NOT a defect: the edge-word equality is enforced in the window search (`if seq[s] != qt[0]: continue`, `if seq[e] != qt[-1]: continue`) |
| 4 MEDIUM | killed process / sent bytes not the checked bytes | = GPT #2 / #3, fixed |
| 5 MEDIUM | 'three and four' = 'three four'; '1 000 000' single-pass; 'one second' = 'one two' | 'and' = GPT #5; spaced thousands chained to a fixpoint; ordinals are their own token ('3rd' = 'third' = 'ord3', never the cardinal) |
| 6 MEDIUM | tests that do not test what they claim | the site test requires an `import canon` statement (not the word 'canonical'); FORBIDDEN gains `re.(sub|split|findall)(r"[^a-z0-9`; the fuzz drops an INTERIOR word and checks 'one and two' / '5 percent' vs '5 dollars' / 'not' vs 'now'; preflight reports a raised check by exception TYPE only, tested with an error whose text carries the secret |
| 7 MEDIUM | headline check ignores units and context; ordinals over-block | = GPT #7 (units and signs); ordinals are kept IN the check on purpose: an invented 'November 8th' (E-FAIL-038) is exactly what it must stop, and a headline ordinal the video does not say is an unsupported claim |
| 8 LOW | crash paths | blockers type-checks before membership; edge_word_fidelity skips an alignment with nothing compared; edges_on_final catches any exception per segment (no proof, never a crash); verify_pack / run_tail / write_report tolerate a panel entry without rows |

## Grok (per chunk) and Heimdall

Heimdall (deepseek, qwen27b, glm), five chunks: no consensus finding, nothing raised. Grok: READY on all five
(A_release: two LOW notes, the G17 evidence written after put and a cosmetic report path in replay; A_delivery_pack,
A_lc_g18, C_select_tools: no defects; B_canon_sites: MEDIUM import hygiene (the relative sys.path inserts; kept: the
same pattern the module used, now pointing at this checkout) and a LOW note on punctuation._key's alignment
tolerance (alignment only, never an equality of content)).

## Cycle 2 (both frontier models on the FIXED diff, cycle2/)

gpt-6.1-sol verified GPT #1, #4 (named case), #5 and the upload-byte half of #2 / #3, and found 8 more; claude-fable-5-2
verified most fixes and found 8 more. All implemented:

| finding | fix | test |
|---|---|---|
| GPT2 #1 dedup / lock per option | one lock and one ledger per RUN: any TELEGRAM_DELIVERY*.json with messages, unknown, in flight or complete refuses the next drop | test_the_same_finals_are_never_sent_twice_under_another_option |
| GPT2 #2 '{}' read as a refusal | only ok True + integer message_id is a success and only ok False + integer error_code a refusal; anything else is an UNKNOWN outcome (never resent); a missing payload is a refusal decided before any request (fable2 F7) | test_only_an_explicit_refusal_is_a_known_outcome |
| GPT2 #3 / fable2 F7 metadata re-read after authorisation | snapshot(): EDL and gate report read once as bytes, hashed against the attestation, then parsed; the channel registry's sha256 is attested and re-checked (authorise + snapshot); caption, headline check and kit use only the snapshot | test_metadata_changed_after_authorisation_is_refused |
| GPT2 #4 a word inserted into a source pause | span_matches compares both ways: final speech where the source is quiet (>= 60 ms) fails too | TestSpanMatches test_a_word_inserted_into_a_pause_is_seen |
| GPT2 #5 / fable2 F3 chained thousands and signs in spans | canon_spans merges chained groups and reads a lone sign word before a number as canon_tokens does ('70 - 75' stays a range) | canon checks; protected preview REPRODUCED |
| GPT2 #6 a spaced minus inside a sentence | a '-' + spaces before a number after a non-digit is 'minus' anywhere in the text | 'change is - 5%' = 'change is minus five percent' |
| GPT2 #7 / fable2 F6 first-party module under a dependency-looking path | a top-level pipeline module NAME outside the checkout is foreign whatever the path; a missing launch revision is a hold; preflight's scope covers the code the run imports (tracked pipeline / segment_v1 / video_pipeline_v3 modules, untracked pipeline/*.py) | test_a_pipeline_module_loaded_from_anywhere_else_is_a_hold (site-packages / dist-packages / venv), test_preflight |
| GPT2 #8 headline context | each headline clause with a number must be supported by ONE reading clause in EACH format: the claim (sign, value, unit), every proper name (capitalised words incl. the first, minus function words / direction words / common headline verbs) and the same direction | test_a_headline_number_needs_its_subject_and_direction_in_both_formats (wrong asset, wrong direction, one format only) |
| fable2 F1 evidence from labels | _samples counts list entries that carry something (never None / empty); outro_locked counts the hashes actually computed; the fallback check counts a clip only after its file was probed | release / delivery suites |
| fable2 F2 adjacent numbers summed | scales strictly descend; 'hundred' only when cur < 100; a violation ends the number at the last completed group ('five thousand and six thousand' = 5000 and 6000) | canon checks |
| fable2 F4 compound ordinals | a spoken cardinal + ordinal tail is one ordinal ('twenty first' = '21st' = ord21, 'one hundredth' = ord100) | canon checks |
| fable2 F5 G3c flipped from a partial failure list | the L-c flip needs EVERY failing G3c entry to fail only by edge flags, all of them proved | run_fresh |
| fable2 F7 a 16:9 sent before the 9:16 digest check | every payload is read and verified before the FIRST send | test_a_final_changed_after_authorisation (nothing sent) |
| fable2 F8 tests | refusals assert their reason; a REAL-speech fixture for the repeat adjudication (the corrected Nov 10 cut's clip_02 matches its source; 300 ms of it repeated does not) | TestSpanMatchesRealSpeech |

MEASURED ON THE WAY (decision for the orchestrator, DoD): a final's gain against its source is not constant along a
clip (loudnorm + the music bed: 1 s windows drift 1.65-2.03 dB on the hook, 2.23-7.25 dB on clip_01 of the corrected
Nov 10 cut), so span_matches and the L-c edge proof now measure the gain next to what they compare. Even so the
amended L-c proof (G17c's unchanged 1 dB criterion on the FINAL) cannot be made on either real run: the gain next to
an edge is not steady (IQR > 1 dB) for hook / clip_01 / clip_02, and clip_03's first word is 9.1 dB (16:9) / 9.2 dB
(9:16) below the source in the final (inside the clip_02 -> clip_03 dissolve). So a G3c failure on an edge now
stands: the corrected Nov 10 cut (= the PBX-approved preview's cut) fails G3c on the hook's tail, a REQUIRED row.
