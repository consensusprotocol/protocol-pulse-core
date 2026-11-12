# gpt-6.1-sol (338 s) usage={'prompt_tokens': 40447, 'completion_tokens': 15190, 'total_tokens': 55637, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 40444, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 13314, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}

**BLOCK.** The diff still contains the following defects. The claimed live execution results are not verifiable from the diff.

### 1. P1 — Concurrent lease entry can bypass the depth counter

**`pipeline/gpu0.py:182–190, 209–219`**

The `_own` lookup and subsequent custody decision are separate:

> `h = _own.get(target)`  
> …  
> `if h is None and held():`  
> `    yield`

Verified failing interleaving:

1. Thread B reads no `_own` entry, then pauses.
2. Thread A acquires and registers the lease, then enters its block.
3. B resumes. `held()` returns true because A holds it, so B takes the **custody branch without incrementing depth**.
4. A exits and closes the descriptor at line 219 while B remains inside its lease block.

Another process can now acquire the lease while B’s GPU work is still running. Protecting the depth updates alone does not fix concurrent acquisition.

### 2. P1 — Lazy Whisper decoding does not check the lease

**`pipeline/gpu0.py:540–549, 615–621`**

`Whisper.transcribe()` checks custody through `self.get()`, then returns:

> `return guard_iter(iter(segments), f"{self.key}: decode"), info`

The decoder subsequently executes:

> `with guard(what):`  
> `    x = next(it)`

Neither `guard_iter()` nor `guard()` calls `require()`.

Consequently, an iterator obtained inside `with gpu0.lease(...)` can continue decoding after that block exits. This is a **lease-check bypass**, separate from the accepted decision that an iterator retains its model until exhaustion.

### 3. P1 — Ollama ownership survives the residency it supposedly authorizes

**`pipeline/gpu0.py:344–346, 380–395, 445–447`**

Ownership is only a model-name membership test:

> `if name not in _ollama_ours:`

`swap_to()` adds the name before its memory proof finishes:

> `_ollama_ours.add(name)`

Names are removed by `_ollama_unload(names)`, not when `/api/ps` shows that a model expired or unloaded independently.

If this process’s model disappears and another client later loads the same name, `foreign()` classifies that residency as ours. A subsequent swap can unload it through lines 443–444. The current ownership record cannot distinguish those residencies.

Whether another client performs that sequence is uncertain; the authorization and unload behavior are visible in the diff.

### 4. P2 — Malformed Ollama readings can mean “nothing resident,” or become an ordinary error

**`pipeline/gpu0.py:356–373`**

An empty HTTP body becomes `{}`:

> `json.loads(...read() or b"{}")`

A response without a `models` field becomes an empty resident list:

> `models = _ollama("/api/ps").get("models", [])`

Thus an empty body or `{}` is accepted as evidence that nothing is resident. Because Ollama processes themselves are exempt in `foreign()` at lines 341–346, this can remove the model-level foreign-user protection.

A top-level JSON array instead raises `AttributeError` at `.get()`, which is not among the caught exceptions at lines 368–373. That escapes as an ordinary exception rather than `Gpu0Unreadable`.

Whether the deployed server emits these responses is uncertain. Their handling is not.

### 5. P2 — GPU0 unreadability is swallowed by the production sampler

**`pipeline/gpu0.py:670–678`; `pipeline/run_fresh.py:1466–1469`**

The sampler suppresses every GPU0 stop:

> `except Gpu0Stop:`  
> `    self.errors += 1`  
> `    return`

This also applies to the synchronous sample at stage entry through `PeakSampler.set()` at lines 666–668. A stage can therefore advance without a peak sample despite GPU0 being unreadable.

The added orchestration code records `sampler_errors`; it does not turn those failures into a HOLD. Whether an unseen attestation check rejects them is uncertain.

The measurement tool has the same evidence hole: **`pipeline/measure_gpu0.py:80–85`** silently discards sampling failures, while **lines 93–103** reject failed children but not failed measurements. A successful child with no successful workload samples can produce `need_mib == 0` and no sampling-failure status.

### 6. P2 — The CPU-session GPU leak detector fails open

**`pipeline/conftest.py:44–53`**

The new custody check returns false when `nvidia-smi` cannot be executed or times out:

> `except (OSError, subprocess.TimeoutExpired):`  
> `    return False`

It also ignores both subprocess return codes. Failed commands with empty stdout likewise mean “no context.”

Therefore an unreadable GPU0 disables the CPU-session enforcement instead of stopping the session.

Detection is also only performed at module boundaries, per **lines 60–62**, and checks only the pytest process’s PID. It does not establish the stronger claim that the session never held a GPU0 context.

### 7. P2 — Captured subprocess OOMs are still truncated before classification

**`pipeline/gpu0.py:509–515`**

`is_oom()` retains only:

> `parts.append(v[-4000:])`

A `CalledProcessError` whose stderr contains an OOM marker followed by more than 4,000 characters of other output is classified as non-OOM.

This matters to the explicitly retained fallback path in **`pipeline/render16.py:621–625`**:

> `if gpu0.is_oom(e):`  
> …  
> `print(... falling back to qa_dir)`

For that exception shape, the OOM still becomes an outro fallback rather than the bounded GPU0 retry. `raise_if_oom()` scans complete stderr, but this exception-based path does not.

### 8. P2 — Failed retries other than a second OOM are not logged as attempt 2

**`pipeline/run_fresh.py:195–224`**

On retry, a non-OOM `Gpu0Stop`, `Hold`, or ordinary exception raises immediately from lines 195–213.

The attempt record is appended only later:

> `self.prov.setdefault("gpu0_oom", {}).setdefault(name, []).append(entry)`

A passed retry has its explicit attempt-2 record at line 192; a second OOM reaches line 224. The other failed retries do neither.

Their HOLD reason retains attempt 1, but **“both attempts logged” remains false** for those paths.

### 9. P2 — The structural tests do not enforce the properties they name

**`pipeline/test_gpu0.py:400–432`**

Three concrete holes:

- **Lines 404–410:** the CUDA `.to(...)` exception skips that pattern throughout `story_semantics.py`, not just inside the approved builder or guard.
- **Lines 417–427:** the NVENC test requires the substring `gpu0.swap_to("nvenc")` somewhere in a top-level function’s source. It does not establish that the swap executes **before** an encode, or on every encode path. Even a comment containing the substring satisfies this test.
- **Lines 429–432:** the Ollama test exempts `story_semantics.py` and `preflight.py` wholesale. An additional unguarded request in either file passes.

These are lexical inventories, not load-bearing enforcement of custody or ordering.

### 10. P2 — The back-to-back test does not require successful runs

**`pipeline/test_gpu0_live.py:200–213`**

The child’s return code is stored:

> `tables.append((run_dir, r.returncode, table))`

but never asserted. The assertions cover stage presence, stage status, and integer peak fields only.

A child that passes those stages and subsequently exits in HOLD—for example during terminal attestation—can satisfy this test. It does not establish successful terminal verdicts or successful `release_auth` completion.