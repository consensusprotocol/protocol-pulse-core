# Audit 1008 (the orchestrator's 10:06 ruling 87 amended: an answered probe resets the clock; the probe asks the family that failed), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes with conditions (pp-ingest updates its calls). One <critical>, two <medium>.
- qwen3.8-27b: SHIP yes. Every <critical> and <high> in its text resolves inside its own text ("This seems correct",
  "This is CORRECT"); its summary: none found.
- glm-5.3-flash: "none found ... SHIP: yes" in 27 tokens and 7 s. That is too thin to count as a review: it is recorded
  here, not counted as evidence either way.

Upper-bound cost: about $0.23 ($0.073 + $0.115 + $0.038), outside SPEND_LY.json.

## Implemented

- grok <medium> 1, the equal-time case. A probe answered AT the second its clock started (now == failing_since) is not
  "before" the failure, so it resets the clock. That is what the code does (`now >= fs`). It is now pinned by a test
  (test_a_late_probe_report_does_not_reset_a_newer_clock): an answer at the failure's own second resets. Mutation H2b
  (`now > fs`) is killed by it. The mutation check: 15 of 15 killed. 20 health tests pass.

## Recorded as a condition, not a defect

- grok <critical>: "pp-ingest's current calls pass no families, so its probe can claim a slot opened by the builder's
  deepseek failure, ask only qwen, and its answer resets the clock".
  - The reset is right under the ruling's first sentence: "'Down' means NO SUCCESSFUL ANSWER of any kind for 15
    minutes: any answered call OR answered probe resets the clock". A qwen answer is an answer of some kind. One model
    down is ruling 82's chain, not 'down'.
  - What is missing until pp-ingest updates is only that ITS probe does not ask the builder's failed family. The
    ruling asks for that; pp-ingest has adopted the API (its message, 10:2x ET): note(False, family=...) for each
    family that failed, probe_due(families=["glm", "muse", "qwen"]), and a probe that asks those three in parallel.
    Each new keyword is passed only when the loaded module's signature takes it. The watcher restarts on this commit's
    sha.
  - Making families required would be worse. A prober with the old API could then never claim while a family is
    recorded, so with the builder idle no one would probe, and the clock would run to plan_b on silence: the false
    outage again. families=None claims as before, by design (and tested).

## Refuted, with evidence from the code

- grok <medium> 1, its second half: "an unparseable failing_since_utc". _t returns None for a time it cannot parse or
  without a zone. An answer then clears the field (fs is None), and _down_rule never switches on it (fs is None). A bad
  field can only be cleared, never read as 'down'.
- grok <medium> 2: "a failure with family=None while the clock runs neither clears nor replaces failing_families". By
  design. The list is the families that failed on THIS clock; a failure that names no family adds none. A new clock
  starts the list afresh, and any answer clears it.
