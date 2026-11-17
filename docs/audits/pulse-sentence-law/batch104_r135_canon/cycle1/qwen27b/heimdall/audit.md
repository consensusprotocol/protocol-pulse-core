# Heimdall audit

**Question:** Review this diff (orchestrator RULING 135, 10:50 ET Nov 17), verbatim in part: "a COMPARISON CANON applied to all three readings before any pair is compared (the lock's logic after that is unchanged, ruling 131 included): (a) case, punctuation and apostrophes ignored; (b) SEGMENTATION ignored: readings whose letters are identical once spaces and hyphens are removed are the same ('itrust capital's' = 'I trust capital's' = 'iTrustCapital's'); this holds for names too, a name is disputed only when its LETTERS differ; (c) spoken reductions equal their full form, a closed list in canon.py: kinda/kind of, sorta/sort of, gonna/going to, wanna/want to, gotta/got to, lemme/let me, gimme/give me, 'cause/cuz/because, 'em/them, ya/you, yeah/yep/yes stay distinct from no; add none without my ruling; (d) NON-LEXICAL tokens are fillers wherever they sit: um, uh, er, ah, hm, hmm, mm, mhm, and any stray single consonant letter one reading alone hears; a filler heard by one reading of three is dropped ... even inside 3 words of an edge. STILL HOLDS, unchanged: numbers (save the currency canon), negations, a name whose letters differ, any content pair where all three differ."

FACTS (unchanged code, not in the diff):
- canon.canon_tokens lowercases, strips punctuation, joins spelled and grouped numbers into digit tokens, writes '$40 trillion' as '40000000000000 dollars'; it keeps apostrophes ("don't", "money's").
- pinned.adjudicate_lock: ops = the non-equal SequenceMatcher opcodes of run vs approved canon tokens; (B) drops currency-only pairs; then the critical check (_lv2_critical: digits, negations incl. any "n't", ordinals, capitalised names) raises PinError on the remaining pairs BEFORE the second recogniser is asked; then the vote (ruling 17 / 18 / 84 (b) / 131 (A)).
- lock_precheck.as_spoken compares the lock's canon tokens with the second recogniser's; each remaining difference gets ruling 84's class or HOLDs.
- word_diff.diff is G18's comparison of the final's decode with the lock text / source span.

Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.

CHECKS:
C1. same_words: does each of (a)-(d) hold as ruled, and does each STILL-HOLDS item still differ: a different number (incl. '12' vs '1 2'), a negation ("can't" vs "can"), a name whose letters differ, two different single letters, a content word?
C2. Is REDUCTIONS exactly the ruled closed list, and is "no" never equal to yes/yeah/yep?
C3. adjudicate_lock: is a pair dropped as spelling_only ONLY when same_words holds, BEFORE the critical check, and is every other pair still checked and voted as before? Is the digest recomputed?
C4. as_spoken, G18 (diff, _omitted_or_repeated_only) and ruling 84 (b)'s kept pairs: is the same function applied the same way, and nothing else changed?
C5. Does anything else change behaviour?

**Panel:** qwen27b  |  **Cost:** $0.0078
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
