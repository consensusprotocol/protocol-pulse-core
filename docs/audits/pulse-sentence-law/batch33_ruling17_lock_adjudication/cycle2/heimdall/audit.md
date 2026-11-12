# Heimdall audit

**Question:** Batch 33 cycle 2 = RULING 17 after cycle 1's consensus fixes (pinned.adjudicate_lock; the diff is the function as committed). Cycle-1 consensus: F2 (critical) a deletion read by the second recogniser as a different word was taken as agreement with the approved text; F3 (medium) ordinals / grouped numbers were not numbers. Fixes: the second recogniser 'reads' a side's words at a difference only when those words and one neighbour on each side are all aligned (in-order SequenceMatcher equal blocks) AND consecutive in its text, so nothing else stands between them (a deletion read as another word is 'neither' -> HOLD); any token containing a digit, or an ordinal / fraction word, is a number (L-v 2: holds before any vote). F1 (not agreed) is covered by the same positional rule.
FIND: any remaining way a lock takes the approved text without the second recogniser reading exactly the approved words at every difference; any number / name / negation difference that reaches the vote; an index or boundary error in the neighbour / consecutive check (start or end of the span, insertions, deletions). Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0231
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- deepseek:F1 [critical] Boundary error in the neighbour/consecutive check: at the start or end of the span, the missing neighbour means the check does not verify that no extra words precede or follow the approved words. For an insertion at the start, idx is [0], so it only checks the first approved word is aligned, not that it is the first word in the second recogniser. If the second recogniser reads the run's extra word before it, the check still passes, and the lock takes the approved text even though the second recogniser did not read exactly the approved words at that difference. (agree: 0)
- deepseek:F2 [high] Cardinal number words like 'one', 'two', 'three' are not in LV2_ORDINALS and contain no digit, so they are not considered numbers. A difference on such a word (e.g., 'one' vs 'two') will not be critical and will reach the second recogniser vote, violating L-v 2 which says a number difference always holds. (agree: 0)
- deepseek:F3 [high] The name check only considers capitalized words that do not open a sentence. A name at the start of a sentence (e.g., 'John' vs 'Jon') is excluded, and a non-capitalized name is not detected. Such name differences reach the vote instead of holding, violating L-v 2. (agree: 0)

## Added in cross-examination (not voted on)
- none
