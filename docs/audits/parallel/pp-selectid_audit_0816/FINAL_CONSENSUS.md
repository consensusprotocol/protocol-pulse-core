# pp-selectid audit 0816 (RULING 53): final consensus after cycle 2

**Cycle 2:** no P0 from any reviewer. qwen: production ready ("the Cycle 1 P0 is resolved by the _time_aligned
logic"). grok and glm: "yes with conditions".

## The conditions

| # | condition | disposition |
|---|---|---|
| C1 | glm P1-1: one clock offset per pair leaves a copy spliced mid-speech unmerged (two offset clusters); test it, or fix it | TESTED and KEPT, with the reason written in reposted_once's docstring. One offset per matched block would merge two different speakers: qwen's cycle-1 pair ("...gold..." / "...silver...", rhythms 0.40 s and 0.25 s per word) stays within 0.3 s of each block's own median offset (block 1 differences 0, 0.15, 0.30, 0.45, median 0.225). That is the false merge cycle 1 removed. A spliced copy is not one audio at one clock, and if it reaches a line-up the package's duplicate check refuses it. The new test asserts a copy with 7 words spliced in after word 5 is not merged. |
| C2 | glm P2-1: the pre-check comment must say the bound holds transitively | Done: shared words >= words in matched blocks >= the time-aligned ones. |
| C3 | glm P2-2: state that the 80 % counts the words that have timings | Done, in the docstring. |
| C4 | grok / glm P2: build the root -> kept map once, not a scan per copy | Done (kept_of). |
| C5 | glm P2-3: the Python floor for fromisoformat on str(datetime) | published_at arrives as a JSON string in every path that builds moments. Python 3.10's fromisoformat also reads isoformat()'s output with a space separator, so a datetime's str() parses as well. No change. |
| C6 | grok P2: the whole-text canonical form vs the per-word keys | They serve two separate tests: equal text, and the alignment keys. Neither is compared with the other. No change. |

## Verification

- test_medley 86 OK; every other suite OK; regression_test.sh is run on the worktree before the commit.
- Real data (the 07:14 inputs, 308 moments): 2 copies, both Strategy (MicroStrategy) re-posts of CNBC Television's
  interview (39 of 39 words time-aligned; one equal text). CNBC's are kept and credited.
