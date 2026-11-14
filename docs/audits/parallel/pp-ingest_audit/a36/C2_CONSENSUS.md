# A36 WIDEN (the orchestrator's 09:02 ruling, mine-hook/4), cycle 2: consensus

Reviewers (Heimdall), on the whole change (af298eb9..7c437fec) with C1_CONSENSUS.md: glm-5.3-flash (262 s, $0.005):
"Yes, with one condition" (P0 / P1 none); muse-spark-open (286 s, $0.028): "Yes. Ship c1141fff (with 7c437fec). No
conditions"; qwen3.8-27b (307 s, $0.009): "Yes" (the condition: run hooks --rerun, an operational step). Cycle 2:
$0.042. All three verified the predicate on every input, the version bump and cache, the stats and the C1 fixes.

## Fixed
- C2-1 (glm's condition, P2-1 "N7"): the claim that the version bumps are free where the prompt did not change rested
  on facts each tested alone. A golden sha256 of a solo episode's hook prompt (de1e0f26..., verified against the
  mine-hook/2 code on the same window) now pins it: a change to HOOK_PROMPT's text or the solo max_h fails
  test_mine test_a_solo_episodes_hook_prompt_is_the_one_asked_before_so_its_cached_replies_answer_it.
- C2-2 (glm N2): the comment at the crashed-spotlight version says the suffix is what makes --rerun ask again.
- C2-3 (qwen P2): the rounding is stated where the constant is (mine.CONVERSATION_TPM: compared with episode_measure's
  rate, rounded to 2 decimals). The design's cycle 1 wording ("0.295 reads as 0.3") was not exact (in binary floating
  point round(0.295, 2) is 0.29): it now says only that the rounded rate is compared. No boundary test is added: the
  boundary is the comparison on the rounded value, already tested at 0.29 / 0.3.
- (The law test caught a model name in the new comment: L-x bans them in code, comments included; removed.)

## Recorded
- glm P3: the episode columns are left NULL on a waiting pass (latent); max_n_spotlight is a constant 2 (latent);
  the "not measured" bucket is legacy and empties itself; muse's float-count note is unreachable and fails open.

Suite: tests/ingest 317 passed (with the next change, A19, still uncommitted in the tree). Audit total: c1 $0.063 +
c2 $0.042 = $0.105 (Heimdall).
