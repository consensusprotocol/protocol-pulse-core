# FRESH-TOPIC GENERALIZATION (2026-11-06)

Approved by PBX 2026-11-06 07:24 ET. Purpose: test whether approved v2f production behavior reproduces on a fresh, unrelated Bitcoin topic. Reference (tag ref-v2f-2026-11-06, references/v2f_2026-11-06/) untouched; run_isolated.py unchanged (asserted by test).

## Scope (exactly the approved minimum)
- `pipeline/run_fresh.py` — new orchestrator: topic -> discover (approved-layout channels only) -> rank -> select -> validate + layout compatibility -> cut + acceptance -> VO (v2f voice/model asserted) -> run_isolated.prerender_clips -> clip contract + Law 14c edge words -> shout-out x2 -> preflight -> render16 -> postflight -> render9 -> postflight + vertical silent-fallback detection -> gates. Verdict: `CANDIDATE FOR HUMAN REVIEW WITH FLAGS` or `HOLD`. Never imports telegram.
- `pipeline/select_passages.py` — EDL times in source-file coordinates (+ provenance offset).
- `pipeline/cut_accept.py` — cut acceptance (no cut accepted merely because of an energy valley).
- `pipeline/clip_contract.py` — 1920x1080, 24/1 fps, 48 kHz stereo, durations within 1 frame, 20/30 ms fades measured.
- `pipeline/config.py` + `render16.py` + `render_vertical.py` — voice consistency over whichever VO entries exist; 9:16 requires an intro only when the EDL has one.
- `pipeline/scan.py` — previously untracked dependency of discover.py, now committed.
- `pipeline/test_fresh.py` — 27 tests incl. must-fail fixtures.

## Gate policy for this experiment (PBX)
- All production gates run exactly as in v2f (run_gates), plus G11 (real), G14 16:9, G14 9:16 (audio offset scored, frame similarity LIMITED), G14c, G15 both.
- G9: APPROVED KNOWN EXCEPTION only if outro master+conformed sha256 equal the locked outro and the failure is luma-only; otherwise FAIL.
- G8: production threshold untouched; reported with source-relative ratio; FLAG/LIMITED unless 16:9 ratio < 0.85 (pipeline degradation) -> FAIL.
- Skipped gates are SKIPPED, never PASS. Any other FAIL/HOLD -> HOLD. Vertical fallback -> 9:16 HOLD.

## Calibration evidence (v2f sources)
Cut acceptance: approved 9.52 / 636.72 / 1011.80 / in 998.00 / in 624.63 accepted; must-fail 9.13, 249.37, 997.25 rejected; 249.63 (one-time exception) rejected in fresh mode; cutter values 636.78, 1012.13, 249.67 rejected. Edge words: all four approved clips pass (incl. "$40 trillion" -> dollars); 997.25 head hears "themselves" -> fail. Contract: four v2f finals pass; unfaded head, unfaded tail, 720p, 30 fps, wrong duration fail.

## Audit legs
cross_llm_audit.py external legs: UNAVAILABLE (OpenAI account out of credits; Gemini removed for unreliable auditing). Not claimed as passed. Local verification: 27 new + 110 existing tests, pipeline/regression.sh EXIT 0, regression_test.sh 0 FAIL, v2f regression render, intro-less smoke render.

## Wrapper dry run on the approved v2f pair (scratch copy, 2026-11-06)
Under this experiment's verdict policy the approved v2f pair itself evaluates to HOLD in both formats: G3c acoustic tail FAIL (16:9 and 9:16; documented false positive on the hook in REFERENCE_v2f.md) and 9:16 G5 true peak FAIL ("approved as reviewed"). G8 -> FLAG (relative ratios 0.963-1.012, no pipeline degradation), G9 -> APPROVED KNOWN EXCEPTION (hash-identical outro, luma-only), G11/G14 audio/G14c/G15 PASS. Consequence: a fresh run that reproduces v2f exactly can still end HOLD on G3c / 9:16 G5 unless PBX extends the documented exception list. Not changed here (Law 26).
