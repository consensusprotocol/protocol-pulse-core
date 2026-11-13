# pp-selectid audit 1420 (RULING 66's standing part: the candidate registry): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", P2s only.
  - qwen: "SHIP: NO", on two "P0"s and two P1s.
  - glm: no P0. Its first attempt failed on transport (IncompleteRead, 18 min). The re-run finished at its 24k-token limit (finish=length), with P1s its own text mostly resolves.
- No P0 holds as stated. One consensus item is applied before cycle 2 (C1).

## Applied (the consensus item)

| # | finding | the change |
|---|---|---|
| C1 | A stored registry time that _at() cannot compare crashes due() mid-build: grok P2 (a malformed "until" raises at due() time), qwen P0-1 (a naive time against the aware now), glm P1-8 (a TypeError there would kill the run) | _at() reads a time without a zone as UTC; every time this module writes is UTC-aware already, from the driver's datetime.now(timezone.utc) and the records' now.isoformat(). The driver now evaluates CA.due(reg, now) inside its refusal block, so a malformed stored time refuses the run (exit 2) before anything is written. Test: test_a_stored_time_without_a_zone_is_utc_and_a_malformed_one_raises. |

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P1-4: "attempts" is not defined in the diff, so a line failure may be classed "clip" | rec["attempts"] is the tried entry's list in the unchanged loop (`rec = {..., "attempts": [], ...}`). EVERY write appends to it: `rec["attempts"].append(att)` after a write, and `rec["attempts"].append({"writer_error": ...})` on a writer error. A line-up that reached a write therefore has a non-empty list. Test: test_the_outcome_class_and_the_fresh_writes asserts "line" for two writes failing on the takeaway. |
| R2 | qwen P1-5 = glm P1-2: build(candidate=) may spend a judged line-up on a verdict served from its recording, or count none for one judged afresh | The unchanged budget line (ruling 65's): `total += 0 if med.get("replayed") or med.get("cached") else 1`, and out["search"]["lineups"] = total, which try_one returns as `judged`. test_a_cached_clips_alone_verdict_is_free (test_medley) asserts lineups 0 for a cached verdict. |
| R3 | qwen P1-3 = glm P1-1: a missing found_at sorts as the string "None" (first, inverting newest-first) | The key is `str(x[1].get("found_at") or "")`: None becomes "", never "None". |
| R4 | qwen P2-7: res["now"] could be None and crash the seeding | The driver sets res["now"] = now.isoformat() (res.update) before package.json is written and before CA.seed reads it. |
| R5 | grok P2: --from-candidate never adds "registry": True | `res["registry"] = True` sits after both branches (the --from-candidate one and the due-candidates one). Only candidate_tries is the due path's own. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | qwen P0-2: an OSError reading a candidate's record closes it as "clip" (for good), though it is not a gate failure | The records are tracked files under tests/package/proof, never written after their build; a missing one is gone for good, not transient. Recorded for cycle 2. |
| G2 | grok P2: the "line" class depends on attempts / relined | R1. |
| G3 | glm P1-4: a fresh try whose build raises leaves fresh_used set in memory | The registry is saved only after package.json, so a crashed run leaves the file as it was, and the next build makes the fresh try again. A crash is not a completed try ("tried once more"). |
| G4 | glm P1-5 (glm: P2): the packaged-close compares the package's segment order | The package's segments are in play order, the line-up's order, in the same build. A miss leaves the candidate open; its next try finds its clips delivered and closes it ("clip"). |
| G5 | glm P1-6 (glm: P2): with no judged line-up left, the record's search block is the last try's | That is reporting only. candidate_tries carries every try's judged count. |
| G6 | glm P2-100: a lost registry re-seeded from the records loses the post-registry outcomes | The registry is tracked in git and committed with the build records it indexes. A corrupt file refuses the run (exit 2). It is never rebuilt silently. |
| G7 | glm P2s (the rest) | Records, or self-resolving in glm's text. |

## Verification

- All 13 suites OK on dev24 (base 4106da2c). With C1: test_candidates 7 OK, test_ledger_build OK.
