# Heimdall audit

**Question:** Batch 41 cycle 2 = PROTECTED REFERENCE (orchestrator order 2026-11-12 '20:30' (c)): pipeline/regression.sh step 7 checks references/pulse_moments_2026-11-12 with pipeline/check_reference_manifest.py (exit 0 = every file listed in SHA256SUMS present with its sha256 and nothing unlisted; 1 = changed / missing / added / bad manifest). Cycle 1 finding (deepseek F1): a MISSING checker made python3 exit 2, which the step read as SKIP. Fixed here: the shell decides SKIP only when the reference's SHA256SUMS is absent; when it is present, ANY nonzero exit of the checker fails the regression (exit 1). The script runs under set -euo pipefail.
FIND: any remaining way the regression passes while the reference is changed, removed, or the checker cannot run; a shell error that is silently ignored. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** glm, deepseek  |  **Cost:** $0.0060
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] SKIP decision uses -f on SHA256SUMS only; a directory with SHA256SUMS but missing/renamed checker still yields nonzero exit, which now correctly fails, so no silent pass. However, if the reference directory exists but SHA256SUMS itself is unreadable (permissions), -f is true and the checker's nonzero exit fails — correct. No remaining silent-pass path found: nonzero checker exit (including 2, missing checker, permission errors) now fails the step because the if ! construct catches any nonzero status under set -e. (agree: 1)

## Added in cross-examination (not voted on)
- deepseek: [high] If the entire reference directory is removed, SHA256SUMS is absent, so the step prints SKIP and the regression passes even though the protected reference is gone.
- deepseek: [high] The checker uses SHA256SUMS as the source of truth; if an attacker modifies a file and updates SHA256SUMS, the checker exits 0 and the regression passes, so the reference is changed but not detected.
- deepseek: [medium] `-f` only checks for a regular file; if SHA256SUMS is a directory or broken symlink, the condition is false and the step skips, allowing a changed/removed reference to pass.
