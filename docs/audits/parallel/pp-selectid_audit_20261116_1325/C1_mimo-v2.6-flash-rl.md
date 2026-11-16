# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 227 s finish=stop usage in 8777 / out 15016 usd_reported=0.001684 usd~0.252 (upper-bound price)

# CODE AUDIT — pp-selectid (RULING 118 (4) id translation)

Scope reviewed: `in_pool_ids` mapping semantics, the `build()` call site, the `ledger_aliases` plumbing, and the test changes. I traced the id flow described in the defect note (ledger_build.make → `mined.ledger_moment_id`, `duplicates_of` → aliases, stories file names ledger ids) against the implementation and the assertions.

---

## FINDINGS

### [P1] Nothing fails closed when a non-empty stories file translates to ZERO matches — the exact silent-death defect this ticket repairs can recur invisibly

`pipeline/package.py`, `in_pool_ids` (diff 9–29) and the call site (diff 49–51).

Every unmatched file id is dropped silently (`idx.get(lid) or idx.get(alias) or []` → `[]`), and the only signal is the new informational record `out["stories"]["matched"]` (diff 50–51), which nothing reads, asserts, or HOLDs on. Consequences:

- If `cleared` moments ever stop carrying `mined.ledger_moment_id` (a moment not re-anchored by `ledger_build.make`, a stripped `mined` dict, a schema drift), **every** story translates to `moment_ids=[]`, `story_angles` builds nothing, and the pipeline proceeds exactly as builds 41–57 did — for as long as it takes a human to notice. That is the precise failure mode this branch exists to fix, and the fix does not close it.
- Same for a future/other stories file that names *build* ids: the new test (diff 118–120) asserts `cleared: 0` as *desired* behaviour, i.e. the code is deliberately built to match nothing in that case, with no stop.
- Per M12 ("missing data … never produces a pass") and the defect history, a non-empty, successfully-read stories file whose total match count is 0 is missing data and should HOLD (or at minimum hard-fail the story-first source), not fall through to the angle writer. `matched` already carries the numbers needed for the check; the gate is simply absent.

Suggested shape: after `in_pool_ids`, if `out["stories"]["read"]` and `stories` non-empty and `sum(len(s["moment_ids"]) for s in stories) == 0` → HOLD with the `matched` record as evidence. (Partial matches are normal — moments that did not clear — so gate on the file-wide zero, not per story.)

---

### [P2] A parent moment and its trimmed variant are both indexed under the same ledger id, so one story line-up can contain two clips of the same speech

`in_pool_ids` (diff 16–20): `idx.setdefault(lid, []).append(mid)` collects **every** build id carrying the ledger id, and the docstring says "every match … each once". The test locks this in: `L1 → ["b1", "b1~trim"]` (diff 116–117).

`ledger_build` keeps a trimmed variant alive with its parent's ledger id (only *ledger rows* are deduped via `duplicates_of` — that alias path handles rows, not variants). So a story naming `L1` now yields both variants as candidate moments, and nothing in this diff (or in `story_angles`/`story_pool`, which are unchanged) shows a same-speech dedup between them. If both clear, a STORY-FIRST line-up can ship two clips of one utterance — an editorial error of the same family PBX caught by hand on 2026-11-10.

Please confirm one of: (a) downstream medley/gates reject two moments sharing a `ledger_moment_id`, or (b) only one variant is ever in `cleared` at a time, or (c) index one preferred variant (e.g. the parent) per ledger id. If none holds, this is the wrong index shape.

---

### [P2] The alias half of the fix is silently disabled for any `build()` caller that omits `ledger_aliases`

`build()` gains `ledger_aliases=None` (diff 40–41); only `tests/package/proof_ledger.py` passes it (diff 63). With the default, `in_pool_ids` still runs but `(aliases or {})` is empty, so a stories file whose ids are all *dropped duplicates* (`duplicates_of` targets) matches nothing — again silently, and again only visible in the informational `matched` record.

Since `stories_path` and `ledger_aliases` are set together or not at all, make the mismatch loud: when `stories_path` is truthy and `ledger_aliases is None`, HOLD (or at least record `aliases: "not supplied"` in `matched`). Also confirm `proof_ledger` is the *only* production caller of `build()` with `stories_path` — no other caller appears in the diff, and I cannot verify from the package that none exists.

---

### [P3] `inputs.get("duplicates_of")` will raise if `inputs` is `None`

`tests/package/proof_ledger.py` (diff 63). Every other argument in that call block is a module constant; this is the only one dereferencing `inputs`. If the harness can run with `inputs = None`, this crashes before `build()` — fail-closed, but an avoidable hard crash. Use `(inputs or {}).get("duplicates_of") or {}`.

---

### [P3] Test helper `ledgered()` replaces `mined` instead of merging into it

`tests/package/test_medley.py` (diff 75–78): `dict(m, mined={"ledger_moment_id": "L" + m["moment_id"]})` discards any other keys `pm()` puts in `mined`. Production moments carry a richer `mined` (the defect note cites `moments[134]`), so the tests exercise a shape production does not have; if any gate or scorer reads another `mined` key, these tests now run against a dict that lacks it. Merge instead: `{**m, "mined": {**(m.get("mined") or {}), "ledger_moment_id": ...}}`.

---

### [P3] Documentation / evidence nits

- The defect note says `matched` records "the file's ids" per story; the code records only **counts** (`len(s["ledger_ids"])`, `len(s["moment_ids"])`, diff 50–51). Counts are enough for a gate, but the doc overstates what an auditor can see — an id-level mismatch is not diagnosable from `matched`.
- The claimed mutation run "T1–T3 beside S1–S18, after a control run" is not in the diff and is not reproducible from it. That said, the three mutation *intents* are killed by committed tests: T1 (no translation) fails the converted story tests that now require `out["angles"][0]["story"] == "S-1"` from ledger ids (diff 131–134) and the medley-call assertions (diff 101–106); T2 (aliases ignored) fails the new exact-equality assertion where `b2` arrives only via the alias (diff 116–117); T3 (direct build-id matching) fails the `cleared: 0` assertion (diff 119). So the coverage is real — only the run log is missing.
- `aliases` is resolved one hop only (`idx.get((aliases or {}).get(lid))`, diff 25). This is correct **iff** `duplicates_of` always maps a dropped row to a *kept* row, as `ledger_build.py:524/:563` is described to do. If a chain (A→B→C, B also dropped) is possible, the tail silently drops. Worth a one-line assertion or a comment pinning the invariant.

---

## WHAT I CHECKED AND DID NOT FIND PROBLEMS WITH

- **Mapping core (request 1):** direct-hit-before-alias precedence is right (`idx` values are always non-empty lists, so `or` never short-circuits a real hit); a dropped duplicate's id is only consulted when its own id is absent from the pool, which cannot collide (a ledger row is either dropped or kept, never both); unknown ids drop cleanly; `b4` with no `mined` does not raise; file order and "each once" dedup are honoured; the original `stories` list is not mutated (`dict(s, …)` copies, `ledger_ids` is a fresh `list(...)`); `pool`/`cleared` is the right index source (only cleared moments are usable, and `story_angles` already indexes `cleared[moment_id]`).
- **Nothing else changed (request 2):** confirmed. The `build()` kwarg is defaulted, so no other caller breaks; `story_angles`, `story_pool`, every gate, threshold and budget are untouched; no renderer/compositor/selector added (M1); no text comparison added outside `canon.py` (L-k n/a); no law on the pulse render path is touched by this diff. The only behavioural delta is the id translation plus the new `matched` record.
- **Tests (request 3):** the conversion of all existing story-first tests to ledger-id-shaped fixtures is complete and consistent (class `MS`, the swap test, the short-story test, the no-file test all use `ledgered()` + `L`-prefixed ids), positive coverage exists (a story *does* produce an angle through the translation), and the negative case (file naming build ids → nothing) is asserted at both function and build level.

---

P1_OR_WORSE: 1