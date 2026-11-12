# claude-fable-5-2 (40 s) usage={'input_tokens': 3184, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 3688, 'output_tokens_details': {'thinking_tokens': 2321}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'} usd=0.17 stop=end_turn

**1. Fail-closed assertion has no control, so it does not prove what the comment claims** (`pipeline/test_fresh.py`, new test, `self.assertFalse(SA.check_edl({"hook": hook, "clips": [...]}, subject=set())["ok"])  # an empty subject HOLDS`).
- The EDL is a stub: no `rate`, and the clip has no timing or words. `ok` may be False for reasons unrelated to the subject.
- There is no twin assertion that the same EDL with `subject={"bitcoin","btc"}` is `ok`, and no assertion on which row failed.
- Uncertain, because `check_edl` is not in the diff: if it treats a falsy subject as "not supplied" (`subject or <derive from edl>`), then `set()` on a real EDL re-derives from `angle`. That is the old behaviour, not a hold. The stub has no `angle` or `topic`, so this test could not detect it.
- The claim "tested through check_edl" is also loose: the helper's output is never fed to `check_edl`; a literal `set()` is.

**2. "Only a Bitcoin label" is implemented as "label mentions Bitcoin", not `label == "bitcoin"`** (`pipeline/run_fresh.py`, `terms = stand_alone.subject_terms("", edl.get("topic") or "")` then `terms == {"bitcoin", "btc"}`).
- By your own description, `subject_terms` returns that set whenever the headline *names* Bitcoin. Labels such as `"bitcoin cash"`, `"not bitcoin"` or `"btc etf"` would therefore pass as a Bitcoin subject.
- The only negative labels tested are `"ethereum"`, `""`, `None` and a missing key. No label that contains Bitcoin but isn't Bitcoin is tested.
- Uncertain: a truthy non-string `topic` (list, `True`) goes straight into `subject_terms`. Whether that raises or returns empty is not visible here. A raise is a crash in `stage_validate`, not a recorded hold.

**3. The marker check is shape-only and switches the subject away from the story** (`pipeline/run_fresh.py`, `if "moments_package_sha256" in edl:` with `re.fullmatch(r"[0-9a-f]{64}", sha)`).
- Nothing in this diff binds the digest to a package or to `pinned.build_edl`.
- Any EDL carrying a 64-hex string under that key and a topic that mentions Bitcoin gets `{"bitcoin","btc"}`, even when `passages.json` supplies a story. The test pins exactly this: `{"affected_object": "Binance hot wallet"}` gives `{"bitcoin","btc"}`, where the old rule gave `{"binance","wallet"}`.
- That is a wider subject for any non-moments EDL that acquires the key. Whether one can is not verifiable from this diff: `build_edl` and the other EDL writers and loaders are not shown, so "only build_edl sets it" rests on your context alone.

**4. The AST test does not pin the wiring** (`pipeline/test_fresh.py`, `test_stage_validate_takes_its_subject_from_the_helper`).
- It only asserts that a call named `stand_alone_subject` exists somewhere in `stage_validate` and that no call is spelled exactly `stand_alone.subject_terms`.
- These mutations pass it:
  - Call the helper, discard the result, and pass `subject=None` or omit `subject=` in `check_edl`.
  - Compute the subject through an alias (`from stand_alone import subject_terms`, or `SA.subject_terms`).
  - Call the helper with `(edl, {})`, dropping the story for non-moments runs.
- No test asserts that the helper's return value reaches `check_edl(..., subject=...)`.

**Not verifiable from the diff:** the helper uses `re.fullmatch`, but no `import re` is added. It presumably exists at module level (`FALLBACK_RE`), but that is not shown.