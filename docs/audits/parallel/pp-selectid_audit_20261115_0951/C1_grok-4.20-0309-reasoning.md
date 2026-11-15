# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 38 s finish=stop usage in 12097 / out 760 usd_reported=0.027769 usd~0.079 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_0951 (C1_STEP.diff)**

**Summary**  
The diff is a narrowly-scoped reporting-only change. It adds `report["refused"]` (moments whose *last* row is non-ready/failed/unreadable) in `word_pass_index`, threads that list into `build_inputs` and `spotlight.next_attempt`, updates the derived counts (`window_refused`, `word_pass_refused`), adjusts the no-word-record path so an all-refused video is not counted as “waiting for a record it will never receive,” and updates logs/tests accordingly. No selection, anchoring, sentence-law, punctuation, gate, EDL, render, release-auth, or byte-producing path is touched. The original mis-count (refused moments appearing as “waiting”) is fixed exactly as described by the integrator note. All governing laws are satisfied: the change is purely diagnostic, cannot alter which moments enter a build, cannot cause a gate to pass what it must refuse, preserves L-j/L-k/L-l fail-closed behavior, leaves v2f and the protected preview untouched, and uses only canonical forms for strings. Tests (including the new ones) pass, 12/14 mutations killed; the two survivors are in unreachable driver-after-router and non-CI report-script paths.

**Findings**  
[P3] `word_pass_index` docstring update is accurate but could explicitly state “last row per `moment_id` wins for both the ready index *and* the refused list” to match the test name and integrator comment.  
[P3] `spotlight.next_attempt` line `r.get("moment_id") not in word_pass` is defensive (refused list is already disjoint) and harmless, but adds a tiny amount of redundant work on every call.  
[P3] `build_inputs` `if not windows and len(rs) > n_ref` branch correctly subtracts refused rows from `no_word_record*` counters and per-video dicts; the all-refused video exclusion is intentional and documented in the new comment, but the control-flow (n_ref incremented in the None-wp path, added after the per-video loop) is subtle and merits a one-line inline comment at the `report["window_refused"] += n_ref` site.  
[P2] The two surviving mutations (driver ruling-95 path when router is mocked out, and `funnel.py` report script) are acceptable given current test coverage, but a future change that exercised the full driver past the router or ran funnel in CI would make them live. Recommend a trivial follow-up test that forces the “no refused= argument” code path in the driver (already partially covered) to reach 14/14.  
[P3] Log string and JSON keys now expose “refused” count/ids; this is useful debugging data and stays inside the audit pack (inputs.json, package.log). No PII or secret material added.  
[P3] All new test assertions match the described semantics (last-row-wins, no double-counting, backward-compat when refused= omitted, vidY/vidZ/vidX cases). Test coverage for the no-window branch is adequate.

No violations of SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, LAW 20/M2, M12 FAIL CLOSED, or the protected-preview reference. No new model calls, no renderer changes, GPU0-only, smallest diff. The fix prevents misleading “4 wait for their own window … when they land” messages for permanently refused Scott Melker moments.

P1_OR_WORSE: 0