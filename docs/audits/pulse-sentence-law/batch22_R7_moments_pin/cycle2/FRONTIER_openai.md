# gpt-6.1-sol (55 s) usage={'prompt_tokens': 3586, 'completion_tokens': 2429, 'total_tokens': 6015, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 3583, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 1906, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}

### 1. BLOCKING — An explicitly null package bypasses validation

**`pipeline/pinned.py:314,316–317,328–330`**
```python
mp = pin.get("moments_package")
...
if mp is not None:
    vo = moments_vo(mp, clips)
...
if mp is not None:
    edl.update(...)
```

`"moments_package": null` is treated exactly like an absent key. It never reaches the object check at **`pipeline/pinned.py:343–344`**, which would reject it.

For an otherwise accepted pin, this path emits an EDL using generated VO and omits the package metadata instead of raising `PinError`. That violates the stated requirement that a **present non-object package is refused, never ignored**.

**Test gap:** **`pipeline/test_pinned.py:320`** tests `"not a package"` as the non-object package. The `"checks null"` case at **line 299** tests a different field. Neither exercises a null package.

Distinguish key absence from a present null value, and add an explicit-null package refusal test.

### 2. Not BLOCKING for file-backed JSON pins — Non-string check keys still raise `AttributeError`

**`pipeline/pinned.py:350`**
```python
failed = sorted(k for k, v in checks.items() if k.endswith("_ok") and v is not True)
```

The preceding validation checks that `checks` is a dictionary and that the two required verdicts are exactly `True`; it does not validate key types.

With otherwise valid package data, this dictionary passes those preliminary checks:
```python
{"vo_fidelity_ok": True, "context_integrity_ok": True, 0: False}
```

Then `0.endswith("_ok")` raises `AttributeError`, not `PinError`. That contradicts the helper’s **“Anything else is a PinError”** contract at **`pipeline/pinned.py:342`**.

**Reachability qualification:** ordinary JSON object keys are strings. Whether any production caller can supply this Python dictionary directly is **uncertain from the supplied diff**; this is a verified helper-level exception leak, not a demonstrated file-ingestion bypass.

**Test gap:** the checks cases at **`pipeline/test_pinned.py:296–302`** cover verdict values and non-dictionary containers, but not non-string dictionary keys.