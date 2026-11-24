# Audit 20261124_0841_K3_r161_fixes: the one consensus finding

Seats. Cycle 1: qwen27b FAIL (1 finding), gemma PASS, gpt-oss no answer. Cycle 2 (cross-examination): qwen27b and gemma answered and added nothing.

## qwen27b F1 [high], gemma agreeing: "current() can still raise on malformed burned_in entries because flags() indexes x['kind']"

**Resolved by the next commit, 0c8630c50. It was true of c52d1b0c7, the commit reviewed.**

- 0c8630c50 rewrites current() (found by the suites: it also undid a 16:9-only decision). current() no longer calls flags().
- It filters the record's existing flags under `isinstance(f, dict)`, and builds the set of sponsor items under `isinstance(x, dict)`.
- formats() (`isinstance(x, dict) and ...`, from c52d1b0c7) and sponsor_item() / listed() / offer_named() (`isinstance(x, dict)`) guard every entry they read.
- flags() still indexes keys. It runs only on check()'s output (visual_pin.check validates every burned_in entry as a dict with those keys, or raises ValueError, at check time), so a malformed entry never reaches it.
- Test: test_visual_pin TestRuling161 "odd" (burned_in ["x", None, {"kind": "bug", "text": None}], advertising ["y", None, {"text": 3}], lower_third "z"): sponsor_graphics and formats return None, no exception.
