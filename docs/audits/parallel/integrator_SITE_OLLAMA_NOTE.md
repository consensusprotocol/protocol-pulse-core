# Integrator note for the orchestrator: the website's article job falls back to a local model on GPU0

Written 2026-11-12 by the integrator (pipeline_pp_dod), order '20:30' (d), "site Ollama fallback note". Nothing on the
site was changed: the site, its cron and its config belong to another session (order '11:57': "Do not change cron or
other sessions yourself"; "Never kill what is not ours").

## What happens (measured)
- `core/services/article_automation.py` provider chain (line ~639): HeimdaLLM -> Ollama (free) -> Gemini -> Anthropic ->
  OpenAI. When Heimdall answers empty, the article is written by `core/services/ai_service.py:187`
  `generate_content_ollama(model="deepseek-coder-v2:16b")` at `OLLAMA_URL` (default `http://localhost:11434`): Ultron's
  Ollama, which loads the model on GPU0 (18128 MiB) and keeps it 5 minutes after the last call.
- 2026-11-12 11:47 ET: that load held run pinned_20261112_164704 at prepare (law L-r: a GPU0 user that is not the
  run's). The production site process was waitress app:app on port 5000; logs/waitress.log: 'HeimdaLLM call:
  model=deepseek/deepseek-v4.1-flash latency=83.92s' -> 'failed: Empty response from Heimdall' -> 'Article generated via
  Ollama'. The current logs/waitress.log holds 110 'Article generated via Ollama' lines.
- Since 11:57 the pipeline waits a foreign GPU0 user out (15 s polls, up to 10 minutes) before it holds (L-r item 4
  amended, 097e1802), so a single article no longer stops a render. Steady fallback traffic (a new call inside every
  5-minute keep-alive) would still hold one: the model never leaves GPU0.
- Mid-afternoon a second foreign model (gemma3:27b, 19 GB) appeared on GPU0 during the integrator's test session, and
  the wait-out handled it; its owner was not identified.

## Options (the site owner's call; none is taken)
1. The site's fallback skips Ultron's Ollama while the pipeline holds GPU0: the pipeline's lease is an exclusive flock
   on `/tmp/pulse_gpu0.lease` (pipeline/gpu0.py, `lease_path()`); a non-blocking probe tells whether a run owns GPU0,
   and the chain then goes on to its next provider. No pipeline change.
2. The site's fallback uses a model that is not on Ultron's GPU0: the CMP box serves Qwen3.8-27B through llama-server
   on :8002 (an OpenAI-style API, so not a drop-in for the Ollama call: a small client change on the site).
3. `OLLAMA_URL` (already read by the site) points the fallback at an Ollama that is not on GPU0. Which GPU or host is
   the owner's decision (GPU1 is quarantined for the pipeline and serves other protected work).

Recommended: option 1, because it needs no new host and costs the site nothing while no render is running.
