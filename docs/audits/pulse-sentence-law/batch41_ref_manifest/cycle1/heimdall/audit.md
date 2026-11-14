# Heimdall audit

**Question:** Batch 41 = PROTECTED REFERENCE (orchestrator order 2026-11-12 '20:30' (c)): the review video PBX was very pleased with is copied read-only to references/pulse_moments_2026-11-12/ with SHA256SUMS ('<sha256>  ./<relative path>' per file; the manifest does not list itself). New pipeline/check_reference_manifest.py check(ref) returns (exit code, problems, files listed): 0 = every listed file present with its listed sha256 and no unlisted file; 1 = a changed, missing or added file, an unreadable manifest line, or an empty manifest; 2 = no manifest (the reference is not on this machine: SKIP). pipeline/regression.sh step 7 runs it and fails the regression on any exit other than 0 or 2.
FIND: any way a changed, removed or added file in the reference passes; a manifest problem that does not fail; a path-normalisation hole (e.g. './a' vs 'a', a subdirectory); the shell step not failing when it should; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0086
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
