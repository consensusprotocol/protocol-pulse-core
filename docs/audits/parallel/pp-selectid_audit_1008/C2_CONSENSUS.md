# Audit 1008 (ruling 87 amended), cycle 2: consensus

Reviewers:
- grok-4.20: SHIP yes with conditions: pp-ingest's family= / families= calls land first. No finding survives.
- qwen3.8-27b: SHIP yes with conditions: pp-ingest updates its calls; `fams` in providers.py is never empty.
- glm-5.3-flash (a real review this time: 238 s, 5,811 tokens): SHIP yes with conditions:
  - (1) pp-ingest's adoption is live;
  - (2) one assertion of coverage: a named prober with an empty failing_families;
  - (3) confirm where the heartbeat cache in note() returns.
  - Its N1-N6 are all "recorded, not a defect" in its own text.

Upper-bound cost: about $0.29 ($0.084 + $0.085 + $0.123). Audit 1008 in all: about $0.52, outside SPEND_LY.json.

## Implemented after cycle 2 (a test and a docstring sentence; no logic)

- glm (2), N4: test_a_clock_with_no_family_recorded_lets_a_named_prober_claim.
  - pp-ingest's current calls name no family, so a clock they start records none.
  - A prober that names its families then claims, as any prober does.
  - Mutation H14 (drop `failed and` from the filter, which would keep a named prober out of a clock with no family) is
    killed by it.
- glm M3, N2: probe_result's docstring now says that a late answer, which does not reset the clock, still counts in
  probe_streak. plan_b's question is whether the last probes answered; the clock's is whether anything answered since
  the failure.
- The mutation check: 16 of 16 killed. 21 health tests pass.
- FINAL.diff = C2_STEP.diff plus these two (the test and the docstring sentence).

## Conditions, and how each is met

- pp-ingest's side (all three reviewers): adopted. Its message (10:2x ET):
  - note(False, family=...) for each distinct family that failed after the latest answer (glm, muse, qwen; the same
    spelling as the builder's glm and qwen);
  - probe_due(families=["glm", "muse", "qwen"]);
  - a probe that asks those three in parallel and reports with the time of the latest answer;
  - no extra note(True) after a probe;
  - each keyword passed only when the loaded module's signature takes it.
  - It restarts its watcher on this commit's sha, which it gets at once.
  - Until then its old API is in force, and families=None claims as before (tested). Under the ruling's first sentence
    any answer resets the clock, so the transition is correct on the clock. Only the family clause waits for pp-ingest's
    restart.
- qwen: "fams is never empty". providers.Router.start_probe (providers.py:1033) builds fams from the Heimdall back-ends
  of the families deepseek, glm and qwen. model_providers.json configures all three, so fams has three names.
  - With none configured, the Router would have no Heimdall back-end to note a failure of, and families=[] would
    correctly leave every recorded family to pp-ingest's prober.
- glm (3): the heartbeat cache. note() checks _SEEN BEFORE it takes the lock or reads the state: the early return at
  heimdall_health.py note(), the `with _SEEN_LOCK: if answered and not drill and ... < HEARTBEAT_S: return` block
  before `with _Locked(path)`.
  - So an answer deduplicated by the heartbeat writes nothing: it does not reset the clock or failing_families.
  - It can only happen within HEARTBEAT_S (30 s) of this process's last WRITTEN answer, with no failure written by this
    process since: this process's own failures pop _SEEN.
  - So the case is a failure written by the OTHER process inside those 30 s. Then the reset waits for this process's
    next answer after 30 s, or for any probe answer.
  - That is at most 30 s on a 15-minute clock, and the families list is only read while the clock runs, which it then
    rightly does. This predates this change (the heartbeat, audit 0108). No change.

## Refuted or recorded (glm N1, N3, N5, N6; qwen's medium)

- N1 (after a probe answer resets the clock, no probe is due until a call fails again): the ruling's semantics, pinned
  by a test ("no clock: no probe").
- N5 (a list of non-strings in failing_families reads as none): only this module writes the field, always a list of
  strings. A malformed field keeping no prober out is the intended direction: no guess, nobody starved.
- N6 and qwen's medium (an empty fams gives families=[]): as above, never empty in this configuration, and right if it
  were.
