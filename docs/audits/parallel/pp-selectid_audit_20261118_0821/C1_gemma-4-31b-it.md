# gemma-4-31b-it (google/gemma-4-31b-it) 186 s finish=stop usage in 19815 / out 3701 usd_reported=0.001073 usd~0.115 (upper-bound price)

The code audit for feature `pp-selectid` is complete. The implementation strictly adheres to the Governing Laws and the specific requirements of RULING 147.

### Audit Findings

**1. RULING 147 (a): Mirror of Integrator's Batch 114**
- **`lock_precheck.py`**: The `RULES` string now includes `ruling 146` and the `DECODER` is updated to `50fa01b400bd`, matching the integrator's lockstep.
- **`sentence_law.py`**: 
    - **Boundary Enforcement (Ruling 73)**: The `_ruling73` function correctly enforces that the `OUT` cut is never before the decoded end of the last locked word and the `IN` cut is never more than 600ms (`IN_LEAD_MAX_S`) before the first locked word.
    - **Clamping**: `accepted_cut` now uses a `clamp` lambda to ensure all cut points are forced within the legal `cut_lo` and `cut_hi` ranges, preventing any "snap" outside the allowed gap.
    - **Hook Lead (Ruling 146(2))**: The `hook_lead` logic implements the "SOFT" failure. If no legal cut provides $\ge 80\text{ms}$ of genuine quiet, `lock_cut` catches the `refused` state and converts it to a `short` flag. This allows the render to proceed while flagging the abrupt start, rather than blocking the build.
    - **Unified Path**: The introduction of `lock_cut` ensures that `write_lock_cut_table` and `lock_precheck.py` use the exact same logic for cut placement.

**2. RULING 147 (b): Exception Pin's Cap**
- **`package_pin.py`**: The `flags_cap` function correctly implements the conditional cap. It returns `PBX_EXCEPTION_CAP` (5) only if the `EXCEPTION_GATE` (`"pbx_exception"`) is present in the gates dictionary; otherwise, it defaults to `REVIEW_FLAGS_MAX` (3).
- **Integration**: Both `review_problems` and `to_pin` now call `flags_cap`, ensuring the exception is applied per-pin based on the sealed gates.

**3. Law Compliance & Technical Fixes**
- **L-b (Edge Word Fidelity)**: The addition of `EDGE_WORD_FLOOR_DBFS = -90.0` in `sentence_law.py` is a critical fix. By ignoring audio below this floor in `edge_word_fidelity` and `span_fidelity`, the system avoids false failures caused by AAC codec noise in the gaps, while still enforcing the 1dB fidelity rule for audible speech.
- **Ruling 18 (Span Fidelity)**: The `span_fidelity` function correctly implements frame-by-frame comparison with a $\pm 2$ hop window and a "fail closed" check to ensure no source frames are left uncompared.
- **L-j (Release Auth)**: The unification of the cut logic into `lock_cut` ensures that the bytes measured by the gates are identical to the bytes used in the final render.

**4. Test Verification**
- `test_lock_precheck.py` and `test_ruling_105.py` verify the new `DECODER` and `RULES`.
- `test_ruling_137.py` confirms the exception cap: a pin with the exception row accepts 5 flags but refuses 6, while a standard pin refuses 4.

### Final Conclusion
The implementation is precise. The "SOFT" failure for hook leads prevents unnecessary blocks while maintaining visibility, and the exception cap is narrowly scoped to the specific pin carrying the exception gate.

P1_OR_WORSE: 0