# claude-fable-5-2 (581 s) usage={'input_tokens': 69297, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 56067, 'output_tokens_details': {'thinking_tokens': 52772}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Verdict: BLOCK.** Two defects verified from the code and one coverage hole that cannot be closed from this diff. The diff prints no line numbers for the new files, so those are cited by function and quoted line. Nothing here was executed; the mutation proofs and the back-to-back run are not verifiable from the diff.

## Blocking

**B1. A `'pending'` Ollama claim never expires, so a foreign model of the same name is adopted and unloaded (cycle-2 fix 2 is incomplete).**
- `gpu0.py` `swap_to`: `_ollama_ours[name] = "pending"` is set before anything is requested.
- `gpu0.py` `ollama_resident`: only `elif state == "resident": del _ollama_ours[n]` prunes. A pending name that never became resident stays claimed.
- Path (a): `swap_to` marks pending, then raises `Gpu0NotFree` in its wait loop. No request was ever sent.
- Path (b): `LocalLLM._post` fails before the model loads. `release_all` then calls `_ollama_unload(ollama_loaded())` with an empty list, which pops nothing.
- From then on, another client's load of that name passes `foreign()` (`if name not in _ollama_ours`) and is flipped to `'resident'` by the next read.
- It is then unloaded by `leave()` (`mine = [n for n in ollama_loaded() if n in _ollama_ours]`), by `swap_to`'s `drop`, by `release_all`, or by `LocalLLM.stop()`.
- `test_ownership_ends_when_the_model_is_seen_gone` covers only resident→gone. No test covers pending→never resident.
- The window is narrow (from the failure to process end), but claims (1) and (2) say "never".

**B2. A runner lost to out-of-memory and reported over HTTP is not named.**
- `story_semantics.py` `_post` (hunk `@@ -187`): the `HTTPError` branch raises `GpuOOM` only if `is_oom(RuntimeError(text))`; otherwise `raise RuntimeError(f"Ollama HTTP {e.code}: ...")`.
- The "model is no longer resident" test exists only in the `(URLError, ConnectionError, TimeoutError)` branch.
- So an HTTP 500 whose body carries no `_OOM` token, with the model gone, leaves as a plain `RuntimeError`: no retry, no out-of-memory in the HOLD. `preflight.check_ollama` has the same shape.
- Uncertain: how often Ollama words a dead runner without an out-of-memory token. The asymmetry in the code is certain.
- No unit test exercises `_post`'s error naming at all.

**B3. Uncertain, blocking until shown: an NVENC out-of-memory inside `run_isolated.prerender_clips`.**
- `run_fresh.py` `stage_prepare`: the wrapper is `gpu0.swap_to("nvenc"); return _prerender_isolated(run_dir, table)`. It has no `guard` and no `raise_if_oom`.
- `test_gpu0.py` `TestNoDirectLoaders.FILES` excludes `run_isolated.py`, so claim (12)'s "every NVENC subprocess call" does not cover it.
- If the protected file reports failure as anything but a `CalledProcessError` with captured stderr, the out-of-memory is renamed on every run's prepare path. I cannot see that file.

## Not blocking

1. **Unfiltered unloads.** `swap_to` (`drop = [n for n in ollama_loaded() if n != name]`) and `release_all` (`_ollama_unload(ollama_loaded())`) do not filter by `_ollama_ours`, unlike `leave()`. A foreign model loaded between `foreign()` and that read is unloaded. Separately, ownership is only observed on reads: an unobserved keep-alive expiry followed by a foreign reload stays "ours".

2. **A dead or refusing Ollama is reported as out-of-memory.** In `_post`, a refused connection makes `ollama_loaded()` return `[]`, so `self.model not in ...` is true and `GpuOOM` is raised. The run ends "CUDA out of memory twice" after a pointless release and retry. The real cause survives in the message text.

3. **A stale decode iterator is not tied to the swap.** `guard_iter` checks `require(what)` only. An unexhausted iterator keeps its model alive after a swap "deleted" it, and can keep decoding beside the new model, or pin memory until `Gpu0NotFree`.

4. **A killed run HOLDs the next one.** `leave()` runs only on orderly ends (`run_fresh.py` `main` finally, `replay.py`, `preflight.py`, `backtest.py`). After SIGTERM or SIGKILL the run's own model stays resident for the server's keep-alive (`_post` sends none). The next owner's `check_gpu0` or `stage_env` then HOLDs on it as "not requested by this run".

5. **Fix 9 can pass without proof.** `release_all`: `mine = sum(m or 0 ...)`. A process whose memory is unreported counts as 0.

6. **Fix 11 is untested, and likely names a dead pid under the wrapper (uncertain).** No test references `_lease_holders`. In `pulse_check_run.sh`, `flock -n 8` runs as a child; /proc/locks probably records that exited child's pid, not the wrapper's. If so, the wrapper is never matched, and a reused pid would be treated as ours along with its descendants. The module docstring still says "the processes holding the lease file open".

7. **Fix 7 stops CPU sessions on hosts without nvidia-smi.** `conftest.py` `_holds_gpu0_context` returns `None` on `OSError`, so `pytest_runtest_teardown` exits 3 after the first module.

8. **`is_oom` can rename a non-OOM failure.** The bare `out of memory` pattern over 1 MB of stderr/output, and over `str(e)`, makes an unrelated failure a "CUDA out of memory" with a retry.

9. **The structural tests are narrower than claimed:**
   - The loader deny-list misses `device = "cuda"` (with spaces), `VoiceEncoder(<args>)`, `.to(device)`, and any library that picks CUDA itself.
   - The NVENC check skips any `subprocess.run` whose command is built outside the call expression.
   - Swap order is lexical only.
   - One `raise_if_oom(r, ...)` clears every `r = subprocess.run(...)` in the function.
   - Only the literal `h264_nvenc` is searched.
   - The Ollama test whitelists `story_semantics._unload`, an unconditional keep_alive-0 unload with no ownership check. Its remaining callers are not visible.

10. **One model at a time may thrash (uncertain).** `backtest._backtest_days` holds `E` and `L` together. Each alternation now unloads and reloads the ~20 GB model. Only the pinned path has a live test.

11. **Headroom is fixed by the constants.** A swap to `ollama:gemma3:27b` needs 21624 of 24564 MiB free, so baseline plus this process's CUDA contexts must stay at or under 2940 MiB, or the stage HOLDs after 180 s. Whether real runs stay under is not shown.

12. **`qa_gates.py` standalone.** `_standalone_lease` says "exits 75", but `sys.exit(<str>)` exits 1. It also runs before the usage check. `_gpu0()` inserts `pipeline/` at `sys.path[0]`; whether that shadows a later lazy import is uncertain.

13. **Removed globals.** `cut_accept._MODEL` and `qa_gates._FW_MODEL` are gone; any external reference or test stub is not visible here.

14. **Evidence.** `TestBackToBack` has the exit-0 and no-`gpu0_oom` assertions but is skipped without `PP_GPU0_LIVE=1`. The diff holds no proof it ran.

## Claims verified by reading

- **(3)** `lease()` takes the mine / custody / acquire decision under `_lock`; the last holder closes the descriptor.
- **(4)** `require` runs before each `next` in `guard_iter`.
- **(5)** An empty or malformed `/api/ps` answer is `Gpu0Unreadable`; only a refused connection reads as nothing resident.
- **(6)** The swap sits after the cache hit in `conform_outro` and after the no-op return in `shot_snap.apply`; `run_isolated.py` is not in the diff.
- **(8)** All five paths in `_attempts` log both attempts. A failed release logs only attempt 1, since no second attempt ran.
- **(13)** The assertions are present.

## Gates, sentence lock, pin validation, release_auth

No change to acceptance logic is visible. `pinned.py`, release_auth and gate thresholds are not in the diff. `sentence_law.py` gains only the swap line in `apply_lead_in_pad`.

Behaviour changes around them:
- Gate G1 and the Whisper gates now refuse without the lease and GPU0.
- G1's encoder is a `gpu0.Model` proxy; any non-plain attribute read in the unseen gate body would raise `AttributeError`.
- `transcript_store.acquire` raises `GpuOOM` instead of returning `punctuation_failed`.
- PROVENANCE gains `gpu0` and `gpu0_oom` before `attest_run`. Whether release_auth constrains PROVENANCE keys is uncertain.