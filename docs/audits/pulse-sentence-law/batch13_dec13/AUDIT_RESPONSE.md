# Batch 13 (DEC-13 channels-first candidates + law L-e word-pass punctuation + validated-reply cache): dispositions

Audits on the actual diff (STEP.diff, 18:17): cross-LLM (GPT-4o + Gemini answered both cycles; Grok over its
$1.00/day budget since 15:55), Heimdall deepseek + qwen27b one chunk per file (heimdall/); both Heimdall models
hit their 16,384-token cap on editorial_select's indented diff, so it was re-audited on `git diff -w`
(heimdall_w/); the audit fixes got their own Heimdall pass (heimdall_pass2/).

## Implemented
- Cross-LLM U-1 (unanimous): the restoration did not carry the reference's sentence-initial capital, so a
  restored sentence start stayed lower-case and editorial start_is_boundary rejected it (Altcoin Daily's
  "even thinking about the seasonality, ..."). punctuation.transfer_case copies that capital onto the aligned
  verbatim word only when the word before it ends a sentence and the reference capitalises it (never the
  first word, never lower-cases, word keys unchanged); used by the editorial word pass only (ensure case=True
  in transcript_store.punctuate); select_passages / the PIN path and both frozen references keep marks only.
  Only start_is_boundary and the entity helper read case (grep); the cut stage, pinned.py and select_passages
  never do. start_is_boundary itself is unchanged. Must-pass: the Altcoin quote is now a valid 8.94 s hook
  window (with marks only it is rejected as lower-case; both asserted in test_punct_word_pass).
- Heimdall (editorial_select, qwen27b F2): the Bitcoin screen missed plurals ("13,597 bitcoins", "BTCs") ->
  BITCOIN_TERMS = \b(bitcoins?|btcs?)\b; tested.
- Heimdall (transcript_store, deepseek F1 + qwen27b): distil-large-v3 and the large-v3 reference could be
  resident together while the word pass's GPU0 arbitration proves only 7 GB free -> transcript_store._load
  keeps one Whisper model at a time; tested with stubbed models.

- Heimdall (punctuation.py, deepseek F1 read as a gap in the rule): transfer_case now copies a capital only
  where BOTH decodes end a sentence right before the word (the result's previous word AND the reference's previous
  word are terminal), so a reference capital that is a proper noun after the verbatim's own full stop ("he left,
  Jerome said") is not copied; the first word is never recased. Altcoin: 41 words recased (42 under the first
  rule), the quote's hook window still valid. Unvoted finding: recasing kept stripping surrounding whitespace ->
  only the first letter changes now (str.replace on the stripped word). Both tested.

- Heimdall (story_semantics, qwen27b F1; deepseek ran out of tokens, so the tool lists it unvoted): the reply
  cache key had no model identity, so re-pulled weights under the same tag would meet old replies -> the key
  includes the Ollama digest (story_semantics.model_digest, read at LocalLLM.start); without a known digest
  nothing is cached; the digest is recorded in TOPIC_SELECTION llm. qwen27b F3: concurrent writers shared one
  temp path -> a per-process temp name. Both tested (test_dec13_clusters TestLLMCache).

- Heimdall chunks (editorial_select, cycle 1): the ledger's channel list keyed by channel_id (as the screen
  counts), not by display name (deepseek, qwen27b); cluster candidates enter the record as each is labelled so a
  crash checkpoint holds them (qwen27b; there is no resume path, so forensic only).

## Found while running the suites (pre-existing at 4ca4b426, not from this batch)
- test_dec1_calibration::test_constants_are_the_reference_measurements still asserted DEC-1's G9 floors
  14.33 / 14.77; DEC-12a (orchestrator 14:45, committed in 4ca4b426) replaced them with v2f's measured luma minus
  the measured re-encode spread, 14.2857 / 14.7315 (test_g9_floor.py proves the derivation). Expectation updated.
- test_fresh::TestProtected::test_run_isolated_unchanged_from_reference_tag has failed since ae965c95 (DEC-10:
  prerender_clips applies each cut's declared fade lengths, absent = the tagged 20 / 30 ms; Law 22 re-proven
  byte-identical after it). The test now accepts exactly the tagged file or the audited ae965c95 version; any
  other change fails.
- Both were among the six failures of the 15:55 batch-12 full-suite run that were reported as CUDA
  out-of-memory; only the GPU set was re-run then. That report was wrong for these two.

## Rejected, with evidence
- Cross-LLM U-2 "editorial_select matches the f'{step}_failed' string, a stringly-typed fail-open risk": it
  does not. The word pass fails closed structurally: `if r is None or not ts.sentence_ready(r)` (the status
  string only goes into the ledger text); test_punct_word_pass asserts a failed restoration is not
  sentence-ready.
- Heimdall F1 (editorial_select) "ts.sentence_ready(None) raises TypeError": sentence_ready reads
  `(rec or {}).get("transcript_method")`; sentence_ready(None) is False (checked).
- Heimdall F3 (editorial_select) "merged candidates leak into the wire pool": _merge_event's candidates carry
  origin "same_event_merge"; the wire pool selects origin == "story_engine" only.
- Heimdall F4 (editorial_select, truncated) "the embedder is not reloaded after the GPU release":
  sm.release_gpu0_for_whisper unloads Ollama models only; the in-process Embedder stays loaded, the LLM
  reloads on its next call.
- Heimdall F2 (transcript_store) "sentence_ready trusts any whisper_words_punct record": only punctuate writes
  that method; records are write-once (_write_once: tmp + link) and hash-checked on every read
  (transcript_records); stretches still unpunctuated after restoration fail closed in the window rules, by law.
- qwen27b (transcript_store reasoning) "ensure mutates rec['words'] in place": transfer and transfer_case copy
  every word dict before editing.

- Heimdall (punctuation.py, deepseek F1) "treat the first word as a sentence start": with no sentence end
  before it, a capital at index 0 is Whisper's segment-start default, not sentence evidence; the law copies a
  capital only after a sentence end both decodes agree on.
- Heimdall (punctuation.py, deepseek F2) "settings may duplicate language / word_timestamps / initial_prompt":
  no caller passes those keys (select_passages: beam_size, vad_filter; the word pass: batch_size); a duplicate
  raises TypeError at once (fail closed), never a silent wrong decode.
- Heimdall (punctuation.py, qwen27b, rejected by the panel itself) "settings or VERBATIM treats {} as absent":
  no caller passes an empty dict.

- Heimdall (story_semantics, qwen27b F2) "the label field is still called headline but asks for a sentence;
  downstream sentence checks will reject it": no check reads the cluster headline as a sentence (it feeds
  derive_story_query and the caption); the instruction is explicit.
- Heimdall (story_semantics, qwen27b F4) "a validator that returns False would pass a cached reply": every
  validator in story_semantics raises; the live path has the same contract, so the cache adds no new path.

- Heimdall chunks (editorial_select, cycle 1), rejected:
  - "members bypass the retrieval threshold" (qwen27b, critical): by design (DEC-13 a: a cluster's evidence is
    its own statements); the counting gate is the unchanged adjudicator (CURRENT_EVENT + verbatim quote +
    independent SUPPORTS), so a member chunk that is not about the claim is simply not counted.
  - "sentence_ready(None) crashes / misjudges" (qwen27b): it is False for None (checked).
  - "the second tier is UNIVERSE_HOURS, not 72" (deepseek): by design (72 h max = the universe); the tier label
    is derived from the constant.
  - "current_ok with a None chunk id" (qwen27b): label_cluster sets current_ok only when current_quote_verified,
    which requires the chunk id among the excerpts.
  - "a resumed run loses labelled candidates" (qwen27b): select_story has no resume; checkpoints are forensic.
  - "None channel_id collapses channels" (qwen27b): transcript_store.chunks yields no chunk without channel_id and
    channel_name (batch 11, TestChunkProvenance).
  - "an unknown-age statement is not counted" (qwen27b): intended; an unknown age cannot prove a 48 / 72 h tier
    (fail closed). "decision '' falls through", "text None" (both): no producer emits either.
  - "story_ledger entries counted once" (qwen27b): the ledger is read-only during selection.

## Heimdall passes that produced no findings
- Both panel models stopped at the tool's fixed 16,384-token output cap before answering on: editorial_select
  (per-file and -w), the first fix pass (heimdall_pass2), test_punct_word_pass. editorial_select was then audited
  in three chunks (heimdall_chunks) and the fixes on a minimal diff (heimdall_pass2b); the test files are covered
  by the cross-LLM audit (Test Quality 9 / 10 and 10 / 10).

## Pending at the time of writing
- heimdall/ for punctuation.py, story_semantics.py and the two test files; heimdall_w/ (editorial_select -w);
  heimdall_pass2/ (the fixes). Appended below when they land.
