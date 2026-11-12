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

## THE CODE NOW: chunk A1_core of the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_p2/A1_core/STEP.diff (2004 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | new file mode 100644
   3 | index 00000000..1709764a
   4 | --- /dev/null
   5 | +++ b/pipeline/model_providers.json
   6 | @@ -0,0 +1,223 @@
   7 | +{
   8 | + "schema": "pp.providers/1",
   9 | + "law": "L-x NO SINGLE MODEL, ULTRON FIRST (orchestrator 2026-11-12 02:45): every role names >= 2 interchangeable back-ends; the local model on Ultron is first wherever it meets the quality bar; a frontier model or Heimdall is used only where a measured blind A/B (tests/providers/ab_roles.py) shows local is not good enough, and the comparison is re-run so roles migrate to local. Verdict roles never run on the writer's vendor (law L-s; Router.call avoid_vendor). No role's code names a vendor or a model: only this file does. Each back-end names its model family: a verdict avoids the vendors AND families of the text it judges (Router.call avoid_vendor / avoid_family). Prices are upper bounds (USD per 1M tokens; per minute of audio for transcription); each paid call reserves its upper bound before it runs.",
  10 | + "decided": "2026-11-12 02:44 ET by pipeline_pp_selectid: an INITIAL order, not yet measured. Mining, story selection and the check verdict put local first (law L-w 1: local gemma mines and scores by id). Angle and writing put a frontier model first (law L-w 1 and PBX 02:35: frontier spend approved for writing and checking) until the A/B shows local meets the bar. Verdicts run on a vendor other than the writer's.",
  11 | + "backends": {
  12 | +  "local:gemma3:27b": {
  13 | +   "vendor": "local",
  14 | +   "model": "gemma3:27b",
  15 | +   "price_usd_per_1m": [
  16 | +    0,
  17 | +    0
  18 | +   ],
  19 | +   "family": "gemma"
  20 | +  },
  21 | +  "openai:gpt-6.1-sol": {
  22 | +   "vendor": "openai",
  23 | +   "model": "gpt-6.1-sol",
  24 | +   "price_usd_per_1m": [
  25 | +    15,
  26 | +    120
  27 | +   ],
  28 | +   "reasoning_effort": "medium",
  29 | +   "min_out": 4000,
  30 | +   "family": "gpt"
  31 | +  },
  32 | +  "anthropic:claude-fable-5-2": {
  33 | +   "vendor": "anthropic",
  34 | +   "model": "claude-fable-5-2",
  35 | +   "price_usd_per_1m": [
  36 | +    8,
  37 | +    40
  38 | +   ],
  39 | +   "effort": "medium",
  40 | +   "min_out": 16000,
  41 | +   "family": "claude"
  42 | +  },
  43 | +  "anthropic:claude-opus-5-5": {
  44 | +   "vendor": "anthropic",
  45 | +   "model": "claude-opus-5-5",
  46 | +   "price_usd_per_1m": [
  47 | +    4,
  48 | +    20
  49 | +   ],
  50 | +   "effort": "medium",
  51 | +   "min_out": 16000,
  52 | +   "family": "claude"
  53 | +  },
  54 | +  "xai:grok-4.20-0309-reasoning": {
  55 | +   "vendor": "xai",
  56 | +   "model": "grok-4.20-0309-reasoning",
  57 | +   "price_usd_per_1m": [
  58 | +    5,
  59 | +    25
  60 | +   ],
  61 | +   "temperature": 0,
  62 | +   "key_name": "XAI_API_KEY_MEDLEY",
  63 | +   "family": "grok"
  64 | +  },
  65 | +  "heimdall:qwen/qwen3.8-27b": {
  66 | +   "vendor": "heimdall",
  67 | +   "model": "qwen/qwen3.8-27b",
  68 | +   "price_usd_per_1m": [
  69 | +    3,
  70 | +    15
  71 | +   ],
  72 | +   "temperature": 0,
  73 | +   "min_out": 16000,
  74 | +   "family": "qwen",
  75 | +   "base_url": "https://api-staging.heimdallm.com/api/v1"
  76 | +  },
  77 | +  "heimdall:deepseek/deepseek-v4.1-flash": {
  78 | +   "vendor": "heimdall",
  79 | +   "model": "deepseek/deepseek-v4.1-flash",
  80 | +   "price_usd_per_1m": [
  81 | +    3,
  82 | +    15
  83 | +   ],
  84 | +   "temperature": 0,
  85 | +   "min_out": 16000,
  86 | +   "family": "deepseek",
  87 | +   "base_url": "https://api-staging.heimdallm.com/api/v1"
  88 | +  },
  89 | +  "heimdall:google/gemma-4-31b-it": {
  90 | +   "vendor": "heimdall",
  91 | +   "model": "google/gemma-4-31b-it",
  92 | +   "price_usd_per_1m": [
  93 | +    3,
  94 | +    15
  95 | +   ],
  96 | +   "temperature": 0,
  97 | +   "min_out": 16000,
  98 | +   "family": "gemma",
  99 | +   "base_url": "https://api-staging.heimdallm.com/api/v1"
 100 | +  },
 101 | +  "xai_search:grok-4.7": {
 102 | +   "vendor": "xai_search",
 103 | +   "model": "grok-4.7",
 104 | +   "price_usd_per_1m": [
 105 | +    5,
 106 | +    25
 107 | +   ],
 108 | +   "key_name": "XAI_API_KEY_MEDLEY",
 109 | +   "tools": [
 110 | +    "x_search",
 111 | +    "web_search"
 112 | +   ],
 113 | +   "family": "grok"
 114 | +  },
 115 | +  "openai_stt:gpt-4o-transcribe-diarize": {
 116 | +   "vendor": "openai_stt",
 117 | +   "model": "gpt-4o-transcribe-diarize",
 118 | +   "family": "gpt",
 119 | +   "diarize": true,
 120 | +   "price_usd_per_min": 0.012,
 121 | +   "timeout_s": 300
 122 | +  },
 123 | +  "elevenlabs_stt:scribe_v1": {
 124 | +   "vendor": "elevenlabs_stt",
 125 | +   "model": "scribe_v1",
 126 | +   "family": "scribe",
 127 | +   "price_usd_per_min": 0.012,
 128 | +   "timeout_s": 300
 129 | +  }
 130 | + },
 131 | + "roles": {
 132 | +  "mine": {
 133 | +   "chain": [
 134 | +    "local:gemma3:27b",
 135 | +    "openai:gpt-6.1-sol",
 136 | +    "anthropic:claude-fable-5-2",
 137 | +    "heimdall:qwen/qwen3.8-27b"
 138 | +   ],
 139 | +   "what": "moments.py: whole-sentence ranges by id with engagement scores, risk flags, topics",
 140 | +   "measured": "blind A/B 2026-11-12 03:40 ET on fresh_20261112_050611 (tests/providers/ab/mine_fresh_20261112_050611.json, judge claude-opus-5-5): gpt-6.1-sol better than heimdall qwen3.8-27b; qwen 2067 s vs 300.5 s, 1 of 6 calls rejected by the strict contract. Local gemma3:27b: the integrator's leg (GPU0 lease)."
 141 | +  },
 142 | +  "angle_write": {
 143 | +   "chain": [
 144 | +    "openai:gpt-6.1-sol",
 145 | +    "anthropic:claude-fable-5-2",
 146 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 147 | +    "local:gemma3:27b"
 148 | +   ],
 149 | +   "what": "package.py: the angle, the order, the PBX MAX VO intro / bridges, ONE title, ONE caption"
 150 | +  },
 151 | +  "fidelity_verdict": {
 152 | +   "chain": [
 153 | +    "xai:grok-4.20-0309-reasoning",
 154 | +    "anthropic:claude-opus-5-5",
 155 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 156 | +    "local:gemma3:27b"
 157 | +   ],
 158 | +   "what": "vo_fidelity.py: the blind claim-by-claim verdict on VO, title and caption; never the writer's vendor"
 159 | +  },
 160 | +  "context_verdict": {
 161 | +   "chain": [
 162 | +    "xai:grok-4.20-0309-reasoning",
 163 | +    "anthropic:claude-opus-5-5",
 164 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 165 | +    "local:gemma3:27b"
 166 | +   ],
 167 | +   "what": "context_integrity.py step A (source context only) and step C (entailment); never the writer's vendor"
 168 | +  },
 169 | +  "viewer_takeaway": {
 170 | +   "chain": [
 171 | +    "anthropic:claude-opus-5-5",
 172 | +    "xai:grok-4.20-0309-reasoning",
 173 | +    "heimdall:qwen/qwen3.8-27b",
 174 | +    "local:gemma3:27b"
 175 | +   ],
 176 | +   "what": "context_integrity.py step B (the finished package only); never the writer's vendor"
 177 | +  },
 178 | +  "trend_brief": {
 179 | +   "chain": [
 180 | +    "xai_search:grok-4.7"
 181 | +   ],
 182 | +   "fallback": "trend_brief.local_baseline (topic frequency across partner channels, last 24 h): free, always available",
 183 | +   "what": "trend_brief.py: one live-search call per cycle; SHADOW weight 0 (law L-w 4)"
 184 | +  },
 185 | +  "story": {
 186 | +   "chain": [
 187 | +    "local:gemma3:27b",
 188 | +    "openai:gpt-6.1-sol",
 189 | +    "anthropic:claude-fable-5-2",
 190 | +    "heimdall:qwen/qwen3.8-27b"
 191 | +   ],
 192 | +   "what": "select_by_id story + line-up calls (story-first type; REQUESTS R6 item 7)"
 193 | +  },
 194 | +  "check": {
 195 | +   "chain": [
 196 | +    "local:gemma3:27b",
 197 | +    "xai:grok-4.20-0309-reasoning",
 198 | +    "anthropic:claude-opus-5-5",
 199 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 200 | +   ],
 201 | +   "what": "select_by_id.ModelChecks; called with avoid_model = the story's model"
 202 | +  },
 203 | +  "exclusion_verdict": {
 204 | +   "chain": [
 205 | +    "local:gemma3:27b",
 206 | +    "xai:grok-4.20-0309-reasoning",
 207 | +    "anthropic:claude-opus-5-5",
 208 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 209 | +   ],
 210 | +   "what": "moments.exclusion_verdict: the hard exclusions of law L-u on one moment in its context"
 211 | +  },
 212 | +  "coherence_verdict": {
 213 | +   "chain": [
 214 | +    "anthropic:claude-opus-5-5",
 215 | +    "xai:grok-4.20-0309-reasoning",
 216 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 217 | +    "local:gemma3:27b"
 218 | +   ],
 219 | +   "what": "package.coherence: the blind QUALITY verdict (through-line, ratings); never the writer's vendor"
 220 | +  },
 221 | +  "transcribe": {
 222 | +   "chain": [
 223 | +    "openai_stt:gpt-4o-transcribe-diarize",
 224 | +    "elevenlabs_stt:scribe_v1"
 225 | +   ],
 226 | +   "what": "transcript_truth.py: law L-v 2's second, independent recognition pass with speaker turns on the selected segment's source audio (CPU fetch; no GPU, no Whisper)"
 227 | +  }
 228 | + }
 229 | +}
 230 | diff --git a/pipeline/moments_gate_adapter.py b/pipeline/moments_gate_adapter.py
 231 | new file mode 100644
 232 | index 00000000..75e32d37
 233 | --- /dev/null
 234 | +++ b/pipeline/moments_gate_adapter.py
 235 | @@ -0,0 +1,121 @@
 236 | +#!/usr/bin/env python3
 237 | +"""The pp-tests exam adapter (pipeline_pp_tests, branch pp-tests: tests/adversarial/test_moments_gates.py; corpora
 238 | +format v1, pp.ci_case/1, pp.vo_case/1, pp.excl_case/1). The harness strips "expected" and "provenance" and calls:
 239 | +
 240 | +  context_integrity(case) -> {"verdict": "pass" | "fail" | "uncertain", "why"}     law L-s
 241 | +  vo_fidelity(case)       -> {"verdict": "pass" | "fail" | "uncertain", "why"}     law L-o 11 / L-t
 242 | +  exclusion(case)         -> {"verdict": "keep" | "exclude" | "uncertain", "why"}  law L-u
 243 | +
 244 | +These are the SAME gates the packager runs (context_integrity.check_contexts, vo_fidelity.check,
 245 | +moments.exclusion_verdict) behind the same provider config (law L-x). The harness forbids network connections, so the
 246 | +gates' model replies are recorded on a run that may call out (PP_GATES_REPLAY unset; this session's
 247 | +tests/package/run_exam_record.py, which strips "expected" exactly as the harness does) and served offline under the
 248 | +harness (PP_GATES_REPLAY=1). A gate that could not MEASURE (an exchange never recorded, every back-end unavailable, an
 249 | +unreadable verdict) RAISES GateNotMeasured, which the harness counts as an ERROR (audit p2 M5): it is never a pass and
 250 | +never a free rejection either (law L-m). A deterministic failure is a measured "fail".
 251 | +"""
 252 | +import os
 253 | +
 254 | +import context_integrity as CI
 255 | +import moments as M
 256 | +import providers as P
 257 | +import vo_fidelity as VF
 258 | +
 259 | +HERE = os.path.dirname(os.path.abspath(__file__))
 260 | +REPO = os.path.dirname(HERE)
 261 | +RECORD = os.environ.get("PP_GATES_RECORD_DIR") or os.path.join(REPO, "tests", "package", "fixtures", "gate_replies")
 262 | +SPEND = os.environ.get("PP_GATES_SPEND") or os.path.join(REPO, "tests", "moments", "proof", "SPEND.json")
 263 | +ENV = P.ENV_PATH
 264 | +THREAD_SAFE = True                     # the router's ledger and recordings are safe across the harness's threads
 265 | +_router = None
 266 | +
 267 | +
 268 | +class GateNotMeasured(Exception):
 269 | +    """The gate could not measure this case (the harness's ERROR)."""
 270 | +
 271 | +
 272 | +def router():
 273 | +    global _router
 274 | +    if _router is None:
 275 | +        _router = P.Router(env_path=ENV, record_dir=RECORD, replay=os.environ.get("PP_GATES_REPLAY") == "1",
 276 | +                           spend_path=SPEND, limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")))
 277 | +    return _router
 278 | +
 279 | +
 280 | +def _join(sentences):
 281 | +    return " ".join(s["text"] for s in sentences or [])
 282 | +
 283 | +
 284 | +def context_integrity(case):
 285 | +    w = case["window"]
 286 | +    n0, n1 = w["selected"]
 287 | +    parts, prev_turn = [], None
 288 | +    for s in w["sentences"]:                     # the caption's own speaker-turn markers, when it has them
 289 | +        t = s["text"]
 290 | +        if s.get("turn") is not None and prev_turn is not None and s["turn"] != prev_turn:
 291 | +            t = "[another speaker] " + t
 292 | +        if s.get("speaker"):
 293 | +            t = f"{s['speaker']}: " + t
 294 | +        prev_turn = s.get("turn")
 295 | +        parts.append((t, n0 <= s["n"] <= n1))
 296 | +    pkg = case["package"]
 297 | +    segs = [{"label": s["label"], "video_id": s["video_id"], "channel": s["channel"], "text": s["text"],
 298 | +             "role": s.get("role")} for s in pkg["segments"]]
 299 | +    moment = [s["label"] for s in pkg["segments"] if s.get("role") == "moment"]
 300 | +    if len(moment) != 1:
 301 | +        return {"verdict": "fail", "why": f"the case names {len(moment)} moment segments (expected 1)"}
 302 | +    src = case.get("source") or {}
 303 | +    contexts = {moment[0]: {"text": CI.mark(parts), "title": src.get("title") or "", "channel": src.get("channel") or "",
 304 | +                            "published": str(src.get("published_at") or "unknown")[:16],
 305 | +                            "show_date": pkg.get("date") or "unknown"}}
 306 | +    bridges = list(pkg["vo"].get("bridges") or [])
 307 | +    package = {"segments": segs, "vo": {"intro": pkg["vo"].get("intro") or "", "bridges": bridges,
 308 | +                                        "bridges_after_clip": list(pkg["vo"].get("bridges_after_clip") or
 309 | +                                                                   range(1, len(bridges) + 1)),
 310 | +                                        "signoff": pkg["vo"].get("signoff") or ""},
 311 | +               "title": pkg.get("title") or "", "caption": pkg.get("caption") or ""}
 312 | +    try:
 313 | +        res = CI.check_contexts(router(), package, contexts, writer_vendor=None)
 314 | +    except P.ReplayMiss as e:
 315 | +        raise GateNotMeasured(f"no recorded verdict (replay): {str(e)[:160]}") from None
 316 | +    if not res.get("measured"):
 317 | +        raise GateNotMeasured("; ".join(v["detail"] for v in res["violations"])[:300])
 318 | +    if res["ok"]:
 319 | +        return {"verdict": "pass", "why": "own sincere assertion; referents and conditions inside; entailed; no false relation"}
 320 | +    return {"verdict": "fail", "why": "; ".join(f"{v['segment']}: {v['rule']} {v['detail']}" for v in res["violations"])[:600]}
 321 | +
 322 | +
 323 | +def vo_fidelity(case):
 324 | +    man = case.get("manifest") or {}
 325 | +    segments = {}
 326 | +    for s in case["segments"]:                  # a speaker is named only when the case states it (law L-v 1)
 327 | +        segments[s["label"]] = {"show": s["channel"], "speaker": s.get("speaker") or None,
 328 | +                                "names": [s["speaker"]] if s.get("speaker") else [], "video_id": s["video_id"],
 329 | +                                "text": _join(s["sentences"])}
 330 | +    lines = [{"slot": f"{ln['slot']}_{i}", "text": ln["text"], "cites": list(ln.get("cites") or [])}
 331 | +             for i, ln in enumerate(case["lines"])]
 332 | +    levels = case.get("current_levels") if isinstance(case.get("current_levels"), list) else None
 333 | +    try:
 334 | +        res = VF.check(router(), segments, lines, writer_vendor=None, manifest=man, current_levels=levels)
 335 | +    except P.ReplayMiss as e:
 336 | +        raise GateNotMeasured(f"no recorded verdict (replay): {str(e)[:160]}") from None
 337 | +    if not res["deterministic"]["ok"]:
 338 | +        return {"verdict": "fail", "why": "; ".join(f"{v['slot']}: {v['rule']} {v['detail']}"
 339 | +                                                     for v in res["deterministic"]["violations"])[:600]}
 340 | +    if not res.get("measured"):
 341 | +        raise GateNotMeasured("; ".join(v["detail"] for v in res["verdict"]["violations"])[:300])
 342 | +    if res["ok"]:
 343 | +        return {"verdict": "pass", "why": "every claim bound to its speaker's words; verdict yes with verbatim support"}
 344 | +    return {"verdict": "fail", "why": "; ".join(f"{v['slot']}: {v['rule']} {v['detail']}" for v in res["violations"])[:600]}
 345 | +
 346 | +
 347 | +def exclusion(case):
 348 | +    try:
 349 | +        res = M.exclusion_verdict(router(), _join(case["moment"]["sentences"]),
 350 | +                                  _join((case.get("context") or {}).get("before")),
 351 | +                                  _join((case.get("context") or {}).get("after")))
 352 | +    except P.ReplayMiss as e:
 353 | +        raise GateNotMeasured(f"no recorded verdict (replay): {str(e)[:160]}") from None
 354 | +    if not res.get("measured"):
 355 | +        raise GateNotMeasured(res["why"])
 356 | +    return {"verdict": res["verdict"], "why": res["why"]}
 357 | diff --git a/pipeline/package.py b/pipeline/package.py
 358 | new file mode 100644
 359 | index 00000000..5be27ff6
 360 | --- /dev/null
 361 | +++ b/pipeline/package.py
 362 | @@ -0,0 +1,780 @@
 363 | +#!/usr/bin/env python3
 364 | +"""pipeline/package.py — STEP 2 PACKAGE + STEP 3 OPTIMISE (law L-q, '01:55'; laws L-s..L-x; orchestrator 03:40, 05:25,
 365 | +05:30): ANGLE FIRST. The moments need not share a development: under moments-first there is no same-event test.
 366 | +
 367 | +usable()      moments a package may use: on screen eligible (word timing, law L-e), no hard-exclusion risk (L-u), not
 368 | +              overlapping a moment delivered in the previous 24 h (novelty by video and time, L-p), channel not opted
 369 | +              out, <= 20 s (L-u), a time-sensitive moment only from a source <= TIME_SENSITIVE_H old (L-v 3), no
 370 | +              measured speaker change (L-v 1)
 371 | +prescreen()   step A of law L-s on each usable moment's own context, ONCE per moment (package-independent), stored on
 372 | +              the moment (`store`: a JSON ledger keyed by moment and the step-A prompt); never recomputed
 373 | +ANGLES        role angle_write: up to MAX_ANGLES one-sentence angles, each backed by 3-8 cleared moments from >= 3
 374 | +              channels (one clip per channel, L-u)
 375 | +lineup_for()  code: hook + 2-3 clips for one angle, every segment from a different channel, at most one price prediction
 376 | +              (L-u), a clip under SHORT_CLIP_S only as the punchline, and the length the runtime (60-70 s, L-o) AND the
 377 | +              factory's EDL rule R4 (VO <= 25 % of runtime, one bridge per channel transition) both allow
 378 | +write_v3()    role angle_write: the PBX MAX VO in the renderer's order (hook -> intro -> clip 1 -> bridge -> ...), in
 379 | +              one of two styles (05:25 item 3): "host" (tease / hedge-matched hand-off of a VERIFIED speaker / the
 380 | +              host's own takeaway after a clip) or "quote" (show + topic, at most four exact words quoted); NEVER a
 381 | +              restatement of a clip's claim; word budgets from R4 and the runtime
 382 | +GATES (hard, every one, recorded in a sealed inventory, package_pin.REQUIRED_GATES):
 383 | +              cheap first (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4;
 384 | +              then concurrently: the classifying fidelity verdict (A / B / C / D, 05:25 items 1-2) and context
 385 | +              integrity B0 / B / C (L-s; step A precomputed); exclusion (L-u) and the second recognition pass (L-v 2)
 386 | +              start in the background as soon as a line-up is fixed; then COHERENCE (blind, >= 4).
 387 | +              Every verdict avoids the vendors and model families of every reply whose text it judges (L-x).
 388 | +              A rejected line goes back to the writer with the exact violations; a clip that fails exclusion or L-v 2
 389 | +              is dropped and the angle re-lined; at most WRITES writes per angle and MAX_ANGLES angles; the first
 390 | +              package with coherence >= COHERENCE_MIN wins (05:30).
 391 | +OUTPUT pp.package/1: segments (moment ids, verbatim text, times), VO, title, caption, the gate inventory, the model per
 392 | +              artefact, seconds and dollars.
 393 | +"""
 394 | +import hashlib
 395 | +import itertools
 396 | +import json
 397 | +import os
 398 | +import re
 399 | +import time
 400 | +from concurrent.futures import ThreadPoolExecutor
 401 | +
 402 | +import context_integrity as CI
 403 | +import eligibility as E
 404 | +import vo_fidelity as VF
 405 | +
 406 | +SEG_MAX_S = 20.0                   # L-u: at most 20 s per source video
 407 | +RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the one hard length rule
 408 | +WPS = 2.6                          # PBX MAX VO words per second: an ASSUMPTION until the render measures it
 409 | +SIGNOFF_WORDS = 18                 # the preview's sign-off ("Clips today from A, B, and C. Go follow them ...")
 410 | +FIXED_S = round(E.TAIL_S - SIGNOFF_WORDS / WPS, 2)   # credits card + outro + transitions without VO (~7.4 s)
 411 | +VO_S = (6.0, 22.0)                 # the VO's seconds (intro + bridges), the slack that lands the runtime
 412 | +R4_WPS, R4_PREROLL_S, R4_SHARE = 2.5, 1.0, 0.25      # edl_rules.rule_r4's own estimate (the factory's rule)
 413 | +TIME_SENSITIVE_H = 24.0            # L-v 3: 'today' / 'just' / a price level only from a source this fresh
 414 | +PRESCREEN_N = 24                   # moments whose own context is screened (step A) before any writing
 415 | +PRESCREEN_BATCH = 8                # excerpts per step-A call
 416 | +PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
 417 | +SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
 418 | +MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
 419 | +WRITES = 2
 420 | +COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >= 4 and a through-line, else next angle
 421 | +BUDGET_S, BUDGET_USD = 360.0, 1.50  # orchestrator 05:25 item 5: per package
 422 | +VO_DEPENDENT = ("NOT_ENTAILED", "POLARITY", "STRONGER", "FALSE_RELATION")   # context failures the VO's framing causes
 423 | +VO_FIX = {"NOT_ENTAILED": "the viewer would take this clip to assert more than its speaker said in context: do not "
 424 | +                          "frame or restate it",
 425 | +          "POLARITY": "the framing flips what the speaker meant: do not characterise the speaker's view",
 426 | +          "STRONGER": "the framing makes the speaker sound more certain than in context: do not restate or reinforce "
 427 | +                      "the clip; keep any attribution's verb as hedged as the clip",
 428 | +          "FALSE_RELATION": "the voice-over makes these speakers look like they respond to or agree WITH each other: "
 429 | +                            "never relate one speaker to another"}
 430 | +
 431 | +
 432 | +def usable(moments, ctx, delivered=(), optout=frozenset()):
 433 | +    """delivered: moment ids, or {"video_id", "start", "end"} of moments delivered in the previous 24 h; a moment that
 434 | +    overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated)."""
 435 | +    ids = {d for d in delivered if isinstance(d, str)}
 436 | +    spans = [d for d in delivered if isinstance(d, dict)]
 437 | +    out, why = [], {}
 438 | +    for m in moments:
 439 | +        mid = m["moment_id"]
 440 | +        overlap = any(d.get("video_id") == m["video_id"] and float(d["start"]) < float(m["end"]) and
 441 | +                      float(m["start"]) < float(d["end"]) for d in spans)
 442 | +        if not m.get("on_screen_ok"):
 443 | +            why[mid] = "not eligible on screen: " + "; ".join(
 444 | +                f"{r}: {', '.join(v['reasons'])}" for r, v in (m.get("eligibility") or {}).items() if not v["ok"])
 445 | +        elif m.get("excluded"):
 446 | +            why[mid] = f"hard exclusion (L-u): {m['excluded']}"
 447 | +        elif mid in ids or overlap:
 448 | +            why[mid] = "delivered in the previous 24 h (or overlaps a delivered moment)"
 449 | +        elif m["channel_id"] in optout:
 450 | +            why[mid] = "channel opted out"
 451 | +        elif m.get("duration_s") is None or m["duration_s"] > SEG_MAX_S:
 452 | +            why[mid] = f"{m.get('duration_s')} s: over the {SEG_MAX_S} s per source video (L-u) or unmeasured"
 453 | +        elif "time_sensitive" in m.get("risk", []) and (E.age_hours(m["published_at"], ctx.now) or 1e9) > TIME_SENSITIVE_H:
 454 | +            why[mid] = f"time-sensitive words from a source older than {TIME_SENSITIVE_H} h (L-v 3)"
 455 | +        elif (m.get("speaker") or {}).get("turn_change_inside") is True:
 456 | +            why[mid] = "a speaker change inside (L-v 1)"
 457 | +        else:
 458 | +            out.append(m)                              # an unmeasured speaker is a CANDIDATE; L-v 2 decides (M11)
 459 | +    return out, why
 460 | +
 461 | +
 462 | +def runtime(segs, vo_s):
 463 | +    """segments' word spans + every spoken VO second (intro, bridges AND the sign-off) + FIXED_S (audit p2 M4)."""
 464 | +    return round(sum(m["duration_s"] for m in segs) + vo_s + FIXED_S, 2)
 465 | +
 466 | +
 467 | +R4_MOMENTS_SHARE = 0.40            # orchestrator 06:00 ruling 4: moments-first VO up to 40 % of the runtime; a VO line
 468 | +                                   # after the hook, after every clip and after the last clip; 60-70 s stays hard
 469 | +
 470 | +
 471 | +def r4_max_vo_words(content_s, n_vo):
 472 | +    """The most VO words (intro + bridges) the moments-first R4 allows: edl_rules' own estimate (words / 2.5 + 1 s per
 473 | +    VO line) <= 40 % of the runtime estimate (content + VO and the standard sign-off at WPS + FIXED_S)."""
 474 | +    num = R4_MOMENTS_SHARE * (content_s + SIGNOFF_WORDS / WPS + FIXED_S) - R4_PREROLL_S * n_vo
 475 | +    return max(0, int(num / (1 / R4_WPS - R4_MOMENTS_SHARE / WPS)))
 476 | +
 477 | +
 478 | +def min_vo_words(content_s):
 479 | +    """The fewest VO words (intro + bridges) that land 60 s: content + VO + the standard sign-off + FIXED_S >= 60."""
 480 | +    return max(0, int(WPS * (RUNTIME_S[0] - content_s - SIGNOFF_WORDS / WPS - FIXED_S) + 0.999))
 481 | +
 482 | +
 483 | +def content_range(n_clips=2):
 484 | +    """Seconds the segments may fill so that some VO lands the runtime in 60-70 s AND fits R4 (one VO line for the
 485 | +    intro + one bridge per clip but the last)."""
 486 | +    n_vo = 1 + (n_clips - 1)
 487 | +    lo = next(c / 10 for c in range(200, 700) if min_vo_words(c / 10) <= r4_max_vo_words(c / 10, n_vo))
 488 | +    return lo, RUNTIME_S[1] - FIXED_S - SIGNOFF_WORDS / WPS - VO_S[0]
 489 | +
 490 | +
 491 | +def r4(pk):
 492 | +    """R4 for a moments-first package, as the orchestrator ordered it at 06:00 (ruling 4; the integrator brings
 493 | +    edl_rules.rule_r4 to it): VO (intro + bridges, edl_rules' estimate 2.5 w/s + 1 s per line) <= 40 % of the runtime
 494 | +    estimate; the word caps of config.py; at most one VO line after each clip (the last clip included).
 495 | +    -> (ok, reason). The share over clips + VO (today's edl_rules denominator) is reported beside it."""
 496 | +    from config import BRIDGE_WORD_CAP, INTRO_WORD_CAP
 497 | +    n_clips = len(pk["segments"]) - 1
 498 | +    words = [len((pk["vo"]["intro"] or "").split())] + [len(b.split()) for b in pk["vo"]["bridges"]]
 499 | +    n_lines = (1 if pk["vo"]["intro"] else 0) + len(pk["vo"]["bridges"])
 500 | +    vo_s = sum(words) / R4_WPS + R4_PREROLL_S * n_lines
 501 | +    share = vo_s / pk["runtime_s_estimate"]
 502 | +    share_old = vo_s / (sum(sg["duration_s"] for sg in pk["segments"]) + vo_s)
 503 | +    after = list(pk["vo"]["bridges_after_clip"])
 504 | +    fails = []
 505 | +    if words[0] > INTRO_WORD_CAP:
 506 | +        fails.append(f"intro {words[0]} words (max {INTRO_WORD_CAP})")
 507 | +    fails += [f"bridge {i + 1} {w} words (max {BRIDGE_WORD_CAP})" for i, w in enumerate(words[1:]) if w > BRIDGE_WORD_CAP]
 508 | +    if len(set(after)) != len(after) or any(type(a) is not int or not 1 <= a <= n_clips for a in after):
 509 | +        fails.append(f"bridges after clips {after}: one per clip, 1..{n_clips}")
 510 | +    if share > R4_MOMENTS_SHARE:
 511 | +        fails.append(f"VO={share:.1%} of the runtime (max {R4_MOMENTS_SHARE:.0%})")
 512 | +    note = f"VO {vo_s:.1f} s = {share:.1%} of the {pk['runtime_s_estimate']} s runtime ({share_old:.1%} of clips + VO)"
 513 | +    return (not fails), ("R4 (moments-first, 06:00) FAIL: " + "; ".join(fails) if fails else
 514 | +                         "R4 (moments-first, 06:00) PASS") + f" | {note}"
 515 | +
 516 | +
 517 | +def budgets(content_s, n_bridges=1):
 518 | +    """Word budgets (intro, each bridge, (min, max) total) that land 60-70 s and fit R4; 40 % to the intro."""
 519 | +    hi = min(r4_max_vo_words(content_s, 1 + n_bridges), int(VO_S[1] * WPS))
 520 | +    lo = min(min_vo_words(content_s), hi)
 521 | +    return max(6, int(hi * 0.4)), max(4, int(hi * 0.6 / max(1, n_bridges))), (lo, hi)
 522 | +
 523 | +
 524 | +def _name(m, ctx):
 525 | +    return (ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]
 526 | +
 527 | +
 528 | +def signoff(segs, ctx):
 529 | +    """L-a: the spoken sign-off names exactly the credit set, hook first (code, never the model)."""
 530 | +    names = list(dict.fromkeys(_name(m, ctx) for m in segs))
 531 | +    who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + f", and {names[-1]}"
 532 | +    return f"Clips today from {who}. Go follow them for more. Links are below."
 533 | +
 534 | +
 535 | +def plain_vo(segs, ctx):
 536 | +    """L-w 2: the plain factual fallback VO ("Next, <show> on <topic>."): it claims nothing beyond who speaks. Ranked
 537 | +    last (orchestrator 03:40); the title names whole channels only (U11)."""
 538 | +    intro = {"text": f"Here's {_name(segs[0], ctx)} on Bitcoin.", "cites": []}
 539 | +    bridges = [{"text": f"Next, {_name(m, ctx)} on Bitcoin.", "cites": []} for m in segs[2:]]
 540 | +    chans = list(dict.fromkeys(_name(m, ctx) for m in segs))
 541 | +    title = "Bitcoin: " + ", ".join(chans[:-1]) + f" and {chans[-1]}"
 542 | +    while len(title) > 70 and len(chans) > 1:
 543 | +        chans = chans[:-1]
 544 | +        title = "Bitcoin: " + ", ".join(chans) + " and others"
 545 | +    caption = f"Clips from {', '.join(dict.fromkeys(_name(m, ctx) for m in segs))}. Links to every source below."
 546 | +    return intro, bridges, {"text": title[:70], "cites": []}, {"text": caption, "cites": []}
 547 | +
 548 | +
 549 | +def assemble(order, by_id, fields, ctx, vo_kind):
 550 | +    segs = [by_id[i] for i in order]
 551 | +    lines = [dict(fields["intro"], slot="intro")] + \
 552 | +        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
 553 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 554 | +    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"].startswith(("intro", "bridge")))
 555 | +    pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
 556 | +          "vo_kind": vo_kind, "style": fields.get("style"),
 557 | +          "segments": [{"label": "hook" if i == 0 else f"clip_{i:02d}", "moment_id": m["moment_id"],
 558 | +                        "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": _name(m, ctx),
 559 | +                        "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
 560 | +                        "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
 561 | +                        "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
 562 | +                        "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
 563 | +                       for i, m in enumerate(segs)],
 564 | +          "vo": {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
 565 | +                 "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1)),     # the renderer's after_clip
 566 | +                 "signoff": signoff(segs, ctx)},
 567 | +          "title": fields["title"]["text"], "caption": fields["caption"]["text"],
 568 | +          "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
 569 | +          "lines": lines}
 570 | +    so_words = len(pk["vo"]["signoff"].split())
 571 | +    pk["runtime_s_estimate"] = runtime(segs, (vo_words + so_words) / WPS)
 572 | +    pk["runtime_note"] = (f"segments {sum(m['duration_s'] for m in segs):.2f} s (word timing) + VO {vo_words} words + "
 573 | +                          f"sign-off {so_words} words at {WPS} w/s (assumed) + fixed {FIXED_S} s (credits card, outro, "
 574 | +                          f"transitions); the render measures the final")
 575 | +    return pk
 576 | +
 577 | +
 578 | +# ── step A once per moment (orchestrator 05:25 item 5) ──
 579 | +
 580 | +STEP_A_VERSION = hashlib.sha256(CI.STEP_A.encode()).hexdigest()[:12]
 581 | +
 582 | +
 583 | +def _load_store(store):
 584 | +    if not store or not os.path.exists(store):
 585 | +        return {}
 586 | +    with open(store) as f:
 587 | +        return json.load(f)
 588 | +
 589 | +
 590 | +def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
 591 | +              store=None, log=print):
 592 | +    """Step A (context only, package-independent by law L-s) on the best n usable moments, distinct channels first:
 593 | +    ({moment_id: A item}, {moment_id: [failing rules]}, {vendor}, {family}). Each moment is screened ONCE: a stored item
 594 | +    (same moment, same step-A prompt, a back-end off the writers' vendor and family) is reused, never recomputed.
 595 | +    writer_vendor / writer_family: of the writers, so step A never runs on them."""
 596 | +    import providers as P
 597 | +    seen, order = set(), []
 598 | +    ranked = sorted(ms, key=lambda m: (-m["rank_score"], m["moment_id"]))
 599 | +    for m in ranked:
 600 | +        if m["channel_id"] not in seen:
 601 | +            order.append(m)
 602 | +            seen.add(m["channel_id"])
 603 | +    order = (order + [m for m in ranked if m not in order])[:n]
 604 | +    db = _load_store(store)
 605 | +    wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
 606 | +    a_by, fails, vendors, families, todo = {}, {}, set(), set(), []
 607 | +    for m in order:
 608 | +        rec = db.get(f"{m['moment_id']}:{STEP_A_VERSION}")
 609 | +        b = router.backends.get((rec or {}).get("backend"))
 610 | +        if rec and b is not None and b.vendor not in wv and b.family not in wf:
 611 | +            a_by[m["moment_id"]] = rec
 612 | +            fails[m["moment_id"]] = CI.a_failures(rec)
 613 | +            vendors.add(b.vendor)
 614 | +            families.add(b.family)
 615 | +        else:
 616 | +            todo.append(m)
 617 | +    for i in range(0, len(todo), batch):
 618 | +        chunk = todo[i:i + batch]
 619 | +        contexts = {}
 620 | +        for m in chunk:
 621 | +            text, win = CI._window_text(sources[m["video_id"]], m["sentences"][0], m["sentences"][1])
 622 | +            contexts[m["moment_id"]] = {"text": text, "title": sources[m["video_id"]].title or "",
 623 | +                                        "channel": _name(m, ctx), "window": win,
 624 | +                                        "published": str(m.get("published_at") or "")[:16],
 625 | +                                        "show_date": ctx.now.strftime("%Y-%m-%d")}
 626 | +        try:
 627 | +            got, backend = CI.step_a(router, contexts, writer_vendor, seed=7 + i, writer_family=writer_family)
 628 | +        except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
 629 | +            for m in chunk:
 630 | +                fails[m["moment_id"]] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}"]
 631 | +            continue
 632 | +        b = router.backends.get(backend)
 633 | +        vendors.add(b.vendor if b else backend)
 634 | +        families.add(b.family if b else backend)
 635 | +        for mid, a in got.items():
 636 | +            a_by[mid] = a
 637 | +            fails[mid] = CI.a_failures(a)
 638 | +            db[f"{mid}:{STEP_A_VERSION}"] = a
 639 | +    if store and todo:
 640 | +        os.makedirs(os.path.dirname(os.path.abspath(store)), exist_ok=True)
 641 | +        with open(store + ".tmp", "w") as f:
 642 | +            json.dump(db, f, indent=1)
 643 | +        os.replace(store + ".tmp", store)
 644 | +    return a_by, fails, vendors, families
 645 | +
 646 | +
 647 | +ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words, with a
 648 | +voice-over that makes a point. Below are clips (verbatim quotes, each with its channel and length) that passed our
 649 | +checks. The channels were not in one conversation and never answer each other.
 650 | +
 651 | +{note}
 652 | +{clips}
 653 | +
 654 | +Find up to {k} ANGLES, best first. An angle is ONE sentence a viewer could repeat: a point that several of these clips
 655 | +GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
 656 | +the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
 657 | +it is today's.
 658 | +The video uses ONE clip per channel: a hook and 2-3 clips, from 3-4 DIFFERENT channels, together {lo:.0f}-{hi:.0f}
 659 | +seconds of clips. Give as many good angles as the clips allow (aim for {k}); for each angle give: "angle" (the
 660 | +sentence); "moments": the ids of 5 to 8 clips that support it (more choice survives a clip that later fails a check),
 661 | +from at least 3 different channels, with enough seconds among them; "hook": one of those ids whose FIRST WORDS grab
 662 | +attention AND set up the angle; "support": for each of those ids, a few words on what it adds (an internal note).
 663 | +Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
 664 | +"support": {{"id": "..."}}}}]}}"""
 665 | +
 666 | +STYLES = {
 667 | +    "host": "HOST STYLE: you have a point of view. A bridge may (a) tease the next clip with a question or a topic, never "
 668 | +            "saying what its speaker thinks; (b) hand off with an attribution ONLY for a clip whose speaker is marked "
 669 | +            "VERIFIED, with the clip's own hedge (\"Stephan Livera thinks so.\"); (c) land your own takeaway AFTER a "
 670 | +            "clip, as your opinion, never as what the speaker said.",
 671 | +    "quote": "QUOTE-LED STYLE: introduce each clip by its show and its topic in a few words; you may quote AT MOST FOUR "
 672 | +             "exact words of that clip in quotation marks; the point is carried by the sequence of clips and the ONE "
 673 | +             "title."}
 674 | +
 675 | +WRITE_V3 = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 676 | +THE ANGLE (the point this video makes): "{angle}"
 677 | +The clips, in play order (verbatim; the channels were not in one conversation and never answer each other):
 678 | +
 679 | +{note}
 680 | +{lineup}
 681 | +
 682 | +The video plays: the HOOK clip, then your INTRO, then clip 1, then {slots}, then a sign-off that credits every channel
 683 | +(written by code).
 684 | +Write:
 685 | +- "intro": heard right AFTER the hook: your own take that sets up the angle.
 686 | +- "bridges": exactly {n_bridges} line(s), one after each clip but the last.
 687 | +- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters.
 688 | +- LENGTH: intro + bridges together {lo}-{hi} words; the intro at most {intro_words}, each bridge at most {bridge_words}.
 689 | +Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
 690 | +{style}
 691 | +RULES (a line that breaks one is rejected):
 692 | +- NEVER restate a clip's claim before or after it, and never repeat its words: the clip says it, in its own words.
 693 | +- Your OWN commentary (an opinion, framing, a question, a tease, a takeaway) is welcome, but it must contain no number,
 694 | +  price, date, named person or company, must not say or imply what any speaker thinks, and must not relate speakers.
 695 | +- Say what a speaker says or thinks ONLY for a clip marked VERIFIED, by that name, with the clip's own hedge: "thinks"
 696 | +  for "I think", "feels" for "I feel like", "says" only for a flat statement. For any other clip credit the SHOW only
 697 | +  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says".
 698 | +- Never say or imply that channels agree, answer, rebut or react to each other.
 699 | +- No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
 700 | +  "slams", "exposes", "admits", "confirms", "caught".
 701 | +{extra}Return ONLY this JSON object: {{"intro": {{"text": "...", "cites": []}}, "bridges": [{{"text": "...", "cites": ["id"]}}],
 702 | +"title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""
 703 | +
 704 | +COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
 705 | +different person's own words).
 706 | +
 707 | +{package}
 708 | +
 709 | +1) State the video's through-line in ONE sentence, or "none" if it has none.
 710 | +2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
 711 | +3) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
 712 | +   1 = no point, or a point the clips do not support).
 713 | +Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "vo_point": 1}}"""
 714 | +
 715 | +
 716 | +def current_levels(sources, ctx, hours=24.0):
 717 | +    """The Bitcoin price levels this universe states as CURRENT (audit p2 C10): from sentences that name Bitcoin, in a
 718 | +    clause with a present-tense word before the price and no future, conditional or history word in the sentence
 719 | +    (vo_fidelity.current_level_values), from sources <= `hours` old (L-v 3)."""
 720 | +    out = set()
 721 | +    for src in sources:
 722 | +        age = E.age_hours(src.published_at, ctx.now)
 723 | +        if age is None or age > hours:
 724 | +            continue
 725 | +        for a, b in src.sentences:
 726 | +            t = E.spoken(src.tokens[a:b + 1])
 727 | +            if E.names_bitcoin(t):
 728 | +                out |= set(VF.current_level_values(t))
 729 | +    return sorted(out)
 730 | +
 731 | +
 732 | +def check_angles(obj, by_id, k=MAX_ANGLES):
 733 | +    if not isinstance(obj, dict) or set(obj) != {"angles"} or not isinstance(obj["angles"], list) or \
 734 | +            not 1 <= len(obj["angles"]) <= k:
 735 | +        raise ValueError(f"exactly {{'angles': [1-{k} items]}}")
 736 | +    out = []
 737 | +    for i, a in enumerate(obj["angles"]):
 738 | +        if not isinstance(a, dict) or set(a) != {"angle", "moments", "hook", "support"}:
 739 | +            raise ValueError(f"angle {i + 1}: keys must be exactly angle, moments, hook, support")
 740 | +        ms = a["moments"]
 741 | +        if not isinstance(a["angle"], str) or not a["angle"].strip() or not isinstance(ms, list) or \
 742 | +                not all(isinstance(m, str) for m in ms):
 743 | +            raise ValueError(f"angle {i + 1}: a sentence and a list of offered ids")
 744 | +        unknown = [m for m in ms if m not in by_id]
 745 | +        if unknown:
 746 | +            raise ValueError(f"angle {i + 1}: ids not offered {unknown[:3]} (never dropped silently)")
 747 | +        if not 3 <= len(ms) <= 8 or len(set(ms)) != len(ms):
 748 | +            raise ValueError(f"angle {i + 1}: 3-8 distinct offered ids")
 749 | +        if len({by_id[m]["channel_id"] for m in ms}) < 3 or a["hook"] not in ms:
 750 | +            raise ValueError(f"angle {i + 1}: >= 3 channels (one clip per channel, L-u), and the hook one of its moments")
 751 | +        if not isinstance(a["support"], dict) or set(a["support"]) != set(ms):
 752 | +            raise ValueError(f"angle {i + 1}: 'support' needs exactly its moment ids")
 753 | +        out.append(a)
 754 | +    return out
 755 | +
 756 | +
 757 | +def lineup_for(angle, by_id, dropped=frozenset()):
 758 | +    """Hook + 2-3 clips for one angle: the proposer's hook (else the angle's best hook-eligible moment by its first
 759 | +    2 s), clips from the angle's other moments, every segment from a different channel (L-u), at most
 760 | +    PRICE_PREDICTIONS_MAX price predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), the
 761 | +    length the runtime AND R4 allow. Best by the proposer's order. None if impossible."""
 762 | +    ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
 763 | +    hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")]
 764 | +    hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
 765 | +    for h in hooks:
 766 | +        pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
 767 | +                and m["channel_id"] != h["channel_id"]]
 768 | +        best = None
 769 | +        for n in (3, 2):
 770 | +            lo, hi = content_range(n)
 771 | +            for combo in itertools.combinations(pool, n):
 772 | +                if len({m["channel_id"] for m in combo}) != n:
 773 | +                    continue
 774 | +                if sum("price_prediction" in m.get("risk", []) for m in (h, *combo)) > PRICE_PREDICTIONS_MAX:
 775 | +                    continue
 776 | +                order = sorted(combo, key=lambda m: angle["moments"].index(m["moment_id"]))
 777 | +                if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
 778 | +                    continue
 779 | +                dur = h["duration_s"] + sum(m["duration_s"] for m in order)
 780 | +                if not lo <= dur <= hi:
 781 | +                    continue
 782 | +                key = (n, -sum(angle["moments"].index(m["moment_id"]) for m in order))
 783 | +                if best is None or key > best[0]:
 784 | +                    best = (key, [h] + order)
 785 | +            if best:
 786 | +                return best[1]
 787 | +    return None
 788 | +
 789 | +
 790 | +STOP = frozenset("a an the and or but so of to in on at for from with by as is are was were be been it its it's this that "
 791 | +                 "these those there here i you he she we they me him her us them my your his our their not no do does "
 792 | +                 "did just like kind sort very really some any all".split())
 793 | +
 794 | +
 795 | +def duplicates(pk):
 796 | +    """A clip must add something (orchestrator 03:40; audit p2 C16): no VO line (intro, every bridge), no title and no
 797 | +    caption repeats ANY clip's words: a run of >= 5 canonical tokens with >= 3 content words, or >= 60 % of a short
 798 | +    clip's (<= 15 content words) CONTENT words."""
 799 | +    out = []
 800 | +    lines = [(x["slot"], x["text"]) for x in pk["lines"]]
 801 | +    for seg in pk["segments"]:
 802 | +        ct = VF.ctoks(seg["text"])
 803 | +        content = [t for t in ct if t not in STOP]
 804 | +        for slot, text in lines:
 805 | +            lt = VF.ctoks(text)
 806 | +            run5 = any(VF._run_in(ct[j:j + 5], lt) and sum(t not in STOP for t in ct[j:j + 5]) >= 3
 807 | +                       for j in range(max(0, len(ct) - 4)))
 808 | +            lset = {t for t in lt if t not in STOP}
 809 | +            share = len([t for t in content if t in lset]) / max(1, len(content))
 810 | +            if run5 or (len(content) <= 15 and share >= 0.6):
 811 | +                out.append({"slot": slot, "rule": "DUPLICATE", "detail": f"repeats the words of {seg['label']}"})
 812 | +    return out
 813 | +
 814 | +
 815 | +NO_LINE = re.compile(r"^\W*(none|no\b|n/?a\b|unclear|nothing|there is no)", re.I)
 816 | +
 817 | +
 818 | +def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
 819 | +    """The blind QUALITY verdict (never the vendor / family of the text it judges): through-line + ratings. ->
 820 | +    (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7)."""
 821 | +    import providers as P
 822 | +    r = None
 823 | +    try:
 824 | +        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(package=CI.package_view(pk)), 1200, seed,
 825 | +                        avoid_vendor=writer_vendor, avoid_family=writer_family)
 826 | +        v = json.loads(r.text.strip())
 827 | +        labels = [sg["label"] for sg in pk["segments"]]
 828 | +        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 829 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labels) or \
 830 | +                any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 831 | +            raise ValueError("coherence verdict out of contract")
 832 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 833 | +        if r is not None and isinstance(e, (ValueError, TypeError)):
 834 | +            router.reject(r)
 835 | +        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False}
 836 | +    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
 837 | +    ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
 838 | +        min(list(v["clips"].values()) + [v["vo_point"]]) >= COHERENCE_MIN
 839 | +    return ok, dict(v, backend=r.backend, measured=True, replayed=bool(getattr(r, "replayed", False)))
 840 | +
 841 | +
 842 | +def _lineup_block(segs, ctx, a_by):
 843 | +    from story_semantics import quote_data
 844 | +    out = []
 845 | +    for i, m in enumerate(segs):
 846 | +        ver = (a_by.get(m["moment_id"]) or {}).get("speaker_verified")
 847 | +        who = f"speaker VERIFIED: {_name(m, ctx)}" if ver else "speaker NOT verified (credit the show only)"
 848 | +        out.append(f'{"HOOK" if i == 0 else f"CLIP {i}"} id={m["moment_id"]} | show: {_name(m, ctx)} | {who} | '
 849 | +                   f'{m["duration_s"]:.1f} s | "{quote_data(m["text"], 700)}"')
 850 | +    return "\n".join(out)
 851 | +
 852 | +
 853 | +def write_v3(router, angle, segs, ctx, a_by, style="host", extra="", seed=7, avoid_vendor=None):
 854 | +    from select_by_id import UNTRUSTED
 855 | +    from story_semantics import quote_data
 856 | +    content = sum(m["duration_s"] for m in segs)
 857 | +    nb = len(segs) - 2
 858 | +    iw, bw, (lo, hi) = budgets(content, nb)
 859 | +    slots = ", then ".join(f"your bridge, then clip {i + 2}" for i in range(nb)) or "nothing"
 860 | +    angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
 861 | +    prompt = WRITE_V3.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 862 | +                             lineup=_lineup_block(segs, ctx, a_by), slots=slots, n_bridges=nb, lo=lo, hi=hi,
 863 | +                             intro_words=min(iw, 30), bridge_words=min(bw, 20), style=STYLES[style],
 864 | +                             extra=(extra + "\n") if extra else "")
 865 | +    r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor)
 866 | +    try:
 867 | +        obj = json.loads(r.text.strip())
 868 | +        ids = [m["moment_id"] for m in segs]
 869 | +        keys = {"intro", "bridges", "title", "caption"}
 870 | +        if not isinstance(obj, dict) or set(obj) != keys:
 871 | +            raise ValueError(f"keys must be exactly {sorted(keys)}")
 872 | +        if not isinstance(obj["bridges"], list) or len(obj["bridges"]) != nb:
 873 | +            raise ValueError(f"'bridges' must hold {nb} lines")
 874 | +        for slot, ln in [("intro", obj["intro"]), ("title", obj["title"]), ("caption", obj["caption"])] + \
 875 | +                [(f"bridge_{i + 1}", b) for i, b in enumerate(obj["bridges"])]:
 876 | +            if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
 877 | +                    not ln["text"].strip() or not isinstance(ln["cites"], list) or \
 878 | +                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]):
 879 | +                raise ValueError(f"{slot}: needs text and cites from the line-up's ids")
 880 | +        if len(obj["title"]["text"]) > 70 or len(obj["caption"]["text"]) > 220:
 881 | +            raise ValueError("title <= 70 characters, caption <= 220")
 882 | +    except (ValueError, TypeError):
 883 | +        router.reject(r)
 884 | +        raise
 885 | +    return r, dict(obj, type="moments", angle=angle["angle"], style=style)
 886 | +
 887 | +
 888 | +def fidelity_segments(pk, a_by):
 889 | +    """The fidelity gate's view of the segments: the show always; the speaker only when step A VERIFIED the channel's
 890 | +    host with quoted evidence (law L-v 1); otherwise not verified."""
 891 | +    out = {}
 892 | +    for sg in pk["segments"]:
 893 | +        ver = (a_by.get(sg["moment_id"]) or {}).get("speaker_verified")
 894 | +        out[sg["moment_id"]] = {"show": sg["channel"], "speaker": sg["channel"] if ver else None,
 895 | +                                "names": [sg["channel"]] if ver else [], "video_id": sg["video_id"], "text": sg["text"]}
 896 | +    return out
 897 | +
 898 | +
 899 | +def cheap_checks(pk, a_by, levels, now):
 900 | +    """The gates that cost nothing, run before any paid verdict: VO fidelity's deterministic rules, DUPLICATE,
 901 | +    runtime, R4. -> (violations, det, dup, rt_ok, r4_res)."""
 902 | +    segs_v = fidelity_segments(pk, a_by)
 903 | +    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
 904 | +    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 905 | +    det = VF.check_deterministic(segs_v, lines, man, levels)
 906 | +    dup = duplicates(pk)
 907 | +    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
 908 | +    r4_res = r4(pk)
 909 | +    v = det["violations"] + dup + ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail":
 910 | +                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change the VO's "
 911 | +                                                      f"length"}]) + \
 912 | +        ([] if r4_res[0] else [{"slot": "-", "rule": "R4", "detail": r4_res[1]}])
 913 | +    return v, det, dup, rt_ok, r4_res
 914 | +
 915 | +
 916 | +def paid_gates(router, pk, sources, a_by, levels, now, writers_v, writers_f, pool):
 917 | +    """The classifying fidelity verdict and context integrity (B0, B, C; step A precomputed), concurrently."""
 918 | +    segs_v = fidelity_segments(pk, a_by)
 919 | +    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
 920 | +    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 921 | +    a_use = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 922 | +    f_fid = pool.submit(VF.check, router, segs_v, lines, writers_v, 7, man, levels, writers_f)
 923 | +    f_ctx = pool.submit(CI.check_contexts, router, pk, CI.contexts_from_sources(pk, sources, now), writers_v, 7, a_use,
 924 | +                        writers_f)
 925 | +    return f_fid.result(), f_ctx.result()
 926 | +
 927 | +
 928 | +def exclusion_for(router, m, sources, cache):
 929 | +    if m["moment_id"] not in cache:
 930 | +        import moments as M
 931 | +        src = sources[m["video_id"]]
 932 | +        a, b = CI.window(src, m["sentences"][0], m["sentences"][1])
 933 | +        sent = lambda k: E.spoken(src.tokens[src.sentences[k][0]:src.sentences[k][1] + 1])
 934 | +        cache[m["moment_id"]] = M.exclusion_verdict(
 935 | +            router, m["text"], " ".join(sent(k) for k in range(a, m["sentences"][0])),
 936 | +            " ".join(sent(k) for k in range(m["sentences"][1] + 1, b + 1)),
 937 | +            avoid_model=(m.get("mined") or {}).get("by"))
 938 | +    return cache[m["moment_id"]]
 939 | +
 940 | +
 941 | +def truth_for(router, m, work_dir, cache):
 942 | +    if m["moment_id"] not in cache:
 943 | +        import transcript_truth as TT
 944 | +        try:
 945 | +            cache[m["moment_id"]] = TT.verify_segment(router, m["video_id"], float(m["start"]), float(m["end"]),
 946 | +                                                      m["text"], work_dir)
 947 | +        except Exception as e:                         # not measured: never a pass (law L-m)
 948 | +            cache[m["moment_id"]] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
 949 | +    return cache[m["moment_id"]]
 950 | +
 951 | +
 952 | +def _writers(router):
 953 | +    """The vendor and family of the angle_write chain's first back-end not down (verdicts avoid them; a live failover
 954 | +    adds the next writer's)."""
 955 | +    for name in router.chain("angle_write"):
 956 | +        b = router.backends.get(name)
 957 | +        if b is not None and name not in router.down:
 958 | +            return {b.vendor}, {b.family}
 959 | +    return set(), set()
 960 | +
 961 | +
 962 | +def _redo(violations):
 963 | +    return ("Your previous script was REJECTED. Exactly these lines failed, with the reason; rewrite ONLY them:\n" +
 964 | +            "\n".join(f"- {v['slot']}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
 965 | +
 966 | +
 967 | +def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 968 | +          writes=WRITES, work_dir=None, store=None, styles=("host", "quote"), spend=None):
 969 | +    """Angle first, inside the orchestrator's budgets (05:25 item 5, 05:30): at most max_angles angles x `writes`
 970 | +    writes, stopped at the first package that passes every hard gate with coherence >= COHERENCE_MIN. work_dir: where
 971 | +    law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger. spend: a
 972 | +    callable returning the ledger's USD (dollars per package). -> {"package", "packages", "tried", "angles", ...}."""
 973 | +    t0 = time.time()
 974 | +    usd0 = spend() if spend else None
 975 | +    ms, why = usable(moments, ctx, delivered, optout)
 976 | +    wv, wf = _writers(router)
 977 | +    a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
 978 | +    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 979 | +    levels = current_levels(sources.values(), ctx)
 980 | +    out = {"packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
 981 | +           "prescreen": {"screened": len(fails), "cleared": len(cleared),
 982 | +                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "package": None}
 983 | +    log(f"  {len(ms)} usable, {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 984 | +    if len({m["channel_id"] for m in cleared.values()}) < 3:
 985 | +        out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 986 | +        return out
 987 | +    if not work_dir:
 988 | +        out["why_none"] = "no work_dir: law L-v 2's second pass cannot run, so no package can pass (fail closed)"
 989 | +        return out
 990 | +    from select_by_id import UNTRUSTED
 991 | +    from story_semantics import quote_data
 992 | +    clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
 993 | +                      for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
 994 | +    lo, hi = content_range(2)[0], content_range(3)[1]
 995 | +    angles, angle_reply = None, None
 996 | +    for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
 997 | +        r = None
 998 | +        try:
 999 | +            r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
1000 | +                                                               clips=clips, k=max_angles, lo=lo, hi=hi), 3000, seed)
1001 | +            angles, angle_reply = check_angles(json.loads(r.text.strip()), cleared, max_angles), r
1002 | +            break
1003 | +        except Exception as e:
1004 | +            if r is not None:
1005 | +                router.reject(r)
1006 | +            out["why_none"] = f"no readable angles: {type(e).__name__}: {str(e)[:200]}"
1007 | +    if not angles:
1008 | +        return out
1009 | +    out.pop("why_none", None)
1010 | +    out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
1011 | +    writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
1012 | +    log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
1013 | +    exc, tru = {}, {}
1014 | +    with ThreadPoolExecutor(max_workers=8) as pool:
1015 | +        for ai, angle in enumerate(angles):
1016 | +            dropped, w_used = set(), 0
1017 | +            while w_used < writes and not out["packages"]:
1018 | +                segs = lineup_for(angle, cleared, frozenset(dropped))
1019 | +                rec = {"angle": ai + 1, "text": angle["angle"],
1020 | +                       "lineup": [m["moment_id"] for m in segs] if segs else None, "attempts": []}
1021 | +                out["tried"].append(rec)
1022 | +                if segs is None:
1023 | +                    rec["why"] = "no line-up: fewer than a hook + 2 clips from distinct channels in the length rules"
1024 | +                    break
1025 | +                bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
1026 | +                                       pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
1027 | +                extra, relined = "", False
1028 | +                while w_used < writes:
1029 | +                    style = styles[min(w_used, len(styles) - 1)]
1030 | +                    w_used += 1
1031 | +                    try:
1032 | +                        wr, fields = write_v3(router, angle, segs, ctx, a_by, style, extra, seed=7 + w_used + 10 * ai)
1033 | +                    except Exception as e:
1034 | +                        rec["attempts"].append({"style": style, "writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
1035 | +                        continue
1036 | +                    writers_v.add(wr.vendor)
1037 | +                    writers_f.add(wr.family)
1038 | +                    pk = assemble([m["moment_id"] for m in segs], cleared, fields, ctx,
1039 | +                                  f"written ({style}), attempt {w_used}")
1040 | +                    cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
1041 | +                    att = {"style": style, "writer": wr.backend, "runtime": pk["runtime_s_estimate"],
1042 | +                           "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]]}
1043 | +                    rec["attempts"].append(att)
1044 | +                    log(f"  angle {ai + 1} write {w_used} ({style}, {wr.backend}): " +
1045 | +                        ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
1046 | +                        + f" ({time.time() - t0:.0f} s)")
1047 | +                    if cheap:
1048 | +                        att["violations"] = cheap
1049 | +                        extra = _redo(cheap)
1050 | +                        continue
1051 | +                    fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
1052 | +                    framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
1053 | +                    att["violations"] = fid["violations"] + cx["violations"]
1054 | +                    att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
1055 | +                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'}, context {'PASS' if cx['ok'] else 'FAIL'} "
1056 | +                        f"({time.time() - t0:.0f} s)")
1057 | +                    if not fid["ok"] or not cx["ok"]:
1058 | +                        if fid["ok"] and not framing:
1059 | +                            rec["why"] = "context integrity failed on something the VO cannot fix"
1060 | +                            w_used = writes
1061 | +                            break
1062 | +                        extra = _redo(fid["violations"] + [{"slot": v["segment"], "rule": v["rule"],
1063 | +                                                            "detail": VO_FIX.get(v["rule"], v["detail"])}
1064 | +                                                           for v in framing])
1065 | +                        continue
1066 | +                    got = {mid: (f[0].result(), f[1].result()) for mid, f in bg.items()}
1067 | +                    lost = {mid for mid, (e, t) in got.items() if e.get("verdict") != "keep" or not t.get("ok")}
1068 | +                    att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
1069 | +                    att["second_pass"] = {mid: t for mid, (_, t) in got.items()}
1070 | +                    if lost:
1071 | +                        dropped |= lost
1072 | +                        rec["why"] = f"exclusion / L-v 2 dropped {sorted(lost)}: re-lined"
1073 | +                        relined = True
1074 | +                        break
1075 | +                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)
1076 | +                    att["coherence"] = coh
1077 | +                    log(f"    coherence {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo {coh.get('vo_point')} "
1078 | +                        f"({time.time() - t0:.0f} s)")
1079 | +                    a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
1080 | +                    pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
1081 | +                                            {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
1082 | +                                            ok_c, coh)
1083 | +                    if not ok_c:
1084 | +                        rec["why"] = "coherence below 4 or no through-line: next angle"
1085 | +                        w_used = writes
1086 | +                        break
1087 | +                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend,
1088 | +                                    "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
1089 | +                                    "coherence": coh.get("backend")}
1090 | +                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh}
1091 | +                    pk["seconds"] = round(time.time() - t0, 1)
1092 | +                    pk["usd"] = round(spend() - usd0, 4) if spend else None
1093 | +                    out["packages"].append(pk)
1094 | +                    rec["result"] = "PACKAGE"
1095 | +                    break
1096 | +                if out["packages"] or not relined:
1097 | +                    break
1098 | +            if out["packages"]:
1099 | +                break
1100 | +            if time.time() - t0 > BUDGET_S * 2 or (spend and spend() - usd0 > BUDGET_USD * 2):
1101 | +                out["why_none"] = "twice the per-package time / spend budget is used: stopped"
1102 | +                break
1103 | +    out["package"] = out["packages"][0] if out["packages"] else None
1104 | +    out["seconds"] = round(time.time() - t0, 1)
1105 | +    out["usd"] = round(spend() - usd0, 4) if spend else None
1106 | +    return out
1107 | +
1108 | +
1109 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
1110 | +    """The sealed GATE INVENTORY (audit p2 C1; package_pin.REQUIRED_GATES): one row per hard gate, each
1111 | +    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m)."""
1112 | +    row = lambda ok, by, replayed=False, n=1, measured=True: {
1113 | +        "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
1114 | +        "replayed": bool(replayed), "n": n}
1115 | +    det = fid["deterministic"]
1116 | +    viol = {v["rule"] for v in ctx_.get("violations") or []}
1117 | +    a_rows = list((a_by or {}).values())
1118 | +    return {
1119 | +        "vo_fidelity_deterministic": row(det["ok"], "code (vo_fidelity.check_deterministic)"),
1120 | +        "vo_fidelity_verdict": row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"), fid.get("replayed"),
1121 | +                                   measured=bool(fid.get("measured"))),
1122 | +        "duplicate": row(not dup, "code (package.duplicates)"),
1123 | +        "price_now": row(not any(v["rule"] == "PRICE_NOW" for v in det["violations"]),
1124 | +                         "code (vo_fidelity.price_now)", measured=bool(det.get("price_now_measured"))),
1125 | +        "runtime": row(rt_ok, f"code (estimate at {WPS} w/s)"),
1126 | +        "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
1127 | +        "context_a": row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
1128 | +                         sorted({str(a.get("backend")) for a in a_rows}), any(a.get("replayed") for a in a_rows),
1129 | +                         n=len(a_rows)),
1130 | +        "context_b": row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
1131 | +                         measured=bool(ctx_.get("measured"))),
1132 | +        "context_c": row(ctx_.get("ok") is True and not (viol & {"NOT_ENTAILED", "POLARITY", "STRONGER"}),
1133 | +                         (ctx_.get("backends") or {}).get("C"), ctx_.get("replayed"), measured=bool(ctx_.get("measured"))),
1134 | +        "exclusion": row(all(e.get("verdict") == "keep" for e in exc.values()),
1135 | +                         sorted({str(e.get("backend")) for e in exc.values()}),
1136 | +                         any(e.get("replayed") for e in exc.values()), n=len(exc),
1137 | +                         measured=all(e.get("measured") for e in exc.values())),
1138 | +        "second_pass": row(all(t.get("ok") for t in truth.values()), sorted({str(t.get("model")) for t in truth.values()}),
1139 | +                           any(t.get("replayed") for t in truth.values()), n=len(truth),
1140 | +                           measured=all("error" not in t for t in truth.values())),
1141 | +        "coherence": row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
1142 | +    }
1143 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
1144 | new file mode 100644
1145 | index 00000000..e1fd886f
1146 | --- /dev/null
1147 | +++ b/pipeline/package_pin.py
1148 | @@ -0,0 +1,98 @@
1149 | +#!/usr/bin/env python3
1150 | +"""pipeline/package_pin.py — a pp.package/1 as the existing PINNED entry point's decision (pipeline/pinned.py, schema
1151 | +protocol_pulse.pinned_story.v1), so the SAME factory downstream (validate -> cut -> sentence law -> voice -> render ->
1152 | +gates -> release authorisation) renders a moments-first package.
1153 | +
1154 | +- Every segment carries `approved_text` = the moment's exact words (its source sentences, verbatim) and the record's
1155 | +  transcript sha256. The pin is `machine_cuts`, so the sentence law locates the words BY TEXT in the acquired
1156 | +  transcript, never by offsets. Times are YouTube coordinates (the store record's own seconds in the full video).
1157 | +- `approved_by` names the machine and REVIEW ONLY. No human approved this decision (law L-q).
1158 | +- The package's VO (intro, bridges with the renderer's after_clip), title, caption and its GATE INVENTORY travel in
1159 | +  `moments_package`, SEALED (audit p2 C1, the L-j pattern): `package_sha256` = seal() over exactly those bytes and the
1160 | +  inventory. to_pin() REFUSES a package whose inventory is missing a required gate, holds anything but exactly "PASS",
1161 | +  or rests on a replayed verdict (never deliverable, law L-j). REQUESTS R7's pinned.py patch recomputes the seal and
1162 | +  refuses any pin whose bytes or gates differ from what was sealed.
1163 | +- Writes nothing itself: to_pin() returns the dict; write_pin() writes it.
1164 | +"""
1165 | +import hashlib
1166 | +import json
1167 | +import os
1168 | +from datetime import datetime, timezone
1169 | +
1170 | +SCHEMA = "protocol_pulse.pinned_story.v1"
1171 | +REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
1172 | +                  "context_a", "context_b", "context_c", "exclusion", "second_pass", "coherence")
1173 | +
1174 | +
1175 | +class PinRefused(Exception):
1176 | +    """The package may not become a pinned decision."""
1177 | +
1178 | +
1179 | +def seal(segments, edl_vo, signoff, title, caption, gates):
1180 | +    """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
1181 | +    words, the transcript sha), the VO the renderer will speak (intro, bridges with after_clip), the sign-off, the ONE
1182 | +    title and caption (law L-t), and the gate inventory."""
1183 | +    body = {"segments": [{"video_id": s["video_id"], "start": round(float(s["start"]), 3),
1184 | +                          "end": round(float(s["end"]), 3), "text": s["approved_text"],
1185 | +                          "transcript_sha256": s.get("transcript_sha256")} for s in segments],
1186 | +            "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
1187 | +                                                             for b in edl_vo.get("bridges") or []]},
1188 | +            "signoff": signoff, "title": title, "caption": caption, "gates": gates}
1189 | +    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
1190 | +
1191 | +
1192 | +def gate_problems(gates):
1193 | +    """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
1194 | +    if not isinstance(gates, dict):
1195 | +        return ["no gate inventory"]
1196 | +    out = []
1197 | +    for g in REQUIRED_GATES:
1198 | +        row = gates.get(g)
1199 | +        if not isinstance(row, dict) or row.get("status") != "PASS":
1200 | +            out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
1201 | +        elif row.get("replayed") is not False:
1202 | +            out.append(f"{g}: replayed or not stated (never deliverable, law L-j)")
1203 | +    return out
1204 | +
1205 | +
1206 | +def to_pin(pk, run_name):
1207 | +    problems = gate_problems(pk.get("gates"))
1208 | +    if problems:
1209 | +        raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
1210 | +    segs = []
1211 | +    for i, s in enumerate(pk["segments"]):
1212 | +        segs.append({"role": "hook" if i == 0 else "clip", "video_id": s["video_id"], "channel": s["channel"],
1213 | +                     "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
1214 | +                     "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
1215 | +                     "time_coords": "youtube", "source": {"kind": "youtube"}})
1216 | +    edl_vo = {"intro": pk["vo"]["intro"],
1217 | +              "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
1218 | +    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"])
1219 | +    return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{sha[:8]}",
1220 | +            "label": "bitcoin", "headline": pk["title"],
1221 | +            "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
1222 | +            "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
1223 | +            "approval_ref": f"docs/audits/parallel/pp-selectid_STATE.md (top package, {run_name})",
1224 | +            "machine_cuts": True, "segments": segs,
1225 | +            "moments_package": {"schema": pk["schema"], "package_sha256": sha, "type": pk["type"],
1226 | +                                "vo_kind": pk.get("vo_kind"), "edl_vo": edl_vo,
1227 | +                                "signoff_expected": pk["vo"]["signoff"],
1228 | +                                "title": pk["title"], "caption": pk["caption"],
1229 | +                                "hook_first_words": pk["hook_first_words"],
1230 | +                                "vo_jobs": {"intro": "context", **{f"bridge_{i + 1}": "connection"
1231 | +                                                                   for i in range(len(pk["vo"]["bridges"]))}},
1232 | +                                "gates": pk["gates"],
1233 | +                                "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
1234 | +                                           "derived_from": "gates (every required row exactly PASS, checked above)",
1235 | +                                           "models": pk.get("models")},
1236 | +                                "runtime_s_estimate": pk["runtime_s_estimate"],
1237 | +                                "sources_30s_before": [s["url_30s_before"] for s in pk["segments"]]}}
1238 | +
1239 | +
1240 | +def write_pin(pk, run_name, out_dir, name="MOMENTS_PIN.json"):
1241 | +    pin = to_pin(pk, run_name)
1242 | +    os.makedirs(out_dir, exist_ok=True)
1243 | +    path = os.path.join(out_dir, name)
1244 | +    with open(path, "w") as f:
1245 | +        json.dump(pin, f, indent=1)
1246 | +    return path, pin
1247 | diff --git a/pipeline/providers.py b/pipeline/providers.py
1248 | new file mode 100644
1249 | index 00000000..0412d035
1250 | --- /dev/null
1251 | +++ b/pipeline/providers.py
1252 | @@ -0,0 +1,751 @@
1253 | +#!/usr/bin/env python3
1254 | +"""pipeline/providers.py — ONE provider interface for every model role (law L-x, orchestrator 2026-11-12 '02:45':
1255 | +"no single model, Ultron first").
1256 | +
1257 | +Every role (mining, angle + writing, fidelity verdict, context verdict, viewer takeaway, trend brief, story selection,
1258 | +check verdict) calls Router.call(role, prompt, ...). The role's back-end CHAIN comes from pipeline/model_providers.json;
1259 | +no vendor or model name appears in any role's code. A back-end that cannot answer now (out of credit, rate-limited after
1260 | +backoff, server error, transport failure, not configured, the local model without its GPU0 lease) raises Unavailable and
1261 | +the chain moves on, so the run continues when any one vendor is down (tonight OpenAI ran dry mid-run). A role whose whole
1262 | +chain is unavailable raises ProviderError: a failed role, never a pass (law L-m).
1263 | +
1264 | +Verdict roles never run on the writer's vendor or model family (law L-s: "a model from a different vendor than the
1265 | +writer"; law L-x: generator and judge are different models): Router.call(..., avoid_vendor=<vendors>,
1266 | +avoid_family=<families>) skips those back-ends; both accept one value or a set (the angle and every writer attempt).
1267 | +
1268 | +Replies are text only; strict parsing stays with the caller (no repair here, law L-l). Every exchange can be recorded
1269 | +(record_dir) and replayed offline (replay=True): the recorded back-end name travels with the reply, so every artefact
1270 | +names the model that produced it. A recording served in a LIVE run is `cached` (the same model's reply to the same
1271 | +bytes); one served offline is `replayed` (never deliverable, law L-j). A reply its caller finds out of contract is
1272 | +dropped from the recordings (Router.reject), so it is asked again next time instead of served again.
1273 | +
1274 | +A back-end that refuses ONE request (RequestRejected: a bad request, over its context, an empty reply) is skipped for
1275 | +that call only; one that cannot answer at all (Unavailable: account, auth, rate limit after backoff, server, transport)
1276 | +is down for the rest of the run. Spend is priced per back-end at the config's upper-bound USD per 1M tokens (per minute
1277 | +for transcription) into one ledger with a guard: each paid call RESERVES its upper bound under the ledger lock before it
1278 | +runs and settles after; an unreadable ledger stops every paid call (fail closed); a free back-end is never stopped
1279 | +(SpendLimit). Heimdall's account is read from its /credits endpoint and the 90% tripwire NOTIFIES (Reply.notices and
1280 | +Router.notices), it never halts (PBX 02:45).
1281 | +
1282 | +Keys are read by name from the env file inside code; never printed or logged.
1283 | +"""
1284 | +import hashlib
1285 | +import json
1286 | +import os
1287 | +import time
1288 | +import urllib.error
1289 | +import urllib.request
1290 | +import uuid
1291 | +from dataclasses import dataclass, field
1292 | +
1293 | +HERE = os.path.dirname(os.path.abspath(__file__))
1294 | +CONFIG = os.path.join(HERE, "model_providers.json")
1295 | +ENV_PATH = os.path.join("/home/ultron/protocol_pulse", ".env")   # the order's key file (read by name inside code only)
1296 | +BACKOFF_S = (10, 30, 90)            # rate limits / server errors / transport; an exhausted account is final at once
1297 | +PER_REQUEST_CODES = (400, 413, 422)  # the request itself was refused: skip this back-end for THIS call only
1298 | +
1299 | +
1300 | +class Unavailable(Exception):
1301 | +    """This back-end cannot answer now: the chain moves to the next one, and it is down for the rest of the run."""
1302 | +
1303 | +
1304 | +class RequestRejected(Exception):
1305 | +    """This back-end refused THIS request (bad request, over its context, empty reply): the chain moves on for this
1306 | +    call only; the back-end stays available to other calls."""
1307 | +
1308 | +
1309 | +class ProviderError(Exception):
1310 | +    """No back-end of the role's chain answered: the role failed (never a pass)."""
1311 | +
1312 | +
1313 | +class SpendLimit(Exception):
1314 | +    """The session's spend guard is reached: no further model call."""
1315 | +
1316 | +
1317 | +class ReplayMiss(Exception):
1318 | +    """Offline replay has no recorded exchange for this call."""
1319 | +
1320 | +
1321 | +@dataclass
1322 | +class Reply:
1323 | +    text: str
1324 | +    backend: str                                  # "vendor:model", the model that produced this text
1325 | +    vendor: str
1326 | +    seconds: float = 0.0
1327 | +    usage: dict = field(default_factory=dict)     # {"in": n, "out": n} (reasoning tokens counted as out)
1328 | +    usd: float = 0.0
1329 | +    replayed: bool = False                        # served OFFLINE from a recording (never deliverable, law L-j)
1330 | +    tried: list = field(default_factory=list)     # [(backend, why unavailable)] before this one answered
1331 | +    notices: list = field(default_factory=list)
1332 | +    family: str = ""                              # the model family (law L-x: generator and judge differ)
1333 | +    cached: bool = False                          # a live run served this model's recorded reply to the same bytes
1334 | +    record_path: str = ""                         # where the exchange is recorded (Router.reject removes it)
1335 | +
1336 | +
1337 | +def env_value(path, name):
1338 | +    """One key's value from an env file, read by name inside code (never printed or logged)."""
1339 | +    try:
1340 | +        with open(path) as f:
1341 | +            for line in f:
1342 | +                k, sep, v = line.strip().partition("=")
1343 | +                k = k.strip()
1344 | +                k = k[len("export "):].strip() if k.startswith("export ") else k
1345 | +                if sep and k == name:
1346 | +                    return v.strip().strip('"').strip("'")
1347 | +    except OSError:
1348 | +        pass
1349 | +    return None
1350 | +
1351 | +
1352 | +def _http_json(url, body, headers, timeout):
1353 | +    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json",
1354 | +                                                                              **headers})
1355 | +    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
1356 | +
1357 | +
1358 | +def _with_backoff(fn, final_codes=()):
1359 | +    """fn() with BACKOFF_S retries on 429 / 5xx / transport; HTTP codes in final_codes, an exhausted account and any
1360 | +    other 4xx are final. A refusal of the request itself (PER_REQUEST_CODES) raises RequestRejected; anything else
1361 | +    that cannot answer raises Unavailable, with the reason."""
1362 | +    last = None
1363 | +    for wait in BACKOFF_S + (None,):
1364 | +        try:
1365 | +            return fn()
1366 | +        except urllib.error.HTTPError as e:
1367 | +            try:
1368 | +                err = json.loads(e.read() or b"{}")
1369 | +            except (ValueError, OSError):
1370 | +                err = {}
1371 | +            e_obj = err.get("error") if isinstance(err.get("error"), dict) else {}
1372 | +            code = str(e_obj.get("code") or e_obj.get("type") or err.get("type") or "")
1373 | +            last = f"HTTP {e.code} {code}".strip()
1374 | +            if e.code in final_codes or "insufficient_quota" in code or "credit" in code or "billing" in code:
1375 | +                raise Unavailable(last + " (final: account)") from None
1376 | +            if (e.code == 429 or e.code >= 500) and wait is not None:
1377 | +                time.sleep(wait)
1378 | +                continue
1379 | +            if e.code in PER_REQUEST_CODES:
1380 | +                raise RequestRejected(last) from None
1381 | +            raise Unavailable(last) from None
1382 | +        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as e:
1383 | +            last = type(e).__name__
1384 | +            if wait is not None:
1385 | +                time.sleep(wait)
1386 | +                continue
1387 | +            raise Unavailable(last) from None
1388 | +    raise Unavailable(last or "unavailable")
1389 | +
1390 | +
1391 | +# ── back-ends ──
1392 | +
1393 | +class Backend:
1394 | +    vendor = "?"
1395 | +
1396 | +    def __init__(self, name, spec, env_path):
1397 | +        self.name, self.spec, self.env_path = name, spec, env_path
1398 | +        self.model = spec["model"]
1399 | +        self.family = spec.get("family") or self.model.split("/")[-1].split(":")[0].split("-")[0]
1400 | +        self.price = tuple(spec.get("price_usd_per_1m") or (0.0, 0.0))
1401 | +        self.timeout = float(spec.get("timeout_s", 600))
1402 | +
1403 | +    def usd(self, usage):
1404 | +        return round(usage.get("in", 0) * self.price[0] / 1e6 + usage.get("out", 0) * self.price[1] / 1e6, 6)
1405 | +
1406 | +    def free(self):
1407 | +        return not any(self.price)
1408 | +
1409 | +    def max_out(self, max_tokens):
1410 | +        """The most output tokens this back-end may bill for one call (its own floor applied)."""
1411 | +        return max(int(self.spec.get("min_out", 0)), max_tokens)
1412 | +
1413 | +    def upper_usd(self, prompt, max_tokens, system=None):
1414 | +        """The call's spend upper bound: every prompt character a token (a safe over-estimate) + the output cap."""
1415 | +        return self.usd({"in": len(prompt) + len(system or "") + 200, "out": self.max_out(max_tokens)})
1416 | +
1417 | +    def key(self, name):
1418 | +        k = env_value(self.env_path, name)
1419 | +        if not k:
1420 | +            raise Unavailable(f"{name} not configured")
1421 | +        return k
1422 | +
1423 | +    def complete(self, prompt, max_tokens, seed, system=None):
1424 | +        raise NotImplementedError
1425 | +
1426 | +
1427 | +class LocalBackend(Backend):
1428 | +    """gemma3:27b (or the configured local model) on Ultron's GPU0 Ollama through story_semantics.LocalLLM: its GPU0
1429 | +    placement guard, digest and temperature 0 kept. Only a STARTED LocalLLM handed in by the caller that holds the GPU0
1430 | +    lease (law L-r) makes this back-end available; without one it is Unavailable (this builder session never uses a GPU)."""
1431 | +    vendor = "local"
1432 | +
1433 | +    def __init__(self, name, spec, env_path, llm=None):
1434 | +        super().__init__(name, spec, env_path)
1435 | +        self.llm = llm
1436 | +
1437 | +    def complete(self, prompt, max_tokens, seed, system=None):
1438 | +        if self.llm is None:
1439 | +            raise Unavailable("local model needs a started LocalLLM under the GPU0 lease (law L-r)")
1440 | +        import http.client
1441 | +        import story_semantics as sm
1442 | +        if len(prompt) / 2.5 + max_tokens > sm.LLM_CTX:       # Ollama keeps the tail and drops the instructions
1443 | +            raise RequestRejected(f"prompt over the local context {sm.LLM_CTX}")
1444 | +        p = (system + "\n\n" + prompt) if system else prompt
1445 | +        t0 = time.time()
1446 | +        try:
1447 | +            text = self.llm._post(p, max_tokens, seed)
1448 | +        except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError) as e:
1449 | +            raise Unavailable(f"ollama: {type(e).__name__}") from None
1450 | +        return text, {"in": 0, "out": 0}, time.time() - t0
1451 | +
1452 | +
1453 | +class OpenAIBackend(Backend):
1454 | +    """OpenAI chat/completions; JSON mode (the word JSON is put in the system message, as json_object requires)."""
1455 | +    vendor = "openai"
1456 | +    URL = "https://api.openai.com/v1/chat/completions"
1457 | +
1458 | +    def complete(self, prompt, max_tokens, seed, system=None):
1459 | +        key = self.key("OPENAI_API_KEY")
1460 | +        body = {"model": self.model, "max_completion_tokens": max(int(self.spec.get("min_out", 0)), max_tokens),
1461 | +                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object."},
1462 | +                             {"role": "user", "content": prompt}],
1463 | +                "response_format": {"type": "json_object"}, "seed": seed}
1464 | +        if self.spec.get("reasoning_effort"):
1465 | +            body["reasoning_effort"] = self.spec["reasoning_effort"]
1466 | +        t0 = time.time()
1467 | +        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout))
1468 | +        u = j.get("usage") or {}
1469 | +        try:
1470 | +            text = j["choices"][0]["message"].get("content") or ""
1471 | +        except (KeyError, IndexError, TypeError):
1472 | +            raise RequestRejected("openai: no choices") from None
1473 | +        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
1474 | +
1475 | +
1476 | +class HeimdallBackend(OpenAIBackend):
1477 | +    """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY) at the config's base_url. JSON is asked for in
1478 | +    words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire."""
1479 | +    vendor = "heimdall"
1480 | +
1481 | +    def _base(self):
1482 | +        if not self.spec.get("base_url"):
1483 | +            raise Unavailable("heimdall: no base_url in the config")
1484 | +        return self.spec["base_url"].rstrip("/")
1485 | +
1486 | +    def complete(self, prompt, max_tokens, seed, system=None):
1487 | +        key = self.key("HEIMDALL_API_KEY")
1488 | +        body = {"model": self.model, "max_tokens": self.max_out(max_tokens), "seed": seed,
1489 | +                "temperature": self.spec.get("temperature", 0),
1490 | +                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."},
1491 | +                             {"role": "user", "content": prompt}]}
1492 | +        t0 = time.time()
1493 | +        base = self._base()
1494 | +        j = _with_backoff(lambda: _http_json(base + "/chat/completions", body, {"Authorization": "Bearer " + key},
1495 | +                                             self.timeout), final_codes=(401, 402, 403))
1496 | +        u = j.get("usage") or {}
1497 | +        try:
1498 | +            text = j["choices"][0]["message"].get("content") or ""
1499 | +        except (KeyError, IndexError, TypeError):
1500 | +            raise RequestRejected("heimdall: no choices") from None
1501 | +        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
1502 | +
1503 | +    def credits(self):
1504 | +        """(total_usage, total_credits) in USD from GET /credits, or None when it cannot be read."""
1505 | +        try:
1506 | +            key = self.key("HEIMDALL_API_KEY")
1507 | +            req = urllib.request.Request(self._base() + "/credits", headers={"Authorization": "Bearer " + key})
1508 | +            d = json.loads(urllib.request.urlopen(req, timeout=30).read())
1509 | +            d = d.get("data", d)
1510 | +            return float(d["total_usage"]), float(d["total_credits"])
1511 | +        except Exception:
1512 | +            return None
1513 | +
1514 | +
1515 | +class XAIBackend(Backend):
1516 | +    """xAI chat/completions; a judge runs at temperature 0 with the attempt's seed (production parity with LocalLLM).
1517 | +    Told it has no tools and must answer in one message (orchestrator 02:00)."""
1518 | +    vendor = "xai"
1519 | +    URL = "https://api.x.ai/v1/chat/completions"
1520 | +    SYSTEM = "You have no tools and no internet access. Answer in ONE message containing only the JSON object asked for."
1521 | +
1522 | +    def max_out(self, max_tokens):
1523 | +        return max(int(self.spec.get("min_out", 8000)), max_tokens * 8)       # a reasoning model thinks inside it
1524 | +
1525 | +    def complete(self, prompt, max_tokens, seed, system=None):
1526 | +        key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
1527 | +        body = {"model": self.model, "max_tokens": self.max_out(max_tokens),
1528 | +                "temperature": self.spec.get("temperature", 0), "seed": seed,
1529 | +                "messages": [{"role": "system", "content": self.SYSTEM + (" " + system if system else "")},
1530 | +                             {"role": "user", "content": prompt}]}
1531 | +        t0 = time.time()
1532 | +        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout),
1533 | +                          final_codes=(401, 402, 403))
1534 | +        u = j.get("usage") or {}
1535 | +        reasoning = int((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
1536 | +        try:
1537 | +            text = j["choices"][0]["message"].get("content") or ""
1538 | +        except (KeyError, IndexError, TypeError):
1539 | +            raise RequestRejected("xai: no choices") from None
1540 | +        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning}, \
1541 | +            time.time() - t0
1542 | +
1543 | +
1544 | +class AnthropicBackend(Backend):
1545 | +    """Anthropic Messages (streaming; adaptive thinking at the configured effort)."""
1546 | +    vendor = "anthropic"
1547 | +
1548 | +    def complete(self, prompt, max_tokens, seed, system=None):
1549 | +        try:
1550 | +            import anthropic
1551 | +        except ImportError:
1552 | +            raise Unavailable("anthropic SDK not installed") from None
1553 | +        client = anthropic.Anthropic(api_key=self.key("ANTHROPIC_API_KEY"), max_retries=3, timeout=self.timeout)
1554 | +        kw = {"model": self.model, "max_tokens": self.max_out(max_tokens),
1555 | +              "messages": [{"role": "user", "content": prompt}],
1556 | +              "system": (system or "") + " Reply with one JSON object only, no prose, no code fence."}
1557 | +        if self.spec.get("effort"):
1558 | +            kw["output_config"] = {"effort": self.spec["effort"]}
1559 | +            kw["thinking"] = {"type": "adaptive"}
1560 | +        t0 = time.time()
1561 | +        try:
1562 | +            with client.messages.stream(**kw) as s:
1563 | +                msg = s.get_final_message()
1564 | +        except anthropic.APIStatusError as e:
1565 | +            if e.status_code in PER_REQUEST_CODES:
1566 | +                raise RequestRejected(f"anthropic HTTP {e.status_code}") from None
1567 | +            raise Unavailable(f"anthropic HTTP {e.status_code}") from None
1568 | +        except anthropic.APIError as e:
1569 | +            raise Unavailable(f"anthropic {type(e).__name__}") from None
1570 | +        text = "".join(b.text for b in msg.content if b.type == "text")
1571 | +        return text, {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}, time.time() - t0
1572 | +
1573 | +
1574 | +class XAISearchBackend(Backend):
1575 | +    """xAI Responses API with live X and web search tools (x_search, web_search), for the trend brief only. The
1576 | +    reply text is returned as written; the caller validates it into the closed taxonomy (law L-w 4)."""
1577 | +    vendor = "xai_search"
1578 | +    URL = "https://api.x.ai/v1/responses"
1579 | +
1580 | +    def complete(self, prompt, max_tokens, seed, system=None):
1581 | +        key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
1582 | +        body = {"model": self.model, "max_output_tokens": max_tokens,
1583 | +                "input": [{"role": "system", "content": system or "Answer with one JSON object only."},
1584 | +                          {"role": "user", "content": prompt}],
1585 | +                "tools": [{"type": t} for t in self.spec.get("tools", ("x_search", "web_search"))]}
1586 | +        t0 = time.time()
1587 | +        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout),
1588 | +                          final_codes=(401, 402, 403))
1589 | +        text = j.get("output_text") or ""
1590 | +        if not text:
1591 | +            for item in j.get("output") or []:
1592 | +                for part in (item.get("content") or []) if isinstance(item, dict) else []:
1593 | +                    if isinstance(part, dict) and part.get("type") in ("output_text", "text"):
1594 | +                        text += part.get("text") or ""
1595 | +        u = j.get("usage") or {}
1596 | +        return text, {"in": int(u.get("input_tokens") or u.get("prompt_tokens") or 0),
1597 | +                      "out": int(u.get("output_tokens") or u.get("completion_tokens") or 0)}, time.time() - t0
1598 | +
1599 | +
1600 | +# ── transcription back-ends (law L-v 2's second recognition pass; role "transcribe") ──
1601 | +
1602 | +def _multipart(fields, file_field, path, content_type="audio/wav"):
1603 | +    boundary = uuid.uuid4().hex
1604 | +    body = b"".join(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
1605 | +                    for k, v in fields.items())
1606 | +    with open(path, "rb") as f:
1607 | +        data = f.read()
1608 | +    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
1609 | +             f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: {content_type}\r\n\r\n").encode() + data + \
1610 | +        f"\r\n--{boundary}--\r\n".encode()
1611 | +    return body, f"multipart/form-data; boundary={boundary}"
1612 | +
1613 | +
1614 | +def _wav_seconds(path):
1615 | +    import wave
1616 | +    try:
1617 | +        with wave.open(path) as w:
1618 | +            return w.getnframes() / float(w.getframerate())
1619 | +    except (wave.Error, OSError, EOFError):
1620 | +        return 600.0                                   # not measurable: priced as ten minutes (an upper bound)
1621 | +
1622 | +
1623 | +def _sha_file(path):
1624 | +    h = hashlib.sha256()
1625 | +    with open(path, "rb") as f:
1626 | +        for chunk in iter(lambda: f.read(1 << 20), b""):
1627 | +            h.update(chunk)
1628 | +    return h.hexdigest()
1629 | +
1630 | +
1631 | +class STTBackend(Backend):
1632 | +    """A transcription back-end: transcribe(wav) -> ({"text", "segments": [{"speaker", "start", "end", "text"}]},
1633 | +    seconds), times in seconds from the start of the audio. Priced per minute of audio (price_usd_per_min)."""
1634 | +
1635 | +    def usd(self, usage):
1636 | +        return round(float(usage.get("seconds", 0.0)) / 60.0 * float(self.spec.get("price_usd_per_min", 0.0)), 6)
1637 | +
1638 | +    def free(self):
1639 | +        return not float(self.spec.get("price_usd_per_min", 0.0))
1640 | +
1641 | +    def upper_usd(self, wav, max_tokens=0, system=None):
1642 | +        return self.usd({"seconds": _wav_seconds(wav) + 5.0})
1643 | +
1644 | +    def _post(self, url, body, headers):
1645 | +        req = urllib.request.Request(url, data=body, headers=headers)
1646 | +        return json.loads(urllib.request.urlopen(req, timeout=self.timeout).read())
1647 | +
1648 | +    def transcribe(self, wav):
1649 | +        raise NotImplementedError
1650 | +
1651 | +
1652 | +class OpenAITranscribe(STTBackend):
1653 | +    """OpenAI's transcription API (diarised JSON when the config says diarize)."""
1654 | +    vendor = "openai"
1655 | +    URL = "https://api.openai.com/v1/audio/transcriptions"
1656 | +
1657 | +    def transcribe(self, wav):
1658 | +        key = self.key("OPENAI_API_KEY")
1659 | +        fields = {"model": self.model, "response_format": "diarized_json" if self.spec.get("diarize") else "json"}
1660 | +        if self.spec.get("diarize"):
1661 | +            fields["chunking_strategy"] = "auto"
1662 | +        body, ctype = _multipart(fields, "file", wav)
1663 | +        t0 = time.time()
1664 | +        d = _with_backoff(lambda: self._post(self.URL, body, {"Authorization": "Bearer " + key, "Content-Type": ctype}),
1665 | +                          final_codes=(401, 402, 403))
1666 | +        segs = [{"speaker": s.get("speaker"), "start": s.get("start"), "end": s.get("end"), "text": s.get("text") or ""}
1667 | +                for s in d.get("segments") or [] if isinstance(s, dict)]
1668 | +        return {"text": d.get("text") or " ".join(s["text"] for s in segs), "segments": segs}, time.time() - t0
1669 | +
1670 | +
1671 | +class ElevenLabsTranscribe(STTBackend):
1672 | +    """ElevenLabs speech-to-text with diarisation: word timings with speaker ids, grouped into speaker runs."""
1673 | +    vendor = "elevenlabs"
1674 | +    URL = "https://api.elevenlabs.io/v1/speech-to-text"
1675 | +
1676 | +    def transcribe(self, wav):
1677 | +        key = self.key("ELEVENLABS_API_KEY")
1678 | +        body, ctype = _multipart({"model_id": self.model, "diarize": "true", "timestamps_granularity": "word",
1679 | +                                  "tag_audio_events": "false"}, "file", wav)
1680 | +        t0 = time.time()
1681 | +        d = _with_backoff(lambda: self._post(self.URL, body, {"xi-api-key": key, "Content-Type": ctype}),
1682 | +                          final_codes=(401, 402, 403))
1683 | +        segs, words = [], []
1684 | +        for w in d.get("words") or []:
1685 | +            if not isinstance(w, dict) or w.get("type", "word") != "word":
1686 | +                continue
1687 | +            words.append({"text": w.get("text") or "", "start": w.get("start"), "end": w.get("end"),
1688 | +                          "speaker": w.get("speaker_id")})
1689 | +            if segs and segs[-1]["speaker"] == w.get("speaker_id"):
1690 | +                segs[-1]["end"] = w.get("end")
1691 | +                segs[-1]["text"] += " " + (w.get("text") or "")
1692 | +            else:
1693 | +                segs.append({"speaker": w.get("speaker_id"), "start": w.get("start"), "end": w.get("end"),
1694 | +                             "text": w.get("text") or ""})
1695 | +        return {"text": d.get("text") or " ".join(s["text"] for s in segs), "segments": segs, "words": words}, \
1696 | +            time.time() - t0
1697 | +
1698 | +
1699 | +VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
1700 | +           "anthropic": AnthropicBackend, "openai_stt": OpenAITranscribe, "elevenlabs_stt": ElevenLabsTranscribe}
1701 | +
1702 | +
1703 | +def _as_set(x):
1704 | +    if not x:
1705 | +        return frozenset()
1706 | +    return frozenset(v for v in x if v) if isinstance(x, (set, frozenset, list, tuple)) else frozenset([x])
1707 | +
1708 | +
1709 | +# ── the router ──
1710 | +
1711 | +class Router:
1712 | +    """Role -> back-end chain from the config. call() tries the chain in order (skipping back-ends this run already
1713 | +    found unavailable, and any on avoid_vendor), records every exchange when record_dir is set, prices it into the
1714 | +    spend ledger, and returns a Reply naming the back-end that answered. replay=True serves recorded exchanges only."""
1715 | +
1716 | +    def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
1717 | +                 local_llm=None, chains=None):
1718 | +        with open(config) as f:
1719 | +            self.config = json.load(f)
1720 | +        self.env_path = env_path or ENV_PATH
1721 | +        self.record_dir, self.replay, self.spend_path, self.limit_usd = record_dir, replay, spend_path, limit_usd
1722 | +        self.down, self.notices = {}, []
1723 | +        self.backends = {}
1724 | +        for name, spec in self.config["backends"].items():
1725 | +            cls = VENDORS[spec["vendor"]]
1726 | +            self.backends[name] = cls(name, spec, self.env_path, local_llm) if cls is LocalBackend else \
1727 | +                cls(name, spec, self.env_path)
1728 | +        self.chains = dict(chains or {})          # tests / the A/B harness may pin a role's chain (still by config name)
1729 | +
1730 | +    def chain(self, role):
1731 | +        if role in self.chains:
1732 | +            return list(self.chains[role])
1733 | +        try:
1734 | +            return list(self.config["roles"][role]["chain"])
1735 | +        except KeyError:
1736 | +            raise ProviderError(f"role {role!r} has no chain in {os.path.basename(CONFIG)}") from None
1737 | +
1738 | +    # recording
1739 | +    def _path(self, role, backend, prompt, max_tokens, seed, system):
1740 | +        k = hashlib.sha256(json.dumps([role, backend, prompt, max_tokens, seed, system or ""]).encode()).hexdigest()
1741 | +        return os.path.join(self.record_dir, k[:2], k + ".json")
1742 | +
1743 | +    # the spend ledger: reserve the upper bound before a paid call, settle after (fail closed)
1744 | +    def _lock(self):
1745 | +        import fcntl
1746 | +        os.makedirs(os.path.dirname(os.path.abspath(self.spend_path)), exist_ok=True)
1747 | +        lk = open(self.spend_path + ".lock", "w")
1748 | +        fcntl.flock(lk, fcntl.LOCK_EX)
1749 | +        return lk
1750 | +
1751 | +    def _ledger(self):
1752 | +        """The ledger (a missing file is an empty one). An unreadable ledger is a SpendLimit: no paid call runs on a
1753 | +        spend total nobody can read (fail closed). Reservations of processes that are gone are released."""
1754 | +        if not os.path.exists(self.spend_path):
1755 | +            return {"usd_estimate": 0.0, "calls": 0, "by_backend": {}, "by_role": {}, "reserved": {}}
1756 | +        try:
1757 | +            with open(self.spend_path) as f:
1758 | +                d = json.load(f)
1759 | +            if not isinstance(d, dict) or not isinstance(d.get("usd_estimate", 0.0), (int, float)):
1760 | +                raise ValueError("not a ledger")
1761 | +        except (OSError, ValueError) as e:
1762 | +            raise SpendLimit(f"the spend ledger {self.spend_path} is unreadable ({type(e).__name__}): no paid call "
1763 | +                             "until it is repaired") from None
1764 | +        for k, v in (("calls", 0), ("by_backend", {}), ("by_role", {}), ("reserved", {})):
1765 | +            d.setdefault(k, v)
1766 | +        live = {}
1767 | +        for k, v in d["reserved"].items():
1768 | +            try:
1769 | +                os.kill(int(str(k).split(":")[0]), 0)
1770 | +                live[k] = v
1771 | +            except PermissionError:
1772 | +                live[k] = v                            # another user's live process
1773 | +            except (ValueError, ProcessLookupError, OSError):
1774 | +                pass
1775 | +        d["reserved"] = live
1776 | +        return d
1777 | +
1778 | +    def _save(self, d):
1779 | +        tmp = f"{self.spend_path}.{os.getpid()}.tmp"
1780 | +        with open(tmp, "w") as f:
1781 | +            json.dump(d, f, indent=1)
1782 | +        os.replace(tmp, self.spend_path)
1783 | +
1784 | +    def _spent(self):
1785 | +        """The ledger's total (raises SpendLimit when it cannot be read)."""
1786 | +        if not self.spend_path:
1787 | +            return 0.0
1788 | +        with self._lock():
1789 | +            return float(self._ledger()["usd_estimate"])
1790 | +
1791 | +    def _reserve(self, b, upper):
1792 | +        """Reserve a paid call's upper bound -> a reservation key (None for a free back-end or no ledger); raises
1793 | +        SpendLimit when spent + reserved + this call's upper bound would pass the limit."""
1794 | +        if not self.spend_path or b.free():
1795 | +            return None
1796 | +        with self._lock():
1797 | +            d = self._ledger()
1798 | +            held = sum(float(x) for x in d["reserved"].values())
1799 | +            if d["usd_estimate"] + held + upper > self.limit_usd:
1800 | +                raise SpendLimit(f"spend estimate {d['usd_estimate']:.2f} USD + reserved {held:.2f} + this call's upper "
1801 | +                                 f"bound {upper:.2f} > the limit {self.limit_usd} USD")
1802 | +            key = f"{os.getpid()}:{uuid.uuid4().hex[:10]}"
1803 | +            d["reserved"][key] = round(upper, 6)
1804 | +            self._save(d)
1805 | +        return key
1806 | +
1807 | +    def _settle(self, key, backend=None, usage=None, usd=0.0, role=""):
1808 | +        """Release a reservation and account the call that answered (a free one too, when the ledger is readable)."""
1809 | +        if not self.spend_path or (key is None and backend is None):
1810 | +            return
1811 | +        with self._lock():
1812 | +            try:
1813 | +                d = self._ledger()
1814 | +            except SpendLimit:
1815 | +                if key is None:
1816 | +                    return                             # a free call: nothing to guard, nothing to write
1817 | +                raise
1818 | +            d["reserved"].pop(key, None)
1819 | +            if backend is not None:
1820 | +                usage = usage or {}
1821 | +                b = d["by_backend"].setdefault(backend.name, {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0,
1822 | +                                                              "price_usd_per_1m": list(backend.price)})
1823 | +                b.update(calls=b["calls"] + 1, usd_estimate=round(b["usd_estimate"] + usd, 6),
1824 | +                         **{"in": b["in"] + int(usage.get("in", 0)), "out": b["out"] + int(usage.get("out", 0))})
1825 | +                if usage.get("seconds"):
1826 | +                    b["audio_s"] = round(b.get("audio_s", 0.0) + float(usage["seconds"]), 2)
1827 | +                r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
1828 | +                r.update(calls=r["calls"] + 1, usd_estimate=round(r["usd_estimate"] + usd, 6))
1829 | +                d.update(calls=d["calls"] + 1, usd_estimate=round(d["usd_estimate"] + usd, 6))
1830 | +            self._save(d)
1831 | +
1832 | +    def reject(self, reply, why=""):
1833 | +        """The caller found this reply out of its contract: drop its recording, so the exchange is asked again next
1834 | +        time instead of served again (fable C1 U1). Offline replay keeps its recordings. -> True if one was dropped."""
1835 | +        if self.replay or reply is None or not getattr(reply, "record_path", ""):
1836 | +            return False
1837 | +        try:
1838 | +            os.remove(reply.record_path)
1839 | +            return True
1840 | +        except OSError:
1841 | +            return False
1842 | +
1843 | +    def heimdall_tripwire(self, at=0.9):
1844 | +        """NOTIFY when Heimdall's account usage reaches `at` of its credits (PBX 02:45: never a halt)."""
1845 | +        h = next((b for b in self.backends.values() if isinstance(b, HeimdallBackend)), None)
1846 | +        got = h.credits() if h else None
1847 | +        if got and got[1] > 0 and got[0] / got[1] >= at:
1848 | +            msg = f"HEIMDALL SPEND AT {int(at * 100)}%: {got[0]:.2f} of {got[1]:.2f} USD"
1849 | +            if msg not in self.notices:
1850 | +                self.notices.append(msg)
1851 | +            return msg
1852 | +        return None
1853 | +
1854 | +    def _skip(self, name, b, av, am, af):
1855 | +        """Why this back-end may not answer this call, or None."""
1856 | +        if b is None:
1857 | +            return "not in config backends"
1858 | +        if b.vendor in av:
1859 | +            return f"same vendor as the text it judges ({b.vendor}): skipped"
1860 | +        if name in am:
1861 | +            return "same model as the generator: skipped"
1862 | +        if b.family in af:
1863 | +            return f"same model family as the generator ({b.family}): skipped"
1864 | +        if name in self.down:
1865 | +            return f"down this run: {self.down[name]}"
1866 | +        return None
1867 | +
1868 | +    def _record(self, path, rec):
1869 | +        import threading
1870 | +        os.makedirs(os.path.dirname(path), exist_ok=True)
1871 | +        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"      # the gates call concurrently (05:25 item 5)
1872 | +        with open(tmp, "w") as f:
1873 | +            json.dump(dict(rec, recorded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), f, indent=1)
1874 | +        os.replace(tmp, path)
1875 | +
1876 | +    def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
1877 | +             avoid_family=None):
1878 | +        av, am, af = _as_set(avoid_vendor), _as_set(avoid_model), _as_set(avoid_family)
1879 | +        tried, notices = [], []
1880 | +        for name in self.chain(role):
1881 | +            b = self.backends.get(name)
1882 | +            why = self._skip(name, b, av, am, af)
1883 | +            if why is None and isinstance(b, STTBackend):
1884 | +                why = "a transcription back-end (Router.transcribe)"
1885 | +            if why:
1886 | +                tried.append((name, why))
1887 | +                continue
1888 | +            path = self._path(role, name, prompt, max_tokens, seed, system) if self.record_dir else None
1889 | +            if path and os.path.exists(path):
1890 | +                with open(path) as f:
1891 | +                    rec = json.load(f)
1892 | +                return Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
1893 | +                             rec.get("usd", 0.0), self.replay, tried, notices, b.family, not self.replay, path)
1894 | +            if self.replay:
1895 | +                tried.append((name, "replay: not recorded"))
1896 | +                continue
1897 | +            key = self._reserve(b, b.upper_usd(prompt, max_tokens, system))
1898 | +            if b.vendor == "heimdall":
1899 | +                n = self.heimdall_tripwire()
1900 | +                if n:
1901 | +                    notices.append(n)
1902 | +            try:
1903 | +                text, usage, secs = b.complete(prompt, max_tokens, seed, system)
1904 | +            except RequestRejected as e:
1905 | +                self._settle(key)
1906 | +                tried.append((name, f"refused this request: {e}"))
1907 | +                continue
1908 | +            except Unavailable as e:
1909 | +                self._settle(key)
1910 | +                self.down[name] = str(e)
1911 | +                tried.append((name, str(e)))
1912 | +                continue
1913 | +            except BaseException:
1914 | +                self._settle(key)
1915 | +                raise
1916 | +            usd = b.usd(usage)
1917 | +            self._settle(key, b, usage, usd, role)
1918 | +            recorded = ""
1919 | +            if path and isinstance(text, str) and text.strip():
1920 | +                self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
1921 | +                                    "max_tokens": max_tokens, "system": system, "prompt": prompt, "text": text,
1922 | +                                    "usage": usage, "usd": usd, "seconds": round(secs, 2)})
1923 | +                recorded = path
1924 | +            return Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
1925 | +                         recorded)
1926 | +        if self.replay:
1927 | +            raise ReplayMiss(f"{role}: no recorded exchange ({tried})")
1928 | +        raise ProviderError(f"{role}: every back-end unavailable: {tried}")
1929 | +
1930 | +    def transcribe(self, role, wav):
1931 | +        """The role's TRANSCRIPTION chain on one audio file (law L-v 2) -> (result, Reply naming the back-end); the
1932 | +        same down / record / replay / spend rules as call(). Recorded by the audio's sha256."""
1933 | +        tried = []
1934 | +        audio = _sha_file(wav)
1935 | +        for name in self.chain(role):
1936 | +            b = self.backends.get(name)
1937 | +            why = self._skip(name, b, frozenset(), frozenset(), frozenset())
1938 | +            if why is None and not isinstance(b, STTBackend):
1939 | +                why = "not a transcription back-end"
1940 | +            if why:
1941 | +                tried.append((name, why))
1942 | +                continue
1943 | +            path = self._path(role, name, "audio:" + audio, 0, 0, None) if self.record_dir else None
1944 | +            if path and os.path.exists(path):
1945 | +                with open(path) as f:
1946 | +                    rec = json.load(f)
1947 | +                return rec["result"], Reply(json.dumps(rec["result"]), name, b.vendor, rec.get("seconds", 0.0),
1948 | +                                            rec.get("usage") or {}, rec.get("usd", 0.0), self.replay, tried, [],
1949 | +                                            b.family, not self.replay, path)
1950 | +            if self.replay:
1951 | +                tried.append((name, "replay: not recorded"))
1952 | +                continue
1953 | +            key = self._reserve(b, b.upper_usd(wav))
1954 | +            try:
1955 | +                result, secs = b.transcribe(wav)
1956 | +            except RequestRejected as e:
1957 | +                self._settle(key)
1958 | +                tried.append((name, f"refused this request: {e}"))
1959 | +                continue
1960 | +            except Unavailable as e:
1961 | +                self._settle(key)
1962 | +                self.down[name] = str(e)
1963 | +                tried.append((name, str(e)))
1964 | +                continue
1965 | +            except BaseException:
1966 | +                self._settle(key)
1967 | +                raise
1968 | +            usage = {"seconds": round(_wav_seconds(wav), 2)}
1969 | +            usd = b.usd(usage)
1970 | +            self._settle(key, b, usage, usd, role)
1971 | +            recorded = ""
1972 | +            if path:
1973 | +                self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor,
1974 | +                                    "audio_sha256": audio, "result": result, "usage": usage, "usd": usd,
1975 | +                                    "seconds": round(secs, 2)})
1976 | +                recorded = path
1977 | +            return result, Reply(json.dumps(result), name, b.vendor, round(secs, 2), usage, usd, False, tried, [],
1978 | +                                 b.family, False, recorded)
1979 | +        if self.replay:
1980 | +            raise ReplayMiss(f"{role}: no recorded transcription ({tried})")
1981 | +        raise ProviderError(f"{role}: every transcription back-end unavailable: {tried}")
1982 | +
1983 | +
1984 | +class RoleModel:
1985 | +    """A select_by_id.Model over a role (law L-x for the story-first selector, REQUESTS R6 item 7): complete() ->
1986 | +    (text, meta) with the answering back-end in meta; ProviderError becomes select_by_id.ModelError."""
1987 | +
1988 | +    def __init__(self, router, role, avoid_vendor=None):
1989 | +        self.router, self.role, self.avoid_vendor = router, role, avoid_vendor
1990 | +        self.name = f"role:{role}"
1991 | +
1992 | +    def complete(self, prompt, max_tokens, seed):
1993 | +        import select_by_id as SB
1994 | +        try:
1995 | +            r = self.router.call(self.role, prompt, max_tokens, seed, avoid_vendor=self.avoid_vendor)
1996 | +        except ProviderError as e:
1997 | +            raise SB.ModelError(str(e)[:300]) from None
1998 | +        except ReplayMiss as e:
1999 | +            raise SB.ReplayMiss(str(e)[:300]) from None
2000 | +        except SpendLimit as e:
2001 | +            raise SB.SpendLimit(str(e)) from None
2002 | +        return r.text, {"backend": r.backend, "vendor": r.vendor, "usd": r.usd, "replayed": r.replayed,
2003 | +                        "tried": r.tried}
2004 | 
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
