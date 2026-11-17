# gemma-4-31b-it (google/gemma-4-31b-it) 204 s finish=stop usage in 12911 / out 4203 usd_reported=0.000921 usd~0.102 (upper-bound price)

The code implements RULING 141 (2), transitioning the `STAND_ALONE` gate to a "SOFT" failure mode during the "never-empty" pass of the medley builder.

### Analysis

**1. Logic for "Soft" Recovery (`_build`)**
In `pipeline/package.py`, the `_build` function now identifies moments that were rejected solely by the `STAND_ALONE` opener rule. 
- It checks `no_topic(m) is None` and ensures no affirmed trim variant exists.
- These moments are added back to the pool via `stand_back` and marked with `m["stand_soft"]`.
- The `m.pop("stand_soft", None)` at the start of `_build` correctly prevents marks from leaking between passes.
- The hook is protected: `_can_open` (referenced in the prompt) and the `stand_soft_rows` logic ensure the hook remains a HARD gate.

**2. Gate Adjudication (`stand_soft_rows` & `stand_ok`)**
The `stand_soft_rows` function is the core validator. It correctly implements the "fail-closed" requirement for hard failures:
- **Hard Failures (Return `None`):** If the hook fails, if any clip is unmarked (`not m.get("stand_soft")`), if the topic rule fails, or if the medley fails to name Bitcoin.
- **Soft Failures (Added to `out`):** If a clip is marked, is not the hook, passes the topic rule, but fails the opener rule.
- **Passes:** Rows that pass are skipped via `continue`.
This ensures that a medley is only "SOFT" if *every* failure in the `STAND_ALONE` check is a marked opener failure.

**3. Integration and Line-up**
- `lineup_ok` and `lineup_for` now use `stand_ok`, which allows medleys containing only soft failures to proceed.
- `inventory` correctly applies the `FLAGGED` status and the exact required prefix: `"The clip ({channel}) may not stand alone: "`.
- `package_pin.py` correctly adds `"stand_alone"` to `SOFT_GATES`, allowing the pin stage to accept these flags.

**4. Test Coverage**
The new tests in `test_ruling_137.py` are comprehensive:
- `test_the_reason_in_plain_words` verifies the regex mapping of internal reasons to plain English.
- `test_only_marked_clips_failing_only_the_opener_are_soft` rigorously tests the hard-failure boundaries (hook, topic, unmarked, Bitcoin).
- The end-to-end `Rig` test confirms that the clean pass rejects the medley while the never-empty pass seals it as `FLAGGED`.

### Findings

No violations of the Governing Laws or the specific RULING 141 (2) requirements were found. The implementation is precise, maintains the integrity of the clean pass, and adheres to the required string formats for the integrator.

P1_OR_WORSE: 0