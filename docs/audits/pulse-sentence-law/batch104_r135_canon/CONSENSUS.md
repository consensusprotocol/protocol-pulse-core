# Batch 104 (ruling 135, the comparison canon): consensus over three Heimdall cycles

Heimdall only. qwen27b and gpt-oss ran one seat each at medium. Cycles 1 and 2 ran in parallel (FAST, per the ruling); cycle 3 audited the fix's delta.

| Cycle | qwen27b | gpt-oss |
|---|---|---|
| 1 (checks C1-C5) | PASS, 9,379 tokens | F1 "spell is always empty", judged NOT a defect (below) |
| 2 (break-it T1-T4) | F1 "the noun 'cause'", judged NOT a defect (below); F2 lone letter: REAL, FIXED | F1 lone letter: REAL, FIXED (its "b vs c" example was already a difference) |
| 3 (the fix's delta, D1-D4) | PASS | PASS |

**The REAL finding (fixed in 3e36a6fb, test 8cb2e0b7).**
- same_words dropped a lone consonant on one side unconditionally. The ruling drops a stray letter only when "one reading alone hears" it, and a pair cannot see the third reading.
- Now same_words(x, y, stray=()) drops a lone letter only on the side the caller names:
  - ruling 72's second recogniser (as_spoken, stray="y");
  - G18's final decode (stray="y");
  - in the lock, none: 131 (A)'s vote decides.
- The mutations S1-S3 are killed. S3 survived until the lock-side test was added.

**Judged NOT defects:**
- gpt-oss c1 F1 quotes `ops = [... and not canon.same_words(...)]` in adjudicate_lock. No such line exists there: adjudicate_lock computes ops unfiltered and then `spell = [o for o in ops if canon.same_words(...)]`. TestRuling135.test_todays_datadash_hook asserts spelling_only == [["itrust", "i trust"]], and mutation E7 (spell = []) is killed.
- qwen c2 F1, the noun "cause". canon_tokens drops a leading apostrophe ("'cause I said" gives ['cause', 'i', 'said']), so the ruled "'cause" can only be implemented on "cause". This is documented in same_words. Two readings of one audio do not trade the noun "cause" for "because".
