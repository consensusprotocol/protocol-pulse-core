# Audit 20261114_1349 (ruling 102, STEP_A_UNAVAILABLE must never end a clip; the 13:02 $19 stop; glm's H1 and M2 from audit 20261114_1246), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes. Its five <medium> notes each say what it verified, with no breaking sequence.
- qwen3.8-27b: SHIP no. One <critical>, refuted below from the diff's own line. One <high>, documented
  (ruling 87's 40 minutes). One <medium>, taken: a new test.
- glm-5.3-flash (826 s, finish=length at its 24,000 cap, so no SHIP line): no <critical>. Its one <high>, H1, it
  downgrades to medium itself. One point taken (M3: the pin note's words); the rest documented.

## Refuted

- **qwen <critical>: "confirm_ahead excludes every family, so it never asks anyone".** Its quote of the code is not
  the code. The diff computes BOTH sets by the back-end's VENDOR (package.py, confirm_ahead):
  `hf = {b.family for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}`.
  - Grok's family "grok" is therefore never in hf, and Grok's vendor "xai" never in hv.
  - The test asserts the exact sets: wf == {deepseek, glm, gemini, gemma}, with no "grok".
  - Taken from the same point: the test checked only the sets. A new test,
    test_through_the_real_chain_grok_answers_ahead_and_no_fallback_is_ever_asked, runs a real providers.Router over
    the five legs with the real prescreen and step_a:
    - every new moment gets Grok's verdict;
    - with Grok down, none does;
    - deepseek, glm, Gemini and the judge are asked 0 times.

## Taken

- **glm M3, the pin note's words.** The note said "no faster leg of step A's SECOND family answered". In Plan B (ruling
  87), the first screen's chain ends in the local judge too, so a FIRST verdict can be the judge's, and the note would
  then misstate why. The rule text now holds in both cases: "ruling 87's last resort: no faster leg answered, so the
  local gemma3:27b on GPU0 (the integrator's judge service) gave this step-A verdict (the last leg of step A's second
  family under ruling 102, or of Plan B's chain under ruling 87)". The test asserts both parts.

## Documented, no change

- **qwen <high> / glm M1, the local judge can hold a build up to 40 minutes, and a moment can be held build after
  build.**
  - The 40 minutes is ruling 87's own allowance (LocalJudgeBackend.WAIT_S 2400, unchanged); ruling 102 names the
    judge as the last leg.
  - A moment held every build stays visible: each build's RULING 102 line counts and names the held moments, in
    capitals on STATE line 1, so the orchestrator sees a repeat.
  - The ruling says held, never refused, and retried next build. No counter is ruled.
- **glm M2, mixed reasons hiding a refusal.** Within this diff each moment's step-A reason list has one entry:
  - prescreen's chunks partition `todo` (`[todo[i:i + batch] for i in range(0, len(todo), batch)]`), so a moment is in
    exactly one chunk;
  - second_screen and the writers' re-screen REPLACE the list.
  - A mixed list (one held, one refusal) reads as refused (`all`), and the test pins it.
- **glm H1 (its own downgrade to medium), the exclusion sets come from every back-end in the router.** A wider set only
  excludes more. The confirm-ahead walks the step_a_second chain, whose only xAI leg is Grok, so only Grok can answer
  ahead (the new real-chain test). A second xAI leg in that chain would need a ruling anyway.
- **glm M4, a sequential plan reports its confirm leg.** This is a report field. Parallel needs why == None, which needs
  a Heimdall lead, a wait over 10 minutes AND a usable confirm leg (the plan test asserts each).

Verification after the changes:
- test_ruling_102.py: 17 tests.
- In dev09: test_ruling_102, test_medley and test_spotlight, 258 passed, network blocked.
- The mutation check: 30 of 30 killed in one run (C1-C3, H1-H8, R1-R3, L1-L5, A1-A2, P1-P5, S1-S3, M2). Its first run
  had H7 surviving: the writers' re-screen's default reason was not reached by any test. A test was added before this
  cycle.
- The question said 31 mutations; there are 30.
