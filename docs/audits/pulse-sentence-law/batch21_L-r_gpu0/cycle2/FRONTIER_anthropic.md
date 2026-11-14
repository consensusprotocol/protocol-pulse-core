# claude-fable-5-2 (612 s) usage={'input_tokens': 64059, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 58993, 'output_tokens_details': {'thinking_tokens': 55423}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Verdict: BLOCK.** Findings are from reading the diff only; nothing was run. Lines are quoted by text, because I cannot assert line numbers inside the hunks.

## Blocking

**1. This pipeline's own leftover Ollama model HOLDs the next run.**
- `gpu0.py` `foreign()`: `if name not in _ollama_ours` uses process memory only.
- Nothing unloads at process end: `run_fresh.main` and `replay` finish with `run.gpu0_stack.close()` only.
- The next process then fails `preflight.check_gpu0` (`if foreign: return False`) or `stage_env` (`raise Hold(... not this run's ...)`), and the foreign rule forbids unloading it.
- The removed preflight code tolerated exactly this ("available with our model released").
- The `REQUIREMENT_MIB` comment ("resident 20548-20559 (nvidia-smi 01:43 / 01:55 ET)") shows the model observed resident at two times 12 minutes apart, i.e. it does stay loaded.
- `measure_gpu0.py` has the same problem: the parent's `gpu0.release_all()` after the `ollama:` child raises an uncaught `Gpu0Foreign`.
- Uncertain: whether `LocalLLM.stop()` unloads, and whether it runs on a HOLD path; neither is in the diff.
- `TestBackToBack` cannot see this: the pinned path ends on Whisper/NVENC.

**2. `_ollama_ours` goes stale, so a foreign model can be unloaded.**
- It shrinks only inside `_ollama_unload`.
- `preflight.check_ollama` adds the name via `swap_to`, then Ollama unloads the model itself (`"keep_alive": 0`), leaving the name set.
- `preflight.main` then runs `mine = [n for n in gpu0.ollama_loaded() if n in gpu0._ollama_ours]` and `gpu0._ollama_unload(mine)`.
- If another client loaded the same model during the remaining checks, the preflight unloads it, and `left_as_found` passes.
- The same applies in a run after keep_alive expiry or Ollama eviction: another client's `gemma3:27b` counts as ours and the next `swap_to` drops it.
- The live "another client" test covers only the case where this process has not yet requested the model.

**3. NVENC out-of-memory conversion is incomplete against claim (11).**
- The diff has 14 `raise_if_oom` calls plus `shot_snap`; the claim says 14 + 5 + 1.
- Five functions get `gpu0.swap_to("nvenc")` and nothing else: `config.conform_outro`, `pulse_transitions.render_wipe`, `pulse_transitions.concat`, `run_isolated.prerender_clips`, `sentence_law.apply_lead_in_pad`.
- `_find_outro` / `_find_outro_vert` use `if gpu0.is_oom(e)` on a `CalledProcessError`. That sees the out-of-memory only if `conform_outro` captures stderr.
- If it does not, the NVENC out-of-memory becomes "falling back to qa_dir". Uncertain: those subprocess bodies are not in the diff.
- No test checks stderr capture or conversion for these five.

**4. Opening the lease file makes a process "ours".**
- `_lease_holders()` matches any descriptor whose path is the lease file (`os.path.realpath(os.readlink(...)) == target`).
- It does not check that the descriptor's open file description holds the flock.
- A same-user process with a read-only descriptor on `/tmp/pulse_gpu0.lease` is therefore exempt from `foreign()`.

## High

**5. An Ollama runner that dies of out-of-memory is not named.**
- `story_semantics._post`: `except (urllib.error.URLError, ConnectionError) as e: if gpu0.is_oom(e)`.
- A dropped connection's text contains no out-of-memory wording, so it re-raises as a connection error.
- `TimeoutError` from the read is not in the tuple.
- Regression: `HTTPError` now becomes `RuntimeError(f"Ollama HTTP {e.code}...")`. Any caller catching `URLError` or `HTTPError` no longer matches (callers not shown).

**6. `release_all` does not prove the failed model was freed.**
- `need = max(REQUIREMENT_MIB.values()) + MARGIN_MIB` is 21624 of 24564 MiB, so 2940 MiB may remain used.
- A pinned `whisper:medium` (2649), embedder (1379) or resemblyzer (775) passes.
- The live test docstring "With the model pinned, release_all times out" is false by these numbers; only the attempt-2 allocation makes that test load-bearing.

**7. `swap_to("nvenc")` runs before it is known that an encode will happen.**
- `conform_outro` swaps before its "content-keyed cache" check; `shot_snap.apply` swaps before its `{"snapped": False}` return.
- A foreign user or a missing lease now stops work that needed no GPU.
- Because `Gpu0Stop` is a `BaseException`, the `_find_outro` fallback no longer applies.

**8. Entry points without a lease die with an uncaught `BaseException`.**
- `qa_gates._gpu0()` says "importable when this file runs on its own too", but takes no lease.
- `backtest.main` catches no `Gpu0Stop`.
- A Python child started with default `close_fds` loses custody and cannot acquire the lease. Uncertain whether any stage spawns such a child.

**9. Retry restructure (`Run._attempts`).**
- A content HOLD on attempt 2 is rewritten as `"infrastructure: {name}: CUDA out of memory on attempt 1 ...; the retry then held: {h}"`. Uncertain whether anything keys on the `infrastructure:` prefix.
- `is_oom` matches `out of memory` in any exception text or in `e.output[-4000:]`. A non-CUDA error then gets a full stage retry and the label "CUDA out of memory twice".
- `drop_traceback` discards the stack without writing it anywhere.
- The idempotency argument is given for prepare only, but every stage is retried.

## Medium / low

- **conftest is weaker than claim (18).** `_holds_gpu0_context` returns `False` on nvidia-smi failure, checks only `os.getpid()`, and runs only at module boundaries.
- **`_locked()` is itself a brief acquisition** (`LOCK_EX | LOCK_NB` then `LOCK_UN`). A concurrent `flock -n 8` in the wrapper can exit 75 with no holder.
- **The lease is path-based.** If the file is deleted mid-run, `_fds_on` stops matching and custody `held()` turns false. A new process can then lock a new inode.
- **`foreign()` can HOLD a clean run falsely.**
  - A compute process with unreadable `used_memory` counts as 0 (`m or 0`), which trips the unlisted rule.
  - `processes()` and `memory()` are separate reads. Uncertain whether an Ollama unload can open a window.
- **`release_gpu0_for_whisper`** still runs "this function's own proof" after `swap_to`. Its docstring says "Unload every model on the GPU0 Ollama", so a foreign model arriving after the swap could be unloaded (loop body not shown).
- **`LocalLLM.start()` / `stop()`** are not shown, and the Ollama test whitelists the whole of `story_semantics.py`.
- **One-model thrash.** Embedder and gemma used to be co-resident. Each switch now reloads about 20 GB (`_backtest_days` uses `E` and `L` together). G1 has the same pattern with resemblyzer and medium. Uncertain how often they interleave.
- **`Model.__getattr__`.** `hasattr` / `getattr(..., default)` on an inner object now silently yields the default. `Model.get()` hands out the raw object; no test forbids keeping it.
- **`transcript_store.acquire`.** The `status="gpu0_out_of_memory"` log line is dead for real out-of-memory errors, because a `GpuOOM` from `guard` skips `except Exception`.
- **REPORT.** `rec["gpu0_peak_mib"] = self.sampler.peaks.get(name)` prints `None`, never "not sampled". Replay records no `sampler_errors` and no `at_start`, so the total shows `None`.

## Gates, sentence lock, pin validation, release_auth

No hunk touches their rules. The outcome-affecting changes are:
- the retry in finding 9;
- proxies replacing the Whisper and VoiceEncoder objects;
- new PROVENANCE keys written before `attest_run`. Uncertain whether attestation validates keys.

## Tests that are not load-bearing

- **`TestBackToBack`** is opt-in. It never asserts the return code, the verdict, or that `gpu0_oom` is empty, so an out-of-memory plus retry passes it.
- **`test_no_model_is_built_outside_gpu0`** is a six-pattern deny-list.
  - It misses `.to(device)`, `torch.device(...)` and libraries that pick CUDA by default.
  - Its allow entry exempts every `.to("cuda` in `story_semantics.py`.
  - `FILES` is a flat glob of `pipeline/*.py` plus `qa_gates.py`, not the import closure.
- **`test_every_nvenc_function_swaps_to_nvenc_first`** checks top-level functions only, and only the literal `h264_nvenc`. It checks presence of the swap, not that it comes first, and not out-of-memory conversion.
- **`test_the_gpu0_ollama_is_called_only_through_gpu0`** matches two strings and exempts two whole files.
- **`test_an_out_of_memory_is_never_a_failure_status`** raises a raw `RuntimeError`, not the `guard` path. Its `release_whisper` stub is vestigial.
- **`test_every_spelling_is_recognised`** covers none of the spellings added in fix (10).
- **`TestOneWhisperModelAtATime`** does not stub `_ollama_pids`, so it depends on the host's `ss`.
- **`TestStageRunner`** mocks `release_all` throughout.