# claude-sonnet-5-5 (effort high) 177 s stop_reason=end_turn usage=in 52110 / out 23074

# Review of the pp-selectid phase-2 STEP.diff

**Scope limit.** The diff contains docs, tests, proof drivers and the R7 patch for `pinned.py`. It does **not** contain `providers.py`, `package.py`, `vo_fidelity.py`, `context_integrity.py`, `moments.py`, `transcript_truth.py` or `package_pin.py`. I cannot verify any gate's actual code, so Q1–Q4 can only be assessed through the tests, the design text and the R7 patch. Where a finding depends on unseen code I say so.

Scores are my assurance that the property holds, given what the diff lets me verify. They are not a grade of the authors' code.

| Question | Score |
|---|---|
| Q1 fail-open | 35 |
| Q2 vendor separation / L-x | 45 |
| Q3 verbatim / model text | 45 |
| Q4 deterministic rules | 40 |
| Q5 tests and wiring | 50 |

## FINDINGS

**P0:** none provable from this diff. The closest case is P1-1, which is mitigated only by the first delivery being REVIEW ONLY (L-q).

### P1-1 (Q1/Q5): R7 trusts self-attested flags, and nothing binds them to the content
```
if not mp.get("checks", {}).get("vo_fidelity_ok") or not mp.get("checks", {}).get("context_integrity_ok"):
    raise PinError(...)
return {"intro": intro, "bridges": [...]}
```
- The check is a truthiness test on JSON booleans.
- `package_sha256` is copied into the EDL (`moments_package_sha256=mp["package_sha256"]`) but never recomputed against `edl_vo`, `title` or `caption`.
- `smoke_r7.py` line 888 sets these flags by hand (`pin["moments_package"]["checks"].update(vo_fidelity_ok=True, ...)`), which shows nothing else binds them.
- **Failing input:** a pin whose `edl_vo.intro` was edited after gating, with `checks = {"vo_fidelity_ok": "no", "context_integrity_ok": "no"}`. Both strings are truthy, so it is accepted.
- Related shape bugs:
  - `checks: null` raises `AttributeError`, not `PinError`.
  - A missing `title` raises `KeyError`.
  - `"moments_package": []` or a string fails `isinstance(mp, dict)` and is silently rendered as a plain pin, with no title and no caption.
- `smoke_r7` bad2 only flips `context_integrity_ok`. No test covers `vo_fidelity_ok=False`, a missing `checks`, a string flag, or a tampered `edl_vo` with a stale sha.

### P1-2 (Q1): the pin gate enforces 2 of the 7+ hard gates
- Missing from the R7 check: DUPLICATE, PRICE_NOW, runtime, coherence and law L-v 2 (second recognition pass).
- L-v 2 looks optional in the drivers: `--truth-dir` is optional (`ap.add_argument("--truth-dir", ...)`) and `truth_dir=truth_dir` defaults to `None`.
- Design §8 says speaker and second-pass checks exist "until they run on a package", i.e. they may not run.
- If `build()` treats `truth_dir=None` as "skip", a package ships with that gate having run on nothing. I cannot see `build()`, so this is unverified.
- R7 item 4 requires release authorisation to read `edl["moments_checks"]`, but the diff delivers no `release_auth` patch. That requirement is currently unenforced.

### P1-3 (Q2): Step A runs before the writer's vendor is known
- Design §4b step 1: Step A is "package-independent" and runs once, before ANGLES.
- Design §6 says Step A must use `context_verdict` "never the writer's vendor".
- If `angle_write` fails over mid-run, for example OpenAI to Anthropic on quota, the writer can land on the vendor that Step A already used.
- The router's `avoid_vendor` is per call, so I see no post-hoc check that every verdict's `backend` vendor differs from the final writer's vendor. That applies after failover and after a rewrite by a fallback writer.
- `test_gates.py`'s `Canned.call` ignores `avoid_vendor`. The test named `..._no_step_runs_on_the_writers_vendor` therefore only proves the argument is passed.
- The config test (lines 1556-1559) covers `fidelity_verdict`, `context_verdict` and `viewer_takeaway` only. It omits `coherence_verdict` and `exclusion_verdict`, and it checks only chain[0].

### P1-4 (Q1/Q4): the fidelity-verdict tests never exercise coverage
- The spec says "code decides: every claim 'yes'". Every test passes a non-empty claim list for the single line.
- Untested:
  - `{"claims": []}`, which is vacuously "all yes".
  - Two lines with claims for only one.
  - A title or caption with no claim.
- `words` must be a verbatim run, but no test covers a trivial run such as `"Bitcoin"` or `"the"`. The code proves provenance of words, not entailment.
- `test_production_facts_support_manifest_language` accepts the claim "clips from these channels; links below" on `"Links to every source are below"`. That text covers only half the claim, so the test blesses partial support.

### P1-5 (proof tooling): the primary pin can be destroyed
```
path, _ = package_pin.write_pin(pk, run, os.path.join(OUT, run))
if i: os.replace(path, path.replace("MOMENTS_PIN.json", f"MOMENTS_PIN_alt{i}.json"))
```
- The `.replace("MOMENTS_PIN.json", ...)` implies a fixed filename. If so:
  - At i=1, `write_pin` overwrites the primary `MOMENTS_PIN.json` with alt1's content.
  - `os.replace` then renames it, so the primary pin is gone.
  - Running `--want 3` leaves no `MOMENTS_PIN.json`, which is the file R7 says to render.

### P2 findings
- **Doc/test contradiction on angle size.** Design §4b says "backed by 4-8 cleared moments". `test_angles` accepts `["a","b","c"]` and rejects 2 with "3-8". Separately, the case `({"angles": []}, "angles")` asserts a substring that almost any message contains.
- **Design §4 says "regenerate once"; §4b says "rewrites up to 3 times".** One of them is stale.
- **`test_at_most_one_price_prediction_per_video` is one-sided.**
  - The three inputs force a single candidate set containing both predictions, so the correct output is an empty list and the loop body never runs.
  - It catches removal of the rule, but an over-strict "reject all predictions" implementation also passes. There is no positive case with exactly one prediction.
- **`test_a_short_clip_only_as_the_punchline` is conditional.** It is guarded by `if seg and any(... == "d")`, so it asserts nothing if `d` is not chosen.
- **Miner contract tests.**
  - `[mom([1,1])] * 13` is 13 overlapping copies, so "at most 12" is asserted on an input that also violates "overlaps"; the test is order-dependent.
  - `scores=...quotable=3.0` is rejected here, while L-l says an integral float is a harmless variation. This is plausibly intended for the miner, but the divergence is unexplained.
  - `True` as a score (bool is an int in Python) is untested.
- **`yield_table.py` hard-codes the gates column.**
  - `gates = "VO fidelity PASS, context integrity PASS"` prints for any package, not from `pk["checks"]`.
  - A universe that was "not run" is labelled DEFECT whenever the oracle has a line-up.
- **`ab_roles.py` doesn't do what its docstring says.**
  - It claims the judge "sees the source rows", but `judge_pair` passes only `m['text'][:400]`.
  - The prompt says "best 8" but the code uses `lst[:8]`, the first 8 unless pre-sorted.
  - Each pair gets one judge call with one coin-flip order. Doc §9's "better/worse" rests on n=1, yet it drives chain order.
  - `ab_verdicts` pops only top-level `expected` and `provenance`. `run_exam_record.blind()` also strips `origin`, nested provenance and the id, so the A/B leg is less blind than the exam leg.
- **Design §9 says "no rule loosened" (lines 147-153), but NAME, NUMBER and Step A were each made to accept more.** The cases are "NAME skips sentence-initial capitals", "number words ≤10 without a unit are counts" and the cleft "it" / generic "we" exemptions. Each is justified by measured false rejects, but the claim conflicts with LAW 20's tone. These now lean on the blind verdict and ATTRIBUTION. Concrete examples:
  - Segment "three analysts expect…" against a VO line "Five analysts expect…": NUMBER is skipped as a count.
  - A VO line starting "Saylor says…": NAME is skipped.
- **Q4 gaps (unverified code, but visible from the tests and doc).**
  - DUPLICATE is defined only for "the VO line right before a clip, and the title". The real incident (R8 item 2) was an intro that repeated `clip_03`. By that definition an intro repeating a non-adjacent clip passes, and the caption is uncovered. The test's intro duplicate is against the hook only.
  - A 5-token run can falsely reject an honest bridge, e.g. "Bitcoin ETF outflows hit" in both bridge and clip.
  - PRICE_NOW is exempted by a single history marker, tested only as "From the 2022 low…". A line like "since 2022, Bitcoin is at $126K" may pass if the exemption is line-wide.
  - A percent move such as "Bitcoin fell 5% today" has no current level to match, so it may falsely reject if moves are in scope.
- **R7 minor issues.**
  - `after_clip` accepts `True`, `1.0` and duplicate bridges after one clip.
  - A non-string `intro` is returned raw.
  - `_generate_vo_script` still runs before being overridden.
  - The hunk header counts check out (20→45).
  - `smoke_r7` mocks `validate_range`, `make_lock` and `sha256_file`, so it cannot catch a text/transcript mismatch, and the "plain pin unchanged" assertion depends on unseen `_generate_vo_script`.
- **Q3.** The tests set the title cite to `["h1"]` while the title names all channels, so correctness rests entirely on the fidelity gate. Nothing in the diff lets me verify that miner `reason`, angle sentences or trend text are kept out of clip text, title, caption or VO. The design says `reason` is "forensic only", but no test asserts it.

## Single highest-leverage change
Make the pin gate re-verify instead of trusting flags, and require all hard gates.

1. In `pinned.moments_vo` (or a shared `package_pin.verify()` that `release_auth` also calls):
   - recompute `package_sha256` over the intro, bridges, title, caption and segments;
   - require `checks[k] is True` for vo_fidelity, duplicate, price_now, context_integrity, coherence and `transcript_truth`;
   - raise `PinError` for any missing key, wrong type or `None`.
2. Add `test_gates` cases for empty or uncovered fidelity claims and for trivial support words, plus `smoke_r7` cases for a tampered `edl_vo`, string flags and missing `checks`.