# gpt-6.1-sol (397 s) usage={'prompt_tokens': 28924, 'completion_tokens': 16811, 'total_tokens': 45735, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 28921, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 13097, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}

## CYCLE 1 — BLOCK

The diff does not enforce the stated ownership, unloading, or retry guarantees.

### (a) Load paths and (c) lease/custody holes

**1. Cached models bypass `require()` entirely.**  
`pipeline/gpu0.py:474–481` calls `swap_to(self.key)` only under:

> `if self._obj is None:`

A model loaded inside a lease remains callable after that lease exits. Subsequent `get()`, `__call__()`, and `Whisper.transcribe()` use the cached object without checking custody, `CUDA_VISIBLE_DEVICES`, or foreign processes (`pipeline/gpu0.py:493–517`).

The Ollama path has the same hole. `pipeline/story_semantics.py:193–205` skips `swap_to` when its generation matches and its model appears loaded:

> `if getattr(self, "_gpu0_gen", None) != gpu0.generation() or self.model not in gpu0.ollama_loaded():`

The following HTTP request has no independent `require()`. Reusing that `LocalLLM` after relinquishing the lease still sends inference requests. Another client loading additional Ollama models does not update this process’s `_gen`.

**2. `Model.unload()` does not establish that the model was deleted.**  
`pipeline/gpu0.py:483–487` only sets `_obj = None` and removes the wrapper from `_resident`. Meanwhile:

- `get()` returns the raw object (`pipeline/gpu0.py:474–481`).
- Non-callable attributes are returned raw (`pipeline/gpu0.py:493–498`), including a batched pipeline’s underlying `.model`.
- Callable wrappers capture the original bound method in `attr` (`pipeline/gpu0.py:496–504`).

A concrete permitted sequence is: obtain a bound method, swap to another model, then invoke the saved method. The saved method keeps the previous model alive and its wrapper checks neither residency nor custody.

`Whisper.transcribe()` also returns a lazy iterator (`pipeline/gpu0.py:513–517`). Nothing invalidates outstanding decoding iterators on a later swap. Whether particular faster-whisper iterators retain GPU allocations throughout decoding requires runtime confirmation; the diff provides no revocation mechanism.

**3. Custody authorizes simultaneous processes; it does not serialize their GPU use.**  
`pipeline/gpu0.py:151–162` treats an inherited locked descriptor as sufficient and simply yields. `_lock`, `_resident`, and `_models` are process-local globals (`pipeline/gpu0.py:85–89, 520–544`).

Two processes sharing the wrapper’s open file description can therefore both pass `require()` and load different models using independent resident registries. Parent/child GPU processes are also exempted by `foreign()` (`pipeline/gpu0.py:289–294`).

The wrapper establishes that shared descriptor at `scripts/pulse_check_run.sh:75–86`. Whether its omitted command sequence currently overlaps GPU work is **uncertain**. The custody API permits the overlap.

**4. `held()` acquires locks instead of merely recognizing custody.**  
`pipeline/gpu0.py:109–121` probes every matching descriptor with:

> `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)`

If a process merely has an unlocked descriptor open to the lease file, this call acquires the lock and returns `True`. `lease()` then takes its “already held” branch without recording an owner or arranging to close that descriptor (`pipeline/gpu0.py:151–162`).

Thus a purported predicate has a persistent acquisition side effect, and a lease context can return without managing the acquired lock’s lifetime.

**5. Thread re-entrancy does not preserve lease lifetime.**  
The nested path increments/decrements `"depth"` (`pipeline/gpu0.py:153–159`), but the original context unconditionally removes `_own[target]` and closes the file (`pipeline/gpu0.py:180–185`).

If thread B enters while thread A owns the lease, A can exit and release it while B remains inside its context. The depth counter does not prevent that. Model calls also execute outside `_lock` (`pipeline/gpu0.py:501–517`), so another thread can swap while an inference call is running.

**6. A complete NVENC launch shown here drops child custody.**  
The measurement child inherits the lease using `pass_fds` (`pipeline/measure_gpu0.py:72–96`). Its FFmpeg launch does not:

> `subprocess.run([...], check=True, timeout=300)`

—`pipeline/measure_gpu0.py:47–53`.

Python’s default descriptor closing means that FFmpeg does not inherit the lease descriptor. Its parent holds a lease, but the process performing the GPU load does not hold the specified descriptor custody. The renderer subprocess launch bodies are omitted, so their inheritance behavior is **uncertain**.

**7. Backtest lease cleanup is not exception-safe.**  
`pipeline/backtest.py:215–220` manually enters the lease, then constructs `Embedder` and starts `LocalLLM` **before** entering the `try`. A construction/start failure skips the shown cleanup.

Inside cleanup, `L.stop()` and `E.close()` precede `lease.__exit__()` (`pipeline/backtest.py:230–233`); either raising also skips lease release. The lock can remain held for the lifetime of a surviving caller process.

### (d) Free-memory proof and (e) foreign-process classification

**8. `swap_to()` explicitly bypasses its memory requirement for “already resident.”**  
`pipeline/gpu0.py:371–382` preserves the requested model, determines `already`, and accepts:

> `if already or total - used >= need:`

That is not verification that free memory meets requirement plus margin. An already-resident Ollama model is also expressly excluded from unloading through `_ollama_unload(keep=name)`.

The test codifies this exception rather than challenging it: `pipeline/test_gpu0.py:133–139` expects the resident model to remain and no unload to occur.

**9. The memory wait does not continue enforcing the foreign-process rule.**  
`foreign()` is called once before unloading (`pipeline/gpu0.py:366–369`). The subsequent wait checks only total memory (`pipeline/gpu0.py:379–387`), and `Model.get()` builds afterward (`pipeline/gpu0.py:474–480`).

A foreign allocation arriving during that interval is not rejected if enough capacity remains. Combined with the raw-reference and cross-process holes above, “enough free memory” can coexist with another resident model; it is not proof of one-model residency.

**10. Process ancestry is substituted for lease ownership in both directions.**  
`pipeline/gpu0.py:289–294` constructs:

> `ours = {os.getpid()} | _ancestors() | _descendants() | _ollama_pids()`

There is no custody check for those PIDs.

Consequences verifiable from that classifier:

- An ancestor or descendant using GPU0 without the lease is accepted.
- A sibling process holding the same inherited lease descriptor is classified foreign, unless separately covered by the Ollama exemption.
- Every identified Ollama listener/runner is accepted regardless of which client submitted its job.

The shared Ollama server is not made lease-aware by this diff. Another client can submit work through the exempt server.

**11. Enumeration can either miss users or HOLD a clean run.**  
`pipeline/gpu0.py:220–231` queries only:

> `--query-compute-apps=pid,gpu_uuid,used_memory,process_name`

It silently skips malformed/nonmatching rows instead of reporting unreadability. It does not enumerate every category of GPU-memory user. Whether this driver reports the relevant NVENC processes through that query is **uncertain**.

`_ollama_pids()` ignores `ss` and `pgrep` return codes and recognizes only the listener’s immediate children (`pipeline/gpu0.py:275–286`). Missing PID visibility or a deeper runner hierarchy can make a legitimate runner appear foreign. The listener search is by port, not by the configured address.

**12. Cleanup can disrupt an owner without holding the lease.**  
`release_all()` has neither `require()` nor a foreign-process check; it unconditionally unloads every model reported by the GPU0 Ollama listener (`pipeline/gpu0.py:396–408`).

A caller without custody can therefore invoke this API and unload the active lease holder’s Ollama model. Nothing distinguishes this run’s requests from another client’s requests.

**13. The “idle” requirement can reject usable, model-free GPU memory.**  
`pipeline/gpu0.py:396–418` defines idle as:

> `min(REQUIREMENT_MIB.values())`

That is currently the **600 MiB NVENC requirement**, not a measured idle/context baseline (`pipeline/gpu0.py:44–53`). Persistent contexts exceeding that threshold make every recovery time out, even if no model weights remain and the incoming model would fit.

Whether that occurs on this host is **uncertain**; the diff supplies no idle-baseline assertion establishing the threshold.

**14. Preflight checks “no additional residency,” not empty GPU0, and performs no final cleanup.**  
`pipeline/preflight.py:161–172` accepts unchanged pre-existing Ollama residency:

> `extra = sorted(set(gpu0.ollama_loaded()) - set(found_models))`

If gemma was present initially and remains present with comparable memory, this returns `True` while reporting:

> `"no model left resident"`

That message is false for that input.

`main()` only calls this assertion after the checks; it does not finally unload models (`pipeline/preflight.py:175–184`). `keep_alive: 0` in the generation request is not a cleanup guarantee when that request fails (`pipeline/preflight.py:67–71`).

### (b) OOM preservation and (f) recovery

**15. The retained OOM traceback can retain exactly what recovery needs to release.**  
`Run._attempts` stores the exception in `err` and retains it while calling `release_all()` (`pipeline/run_fresh.py:189–214`).

Model call frames contain `obj` (`pipeline/gpu0.py:506–517`), and guards retain the original exception as `__cause__` (`pipeline/gpu0.py:442–451`). A failed embedder call can additionally retain CUDA tensors in its traceback frame (`pipeline/story_semantics.py:87–96`).

Setting `Model._obj = None` does not release those traceback-held references. Garbage collection and `empty_cache()` do not reclaim live tensors. Recovery can therefore wait on memory retained by its own saved exception rather than retrying.

**16. OOMs still have paths to suppression or reclassification.**

- `_empty_caches()` catches every `Exception` and executes `pass`, including a matching CUDA OOM (`pipeline/gpu0.py:345–353`).
- `_ollama_unload()` converts an `OSError`/HTTP error into `Gpu0NotFree` without checking for OOM (`pipeline/gpu0.py:318–324`).
- Preflight’s generation request is not guarded. An HTTP OOM response reaches `run_checks()` as an ordinary exception and becomes the type-only `"HTTPError (raised)"`, not an OOM retry (`pipeline/preflight.py:67–71, 149–158`).
- `LocalLLM._post()` truncates the HTTP body **before** classification: `e.read().decode(... )[:400]` (`pipeline/story_semantics.py:206–210`). An OOM indication later in the body is missed.

`transcript_store.acquire()` also calls `release_whisper()` before raising its replacement `GpuOOM`, without preserving the original if cleanup raises (`pipeline/transcript_store.py:480–489`). Its new OOM test stubs that cleanup away (`pipeline/test_punct_word_pass.py:168–184`), so it does not exercise that failure path.

**17. Retry count is bounded, but both attempts are not logged.**  
The visible loop permits at most two `fn()` invocations:

> `for attempt in (1, 2):`

—`pipeline/run_fresh.py:182–186`.

However, successful execution returns before an attempt record is written. After first-attempt OOM and second-attempt success, provenance contains only the failure. The live test expressly expects one log entry for two attempts (`pipeline/test_gpu0_live.py:104–114`).

On the second OOM, `_attempts` raises HOLD before calling `release_all()` (`pipeline/run_fresh.py:202–214`). It does not perform the shown recovery cleanup for that failure.

The REPORT column also counts OOM entries, not retries: two failed attempts display `2` despite only one retry (`pipeline/run_fresh.py:1293–1298`).

### (f) Side effects and (g) acceptance preservation

**18. Retrying the entire stage has no rollback or idempotency boundary.**  
`pipeline/run_fresh.py:178–214` simply invokes the same `fn()` again. It does not restore files, mutable run state, or completed operations.

The diff identifies existing in-place mutators:

- `apply_lead_in_pad`: “Prepend …” with “atomic replace” of `qa/final_<clip>.mp4` (`pipeline/sentence_law.py:813–822`).
- `shot_snap.apply`: “Snap … in place” (`pipeline/shot_snap.py:48–58`).

If such a mutation completes before a later OOM, retry can encounter the already-mutated artifact. Atomic replacement does not make an operation idempotent.

Whether the actual containing stages regenerate their inputs, or gates detect repeated padding/snapping, is **uncertain** because those bodies are omitted. I cannot verify a gate bypass from this diff.

The visible gate changes replace loaders; the sentence-law changes insert `swap_to`. No acceptance-predicate change to pin validation, sentence locking, or `release_auth` is shown. That does **not** establish behavioral equivalence under whole-stage retries and persistent side effects.

### (h) Evidence and test weaknesses

**19. The peak table is not reliable per-stage peak evidence.**  
`_attempts()` labels the sampler only before calling the stage (`pipeline/run_fresh.py:182–186`), but `stage_env()` creates it at the stage’s end (`pipeline/run_fresh.py:285–294`). Consequently, the normal `env` stage has no labeled sample.

`PeakSampler._sample()` reads memory before reading the current label, without synchronization (`pipeline/gpu0.py:561–572`). A stage transition during the query can attribute memory to the wrong stage. One-second polling also provides sampled maxima, not verified allocation peaks.

**20. The live “every stage” must-fail does not execute every stage.**  
`pipeline/test_gpu0_live.py:72–82` tests four stand-ins:

- pinned: Whisper transcription;
- review: `swap_to` only;
- render: `swap_to` only;
- gates: Whisper transcription.

It does not execute actual review HTTP inference, NVENC encoding, complete stage bodies, or all stages. It cannot expose the cached `_post()` hole or retry side effects in the real pipeline.

The own-resident swap test covers only one transition, embedder → pinned Whisper (`pipeline/test_gpu0_live.py:85–96`). The real OOM test is an oversized standalone allocation, not an OOM inside a model call retaining model/tensor traceback references (`pipeline/test_gpu0_live.py:99–124`).

**21. The back-to-back test can pass two unsuccessful, incomplete runs.**  
`pipeline/test_gpu0_live.py:130–149`:

- records and prints return codes without asserting them;
- does not require a candidate verdict or completion of the expected stages;
- does not require numeric samples for every stage;
- only rejects two substrings in stage reasons;
- calls `gpu0.release_all()` before **each** run.

A run HOLDing early for another reason can pass these assertions. The external cleanup before run two also hides residency left by run one.

**22. The measurement claims are not established by the supplied evidence.**  
`pipeline/measure_gpu0.py:76` defaults to **60 seconds**, while its own comment says at least 480 seconds is needed to fill the batched workload.

Child failures are recorded and printed, but do not cause a failing exit status (`pipeline/measure_gpu0.py:95–111`). Sampling errors are discarded (`pipeline/measure_gpu0.py:86–91`).

The constants claim a 600-second measurement (`pipeline/gpu0.py:41–53`), but no measurement results are included. Whether those requirements were actually measured under the claimed workloads is **uncertain**.