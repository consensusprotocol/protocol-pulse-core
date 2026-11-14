# pp-tests_batch78 — CYCLE 1 CONSENSUS (written by the session; 2026-11-14 ~08:45 ET)

Why the session writes it: the repo tool's consensus step calls claude-sonnet-4-6 and the Anthropic account is out of
credit (HTTP 400 again at 08:27 ET). Rule (pp-ingest's): a finding is consensus when >= 2 reviewers raise the same
file, function and root cause, or when one reviewer's finding is verified against the code; a refuted finding is
recorded with its evidence.

Reviewers (the same AUDIT_PACKAGE.md, 45,153 chars, built by the repo tool from the brief and the diff):
- gemini-2.5-pro (the tool's leg): 96/100, "ready for production merge", one P2.
- Heimdall qwen/qwen3.8-27b (effort none): 94/100, "ready for merge", one P2 and two P3.
- Heimdall z-ai/glm-5.3-flash (effort none): 92/100, "Ready to merge", one P1, two P2, three P3.
- gpt-4o: OpenAI HTTP 429 insufficient_quota. Grok: not run (unmetered by the session's ledger).

## Dispositions

1. Gemini P2, "consolidate the network-guard logic shared by conftest.py, moments_exam.py and the child guard".
   ACCEPTED, verified: three hand-kept lists, and this batch's finding is their drift. Implemented as ONE list,
   tests/adversarial/child_guard/netguard_names.py (INET_METHODS, LOOKUPS: names only, importing it patches
   nothing). The child guard imports it from its own directory; conftest.py and the runner load it by path. The
   runner's guard is now one wrapper per listed method and per listed lookup. New test
   test_moments_gates::test_the_runner_refuses_every_call_of_the_suites_list: in a child, after refuse_network(),
   all nine listed calls are the runner's (`_exam_no_<name>`).
2. qwen P2, "derive KEY_LOADER relatively or from an environment variable". REFUTED:
   - relay.py finds the project's key file beside itself (relay.py:44-47). The worktree's copy has none beside it:
     keys live only in the main tree.
   - A path taken from the environment would choose a file that is EXECUTED in a process holding keys.
   - The house pattern pins the same absolute path (scripts/integrator/grok_audit.py:15). The new detection test pins it too.
3. qwen P3, "an automated check for .pth socket bindings". NOT ACTED ON. It is a fact about the interpreter's
   site-packages, which differ by machine, not about this suite's code. The docstring records the dated measurement.
4. qwen P3, "reset the toy's `_calls`". REFUTED. Each runner run is a fresh process, so the module starts at 0. The
   assertion needs both lookups among the 33 rows, whatever the starting parity.
5. glm P1, "automate PP-E31's detection: the batch's own law says 'none automatic'". ACCEPTED, verified. New test
   test_f0::test_keys_are_read_only_by_name_through_the_pipelines_loader:
   - no string constant in any .py of the suite names the key file (the scan walks >= 20 files);
   - frontier_blind.KEY_LOADER is the main tree's video_pipeline_v3/relay.py;
   - `_key` calls `.get_key` and opens no file.
   Mutation: a throwaway suite file holding the key-file path fails the test, naming it; the file was then deleted.
6. glm P2, "spec None gives a cryptic AttributeError". REFUTED, measured: for a missing .py path,
   spec_from_file_location returns a SourceFileLoader spec, and exec_module raises
   `FileNotFoundError: [Errno 2] No such file or directory: '<the path>'`. That error is legible and fails closed. It
   is now documented in `_key`'s docstring.
7. glm P2, "document the process-wide bytecode-toggle window". ACCEPTED (`_key`'s docstring).
8. glm P3, "note the network test's dependency on the runner's ERROR-row format". ACCEPTED (docstring, naming
   moments_exam._judge).
9. glm P3, "package awareness in the unscanned-names check". ACCEPTED, with the direction corrected. A dropped package
   was a FALSE NEGATIVE, not a false positive: the check looked only for <root>/<name>.py. Now it also looks for
   <root>/<name>/__init__.py.
10. glm P3, "network_reverse's context_integrity / vo_fidelity are unexercised". NOT ACTED ON. They are the
    harness's gate contract (all three functions), exactly as moments_toy_gates/network.py.

No P0. Nothing implemented loosens what a check accepts. Cycle 2 reviews the UPDATED diff (CURRENT.diff regenerated
after items 1, 5, 7, 8 and 9).
