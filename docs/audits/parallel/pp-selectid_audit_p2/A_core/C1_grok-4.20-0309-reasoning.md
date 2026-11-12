# grok-4.20-0309-reasoning (xAI, medley key) 55 s usage=64964

**Q1: 72/100**  
No package reaches `build()`'s final `out["package"]` (or the pinned artefact) while a hard gate is failed, unreadable, or produced an "uncertain"/exception outcome. `integrity()` requires `fid["ok"] and not dup and ctx_["ok"] and rt_ok`; `check_contexts`, `check_verdict`, `coherence` and the transcript-truth pass all turn any exception, `ReplayMiss`, missing field, or "uncertain" into a violation and `ok=False` (see `context_integrity:257-259`, `vo_fidelity:2856-2858`, `moments_gate_adapter:970-971/988-989/1000-1001`, `package:1617-1618/1630-1636/1642-1645/1670-1676`). Plain-VO fallback only ships after its own `g3["ok"]` (lines 1638-1649). The only theoretical hole is an uncaught Python exception escaping the outer `try` in `build()` (none visible in diff).

**Q2: 88/100**  
Verdict roles (`fidelity_verdict`, `context_verdict`, `viewer_takeaway`, `coherence_verdict`) never run on the writer's vendor: `prescreen`/`integrity`/`coherence` pass `writer_vendor=_writer_vendor()` (first backend in the `angle_write` chain, lines 1702-1706) and `Router.call(..., avoid_vendor=writer_vendor)` skips any matching vendor (providers:2167-2169). Chains live only in `model_providers.json`; no role hard-codes a vendor/model. Failover cannot silently accept a contract violation—`check_written`, `check_moments`, `_strict`, `check_angles`, `check_verdict` raise `ValueError`/`Rejected` treated as failure (lines 801, 1287, 1583, 1605, 2856). ProviderError on a completely unavailable verdict chain becomes a gate violation, never a pass.

**Q3: 93/100**  
Clips are source sentences verbatim (`moments.record:776 "text": sp.text`, `package.assemble:1247 "text": m["text"]`, `package_pin:1739 "approved_text": s["text"]`; `candidate_rows` only punctuated sentence-ready spans). Miner `reason`, angle sentences, verdict claims, trend brief never enter clip/VO/title/caption—writer output is fed to `vo_fidelity.check` + `context_integrity.check_contexts` before any package is kept (`build:1608-1610/1678`). Model text only appears in forensic fields (`mined`, `checks`, `models`).

**Q4: 55/100**  
- **False PASS (misleading line accepted):** `vo_fidelity.names_of` + `_title_case` returns `[]` for any Title-Case line (>=3 long words, >70 % capitalised). Concrete input: title `"MicroStrategy Buys Another 5000 BTC"` when no clip contains "MicroStrategy" and the manifest does not list it—deterministic NAME rule is skipped, ATTRIBUTION never triggers (no verb match), PRICE_NOW passes if level is inside tolerance of a current_level. Blind verdict must catch it; if the model omits the claim it ships.  
- **False REJECT (honest line blocked):** `check_deterministic:2751-2754` flags RELATION on any "both agree" phrasing even when both cited segments are from the *same* video (one conversation) and the blind verdict would accept. Concrete: bridge `"Both agree the ETF outflow is accelerating"` citing two segments from the identical YouTube video—violates even though law L-s only forbids cross-video false relation.  
- `price_now` tolerance=0.05 can false-pass a stale rounded figure (e.g. line says 74000 when universe's fresh level is 74210). `duplicates` 60 % share test on a short 8-word clip can false-reject a legitimate bridge that re-uses the hook's opening canonical tokens.

**Q5: 45/100**  
`moments_gate_adapter` correctly maps to the live gates, returns `"fail"`/`"exclude"` on `ReplayMiss` or malformed case (lines 970, 988, 1000), so adversarial tests fail closed. No vacuous assertions visible. R7 wiring (`package_pin.to_pin`) produces a `protocol_pulse.pinned_story.v1` that hard-codes `"vo_fidelity_ok": True, "context_integrity_ok": True` (lines 1758-1759) regardless of the incoming `pk["checks"]`; the downstream factory therefore cannot refuse an ungated package. Plain-pin path is unchanged but the new moments path can emit a lying PIN. (pinned.py patch itself not in diff, so certainty limited.)

**FINDINGS**

**P1: pipeline/package_pin.py:1758**  
```python
"checks": {"vo_fidelity_ok": True, "context_integrity_ok": True, ...
```
A package with `integrity["vo_fidelity"]["violations"]` or `context["violations"]` non-empty can still be pinned with `ok=True`. Concrete failing input: feed `build()` a package that failed `VERDICT_NO` on the caption and call `to_pin(pk, "test-run")`—the resulting MOMENTS_PIN.json claims both gates passed. Violates L-j ("exactly the bytes the gates measured") and L-m (fail-closed).

**P2: pipeline/vo_fidelity.py:2644 (`_title_case`) + 2654**  
```python
if _title_case(text): return []
...
if _title_case(text):
    return []
```
Title-case suppression defeats the NAME rule for any headline that introduces a speaker not present in the cited clips. Concrete: title `"Michael Saylor Warns of Incoming Crash"` when no moment contains "Saylor" and manifest does not list him—deterministic layer silent; only blind verdict can catch it. Measured false-reject avoidance created a false-pass vector.

**Highest-leverage change (single diff hunk):**  
Replace the hard-coded `True` values in `package_pin.to_pin` (lines 1758-1759) with actual values pulled from `pk.get("checks", {})["integrity"]` (or reject if missing). This makes the PIN truthfully reflect the gate bytes that were measured, closes the L-j authorisation bypass, and requires zero changes to any gate or test. All other issues are secondary to "the bytes that are sent must be exactly the bytes the gates passed on". 

**Summary:** The design is tight, fail-closed where it matters, and complies with L-x / L-s / L-l / L-k on the evidence present in the diff. The two concrete P1/P2 findings above are the only clear violations reachable from the shown code.