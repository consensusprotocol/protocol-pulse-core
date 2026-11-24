# Heimdall audit

**Question:** TASK: audit batch 120 of the Protocol Pulse video pipeline (Python), landed under ruling 153 ("audit already done where done"); this is its follow-up audit. You are reviewing a diff of pipeline/gpu0.py (the GPU lease and model-swap guard, law L-r: every GPU has one owner at a time; a foreign GPU user is waited out up to 600 s, then Gpu0Foreign stops the caller) and the note line in telegram.py. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

THE RULING (145, restated by the orchestrator 18:18 ET Nov 23): "a foreign program under 2 GiB and under 10 percent use is tolerated and logged", "so a stray program never kills the word pass again".

WHAT THE DIFF DOES: small_tenants(f, need_mib) tolerates the foreign users f only when EVERY one is a process with a pid and reported memory under SMALL_TENANT_MAX_MIB (2048), none is an Ollama model (its pid in _ollama_pids(): another client's model is waited out as before), the GPU keeps the caller's measured need (REQUIREMENT_MIB[key], 0 for release_all) plus SMALL_TENANT_HEADROOM_MIB (4096) free of everything that is not this run's, and the GPU's utilisation is under 10 percent. Tolerated: one "small_tenant" event in the lease events (copied to the run's PROVENANCE) and a printed line; telegram.tenant_lines puts one plain line in the release caption. Otherwise the old path runs unchanged (the 600 s wait, then Gpu0Foreign). foreign() still lists unaccounted memory as (None, ..., MiB), which small_tenants refuses (pid None).

CHECK, AND ANSWER EACH:
Q1. Can a tenant over 2 GiB, a busy GPU (>= 10 percent), an Ollama model of another client, or unaccounted GPU memory ever be tolerated?
Q2. Can the tolerance let this run's own load fail for lack of memory (the free-memory arithmetic: total - used + this run's own memory)?
Q3. Does utilisation() fail safe (an unreadable nvidia-smi line raises Gpu0Unreadable, a Gpu0Stop) and is that acceptable inside _refuse_foreign?
Q4. Any other defect.

OUTPUT: for each finding, severity (critical|high|medium|low), file:line, the concrete failure (inputs -> wrong result), and the fix. If none, say NONE for that question.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** gptoss  |  **Cost:** $0.0012
## Consensus findings (majority of panel agrees)
- **[high] pipeline/gpu0.py:410** `utilisation()` raises `Gpu0Unreadable` instead of the expected `Gpu0Stop`, causing `_refuse_foreign` to propagate an unexpected exception when `nvidia-smi` output is unreadable.
  - evidence: `    try:
        return int(out.strip())
    except ValueError:
        raise Gpu0Unreadable(f"nvidia-smi utilisation line unreadable: {out.strip()[:80]!r}") from None`
  - fix: Change the exception to raise `Gpu0Stop` (or make `Gpu0Unreadable` a subclass of `Gpu0Stop`) or catch `Gpu0Unreadable` inside `_refuse_foreign` and convert it to a `Gpu0Stop`.
  - raised by gptoss:F1; agree: gptoss
- **[medium] pipeline/gpu0.py:432** The free‑memory calculation may underestimate available memory if `processes()` returns `None` for the memory of this run’s processes, leading to a false refusal of a small tenant.
  - evidence: `    mine = sum(m for pid, _, m in processes() if pid in ours and m)`
  - fix: Treat `None` memory values as `0` or handle them explicitly when summing `mine` (e.g., `sum(m or 0 for pid, _, m in processes() if pid in ours)`).
  - raised by gptoss:F2; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
