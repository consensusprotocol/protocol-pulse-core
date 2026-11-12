# gpt-6.1-sol (93 s) usage={'prompt_tokens': 2388, 'completion_tokens': 3549, 'total_tokens': 5937, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 2385, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 2039, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}

## 1. Placement validation is incomplete

- **`True` and `1.0` pass as clip index `1`**, provided clip 1 is not the last clip. Membership in an integer set uses equality, not strict integer typing. Both values are returned unchanged. Conversely, `"1"`, `False`, and hook index `0` are rejected because they are not in the one-based clip-index set. **`pipeline/pinned.py:311–312,342–350`**  
  **Uncertain:** whether the renderer handles the accepted boolean/float values identically to integer indices; renderer code is not supplied.

- **Duplicate and out-of-order bridges pass.** There is no uniqueness, ordering, or coverage check. Two bridges after clip 1 pass; with at least three clips, bridges ordered after clip 2 and then clip 1 pass. The returned list preserves that input order. **`pipeline/pinned.py:343–350`**  
  **Uncertain:** whether the renderer preserves, reorders, drops, or duplicates these placements.

- **The documented “one bridge after each clip but the last” is not enforced.** Missing `edl_vo`, missing `bridges`, or an empty bridge list permits no bridges at all; missing `intro` becomes `None`. These pass with truthy gate values. **`pipeline/pinned.py:336–341,348–350`**

- **Non-string VO passes.** For example, `intro=123` or a bridge with `text=["x"]` passes the stringified nonblank check, but the original value—not its string conversion—is returned. **`pipeline/pinned.py:344,346–350`**  
  **Uncertain:** downstream handling of those values.

An explicit bridge after hook index `0`, after the last clip, or after a nonexistent integer clip is rejected by this helper when the clip set is nonempty. **`pipeline/pinned.py:342–345`**

## 2. Gate verdicts are trusted, not established

- **Truthy values masquerade as passing gates.** For example:
  ```python
  {"vo_fidelity_ok": "false", "context_integrity_ok": "false"}
  ```
  passes. The condition tests truthiness, not `is True`. **`pipeline/pinned.py:348–349`**

- **Forged `True` verdicts are sufficient at this boundary.** The added code does not recompute either gate or authenticate its provenance. It also copies `package_sha256` without checking that it binds the title, caption, VO, or checks. An otherwise acceptable package containing supplied passing verdicts reaches EDL construction. **`pipeline/pinned.py:317,329–330,348–350`**  
  **Uncertain:** whether unseen upstream validation supplies those protections.

- **A non-dict `moments_package` is silently treated as no package by the added code.** Both package validation and package-field propagation are guarded by `isinstance(mp, dict)`. This does not carry its package payload into the EDL; it bypasses package handling entirely. **`pipeline/pinned.py:314–317,328–330`**  
  **Uncertain:** whether earlier validation rejects that input.

For an otherwise well-shaped dict package, absent checks, an absent gate key, or a falsey gate value produces `PinError`; missing checks alone are not a bypass. **`pipeline/pinned.py:348–349`**

## 3. Malformed packages escape the `PinError` contract

| Input, with other prerequisites satisfied | Result | Evidence |
|---|---|---|
| Missing `title`, `caption`, or `package_sha256` | `KeyError` | **`pipeline/pinned.py:329`** |
| Truthy non-dict `edl_vo`, such as `[1]` | `AttributeError` at `.get("intro")` | **`pipeline/pinned.py:339–340`** |
| `checks=None`, `[]`, `False`, or another ordinary non-dict value | `AttributeError` at `.get(...)` | **`pipeline/pinned.py:348`** |
| Truthy non-iterable `bridges`, such as `1` | `TypeError` | **`pipeline/pinned.py:341,343`** |
| Bridge `after_clip=[]` or `{}` | `TypeError` during set membership | **`pipeline/pinned.py:344`** |
| Empty `clips` plus any bridge | `ValueError` from `max(idx)` while constructing the rejection message | **`pipeline/pinned.py:342–345`** |

**Uncertain:** whether empty `clips` can reach this helper through `build_edl`; the helper itself has that failure.

Missing or falsey malformed `edl_vo` is instead normalized to `{}` and accepted with passing checks. There is also no added type/nonblank validation for title or caption, or digest validation for `package_sha256`. **`pipeline/pinned.py:329,339–341,348–350`**

## 4. A pin without a package gets no new EDL fields

For an absent `moments_package`, the original VO generator receives the same arguments, and title, caption, digest, and checks are not added. The diff exposes no new-field mechanism that changes downstream gate acceptance for that case. **`pipeline/pinned.py:314–330`**

**Uncertain:** actual downstream gate behavior is not shown. The regression test checks only empty VO and absence of `title`, not full EDL equivalence or downstream acceptance. **`pipeline/test_pinned.py:284–288`**

## 5. Release-authorisation binding is not implemented here

The change copies title and caption into the EDL. The test verifies their presence in `edl.json`. **`pipeline/pinned.py:329–330`; `pipeline/test_pinned.py:277–282`**

No release-authorisation reader, binding, or assertion is added in this diff. This change therefore **leaves that integration unimplemented here**. Whether existing downstream code already consumes these exact fields is **uncertain**; none is supplied.

## 6. Tests leave the failure boundaries uncovered

- The positive test checks EDL serialization, not renderer placement or release-authorisation consumption. **`pipeline/test_pinned.py:277–282`**
- The rejection table covers only one missing gate verdict, last/nonexistent clip indices, blank bridge text, and blank intro. It does not cover explicit false gate combinations, absent checks, non-dict checks, truthy forged verdicts, or digest binding. **`pipeline/test_pinned.py:290–298`**
- No tests cover boolean/float/string indices, hook index `0`, duplicate or reversed bridges, missing bridge coverage, non-string VO, or the exception leaks listed above. **`pipeline/test_pinned.py:277–298`**
- The no-package test does not compare the complete old EDL, assert absence of every new field, or exercise any shared downstream gate. **`pipeline/test_pinned.py:284–288`**