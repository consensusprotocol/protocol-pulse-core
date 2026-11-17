# Heimdall audit

**Question:** Review this diff (pipeline/canon.py, pipeline/pinned.py). ORCHESTRATOR RULING 142 (14:32 ET Nov 17): "(1) a hyphen right after a number and a space, before a digit, is never a sign ('24/7/365') ... re-judge Yahoo Finance f0a51c45 from its cached readings. (2) L-v 2 'bitcoin' against 'bitcoin's': a possessive or plural ending is a word-form pair like any other: ruling 131 (A)'s two-of-three decides it and the sealed text takes that reading; all three differing still holds. Apply to Natalie Brunell feb4b72f from cache." Batch 110 (live) implemented (1) in canon._prepare as _NUM_HYPHEN = re.compile(r"(\d\s+)-(?=\d)") on the WHOLE text, and (2) as canon.word_form (one token differing only by 's, s', ', s). Re-judged, f0a51c45 still held: pinned._majority_text maps tokens to words with canon.canon_spans (word by word: the word '-7,' alone read 'minus 7') and requires them equal to canon_tokens of the text ('24 7'), else 'the settled reading cannot be written'. feb4b72f still held: its "Bitcoin's" is the CONTRACTION of 'Bitcoin is' (run 'Bitcoin is a responsibility', approved "Bitcoin's a responsibility"), a 1-token against 2-token pair. This diff (batch 112): canon_spans drops the hyphen of a word '-<digit>...' that follows a word ending in a digit (the whole-text rule, word by word); word_form also takes [t + "'s"] against [t, 'is'] or [t, 'has'] (no digit in t); and pinned.post_live_offset (batch 111, unmerged) aligns through canon_spans instead of an ad-hoc normaliser (the canon law: every comparison goes through canon).
FACTS (unchanged): canon_spans(words) -> [(token, first word index, last word index)] and joins a lone '-' with a following number word unless the previous word ends in [\d.,%] (a range); _prepare applies, in order, _NUM_HYPHEN, _CUR_SIGN, _PLUS, _SIGN_SPACED, _SIGN, then every '-' becomes a space; law L-v 2: a number, a negation or a name whose letters differ always holds; 131 (A) runs only on pairs not held by L-v 2's critical check, and word_form pairs are exempt from that check.
Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.
CHECKS:
H1. For every word list, do canon_spans' tokens now equal canon_tokens(' '.join(words)) in the '<number> -<digit>' case, and do real signs ('-5%' after a word, '(-$40M)', '-$5' after a number, 'is - 5%') keep 'minus' in both?
H2. Can the contraction rule make a number, a negation, a different name, or a different verb ('was', 'had') a word form?
H3. Can any input raise in canon_spans, word_form or post_live_offset's token helper?
H4. Does anything else change behaviour?

**Panel:** gptoss  |  **Cost:** $0.0006
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
