# Batch 54 cycle 2: consensus and what was done

- C1 [low]: the failed-conversion test now also asserts that no sources_bt601/ original was created (nothing is moved before the encode succeeds).
- glm F1 [low, 1 vote], a re-run loses the original tags: no. A re-run skips the already-BT.709 source, so to_bt709 returns no record for it, and the merge keeps the first record, with its "from" tags.

- Found by the new assertion itself: to_bt709 created sources_bt601/ before the encode, so a failed conversion left an empty directory. Fixed (0340f048): the directory is created only after the encode succeeds.
