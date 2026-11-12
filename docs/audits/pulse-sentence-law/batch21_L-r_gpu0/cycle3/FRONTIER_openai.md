# gpt-6.1-sol (408 s) usage={'prompt_tokens': 43952, 'completion_tokens': 17010, 'total_tokens': 60962, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 43949, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 14853, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}

## BLOCKING findings

### 1. `swap_to()` and `release_all()` can unload a foreign Ollama model loaded after their initial check

**`pipeline/gpu0.py:459–467`** checks `_refuse_foreign()` and subsequently performs another residency read:

> `drop = [n for n in ollama_loaded() if n != name]`

That second list is **not filtered against `_ollama_ours`**. If another client loads a different model between the initial check and this read, it is passed to `_ollama_unload()`.

**`pipeline/gpu0.py:498–505`** has the same defect:

> `_ollama_unload(ollama_loaded())`

**`pipeline/gpu0.py:401–407`** sends unload requests without independently checking ownership. `_lock` cannot serialize another client's Ollama requests.

This is a concrete interleaving that unloads a foreign model. The earlier foreign check does not establish ownership of a later response.

### 2. `LocalLLM._post()` can bypass foreign-model refusal after ownership was correctly pruned

**`pipeline/story_semantics.py:197–200`** decides whether to swap using only generation and residency:

> `getattr(self, "_gpu0_gen", None) != gpu0.generation() or self.model not in gpu0.ollama_loaded()`

It does not check whether the resident name is still in `_ollama_ours`.

**`pipeline/gpu0.py:387–394`** removes ownership when a resident model is observed gone, but does not change `_gen`.

Consequently:

1. This run uses the model.
2. A residency read observes it gone and removes ownership.
3. Another client loads the same name.
4. `_post()` sees the same generation and a resident matching name, skips `swap_to()`, and submits the chat request.

The code correctly identifies the later load as foreign *if `foreign()` runs*. This path avoids running it.

### 3. Pending ownership survives a completed or failed request and can claim another client's later load

**`pipeline/gpu0.py:465–470`** records `"pending"` before the request. **`pipeline/gpu0.py:387–393`** preserves an absent pending entry indefinitely and promotes it whenever that name next appears.

A concrete affected path is **`pipeline/preflight.py:65–75`**:

> `"keep_alive": 0`

The preflight request can load and unload its model without any intervening residency observation. The pending entry remains. If another client subsequently loads the same name before cleanup, the next observation promotes that foreign load to `"resident"` ownership.

**`pipeline/gpu0.py:525–530`** then includes it in `leave()`'s unload list. A failed `_post()` request likewise has no pending-ownership cancellation in **`pipeline/story_semantics.py:207–218`**.

The pending state is evidence that a request was prepared, not proof that a later resident instance belongs to this run.

### 4. `release_all()` treats unknown process memory as proof of zero retained memory

**`pipeline/gpu0.py:509–513`**:

> `mine = sum(m or 0 for p, _, m in processes() if p == os.getpid())`

A `None` memory reading becomes zero. The release can therefore succeed without proving the process is below `CONTEXT_MAX_MIB`.

For example, with the current process reporting `None`, total memory of 24,564 MiB and used memory of 2,700 MiB:

- free memory exceeds the largest requirement plus margin;
- `mine` becomes zero;
- the release passes.

Meanwhile, **`pipeline/gpu0.py:354–358`** deliberately skips unlisted-memory accounting when a process reports `None`. Neither check proves that the failed model was freed. This defeats fix (9).

### 5. End-of-process cleanup is neither unconditional nor part of the terminal verdict

**`pipeline/run_fresh.py:1500–1507`** catches a cleanup refusal and only prints it:

> `except gpu0.Gpu0Stop as e:`  
> `print(...)`

It then closes the lease and exits according to the existing verdict. A CANDIDATE can therefore exit zero even when `leave()` reports that its Ollama model could not be unloaded.

**`pipeline/replay.py:106–114`** similarly writes the report and verdict before cleanup, then merely prints a cleanup refusal. Those saved outputs do not record the cleanup failure.

There are also paths that never call `leave()`:

- **`pipeline/backtest.py:237–243`** calls it only after `_backtest_days()` returns normally.
- **`pipeline/backtest.py:219–221`** calls `L.stop()` before `E.close()`; a stop exception skips `E.close()`.
- **`pipeline/replay.py:106–111`** performs report and verdict-file writes before reaching cleanup; a write failure skips it.

The claimed “every process end” finalizer is not implemented. Whether a particular skipped path leaves an Ollama model resident depends on the failure, but the cleanup and verdict defects are explicit.

### 6. Lost-runner HTTP failures still surface as ordinary errors

**`pipeline/story_semantics.py:209–218`** checks for a disappeared model only in the `URLError` / `ConnectionError` / `TimeoutError` branch.

The earlier `HTTPError` branch does this instead:

> `raise RuntimeError(f"Ollama HTTP {e.code}: {text[:400]}")`

Thus an HTTP failure reporting a terminated runner, without an explicit OOM spelling, becomes `RuntimeError` even if the model is gone. That branch never checks residency.

**`pipeline/preflight.py:70–75`** has the same classification gap: an HTTP error without a matching OOM string is re-raised.

An actual OOM behind any particular runner termination is **uncertain**. What is verifiable is that the claimed “lost runner whose model is gone” suspected-OOM handling does not cover HTTP failures.

### 7. Some malformed `/api/ps` answers escape as `TypeError`, not `Gpu0Unreadable`

**`pipeline/gpu0.py:375–388`** validates the outer dictionary and models list, but not the model-name type.

For this malformed response:

```json
{"models": [{"name": []}]}
```

the list construction succeeds. This later expression fails:

> `names = {n for n, _ in out}`

It is outside the parser's exception handler. The resulting unhashable-name `TypeError` is not converted to `Gpu0Unreadable`.

The malformed-answer test in **`pipeline/test_gpu0.py`, `TestOllamaReadingsFailClosed`** covers outer-container failures, not malformed entries. Fix (5) remains incomplete.

### 8. The CPU-session detector still fails open on malformed successful output

**`pipeline/conftest.py:54–57`** checks return codes and whether the UUID output is nonempty, then uses:

> `return any(... for line in b.stdout.splitlines())`

It never validates the compute-process rows. A successful command returning malformed nonempty output—for example, `[Not Supported]`—produces `False`, meaning “this process holds no GPU0 context,” rather than `None`.

Likewise, any nonempty malformed UUID is accepted. The detector fails closed on command failures, but not on unreadable successful responses. That is a remaining bypass of fix (7).

### 9. A retained model reference can survive a swap while the next model loads

**`pipeline/gpu0.py:612–626`** exposes the raw object:

> `return self._obj`

and “unloads” it by clearing only the proxy reference:

> `self._obj = None`

A caller retaining a `get()` result keeps the object alive. **`pipeline/gpu0.py:472–477`** then checks only whether enough memory exists for the incoming model; it does not prove the previous model was freed.

The same lifetime issue is acknowledged in **`pipeline/gpu0.py:580–590`**: the decoding iterator keeps its model alive. Its decoding guard checks the lease, not whether that model was displaced by another swap.

The API therefore permits retaining one model, swapping to another that fits beside it, and continuing to use the first. **Whether current production callers interleave decoding this way is uncertain from the shown code.** The claimed one-model-at-a-time construction nevertheless does not enforce that invariant.

## Not BLOCKING on its own

### 10. The structural tests do not establish the claimed AST-level guarantees

**`pipeline/test_gpu0.py:452–478`**, `test_no_model_is_built_outside_gpu0`, uses regular expressions for loader detection. AST is used only to exempt the `Embedder` class. Variants such as whitespace between a constructor name and `(` evade those expressions.

**`pipeline/test_gpu0.py:480–534`**, the NVENC test:

- treats the presence of `capture_output` or `stderr` as capture, regardless of its value;
- checks lexical line order, not whether the swap executes on the encode path;
- searches nested-function bodies through `ast.walk(fn)`.

These are verifiable test-acceptance gaps. They do not, by themselves, establish an additional production bypass.

The supplied diff does not verify execution of the claimed live or mutation proofs.