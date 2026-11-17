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

**Panel:** gptoss  |  **Cost:** $0.0011
## Consensus findings (majority of panel agrees)
- **[critical] pipeline/canon.py:312** same_words incorrectly treats two single‑consonant tokens that differ as the same word. If only one side contains a single consonant, that token is removed as non‑lexical, leaving both token lists empty, so a==b returns True and the function returns True. This allows the lock to skip a real difference (e.g., "b" vs "c").
  - evidence: `    lx = [t for t in cx if len(t) == 1 and t in CONSONANTS]
    ly = [t for t in cy if len(t) == 1 and t in CONSONANTS]
    if lx and ly and lx != ly:
        return False
    a, b = [t for t in cx if`
  - fix: Add a check that returns False when only one side has a single‑consonant token or when the single‑consonant tokens differ:
    if (lx and not ly) or (ly and not lx) or (lx and ly and lx != ly):
        return False
  This ensures that "b" vs "c" (or any single‑consonant mismatch) is treated as a difference rather than ignored.
  - raised by gptoss:F1; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
