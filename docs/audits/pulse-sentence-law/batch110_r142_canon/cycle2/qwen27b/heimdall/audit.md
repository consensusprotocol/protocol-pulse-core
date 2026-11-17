# Heimdall audit

**Question:** Review this diff (pipeline/canon.py, pipeline/pinned.py, pipeline/lock_precheck.py). ORCHESTRATOR RULING 142 (14:32 ET Nov 17), verbatim: "(1) THE CANON FIX IS APPROVED: a hyphen right after a number and a space, before a digit, is never a sign ('24/7/365'). ... (2) L-v 2 'bitcoin' against 'bitcoin's': a possessive or plural ending is a word-form pair like any other: ruling 131 (A)'s two-of-three decides it and the sealed text takes that reading; all three differing still holds." Law L-v 2 (unchanged): a number, a negation, or a name whose letters differ ALWAYS holds. Ruling 131 (A) (unchanged): per differing pair of the run decode and the approved text, the second recogniser's reading decides with one of them; the run's reading only at least 3 tokens from an edge; all three different holds.
FACTS (unchanged code): canon._prepare turns text into canonical tokens; _SIGN / _SIGN_SPACED / _CUR_SIGN / _PLUS write a sign as 'minus' / 'plus' (GPT-cut F04: -5% != +5%); afterwards every remaining '-' becomes a space. canon_tokens keeps an apostrophe inside a token ("bitcoin's") and folds the curly apostrophe. In pinned.adjudicate_lock, ops are the SequenceMatcher opcodes of the run's tokens r and the approved text's tokens p; before this diff any op holding a critical token (_lv2_critical: a digit, a negation, an ordinal, or a capitalised mid-sentence word = a name) raised PinError (law L-v 2) before the 131 (A) vote.
Cycle 2: try to BREAK it. Report ONLY a defect you can show with CONCRETE texts (run decode, approved text, second reading) traced through the diff's code. Keep each "issue" under 80 words. If you cannot break it, answer PASS with no findings.
TARGETS:
T1. A spoken minus sign or negative number that now compares equal to a positive one.
T2. A number, negation or different name that now passes the lock through the word-form exemption.
T3. A word-form pair sealed without two of three readings agreeing.

**Panel:** qwen27b  |  **Cost:** $0.0107
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
