# Heimdall audit

**Question:** Batch 82 = a defect in the integrator's readiness tool, scripts/integrator/check_pin_only.py, found on the first spotlight pin (3f481f5a, 2026-11-14): it called the builder's package_pin.gate_problems with its medley default and reported "r4: missing; coherence: missing" for any spotlight (a spotlight's sealed inventory has no r4 / coherence rows by contract), and recomputed the seal by hand. The fix: gate_problems(gates, PP.required_gates(mp)) (the builder's shape-aware required set) and PP.pin_seal(pin) (the builder's documented readiness call, covering every shape and the fields it seals later). Measured on real pins: the spotlight 3f481f5a is READY; the medley 13949b7c (takeaway with no takeaway_value row) is still refused, now by the builder's required set; a resealed copy with the row is READY with the same seal the old hand call gave.
FIND: a pin the fixed tool now passes that the render would refuse, or that the old tool rightly refused; a seal it could accept from bytes other than the pin's. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0004
## Consensus findings (majority of panel agrees)
- **[low] scripts/integrator/check_pin_only.py:24** gate_problems is now called with the pin's own shape-aware required set, so a pin whose gates dict lacks gates the builder requires only via required_gates(mp) would pass the gates check here even if the builder's readiness call would refuse it — but the subsequent PP.pin_seal(pin) comparison against package_sha256 still catches any such divergence, since the seal covers the gates. No defect observed in the diff; the seal check subsumes the gates check for readiness.
  - evidence: `problems = PP.gate_problems(mp.get("gates"), PP.required_gates(mp))   # the pin's own shape: a spotlight has no
    if problems:                                                          # r4 / coheren`
  - fix: None required; the pin_seal comparison already enforces readiness against the builder's own seal, so the gates check is advisory only.
  - raised by glm:F1; agree: qwen27b, glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
