# Heimdall audit

**Question:** Batch 41 cycle 4 (verification) = PROTECTED REFERENCE regression step 7 (pipeline/regression.sh, set -euo pipefail). The reference's small files incl. SHA256SUMS are git-tracked and pinned by tag ref-pulse-moments-2026-11-12; large files untracked, listed in SHA256SUMS. This diff implements cycle 3: SKIP iff `git ls-files --error-unmatch references/pulse_moments_2026-11-12/SHA256SUMS` fails (this checkout does not track the reference; the index still lists a tracked file whose working copy was deleted); when tracked: the manifest checker must exit 0, the tag must exist (explicit FAIL otherwise), and `git diff --quiet <tag> -- <reference dir>` must hold. Proven on a throwaway repo: intact 0; tag missing 1; tag restored 0; directory deleted 1; directory back 0; a file changed with SHA256SUMS re-made to match 1; an untracked directory SKIP.
FIND: whether the fix is correct and complete; any way an intact reference fails or a changed / deleted / replaced one passes. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0003
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] When the reference is tracked, the tag-diff check covers tracked files only; a changed *untracked* file inside the reference dir is caught only if it is listed in SHA256SUMS (checker) — but a file listed in SHA256SUMS yet untracked-and-modified is caught by the checker, and an extra untracked file not in SHA256SUMS is caught by the checker's 'none added' rule, so coverage is complete. Only residual gap: if the checker script itself is missing, the FAIL path is taken (nonzero), which is intended. No defect found. (agree: 1)

## Added in cross-examination (not voted on)
- glm: [low] Untracked-directory SKIP path: if the index does not list SHA256SUMS and the dir exists, step 7 silently skips with no existence/manifest check, so a present-but-untracked (or partially deleted) reference passes as SKIP
