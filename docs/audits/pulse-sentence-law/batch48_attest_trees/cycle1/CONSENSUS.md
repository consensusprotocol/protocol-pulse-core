# Batch 48 cycle 1: consensus and what was done

The run's cross-examination call to glm hung for 12+ minutes, so it was stopped. The verdicts below are read from
heimdall/raw_c1_qwen27b.json, raw_c1_glm.json and raw_c2_qwen27b.json.

Implemented:
- glm F1 [medium], git failures folded silently: exec_trees records a path git cannot resolve as
  'UNREADABLE: <git's message>', never as an id, and the output must be 40 hex characters. Either end UNREADABLE is a
  reason ("executable tree not readable"). A failing `git diff` is its own reason ("git diff against the launch
  revision failed"), never confused with "no changes". Test: test_an_unknown_launch_revision_fails_closed.
- glm F3 [low]: test_a_docs_commit_then_an_uncommitted_registry_edit_names_only_the_edit. A docs commit plus an
  uncommitted registry edit gives exactly the 'differ' reason and no tree reason.

Not implemented, with the measured reason:
- qwen F1 [high] / glm F2 [medium], qwen agreeing in c2: extend the launch untracked check to every EXEC_PATH. Today
  `git ls-files --others --exclude-standard -- segment_v1 scripts` lists 1724 untracked files, including historical
  .py renders (segment_v1/render_v5.py ... render_v13_vertical.py, audit/, repro/). stage_env's own comment records
  that segment_v1 keeps historical untracked scratch. Refusing them at launch would refuse every run. What protects
  the run is unchanged and now tested:
  - the end-of-run per-module check refuses any untracked module a run IMPORTS
    (test_an_untracked_module_the_run_imports_is_refused: segment_v1/scratch_v9.py (untracked));
  - the untracked data a run READS (the brand/ outros, the music, segment_v1's face model) is hashed per run in
    runtime_assets_sha256.
- qwen F2 [medium, qwen itself disagreeing in c2], staged changes: `git diff <commit>` compares the working tree,
  staged changes included, with the commit.
