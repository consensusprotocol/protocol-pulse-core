# qwen3.8-27b (qwen/qwen3.8-27b) 730 s finish=length usage in 11659 / out 24000 usd_reported=0.020082 usd~0.395 (upper-bound price)



# Code Audit — pp-selectid / RULING 130 (4) Coherence Panel Wiring

## Scope Reviewed

`pipeline/model_providers.json` (2 new Heimdall back-ends + `coherence_panel` role), `pipeline/package.py` (`coherence_panel_spec`, `coherence_by_panel`, modified `coherence`/`parse`), `tests/package/test_medley.py` (`TestRuling130CoherencePanel`, 7 tests).

I checked the five requested areas plus every governing law that touches this code path.

---

## Findings

### [P2] Staging `base_url` in production model config

Both new back-ends point at `https://api-staging.heimdallm.com/api/v1`. The replay (panel118/TABLE.md) was measured against this endpoint, so the wiring is correct *