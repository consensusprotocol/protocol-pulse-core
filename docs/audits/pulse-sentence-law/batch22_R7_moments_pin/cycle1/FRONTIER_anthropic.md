# claude-fable-5-2 (123 s) usage={'input_tokens': 3768, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 12010, 'output_tokens_details': {'thinking_tokens': 9569}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Verdict: do not merge as-is.** Self-attested gates pass on truthiness, five malformed-package shapes raise non-PinError exceptions, and nothing in this diff binds title/caption to release. Line numbers are new-file lines computed from the hunk headers (`pinned.py @@ +311,45`, `test_pinned.py @@ +261,43` and `@@ +326,9`). Nothing was run.

## (1) Shapes that pass `moments_vo` but may misplace

- **bool/float `after_clip`** (pinned.py:344): `True in {1,2}` and `1.0 in {1,2}` are both true in Python, so both pass. Line 350 emits the raw value, so edl.json carries `true` / `1.0`. Uncertain how the renderer treats these (not in diff). The string `"1"` is refused.
- **Duplicates** (344): two bridges with the same `after_clip` both pass. Uncertain whether the renderer places both, the last, or the first.
- **Order** (350): bridges are emitted in package order, unsorted. Uncertain whether the renderer places by position or by `after_clip`.
- **Completeness**: the docstring (336–338) says "one bridge after each clip but the last", but nothing enforces it. Zero bridges, or `edl_vo` absent, `null`, `[]` or `""` (339: `or {}`), yields `{"intro": None, "bridges": []}`, which is identical to the no-package VO while still carrying title, caption and checks.
- **Non-string text** (344, 346, 350): validation uses `str(...)` but the raw value is emitted. `text: 123`, `text: ["a"]`, `intro: False`, `intro: 0` and `intro: {}` all pass and reach the EDL. Whitespace is not stripped.
- **Dropped keys** (339–341, 350): any `edl_vo` key other than `intro`/`bridges` is silently discarded. Uncertain whether the package gates cover other VO lines.
- **Positional binding only** (311–312, 342): `after_clip` is checked against indices `build_edl` assigns, not against a segment identity. Uncertain whether hook selection or clip ordering upstream of line 311 can differ from pp-selectid's numbering; if so, bridges land after the wrong clip with no error.
- **Bridge after the hook**: `after_clip: 0` and `False` are refused (not in `idx`). This is untested.

## (2) Failed, missing or forged gates reaching the EDL

- **Truthiness, not `is True`** (348): `"vo_fidelity_ok": "false"`, `"FAIL"`, `1`, `[False]` or `{"ok": False}` all pass.
- **Self-attested** (348): the verdicts are read from PIN.json. This diff does not call `pipeline/package.py`, despite the docstring at 336.
- **`package_sha256` copied, never recomputed** (329): VO, title, caption or segments can be edited after gating and still pass. The hash in the EDL attests nothing.
- **Non-dict package silently ignored** (316, 328): `moments_package` as a list, string or `true` skips the gate and renders as a plain pin with default VO and no title/caption. This fails open, not closed.
- **Other failed checks pass**: only two keys are tested; any other check that is false is carried into `moments_checks` (330) without refusal.
- **No title/caption validation** (329): `None`, `""` and non-strings are accepted.

## (3) Non-PinError exceptions

- **Missing `title`, `caption` or `package_sha256`** (329): `KeyError`, raised after `moments_vo` has already passed.
- **`checks` is `null`, a list or a string** (348): `AttributeError`, because `.get("checks", {})` returns the present non-dict value.
- **`edl_vo` is a truthy non-dict** (340): `AttributeError`.
- **`bridges` is a truthy non-iterable, e.g. `5` or `true`** (343): `TypeError`.
- **`after_clip` is unhashable, e.g. `[1]` or `{}`** (344): `TypeError` from set membership.
- **Empty `clips` with any bridge** (345): `ValueError` from `max(idx)` in the message f-string. Uncertain whether `build_edl` can reach here with zero clips.
- **Wrapping**: uncertain whether `prepare` or `stage_pinned` wraps these. `prepare`'s docstring (354–355) promises PinError; the diff adds no wrapping or validation.

## (4) Pin without a package

- **Unchanged, verified from the diff.** The `_generate_vo_script` call has the same arguments (315), `"vo"` keeps its key position (323), and new keys are added only under `isinstance(mp, dict)` (328).
- **Caveat**: a non-dict `moments_package` also takes this path (see 2).
- **Uncertain for package pins**: `mode` stays `"pinned"` (325). Whether any downstream gate is lenient for that mode, or whether edl_rules rejects the four new top-level keys, is not in the diff and not tested.

## (5) Title/caption binding

- **Not done here.** The diff only writes `title`, `caption`, `moments_package_sha256` and `moments_checks` into the `edl` dict (329–330); the test shows they land in edl.json.
- **No reader exists in this diff.** Nothing touches PINNED_DECISION, verify or release authorisation, and by your own statement downstream is unchanged.
- **The comment at 328 ("travel with the EDL to release") is unbacked.** Law L-t's release-authorisation requirement is left to later.

## (6) Test weaknesses

- **No message assertion** (test_pinned.py:297): bare `assertRaises(PinError)` cannot show which branch refused. `assertRaisesRegex` is needed.
- **No `subTest`** (291–298): the first failure hides the rest.
- **Fixture-dependent** (292): "bridge after the last clip" with `after_clip: 2` only holds if the fixture yields exactly two clips. That is not asserted.
- **One gate case only** (291): missing `context_integrity_ok` is tested. The reverse, explicit `False`, truthy non-bools, `checks` absent, `checks: None` and non-dict `checks` are not.
- **No (3) cases at all**: missing title/caption/sha and malformed `edl_vo` are untested.
- **No type or shape cases**: bool/float/str/0/list `after_clip`, duplicates, out-of-order, non-dict bridge, non-dict package and the empty-`edl_vo` package are untested.
- **Weak "unchanged" test** (287–288): it checks only `vo` and the absence of `title`. It does not check the other three keys or compare the full EDL to a baseline, and its expected VO is indistinguishable from an empty-package VO.
- **Positive test stops at `prepare`** (278–282): it does not show that validate, the Law 2 gate, voice or render accept the package EDL. It also just mirrors input.
- **Unrelated change bundled** (329–331): the anchored regex and `assertNotIn` in `TestPinnedStageFreesGpu0First` are not part of R7 item 1.