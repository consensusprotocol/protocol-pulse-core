# Ruling 77 (expiry + rolling purge), audit cycle 1: consensus and dispositions

Reviewers (Heimdall-served; the frozen vendors skipped): qwen3.8-27b (222 s, $0.018), glm-5.3-flash (363 s, $0.004),
muse-spark-open-816b (554 s, $0.026). Verdicts: all three "ready for production"; no P0 from any.
Q1 (can it delete what the ruling keeps?) all three: no. Q3 (can the adapter return a moment 12 h after publish?) all
three: no (glm and muse traced every path: no field, a later field, no publish time, a re-mined row, a wider horizon).

## IMPLEMENTED (each with a test)
| finding | reviewers | fix | proof |
|---|---|---|---|
| a corrupt or unreadable record of a delivered run (edl.json, PIN.json, PROVENANCE.json) silently shrank the delivered set: the one fail-open path | glm P1 (and P2 "inconsistent failure policy") | unit_videos records it as a problem: the pass deletes nothing | test_purge `test_a_corrupt_record_of_a_delivered_run_stops_the_pass` |
| a purge that cannot run (spec refused, /proc or the delivered set unreadable) was only logged | muse P1 | after 30 min, one line at the top of STATE ("PURGE NOT RUNNING since ..."), removed by the first pass that runs | test_service `test_a_purge_that_cannot_run_safely_for_30_min_is_noticed_at_the_top_of_state` |
| processes whose open files cannot be read were skipped silently | muse P1 | counted and reported in every pass (`proc_unreadable_pids`); not a refusal: they are other users' processes, and the 2 h idle rule is the second guard | the pass report |
| an unreadable directory or file inside a unit | qwen (permissions) | os.walk raises on an unreadable directory: the unit counts as in use; an unreadable file is kept ("not readable") | test_purge `test_an_unreadable_directory_makes_its_run_in_use` |
| wrong-typed spec fields fail late (TypeError in the constructor) | glm P3 | load_spec checks every type (targets a list of objects, enabled a bool, delivered lists and absolute paths, publish_time); the constructor catches any exception and the purge stays off | test_purge `test_the_spec_refuses_wrong_types` (5 cases) |
| the 12 h boundary untested in the purge | muse P2 | at exactly publish + 12 h the media goes, as the adapter expires it | test_purge `test_a_file_exactly_12_h_after_its_publish_time_is_expired_as_in_the_adapter` |
| a bare upload date (midnight, no source) could make a video look up to a day older | found by the builder while auditing | the end of that day is used: never deleted early | test_purge `test_a_bare_upload_date_is_read_as_the_end_of_that_day...` |

## REFUTED / BY DESIGN
| finding | reviewer | evidence |
|---|---|---|
| P0 "verify symlink handling against a real filesystem" | qwen | already tested on a real filesystem: a real symlink in sources/ is kept and its target intact (test_purge `test_a_pass_deletes_only_expired...`) |
| the 72 -> 12 h horizon default is a breaking change | muse | the output cannot change: every line older than 12 h is refused as expired whatever the horizon; documented in the module docstring |
| reading lines that are then dropped as expired is wasteful | glm | by design (one bounded read); measured 0.86 s per pass |
| "more than 12 h old" vs `now >= exp` | muse | "usable only WITHIN 12 h" (ruling 76): at 12 h exactly it is no longer within; the adapter and the purge agree (tested) |
| hot-reload of purge.json | glm P2 | deferred: the spec changes only by a ruling, and a restart is safe (the queue recovers); a refused new spec would anyway stop the purge |
| freed_total mixes regimes if expiry_h changes | glm P3 | expiry_h is locked to config.EXPIRY_H by load_spec |
| newest_mtime does not follow symlinked directories | glm P3 | documented: the files deleted are never behind one (symlinked units are skipped, symlinked files never deleted) |
| a wall-clock jump | muse | inherent to wall-clock expiry; noted |
