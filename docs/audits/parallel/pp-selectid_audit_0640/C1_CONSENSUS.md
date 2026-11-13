# pp-selectid audit 0640 (ORDER 06:22 items 45 and 44): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers package.py and test_medley.py. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- qwen: "SHIP: yes with conditions" (its P1-1 and P1-2);
- glm: "SHIP: yes with conditions" (four conditions); no P0.

## Consensus: IMPLEMENTED

| # | finding (reviewers) | change |
|---|---|---|
| F1 | An exception out of one parallel prescreen call would crash the whole build, not fail its clips closed (qwen P1-1, glm P1-3 / condition 4's spirit) | second_screen runs each chunk through one(): a raising chunk returns STEP_A_UNAVAILABLE: <exception> for each of its clips, never a pass, never a crash. Tested (a raising prescreen fails all four clips closed). |

## Single-reviewer findings: IMPLEMENTED (no change to what any check accepts)

| # | finding | change |
|---|---|---|
| S1 | glm P2-8: the STEP_A_SAME_VENDOR reason says "not off the first's vendor" while the check also compares the family | the reason names both ("not off the first's vendor X and family Y"). |
| S2 | glm P2-9: the "no swap fits -> re-lined" branch of item 44 is untested | tested: y fails its re-screen, no clip can replace it, the line-up re-lines, y stays out (rescreen_failed), no second line-up is judged. |
| S3 | glm condition 1: the both-writers case is tested only with the rig's third vendor | the production-shape fact is now asserted: when Grok writes the angles, every write avoids Heimdall (rig.write_avoid == [{"heimdall"}]). See K3. |

## Misreadings and non-defects (verified from the code)

| # | claim | the code |
|---|---|---|
| K1 | qwen P1-2: `two[mid] = [a_by[mid], a2]` can raise KeyError | second_screen groups a clip by `a_by.get(mid)`'s back-end; a clip with no first verdict lands in the None group, which never reaches that line. Also build() makes `cleared` from `a_by` (`m["moment_id"] in a_by and not fails...`), so every cleared clip has a first verdict. |
| K2 | glm P1-1: a clip beyond PRESCREEN_N could reach second_screen without a first verdict and read as UNKNOWN_BACKEND | `cleared` holds only moments the first screen answered and passed (same line as K1). second_screen passes n=len(chunk), so nothing of a chunk is truncated. |
| K3 | glm P2-3: with both vendors writing, the re-screen has no back-end, and the swap could loop | (1) It cannot arise with the configured chains. writer_avoid = the angle_write chain's vendors minus the angle's vendor, and write_takeaway passes it to router.call (package.py, write_takeaway: `avoid_vendor=avoid_vendor`). After a Grok angle, no write can come from Heimdall, so the writers stay one vendor. Now asserted (S3). (2) It is bounded anyway. Each failed re-screen adds its clips to `doomed`, the swap and re-line exclude `dropped \| doomed`, and `total < lineups` (8) plus the search budget stop the loop. The rig's third vendor exercises item 44's mechanics for a future chain with three vendors. |
| K4 | glm P2-4 / condition 3: the router's spend ledger may not be thread-safe under the parallel second screen | providers.Router serialises every ledger write under `_lock()`, an fcntl.flock on the ledger's lock file. Each call opens its own file description, so threads in one process exclude each other. Records use per-thread tmp names (`_record`: `{pid}.{thread ident}.tmp`). build() already calls the router concurrently (truth_for / exclusion_for in a ThreadPoolExecutor; "the gates call concurrently", 05:25 item 5). Kept parallel: it saves about 3 min per build. |
| K5 | glm P2-6: second_vendor's "PASS (backend)" can differ from the verdict the gates finally use (a third, after a re-screen) | the sealed gate inventory's "context_a" row records the back-ends of the step-A verdicts actually used (inventory: `sorted({str(a.get("backend")) for a in a_rows})`, from a_lab = a_by of the package's segments). second_vendor records the pre-angle screen, as named. |
| K6 | qwen P1-6, glm P2-2 / P2-10 / P1-4 | verified by the reviewers themselves in their own text (stale a_by entries for filtered clips are never read; the fallback string is defensive; the swap excludes dropped and doomed). |

## Recorded, not changed (the order's own design)

- **glm P2-5:** a Heimdall step-A outage at second-screen time now ends a build before the angle step. The old code
  could have completed if Heimdall came back in time and the angle came from Heimdall. Order 45 orders exactly this:
  both screens before the angle step, so no line-up is built on a clip a re-screen would fail. Fail closed (L-m),
  earlier and cheaper, with the reasons in out["prescreen"]["second_vendor"]. This trade-off goes into STATE.

## Verification

- test_medley: 80 tests OK (72 before this change; 8 new). The other suites (angles, gates, hook_onset, house_style,
  ledger_build, speakers, providers, moments, eligibility, select_by_id) are OK on the change.
