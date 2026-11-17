# Cycle 1 consensus (pp-selectid_audit_20261117_1330, stage 2b (1): the soft hook bar)

SEATS ANSWERED: 3 of 3. qwen3.8-27b: P0/P1 none (two P2s). gemma-4-31b-it: P0/P1 none. gpt-oss-20b: 2 P0 and 2 P1
claimed; every one is refuted below from the code and the passing tests.

## gpt-oss's claims
1. [P0] "the mark is set after hook_own runs, so no flag": REFUTED. hook_own is not run once and stored. Every reader
   calls it when it reads: _can_open for rated_open (package.py:3342, AFTER the mark), the clips-alone verdict (medley,
   :2153), coherence (:2089), rulings 62 / 63, hook_weak and the coherence floors in the line-up loop. All run after the
   mark, which is set right after the ratings are attached. The end-to-end test through test_medley's Rig (the real
   build) seals with the medley row FLAGGED in the exact sentence, and mutation H1 (the mark not opening) is killed.
2. [P0] "the inventory never flags": REFUTED, for the same reason. The verdict's hook_own (medley stub and real medley()
   both copy hook_own(segs[0])) carries "flagged", and the end-to-end test asserts the FLAGGED row and review_flags_of.
3. [P1] "a hook not under the bar may be marked": REFUTED. The marked set is filtered by hook_bar_under(m), which is None
   for a passing hook; hook_order only orders that set. Tests: the best-two test; mutations H6 and H12 are killed.
4. [P1] "vision is paid for every opener before marking": REFUTED. hook_ratings is the Grok hook RATING (unchanged, cached
   per moment), not vision. Vision is see(rated_open) at :3343, AFTER the mark; rated_open is can_open: the passing hooks
   (as before) plus at most HOOK_SOFT_MAX = 2 marked ones.
5. [P2] duplication between hook_bar_under and hook_own: DECLINED. hook_bar_under is the one source of the soft detail;
   hook_own calls it.
6. [P3] "hook_rating popped twice": REFUTED (one pop at the hook stage's start; the later line assigns the new rating).
7. [P3] the test pins HOOK_SOFT_MAX == 2: BY DESIGN (the ruled value is checked; the slice uses the constant).

## qwen's P2s
- hook_bar_under called up to 4 times per marked hook: DECLINED. Each call reads the per-minute cached bar (_live_bar);
  a handful of dict reads per build.
- "The opening clip" readability: by design (CLIP_PLACE, ruling 138 (3), as stage 1 and 2a's flags).

## No change from cycle 1 to cycle 2.
