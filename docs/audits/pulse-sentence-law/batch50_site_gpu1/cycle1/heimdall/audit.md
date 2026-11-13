# Heimdall audit

**Question:** Batch 50 = GPU1 ORDER '22:50' ITEM 3: the website's Ollama fallback moves off GPU0. Law L-r: EVERY GPU HAS ONE OWNER AT A TIME; GPU0 = the renders, GPU1 = everything else, each under its lease.
Before: core/services/ai_service.generate_content_ollama posted to OLLAMA_URL, default http://localhost:11434 (GPU0's Ollama), with no lease. The live site sets no OLLAMA_URL. On 2026-11-12 11:47 a fallback load of deepseek-coder-v2:16b (18 GB, kept 5 min) held a render at prepare.
After: the same model, the same options (temperature 0.7, num_predict 2500), the same timeout of 180 s, through services/gpu_lease_client.chat_gpu1. That is pipeline/gpu0.ollama_call(1, ...), already audited in batch 45:
- the GPU1 lease, with a wait of up to 300 s;
- a foreign GPU1 user waited out within that bound;
- the free-memory proof;
- keep_alive 0, and the unload confirmed before the lease is released.

The client file is loaded by its ABSOLUTE path under the private module name pp_gpu_lease_client, because the site's own 'services' package is core/services. Empty content raises ValueError. Every failure, Gpu1Unavailable included, is logged and re-raised, so the article chain moves to its next provider exactly as before.
Verified live 00:57 ET:
- the call waited for the stage broadcast's lease, then held the GPU1 lease as "website article fallback (core ai_service)";
- deepseek loaded on GPU1 (19.7 GB), answered in 14.4 s total (828 chars), and unloaded: GPU1 back at 503 MiB, nothing resident;
- GPU0's process list was identical before and after (only the render), and GPU0's Ollama stayed empty.
FIND:
- any way the fallback still reaches GPU0;
- a failure that no longer raises (so the chain stops, or an empty article is stored);
- a module-name collision or a sys.path change in the site process;
- the 300 s lease wait blocking something it must not (the call runs inside the waitress process);
- a lease or model left behind after an exception.
Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0008
## Consensus findings (majority of panel agrees)
- **[low] core/services/ai_service.py:0** chat_gpu1's 300 s lease wait plus 180 s timeout can exceed waitress's default connection-queue/timeout expectations, but the diff shows the call is inside the existing try/except that re-raises, so the chain still proceeds; no defect proven in the given code.
  - evidence: `content = _gpu1_client().chat_gpu1(model, messages, owner="website article fallback (core ai_service)", ... wait_s=300, timeout=180)`
  - fix: None required; optionally document the worst-case ~480 s stall for the waitress worker.
  - raised by glm:F1; agree: qwen27b, glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- glm: [low] Module-level _GPU1_CLIENT path is computed at import time from __file__; if the checkout is relocated or the file is edited while the waitress process is warm, the cached pp_gpu_lease_client module (kept in sys.modules forever) serves stale code until restart.
- glm: [low] If importlib.util.spec_from_file_location returns None (file missing at the computed path), the next line module_from_spec(spec) raises AttributeError, not a clear 'client not found' error; it is still caught by the outer except and re-raised, so the chain proceeds, but the log message ('Ollama API error: ...') obscures the real cause.
- glm: [low] The success log line 'Ollama (GPU1, %s) answered under the GPU1 lease' fires only when content is non-empty; an empty-but-200 response logs only the generic error, making it harder to distinguish 'model returned empty' from 'lease/HTTP failure' when triaging the article chain.
