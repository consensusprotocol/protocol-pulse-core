# Heimdall audit

**Question:** Review this diff (orchestrator RULING 135, 10:50 ET Nov 17), verbatim in part: "a COMPARISON CANON applied to all three readings before any pair is compared (the lock's logic after that is unchanged, ruling 131 included): (a) case, punctuation and apostrophes ignored; (b) SEGMENTATION ignored: readings whose letters are identical once spaces and hyphens are removed are the same ('itrust capital's' = 'I trust capital's' = 'iTrustCapital's'); this holds for names too, a name is disputed only when its LETTERS differ; (c) spoken reductions equal their full form, a closed list in canon.py: kinda/kind of, sorta/sort of, gonna/going to, wanna/want to, gotta/got to, lemme/let me, gimme/give me, 'cause/cuz/because, 'em/them, ya/you, yeah/yep/yes stay distinct from no; add none without my ruling; (d) NON-LEXICAL tokens are fillers wherever they sit: um, uh, er, ah, hm, hmm, mm, mhm, and any stray single consonant letter one reading alone hears; a filler heard by one reading of three is dropped ... even inside 3 words of an edge. STILL HOLDS, unchanged: numbers (save the currency canon), negations, a name whose letters differ, any content pair where all three differ."

FACTS (unchanged code, not in the diff):
- canon.canon_tokens lowercases, strips punctuation, joins spelled and grouped numbers into digit tokens, writes '$40 trillion' as '40000000000000 dollars'; it keeps apostrophes ("don't", "money's").
- pinned.adjudicate_lock: ops = the non-equal SequenceMatcher opcodes of run vs approved canon tokens; (B) drops currency-only pairs; then the critical check (_lv2_critical: digits, negations incl. any "n't", ordinals, capitalised names) raises PinError on the remaining pairs BEFORE the second recogniser is asked; then the vote (ruling 17 / 18 / 84 (b) / 131 (A)).
- lock_precheck.as_spoken compares the lock's canon tokens with the second recogniser's; each remaining difference gets ruling 84's class or HOLDs.
- word_diff.diff is G18's comparison of the final's decode with the lock text / source span.

Cycle 2: try to BREAK it. Report ONLY a defect you can show with CONCRETE readings traced through the diff's code. Keep each "issue" under 80 words. If you cannot break it, answer PASS with no findings.

BREAK-IT TARGETS:
T1. Two readings that differ in WHAT WAS SAID (a word, a number, a negation, a name's letters) but that same_words calls equal, so the lock passes them unexamined.
T2. A reduction or filler rule that swallows a real word ("cause" the noun, "em", "ya", a one-letter word such as "a" or "I", a product named "Q").
T3. A pair same_words calls equal that the critical check would have held, now passing (a number or a negation hidden inside a segmentation or reduction).
T4. Readings that are the same words by the ruling but that the diff still holds.

**Panel:** qwen27b  |  **Cost:** $0.0193
## Consensus findings (majority of panel agrees)
- **[high] pipeline/canon.py:286** The noun 'cause' is indistinguishable from the contraction "'cause" after apostrophe-stripping, so both expand to 'because'. The ruling's closed list authorises only "'cause/cuz/because" (contraction); the noun 'cause' is not a spoken reduction of 'because'. A lock comparing 'the cause of the fire' vs 'the because of the fire' passes as spelling-only.
  - evidence: `t = str(t).replace("'", "")
        out += list(REDUCTIONS.get(t, (t,)))`
  - fix: Look up REDUCTIONS on the original token (before apostrophe-stripping) and key the contraction as "'cause" so the noun 'cause' is not expanded. E.g.: out += list(REDUCTIONS.get(t, (t,))) before the replace, then strip apostrophes only for non-reduction tokens.
  - raised by qwen27b:F1; agree: qwen27b
- **[medium] pipeline/canon.py:303** nonlexical() drops every single consonant unconditionally, but the ruling says a stray consonant is a filler only when 'one reading alone hears' it. A letter-name (e.g. brand 'B') present in 2 of 3 readings is a real word; same_words(["b"], []) returns True and the lock passes the missing letter unexamined.
  - evidence: `return tok in FILLER_TOKENS or (len(tok) == 1 and tok in CONSONANTS)`
  - fix: same_words cannot see the third reading, so the 'one reading alone' guard must be applied at the call-site (adjudicate_lock / as_spoken / word_diff) where all three readings are available: only treat a single consonant as non-lexical if it appears in exactly one of the three readings.
  - raised by qwen27b:F2; agree: qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
