# pp-selectid audit 2005 (ruling 82: the second-vendor step A's failover chain): cycle 1 consensus

- **grok:** "SHIP: yes", no P0 or P1.
- **qwen:** "SHIP: yes with conditions". Its P0s were withdrawn in its own text after tracing; two conditions.
- **glm:** "SHIP: yes with conditions". No P0; three conditions.

## Implemented

- **qwen #9:** the defensive branch (the router returns a model already skipped) now raises
  providers.ProviderError, the documented "no verdict", not the original ValueError. A caller catching ProviderError
  never meets another type from the failover path. Without failover (the first verdict's path), a bad answer still
  raises ValueError, as before.
- **glm (3):** a test pins that the off-writer re-screen receives the deadline. In the Rig, the step-A calls carry
  [None (the first screen, unchanged), 120, 120 (the second screen's two chunks of 2), 120, 120 (both off-writer
  re-screens)].

## Confirmed from the code (conditions that ask for a check)

- **glm (1) / qwen (2): avoid_model is keyed exactly as ra.backend.** providers.Router.call walks the role's chain
  by name, and `_skip(name, ...)` refuses `name in am`. The Reply it returns carries that same `name` as `.backend`
  (`Reply(text, name, ...)`), so the skip set holds exactly the names the router compares. The failover test runs
  the REAL Router (tests/providers/test_providers.router) with fake back-ends: glm is skipped on the second call,
  and qwen answers.
- **glm (2): a late answer to an abandoned call is never cached.** On DeadlineExceeded, Router.call books the upper
  bound, logs `missed_deadline` to the Heimdall evidence file (item 55), and `continue`s. `_record` (the reply cache)
  runs only after an answer returned inside the deadline and was non-empty. prescreen stores a verdict only after
  step_a parsed it (an exception in a chunk is STEP_A_UNAVAILABLE, never stored). Unchanged code.
- **glm P1-5:** the first verdict's step A stays unbounded. That is the ruling's scope ("the second-vendor step A"),
  and the comment says so.

## Recorded (no change)

- **glm P1-3:** the all-three test spends the chain through router-level and contract failures together. Each is
  also exercised alone (deepseek down; glm out of contract).
- **qwen #10:** the test helper P_ProviderError imports at call time. Style.
- **Cost:** an abandoned call books its upper bound (about $0.24) on ruling 48's ledger, by the existing rule.
  Batches of 2 are what keep calls inside 120 s.

## Suites

All 15 OK (medley 160, ledger_build 37, ...).
