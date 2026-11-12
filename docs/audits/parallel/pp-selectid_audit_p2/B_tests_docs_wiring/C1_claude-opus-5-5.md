# claude-opus-5-5 (effort high) 269 s stop_reason=end_turn usage=in 52110 / out 26375

# Code audit: pp-selectid-p2 (moments-first, provider interface)

**Reviewer identity:** I am Claude (Anthropic). I am not Gemini, GPT-4o or Grok. The review below stands on its own.

## Scope limit

The diff under review contains only:

- `docs/audits/MOMENTS_FIRST_DESIGN.md` (new)
- R7 and R8 in `pp-selectid_REQUESTS.md`, which includes the pinned.py patch as text only
- tests and harnesses under `tests/moments`, `tests/package` and `tests/providers`

It does **not** contain:

- `pipeline/providers.py`, `moments.py`, `package.py`, `vo_fidelity.py`, `context_integrity.py`, `transcript_truth.py`, `package_pin.py`, `moments_gate_adapter.py`
- `model_providers.json`
- any `release_auth.py` change

Most of Q1–Q4 therefore cannot be verified. I mark each claim as **verified** (from diff code), **inferred** (from test expectations or doc text) or **unverifiable**.

The stack header (Flask, SQLite, CSS-only UI, 1000 users, DB indexes) does not apply. There are no routes, DB access or UI in this diff.

## Scores

Scores are confidence that the property holds, as far as the diff shows.

| Q | Score | Basis |
|---|---|---|
| Q1 Fail-open | **35** | R7 trusts self-asserted, truthy booleans not bound to content. L-v 2 is optional in the driver. An unmeasured speaker change counts as usable (verified in a test). The release requirement (R7 item 4) has no code. Gate internals are unverifiable. |
| Q2 Vendor separation / L-x | **45** | The router avoids `avoid_vendor` and fails closed when the chain is exhausted (verified in a test). A single `writer_vendor` string cannot cover angle + writer + rewrites after failover, and Step A runs before any writer exists. The config test checks only the first back-end of three verdict roles. Harness code hard-codes `local:gemma3:27b`. |
| Q3 Verbatim / model text | **30** | The title, caption and VO reach the EDL from the pin with no check against the gated text or the sha. The EDL's `topic` / `angle` come from pin fields of unknown origin. Clip verbatimness happens in sentence-law code that the smoke test mocks out. |
| Q4 Deterministic rules | **40** | Only test inputs and doc text are visible. Several scope gaps are documented (PRICE_NOW on headlines only, DUPLICATE on the line before only with no caption, NAME skips Title Case). |
| Q5 Tests / R7 | **50** | R7 refuses a bridge after the last clip and a falsy context check, and keeps a plain pin unchanged (verified via smoke). There are vacuous or near-vacuous tests, a tautological sha assertion, the smoke test applies with `patch` rather than `git apply`, and a pin-clobbering bug in the proof driver. |

---

## FINDINGS

### P0

**P0-1. R7: the gate verdicts are not bound to the bytes that get rendered.** Violates L-t ("any change after the gates re-runs them"), L-j and M12. Verified.

`REQUESTS.md` R7 patch:

```
332-334  edl.update(title=mp["title"], caption=mp["caption"], moments_package_sha256=mp["package_sha256"], moments_checks=mp.get("checks"))
343      v = mp.get("edl_vo") or {}
352      if not mp.get("checks", {}).get("vo_fidelity_ok") or not mp.get("checks", {}).get("context_integrity_ok"):
```

Five problems:

- `package_sha256` is copied, never recomputed.
- `edl_vo`, `title` and `caption` are never compared to the text that was gated (`mp["vo"]`).
- The checks are truthiness tests, so `"false"`, `"no"`, `1` and `{"x":1}` all pass.
- Only two of the hard gates are required. DUPLICATE, PRICE_NOW, runtime, coherence and L-v 2 are absent unless they are folded into `vo_fidelity_ok`, which is unverifiable.
- R7 item 4 (lines 293-300, "release authorisation must require both, from `edl["moments_checks"]`") has no patch in the diff. Nothing downstream checks these fields.

The smoke test itself shows the checks are plain editable fields (line 888: `pin["moments_package"]["checks"].update(vo_fidelity_ok=True, context_integrity_ok=True)`).

Failing input: take a gated pin and edit `edl_vo.intro` to "Bitcoin is at 126K today." and `title` to anything. Set `"vo_fidelity_ok": "false"`.

- `build_edl` accepts it.
- The EDL carries the edited VO and title with the original sha.

### P1

**P1-1. R7: a malformed package silently becomes a plain pin.** Verified.

```
319  if isinstance(mp, dict):
320      vo = moments_vo(mp, clips)
332  if isinstance(mp, dict):
```

`"moments_package": null`, a list or a string skips every moments check. The result is an EDL with no `moments_checks`, rendered as an ordinary pin with the default VO.

The fix is fail closed: `if "moments_package" in pin and not isinstance(mp, dict): raise PinError`.

Related, also verified:

- `checks: null` raises an AttributeError, not a PinError (`mp.get("checks", {})` returns None).
- A missing `edl_vo` renders no package VO at all while keeping the package's title.

**P1-2. Missing speaker-change measurement counts as usable.** Violates M12. Verified in a test.

`tests/moments/test_moments.py`:

- line 586: every fixture has `"speaker": {"turn_change_inside": None}`
- line 612: `self.assertEqual([m["moment_id"] for m in ok], ["f"])`

An unmeasured value (None) passes `usable`, although the design says "no measured speaker change inside (L-v 1)" (doc line 91). Doc §8 (216-219) admits L-v 1/2 are not run.

Failing input: a moment with `turn_change_inside: None` that actually spans two speakers. Only the model's Step A guards it.

**P1-3. L-v 2 (the second recognition pass) is optional.** Inferred.

- `tests/package/proof_packages.py:705` passes `truth_dir=truth_dir`, which defaults to None.
- Line 730 help: "run law L-v 2's second recognition pass (audio windows go here)".
- Doc 4b step 7 (134-136) calls it part of the build.
- Doc §8 (216) says it is open.

The default path produces a package without L-v 2. Whether `PK.build` fails closed on `truth_dir=None` is unverifiable. The help text implies it skips.

**P1-4. Vendor separation is a single string.** Partly unverifiable.

- `test_gates.py:1080`: `CI.check_contexts(r, PKG, CTX, writer_vendor="openai")`.
- Doc line 50: `avoid_vendor = the writer's vendor`.

Three gaps:

- Angles (doc 119-122) and the VO writer are separate `angle_write` calls. Rewrites can run up to 3 times (127). Failover marks a vendor down "for the rest of the run" (48).
- The package text can therefore come from two vendors: angle and hook from V1, VO from V2. A verdict that avoids only V2 can run on V1. Concrete case: the openai writer hits a 429 mid-rewrite, anthropic finishes the job, and coherence runs on openai.
- Step A "never the writer's vendor" (doc 185) is impossible to enforce. Step A runs before any writer exists (doc 118: "screens each candidate moment's own context once (package-independent)").

The fix: verdicts should take the set of vendors of every Reply whose text they judge.

**P1-5. The config test checks only part of the separation.** Verified.

`tests/providers/test_providers.py:1556-1559` loops over `("fidelity_verdict", "context_verdict", "viewer_takeaway")` and compares only `chain[0]` against the writer's `chain[0]`.

- `coherence_verdict` and `exclusion_verdict` are unchecked.
- So is the rest of each chain.

**P1-6. The A/B on the verdict roles is not blinded.** Affects the L-x re-ordering decision. Verified.

`tests/providers/ab_roles.py:1408-1409`:

```
expected = case.pop("expected", {}).get("verdict")
case.pop("provenance", None)
```

The real case `id`, `origin` and nested `provenance` reach the gate. Compare `run_exam_record.blind()` (775-784), which strips them and hashes the id.

Failing input: a case with `"id": "vo_fidelity_mustfail_017"`. The answer leaks to the gate, and to the model if the adapter prompts with the id. That inflates the confusion table used to re-order chains.

Also, `expected: null` crashes on `.get`.

**P1-7. The yield report writes "PASS" without reading the gates.** Verified.

`tests/package/yield_table.py:1250`:

```
gates = "VO fidelity PASS, context integrity PASS"
```

This is hard-coded whenever `package` exists. The L-n DONE decision ("DEFECT to fix before DONE") is read from this table.

The fix: render `pk["checks"]` and mark it FAIL when a check is missing.

**P1-8. The proof driver clobbers the top pin when alternatives exist.** Verified.

`tests/package/proof_packages.py:713-717`:

```
path, _ = package_pin.write_pin(pk, run, os.path.join(OUT, run))
if i:
    os.replace(path, path.replace("MOMENTS_PIN.json", f"MOMENTS_PIN_alt{i}.json"))
```

Every iteration writes the same `MOMENTS_PIN.json`. With `--want 2`, the sequence is:

1. Iteration 0 writes the top pin.
2. Iteration 1 overwrites it with the alternative.
3. Iteration 1 then moves it to `_alt1`.

The top pin is gone, but line 718 logs its path. R7 step 2 renders "the MOMENTS_PIN.json" by path.

**P1-9. PRICE_NOW covers headlines only.** Documented scope gap.

Doc line 141-142: "a headline line (intro, title, caption)".

Failing input: a bridge "Next: Bitcoin at 126K." citing Simply Bitcoin 399.15-405.25. This is the exact R8-1 misleading-now case, moved into a bridge. NUMBER passes because the value is in the cited sentence.

Unverifiable whether `current_levels` filters hypotheticals. Example: a ≤24 h source saying "if Bitcoin is at 126K by summer" in present tense could become a "current level". The test (1005-1008) covers only "is trading at ... right now" and a dated history sentence.

**P1-10. Names in Title Case titles are guarded by the model verdict only.** Inferred from the doc.

- Doc 148: NAME "skips ... Title Case titles".
- Doc §8 (219) forbids naming any person.

Failing input: title "Michael Saylor: Bitcoin Holds The Line". NAME skips it and no attribution verb triggers ATTRIBUTION. Only the blind verdict stands between a named person and the title.

**P1-11. Fidelity verdict coverage is untested.** Unverifiable, high risk.

No test covers either of these:

- `{"claims": []}`
- claims only for `intro` while `title` and `caption` get none

If the code is "all claims yes", an empty or partial claim list passes vacuously.

There is also no test of a minimal-length support. `{"segment":"m1","words":"Bitcoin"}` is a verbatim run of any segment, so the code check (doc 175) only rules out fabricated words. It does not rule out a lenient judge.

### P2

**P2-1. The DUPLICATE scope misses the real R8-2 case and over-matches.**

Scope gaps (doc 144-145: the "line right before a clip, and the title"):

- An intro repeating clip_03 is not caught, because the intro is "before hook" (test line 1002).
- The caption is not covered at all.

False reject: a bridge "Next, what the price of Bitcoin is doing" before a clip "the price of Bitcoin is down 8%". That is a 5-token run of function words.

**P2-2. Vacuous tests.**

- `test_angles.py:989`: `if seg and any(m["moment_id"] == "d" ...)` asserts nothing when "d" is excluded or the line-up is None.
- `test_moments.py:620`: `for s in PK.candidate_sets(ms)` asserts nothing if no set is produced. In the correct case it produces none, since the only 3-channel set has two predictions.
- `smoke_r7.py:901`: `assert edl["moments_package_sha256"] == pin["moments_package"]["package_sha256"]` is a copy-equals-copy tautology.
- `test_gates.py:1124-1125`: the "step A skipped a segment" case asserts only `not ok`, with no rule.

**P2-3. Test fixture contradictions and missing cases.**

- `test_angles.py:969-970` expects "3-8" and accepts a 3-moment angle. Doc line 121 says 4-8.
- The `["a","e","zz"]` case expecting "3-8" suggests unknown ids are filtered and then counted, which would be repair rather than rejection. No test covers `["a","b","c","zz"]`. If that is accepted, it is a silent repair.

**P2-4. The spend guard overshoots.** `test_providers.py:1532-1539` asserts that two $10 calls succeed under `limit_usd=15`. The guard checks after the fact. The fix is to reserve the upper-bound cost (`max_tokens × price`) before the call.

**P2-5. The replay key omits the model version.**

- Doc line 51 keys on (role, back-end, prompt, max_tokens, seed, system), with no model digest or temperature.
- L-f's cache keys on the Ollama digest.

A re-pulled `gemma3:27b` replays stale replies. Separately, R7 does not check a `replayed` flag, so a `--replay` package can become a pin (L-j: replays are never deliverable). This is unverifiable beyond the patch.

**P2-6. Smoke vs claim.**

- `smoke_r7.py:872` uses `patch -p1`, which allows fuzz.
- Doc line 266 claims `git apply --check` is clean.
- `validate_range`, `make_lock` and `sha256_file` are all mocked (889-896), so text location by the sentence law is not exercised.
- Not tested: after_clip 0, duplicate after_clip, `after_clip=True` (`True in {1,2}` is true), and checks as truthy strings.

**P2-7. A/B harness quality.**

- The judge prompt (1314-1325) contains no source rows, contradicting the docstring (1283).
- It sends the first 8 moments, not the best 8.
- It runs once with one random flip, so the "better / worse" in doc line 246-247 is n=1.
- `--judge` (1376) is not checked against the compared set.
- `next(...)` raises StopIteration outside the try block.

**P2-8. L-x hygiene in harness code.**

- `ab_roles.py:1373` and `test_providers.py:1555` hard-code `"local:gemma3:27b"`.
- `ab_roles.py:1312` `ENV = "/home/ultron/protocol_pulse/" + "." + "env"` looks built to evade a path or secret scanner. Read it from config or the environment openly.

**P2-9. The exam blinding is not "EXACTLY as the harness strips it".**

- Docstring 752-753: "expected", "provenance", "origin", any **nested "provenance"**.
- `blind()` (777-778) strips nested `origin` and `expected` too.

The prompts can differ from the harness's, so its offline replay misses.

---

## Single highest-leverage change

**Make `pinned.moments_vo` verify, not trust.** Each step below fails closed with a PinError.

1. Recompute `sha256` over a canonical serialisation of the gated content: VO intro, bridges and `after_clip`, title, caption, segment ids and their `approved_text`. Require it to equal `package_sha256`.
2. Require `edl_vo`, `title` and `caption` to be exactly the gated values.
3. Require a sealed `checks` record listing every hard gate, each `is True` with evidence present: vo_fidelity deterministic, vo_fidelity verdict, DUPLICATE, PRICE_NOW, context A/B/C, runtime and L-v 2.
4. Refuse any `moments_package` that is present but not a dict, and any replayed package.
5. Land R7 item 4 as a versioned release_auth inventory (v2) with these rows REQUIRED, so the same binding is re-checked on the final bytes.

This one change closes P0-1, P1-1 and most of Q3. It also makes every unverifiable gate internal at least observable at the render boundary.