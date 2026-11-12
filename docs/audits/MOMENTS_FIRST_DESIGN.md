# MOMENTS FIRST, THEN PACKAGE — design (pp-selectid phase 2, 2026-11-12)

Orders and laws:
- Orchestrator phase-2 order (01:55 ET Nov 12) and its addition (trend brief; "vo check needs to be real 100%").
- Orchestrator notes 02:00 (model roles), 02:30 (laws L-s..L-w), 02:35 (PBX decisions), 02:45 (law L-x) and 03:00
  (exam by pipeline_pp_tests; yield against the oracle).
- Orchestrator review 03:40 (angle first), decisions 05:25 / 05:30 (the VO classification A / B / C / D, the no-paraphrase
  styles, budgets), 05:35 / 06:00 / 06:22 (tonight's package; rulings 3-6).
- The phase-2 audit, cycle 1 (docs/audits/parallel/pp-selectid_audit_p2/C1_CONSENSUS.md).
- Laws L-n, L-o (amended), L-p, L-q, L-r (PIPELINE_LAWS.md).

New modules only:
- pipeline/providers.py and model_providers.json;
- pipeline/trend_brief.py, moments.py, package.py, vo_fidelity.py, context_integrity.py;
- pipeline/moments_gate_adapter.py (the exam adapter).

No existing pipeline file is edited. The wiring is an exact patch in docs/audits/parallel/pp-selectid_REQUESTS.md (R7).

## 1. The cycle

```
ingest (pipeline_pp_ingest: new uploads -> store -> word pass)            -> moment ledger (append-only, pp.moment/1)
trend_brief: local_baseline (free) + one live-search call (SHADOW, weight 0)
moments.mine: pre-filter (code) -> one batched mining pass by id (role "mine") -> eligibility per moment -> rank (code)
package.build: usable (code) -> step A once per moment (stored) -> ANGLES (role angle_write)
               -> per angle: line-up (code, runtime + R4) -> exclusion + L-v 2 start in the background
               -> write (host style, then quote-led) -> cheap gates (code) -> fidelity verdict || context B0 / B / C
               -> coherence -> sealed gate inventory -> pp.package/1 -> package_pin -> MOMENTS_PIN.json
integrator: pinned path (R7) -> word pass -> sentence lock -> render -> gates -> release authorisation over BOTH files
            + the title + caption (L-t) -> Telegram REVIEW ONLY (first one)
```

## 2. Provider interface (law L-x)

- Every role calls `providers.Router.call(role, prompt, ...)`; transcription calls `Router.transcribe(role, wav)`. The
  chain of back-ends per role lives only in pipeline/model_providers.json, as does every model name, model family,
  price and base URL.
- Back-ends:
  - local: gemma3:27b through story_semantics.LocalLLM; only with a started LocalLLM under the GPU0 lease, law L-r;
  - OpenAI chat/completions;
  - Anthropic Messages (streaming);
  - xAI chat/completions at temperature 0 with the attempt's seed;
  - xAI Responses with x_search / web_search (the trend brief);
  - Heimdall (OpenAI-compatible);
  - transcription: OpenAI diarised and ElevenLabs Scribe (role "transcribe", law L-v 2).
- **Unavailable** (credit, auth, 429 or 5xx after backoff, transport, no lease): the chain moves on and the back-end
  is down for the rest of the run. **RequestRejected** (400 / 413 / 422, over the local context, an empty reply): the
  chain moves on for THIS call only. A role whose whole chain fails raises ProviderError: a failed role, never a pass.
- Verdicts take `avoid_vendor` and `avoid_family`: the vendors and model families of EVERY reply whose text they judge
  (the angle and every writer attempt). Generator and judge are always different models.
- Every exchange is recorded by (role, back-end, prompt, max_tokens, seed, system), or by the audio's sha256. A recording
  served in a live run is `cached`; one served offline is `replayed`, and it is never deliverable (L-j).
  `Router.reject(reply)` deletes the recording of a reply its caller found out of contract, so it is asked again.
- Spend: each paid call RESERVES its upper bound (every prompt character a token + the output cap, at the config's
  upper-bound price) under the ledger lock BEFORE it runs, and settles after. An unreadable ledger stops every paid
  call. A free back-end is never stopped.
- Heimdall's GET /credits feeds the 90 % tripwire: a NOTIFY, never a halt (PBX 02:45).
- The order per role is in the config; the blind A/B per role (tests/providers/ab_roles.py, both judge orders, a judge
  outside the compared vendors and families) re-decides it. The integrator runs the local legs.

## 3. Mining (moments.py)

- Pre-filter (code): sources in the window (new since the last cycle plus a recent window); not opted out
  (pipeline/optout.json, PBX 02:35); eligible as a source. Rows are punctuated, injection-free, never an ad read, and
  within one sentence of a Bitcoin mention. Rows go round-robin across videos, on-screen-capable videos first, in
  context-budget tables.
- One batched pass: the model answers ids only, `{"moments": [{"range", "scores": 7 axes 0-5, "names_person",
  "risk", "topics", "reason"}]}`. The reply contract is strict and never repaired (L-l); anything else is re-asked.
  Each moment is then judged by eligibility on its own (a moment is its own statement).
- Ranking (code, L-u): hook_first_2s + quotable + surprising_fact + stance + stakes + stands_alone, minus 2 x
  contempt_outrage, minus soft-risk penalties, plus a trend weight that is 0 in SHADOW. Hard risks never rank.
- The miner's own risk flags are never the exclusion gate: `moments.exclusion_verdict` runs in production on every
  segment of a line-up, never on the miner's model (avoid_model), after a deterministic ad-read screen of the moment and
  the sentence before it (audit p2 C3).
- Durations come from word timing only. The `reason` is forensic only.

## 4. Packaging (package.py): angle first

The first package (03:25) passed every safety gate and failed the product (orchestrator 03:40). package.build is angle
first, inside the orchestrator's budgets (05:25 item 5, 05:30): at most 3 angles x 2 writes, stopped at the first
package with coherence >= 4; per package <= 6 minutes and <= $1.50 (tonight: 76-144 s and $0.25-0.59 per full gate run).

1. **usable** (code): on screen eligible (L-e); no hard exclusion (L-u); not overlapping a moment delivered in 24 h, by
   video and time (L-p, audit p2 U2); not opted out; <= 20 s per source video (L-u); time-sensitive words only from a
   source <= 24 h old (L-v 3); no MEASURED speaker change (an unmeasured one is a candidate; L-v 2 decides).
2. **Step A once per moment** (context only, package-independent), stored on the moment (a ledger keyed by moment and
   the step-A prompt), never recomputed; never on the writers' vendor or family.
3. **ANGLES** (role angle_write): up to 3 one-sentence angles, each backed by 3-8 cleared moments (the prompt asks for
   5-8) from >= 3 channels; an unknown id is rejected, never dropped. One re-ask on an out-of-contract reply.
4. **Line-up per angle** (code): the hook, then 2-3 clips from distinct channels in the proposer's order; at most one
   price prediction (L-u); a clip under 8 s only last (the punchline); the length that BOTH the runtime (60-70 s) and
   the moments R4 allow (section 4c). Exclusion and the L-v 2 second pass start in the background.
5. **Writer** (role angle_write), in the renderer's order (hook -> intro -> clip 1 -> bridge -> ...):
   - style "host" first: tease a clip with a question or topic, never saying what its speaker thinks; hand off with a
     hedge-matched attribution ONLY for a VERIFIED speaker; land the host's own takeaway after a clip;
   - style "quote" (quote-led) second: show + topic, at most four exact words quoted;
   - never a restatement of a clip's claim (DUPLICATE checks every line against every clip);
   - word budgets from R4 and the runtime; ONE title and ONE caption (L-t); the sign-off is code (L-a);
   - the plain VO ("Next, <show> on Bitcoin.") remains as the last resort, ranked below every written VO.
6. **Cheap gates first** (code, no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4. A failure goes back
   to the writer with the exact violations; no paid verdict is spent on it.
7. **Paid gates, concurrently**: the classifying fidelity verdict (section 5) and context integrity B0 / B / C (section
   6). A VO-dependent context failure goes back to the writer; any other context failure ends the angle.
8. **Exclusion and L-v 2** results are collected; a moment that fails either is dropped and the angle re-lined.
9. **COHERENCE** (blind, never the vendor / family of the text): the through-line, each clip 1-5, the VO's point 1-5.
   Below 4, or no through-line ('None.', 'n/a', under 4 words), moves to the next angle.
10. **The sealed gate inventory** (package.inventory; package_pin.REQUIRED_GATES): one row per hard gate, each exactly
    "PASS" with who measured it and "replayed": false. package_pin seals the gated bytes and the inventory
    (package_pin.seal) and refuses anything else (audit p2 C1).

## 4c. Length: the runtime and R4

- runtime = segments' word spans + every spoken VO word INCLUDING the sign-off at WPS + FIXED_S (audit p2 M4: the
  sign-off was subtracted twice, about 6.9 s short). FIXED_S = TAIL_S (14.30 s, measured) - an 18-word sign-off at WPS.
  WPS = 2.6 is an ASSUMPTION until a moments-first render measures it.
- R4 for moments (orchestrator 06:00 ruling 4; the integrator's edl_rules._r4_moments, main tree a5ec0f17): VO (intro
  + lines, words / 2.5 + 1 s pre-roll each) <= 40 % of the TOTAL runtime; one VO line per slot: after the hook, after
  each clip, after the last clip (the takeaway); word caps (intro 30, bridge 20). package.r4 mirrors it and
  package.content_range / budgets derive the line-up length and word budgets from it.

## 5. VO fidelity (vo_fidelity.py): "real 100%", and a host with a point of view

(a) Deterministic, on every VO line, the title and the caption, through canon (L-k):

| rule | what it checks |
|---|---|
| NEEDS_SOURCE | a line with a fact (a number that is not a production count, a name, a quote, an attribution, a time word) cites a segment |
| ATTRIBUTION | "<X> says / thinks ...", "<X>: ...", "according to <X>" bind X to a cited segment: by its VERIFIED speaker, or by its show; a person-like show with a speech verb needs the speaker verified (L-v 1); a pronoun or generic subject ("she says", "analysts say") is unbound |
| HEDGE | the attribution verb matches the clip's own hedge: "thinks" for "I think", "feels" for "I feel like" (05:25 item 2) |
| NUMBER | value and unit, in the sentences of the attribution that governs it (the nearest in its sentence), else the cited ones |
| NAME | every capitalised token that is not an English word (the system word list) is in the cited sentences or production metadata, wherever it stands (Title Case and sentence starts included) |
| QUOTE | double or single quotes, a verbatim run of the governing segment |
| RELATION | agree / answer / rebut / echo / goes further / similarly ... only when every party (cited segments, named shows, "both") is in one source video |
| FRAMING | destroys / slams / exposes / admits / confirms / caught / torches / debunks / bombshell ... only if the source says it |
| IMPERATIVE | no financial imperative or advice (you should buy, time to buy, don't sell); "short-term", "sell-off" are not verbs |
| TIME | today, overnight, this month, just hit / just set ... only if a cited segment says it (L-v 3) |
| PRICE_NOW | on ANY line, a price level is today's (a level the universe states as current, from present-tense sentences with no forecast or history word), or reads as history (a marker before it, no present tense), or as a forecast |

(b) The blind CLASSIFYING verdict (role fidelity_verdict, never the vendor or family of the text; 05:25 items 1-2):
every sentence of every line belongs to a claim whose `words` are the line's own, classified as
- **A attribution** / **B fact**: "yes" only with supports that are verbatim runs (>= 3 words) of the LINE'S OWN cited
  segments, same polarity and the same or weaker certainty; a named person only when the segment's speaker is
  verified;
- **C production**: supported by the manifest (the credited shows, the clip count, links below, the show and date);
- **D host commentary**: allowed without clip support when its five tests are all "no" (a checkable fact, a speaker's
  view or relation, a financial imperative or prediction, an accusation, sounding like a speaker), AND none of the rule
  features (a number, a name, a quote, an attribution, a price, a time word, an imperative, a relation or framing word)
  appears in its words; otherwise it is judged strict (NOT_COMMENTARY).
Code decides; an uncovered sentence (VERDICT_INCOMPLETE), "no", "uncertain" or an unverifiable support fails.

(c) The exam is pipeline_pp_tests'. The gate runs under its harness through pipeline/moments_gate_adapter.py; a gate
that could not MEASURE raises GateNotMeasured, the harness's ERROR (audit p2 M5), never a free rejection.

## 6. Context integrity (context_integrity.py, law L-s)

- Window per moment: AT LEAST 90 s before (back to the question it answers, when one ends within 180 s) and AT LEAST
  60 s after, in whole sentences (audit p2 C11). Every sentence is escaped and the selection marked after escaping;
  a window over 12,000 characters is CONTEXT_TOO_LONG, never cut.
- A (context only; package hidden): speaker change inside; the view; referents (inside, and whether resolving them
  differently changes the assertion); conditions; retraction (a withdrawal, reversal, correction or material limit, not
  a consistent elaboration: ruling 6); time_ok (no default); the proposition; certainty; who speaks ("host" verified
  only with verbatim evidence of the excerpt: L-v 1).
- B0 (the clips alone) and B (the package as the viewer meets it, in the renderer's order): what the viewer concludes
  each speaker asserts, INCLUDING what the title, caption or VO attributes to that speaker (host commentary attributed
  to nobody is the host's); certainty; polarity; a relation for EVERY pair of clips (audit p2 C5).
- C: entailment between A and the CLIP'S OWN WORDS as heard (ruling 5), same polarity, stronger certainty, with the
  words that justify a failure.
- PASS (code) only if all hold: no speaker change; own sincere; referents inside, or outside without changing the
  assertion (ruling 3); conditions inside; no retraction; certainty known; entailed; same polarity; no false relation;
  no "uncertain" anywhere. A failure that blames the video must quote the video's own words (`raising_words`,
  `added_by` naming the speaker's show); one that blames the context must quote the context's own words outside the
  clip (`dropped_limit`). Unquoted, it is a NOTE (rulings 3 and 5; E-FAIL-PS17). STRONGER is also a note when the clip
  alone already sounds certain.
- Repair is dropping the moment (the law also permits extending by whole locked sentences; not built). The VO never
  carries the missing context.
- After every change to these rules, the exam's context-integrity MUST-FAIL cases are re-run (tests/package/
  ci_mustfail_check.py): 41/41 rejected tonight after each ruling.

## 7. Trend brief (trend_brief.py)

- A closed taxonomy of 18 Bitcoin topics, each with our own label and pattern.
- `local_baseline`: the share of partner channels per topic in the last 24 h. Free.
- One live-search call per cycle (xAI Responses, x_search + web_search, < 6k out), cached per 4 h cycle.
  - The reply is validated into the taxonomy; strict.
  - Raw post text never leaves the module or enters a prompt.
  - Persons may boost only a moment whose VERIFIED speaker is that person.
  - Failure means no boost.
- SHADOW: TREND_WEIGHT = 0 until it measurably helps. When enabled, the weight is capped at ~10-15%.
- Titles never take trend phrasing (L-t).

## 8. Open items (named, not hidden)

- **The phase-2 code is under its audit's cycle 2** (cycle 1: C1_CONSENSUS.md, implemented). Until it passes, the code
  is not committed; tonight's package, its pin and its proof are.
- **The runtime estimate's WPS (2.6) and FIXED_S (7.4 s).** Assumptions until a moments-first render measures them.
- **Speaker verification (L-v 1)** rests on step A's "host" with verbatim evidence; diarisation (L-v 2) proves one
  speaker inside a clip, never who. Tonight no clip's speaker was verified, so no VO line names a person.
- **The exam's full run** (both directions, the false-reject rate on must-pass cases) waits for the Heimdall / local legs
  (orchestrator 05:30); the context-integrity must-fail half ran 41/41 after every ruling.
- **The yield sweep** of the other 9 universes is postponed (orchestrator 05:30).
- **The trend brief's search call** has never run; it is shadow and not on the critical path.

## 9. Measured so far (2026-11-12, saved universes; CPU and API only)

- **Mining, gpt-6.1-sol, word-timed sources** (the 10 saved universes): every call accepted at the first attempt.

| universe | moments mined | usable on screen |
|---|---|---|
| fresh_20261106_213852 | 12 | 9 |
| fresh_20261107_065702 | 12 | 11 |
| fresh_20261107_080503 | 12 | 10 |
| fresh_20261110_093150 | 24 | 16 |
| fresh_20261111_190259 | 71 | 62 |
| fresh_20261111_192645 | 70 | 65 |
| fresh_20261111_213954 | 69 | 61 |
| fresh_20261112_001448 | 59 | 52 |
| fresh_20261112_013452 | 59 | 54 |
| fresh_20261112_050611 (tonight) | 62 | 58 |

- **Mining A/B** (blind, judged by claude-opus-5-5, tests/providers/ab/mine_fresh_20261112_050611.json):

| back-end | calls accepted | latency | spend (upper bound) | blind verdict |
|---|---|---|---|---|
| gpt-6.1-sol | 6 / 6 | 300.5 s | $2.17 | better |
| Heimdall qwen3.8-27b | 5 / 6 | 2,067 s | $1.63 | worse |

  local gemma3:27b: the integrator's leg (GPU0 lease).
- **Law L-v 2 on tonight's first package**: the second pass (gpt-4o-transcribe-diarize) agreed on every number,
  name and negation of all 4 segments, with one speaker inside each.
- **Tonight's package** (fresh_20261112_050611; the orchestrator's 06:00 package with the line fixes of attempt 4,
  approved 06:22): every one of the 12 gates exactly PASS (attempt 9), pinned and sealed
  (tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json); 9 gate attempts, $3.46; the deployed factory's own
  R4 (moments) on its EDL: VO 30.93 % of an estimated 64.01 s.
- **Context integrity, the exam's 41 must-fail cases**, after each of rulings 3, 5 and 6: 41/41 rejected
  (tests/package/exam/ci_mustfail_*.json; claude-opus-5-5, about $0.01 a call).

