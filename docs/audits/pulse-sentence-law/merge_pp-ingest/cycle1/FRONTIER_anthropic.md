# claude-fable-5-2 (367 s) usage={'input_tokens': 81581, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 34452, 'output_tokens_details': {'thinking_tokens': 31309}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Verdict: do not merge 753dec1d as is. Four findings are blocking, three inside your five questions and one outside them.**

References are file, function and quoted line; I did not count line offsets in a diff this size and will not invent them.

## BLOCKING

**B1 (question 2). The 90% tripwire halts the Heimdall leg instead of only notifying.**
- `pipeline/ingest/providers.py`, `Router.available`: `if st != "ok": return False, f"heimdall spend {st}"`.
- `spend.py` says the 90% state never clears: "A 90 % notice stays once written (spend does not go back down)". Heimdall mining is therefore off permanently at $414 until someone edits `cap_usd`.
- The same line also cuts Heimdall when the meter is merely `unmeasured`, meaning `/credits` failed or the reading is older than `stale_after_s` (3600).

**B2 (question 2). An outage of about 80 minutes turns into permanent, silent loss of moments.**
- `service.py`: `MINE_MAX_TRIES = 8`, `MINE_RETRY_S = 600`, and `if rep["failed"] and tries < MINE_MAX_TRIES:` waits; otherwise the video goes to `MINED_PARTIAL` with `next_at=self.clock() + 10 ** 9`.
- A window fails the same way whether back-ends errored or were only skipped (budget used, meter not ok, circuit open).
- B1 plus the silent `daily_budget_usd` caps (15 and 10) on the two remaining mine back-ends is a direct path into this state.
- `coverage.py` then counts the video as mined: `if state in (Q.MINED, Q.MINED_PARTIAL): rep["mined"] += 1`.
- The module docstring "Nothing is dropped" is false.

**B3 (question 1). The GPU0 "lease" is an environment string, and nothing in the diff imports `pipeline/gpu0.py`.**
- `ab.py`, `main`: `lease = (lambda: True) if os.environ.get("PP_INGEST_GPU0_LEASE_HELD") == "1" else None`.
- `providers.py`, `OllamaLocalBackend.complete`: `self._llm = sm.LocalLLM(model=self.model).start()`.
- The lease is checked once at call entry; a call can run 600 s past it. `_llm` is cached and never stopped.
- Blocking unless `story_semantics.LocalLLM` itself takes the lease through `gpu0.py`. That file is not shown, so this is uncertain.
- As shipped, the local back-end is disabled and `cmd_run` calls `Service()` with no lease, so the merge alone loads nothing on GPU0.

**B4 (outside the five questions). One age-gated video stalls all YouTube access.**
- `watch.py`: `RATE_LIMIT_MARKS` contains `"Sign in to confirm you"`, which is a prefix of `"Sign in to confirm your age"` in `fetch.py` `UNAVAILABLE_MARKS`.
- `YouTubeGate.run` checks stderr first and trips the global breaker, so the `unavailable` branch is unreachable for age-gates.
- The video is requeued as `PROBE_RETRY` with no terminal state and re-trips after each pause.
- `YouTubeGate.calm()` is never called in the shown code, so `trips` only grows; the fourth trip and every later one pauses 60 minutes.

## NOT BLOCKING

**Question 1 (GPU0)**
- There is no literal `127.0.0.1:11434` and no model load in the watch, fetch or mine path.
- Uncertain: whether `transcript_store.fetch_captions` or `canonical_transcript` can reach Whisper (not shown).
- No shipped entry point passes a lease to `Service`, so local-first (L-x) is unreachable in `run` without a code edit.

**Question 2 (providers)**
- Vendor names appear outside `providers.json`:
  - `providers.py`: `== "heimdall"`, `"anthropic"`, `"google"`, `"ultron-gpu0"`, the classes `AnthropicBackend`, `GeminiBackend`, `OllamaLocalBackend`, and "xAI" in the `price_cost` docstring.
  - `spend.py`: `HeimdallMeter`, `"HEIMDALL SPEND AT 90%"`.
  - `stats.py`: `heimdall_error_rate`.
  - `tools/ingest_watch.py`: `PP_INGEST_HEIMDALL_BASE` in the docstring.
  - REQUESTS R6.4: `local_gemma,heimdall_qwen27b`.
- No model id is hard-coded in the code shown.
- Back-end counts: `mine` has three enabled plus local disabled; `judge` has three and no local. `load_config` does not enforce a minimum of two.
- `daily_budget_usd` halts a back-end for the UTC day with no notification.
- A circuit can stick half-open forever. `Health.allow` sets `self.probing = True`; if `validate` raises anything other than `Invalid` (for example `RecursionError` from `json.loads`), `_try` exits without `record()`.
- Uncertain: whether the meter measures the right account. The key rotates over every `HEIMDALL_API_KEY*` name, and the cap and baseline are the probe sweep's.

**Question 3 (ledger)**
- Append-only holds in the shown code: the only writes are `O_APPEND` in `append` and `seal`, under `flock` with `fsync`. There is no rewrite, truncate or reorder.
- A crash between `ledger.append(...)` and `q.set_state(...)` in `service.py` re-mines the video and appends it again with a new `mined.at`. The adapter's "latest line wins" then re-serves old moments as mined since T.
- There is no single-instance guard. `Service.__init__` always runs `self.q.recover()`, so `once` started beside `run` resets the live process's `MINING` rows; both mine and both append.
- `seal` runs only at start. A failed write in a live process (ENOSPC, EIO) leaves a torn tail, and the next append's first line is glued to it and lost.
- `mine.mine_video` keeps the first window's flags for a repeated range (`by_range[key]["mined"]["observations"] += 1; continue`), so the second observation's risk flags are discarded.
- `append` does not run `line_problems`. A `None` title or channel_id is written, then rejected by every reader.
- `offset_before` trusts mining-time order; its "0 when in doubt" is not implemented.
- `best_unused_moments` skips the opt-out and registry exclusions at its defaults (`optout=()`, `registry=None`).
- Ids are deterministic given `w0` and `w1`: `sha256(f"{video_id}|{transcript_sha256}|{w0}|{w1}")`.
- Uncertain: whether text is verbatim. It is `E.spoken(...)` from modules not shown; the model returns ids only.
- Timing is marked by `timing` and by `duration_s` versus `duration_estimate_s`. `start` and `end` are unlabelled, and the `timing` value is not validated.

**Question 4 (secrets, prompts)**
- No key is printed, logged or put in a prompt in the shown code.
- `<store>/ingest/overrides.json` can point `"Authorization": "Bearer " + self._key()` at any URL, with no allow-list. urllib also forwards that header on redirects.
- Vendor error bodies (`body[:300]`) are persisted to `replies_log`, `calls.error`, `NOTIFY.txt` and the STATE doc. Uncertain whether any vendor echoes a key there.
- Transcript text is not escaped in `mine.prompt`, so a literal `</sentences>` closes the untrusted block. The hard-risk exclusion rests solely on that model's flags.
- `ab.py` `_fmt` puts `l['text'][:400]` into `<list_X>` and `<list_Y>`, outside the block that carries the SECURITY notice.
- `providers.py` `_try` appends `"YOUR PREVIOUS REPLY WAS REJECTED: " + why` unquoted; `why` can carry keys and values from the model's reply.

**Question 5 (writes, edits)**
- `spend.write_state_notice` rewrites the tracked `docs/audits/parallel/pp-ingest_STATE.md` by read-modify-`os.replace` with no lock. It runs on every start, including the first `ok` state.
- `contract._load_file` executes code from `/home/ultron/worktrees/pp-selectid/pipeline`. Python will write `__pycache__` there, so "read-only" is not true.
- `handoff --apply` writes into `--main` with no guard and leaves `.handoff.tmp` behind if `os.link` fails.
- Every file in the diff is `new file mode`; no existing pipeline file is edited. Tests were not shown.
- The branch depends on private APIs it does not own: `ts._ytdlp`, `_vdir`, `_write_once`, `_store`, `_log_attempt` and `LocalLLM._post`.