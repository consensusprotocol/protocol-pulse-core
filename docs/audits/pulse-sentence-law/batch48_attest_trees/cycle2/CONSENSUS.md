# Batch 48 cycle 2: consensus and what was done

Implemented: the consensus [low]. The launch half had no test. It is now run_fresh.launch_code(repo), the one function stage_env calls once (one snapshot): the clean check over EXEC_PATHS, the untracked pipeline/*.py check, HEAD, and exec_trees(HEAD). Tests:
- test_launch_records_the_trees_of_a_clean_checkout;
- test_launch_refuses_any_dirty_executable_path_and_accepts_dirty_docs: scripts/, segment_v1/, relay.py and the registry dirty each refuse; an untracked pipeline module refuses; a dirty doc does not.

Not implemented (single votes): a change made AND reverted between launch and end attests. The ruling binds launch and end, and every module the run imported is hashed at the end (executed_code_sha256), so a changed module that is still loaded is caught. skip-worktree / assume-unchanged files are not used in this repository.
