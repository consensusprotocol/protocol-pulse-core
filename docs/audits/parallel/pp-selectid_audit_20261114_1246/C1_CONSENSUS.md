# Audit 20261114_1246 (the orchestrator's 12:16 rulings 100, deadlines follow the model, and 101, step A in parallel), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes with conditions. Two <medium>, both documented edges (below), no code finding.
- qwen3.8-27b: SHIP no. One <critical> that resolves inside its own text, one <high> and one <medium>, both refuted
  below with the ruling's words and the code.
- glm-5.3-flash (821 s, finish=length at its 24,000 cap): no <critical>; 48 <medium> notes. One is a real
  defect (M27), fixed; three hardenings taken (M5, M11, M37). See the addendum at the end.

## grok's conditions (documented, no change)

- "If the first screen raises, par['used'] stays 0". Then the build itself raises: the exception leaves the `try`
  after the confirm-ahead is joined in `finally`, and no report line is printed for a build that did not finish. A 0
  can only be printed for a build that finished without reaching the second screen. In that case it is TRUE: no
  confirm-ahead verdict was used, and all of its spend is the extra.
- "A leading leg with no deadline (Grok) gives wait 0, so sequential". That is the ruling: the filter worth parallelising
  is Heimdall's slow one. When Grok leads the first screen it answers in its own time (median 46 s, n 268), and
  step_a_plan's docstring says so. The build's line then prints the leg ("on xai:grok") and the 0, so it reads plainly.

## Refuted, with evidence

- qwen <high>: "the ruling says 'Grok's call is then not saved', and the code saves Grok's verdicts to the cache".
  - The sentence is about money: "Grok's call is then not saved, and you report the extra spend per build".
  - The saving it names is the sequential order's: Grok is asked only on a filter pass, so a moment the filter fails
    costs no Grok call. In parallel that saving is not made, and the build reports what it cost
    (proof_ledger.ruling_101_line: usd x unused / asked).
  - The verdict itself goes to the shared step-A cache, because that is how the unchanged second screen reads it.
    Verdicts are paid once (ruling 58).
- qwen <medium>: "confirm_ahead can spend past ruling 48's cap with no mid-build check".
  - Every confirm-ahead call goes through Router.call: _Tally.call delegates to the router's own call. Before any paid
    call, Router.call reserves the call's upper bound (_reserve), which raises SpendLimit when spent + reserved + this
    call would pass the limit (unchanged code).
  - The cap is checked per call, in parallel threads alike (the reservation is under the ledger's lock).
- qwen <critical>: "the two prescreens race on the cache". Its own trace concedes the lock: _cache_put re-reads and
  merges under CACHE_LOCK.
  - What remains in its text is the "orphaned" Grok verdict on a moment the filter fails: exactly the extra spend that
    is reported.
  - Its reuse in a later build as that moment's FIRST verdict is not new. Grok's verdicts from the first screen's own
    fallback (the step_a_first chain ends in Grok) have always been cached and reused the same way. The second screen
    still needs a verdict off the first's vendor and family, so "both pass, from two families" holds.

The mutation check: 22 of 22 killed. In dev08: 22 suites, 591 tests.

## Addendum: glm-5.3-flash (its review arrived after the part above)

### Fixed

- **M27 / attack (b), the main finding, CONFIRMED:** "the first screen's Grok leg, 120 s -> unbounded".
  - The cause: first_bounds passed deadline_s None, and role_deadline gives Grok none.
  - The fix (dev08):
    - first_bounds is RESTORED to its old text ({batch 2, deadline_s 120}; failover follows the deadline,
      package.py:551, unchanged).
    - Ruling 100 moved into a new Router.effective_deadline(role, b, deadline_s) (providers.py:1020). Router.call
      uses it (providers.py:1246). Where a deadline applies (the caller's, else role_deadline's), a VERDICT pair's
      own row replaces it. Where none applies, none is added.
    - role_deadline is back to the gateway's number only.
  - The first screen's legs, under heimdall_first:
    - glm: 120 s, then its row, 60 s.
    - deepseek: 120 s, then 300 s.
    - Grok: 120 s, then its own row, 118.1 s (n 286, p90 78.7).
  - The second screen's Grok keeps no deadline, as ruling 88 (c) set it (_second_bounds, package.py:681, unchanged).
  - New tests:
    - A live Router.call is held to effective_deadline's number: [300, 120.7, 120, 300] for deepseek, Grok with
      120 s, glm, and a writer at 300 s. Grok with no deadline is not held.
    - test_ruling_85 asserts the 120 s again.
  - Mutations: D9 (first_bounds loses its 120 s) and D10 (Router.call ignores effective_deadline), both killed.
- **M5:** _Tally read usage with `or {}`, so a non-dict usage raised. It now reads usd_reported only from a dict.
- **M11:** load() with no record dir recomputed an EMPTY table and saved it over a good one. Now it never saves without
  a record dir.
  - Its test found a worse defect, now fixed: compute(None) globbed "*/*.json" in the CURRENT directory, and raised on
    a JSON list.
  - Now there is no record dir -> no rows, and a record that is not an object is skipped.
  - Mutations D13, D15, D16, all killed.
- **M37:** deadline() returned a saved row as it stood, so a hand-edited 500 s was used. It now clamps every row to
  60-300 s, and a non-finite value gives no row. Mutation D17, killed.

### Changed beside the fix

- Ruling 101's plan now needs a HEIMDALL family to lead the filter (package._heimdall, providers.gateway).
  - With the Grok row applied to the first screen, Grok could lead with a wait over 10 minutes: 80 new moments at
    118.1 s is 826.7 s.
  - In that case the first verdicts are Grok's own, so a confirm off Heimdall could never serve them. The plan is
    sequential, whatever the wait.
  - Mutation P12, killed.
- confirm_ahead uses the same predicate.
- proof_ledger.applied lists the rows the build uses: Heimdall's verdict pairs, plus Grok's context_verdict on the
  first screen. Mutation D14, killed.

### Documented, no change

- M4 / M33, the estimate:
  - The plan is taken once, before the first screen, from the leading leg's deadline per round.
  - A breaker that opens mid-build, or a failover inside a round, makes the real wait longer than estimated. So the
    plan can only err toward sequential, the ruled default.
- M12, "today" routing: the step_a_first chain is led by Grok, and first_bounds gives no deadline, so the plan is
  sequential (it is now also gated on a Heimdall lead).
- M16: the table's key is the recorded "backend" field. Router._record writes it from the back-end's config name,
  b.name; the measured rows above carry the config names.
- M36 / M47, threads and the cap: Router.call reserves each paid call's upper bound under the ledger's lock, and
  raises SpendLimit before a call that would pass the cap (the qwen <medium> above).
- M39, the table under tests/package/proof: the build (proof_ledger) is its only user. It sits beside BREAKERS.json and
  HEIMDALL_HEALTH.json, and is runtime state, never committed.
- M44, "used overcounts": refuted. prewarm_used is taken over `cleared` (package.py:2598), the same set passed to
  second_screen on the next line.
- M46, glm's 483-532 s runs: a call abandoned at its deadline is a MISS, not an answer. Only answered calls are
  recorded, so glm's row stays at the 60 s floor, and its slow runs trip its breaker, as ruling 100 says.

The mutation check, after the fixes: 30 of 30 killed (D1-D17, P1-P13). In dev08: 22 suites, 593
tests, network blocked.
