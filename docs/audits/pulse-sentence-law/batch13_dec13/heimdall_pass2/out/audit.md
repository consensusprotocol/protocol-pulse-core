# Heimdall audit

**Question:** Second pass of batch 13 (audit fixes) for the editorial word pass punctuation law L-e. NEW since the first audit: (U-1, unanimous cross-LLM) punctuation.transfer_case copies a reference word's sentence-initial capital onto the aligned verbatim word when the word before it (in the result) ends a sentence (sentence_law.is_terminal) and the reference capitalises it; never the first word, never lowercases, word keys never change; ensure(case=True) is used only by transcript_store.punctuate (editorial word pass); select_passages keeps case=False. (Heimdall F1) transcript_store._load keeps one Whisper model on GPU0 at a time (loading distil-large-v3 drops the large-v3 reference and vice versa) because the word pass's GPU0 arbitration only proves 7 GB free. Find: correctness bugs, any way the capital transfer could create a sentence start the reference decode did not have, fail-open paths, races, and tests that do not test what they claim. Report at most 8 findings with quoted evidence.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0171
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
