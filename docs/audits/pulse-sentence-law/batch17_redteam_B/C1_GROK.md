**Q1: CORRECTNESS**  
The diff is correct on what it changes. `_field` (lines 9-25) and `_str_list` (28-30) perform strict type/allowed/range/nonempty checks and raise `ValueError` on any failure. All validator functions (`_v_derive`, `_v_adj`, `_v_sup`, `_v_react`, `_v_label`, `_v_rate`) now route through them. `verify_support` (102-108) now requires `same_actor_action_object is True` and `presented_as == "current"` exactly; any deviation downgrades the verdict. `rate_passages` (175-178) only consumes data after `validate` succeeds and no longer clamps or silently drops bad entries. No time/index arithmetic, no audio/gate logic, and no silent exception swallowing paths are present in this diff.

**Q2: LAW COMPLIANCE**  
COMPLIANT with M12 (fail closed) and the red-team intent stated in the comments. The changes make malformed or incomplete LLM replies produce `ValueError` (caught as parse failure) rather than a partial or defaulted result. No changes touch sentence boundaries, selection locks, cut movement, edge-word rules, or any gate threshold. No path in this diff can move a cut outside a locked sentence or recompute first/last words.

**Q3: TESTS**  
Tests are updated to supply complete objects that pass the new validators (e.g., lines 190-196, 278-279, 282-283). The new test at 224-238 explicitly asserts that missing, mistyped, out-of-range, or duplicate fields raise `ValueError`. The `ScriptedLLM._ok` helper (294-299) enforces that `validate` must succeed before a reply is returned. No vacuous assertions observed.

**Q4: VERDICT**  
No defects found in the supplied diff.

**READY**