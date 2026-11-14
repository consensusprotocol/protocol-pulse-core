# Audit 0108 (rulings 85-88), cycle 2: outcome, both packages

PACKAGE A (the router, the health state, the config, the driver):
- grok-4.20: P0 none; SHIP yes with conditions. It agrees each cycle-1 fix resolves its point, and agrees the 40-minute
  local-judge wait is the ruled one (ruling 87).
- qwen3.8-27b: every cycle-1 point resolved. It keeps the local judge's 40-minute wait as "a P1 operational risk, not
  a P0 code bug". That wait is the ruled one: ruling 87 names the local judge for step A's second verdict when one
  outside family answers, and the integrator's GPU0 swap waits behind a live render.
- glm-5.3-flash: P0 none; SHIP yes. It confirms the torn-read, _SEEN, HealthUnreadable and _prepend fixes against the
  tests, and that the local-judge call is abandoned (not killed) at its deadline: at most one polling thread per
  call, holding no lock. It rates that P2.
PACKAGE B (the verdict call sites, the shadow report, the replay):
- grok-4.20: P0 none, P1 none; SHIP yes with conditions (comments only).
- qwen3.8-27b: P0 none. Its condition, "verify providers.gateway returns a stable identifier", is package A's code:
  gateway() returns "heimdall" for every Heimdall back-end and the vendor otherwise.
  test_the_writes_keep_their_gateway covers it.
- glm-5.3-flash: P0 none, P1 none; "Ship". It compared each parse function with its deleted inline block (all moved
  unchanged), each except clause with call_parsed's raise-set, and the cache writes (only after a parse that
  succeeds).

THEN RULING 96 (orchestrator 01:40 ET Nov 14), routing FINAL until re-measured. This is a data change in
model_providers.json, the ruling's own lists:
- fidelity glm -> qwen -> Grok;
- exclusion glm -> deepseek -> Grok;
- step A's first screen glm -> deepseek -> qwen -> Grok (qwen third as failover; the ruling names glm and deepseek);
- the hook qwen -> glm -> deepseek -> Grok, as the table moved it;
- every other type Grok first, unchanged.
test_ledger_build's routing test asserts the new lists, and the picks when xAI answers nothing and deepseek writes.
