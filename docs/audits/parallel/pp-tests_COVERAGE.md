# pp-tests COVERAGE — every red-team finding mapped to the test that now pins it (or UNCOVERED, honestly)

Source: every row of docs/audits/REDTEAM_2026-11-11.md (the ledger at c1451047: 244 rows from openai_gates,
openai_select, xai_select, xai_cut, xai_gates, xai47_select, openai_r2_cut, anthropic_r2_gates, anthropic_r2_select;
the frontier reports that produced no findings - anthropic_cut / _gates / _select, openai_cut, xai47_cut / _gates,
xai_r2_*, anthropic_r2_cut - have no rows). Generated from the ledger's own rows so no finding can be left out; the
mapping was written by hand against the tests.

Test files (tests/adversarial/): f1 = test_f1_text_meaning.py, f2 = test_f2_provenance.py, f3 =
test_f3_release_auth.py, f4 = test_f4_vacuity.py, f5 = test_f5_references.py. **XFAIL** = a strict xfail that fails
today on exactly that defect (read with --runxfail) and names its request in pp-tests_REQUESTS.md; it flips to a
failure the moment the fix lands. Every other named test passes today (it pins a fix that holds, or a check that
already fails closed).

Totals: 244 rows; 97 pinned by at least one test here (30 of them by a strict xfail = the finding is still open in
the code); 147 UNCOVERED. UNCOVERED is mostly outside the five families of the order: selection logic that needs the
embedder / model (same-event merge, clusters, budgets, dates and time zones), process and wrapper behaviour (GPU
lock, cron, concurrency, disk-full), the MONITORING gates (G1, G2, G4, G6, G10, G11, G13: not release-deciding) and
GPU-only paths (Whisper, SCRFD, voice embeddings). "UNCOVERED here" names the pipeline test that covers it instead.

New findings from this wall (not in the ledger): PP-01 canon is not a fixpoint on adjacent spoken numbers (f1, XFAIL
R-01); PP-02 verify_lock never compares the lock's words with its transcript (f2, XFAIL R-11); PP-03 G4s / G14 / G19
pass on nothing (f4, XFAIL R-15); PP-04 L-b measured on the references disagrees with G17c's dispositions (f5, pinned
table, a decision: pp-tests_REQUESTS.md).

Correction to the ledger, measured: Claude-gates T1 is marked CONFIRMED-FIXED ("never substrings"), but G3b's
_g3b_match still accepts `expected in heard` inside a token ('week' matches 'weekend'): f1 TestG3b (XFAIL R-07).

## Highest-risk UNCOVERED rows (my reading of the ledger; owners and order are the orchestrator's)

Tier 1, a release could pass with a wrong video or a wrong claim (a REQUIRED gate or the selection meaning):
- GPT-gates F29 / F30, Claude-gates A7, M6: G14 absorbs a constant cut-in offset and cannot see lip-sync at 40 ms
  (REQUIRED in both formats); needs AV fixtures with a known slip (the integrator's test_g14_sampling has one).
- GPT-cut F13 (G17 accepts early starts / extended tails), F14 / F15 / F31 (fade retries and shot snapping change the
  file after the preparation checks passed), F16 (a file head taken as proof of a sentence start).
- GPT-select F02 / F07 (an off-topic or mid-thought passage, a fallback bypassing the stand-alone rejection), F06
  (same-event merging pools different events), Grok47-select F1 / F11 (the model rewrites the event; currentness
  checked against the model's own summary): selection logic that needs the embedder / model to exercise.
Tier 2, the run can hang, collide or read the wrong day: GPT-gates F34, GPT-cut F11, Grok-select I, Claude-gates X8
(GPU lock), GPT-cut F26 / F27, Grok-cut 4 (hangs, run-directory collisions), Grok-select D / E, Claude-gates D1-D7
(UTC vs ET, windows, weekends).
Tier 3, reported but not release-deciding: the MONITORING gates G1, G2, G4, G6, G10, G11, G13 (GPT-gates F06, F18-F26,
F31; Claude-gates V1-V3, V6, T7, T8, A1-A3, A8) until each has its fixtures (addendum '22:15' item 4).

| report | id | finding | ledger status | pinned by (tests/adversarial/test_*.py) | note |
|---|---|---|---|---|---|
| GPT-gates | F01 | Old QA can authorize a replacement video | CONFIRMED-FIXED | f3 test_the_9x16_replaced_after_authorisation_refuses_and_nothing_is_sent, test_the_two_finals_swapped_on_disk_refuses, test_gates_that_measured_a_different_file_hold, test_an_attested_digest_of_a_different_file_refuses, test_the_9x16_swapped_during_delivery_never_reaches_the_chat |  |
| GPT-gates | F02 | One arbitrary PASS row per format constitutes “all gates passed” | CONFIRMED-FIXED | f3 test_a_missing_required_gate_refuses (every REQUIRED row, both formats), test_a_required_row_that_is_not_exactly_pass_refuses |  |
| GPT-gates | F03 | The legacy Telegram entry point bypasses the newer verification regime | CONFIRMED-FIXED | f3 test_the_legacy_send_path_is_gone |  |
| GPT-gates | F04 | The public QA runner does not run several gates defined in its own module | CONFIRMED-FIXED | f3 test_a_missing_required_gate_refuses (every REQUIRED row, both formats), test_a_required_row_that_is_not_exactly_pass_refuses |  |
| GPT-gates | F05 | Missing segments turn large portions of QA into successful no-ops | OPEN | f4 test_a_required_gate_never_passes_on_nothing [G3b / G3c / G8 vacuous] **XFAIL** R-13; test_whatever_a_gate_returns_on_nothing_release_blocks_it |  |
| GPT-gates | F06 | Empty sign-off text disables the audible sign-off check | OPEN | UNCOVERED | G13 is MONITORING (not release-deciding); its sign-off path needs the VO manifest + ASR |
| GPT-gates | F07 | The verification caller converts an invalid or negative panel response into success | CONFIRMED-FIXED | f4 test_v1_never_passes_on_a_garbage_reply, test_v1_one_line_not_exactly_yes_fails, test_v1_control_a_whole_yes_reply_passes |  |
| GPT-gates | F08 | `vision=False` can produce a “complete” pack with no visual verdict | CONFIRMED-FIXED | f3 test_a_pack_without_vision_or_incomplete_refuses |  |
| GPT-gates | F09 | A partially missing verification sheet is marked complete | CONFIRMED-FIXED | f3 test_a_pack_without_vision_or_incomplete_refuses, test_a_missing_pack_refuses | verify_pack._sheet's partial-frame rule itself not exercised here |
| GPT-gates | F10 | Failed ffmpeg commands can reuse evidence from an earlier render | OPEN | f4 test_g8_never_measures_a_frame_of_an_earlier_render **XFAIL** R-21 |  |
| GPT-gates | F11 | Failure state is shared across formats and is not transactional | CONFIRMED-FIXED | f3 test_legacy_markers_authorise_nothing |  |
| GPT-gates | F12 | Word-set overlap permits materially wrong narration | CONFIRMED-FIXED | f1 (canonical tokens only) | G1 / G13 set overlap: UNCOVERED (MONITORING; voice model / ASR) |
| GPT-gates | F13 | Typography normalization differs between gates and destroys token boundaries | CONFIRMED-FIXED | f1 every comparator on the same surface variants (canon, G18, quote_in, align_quote, anchor, headline, G20, G3b) |  |
| GPT-gates | F14 | Written/spoken number equivalence is still incomplete | CONFIRMED-FIXED | f1 TestCanonicalForm, TestG18, TestHeadlineNumbers, TestG3b::test_written_and_spoken_amount_is_the_same_last_word |  |
| GPT-gates | F15 | Substrings still count as complete boundary words | OPEN | f1 TestG3b::test_a_longer_word_containing_the_last_word_is_a_different_word **XFAIL** R-07 |  |
| GPT-gates | F16 | Repeating the last word hides a next-word leak | OPEN | f1 TestG3b::test_a_next_word_equal_to_the_last_word_still_leaks **XFAIL** R-08 |  |
| GPT-gates | F17 | G20 can hear the wrong channel variant as the credited channel | OPEN | f1 TestSignoffNames::test_a_different_channel_variant_is_not_the_credited_channel **XFAIL** R-06 |  |
| GPT-gates | F18 | G1 verifies consistency with this run’s generated voice, not the approved voice | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F19 | Sign-off voice identity is not checked | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F20 | Correct sidecar stems can certify an incorrect final mix | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F21 | G6 interprets “no detected onset” as compliant pre-roll | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F22 | G4 ignores its source classification and trusts metadata that can waive face checks | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F23 | G4’s shoutout failure is never incorporated into its return value | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F24 | Missing or mismatched registry metadata disables chyron protection | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F25 | G10 does not inspect where a vertical render may put the chyron | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F26 | Red pixels are sufficient to impersonate a watermark | OPEN | UNCOVERED | G2 MONITORING |
| GPT-gates | F27 | Sharpness compares different scene geometry | OPEN | f5 test_g8_9x16_v2f_passes_through_the_production_wiring_at_its_floor (crop compared with crop on the saved files) |  |
| GPT-gates | F28 | G8 accepts one successful sample as if all five were measured | OPEN | f4 test_g8_never_passes_on_one_of_five_samples **XFAIL** R-20 |  |
| GPT-gates | F29 | G14 absorbs a constant wrong cut offset into its reference | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F30 | G14’s picture comparison cannot establish 40 ms AV synchronization | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F31 | G11’s segment-count comparison is literally self-comparison | OPEN | UNCOVERED | G11 MONITORING |
| GPT-gates | F32 | Short visual defects can fall between every deterministic probe | OPEN | UNCOVERED | sampling density between probes needs a render |
| GPT-gates | F33 | The avatar registry cache survives registry changes | OPEN | UNCOVERED | avatar registry cache |
| GPT-gates | F34 | QA can collide with another GPU user despite the wrapper lock | OPEN | UNCOVERED | GPU lock: outside a CPU-only suite |
| GPT-gates | F35 | English is forced even when the selected speech is not English | OPEN | UNCOVERED | ASR language (Whisper) |
| GPT-gates | F36 | Telegram payload limits are checked for photos but not videos or publishing text | CONFIRMED-FIXED | UNCOVERED here | pipeline/test_telegram_delivery.py TestLimits |
| GPT-gates | F37 | Partial Telegram delivery has no durable checkpoint or reconciliation | CONFIRMED-FIXED | f3 test_a_partially_delivered_run_is_never_resent_automatically |  |
| GPT-gates | F38 | The wrapper can exit zero without delivering or locating a successful run | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F39 | Detached pinned runs discard the absolute path already resolved by the parent | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-gates | F40 | A logged Git HEAD does not identify the code actually executed | CONFIRMED-FIXED | UNCOVERED here | pipeline/test_release_auth.py TestRunFreshWiring |
| GPT-select | F01 | The independent support verifier fails open on missing or mistyped fields | CONFIRMED-FIXED | f4 test_adjudicate_never_counts_a_garbage_reply (mistyped / missing deciding fields) |  |
| GPT-select | F02 | A passage explicitly rated off-topic or mid-thought can still be selected | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F03 | Quote verification destroys quantitative distinctions | CONFIRMED-FIXED | f1 TestQuoteVerification::test_variants_verified_mutants_refused |  |
| GPT-select | F04 | Fuzzy alignment can replace the approved claim with a different claim | OPEN | f1 TestSelectionAnchors::test_align_quote_never_moves_a_quote_onto_a_different_claim **XFAIL** R-05 |  |
| GPT-select | F05 | Supporting chunk IDs are not bound to the verified quote | OPEN | f1 TestQuoteVerification::test_adjudicate_counts_a_quote_only_with_the_chunk_that_says_it **XFAIL** R-04 |  |
| GPT-select | F06 | Same-event merging can pool different events and retain invalid inherited verdicts | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F07 | Boundary fallback bypasses the editor’s stand-alone rejection | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F08 | SELECT returns success with too few clips or only one channel | OPEN | f2 TestSelectContract::test_select_with_fewer_than_two_clips_is_not_a_success, ::test_select_with_one_channel_is_not_a_success **XFAIL** R-23 |  |
| GPT-select | F09 | A cached download is relabelled with a newly requested offset | OPEN | f2 TestDirtyCache::test_a_cached_window_of_another_request_is_never_relabelled **XFAIL** R-09 |  |
| GPT-select | F10 | Transcription caches are not bound to the media they transcribe | OPEN | f2 TestDirtyCache::test_a_transcript_of_other_bytes_is_never_used, TestLockBinding::test_g16_refuses_a_source_whose_bytes_changed_after_the_lock **XFAIL** R-10 |  |
| GPT-select | F11 | Model schema validation accepts objects that crash callers outside the retry boundary | CONFIRMED-FIXED | f4 test_adjudicate_never_counts_a_garbage_reply, test_rate_passages_never_rates_from_a_garbage_reply, test_derive_story_query_never_invents_a_query, test_label_cluster_never_labels_from_a_garbage_reply, test_sentence_and_adjacency_checks_never_admit_on_a_garbage_reply |  |
| GPT-select | F12 | Invalid scores are converted into perfect scores | CONFIRMED-FIXED | f4 test_rate_passages_never_rates_from_a_garbage_reply (score 9, '5', NaN, unknown fault, duplicate id) |  |
| GPT-select | F13 | Embedding deduplication deletes candidates before finding out whether they work | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F14 | Cluster labelling’s “diversity” can consist entirely of one channel | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F15 | The 24-passage shortlist can eliminate every passage from a necessary channel | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F16 | A “48h” candidate can be labelled from older evidence and scored using unrelated fresh mem | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F17 | Wire-story age stops advancing when the story-engine file stops updating | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F18 | Written and spoken amounts still disagree before the repaired QA gate | CONFIRMED-FIXED | f1 TestSelectionAnchors::test_surface_variants_anchor_on_the_sentence |  |
| GPT-select | F19 | Hyphenation and compound tokens disagree across the selection gates | CONFIRMED-FIXED | f1 TestCanonicalForm (hyphenated number words, 'well-known') |  |
| GPT-select | F20 | Legal sentence starts with currency or dash punctuation are rejected | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F21 | A bad alignment can crash instead of returning “no anchor” | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F22 | A downloaded source without a successful transcript crashes fallback | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F23 | Failed yt-dlp processes can be accepted as successful downloads | OPEN | f2 TestDirtyCache::test_a_failed_download_never_supplies_a_source **XFAIL** R-22 |  |
| GPT-select | F24 | An Ollama outage becomes a many-hour semantic rejection storm | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F25 | GPU “arbitration” has no exclusion and unloads other jobs’ models | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F26 | Exceptions bypass resource cleanup | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F27 | Missing video duration defeats the transcription budget | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F28 | Forced English decoding cannot establish that the source actually speaks English | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F29 | Embedding cache identity omits the actual chunk text | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F30 | Embedding caches are written non-atomically and read without recovery | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F31 | Event-date parsing changes real dates and accepts impossible ones | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F32 | Currentness votes are per video, not per independent channel | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F33 | Artifact writes are neither a run transaction nor safe for concurrent same-directory attem | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F34 | Fallback changes the actual lineup without updating the frozen source manifest | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F35 | Future timestamps are freshness winners rather than invalid metadata | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-select | F36 | The injected run clock is not normalized or propagated to universe acquisition | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-select | A | A channel transcript contains `S&amp;P 500` (HTML entity from YouTube captions) while the  | CONFIRMED-FIXED | f1 entity variants in every comparator, TestSignoffNames |  |
| Grok-select | B | Spoken “eighty one thousand” vs written “$81,000” (or “81k”). `qa_gates._g3b_words` and ed | CONFIRMED-FIXED | f1 number words vs digits in every comparator |  |
| Grok-select | C | Smart quotes `“Bitcoin”` vs straight quotes in model output or previous run’s approved_tex | CONFIRMED-FIXED | f1 curly quotes in every comparator |  |
| Grok-select | D | Run starts at 23:50 UTC on a day that crosses DST boundary in a US channel’s local time. ` | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-select | E | A story published at 23:55 UTC is evaluated in a run that started at 00:05 UTC the next ca | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-select | F | `derive_story_query` receives a cluster headline containing the phrase “Bitcoin hits new A | OPEN | f4 test_derive_story_query_never_invents_a_query | schema half only; the semantic half (is_specific_event wrong but well-formed) UNCOVERED |
| Grok-select | G | `rate_passages` returns a JSON with `fault: "starts_mid_thought"` on a passage that clearl | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-select | H | Prompt changed (new CLUSTER_NOTE text) but cache key only contains `prompt_sha(DERIVE_PROM | NOT REPRODUCED: the reply-cache key is sha256 | UNCOVERED | ledger: NOT REPRODUCED |
| Grok-select | I | Two concurrent `run_fresh` instances (cron overlap or manual rerun) both call `release_gpu | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-select | J | yt-dlp returns a file whose first 0.4 s is a YouTube preroll bumper because `--download-se | OPEN | f2 TestKnownOffset (cuts located by text, EDL in file coordinates) |  |
| Grok-select | K | A fast-talking panel show (no pauses >180 ms) is selected. `edge_plan` in sentence_law use | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-select | L | `G3b` majority vote receives zero valid ASR readings because the last word is “dollars” an | OPEN | f4 test_a_required_gate_never_passes_on_nothing[G3b reading empty] (FAIL, as required) |  |
| Grok-select | M | Run is killed after `select_passages.py` writes `edl.json` but before `render.py` finishes | OPEN | f2 TestDirtyCache (stale artefacts of an earlier attempt) **XFAIL** R-09 / R-10 |  |
| Grok-select | N | All 48 h clusters have exactly 2 channels but one of them has `has_chyron=true` so `layout | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-select | O | A clip ends on a word that Whisper tokenises as “$” but the QA oracle expands to “dollars” | OPEN | f1 TestG3b::test_written_and_spoken_amount_is_the_same_last_word |  |
| Grok-cut | 1 | **** A headline contains a real em-dash or curly quote (“Bitcoin — ETF inflows hit record” | CONFIRMED-FIXED | f1 em-dash / curly-quote surface variants |  |
| Grok-cut | 2 | **** Clip ends with “...above $74,000 dollars”. `qa_gates._g3b_words` still does literal s | CONFIRMED-FIXED | f1 TestCanonicalForm::test_named_equivalences_compare_equal['above $74,000 dollars'] |  |
| Grok-cut | 3 | **** Run starts at 23:55 UTC on a day when US markets close. `editorial_select` uses `chan | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-cut | 4 | **** Two concurrent `run_fresh.py` instances (cron overlap or manual rerun). Both write to | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-cut | 5 | **** A channel publishes a title “Bitcoin hits $88k”. Whisper large-v3 on the auto-caption | CONFIRMED-FIXED | f1 'k' suffix variants ($81k) |  |
| Grok-cut | 6 | **** Ollama model digest changes (new quant or new pull). The validated-reply cache is key | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-cut | 7 | **** A fast-talking panel (no pauses > 80 ms). `sentence_law.boundary()` finds no acoustic | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-cut | 8 | **** Disk fills during render (qa/ grows with contact sheets, g14 frames, etc.). `record_a | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-cut | 9 | **** Channel list in `channels.json` changes (new channel added). The editorial cache (sha | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-cut | 10 | **** Vertical render falls back to original 16:9 because face detector returns no faces on | OPEN | f4 test_whatever_a_gate_returns_on_nothing_release_blocks_it (vertical_silent_fallback with no clip checked = 0 samples) | the render-log path itself UNCOVERED (needs a render) |
| Grok-cut | 11 | **** Sign-off voiceover text uses “Coin Bureau, Natalie Brunell and others” while the card | OPEN | f5 test_l_a_v2f_signoff_card_and_clips_are_one_set, test_l_a_the_preview_is_the_documented_must_fail; f1 TestSignoffNames |  |
| Grok-cut | 12 | **** GPU0 OOM during `gate_g18` because previous Ollama process did not fully release. `fr | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 1 | A channel transcript contains `&quot;Bitcoin&quot;` (HTML entity) while the editorial mode | CONFIRMED-FIXED | f1 TestSignoffNames (entity sign-off) |  |
| Grok-gates | 2 | Clip ends with “$88K”. `_g3b_words` turns it into `['88k', 'thousand']` but EDL `last_word | CONFIRMED-FIXED | f1 TestG3b |  |
| Grok-gates | 3 | Two channels use “Bitcoin” vs “bitcoin” in different casing in registry aliases. `spoken_c | OPEN | f1 TestSignoffNames (upper-case sign-off) |  |
| Grok-gates | 4 | Run starts at 23:55 UTC on a day that crosses DST in a US timezone used by `datetime` cach | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 5 | Video published 23:59 previous day, transcript timestamped in local time. 48 h window incl | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 6 | Ollama returns JSON with extra `"reason"` key or `null` for a required field. `validated m | NOT REPRODUCED for the cache: a cached reply is re-validated on read | f4 model replies with extra / null fields | partial |
| Grok-gates | 7 | Prompt “Is this the same event? yes/no” returns “maybe” or “Yes, but…”. Code treats any no | NOT REPRODUCED: no yes/no substring parsing exists | f4 '"yes"' / prose replies never count | ledger: NOT REPRODUCED |
| Grok-gates | 8 | Prompt changed but cache key only contains `sha256(model, digest, context, max_tokens, pro | NOT REPRODUCED: see Grok-select H | UNCOVERED | ledger: NOT REPRODUCED |
| Grok-gates | 9 | yt-dlp returns age-gated video with auto-captions only. Pipeline falls back to thumbnail f | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 10 | ElevenLabs rate limit hits mid-signoff. Partial VO file is written. Rerun on dirty dir reu | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 11 | Fast-talking panel (no pauses >300 ms). G3c valley check uses speech_median of full clip;  | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 12 | Non-English code-switched clip (“Bitcoin a $74k, ¿sabes?”). Whisper “en” model outputs mix | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 13 | Zero talking-head segments (only hook + signoff). G4, G3, G3b, G3c, G8, G10 all skip their | OPEN | f4 vacuity probes **XFAIL** R-13 + release backstop |  |
| Grok-gates | 14 | G13 signoff transcript is exactly a music hallucination phrase because VO stem is missing. | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 15 | Run killed after rendering 16x9 but before 9x16. Dirty run_dir still contains `gate_result | CONFIRMED-FIXED | f3 test_legacy_markers_authorise_nothing |  |
| Grok-gates | 16 | All clusters have coverage < 3 channels on a slow news day. Threshold compounds with “Bitc | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 17 | Model returns the same hook sentence that was already published two days ago (ledger only  | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok-gates | 18 | G20 fails (missing one channel name) but `gate_status()` in `telegram.py:135` only looks a | CONFIRMED-FIXED | f3 test_an_extra_unknown_gate_refuses['G3b_cut_out_clean(run_gates)']; f5 test_the_preview_recorded_gate_report_is_not_releasable |  |
| Grok47-select | F1 | Wire path and same-event merge still let the model rewrite the event. | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F2 | A stale `candidate_stories.json` is scored as breaking news. | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F3 | Embedding dedupe merges different prices. | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F4 | The four tokenizers still disagree, and `quote_in` is a substring test. | OPEN | f1 TestQuoteVerification::test_a_quote_never_matches_inside_a_longer_word_or_number **XFAIL** R-02 |  |
| Grok47-select | F5 | The cut path is a second, unfixed decoder, and the file start is not the offset you record | OPEN | f2 TestKnownOffset |  |
| Grok47-select | F6 | Caches are keyed by video id and then treated as the requested window. | OPEN | f2 TestDirtyCache **XFAIL** R-09 / R-10 |  |
| Grok47-select | F7 | Failure does not invalidate last run's success artifacts. | OPEN | f3 test_another_runs_attestation_copied_in_refuses, test_legacy_markers_authorise_nothing | partial |
| Grok47-select | F8 | The approval package can describe a different video than the one cut, and select's True is | OPEN | f3 test_an_edl_changed_after_the_gates_ran_holds **XFAIL** R-12 |  |
| Grok47-select | F9 | Opener and subject checks kill ordinary Bitcoin speech and accept the wrong asset. | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F10 | Schema-valid model output is cached as truth, and several gates default open. | OPEN | f4 model-reply probes | partial (cached replies not exercised: fake model has no digest) |
| Grok47-select | F11 | Cluster "current" is verified against the model's own summary, and the prompt's example is | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F12 | First producible 48 h cluster ends the search, and the screen only sees the literals `bitc | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F13 | Adjacent-sentence admission still asks the model a yes/no after a vacuous pronoun hit. | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F14 | A legal quote window is thrown away because expansion broke the start, and lowercase / non | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F15 | "Today" is UTC on an ET show, and naive timestamps are read as UTC. | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F16 | GPU release is neither exclusive nor correctly classified, and the whisper budget is bypas | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F17 | Lower-thirds and ads are policy by a stale flag, not by the frames. | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F18 | Currentness conflict ignores unverified historical quotes, and one counted quote is enough | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Grok47-select | F19 | `quote_in` does not require the quote to lie inside one excerpt or inside the supporting i | OPEN | f1 TestQuoteVerification::test_a_quote_never_straddles_two_excerpts **XFAIL** R-03 |  |
| Grok47-select | F20 | Duration floors, hook score 4.0, and the 8 s / 2-sentence cap compound into a hold on a no | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F01 | Required gates can disappear without blocking the verdict | CONFIRMED-FIXED | f3 test_a_missing_required_gate_refuses |  |
| GPT-cut | F02 | Missing visual verification is accepted as “nothing to add” | CONFIRMED-FIXED | f3 test_a_missing_required_gate_refuses[*-V1_visual_checklist], test_a_pack_without_vision_or_incomplete_refuses |  |
| GPT-cut | F03 | A finished-video failure can be overruled by a prepared-clip check | CONFIRMED-FIXED | UNCOVERED here | stage_gates' L-c path needs GPU0 (pipeline/test_release_auth, test_word_diff) |
| GPT-cut | F04 | G18 erases changes in units and numeric sign | CONFIRMED-FIXED | f1 TestG18::test_diff_equal_variants_and_unequal_mutants (percent vs dollars, signs) |  |
| GPT-cut | F05 | G18 deliberately hides repeated words introduced by rendering | CONFIRMED-FIXED | UNCOVERED here | span_matches on audio: pipeline/test_word_diff TestSpanMatches |
| GPT-cut | F06 | An approved quotation can lose its negation during anchoring | OPEN | f1 TestSelectionAnchors::test_sentence_law_anchor_never_locks_a_different_claim **XFAIL** R-05 |  |
| GPT-cut | F07 | G17c can report perfect fidelity after comparing zero word samples | CONFIRMED-FIXED | f4 [G17c hook without lock or cut] (FAIL) | the zero-frame alignment itself: pipeline/test_word_diff |
| GPT-cut | F08 | A meaningful middle-word mismatch against the selection lock is report-only | OPEN | f1 TestG18::test_gate_g18_fails_a_number_that_differs_from_the_lock **XFAIL** R-16 |  |
| GPT-cut | F09 | Outro identity is calculated, then ignored | CONFIRMED-FIXED | f4 [outro_locked identity unknown] (FAIL) |  |
| GPT-cut | F10 | Provenance failure adds a HOLD reason without changing the candidate verdict | CONFIRMED-FIXED | f3 test_a_replay_or_an_unclean_run_refuses |  |
| GPT-cut | F11 | GPU availability is checked, not reserved | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F12 | A legal selected hook can be guaranteed to fail its later lead-in gate | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F13 | G17 output timing accepts early starts and extended tails | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F14 | Fade retries move cuts without recomputing their fades | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F15 | Shot snapping changes the file after the preparation checks passed | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F16 | “File head” is treated as proof of a sentence start | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F17 | Valid sentence ends with unsupported closing quotation marks are rejected | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F18 | Abbreviation handling rejects real sentence ends and accepts false ones | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F19 | G18 recreates split-token text independently of transcript-store repairs | OPEN | f1 TestG18::test_gate_g18_through_its_public_entry['$81 ,000'] |  |
| GPT-cut | F20 | Common spoken numeric forms still fail canonical equality | OPEN | f1 TestCanonicalForm, TestG18 |  |
| GPT-cut | F21 | Anchoring silently chooses one occurrence of a repeated sentence | OPEN | f2 TestDirtyCache uses a repeated sentence | partial: which occurrence anchor picks is not pinned |
| GPT-cut | F22 | Duplicate manifest labels let G18 check only the last occurrence | OPEN | f1 TestG18::test_gate_g18_checks_every_occurrence_of_a_label **XFAIL** R-17 |  |
| GPT-cut | F23 | Several gates pass on zero work | OPEN | f4 [G18 / G17a vacuous] **XFAIL** R-14 + release backstop |  |
| GPT-cut | F24 | End-of-run code verification compares against the wrong revision | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F25 | Disk-full and termination can leave no terminal verdict | CONFIRMED-FIXED | f3 test_a_run_without_an_attestation_refuses |  |
| GPT-cut | F26 | Launch-time subprocesses can hang the daily run indefinitely | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F27 | Run creation is neither collision-safe nor single-flight | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F28 | Flat RMS input generates NaN thresholds instead of a controlled rejection | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F29 | Transition duration uses packet count divided by a hard-coded FPS | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F30 | Style B’s thump extends into speech despite a legal transition plan | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| GPT-cut | F31 | Fade retry exhaustion can reject a clip with a known legal passing point | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | T1 | Substring matching passes clipped and leaky cuts | CONFIRMED-FIXED | f1 TestG3b::test_a_longer_word_containing_the_last_word_is_a_different_word **XFAIL** R-07; TestQuoteVerification substring **XFAIL** R-02 | the ledger's CONFIRMED-FIXED does not hold for G3b's _g3b_match |
| Claude-gates | T2 | The leak check anchors on the last substring match | OPEN | f1 TestG3b::test_a_next_word_equal_to_the_last_word_still_leaks **XFAIL** R-08 |  |
| Claude-gates | T3 | A trailing extra word is tolerated unless the EDL names it | OPEN | f2 TestSelectContract::test_every_segment_names_the_next_source_word_for_g3b **XFAIL** R-18 |  |
| Claude-gates | T4 | `_g3b_words` strips only `. , ? !` | CONFIRMED-FIXED | f1 unicode punctuation variants |  |
| Claude-gates | T5 | Written-versus-spoken forms beyond `$` and `%` | OPEN | f1 currency / percent / scale / sign variants |  |
| Claude-gates | T6 | G3 and G3b normalise differently | CONFIRMED-FIXED | f1 TestG3b with canon variants |  |
| Claude-gates | T7 | VO text checks are set-based | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | T8 | G13 exact alias versus G20 fuzzy 0.85 | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | T9 | G20 name-length and exact-match traps | OPEN | f1 TestSignoffNames **XFAIL** R-06 |  |
| Claude-gates | T10 | Channel identity is the display-name string everywhere | OPEN | f1 TestSignoffNames |  |
| Claude-gates | T11 | [UNSEEN] Sentence splitting on abbreviations | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | T12 | [UNSEEN] Caption residue beyond the entity fix | OPEN | f1 &#39;, &amp;, U+00A0 / U+202F in numbers | partial: VTT tags, [Music], '>>', double-encoded entities UNCOVERED |
| Claude-gates | T13 | Model headline goes verbatim into the caption and suggested title | CONFIRMED-FIXED | f1 TestHeadlineNumbers |  |
| Claude-gates | D1 | The run stamp is UTC and is shown in the caption | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | D2 | [UNSEEN] UTC midnight during the run | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | D3 | [UNSEEN] Window granularity | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | D4 | [UNSEEN] Publish time is not event time | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | D5 | [UNSEEN] Weekends | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | D6 | [UNSEEN] The newest videos lack auto-captions | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | D7 | Cron | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | M1 | The visual verdict passes on empty answers | CONFIRMED-FIXED | f4 V1 garbage / partial replies |  |
| Claude-gates | M2 | Vision models decide what pixels decide | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | M3 | Whisper as oracle | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | M4 | [UNSEEN] The reply cache key as described omits the validator version and sampling options | NOT REPRODUCED: story_semantics.LocalLLM.chat_json re-validates a cached reply with the CURRENT validator on every read | UNCOVERED | ledger: NOT REPRODUCED |
| Claude-gates | M5 | The three G3b reads collapse to one | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | M6 | G14 discards non-matching audio as inconclusive | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | C1 | QA artefacts have fixed names and existence-only checks | OPEN | f4 test_g8_never_measures_a_frame_of_an_earlier_render **XFAIL** R-21 |  |
| Claude-gates | C2 | The gate report is not bound to the delivered bytes | CONFIRMED-FIXED | f3 byte-binding mutations |  |
| Claude-gates | C3 | Legacy state files | CONFIRMED-FIXED | f3 test_legacy_markers_authorise_nothing |  |
| Claude-gates | C4 | Hard-coded checkout paths with `sys.path.insert(0, …)` | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | C5 | Lazy imports inside functions | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | C6 | [UNSEEN] Story ledger keyed on statements | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | X1 | No size check before sendVideo | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | X2 | No retry on 429 or timeout, and the token can leak | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | X3 | Caption truncation is off by one | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | X4 | The publish kit is built after both videos are sent | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | X5 | The legacy path sends the 16:9 only, captioned "gates PASS" | CONFIRMED-FIXED | f3 test_the_legacy_send_path_is_gone |  |
| Claude-gates | X6 | [UNSEEN] yt-dlp | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | X7 | [UNSEEN] ElevenLabs | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | X8 | The GPU is shared outside the lock | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | X9 | Ten-second ffprobe timeouts and an unguarded `float()` | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | A1 | G4 uses a Haar frontal cascade | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | A2 | The shoutout "circle" check cannot fail | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | A3 | G2's "red" includes Bitcoin orange | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | A4 | G8 compares incomparable frames | NOT REPRODUCED for the production wiring: 9:16 G8 sources are the reframed vertical clips | f5 test_g8_9x16_v2f_passes_through_the_production_wiring_at_its_floor |  |
| Claude-gates | A5 | Zero-margin thresholds from one reference | CONFIRMED-DEFERRED: the calibrated floors are the reference's measured values | f5 test_g8_9x16_v2f_passes_through_the_production_wiring_at_its_floor (pins clip_03 = 10.84 = floor) |  |
| Claude-gates | A6 | G3c measures after the fade | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | A7 | G14 forgives offsets and cannot see lip-sync | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | A8 | G10 runs only for registry `has_chyron` channels | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | A9 | G15 sampling and avatars | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | A10 | [UNSEEN] Content shape | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | A11 | G5's 60 s floor | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | V1 | G1 is a tautology, and it is empty for this format | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | V2 | G6 passes on nothing | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | V3 | G13's sign-off block is skipped when the text is empty | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | V4 | G3 and G3b skip silently when `last_word` is absent | OPEN | f4 [G3b talking head with no expected last word] **XFAIL** R-13 |  |
| Claude-gates | V5 | Fail-open branches | OPEN | f4 vacuity probes **XFAIL** R-13 / R-14 / R-15 + release backstop |  |
| Claude-gates | V6 | Parity | OPEN | UNCOVERED | G11 MONITORING |
| Claude-gates | V7 | No shoutout segment | OPEN | f4 [G12 no shoutout / G15 no shoutout] (explicit skip = SKIPPED) |  |
| Claude-gates | V8 | `gate_status` has no required-row list | CONFIRMED-FIXED | f3 inventory mutations |  |
| Claude-gates | V9 | "no waivers" is a string constant | CONFIRMED-FIXED | f3 test_a_required_row_that_is_not_exactly_pass_refuses['PASS (waived)', 'WAIVED', ...], test_a_pack_without_vision_or_incomplete_refuses |  |
| Claude-gates | V10 | Pack "complete" ignores the visual verdict | CONFIRMED-FIXED | f3 test_a_pack_without_vision_or_incomplete_refuses |  |
| Claude-gates | P1 | The lock fd is inherited by children | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | P2 | The run dir is scraped from the log by regex | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | P3 | A hold, a crash and a quiet day look the same | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | P4 | Exit 0 delivers regardless of `gate_status` | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | P5 | Non-atomic writes | CONFIRMED-FIXED | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | S1 | Compounding thresholds | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | S2 | Expensive disqualifiers run only after the render | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | S3 | [UNSEEN] The free Bitcoin screen admits off-brand stories | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-gates | S4 | Duplicates and stale stories | OPEN | UNCOVERED | outside the five families (selection logic / dates / ops / MONITORING gate / GPU path) |
| Claude-select | T1 | Verbatim check has zero tolerance for the model's own clean-up (5% vs 5 percent, sell-off  | OPEN | f1 TestQuoteVerification::test_a_compound_name_written_apart_is_the_same_quote **XFAIL** R-19 |  |
