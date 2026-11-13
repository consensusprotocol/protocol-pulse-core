# pp-selectid audit 0816 (RULING 53: a speech re-posted by a second channel is one moment): cycle 1 consensus

**Run.** Verdicts:
- grok: "SHIP: yes";
- glm: "yes with conditions" (no P0);
- qwen: "SHIP: NO", on one P0 that holds.

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | qwen P0: text-only alignment merges two DIFFERENT short statements that differ in one key word ("Bitcoin is the new gold. It is digital." vs "...silver...": 7 of 8 words align in order) | The match is now what ruling 53 says: "time-aligned overlap of 80 % of the words". A word counts only when it matches in order (difflib's blocks) AND its start time keeps the one clock offset of the pair: within REPOST_TIME_TOL_S (0.3 s) of the median start difference. A re-post is the same audio, so every matched word keeps its spacing; two speakers saying similar words do not. My K1 reading had dropped the "time" part; it is restored. Without a word record with timings, only EQUAL text merges, so nothing merges on a guess. Tested: the gold / silver pair at two rhythms is not merged; a re-post with 3 extra words at a 97.5 s offset is merged (15 of 15 time-aligned). Measured on the 07:14 inputs: the same 2 CNBC / Strategy copies (39 of 39 words time-aligned; one equal text). |
| F2 | qwen P1: a published_at with no zone was "never preferred", so a naive original could lose to an aware copy | A time with no zone is read as UTC, the pipeline's own clock. An unreadable time is never preferred (tested both ways). |

## Refuted or recorded

| # | claim | the code |
|---|---|---|
| R1 | glm P1-1: the tie-break "lower moment id" is not implemented; min keeps input order | at() returns (0, timestamp, moment_id): on equal times the tuple's third element decides, so the lower id wins whatever the input order. |
| R2 | glm P1-3 / qwen P1-2: union-find merges a chain A~B, B~C even when A and C do not match | Intended: one speech re-posted twice is one group, and its earliest publisher is kept. qwen marks it "Correct". |
| R3 | glm P1-5 / qwen P1: O(n^2) pairs | The same-channel skip and the multiset pre-check (an upper bound on the aligned words) prune most pairs. Measured 2.3 s on 308 moments, about 1 s on the ~170 usable ones a build passes. Recorded; no change. |
| R4 | glm P1-4: STAND_ALONE and the trims run on the de-duplicated moments | Intended (K2): a copy makes no trimmed variant either. out["usable"] keeps its pre-duplicate count, as tested. |

## Verification

- test_medley 86 OK (the ruling-53 tests rewritten for the time-aligned rule); every other suite OK.
