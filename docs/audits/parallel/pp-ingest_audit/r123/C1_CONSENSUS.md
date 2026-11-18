# r123: the miner's last fallback, the local model on a free card under the lease, cycle 1: consensus

Reviewers (Heimdall, diff-scoped; qwen + muse, glm out by ruling 119 (3)). qwen3.8-27b (102 s, $0.007 reported): "The
code is logically sound ... The tests are comprehensive and verify the integration with the real lease client", no
defect. muse-spark-open (187 s, $0.005 reported): "P0 CRITICAL: (none) ... P1 HIGH: (none) ... This code is ready for
production", three P2s and three P3s. Cycle 1: $0.0120 of the $1.00 cap (455 changed lines; COST.json).

## Agreed by both (verified)
- No GPU stop can reach the miner's threads: the client renames every gpu0.Gpu0Stop as Gpu1Unavailable
  (services/gpu_lease_client.py:47) and complete() reads it as BackendError("busy"); `busy` is in neither RETRY nor
  REJECTED, so Router._try (providers.py:1014, 1020) neither retries it on the card nor counts it as a rejected try: the
  work waits (outage). test_r123 runs the main tree's real client file with a stand-in gpu0 raising LeaseBusy.
- The yield: `reached` is False only for a refusal; success and the request's own errors leave the card free for
  yield_s. enabled() is a check (config + file), never a load or a lease (B3). A client that is not the API is never
  cached. The local back-end never feeds the outage clock (downsignal.py:182, vendor ultron-gpu1). Law L-x holds.
- One thread at a time in complete(): the router's per-back-end BoundedSemaphore of max_inflight 1 (providers.py:819).

## Fixed
- None needed in the code. The audit context's excerpt of the client began one line late (at `import os`), which made
  qwen ask whether `importlib` was imported (it then answered itself wrongly that `import importlib.util` was there):
  the file's line 10 is `import importlib.util`; the excerpt for cycle 2 starts there.

## Refuted (with the evidence)
- muse P2 "add a circuit breaker for the local back-end's consecutive failures (a sustained GPU1 outage costs 60 s a
  request)": every back-end has one already: Router.__init__ `self.health = {bid: Health(...) for bid in
  self.backends}` (providers.py:817), every failed call records it (`h.record(False, r.latency_s, r.kind)`, 1019),
  available() asks it (868); providers.json health: 5 consecutive failures open it for 300 s, then one half-open
  probe. A busy card costs at most 5 x 60 s, then one 60 s probe every 5 minutes.
- muse P3 "add timeout_s's rationale to the providers.json note": it is there ("timeout_s: the request (the model's
  load and the reply)").
- qwen "a race on _free_at if two threads entered": they cannot (the semaphore above; muse Step 6 verified "no race").
  A config raising max_inflight would still be serialised by the client's per-GPU in-process lock
  (gpu0.ollama_call, _call_locks), the yield then only approximate.

## Recorded
- muse P2 "a BaseException raised while the client file is imported (SystemExit) escapes complete()'s `except
  Exception`": muse itself: "Theoretical gap, not production-reaching". The real client imports only importlib.util, os
  and sys and defines a class and two functions: nothing at import raises. An interrupt (KeyboardInterrupt, SystemExit)
  is a process stop and propagates as from every back-end; the service then puts the video back ("mining stopped:
  ...", service.py:333). The tests' stand-in file raises SystemExit on purpose: a test that ever loaded it fails loudly.
- muse P2 "report the GPU wait apart from the reply's latency": the client returns the reply's content only; gpu0's
  events (the swap's waited_s, foreign_wait) are in the watcher's process (pp_gpu0.events()) and could be read after
  each request. Observability for a later change; the busy detail already names the holder or the foreign user.
- muse P3 "an adaptive yield (look at the lease file before sleeping)": looking is itself a flock probe that could make
  a zero-wait acquirer fail in that instant; 3 s after a request of 30-120 s is negligible.
- muse P3 "log the context size the model ran with" and qwen "num_ctx not validated": the client returns no metadata;
  16384 is the pipeline LocalLLM's setting at which gpu0.REQUIREMENT_MIB was measured, 6x the longest mine prompt.
- qwen "no log line when the client is loaded": the startup line names the local back-end as callable; a load
  failure is the attempt's own "disabled: the GPU lease client cannot be used: ..." record.

Suite: tests/ingest 439 passed. Mutations M51-M64: 14 of 14 killed; control passed.
