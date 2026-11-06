# G8 Policy Proposal — Source-Relative Sharpness (A9)

**Date:** 2026-11-06
**Status:** PENDING PBX APPROVAL

## Change Summary

G8 previously used an absolute Laplacian variance floor (60 for native content).
This misses pipeline-induced blur when the source is very sharp, and false-fails
when the source itself is naturally soft (e.g. studio lighting, cinematic grain).

## New Behaviour

Two independent checks per talking-head segment:

1. **Source usability**: Source median Laplacian >= `SHARPNESS_FLOOR` (60, or scaled
   for R1 crops). If source is soft, this is reported but the pipeline is not blamed.

2. **Pipeline degradation**: Output median >= `DEGRADATION_RATIO` (0.85) x source
   median. Catches encode quality loss, bad scaling, or accidental blur introduced
   by the pipeline.

Both checks must pass. Missing source or missing frames => FAIL (fail-closed).

## Constants

| Constant | Value | Rationale |
|---|---|---|
| `SHARPNESS_FLOOR` | 60 | Law 20, unchanged |
| `DEGRADATION_RATIO` | 0.85 | Allows ~15% loss from re-encode + scaling; stricter than 0.80 which some H.264 re-encodes hit |

## Test Coverage

- Faithful soft source: source Laplacian 50, output 48 => floor fails but degradation passes (ratio 0.96). Overall FAIL (source unusable). Correct.
- Sharp source, clean pipeline: source 200, output 180 => both pass (ratio 0.90). Correct.
- Sharp source, degraded render: source 200, output 100 => floor passes, degradation fails (ratio 0.50). Correct.
- Missing source: no source_clips entry => FAIL. Correct.
- Missing frame: extract_frame returns nothing => FAIL. Correct.

## Approval Required

The `DEGRADATION_RATIO = 0.85` threshold is new. Until PBX approves, the gate
reports FAIL for any segment where it would have previously been waived. This is
intentionally fail-closed per addendum 2 item 3.
