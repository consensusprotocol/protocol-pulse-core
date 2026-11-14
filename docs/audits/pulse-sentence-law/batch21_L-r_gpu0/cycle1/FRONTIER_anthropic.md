# claude-fable-5-2 (466 s) usage={'input_tokens': 45828, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 44923, 'output_tokens_details': {'thinking_tokens': 39469}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Scope:** I only have the diff. New files have no reliable line numbers here, so each finding quotes the line and names file and function. "Verified" means read from the diff; nothing was executed.

The five worst, all detailed below: the retry cannot free the model that OOM'd (f1); any Ollama client loads onto GPU0 without the lease (e1); the live OOM must-fail passes without `release_all` doing anything (h1); a second-attempt error replaces the OOM (b1); the preflight "left as found" assert is vacuous when gemma was already resident (d2).

## (a) Load paths that bypass swap_to/require

- **Verified, raw objects escape the Model.** `gpu0.py` `Model.__getattr__`: `if not callable(attr): return attr`. Any non-callable attribute leaves unguarded and holds a strong reference that `unload()` cannot break. `test_punct_word_pass.py` does exactly this with `a.model.name`.
- **Verified, direct loaders after a bare swap.** `measure_gpu0.py` CHILD: `gpu0.swap_to("resemblyzer")` then `enc = VoiceEncoder()`; the `ollama:` and `nvenc` branches likewise load directly. "Nothing calls a loader directly" is already false inside the change.
- **Verified, NVENC is not gated by construction.** `swap_to("nvenc")` is a one-time check at function entry (e.g. `render16.py` `render_16x9`). Nothing ties an individual ffmpeg invocation to it, and nothing enforces the "one … encode at a time" that the 600 MiB figure assumes.
- **Uncertain, not in the diff:**
  - `LocalLLM().start()` (used in `backtest.py`: `E, L = sm.Embedder(), sm.LocalLLM().start()`); only `_post` was changed. If `start()` warms the model, it bypasses.
  - Any other client of `:11434` (e.g. the vision checklist) and any other `h264_nvenc`/`-hwaccel cuda` site, e.g. the G9 re-encode in `qa_gates.py`.
  - mediapipe in `render_vertical.py` (`reframe_fixed_crop`, `render_vo_visual_vert`): if it uses a GPU delegate, that memory is in no requirement.
  - `word_diff.py`: `gpu0.whisper(ASR["model"])`. If that name is not a `REQUIREMENT_MIB` key, a clean run HOLDs with "never loaded".

## (b) OOM or stop surfacing as a different error, or swallowed

1. **Verified, attempt 2 can rename the OOM.** `run_fresh.py` `_attempts`: `except Hold: raise`, with no attempt check. If attempt 1 OOMs and attempt 2 raises a Hold or any other exception from half-done state, the HOLD reason is that second error. The OOM survives only in `prov["gpu0_oom"]`.
2. **Verified, the OOM is still recorded as a video error.** `transcript_store.py` `acquire`: `LAST_ERROR[video_id] = …` and `_log_attempt(video_id, step=step, status="error", …)` run before `if gpu0.is_oom(e):`. Whether anything trusts that log is uncertain.
3. **Verified, the regex is a closed list.** `gpu0.py` `_OOM` has `CUBLAS_STATUS_ALLOC_FAILED` but not `CUDNN_STATUS_ALLOC_FAILED`, and none of Ollama's "unable to allocate" spellings. Those still become "transcription failed" in `select_passages.py` or `RuntimeError("Ollama HTTP …")`.
4. **Verified, `_post` converts only `HTTPError`.** A runner that dies mid-request (connection reset, `URLError`) is not inspected.
5. **Verified, "nothing" when unreadable.** `_attempts`: `gpu0.describe(entry.get('gpu0_processes') or [])`. If nvidia-smi was unreadable, the HOLD says "on GPU0: nothing", contradicting "never read as 'nothing there'".
6. **Uncertain, NVENC fallback.** `render16.py` `_find_outro` detects OOM only through `is_oom(e)` reading `e.stderr`. If `conform_outro` does not capture stderr, the OOM still falls back to qa_dir.
7. **Uncertain, uncaught stop in main.** `replay.py` gained `except rf.gpu0.Gpu0Stop`; no such clause is added to `run_fresh.main` in this diff. A stop raised outside `Run.stage` passes `except Exception`. A bare `except:` or a plain `threading.Thread` anywhere would also swallow it.

## (c) Lease and custody

1. **Verified, `held()` is not a probe.** `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); return True` runs on every fd open on the path. With the lease free, any process that merely has the file open acquires it: no record, no `_own` entry, never released. The test `…a_reopened_one_is_not` only checks this while the parent holds it.
2. **Verified, `depth` is never read.** `lease()` does `h["depth"] += 1`, but the outer exit does `_own.pop(target, None); f.close()` unconditionally. `_own` is also mutated without `_lock`.
3. **Verified, `holder()` can cause a spurious busy.** It takes `LOCK_EX` on a private description, then `LOCK_UN`. A concurrent `flock -n 8` or `lease(wait_s=0)` in that window fails. The window is narrow.
4. **Verified, the path is the identity.** `lease_path()` re-reads `PP_GPU0_LEASE` on every call, so any process with a different value has a private lease. If `/tmp/pulse_gpu0.lease` is unlinked, `_fds_on` stops matching ("(deleted)"), `held()` goes False mid-run, and a new locker gets a second lease.
5. **Verified, custody is plural.** Parent and child both pass `require()` (`pass_fds=(fd,)` in `measure_gpu0.py` and `test_gpu0_live.py`). `_resident` and `_lock` are per-process, so "one model at a time" does not hold across them.
6. **Verified, wrapper record is unescaped.** `scripts/pulse_check_run.sh`: `printf '{"pid": %s, "owner": "pulse_check_run %s (%s)" …' … "${ARGS[*]:-auto}"`. A quote in the args makes the record invalid and the holder "unrecorded".
7. **Uncertain, fd 8 leaks.** Bash's fd 8 is inheritable; any background child of the wrapper, or an `os.system`/fork child of run_fresh, keeps the lease after the wrapper exits. Nothing checks the recorded pid is alive.
8. **Uncertain, wrong card.** `require()` checks `CUDA_VISIBLE_DEVICES != "0"` only, while all verification uses `nvidia-smi -i 0`. Without `CUDA_DEVICE_ORDER=PCI_BUS_ID`, CUDA device 0 need not be nvidia-smi index 0.

## (d) swap_to declaring free when it is not, or refusing forever

1. **Verified, `already` skips the proof.** `if already or total - used >= need: break`. For Ollama, `already` is just `name in ollama_loaded()`. `test_the_model_already_resident_is_kept` enshrines this.
2. **Verified, the preflight assert is relative.** `preflight.py` `left_as_found`: `extra = sorted(set(gpu0.ollama_loaded()) - set(found_models))` and `used <= found_used + slack_mib`. If gemma was resident before the preflight (the stated normal state), leaving it resident passes. The test covers only `found=100, []`.
3. **Verified, the idle threshold is not an idle measurement.** `release_all`: `idle_mib = min(REQUIREMENT_MIB.values())`, i.e. NVENC's 600. The recorded `at_start.memory_mib` is not used. If the baseline plus this process's CUDA contexts exceeds 600 MiB, every release times out at 180 s. The actual figure is uncertain.
4. **Verified, `release_all` has no `require()` and no `foreign()`.** It unloads every Ollama model without a lease.
5. **Verified, the nvenc figure comes from a synthetic workload.** `measure_gpu0.py`: `testsrc2=size={size}:rate=30 … -f null -`, with no decode, filters or overlays. Default `MEASURE_SECONDS` is `"60"`, while the constants claim 600 s.
6. **Verified, the check is point-in-time.** The Ollama load happens after `swap_to` returns, with nothing held in between (see e1).

## (e) Foreign-process classification

1. **Verified, Ollama is a lease-free door.** `foreign()`: `ours = {os.getpid()} | _ancestors() | _descendants() | _ollama_pids()`. Any other session can load any model through the exempt server mid-stage and is never named. Conversely `_ollama_unload` evicts other sessions' models.
2. **Verified, ancestors are exempt by ancestry, not lease.** `_ancestors()` walks to pid 1. An orchestrator or pytest parent with its own GPU0 memory is invisible and cannot be unloaded.
3. **Verified, silent "nothing there".**
   - `_ollama_pids` never checks the `ss` or `pgrep` return codes.
   - `processes()` drops unparsable lines: `if len(p) == 4 and p[1] == uuid and p[0].isdigit()`.
   - `--query-compute-apps` omits graphics-type processes.
   - `_descendants()` does `continue` on any `/proc/…/children` error.
4. **Uncertain, clean-run HOLD.** If Ollama runs as another user, `ss -p` shows no pid unprivileged, the runner becomes foreign, and every run HOLDs. The old code used `_listener_pid()`, not shown.
5. **Verified, a reparented own child is foreign.** For example ffmpeg orphaned by a shell timeout. Arguably correct, but it HOLDs a run on its own leak.

## (f) The retry

1. **Verified by reading, the retry keeps the failed model alive.** `_attempts`: `err = e` stays live through `entry["release"] = gpu0.release_all()`. `err.__traceback__` and `__cause__` pin the failed frames (`obj` in `Whisper.transcribe`, `attr` in `call`, `it` in `guard_iter`). `Model.unload()` only does `self._obj = None`. The model that OOM'd cannot be collected, so `release_all` should time out into "did not come free". No test covers this (see h1).
2. **Bounded: yes, per `stage()` call** (`for attempt in (1, 2)`). Nested stages are uncertain.
3. **Verified, "both attempts" are not logged.** A successful attempt 2 writes nothing; `test_one_retry_then_success` asserts `len(log) == 1`. The REPORT column "out-of-memory retries" is `len(...)` of OOM entries, so two OOMs with one retry prints 2.
4. **Verified, the whole stage is retried, over in-place mutators.** `sentence_law.apply_lead_in_pad` ("Prepend … to qa/final_<clip>.mp4 (atomic replace)") and `shot_snap.apply` ("in place") are not idempotent. Whether the enclosing stage regenerates the clips first is uncertain. The declared pad in `cuts_final.json` is what "every gate knows", so this must be proven. `_log_attempt` entries and any `run.prov` appends also double.

## (g) Gates, sentence lock, pin validation, release_auth

- **Verified, preflight acceptance changed.** `need = max(GPU0_FREE_MIB, max(gpu0.REQUIREMENT_MIB.values()) + gpu0.MARGIN_MIB)` is 21624, up from 20000. There is a new failing check `gpu0_left` and a new `return 3`.
- **Verified, `qa_gates.py` objects are now proxies.** `encoder = _gpu0().model("resemblyzer", VoiceEncoder)`: `_`-prefixed attributes raise and dunder protocols bypass `__getattr__`. A standalone gate run without a lease now dies with `LeaseMissing` (a BaseException) instead of returning a verdict.
- **Verified, exception type changed.** `story_semantics.py` `_post`: `raise RuntimeError(f"Ollama HTTP {e.code}: {text}") from None`. Any caller catching `HTTPError`/`OSError` no longer matches.
- **Verified, an OOM video is no longer dropped.** `acquire` used to return `f"{step}_failed"`; it now raises, so the stage is retried or HOLDs. Presumably intended, but selection behaviour changes.
- **Uncertain.** New keys (`gpu0`, `gpu0_oom`, `gpu0_peak_mib`) are written before `attest_run`; any strict-schema or hash effect on release_auth is not visible. Sentence lock and pin validation are not touched in the diff.

## (h) Tests

1. **Verified, the live OOM test is not load-bearing.** `test_gpu0_live.py`: `torch.empty(int(40e9), …)` cannot fit on an empty 24 GB card, nothing is resident, and recovery is scripted by `if len(attempts) == 1:`. Remove the body of `release_all` and only `assertIn("after", …)` notices. It never OOMs with a loaded model.
2. **Verified, "every stage kind" is four labels on lambdas** (`gpu0.swap_to("nvenc")` etc.), not the real stage functions. A bypass in a real stage is not caught.
3. **Verified, the back-to-back test is weak.**
   - It calls `gpu0.release_all()` before each run, erasing the leftover state it exists to test.
   - It stores the exit code (`tables.append((run_dir, r.returncode, table))`) but never asserts it or the verdict.
   - It does not check that peaks are numeric.
   - It is skipped unless `PP_GPU0_LIVE=1`.
4. **Verified, the stubs hide the real code.** `Box` stubs `memory`, `processes`, `ollama_loaded`, `_ollama_pids` and `_ollama_unload`. Every `TestStageRunner` case mocks `release_all`. The nvidia-smi/ss parsing, the unload wait and the release threshold never run on CPU.
5. **Verified, nothing enforces "no direct loader".** No test greps for `WhisperModel(`, `.to("cuda`, `h264_nvenc` or `:11434` outside gpu0.
6. **Verified, the incident is not reproduced live.** No test puts gemma on Ollama via another client and then runs a Whisper stage; `TestOwnResidentModelIsSwappedOut` uses the Embedder.
7. **Verified, conftest takes the real lease for CPU runs.** With `CUDA_VISIBLE_DEVICES` unset it runs `os.environ["CUDA_VISIBLE_DEVICES"] = "0"` and takes the lease. A CPU-only pytest run blocks production (wrapper exit 75) and vice versa. `segment_v1/` has no conftest.
8. **Verified, `test_every_spelling…` asserts `OSError(12, "Cannot allocate memory")` is not OOM** and has no cuDNN or Ollama spellings.
9. **Verified, the peak table is a 1 s sample** of `memory.used`. It is a lower bound that misses the transient spikes that cause an OOM.