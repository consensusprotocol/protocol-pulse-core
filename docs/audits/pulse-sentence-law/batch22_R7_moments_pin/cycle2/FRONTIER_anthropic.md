# claude-fable-5-2 (121 s) usage={'input_tokens': 5533, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 11601, 'output_tokens_details': {'thinking_tokens': 9711}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Verdict: not clean.** The cycle-1 fixes are present as described, but four holes remain that I rate BLOCKING, two of them one-line fixes. Line numbers are new-file lines counted from the hunk headers.

## BLOCKING

**B1. `"moments_package": null` is silently ignored — `pinned.py:314, 316, 328`.**
`mp = pin.get("moments_package")` followed by `if mp is not None:` treats a present JSON null the same as an absent key. The run proceeds with the generic VO and no title, caption or checks. This contradicts "a present package that is not an object is refused (never ignored)". A producer that serialises a failed package as null gets a normal pinned video instead of a refusal. Fix: branch on `"moments_package" in pin`.

**B2. A missing `bridges` key is defaulted, not refused — `pinned.py:361`.**
`v.get("bridges", [])` means `edl_vo: {}` or a misspelt key (`"bridge"`) passes validation. The package then reaches the EDL with all checks true and none of its gated bridges. `"bridges": null` is refused at line 364, so absent and null are treated inconsistently. The same line lets a missing `intro` pass as null.

**B3. `package_sha256` is format-checked only — `pinned.py:356, 329-330`.**
Nothing recomputes it over the package. Title, caption or `edl_vo` can be edited after gating and the EDL still records `moments_package_sha256` and `moments_checks` as if they described that content. The stated deferral (R7 item 4) covers recomputing verdicts; a hash recompute is not mentioned. Uncertain whether package.py's canonical form makes the recompute possible here, since it is not in the diff.

**B4. Nothing in this diff binds the package to the pin's clips — `pinned.py:366-377`.**
`moments_vo` uses `clips` only for index range. A package gated against one set of moments can ride on a pin with different segments, provided the bridge indices fit. Uncertain whether `validate` cross-checks this elsewhere; it is not shown. If it does not, this is an unpassed combination reaching the EDL.

## Not blocking

- **`pinned.py:350`**: only keys ending in `_ok` are checked. A failed verdict in any other shape (`"passed": false`, `"title_OK": false`, nested objects) passes and is copied into the EDL at line 330.
- **`pinned.py:350`**: `build_edl` is callable with an in-memory dict. A non-string key in `checks` raises AttributeError on `k.endswith` (or TypeError in `sorted`). This is not reachable via JSON.
- **`pinned.py:315`**: `_generate_vo_script` now runs and is discarded on the package path. Uncertain whether it has side effects or cost.
- **`pinned.py:335` via `build_edl(pin, acq, …)`**: package validation runs after acquisition, per the `prepare` docstring at 382 ("Validate + acquire + build"). Everything except the bridge-index check could be refused before download and Whisper. Uncertain whether `validate` also inspects the package.
- **`pinned.py:375`**: with one clip the message reads "in 1..0".
- **`pinned.py:372, 375`**: `{b!r}` puts unbounded pin content into the error text.
- **`pinned.py:354`**: `.strip()` passes zero-width-only strings (U+200B). The unstripped value ships, with no length cap.
- **`pinned.py:356`**: `re` import is not visible in the diff, so uncertain.
- **No-package path**: the same `_generate_vo_script` call with the same arguments and no new keys. I see no change in what is accepted, apart from B1's null case.

## Test weaknesses (`test_pinned.py`)

- **Line 320**: the only non-object package is a truthy string. Changing `is not None` to `if mp:` at `pinned.py:316/328` passes every test. Add `[]`, `0`, `False`, `""`, `{}` and null.
- **Line 319**: the only sha case is `"zz"`. Uppercase hex, 63/65 characters, a non-string and a missing key are untested, so `[0-9a-fA-F]` or `re.match` would pass.
- **Lines 310-311**: the regex `"text"` matches the bridge repr (`'text'`) in the after_clip message and "con**text**-integrity" in the gate message. It does not identify the branch.
- **Line 332**: "strictly increasing" appears in every after_clip refusal (`pinned.py:376`). Only the fixture construction proves the ordering branch fired.
- **Non-dict bridge element**: there is no such case (`"x"`, null). The `isinstance(b, dict)` guard at `pinned.py:371` can be deleted with the tests still green.
- **Other missing cases**: `after_clip` missing or null, a negative index, a single-clip pin with a package, `edl_vo: {}`, missing `bridges`, and a verdict of `1`.
- **Lines 321-324**: refusals do not assert that `edl.json` is absent afterwards. All subtests share `self.run_dir`.
- **Line 282**: no test pins what happens to non-`_ok` content in `checks`.

## Not verifiable from this diff

- That `release_auth.authorise` re-hashes `edl.json`, and that `stage_pinned` records `pin_sha256`.
- That any consumer uses `edl["title"]` and `edl["caption"]` rather than `angle`, `topic` or its own generation.
- That render16 places bridges in list order.