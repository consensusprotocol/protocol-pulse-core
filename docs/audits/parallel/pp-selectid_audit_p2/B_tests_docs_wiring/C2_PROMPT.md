# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-p2
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## CLAUDE-FABLE-5-2 — CYCLE 1 OUTPUT
# claude-fable-5-2 (effort high) 465 s stop_reason=end_turn usage=in 52110 / out 44044

**Reviewer note:** I am Claude, not one of the three models named in the header; record that if the audit trail depends on which models reviewed.

**Scope limit:** the diff contains the design doc, the R7 patch text, tests and harnesses only. None of the reviewed modules (`providers.py`, `moments.py`, `package.py`, `vo_fidelity.py`, `context_integrity.py`, `package_pin.py`, `transcript_truth.py`, `moments_gate_adapter.py`, `model_providers.json`) is in it. For Q1–Q4 I can only verify what the tests pin and what the doc and patch state. The Flask/DB/load rules do not apply (no routes, no queries).

## Scores

| Q | Score | Basis |
|---|---|---|
| Q1 fail-open | 35 | The decision rules of the context gate and the fidelity verdict are tested well. `package.build`, which composes the gates, has no test, and the R7 wiring checks two self-reported flags. |
| Q2 vendor separation | 45 | The router honours `avoid_vendor` on a single call. Nothing covers writer failover, a rewrite by a fallback writer, precomputed step A, or coherence. |
| Q3 verbatim / model text | 40 | Mostly unverifiable here. One visible path (`pin["label"]` into the EDL) is unexplained. |
| Q4 deterministic rules | 30 | Of the rules asked about, only PRICE_NOW, `current_levels` and DUPLICATE have a test here; the other nine have none. |
| Q5 tests + R7 | 50 | The patch refuses the cases the smoke test exercises. It accepts several it does not exercise, and some assertions are vacuous. |

## FINDINGS

### P0

**P0-1. The pin's gate evidence is self-reported and bound to nothing (R7 patch).**
```
edl.update(title=mp["title"], caption=mp["caption"], moments_package_sha256=mp["package_sha256"],
           moments_checks=mp.get("checks"))
```
- The sha is copied, never recomputed. `smoke_r7.py` shows this: it runs `pin["moments_package"]["checks"].update(vo_fidelity_ok=True, context_integrity_ok=True)` after `to_pin`, and `build_edl` accepts the result.
- Nothing ties `pin["segments"]` to the package's segments.
- Failing input: change `segments[1].approved_text/start/end` to another sentence of the same video, or edit `edl_vo.intro` or `title`, and leave `checks` alone. The EDL builds and carries `moments_checks` saying both gates passed.
- R7 item 4 then tells release authorisation to trust `edl["moments_checks"]`. That conflicts with L-j ("on exactly the bytes") and with R7's own L-t line ("any change after the gates re-runs them").
- I cannot see whether a later stage re-verifies. R7 gives no patch for `release_auth` or `run_fresh`, and item 2 ("TONIGHT") runs before items 3–4 exist.

**P0-2. The wiring requires two of the hard gates; the second recognition pass is not requested.**
- `moments_vo` checks only `vo_fidelity_ok` and `context_integrity_ok`. Design §4b also lists DUPLICATE, PRICE_NOW, runtime and L-v 2 as hard. The diff does not show whether these are folded into the two flags.
- R7 item 3's production call is `package.build(router, mined["moments"], sources, ctx, delivered=…, optout=…)`, with no `truth_dir`.
- `proof_packages.py` shows `truth_dir=None` by default, with help text "run law L-v 2's second recognition pass".
- So, as specified, a package reaches the pin without L-v 2, and nothing downstream asks for evidence of it. Design §8 admits L-v 1/2 are open.

### P1

**P1-1. Truthiness instead of exact values (R7 patch).**
- Code: `if not mp.get("checks", {}).get("vo_fidelity_ok") or not …`.
- Failing input: `{"vo_fidelity_ok": "false", "context_integrity_ok": "uncertain"}` is accepted, as is `{"ok": false}` in either slot. L-l and L-j require exact `True` / `'PASS'`.
- `"checks": null` raises `AttributeError`, not `PinError`.

**P1-2. A malformed package silently becomes a plain pin (R7 patch).**
- `if isinstance(mp, dict):` means `"moments_package": []`, a string or `null` falls through to `_generate_vo_script`. A machine pin then renders as an ordinary pinned run with no `moments_checks` (M12).
- `v = mp.get("edl_vo") or {}` means a missing `edl_vo` yields `{"intro": None, "bridges": []}`. The gates judged a package with a VO; the render has none.
- The EDL keeps `"mode": "pinned"`. Nothing marks it as machine-decided for downstream gates that may assume a human approved a pin.

**P1-3. `package.build` has no test in this diff.**
- This is the composition Q1 asks about: three rewrites, plain-VO fallback, drop-and-repack, coherence, L-v 2, ranking.
- Only the live-model proof drivers call it. Coherence has no test at all.
- Arithmetic worth testing: `test_angles` accepts a 40 s line-up as in range. The plain VO in the fixtures is about 9 words (3.5 s at 2.6 words/s). 40 + 7.4 + 3.5 ≈ 51 s, below 60. Either the plain fallback cannot ship there or runtime is not applied to it; no test says which.

**P1-4. "Ran on nothing" inputs are untested (`test_gates.py`).**
- `Canned(fidelity_verdict=[{"claims": []}])`: "every claim yes" is vacuously true

## CLAUDE-OPUS-5-5 — CYCLE 1 OUTPUT
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

`tests/moments/

## CLAUDE-SONNET-5-5 — CYCLE 1 OUTPUT
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
  - At i=1, `write_pin` overwrites the primary `MO

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (xAI, medley key) 69 s usage=42710

**Q1: 82/100**  
From the diff only (MOMENTS_FIRST_DESIGN.md:105-110 "Both are hard. The package is never shipped failing.", 107-109 on regenerate-then-plain-VO or drop-and-repack; test_gates.py:1120-1126 "if not json ... CONTEXT_UNAVAILABLE", 1187-1189 "no verdict is a failure" with VERDICT_UNAVAILABLE; test_angles.py:1014-1015 PRICE_NOW violation added; pinned.py patch:352-353 `if not mp.get("checks", {}).get("vo_fidelity_ok") or not mp.get("checks", {}).get("context_integrity_ok"): raise PinError`; R7:296 "release authorisation must require both, from edl["moments_checks"]"; run_exam_record.py:814-815 exception -> error verdict): no package is returned when a hard gate fails, cannot run, or returns unreadable/partial/"uncertain". Model replies must be exact contract (test_moments.py:544-561 raises Rejected on missing keys, wrong types, fabricated ids, non-integer scores). Plain-VO path is only after fidelity reject + context pass and is labelled/ranked below; pinned refuses ungated package. Uncertain on whether *every* plain-VO path re-runs *all* deterministic rules on the final bytes (design mentions "by construction" but full package.build not shown). No exception is swallowed into a pass.  

**Q2: 93/100**  
From the diff only (providers/test_providers.py:1495-1504 `r.call("verdict", "p", avoid_vendor="openai")` then asserts backend != writer vendor, raises ProviderError if only writer vendor left; 1489-1493 failover only on Unavailable, down backend skipped for rest of run but full failure -> ProviderError never a pass; 1557-1559 config test enforces verdict chain first backend vendor != writer_first and every role >=2 backends; MOMENTS_FIRST_DESIGN.md:38-59 "every role calls providers.Router.call", "Verdict roles take avoid_vendor = the writer's vendor", "A back-end that cannot answer raises Unavailable", "never a pass"; test_providers.py:1569-1570 RoleModel maps only after valid reply; ab_roles.py:1404 pins per-role chains from config; R7:304-306 "Every role resolves through pipeline/model_providers.json, so no model name lives in code"; no vendor string appears in any new .py except inside test fixtures/config loading): verdict roles (fidelity_verdict, context_verdict, viewer_takeaway, coherence, exclusion) never run on writer's vendor even after failover/rewrite (avoid_vendor passed and config enforces separation). No role hard-codes a vendor/model outside model_providers.json. Contract violation does *not* silently failover (only Unavailable does; bad JSON/keys -> Rejected/ProviderError in caller).  

**Q3: 88/100**  
From the diff only (MOMENTS_FIRST_DESIGN.md:68-69 miner returns ids/scores only, "The reply contract is strict and never repaired"; 102 "every line cites moment ids"; 174-176 "code decides: every claim 'yes' with words that are a verbatim run of that segment; otherwise fail"; test_gates.py:1152-1154 "supported with verbatim words passes", 1162-1167 cross-clip needs both verbatim runs or VERDICT_UNVERIFIED, 1178-1184 uncertain/no/support-empty -> failure; 161-170 table of deterministic rules (QUOTE, NUMBER, NAME, ATTRIBUTION... all checked through canon); R7:278 "segments carry approved_text = the moments' exact words"; test_moments.py:623-628 PK.signoff uses credit set only; miner's "reason" and angle "reason" never reach VO/title/caption per forensic-only note line 80 and fidelity gate): no, model-wrote text (reason, angle sentence, verdict reason, trend brief raw post) cannot reach clip/VO/title/caption without fidelity gate. Clips are source sentences verbatim (approved_text + selection_lock preserved).  

**Q4: 75/100**  
From the diff only (vo_fidelity table lines 161-170; test_angles.py:1004-1015 concrete PRICE_NOW: `VF.price_now("Bitcoin ran from 16K to 126K", levels=[73000])` returns non-empty -> PRICE_NOW violation in title (false-pass prevented); `VF.price_now("Bitcoin holds $73,000", levels)` and "From the 2022 low..." return empty -> pass; test_gates.py:1152-1167 verbatim-run requirement for support, uncertain/no -> VERDICT_UNVERIFIED/VERDICT_NO; 148-153 "Measured false rejects, fixed (no rule loosened)": NAME now skips sentence-initial/Title-Case (9-case check passes both ways), NUMBER treats words <=10 without unit as counts, cleft-"it"/generic-"we" no longer REFERENT_OUTSIDE, cross-clip points allowed if both verbatim, production facts citable via manifest). No concrete false-PASS input survives the shown tests. Concrete false-REJECT (now fixed): title "Bitcoin ran from 16K to 126K" with history marker or current-level match; "It's not Bitcoin that's getting hacked" (cleft it). Uncertain on untested edge cases (e.g. complex negation in NUMBER or framing verb inside attributed quote) because full vo_fidelity.py implementation not in diff.  

**Q5: 78/100**  
From the diff only (all new test_*.py + smoke_r7.py + proof_*.py): tests fail for the right reasons (test_moments.py:559-561 `with self.assertRaises(S

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid PHASE 2 audit: cycle 1 consensus (synthesis by the pp-selectid session, 2026-11-12, ET)

The package is the repo's utils/cross_llm_audit.py build_audit_package, run on two chunks of the phase-2 diff (each
chunk under the 220,000-byte limit):

- A_core: pipeline/*.py and model_providers.json.
- B_tests_docs_wiring: tests, design doc, REQUESTS R7/R8.

The question is QUESTION.txt Q1-Q5.

Reviewers, each named in its file:

- claude-fable-5-2, claude-opus-5-5 and claude-sonnet-5-5 (effort high);
- grok-4.20-0309-reasoning (temperature 0, no tools);
- the tool's own gpt-4o leg, which FAILED with HTTP 429 (no credit) on both chunks.

Four reviewers per chunk.

Scores (Q1 / Q2 / Q3 / Q4 / Q5):

| chunk | fable | opus | sonnet | grok |
|---|---|---|---|---|
| A | 35/70/75/40/15 | (no table) | 38/66/58/40/30 | 72/88/93/55/45 |
| B | 35/45/40/30/50 | 35/45/30/40/50 | 35/45/45/40/50 | 82/93/88/75/78 |

Every finding below was checked against the code before its disposition. "Verified" means the defect is reproduced
from the code as written. "Refuted" gives the evidence.

The rule is consensus only. A finding raised by at least two reviewers (in either chunk) is implemented. A unique
finding is evaluated on its own evidence and either implemented or recorded with a reason.

## Unanimous or 3-4 of 4: implemented

### C1. The pin asserts the gates passed with literals
Raised by: A fable P0-1, opus P1-8, sonnet P1-4, grok P1; B fable P0-1, opus P0-1, sonnet P1-1.

**Verified:**
- package_pin.to_pin writes `"checks": {"vo_fidelity_ok": True, "context_integrity_ok": True}` and never reads
  `pk["checks"]`.
- R7's pinned.py patch tests these flags for truthiness only.
- The patch copies `package_sha256` and never recomputes it.

**Fix: a sealed GATE INVENTORY (the L-j pattern).** package.build writes `pk["gates"]` with a fixed set of rows:
- `vo_fidelity_deterministic`, `vo_fidelity_verdict`, `duplicate`, `price_now`, `runtime`;
- `context_a`, `context_b`, `context_c`;
- `exclusion`, `second_pass`, `coherence`.

Each row is exactly `"PASS"` with evidence: the back-end, n judged, and replayed false.

`package_sha256` is computed by one function, `package.seal()`, over a canonical serialisation of the gated bytes:
- segments (video_id, start, end, text, transcript_sha256);
- the VO intro, bridges and after_clip;
- the title and caption;
- the inventory.

Both package_pin.to_pin and the R7 patch recompute it:
- package_pin.to_pin refuses a package whose inventory is missing, not exactly PASS on every row, or replayed.
- R7 refuses any mismatch between the recomputed sha and the pin, and any pin VO, title or caption that differs from
  the sealed bytes.
- R7 also refuses a non-dict `moments_package`, `checks: null`, and a non-int or duplicate `after_clip`.

### C2. The blind fidelity verdict passes on `{"claims": []}` or partial coverage
Raised by: A fable P0-2, opus P0-1, sonnet P0-1; B fable P1-4, opus P1-11, sonnet P1-4.

**Verified:** vo_fidelity.ch

---

## THE CODE NOW: chunk B_tests_docs_wiring of the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_p2/B_tests_docs_wiring/STEP.diff (2100 lines)
```
   1 | diff --git a/docs/audits/MOMENTS_FIRST_DESIGN.md b/docs/audits/MOMENTS_FIRST_DESIGN.md
   2 | new file mode 100644
   3 | index 00000000..98a59c1a
   4 | --- /dev/null
   5 | +++ b/docs/audits/MOMENTS_FIRST_DESIGN.md
   6 | @@ -0,0 +1,236 @@
   7 | +# MOMENTS FIRST, THEN PACKAGE — design (pp-selectid phase 2, 2026-11-12)
   8 | +
   9 | +Orders and laws:
  10 | +- Orchestrator phase-2 order (01:55 ET Nov 12) and its addition (trend brief; "vo check needs to be real 100%").
  11 | +- Orchestrator notes 02:00 (model roles), 02:30 (laws L-s..L-w), 02:35 (PBX decisions), 02:45 (law L-x) and 03:00
  12 | +  (exam by pipeline_pp_tests; yield against the oracle).
  13 | +- Orchestrator review 03:40 (angle first), decisions 05:25 / 05:30 (the VO classification A / B / C / D, the no-paraphrase
  14 | +  styles, budgets), 05:35 / 06:00 / 06:22 (tonight's package; rulings 3-6).
  15 | +- The phase-2 audit, cycle 1 (docs/audits/parallel/pp-selectid_audit_p2/C1_CONSENSUS.md).
  16 | +- Laws L-n, L-o (amended), L-p, L-q, L-r (PIPELINE_LAWS.md).
  17 | +
  18 | +New modules only:
  19 | +- pipeline/providers.py and model_providers.json;
  20 | +- pipeline/trend_brief.py, moments.py, package.py, vo_fidelity.py, context_integrity.py;
  21 | +- pipeline/moments_gate_adapter.py (the exam adapter).
  22 | +
  23 | +No existing pipeline file is edited. The wiring is an exact patch in docs/audits/parallel/pp-selectid_REQUESTS.md (R7).
  24 | +
  25 | +## 1. The cycle
  26 | +
  27 | +```
  28 | +ingest (pipeline_pp_ingest: new uploads -> store -> word pass)            -> moment ledger (append-only, pp.moment/1)
  29 | +trend_brief: local_baseline (free) + one live-search call (SHADOW, weight 0)
  30 | +moments.mine: pre-filter (code) -> one batched mining pass by id (role "mine") -> eligibility per moment -> rank (code)
  31 | +package.build: usable (code) -> step A once per moment (stored) -> ANGLES (role angle_write)
  32 | +               -> per angle: line-up (code, runtime + R4) -> exclusion + L-v 2 start in the background
  33 | +               -> write (host style, then quote-led) -> cheap gates (code) -> fidelity verdict || context B0 / B / C
  34 | +               -> coherence -> sealed gate inventory -> pp.package/1 -> package_pin -> MOMENTS_PIN.json
  35 | +integrator: pinned path (R7) -> word pass -> sentence lock -> render -> gates -> release authorisation over BOTH files
  36 | +            + the title + caption (L-t) -> Telegram REVIEW ONLY (first one)
  37 | +```
  38 | +
  39 | +## 2. Provider interface (law L-x)
  40 | +
  41 | +- Every role calls `providers.Router.call(role, prompt, ...)`; transcription calls `Router.transcribe(role, wav)`. The
  42 | +  chain of back-ends per role lives only in pipeline/model_providers.json, as does every model name, model family,
  43 | +  price and base URL.
  44 | +- Back-ends:
  45 | +  - local: gemma3:27b through story_semantics.LocalLLM; only with a started LocalLLM under the GPU0 lease, law L-r;
  46 | +  - OpenAI chat/completions;
  47 | +  - Anthropic Messages (streaming);
  48 | +  - xAI chat/completions at temperature 0 with the attempt's seed;
  49 | +  - xAI Responses with x_search / web_search (the trend brief);
  50 | +  - Heimdall (OpenAI-compatible);
  51 | +  - transcription: OpenAI diarised and ElevenLabs Scribe (role "transcribe", law L-v 2).
  52 | +- **Unavailable** (credit, auth, 429 or 5xx after backoff, transport, no lease): the chain moves on and the back-end
  53 | +  is down for the rest of the run. **RequestRejected** (400 / 413 / 422, over the local context, an empty reply): the
  54 | +  chain moves on for THIS call only. A role whose whole chain fails raises ProviderError: a failed role, never a pass.
  55 | +- Verdicts take `avoid_vendor` and `avoid_family`: the vendors and model families of EVERY reply whose text they judge
  56 | +  (the angle and every writer attempt). Generator and judge are always different models.
  57 | +- Every exchange is recorded by (role, back-end, prompt, max_tokens, seed, system), or by the audio's sha256. A recording
  58 | +  served in a live run is `cached`; one served offline is `replayed`, and it is never deliverable (L-j).
  59 | +  `Router.reject(reply)` deletes the recording of a reply its caller found out of contract, so it is asked again.
  60 | +- Spend: each paid call RESERVES its upper bound (every prompt character a token + the output cap, at the config's
  61 | +  upper-bound price) under the ledger lock BEFORE it runs, and settles after. An unreadable ledger stops every paid
  62 | +  call. A free back-end is never stopped.
  63 | +- Heimdall's GET /credits feeds the 90 % tripwire: a NOTIFY, never a halt (PBX 02:45).
  64 | +- The order per role is in the config; the blind A/B per role (tests/providers/ab_roles.py, both judge orders, a judge
  65 | +  outside the compared vendors and families) re-decides it. The integrator runs the local legs.
  66 | +
  67 | +## 3. Mining (moments.py)
  68 | +
  69 | +- Pre-filter (code): sources in the window (new since the last cycle plus a recent window); not opted out
  70 | +  (pipeline/optout.json, PBX 02:35); eligible as a source. Rows are punctuated, injection-free, never an ad read, and
  71 | +  within one sentence of a Bitcoin mention. Rows go round-robin across videos, on-screen-capable videos first, in
  72 | +  context-budget tables.
  73 | +- One batched pass: the model answers ids only, `{"moments": [{"range", "scores": 7 axes 0-5, "names_person",
  74 | +  "risk", "topics", "reason"}]}`. The reply contract is strict and never repaired (L-l); anything else is re-asked.
  75 | +  Each moment is then judged by eligibility on its own (a moment is its own statement).
  76 | +- Ranking (code, L-u): hook_first_2s + quotable + surprising_fact + stance + stakes + stands_alone, minus 2 x
  77 | +  contempt_outrage, minus soft-risk penalties, plus a trend weight that is 0 in SHADOW. Hard risks never rank.
  78 | +- The miner's own risk flags are never the exclusion gate: `moments.exclusion_verdict` runs in production on every
  79 | +  segment of a line-up, never on the miner's model (avoid_model), after a deterministic ad-read screen of the moment and
  80 | +  the sentence before it (audit p2 C3).
  81 | +- Durations come from word timing only. The `reason` is forensic only.
  82 | +
  83 | +## 4. Packaging (package.py): angle first
  84 | +
  85 | +The first package (03:25) passed every safety gate and failed the product (orchestrator 03:40). package.build is angle
  86 | +first, inside the orchestrator's budgets (05:25 item 5, 05:30): at most 3 angles x 2 writes, stopped at the first
  87 | +package with coherence >= 4; per package <= 6 minutes and <= $1.50 (tonight: 76-144 s and $0.25-0.59 per full gate run).
  88 | +
  89 | +1. **usable** (code): on screen eligible (L-e); no hard exclusion (L-u); not overlapping a moment delivered in 24 h, by
  90 | +   video and time (L-p, audit p2 U2); not opted out; <= 20 s per source video (L-u); time-sensitive words only from a
  91 | +   source <= 24 h old (L-v 3); no MEASURED speaker change (an unmeasured one is a candidate; L-v 2 decides).
  92 | +2. **Step A once per moment** (context only, package-independent), stored on the moment (a ledger keyed by moment and
  93 | +   the step-A prompt), never recomputed; never on the writers' vendor or family.
  94 | +3. **ANGLES** (role angle_write): up to 3 one-sentence angles, each backed by 3-8 cleared moments (the prompt asks for
  95 | +   5-8) from >= 3 channels; an unknown id is rejected, never dropped. One re-ask on an out-of-contract reply.
  96 | +4. **Line-up per angle** (code): the hook, then 2-3 clips from distinct channels in the proposer's order; at most one
  97 | +   price prediction (L-u); a clip under 8 s only last (the punchline); the length that BOTH the runtime (60-70 s) and
  98 | +   the moments R4 allow (section 4c). Exclusion and the L-v 2 second pass start in the background.
  99 | +5. **Writer** (role angle_write), in the renderer's order (hook -> intro -> clip 1 -> bridge -> ...):
 100 | +   - style "host" first: tease a clip with a question or topic, never saying what its speaker thinks; hand off with a
 101 | +     hedge-matched attribution ONLY for a VERIFIED speaker; land the host's own takeaway after a clip;
 102 | +   - style "quote" (quote-led) second: show + topic, at most four exact words quoted;
 103 | +   - never a restatement of a clip's claim (DUPLICATE checks every line against every clip);
 104 | +   - word budgets from R4 and the runtime; ONE title and ONE caption (L-t); the sign-off is code (L-a);
 105 | +   - the plain VO ("Next, <show> on Bitcoin.") remains as the last resort, ranked below every written VO.
 106 | +6. **Cheap gates first** (code, no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4. A failure goes back
 107 | +   to the writer with the exact violations; no paid verdict is spent on it.
 108 | +7. **Paid gates, concurrently**: the classifying fidelity verdict (section 5) and context integrity B0 / B / C (section
 109 | +   6). A VO-dependent context failure goes back to the writer; any other context failure ends the angle.
 110 | +8. **Exclusion and L-v 2** results are collected; a moment that fails either is dropped and the angle re-lined.
 111 | +9. **COHERENCE** (blind, never the vendor / family of the text): the through-line, each clip 1-5, the VO's point 1-5.
 112 | +   Below 4, or no through-line ('None.', 'n/a', under 4 words), moves to the next angle.
 113 | +10. **The sealed gate inventory** (package.inventory; package_pin.REQUIRED_GATES): one row per hard gate, each exactly
 114 | +    "PASS" with who measured it and "replayed": false. package_pin seals the gated bytes and the inventory
 115 | +    (package_pin.seal) and refuses anything else (audit p2 C1).
 116 | +
 117 | +## 4c. Length: the runtime and R4
 118 | +
 119 | +- runtime = segments' word spans + every spoken VO word INCLUDING the sign-off at WPS + FIXED_S (audit p2 M4: the
 120 | +  sign-off was subtracted twice, about 6.9 s short). FIXED_S = TAIL_S (14.30 s, measured) - an 18-word sign-off at WPS.
 121 | +  WPS = 2.6 is an ASSUMPTION until a moments-first render measures it.
 122 | +- R4 for moments (orchestrator 06:00 ruling 4; the integrator's edl_rules._r4_moments, main tree a5ec0f17): VO (intro
 123 | +  + lines, words / 2.5 + 1 s pre-roll each) <= 40 % of the TOTAL runtime; one VO line per slot: after the hook, after
 124 | +  each clip, after the last clip (the takeaway); word caps (intro 30, bridge 20). package.r4 mirrors it and
 125 | +  package.content_range / budgets derive the line-up length and word budgets from it.
 126 | +
 127 | +## 5. VO fidelity (vo_fidelity.py): "real 100%", and a host with a point of view
 128 | +
 129 | +(a) Deterministic, on every VO line, the title and the caption, through canon (L-k):
 130 | +
 131 | +| rule | what it checks |
 132 | +|---|---|
 133 | +| NEEDS_SOURCE | a line with a fact (a number that is not a production count, a name, a quote, an attribution, a time word) cites a segment |
 134 | +| ATTRIBUTION | "<X> says / thinks ...", "<X>: ...", "according to <X>" bind X to a cited segment: by its VERIFIED speaker, or by its show; a person-like show with a speech verb needs the speaker verified (L-v 1); a pronoun or generic subject ("she says", "analysts say") is unbound |
 135 | +| HEDGE | the attribution verb matches the clip's own hedge: "thinks" for "I think", "feels" for "I feel like" (05:25 item 2) |
 136 | +| NUMBER | value and unit, in the sentences of the attribution that governs it (the nearest in its sentence), else the cited ones |
 137 | +| NAME | every capitalised token that is not an English word (the system word list) is in the cited sentences or production metadata, wherever it stands (Title Case and sentence starts included) |
 138 | +| QUOTE | double or single quotes, a verbatim run of the governing segment |
 139 | +| RELATION | agree / answer / rebut / echo / goes further / similarly ... only when every party (cited segments, named shows, "both") is in one source video |
 140 | +| FRAMING | destroys / slams / exposes / admits / confirms / caught / torches / debunks / bombshell ... only if the source says it |
 141 | +| IMPERATIVE | no financial imperative or advice (you should buy, time to buy, don't sell); "short-term", "sell-off" are not verbs |
 142 | +| TIME | today, overnight, this month, just hit / just set ... only if a cited segment says it (L-v 3) |
 143 | +| PRICE_NOW | on ANY line, a price level is today's (a level the universe states as current, from present-tense sentences with no forecast or history word), or reads as history (a marker before it, no present tense), or as a forecast |
 144 | +
 145 | +(b) The blind CLASSIFYING verdict (role fidelity_verdict, never the vendor or family of the text; 05:25 items 1-2):
 146 | +every sentence of every line belongs to a claim whose `words` are the line's own, classified as
 147 | +- **A attribution** / **B fact**: "yes" only with supports that are verbatim runs (>= 3 words) of the LINE'S OWN cited
 148 | +  segments, same polarity and the same or weaker certainty; a named person only when the segment's speaker is
 149 | +  verified;
 150 | +- **C production**: supported by the manifest (the credited shows, the clip count, links below, the show and date);
 151 | +- **D host commentary**: allowed without clip support when its five tests are all "no" (a checkable fact, a speaker's
 152 | +  view or relation, a financial imperative or prediction, an accusation, sounding like a speaker), AND none of the rule
 153 | +  features (a number, a name, a quote, an attribution, a price, a time word, an imperative, a relation or framing word)
 154 | +  appears in its words; otherwise it is judged strict (NOT_COMMENTARY).
 155 | +Code decides; an uncovered sentence (VERDICT_INCOMPLETE), "no", "uncertain" or an unverifiable support fails.
 156 | +
 157 | +(c) The exam is pipeline_pp_tests'. The gate runs under its harness through pipeline/moments_gate_adapter.py; a gate
 158 | +that could not MEASURE raises GateNotMeasured, the harness's ERROR (audit p2 M5), never a free rejection.
 159 | +
 160 | +## 6. Context integrity (context_integrity.py, law L-s)
 161 | +
 162 | +- Window per moment: AT LEAST 90 s before (back to the question it answers, when one ends within 180 s) and AT LEAST
 163 | +  60 s after, in whole sentences (audit p2 C11). Every sentence is escaped and the selection marked after escaping;
 164 | +  a window over 12,000 characters is CONTEXT_TOO_LONG, never cut.
 165 | +- A (context only; package hidden): speaker change inside; the view; referents (inside, and whether resolving them
 166 | +  differently changes the assertion); conditions; retraction (a withdrawal, reversal, correction or material limit, not
 167 | +  a consistent elaboration: ruling 6); time_ok (no default); the proposition; certainty; who speaks ("host" verified
 168 | +  only with verbatim evidence of the excerpt: L-v 1).
 169 | +- B0 (the clips alone) and B (the package as the viewer meets it, in the renderer's order): what the viewer concludes
 170 | +  each speaker asserts, INCLUDING what the title, caption or VO attributes to that speaker (host commentary attributed
 171 | +  to nobody is the host's); certainty; polarity; a relation for EVERY pair of clips (audit p2 C5).
 172 | +- C: entailment between A and the CLIP'S OWN WORDS as heard (ruling 5), same polarity, stronger certainty, with the
 173 | +  words that justify a failure.
 174 | +- PASS (code) only if all hold: no speaker change; own sincere; referents inside, or outside without changing the
 175 | +  assertion (ruling 3); conditions inside; no retraction; certainty known; entailed; same polarity; no false relation;
 176 | +  no "uncertain" anywhere. A failure that blames the video must quote the video's own words (`raising_words`,
 177 | +  `added_by` naming the speaker's show); one that blames the context must quote the context's own words outside the
 178 | +  clip (`dropped_limit`). Unquoted, it is a NOTE (rulings 3 and 5; E-FAIL-PS17). STRONGER is also a note when the clip
 179 | +  alone already sounds certain.
 180 | +- Repair is dropping the moment (the law also permits extending by whole locked sentences; not built). The VO never
 181 | +  carries the missing context.
 182 | +- After every change to these rules, the exam's context-integrity MUST-FAIL cases are re-run (tests/package/
 183 | +  ci_mustfail_check.py): 41/41 rejected tonight after each ruling.
 184 | +
 185 | +## 7. Trend brief (trend_brief.py)
 186 | +
 187 | +- A closed taxonomy of 18 Bitcoin topics, each with our own label and pattern.
 188 | +- `local_baseline`: the share of partner channels per topic in the last 24 h. Free.
 189 | +- One live-search call per cycle (xAI Responses, x_search + web_search, < 6k out), cached per 4 h cycle.
 190 | +  - The reply is validated into the taxonomy; strict.
 191 | +  - Raw post text never leaves the module or enters a prompt.
 192 | +  - Persons may boost only a moment whose VERIFIED speaker is that person.
 193 | +  - Failure means no boost.
 194 | +- SHADOW: TREND_WEIGHT = 0 until it measurably helps. When enabled, the weight is capped at ~10-15%.
 195 | +- Titles never take trend phrasing (L-t).
 196 | +
 197 | +## 8. Open items (named, not hidden)
 198 | +
 199 | +- **The phase-2 code is under its audit's cycle 2** (cycle 1: C1_CONSENSUS.md, implemented). Until it passes, the code
 200 | +  is not committed; tonight's package, its pin and its proof are.
 201 | +- **The runtime estimate's WPS (2.6) and FIXED_S (7.4 s).** Assumptions until a moments-first render measures them.
 202 | +- **Speaker verification (L-v 1)** rests on step A's "host" with verbatim evidence; diarisation (L-v 2) proves one
 203 | +  speaker inside a clip, never who. Tonight no clip's speaker was verified, so no VO line names a person.
 204 | +- **The exam's full run** (both directions, the false-reject rate on must-pass cases) waits for the Heimdall / local legs
 205 | +  (orchestrator 05:30); the context-integrity must-fail half ran 41/41 after every ruling.
 206 | +- **The yield sweep** of the other 9 universes is postponed (orchestrator 05:30).
 207 | +- **The trend brief's search call** has never run; it is shadow and not on the critical path.
 208 | +
 209 | +## 9. Measured so far (2026-11-12, saved universes; CPU and API only)
 210 | +
 211 | +- **Mining, gpt-6.1-sol, word-timed sources** (the 10 saved universes): every call accepted at the first attempt.
 212 | +
 213 | +| universe | moments mined | usable on screen |
 214 | +|---|---|---|
 215 | +| fresh_20261106_213852 | 12 | 9 |
 216 | +| fresh_20261107_065702 | 12 | 11 |
 217 | +| fresh_20261107_080503 | 12 | 10 |
 218 | +| fresh_20261110_093150 | 24 | 16 |
 219 | +| fresh_20261111_190259 | 71 | 62 |
 220 | +| fresh_20261111_192645 | 70 | 65 |
 221 | +| fresh_20261111_213954 | 69 | 61 |
 222 | +| fresh_20261112_001448 | 59 | 52 |
 223 | +| fresh_20261112_013452 | 59 | 54 |
 224 | +| fresh_20261112_050611 (tonight) | 62 | 58 |
 225 | +
 226 | +- **Mining A/B** (blind, judged by claude-opus-5-5, tests/providers/ab/mine_fresh_20261112_050611.json):
 227 | +
 228 | +| back-end | calls accepted | latency | spend (upper bound) | blind verdict |
 229 | +|---|---|---|---|---|
 230 | +| gpt-6.1-sol | 6 / 6 | 300.5 s | $2.17 | better |
 231 | +| Heimdall qwen3.8-27b | 5 / 6 | 2,067 s | $1.63 | worse |
 232 | +
 233 | +  local gemma3:27b: the integrator's leg (GPU0 lease).
 234 | +- **Law L-v 2 on tonight's first package**: the second pass (gpt-4o-transcribe-diarize) agreed on every number,
 235 | +  name and negation of all 4 segments, with one speaker inside each.
 236 | +- **Tonight's package** (fresh_20261112_050611; the orchestrator's 06:00 package with the line fixes of attempt 4,
 237 | +  approved 06:22): every one of the 12 gates exactly PASS (attempt 9), pinned and sealed
 238 | +  (tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json); 9 gate attempts, $3.46; the deployed factory's own
 239 | +  R4 (moments) on its EDL: VO 30.93 % of an estimated 64.01 s.
 240 | +- **Context integrity, the exam's 41 must-fail cases**, after each of rulings 3, 5 and 6: 41/41 rejected
 241 | +  (tests/package/exam/ci_mustfail_*.json; claude-opus-5-5, about $0.01 a call).
 242 | +
 243 | diff --git a/tests/moments/proof_moments.py b/tests/moments/proof_moments.py
 244 | new file mode 100644
 245 | index 00000000..38c7c6c7
 246 | --- /dev/null
 247 | +++ b/tests/moments/proof_moments.py
 248 | @@ -0,0 +1,96 @@
 249 | +#!/usr/bin/env python3
 250 | +"""Phase-2 proof driver, step 1 (MINE) on saved universes. CPU only; read-only inputs (the run's universe, the store's
 251 | +records by the recorded sha, as tests/select_by_id/proof_saved_runs.py reads them); every model reply recorded under
 252 | +tests/moments/fixtures/replies (offline replay); spend in tests/moments/proof/SPEND.json with the phase-2 $40 guard.
 253 | +
 254 | +Mining scope here: the videos with a sentence-ready word record in the store (on-screen capable, law L-e). A
 255 | +caption-only video can be mined in production after the cycle's word pass (pipeline_pp_ingest); in this CPU replay it is
 256 | +reported as awaiting the word pass, never mined from caption timing for the screen.
 257 | +
 258 | +Usage: python3 tests/moments/proof_moments.py --runs fresh_20261112_050611 [--replay] [--recent-h 72]
 259 | +"""
 260 | +import argparse
 261 | +import json
 262 | +import os
 263 | +import sys
 264 | +import time
 265 | +from datetime import datetime, timezone
 266 | +
 267 | +HERE = os.path.dirname(os.path.abspath(__file__))
 268 | +REPO = os.path.dirname(os.path.dirname(HERE))
 269 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 270 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 271 | +import eligibility as E  # noqa: E402
 272 | +import moments as M  # noqa: E402
 273 | +import providers as P  # noqa: E402
 274 | +import proof_saved_runs as PS  # noqa: E402
 275 | +import trend_brief as TB  # noqa: E402
 276 | +
 277 | +REPLIES = os.path.join(HERE, "fixtures", "replies")
 278 | +OUT = os.path.join(HERE, "proof")
 279 | +SPEND = os.path.join(OUT, "SPEND.json")
 280 | +LIMIT_USD = 64.28                  # the phase-2 guard: $40 from 01:55 ET Nov 12, raised at 05:30 by $25 from
 281 | +                                   # $39.28 (orchestrator amendment 05:30: $25, a package for tonight first)
 282 | +
 283 | +
 284 | +def universe_sources(run):
 285 | +    """(word Sources of the run's universe, caption-only video ids, ctx) from the saved run, read-only."""
 286 | +    saved = json.load(open(os.path.join(PS.RUNS, run, "TOPIC_SELECTION.json")))
 287 | +    started = datetime.fromisoformat(saved["started"])
 288 | +    assert started.tzinfo is not None
 289 | +    now = started.astimezone(timezone.utc)
 290 | +    ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
 291 | +    words, captions = [], []
 292 | +    for u in saved.get("universe") or []:
 293 | +        if not u.get("transcript_sha256") or u["video_id"] in E.V2F_VIDEO_IDS:
 294 | +            continue
 295 | +        w = PS.word_source(u, ctx)
 296 | +        if w is not None:
 297 | +            words.append(w)
 298 | +        else:
 299 | +            captions.append(u["video_id"])
 300 | +    return words, captions, ctx, saved
 301 | +
 302 | +
 303 | +def run_one(run, router, recent_h, log=print):
 304 | +    words, captions, ctx, saved = universe_sources(run)
 305 | +    t0 = time.time()
 306 | +    base = TB.local_baseline(words, ctx, hours=24.0)
 307 | +    out = M.mine(router, words, ctx, TB.TOPICS, since=None, optout=M.optout_ids(), log=log, cycle=f"proof:{run}",
 308 | +                 recent_h=recent_h)
 309 | +    for m in out["moments"]:
 310 | +        m["trend"] = TB.trend_match(m, None, base)
 311 | +    rec = {"run": run, "now": ctx.now.isoformat(), "seconds": round(time.time() - t0, 1),
 312 | +           "scope": {"word_sources": len(words), "caption_only_awaiting_word_pass": len(captions)},
 313 | +           "baseline": base, "rows": out["rows"], "sources_in_window": out["sources"], "skipped": out["skipped"],
 314 | +           "calls": [{k: v for k, v in c.items() if k != "attempts"} | {"attempts": [
 315 | +               {k2: v2 for k2, v2 in a.items() if k2 in ("attempt", "rejected", "declined", "model_error", "accepted",
 316 | +                                                        "meta", "prompt_sha256")} for a in c["attempts"]]}
 317 | +               for c in out["calls"]],
 318 | +           "moments": out["moments"]}
 319 | +    os.makedirs(os.path.join(OUT, run), exist_ok=True)
 320 | +    json.dump(rec, open(os.path.join(OUT, run, "moments.json"), "w"), indent=1, default=str)
 321 | +    usable = [m for m in out["moments"] if m["on_screen_ok"] and not m["excluded"]]
 322 | +    log(f"{run}: {len(words)} word sources ({len(captions)} caption-only), rows {out['rows']}, calls "
 323 | +        f"{[c['status'] for c in out['calls']]}, moments {len(out['moments'])}, usable on screen {len(usable)} "
 324 | +        f"({rec['seconds']} s)")
 325 | +    return rec
 326 | +
 327 | +
 328 | +def main(argv=None):
 329 | +    ap = argparse.ArgumentParser()
 330 | +    ap.add_argument("--runs", nargs="+", required=True)
 331 | +    ap.add_argument("--replay", action="store_true")
 332 | +    ap.add_argument("--recent-h", type=float, default=72.0, help="the first cycle of a saved universe: its whole 72 h")
 333 | +    ap.add_argument("--chain", nargs="*", help="pin the mine role's chain (config names), e.g. for the A/B")
 334 | +    a = ap.parse_args(argv)
 335 | +    router = P.Router(env_path=PS.ENV, record_dir=REPLIES, replay=a.replay, spend_path=SPEND, limit_usd=LIMIT_USD,
 336 | +                      chains={"mine": a.chain} if a.chain else None)
 337 | +    for run in a.runs:
 338 | +        run_one(run, router, a.recent_h)
 339 | +    if router.notices:
 340 | +        print("NOTICES:", router.notices)
 341 | +
 342 | +
 343 | +if __name__ == "__main__":
 344 | +    main()
 345 | diff --git a/tests/moments/test_moments.py b/tests/moments/test_moments.py
 346 | new file mode 100644
 347 | index 00000000..4535455d
 348 | --- /dev/null
 349 | +++ b/tests/moments/test_moments.py
 350 | @@ -0,0 +1,142 @@
 351 | +#!/usr/bin/env python3
 352 | +"""pipeline/moments.py + pipeline/package.py (deterministic parts): the miner's reply contract is strict and never
 353 | +repaired; ranking is deterministic with contempt as a penalty; ad reads and opted-out channels are never offered; the
 354 | +packager's usable() keeps L-u (<= 20 s per source video), L-v 1 / L-v 3 and novelty by overlap; the sign-off names
 355 | +exactly the credit set (L-a). The line-up rules are in tests/package/test_angles.py. Offline: no model call."""
 356 | +import json
 357 | +import os
 358 | +import sys
 359 | +import unittest
 360 | +from datetime import datetime, timedelta, timezone
 361 | +
 362 | +HERE = os.path.dirname(os.path.abspath(__file__))
 363 | +REPO = os.path.dirname(os.path.dirname(HERE))
 364 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 365 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 366 | +import eligibility as E  # noqa: E402
 367 | +import moments as M  # noqa: E402
 368 | +import package as PK  # noqa: E402
 369 | +import select_by_id as SB  # noqa: E402
 370 | +import trend_brief as TB  # noqa: E402
 371 | +from test_eligibility import CID, HOOK_TXT, CLIP_TXT, CLIP2_TXT, NOW, REG, source  # noqa: E402
 372 | +
 373 | +
 374 | +def reply(**kw):
 375 | +    return json.dumps(kw)
 376 | +
 377 | +
 378 | +SCORES = {"hook_first_2s": 4, "quotable": 3, "surprising_fact": 2, "stance": 3, "stakes": 2, "stands_alone": 4,
 379 | +          "contempt_outrage": 0}
 380 | +
 381 | +
 382 | +def mom(rng, **kw):
 383 | +    d = {"range": rng, "scores": dict(SCORES), "names_person": False, "risk": [], "topics": ["price_action"],
 384 | +         "reason": "a clean statement"}
 385 | +    d.update(kw)
 386 | +    return d
 387 | +
 388 | +
 389 | +class TestMineContract(unittest.TestCase):
 390 | +    def setUp(self):
 391 | +        self.a = source([HOOK_TXT, CLIP_TXT], channel="DataDash", vid="A")
 392 | +        self.b = source([CLIP2_TXT], channel="Natalie Brunell", vid="B")
 393 | +        self.t = SB.Table([(self.a, 0, False), (self.a, 1, False), (self.b, 0, False)])
 394 | +
 395 | +    def check(self, obj):
 396 | +        return M.check_moments(obj, self.t, TB.TOPICS)
 397 | +
 398 | +    def test_a_valid_reply_and_an_empty_one(self):
 399 | +        got = self.check({"moments": [mom([1, 2]), mom([3, 3])]})
 400 | +        self.assertEqual([(sp.source.video_id, sp.k0, sp.k1) for sp, _ in got], [("A", 0, 1), ("B", 0, 0)])
 401 | +        self.assertEqual(self.check({"moments": []}), [])
 402 | +
 403 | +    def test_rejected_never_repaired(self):
 404 | +        bad = [({"moments": [mom([1, 3])]}, "cross-source"),
 405 | +               ({"moments": [mom([1, 2]), mom([2, 2])]}, "overlaps"),
 406 | +               ({"moments": [mom([9, 9])]}, "fabricated"),
 407 | +               ({"moments": [mom([1, 1], scores=dict(SCORES, quotable=6))]}, "integer 0-5"),
 408 | +               ({"moments": [mom([1, 1], scores=dict(SCORES, quotable=3.0))]}, "integer 0-5"),
 409 | +               ({"moments": [mom([1, 1], scores={k: v for k, v in SCORES.items() if k != "stakes"})]}, "exactly"),
 410 | +               ({"moments": [mom([1, 1], risk=["libel"])]}, "'risk'"),
 411 | +               ({"moments": [mom([1, 1], topics=["altcoins"])]}, "'topics'"),
 412 | +               ({"moments": [mom([1, 1], topics=[])]}, "'topics'"),
 413 | +               ({"moments": [mom([1, 1], reason="")]}, "'reason'"),
 414 | +               ({"moments": [mom([1, 1], names_person="no")]}, "'names_person'"),
 415 | +               ({"moments": [dict(mom([1, 1]), headline="Bitcoin finds support")]}, "keys must be exactly"),
 416 | +               ({"moments": [mom([1, 1])] * 13}, "at most 12")]
 417 | +        for obj, why in bad:
 418 | +            with self.assertRaises(SB.Rejected) as cm:
 419 | +                self.check(obj)
 420 | +            self.assertIn(why, str(cm.exception), obj)
 421 | +
 422 | +    def test_ranking_is_deterministic_and_contempt_is_a_penalty(self):
 423 | +        calm = {"scores": dict(SCORES), "risk": [], "topics": ["price_action"]}
 424 | +        angry = {"scores": dict(SCORES, contempt_outrage=4), "risk": [], "topics": ["price_action"]}
 425 | +        pred = {"scores": dict(SCORES), "risk": ["price_prediction"], "topics": ["price_action"]}
 426 | +        self.assertGreater(M.rank_score(calm), M.rank_score(angry))
 427 | +        self.assertGreater(M.rank_score(calm), M.rank_score(pred))
 428 | +        self.assertEqual(M.rank_score(calm, trend={"price_action": 1.0}), M.rank_score(calm))   # SHADOW: weight 0
 429 | +
 430 | +    def test_ad_reads_are_never_offered_and_the_optout_registry_is_honoured(self):
 431 | +        ad = source(["This episode is brought to you by Swan Bitcoin, use code PULSE for a discount on Bitcoin.",
 432 | +                     HOOK_TXT], channel="DataDash", vid="AD")
 433 | +        self.assertNotIn(0, M.candidate_rows(ad))
 434 | +        self.assertIn(1, M.candidate_rows(ad))
 435 | +        ctx = E.Context(NOW, REG)
 436 | +        keep, skipped = M.window_sources([self.a, self.b], ctx, optout=frozenset({CID["DataDash"]}))
 437 | +        self.assertEqual([s.video_id for s in keep], ["B"])
 438 | +        self.assertIn("opted out", skipped["A"])
 439 | +
 440 | +
 441 | +def pm(mid, channel, dur, rank=10.0, hook=True, clip=True, risk=(), topics=("price_action",), vid=None):
 442 | +    return {"moment_id": mid, "channel_id": channel, "channel_name": channel, "video_id": vid or f"v{mid}",
 443 | +            "duration_s": dur, "rank_score": rank, "scores": dict(SCORES), "risk": list(risk), "topics": list(topics),
 444 | +            "eligibility": {"hook": {"ok": hook}, "clip": {"ok": clip}}, "on_screen_ok": True, "excluded": [],
 445 | +            "published_at": (NOW - timedelta(hours=6)).isoformat(), "speaker": {"turn_change_inside": None},
 446 | +            "text": "Bitcoin x.", "sentences": [0, 0], "words": [0, 1], "start": 0.0, "end": dur,
 447 | +            "transcript_sha256": "s"}
 448 | +
 449 | +
 450 | +class TestPackageUsable(unittest.TestCase):
 451 | +    def test_over_20_s_unmeasured_excluded_and_stale_time_words_are_unusable(self):
 452 | +        ctx = E.Context(NOW, REG)
 453 | +        long_ = pm("l", "A", 21.0)
 454 | +        unmeasured = dict(pm("u", "B", 10.0), duration_s=None)
 455 | +        stale = dict(pm("s", "C", 12.0, risk=("time_sensitive",)), published_at=(NOW - timedelta(hours=30)).isoformat())
 456 | +        fresh = pm("f", "D", 12.0, risk=("time_sensitive",))
 457 | +        excluded = dict(pm("x", "E", 12.0), excluded=["accusation"])
 458 | +        changed = dict(pm("t", "F", 12.0), speaker={"turn_change_inside": True})
 459 | +        ok, why = PK.usable([long_, unmeasured, stale, fresh, excluded, changed], ctx)
 460 | +        self.assertEqual([m["moment_id"] for m in ok], ["f"])     # an UNMEASURED speaker (None) is a candidate only:
 461 | +        self.assertIn("20.0 s", why["l"])                          # L-v 2 measures it at packaging and the pin refuses
 462 | +        self.assertIn("L-v 3", why["s"])                           # an unmeasured second pass (audit p2 M11)
 463 | +        self.assertIn("accusation", why["x"])
 464 | +        self.assertIn("L-v 1", why["t"])
 465 | +
 466 | +    def test_novelty_by_overlap_not_by_id(self):
 467 | +        ctx = E.Context(NOW, REG)
 468 | +        m = dict(pm("new-id", "A", 10.0, vid="V"), start=100.0, end=110.0)
 469 | +        ok, why = PK.usable([m], ctx, delivered=[{"video_id": "V", "start": 105.0, "end": 115.0}])
 470 | +        self.assertEqual(ok, [])
 471 | +        self.assertIn("delivered", why["new-id"])
 472 | +        ok, _ = PK.usable([m], ctx, delivered=[{"video_id": "V", "start": 111.0, "end": 115.0}, "other-id"])
 473 | +        self.assertEqual([x["moment_id"] for x in ok], ["new-id"])
 474 | +
 475 | +    def test_the_signoff_names_exactly_the_credit_set_hook_first(self):
 476 | +        ctx = E.Context(NOW, REG)
 477 | +        segs = [pm("h", CID["DataDash"], 10.0), pm("c1", CID["Natalie Brunell"], 15.0),
 478 | +                pm("c2", CID["Yahoo Finance"], 15.0)]
 479 | +        self.assertEqual(PK.signoff(segs, ctx), "Clips today from DataDash, Natalie Brunell, and Yahoo Finance. "
 480 | +                                                "Go follow them for more. Links are below.")
 481 | +
 482 | +    def test_the_plain_title_never_cuts_a_name(self):
 483 | +        ctx = E.Context(NOW, REG)
 484 | +        segs = [pm("h", "Averyveryverylongchannelname One", 10.0), pm("c1", "Averyveryverylongchannelname Two", 15.0),
 485 | +                pm("c2", "Averyveryverylongchannelname Three", 15.0)]
 486 | +        title = PK.plain_vo(segs, ctx)[2]["text"]
 487 | +        self.assertLessEqual(len(title), 70)
 488 | +        self.assertTrue(title.endswith(("and others", "Two", "One")), title)
 489 | +
 490 | +
 491 | +if __name__ == "__main__":
 492 | +    unittest.main()
 493 | diff --git a/tests/package/ci_mustfail_check.py b/tests/package/ci_mustfail_check.py
 494 | new file mode 100644
 495 | index 00000000..0d499ebb
 496 | --- /dev/null
 497 | +++ b/tests/package/ci_mustfail_check.py
 498 | @@ -0,0 +1,90 @@
 499 | +#!/usr/bin/env python3
 500 | +"""Orchestrator 06:00 ruling 3: the two narrowed context-integrity rules (REFERENT_OUTSIDE needs no antecedent or
 501 | +completing predicate in the selection AND a changed assertion; STRONGER needs the VO / title words that raise the
 502 | +certainty, cited verbatim, and a clip that does not already sound that certain alone) must not let ANY must-fail case
 503 | +pass. This runs the exam's context-integrity MUST-FAIL cases (pipeline_pp_tests corpora, format v1) through the SAME
 504 | +gate (pipeline/moments_gate_adapter.context_integrity), each case blinded exactly as the harness blinds it
 505 | +(moments_exam.py:117-129: top-level "expected" and "origin" removed, "provenance" at any depth, the id salted). The
 506 | +answers are read only to SELECT the must-fail cases and, after the gate answered, to count. Concurrent (threads).
 507 | +
 508 | +Usage: python3 tests/package/ci_mustfail_check.py --corpus <corpora dir> [--chain ROLE=BACKEND ...] [--jobs 8]
 509 | +Writes tests/package/exam/ci_mustfail_<stamp>.json."""
 510 | +import argparse
 511 | +import copy
 512 | +import hashlib
 513 | +import json
 514 | +import os
 515 | +import sys
 516 | +import time
 517 | +from concurrent.futures import ThreadPoolExecutor
 518 | +
 519 | +HERE = os.path.dirname(os.path.abspath(__file__))
 520 | +REPO = os.path.dirname(os.path.dirname(HERE))
 521 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 522 | +import moments_gate_adapter as A  # noqa: E402
 523 | +import providers as P  # noqa: E402
 524 | +
 525 | +
 526 | +def blind(case, salt):
 527 | +    def strip(x):
 528 | +        if isinstance(x, dict):
 529 | +            return {k: strip(v) for k, v in x.items() if k != "provenance"}
 530 | +        if isinstance(x, list):
 531 | +            return [strip(v) for v in x]
 532 | +        return x
 533 | +    out = strip(copy.deepcopy({k: v for k, v in case.items() if k not in ("expected", "origin")}))
 534 | +    out["id"] = "case-" + hashlib.sha256((salt + case["id"]).encode()).hexdigest()[:12]
 535 | +    return out
 536 | +
 537 | +
 538 | +def main(argv=None):
 539 | +    ap = argparse.ArgumentParser()
 540 | +    ap.add_argument("--corpus", required=True)
 541 | +    ap.add_argument("--chain", nargs="*", default=[])
 542 | +    ap.add_argument("--jobs", type=int, default=8)
 543 | +    a = ap.parse_args(argv)
 544 | +    chains = {}
 545 | +    for x in a.chain:
 546 | +        role, backend = x.split("=", 1)
 547 | +        chains.setdefault(role, []).append(backend)
 548 | +    A._router = P.Router(env_path=A.ENV, record_dir=A.RECORD, spend_path=A.SPEND,
 549 | +                         limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")), chains=chains or None)
 550 | +    d = os.path.join(a.corpus, "context_integrity")
 551 | +    cases = [json.load(open(os.path.join(d, f))) for f in sorted(os.listdir(d))
 552 | +             if f.endswith(".json") and f != "INDEX.json"]
 553 | +    must_fail = [c for c in cases if c["expected"]["verdict"] == "fail"]
 554 | +    salt = os.urandom(8).hex()
 555 | +    t0, led0 = time.time(), json.load(open(A.SPEND))["usd_estimate"]
 556 | +
 557 | +    def run(c):
 558 | +        try:
 559 | +            v = A.context_integrity(blind(c, salt))
 560 | +            return {"verdict": v["verdict"], "why": v["why"][:300]}
 561 | +        except A.GateNotMeasured as e:
 562 | +            return {"verdict": "ERROR", "why": f"not measured: {str(e)[:240]}"}
 563 | +        except P.SpendLimit as e:
 564 | +            return {"verdict": "ERROR", "why": f"spend guard: {e}"}
 565 | +        except Exception as e:                             # noqa: BLE001 (a crash is an ERROR, never a verdict)
 566 | +            return {"verdict": "ERROR", "why": f"{type(e).__name__}: {str(e)[:240]}"}
 567 | +
 568 | +    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
 569 | +        got = list(ex.map(run, must_fail))
 570 | +    rows = [{"id": c["id"], "class": c["expected"].get("class"), **g} for c, g in zip(must_fail, got)]
 571 | +    rejected = sum(r["verdict"] in ("fail", "uncertain") for r in rows)
 572 | +    passed = [r for r in rows if r["verdict"] == "pass"]
 573 | +    errors = [r for r in rows if r["verdict"] == "ERROR"]
 574 | +    led1 = json.load(open(A.SPEND))["usd_estimate"]
 575 | +    rep = {"corpus": d, "must_fail": len(rows), "rejected": rejected, "passed": len(passed), "errors": len(errors),
 576 | +           "chains": chains, "seconds": round(time.time() - t0, 1), "usd": round(led1 - led0, 4), "rows": rows}
 577 | +    os.makedirs(os.path.join(HERE, "exam"), exist_ok=True)
 578 | +    out = os.path.join(HERE, "exam", f"ci_mustfail_{time.strftime('%Y%m%dT%H%M%S')}.json")
 579 | +    json.dump(rep, open(out, "w"), indent=1)
 580 | +    print(f"CONTEXT INTEGRITY MUST-FAIL: {rejected}/{len(rows)} rejected; {len(passed)} PASSED (a miss); "
 581 | +          f"{len(errors)} ERROR (not measured) | {rep['seconds']} s, ${rep['usd']} | {out}")
 582 | +    for r in passed + errors:
 583 | +        print(f"  {r['verdict']}: {r['id']} ({r['class']}): {r['why'][:200]}")
 584 | +    return 0 if rejected == len(rows) else 1
 585 | +
 586 | +
 587 | +if __name__ == "__main__":
 588 | +    sys.exit(main())
 589 | diff --git a/tests/package/proof_packages.py b/tests/package/proof_packages.py
 590 | new file mode 100644
 591 | index 00000000..8c4be000
 592 | --- /dev/null
 593 | +++ b/tests/package/proof_packages.py
 594 | @@ -0,0 +1,92 @@
 595 | +#!/usr/bin/env python3
 596 | +"""Phase-2 proof driver, step 2 (PACKAGE) on saved universes: reads tests/moments/proof/<run>/moments.json, builds the
 597 | +package through both gates (pipeline/package.py), records every reply (tests/package/fixtures/replies), spends into the
 598 | +phase-2 ledger (tests/moments/proof/SPEND.json, $40 guard), writes tests/package/proof/<run>/package.json and prints the
 599 | +package in full. CPU only; read-only inputs.
 600 | +
 601 | +Usage: python3 tests/package/proof_packages.py --runs fresh_20261112_050611 [--replay]
 602 | +"""
 603 | +import argparse
 604 | +import json
 605 | +import os
 606 | +import sys
 607 | +import time
 608 | +
 609 | +HERE = os.path.dirname(os.path.abspath(__file__))
 610 | +REPO = os.path.dirname(os.path.dirname(HERE))
 611 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 612 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 613 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 614 | +import moments as M  # noqa: E402
 615 | +import package as PK  # noqa: E402
 616 | +import proof_moments as PM  # noqa: E402
 617 | +import providers as P  # noqa: E402
 618 | +
 619 | +REPLIES = os.path.join(HERE, "fixtures", "replies")
 620 | +OUT = os.path.join(HERE, "proof")
 621 | +
 622 | +
 623 | +def show(pk):
 624 | +    coh = (pk.get("checks") or {}).get("coherence") or {}
 625 | +    gates = "; ".join(f"{k} {v['status']}" for k, v in (pk.get("gates") or {}).items())
 626 | +    lines = [f"ANGLE: {pk['angle']}", f"VO {pk['vo_kind']} | runtime estimate {pk['runtime_s_estimate']} s "
 627 | +             f"({pk['runtime_note']})",
 628 | +             f"COHERENCE (blind, {coh.get('backend')}): through-line \"{coh.get('through_line')}\" | clips "
 629 | +             f"{coh.get('clips')} | VO point {coh.get('vo_point')}",
 630 | +             f"TITLE: {pk['title']}", f"CAPTION: {pk['caption']}", f"VO intro: {pk['vo']['intro']}"]
 631 | +    after = dict(zip(pk["vo"].get("bridges_after_clip") or [], pk["vo"]["bridges"]))
 632 | +    for i, s in enumerate(pk["segments"]):
 633 | +        lines.append(f"  [{s['label']}] {s['channel']} {s['video_id']} {s['start']:.2f}-{s['end']:.2f} "
 634 | +                     f"({s['duration_s']} s): \"{s['text']}\"")
 635 | +        if after.get(i):
 636 | +            lines.append(f"VO bridge: {after[i]}")
 637 | +    lines.append(f"VO sign-off: {pk['vo']['signoff']}")
 638 | +    lines.append(f"models: {pk.get('models')}")
 639 | +    lines.append(f"gates: {gates}")
 640 | +    return "\n".join(lines)
 641 | +
 642 | +
 643 | +def run_one(run, router, log=print, work_dir=None, max_angles=PK.MAX_ANGLES, writes=PK.WRITES):
 644 | +    rec_m = json.load(open(os.path.join(PM.OUT, run, "moments.json")))
 645 | +    words, captions, ctx, saved = PM.universe_sources(run)
 646 | +    sources = {s.video_id: s for s in words}
 647 | +    t0 = time.time()
 648 | +    spend = lambda: json.load(open(PM.SPEND))["usd_estimate"]
 649 | +    res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log,
 650 | +                   max_angles=max_angles, writes=writes, work_dir=work_dir,
 651 | +                   store=os.path.join(OUT, run, "step_a.json"), spend=spend)
 652 | +    res["seconds"] = round(time.time() - t0, 1)
 653 | +    res["run"] = run
 654 | +    os.makedirs(os.path.join(OUT, run), exist_ok=True)
 655 | +    json.dump(res, open(os.path.join(OUT, run, "package.json"), "w"), indent=1, default=str)
 656 | +    if res["package"]:
 657 | +        import package_pin
 658 | +        for i, pk in enumerate(res["packages"]):
 659 | +            name = "MOMENTS_PIN.json" if i == 0 else f"MOMENTS_PIN_alt{i}.json"    # never overwrites the top pin
 660 | +            path, _ = package_pin.write_pin(pk, run, os.path.join(OUT, run), name=name)
 661 | +            log(f"{run}: {'PACKAGE' if i == 0 else f'ALTERNATIVE {i}'} ({res['seconds']} s, ${res.get('usd')}) pin "
 662 | +                f"{path}\n" + show(pk))
 663 | +    else:
 664 | +        log(f"{run}: no package ({res.get('why_none')}); usable moments {res['usable']}; tried "
 665 | +            f"{json.dumps(res['tried'], default=str)[:1500]}")
 666 | +    return res
 667 | +
 668 | +
 669 | +def main(argv=None):
 670 | +    ap = argparse.ArgumentParser()
 671 | +    ap.add_argument("--runs", nargs="+", required=True)
 672 | +    ap.add_argument("--replay", action="store_true")
 673 | +    ap.add_argument("--work-dir", required=True, help="law L-v 2's audio windows (required: no second pass, no package)")
 674 | +    ap.add_argument("--max-angles", type=int, default=PK.MAX_ANGLES)
 675 | +    ap.add_argument("--writes", type=int, default=PK.WRITES)
 676 | +    a = ap.parse_args(argv)
 677 | +    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, replay=a.replay, spend_path=PM.SPEND,
 678 | +                      limit_usd=PM.LIMIT_USD)
 679 | +    for run in a.runs:
 680 | +        run_one(run, router, work_dir=a.work_dir, max_angles=a.max_angles, writes=a.writes)
 681 | +    if router.notices:
 682 | +        print("NOTICES:", router.notices)
 683 | +
 684 | +
 685 | +if __name__ == "__main__":
 686 | +    main()
 687 | diff --git a/tests/package/run_exam_record.py b/tests/package/run_exam_record.py
 688 | new file mode 100644
 689 | index 00000000..ebe73193
 690 | --- /dev/null
 691 | +++ b/tests/package/run_exam_record.py
 692 | @@ -0,0 +1,81 @@
 693 | +#!/usr/bin/env python3
 694 | +"""Record this session's gate replies for pipeline_pp_tests' exam (tests/adversarial/corpora, format v1), so that the
 695 | +exam's harness, which forbids network connections, replays them offline (PP_GATES_REPLAY=1).
 696 | +
 697 | +Each case is stripped EXACTLY as the harness strips it before the gate sees it (moments_exam.py:117-129): top-level
 698 | +"expected" and "origin", "provenance" at any depth, and the real id (replaced by case-<12 hex>). This script never reads an answer. It writes
 699 | +nothing but the recorded replies (pipeline/moments_gate_adapter.py's record dir) and a verdict log keyed by the
 700 | +blinded id. The confusion table is the harness's to compute.
 701 | +
 702 | +Usage: python3 tests/package/run_exam_record.py --corpus /home/ultron/worktrees/pp-tests/tests/adversarial/corpora
 703 | +       [--chain ROLE=BACKEND ...]   (pin a leg of the L-x A/B; default: pipeline/model_providers.json)
 704 | +"""
 705 | +import argparse
 706 | +import hashlib
 707 | +import json
 708 | +import os
 709 | +import sys
 710 | +
 711 | +HERE = os.path.dirname(os.path.abspath(__file__))
 712 | +REPO = os.path.dirname(os.path.dirname(HERE))
 713 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 714 | +import moments_gate_adapter as A  # noqa: E402
 715 | +import providers as P  # noqa: E402
 716 | +
 717 | +GATES = (("context_integrity", "context_integrity"), ("vo_fidelity", "vo_fidelity"), ("exclusions", "exclusion"))
 718 | +
 719 | +
 720 | +def blind(case, salt=""):
 721 | +    """Exactly the harness's blinding (moments_exam.py:117-129): top-level "expected" and "origin" removed,
 722 | +    "provenance" removed at any depth, the id replaced (the gate's prompts never carry the id)."""
 723 | +    import copy
 724 | +
 725 | +    def strip(x):
 726 | +        if isinstance(x, dict):
 727 | +            return {k: strip(v) for k, v in x.items() if k != "provenance"}
 728 | +        if isinstance(x, list):
 729 | +            return [strip(v) for v in x]
 730 | +        return x
 731 | +    c = strip(copy.deepcopy({k: v for k, v in case.items() if k not in ("expected", "origin")}))
 732 | +    c["id"] = "case-" + hashlib.sha256((salt + str(case.get("id"))).encode()).hexdigest()[:12]
 733 | +    return c
 734 | +
 735 | +
 736 | +def main(argv=None):
 737 | +    ap = argparse.ArgumentParser()
 738 | +    ap.add_argument("--corpus", required=True)
 739 | +    ap.add_argument("--chain", nargs="*", default=[], help="ROLE=BACKEND (config names), one per role to pin")
 740 | +    ap.add_argument("--out", default=os.path.join(HERE, "exam"))
 741 | +    a = ap.parse_args(argv)
 742 | +    chains = {}
 743 | +    for x in a.chain:
 744 | +        role, backend = x.split("=", 1)
 745 | +        chains.setdefault(role, []).append(backend)
 746 | +    A._router = P.Router(env_path=A.ENV, record_dir=A.RECORD, spend_path=A.SPEND, limit_usd=40.0, chains=chains or None)
 747 | +    os.makedirs(a.out, exist_ok=True)
 748 | +    log = []
 749 | +    for corpus, gate in GATES:
 750 | +        d = os.path.join(a.corpus, corpus)
 751 | +        if not os.path.isdir(d):
 752 | +            continue
 753 | +        for f in sorted(x for x in os.listdir(d) if x.endswith(".json") and x != "INDEX.json"):
 754 | +            case = blind(json.load(open(os.path.join(d, f))))
 755 | +            try:
 756 | +                v = getattr(A, gate)(case)
 757 | +            except P.SpendLimit as e:
 758 | +                log.append({"gate": gate, "case": case["id"], "stopped": str(e)})
 759 | +                print("SPEND GUARD:", e)
 760 | +                json.dump(log, open(os.path.join(a.out, "record_log.json"), "w"), indent=1)
 761 | +                return 2
 762 | +            except Exception as e:                       # a gate that could not measure is an ERROR (audit p2 M5)
 763 | +                v = {"verdict": "error", "why": f"{type(e).__name__}: {str(e)[:200]}"}
 764 | +            log.append({"gate": gate, "case": case["id"], "verdict": v["verdict"]})
 765 | +            print(gate, case["id"], v["verdict"], flush=True)
 766 | +    json.dump(log, open(os.path.join(a.out, "record_log.json"), "w"), indent=1)
 767 | +    if A._router.notices:
 768 | +        print("NOTICES:", A._router.notices)
 769 | +    return 0
 770 | +
 771 | +
 772 | +if __name__ == "__main__":
 773 | +    sys.exit(main())
 774 | diff --git a/tests/package/run_given_package.py b/tests/package/run_given_package.py
 775 | new file mode 100644
 776 | index 00000000..0ccbc554
 777 | --- /dev/null
 778 | +++ b/tests/package/run_given_package.py
 779 | @@ -0,0 +1,233 @@
 780 | +#!/usr/bin/env python3
 781 | +"""ORCHESTRATOR ORDER 05:35 ET: tonight's package as WRITTEN BY THE ORCHESTRATOR, run through the corrected gates as
 782 | +attempt 1 (no writer loop). Gates:
 783 | +
 784 | +- VO fidelity: deterministic, then the blind CLASSIFYING verdict (A attribution / B fact / C production / D host
 785 | +  commentary; orchestrator 05:25 items 1-2);
 786 | +- context integrity: step A on each moment's own context (package-independent), then B and C on the package;
 787 | +- the factory's own EDL rule R4 (edl_rules.rule_r4) and the 60-70 s runtime arithmetic;
 788 | +- DUPLICATE;
 789 | +- the exclusion verdict per moment (L-u);
 790 | +- law L-v 2's second recognition pass per segment (the router's transcribe chain) on the saved audio windows;
 791 | +- the blind coherence verdict.
 792 | +
 793 | +Independent calls run concurrently (05:25 item 5). Vendor rule: the VO's author is the orchestrator (assumed a Claude
 794 | +session), so every verdict on the VO avoids vendor anthropic and family claude. Step A and the exclusion verdicts judge
 795 | +only the source moments and use the cheapest capable model (claude-opus-5-5, $0.01 a call measured).
 796 | +
 797 | +Usage: python3 tests/package/run_given_package.py [--variant r4|full] [--bridge-alt] [--takeaway-alt]
 798 | +Writes tests/package/proof/fresh_20261112_050611/given_<variant>.json and prints every line's class and verdict."""
 799 | +import argparse
 800 | +import json
 801 | +import os
 802 | +import sys
 803 | +import time
 804 | +from concurrent.futures import ThreadPoolExecutor
 805 | +
 806 | +HERE = os.path.dirname(os.path.abspath(__file__))
 807 | +REPO = os.path.dirname(os.path.dirname(HERE))
 808 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 809 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 810 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 811 | +import context_integrity as CI  # noqa: E402
 812 | +import moments as M  # noqa: E402
 813 | +import package as PK  # noqa: E402
 814 | +import proof_moments as PM  # noqa: E402
 815 | +import providers as P  # noqa: E402
 816 | +import transcript_truth as TT  # noqa: E402
 817 | +import vo_fidelity as VF  # noqa: E402
 818 | +
 819 | +RUN = "fresh_20261112_050611"
 820 | +SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
 821 | +AUDIO = os.path.join(SCRATCH, "lv2")
 822 | +REPLIES = os.path.join(HERE, "fixtures", "replies")
 823 | +OUT = os.path.join(HERE, "proof", RUN)
 824 | +HOOK, WBD, LIVERA = "3b3050f4afd6f3c011e7", "876662b7dc4e961d47e1", "b0b787f8a62d97d81dbb"
 825 | +AUTHOR = {"vendor": "anthropic", "family": "claude"}      # the orchestrator's text: verdicts avoid its vendor / family
 826 | +CHAINS = {"context_verdict": ["anthropic:claude-opus-5-5", "xai:grok-4.20-0309-reasoning",
 827 | +                              "heimdall:deepseek/deepseek-v4.1-flash"],
 828 | +          "viewer_takeaway": ["anthropic:claude-opus-5-5", "xai:grok-4.20-0309-reasoning",
 829 | +                              "heimdall:deepseek/deepseek-v4.1-flash"],
 830 | +          "fidelity_verdict": ["xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash"],
 831 | +          "coherence_verdict": ["xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash"],
 832 | +          "exclusion_verdict": ["anthropic:claude-opus-5-5", "xai:grok-4.20-0309-reasoning"],
 833 | +          "transcribe": ["openai_stt:gpt-4o-transcribe-diarize", "elevenlabs_stt:scribe_v1"]}
 834 | +
 835 | +
 836 | +NATALIE = "5e38ec62aa36eae80132"
 837 | +
 838 | +
 839 | +def fields(variant, bridge_alt, takeaway_alt, bridge_text=None, caption_text=None):
 840 | +    """The orchestrator's lines. The renderer plays hook -> intro VO -> clip_01 -> bridge(after 1) -> clip_02 ->
 841 | +    bridge(after 2) -> shout-out (render16.py:306-334, render_vertical.py:853-880). 'r4' / 'full': the 05:35 package
 842 | +    (Livera); 'v0600': the 06:00 package (orchestrator decisions 06:00 item 5: Natalie Brunell last, three VO lines)."""
 843 | +    if variant == "v0600":
 844 | +        vo2 = bridge_text or ("Here's Natalie Brunell on what that takes." if bridge_alt else
 845 | +                              "So what does a system with no one in charge actually have to get right? Here's Natalie "
 846 | +                              "Brunell.")
 847 | +        vo3 = "No ruler. Just rules. That's the whole idea." if takeaway_alt else \
 848 | +            "No ruler. Just rules nobody gets to bend. That's the whole idea, and it's the part people miss."
 849 | +        ids = [HOOK, WBD, NATALIE]
 850 | +        return {"order": ids, "after": [1, 2],
 851 | +                "intro": {"text": "Nobody is in charge of Bitcoin. That's not a flaw. That's the design. So the next "
 852 | +                                  "time you hear about a hack, ask what actually got hacked.", "cites": [HOOK, WBD]},
 853 | +                "bridges": [{"text": vo2, "cites": [NATALIE]}, {"text": vo3, "cites": []}],
 854 | +                "title": {"text": "Nobody is in charge of Bitcoin.", "cites": ids},
 855 | +                "caption": {"text": caption_text or "no authority. three voices on why that is the point.", "cites": ids},
 856 | +                "type": "moments", "angle": "Nobody is in charge of Bitcoin, and that is the point."}
 857 | +    ids = [HOOK, WBD, LIVERA]
 858 | +    hand_off = bridge_text or ("And Stephan Livera thinks it's still underpriced." if bridge_alt else
 859 | +                               "And Stephan Livera thinks the market still hasn't priced that in.")
 860 | +    takeaway = "No ruler. No back door. That's the whole idea." if takeaway_alt else \
 861 | +        "No ruler. No back door. That's what you're actually buying into."
 862 | +    intro = "Nobody is in charge of Bitcoin. That's not a flaw. That's the design."
 863 | +    if variant == "full":
 864 | +        intro += " So the next time you hear about a hack, ask what actually got hacked."
 865 | +        bridges = [{"text": hand_off, "cites": [LIVERA]}, {"text": takeaway, "cites": []}]
 866 | +    else:
 867 | +        bridges = [{"text": hand_off, "cites": [LIVERA]}]
 868 | +    return {"order": ids, "after": [1, 2] if variant == "full" else [1], "intro": {"text": intro, "cites": ids},
 869 | +            "bridges": bridges, "title": {"text": "Nobody is in charge of Bitcoin", "cites": ids},
 870 | +            "caption": {"text": caption_text or "no authority. no back door. three voices on why that is the point.",
 871 | +                        "cites": ids},
 872 | +            "type": "moments", "angle": "Nobody is in charge of Bitcoin, and that is the point."}
 873 | +
 874 | +
 875 | +def main(argv=None):
 876 | +    ap = argparse.ArgumentParser()
 877 | +    ap.add_argument("--variant", choices=("r4", "full", "v0600"), default="v0600")
 878 | +    ap.add_argument("--cheap-only", action="store_true", help="the free gates only (no model call)")
 879 | +    ap.add_argument("--bridge-alt", action="store_true")
 880 | +    ap.add_argument("--takeaway-alt", action="store_true")
 881 | +    ap.add_argument("--bridge-text", help="a line fix for the bridge (the order allows 2 per line)")
 882 | +    ap.add_argument("--caption-text", help="a line fix for the caption")
 883 | +    ap.add_argument("--intro-text", help="a line fix for VO 1 (the intro)")
 884 | +    ap.add_argument("--takeaway-text", help="a line fix for VO 3 (the takeaway)")
 885 | +    ap.add_argument("--tag", default="", help="suffix of the output file")
 886 | +    a = ap.parse_args(argv)
 887 | +    t_start = time.time()
 888 | +    led0 = json.load(open(PM.SPEND))["usd_estimate"]
 889 | +    router = P.Router(env_path=P.ENV_PATH, record_dir=REPLIES, spend_path=PM.SPEND, limit_usd=PM.LIMIT_USD,
 890 | +                      chains=CHAINS)
 891 | +    rec_m = json.load(open(os.path.join(PM.OUT, RUN, "moments.json")))
 892 | +    by_id = {m["moment_id"]: m for m in rec_m["moments"]}
 893 | +    words, captions, ctx, saved = PM.universe_sources(RUN)
 894 | +    sources = {s.video_id: s for s in words}
 895 | +    f = fields(a.variant, a.bridge_alt, a.takeaway_alt, a.bridge_text, a.caption_text)
 896 | +    if a.intro_text:
 897 | +        f["intro"] = dict(f["intro"], text=a.intro_text)
 898 | +    if a.takeaway_text and len(f["bridges"]) > 1:
 899 | +        f["bridges"][-1] = dict(f["bridges"][-1], text=a.takeaway_text)
 900 | +    pk = PK.assemble(f["order"], by_id, f, ctx, f"written by the orchestrator, variant {a.variant}")
 901 | +    pk["vo"]["bridges_after_clip"] = list(f["after"])           # a takeaway may follow the last clip (06:00 ruling 4)
 902 | +    levels = PK.current_levels(sources.values(), ctx)
 903 | +    contexts = CI.contexts_from_sources(pk, sources, ctx.now)
 904 | +    log = []
 905 | +    say = lambda s: (log.append(s), print(s, flush=True))
 906 | +    say(f"PACKAGE {a.variant}: runtime estimate {pk['runtime_s_estimate']} s ({pk['runtime_note']})")
 907 | +    r4_ok, r4_why = PK.r4(pk)
 908 | +    say(f"R4: {r4_why}")
 909 | +    say(f"VO: intro {len(pk['vo']['intro'].split())} words; bridges {[len(b.split()) for b in pk['vo']['bridges']]} "
 910 | +        f"after clips {pk['vo']['bridges_after_clip']}; sign-off: {pk['vo']['signoff']!r}")
 911 | +    if a.cheap_only:
 912 | +        v, det, dup, rt_ok, r4r = PK.cheap_checks(pk, {}, PK.current_levels(sources.values(), ctx), ctx.now)
 913 | +        say(f"CHEAP GATES (speakers unverified until step A): {json.dumps(v)}")
 914 | +        return 0
 915 | +    # 1. step A (package-independent; the cheapest capable model) -> verified speakers for the fidelity check
 916 | +    t0 = time.time()
 917 | +    a_by, a_backend = CI.step_a(router, contexts, writer_vendor=None)
 918 | +    say(f"step A ({a_backend}, {time.time() - t0:.0f} s): " + "; ".join(
 919 | +        f"{lb}: fails {CI.a_failures(x) or 'none'}, speaker {x.get('speaker_is')} verified {x.get('speaker_verified')}"
 920 | +        f" ({x.get('speaker_evidence')!r:.60})" for lb, x in a_by.items()))
 921 | +    segs_v = {}
 922 | +    for sg in pk["segments"]:
 923 | +        ver = a_by[sg["label"]].get("speaker_verified")
 924 | +        segs_v[sg["moment_id"]] = {"show": sg["channel"], "speaker": sg["channel"] if ver else None,
 925 | +                                   "names": [sg["channel"]] if ver else [], "video_id": sg["video_id"], "text": sg["text"]}
 926 | +    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
 927 | +    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": ctx.now.strftime("%Y-%m-%d")}
 928 | +    # 2. everything else that is independent, concurrently
 929 | +    t0 = time.time()
 930 | +    wavs = {sg["video_id"]: next((os.path.join(AUDIO, x) for x in sorted(os.listdir(AUDIO))
 931 | +                                  if x.startswith(sg["video_id"] + "_") and x.endswith(".wav")), None)
 932 | +            for sg in pk["segments"]}
 933 | +
 934 | +    def truth(sg):
 935 | +        w = wavs.get(sg["video_id"])
 936 | +        ws = int(os.path.basename(w).split("_")[-2]) / 1000.0 if w else None
 937 | +        return TT.verify_segment(router, sg["video_id"], float(sg["start"]), float(sg["end"]), sg["text"], AUDIO,
 938 | +                                 wav=w, wav_start=ws)
 939 | +
 940 | +    def exclusion(sg):
 941 | +        src = sources[sg["video_id"]]
 942 | +        a_, b_ = CI.window(src, sg["k0"], sg["k1"])
 943 | +        sent = lambda k: " ".join(t.get("word") or "" for t in src.tokens[src.sentences[k][0]:src.sentences[k][1] + 1])
 944 | +        before = " ".join(sent(k) for k in range(a_, sg["k0"]))
 945 | +        after = " ".join(sent(k) for k in range(sg["k1"] + 1, b_ + 1))
 946 | +        return M.exclusion_verdict(router, sg["text"], before, after, avoid_model=by_id[sg["moment_id"]]["mined"]["by"])
 947 | +
 948 | +    with ThreadPoolExecutor(max_workers=10) as ex:
 949 | +        f_fid = ex.submit(VF.check, router, segs_v, lines, AUTHOR["vendor"], 7, man, levels, AUTHOR["family"])
 950 | +        f_ctx = ex.submit(CI.check_contexts, router, pk, contexts, AUTHOR["vendor"], 7,
 951 | +                          {lb: x for lb, x in a_by.items()}, AUTHOR["family"])
 952 | +        f_exc = {sg["label"]: ex.submit(exclusion, sg) for sg in pk["segments"]}
 953 | +        f_tru = {sg["label"]: ex.submit(truth, sg) for sg in pk["segments"]}
 954 | +        fid, ctx_ = f_fid.result(), f_ctx.result()
 955 | +        exc = {k: v.result() for k, v in f_exc.items()}
 956 | +        tru = {}
 957 | +        for k, v in f_tru.items():
 958 | +            try:
 959 | +                tru[k] = v.result()
 960 | +            except Exception as e:
 961 | +                tru[k] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
 962 | +    say(f"concurrent gates: {time.time() - t0:.0f} s")
 963 | +    dup = PK.duplicates(pk)
 964 | +    ok_c, coh = PK.coherence(router, pk, AUTHOR["vendor"], writer_family=AUTHOR["family"])
 965 | +    # report
 966 | +    say("VO FIDELITY deterministic: " + ("PASS" if fid["deterministic"]["ok"] else "FAIL " + json.dumps(
 967 | +        fid["deterministic"]["violations"])))
 968 | +    say(f"VO FIDELITY verdict ({fid['backend']}): " + ("PASS" if (fid["verdict"] or {}).get("ok") else "FAIL"))
 969 | +    for c in (fid["verdict"] or {}).get("claims") or []:
 970 | +        say(f"   [{c.get('line')}] {c.get('class')}: {c.get('words')!r} -> {c.get('supported')} "
 971 | +            f"{json.dumps(c.get('tests')) if c.get('class') == 'commentary' else json.dumps(c.get('support'))[:240]}")
 972 | +    for v in (fid["verdict"] or {}).get("violations") or []:
 973 | +        say(f"   VIOLATION {v['slot']}: {v['rule']}: {v['detail']}")
 974 | +    say(f"CONTEXT INTEGRITY (A {ctx_['backends'].get('A')}, B {ctx_['backends'].get('B')}, C "
 975 | +        f"{ctx_['backends'].get('C')}): " + ("PASS" if ctx_["ok"] else "FAIL " + json.dumps(ctx_["violations"])))
 976 | +    for lb, x in (ctx_.get("segments") or {}).items():
 977 | +        say(f"   {lb}: A '{x['A']['proposition']}' ({x['A']['certainty']}) | B '{x['B']['asserts']}' "
 978 | +            f"({x['B']['certainty']}) | B0 clip alone ({x['B0']['certainty']}) | C {x['C']}")
 979 | +    for n in ctx_.get("notes") or []:
 980 | +        say(f"   note: {n}")
 981 | +    say(f"   relations: {ctx_.get('relations')}")
 982 | +    say("DUPLICATE: " + ("PASS" if not dup else "FAIL " + json.dumps(dup)))
 983 | +    say("EXCLUSION: " + "; ".join(f"{k}: {v['verdict']} ({v.get('backend')}: {v['why'][:80]})" for k, v in exc.items()))
 984 | +    say("L-v 2 SECOND PASS: " + "; ".join(f"{k}: {'PASS' if v.get('ok') else 'FAIL'} ({v.get('model')}, disagree "
 985 | +                                          f"{v.get('disagree')}, speakers {v.get('speakers')}, err {v.get('error')})"
 986 | +                                          for k, v in tru.items()))
 987 | +    say(f"COHERENCE ({coh.get('backend')}): {'PASS' if ok_c else 'FAIL'} {json.dumps(coh)[:500]}")
 988 | +    rt_ok = PK.RUNTIME_S[0] <= pk["runtime_s_estimate"] <= PK.RUNTIME_S[1]
 989 | +    gates = {"vo_fidelity_deterministic": fid["deterministic"]["ok"], "vo_fidelity_verdict": bool((fid["verdict"] or {}).get("ok")),
 990 | +             "price_now_measured": fid["deterministic"].get("price_now_measured"), "duplicate": not dup,
 991 | +             "runtime": rt_ok, "r4": r4_ok, "context": ctx_["ok"], "exclusion": all(v["verdict"] == "keep" for v in exc.values()),
 992 | +             "second_pass": all(v.get("ok") for v in tru.values()), "coherence": ok_c}
 993 | +    led1 = json.load(open(PM.SPEND))["usd_estimate"]
 994 | +    say(f"GATES: {json.dumps(gates)}")
 995 | +    say(f"ALL PASS: {all(v for k, v in gates.items() if k != 'price_now_measured')} | wall {time.time() - t_start:.0f} s | "
 996 | +        f"spend this attempt ${led1 - led0:.2f} (ledger ${led1:.2f} of ${PM.LIMIT_USD})")
 997 | +    pk["gates"] = PK.inventory(fid, dup, rt_ok, (r4_ok, r4_why), ctx_, a_by, exc, tru, ok_c, coh)
 998 | +    say("INVENTORY: " + "; ".join(f"{k} {v['status']}" for k, v in pk["gates"].items()))
 999 | +    pk["checks_given"] = {"fidelity": fid, "context": ctx_, "duplicates": dup, "exclusion": exc, "truth": tru,
1000 | +                          "coherence": coh, "r4": [r4_ok, r4_why], "runtime_ok": rt_ok, "gates": gates,
1001 | +                          "step_a": a_by, "current_levels": levels, "author": AUTHOR,
1002 | +                          "wall_s": round(time.time() - t_start, 1), "usd": round(led1 - led0, 4)}
1003 | +    os.makedirs(OUT, exist_ok=True)
1004 | +    name = f"given_{a.variant}{'_balt' if a.bridge_alt else ''}{'_talt' if a.takeaway_alt else ''}{a.tag}.json"
1005 | +    json.dump(pk, open(os.path.join(OUT, name), "w"), indent=1, default=str)
1006 | +    open(os.path.join(OUT, name.replace(".json", ".log")), "w").write("\n".join(log) + "\n")
1007 | +    say(f"written {os.path.join(OUT, name)}")
1008 | +    return 0
1009 | +
1010 | +
1011 | +if __name__ == "__main__":
1012 | +    sys.exit(main())
1013 | diff --git a/tests/package/smoke_r7.py b/tests/package/smoke_r7.py
1014 | new file mode 100644
1015 | index 00000000..dade36c3
1016 | --- /dev/null
1017 | +++ b/tests/package/smoke_r7.py
1018 | @@ -0,0 +1,119 @@
1019 | +#!/usr/bin/env python3
1020 | +"""Smoke test of the moments-first wiring AS DEPLOYED (REQUESTS R7; the integrator's main tree: pinned.py 380a06f3 and
1021 | +edl_rules.py a5ec0f17). It reads COPIES of the main tree's pinned.py, edl_rules.py and config.py into a temporary
1022 | +directory beside this worktree's pipeline/ (nothing is written to the main tree), makes a pin with
1023 | +pipeline/package_pin.py from a gated package, and runs the deployed pinned.build_edl on it with a faked acquisition
1024 | +(the transcript words of each range; no download, no Whisper, no GPU, no network).
1025 | +
1026 | +Checks:
1027 | +- the EDL carries the package's VO (intro, and a line after each clip, the LAST clip included), the ONE title and
1028 | +  caption (law L-t), the digest and both gate verdicts; the deployed R4 for moments passes on it;
1029 | +- package_pin refuses a package whose gate inventory is not exactly PASS; a pin edited after the gates breaks its seal
1030 | +  (package_pin.seal), and the deployed moments_vo refuses a gate verdict that is not exactly true;
1031 | +- a pin without a package keeps today's VO (Editorial Law 2's default).
1032 | +Usage: python3 tests/package/smoke_r7.py [MAIN_TREE]   (default /home/ultron/protocol_pulse)"""
1033 | +import copy
1034 | +import os
1035 | +import shutil
1036 | +import sys
1037 | +import tempfile
1038 | +
1039 | +HERE = os.path.dirname(os.path.abspath(__file__))
1040 | +REPO = os.path.dirname(os.path.dirname(HERE))
1041 | +
1042 | +
1043 | +def fake_acq(pin):
1044 | +    """The transcript words of each range, spread over the segment's own start-end (its real duration)."""
1045 | +    acq = {}
1046 | +    for s in pin["segments"]:
1047 | +        ws = s["approved_text"].split()
1048 | +        a, b = float(s["start"]), float(s["end"])
1049 | +        step = (b - a) / len(ws)
1050 | +        words = [{"word": w, "start": round(a + i * step, 3), "end": round(a + (i + 1) * step - 0.02, 3)}
1051 | +                 for i, w in enumerate(ws)]
1052 | +        acq[s["video_id"]] = {"transcript": {"words": words, "segments": []}, "transcript_path": __file__,
1053 | +                              "offset": 0.0, "provenance": {"kind": "smoke"}}
1054 | +    return acq
1055 | +
1056 | +
1057 | +def main(argv=None):
1058 | +    main_tree = (argv or sys.argv[1:] or ["/home/ultron/protocol_pulse"])[0]
1059 | +    tmp = tempfile.mkdtemp(prefix="pp_r7_smoke_")
1060 | +    try:
1061 | +        shutil.copytree(os.path.join(REPO, "pipeline"), os.path.join(tmp, "pipeline"),
1062 | +                        ignore=shutil.ignore_patterns("__pycache__", "*.mp4", "*.onnx", "fixtures", "avatars"))
1063 | +        for f in ("pinned.py", "edl_rules.py", "config.py"):          # the DEPLOYED versions (read-only copies)
1064 | +            shutil.copy(os.path.join(main_tree, "pipeline", f), os.path.join(tmp, "pipeline", f))
1065 | +        sys.path.insert(0, os.path.join(tmp, "pipeline"))
1066 | +        import edl_rules
1067 | +        import package_pin
1068 | +        import pinned
1069 | +        assert os.path.dirname(pinned.__file__) == os.path.join(tmp, "pipeline")
1070 | +        gates = {k: {"status": "PASS", "by": "smoke", "replayed": False, "n": 1} for k in package_pin.REQUIRED_GATES}
1071 | +        segs = [("vgsSZ4mAHfQ", "Saifedean Ammous", 5144.99, 5153.37), ("c1JGheQBPH4", "What Bitcoin Did", 2480.28, 2491.52),
1072 | +                ("wdk5JZ9hPzs", "Natalie Brunell", 529.05, 539.34)]
1073 | +        pk = {"schema": "pp.package/1", "type": "moments", "title": "Nobody is in charge of Bitcoin.",
1074 | +              "caption": "no authority. three voices on why that is the point.", "vo_kind": "smoke",
1075 | +              "hook_first_words": "Bitcoin is the subject of", "runtime_s_estimate": 60.75, "models": {}, "gates": gates,
1076 | +              "vo": {"intro": "Nobody is in charge of Bitcoin. That's not a flaw. That's the design.",
1077 | +                     "bridges": ["Next, from Natalie Brunell's show: what does a system with no one in charge have to "
1078 | +                                 "get right?", "No ruler. Just rules nobody gets to bend. That's the idea."],
1079 | +                     "bridges_after_clip": [1, 2], "signoff": "Clips today from ..."},
1080 | +              "segments": [{"video_id": v, "channel": ch, "start": a, "end": b, "transcript_sha256": "t",
1081 | +                            "url_30s_before": f"https://www.youtube.com/watch?v={v}&t={int(a) - 30}s",
1082 | +                            "text": f"Bitcoin is the subject of sentence {i} spoken on {ch} here today."}
1083 | +                           for i, (v, ch, a, b) in enumerate(segs)]}
1084 | +        pin = package_pin.to_pin(pk, "smoke")
1085 | +        pinned.validate_range = lambda s, a: {"i0": 0, "i1": len(a["transcript"]["words"]) - 1,
1086 | +                                              "text": s["approved_text"], "first_word": s["approved_text"].split()[0],
1087 | +                                              "last_word": s["approved_text"].split()[-1], "start_file": s["start"],
1088 | +                                              "end_file": s["end"], "source_duration": 9999.0,
1089 | +                                              "words": a["transcript"]["words"], "transcript_word_straddles_boundary": False,
1090 | +                                              "edge_words_from": "smoke", "approved_text_similarity": 1.0}
1091 | +        pinned.L.make_lock = lambda *a, **k: {"smoke": True}
1092 | +        pinned.L.sha256_file = lambda p: "0" * 64
1093 | +        edl, ov, rep = pinned.build_edl(pin, fake_acq(pin))
1094 | +        assert edl["vo"]["intro"] == pk["vo"]["intro"], edl["vo"]
1095 | +        assert [b["after_clip"] for b in edl["vo"]["bridges"]] == [1, 2], edl["vo"]
1096 | +        assert edl["title"] == pk["title"] and edl["caption"] == pk["caption"], edl
1097 | +        assert edl["moments_package_sha256"] == package_pin.seal(pin["segments"], pin["moments_package"]["edl_vo"],
1098 | +                                                                 pin["moments_package"]["signoff_expected"],
1099 | +                                                                 pk["title"], pk["caption"], gates)
1100 | +        for c in edl["clips"]:
1101 | +            c.setdefault("duration", round(c.get("end_file", 0) - c.get("start_file", 0), 2))
1102 | +        ok, why = edl_rules.rule_r4(edl)
1103 | +        assert ok, why
1104 | +        bad_pk = copy.deepcopy(pk)
1105 | +        bad_pk["gates"]["second_pass"]["status"] = "NOT RUN"
1106 | +        try:
1107 | +            package_pin.to_pin(bad_pk, "smoke")
1108 | +            raise SystemExit("FAIL: a package with a gate NOT RUN was pinned")
1109 | +        except package_pin.PinRefused:
1110 | +            pass
1111 | +        tampered = copy.deepcopy(pin)
1112 | +        tampered["moments_package"]["title"] = "Bitcoin is at 126K today"
1113 | +        mp = tampered["moments_package"]
1114 | +        assert package_pin.seal(tampered["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"],
1115 | +                                mp["gates"]) != mp["package_sha256"], "the seal does not see a title edited after the gates"
1116 | +        bad2 = copy.deepcopy(pin)
1117 | +        bad2["moments_package"]["checks"]["context_integrity_ok"] = "true"
1118 | +        try:
1119 | +            pinned.build_edl(bad2, fake_acq(bad2))
1120 | +            raise SystemExit("FAIL: the deployed moments_vo accepted a truthy string as a gate verdict")
1121 | +        except pinned.PinError:
1122 | +            pass
1123 | +        plain = copy.deepcopy(pin)
1124 | +        plain.pop("moments_package")
1125 | +        edl2, _, _ = pinned.build_edl(plain, fake_acq(plain))
1126 | +        assert "title" not in edl2, edl2
1127 | +        print("SMOKE R7 PASS (deployed pinned.py / edl_rules.py): the package's VO (a line after every clip, the last "
1128 | +              "included), title and caption reach the EDL; R4 for moments passes (" + why + "); an ungated package is "
1129 | +              "refused at the pin; an edited pin breaks its seal; a truthy-string verdict is refused; a plain pin is "
1130 | +              "unchanged")
1131 | +        return 0
1132 | +    finally:
1133 | +        shutil.rmtree(tmp, ignore_errors=True)
1134 | +
1135 | +
1136 | +if __name__ == "__main__":
1137 | +    sys.exit(main())
1138 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
1139 | new file mode 100644
1140 | index 00000000..2d8a2522
1141 | --- /dev/null
1142 | +++ b/tests/package/test_angles.py
1143 | @@ -0,0 +1,159 @@
1144 | +#!/usr/bin/env python3
1145 | +"""pipeline/package.py (angle first), pipeline/package_pin.py and pipeline/transcript_truth.py, deterministic parts:
1146 | +the angle contract; the line-up per angle (one segment per channel, at most one price prediction, a short clip only as
1147 | +the punchline, the length the runtime AND the moments R4 allow); DUPLICATE against every clip; PRICE_NOW against the
1148 | +universe's current levels; the moments R4 mirror on tonight's real numbers; the pin refuses anything not exactly PASS
1149 | +and is sealed; the second recognition pass compares both ways. Offline."""
1150 | +import os
1151 | +import sys
1152 | +import unittest
1153 | +
1154 | +HERE = os.path.dirname(os.path.abspath(__file__))
1155 | +REPO = os.path.dirname(os.path.dirname(HERE))
1156 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1157 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
1158 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1159 | +import eligibility as E  # noqa: E402
1160 | +import package as PK  # noqa: E402
1161 | +import package_pin  # noqa: E402
1162 | +import transcript_truth as TT  # noqa: E402
1163 | +import vo_fidelity as VF  # noqa: E402
1164 | +from test_eligibility import NOW, REG, source  # noqa: E402
1165 | +from test_moments import pm  # noqa: E402
1166 | +
1167 | +
1168 | +def angle(ms, hook, text="Nobody controls Bitcoin."):
1169 | +    return {"angle": text, "moments": ms, "hook": hook, "support": {m: "x" for m in ms}}
1170 | +
1171 | +
1172 | +class TestAngles(unittest.TestCase):
1173 | +    def setUp(self):
1174 | +        self.by = {m["moment_id"]: m for m in (pm("a", "A", 10.0), pm("b", "B", 14.0), pm("c", "C", 13.0),
1175 | +                                                pm("d", "D", 6.0), pm("e", "A", 14.0))}
1176 | +
1177 | +    def test_the_angle_contract_is_strict_and_never_drops_an_id(self):
1178 | +        self.assertEqual(len(PK.check_angles({"angles": [angle(["a", "b", "c"], "a")]}, self.by)), 1)
1179 | +        for bad, why in (({"angles": [angle(["a", "b"], "a")]}, "3-8"),
1180 | +                         ({"angles": [angle(["a", "b", "c", "zz"], "a")]}, "ids not offered ['zz']"),
1181 | +                         ({"angles": [angle(["a", "e", "b"], "a")]}, ">= 3 channels"),
1182 | +                         ({"angles": [angle(["a", "b", "c"], "d")]}, "the hook one of its moments"),
1183 | +                         ({"angles": [dict(angle(["a", "b", "c"], "a"), title="x")]}, "keys must be exactly"),
1184 | +                         ({"angles": []}, "1-3 items")):
1185 | +            with self.assertRaises(ValueError) as cm:
1186 | +                PK.check_angles(bad, self.by)
1187 | +            self.assertIn(why, str(cm.exception))
1188 | +
1189 | +    def test_a_lineup_keeps_one_segment_per_channel_and_the_length_rules(self):
1190 | +        seg = PK.lineup_for(angle(["a", "b", "c", "e"], "a"), self.by)
1191 | +        self.assertEqual([m["moment_id"] for m in seg], ["a", "b", "c"])           # the proposer's hook first
1192 | +        self.assertEqual(len({m["channel_id"] for m in seg}), 3)                   # L-u: one per channel
1193 | +        lo, hi = PK.content_range(2)
1194 | +        self.assertTrue(lo <= 37.0 <= hi)
1195 | +
1196 | +    def test_a_short_clip_only_as_the_punchline(self):
1197 | +        by = {m["moment_id"]: m for m in (pm("a", "A", 10.0), pm("d", "D", 6.0), pm("b", "B", 14.0), pm("c", "C", 13.0))}
1198 | +        seg = PK.lineup_for(angle(["a", "d", "b", "c"], "a"), by)
1199 | +        self.assertIsNotNone(seg)
1200 | +        self.assertNotIn("d", [m["moment_id"] for m in seg[1:-1]])                # 6 s: never in the middle
1201 | +        by2 = {m["moment_id"]: m for m in (pm("a", "A", 12.0), pm("b", "B", 16.0), pm("d", "D", 6.0))}
1202 | +        seg2 = PK.lineup_for(angle(["a", "b", "d"], "a"), by2)
1203 | +        self.assertEqual([m["moment_id"] for m in seg2], ["a", "b", "d"])         # allowed as the last (the punchline)
1204 | +
1205 | +    def test_at_most_one_price_prediction_per_video(self):
1206 | +        two = {m["moment_id"]: m for m in (pm("h", "A", 10.0, risk=("price_prediction",)),
1207 | +                                           pm("c1", "B", 14.0, risk=("price_prediction",)), pm("c2", "C", 13.0))}
1208 | +        self.assertIsNone(PK.lineup_for(angle(["h", "c1", "c2"], "h"), two))      # the only line-up has two
1209 | +        one = dict(two, c1=dict(two["c1"], risk=[]))
1210 | +        self.assertIsNotNone(PK.lineup_for(angle(["h", "c1", "c2"], "h"), one))   # one is fine
1211 | +
1212 | +    def test_a_clip_must_add_something_against_every_line(self):
1213 | +        pk = {"segments": [{"label": "hook", "text": "Bitcoin ran from 16K to 126K. That move is about an 8x."},
1214 | +                           {"label": "clip_01", "text": "Nobody can take your Bitcoin without your keys, that is the point."},
1215 | +                           {"label": "clip_02", "text": "The hacks hit the exchanges and the intermediaries, never Bitcoin itself."}],
1216 | +              "lines": [{"slot": "intro", "text": "Bitcoin ran from 16K to 126K."},
1217 | +                        {"slot": "bridge_1", "text": "Watch what the hacks hit: the exchanges and the intermediaries, never Bitcoin itself."},
1218 | +                        {"slot": "title", "text": "Who controls Bitcoin?"},
1219 | +                        {"slot": "caption", "text": "Nobody can take your Bitcoin without your keys."}]}
1220 | +        self.assertEqual({(x["slot"], x["detail"]) for x in PK.duplicates(pk)},
1221 | +                         {("intro", "repeats the words of hook"), ("bridge_1", "repeats the words of clip_02"),
1222 | +                          ("caption", "repeats the words of clip_01")})
1223 | +
1224 | +    def test_price_now_against_the_current_levels(self):
1225 | +        src = source(["Bitcoin is trading at seventy three thousand dollars right now.",
1226 | +                      "Back in 2022 Bitcoin was at sixteen thousand dollars.",
1227 | +                      "I think Bitcoin is going to two hundred fifty thousand dollars."], age_h=3.0)
1228 | +        levels = PK.current_levels([src], E.Context(NOW, REG))
1229 | +        self.assertEqual(levels, [73000.0])                                      # history and forecasts never current
1230 | +        self.assertEqual(VF.price_now("Bitcoin ran from 16K to 126K", levels), [16000.0, 126000.0])
1231 | +        self.assertEqual(VF.price_now("Bitcoin holds $73,000", levels), [])
1232 | +        self.assertEqual(VF.price_now("From the 2022 low, Bitcoin ran from 16K to 126K", levels), [])
1233 | +
1234 | +
1235 | +class TestLengthAndR4(unittest.TestCase):
1236 | +    def test_the_runtime_counts_the_signoff_once(self):
1237 | +        segs = [{"duration_s": 10.0}, {"duration_s": 20.0}]
1238 | +        self.assertAlmostEqual(PK.runtime(segs, (40 + 18) / PK.WPS), 30.0 + 58 / 2.6 + PK.FIXED_S, places=2)
1239 | +        self.assertAlmostEqual(PK.FIXED_S + 18 / PK.WPS, E.TAIL_S, places=1)     # the tail = fixed + one sign-off
1240 | +
1241 | +    def test_the_moments_r4_on_tonights_numbers(self):
1242 | +        def pk(vo1, vo2, vo3):
1243 | +            p = {"segments": [{"duration_s": 8.38, "channel": "A"}, {"duration_s": 11.24, "channel": "B"},
1244 | +                              {"duration_s": 10.29, "channel": "C"}],
1245 | +                 "vo": {"intro": vo1, "bridges": [vo2, vo3], "bridges_after_clip": [1, 2]}}
1246 | +            p["runtime_s_estimate"] = PK.runtime(p["segments"], (sum(len(x.split()) for x in (vo1, vo2, vo3)) + 19) / PK.WPS)
1247 | +            return p
1248 | +        w = lambda n: " ".join(["word"] * n)
1249 | +        ok, why = PK.r4(pk(w(27), w(18), w(18)))                                  # 05:35-06:00's 63 words
1250 | +        self.assertFalse(ok)
1251 | +        self.assertIn("41.0%", why)
1252 | +        ok, why = PK.r4(pk(w(13), w(18), w(11)))                                  # the rendered 42 words
1253 | +        self.assertTrue(ok, why)
1254 | +        self.assertIn("32.6%", why)
1255 | +        self.assertFalse(PK.r4(dict(pk(w(13), w(18), w(11)), vo={"intro": w(13), "bridges": [w(5), w(5)],
1256 | +                                                                  "bridges_after_clip": [1, 1]}))[0])
1257 | +        self.assertLessEqual(PK.min_vo_words(29.91), PK.r4_max_vo_words(29.91, 3))
1258 | +
1259 | +
1260 | +class TestPinAndTruth(unittest.TestCase):
1261 | +    def pk(self, **gates):
1262 | +        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.REQUIRED_GATES}
1263 | +        g.update(gates)
1264 | +        return {"schema": "pp.package/1", "type": "moments", "title": "T", "caption": "C", "hook_first_words": "Bitcoin is",
1265 | +                "runtime_s_estimate": 62.0, "vo_kind": "written", "gates": g,
1266 | +                "vo": {"intro": "I", "bridges": ["B"], "bridges_after_clip": [1], "signoff": "S"},
1267 | +                "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
1268 | +                              "transcript_sha256": "t", "url_30s_before": "u"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
1269 | +
1270 | +    def test_the_pin_refuses_anything_not_exactly_pass_and_is_sealed(self):
1271 | +        pin = package_pin.to_pin(self.pk(), "r")
1272 | +        mp = pin["moments_package"]
1273 | +        self.assertEqual(mp["package_sha256"], package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"],
1274 | +                                                                 mp["title"], mp["caption"], mp["gates"]))
1275 | +        mp2 = dict(mp, title="changed after the gates")
1276 | +        self.assertNotEqual(mp["package_sha256"], package_pin.seal(pin["segments"], mp2["edl_vo"], mp2["signoff_expected"],
1277 | +                                                                    mp2["title"], mp2["caption"], mp2["gates"]))
1278 | +        for bad in ({"second_pass": {"status": "NOT RUN", "by": None, "replayed": False, "n": 0}},
1279 | +                    {"coherence": {"status": "FAIL", "by": "x", "replayed": False, "n": 1}},
1280 | +                    {"context_b": {"status": "PASS", "by": "x", "replayed": True, "n": 1}},
1281 | +                    {"exclusion": {"status": "pass", "by": "x", "replayed": False, "n": 1}}):
1282 | +            with self.assertRaises(package_pin.PinRefused):
1283 | +                package_pin.to_pin(self.pk(**bad), "r")
1284 | +        p = self.pk()
1285 | +        p.pop("gates")
1286 | +        with self.assertRaises(package_pin.PinRefused):
1287 | +            package_pin.to_pin(p, "r")
1288 | +
1289 | +    def test_the_second_pass_compares_both_ways_inside_the_clip_only(self):
1290 | +        self.assertFalse(TT.compare("Bitcoin is going to zero.", "Bitcoin is not going to zero.")["ok"])   # a dropped not
1291 | +        self.assertFalse(TT.compare("Bitcoin is not going to zero.", "Bitcoin is going to zero.")["ok"])
1292 | +        self.assertFalse(TT.compare("It hit 126,000.", "It hit 126,000 and 126,000.")["ok"])               # counts
1293 | +        self.assertTrue(TT.compare("Bitcoin ran from 16K to 126K.", "Bitcoin ran from 16k to 126k.")["ok"])
1294 | +        sec = {"segments": [], "words": [{"text": w, "start": i, "end": i + 0.9, "speaker": "s0"}
1295 | +                                         for i, w in enumerate("Your friends are not here Bitcoin is money".split())]}
1296 | +        self.assertEqual(TT.span_text(sec, 5.0, 8.0), "Bitcoin is money")
1297 | +        self.assertIs(TT.speaker_turns(sec, 5.0, 8.0)["turn_change_inside"], False)
1298 | +        self.assertIsNone(TT.speaker_turns({"segments": [], "words": []}, 0, 1)["turn_change_inside"])   # not measured
1299 | +
1300 | +
1301 | +if __name__ == "__main__":
1302 | +    unittest.main()
1303 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
1304 | new file mode 100644
1305 | index 00000000..4080143b
1306 | --- /dev/null
1307 | +++ b/tests/package/test_gates.py
1308 | @@ -0,0 +1,281 @@
1309 | +#!/usr/bin/env python3
1310 | +"""pipeline/context_integrity.py (law L-s, the orchestrator's rulings 3 / 5 / 6) and pipeline/vo_fidelity.py (law
1311 | +L-o 11 / L-t, the 05:25 classification A / B / C / D): the DECISION RULES, with canned model replies on a fake router
1312 | +(unit fixtures; the exam corpus is pipeline_pp_tests'). Offline."""
1313 | +import json
1314 | +import os
1315 | +import sys
1316 | +import unittest
1317 | +
1318 | +HERE = os.path.dirname(os.path.abspath(__file__))
1319 | +REPO = os.path.dirname(os.path.dirname(HERE))
1320 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1321 | +import context_integrity as CI  # noqa: E402
1322 | +import providers as P  # noqa: E402
1323 | +import vo_fidelity as VF  # noqa: E402
1324 | +
1325 | +
1326 | +class Canned:
1327 | +    """A router stand-in: answers each role from a queue; records (role, avoid_vendor, avoid_family)."""
1328 | +
1329 | +    def __init__(self, **answers):
1330 | +        self.answers, self.calls, self.rejected = {k: list(v) for k, v in answers.items()}, [], []
1331 | +
1332 | +    def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
1333 | +             avoid_family=None):
1334 | +        self.calls.append((role, avoid_vendor, avoid_family))
1335 | +        q = self.answers.get(role)
1336 | +        if not q:
1337 | +            raise P.ProviderError(f"{role}: no canned answer")
1338 | +        text = q.pop(0)
1339 | +        return P.Reply(text if isinstance(text, str) else json.dumps(text), f"fake:{role}", "fake")
1340 | +
1341 | +    def reject(self, reply, why=""):
1342 | +        self.rejected.append(reply.backend)
1343 | +        return False
1344 | +
1345 | +
1346 | +PKG = {"segments": [{"label": "hook", "video_id": "v1", "channel": "Coin Bureau", "text": "Bitcoin held its 200-day average."},
1347 | +                    {"label": "clip_01", "video_id": "v2", "channel": "Natalie Brunell", "text": "ETF outflows hit $1.3 billion."}],
1348 | +       "vo": {"intro": "Here's the thing.", "bridges": [], "bridges_after_clip": [], "signoff": "Clips today from ..."},
1349 | +       "title": "Bitcoin: Coin Bureau and Natalie Brunell", "caption": "Clips from Coin Bureau, Natalie Brunell."}
1350 | +CTX = {lb: {"text": CI.mark([("before.", False), (s["text"], True), ("after.", False)]), "title": "t",
1351 | +            "channel": s["channel"]} for lb, s in (("hook", PKG["segments"][0]), ("clip_01", PKG["segments"][1]))}
1352 | +
1353 | +
1354 | +def a_item(label, **kw):
1355 | +    d = {"label": label, "speaker_changes_inside": "no", "view": "own_sincere", "referents": [], "conditions": [],
1356 | +         "retraction": "none", "time_ok": "yes", "proposition": "p", "certainty": "certain", "speaker_is": "uncertain",
1357 | +         "speaker_evidence": ""}
1358 | +    d.update(kw)
1359 | +    return d
1360 | +
1361 | +
1362 | +def c_item(label, **kw):
1363 | +    d = {"label": label, "entails": "yes", "dropped_limit": "", "added_by": "", "same_polarity": "yes",
1364 | +         "stronger_certainty": "no", "raising_words": ""}
1365 | +    d.update(kw)
1366 | +    return d
1367 | +
1368 | +
1369 | +def b_items(cert="certain"):
1370 | +    return [{"label": lb, "asserts": "p", "certainty": cert, "polarity": "neutral"} for lb in ("hook", "clip_01")]
1371 | +
1372 | +
1373 | +def run(a=None, b=None, b0=None, c=None, relations=None, pkg=PKG, ctx=CTX):
1374 | +    A = {"excerpts": a or [a_item("hook"), a_item("clip_01")]}
1375 | +    rel = relations if relations is not None else [{"labels": ["hook", "clip_01"], "relation": "none"}]
1376 | +    B = {"takeaways": b or b_items(), "relations": rel}
1377 | +    B0 = {"takeaways": b0 or b_items(), "relations": rel}
1378 | +    C = {"pairs": c or [c_item("hook"), c_item("clip_01")]}
1379 | +    r = Canned(context_verdict=[A, C], viewer_takeaway=[B0, B])
1380 | +    return CI.check_contexts(r, pkg, ctx, writer_vendor="openai", writer_family="gpt"), r
1381 | +
1382 | +
1383 | +class TestContextDecision(unittest.TestCase):
1384 | +    def test_a_clean_package_passes_and_no_judged_step_runs_on_the_writers_vendor_or_family(self):
1385 | +        res, r = run()
1386 | +        self.assertTrue(res["ok"], res["violations"])
1387 | +        self.assertTrue(res["measured"])
1388 | +        judged = [c for c in r.calls if c[0] != "viewer_takeaway" or c[1] is not None]
1389 | +        self.assertTrue(all(v == "openai" and f == "gpt" for _, v, f in judged), r.calls)
1390 | +
1391 | +    def test_every_failure_class_fails(self):
1392 | +        cases = [
1393 | +            ({"a": [a_item("hook", view="attributed"), a_item("clip_01")]}, "NOT_OWN_SINCERE"),
1394 | +            ({"a": [a_item("hook", view="sarcastic"), a_item("clip_01")]}, "NOT_OWN_SINCERE"),
1395 | +            ({"a": [a_item("hook", speaker_changes_inside="uncertain"), a_item("clip_01")]}, "SPEAKER_CHANGE"),
1396 | +            ({"a": [a_item("hook", referents=[{"word": "it", "refers_to": "the ETF", "inside": False,
1397 | +                                               "changes_assertion": "yes"}]), a_item("clip_01")]}, "REFERENT_OUTSIDE"),
1398 | +            ({"a": [a_item("hook", referents=[{"word": "it", "refers_to": "the ETF", "inside": False,
1399 | +                                               "changes_assertion": "uncertain"}]), a_item("clip_01")]},
1400 | +             "REFERENT_OUTSIDE"),
1401 | +            ({"a": [a_item("hook", conditions=[{"text": "if the Fed cuts", "inside": False}]), a_item("clip_01")]},
1402 | +             "CONDITION_OUTSIDE"),
1403 | +            ({"a": [a_item("hook", retraction="later says he misspoke"), a_item("clip_01")]}, "RETRACTION"),
1404 | +            ({"a": [a_item("hook", certainty="uncertain"), a_item("clip_01")]}, "UNCERTAIN"),
1405 | +            ({"a": [a_item("hook", time_ok="no"), a_item("clip_01")]}, "STALE_TIME"),
1406 | +            ({"a": [a_item("hook", time_ok="uncertain"), a_item("clip_01")]}, "STALE_TIME"),
1407 | +            ({"c": [c_item("hook", entails="uncertain"), c_item("clip_01")]}, "NOT_ENTAILED"),
1408 | +            ({"c": [c_item("hook", entails="no", dropped_limit="back in 2021"), c_item("clip_01")],
1409 | +              "ctx": dict(CTX, hook=dict(CTX["hook"], text=CI.mark([("That was back in 2021.", False),
1410 | +                                                                    (PKG["segments"][0]["text"], True)])))},
1411 | +             "NOT_ENTAILED"),
1412 | +            ({"c": [c_item("hook", added_by="Coin Bureau and Natalie Brunell"), c_item("clip_01")]}, "NOT_ENTAILED"),
1413 | +            ({"c": [c_item("hook", same_polarity="uncertain"), c_item("clip_01")]}, "POLARITY"),
1414 | +            ({"c": [c_item("hook", stronger_certainty="uncertain"), c_item("clip_01")]}, "STRONGER"),
1415 | +            ({"c": [c_item("hook", stronger_certainty="yes", raising_words="Here's the thing"), c_item("clip_01")],
1416 | +              "b0": [dict(b_items()[0], certainty="likely"), b_items()[1]]}, "STRONGER"),
1417 | +            ({"relations": [{"labels": ["hook", "clip_01"], "relation": "answering"}]}, "FALSE_RELATION"),
1418 | +            ({"relations": [{"labels": ["hook", "clip_01"], "relation": "uncertain"}]}, "FALSE_RELATION"),
1419 | +        ]
1420 | +        for kw, rule in cases:
1421 | +            res, _ = run(**{k: v for k, v in kw.items()})
1422 | +            self.assertFalse(res["ok"], rule)
1423 | +            self.assertIn(rule, {v["rule"] for v in res["violations"]}, (rule, res["violations"]))
1424 | +
1425 | +    def test_rulings_3_5_6_uncited_disagreements_are_notes_never_failures(self):
1426 | +        # ruling 3: STRONGER with no cited words, or the clip alone already certain -> a note
1427 | +        for c in (c_item("hook", stronger_certainty="yes"),
1428 | +                  c_item("hook", stronger_certainty="yes", raising_words="Here's the thing")):
1429 | +            res, _ = run(c=[c, c_item("clip_01")])
1430 | +            self.assertTrue(res["ok"], res["violations"])
1431 | +            self.assertTrue(res.get("notes"))
1432 | +        # ruling 3: cited words that are NOT the video's own -> a note
1433 | +        res, _ = run(c=[c_item("hook", stronger_certainty="yes", raising_words="the bottom is in"), c_item("clip_01")],
1434 | +                     b0=[dict(b_items()[0], certainty="likely"), b_items()[1]])
1435 | +        self.assertTrue(res["ok"], res["violations"])
1436 | +        # ruling 5: entails "no" with no limit, or a limit that is not the context's own words -> a note
1437 | +        for lim in ("", "for that to emerge"):
1438 | +            res, _ = run(c=[c_item("hook", entails="no", dropped_limit=lim), c_item("clip_01")])
1439 | +            self.assertTrue(res["ok"], (lim, res["violations"]))
1440 | +        # ruling 5: an added claim cited in words that do not name the speaker's show -> a note
1441 | +        res, _ = run(c=[c_item("hook", added_by="Here's the thing"), c_item("clip_01")])
1442 | +        self.assertTrue(res["ok"], res["violations"])
1443 | +        # ruling 3 (referent): outside, but resolving it differently does not change the assertion -> passes
1444 | +        res, _ = run(a=[a_item("hook", referents=[{"word": "it", "refers_to": "recent hacks", "inside": False,
1445 | +                                                    "changes_assertion": "no"}]), a_item("clip_01")])
1446 | +        self.assertTrue(res["ok"], res["violations"])
1447 | +
1448 | +    def test_an_unreadable_or_incomplete_step_is_not_measured_and_fails(self):
1449 | +        r = Canned(context_verdict=["not json"], viewer_takeaway=[])
1450 | +        res = CI.check_contexts(r, PKG, CTX, writer_vendor="openai")
1451 | +        self.assertEqual((res["ok"], res["measured"], res["violations"][0]["rule"]), (False, False, "CONTEXT_UNAVAILABLE"))
1452 | +        for kw in ({"a": [a_item("hook")]},                                      # step A skipped a segment
1453 | +                   {"relations": []},                                            # a pair not rated (audit C5)
1454 | +                   {"relations": [{"labels": ["hook", "clip_01"], "relation": "none"}] * 2},   # rated twice
1455 | +                   {"a": [{k: v for k, v in a_item("hook").items() if k != "time_ok"}, a_item("clip_01")]}):   # no default
1456 | +            res, _ = run(**kw)
1457 | +            self.assertFalse(res["ok"], kw)
1458 | +            self.assertIn("CONTEXT_UNAVAILABLE", {v["rule"] for v in res["violations"]}, kw)
1459 | +
1460 | +    def test_a_relation_inside_one_video_is_allowed(self):
1461 | +        same = dict(PKG, segments=[dict(PKG["segments"][0]), dict(PKG["segments"][1], video_id="v1")])
1462 | +        res, _ = run(pkg=same, relations=[{"labels": ["hook", "clip_01"], "relation": "same_conversation"}])
1463 | +        self.assertTrue(res["ok"], res["violations"])
1464 | +
1465 | +    def test_the_view_follows_the_renderer_and_the_selection_marks_survive_escaping(self):
1466 | +        pk = dict(PKG, vo={"intro": "INTRO", "bridges": ["AFTER ONE"], "bridges_after_clip": [1], "signoff": "S"})
1467 | +        v = CI.package_view(pk)
1468 | +        self.assertLess(v.index('label="hook"'), v.index("INTRO"))         # the intro plays AFTER the hook
1469 | +        self.assertLess(v.index('label="clip_01"'), v.index("AFTER ONE"))
1470 | +        marked = CI.mark([("a <b>", False), ("sel", True)])
1471 | +        self.assertIn("<selected>sel</selected>", marked)
1472 | +        self.assertNotIn("<b>", marked)
1473 | +
1474 | +    def test_a_speaker_is_verified_only_by_host_and_verbatim_evidence(self):
1475 | +        text = CI.mark([("Welcome back to my channel everyone.", False), ("Bitcoin is money.", True)])
1476 | +        self.assertTrue(CI.speaker_verified({"speaker_is": "host", "speaker_evidence": "welcome back to my channel"}, text))
1477 | +        self.assertFalse(CI.speaker_verified({"speaker_is": "host", "speaker_evidence": "welcome to the show"}, text))
1478 | +        self.assertFalse(CI.speaker_verified({"speaker_is": "guest", "speaker_evidence": "welcome back to my channel"},
1479 | +                                             text))
1480 | +
1481 | +
1482 | +class TestFidelityVerdict(unittest.TestCase):
1483 | +    SEGS = {"m1": {"show": "Coin Bureau", "speaker": None, "names": [], "video_id": "v1",
1484 | +                   "text": "Bitcoin dropped to $73,000 and found support at its 200-day moving average."},
1485 | +            "m2": {"show": "Stephan Livera", "speaker": "Stephan Livera", "names": ["Stephan Livera"], "video_id": "v2",
1486 | +                   "text": "I think Bitcoin is by far the most undervalued asset in the entire financial system."}}
1487 | +    LINES = [{"slot": "intro", "text": "Coin Bureau says Bitcoin found support at its 200-day moving average.",
1488 | +              "cites": ["m1"]}]
1489 | +    T0 = {t: "no" for t in VF.COMMENTARY_TESTS}
1490 | +
1491 | +    @staticmethod
1492 | +    def claim(line, words, cls, claim="c", sup="yes", support=(), tests=None):
1493 | +        return {"line": line, "words": words, "class": cls, "claim": claim, "supported": sup, "support": list(support),
1494 | +                "tests": tests if tests is not None else {}}
1495 | +
1496 | +    def verdict(self, claims, lines=None):
1497 | +        r = Canned(fidelity_verdict=[{"claims": claims}])
1498 | +        return VF.check(r, self.SEGS, lines or self.LINES, writer_vendor="openai", writer_family="gpt"), r
1499 | +
1500 | +    def test_an_attribution_with_verbatim_support_passes(self):
1501 | +        res, r = self.verdict([self.claim("intro", self.LINES[0]["text"], "attribution", support=[
1502 | +            {"segment": "m1", "words": "found support at its 200-day moving average"}])])
1503 | +        self.assertTrue(res["ok"], res["violations"])
1504 | +        self.assertEqual(r.calls, [("fidelity_verdict", "openai", "gpt")])
1505 | +
1506 | +    def test_host_commentary_passes_on_the_five_tests_alone(self):
1507 | +        lines = [{"slot": "intro", "text": "So is Bitcoin still cheap at these levels?", "cites": []}]
1508 | +        res, _ = self.verdict([self.claim("intro", lines[0]["text"], "commentary", sup="n/a", tests=self.T0)], lines)
1509 | +        self.assertTrue(res["ok"], res["violations"])
1510 | +        for t in VF.COMMENTARY_TESTS:
1511 | +            res, _ = self.verdict([self.claim("intro", lines[0]["text"], "commentary", sup="n/a",
1512 | +                                              tests=dict(self.T0, **{t: "uncertain"}))], lines)
1513 | +            self.assertIn("COMMENTARY", {v["rule"] for v in res["violations"]}, t)
1514 | +
1515 | +    def test_commentary_that_carries_a_fact_is_judged_strict(self):
1516 | +        lines = [{"slot": "intro", "text": "Bitcoin is at 126K now, the bottom is in.", "cites": ["m1"]}]
1517 | +        res, _ = self.verdict([self.claim("intro", lines[0]["text"], "commentary", sup="n/a", tests=self.T0)], lines)
1518 | +        self.assertIn("NOT_COMMENTARY", {v["rule"] for v in res["violations"]})
1519 | +
1520 | +    def test_every_sentence_needs_a_claim_and_an_empty_verdict_fails(self):
1521 | +        lines = [{"slot": "intro", "text": "Coin Bureau says Bitcoin found support. So is it cheap?", "cites": ["m1"]}]
1522 | +        half = [self.claim("intro", "Coin Bureau says Bitcoin found support.", "attribution",
1523 | +                           support=[{"segment": "m1", "words": "found support at its"}])]
1524 | +        for claims in ([], half):
1525 | +            res, _ = self.verdict(claims, lines)
1526 | +            self.assertIn("VERDICT_INCOMPLETE", {v["rule"] for v in res["violations"]}, claims)
1527 | +
1528 | +    def test_supports_must_be_verbatim_three_words_from_the_lines_own_cites(self):
1529 | +        for sup in ([{"segment": "m1", "words": "found strong support"}],          # not verbatim
1530 | +                    [{"segment": "m1", "words": "Bitcoin"}],                       # one word
1531 | +                    [{"segment": "m2", "words": "the most undervalued asset"}],    # not this line's cite
1532 | +                    []):
1533 | +            res, _ = self.verdict([self.claim("intro", self.LINES[0]["text"], "attribution", support=sup)])
1534 | +            self.assertIn("VERDICT_UNVERIFIED", {v["rule"] for v in res["violations"]}, sup)
1535 | +        for sup, rule in (("no", "VERDICT_NO"), ("uncertain", "VERDICT_UNCERTAIN")):
1536 | +            res, _ = self.verdict([self.claim("intro", self.LINES[0]["text"], "attribution", sup=sup)])
1537 | +            self.assertIn(rule, {v["rule"] for v in res["violations"]})
1538 | +
1539 | +    def test_production_claims_cite_the_manifest(self):
1540 | +        lines = [{"slot": "caption", "text": "Clips from Coin Bureau and Stephan Livera.", "cites": []}]
1541 | +        ok = [self.claim("caption", lines[0]["text"], "production",
1542 | +                         support=[{"segment": "manifest", "words": "Links to every source are below"}])]
1543 | +        res, _ = self.verdict(ok, lines)
1544 | +        self.assertTrue(res["ok"], res["violations"])
1545 | +
1546 | +    def test_no_verdict_is_a_failure_and_not_measured(self):
1547 | +        res = VF.check(Canned(), self.SEGS, self.LINES, writer_vendor="openai")
1548 | +        self.assertEqual((res["ok"], res["measured"]), (False, False))
1549 | +        self.assertEqual(res["verdict"]["violations"][0]["rule"], "VERDICT_UNAVAILABLE")
1550 | +        res = VF.check(Canned(fidelity_verdict=[{"claims": [{"line": ["intro"]}]}]), self.SEGS, self.LINES, "openai")
1551 | +        self.assertEqual(res["verdict"]["violations"][0]["rule"], "VERDICT_UNAVAILABLE")    # malformed: no crash
1552 | +
1553 | +
1554 | +class TestDeterministicRules(unittest.TestCase):
1555 | +    SEGS = TestFidelityVerdict.SEGS
1556 | +
1557 | +    def rules(self, text, cites, levels=None, segs=None):
1558 | +        r = VF.check_deterministic(segs or self.SEGS, [{"slot": "intro", "text": text, "cites": cites}],
1559 | +                                   current_levels=levels)
1560 | +        return {v["rule"] for v in r["violations"]}
1561 | +
1562 | +    def test_attribution_needs_a_verified_speaker_and_the_clips_own_hedge(self):
1563 | +        self.assertEqual(self.rules("Stephan Livera thinks Bitcoin is undervalued.", ["m2"]), set())
1564 | +        self.assertIn("HEDGE", self.rules("Stephan Livera says Bitcoin is undervalued.", ["m2"]))
1565 | +        unverified = dict(self.SEGS, m2=dict(self.SEGS["m2"], speaker=None, names=[]))
1566 | +        self.assertIn("ATTRIBUTION", self.rules("Stephan Livera thinks Bitcoin is undervalued.", ["m2"], segs=unverified))
1567 | +        self.assertEqual(self.rules("Next, on Stephan Livera's show.", ["m2"], segs=unverified), set())
1568 | +        self.assertIn("ATTRIBUTION", self.rules("She says Bitcoin is undervalued.", ["m2"]))
1569 | +
1570 | +    def test_names_numbers_quotes_relations_and_imperatives(self):
1571 | +        self.assertIn("NAME", self.rules("Michael Saylor Warns Of Incoming Crash", ["m1"]))
1572 | +        self.assertEqual(self.rules("Why The Dollar Is Losing To Bitcoin", ["m1"]), set())
1573 | +        self.assertIn("NUMBER", self.rules("Seven countries hold Bitcoin.", ["m1"]))
1574 | +        self.assertIn("QUOTE", self.rules("Coin Bureau calls it 'a crash'.", ["m1"]))
1575 | +        self.assertIn("RELATION", self.rules("Both agree Bitcoin is undervalued.", ["m1", "m2"]))
1576 | +        self.assertEqual(self.rules("Next, Coin Bureau on how Bitcoin responded to the rate hike.", ["m1"]), set())
1577 | +        self.assertIn("IMPERATIVE", self.rules("It's time to buy.", ["m1"]))
1578 | +        self.assertEqual(self.rules("Short-term holders are selling.", ["m1"]), set())
1579 | +
1580 | +    def test_price_now_reads_history_forecasts_and_counts(self):
1581 | +        self.assertIn("PRICE_NOW", self.rules("Bitcoin just set an all-time high at $126,000.", ["m1"], [73000.0]))
1582 | +        self.assertIn("PRICE_NOW", self.rules("Since 2022, Bitcoin is at $126,000.", ["m1"], [73000.0]))
1583 | +        self.assertNotIn("PRICE_NOW", self.rules("Strategy now holds 640,000 bitcoin.", ["m1"], [73000.0]))
1584 | +        self.assertEqual(VF.price_now("From the 2022 low, Bitcoin ran from 16K to 126K", [73000.0]), [])
1585 | +        self.assertEqual(VF.price_now("Bitcoin could hit 150,000", [73000.0]), [])
1586 | +
1587 | +
1588 | +if __name__ == "__main__":
1589 | +    unittest.main()
1590 | diff --git a/tests/package/yield_table.py b/tests/package/yield_table.py
1591 | new file mode 100644
1592 | index 00000000..a7fb294a
1593 | --- /dev/null
1594 | +++ b/tests/package/yield_table.py
1595 | @@ -0,0 +1,83 @@
1596 | +#!/usr/bin/env python3
1597 | +"""Yield per saved universe against the backtest's blind oracle (orchestrator 03:00; law L-n): the oracle's
1598 | +moments-first line-ups judged to pass (/home/ultron/heimdall_probe/pp_redteam/oracle/<day>/moments/JUDGE_L*.json,
1599 | +read-only) beside this session's miner + packager (tests/moments/proof/<run>/moments.json,
1600 | +tests/package/proof/<run>/package.json). A universe where the oracle has a line-up that passes and this pipeline has no
1601 | +package is a DEFECT to fix before DONE. Note the rules differ: the oracle judged caption-line timing without the
1602 | +02:30 laws (one clip per channel L-u, context integrity L-s, layout DEC-12d); this pipeline applies them all.
1603 | +Writes docs/audits/parallel/pp-selectid_YIELD.md."""
1604 | +import glob
1605 | +import json
1606 | +import os
1607 | +
1608 | +HERE = os.path.dirname(os.path.abspath(__file__))
1609 | +REPO = os.path.dirname(os.path.dirname(HERE))
1610 | +ORACLE = "/home/ultron/heimdall_probe/pp_redteam/oracle"
1611 | +OUT = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_YIELD.md")
1612 | +RUNS = ("fresh_20261106_213852", "fresh_20261107_065702", "fresh_20261107_080503", "fresh_20261110_093150",
1613 | +        "fresh_20261111_190259", "fresh_20261111_192645", "fresh_20261111_213954", "fresh_20261112_001448",
1614 | +        "fresh_20261112_013452", "fresh_20261112_050611")
1615 | +
1616 | +
1617 | +def oracle_counts(run):
1618 | +    """(moments-first line-ups the oracle judged to pass, story-first ones), or None when the oracle has no directory
1619 | +    for this universe (never read as zero: audit p2 C17)."""
1620 | +    day = run.replace("fresh_", "")
1621 | +    if not os.path.isdir(os.path.join(ORACLE, day)):
1622 | +        return None
1623 | +    d = os.path.join(ORACLE, day, "moments")
1624 | +    passed = 0
1625 | +    for f in glob.glob(os.path.join(d, "JUDGE_L*.json")):
1626 | +        if (json.load(open(f)).get("verdict") or "").upper() == "LEGAL":
1627 | +            passed += 1
1628 | +    story = 0
1629 | +    for f in glob.glob(os.path.join(ORACLE, day, "JUDGE_L*.json")):
1630 | +        if (json.load(open(f)).get("verdict") or "").upper() == "LEGAL":
1631 | +            story += 1
1632 | +    return passed, story
1633 | +
1634 | +
1635 | +def main():
1636 | +    rows = ["| universe | oracle: moments-first line-ups that pass / story-first | moments mined / usable | package | "
1637 | +            "title | gates | defect? |", "|---|---|---|---|---|---|---|"]
1638 | +    defects = 0
1639 | +    for run in RUNS:
1640 | +        oc = oracle_counts(run)
1641 | +        mp, sp = oc if oc else (None, None)
1642 | +        mf = os.path.join(REPO, "tests", "moments", "proof", run, "moments.json")
1643 | +        pf = os.path.join(HERE, "proof", run, "package.json")
1644 | +        m = json.load(open(mf)) if os.path.exists(mf) else None
1645 | +        p = json.load(open(pf)) if os.path.exists(pf) else None
1646 | +        mined = f"{len(m['moments'])} / {sum(1 for x in m['moments'] if x['on_screen_ok'] and not x['excluded'])}" \
1647 | +            if m else "not mined"
1648 | +        pk = (p or {}).get("package")
1649 | +        pin_f = os.path.join(HERE, "proof", run, "MOMENTS_PIN.json")
1650 | +        if not pk and os.path.exists(pin_f):                 # a sealed pin: every gate exactly PASS (package_pin refuses
1651 | +            pin = json.load(open(pin_f))                     # anything else)
1652 | +            mpk = pin.get("moments_package") or {}
1653 | +            if mpk.get("gates") and all(g.get("status") == "PASS" for g in mpk["gates"].values()):
1654 | +                pk = {"type": f"{mpk.get('type')}, pinned {pin.get('story_id')}", "segments": pin["segments"],
1655 | +                      "runtime_s_estimate": mpk.get("runtime_s_estimate"), "title": mpk.get("title"),
1656 | +                      "gates": mpk["gates"]}
1657 | +        if pk:
1658 | +            pkg, title = f"YES ({pk['type']}, {len(pk['segments'])} segments, ~{pk['runtime_s_estimate']} s)", pk["title"]
1659 | +            gates = ", ".join(f"{k} {v['status']}" for k, v in (pk.get("gates") or {}).items()) or "NO GATE INVENTORY"
1660 | +        else:
1661 | +            pkg = "no" if p else "not run"
1662 | +            title = "-"
1663 | +            gates = (p or {}).get("why_none") or "; ".join(
1664 | +                f"angle {t.get('angle')}: " + (t.get("why") or ", ".join(sorted({v["rule"] for a in t.get("attempts", [])
1665 | +                                                                                  for v in a.get("violations", [])})))
1666 | +                for t in (p or {}).get("tried", []))[:200] or "-"
1667 | +        defect = "ORACLE MISSING" if oc is None else ("DEFECT (L-n)" if mp and not pk else "")
1668 | +        defects += defect == "DEFECT (L-n)"
1669 | +        rows.append(f"| {run} | {'-' if oc is None else f'{mp} / {sp}'} | {mined} | {pkg} | {title.replace('|', '/')} | {gates.replace('|', '/')} | "
1670 | +                    f"{defect} |")
1671 | +    text = "# pp-selectid — phase-2 yield against the blind oracle (generated by tests/package/yield_table.py)\n\n" + \
1672 | +        "\n".join(rows) + f"\n\nDefects (oracle has a passing line-up, this pipeline none): {defects}\n"
1673 | +    open(OUT, "w").write(text)
1674 | +    print(text)
1675 | +
1676 | +
1677 | +if __name__ == "__main__":
1678 | +    main()
1679 | diff --git a/tests/providers/ab_roles.py b/tests/providers/ab_roles.py
1680 | new file mode 100644
1681 | index 00000000..d80cbac3
1682 | --- /dev/null
1683 | +++ b/tests/providers/ab_roles.py
1684 | @@ -0,0 +1,179 @@
1685 | +#!/usr/bin/env python3
1686 | +"""Blind A/B per model role (law L-x, orchestrator 02:45: "for each role report a blind A/B on saved data: local
1687 | +gemma3:27b vs frontier vs Heimdall: quality verdict, failures, latency, dollars"). The integrator runs the LOCAL leg
1688 | +under the GPU0 lease (--local: a started story_semantics.LocalLLM is handed to the router); builders run the rest.
1689 | +Generator and judge are always different models: the quality judge is a back-end outside the compared set.
1690 | +
1691 | +Roles:
1692 | +  mine        moments.mine on a saved universe with the role's chain pinned to ONE back-end per leg; quality: a blind
1693 | +              pairwise judge (outside the compared vendors and families) sees two anonymised lists of each leg's best
1694 | +              8 moments (verbatim text, channel), in BOTH orders, and says which list holds better moments for a
1695 | +              60-second Bitcoin video; a split is a tie; failures = rejected / model_error calls; latency = model
1696 | +              seconds; dollars from the spend ledger.
1697 | +  verdicts    fidelity_verdict, context_verdict, viewer_takeaway, exclusion_verdict: the pp-tests exam corpora
1698 | +              (format v1) through pipeline/moments_gate_adapter.py with the chain pinned per leg; quality = the
1699 | +              confusion table against the exam's answers (read only AFTER the gate answered, by this harness, never
1700 | +              by the gate).
1701 | +Usage:
1702 | +  python3 tests/providers/ab_roles.py mine --run fresh_20261112_050611 --legs heimdall:qwen/qwen3.8-27b openai:gpt-6.1-sol [--local]
1703 | +  python3 tests/providers/ab_roles.py verdicts --corpus /home/ultron/worktrees/pp-tests/tests/adversarial/corpora --legs ...
1704 | +Output: tests/providers/ab/<role>_<name>.json and a printed table.
1705 | +"""
1706 | +import argparse
1707 | +import json
1708 | +import os
1709 | +import sys
1710 | +import time
1711 | +
1712 | +HERE = os.path.dirname(os.path.abspath(__file__))
1713 | +REPO = os.path.dirname(os.path.dirname(HERE))
1714 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1715 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
1716 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1717 | +sys.path.insert(0, os.path.join(REPO, "tests", "package"))
1718 | +import providers as P  # noqa: E402
1719 | +
1720 | +OUT = os.path.join(HERE, "ab")
1721 | +REPLIES = os.path.join(REPO, "tests", "moments", "fixtures", "replies")    # shared: a leg already mined replays
1722 | +SPEND = os.path.join(REPO, "tests", "moments", "proof", "SPEND.json")
1723 | +ENV = P.ENV_PATH
1724 | +
1725 | +JUDGE_PROMPT = """Two editors each picked MOMENTS (verbatim quotes) for 60-second Bitcoin videos from the same
1726 | +transcripts. Judge which LIST is better material: moments that grab attention in the first seconds, are quotable,
1727 | +state something surprising or clear, stand alone without context, are about Bitcoin, and avoid accusations, advice,
1728 | +ads and outrage. Ignore list length beyond the best 8.
1729 | +
1730 | +LIST A:
1731 | +{a}
1732 | +
1733 | +LIST B:
1734 | +{b}
1735 | +
1736 | +Return ONLY this JSON object: {{"better": "A" | "B" | "tie", "why": "two sentences at most"}}"""
1737 | +
1738 | +
1739 | +def _router(chains, local=None):
1740 | +    return P.Router(env_path=ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=40.0, chains=chains,
1741 | +                    local_llm=local)
1742 | +
1743 | +
1744 | +def _local_llm():
1745 | +    import story_semantics as sm
1746 | +    return sm.LocalLLM().start()                 # proves the GPU0-only Ollama listener (law L-r: the caller's lease)
1747 | +
1748 | +
1749 | +def leg_mine(run, backend, local=None):
1750 | +    import moments as M
1751 | +    import proof_moments as PM
1752 | +    import trend_brief as TB
1753 | +    words, captions, ctx, saved = PM.universe_sources(run)
1754 | +    r = _router({"mine": [backend]}, local)
1755 | +    t0 = time.time()
1756 | +    out = M.mine(r, words, ctx, TB.TOPICS, since=None, optout=M.optout_ids(), log=lambda s: None,
1757 | +                 cycle=f"ab:{run}:{backend}", recent_h=72.0)
1758 | +    secs = round(time.time() - t0, 1)
1759 | +    statuses = [c["status"] for c in out["calls"]]
1760 | +    usd = sum((a.get("meta") or {}).get("usd", 0.0) for c in out["calls"] for a in c["attempts"])
1761 | +    return {"backend": backend, "calls": len(statuses), "accepted": statuses.count("accepted"),
1762 | +            "failures": {s: statuses.count(s) for s in set(statuses) if s != "accepted"}, "seconds": secs,
1763 | +            "usd": round(usd, 4), "moments": out["moments"]}
1764 | +
1765 | +
1766 | +def judge_pair(judge_backend, a, b, seed):
1767 | +    """The blind pairwise judge, in BOTH orders (audit p2 C17: one coin-flip order was n = 1); a split verdict is a
1768 | +    tie. The lists are mine()'s output, ranked by rank_score, so [:8] is each leg's best 8."""
1769 | +    def fmt(lst):
1770 | +        return "\n".join(f"- [{m['channel_name']}] \"{m['text'][:400]}\"" for m in lst[:8]) or "(none)"
1771 | +    r = _router({"ab_judge": [judge_backend]})
1772 | +    votes, why = [], []
1773 | +    for flip in (False, True):
1774 | +        x, y = (b, a) if flip else (a, b)
1775 | +        rep = r.call("ab_judge", JUDGE_PROMPT.format(a=fmt(x), b=fmt(y)), 600, seed + int(flip))
1776 | +        v = json.loads(rep.text.strip())
1777 | +        if not isinstance(v, dict) or v.get("better") not in ("A", "B", "tie"):
1778 | +            raise ValueError("judge reply out of contract")
1779 | +        votes.append(v["better"] if v["better"] == "tie" else (("B" if v["better"] == "A" else "A") if flip
1780 | +                                                               else v["better"]))
1781 | +        why.append(v.get("why"))
1782 | +    better = votes[0] if votes[0] == votes[1] else "tie"
1783 | +    return {"better": better, "votes": votes, "why": why, "judge": judge_backend}
1784 | +
1785 | +
1786 | +def ab_mine(args):
1787 | +    cfg = json.load(open(P.CONFIG))
1788 | +    legs = [leg_mine(args.run, b) for b in args.legs]
1789 | +    if args.local:
1790 | +        local = next(n for n, s_ in cfg["backends"].items() if s_["vendor"] == "local")   # no model name in code (L-x)
1791 | +        legs.append(leg_mine(args.run, local, _local_llm()))
1792 | +    compared = {l["backend"] for l in legs}
1793 | +    vendors = {cfg["backends"][c]["vendor"] for c in compared if c in cfg["backends"]}
1794 | +    families = {cfg["backends"][c].get("family") for c in compared if c in cfg["backends"]}
1795 | +    outside = [b for b, s_ in cfg["backends"].items() if b not in compared and s_["vendor"] not in vendors
1796 | +               and s_.get("family") not in families and not s_["vendor"].endswith(("_stt", "_search"))]
1797 | +    if args.judge and args.judge not in outside:
1798 | +        raise SystemExit(f"--judge {args.judge} is a compared leg's vendor or family (or not a text back-end)")
1799 | +    if not (args.judge or outside):
1800 | +        raise SystemExit("no judge outside the compared vendors and families: pass --judge")
1801 | +    judge = args.judge or outside[0]
1802 | +    pairs = []
1803 | +    for i in range(len(legs)):
1804 | +        for j in range(i + 1, len(legs)):
1805 | +            try:
1806 | +                v = judge_pair(judge, legs[i]["moments"], legs[j]["moments"], seed=7 + i * 10 + j)
1807 | +            except Exception as e:
1808 | +                v = {"better": None, "why": f"judge failed: {type(e).__name__}: {str(e)[:160]}", "judge": judge}
1809 | +            pairs.append({"A": legs[i]["backend"], "B": legs[j]["backend"], **v})
1810 | +    rec = {"role": "mine", "run": args.run, "judge": judge,
1811 | +           "legs": [{k: v for k, v in l.items() if k != "moments"} | {"n_moments": len(l["moments"])} for l in legs],
1812 | +           "pairs": pairs}
1813 | +    os.makedirs(OUT, exist_ok=True)
1814 | +    json.dump(rec, open(os.path.join(OUT, f"mine_{args.run}.json"), "w"), indent=1, default=str)
1815 | +    print(json.dumps(rec, indent=1, default=str)[:4000])
1816 | +
1817 | +
1818 | +def ab_verdicts(args):
1819 | +    import moments_gate_adapter as A
1820 | +    rows = []
1821 | +    for backend in args.legs:
1822 | +        for gate, corpus, role in (("context_integrity", "context_integrity", ("context_verdict", "viewer_takeaway")),
1823 | +                                   ("vo_fidelity", "vo_fidelity", ("fidelity_verdict",)),
1824 | +                                   ("exclusion", "exclusions", ("exclusion_verdict",))):
1825 | +            d = os.path.join(args.corpus, corpus)
1826 | +            if not os.path.isdir(d):
1827 | +                continue
1828 | +            A._router = _router({r: [backend] for r in role})
1829 | +            conf, secs = {}, 0.0
1830 | +            for f in sorted(x for x in os.listdir(d) if x.endswith(".json") and x != "INDEX.json"):
1831 | +                raw = json.load(open(os.path.join(d, f)))
1832 | +                expected = (raw.get("expected") or {}).get("verdict")
1833 | +                import run_exam_record as R
1834 | +                case = R.blind(raw)                        # exactly the harness's blinding (audit p2 C17)
1835 | +                t0 = time.time()
1836 | +                try:
1837 | +                    got = getattr(A, gate)(case)["verdict"]
1838 | +                except Exception as e:
1839 | +                    got = f"error:{type(e).__name__}"
1840 | +                secs += time.time() - t0
1841 | +                conf[(expected, got)] = conf.get((expected, got), 0) + 1
1842 | +            rows.append({"backend": backend, "gate": gate, "confusion": {f"{k[0]}->{k[1]}": v for k, v in conf.items()},
1843 | +                         "seconds": round(secs, 1)})
1844 | +    os.makedirs(OUT, exist_ok=True)
1845 | +    json.dump(rows, open(os.path.join(OUT, "verdicts.json"), "w"), indent=1)
1846 | +    for r in rows:
1847 | +        print(r)
1848 | +
1849 | +
1850 | +def main(argv=None):
1851 | +    ap = argparse.ArgumentParser()
1852 | +    ap.add_argument("role", choices=("mine", "verdicts"))
1853 | +    ap.add_argument("--run")
1854 | +    ap.add_argument("--corpus")
1855 | +    ap.add_argument("--legs", nargs="+", required=True)
1856 | +    ap.add_argument("--local", action="store_true", help="add the local gemma3:27b leg (the integrator, GPU0 lease)")
1857 | +    ap.add_argument("--judge")
1858 | +    a = ap.parse_args(argv)
1859 | +    (ab_mine if a.role == "mine" else ab_verdicts)(a)
1860 | +
1861 | +
1862 | +if __name__ == "__main__":
1863 | +    main()
1864 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
1865 | new file mode 100644
1866 | index 00000000..23c2775b
1867 | --- /dev/null
1868 | +++ b/tests/providers/test_providers.py
1869 | @@ -0,0 +1,230 @@
1870 | +#!/usr/bin/env python3
1871 | +"""pipeline/providers.py (law L-x): one interface, a chain per role, the run continues when a vendor is down, verdicts
1872 | +never on the writer's vendor or model family, every exchange recorded and replayable, an invalid reply never served
1873 | +again, spend guarded (reserve the upper bound, fail closed, free back-ends never stopped). Offline: fake back-ends."""
1874 | +import json
1875 | +import os
1876 | +import sys
1877 | +import tempfile
1878 | +import unittest
1879 | +
1880 | +HERE = os.path.dirname(os.path.abspath(__file__))
1881 | +REPO = os.path.dirname(os.path.dirname(HERE))
1882 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1883 | +import providers as P  # noqa: E402
1884 | +
1885 | +
1886 | +class Fake(P.Backend):
1887 | +    def __init__(self, name, vendor, answer=None, fail=None, usage=None, price=(10, 100), family=None):
1888 | +        spec = {"model": name.split(":", 1)[1], "price_usd_per_1m": list(price)}
1889 | +        if family:
1890 | +            spec["family"] = family
1891 | +        super().__init__(name, spec, "/nonexistent")
1892 | +        self.vendor, self.answer, self.fail, self.calls = vendor, answer, fail, 0
1893 | +        self._usage = usage or {"in": 1000, "out": 100}
1894 | +
1895 | +    def complete(self, prompt, max_tokens, seed, system=None):
1896 | +        self.calls += 1
1897 | +        if isinstance(self.fail, Exception):
1898 | +            raise self.fail
1899 | +        if self.fail:
1900 | +            raise P.Unavailable(self.fail)
1901 | +        return self.answer, dict(self._usage), 0.01
1902 | +
1903 | +
1904 | +class FakeSTT(P.STTBackend):
1905 | +    def __init__(self, name, vendor, result=None, fail=None):
1906 | +        super().__init__(name, {"model": name.split(":", 1)[1], "price_usd_per_min": 0.01}, "/nonexistent")
1907 | +        self.vendor, self.result, self.fail, self.calls = vendor, result, fail, 0
1908 | +
1909 | +    def transcribe(self, wav):
1910 | +        self.calls += 1
1911 | +        if self.fail:
1912 | +            raise P.Unavailable(self.fail)
1913 | +        return self.result, 0.01
1914 | +
1915 | +
1916 | +def router(tmp, backends, roles, **kw):
1917 | +    cfg = os.path.join(tmp, "cfg.json")
1918 | +    json.dump({"schema": "pp.providers/1",
1919 | +               "backends": {b.name: {"vendor": "openai", "model": b.model} for b in backends},
1920 | +               "roles": {r: {"chain": c} for r, c in roles.items()}}, open(cfg, "w"))
1921 | +    r = P.Router(cfg, env_path="/nonexistent", **kw)
1922 | +    r.backends = {b.name: b for b in backends}
1923 | +    return r
1924 | +
1925 | +
1926 | +def wav(tmp, seconds=2.0):
1927 | +    import wave
1928 | +    p = os.path.join(tmp, "a.wav")
1929 | +    with wave.open(p, "w") as w:
1930 | +        w.setnchannels(1)
1931 | +        w.setsampwidth(2)
1932 | +        w.setframerate(16000)
1933 | +        w.writeframes(b"\x00\x00" * int(16000 * seconds))
1934 | +    return p
1935 | +
1936 | +
1937 | +class TestRouter(unittest.TestCase):
1938 | +    def test_the_chain_fails_over_and_names_the_model_that_answered(self):
1939 | +        with tempfile.TemporaryDirectory() as d:
1940 | +            a = Fake("openai:x", "openai", fail="HTTP 429 insufficient_quota (final: account)")
1941 | +            b = Fake("anthropic:y", "anthropic", answer='{"ok": 1}')
1942 | +            r = router(d, [a, b], {"write": ["openai:x", "anthropic:y"]})
1943 | +            rep = r.call("write", "p")
1944 | +            self.assertEqual((rep.text, rep.backend, rep.vendor), ('{"ok": 1}', "anthropic:y", "anthropic"))
1945 | +            self.assertEqual(rep.tried[0][0], "openai:x")
1946 | +            r.call("write", "p2")
1947 | +            self.assertEqual(a.calls, 1)                    # down for the rest of the run: not asked again
1948 | +
1949 | +    def test_a_refused_request_skips_the_backend_for_that_call_only(self):
1950 | +        with tempfile.TemporaryDirectory() as d:
1951 | +            a = Fake("local:g", "local", fail=P.RequestRejected("prompt over the local context"), price=(0, 0))
1952 | +            b = Fake("xai:z", "xai", answer='{"v": 1}')
1953 | +            r = router(d, [a, b], {"verdict": ["local:g", "xai:z"]})
1954 | +            self.assertEqual(r.call("verdict", "a long prompt").backend, "xai:z")
1955 | +            self.assertNotIn("local:g", r.down)               # never down for the run
1956 | +            a.fail, a.answer = None, '{"v": 2}'
1957 | +            self.assertEqual(r.call("verdict", "a short prompt").backend, "local:g")
1958 | +
1959 | +    def test_a_verdict_never_runs_on_the_vendors_or_families_of_the_text_it_judges(self):
1960 | +        with tempfile.TemporaryDirectory() as d:
1961 | +            a = Fake("openai:x", "openai", answer="{}")
1962 | +            b = Fake("xai:z", "xai", answer='{"v": 1}')
1963 | +            g = Fake("heimdall:gem", "heimdall", answer='{"v": 2}', family="gemma")
1964 | +            r = router(d, [a, g, b], {"verdict": ["openai:x", "heimdall:gem", "xai:z"]})
1965 | +            rep = r.call("verdict", "p", avoid_vendor={"openai", "anthropic"}, avoid_family={"gemma"})
1966 | +            self.assertEqual(rep.backend, "xai:z")
1967 | +            self.assertEqual((a.calls, g.calls), (0, 0))
1968 | +            with self.assertRaises(P.ProviderError):
1969 | +                router(d, [a], {"verdict": ["openai:x"]}).call("verdict", "p", avoid_vendor="openai")
1970 | +
1971 | +    def test_every_backend_down_is_a_failed_role_never_a_pass(self):
1972 | +        with tempfile.TemporaryDirectory() as d:
1973 | +            r = router(d, [Fake("openai:x", "openai", fail="HTTP 503"), Fake("xai:z", "xai", fail="URLError")],
1974 | +                       {"mine": ["openai:x", "xai:z", "heimdall:missing"]})
1975 | +            with self.assertRaises(P.ProviderError) as cm:
1976 | +                r.call("mine", "p")
1977 | +            self.assertIn("HTTP 503", str(cm.exception))
1978 | +            self.assertIn("not in config backends", str(cm.exception))
1979 | +            with self.assertRaises(P.ProviderError):
1980 | +                r.call("unknown_role", "p")
1981 | +
1982 | +    def test_record_then_replay_offline_and_cached_is_not_replayed(self):
1983 | +        with tempfile.TemporaryDirectory() as d:
1984 | +            a = Fake("anthropic:y", "anthropic", answer='{"ok": 1}')
1985 | +            rec = os.path.join(d, "rec")
1986 | +            r = router(d, [a], {"write": ["anthropic:y"]}, record_dir=rec)
1987 | +            first = r.call("write", "p", seed=7)
1988 | +            self.assertEqual((first.replayed, first.cached), (False, False))
1989 | +            again = r.call("write", "p", seed=7)              # a live run served the recording: cached, not replayed
1990 | +            self.assertEqual((again.replayed, again.cached, a.calls), (False, True, 1))
1991 | +            rp = router(d, [Fake("anthropic:y", "anthropic", fail="must not be called")], {"write": ["anthropic:y"]},
1992 | +                        record_dir=rec, replay=True)
1993 | +            rep = rp.call("write", "p", seed=7)
1994 | +            self.assertEqual((rep.text, rep.backend, rep.replayed), ('{"ok": 1}', "anthropic:y", True))
1995 | +            with self.assertRaises(P.ReplayMiss):
1996 | +                rp.call("write", "p", seed=8)               # another attempt is its own exchange
1997 | +
1998 | +    def test_a_rejected_reply_is_asked_again_never_served_again(self):
1999 | +        with tempfile.TemporaryDirectory() as d:
2000 | +            a = Fake("anthropic:y", "anthropic", answer="not json")
2001 | +            r = router(d, [a], {"write": ["anthropic:y"]}, record_dir=os.path.join(d, "rec"))
2002 | +            bad = r.call("write", "p")
2003 | +            self.assertTrue(r.reject(bad, "not one JSON object"))
2004 | +            a.answer = '{"ok": 1}'
2005 | +            self.assertEqual((r.call("write", "p").text, a.calls), ('{"ok": 1}', 2))
2006 | +
2007 | +    def test_the_spend_guard_reserves_the_upper_bound_and_never_passes_the_limit(self):
2008 | +        with tempfile.TemporaryDirectory() as d:
2009 | +            led = os.path.join(d, "SPEND.json")
2010 | +            a = Fake("openai:x", "openai", answer="{}", usage={"in": 400_000, "out": 0})        # $4.00 a call
2011 | +            r = router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=10)
2012 | +            p = "p" * 400_000                                     # upper bound ~ $4.00 in + $0.20 out
2013 | +            r.call("write", p)
2014 | +            r.call("write", p)
2015 | +            with self.assertRaises(P.SpendLimit):
2016 | +                r.call("write", p)                                # 8.00 + 4.20 > 10: refused BEFORE it runs
2017 | +            d_ = json.load(open(led))
2018 | +            self.assertEqual((d_["calls"], a.calls, d_["reserved"]), (2, 2, {}))
2019 | +            self.assertLessEqual(d_["usd_estimate"], 10)
2020 | +            free = Fake("local:g", "local", answer="{}", price=(0, 0))
2021 | +            rf = router(d, [free], {"write": ["local:g"]}, spend_path=led, limit_usd=1)
2022 | +            self.assertEqual(rf.call("write", "p").backend, "local:g")      # a free back-end is never stopped
2023 | +
2024 | +    def test_an_unreadable_ledger_stops_every_paid_call_and_a_failed_call_releases_its_reservation(self):
2025 | +        with tempfile.TemporaryDirectory() as d:
2026 | +            led = os.path.join(d, "SPEND.json")
2027 | +            open(led, "w").write("{ corrupt")
2028 | +            r = router(d, [Fake("openai:x", "openai", answer="{}")], {"write": ["openai:x"]}, spend_path=led)
2029 | +            with self.assertRaises(P.SpendLimit):
2030 | +                r.call("write", "p")
2031 | +            self.assertEqual(open(led).read(), "{ corrupt")      # never overwritten from zero
2032 | +            os.remove(led)
2033 | +            r2 = router(d, [Fake("openai:x", "openai", fail="HTTP 503")], {"write": ["openai:x"]}, spend_path=led)
2034 | +            with self.assertRaises(P.ProviderError):
2035 | +                r2.call("write", "p")
2036 | +            self.assertEqual(json.load(open(led))["reserved"], {})
2037 | +
2038 | +    def test_transcription_runs_its_own_chain_with_failover_record_and_replay(self):
2039 | +        with tempfile.TemporaryDirectory() as d:
2040 | +            res = {"text": "Bitcoin is not going to zero.", "segments": [{"speaker": "A", "start": 0.1, "end": 1.9,
2041 | +                                                                           "text": "Bitcoin is not going to zero."}]}
2042 | +            a = FakeSTT("openai_stt:t", "openai", fail="HTTP 429 insufficient_quota (final: account)")
2043 | +            b = FakeSTT("elevenlabs_stt:s", "elevenlabs", result=res)
2044 | +            rec = os.path.join(d, "rec")
2045 | +            r = router(d, [a, b], {"transcribe": ["openai_stt:t", "elevenlabs_stt:s"]}, record_dir=rec)
2046 | +            got, rep = r.transcribe("transcribe", wav(d))
2047 | +            self.assertEqual((got, rep.backend, rep.tried[0][0]), (res, "elevenlabs_stt:s", "openai_stt:t"))
2048 | +            rp = router(d, [FakeSTT("openai_stt:t", "openai", fail="x"), FakeSTT("elevenlabs_stt:s", "elevenlabs",
2049 | +                                                                                 fail="must not be called")],
2050 | +                        {"transcribe": ["openai_stt:t", "elevenlabs_stt:s"]}, record_dir=rec, replay=True)
2051 | +            got2, rep2 = rp.transcribe("transcribe", wav(d))
2052 | +            self.assertEqual((got2, rep2.replayed), (res, True))
2053 | +
2054 | +    def test_the_local_backend_without_its_gpu_lease_is_unavailable(self):
2055 | +        b = P.LocalBackend("local:gemma3:27b", {"model": "gemma3:27b"}, "/nonexistent", llm=None)
2056 | +        with self.assertRaises(P.Unavailable):
2057 | +            b.complete("p", 10, 7)
2058 | +
2059 | +    def test_the_shipped_config_keeps_every_verdict_off_every_possible_writer(self):
2060 | +        cfg = json.load(open(P.CONFIG))
2061 | +        be = cfg["backends"]
2062 | +        for name, spec in be.items():
2063 | +            self.assertTrue(spec.get("family"), name)                           # law L-x: model family named
2064 | +            if spec["vendor"] == "heimdall":
2065 | +                self.assertTrue(spec.get("base_url"), name)
2066 | +        for role, spec in cfg["roles"].items():
2067 | +            if role == "trend_brief":
2068 | +                self.assertIn("fallback", spec)              # the free local baseline is its second back-end
2069 | +                continue
2070 | +            self.assertGreaterEqual(len(spec["chain"]), 2, role)
2071 | +            for b in spec["chain"]:
2072 | +                self.assertIn(b, be, (role, b))
2073 | +        local = [n for n, s in be.items() if s["vendor"] == "local"]
2074 | +        self.assertEqual(cfg["roles"]["mine"]["chain"][0], local[0])             # Ultron first (L-x)
2075 | +        self.assertTrue(all(be[b]["vendor"].endswith("_stt") for b in cfg["roles"]["transcribe"]["chain"]))
2076 | +        for role in ("fidelity_verdict", "context_verdict", "viewer_takeaway", "coherence_verdict"):
2077 | +            for writer in cfg["roles"]["angle_write"]["chain"]:
2078 | +                w = be[writer]
2079 | +                left = [b for b in cfg["roles"][role]["chain"]
2080 | +                        if be[b]["vendor"] != w["vendor"] and be[b]["family"] != w["family"]]
2081 | +                self.assertGreaterEqual(len(left), 2, (role, writer))           # still a chain, never one back-end
2082 | +        miners = cfg["roles"]["mine"]["chain"]
2083 | +        for m in miners:
2084 | +            left = [b for b in cfg["roles"]["exclusion_verdict"]["chain"] if b != m]
2085 | +            self.assertGreaterEqual(len(left), 2, m)
2086 | +
2087 | +    def test_role_model_maps_failures_into_select_by_id(self):
2088 | +        import select_by_id as SB
2089 | +        with tempfile.TemporaryDirectory() as d:
2090 | +            r = router(d, [Fake("openai:x", "openai", fail="HTTP 503")], {"story": ["openai:x"]})
2091 | +            with self.assertRaises(SB.ModelError):
2092 | +                P.RoleModel(r, "story").complete("p", 10, 7)
2093 | +            ok = router(d, [Fake("xai:z", "xai", answer='{"story": [], "claim": null}')], {"story": ["xai:z"]})
2094 | +            text, meta = P.RoleModel(ok, "story").complete("p", 10, 7)
2095 | +            self.assertEqual(meta["backend"], "xai:z")
2096 | +
2097 | +
2098 | +if __name__ == "__main__":
2099 | +    unittest.main()
2100 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
