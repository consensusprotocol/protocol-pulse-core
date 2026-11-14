# Heimdall audit

**Question:** Batch 48 cycle 2 (verification). Cycle-1 consensus implemented, see CONSENSUS.md: exec_trees fails closed (UNREADABLE marker, 40-hex check); a failing git diff is its own reason; tests for docs-commit + uncommitted registry edit, an unknown launch revision, and an untracked IMPORTED module (refused at the end). NOT implemented, with the measured reason: extending the launch untracked check to segment_v1/scripts (1724 historical untracked files there; imported untracked modules are refused at the end; untracked data read is hashed in runtime_assets_sha256).

Batch 48 = RULING 27 (orchestrator 2026-11-12 '23:20'). The ruling, verbatim in substance: "the attestation records and verifies the git TREE hash of executable paths (pipeline/, segment_v1/, scripts/, the registry and config data the run reads - enumerate from what run_fresh imports/reads) at launch and end. docs/ and *.md outside those are excluded. Must-fail: touching pipeline/ mid-run is refused; committing docs mid-run is accepted."
Enumeration, measured on the Nov 12 medley run's PROVENANCE:
- executed modules: 34 under pipeline/, 2 under segment_v1/, 1 = video_pipeline_v3/relay.py;
- tracked data read: pipeline/channels.json (the registry), segment_v1's brand mark and face model;
- launcher: scripts/pulse_check_run.sh;
- untracked runtime assets (the brand/ outros, the music mp3s): in no tree; runtime_assets_sha256 already hashes them per run;
- vertical/ layout tables: not read by runs (validate_edl is called without layout_tables_dir).

Hence EXEC_PATHS = (pipeline, segment_v1, scripts, video_pipeline_v3/relay.py). The change:
- stage_env requires all of them clean at launch (porcelain, untracked excluded, as before for pipeline / segment_v1) and records exec_trees(HEAD) = {path: git rev-parse <rev>:<path>}.
- executed_code(launch) no longer gives "HEAD moved" as a reason. Instead:
  - a tree id at HEAD differing from the launch commit's is a reason;
  - git diff --name-only <launch> -- EXEC_PATHS (the working tree, uncommitted edits included, vs the launch commit) non-empty or failing is a reason;
  - the per-module checks are unchanged.
- The end records git_head_at_end and exec_trees_at_end.
FIND: anything still open from cycle 1; a new way a change to executed code or read data mid-run still attests; a docs-only commit still refused; a git failure that passes; a test that does not test what it claims. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0019
## Consensus findings (majority of panel agrees)
- **[low] pipeline/test_attestation_trees.py:60** test_the_launch_trees_are_recorded_for_every_executable_path asserts all values are 40 chars, but exec_trees stores 'UNREADABLE: ...' strings on failure, so the test would catch that; however the test's assertTrue(len(v or '')==40) also passes for a 40-hex UNREADABLE-prefixed... no, it would fail; the weaker claim: the test never exercises stage_env at all, so the launch-side requirement (all EXEC_PATHS clean, recorded exec_trees(HEAD)) is untested — the new stage_env behavior (porcelain over EXEC_PATHS, the new prov key) has no test, despite the ruling's must-fail 'touching pipeline/ mid-run is refused' being an end-check only; a regression in stage_env's EXEC_PATHS spread (e.g. reverting to the old two-path list) would pass the whole suite.
  - evidence: `def why(self): return rf.executed_code(self.launch, modules={}, repo=self.repo)[1]  # stage_env never called in any test`
  - fix: Add a test that runs stage_env (or its porcelain+exec_trees portion) in the scratch repo with a dirty scripts/ file and asserts the Hold and the recorded exec_trees key.
  - raised by glm:F3; agree: qwen27b, glm

## Raised but not agreed
- glm:F1 [medium] A mid-run change to read data outside EXEC_PATHS still attests: segment_v1's brand mark and face model are read data per the ruling, but only the whole segment_v1 tree id is compared; the diff check covers them, yet the tracked-data read of pipeline/channels.json is only caught by the diff, and the end-of-run evidence records exec_trees_at_end but never re-runs the porcelain cleanliness check, so an uncommitted edit made and reverted before the end check passes silently — actually the diff catches it only if still present; a transient edit that is reverted attests. More importantly, exec_trees_at_end is computed at record_assets time, but executed_code's tree comparison uses the same call, so the recorded evidence and the verdict are consistent; the real gap: the launch-side stage_env porcelain check now includes scripts/ and video_pipeline_v3/relay.py, but the untracked_py check still only covers pipeline/*.py, so an untracked module under segment_v1/ or video_pipeline_v3/ that the run imports passes stage_env (the consensus said this is measured/accepted for segment_v1, but video_pipeline_v3/relay.py itself, if untracked, would pass launch and only fail at the end via ls-files). (agree: 1)
- glm:F2 [low] The 'executable tree changed' reason compares launch vs HEAD trees, but the working-tree diff against launch is a separate reason; a committed change plus a reverted-then-recommitted identical content yields no reason (correct), yet a change committed mid-run whose tree id happens to equal launch (empty commit) is correctly ignored — however the moved list filters out UNREADABLE end trees, so when the end tree is UNREADABLE but the launch tree was readable, the only reason is 'not readable', which is fine; the residual gap: git diff --name-only compares the working tree, but untracked-but-tracked-ignored edits (skip-worktree/assume-unchanged files) are invisible to both diff and porcelain, so a modified tracked module with assume-unchanged set attests clean while the executed bytes differ from the launch tree. (agree: 1)

## Added in cross-examination (not voted on)
- glm: [low] exec_trees('HEAD') in record_assets and executed_code both run at end-of-run, but the diff-vs-launch in executed_code compares the working tree, while exec_trees_at_end records the committed HEAD tree; if a mid-run committed change to EXEC_PATHS is later reverted by a second commit before record_assets, the diff is empty and t0==t1, so the mid-run code change attests with no evidence it ever differed — the ruling's 'touching pipeline/ mid-run is refused' only holds if the change survives to the end check
