# pp-selectid audit 2005 (ruling 82: the second-vendor step A's failover chain): FINAL consensus (cycle 2)

| cycle | grok | qwen | glm |
|---|---|---|---|
| 1 | SHIP yes | yes with conditions (its P0s withdrawn) | yes with conditions |
| 2 | Production ready: Yes | yes with conditions | Production ready: Yes (P2 conditions) |

No P0 in either cycle, and no P1 from grok or glm in cycle 2.

## Cycle 2, implemented (glm's three P2 conditions; tests and a guard only)

- A unit test of the defensive branch: a router that returns a model it was told to skip. step_a raises
  ProviderError after exactly two calls, so it never loops.
- The deadline guard is `deadline_s is not None` (0 is no longer read as "unbounded").
- The failover test resets its spy between its runs and asserts each run: the first-verdict path is unbounded
  ([None]); every call of the chain is 120 s.

FINAL_STEP.diff is the diff as committed.

## Refuted

- **qwen C2 P1-NEW-1 ("the test uses a mock router"):** tests/providers/test_providers.router (lines 47-54) writes
  a config and builds a REAL providers.Router (`P.Router(cfg, env_path=..., **kw)`). It only replaces `.backends`
  with fakes. Router.call, `_skip` (`name in am`) and the chain walk are the production code. The skip of glm on the
  second call, and qwen's answer, are the real router's behaviour.

## Recorded (P2, no change)

- qwen: the local import in the defensive branch. That branch is never taken in correct operation.
- qwen: second_screen chunks by 2 and prescreen's batch is 2. That is consistent, by design.

## Cost

Upper-bound price estimates, not on the ledger:
- cycle 1: grok $0.071, qwen $0.083, glm $0.105;
- cycle 2: grok $0.090, qwen $0.085, glm $0.066.

About $0.50 in all.
