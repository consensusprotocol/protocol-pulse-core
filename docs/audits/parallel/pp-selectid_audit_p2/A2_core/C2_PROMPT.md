# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-p2
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## CLAUDE-FABLE-5-2 — CYCLE 1 OUTPUT
# claude-fable-5-2 (effort high) 469 s stop_reason=end_turn usage=in 87345 / out 44522

**Reviewer note:** I am Claude (Anthropic), not one of the three models named in the header. Scope limits: the diff contains no test files and no `pinned.py` / R7 patch, so Q5 is only answerable for `moments_gate_adapter.py` and `package_pin.py`. Laws L-m through L-x are cited by the code but are not in the law list I was given, and `canon.py`, `eligibility.py`, `select_by_id.py` and `story_semantics.quote_data` are not shown. Findings that depend on them say so.

## Scores

| Q | Score | Summary |
|---|---|---|
| Q1 fail-open | 35 | Explicit failures fail closed, but several gates pass when the model answers with nothing, and one gate is optional. |
| Q2 vendor separation / L-x | 70 | `avoid_vendor` holds through failover, rewrites and precomputed step A; L-x is broken by hard-coded vendors, and per-request errors trigger silent failover. |
| Q3 verbatim / model text | 75 | Clip text is by id only (assuming `Span.text` is verbatim); title, caption and VO are always gated; the angle is ungated and attribution is by channel, not speaker. |
| Q4 deterministic rules | 40 | Many concrete false passes and false rejects (table below). |
| Q5 tests / R7 | 15, on the two visible files only | Tests and R7 are not in the diff; the pin stamps gates as passed with literals. |

## P0

**P0-1. The pin asserts gates passed with constants** (`package_pin.py`)
`"checks": {"vo_fidelity_ok": True, "context_integrity_ok": True, "models": pk.get("models")}`
- `to_pin` never reads `pk["checks"]`.
- Failing input: any dict with the right keys (a plain-VO package, a hand-edited package, one that never went through `build`) is pinned with both flags `True`.
- Any R7 refusal keyed on these flags would be vacuous.

**P0-2. The blind fidelity verdict passes on an empty answer** (`vo_fidelity.check_verdict`)
`for c in obj["claims"]: ...` then `return {"ok": not v, ...}`
- Failing input: the reply `{"claims": []}` gives `ok: True`. A reply covering only the intro and skipping the title also passes.
- `write_v2` accepts `"cites": []` on every line, since `any(c not in ids for c in ln["cites"])` is false for an empty list.
- NEEDS_SOURCE only fires on a detected number, name, quote, attribution or time word.
- Combined: intro "The government is banning self-custody." with no cites and an empty verdict passes both layers.

**P0-3. The exclusion gate the exam certifies is not run in production** (`moments.py`, `package.py`, `moments_gate_adapter.py`)
- The adapter says "These are the SAME gates the packager runs (… `moments.exclusion_verdict`)".
- In the diff, `exclusion_verdict` is called only from the adapter.
- Production uses `"excluded": sorted(set(m["risk"]) & set(HARD_RISKS))`, which is the miner's own flags on the moment it just picked.
- `time_sensitive` in `usable()` rests on the same self-report.
- Failing input: the miner returns `"risk": []` for an accusation against a named person; nothing else in `build` screens it.

**P0-4. The second recognition pass (L-v 2) is optional, partial and one-directional** (`package.build`, `transcript_truth.py`)
- **Optional:** `if truth_dir:` with default `None`. The package is returned with no marker that the pass did not run.
- **Skipped for plain VO:** `out["plain"].append(pk3)` happens before the truth block, and `out["package"] = (out["packages"] or out["plain"] or [None])[0]`. So the plain fallback can ship unverified.
- **Partial:** `if any(TT.critical_tokens(sg["text"])[k] for k in ("numbers", "negations"))`. A segment with only names gets neither the name check nor diarisation.
- **One-directional:** `[n for n in a["negations"] if n not in bset]`. Whisper "Bitcoin is going to zero" against a second pass "is not going to zero" is never even sent for checking.
- **Set membership over the padded window:** a "not" in the ±1.5 s neighbour satisfies a missing one inside the selection.
- **Unmeasured passes:** `speaker_turns` returns `turn_change_inside: None` for "not measured", and `build` treats `None` as clean.

## P1

**P1-1. Step B relations pass when unanswered** (`context_integrity.check_contexts`)
`for rel in B["relations"]:`
- Nothing requires every pair to be answered.
- Failing input: `"relations": []` means FALSE_RELATION can never fire.

**P1-2. The speaker is always the channel** (`package.integrity`)
`"speaker": s["channel"], "names": [s["channel"]]`
- Step A's JSON has no "who is speaking" field, although the docstring promises one.
- Failing input: a guest's whole moment on the Natalie Brunell channel. No speaker change inside, own sincere view, so the VO "Natalie Brunell says …" passes ATTRIBUTION, and the blind verdict is told she is the speaker.

**P1-3. The attribution format the prompt recommends is unbound** (`vo_fidelity._attributions`, `WRITE_V2`)
- `WRITE_V2` recommends `"Saifedean Ammous: no authority…"`. `_attributions` knows only the verb list and "according to".
- Failing inp

## CLAUDE-OPUS-5-5 — CYCLE 1 OUTPUT
# claude-opus-5-5 (effort high) 414 s stop_reason=end_turn usage=in 87345 / out 42066

# Pre-merge audit: pp-selectid-p2, A_core/STEP.diff

**Reviewer:** Claude (Anthropic). I am not one of the three models the template lists, so please label this review accordingly in the audit record.

**Scope:** Only the diff is reviewed. Citations use the diff's line numbers (`L####`). Many symbols are defined outside the diff (`E.*`, `SB.*`, `canon.*`, `story_semantics.quote_data`, `E.TAIL_S`), and the findings say so where that matters. The stack notes about Flask, DB indexes, CSS and 1000 users do not apply: this diff has no route, model or UI.

---

## Scores (0-100, higher = safer / more compliant)

| Q | Score | One-line reason |
|---|---|---|
| Q1 Fail-open | **40** | No exception becomes a pass. But empty or partial model replies pass (fidelity verdict, step-B relations). The second recognition pass is optional, selective and skipped on the plain path. `package_pin` asserts checks it never reads. |
| Q2 Vendor separation / L-x | **72** | `avoid_vendor` is threaded correctly, including the precomputed step-A re-check. However, `transcript_truth.py` hard-codes the OpenAI model and endpoint outside the config, and `"openai"` is hard-coded in `package.py`. |
| Q3 Verbatim / model text | **80** | Clip text is the source span. The miner reason, angle and trend text never reach audience slots ungated. The weakness is that "gated" depends on Q1/Q4 holes. |
| Q4 Deterministic rules | **35** | Several concrete false passes (Title Case titles disable NAME; attribution is case-sensitive; numbers bind to the wrong speaker; HISTORY and PRESENT are too broad). Several concrete false rejects ("exposure", "Short-term", "Sell-offs", "breaking", "answer"). |
| Q5 Tests / R7 | **10** | The diff contains no tests and no R7 `pinned.py` patch, so neither can be verified. The exam adapter does not exercise production paths (PRICE_NOW, DUPLICATE, precomputed A, truth pass). Production does not run the exclusion gate the exam measures. |

---

## Q1: Fail-open in the gates

**What holds:**
- Every caught exception produces a failure, never a pass:
  - `prescreen`: `except Exception`, recorded as `STEP_A_UNAVAILABLE` (L1315-1318).
  - `check_contexts`: produces a `CONTEXT_UNAVAILABLE` violation (L257-260).
  - `VF.check`: produces `VERDICT_UNAVAILABLE` (L2856-2858).
  - `coherence`: returns `(False, …)` (L1499-1500).
  - Truth pass: an error drops the moment (L1666-1671).
  - `exclusion_verdict`: excludes (L884-886).
- `ReplayMiss` is not caught inside `integrity`, so it crashes `build`. That is a crash, not a pass.
- Step A and step C label sets are exact (L193, L255). Every certainty, view and retraction test is an equality against the passing value, so unknown values fail.

**What leaks:**
1. **The fidelity verdict passes on an empty or partial `claims` list.** This is the P0 below.
2. **Step B may omit relation pairs.** A missing pair is never checked (P1).
3. **The second recognition pass can be skipped while a package ships:**
   - `truth_dir=None` is the default (L1554, L1658).
   - The pass is triggered only by numbers or negations, never names (L1661).
   - "Not measured" speakers pass (L1670-1671, L2339).
   - The plain-VO path skips it entirely (L1637-1651).
   - If no segment has numbers or negations, `truth=[]` and the package ships with `transcript_truth: []`. The check "ran on nothing".
4. **`package_pin` emits `"vo_fidelity_ok": True, "context_integrity_ok": True` unconditionally** (L1758-1759).
5. **The runtime gate runs on an estimate whose arithmetic is internally inconsistent** (P1).
6. **The plain-VO fallback** is fully integrity-gated (L1642-1645), but it skips coherence (by design) and the truth pass (not by design).

## Q2: Vendor separation and L-x

**What holds:**
- `integrity(…, wr.vendor, None if wr.vendor in a_vendors else a_by, …)` (L1609, L1642) re-runs step A when the actual writer, including a fallback writer on a rewrite, shares a vendor with any step-A batch.
- Fidelity (L2852), step B (L240), step C (L251) and coherence (L1491) all pass `avoid_vendor=writer_vendor`.
- Each rewrite attempt recomputes `wr`.
- The router never turns a contract violation into failover. It returns text, and parsing failures belong to the caller. Only `Unavailable` advances the chain (L2193-2196).

**What leaks:**
- `transcript_truth.second_pass` hard-codes `model="gpt-4o-transcribe-diarize"`, the OpenAI URL and `ENV` (L2262, L2288, L2302). It bypasses the router entirely: no failover, no spend ledger, no record/replay. This violates L-x: "No role's code names a vendor or a model: only this file does."
- `_writer_vendor` falls back to `return "openai"` (L1706), and `prescreen(…, writer_vendor="openai")` (L1290).
- Vendor is not the same as model family. Heimdall hosts deepseek, qwen and gemma. Today's chains do not collide, but nothing prevents a future chain from pairing `local:gemma3` (writer) with `heimdall:google/gemma-4-

## CLAUDE-SONNET-5-5 — CYCLE 1 OUTPUT
# claude-sonnet-5-5 (effort high) 290 s stop_reason=end_turn usage=in 87345 / out 37492

# Audit: pp-selectid-p2 (moments, package, providers)

Scope: only the diff shown. The tests, `pinned.py`, `eligibility.py`, `canon.py`, `story_semantics.quote_data` and `select_by_id` are not in it, so anything depending on them is marked uncertain.

## Scores

| Question | Score | Why |
|---|---|---|
| Q1 fail-open | 38 | The main control flow is sound, but the blind verdict accepts zero claims and the second recognition pass is optional and one-directional. |
| Q2 vendor separation / L-x | 66 | The writer-vendor handling is sound. The router's permanent "down" marking and some hard-coded vendors are real defects. |
| Q3 verbatim / model text | 58 | Clip text is verbatim, but hard exclusions rest on the miner's own self-report and the angle text is injected raw. |
| Q4 deterministic rules | 40 | Several concrete false passes and false rejects (below). |
| Q5 tests / wiring | 30 | Mostly unverifiable from the diff. `package_pin` hard-codes its gate results, and the adapter makes must-fail cases pass vacuously. |

## FINDINGS

### P0

**P0-1. The blind fidelity verdict passes with zero or partial claims** (`vo_fidelity.check_verdict`).
```python
obj["claims"] ... v = [] ... return {"ok": not v, "claims": obj["claims"], "violations": v}
```
- Failing input: the model replies `{"claims": []}`. `v` stays empty, so `ok` is True.
- The same happens if it lists one benign claim for the intro and omits the title and caption.
- Code never requires that each non-connective slot has at least one claim.
- Impact: layer (b) can be bypassed entirely by an omission. Layer (a) is then the only defence, and it has the holes in Q4 (including Title Case lines skipping NAME).
- Also, a "yes" is only checked for verbatim-ness of the cited words, not for support. `texts` includes `manifest`, so any claim can "cite" the manifest text `"contains clips from"`.

**P0-2. The L-v 2 second recognition pass is optional, one-directional and skipped on the plain path** (`package.build`).
- **Optional by default:** the pass only runs under `if truth_dir:`, and the default is `truth_dir=None`. With the default, a package ships with no second pass.
- **Trigger reads the first transcript only:**
  ```python
  if any(TT.critical_tokens(sg["text"])[k] for k in ("numbers", "negations")):
  ```
  If the first ASR dropped the only "not" or number, the segment is never sent to the second pass.
  - Names are not in the trigger.
  - Speaker-change detection therefore only runs for segments that already contain a number or negation.
- **Comparison is one-directional and set-based** (`transcript_truth.compare`):
  ```python
  bset = set(b); ... [n for n in a["negations"] if n not in bset]
  ```
  - It only checks that the first transcript's critical tokens appear somewhere in the second.
  - Failing input: the first text says "will rise". The second says "will not rise". `not` is absent from `a`, so nothing is checked.
  - Presence anywhere in the window also satisfies a token. First "will not rise" against second "will rise… not sure" passes.
- **"Not measured" counts as pass:**
  ```python
  or (t.get("speakers") or {}).get("turn_change_inside")
  ```
  `None` is falsy and is not treated as bad.
- **Plain-VO path skips it:** the plain package goes into `out["plain"]` and returns as `out["package"]` without coherence or truth. It never reaches the `truth_dir` block.

### P1

**P1-1. The runtime gate underestimates, by my arithmetic** (`package.py`).
```python
FIXED_S = round(E.TAIL_S - SIGNOFF_WORDS / WPS, 2)
vo_s = vo_words / WPS + len(pk["vo"]["signoff"].split()) / WPS - SIGNOFF_WORDS / WPS
```
- The sign-off VO duration is subtracted twice, once in `FIXED_S` and once in `vo_s`. The estimate therefore omits the sign-off VO (about 18/2.6 ≈ 6.9 s).
- Whatever `E.TAIL_S` contains, the estimate is low.
- Packages of about 70–77 s real length can pass `rt_ok`.
- `content_range` inherits the same offset.
- WPS is also an assumed constant. The estimate is not the rendered runtime.

**P1-2. The independent exclusion verdict is not wired in this diff.**
- `moments.exclusion_verdict` is called only from `moments_gate_adapter.exclusion`.
- `package.usable` relies on `m.get("excluded")`, which `record()` sets from the miner's own `risk` list: `sorted(set(m["risk"]) & set(HARD_RISKS))`.
- Failing input: the mining model omits `"accusation"` or `"imperative"` and the moment ships.
- The `package.py` docstring ("an exclusion failure drops the moment") has no code behind it here. If it is wired elsewhere, I can't see it.

**P1-3. `Router.down` is permanent and content-triggered** (`providers.Router.call`).
```python
except Unavailable as e:
    self.down[name] = str(e)
```
- `LocalBackend.complete` raises `Unavailable("prompt over the local context …")` for one oversized prompt. That marks local down for the whole run, contradicting "Ultron first".
- Any HTTP 4xx on one bad re

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (xAI, medley key) 55 s usage=64964

**Q1: 72/100**  
No package reaches `build()`'s final `out["package"]` (or the pinned artefact) while a hard gate is failed, unreadable, or produced an "uncertain"/exception outcome. `integrity()` requires `fid["ok"] and not dup and ctx_["ok"] and rt_ok`; `check_contexts`, `check_verdict`, `coherence` and the transcript-truth pass all turn any exception, `ReplayMiss`, missing field, or "uncertain" into a violation and `ok=False` (see `context_integrity:257-259`, `vo_fidelity:2856-2858`, `moments_gate_adapter:970-971/988-989/1000-1001`, `package:1617-1618/1630-1636/1642-1645/1670-1676`). Plain-VO fallback only ships after its own `g3["ok"]` (lines 1638-1649). The only theoretical hole is an uncaught Python exception escaping the outer `try` in `build()` (none visible in diff).

**Q2: 88/100**  
Verdict roles (`fidelity_verdict`, `context_verdict`, `viewer_takeaway`, `coherence_verdict`) never run on the writer's vendor: `prescreen`/`integrity`/`coherence` pass `writer_vendor=_writer_vendor()` (first backend in the `angle_write` chain, lines 1702-1706) and `Router.call(..., avoid_vendor=writer_vendor)` skips any matching vendor (providers:2167-2169). Chains live only in `model_providers.json`; no role hard-codes a vendor/model. Failover cannot silently accept a contract violation—`check_written`, `check_moments`, `_strict`, `check_angles`, `check_verdict` raise `ValueError`/`Rejected` treated as failure (lines 801, 1287, 1583, 1605, 2856). ProviderError on a completely unavailable verdict chain becomes a gate violation, never a pass.

**Q3: 93/100**  
Clips are source sentences verbatim (`moments.record:776 "text": sp.text`, `package.assemble:1247 "text": m["text"]`, `package_pin:1739 "approved_text": s["text"]`; `candidate_rows` only punctuated sentence-ready spans). Miner `reason`, angle sentences, verdict claims, trend brief never enter clip/VO/title/caption—writer output is fed to `vo_fidelity.check` + `context_integrity.check_contexts` before any package is kept (`build:1608-1610/1678`). Model text only appears in forensic fields (`mined`, `checks`, `models`).

**Q4: 55/100**  
- **False PASS (misleading line accepted):** `vo_fidelity.names_of` + `_title_case` returns `[]` for any Title-Case line (>=3 long words, >70 % capitalised). Concrete input: title `"MicroStrategy Buys Another 5000 BTC"` when no clip contains "MicroStrategy" and the manifest does not list it—deterministic NAME rule is skipped, ATTRIBUTION never triggers (no verb match), PRICE_NOW passes if level is inside tolerance of a current_level. Blind verdict must catch it; if the model omits the claim it ships.  
- **False REJECT (honest line blocked):** `check_deterministic:2751-2754` flags RELATION on any "both agree" phrasing even when both cited segments are from the *same* video (one conversation) and the blind verdict would accept. Concrete: bridge `"Both agree the ETF outflow is accelerating"` citing two segments from the identical YouTube video—violates even though law L-s only forbids cross-video false relation.  
- `price_now` tolerance=0.05 can false-pass a stale rounded figure (e.g. line says 74000 when universe's fresh level is 74210). `duplicates` 60 % share test on a short 8-word clip can false-reject a legitimate bridge that re-uses the hook's opening canonical tokens.

**Q5: 45/100**  
`moments_gate_adapter` correctly maps to the live gates, returns `"fail"`/`"exclude"` on `ReplayMiss` or malformed case (lines 970, 988, 1000), so adversarial tests fail closed. No vacuous assertions visible. R7 wiring (`package_pin.to_pin`) produces a `protocol_pulse.pinned_story.v1` that hard-codes `"vo_fidelity_ok": True, "context_integrity_ok": True` (lines 1758-1759) regardless of the incoming `pk["checks"]`; the downstream factory therefore cannot refuse an ungated package. Plain-pin path is unchanged but the new moments path can emit a lying PIN. (pinned.py patch itself not in diff, so certainty limited.)

**FINDINGS**

**P1: pipeline/package_pin.py:1758**  
```python
"checks": {"vo_fidelity_ok": True, "context_integrity_ok": True, ...
```
A package with `integrity["vo_fidelity"]["violations"]` or `context["violations"]` non-empty can still be pinned with `ok=True`. Concrete failing input: feed `build()` a package that failed `VERDICT_NO` on the caption and call `to_pin(pk, "test-run")`—the resulting MOMENTS_PIN.json claims both gates passed. Violates L-j ("exactly the bytes the gates measured") and L-m (fail-closed).

**P2: pipeline/vo_fidelity.py:2644 (`_title_case`) + 2654**  
```python
if _title_case(text): return []
...
if _title_case(text):
    return []
```
Title-case suppression defeats the NAME rule for any headline that introduces a speaker not present in the cited clips. Concrete: title `"Michael Saylor Warns of Incoming Crash"` when no moment contains "Saylor" and manifest does not list him—deterministic layer silent; only blind verdict can catch it. Measured fal

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

## THE CODE NOW: chunk A2_core of the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_p2/A2_core/STEP.diff (1959 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | new file mode 100644
   3 | index 00000000..c7dc68cc
   4 | --- /dev/null
   5 | +++ b/pipeline/context_integrity.py
   6 | @@ -0,0 +1,501 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/context_integrity.py — CONTEXT INTEGRITY (law L-s, orchestrator 2026-11-12 '02:30'; a HARD gate, separate
   9 | +from VO fidelity): a verbatim whole sentence can still misrepresent its speaker once lifted. Per selected moment:
  10 | +
  11 | +INPUTS  the source's transcript from >= CONTEXT_BEFORE_S before the moment (pulled back to the question it answers, when
  12 | +        one ends within CONTEXT_MAX_BEFORE_S) to >= CONTEXT_AFTER_S after it, the video title, the selected sentences,
  13 | +        and the finished package (order, adjacent clips, VO, title, caption).
  14 | +STEP A  (context only, the package hidden; role "context_verdict", never the writer's vendor): who is speaking, whose
  15 | +        view it is (own sincere / attributed / hypothetical / conditional / sarcastic / question / reading aloud / ad
  16 | +        read), every pronoun and this / that / today with its referent and whether it lies inside the selection, any
  17 | +        governing condition or time frame, any retraction or qualification in the window, the proposition asserted.
  18 | +STEP B  (the package only; role "viewer_takeaway", never the writer's vendor): what an ordinary viewer concludes each
  19 | +        speaker asserts, how certain, and any implied relation (agreeing / answering / rebutting / one conversation)
  20 | +        between speakers.
  21 | +STEP C  (role "context_verdict"): does A's in-context proposition entail B's takeaway, same polarity, no stronger
  22 | +        certainty?
  23 | +DECIDE  (code) PASS only if: own sincere assertion; no speaker change inside; every referent and condition inside the
  24 | +        selection; no retraction; C entails, same polarity, not stronger; no implied relation between speakers of
  25 | +        different source videos. Any "uncertain" fails (law L-m).
  26 | +REPAIR  dropping the MOMENT and repacking (the law also permits extending the clip by whole locked sentences; that is
  27 | +        not built); never writing the missing context into the VO (L-s).
  28 | +"""
  29 | +import itertools
  30 | +import json
  31 | +import re
  32 | +
  33 | +import eligibility as E
  34 | +
  35 | +CONTEXT_BEFORE_S = 90.0
  36 | +CONTEXT_MAX_BEFORE_S = 180.0
  37 | +CONTEXT_AFTER_S = 60.0
  38 | +EXCERPT_MAX = 12000                # characters of one escaped window; a longer one is CONTEXT_TOO_LONG (never cut)
  39 | +A_KEYS = ("label", "speaker_changes_inside", "view", "referents", "conditions", "retraction", "time_ok", "proposition",
  40 | +          "certainty", "speaker_is", "speaker_evidence")
  41 | +VIEWS = ("own_sincere", "attributed", "hypothetical", "conditional", "sarcastic", "question", "reading_aloud",
  42 | +         "ad_read", "joke", "uncertain")
  43 | +CERTAINTY = ("certain", "likely", "possible", "speculative", "uncertain")
  44 | +RELATIONS = ("none", "agreeing", "answering", "rebutting", "same_conversation", "uncertain")
  45 | +YNU = ("yes", "no", "uncertain")
  46 | +
  47 | +
  48 | +def window(src, k0, k1, before=CONTEXT_BEFORE_S, after=CONTEXT_AFTER_S, max_before=CONTEXT_MAX_BEFORE_S):
  49 | +    """Sentence indices (a, b) of the context window around the moment k0..k1: AT LEAST `before` s earlier (back to
  50 | +    the question the moment answers, when one ends within `max_before` s) and AT LEAST `after` s later, in whole
  51 | +    sentences, or to the transcript's edge (audit p2 C11: the window was at most those spans)."""
  52 | +    S, T = src.sentences, src.tokens
  53 | +    t0 = E._time(T[S[k0][0]], "start")
  54 | +    t1 = E._time(T[S[k1][1]], "end")
  55 | +    a = k0
  56 | +    while a > 0 and t0 is not None:
  57 | +        cur = E._time(T[S[a][0]], "start")
  58 | +        if cur is not None and cur <= t0 - before:
  59 | +            break                                       # the window already starts >= `before` s earlier
  60 | +        prev = E._time(T[S[a - 1][0]], "start")
  61 | +        if prev is not None and prev < t0 - max_before:
  62 | +            break
  63 | +        a -= 1
  64 | +    q = a
  65 | +    while q > 0 and t0 is not None and (E._time(T[S[q - 1][0]], "start") or -1e18) >= t0 - max_before:
  66 | +        q -= 1
  67 | +        if (T[S[q][1]].get("word") or "").rstrip().endswith("?"):
  68 | +            a = min(a, q)
  69 | +            break
  70 | +    b = k1
  71 | +    while b + 1 < len(S) and t1 is not None:
  72 | +        cur = E._time(T[S[b][1]], "end")
  73 | +        if cur is not None and cur >= t1 + after:
  74 | +            break                                       # the window already ends >= `after` s later
  75 | +        b += 1
  76 | +    return a, b
  77 | +
  78 | +
  79 | +def mark(parts):
  80 | +    """[(sentence text, selected?)] -> the excerpt: every sentence escaped (story_semantics.quote_data, no limit),
  81 | +    the selection wrapped in <selected> AFTER escaping, so the markers survive (audit p2 C11)."""
  82 | +    from story_semantics import quote_data
  83 | +    out = []
  84 | +    for t, sel in parts:
  85 | +        q = quote_data(t, 10 ** 9)
  86 | +        out.append(f"<selected>{q}</selected>" if sel else q)
  87 | +    return " ".join(out)
  88 | +
  89 | +
  90 | +def _window_text(src, k0, k1):
  91 | +    a, b = window(src, k0, k1)
  92 | +    S, T = src.sentences, src.tokens
  93 | +    return mark([(E.spoken(T[S[k][0]:S[k][1] + 1]), k0 <= k <= k1) for k in range(a, b + 1)]), (a, b)
  94 | +
  95 | +
  96 | +STEP_A = """You read transcripts of Bitcoin videos. For each EXCERPT below, the sentences inside <selected> are a clip
  97 | +that may be shown on its own. Use the whole excerpt (what comes before and after) to judge the selected words. You do
  98 | +not know how the clip will be used.
  99 | +
 100 | +{excerpts}
 101 | +
 102 | +For each excerpt answer:
 103 | +- "speaker_changes_inside": does the speaker change inside the selected words? "yes" / "no" / "uncertain"
 104 | +- "view": whose view the selected words express: "own_sincere" (the speaker's own sincere assertion), "attributed"
 105 | +  (someone else's view, quoted or reported), "hypothetical", "conditional" (true only under a condition), "sarcastic",
 106 | +  "question", "reading_aloud" (reading a post or article), "ad_read", "joke", or "uncertain"
 107 | +- "referents": every pronoun or pointing word in the selected words (it, they, this, that, he, she, today, here...)
 108 | +  that points at something specific, with what it refers to; "inside": true if the selected words themselves give
 109 | +  its antecedent or the predicate that completes it (an ellipsis completed by an earlier selected sentence: "It's not
 110 | +  Bitcoin that's getting hacked. It's other intermediaries." = other intermediaries are getting hacked), or it points
 111 | +  only at a general topic the clip presupposes; "inside": false if a listener needs the words before or after the
 112 | +  selection; "changes_assertion": "yes" if resolving it differently would change WHAT THE SPEAKER ASSERTS, "no" if
 113 | +  not, "uncertain". Leave out words that point at nothing outside: a dummy "it" ("it's raining", "it's not X that
 114 | +  ...", where X is in the selection), and a generic "we" / "you" / "they" meaning people in general
 115 | +- "conditions": any condition or time frame that governs the selected words, and whether it is INSIDE them
 116 | +- "retraction": "none", or what the speaker later in the excerpt WITHDRAWS, REVERSES, CORRECTS or MATERIALLY LIMITS
 117 | +  about the selected words ("actually I misspoke", "that said, I don't believe that", "but that only holds if ...").
 118 | +  A later elaboration or warning that is CONSISTENT with a condition already stated inside the selected words is not
 119 | +  a retraction ("none"); it would be one if the selected words had dropped that condition
 120 | +- "time_ok": "yes" if every time word in the selected words (today, now, this week, just, recently, a "current"
 121 | +  price) still holds on the show date given when the video was published (both on the excerpt), or there is none;
 122 | +  "no" if it is stale; "uncertain"
 123 | +- "proposition": in one sentence, what the speaker asserts in the selected words, read in context
 124 | +- "certainty": "certain", "likely", "possible", "speculative" or "uncertain"
 125 | +- "speaker_is": "host" if the excerpt shows that the speaker of the selected words is the channel's own host,
 126 | +  "guest" if it shows a guest or another person speaking them, "uncertain" otherwise; "speaker_evidence": the exact
 127 | +  words of the excerpt that show it (copied exactly, e.g. the host's own "welcome back to my channel"), or ""
 128 | +Return ONLY this JSON object: {{"excerpts": [{{"label": "...", "speaker_changes_inside": "...", "view": "...",
 129 | +"referents": [{{"word": "...", "refers_to": "...", "inside": true, "changes_assertion": "no"}}], "conditions":
 130 | +[{{"text": "...", "inside": true}}],
 131 | +"retraction": "none", "time_ok": "yes", "proposition": "...", "certainty": "...", "speaker_is": "...",
 132 | +"speaker_evidence": "..."}}]}}"""
 133 | +
 134 | +STEP_B = """You are an ordinary viewer of a 60-second video. Here is everything the video shows and says, in order.
 135 | +
 136 | +{package}
 137 | +
 138 | +For each clip say what you conclude its speaker asserts, how certain they sound, and whether it is positive, negative
 139 | +or neutral about its subject. What you conclude a speaker asserts INCLUDES whatever the title, the caption or the
 140 | +voice-over ATTRIBUTES to that speaker ("X: Y" or "X says Y" tells you that X asserts Y). The voice-over's own opinion,
 141 | +framing, question or takeaway, attributed to nobody, is the host's, not the speaker's. Each clip's label is the text inside label="..." after the word CLIP: use exactly that
 142 | +label in "label" and in "labels", never the speakers' names. Labels: {labels}. Then, for each pair of clips, say whether the video presents their speakers as RELATED TO EACH
 143 | +OTHER: one answering the other, one rebutting the other, one agreeing WITH the other ("X agrees", "Y backs that up",
 144 | +"both say"), or the two being in one conversation. Two speakers who each state their own view on the same subject,
 145 | +each credited, are NOT related ("none") unless the video says or implies that they respond to each other.
 146 | +Return ONLY this JSON object: {{"takeaways": [{{"label": "...", "asserts": "...", "certainty": "certain" | "likely" |
 147 | +"possible" | "speculative" | "uncertain", "polarity": "positive" | "negative" | "neutral"}}], "relations":
 148 | +[{{"labels": ["...", "..."], "relation": "none" | "agreeing" | "answering" | "rebutting" | "same_conversation" |
 149 | +"uncertain"}}]}}"""
 150 | +
 151 | +STEP_C = """For each pair below, A is what a speaker asserted, read in its original context; CLIP is the speaker's exact
 152 | +words as the viewer hears them; B is what a viewer of a short video concludes the same speaker asserted (from the clip
 153 | +and from whatever the video's title, caption or voice-over attributes to the speaker). The video's own words are:
 154 | +
 155 | +{vo}
 156 | +
 157 | +Answer for each pair:
 158 | +- "entails": does A support what the CLIP'S OWN WORDS assert? Judge the speaker's in-context assertion against the
 159 | +  clip's words as heard, not two paraphrases. A difference of scope is "no" ONLY when the context LIMITS the claim in a
 160 | +  way the clip's words drop ("in this one case", "for small holders only", "back in 2021") and that limit changes what
 161 | +  a reasonable viewer concludes; a presupposed topic or occasion is not such a limit. "yes", "no" or "uncertain".
 162 | +- "dropped_limit": when "entails" is "no", that limit in the context's own words; otherwise "".
 163 | +- "added_by": the EXACT words of the video's title, caption or voice-over that ATTRIBUTE to this speaker something A
 164 | +  does not support (e.g. a title "Swan Bitcoin: the AI bubble is about to pop" when the speaker said investors could
 165 | +  lose money), or "" when none do. The host's own commentary, attributed to nobody, attributes nothing.
 166 | +- "same_polarity": do A and B have the same polarity? "yes", "no" or "uncertain".
 167 | +- "stronger_certainty": is B more certain than A? "yes", "no" or "uncertain"; and "raising_words": when it is, the
 168 | +  EXACT words of the video's voice-over, title or caption above that make the speaker sound more certain, or "" when no
 169 | +  such words exist (the speaker's own words alone).
 170 | +
 171 | +{pairs}
 172 | +
 173 | +Return ONLY this JSON object: {{"pairs": [{{"label": "...", "entails": "...", "dropped_limit": "...",
 174 | +"added_by": "...", "same_polarity": "...", "stronger_certainty": "...", "raising_words": "..."}}]}}"""
 175 | +
 176 | +
 177 | +def _q(t, n):
 178 | +    from story_semantics import quote_data
 179 | +    return quote_data(t, n)
 180 | +
 181 | +
 182 | +def package_view(package):
 183 | +    """The package as a viewer meets it, in the RENDERER's order (render16.py / render_vertical.py segment lists): the
 184 | +    hook, then the VO intro, then each clip with any VO bridge after it (after_clip, including after the last clip),
 185 | +    then the sign-off; the title and caption."""
 186 | +    out = [f"TITLE: {_q(package['title'], 200)}", f"CAPTION: {_q(package['caption'], 400)}"]
 187 | +    vo = package["vo"]
 188 | +    bridges = list(vo.get("bridges") or [])
 189 | +    after = list(vo.get("bridges_after_clip") or range(1, len(bridges) + 1))   # bridge j follows clip after[j]
 190 | +    by_clip = {a_: b_ for a_, b_ in zip(after, bridges)}
 191 | +    for i, seg in enumerate(package["segments"]):                            # segment 0 is the hook, i = clip index
 192 | +        out.append(f'CLIP label="{seg["label"]}" (on screen: {_q(seg["channel"], 80)}): "{_q(seg["text"], 900)}"')
 193 | +        if i == 0 and vo.get("intro"):
 194 | +            out.append(f"VOICE-OVER: {_q(vo['intro'], 400)}")
 195 | +        if i and by_clip.get(i):
 196 | +            out.append(f"VOICE-OVER: {_q(by_clip[i], 400)}")
 197 | +    if vo.get("signoff"):
 198 | +        out.append(f"VOICE-OVER: {_q(vo['signoff'], 300)}")
 199 | +    return "\n".join(out)
 200 | +
 201 | +
 202 | +def _strict(raw, top, item_keys):
 203 | +    obj = json.loads(raw.strip())
 204 | +    if not isinstance(obj, dict) or set(obj) != set(top):
 205 | +        raise ValueError(f"keys must be exactly {sorted(top)}")
 206 | +    for k, keys in item_keys.items():
 207 | +        if not isinstance(obj[k], list):
 208 | +            raise ValueError(f"'{k}' must be a list")
 209 | +        for it in obj[k]:
 210 | +            if not isinstance(it, dict) or set(it) != set(keys):
 211 | +                raise ValueError(f"each item of '{k}' needs exactly {sorted(keys)}")
 212 | +    return obj
 213 | +
 214 | +
 215 | +def contexts_from_sources(package, sources, now=None):
 216 | +    """{label: {"text": the window with <selected> marks, "title", "channel", "published", "show_date", "window"}}."""
 217 | +    out = {}
 218 | +    for seg in package["segments"]:
 219 | +        src = sources[seg["video_id"]]
 220 | +        text, win = _window_text(src, seg["k0"], seg["k1"])
 221 | +        out[seg["label"]] = {"text": text, "title": src.title or "", "channel": seg["channel"], "window": win,
 222 | +                             "published": str(src.published_at or "")[:16],
 223 | +                             "show_date": now.strftime("%Y-%m-%d") if now else None}
 224 | +    return out
 225 | +
 226 | +
 227 | +def check(router, package, sources, writer_vendor, seed=7):
 228 | +    """The pipeline's entry: contexts built from the sources' records (every segment is a moment)."""
 229 | +    return check_contexts(router, package, contexts_from_sources(package, sources), writer_vendor, seed)
 230 | +
 231 | +
 232 | +def step_a(router, contexts, writer_vendor, seed=7, writer_family=None):
 233 | +    """Step A alone (context only, the package hidden): {label: item} for exactly the given labels, and the back-end.
 234 | +    Raises ValueError / ProviderError when it cannot be had or read."""
 235 | +    labels = list(contexts)
 236 | +    for lb in labels:
 237 | +        if len(contexts[lb]["text"]) > EXCERPT_MAX:
 238 | +            raise ValueError(f"CONTEXT_TOO_LONG: {lb}'s window is {len(contexts[lb]['text'])} characters (> "
 239 | +                             f"{EXCERPT_MAX}); never truncated")
 240 | +    ex = [f'<excerpt label="{lb}" channel="{_q(contexts[lb]["channel"], 80)}" video_title='
 241 | +          f'"{_q(contexts[lb].get("title") or "", 160)}" published="{contexts[lb].get("published") or "unknown"}" '
 242 | +          f'show_date="{contexts[lb].get("show_date") or "unknown"}">{contexts[lb]["text"]}</excerpt>'
 243 | +          for lb in labels]
 244 | +    ra = router.call("context_verdict", STEP_A.format(excerpts="\n".join(ex)), 4000, seed, avoid_vendor=writer_vendor,
 245 | +                     avoid_family=writer_family)
 246 | +    try:
 247 | +        A = _strict(ra.text, {"excerpts"}, {"excerpts": A_KEYS})
 248 | +        a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
 249 | +        if set(a_by) != set(labels) or len(A["excerpts"]) != len(labels):
 250 | +            raise ValueError(f"step A must answer exactly the labels {labels}")
 251 | +    except (ValueError, TypeError):
 252 | +        if hasattr(router, "reject"):
 253 | +            router.reject(ra)
 254 | +        raise
 255 | +    for lb in labels:
 256 | +        a_by[lb] = dict(a_by[lb], backend=ra.backend, replayed=bool(getattr(ra, "replayed", False)),
 257 | +                        speaker_verified=speaker_verified(a_by[lb], contexts[lb]["text"]))
 258 | +    return a_by, ra.backend
 259 | +
 260 | +
 261 | +def speaker_verified(a, excerpt_text):
 262 | +    """Law L-v 1: the speaker of the selected words is the channel's own host only with step A's "host" AND its
 263 | +    evidence a verbatim run (>= 3 canonical tokens) of the excerpt. -> bool."""
 264 | +    import canon
 265 | +    ev = a.get("speaker_evidence")
 266 | +    if a.get("speaker_is") != "host" or not isinstance(ev, str):
 267 | +        return False
 268 | +    et = canon.canon_tokens(ev)
 269 | +    xt = canon.canon_tokens(re.sub(r"</?selected>", " ", excerpt_text or ""))
 270 | +    return len(et) >= 3 and any(xt[i:i + len(et)] == et for i in range(len(xt) - len(et) + 1))
 271 | +
 272 | +
 273 | +def referent_outside(r):
 274 | +    """Orchestrator 06:00 ruling 3: a referent is OUTSIDE only if the selected words give no antecedent or completing
 275 | +    predicate ("inside" not true) AND resolving it differently would change what the speaker asserts (anything but an
 276 | +    explicit "no"; an uncertain or missing answer fails, law L-m)."""
 277 | +    return not isinstance(r, dict) or (r.get("inside") is not True and r.get("changes_assertion") != "no")
 278 | +
 279 | +
 280 | +def a_failures(a):
 281 | +    """The step-A half of the decision rule for one moment: [rule, ...] (empty = its own context passes)."""
 282 | +    out = []
 283 | +    if a.get("speaker_changes_inside") != "no":
 284 | +        out.append("SPEAKER_CHANGE")
 285 | +    if a.get("view") != "own_sincere":
 286 | +        out.append("NOT_OWN_SINCERE")
 287 | +    refs, conds = a.get("referents"), a.get("conditions")
 288 | +    if not isinstance(refs, list) or any(referent_outside(r) for r in refs):
 289 | +        out.append("REFERENT_OUTSIDE")
 290 | +    if not isinstance(conds, list) or any(not isinstance(c, dict) or c.get("inside") is not True for c in conds):
 291 | +        out.append("CONDITION_OUTSIDE")
 292 | +    if a.get("retraction") != "none":
 293 | +        out.append("RETRACTION")
 294 | +    if a.get("time_ok") != "yes":                   # law L-v 3; a missing field is a failure (L-l, audit p2 C11)
 295 | +        out.append("STALE_TIME")
 296 | +    if a.get("certainty") not in CERTAINTY[:4]:
 297 | +        out.append("UNCERTAIN")
 298 | +    return out
 299 | +
 300 | +
 301 | +def clips_alone(package):
 302 | +    """The package with every VO line, the title and the caption removed: the clips as heard on their own (the
 303 | +    baseline for STRONGER, orchestrator 05:25 item 3)."""
 304 | +    return dict(package, title="", caption="", vo={"intro": "", "bridges": [], "bridges_after_clip": [], "signoff": ""})
 305 | +
 306 | +
 307 | +def vo_words(package):
 308 | +    """The video's own words for step C: the VO lines in the renderer's order, the title, the caption."""
 309 | +    vo = package["vo"]
 310 | +    lines = [f"TITLE: {_q(package.get('title') or '', 200)}", f"CAPTION: {_q(package.get('caption') or '', 400)}"]
 311 | +    if vo.get("intro"):
 312 | +        lines.append(f"VOICE-OVER after the hook: {_q(vo['intro'], 400)}")
 313 | +    for a_, t in zip(list(vo.get("bridges_after_clip") or []), list(vo.get("bridges") or [])):
 314 | +        lines.append(f"VOICE-OVER after clip {a_}: {_q(t, 400)}")
 315 | +    return "\n".join(lines)
 316 | +
 317 | +
 318 | +def raising_words_ok(words, package):
 319 | +    """Step C's cited raising words are a verbatim run (>= 2 canonical tokens) of the video's own VO, title or caption
 320 | +    (orchestrator 06:00 ruling 3)."""
 321 | +    import canon
 322 | +    if not isinstance(words, str) or not words.strip():
 323 | +        return False
 324 | +    wt = canon.canon_tokens(words)
 325 | +    vo = package["vo"]
 326 | +    texts = [package.get("title") or "", package.get("caption") or "", vo.get("intro") or ""] + list(vo.get("bridges") or [])
 327 | +    return len(wt) >= 2 and any(any(tt[i:i + len(wt)] == wt for i in range(len(tt) - len(wt) + 1))
 328 | +                                for tt in (canon.canon_tokens(t) for t in texts))
 329 | +
 330 | +
 331 | +def outside_words(words, window_text):
 332 | +    """Step C's named limit is the context's OWN words: a verbatim run (>= 2 canonical tokens) of the excerpt OUTSIDE
 333 | +    the selected sentences (orchestrator 06:22 ruling 5: a limit the clip's words drop)."""
 334 | +    import canon
 335 | +    if not isinstance(words, str) or not words.strip():
 336 | +        return False
 337 | +    outside = re.sub(r"<selected>.*?</selected>", " | ", window_text or "", flags=re.S)
 338 | +    wt = canon.canon_tokens(words)
 339 | +    for part in outside.split(" | "):
 340 | +        pt = canon.canon_tokens(part)
 341 | +        if len(wt) >= 2 and any(pt[i:i + len(wt)] == wt for i in range(len(pt) - len(wt) + 1)):
 342 | +            return True
 343 | +    return False
 344 | +
 345 | +
 346 | +def attributes_to(words, seg):
 347 | +    """The cited words name this segment's show (channel) or its stated speaker: an attribution to it."""
 348 | +    import canon
 349 | +    wt = canon.canon_tokens(words or "")
 350 | +    for name in (seg.get("channel"), seg.get("speaker")):
 351 | +        nt = canon.canon_tokens(name or "")
 352 | +        nt2 = [re.sub(r"['’]s$", "", t) for t in nt]
 353 | +        wt2 = [re.sub(r"['’]s$", "", t) for t in wt]
 354 | +        if nt2 and any(wt2[i:i + len(nt2)] == nt2 for i in range(len(wt2) - len(nt2) + 1)):
 355 | +            return True
 356 | +    return False
 357 | +
 358 | +
 359 | +def _rank(c):
 360 | +    return CERTAINTY.index(c) if c in CERTAINTY else len(CERTAINTY)
 361 | +
 362 | +
 363 | +def check_contexts(router, package, contexts, writer_vendor, seed=7, a_by=None, writer_family=None):
 364 | +    """package: {"segments": [{"label", "video_id", "channel", "text"}], "vo": {"intro", "bridges",
 365 | +    "bridges_after_clip", "signoff"}, "title", "caption"}; contexts: {label: {"text" (the window, the moment inside
 366 | +    <selected>), "title", "channel"}} for the segments to judge (a segment without a context is judged only through the
 367 | +    package: relations). a_by: step A items already screened (package-independent), by label.
 368 | +    -> {"ok", "segments", "relations", "violations", "backends", "measured"}. A step that cannot be had or read fails
 369 | +    and leaves the gate NOT measured (L-m); step B must rate EVERY pair of clips (audit p2 C5)."""
 370 | +    import providers as P
 371 | +    segs = package["segments"]
 372 | +    labels = [s["label"] for s in segs if s["label"] in contexts]
 373 | +    all_labels = [s["label"] for s in segs]
 374 | +    out = {"segments": {}, "relations": [], "violations": [], "backends": {}, "measured": False, "replayed": False}
 375 | +    V = lambda label, rule, detail: out["violations"].append({"segment": label, "rule": rule, "detail": detail})
 376 | +    if not labels:
 377 | +        V("-", "CONTEXT_UNAVAILABLE", "no segment has its source context")
 378 | +        out["ok"] = False
 379 | +        return out
 380 | +    r0 = rb = rc = None
 381 | +    try:
 382 | +        if a_by is None:
 383 | +            a_by, out["backends"]["A"] = step_a(router, {lb: contexts[lb] for lb in labels}, writer_vendor, seed,
 384 | +                                                writer_family)
 385 | +        else:
 386 | +            missing = [lb for lb in labels if not isinstance(a_by.get(lb), dict) or set(A_KEYS) - set(a_by[lb])]
 387 | +            if missing:
 388 | +                raise ValueError(f"precomputed step A lacks {missing} or a field")
 389 | +            a_by = {lb: a_by[lb] for lb in labels}
 390 | +            out["backends"]["A"] = {lb: a_by[lb].get("backend") or "precomputed (unnamed)" for lb in labels}
 391 | +        lab_list = ", ".join(all_labels)
 392 | +        r0 = router.call("viewer_takeaway", STEP_B.format(package=package_view(clips_alone(package)), labels=lab_list),
 393 | +                         3000, seed)
 394 | +        out["backends"]["B0"] = r0.backend
 395 | +        B0 = _strict(r0.text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
 396 | +                                                           "relations": ("labels", "relation")})
 397 | +        b0_by = {t["label"]: t for t in B0["takeaways"] if isinstance(t.get("label"), str)}
 398 | +        if not set(labels) <= set(b0_by):
 399 | +            raise ValueError(f"step B (clips alone) must answer at least {labels}")
 400 | +        rb = router.call("viewer_takeaway", STEP_B.format(package=package_view(package), labels=lab_list), 3000, seed,
 401 | +                         avoid_vendor=writer_vendor, avoid_family=writer_family)
 402 | +        out["backends"]["B"] = rb.backend
 403 | +        B = _strict(rb.text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
 404 | +                                                          "relations": ("labels", "relation")})
 405 | +        b_by = {t["label"]: t for t in B["takeaways"] if isinstance(t.get("label"), str)}
 406 | +        if not set(labels) <= set(b_by) or any(not isinstance(b_by[lb].get("asserts"), str) for lb in labels):
 407 | +            raise ValueError(f"step B must answer at least {labels}")
 408 | +        pairs_want = {frozenset(p) for p in itertools.combinations(all_labels, 2)}
 409 | +        got = []
 410 | +        for rel in B["relations"]:
 411 | +            labs = rel.get("labels")
 412 | +            if not isinstance(labs, list) or len(labs) != 2 or not all(isinstance(x, str) for x in labs) or \
 413 | +                    labs[0] == labs[1] or rel.get("relation") not in RELATIONS:
 414 | +                raise ValueError(f"step B relation out of contract: {json.dumps(rel)[:160]}")
 415 | +            got.append(frozenset(labs))
 416 | +        if len(got) != len(set(got)) or set(got) != pairs_want:
 417 | +            raise ValueError(f"step B must rate every pair of clips exactly once ({len(pairs_want)} pairs, got "
 418 | +                             f"{len(set(got))} distinct of {len(got)})")
 419 | +        text_of = {sg["label"]: sg["text"] for sg in segs}
 420 | +        pairs = "\n".join(f'<pair label="{lb}"><A>{_q(a_by[lb]["proposition"], 400)} (certainty: '
 421 | +                          f'{a_by[lb]["certainty"]})</A><CLIP>{_q(text_of[lb], 900)}</CLIP><B>{_q(b_by[lb]["asserts"], 400)}'
 422 | +                          f' (certainty: {b_by[lb]["certainty"]})</B></pair>' for lb in labels)
 423 | +        rc = router.call("context_verdict", STEP_C.format(pairs=pairs, vo=vo_words(package)), 2000, seed,
 424 | +                         avoid_vendor=writer_vendor, avoid_family=writer_family)
 425 | +        out["backends"]["C"] = rc.backend
 426 | +        C = _strict(rc.text, {"pairs"}, {"pairs": ("label", "entails", "dropped_limit", "added_by", "same_polarity",
 427 | +                                                   "stronger_certainty", "raising_words")})
 428 | +        c_by = {c["label"]: c for c in C["pairs"] if isinstance(c.get("label"), str)}
 429 | +        if set(c_by) != set(labels) or len(C["pairs"]) != len(labels):
 430 | +            raise ValueError(f"step C must answer exactly the labels {labels}")
 431 | +    except (P.ProviderError, P.SpendLimit, ValueError, KeyError, TypeError) as e:
 432 | +        for r_ in (r0, rb, rc):
 433 | +            if r_ is not None and isinstance(e, (ValueError, KeyError, TypeError)) and hasattr(router, "reject"):
 434 | +                router.reject(r_)
 435 | +        V("-", "CONTEXT_UNAVAILABLE", f"{type(e).__name__}: {str(e)[:240]}")
 436 | +        out["ok"] = False
 437 | +        return out
 438 | +    out["measured"] = True
 439 | +    out["replayed"] = any(bool(getattr(r_, "replayed", False)) for r_ in (r0, rb, rc))
 440 | +    vid = {s["label"]: s["video_id"] for s in segs}
 441 | +    segs_by = {s["label"]: s for s in segs}
 442 | +    for lb in labels:
 443 | +        a, b, c = a_by[lb], b_by[lb], c_by[lb]
 444 | +        out["segments"][lb] = {"A": a, "B": b, "B0": b0_by[lb], "C": c, "window": (contexts[lb] or {}).get("window")}
 445 | +        for rule in a_failures(a):
 446 | +            if rule == "REFERENT_OUTSIDE":
 447 | +                for r in a["referents"] if isinstance(a["referents"], list) else [None]:
 448 | +                    if referent_outside(r):
 449 | +                        V(lb, rule, f"{(r or {}).get('word')!r} -> {(r or {}).get('refers_to')!r} (changes the "
 450 | +                                    f"assertion: {(r or {}).get('changes_assertion')!r})")
 451 | +            elif rule == "CONDITION_OUTSIDE":
 452 | +                for cnd in a["conditions"] if isinstance(a["conditions"], list) else [None]:
 453 | +                    if not isinstance(cnd, dict) or cnd.get("inside") is not True:
 454 | +                        V(lb, rule, f"{(cnd or {}).get('text')!r}")
 455 | +            else:
 456 | +                V(lb, rule, {"SPEAKER_CHANGE": f"speaker change inside: {a.get('speaker_changes_inside')}",
 457 | +                             "NOT_OWN_SINCERE": f"view: {a.get('view')}",
 458 | +                             "RETRACTION": str(a.get("retraction"))[:200],
 459 | +                             "STALE_TIME": f"time words stale on the show date: {a.get('time_ok')}",
 460 | +                             "UNCERTAIN": f"certainty A {a.get('certainty')}"}.get(rule, rule))
 461 | +        if b["certainty"] not in CERTAINTY[:4]:
 462 | +            V(lb, "UNCERTAIN", f"certainty B {b['certainty']}")
 463 | +        limit = c.get("dropped_limit") if isinstance(c.get("dropped_limit"), str) else ""
 464 | +        if c["entails"] == "uncertain" or (c["entails"] != "yes" and outside_words(limit, contexts[lb]["text"])):
 465 | +            V(lb, "NOT_ENTAILED", f"entails: {c['entails']}; the context's limit the clip drops: {limit[:200]!r}")
 466 | +        elif c["entails"] != "yes":                  # orchestrator 06:22 ruling 5: a scope difference without a limit
 467 | +            out.setdefault("notes", []).append(
 468 | +                f"{lb}: step C answers entails {c['entails']!r} but names no limit in the context's OWN words outside "
 469 | +                f"the clip (named: {limit[:120]!r}): a NOTE, not NOT_ENTAILED (orchestrator 06:22 ruling 5)")
 470 | +        added = c.get("added_by")
 471 | +        if isinstance(added, str) and added.strip():
 472 | +            if raising_words_ok(added, package) and attributes_to(added, segs_by[lb]):
 473 | +                V(lb, "NOT_ENTAILED", f"the video's words {added!r} attribute to this speaker more than they asserted "
 474 | +                                      f"in context")
 475 | +            else:
 476 | +                out.setdefault("notes", []).append(
 477 | +                    f"{lb}: step C cites {added[:120]!r} as adding to the speaker, but those words are not the video's "
 478 | +                    f"own or do not attribute anything to this speaker (no show or speaker name): a NOTE")
 479 | +        if c["same_polarity"] != "yes":
 480 | +            V(lb, "POLARITY", f"same polarity: {c['same_polarity']}")
 481 | +        if c["stronger_certainty"] == "uncertain":
 482 | +            V(lb, "STRONGER", "stronger certainty: uncertain")
 483 | +        elif c["stronger_certainty"] != "no":
 484 | +            cited = raising_words_ok(c.get("raising_words"), package)
 485 | +            alone_certain = b0_by[lb]["certainty"] == "certain"      # the ruling's words: "the clip alone reads as certain"
 486 | +            if cited and not alone_certain:
 487 | +                V(lb, "STRONGER", f"stronger certainty: the video's words {c['raising_words']!r} make the clip sound "
 488 | +                                  f"{b['certainty']} (in context {a['certainty']}; the clip alone "
 489 | +                                  f"{b0_by[lb]['certainty']})")
 490 | +            else:                                     # orchestrator 05:25 item 3 and 06:00 ruling 3
 491 | +                out.setdefault("notes", []).append(
 492 | +                    f"{lb}: step C reads the viewer's takeaway as firmer than the speaker in context ({a['certainty']} -> "
 493 | +                    f"{b['certainty']}) but " + ("cites no words of the video that raise it" if not cited else
 494 | +                                                  "the clip ALONE already sounds certain") +
 495 | +                    ": a NOTE, not STRONGER (orchestrator 06:00 ruling 3: a STRONGER failure cites the exact VO / "
 496 | +                    "title words that raise the certainty; an attribution verb firmer than the clip's hedge is "
 497 | +                    "vo_fidelity's HEDGE rule)")
 498 | +    for rel in B["relations"]:
 499 | +        labs, kind = rel["labels"], rel["relation"]
 500 | +        if kind == "none":
 501 | +            continue
 502 | +        if kind == "uncertain" or vid[labs[0]] != vid[labs[1]]:
 503 | +            V("+".join(labs), "FALSE_RELATION", f"the package makes them look {kind}; they are not one conversation")
 504 | +    out["relations"] = B["relations"]
 505 | +    out["judged"] = labels
 506 | +    out["ok"] = not out["violations"]
 507 | +    return out
 508 | diff --git a/pipeline/moments.py b/pipeline/moments.py
 509 | new file mode 100644
 510 | index 00000000..eb78ab32
 511 | --- /dev/null
 512 | +++ b/pipeline/moments.py
 513 | @@ -0,0 +1,395 @@
 514 | +#!/usr/bin/env python3
 515 | +"""pipeline/moments.py — STEP 1 MINE (law L-q, orchestrator 2026-11-12 '01:55'): the cycle's best MOMENTS, by sentence id,
 516 | +never rewritten. A moment is 1-3 consecutive whole sentences of ONE source record that makes sense heard on its own.
 517 | +
 518 | +1 LOCAL PRE-FILTER (free, deterministic, no model): sources of the window (published since the last cycle, plus the
 519 | +  recent window RECENT_H, inside the 72 h universe; opted-out channels never: pipeline/optout.json), eligible as
 520 | +  sources (partner, identity, upload, current); rows = punctuated, injection-free sentences within one sentence of a
 521 | +  sentence that names Bitcoin; an ad read (sponsor markers) is never offered; rows are taken round-robin across videos,
 522 | +  word-timed and on-screen-capable videos first, inside the model's context budget (one call per chunk).
 523 | +2 ONE BATCHED MINING PASS (role "mine" through pipeline/providers.py, law L-x: local gemma first): the model sees
 524 | +  numbered rows and answers ids only: {"moments": [{"range": [a, b], "scores": {7 axes, ints 0-5}, "names_person",
 525 | +  "risk": [enum], "topics": [taxonomy ids], "reason"}]}. The REPLY contract is strict and never repaired (law L-l):
 526 | +  exact keys, integer scores, closed enums, ranges of existing consecutive ids of one video, no overlap; anything else
 527 | +  is rejected and asked again with the reason. Each accepted moment is then judged on its own by eligibility (a
 528 | +  moment is its own statement): failures are recorded on the moment (excluded from packaging), never edited.
 529 | +3 DETERMINISTIC RANKING (law L-u): hook_first_2s + quotable + surprising_fact + stance + stakes + stands_alone
 530 | +  - 2 x contempt_outrage - soft-risk penalties + trend weight x trend match (SHADOW: weight 0, law L-w 4); "named
 531 | +  figure" is a fact, never a positive axis; hard-exclusion risks never rank. Ties by moment_id.
 532 | +
 533 | +Durations come from locked word timing (timing "word"); a caption / segment duration is only a FLAGGED estimate
 534 | +(duration_estimate_s) and never feeds a runtime. The model's `reason` is forensic only: it never enters a prompt or
 535 | +anything audience-facing. Output records follow the contract published in docs/audits/parallel/pp-selectid_STATE.md
 536 | +(pp.moment/1).
 537 | +"""
 538 | +import hashlib
 539 | +import json
 540 | +import os
 541 | +import re
 542 | +import time
 543 | +from dataclasses import replace
 544 | +
 545 | +import eligibility as E
 546 | +import select_by_id as SB
 547 | +import sentence_law
 548 | +
 549 | +HERE = os.path.dirname(os.path.abspath(__file__))
 550 | +RECENT_H = 24.0                    # "plus a recent window": the last 24 h, beside what is new since the last cycle
 551 | +MAX_MOMENTS_PER_CALL = 12
 552 | +MINE_MAX_TOKENS = 3000
 553 | +ATTEMPTS = 3
 554 | +AXES = ("hook_first_2s", "quotable", "surprising_fact", "stance", "stakes", "stands_alone", "contempt_outrage")
 555 | +POSITIVE = AXES[:6]
 556 | +HARD_RISKS = ("accusation", "partner_attack", "imperative", "guaranteed_return", "single_source_breaking", "ad_read",
 557 | +              "third_party_media")                                  # law L-u: never auto-selected
 558 | +SOFT_RISKS = {"price_prediction": 2, "doom": 2, "politics_non_btc": 3, "time_sensitive": 0}   # down-weights (L-u)
 559 | +RISKS = HARD_RISKS + tuple(SOFT_RISKS)
 560 | +CONTEMPT_WEIGHT = 2                # contempt / outrage is a PENALTY (law L-u)
 561 | +TREND_WEIGHT = 0.0                 # SHADOW (law L-w 4): logged, zero weight; when enabled, capped at ~10-15 % of score
 562 | +REASON_MAX = 200
 563 | +AD_MARKERS = re.compile(r"\b(sponsor(ed)?|brought to you by|use (my |our )?code|promo code|link in the description|"
 564 | +                        r"affiliate link|today's sponsor|check out .{0,30}(dot com|\.com))\b", re.I)
 565 | +OPTOUT = os.path.join(HERE, "optout.json")
 566 | +
 567 | +
 568 | +class Rejected(SB.Rejected):
 569 | +    pass
 570 | +
 571 | +
 572 | +def optout_ids(path=OPTOUT):
 573 | +    """The opt-out registry (PBX 02:35: no outreach; a simple file the selector honours): channel ids never mined or
 574 | +    packaged. A missing file = nobody opted out; an unreadable one fails closed (raises)."""
 575 | +    if not os.path.exists(path):
 576 | +        return frozenset()
 577 | +    with open(path) as f:
 578 | +        d = json.load(f)
 579 | +    ids = d.get("channel_ids") if isinstance(d, dict) else None
 580 | +    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
 581 | +        raise ValueError(f"{path}: expected {{'channel_ids': [str, ...]}}")
 582 | +    return frozenset(ids)
 583 | +
 584 | +
 585 | +def moment_id(src, w0, w1):
 586 | +    return hashlib.sha256(f"{src.video_id}|{src.transcript_sha256}|{w0}|{w1}".encode()).hexdigest()[:20]
 587 | +
 588 | +
 589 | +# ── 1 local pre-filter ──
 590 | +
 591 | +def window_sources(sources, ctx, since=None, recent_h=RECENT_H, optout=frozenset()):
 592 | +    """The cycle's sources: published since `since` (an aware datetime: new since the last cycle) or inside the recent
 593 | +    window, eligible as sources, not opted out; on-screen-capable (word-timed, sentence-ready, layout-eligible) first,
 594 | +    then newest first. Returns (sources, {video_id: why not})."""
 595 | +    keep, skipped = [], {}
 596 | +    for src in sources:
 597 | +        if src.channel_id in optout:
 598 | +            skipped[src.video_id] = "opted out (pipeline/optout.json)"
 599 | +            continue
 600 | +        r = E.eligible(src, replace(ctx, role="evidence"))
 601 | +        if not r.ok:
 602 | +            skipped[src.video_id] = r.why()
 603 | +            continue
 604 | +        age = r.facts.get("age_h")
 605 | +        new = since is not None and E._parse_time(src.published_at) is not None and E._parse_time(src.published_at) >= since
 606 | +        if not (new or (age is not None and age <= recent_h)):
 607 | +            skipped[src.video_id] = (f"outside the window ({'?' if age is None else f'{age:.1f}'} h old, not new since "
 608 | +                                     f"the last cycle)")
 609 | +            continue
 610 | +        keep.append(src)
 611 | +    on = lambda s: (s.timing == "word" and E.sentence_ready(s) and E.layout_ok(ctx.channel(s.channel_id)))
 612 | +    keep.sort(key=lambda s: (not on(s), E.age_hours(s.published_at, ctx.now) or 1e9, s.video_id))
 613 | +    return keep, skipped
 614 | +
 615 | +
 616 | +def candidate_rows(src):
 617 | +    """Sentence indices of one source worth offering: punctuated, injection-free, not an ad read, within one sentence
 618 | +    of a sentence that names Bitcoin (a range of 1-3 sentences can then name it)."""
 619 | +    import story_semantics as sm
 620 | +    S, T = src.sentences, src.tokens
 621 | +    text = [E.spoken(T[a:b + 1]) for a, b in S]
 622 | +    btc = [E.names_bitcoin(t) for t in text]
 623 | +    rows = []
 624 | +    for k, (a, b) in enumerate(S):
 625 | +        if not any(btc[max(0, k - 1):k + 2]):
 626 | +            continue
 627 | +        if AD_MARKERS.search(text[k]) or sm.injection_markers(text[k]):
 628 | +            continue
 629 | +        if not (E.ends_statement(T[b].get("word")) or (T[b].get("word") or "").rstrip().endswith("?")):
 630 | +            continue
 631 | +        if not all(sentence_law.is_punctuated(T, i) for i in ([a - 1] if a > 0 else []) + [b]):
 632 | +            continue
 633 | +        rows.append(k)
 634 | +    return rows
 635 | +
 636 | +
 637 | +def tables(sources, ctx, budget_chars):
 638 | +    """Round-robin over the sources (no video crowds out the others) into Tables of at most budget_chars of row text."""
 639 | +    per = [(s, candidate_rows(s)) for s in sources]
 640 | +    order, i = [], 0
 641 | +    while any(i < len(ks) for _, ks in per):
 642 | +        for s, ks in per:
 643 | +            if i < len(ks):
 644 | +                order.append((s, ks[i]))
 645 | +        i += 1
 646 | +    chunks, cur, used = [], [], 0
 647 | +    for s, k in order:
 648 | +        cost = len(SB._q(E.Span(s, k, k).text, 600)) + 40
 649 | +        if cur and used + cost > budget_chars:
 650 | +            chunks.append(cur)
 651 | +            cur, used = [], 0
 652 | +        cur.append((s, k))
 653 | +        used += cost
 654 | +    if cur:
 655 | +        chunks.append(cur)
 656 | +    out = []
 657 | +    for ch in chunks:                                  # each table: its sources' rows in sentence order
 658 | +        srcs = list(dict.fromkeys(s for s, _ in ch))
 659 | +        items = [(s, k, False) for s in srcs for k in sorted(k for t, k in ch if t is s)]
 660 | +        out.append(SB.Table(items))
 661 | +    return out
 662 | +
 663 | +
 664 | +# ── 2 the mining call ──
 665 | +
 666 | +MINE_PROMPT = """You pick MOMENTS for 60-second Bitcoin videos built from other channels' own words: the lines a viewer
 667 | +would stop scrolling for. Below are numbered sentences, transcribed word for word, from recent videos (one block per
 668 | +video). Today is {today}.
 669 | +
 670 | +{note}
 671 | +<sentences>
 672 | +{rows}
 673 | +</sentences>
 674 | +
 675 | +A moment is a range [first id, last id] of 1 to 3 consecutive sentences of ONE video that makes sense heard with
 676 | +nothing before it, states something (not a question) and names Bitcoin.
 677 | +For each moment give:
 678 | +- "scores", integers 0-5: "hook_first_2s" (do its first words grab attention), "quotable", "surprising_fact" (a
 679 | +  surprising number or fact), "stance" (a clear opinion), "stakes" (why it matters, emotion), "stands_alone" (clear
 680 | +  without any context), "contempt_outrage" (contempt or outrage: counted AGAINST the moment)
 681 | +- "names_person": true if it names a person
 682 | +- "risk": every one that applies, from: {risks}
 683 | +  (accusation = crime, fraud, insolvency or dishonesty alleged against a named person or company; partner_attack = one
 684 | +  channel attacking another; imperative = telling the viewer to buy, sell or use leverage; ad_read = a sponsor or ad;
 685 | +  third_party_media = someone else's clip being played; time_sensitive = 'today', 'just', or a price level that dates)
 686 | +- "topics": one to three, from: {topics}
 687 | +- "reason": why it works, at most 20 words (internal note; never shown to anyone)
 688 | +Return at most {n} moments, best first, never two that overlap. Use ids only; never rewrite a sentence.
 689 | +If nothing qualifies, answer {{"moments": []}}.
 690 | +Return ONLY this JSON object: {{"moments": [{{"range": [first, last], "scores": {{...}}, "names_person": false,
 691 | +"risk": [], "topics": [], "reason": "..."}}]}}"""
 692 | +
 693 | +
 694 | +def mine_prompt(table, ctx, topics, n=MAX_MOMENTS_PER_CALL):
 695 | +    return MINE_PROMPT.format(today=ctx.now.strftime("%Y-%m-%d"), note=SB.UNTRUSTED, rows=_rows(table, ctx),
 696 | +                              risks=", ".join(RISKS), topics=", ".join(topics), n=n)
 697 | +
 698 | +
 699 | +def _rows(table, ctx):
 700 | +    out, cur, prev = [], None, None
 701 | +    for r in table.rows:
 702 | +        if prev is not None and r.source is prev.source and r.k != prev.k + 1:
 703 | +            out.append("   ... (sentences not shown here: a range never crosses this line)")
 704 | +        prev = r
 705 | +        if r.source is not cur:
 706 | +            cur = r.source
 707 | +            reg = ctx.channel(cur.channel_id) or {}
 708 | +            age = E.age_hours(cur.published_at, ctx.now)
 709 | +            out.append(f"== {reg.get('display_name') or cur.channel_name} | published "
 710 | +                       f"{'?' if age is None else f'{age:.0f} h'} ago | \"{SB._q(cur.title or '', 120)}\"")
 711 | +        sp = r.span
 712 | +        dur = f"{sp.end - sp.start:4.1f} s" if cur.timing == "word" else "  ?  s"
 713 | +        out.append(f"{r.n} | {SB._mmss(sp.start)} | {dur} | {SB._q(sp.text, 600)}")
 714 | +    return "\n".join(out)
 715 | +
 716 | +
 717 | +def check_moments(obj, table, topics, n=MAX_MOMENTS_PER_CALL):
 718 | +    """The reply contract (rejected, never repaired) -> [(span, fields)]. {"moments": []} is a valid empty answer."""
 719 | +    SB._keys(obj, ("moments",))
 720 | +    ms = obj["moments"]
 721 | +    if not isinstance(ms, list) or len(ms) > n:
 722 | +        raise Rejected(f"'moments' must be a list of at most {n}")
 723 | +    out, used = [], {}
 724 | +    for i, m in enumerate(ms):
 725 | +        what = f"moment {i + 1}"
 726 | +        if not isinstance(m, dict):
 727 | +            raise Rejected(f"{what} is not an object")
 728 | +        SB._keys(m, ("range", "scores", "names_person", "risk", "topics", "reason"))
 729 | +        sp = SB._range(m["range"], table, what)
 730 | +        for k in range(sp.k0, sp.k1 + 1):
 731 | +            if (sp.source.video_id, k) in used:
 732 | +                raise Rejected(f"{what} overlaps {used[(sp.source.video_id, k)]}")
 733 | +            used[(sp.source.video_id, k)] = what
 734 | +        sc = m["scores"]
 735 | +        if not isinstance(sc, dict) or set(sc) != set(AXES):
 736 | +            raise Rejected(f"{what}: 'scores' must have exactly {list(AXES)}")
 737 | +        for a in AXES:
 738 | +            if type(sc[a]) is not int or not 0 <= sc[a] <= 5:
 739 | +                raise Rejected(f"{what}: score {a} must be an integer 0-5")
 740 | +        if type(m["names_person"]) is not bool:
 741 | +            raise Rejected(f"{what}: 'names_person' must be true or false")
 742 | +        for key, allowed, lo, hi in (("risk", RISKS, 0, len(RISKS)), ("topics", topics, 1, 3)):
 743 | +            v = m[key]
 744 | +            if not isinstance(v, list) or not lo <= len(v) <= hi or len(set(v)) != len(v) or \
 745 | +                    any(not isinstance(x, str) or x not in allowed for x in v):
 746 | +                raise Rejected(f"{what}: '{key}' must be {lo}-{hi} distinct values from the given list")
 747 | +        if not isinstance(m["reason"], str) or not m["reason"].strip() or len(m["reason"]) > REASON_MAX:
 748 | +            raise Rejected(f"{what}: 'reason' must be a short non-empty string")
 749 | +        out.append((sp, m))
 750 | +    return out
 751 | +
 752 | +
 753 | +# ── 3 judging and ranking ──
 754 | +
 755 | +def judge(sp, ctx):
 756 | +    """The moment on its own (it is its own statement: T13 is met by its own sentences; L-s context integrity judges
 757 | +    what it leaves out). Word-timed: as hook and as clip; otherwise as evidence only (on screen after the word pass)."""
 758 | +    own = tuple(E.statement_entry(E.Span(sp.source, k, k)) for k in range(sp.k0, sp.k1 + 1))
 759 | +    if sp.source.timing == "word":
 760 | +        res = {role: E.eligible(sp, replace(ctx, role=role, story=own)) for role in ("hook", "clip")}
 761 | +    else:
 762 | +        res = {"evidence": E.eligible(sp, replace(ctx, role="evidence"))}
 763 | +    return res
 764 | +
 765 | +
 766 | +def rank_score(rec, trend=None, trend_weight=TREND_WEIGHT):
 767 | +    s = rec["scores"]
 768 | +    score = sum(s[a] for a in POSITIVE) - CONTEMPT_WEIGHT * s["contempt_outrage"]
 769 | +    score -= sum(SOFT_RISKS.get(r, 0) for r in rec["risk"])
 770 | +    if trend and trend_weight:
 771 | +        score += trend_weight * max([trend.get(t, 0.0) for t in rec["topics"]] or [0.0])
 772 | +    return score
 773 | +
 774 | +
 775 | +def record(sp, m, ctx, res, mined):
 776 | +    src = sp.source
 777 | +    dur = round(sp.end - sp.start, 2) if src.timing == "word" else None
 778 | +    elig = {role: {"ok": r.ok, "reasons": r.names(), "targets_missed": r.facts.get("targets_missed", [])}
 779 | +            for role, r in res.items()}
 780 | +    reg = ctx.channel(src.channel_id) or {}
 781 | +    return {"schema": "pp.moment/1", "moment_id": moment_id(src, sp.w0, sp.w1), "video_id": src.video_id,
 782 | +            "channel_id": src.channel_id, "channel_name": reg.get("display_name") or src.channel_name,
 783 | +            "published_at": src.published_at, "title": src.title, "transcript_sha256": src.transcript_sha256,
 784 | +            "transcript_method": src.transcript_method, "timing": src.timing, "words": [sp.w0, sp.w1],
 785 | +            "sentences": [sp.k0, sp.k1], "text": sp.text, "start": sp.start, "end": sp.end, "duration_s": dur,
 786 | +            "duration_estimate_s": None if dur is not None else round(sp.end - sp.start, 2),
 787 | +            "speaker": {"turn_change_inside": None, "label": None, "confidence": None, "named": None,
 788 | +                        "named_source": None},
 789 | +            "scores": dict(m["scores"]), "names_person": m["names_person"], "risk": list(m["risk"]),
 790 | +            "topics": list(m["topics"]), "reason": m["reason"], "eligibility": elig,
 791 | +            "on_screen_ok": any(r.ok for role, r in res.items() if role in E.ON_SCREEN), "excluded": sorted(set(m["risk"]) & set(HARD_RISKS)),
 792 | +            "mined": mined}
 793 | +
 794 | +
 795 | +def mine(router, sources, ctx, topics, since=None, optout=frozenset(), log=print, n=MAX_MOMENTS_PER_CALL,
 796 | +         budget_chars=None, attempts=ATTEMPTS, cycle="", recent_h=RECENT_H):
 797 | +    """The cycle's mining pass -> {"moments": [records, ranked], "calls": [...], "rows": n, "skipped": {...}}."""
 798 | +    srcs, skipped = window_sources(sources, ctx, since=since, recent_h=recent_h, optout=optout)
 799 | +    budget = budget_chars or SB.row_budget(MINE_MAX_TOKENS)
 800 | +    out = {"moments": [], "calls": [], "skipped": skipped, "sources": len(srcs), "rows": 0}
 801 | +    model = _MineModel(router)
 802 | +    for ti, table in enumerate(tables(srcs, ctx, budget)):
 803 | +        out["rows"] += len(table)
 804 | +        log_ = []
 805 | +        base = mine_prompt(table, ctx, topics, n)
 806 | +        status, got = SB._ask(model, base, MINE_MAX_TOKENS, lambda obj: check_moments(obj, table, topics, n),
 807 | +                              attempts, log_)
 808 | +        call = {"table": ti, "rows": len(table), "status": status, "attempts": log_}
 809 | +        out["calls"].append(call)
 810 | +        if status != "accepted":
 811 | +            continue
 812 | +        last = log_[-1]
 813 | +        mined = {"by": (last.get("meta") or {}).get("backend"), "prompt_sha256": last.get("prompt_sha256"),
 814 | +                 "reply_sha256": hashlib.sha256((last.get("raw") or "").encode()).hexdigest(),
 815 | +                 "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cycle": cycle}
 816 | +        for sp, m in got:
 817 | +            out["moments"].append(record(sp, m, ctx, judge(sp, ctx), mined))
 818 | +    seen = {}
 819 | +    for rec in out["moments"]:                          # one record per moment id (a re-mined moment: the last wins)
 820 | +        seen[rec["moment_id"]] = rec
 821 | +    ranked = sorted(seen.values(), key=lambda r: (-rank_score(r), r["moment_id"]))
 822 | +    for i, rec in enumerate(ranked):
 823 | +        rec["rank"], rec["rank_score"] = i + 1, rank_score(rec)
 824 | +    out["moments"] = ranked
 825 | +    return out
 826 | +
 827 | +
 828 | +class _MineModel(SB.Model):
 829 | +    """select_by_id's call loop over the router's "mine" role (law L-x)."""
 830 | +
 831 | +    def __init__(self, router):
 832 | +        self.router, self.name = router, "role:mine"
 833 | +
 834 | +    def complete(self, prompt, max_tokens, seed):
 835 | +        import providers as P
 836 | +        try:
 837 | +            r = self.router.call("mine", prompt, max_tokens, seed)
 838 | +        except P.ProviderError as e:
 839 | +            raise SB.ModelError(str(e)[:300]) from None
 840 | +        except P.ReplayMiss as e:
 841 | +            raise SB.ReplayMiss(str(e)[:300]) from None
 842 | +        except P.SpendLimit as e:
 843 | +            raise SB.SpendLimit(str(e)) from None
 844 | +        return r.text, {"backend": r.backend, "vendor": r.vendor, "usd": r.usd, "usage": r.usage,
 845 | +                        "replayed": r.replayed, "tried": r.tried}
 846 | +
 847 | +
 848 | +# ── the exclusion verdict on one moment in its context (law L-u; also the pp-tests harness's exclusion gate) ──
 849 | +
 850 | +EXCLUSION_PROMPT = """You screen ONE moment (the sentences inside <moment>) from a Bitcoin video before it can be clipped
 851 | +into a short video. The text around it is context only.
 852 | +
 853 | +<before>{before}</before>
 854 | +<moment>{moment}</moment>
 855 | +<after>{after}</after>
 856 | +
 857 | +Answer:
 858 | +- "risks": every one that applies to the MOMENT: "accusation" (crime, fraud, insolvency or dishonesty alleged against a
 859 | +  named person or company), "partner_attack" (one Bitcoin channel or host attacking another), "imperative" (telling
 860 | +  the viewer to buy, sell or use leverage), "guaranteed_return", "single_source_breaking" (a breaking factual claim
 861 | +  resting on one unnamed source or rumour), "ad_read" (a sponsor, ad or affiliate pitch), "third_party_media" (someone
 862 | +  else's clip, song or broadcast being played); an empty list if none
 863 | +- "about_bitcoin": "yes" if the moment is about Bitcoin, "no" if it is about another coin or no crypto at all,
 864 | +  "uncertain"
 865 | +- "why": one short line
 866 | +Criticising a policy is not an accusation; a prediction framed as the speaker's own view is not an imperative;
 867 | +naming a company neutrally is not an accusation.
 868 | +Return ONLY this JSON object: {{"risks": [], "about_bitcoin": "yes", "why": "..."}}"""
 869 | +
 870 | +
 871 | +def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7, avoid_model=None):
 872 | +    """-> {"verdict": "keep" | "exclude", "why", "risks", "backend", "measured", "replayed"}: a deterministic ad-read
 873 | +    screen (a marker in the moment, or in the sentence right before it: an ad read runs on), then the blind model
 874 | +    verdict (role "exclusion_verdict", never on the moment's own miner: avoid_model; audit p2 C3); any hard risk, a
 875 | +    moment not about Bitcoin, an unreadable or uncertain verdict excludes (law L-m). An unreadable or unavailable verdict
 876 | +    is also NOT measured (the exam adapter reports it as such)."""
 877 | +    import providers as P
 878 | +    from story_semantics import quote_data
 879 | +    last_before = re.split(r"(?<=[.!?])\s+", (before_text or "").strip())[-1] if (before_text or "").strip() else ""
 880 | +    for where, txt in (("the moment", moment_text or ""), ("the sentence before it", last_before)):
 881 | +        if AD_MARKERS.search(txt):
 882 | +            return {"verdict": "exclude", "why": f"ad-read marker '{AD_MARKERS.search(txt).group(0)}' in {where}",
 883 | +                    "risks": ["ad_read"], "backend": "deterministic", "measured": True, "replayed": False}
 884 | +    r = None
 885 | +    try:
 886 | +        r = router.call("exclusion_verdict", EXCLUSION_PROMPT.format(before=quote_data(before_text, 3000),
 887 | +                                                                     moment=quote_data(moment_text, 1500),
 888 | +                                                                     after=quote_data(after_text, 3000)), 800, seed,
 889 | +                        avoid_model=avoid_model)
 890 | +        obj = json.loads(r.text.strip())
 891 | +        if not isinstance(obj, dict) or set(obj) != {"risks", "about_bitcoin", "why"} or \
 892 | +                not isinstance(obj["risks"], list) or any(not isinstance(x, str) or x not in HARD_RISKS
 893 | +                                                          for x in obj["risks"]) or \
 894 | +                obj["about_bitcoin"] not in ("yes", "no", "uncertain"):
 895 | +            raise ValueError("the verdict does not match its contract")
 896 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 897 | +        if r is not None and isinstance(e, (ValueError, TypeError)):
 898 | +            router.reject(r)
 899 | +        return {"verdict": "exclude", "why": f"no readable verdict ({type(e).__name__}: {str(e)[:160]})",
 900 | +                "risks": [], "backend": None, "measured": False, "replayed": False}
 901 | +    meas = {"measured": True, "replayed": bool(getattr(r, "replayed", False))}
 902 | +    if obj["risks"]:
 903 | +        return dict(meas, verdict="exclude", why=f"{obj['risks']}: {str(obj['why'])[:200]}", risks=obj["risks"],
 904 | +                    backend=r.backend)
 905 | +    if obj["about_bitcoin"] != "yes":
 906 | +        return dict(meas, verdict="exclude", why=f"about Bitcoin: {obj['about_bitcoin']}: {str(obj['why'])[:200]}",
 907 | +                    risks=[], backend=r.backend)
 908 | +    return dict(meas, verdict="keep", why=str(obj["why"])[:200], risks=[], backend=r.backend)
 909 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
 910 | new file mode 100644
 911 | index 00000000..d059221b
 912 | --- /dev/null
 913 | +++ b/pipeline/transcript_truth.py
 914 | @@ -0,0 +1,132 @@
 915 | +#!/usr/bin/env python3
 916 | +"""pipeline/transcript_truth.py — SPEAKER AND TRANSCRIPT TRUTH (law L-v, orchestrator 2026-11-12 '02:30').
 917 | +
 918 | +(2) Every gate trusts one Whisper transcript. For EVERY selected segment, a second, independent recognition pass runs
 919 | +    on the SOURCE audio through the router's "transcribe" chain (law L-x: pipeline/model_providers.json). Any
 920 | +    disagreement on a number, a name or a negation, in either direction, drops the moment.
 921 | +(1) The same pass's diarisation reports the speaker turns inside the segment: a moment may not span a speaker change,
 922 | +    and "not measured" never passes; a person is NAMED only from verified evidence, never from a diarisation label.
 923 | +
 924 | +audio_window() fetches the audio of [start - pad, end + pad] of a YouTube video on CPU (yt-dlp download sections +
 925 | +ffmpeg to 16 kHz mono WAV) into a caller-given directory (the integrator already holds the downloaded window:
 926 | +verify_segment() takes any audio path). No GPU, no Whisper. Keys by name inside the router's back-ends.
 927 | +"""
 928 | +import json
 929 | +import os
 930 | +import re
 931 | +import subprocess
 932 | +
 933 | +import canon
 934 | +
 935 | +NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "cannot", "can't",
 936 | +                       "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "shouldn't",
 937 | +                       "wouldn't", "couldn't", "hasn't", "haven't", "hadn't"})
 938 | +_NUM = re.compile(r"^-?\d+(\.\d+)?$")
 939 | +PAD_S = 1.5
 940 | +
 941 | +
 942 | +def audio_window(video_id, start, end, out_dir, pad=PAD_S):
 943 | +    """WAV (16 kHz mono) of [start - pad, end + pad] (clamped at the video head), fetched with yt-dlp's download
 944 | +    sections -> (path, the window's real start in video seconds)."""
 945 | +    os.makedirs(out_dir, exist_ok=True)
 946 | +    a, b = max(0.0, start - pad), end + pad
 947 | +    stem = f"{video_id}_{int(a * 1000)}_{int(b * 1000)}"
 948 | +    base = os.path.join(out_dir, stem)
 949 | +    wav = base + ".wav"
 950 | +    if os.path.exists(wav):
 951 | +        return wav, a
 952 | +    subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", "bestaudio", "--download-sections", f"*{a:.2f}-{b:.2f}",
 953 | +                    "--force-keyframes-at-cuts", "-o", base + ".%(ext)s", f"https://www.youtube.com/watch?v={video_id}"],
 954 | +                   check=True, timeout=300, capture_output=True)
 955 | +    src = next(os.path.join(out_dir, f) for f in sorted(os.listdir(out_dir))
 956 | +               if os.path.splitext(f)[0] == stem and not f.endswith(".wav"))       # exact stem: never a longer id
 957 | +    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True,
 958 | +                   timeout=120)
 959 | +    return wav, a
 960 | +
 961 | +
 962 | +def second_pass(router, wav):
 963 | +    """The second, independent recognition pass through the router's "transcribe" chain (law L-x): ({"text",
 964 | +    "segments": [{"speaker", "start", "end", "text"}]}, the Reply naming the back-end)."""
 965 | +    return router.transcribe("transcribe", wav)
 966 | +
 967 | +
 968 | +FILLERS = frozenset({"um", "uh", "erm", "hmm", "mm", "ah", "oh", "yeah", "okay", "ok"})
 969 | +
 970 | +
 971 | +def critical_tokens(text):
 972 | +    """The tokens law L-v 2 protects: numbers (canonical values), negations, and proper names (capitalised words that
 973 | +    are not English words: vo_fidelity.lexicon; never a filler, never the unit letter of a number such as the K of
 974 | +    '16K')."""
 975 | +    import vo_fidelity as VF
 976 | +    toks = canon.canon_tokens(text)
 977 | +    nums = [t for t in toks if _NUM.match(t)]
 978 | +    negs = [t for t in toks if t in NEGATIONS or t.endswith("n't")]
 979 | +    words = re.findall(r"(?<![\w$])[A-Za-z][A-Za-z'’-]*", text or "")
 980 | +    names = sorted({w for w in words if w[0].isupper() and w not in ("I",) and w.lower() not in FILLERS and
 981 | +                    re.sub(r"['’]s$", "", w).lower() not in VF.lexicon()})
 982 | +    return {"numbers": nums, "negations": negs, "names": names}
 983 | +
 984 | +
 985 | +def compare(selected_text, second_text):
 986 | +    """BOTH directions, with counts (audit p2 C4): every number and negation of the selected sentences is read as
 987 | +    often in the second pass's text of the same span, and the second pass reads none the first did not (a dropped
 988 | +    "not" is as fatal as an added one); every name of either side appears on the other (case folded).
 989 | +    -> {"ok", "disagree": {...}, "critical": first, "second_critical": second}."""
 990 | +    from collections import Counter
 991 | +    a, b = critical_tokens(selected_text), critical_tokens(second_text)
 992 | +    dis = {}
 993 | +    for k in ("numbers", "negations"):
 994 | +        ca, cb = Counter(a[k]), Counter(b[k])
 995 | +        dis[k] = sorted(set((ca - cb).elements()) | set((cb - ca).elements()))
 996 | +    fold = lambda ns: {n.lower().rstrip("'’s") for n in ns}
 997 | +    ta, tb = set(canon.canon_tokens(selected_text)), set(canon.canon_tokens(second_text))
 998 | +    dis["names"] = sorted({n for n in a["names"] if n.lower().rstrip("'’s") not in tb | fold(b["names"])} |
 999 | +                          {n for n in b["names"] if n.lower().rstrip("'’s") not in ta | fold(a["names"])})
1000 | +    return {"ok": not any(dis.values()), "disagree": dis, "critical": a, "second_critical": b}
1001 | +
1002 | +
1003 | +def _inside(x, start_rel, end_rel):
1004 | +    if x.get("start") is None or x.get("end") is None:
1005 | +        return False
1006 | +    mid = (float(x["start"]) + float(x["end"])) / 2
1007 | +    return start_rel - 0.15 <= mid <= end_rel + 0.15
1008 | +
1009 | +
1010 | +def span_text(second, start_rel, end_rel):
1011 | +    """The second pass's words of [start_rel, end_rel] (seconds in the audio): word by word when the back-end gives
1012 | +    word timing (each word whose midpoint lies inside), else its segments overlapping the span."""
1013 | +    if second.get("words"):
1014 | +        return " ".join(w["text"] for w in second["words"] if _inside(w, start_rel, end_rel)).strip()
1015 | +    return " ".join(s["text"] for s in second["segments"]
1016 | +                    if s.get("start") is not None and s.get("end") is not None and s["end"] > start_rel + 0.25
1017 | +                    and s["start"] < end_rel - 0.25).strip()
1018 | +
1019 | +
1020 | +def speaker_turns(second, start_rel, end_rel):
1021 | +    """Speakers of the second pass's segments overlapping [start_rel, end_rel] (seconds inside the audio): one label =
1022 | +    no change inside (False); more = a change (True); none = NOT measured (None, which never passes)."""
1023 | +    if second.get("words"):
1024 | +        sp = [w.get("speaker") for w in second["words"] if _inside(w, start_rel, end_rel)]
1025 | +    else:
1026 | +        sp = [s.get("speaker") for s in second["segments"]
1027 | +              if s.get("start") is not None and s.get("end") is not None and s["end"] > start_rel + 0.25
1028 | +              and s["start"] < end_rel - 0.25]
1029 | +    labels = sorted({x for x in sp if x})
1030 | +    return {"labels": labels, "turn_change_inside": (len(labels) > 1) if labels else None}
1031 | +
1032 | +
1033 | +def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_start=None):
1034 | +    """Both checks for one selected segment -> a record (the second pass's text kept as evidence). ok only when the
1035 | +    critical tokens agree in both directions AND exactly one speaker was measured inside."""
1036 | +    if wav is None:
1037 | +        wav, wav_start = audio_window(video_id, start, end, work_dir)
1038 | +    sec, rep = second_pass(router, wav)
1039 | +    off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_S))
1040 | +    span = span_text(sec, off, off + (end - start)) or sec["text"]
1041 | +    cmp_ = compare(text, span)
1042 | +    turns = speaker_turns(sec, off, off + (end - start))
1043 | +    return {"video_id": video_id, "start": start, "end": end, "model": rep.backend, "replayed": rep.replayed,
1044 | +            "second_pass_text": span, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
1045 | +            "critical": cmp_["critical"], "speakers": turns, "audio": os.path.basename(wav),
1046 | +            "ok": cmp_["ok"] and turns["turn_change_inside"] is False}
1047 | diff --git a/pipeline/trend_brief.py b/pipeline/trend_brief.py
1048 | new file mode 100644
1049 | index 00000000..ebc72100
1050 | --- /dev/null
1051 | +++ b/pipeline/trend_brief.py
1052 | @@ -0,0 +1,171 @@
1053 | +#!/usr/bin/env python3
1054 | +"""pipeline/trend_brief.py — what is hot right now, as a RANKING input only (orchestrator Phase 2 addition '01:55';
1055 | +law L-w 4, '02:30'). Trend is never a gate and never a fact source.
1056 | +
1057 | +- TAXONOMY: a closed list of Bitcoin topic ids, each with our own fixed label and a keyword pattern. Every trend signal
1058 | +  is forced into it; anything else is discarded.
1059 | +- local_baseline(): the free signal from our own corpus. For each topic, the share of partner channels (last 24 h)
1060 | +  with a Bitcoin sentence on that topic. Always available; no model, no network.
1061 | +- grok_brief(): ONE live-search call per cycle (role "trend_brief" through pipeline/providers.py: xAI's Responses API
1062 | +  with x_search + web_search). It asks for 8-12 Bitcoin-only topics with heat 0-1 and rising / fading / steady.
1063 | +  - The reply is validated into the taxonomy (strict, never repaired). Raw post text never enters any prompt: only
1064 | +    (topic id, heat, direction, source count) leave this module, and person names only as a list the packager may use
1065 | +    to boost a moment whose verified SPEAKER is that person.
1066 | +  - Cached per cycle (cycle id + timestamp + sha256 of the reply).
1067 | +  - On any failure: no boost, and the cycle says so.
1068 | +- SHADOW (law L-w 4): moments.TREND_WEIGHT is 0. The brief is logged and compared with the baseline, never used to
1069 | +  rank, until it measurably helps. When enabled, the weight is capped at ~10-15 % of a moment's score. Titles never
1070 | +  take trend phrasing: they use our taxonomy labels at most (law L-t: every word of a title must be supported by the
1071 | +  clips).
1072 | +"""
1073 | +import hashlib
1074 | +import json
1075 | +import os
1076 | +import re
1077 | +import time
1078 | +
1079 | +import eligibility as E
1080 | +
1081 | +TAXONOMY = {   # id: (our own label, pattern over a sentence that names Bitcoin)
1082 | +    "price_action": ("Bitcoin's price move", r"\b(price|all[- ]time high|support|resistance|pullback|sell[- ]?off|rally|"
1083 | +                                             r"dump|pump|correction|drawdown|breakout|\$\d)"),
1084 | +    "etf_flows": ("Bitcoin ETF flows", r"\b(etfs?|inflows?|outflows?|ibit|blackrock|fidelity|grayscale)\b"),
1085 | +    "treasury_companies": ("Bitcoin treasury companies", r"\b(strategy|microstrategy|saylor|treasury compan|metaplanet|"
1086 | +                                                         r"balance sheet|mnav|cost basis)"),
1087 | +    "us_policy": ("US Bitcoin policy", r"\b(strategic (bitcoin )?reserve|congress|senate|house|bill|sec\b|regulat|"
1088 | +                                       r"executive order|white house|legislation)"),
1089 | +    "macro_fed": ("rates, the Fed and the dollar", r"\b(fed\b|federal reserve|rate cuts?|interest rates?|inflation|cpi|"
1090 | +                                                   r"powell|dollar|yields?|liquidity|m2)\b"),
1091 | +    "mining": ("Bitcoin mining", r"\b(miners?|mining|hash ?rate|difficulty|hashprice|halving)\b"),
1092 | +    "onchain": ("on-chain signals", r"\b(on[- ]chain|whales?|long[- ]term holders?|short[- ]term holders?|"
1093 | +                                     r"exchange reserves?|realized price)\b"),
1094 | +    "derivatives_leverage": ("leverage and liquidations", r"\b(leverage|liquidat\w*|futures|options|open interest|"
1095 | +                                                          r"funding rates?)\b"),
1096 | +    "institutional_adoption": ("institutions and Bitcoin", r"\b(banks?|institution\w*|vanguard|jpmorgan|goldman|"
1097 | +                                                           r"pensions?|wall street|custod\w*)\b"),
1098 | +    "sovereign_adoption": ("countries and Bitcoin", r"\b(el salvador|bhutan|nation[- ]states?|countr(y|ies)|sovereign)\b"),
1099 | +    "protocol_dev": ("Bitcoin development", r"\b(bitcoin core|knots|op_return|soft fork|covenants?|taproot|lightning|"
1100 | +                                             r"nodes?)\b"),
1101 | +    "security_custody": ("self-custody and security", r"\b(self[- ]custody|cold storage|seed phrase|hacks?|exploit|"
1102 | +                                                       r"private keys?)\b"),
1103 | +    "quantum": ("quantum computing and Bitcoin", r"\bquantum\b"),
1104 | +    "elections_politics": ("elections and Bitcoin", r"\b(elections?|midterms?|democrats?|republicans?|votes?|campaign)\b"),
1105 | +    "market_sentiment": ("market sentiment", r"\b(fear|greed|capitulat\w*|sentiment|bear market|bull market|cycle|"
1106 | +                                             r"bottom|top)\b"),
1107 | +    "stocks_correlation": ("Bitcoin and stocks", r"\b(nasdaq|s&p|stocks?|equities|tech stocks|nvidia|correlat\w*)"),
1108 | +    "gold_comparison": ("Bitcoin and gold", r"\bgold\b"),
1109 | +    "payments_adoption": ("Bitcoin as money", r"\b(payments?|merchants?|pay with|spend(ing)?|everyday use)\b"),
1110 | +}
1111 | +TOPICS = tuple(TAXONOMY)
1112 | +_PAT = {t: re.compile(p, re.I) for t, (_, p) in TAXONOMY.items()}
1113 | +DIRECTIONS = ("rising", "fading", "steady")
1114 | +BRIEF_MAX_TOKENS = 5000            # < 6k out (token discipline, Phase 2 addition)
1115 | +
1116 | +
1117 | +def label(topic):
1118 | +    return TAXONOMY[topic][0]
1119 | +
1120 | +
1121 | +def topics_of(text):
1122 | +    """Taxonomy ids whose pattern a Bitcoin-naming text matches (the free local classifier)."""
1123 | +    if not E.names_bitcoin(text):
1124 | +        return []
1125 | +    return [t for t in TOPICS if _PAT[t].search(text)]
1126 | +
1127 | +
1128 | +def local_baseline(sources, ctx, hours=24.0):
1129 | +    """{topic: heat 0-1}: the share of the window's partner channels with a Bitcoin sentence on that topic; plus the
1130 | +    channel counts. Free, deterministic, always available (law L-w 4's baseline)."""
1131 | +    by_topic, channels = {t: set() for t in TOPICS}, set()
1132 | +    for src in sources:
1133 | +        age = E.age_hours(src.published_at, ctx.now)
1134 | +        if age is None or age > hours or age < 0:
1135 | +            continue
1136 | +        channels.add(src.channel_id)
1137 | +        for a, b in src.sentences:
1138 | +            for t in topics_of(E.spoken(src.tokens[a:b + 1])):
1139 | +                by_topic[t].add(src.channel_id)
1140 | +    n = max(1, len(channels))
1141 | +    return {"topics": {t: round(len(c) / n, 3) for t, c in by_topic.items() if c},
1142 | +            "channels": {t: len(c) for t, c in by_topic.items() if c}, "window_channels": len(channels),
1143 | +            "hours": hours}
1144 | +
1145 | +
1146 | +BRIEF_PROMPT = """Search X and the web now ({now} UTC) for what Bitcoin-focused accounts and outlets are talking about
1147 | +in the last 24 hours. Bitcoin only: ignore altcoins, memecoins and general politics unless it is about Bitcoin policy.
1148 | +Classify what you find into these topic ids ONLY (anything else is discarded): {topics}.
1149 | +Return 8 to 12 topics. For each: "topic" (an id from the list), "heat" (0 to 1: how much attention it has now),
1150 | +"direction" ("rising", "fading" or "steady"), "sources" (how many distinct posts or articles you saw on it, an integer).
1151 | +Also "persons": at most 5 names of people at the centre of today's Bitcoin conversation (names only).
1152 | +Do not include quotes, post text, links or opinions.
1153 | +Return ONLY this JSON object: {{"topics": [{{"topic": "...", "heat": 0.0, "direction": "...", "sources": 0}}],
1154 | +"persons": []}}"""
1155 | +
1156 | +
1157 | +def check_brief(obj):
1158 | +    """Strict validation into the closed taxonomy (never repaired): -> {topic: {heat, direction, sources}}, persons."""
1159 | +    if not isinstance(obj, dict) or set(obj) != {"topics", "persons"}:
1160 | +        raise ValueError("keys must be exactly ['topics', 'persons']")
1161 | +    ts = obj["topics"]
1162 | +    if not isinstance(ts, list) or not 1 <= len(ts) <= 12:
1163 | +        raise ValueError("'topics' must hold 1-12 items")
1164 | +    out = {}
1165 | +    for t in ts:
1166 | +        if not isinstance(t, dict) or set(t) != {"topic", "heat", "direction", "sources"}:
1167 | +            raise ValueError("each topic needs exactly topic, heat, direction, sources")
1168 | +        if t["topic"] not in TAXONOMY or t["topic"] in out:
1169 | +            raise ValueError(f"topic {t['topic']!r} not in the taxonomy or repeated")
1170 | +        if type(t["heat"]) not in (int, float) or not 0 <= t["heat"] <= 1 or t["direction"] not in DIRECTIONS or \
1171 | +                type(t["sources"]) is not int or t["sources"] < 0:
1172 | +            raise ValueError(f"topic {t['topic']}: heat 0-1, direction {DIRECTIONS}, sources an integer")
1173 | +        out[t["topic"]] = {"heat": float(t["heat"]), "direction": t["direction"], "sources": t["sources"]}
1174 | +    ps = obj["persons"]
1175 | +    if not isinstance(ps, list) or len(ps) > 5 or any(not isinstance(p, str) or not 2 <= len(p) <= 60 or
1176 | +                                                      not re.fullmatch(r"[A-Za-z][A-Za-z .'\-]+", p) for p in ps):
1177 | +        raise ValueError("'persons' must be at most 5 plain names")
1178 | +    return out, list(ps)
1179 | +
1180 | +
1181 | +def cycle_id(now, hours=4):
1182 | +    """A cycle is a 4 h slot of the UTC day (one call per cycle; law L-p cadence 3-5 h)."""
1183 | +    return f"{now.strftime('%Y%m%d')}T{now.hour // hours * hours:02d}"
1184 | +
1185 | +
1186 | +def grok_brief(router, now, cache_dir, log=print):
1187 | +    """ONE live-search call per cycle, cached when it succeeded; -> {"status", "topics", "persons", "cycle", "backend",
1188 | +    "sha256", ...}. Failure (no back-end, invalid reply) -> status "failed" and NO boost (trend is never a gate); a
1189 | +    failure is not cached, so the next run of the cycle asks again."""
1190 | +    import providers as P
1191 | +    cyc = cycle_id(now)
1192 | +    path = os.path.join(cache_dir, f"brief_{cyc}.json")
1193 | +    if os.path.exists(path):
1194 | +        with open(path) as f:
1195 | +            return dict(json.load(f), cached=True)
1196 | +    prompt = BRIEF_PROMPT.format(now=now.strftime("%Y-%m-%d %H:%M"), topics=", ".join(TOPICS))
1197 | +    rec = {"cycle": cyc, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mode": "shadow (weight 0)"}
1198 | +    try:
1199 | +        r = router.call("trend_brief", prompt, BRIEF_MAX_TOKENS, seed=7)
1200 | +        raw = r.text.strip()
1201 | +        rec.update(backend=r.backend, usd=r.usd, usage=r.usage, sha256=hashlib.sha256(raw.encode()).hexdigest())
1202 | +        topics, persons = check_brief(json.loads(raw))        # exactly one JSON object: prose is never repaired
1203 | +        rec.update(status="ok", topics=topics, persons=persons)
1204 | +    except (P.ProviderError, P.SpendLimit, ValueError, KeyError) as e:
1205 | +        rec.update(status="failed", why=f"{type(e).__name__}: {str(e)[:200]}", topics={}, persons=[])
1206 | +        log(f"  trend brief: no boost this cycle ({rec['why']})")
1207 | +    if rec.get("status") == "ok":                             # a failed brief is never cached (audit p2 U13)
1208 | +        os.makedirs(cache_dir, exist_ok=True)
1209 | +        with open(path, "w") as f:
1210 | +            json.dump(rec, f, indent=1)
1211 | +    return rec
1212 | +
1213 | +
1214 | +def trend_match(moment, brief, baseline=None):
1215 | +    """The local trend-match axis (no model call): the hottest brief topic among the moment's topics (0 when the brief
1216 | +    failed); person-trends only for a moment whose VERIFIED speaker is that person (law L-w 4)."""
1217 | +    heat = max([((brief or {}).get("topics") or {}).get(t, {}).get("heat", 0.0) for t in moment.get("topics") or []]
1218 | +               or [0.0])
1219 | +    sp = (moment.get("speaker") or {}).get("named")
1220 | +    if sp and sp in ((brief or {}).get("persons") or []) and (moment.get("speaker") or {}).get("named_source"):
1221 | +        heat = max(heat, 0.5)
1222 | +    base = max([((baseline or {}).get("topics") or {}).get(t, 0.0) for t in moment.get("topics") or []] or [0.0])
1223 | +    return {"brief": round(heat, 3), "baseline": round(base, 3)}
1224 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
1225 | new file mode 100644
1226 | index 00000000..a4ddcc6f
1227 | --- /dev/null
1228 | +++ b/pipeline/vo_fidelity.py
1229 | @@ -0,0 +1,729 @@
1230 | +#!/usr/bin/env python3
1231 | +"""pipeline/vo_fidelity.py — VO FIDELITY (law L-o 11, '01:55'; law L-t, '02:30'): the PBX MAX VO, the title and the
1232 | +caption never put words in a speaker's mouth. Two layers, BOTH must pass ("vo check needs to be real 100%"):
1233 | +
1234 | +(a) DETERMINISTIC (this module, no model): every line names the segments it relies on (cites = moment ids), and
1235 | +    - NEEDS_SOURCE: a line with a fact (number, name, quote, attribution, time word) cites at least one segment;
1236 | +    - ATTRIBUTION: "<X> says / argues / ...", "<X>: ...", "according to <X>" bind X to a cited segment: by its VERIFIED
1237 | +      speaker, or by its show. A person-like show name with a speech verb needs the speaker verified (law L-v 1: a
1238 | +      person is named only when verified; otherwise credit the show: "on X"). A pronoun or generic subject ("she
1239 | +      says", "analysts say") is unbound;
1240 | +    - NUMBER: every number (canon value and unit, law L-k) is in the sentences of the attribution that governs it
1241 | +      (the nearest one in its sentence), else of the cited segments; a count of the package itself ("three voices")
1242 | +      and "one" as a determiner are production language;
1243 | +    - NAME: every capitalised token that is not an English word (/usr/share/dict/words) is in the cited sentences or
1244 | +      is production metadata (a credited show, a verified speaker, the show date): no person who does not appear (L-t);
1245 | +    - QUOTE: quoted words (double or single quotes) are a verbatim run of the governing segment (canonical form);
1246 | +    - RELATION: words that make speakers agree, answer, rebut or echo each other only when every party is from the same
1247 | +      source video (one conversation); parties are the cited segments, the credited shows named, or a plural party word;
1248 | +    - FRAMING: banned framing verbs (L-t) only when the source itself uses the word;
1249 | +    - IMPERATIVE: no financial imperative or advice framing (buy / sell / leverage / all in / time to buy) (L-t);
1250 | +    - TIME: a recency word (today, overnight, just hit, this month, ...) only when a cited segment says it (L-v 3);
1251 | +    - PRICE_NOW: a price level on ANY line is today's (within tolerance of a level the universe states as current),
1252 | +      or reads as history (a history marker governs it and no present-tense word), or as a forecast (a modal or future
1253 | +      word governs it) (orchestrator 03:40; L-v 3 / L-t).
1254 | +(b) BLIND VERDICT (role "fidelity_verdict" through pipeline/providers.py, never the vendor or model family of the text
1255 | +    it judges): given ONLY the segments' sentences, their shows and verified speakers, the production facts and the
1256 | +    lines, every claim of EVERY line (a connective line too), each yes / no / uncertain with supporting words COPIED
1257 | +    EXACTLY from the line's own cited segments or the production facts. The decision is code: every line covered, every
1258 | +    claim "yes", every support a verbatim run (>= 3 tokens, or a whole shorter segment); anything else fails (law L-m).
1259 | +"""
1260 | +import json
1261 | +import re
1262 | +
1263 | +import canon
1264 | +
1265 | +METADATA = ("PBX MAX", "Protocol Pulse", "Pulse Check", "Bitcoin", "BTC")
1266 | +SPEECH_S = ("says", "said", "argues", "argued", "thinks", "thought", "believes", "believed", "warns", "warned",
1267 | +            "predicts", "predicted", "claims", "claimed", "notes", "noted", "explains", "explained", "expects",
1268 | +            "expected", "sees", "saw", "tells", "told", "adds", "added", "calls", "called", "reckons", "insists",
1269 | +            "insisted", "suggests", "suggested", "writes", "wrote", "asks", "asked", "points out", "pointed out",
1270 | +            "makes the case", "made the case")
1271 | +SPEECH_BASE = ("say", "argue", "think", "believe", "warn", "predict", "claim", "note", "explain", "expect", "see",
1272 | +               "tell", "add", "call", "reckon", "insist", "suggest", "write", "ask", "point out", "make the case")
1273 | +ATTRIB_VERBS = SPEECH_S                                        # (kept for callers that list them)
1274 | +PRONOUN_SUBJECTS = ("he", "she", "they", "his guest", "her guest", "their guest", "the guest", "the host",
1275 | +                    "this guest", "this host", "the speaker", "this speaker", "the analyst", "this analyst",
1276 | +                    "the author", "experts", "analysts", "critics", "many", "some", "others", "people", "everyone")
1277 | +VO_SELF = ("i", "we")                                          # PBX MAX itself: its claims are the verdict's to judge
1278 | +RELATION = re.compile(
1279 | +    r"\b(agree[sd]?|agreeing|disagree[sd]?|disagreeing|respond(s|ed|ing)? to|repl(y|ies|ied|ying) to|"
1280 | +    r"answer(s|ed|ing)? (him|her|them|that|this|the question)|rebut(s|ted|ting)?|push(es|ed|ing)? back|"
1281 | +    r"counter(s|ed|ing)?|fire[sd]? back|echo(es|ed|ing)?|contradict(s|ed|ing)?|"
1282 | +    r"back(s|ed|ing)? (him|her|them|that|this) up|backs? up|sides? with|takes? issue|in response|in contrast|"
1283 | +    r"on the other side|on the other hand|weighs? in|shoots? down|goes further|went further|takes? it further|"
1284 | +    r"(sees?|saw|puts?) it the same way|the same view|similarly|likewise|concur(s|red|ring)?|isn'?t buying it|"
1285 | +    r"(has|takes|had|took) (a different|the opposite|another) (view|take)|different take|"
1286 | +    r"both (say|said|agree|think|warn|see|argue|believe|expect|predict|make)|"
1287 | +    r"all (three|four) (say|agree|think|warn|see|argue|believe|expect|predict)|"
1288 | +    r"(are|were) on the same page|each other|one another)\b", re.I)
1289 | +PARTY_WORDS = re.compile(r"\b(both|all three|all four|they all|the two|these (channels|voices|speakers)|each other|"
1290 | +                         r"one another|everyone)\b", re.I)
1291 | +FRAMING = {"destroy": r"destroy(s|ed|ing)?", "slam": r"slam(s|med|ming)?", "expose": r"expos(e|es|ed|ing)",
1292 | +           "admit": r"admit(s|ted|ting)?", "confirm": r"confirm(s|ed|ing)?", "caught": r"caught",
1293 | +           "torch": r"torch(es|ed|ing)", "blast": r"blast(s|ed|ing)?", "crush": r"crush(es|ed|ing)?",
1294 | +           "debunk": r"debunk(s|ed|ing)?", "obliterate": r"obliterat(e|es|ed|ing)", "demolish": r"demolish(es|ed|ing)?",
1295 | +           "wreck": r"wreck(s|ed|ing)?", "eviscerate": r"eviscerat(e|es|ed|ing)", "humiliate": r"humiliat(e|es|ed|ing)",
1296 | +           "rip into": r"rip(s|ped|ping)? into", "dunk on": r"dunk(s|ed|ing)? on", "bombshell": r"bombshells?",
1297 | +           "reveal": r"reveal(s|ed|ing)?"}
1298 | +_TRADE = r"(buy(ing)?|sell(ing)?|short(ing)?|long|load(ing)? up|ape|go(ing)? all[- ]in|get(ting)? in|stack(ing)?|" \
1299 | +         r"lever(age|aging)?( up)?|bet(ting)?)"
1300 | +_NOT_A_VERB = r"(?![-‐–]|\s+(pressure|side|walls?|orders?|signals?|volume|interest|squeezes?|sellers?|buyers?|term|" \
1301 | +              r"positions?|liquidations?|offs?|programs?|ratios?)\b)"
1302 | +IMPERATIVE = re.compile(
1303 | +    r"\byou(?:'ve|’ve| have|'d|’d| had)?\s+(?:(?:really|probably|definitely|just|absolutely|seriously)\s+)?"
1304 | +    r"(?:should|need to|must|have to|ought to|got to|gotta|better)\s+(?:(?:really|probably|definitely|just|"
1305 | +    r"absolutely|seriously|be)\s+)?" + _TRADE + r"\b"
1306 | +    r"|\b(?:it'?s|it’s|it is|now'?s|now is|now’s)\s+(?:the\s+)?time\s+to\s+(?:buy|sell|get in|load up|stack|"
1307 | +    r"go all[- ]in|back up the truck)\b"
1308 | +    r"|\b(?:don'?t|don’t|do not|never)\s+(?:ever\s+)?(?:sell|buy|miss)\b"
1309 | +    r"|(?:^|[.!?:]\s+|\bso\s+)(?:buy|sell|short|load up|ape in|go all[- ]in|get in now|stack sats|lever up)\b"
1310 | +    + _NOT_A_VERB, re.I)
1311 | +TIME_WORDS = ("today", "tonight", "yesterday", "this morning", "this afternoon", "this evening", "this week",
1312 | +              "this weekend", "this month", "last night", "overnight", "right now", "currently", "at the moment",
1313 | +              "as we speak", "recently", "minutes ago", "hours ago", "breaking news")
1314 | +_TIME_RE = re.compile(r"\bjust\s+(?:\w+ed|hit|set|broke|fell|rose|ran|made|won|lost|got|saw|bought|sold|went|came|"
1315 | +                      r"took|began|flipped|topped)\b|\bbreaking\s*:|\b(?:monday|tuesday|wednesday|thursday|friday|"
1316 | +                      r"saturday|sunday)(?:'s|’s)?\b", re.I)
1317 | +_NUM = re.compile(r"^-?\d+(\.\d+)?$")
1318 | +HISTORY_WORDS = ("since", "back", "ago", "once", "was", "were", "had", "history", "historically", "historic",
1319 | +                 "decade", "decades", "past", "previous", "last cycle", "used to", "low", "bottom")
1320 | +FUTURE_WORDS = ("could", "will", "would", "might", "may", "going", "gonna", "target", "targets", "predict",
1321 | +                "predicts", "predicted", "forecast", "forecasts", "expect", "expects", "expected", "projection",
1322 | +                "reach", "if", "should", "call", "calls", "eventually", "someday")
1323 | +PRESENT_WORDS = ("is", "are", "now", "today", "currently", "trading", "trades", "sits", "sitting", "hovering",
1324 | +                 "tonight", "holds", "holding")
1325 | +PRICE_PREPS = ("at", "to", "hit", "hits", "from", "above", "below", "past", "over", "under", "near", "around",
1326 | +               "trading", "reached", "reaches", "crossed", "crosses", "broke", "breaks", "tops", "topped", "tested",
1327 | +               "tests", "testing", "toward", "towards", "reclaimed", "reclaims", "holds", "held", "sits")
1328 | +COUNT_WORDS = ("bitcoin", "bitcoins", "btc", "coins", "coin", "sats", "satoshis", "holders", "addresses", "people",
1329 | +               "users", "companies", "nodes", "miners", "transactions", "blocks", "times", "percent", "years",
1330 | +               "months", "days", "hours")
1331 | +PRODUCTION_NOUNS = ("clips", "clip", "channels", "channel", "voices", "voice", "shows", "show", "videos", "video",
1332 | +                    "takes", "views", "speakers", "segments", "sources")
1333 | +_QUOTE = re.compile(r"[\"“”]([^\"“”]{2,}?)[\"“”]|(?<![\w’'])[‘']([^‘’']{2,}?)[’'](?![\w’'])")
1334 | +COMMON_CAPS = frozenset("I The This That These Those It And But So We You They He She Here There Now Today Next First "
1335 | +                        "Then Also Plus Meanwhile Still Yet Why What How When Where Who Which Our Your Their Its "
1336 | +                        "Let Let's Clips Go Links Follow Watch Stay A An In On At For From With As If Not No Yes "
1337 | +                        "One Two Three Four Five Six Seven Eight Nine Ten Here's That's It's".split())
1338 | +PRODUCTION_WORDS = frozenset({"pbx", "max", "protocol", "pulse", "check", "bitcoin", "btc", "sats", "hodl", "crypto"})
1339 | +_LEX = None
1340 | +
1341 | +
1342 | +def lexicon():
1343 | +    """Lower-case English words (the system word list) + production words. A capitalised token that is not one of
1344 | +    them is a NAME candidate. Without the word list every capitalised token is a candidate (fail closed)."""
1345 | +    global _LEX
1346 | +    if _LEX is None:
1347 | +        words = set(PRODUCTION_WORDS)
1348 | +        try:
1349 | +            with open("/usr/share/dict/words") as f:
1350 | +                words |= {w.strip() for w in f if w.strip() and w.strip().islower()}
1351 | +        except OSError:
1352 | +            pass
1353 | +        _LEX = frozenset(words)
1354 | +    return _LEX
1355 | +
1356 | +
1357 | +def ctoks(text):
1358 | +    return canon.canon_tokens(text or "")
1359 | +
1360 | +
1361 | +def _run_in(sub, toks):
1362 | +    """sub (canonical tokens) occurs as a contiguous run in toks."""
1363 | +    n = len(sub)
1364 | +    return n > 0 and any(toks[i:i + n] == sub for i in range(len(toks) - n + 1))
1365 | +
1366 | +
1367 | +def _fold(w):
1368 | +    """A token for name matching: lower case, possessive and plural folded."""
1369 | +    w = re.sub(r"(['’]s|['’])$", "", (w or "").lower().strip(".,;:!?\"“”()"))
1370 | +    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
1371 | +
1372 | +
1373 | +def _folds(text):
1374 | +    return [_fold(w) for w in re.findall(r"[A-Za-z0-9][\w'’&.-]*", text or "") if _fold(w)]
1375 | +
1376 | +
1377 | +def numbers_of(text):
1378 | +    """[(value, unit or None)] in canonical form: '$73,000' -> ('73000', 'dollars'); '16%' -> ('16', 'percent')."""
1379 | +    t = ctoks(text)
1380 | +    out = []
1381 | +    for i, w in enumerate(t):
1382 | +        if _NUM.match(w):
1383 | +            unit = t[i + 1] if i + 1 < len(t) and t[i + 1] in ("dollars", "percent") else None
1384 | +            out.append((w, unit))
1385 | +    return out
1386 | +
1387 | +
1388 | +def _has_number(src_toks, value, unit):
1389 | +    for i, w in enumerate(src_toks):
1390 | +        if w == value and (unit is None or (i + 1 < len(src_toks) and src_toks[i + 1] == unit)):
1391 | +            return True
1392 | +    return False
1393 | +
1394 | +
1395 | +# ── price levels (PRICE_NOW, orchestrator 03:40) ──
1396 | +
1397 | +def _sentences(text):
1398 | +    return [s for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]
1399 | +
1400 | +
1401 | +def _clauses(sentence):
1402 | +    return [c for c in re.split(r"[;—–]|,\s|:\s", sentence) if c.strip()]
1403 | +
1404 | +
1405 | +def _price_values(toks):
1406 | +    """[(index, value)] of the price-like numbers of canonical tokens: a money amount of 1,000-10,000,000 dollars, or
1407 | +    10,000-1,000,000 after a price word ('at', 'to', 'hit', 'trading', ...); never a count of coins or holders."""
1408 | +    out = []
1409 | +    for i, w in enumerate(toks):
1410 | +        if not _NUM.match(w):
1411 | +            continue
1412 | +        v = float(w)
1413 | +        nxt = toks[i + 1] if i + 1 < len(toks) else ""
1414 | +        prv = toks[i - 1] if i > 0 else ""
1415 | +        if nxt in COUNT_WORDS:
1416 | +            continue
1417 | +        if (nxt == "dollars" and 1_000 <= v <= 10_000_000) or (10_000 <= v <= 1_000_000 and prv in PRICE_PREPS):
1418 | +            out.append((i, v))
1419 | +    return out
1420 | +
1421 | +
1422 | +def _has(words, toks):
1423 | +    for w in words:
1424 | +        wt = w.split()
1425 | +        if _run_in(wt, toks):
1426 | +            return True
1427 | +    return False
1428 | +
1429 | +
1430 | +def price_mentions(text):
1431 | +    """[(value, kind)] for each price-like number of a line: kind "future" (a modal / future word before it in its
1432 | +    clause), "history" (a history marker or a year before it in its sentence, and no present-tense word in its clause),
1433 | +    else "current"."""
1434 | +    out = []
1435 | +    for s in _sentences(text):
1436 | +        st = ctoks(s)
1437 | +        for c in _clauses(s):
1438 | +            ct = ctoks(c)
1439 | +            for i, v in _price_values(ct):
1440 | +                before = ct[:i]
1441 | +                k = _run_find(ct, st)
1442 | +                sent_before = st[:k + i] if k is not None else st
1443 | +                year_before = any(re.fullmatch(r"(19|20)\d\d", t) for t in sent_before if t != ct[i])
1444 | +                by_year_after = any(ct[j] == "by" and j + 1 < len(ct) and re.fullmatch(r"(19|20)\d\d", ct[j + 1])
1445 | +                                    for j in range(i + 1, len(ct) - 1))
1446 | +                if _has(FUTURE_WORDS, before) or by_year_after:
1447 | +                    out.append((v, "future"))
1448 | +                elif (year_before or _has(HISTORY_WORDS, sent_before)) and not _has(PRESENT_WORDS, before):
1449 | +                    out.append((v, "history"))
1450 | +                else:
1451 | +                    out.append((v, "current"))
1452 | +    return out
1453 | +
1454 | +
1455 | +def _run_find(sub, toks):
1456 | +    n = len(sub)
1457 | +    for i in range(len(toks) - n + 1):
1458 | +        if toks[i:i + n] == sub:
1459 | +            return i
1460 | +    return None
1461 | +
1462 | +
1463 | +def price_levels(text):
1464 | +    """Every price-like value a line states (any kind)."""
1465 | +    return [v for v, _ in price_mentions(text)]
1466 | +
1467 | +
1468 | +def current_level_values(sentence):
1469 | +    """The levels one source sentence states as CURRENT: a price in a clause with a present-tense word before it and no
1470 | +    future / conditional / history word anywhere in the sentence (package.current_levels)."""
1471 | +    st = ctoks(sentence)
1472 | +    if _has(FUTURE_WORDS, st) or _has(HISTORY_WORDS, st) or any(re.fullmatch(r"(19|20)\d\d", t) for t in st):
1473 | +        return []
1474 | +    out = []
1475 | +    for c in _clauses(sentence):
1476 | +        ct = ctoks(c)
1477 | +        out += [v for i, v in _price_values(ct) if _has(PRESENT_WORDS, ct[:i]) and 10_000 <= v <= 1_000_000]
1478 | +    return out
1479 | +
1480 | +
1481 | +def price_now(text, current_levels, tolerance=0.05):
1482 | +    """PRICE_NOW: the CURRENT-kind price values of a line that match no current level within tolerance. -> [values]."""
1483 | +    cur = [float(c) for c in current_levels or ()]
1484 | +    return [v for v, kind in price_mentions(text)
1485 | +            if kind == "current" and not any(abs(v - c) <= tolerance * c for c in cur if c > 0)]
1486 | +
1487 | +
1488 | +# ── names and attribution ──
1489 | +
1490 | +def _segment_names(s):
1491 | +    """A segment's VERIFIED speaker names (empty when the speaker is not verified)."""
1492 | +    return [n for n in [s.get("speaker")] + list(s.get("names") or []) if n]
1493 | +
1494 | +
1495 | +def _show(s):
1496 | +    return s.get("show") or s.get("speaker") or ""
1497 | +
1498 | +
1499 | +def person_like(name):
1500 | +    """A show named like a person: two or more capitalised tokens, none an English word ('Natalie Brunell')."""
1501 | +    ws = re.findall(r"[A-Za-z][A-Za-z'’.-]*", name or "")
1502 | +    return len(ws) >= 2 and all(w[0].isupper() and _fold(w) not in lexicon() for w in ws)
1503 | +
1504 | +
1505 | +def manifest_terms(segments, manifest=None):
1506 | +    """Production metadata a line may state without a citation (never a claim about what anyone said): the credited
1507 | +    shows and verified speaker names, the show, the date (month, weekday) and the package's own counts."""
1508 | +    from datetime import date
1509 | +    names = {n for s in segments.values() for n in [_show(s)] + _segment_names(s) if n}
1510 | +    m = manifest or {}
1511 | +    names |= set(m.get("channels") or []) | ({m["show"]} if m.get("show") else set())
1512 | +    nums = {str(len(segments)), str(len({s["video_id"] for s in segments.values()})),
1513 | +            str(len(set(m.get("channels") or []) or {_show(s) for s in segments.values()}))}
1514 | +    if m.get("date"):
1515 | +        try:
1516 | +            d = date.fromisoformat(m["date"])
1517 | +            names |= {d.strftime("%B"), d.strftime("%A"), d.strftime("%b")}
1518 | +        except ValueError:
1519 | +            pass
1520 | +    return sorted(names), nums
1521 | +
1522 | +
1523 | +def names_of(text, allowed=()):
1524 | +    """NAME candidates of a line: capitalised tokens (or all-caps acronyms) that are not English words, production
1525 | +    metadata or allowed terms, wherever they stand (a Title Case line and a sentence start included)."""
1526 | +    ok = {f for a in tuple(allowed) + METADATA for f in _folds(a)}
1527 | +    out = []
1528 | +    for w in re.findall(r"[A-Za-z][A-Za-z'’.&-]*", text or ""):
1529 | +        core = re.sub(r"(['’]s|['’])$", "", w.strip(".-"))
1530 | +        if not core or not core[0].isupper():
1531 | +            continue
1532 | +        parts = [p for p in re.split(r"[-.&]", core) if p]
1533 | +        acronym = core.isupper() and len(core) >= 2
1534 | +        if not acronym and all(p.lower() in lexicon() for p in parts):
1535 | +            continue
1536 | +        if core in ("I", "A") or _fold(core) in ok:
1537 | +            continue
1538 | +        out.append(core)
1539 | +    return list(dict.fromkeys(out))
1540 | +
1541 | +
1542 | +_CAPRUN = r"[A-Z][\w'’.&-]*(?:\s+(?:of|and|&|de|van|von|da)\s+[A-Z][\w'’.&-]*|\s+[A-Z][\w'’.&-]*){0,5}"
1543 | +
1544 | +
1545 | +def _verbs(forms):
1546 | +    return "|".join(re.escape(v) for v in sorted(forms, key=len, reverse=True))
1547 | +
1548 | +
1549 | +def _attributions(text):
1550 | +    """[(subject, form, start)] in order: '<Subject> <speech verb>' (case-insensitive verb, capitalised subject),
1551 | +    '<pronoun or generic subject> <speech verb>', '<Subject>: ...' (at a sentence start), 'according to <Subject>'."""
1552 | +    out = []
1553 | +    t = text or ""
1554 | +    for m in re.finditer(r"(" + _CAPRUN + r")\s+(?:also\s+|now\s+|still\s+|even\s+)?(?i:" + _verbs(SPEECH_S + SPEECH_BASE)
1555 | +                         + r")\b", t):
1556 | +        out.append((m.group(1), "speech", m.start()))
1557 | +    for m in re.finditer(r"(?i:\b(" + "|".join(re.escape(p) for p in PRONOUN_SUBJECTS) + r")\s+(?:also\s+)?(?:"
1558 | +                         + _verbs(SPEECH_S + SPEECH_BASE) + r")\b)", t):
1559 | +        if not any(a[2] <= m.start() < a[2] + len(a[0]) + 1 for a in out):
1560 | +            out.append((m.group(1), "pronoun", m.start()))
1561 | +    for m in re.finditer(r"(?:^|[.!?]\s+|\b(?:Next|Then|And|Here's|Now),?\s+)(" + _CAPRUN + r"):\s", t):
1562 | +        out.append((m.group(1), "colon", m.start(1)))
1563 | +    for m in re.finditer(r"(?i:according to)\s+(" + _CAPRUN + r")", t):
1564 | +        out.append((m.group(1), "according", m.start()))
1565 | +    out.sort(key=lambda a: a[2])
1566 | +    return out
1567 | +
1568 | +
1569 | +def _clean_subject(subj):
1570 | +    ws = subj.split()
1571 | +    while ws and ws[0].strip(",") in COMMON_CAPS:
1572 | +        ws = ws[1:]
1573 | +    return " ".join(ws)
1574 | +
1575 | +
1576 | +def _match(subject, name):
1577 | +    s, n = _folds(subject), _folds(name)
1578 | +    return bool(s and n) and (_run_in(n, s) or _run_in(s, n))
1579 | +
1580 | +
1581 | +def _governed(text, atts):
1582 | +    """Split a line into (chunk text, attribution index or None): each attribution governs its sentence from its
1583 | +    position to the next attribution; the words before a sentence's first attribution belong to it as well ('..., says
1584 | +    X'); a sentence without one is governed by the cited segments (None)."""
1585 | +    out, pos = [], 0
1586 | +    for s in _sentences(text):
1587 | +        start = (text or "").find(s, pos)
1588 | +        end = start + len(s)
1589 | +        pos = end
1590 | +        inside = [(i, a) for i, a in enumerate(atts) if start <= a[2] < end]
1591 | +        if not inside:
1592 | +            out.append((s, None))
1593 | +            continue
1594 | +        cuts = [a[2] for _, a in inside] + [end]
1595 | +        out.append((text[start:cuts[1]], inside[0][0]))
1596 | +        for k in range(1, len(inside)):
1597 | +            out.append((text[cuts[k]:cuts[k + 1]], inside[k][0]))
1598 | +    return out
1599 | +
1600 | +
1601 | +_META_FOLDS = frozenset(f for m in METADATA for f in _folds(m))
1602 | +_OPINION = {"think": ("thinks", "think", "thought", "believes", "believe", "believed", "reckons", "reckon"),
1603 | +            "feel": ("feels", "feel", "felt"),
1604 | +            "believe": ("believes", "believe", "believed", "thinks", "think", "thought"),
1605 | +            "guess": ("guesses", "guess", "suspects", "suspect", "thinks", "think", "reckons", "reckon"),
1606 | +            "suspect": ("suspects", "suspect", "thinks", "think", "reckons", "reckon"),
1607 | +            "reckon": ("reckons", "reckon", "thinks", "think")}
1608 | +_OPINION_RE = re.compile(r"\bI\s+(?:really\s+|just\s+|do\s+|personally\s+|kind of\s+|kinda\s+|still\s+)?"
1609 | +                         r"(think|feel|believe|guess|suspect|reckon)\b|\b(in my (?:opinion|view)|to me,|I'd say|"
1610 | +                         r"I would say|my sense is|my view is|my take is)", re.I)
1611 | +
1612 | +
1613 | +def hedge_markers(text):
1614 | +    """The clip's own opinion markers ('I think', 'I feel like', 'in my opinion', ...)."""
1615 | +    return [m.group(0) for m in _OPINION_RE.finditer(text or "")]
1616 | +
1617 | +
1618 | +def hedge_verbs(text):
1619 | +    """The attribution verbs a clip's hedges allow (orchestrator 05:25 item 2: 'thinks' for 'I think', 'feels' for 'I
1620 | +    feel like', 'says' only for a flat assertion). Empty when the clip has no opinion marker."""
1621 | +    need = set()
1622 | +    for m in _OPINION_RE.finditer(text or ""):
1623 | +        need |= set(_OPINION[m.group(1).lower()]) if m.group(1) else {"thinks", "think", "feels", "feel", "believes",
1624 | +                                                                        "believe", "reckons", "reckon"}
1625 | +    return need
1626 | +
1627 | +
1628 | +def _speech_verb(subj0, form, text, start):
1629 | +    """The speech verb right after an attribution's subject (None for the colon / 'according to' forms)."""
1630 | +    if form not in ("speech", "pronoun"):
1631 | +        return None
1632 | +    m = re.match(r"\s+(?:also\s+|now\s+|still\s+|even\s+)?(" + _verbs(SPEECH_S + SPEECH_BASE) + r")\b",
1633 | +                 (text or "")[start + len(subj0):], re.I)
1634 | +    return m.group(1).lower() if m else None
1635 | +
1636 | +
1637 | +def time_words(text, meta=()):
1638 | +    """Recency words of a line (L-v 3); the show date's own weekday is production metadata."""
1639 | +    out = [w for w in TIME_WORDS if re.search(r"\b" + re.escape(w) + r"\b", text or "", re.I)]
1640 | +    for m in _TIME_RE.finditer(text or ""):
1641 | +        if re.sub(r"['’]s$", "", m.group(0)).strip().title() not in set(meta):
1642 | +            out.append(m.group(0))
1643 | +    return out
1644 | +
1645 | +
1646 | +def fact_numbers(text, meta_nums=frozenset()):
1647 | +    """The numbers of a text that state a fact, [(value, unit)]: leaves out the package's own count beside a production
1648 | +    noun ('three voices') and 'one' written as a word (a determiner or pronoun: 'one thing', 'one of')."""
1649 | +    out, t = [], ctoks(text)
1650 | +    plain = (text or "").replace(",", "")
1651 | +    for i, w in enumerate(t):
1652 | +        if not _NUM.match(w):
1653 | +            continue
1654 | +        unit = t[i + 1] if i + 1 < len(t) and t[i + 1] in ("dollars", "percent") else None
1655 | +        spelled = not re.search(rf"(?<![\d.]){re.escape(w)}(?![\d])", plain)
1656 | +        if unit is None and w in meta_nums and any(x in PRODUCTION_NOUNS for x in t[i + 1:i + 3]):
1657 | +            continue
1658 | +        if unit is None and w == "1" and spelled:
1659 | +            continue
1660 | +        out.append((w, unit))
1661 | +    return out
1662 | +
1663 | +
1664 | +def check_deterministic(segments, lines, manifest=None, current_levels=None):
1665 | +    """segments: {moment_id: {"show": the credited channel, "speaker": the VERIFIED speaker's name or None, "names":
1666 | +    [verified names], "video_id", "text"}} (a caller without "show" passes the speaker as both); lines: [{"slot", "text",
1667 | +    "cites": [moment_id, ...]}] (VO lines, the title, the caption); manifest: {"channels", "date", "show"};
1668 | +    current_levels: the universe's current price levels (None: PRICE_NOW not measured).
1669 | +    -> {"ok", "violations": [{"slot", "rule", "detail"}], "price_now_measured"}."""
1670 | +    v = []
1671 | +    meta, meta_nums = manifest_terms(segments, manifest)
1672 | +    seg_toks = {mid: ctoks(s["text"]) for mid, s in segments.items()}
1673 | +    for ln in lines:
1674 | +        slot, text = ln["slot"], ln.get("text") or ""
1675 | +        cites = [c for c in (ln.get("cites") or []) if isinstance(c, str)]
1676 | +        V = lambda rule, detail: v.append({"slot": slot, "rule": rule, "detail": detail})
1677 | +        unknown = [c for c in ln.get("cites") or [] if not isinstance(c, str) or c not in segments]
1678 | +        if unknown:
1679 | +            V("CITE_UNKNOWN", f"cites {unknown} are not segments of this package")
1680 | +        cited = [c for c in cites if c in segments]
1681 | +        pool = [t for c in cited for t in seg_toks[c]]
1682 | +        atts = _attributions(text)
1683 | +        names = names_of(text, meta)
1684 | +        quotes = [q for pair in _QUOTE.findall(text) for q in pair if q]
1685 | +        times = time_words(text, meta)
1686 | +        if (fact_numbers(text, meta_nums) or names or quotes or atts or times) and not cited:
1687 | +            V("NEEDS_SOURCE", "a line with a number, name, quote, attribution or time word cites no segment")
1688 | +        pools = []                                                   # per attribution: the governing segments
1689 | +        for subj0, form, _ in atts:
1690 | +            subj = _clean_subject(subj0)
1691 | +            words0 = subj0.lower().split()
1692 | +            if form == "pronoun" or subj.lower() in PRONOUN_SUBJECTS or (not subj and words0 and
1693 | +                                                                         words0[-1] in PRONOUN_SUBJECTS + VO_SELF):
1694 | +                who = (subj or (words0[-1] if words0 else "")).lower()
1695 | +                if who not in VO_SELF:
1696 | +                    V("ATTRIBUTION", f"'{subj0.strip()} ...': name who speaks, by the show ('on <show>') or by a "
1697 | +                                     f"verified name")
1698 | +                pools.append(None)
1699 | +                continue
1700 | +            if not subj:
1701 | +                pools.append(None)
1702 | +                continue
1703 | +            by_speaker = [c for c in cited if any(_match(subj, n) for n in _segment_names(segments[c]))]
1704 | +            by_show = [c for c in cited if c not in by_speaker and _match(subj, _show(segments[c]))]
1705 | +            if by_speaker:
1706 | +                pools.append(by_speaker)
1707 | +            elif by_show:
1708 | +                if form == "speech" and person_like(_show(segments[by_show[0]])):
1709 | +                    V("ATTRIBUTION", f"'{subj}' with a speech verb names a person, but the speaker of "
1710 | +                                     f"{_show(segments[by_show[0]])}'s clip is not verified (law L-v 1): credit the show "
1711 | +                                     f"('on {_show(segments[by_show[0]])}')")
1712 | +                pools.append(by_show)
1713 | +            elif all(_fold(w) in lexicon() or _fold(w) in _META_FOLDS for w in subj.split()):
1714 | +                if form in ("speech", "according"):                  # "Analysts say", "according to experts"
1715 | +                    V("ATTRIBUTION", f"'{subj}' is not a speaker of this package: name who speaks, by the show "
1716 | +                                     f"('on <show>') or by a verified name")
1717 | +                pools.append(None)                                   # "Bitcoin: ..." is a label, not a speaker
1718 | +            else:
1719 | +                V("ATTRIBUTION", f"'{subj}': no cited segment is spoken by {subj} or comes from that show")
1720 | +                pools.append(None)
1721 | +        for (subj0, form, start), segs_ in zip(atts, pools):
1722 | +            verb = _speech_verb(subj0, form, text, start)
1723 | +            for c in segs_ or []:
1724 | +                need = hedge_verbs(segments[c]["text"])
1725 | +                if verb and need and verb not in need:
1726 | +                    V("HEDGE", f"'{verb}' makes {_show(segments[c])}'s clip sound firmer than it is: the clip hedges "
1727 | +                               f"('{hedge_markers(segments[c]['text'])[0]}'); use {sorted(need)[:3]}")
1728 | +        for chunk, ai in _governed(text, atts):
1729 | +            gov = pools[ai] if ai is not None and pools[ai] else cited
1730 | +            gpool = [t for c in gov for t in seg_toks[c]]
1731 | +            for val, unit in fact_numbers(chunk, meta_nums):
1732 | +                if not _has_number(gpool, val, unit):
1733 | +                    V("NUMBER", f"{val}{' ' + unit if unit else ''} is not in the cited sentences" +
1734 | +                      (" of the attributed speaker / show" if ai is not None and pools[ai] else ""))
1735 | +            for q in [q for pair in _QUOTE.findall(chunk) for q in pair if q]:
1736 | +                if not any(_run_in(ctoks(q), seg_toks[c]) for c in gov):
1737 | +                    V("QUOTE", f"\"{q}\" is not a verbatim run of the " +
1738 | +                      ("attributed speaker's" if ai is not None and pools[ai] else "cited") + " sentences")
1739 | +        pool_f = {_fold(t) for t in pool} | {_fold(t) for c in cited for t in re.findall(r"[\w'’]+", segments[c]["text"])}
1740 | +        for n in names:
1741 | +            if _fold(n) not in pool_f:
1742 | +                V("NAME", f"'{n}' is not said in the cited sentences (and is not a credited show, a verified speaker or "
1743 | +                          f"the show date)")
1744 | +        parties = {segments[c]["video_id"] for c in cited}
1745 | +        named = {segments[c]["video_id"] for c in segments if _show(segments[c]) and
1746 | +                 re.search(r"\b" + re.escape(_show(segments[c])) + r"\b", text)}
1747 | +        if PARTY_WORDS.search(text):
1748 | +            named |= {s["video_id"] for s in segments.values()}
1749 | +        rel = RELATION.search(text)
1750 | +        if rel and len(parties | named) > 1:
1751 | +            V("RELATION", f"'{rel.group(0)}' relates speakers who were not in one conversation")
1752 | +        for lemma, pat in FRAMING.items():
1753 | +            if re.search(r"\b" + pat + r"\b", text, re.I) and not any(
1754 | +                    re.search(r"\b" + pat + r"\b", segments[c]["text"], re.I) for c in cited):
1755 | +                V("FRAMING", f"'{lemma}' framing is not the source's own word (L-t)")
1756 | +        if IMPERATIVE.search(text):
1757 | +            V("IMPERATIVE", f"financial imperative or advice framing: '{IMPERATIVE.search(text).group(0).strip()}'")
1758 | +        for w in times:
1759 | +            if not any(_run_in(ctoks(w), seg_toks[c]) for c in cited):
1760 | +                V("TIME", f"'{w}' is not said in the cited sentences (L-v 3: time words need the source's own)")
1761 | +        if current_levels is not None:
1762 | +            stale = price_now(text, current_levels)
1763 | +            if stale:
1764 | +                V("PRICE_NOW", f"states the level(s) {stale} as if current, but this universe's current levels are "
1765 | +                               f"{sorted(set(current_levels))[:6]}; mark it as history or drop it (L-v 3 / L-t)")
1766 | +    return {"ok": not v, "violations": v, "price_now_measured": current_levels is not None}
1767 | +
1768 | +
1769 | +CLASSES = ("attribution", "fact", "production", "commentary")
1770 | +COMMENTARY_TESTS = ("fact", "speaker_view", "imperative_or_prediction", "accusation", "sounds_like_a_speaker")
1771 | +VERDICT_PROMPT = """You check a short video script for fidelity to its sources. You see ONLY the words each clip's
1772 | +speaker said (the segments, each with its show and whether the speaker's identity is verified), the production facts
1773 | +(true by construction), and the script's lines (voice-over, title, caption), each with the clips it cites.
1774 | +
1775 | +SEGMENTS:
1776 | +{segments}
1777 | +
1778 | +PRODUCTION FACTS (segment label "manifest"):
1779 | +{manifest}
1780 | +
1781 | +SCRIPT LINES:
1782 | +{lines}
1783 | +
1784 | +Split every line into its claims and CLASSIFY each claim:
1785 | +- "attribution": says or implies what a named speaker or show said, thinks, feels or did; who a speaker is; any
1786 | +  agreement, answer or disagreement between speakers;
1787 | +- "fact": a checkable statement about the world in the voice-over's own voice: a number, price, date, event, or a named
1788 | +  person or company doing something;
1789 | +- "production": what the video itself is: its channels, how many clips or voices, credits, "next", "links below";
1790 | +- "commentary": the host's OWN opinion, framing, question, tease or takeaway, attributed to nobody.
1791 | +When unsure between commentary and attribution or fact, choose attribution or fact.
1792 | +EVERY sentence of every line belongs to at least one claim. Give each claim's "words": its exact words in the line.
1793 | +For an attribution, fact or production claim, "supported" is "yes" only if the words you cite state it with the same
1794 | +meaning and polarity and the SAME OR WEAKER certainty, adding nothing; "no" if they do not; "uncertain" if you cannot
1795 | +tell. Attribution and fact claims cite ONLY the segments their line cites; production claims cite "manifest". A claim
1796 | +that a NAMED PERSON said or thinks something is "yes" only if that segment's speaker is verified as that person. Copy
1797 | +every supporting run EXACTLY (a continuous run of at least three words, or the whole segment if it is shorter); several
1798 | +segments may support one claim together, each with its own words. Set "tests" to {{}}.
1799 | +For a commentary claim, set "supported" to "n/a" and "support" to [], and answer each test "yes", "no" or "uncertain"
1800 | +in "tests": "fact" (does it state a checkable fact, number, price, date or a named person or company?),
1801 | +"speaker_view" (does it characterise any speaker's view, or how one speaker relates to another?),
1802 | +"imperative_or_prediction" (financial advice, or a prediction?), "accusation", "sounds_like_a_speaker" (could a viewer
1803 | +take it for something a speaker said: in quotation marks, or after "as X put it"?).
1804 | +Return ONLY this JSON object: {{"claims": [{{"line": "<slot>", "words": "<exact words of the line>", "class":
1805 | +"attribution" | "fact" | "production" | "commentary", "claim": "...", "supported": "yes" | "no" | "uncertain" | "n/a",
1806 | +"support": [{{"segment": "<label>", "words": "<exact words>"}}], "tests": {{}}}}]}}"""
1807 | +
1808 | +
1809 | +def manifest_text(segments, manifest=None):
1810 | +    """The production facts a line may state: the credited shows, the show, the date, that source links are given."""
1811 | +    m = manifest or {}
1812 | +    chans = list(dict.fromkeys(list(m.get("channels") or []) + [_show(s) for s in segments.values()]))
1813 | +    parts = [f"The video is about Bitcoin and contains clips from {', '.join(chans)}.", f"There are {len(segments)} clips.",
1814 | +             "Links to every source are below.", "The voice-over is PBX MAX on Protocol Pulse."]
1815 | +    if m.get("show"):
1816 | +        parts.append(f"The show is {m['show']}.")
1817 | +    if m.get("date"):
1818 | +        parts.append(f"The show date is {m['date']}.")
1819 | +    return " ".join(parts)
1820 | +
1821 | +
1822 | +def verdict_prompt(segments, lines, manifest=None):
1823 | +    from story_semantics import quote_data
1824 | +    seg = "\n".join(
1825 | +        f'<segment label="{mid}" show="{quote_data(_show(s), 80)}" speaker="'
1826 | +        f'{quote_data(s["speaker"], 80) + " (verified)" if s.get("speaker") else "not verified"}">'
1827 | +        f'{quote_data(s["text"], 900)}</segment>' for mid, s in segments.items())
1828 | +    lns = "\n".join(f'<line slot="{ln["slot"]}" cites="{", ".join(str(c) for c in ln.get("cites") or []) or "none"}">'
1829 | +                    f'{quote_data(ln.get("text") or "", 400)}</line>' for ln in lines)
1830 | +    return VERDICT_PROMPT.format(segments=seg, lines=lns, manifest=manifest_text(segments, manifest))
1831 | +
1832 | +
1833 | +def strict_features(words, segments, manifest=None):
1834 | +    """What makes words NOT host commentary by rule (05:25 item 2, tests i, iii, v): a fact number, a name that is not
1835 | +    production metadata, a quote, an attribution, a price, a time word, a financial imperative, a relation or framing
1836 | +    word, 'as X put it'. -> [feature, ...] (empty: the words may be commentary)."""
1837 | +    meta, meta_nums = manifest_terms(segments, manifest)
1838 | +    out = []
1839 | +    if fact_numbers(words, meta_nums):
1840 | +        out.append("a number")
1841 | +    if names_of(words, meta):
1842 | +        out.append(f"a name ({', '.join(names_of(words, meta)[:3])})")
1843 | +    if [q for pair in _QUOTE.findall(words) for q in pair if q] or re.search(r"\bas \w+(\s\w+)? (put|puts|said) it\b",
1844 | +                                                                               words, re.I):
1845 | +        out.append("a quotation")
1846 | +    if [a for a in _attributions(words) if a[1] != "colon" or _clean_subject(a[0])]:
1847 | +        out.append("an attribution")
1848 | +    if price_mentions(words):
1849 | +        out.append("a price")
1850 | +    if time_words(words, meta):
1851 | +        out.append("a time word")
1852 | +    if IMPERATIVE.search(words):
1853 | +        out.append("a financial imperative")
1854 | +    if RELATION.search(words) or any(re.search(r"\b" + p + r"\b", words, re.I) for p in FRAMING.values()):
1855 | +        out.append("a relation or framing word")
1856 | +    return out
1857 | +
1858 | +
1859 | +def check_verdict(raw, segments, lines, manifest=None):
1860 | +    """The blind CLASSIFYING verdict's reply (strict; never repaired) -> {"ok", "claims", "violations", "classes"}.
1861 | +    Every sentence of every line is covered by a claim whose words are the line's own. Attribution / fact: "yes" with
1862 | +    supports from the line's own cited segments; production: "yes" with supports from the manifest; each support a
1863 | +    verbatim run (>= 3 tokens, or a whole shorter text). Commentary: every test "no", and none of the rule features
1864 | +    (strict_features) - a commentary label on words that carry one is judged as a fact with no support (strict by
1865 | +    default, 05:25 item 2). Anything else fails (law L-m)."""
1866 | +    obj = json.loads(raw.strip()) if isinstance(raw, str) else None
1867 | +    if not isinstance(obj, dict) or set(obj) != {"claims"} or not isinstance(obj["claims"], list):
1868 | +        raise ValueError("the verdict must be exactly {'claims': [...]}")
1869 | +    by_slot = {ln["slot"]: ln for ln in lines}
1870 | +    cites = {s: [c for c in ln.get("cites") or [] if isinstance(c, str)] for s, ln in by_slot.items()}
1871 | +    texts = dict({mid: s["text"] for mid, s in segments.items()}, manifest=manifest_text(segments, manifest))
1872 | +    v, cover, classes = [], {s: [] for s in by_slot}, {}
1873 | +    keys = {"line", "words", "class", "claim", "supported", "support", "tests"}
1874 | +    for c in obj["claims"]:
1875 | +        if not isinstance(c, dict) or set(c) != keys:
1876 | +            raise ValueError(f"each claim needs exactly {sorted(keys)}")
1877 | +        if not isinstance(c["line"], str) or c["line"] not in by_slot or not isinstance(c["words"], str) or \
1878 | +                c["class"] not in CLASSES or not isinstance(c["claim"], str) or not isinstance(c["support"], list) or \
1879 | +                not isinstance(c["tests"], dict) or c["supported"] not in ("yes", "no", "uncertain", "n/a"):
1880 | +            raise ValueError(f"claim on line {str(c.get('line'))[:40]!r}: a field is out of its contract")
1881 | +        slot, lt, wt = c["line"], ctoks(by_slot[c["line"]]["text"]), ctoks(c["words"])
1882 | +        at = _run_find(wt, lt) if wt else None
1883 | +        if at is None:
1884 | +            v.append({"slot": slot, "rule": "VERDICT_WORDS", "detail": f"the claim's words are not the line's own: "
1885 | +                                                                       f"{c['words'][:120]!r}"})
1886 | +            continue
1887 | +        cover[slot].append((at, at + len(wt)))
1888 | +        classes.setdefault(slot, []).append(c["class"])
1889 | +        if c["class"] == "commentary":
1890 | +            if c["supported"] != "n/a" or c["support"] or set(c["tests"]) != set(COMMENTARY_TESTS) or \
1891 | +                    any(x not in ("yes", "no", "uncertain") for x in c["tests"].values()):
1892 | +                raise ValueError("a commentary claim needs supported 'n/a', support [] and exactly the five tests")
1893 | +            feats = strict_features(c["words"], segments, manifest)
1894 | +            if feats:
1895 | +                v.append({"slot": slot, "rule": "NOT_COMMENTARY",
1896 | +                          "detail": f"'{c['words'][:100]}' is labelled commentary but carries {', '.join(feats)}: as an "
1897 | +                                    f"attribution or fact it has no support"})
1898 | +                continue
1899 | +            failed = [t for t in COMMENTARY_TESTS if c["tests"][t] != "no"]
1900 | +            if failed:
1901 | +                v.append({"slot": slot, "rule": "COMMENTARY",
1902 | +                          "detail": f"host commentary '{c['words'][:100]}' fails {', '.join(failed)}"})
1903 | +            continue
1904 | +        if c["tests"] != {} or c["supported"] == "n/a":
1905 | +            raise ValueError("an attribution / fact / production claim needs supported yes|no|uncertain and tests {}")
1906 | +        if c["supported"] != "yes":
1907 | +            v.append({"slot": slot, "rule": "VERDICT_" + c["supported"].upper(), "detail": c["claim"][:200]})
1908 | +            continue
1909 | +        allowed = {"manifest"} if c["class"] == "production" else set(cites[slot])
1910 | +        good = []
1911 | +        for x in c["support"]:
1912 | +            if isinstance(x, dict) and set(x) == {"segment", "words"} and isinstance(x["segment"], str) and \
1913 | +                    isinstance(x["words"], str) and x["segment"] in allowed and x["segment"] in texts:
1914 | +                st, xt = ctoks(texts[x["segment"]]), ctoks(x["words"])
1915 | +                if _run_in(xt, st) and (len(xt) >= 3 or xt == st):
1916 | +                    good.append(x)
1917 | +        if not c["support"] or len(good) != len(c["support"]):
1918 | +            v.append({"slot": slot, "rule": "VERDICT_UNVERIFIED",
1919 | +                      "detail": f"supports are not verbatim runs (>= 3 words) of " +
1920 | +                                ("the production facts" if c["class"] == "production" else "the line's own cited "
1921 | +                                                                                           "segments") +
1922 | +                                f": {c['claim'][:150]}"})
1923 | +    for slot, ln in by_slot.items():
1924 | +        lt, pos = ctoks(ln.get("text") or ""), 0
1925 | +        for sent in _sentences(ln.get("text") or ""):
1926 | +            st = ctoks(sent)
1927 | +            at = _run_find(st, lt[pos:]) if st else None
1928 | +            if at is None:
1929 | +                continue
1930 | +            a, b = pos + at, pos + at + len(st)
1931 | +            pos = b
1932 | +            if not any(x < b and y > a for x, y in cover[slot]):
1933 | +                v.append({"slot": slot, "rule": "VERDICT_INCOMPLETE", "detail": f"no claim covers: {sent[:100]!r}"})
1934 | +    return {"ok": not v, "claims": obj["claims"], "violations": v, "classes": classes}
1935 | +
1936 | +
1937 | +def check(router, segments, lines, writer_vendor, seed=7, manifest=None, current_levels=None, writer_family=None):
1938 | +    """Both layers. -> {"ok", "deterministic", "verdict", "violations", "backend", "measured", "replayed"}; the verdict
1939 | +    never runs on the vendors / families of the text it judges; a verdict that cannot be had or read is a failure
1940 | +    (law L-m) and leaves the layer NOT measured."""
1941 | +    import providers as P
1942 | +    det = check_deterministic(segments, lines, manifest, current_levels)
1943 | +    out = {"deterministic": det, "verdict": None, "backend": None, "measured": False, "replayed": False}
1944 | +    r = None
1945 | +    try:
1946 | +        r = router.call("fidelity_verdict", verdict_prompt(segments, lines, manifest), 2500, seed,
1947 | +                        avoid_vendor=writer_vendor, avoid_family=writer_family)
1948 | +        out["backend"], out["replayed"] = r.backend, bool(getattr(r, "replayed", False))
1949 | +        out["verdict"] = check_verdict(r.text, segments, lines, manifest)
1950 | +        out["measured"] = True
1951 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
1952 | +        if r is not None and isinstance(e, (ValueError, TypeError)) and hasattr(router, "reject"):
1953 | +            router.reject(r, str(e))
1954 | +        out["verdict"] = {"ok": False, "claims": [], "violations": [{"slot": "-", "rule": "VERDICT_UNAVAILABLE",
1955 | +                                                                      "detail": f"{type(e).__name__}: {str(e)[:200]}"}]}
1956 | +    out["violations"] = det["violations"] + out["verdict"]["violations"]
1957 | +    out["ok"] = det["ok"] and out["verdict"]["ok"]
1958 | +    return out
1959 | 
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
