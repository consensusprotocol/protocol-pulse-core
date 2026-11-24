# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), the build driver's RULING 107 (1) guard (tests/package/proof_ledger.py, uncommitted). THE GUARD: a build whose inputs fingerprint the same as an earlier FINISHED build that left NOTHING undone (open_work(...) == 0) is skipped as "NOTHING NEW" (no model asked, $0). THE FINDING (the independent verifier, Nov 23): its offline drill measured no word check at all (every download blocked), recorded "0 items left undone", and the identical re-run was refused as NOTHING NEW; a real build whose downloads failed would have its next identical build skipped the same way. THE CHANGE: open_work now also counts, in the clean pass's prescreen record AND in the never-empty pass's (res["never_empty"]["soft_record"]["prescreen"]), every moment whose "second_pass" (L-v 2), "hook_onset" (G17a) or "trim_cut" entry starts "NOT MEASURED" (the exact prefix package._build writes for a check that could not run; a measured failure reads "L-v 2 FAIL" / "FAIL: ..." / "not cuttable ..."), each (check, moment) once.
CHECK, quoting the code: can a build with an unmeasured check still be followed by a NOTHING NEW skip; can a measured failure or a pass now count as undone (so the guard never skips, or a skip loops); can a missing or malformed record raise here. Report only what the code shows.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0293
## Consensus findings (majority of panel agrees)
- **[medium] tests/package/proof_ledger.py:191** The new unmeasured scan can raise on a malformed record: it calls .items() on the value retrieved for second_pass/hook_onset/trim_cut after only an `or {}` fallback, so a non-empty non-dict value (or a non-dict prescreen object) causes AttributeError instead of being treated as undone or skipped.
  - evidence: `for mid, v in ((p or {}).get(k) or {}).items() if str(v).startswith("NOT MEASURED")`
  - fix: Guard with isinstance before calling .get/.items, e.g. `p = p if isinstance(p, dict) else {}` and `container = p.get(k); if not isinstance(container, dict): continue`.
  - raised by qwen27b:F1; agree: qwen27b, gemma
- **[critical] tests/package/proof_ledger.py:190** Undefined variable 'pre' used in set comprehension
  - evidence: `unmeasured = {(k, mid) for p in (pre, soft_pre) for k in ("second_pass", "hook_onset", "trim_cut")   # the verifier,
                  for mid, v in ((p or {}).get(k) or {}).items() if str(v).startswi`
  - fix: Define 'pre' before use or remove it from the tuple, e.g., use (soft_pre,) instead of (pre, soft_pre).
  - raised by gptoss:F1; agree: qwen27b, gemma
- **[critical] tests/package/proof_ledger.py:190** Undefined variable 'pre' used in set comprehension will cause a NameError.
  - evidence: `unmeasured = {(k, mid) for p in (pre, soft_pre) for k in ("second_pass", "hook_onset", "trim_cut")`
  - fix: Define 'pre' before its use in the set comprehension, likely as the primary prescreen record from the result object: pre = (res or {}).get("prescreen") or {}
  - raised by gemma:F1; agree: qwen27b, gemma

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- qwen27b: [medium] The new `soft_pre` extraction can also raise AttributeError on malformed records: `or {}` only replaces falsy values, so a truthy non-dict `res`, `never_empty`, or `soft_record` will fail on `.get`.
- gemma: [critical] Undefined variable 'h' used in open_work
