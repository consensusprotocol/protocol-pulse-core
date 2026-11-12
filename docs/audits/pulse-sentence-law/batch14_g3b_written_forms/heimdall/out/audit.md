# Heimdall audit

**Question:** Batch 14, law L-g (2026-11-11). The Law 22 re-render of the approved v2f reference was byte-identical but gate G3b (DEC-12f: three Whisper readings of each clip tail with 1.5 s context; the EDL's last word must be one of the last two words heard in >= 2 of 3 readings; the EDL's next source word must not be heard after it in a majority) failed the approved 9:16 clip_02 whose last word is 'dollars' ('... above 40 trillion dollars.'): readings 'above $40 trillion | above $40 trillion | above $40 trillion dollars' (1/3). The fix: qa_gates._g3b_words reads ASR symbols as the spoken words in spoken order ('$40 trillion' -> '40 trillion dollars' including scale words, '$74,000' -> '74000 dollars', '50%' -> '50 percent'), drops thousands separators and trailing full stops, keeps decimals ('1.66') and internal stops ('u.s'), and gate_g3b normalises the EDL's last word and next word with the same function. Vote rule and thresholds unchanged; G17c still compares every edge word with the source. Find: correctness bugs, any way a clip whose last word is NOT heard could now pass (false accept), a next-word leak that could now go unseen, tokenisation regressions against the old rule (which replaced . , ? ! with spaces), and tests that do not test what they claim. At most 6 findings, quote evidence.

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0244
## Consensus findings (majority of panel agrees)
- **[high] segment_v1/qa_gates.py:0** Next-word leak check only examines the first word of next_source_word, so later words in a multi-word next source phrase can leak unseen; this contradicts the comment 'check ALL next words'.
  - evidence: `# R2-03: check ALL next words including short ones like "So"
edl_entry = edl_clips.get(label, {})
nw = _g3b_words(edl_entry.get("next_source_word", "") or "")
next_word = nw[0] if nw else ""`
  - fix: Use all words from nw in the leak check, e.g. test whether any word in nw appears after the expected last word.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[medium] segment_v1/qa_gates.py:0** Comma removal without replacing with a space merges tokens, a regression from the old rule that replaced commas with spaces. For example, 'hello,world' becomes 'helloworld' instead of 'hello world'.
  - evidence: `toks = text.lower().replace(",", "").replace("?", " ").replace("!", " ").split()`
  - fix: Replace commas with spaces, or only strip commas that are thousands separators between digits.
  - raised by deepseek:F2; agree: deepseek, qwen27b
- **[medium] segment_v1/qa_gates.py:0** Abbreviated scale symbols in _G3B_SCALE are not expanded to spoken words. For example, '$40M' becomes ['40m','dollars'] instead of ['40','million','dollars'], so an EDL last word of 'million' would fail.
  - evidence: `_G3B_SCALE = {"hundred", "thousand", "million", "billion", "trillion", "k", "m", "b", "bn"}
...
if t.startswith("$") and len(t) > 1:
    t, dollars = t[1:], True`
  - fix: Expand k/m/b/bn to thousand/million/billion when they follow a dollar amount.
  - raised by deepseek:F3; agree: deepseek, qwen27b
- **[low] segment_v1/qa_gates.py:0** When the ASR already includes 'dollars' after a dollar amount, the function inserts a duplicate 'dollars'. For example, '$40 trillion dollars' becomes ['40','trillion','dollars','dollars'], which can distort the last-two-word window and leak checks.
  - evidence: `if dollars and t not in _G3B_SCALE:
    out.append("dollars")
    dollars = False
...
if t:
    out.append(t)`
  - fix: Only insert 'dollars' if the current token is not already 'dollars'.
  - raised by deepseek:F4; agree: deepseek, qwen27b
- **[high] segment_v1/qa_gates.py:399** Comma tokenisation regression: old code replaced ',' with a space (splitting 'well,known' into two tokens); new code removes ',' with no space, merging adjacent words into one unrecognisable token. Any EDL last_word or ASR reading containing a comma without a following space will produce a fused token that cannot match the other side.
  - evidence: `toks = text.lower().replace(",", "").replace("?", " ").replace("!", " ").split()`
  - fix: Use .replace(",", " ") (space, as before) for general commas, then post-process numeric tokens to strip internal spaces (e.g. re-join '74 000' → '74000') only when the pattern is a thousands separator (digit-comma-digit with no space on either side in the original).
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[medium] segment_v1/qa_gates.py:411** When a single token carries both a '$' prefix and a '%' suffix (e.g. '$50%'), the '$' branch sets dollars=True, then the '%' branch appends the number and 'percent' and `continue`s without clearing the flag. The next non-scale token will trigger a spurious 'dollars' insertion, corrupting the word list and potentially causing a false accept or false reject in the majority vote.
  - evidence: `if t.startswith("$") and len(t) > 1:
            t, dollars = t[1:], True
        if t.endswith("%") and len(t) > 1:
            out += [t[:-1], "percent"]
            continue`
  - fix: In the '%' branch, set `dollars = False` before the `continue` (a percentage does not imply a dollar amount), or restructure so the two symbol handlers are mutually exclusive.
  - raised by qwen27b:F2; agree: deepseek, qwen27b
- **[medium] segment_v1/qa_gates.py:476** next_word leak check now inspects only the first token of the processed list (nw[0]). If next_source_word is a multi-word phrase (e.g. 'So what'), the old code passed the full string to _leak; the new code checks only 'so'. A leak of 'what' (the second word) would go undetected, allowing a clip that runs into the next sentence to pass check 2.
  - evidence: `nw = _g3b_words(edl_entry.get("next_source_word", "") or "")
        next_word = nw[0] if nw else ""`
  - fix: Pass the full `nw` list to the leak predicate and require that NONE of the tokens appear after the last word in a majority of readings, or at minimum check all tokens rather than only nw[0].
  - raised by qwen27b:F4; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F3 [high] False-accept vector: the '$' → 'dollars' expansion synthesises a word the speaker may never have uttered. If ASR writes 'above $40 trillion' as a currency notation while the speaker said only 'above forty trillion', the gate now sees 'dollars' in the last-two positions and passes check 1 for an EDL last_word of 'dollars'. The old rule (pure punctuation split) would have correctly failed this reading because 'dollars' was absent from the heard tokens. (agree: 0)
- qwen27b:F5 [medium] The unit test for _g3b_words asserts only the happy-path expansions. It does not test: (a) a comma-without-space input ('well,known') that exposes the F1 regression; (b) a '$'+'%' combined token; (c) the edl_last extraction when last_word itself contains a symbol (e.g. last_word='$5' → edl_last='dollars'); (d) a must-FAIL case where the ASR writes '$40 trillion' but the EDL last_word is a non-dollar word, proving the gate still rejects. The integration test (test_v2f_vertical_dollars_tail_passes) covers only the pass path. (agree: 1)
- qwen27b:F6 [low] rstrip('.') strips only trailing dots, so 'U.S.' becomes 'u.s' (one token) whereas the old replace('.',' ') produced ['u','s']. If the EDL last_word or an ASR reading uses the two-token form 'u s' (e.g. Whisper splitting on the period), the two sides will never match, causing a silent false reject on clips ending in an abbreviation. (agree: 0)

## Added in cross-examination (not voted on)
- none
