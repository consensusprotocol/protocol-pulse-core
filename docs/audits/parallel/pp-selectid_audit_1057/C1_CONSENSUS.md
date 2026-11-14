# Audit 1057 (the orchestrator's 10:48 ruling 99, the circuit breaker), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes. Two <medium>.
- qwen3.8-27b: SHIP no. Two <critical>, one <high> and four <medium>. One <medium> stands (implemented); the others are
  refuted below.
- glm-5.3-flash: no SHIP line (14 minutes, 89K). Most of its tags resolve inside its own text. It stands on: the trial
  hold against "after 30 minutes one real call may try it again", the event cap, and a fixed sleep in a test. It asks to
  verify the late runaway's cap (refuted below, with the code).

Upper-bound cost: grok $0.093 + qwen $0.118 + glm (its usage line is in its file). Outside SPEND_LY.json.

## Implemented

1. The trial's hold (grok <medium> 2, glm <high> 2). The two reviewers point opposite ways, and both are right:
   - grok: a 15-minute hold is shorter than the local judge's 2400 s deadline floor, so a second trial could be claimed
     while the first is legitimately in flight. That breaks "ONE real call".
   - glm: a hold longer than the call delays "after 30 minutes one real call may try it again" when the trial's
     process dies.
   - Now the trial is held for ITS OWN call's deadline + 60 s (allow(hold_s=...), stored as trial_until). The Router
     computes the leg's deadline before the breaker check, local judge floor included, and passes it.
   - So: about 3 minutes for a Heimdall leg (120 s), 41 minutes for the local judge (2400 s), and TRIAL_HOLD_S (15
     minutes) only for a leg with no deadline.
   - Tests: the default, a Heimdall-style and a local-judge-style hold, read at the claim. The Router claims with its
     deadline + 60 s, and a second claim inside it is refused.
   - Mutations B18 (the hold ignores its call's deadline), B20 (the Router passes no hold) and B21 (a 45-minute
     default): killed.
2. qwen <medium> 7: summary() counted an event whose time cannot be read (`None or since >= since`). It no longer does.
   Test: an event with utc "garbage" is not counted. Mutation B19: killed.
3. glm: EVENTS_KEPT 500 -> 5000, so the 24-hour count on STATE line 1 cannot be cut short by a flapping day.
4. glm: the Router test's fixed 0.6 s sleep is replaced by a bounded wait on the abandoned calls' own count.

The mutation check: 20 of 20 killed. 10 breaker tests.

## Refuted, with evidence from the code

- qwen <critical> 1: "M12 fail closed: an unreadable breaker state must reject the call".
  - M12 is about a gate: "missing data, model failure or an exception rejects; it never produces a pass".
  - The breaker never decides a verdict. It only decides whether a leg is tried now or skipped for the next family.
  - An unreadable state that skips nothing leaves the chain exactly as it was before ruling 99. Every verdict is still
    the model's own, judged by its gate. A model that should have been skipped can only cost its deadline, never pass
    anything.
  - Failing closed here would stop EVERY live call on one bad file. That is an outage made by an optimisation.
  - Ruling 87's health is different: its mode chooses whole chains (Plan B), so an unreadable health raises
    (providers.Router.mode).
- qwen <critical> 2: "production state under tests/". tests/package/proof is this builder's state directory. Ruling 87's
  shared HEIMDALL_HEALTH.json (heimdall_health.STATE), ruling 48's SPEND_LY.json and the evidence file all live there,
  and the build's records too. The breaker sits beside them by the same convention.
- qwen <high> 3: "a late runaway is ignored while the breaker is open (flapping)". By design: a call in flight from
  before the open never extends or re-opens the window (tested). After the window, one trial decides. If the model is
  still bad, its next misses or runaway open it again by the same rule.
- qwen <medium> 4: "an import inside a method". The same lazy-import pattern as heimdall_health in this file
  (providers.Router.mode, _note, start_probe). The module stays importable without the breaker.
- qwen <medium> 5: "orphaned temp files on a crash". The same write-then-os.replace as heimdall_health._save. A crash
  between the two leaves one small file, never a torn state.
- grok <medium> 1: "every leg's breaker open, no leg". The loop records each skip in `tried`. After the chain the
  Router raises ProviderError ("every back-end unavailable", unchanged code after the loop). Every gate's call_parsed
  turns that into NOT MEASURED (law L-m): fail closed. Grok has no deadline, so it can only open on a runaway past 16x
  the caller's max_tokens; none of 676 recorded Grok answers comes near.
- glm (verify): "the late runaway's cap could come from a booking without max_out". providers._within is called in ONE
  place (providers.py:1253-1254), with on_abandon=abandon and on_late=self._late. _within passes abandon()'s value to
  on_late, and abandon() now returns max_out. There is no other booking.
