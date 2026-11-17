# C1 CONSENSUS — pp-selectid audit 20261116_2313 (RULING 130 (2): the render's lock before any paid vision check)

Seats (Heimdall only): qwen3.8-27b (effort medium, 24,000), gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3
(mimo EMPTY at 32,000). P1_OR_WORSE: qwen 0, gemma 1. Cycle 1 $0.0096 of Heimdall, not capped.

gemma's [P0] ("the no-voice path proceeds to see(order) on a HOLD: nv_pre.get('error') is None and the segments are
populated, so the 'if' fails"): NOT SO. Its excerpt leaves out the OUTER guard. dev51 package.py, the no-voice block:
  :3457  if nv_pre is not None and not nv_pre.get("ok"):          <- a HOLD has ok False: this branch is taken
  :3458      note["why_not"] = f"ruling 68 / 72: the render's lock: {... or 'a clip holds'}"
  :3459      if nv_pre.get("error") or not nv_pre.get("segments"):   <- only no-verdict also sets lock_stop
  :3460          out["lock_stop"] = note["why_not"]
  :3461      return None                                        <- every not-ok answer (hold or no verdict) returns
  :3462  see(order)                                             <- reached only with ok True
Its claim that the tests miss this branch is also not so: test_medley TestRuling72Lock
test_the_no_voice_line_up_asks_the_lock_too drives the no-voice line-up ([h, x, y, z], z added) with the lock holding z
and asserts z is never seen (rig.visual_calls); mutation K2 (a see(order) put back before that lock) was KILLED by it.
No change. qwen: 0. Unchanged: dev51, mutations K1-K6 6 of 6 killed after a control run; 40 suite files by exit code,
854 tests.
