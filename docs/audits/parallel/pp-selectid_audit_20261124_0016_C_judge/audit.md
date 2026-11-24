# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), RULINGS 154 (1) and 152 (2), uncommitted (diff below). THE RULINGS: "'every back-end unavailable ... same vendor' must never be an outcome. Judge order: a Heimdall family that did not write, then any Heimdall family, then the paid model, with ONE flag" and "L-x soft: a Heimdall panel with a flag". THE CODE: providers.Router.call (line 1386) wraps the old loop, now Router._call (line 1406, its body unchanged but for the optional `_names` list); ONLY when router.lx_soft is True (package.build sets it for the never-empty pass alone, line 4848), the call carried a writer to avoid (avoid_vendor or avoid_family), and the role is not in LX_SOFT_NEVER (line 696: the writer, a probe, a panel seat), a call whose own chain gave no answer tries Router._lx_steps (line 1371) in order and marks the reply (Reply.lx_soft). Router._skip (line 1349, unchanged) still refuses a back-end that is down. vo_fidelity / context_integrity / package copy the mark into their verdict records; package.stand_in_checks (line 4894) names those checks in ONE soft "judge" row (package_pin SOFT_GATES, line 37; gate_problems, line 460, refuses a FLAGGED row on any gate outside SOFT_GATES). package.coherence_by_panel (line 2253): in the never-empty pass, when the writers left the panel under min_members, the next Heimdall families of the writer chain (glm out, ruling 119; never the writers' family) sit, each asked BY NAME through its own one-model list, only until enough members answered; a reply from another model is no vote.
CHECK, quoting the code: can a stand-in judge answer in the CLEAN pass, for a writer's call, a probe or a panel seat; can the order differ from the ruling's (1) not-the-writer Heimdall, (2) any Heimdall, (3) paid; can a stand-in verdict reach the pin WITHOUT the one flag (a record that drops the mark); can a panel vote be counted for the wrong member, or the writers' family sit; can lx_soft leak past the never-empty pass (an exception inside _build); can the ReplayMiss / ProviderError handling swallow a SpendLimit or another error it must raise. Report only what the code shows.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0517
## Consensus findings (majority of panel agrees)
- **[high] pipeline/package.py:4848** build() enables lx_soft for the pass without checking never_empty, so a clean pass through build() can activate stand-in judges.
  - evidence: `def build(*args, never_empty=False, flagged_today=0, **kw): | lx_mark(True)`
  - fix: Gate the mark on the never-empty pass, e.g. if never_empty: lx_mark(True), or ensure build() is only invoked for the never-empty pass.
  - raised by qwen27b:F1; agree: qwen27b, gemma
- **[high] pipeline/package.py:2253** coherence_by_panel() catches P.SpendLimit and records it as a miss, so a spend-limit error is swallowed and the loop can continue to further calls.
  - evidence: `except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:`
  - fix: Re-raise P.SpendLimit (or handle it outside the per-seat loop) instead of appending it to misses.
  - raised by qwen27b:F2; agree: qwen27b, gemma
- **[medium] pipeline/package.py:2253** The one-model list for an extra panel seat is registered under a family key, not a backend-name key; if two extra seats share a Heimdall family, the second seat's list is not set to its name and the r.backend != n check will reject the answer, so the seat is not asked by name.
  - evidence: `router.chains.setdefault(f"coherence_panel:seat_{fams[n]}", [n])`
  - fix: Key the one-model list by backend name (e.g. f"coherence_panel:seat_{n}") or pass _names=[n] to the call.
  - raised by qwen27b:F3; agree: qwen27b, gemma

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- qwen27b: [high] If every stand-in step fails, `Router.call` re-raises the original error, so the forbidden 'every back-end unavailable ... same vendor' outcome can still occur.
- qwen27b: [high] The one-model list is stored on `router.chains` with `setdefault` and a family-keyed name, so a stale list from an earlier panel can make a later seat ask a different backend.
