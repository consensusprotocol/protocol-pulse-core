# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1541
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 772 s finish=length usage in 27855 / out 24000 usd~0.444 (upper-bound price)

# AUDIT — pp-selectid, RULING 70 (pin-stage visual check)

Scope: only the diff shown. I reviewed it as the "new gate that looks at source video and seals its findings" reviewer. Where I could not verify something from the diff, I say so.

---

## P0 findings

**P0-1 — `visual_pin.sealed()` can seal a record whose `measured` is False; the pin then carries an unmeasured clip's "visual" as if it were evidence.**
`visual_pin.py:636-643` (`sealed`) copies whatever keys are present, including `"measured": False` + `"why"`, and `package.py:58-59` seals it whenever `m.get("visual")` is truthy — an unmeasured record `{"version", "measured": False, "why": ...}` is truthy. The gate row (package.py:209-215) does require `measured is True` for every clip, so the *gate* is honest; but the *seal* is not conditioned on it. Scenario: a clip's check fails twice (`visual_for` returns `measured: False` at visual_pin.py:680-681), the line-up is re-lined (package.py:175-182) — good — but the no-voice fallback path (package.py:148-156) returns `None` only when `vbad` is non-empty *at that point*; if the record was later overwritten... actually the fallback does check. The weaker case: `hook_block` at visual_pin.py:626-633 treats a record with `measured: True` but no `flags` key as clean (`rec.get("flags") or []`), and `sealed()` happily seals a `measured: True` record that never went through `check()` — e.g. the test rig's record (test_medley.py:760-765) has no `version`-keyed contract. This is a P1, not P0; I downgrade it. **No verified P0.** (I flag the *shape* of the risk: the gate row and the seal are computed independently, so a future caller that seals without the inventory row would silently pass. Today, from the diff, both paths are covered.)

**P0-2 — `out_visual["cached"/"calls"]` accounting is wrong for unmeasured replies.**
package.py:113: `out_visual["cached" if rec.get("cached") else "calls"] += 1 if rec.get("measured") else 0`. For an unmeasured record (`cached` falsy, `measured` falsy) it adds `0` to `calls` — so an unmeasured clip increments *neither* counter, but *does* increment `unmeasured`. That is consistent. However for a **cached** record, `visual_for` returns `dict(cache[k], cached=True, usd=0.0)` (visual_pin.py:653) — `cached=True` and `measured=True`, so it counts into `cached`. Fine. But note `visual_for` only writes to the cache when `not rec["replayed"]` (visual_pin.py:673-674) — a *replayed* (recorded, offline) verdict is measured, not cached, and is counted in `calls` with its `usd` (0.0 for a replay). Consistent, but the ruling's "Report the measured cost on the first build" is satisfied only because replays cost 0. **No defect verified;** the accounting is internally consistent. Downgraded to P2-1 below for the one case I *can* break.

---

## P1 findings

**P1-1 — `visual_for`'s failure return after a successful sheet loses the sheet's *path* consistency: the second-try failure return (visual_pin.py:680-681) references `path`, `sha`, `ts` — but if the *first* try raised inside `router.call`/`check`/`_json` while the second try also raised, `path`/`sha`/`ts` are bound from the successful `sheet()` call, fine. However if `fetch()` succeeded and `sheet()` raised, the except at :659-660 returns without a `sheet` key, and `sealed()` (visual_pin.py:641-642) then omits `sheet` — while `proof_ledger.py:701-706` guards with `sh.get("name")`. Consistent.** But: the *first* failure return (visual_pin.py:660) also has no `flags` key, and `hook_block` (visual_pin.py:630) reads `rec.get("flags") or []` — guarded. OK. **Real issue: the retry loop's `why` (visual_pin.py:679) keeps only the LAST failure's reason; the first try's reason is discarded.** Minor observability loss, not a correctness bug. P2.

**P1-2 — `check()` (visual_pin.py:595-612) does not bound `on_screen_text` length or `finding`/`why`/`text` string lengths.** A model reply with 500 chyron entries passes `check()`; `flags()` (visual_pin.py:621-623) then seals all of them into the pin. Not a correctness bug (fail-closed is preserved), but the pin body grows unboundedly and `seal()` hashes it — a later re-seal of the same pin is still deterministic, so no seal-compat issue. P2.

**P1-3 — Router: a *text* role can reach a vision back-end, and the vision back-end raises `RequestRejected` (providers.py:349-350).** The router's skip logic (providers.py:393-396) skips `XAIVisionBackend` for a text prompt ("a vision back-end (ruling 70)"), so within the router this cannot happen — *unless* a role's chain in `model_providers.json` lists `xai_vision:grok-4An7`... the diff only adds it to `visual_check`. Verified: the only role touched is `visual_check`, whose members are all vision-capable (Heimdall `vision = True` at :313, xAI at :341). **But note: `HeimdallBackend.vision = True` means a *text* role that includes a heimdall back-end now ge

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 51 s finish=stop usage in 27153 / out 488 usd~0.148 (upper-bound price)

**P0: None verifiable from diff.**  
**P1: None verifiable from diff.**  
**P2: pipeline/visual_pin.py:659 (and :676)**  
Broad `except Exception as e: # noqa: BLE001` on sheet/verdict paths (including router.call, check, JSON parse, PIL, ffmpeg). Matches style of surrounding providers.py changes but would mask unexpected failures (e.g. OOM on large sheet, router SpendLimit) as "not measured". Concrete: a transient Heimdall 429 on first try + bad JSON on retry seed+1 yields measured=False with generic why; no tighter exception list is present.  

**P2: pipeline/providers.py:275**  
`prompt_text` does `hashlib.sha256(i.encode())` on the *base64 string* (not decoded JPEG bytes). Recording/logs contain only the hex digest (test at :996 confirms image bytes never written). Verifiably unique per image for cache key but not a literal byte hash of the visual data sent to the model.  

**P2: pipeline/package.py:153 (and :175, :210)**  
`see(order)` / visual row requires *every* clip measured for PASS (and drops unmeasured before write or blocks hook). Matches ruling's "fail closed" and L-m/L-j but the visual gate is now in MEDLEY_GATES/REQUIRED_GATES for all new medleys; old pins untouched only because visual is in SEALED_LATER and check_pin_only still uses pre-ruling REQUIRED list (verified in updated test_medley.py:731 and test_no_voice).  

No other concrete violations of the supplied ruling text, K1–K4, or governing laws (sentence/selection/snap/edge/credits/L-a..L-l, release-on-bytes, one-canon, model-whole-reply, fail-closed, v2f byte-identical re-render) can be verified from the diff alone. Router vision/text separation, upper_usd image token charging, XAIVision/Heimdall request bodies, cache-per-span+VERSION, sealed() subset (no path/cost), hook_block on third_person, parallel see() before angle/write, and all 14 test cases match the described behavior exactly. Uncertain on router thread-safety under ThreadPoolExecutor(4) for concurrent visual calls (not shown in diff).  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 75 s finish=stop usage in 30772 / out 3597 usd~0.146 (upper-bound price)

I’ll audit the diff strictly against the stated laws and the RULING 70 requirements, focusing on the new visual gate, router changes, sealing, and cost accounting.

## P0 Findings

**1. `pipeline/package.py:113` — `out_visual["calls"]` / `out_visual["cached"]` accounting is wrong (undercounts, can misreport).**
- Concrete scenario: `see()` iterates `todo` and does:
  ```python
  out_visual["cached" if rec.get("cached") else "calls"] += 1 if rec.get("measured") else 0
  ```
  This only increments when `rec.get("measured")` is truthy. But `visual_for` returns a record with `measured: False` on failure (no sheet, out-of-contract twice). Those failures are *calls* (or at least attempts) that should be visible in the “calls”/“unmeasured” accounting, yet they are not counted in `calls`/`cached`. Meanwhile `out_visual["unmeasured"]` is incremented separately, so the total `calls + cached` will not equal the number of `see()` invocations, and the log line “{calls} sheet(s) judged, {cached} cached” is misleading: a failed call is neither “judged” nor “cached”, but it was still a paid/attempted call.
- Why it matters: RULING 70 says “Report the measured cost on the first build.” The `usd` field is updated correctly, but the call/cached counts are not a faithful record of what happened. This is a reporting defect in a new gate that is meant to be auditable.
- Fix: count every `todo` item as a call unless it was served from cache; e.g.
  ```python
  if rec.get("cached"):
      out_visual["cached"] += 1
  else:
      out_visual["calls"] += 1
  ```
  and keep `unmeasured` as a separate counter.

**2. `pipeline/visual_pin.py:673-674` — cache stores a record that may include `usd` and `usage`, but `sealed()` later strips them; however the cache key does not include the image bytes, only `moment_id:start-end:VERSION`.**
- Concrete scenario: Two different contact sheets for the same `moment_id` and same `start`/`end` (e.g. after a re-fetch of a different quality, or a change in `TILES`/`EVERY_S` that is not reflected in `VERSION`) would collide in the cache. The cache is keyed by `key(m)` which is `f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{VERSION}"`. The sheet’s `sha256` is not part of the key. If the sheet changes (different frames, different resolution, different labeling) but the moment and span are the same, the old verdict is returned as `cached=True` and the new sheet is never judged.
- Why it matters: Law L-m (fail closed) and the ruling’s “one contact sheet per clip” require that the verdict corresponds to the exact bytes the model saw. A stale cache entry violates this. The `VERSION` constant is `"visual-1"`, but it is not bumped when `TILES`, `EVERY_S`, `TILE_W`, or `FORMAT` change.
- Fix: include the sheet’s `sha256` in the cache key, or bump `VERSION` whenever any sheet-generation parameter changes. Better: key by `moment_id:start-end:VERSION:sheet_sha256`.

**3. `pipeline/providers.py:393-396` — router skip logic for vision prompts is asymmetric and can cause a vision prompt to be routed to a text-only backend if the chain is misconfigured.**
- Concrete scenario: The router skips a backend if `is_vision(prompt) and not b.vision`. But it also skips `XAIVisionBackend` if `not is_vision(prompt)`. This is correct. However, the `visual_check` chain in `model_providers.json` is:
  ```json
  ["xai_vision:grok-4.7", "heimdall:qwen/qwen3.8-27b", "heimdall:nvidia/nemotron-3.5-super-vl"]
  ```
  The `heimdall:qwen/qwen3.8-27b` backend is not defined in the diff (only `heimdall:nvidia/nemotron-3.5-super-vl` is added). If `heimdall:qwen/qwen3.8-27b` is a text-only Heimdall backend (i.e. `vision = False`), it will be skipped for vision prompts, which is correct. But if it is not defined at all, the router will raise an error or skip it. The diff does not show its definition, so I cannot verify it has `vision = True`. This is a potential fail-open: if the first backend (`xai_vision:grok-4.7`) fails and the second (`heimdall:qwen/qwen3.8-27b`) is not a vision backend, it is skipped, and the third (`heimdall:nvidia/nemotron-3.5-super-vl`) is tried. That is acceptable. But if the second backend is a vision backend that is not properly configured, it may fail. The key issue is that the diff does not define `heimdall:qwen/qwen3.8-27b`, so I cannot confirm it has `vision = True`.
- Why it matters: The ruling says “xAI first, Heimdall image models as failover.” If the failover chain is broken, the clip is not measured, which is fail-closed (good), but the cost and latency are wasted. More importantly, if a text-only backend is accidentally in the chain and not skipped, it would receive a vision prompt and fail, which is also fail-closed. The asymmetry is not a bug per se, but the missing definition is a gap.
- Fix: Ensure `heimdall:qwen/qwen3.8-27b` is defined with `vision = True` in `model_providers.jso

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1541 (RULING 70: the pin-stage visual check): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", no findings.
  - qwen: "SHIP: no", on four "P0"s.
  - glm: ran to its 24k-token limit; "No verified P0", with many P1s, most of them self-resolved in its own text.
- Two consensus items are applied before cycle 2.

## Applied

| # | finding | the change |
|---|---|---|
| C1 | The cache key (moment + span + VERSION) left out inputs the verdict depends on, so a stale verdict could be served (qwen P0-2; glm P1-5, P1-47, P1-77): a change to the clip's words, the prompt or the sheet's parameters without a VERSION bump, or other sheet bytes | key() adds a digest of [PROMPT, TILES, EVERY_S, TILE_W, FORMAT, the clip's words]. A hit is used only when the judged sheet is on disk with its judged sha256. Otherwise the sheet is rebuilt: the same bytes keep the verdict, other bytes are judged afresh. Tests: the same bytes are cached (no call); other bytes are re-judged (a call); other words give another key. |
| C2 | The visual accounting counted only measured attempts as calls (qwen P0-1; glm P0-2 / P2-1) | Every attempt that is not a cache hit counts as a call (asked), and "unmeasured" stays its own counter. The driver's line reads "N sheet(s) asked (U not measured), K cached, F flag(s); measured cost $...". |

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P0-3: heimdall:qwen/qwen3.8-27b is not defined, so the failover may not be a vision back-end | It is an existing backend of pipeline/model_providers.json ("heimdall:qwen/qwen3.8-27b", vendor heimdall, base_url set). This diff makes HeimdallBackend.vision = True (providers.py), and it is the model the render's pipeline/visual_check.py already sends images to (VISION_MODELS). test_providers' config test checks every chain member is a defined backend. |
| R2 | qwen P0-4: replacing '"' with "'" in the clip's words corrupts them | It only keeps the prompt's own double quotes balanced around the words. The model judges meaning and negativity; the quote mark's shape changes neither. The sealed approved_text is untouched. |
| R3 | qwen P1-5: two threads may judge the same key at once | see() hands visual_for each moment once (its todo list is the line-up's distinct moments, or the passing hooks). Moments already measured in this build are skipped, so one build never asks the same key twice. |
| R4 | qwen P1-9: visual_hook_block may be stale across builds | build() pops visual_hook_block from every cleared moment before it judges the hooks (package.py, right before rated_open), as glm's P1-8 verified. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | qwen P1-6, P1-7: download / ffmpeg timeouts | Each fails closed: not measured, then the clip is dropped or the hook blocked. A build that loses clips this way records why. |
| G2 | qwen P1-8, glm P1-4: the xai_vision output cap (8000 tokens) makes a $0.23 reservation per call

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1541/C2_STEP.diff (1065 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 8c184de..8ca333d 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -106,6 +106,29 @@
   6 |     ],
   7 |     "family": "grok"
   8 |    },
   9 | +  "xai_vision:grok-4.7": {
  10 | +   "vendor": "xai_vision",
  11 | +   "model": "grok-4.7",
  12 | +   "price_usd_per_1m": [
  13 | +    5,
  14 | +    25
  15 | +   ],
  16 | +   "temperature": 0,
  17 | +   "key_name": "XAI_API_KEY_MEDLEY",
  18 | +   "family": "grok"
  19 | +  },
  20 | +  "heimdall:nvidia/nemotron-3.5-super-vl": {
  21 | +   "vendor": "heimdall",
  22 | +   "model": "nvidia/nemotron-3.5-super-vl",
  23 | +   "price_usd_per_1m": [
  24 | +    3,
  25 | +    15
  26 | +   ],
  27 | +   "temperature": 0,
  28 | +   "min_out": 16000,
  29 | +   "family": "nemotron",
  30 | +   "base_url": "https://api-staging.heimdallm.com/api/v1"
  31 | +  },
  32 |    "openai_stt:gpt-4o-transcribe-diarize": {
  33 |     "vendor": "openai_stt",
  34 |     "model": "gpt-4o-transcribe-diarize",
  35 | @@ -221,6 +244,14 @@
  36 |     ],
  37 |     "what": "speakers.attribute: who speaks one pin segment, from the source's own title / channel / description and the transcript around the clip (orchestrator 00:05 ET Nov 13 item 3); code keeps only what the text shows"
  38 |    },
  39 | +  "visual_check": {
  40 | +   "chain": [
  41 | +    "xai_vision:grok-4.7",
  42 | +    "heimdall:qwen/qwen3.8-27b",
  43 | +    "heimdall:nvidia/nemotron-3.5-super-vl"
  44 | +   ],
  45 | +   "what": "RULING 70 (orchestrator 15:29 Nov 13): visual_pin.visual_for, one contact sheet per clip: a third person shown as a still while the words make a negative claim, the source's on-screen text that asserts more than the words, the lower third; xAI first, the Heimdall image models (pipeline/visual_check.py's) as failover; fail closed"
  46 | +  },
  47 |    "transcribe": {
  48 |     "chain": [
  49 |      "openai_stt:gpt-4o-transcribe-diarize",
  50 | diff --git a/pipeline/package.py b/pipeline/package.py
  51 | index 978628c..ce8c6e4 100644
  52 | --- a/pipeline/package.py
  53 | +++ b/pipeline/package.py
  54 | @@ -329,6 +329,8 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
  55 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s",
  56 |                          **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"]}
  57 |                             if m.get("trimmed_leading") else {}),
  58 | +                        **({"visual": __import__("visual_pin").sealed(m["visual"])}    # ruling 70: sealed
  59 | +                           if m.get("visual") else {}),
  60 |                          **({"scorer_verdict": verdict_of(m)}  # ruling 56: "seal only what it affirms" (the pin
  61 |                             if (verdict_of(m) or {}).get("affirmed") is True else {})}   # refuses any other)
  62 |                         for lb, m in zip(labels(len(segs)), segs)],
  63 | @@ -1151,6 +1153,12 @@ def hook_own(m):
  64 |  
  65 |  
  66 |  def can_open(m):
  67 | +    if m.get("visual_hook_block"):                       # RULING 70: its picture may not open the medley
  68 | +        return False
  69 | +    return _can_open(m)
  70 | +
  71 | +
  72 | +def _can_open(m):
  73 |      """Whether a moment may OPEN a line-up: hook-eligible, its hook onset measured and passed (G17a), a first word the
  74 |      render's STAND_ALONE takes for a hook (stand_alone.opener), and, once the build has rated the pool's hooks (RULING
  75 |      59: build() sets "hook_rating" on every cleared moment before any line-up), rated >= HOOK_MIN on the hook's own job
  76 | @@ -2024,7 +2032,8 @@ def candidate_lineup(router, candidate, cleared, now):
  77 |  
  78 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  79 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  80 | -          hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None):
  81 | +          hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  82 | +          visual_cache=None):
  83 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  84 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  85 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  86 | @@ -2039,6 +2048,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  87 |      ('no hook in the pool', the three best listed) before the second screen, the angles and any line-up. The angle
  88 |      writer is given THE HOOKS and writes each angle FOR one; the angles are tried best hook first (ruling 57's
  89 |      freshness next), each line-up opens on its angle's own hook and never swaps it.
  90 | +    RULING 70, THE VISUAL CHECK (visual_pin): every hook rated >= HOOK_MIN is seen right after the ratings, before any
  91 | +    angle is asked (a hook whose sheet shows a third person while its words make a negative claim, or that is not
  92 | +    measured, may not open: can_open); every clip of a line-up that passes the clips-alone verdict is seen before any
  93 | +    write (not measured: dropped and re-lined, law L-m). Findings are sealed as FLAGS on the segment, never a reject by
  94 | +    themselves; the "visual" row is required (package_pin.MEDLEY_GATES). visual_cache: the verdicts by moment and span.
  95 |      RULING 66, A PASSED LINE-UP IS KEPT: candidate (load_candidate) tries ONLY that line-up, after the same pool stages:
  96 |      no angle is asked for (its own angle and back-end), its clips must still form it (candidate_lineup), and it is
  97 |      judged and written with its own seeds, so its recorded calls are served from their recordings; it is never
  98 | @@ -2049,6 +2063,22 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  99 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 100 |      t0 = time.time()
 101 |      usd0 = _spent(spend)
 102 | +    import visual_pin as VP                            # ruling 70
 103 | +    vcache = VP.load_cache(visual_cache) if visual_cache else {}
 104 | +    out_visual = {"calls": 0, "cached": 0, "usd": 0.0, "unmeasured": 0, "flags": 0}
 105 | +
 106 | +    def see(ms_):                                      # RULING 70: the clips' sheets, judged (cached per moment)
 107 | +        todo = [m for m in ms_ if not (m.get("visual") or {}).get("measured")]
 108 | +        if todo:
 109 | +            with ThreadPoolExecutor(max_workers=4) as vp:
 110 | +                recs = list(vp.map(lambda m: VP.visual_for(router, m, work_dir, vcache), todo))
 111 | +            for m, rec in zip(todo, recs):
 112 | +                m["visual"] = rec
 113 | +                out_visual["cached" if rec.get("cached") else "calls"] += 1     # audit 1541 C1: every attempt
 114 | +                out_visual["usd"] = round(out_visual["usd"] + float(rec.get("usd") or 0.0), 6)
 115 | +                out_visual["unmeasured"] += 0 if rec.get("measured") else 1
 116 | +                out_visual["flags"] += len(rec.get("flags") or [])
 117 | +            VP.save_cache(visual_cache, vcache)
 118 |      ms, why = usable(moments, ctx, delivered, optout)
 119 |      n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
 120 |      ms, reposted = reposted_once(ms, sources)          # ruling 53: a speech re-posted by a second channel is ONE
 121 | @@ -2134,10 +2164,25 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 122 |          m["hook_rating"] = rated.get(mid) or {"rating": None, "why": (f"not rated: {hook_err}" if mid in openers else
 123 |                                                                        "cannot open (hook eligibility, G17a or the "
 124 |                                                                        "render's hook rule)")}
 125 | +    for m in cleared.values():
 126 | +        m.pop("visual_hook_block", None)
 127 | +    rated_open = [m for m in cleared.values() if can_open(m)]              # RULING 70: the hooks that would open,
 128 | +    see(rated_open)                                                          # seen before any angle is asked
 129 | +    blocked = {}
 130 | +    for m in rated_open:
 131 | +        why_v = VP.hook_block(m["visual"])
 132 | +        if why_v:
 133 | +            m["visual_hook_block"] = blocked[m["moment_id"]] = why_v
 134 | +    out["visual"] = out_visual
 135 | +    if rated_open:
 136 | +        log(f"  visual (ruling 70): {len(rated_open)} hook(s) seen, {len(blocked)} may not open"
 137 | +            + (f" ({'; '.join(f'{k}: {v[:90]}' for k, v in blocked.items())})" if blocked else "")
 138 | +            + f" ({time.time() - t0:.0f} s)")
 139 |      best = [hook_line(m, ctx) for m in hook_order([m for mid, m in openers.items() if mid in rated])[:3]]
 140 |      out["hook_pool"] = {"can_open": len(openers), "rated": len(rated), "error": hook_err, "min": HOOK_MIN,
 141 |                          "ratings": {mid: rated[mid] for mid in sorted(rated)}, "best": best,
 142 | -                        "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])]}
 143 | +                        "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])],
 144 | +                        "visual_blocked": blocked}
 145 |      log(f"  hooks (ruling 59): {len(openers)} can open, {len(rated)} rated, {len(out['hook_pool']['passing'])} rated >= "
 146 |          f"{HOOK_MIN} on the hook's own job" + (f"; NOT RATED: {hook_err}" if hook_err else "") +
 147 |          f" ({time.time() - t0:.0f} s)")
 148 | @@ -2336,6 +2381,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 149 |                    "no_voice": {"why": "the takeaway failed its gates in both writes; ruling 3 (22:40) ships the clips "
 150 |                                        "back to back with the sign-off only", "added_clip": added,
 151 |                                 "lineup_before": [m["moment_id"] for m in segs]}}
 152 | +        see(order)                                        # RULING 70: the added clip is seen too
 153 | +        vbad = [m["moment_id"] for m in order if not (m.get("visual") or {}).get("measured")]
 154 | +        if vbad:
 155 | +            note["why_not"] = f"ruling 70: the visual check is not measured for {vbad}"
 156 | +            return None
 157 |          pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
 158 |          pk["medley"] = nv_med
 159 |          cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 160 | @@ -2362,7 +2412,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 161 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 162 |                                  shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 163 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 164 | -                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
 165 | +                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 166 | +                                visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]])
 167 |          import package_pin
 168 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 169 |          if problems:
 170 | @@ -2491,6 +2542,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 171 |                  bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
 172 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
 173 |                  extra, relined, w_used, written = "", False, 0, ()
 174 | +                see(segs)                                   # RULING 70: every clip seen before any write is paid
 175 | +                vbad = {m["moment_id"]: (m.get("visual") or {}).get("why") for m in segs
 176 | +                        if not (m.get("visual") or {}).get("measured")}
 177 | +                if vbad or segs[0].get("visual_hook_block"):
 178 | +                    vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
 179 | +                    dropped |= set(vbad)
 180 | +                    doomed |= set(vbad)
 181 | +                    rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
 182 | +                    relined, w_used = True, writes      # no write is paid
 183 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 184 |                  while w_used < writes:
 185 |                      if over_budget(ai):
 186 | @@ -2642,7 +2702,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 187 |                                              ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 188 |                                              style=HS.lint_lines(pk["lines"]),
 189 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 190 | -                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
 191 | +                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 192 | +                                            visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]])
 193 |                      if not ok_c:
 194 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 195 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 196 | @@ -2722,7 +2783,7 @@ def _spent(spend):
 197 |  
 198 |  
 199 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 200 | -              hook=None, stand=None):
 201 | +              hook=None, stand=None, visual=None):
 202 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 203 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 204 |      A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 205 | @@ -2797,4 +2858,12 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 206 |                                        f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 207 |                                  medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 208 |             if stand is not None else {}),
 209 | +        **({"visual": dict(row(bool(visual) and all((v or {}).get("measured") is True for v in visual),
 210 | +                               sorted({str((v or {}).get("backend")) for v in visual}) or None,
 211 | +                               rep((v or {}).get("replayed") for v in visual), n=len(visual or []),
 212 | +                               measured=bool(visual) and all((v or {}).get("measured") is True for v in visual)),
 213 | +                           flags=[{"segment": i, **f} for i, v in enumerate(visual) for f in (v or {}).get("flags") or []],
 214 | +                           by_rule="visual_pin (ruling 70): one contact sheet per clip; a finding is a FLAG, sealed, "
 215 | +                                   "never a reject by itself")}
 216 | +           if visual is not None else {}),
 217 |      }
 218 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 219 | index 90c18f3..19330af 100644
 220 | --- a/pipeline/package_pin.py
 221 | +++ b/pipeline/package_pin.py
 222 | @@ -29,7 +29,8 @@ REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate
 223 |  # L-y (20:30): the clips-alone verdict and the medley's shape; ruling 6 (22:40): PBX's copy rules on every line;
 224 |  # hook_onset: G17a at the pin stage, after batch pin #1's render hold (01:39 ET Nov 13); stand_alone: the render's
 225 |  # STAND_ALONE at the pin stage, after pin d2657bbe's hold at the integrator's validate (03:00 ET Nov 13)
 226 | -MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone")
 227 | +MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone",
 228 | +                "visual")                                  # ruling 70: every clip's sheet judged (flags sealed)
 229 |  
 230 |  
 231 |  def required_gates(pk):
 232 | @@ -71,7 +72,8 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
 233 |                  "scorer_pending",                          # is trimmed, so every other pin seals as before (ruling 49 a;
 234 |                                                             # retired by ruling 56: kept so its pins still recompute)
 235 |                  "scorer_verdict",                          # ruling 56: the clip scorer's affirmation, only when sealed
 236 | -                "attested")                                # ruling 67: the attested-text re-seal's record (re-sealed)
 237 | +                "attested",                                # ruling 67: the attested-text re-seal's record (re-sealed)
 238 | +                "visual")                                  # ruling 70: the clip's visual record (flags, sheet sha)
 239 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
 240 |                                                             # separate constant (a test holds them equal): the
 241 |                                                             # integrator's check_pin_only imports this module, which
 242 | @@ -279,7 +281,8 @@ def to_pin(pk, run_name):
 243 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 244 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 245 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 246 | -                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict") if k in s},
 247 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual")
 248 | +                        if k in s},
 249 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 250 |      edl_vo = {"intro": pk["vo"]["intro"],
 251 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 252 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 253 | index 1eaba43..aa6c175 100644
 254 | --- a/pipeline/providers.py
 255 | +++ b/pipeline/providers.py
 256 | @@ -66,6 +66,25 @@ class ReplayMiss(Exception):
 257 |      """Offline replay has no recorded exchange for this call."""
 258 |  
 259 |  
 260 | +IMAGE_TOKENS_UPPER = 6000            # ruling 70: one image's input tokens, as the spend guard's upper bound
 261 | +
 262 | +
 263 | +def is_vision(prompt):
 264 | +    """RULING 70: a VISION prompt is {"text": str, "images": [base64 JPEG, ...]}; only a back-end with vision = True
 265 | +    is asked it (the others are skipped for that call)."""
 266 | +    return isinstance(prompt, dict) and isinstance(prompt.get("text"), str) and isinstance(prompt.get("images"), list) \
 267 | +        and all(isinstance(i, str) and i for i in prompt["images"])
 268 | +
 269 | +
 270 | +def prompt_text(prompt):
 271 | +    """The prompt as text, for the spend estimate, the logs and the recordings: a vision prompt's text with each image
 272 | +    as its sha256 (a recording never stores the image; its key still covers the image bytes)."""
 273 | +    if not is_vision(prompt):
 274 | +        return prompt
 275 | +    return prompt["text"] + "".join(f"\n[image sha256={hashlib.sha256(i.encode()).hexdigest()}]"
 276 | +                                    for i in prompt["images"])
 277 | +
 278 | +
 279 |  @dataclass
 280 |  class Reply:
 281 |      text: str
 282 | @@ -140,6 +159,7 @@ def _with_backoff(fn, final_codes=()):
 283 |  
 284 |  class Backend:
 285 |      vendor = "?"
 286 | +    vision = False                   # ruling 70: True only where complete() takes a vision prompt
 287 |  
 288 |      def __init__(self, name, spec, env_path):
 289 |          self.name, self.spec, self.env_path = name, spec, env_path
 290 | @@ -159,8 +179,11 @@ class Backend:
 291 |          return max(int(self.spec.get("min_out", 0)), max_tokens)
 292 |  
 293 |      def upper_usd(self, prompt, max_tokens, system=None):
 294 | -        """The call's spend upper bound: every prompt character a token (a safe over-estimate) + the output cap."""
 295 | -        return self.usd({"in": len(prompt) + len(system or "") + 200, "out": self.max_out(max_tokens)})
 296 | +        """The call's spend upper bound: every prompt character a token (a safe over-estimate), IMAGE_TOKENS_UPPER per
 297 | +        image of a vision prompt, + the output cap."""
 298 | +        n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
 299 | +        return self.usd({"in": len(text) + len(system or "") + 200 + IMAGE_TOKENS_UPPER * n_img,
 300 | +                         "out": self.max_out(max_tokens)})
 301 |  
 302 |      def key(self, name):
 303 |          k = env_value(self.env_path, name)
 304 | @@ -260,8 +283,11 @@ def _reported(usd):
 305 |  
 306 |  class HeimdallBackend(OpenAIBackend):
 307 |      """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY) at the config's base_url. JSON is asked for in
 308 | -    words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire."""
 309 | +    words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire. A vision
 310 | +    prompt (ruling 70) goes as chat-completions content parts: the text, then each image as an image_url data URL, the
 311 | +    form pipeline/visual_check.py uses with these image models."""
 312 |      vendor = "heimdall"
 313 | +    vision = True
 314 |  
 315 |      def _base(self):
 316 |          if not self.spec.get("base_url"):
 317 | @@ -270,10 +296,13 @@ class HeimdallBackend(OpenAIBackend):
 318 |  
 319 |      def complete(self, prompt, max_tokens, seed, system=None):
 320 |          key = self.key("HEIMDALL_API_KEY")
 321 | +        content = prompt if not is_vision(prompt) else \
 322 | +            [{"type": "text", "text": prompt["text"]}] + [{"type": "image_url", "image_url": {
 323 | +                "url": "data:image/jpeg;base64," + i}} for i in prompt["images"]]
 324 |          body = {"model": self.model, "max_tokens": self.max_out(max_tokens), "seed": seed,
 325 |                  "temperature": self.spec.get("temperature", 0),
 326 |                  "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."},
 327 | -                             {"role": "user", "content": prompt}]}
 328 | +                             {"role": "user", "content": content}]}
 329 |          t0 = time.time()
 330 |          base = self._base()
 331 |          j = _with_backoff(lambda: _http_json(base + "/chat/completions", body, {"Authorization": "Bearer " + key},
 332 | @@ -384,6 +413,47 @@ class XAISearchBackend(Backend):
 333 |                        "out": int(u.get("output_tokens") or u.get("completion_tokens") or 0)}, time.time() - t0
 334 |  
 335 |  
 336 | +class XAIVisionBackend(Backend):
 337 | +    """RULING 70: xAI's Responses API with image input (docs.x.ai, image understanding: "type": "input_image", a data
 338 | +    URL, "detail": "high"; "store": false, since a server-side record can make image requests fail). Only a vision
 339 | +    prompt is asked here. Its cost is the vendor's own figure when the reply carries one (cost_in_usd_ticks)."""
 340 | +    vendor = "xai_vision"
 341 | +    vision = True
 342 | +    URL = "https://api.x.ai/v1/responses"
 343 | +    SYSTEM = "You have no tools and no internet access. Answer in ONE message containing only the JSON object asked for."
 344 | +
 345 | +    def max_out(self, max_tokens):
 346 | +        return max(int(self.spec.get("min_out", 8000)), max_tokens * 4)        # a reasoning model thinks inside it
 347 | +
 348 | +    def complete(self, prompt, max_tokens, seed, system=None):
 349 | +        if not is_vision(prompt):
 350 | +            raise RequestRejected("xai_vision takes a vision prompt only")
 351 | +        key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
 352 | +        parts = [{"type": "input_text", "text": prompt["text"]}] + [
 353 | +            {"type": "input_image", "image_url": "data:image/jpeg;base64," + i, "detail": "high"}
 354 | +            for i in prompt["images"]]
 355 | +        body = {"model": self.model, "max_output_tokens": self.max_out(max_tokens), "store": False,
 356 | +                "temperature": self.spec.get("temperature", 0),
 357 | +                "input": [{"role": "system", "content": self.SYSTEM + (" " + system if system else "")},
 358 | +                          {"role": "user", "content": parts}]}
 359 | +        t0 = time.time()
 360 | +        j = _with_backoff(lambda: _http_json(self.URL, body, {"Authorization": "Bearer " + key}, self.timeout),
 361 | +                          final_codes=(401, 402, 403))
 362 | +        text = j.get("output_text") or ""
 363 | +        if not text:
 364 | +            for item in j.get("output") or []:
 365 | +                for part in (item.get("content") or []) if isinstance(item, dict) else []:
 366 | +                    if isinstance(part, dict) and part.get("type") in ("output_text", "text"):
 367 | +                        text += part.get("text") or ""
 368 | +        u = j.get("usage") or {}
 369 | +        reasoning = int((u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0)
 370 | +        out = int(u.get("output_tokens") or u.get("completion_tokens") or 0)
 371 | +        ticks = u.get("cost_in_usd_ticks")                    # the vendor's own cost: 1 USD = 1e10 ticks
 372 | +        return text, dict({"in": int(u.get("input_tokens") or u.get("prompt_tokens") or 0),
 373 | +                           "out": out + (reasoning if reasoning > out else 0)},
 374 | +                          **_reported(ticks / 1e10 if _num(ticks) else None)), time.time() - t0
 375 | +
 376 | +
 377 |  # ── transcription back-ends (law L-v 2's second recognition pass; role "transcribe") ──
 378 |  
 379 |  def _multipart(fields, file_field, path, content_type="audio/wav"):
 380 | @@ -483,7 +553,7 @@ class ElevenLabsTranscribe(STTBackend):
 381 |              time.time() - t0
 382 |  
 383 |  
 384 | -VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
 385 | +VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "xai_vision": XAIVisionBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
 386 |             "anthropic": AnthropicBackend, "openai_stt": OpenAITranscribe, "elevenlabs_stt": ElevenLabsTranscribe}
 387 |  
 388 |  
 389 | @@ -718,6 +788,10 @@ class Router:
 390 |              why = self._skip(name, b, av, am, af)
 391 |              if why is None and isinstance(b, STTBackend):
 392 |                  why = "a transcription back-end (Router.transcribe)"
 393 | +            if why is None and is_vision(prompt) and not b.vision:
 394 | +                why = "no image input (ruling 70)"
 395 | +            if why is None and not is_vision(prompt) and isinstance(b, XAIVisionBackend):
 396 | +                why = "a vision back-end (ruling 70)"
 397 |              if why:
 398 |                  tried.append((name, why))
 399 |                  continue
 400 | @@ -745,7 +819,8 @@ class Router:
 401 |                  self._settle(key, b, {"in": 0, "out": 0}, upper, role)     # booked as spent (estimate, unreported)
 402 |                  tried.append((name, f"{e} (abandoned at the deadline; its upper bound ${upper:.2f} booked as spent)"))
 403 |                  self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
 404 | -                                "deadline_s": deadline_s, "seconds": deadline_s, "prompt_chars": len(prompt),
 405 | +                                "deadline_s": deadline_s, "seconds": deadline_s,
 406 | +                                "prompt_chars": len(prompt_text(prompt)),
 407 |                                  "max_tokens": max_tokens})
 408 |                  continue
 409 |              except RequestRejected as e:
 410 | @@ -765,7 +840,8 @@ class Router:
 411 |              if secs >= self.slow_log_s:                # item 55: an answer this slow is evidence too
 412 |                  self._log_slow({"kind": "answered_slowly", "threshold_s": self.slow_log_s, "role": role, "model": name,
 413 |                                  "vendor": b.vendor, "deadline_s": deadline_s, "seconds": round(secs, 2),
 414 | -                                "prompt_chars": len(prompt), "max_tokens": max_tokens, "in": (usage or {}).get("in"),
 415 | +                                "prompt_chars": len(prompt_text(prompt)), "max_tokens": max_tokens,
 416 | +                                "in": (usage or {}).get("in"),
 417 |                                  "out": (usage or {}).get("out")})
 418 |              if not (isinstance(text, str) and text.strip()):   # an empty reply: this call moves on (audit C2 K7)
 419 |                  tried.append((name, "refused this request: an empty reply"))
 420 | @@ -773,7 +849,8 @@ class Router:
 421 |              recorded = ""
 422 |              if path and isinstance(text, str) and text.strip():
 423 |                  self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
 424 | -                                    "max_tokens": max_tokens, "system": system, "prompt": prompt, "text": text,
 425 | +                                    "max_tokens": max_tokens, "system": system, "prompt": prompt_text(prompt),
 426 | +                                    "text": text,
 427 |                                      "usage": usage, "usd": usd, "seconds": round(secs, 2)})
 428 |                  recorded = path
 429 |              return Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
 430 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
 431 | new file mode 100644
 432 | index 0000000..91ed674
 433 | --- /dev/null
 434 | +++ b/pipeline/visual_pin.py
 435 | @@ -0,0 +1,263 @@
 436 | +"""pipeline/visual_pin.py: RULING 70 (orchestrator 15:29 Nov 13), the pin-stage VISUAL check.
 437 | +
 438 | +"One contact sheet per clip, the three questions including lower_third; xAI first, Heimdall image models as failover;
 439 | +fail closed. A finding on third_person or on_screen_text does not reject the clip by itself: it is sealed as a FLAG
 440 | +that I and PBX see with the pin (text of the finding + the sheet), and a clip with a third_person finding may not be
 441 | +the HOOK unless the claim in the words is confirmed as reported fact by step A's context. lower_third feeds ruling 69
 442 | +as one more piece of evidence, never alone. Report the measured cost on the first build."
 443 | +
 444 | +Per clip (a moment's [start, end]):
 445 | +- fetch(): the span's video at <= 480p, yt-dlp download sections on CPU (as transcript_truth.audio_window fetches its
 446 | +  audio).
 447 | +- sheet(): at most TILES stills (the cut-in frame, one every EVERY_S seconds, the last frame), each labelled with its
 448 | +  time in the source, in ONE JPEG contact sheet (ffmpeg on CPU, PIL to tile). No GPU.
 449 | +- ONE verdict (role visual_check: xai_vision:grok-4.7, then the Heimdall image models), JSON, checked in code
 450 | +  (check()). A reply out of contract, or no answer, is retried once with a new seed, then the clip is NOT measured:
 451 | +  it cannot be sealed (law L-m).
 452 | +- flags(): a third_person finding (a person other than the speaker shown as a still, photo or graphic while the words
 453 | +  make a negative claim) and every on-screen text that asserts more than the words. They are sealed, never a reject.
 454 | +- hook_block(): why the clip may not be the HOOK, or None. Step A passes only a clip whose view is "own_sincere" (the
 455 | +  speaker's own assertion: context_integrity.a_failures), so no step-A verdict confirms a claim as REPORTED fact; a
 456 | +  third_person finding therefore blocks the hook (fail closed) until step A is asked that.
 457 | +Verdicts are cached per moment and span (cache=), like step A's: a clip is paid for once across builds."""
 458 | +import base64
 459 | +import hashlib
 460 | +import json
 461 | +import os
 462 | +import subprocess
 463 | +import threading
 464 | +
 465 | +VERSION = "visual-1"
 466 | +ROLE = "visual_check"
 467 | +TILES, EVERY_S, TILE_W = 8, 2.0, 480
 468 | +HOW = ("still", "photo", "graphic", "none")
 469 | +FORMAT = "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]"
 470 | +CACHE_LOCK = threading.Lock()
 471 | +
 472 | +PROMPT = """You check what a VIEWER SEES in one clip of another channel's video, before it is cut into ours.
 473 | +The image is a contact sheet of {n} frames of the clip, left to right and top to bottom, each labelled with its time in
 474 | +the source video (seconds). The clip's words, as spoken:
 475 | +"{text}"
 476 | +
 477 | +Answer three questions from the frames only:
 478 | +1. third_person: is a person who is NOT the one speaking shown as a STILL, a PHOTO or a GRAPHIC (not live video of a
 479 | +   person taking part in the show) while the clip's words make a NEGATIVE claim (a mistake, an accusation, a scandal,
 480 | +   a crime, a failure)? Report any NAME the screen shows as TEXT with that person. Never name anyone from a face: only
 481 | +   text on the screen names a person.
 482 | +2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not subtitles of the spoken
 483 | +   words, not the channel's logo), copied exactly, each with whether it ASSERTS something the clip's words do not.
 484 | +3. lower_third: the on-screen name strap (lower third) of the person speaking, copied exactly, or null.
 485 | +
 486 | +Return ONLY this JSON object:
 487 | +{{"third_person": {{"shown": true or false, "how": "still|photo|graphic|none", "words_negative": true or false,
 488 | +  "name_on_screen": "<the on-screen text naming them> or null", "finding": "<one sentence>"}},
 489 | + "on_screen_text": [{{"text": "...", "asserts_beyond_words": true or false, "why": "..."}}],
 490 | + "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}}}}"""
 491 | +
 492 | +
 493 | +def load_cache(path):
 494 | +    try:
 495 | +        with open(path) as f:
 496 | +            d = json.load(f)
 497 | +        return d if isinstance(d, dict) else {}
 498 | +    except (OSError, ValueError):
 499 | +        return {}
 500 | +
 501 | +
 502 | +def save_cache(path, cache):
 503 | +    if not path:
 504 | +        return
 505 | +    with CACHE_LOCK:
 506 | +        with open(path + ".tmp", "w") as f:
 507 | +            json.dump(cache, f, indent=1, sort_keys=True)
 508 | +        os.replace(path + ".tmp", path)
 509 | +
 510 | +
 511 | +def key(m):
 512 | +    """The cache key: the moment and span, VERSION, and a digest of everything else the verdict reads (the clip's
 513 | +    words, the prompt, the sheet's parameters; audit 1541 C1). A hit is used only on the same sheet bytes."""
 514 | +    inputs = json.dumps([PROMPT, TILES, EVERY_S, TILE_W, FORMAT, str(m.get("text") or "")])
 515 | +    return (f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{VERSION}:"
 516 | +            f"{hashlib.sha256(inputs.encode()).hexdigest()[:16]}")
 517 | +
 518 | +
 519 | +def _sha_of(path):
 520 | +    try:
 521 | +        with open(path, "rb") as f:
 522 | +            return hashlib.sha256(f.read()).hexdigest()
 523 | +    except OSError:
 524 | +        return None
 525 | +
 526 | +
 527 | +def times(dur, every=EVERY_S, tiles=TILES):
 528 | +    """The stills' offsets in the clip: the cut-in frame, one every `every` seconds, the last frame; at most `tiles`,
 529 | +    the first and the last always kept."""
 530 | +    last = max(0.0, dur - 0.05)
 531 | +    ts = [0.0]
 532 | +    t = every
 533 | +    while t < last - 0.25:
 534 | +        ts.append(round(t, 2))
 535 | +        t += every
 536 | +    if last > 0:
 537 | +        ts.append(round(last, 2))
 538 | +    if len(ts) > tiles:                                  # too many for one sheet: evenly spaced, both ends kept
 539 | +        ts = [round(last * i / (tiles - 1), 2) for i in range(tiles)]
 540 | +    return ts
 541 | +
 542 | +
 543 | +def fetch(video_id, start, end, work_dir):
 544 | +    """The span's video at <= 480p (yt-dlp download sections, CPU) -> the file's path."""
 545 | +    d = os.path.join(work_dir, "visual")
 546 | +    os.makedirs(d, exist_ok=True)
 547 | +    stem = f"{video_id}_{int(start * 1000)}_{int(end * 1000)}"
 548 | +    have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
 549 | +    if not have:
 550 | +        subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", FORMAT, "--download-sections",
 551 | +                        f"*{start:.2f}-{end:.2f}", "--force-keyframes-at-cuts", "-o", os.path.join(d, stem + ".%(ext)s"),
 552 | +                        f"https://www.youtube.com/watch?v={video_id}"], check=True, timeout=300, capture_output=True)
 553 | +        have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
 554 | +    if not have:
 555 | +        raise OSError(f"no video fetched for {stem}")
 556 | +    return os.path.join(d, have[0])
 557 | +
 558 | +
 559 | +def sheet(video, start, end, work_dir):
 560 | +    """ONE contact sheet of the clip -> (its path, sha256, the stills' source times)."""
 561 | +    from PIL import Image, ImageDraw
 562 | +    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
 563 | +                       capture_output=True, text=True, check=True, timeout=30)
 564 | +    dur = min(float(r.stdout.strip()), end - start)
 565 | +    offs = times(dur)
 566 | +    d = os.path.join(work_dir, "visual")
 567 | +    tiles = []
 568 | +    for i, t in enumerate(offs):
 569 | +        out = os.path.join(d, f"_still_{os.getpid()}_{threading.get_ident()}_{i}.jpg")
 570 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf",
 571 | +                        f"scale={TILE_W}:-2", "-q:v", "3", out], check=True, timeout=60)
 572 | +        with Image.open(out) as im:
 573 | +            tiles.append(im.convert("RGB").copy())
 574 | +        os.remove(out)
 575 | +    cols = min(4, len(tiles))
 576 | +    rows = (len(tiles) + cols - 1) // cols
 577 | +    w, h = tiles[0].size
 578 | +    canvas = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
 579 | +    draw = ImageDraw.Draw(canvas)
 580 | +    for i, (im, t) in enumerate(zip(tiles, offs)):
 581 | +        x, y = (i % cols) * w, (i // cols) * h
 582 | +        canvas.paste(im.resize((w, h)), (x, y))
 583 | +        label = f"{start + t:.2f} s"
 584 | +        draw.rectangle([x, y, x + 9 * len(label), y + 16], fill=(0, 0, 0))
 585 | +        draw.text((x + 3, y + 2), label, fill=(255, 255, 255))
 586 | +    tmp = os.path.join(d, f"_sheet_{os.getpid()}_{threading.get_ident()}.jpg")
 587 | +    canvas.save(tmp, "JPEG", quality=85)
 588 | +    with open(tmp, "rb") as f:
 589 | +        sha = hashlib.sha256(f.read()).hexdigest()
 590 | +    path = os.path.join(d, f"visual_{sha[:16]}.jpg")
 591 | +    os.replace(tmp, path)
 592 | +    return path, sha, [round(start + t, 2) for t in offs]
 593 | +
 594 | +
 595 | +def _json(text):
 596 | +    t = str(text or "")
 597 | +    a, b = t.find("{"), t.rfind("}")
 598 | +    if a < 0 or b < a:
 599 | +        raise ValueError("no JSON object in the reply")
 600 | +    return json.loads(t[a:b + 1])
 601 | +
 602 | +
 603 | +def _opt_str(x):
 604 | +    return x.strip() if isinstance(x, str) and x.strip() and x.strip().lower() not in ("null", "none") else None
 605 | +
 606 | +
 607 | +def check(v):
 608 | +    """The verdict, in contract or ValueError -> {"third_person", "on_screen_text", "lower_third"}."""
 609 | +    if not isinstance(v, dict) or set(v) != {"third_person", "on_screen_text", "lower_third"}:
 610 | +        raise ValueError("keys must be exactly third_person, on_screen_text, lower_third")
 611 | +    tp, ost, lt = v["third_person"], v["on_screen_text"], v["lower_third"]
 612 | +    if not isinstance(tp, dict) or type(tp.get("shown")) is not bool or tp.get("how") not in HOW or \
 613 | +            type(tp.get("words_negative")) is not bool or not isinstance(tp.get("finding"), str):
 614 | +        raise ValueError("third_person out of contract")
 615 | +    if not isinstance(ost, list) or any(not isinstance(x, dict) or not isinstance(x.get("text"), str) or
 616 | +                                        type(x.get("asserts_beyond_words")) is not bool for x in ost):
 617 | +        raise ValueError("on_screen_text out of contract")
 618 | +    if not isinstance(lt, dict):
 619 | +        raise ValueError("lower_third out of contract")
 620 | +    return {"third_person": {"shown": tp["shown"], "how": tp["how"], "words_negative": tp["words_negative"],
 621 | +                             "name_on_screen": _opt_str(tp.get("name_on_screen")), "finding": tp["finding"].strip()},
 622 | +            "on_screen_text": [{"text": x["text"].strip(), "asserts_beyond_words": x["asserts_beyond_words"],
 623 | +                                "why": str(x.get("why") or "").strip()} for x in ost if x["text"].strip()],
 624 | +            "lower_third": {"name": _opt_str(lt.get("name")), "text": _opt_str(lt.get("text"))}}
 625 | +
 626 | +
 627 | +def flags(v):
 628 | +    """RULING 70: the findings sealed as FLAGS (never a reject by themselves)."""
 629 | +    out = []
 630 | +    tp = v["third_person"]
 631 | +    if tp["shown"] and tp["how"] in ("still", "photo", "graphic") and tp["words_negative"]:
 632 | +        out.append({"kind": "third_person", "text": tp["finding"], "name_on_screen": tp["name_on_screen"]})
 633 | +    out += [{"kind": "on_screen_text", "text": x["text"], "why": x["why"]} for x in v["on_screen_text"]
 634 | +            if x["asserts_beyond_words"]]
 635 | +    return out
 636 | +
 637 | +
 638 | +def hook_block(rec):
 639 | +    """Why this clip may not be the HOOK (ruling 70), or None."""
 640 | +    if not (rec or {}).get("measured"):
 641 | +        return "its visual check is not measured (law L-m)"
 642 | +    if any(f["kind"] == "third_person" for f in rec.get("flags") or []):
 643 | +        return ("ruling 70: a third person is shown as a still while the words make a negative claim, and step A's "
 644 | +                "context does not confirm the claim as reported fact (step A passes only the speaker's own view)")
 645 | +    return None
 646 | +
 647 | +
 648 | +def sealed(rec):
 649 | +    """The part of a visual record a pin seals (package_pin.SEALED_LATER "visual"): the findings, the flags, the sheet's
 650 | +    name, sha256 and times (the sheet itself is copied beside the pin), the back-end. Never a scratch path or a cost."""
 651 | +    out = {k: rec[k] for k in ("version", "measured", "flags", "third_person", "on_screen_text", "lower_third",
 652 | +                               "backend", "replayed", "why") if k in rec}
 653 | +    if isinstance(rec.get("sheet"), dict):
 654 | +        out["sheet"] = {k: rec["sheet"][k] for k in ("name", "sha256", "times") if k in rec["sheet"]}
 655 | +    return out
 656 | +
 657 | +
 658 | +def visual_for(router, m, work_dir, cache, seed=7, log=print):
 659 | +    """The clip's visual record (cached per moment and span). Not measured on any failure: never a pass (law L-m).
 660 | +    -> {"version", "measured", "flags", "third_person", "on_screen_text", "lower_third", "sheet" {"name", "sha256",
 661 | +    "times", "path"}, "backend", "replayed", "usd", "cached"} or {"measured": False, "why"}."""
 662 | +    import providers as P
 663 | +    k = key(m)
 664 | +    hit = cache.get(k) if cache is not None and (cache.get(k) or {}).get("measured") else None
 665 | +    if hit is not None:                              # the judged sheet, still on disk with the judged bytes
 666 | +        p = os.path.join(work_dir, "visual", (hit.get("sheet") or {}).get("name") or "-")
 667 | +        if _sha_of(p) == (hit.get("sheet") or {}).get("sha256"):
 668 | +            return dict(hit, cached=True, usd=0.0, sheet=dict(hit["sheet"], path=p))
 669 | +    try:
 670 | +        video = fetch(m["video_id"], float(m["start"]), float(m["end"]), work_dir)
 671 | +        path, sha, ts = sheet(video, float(m["start"]), float(m["end"]), work_dir)
 672 | +        if hit is not None and sha == hit["sheet"]["sha256"]:        # rebuilt, the same bytes: the same verdict
 673 | +            return dict(hit, cached=True, usd=0.0, sheet=dict(hit["sheet"], path=path))
 674 | +        with open(path, "rb") as f:
 675 | +            b64 = base64.b64encode(f.read()).decode()
 676 | +    except Exception as e:                       # noqa: BLE001  no sheet: not measured (law L-m)
 677 | +        return {"version": VERSION, "measured": False, "why": f"no contact sheet: {type(e).__name__}: {str(e)[:160]}"}
 678 | +    prompt = {"text": PROMPT.format(n=len(ts), text=str(m.get("text") or "").replace('"', "'")), "images": [b64]}
 679 | +    why = None
 680 | +    for sd in (seed, seed + 1):
 681 | +        r = None
 682 | +        try:
 683 | +            r = router.call(ROLE, prompt, 1500, sd)
 684 | +            v = check(_json(r.text))
 685 | +            rec = {"version": VERSION, "measured": True, **v, "flags": flags(v),
 686 | +                   "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path},
 687 | +                   "backend": r.backend, "replayed": bool(getattr(r, "replayed", False)),
 688 | +                   "usd": 0.0 if getattr(r, "cached", False) else float(getattr(r, "usd", 0.0) or 0.0),
 689 | +                   "usage": getattr(r, "usage", None), "cached": bool(getattr(r, "cached", False))}
 690 | +            if cache is not None and not rec["replayed"]:
 691 | +                cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd")}
 692 | +            return rec
 693 | +        except Exception as e:                   # noqa: BLE001
 694 | +            if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)) and hasattr(router, "reject"):
 695 | +                router.reject(r)
 696 | +            why = f"{type(e).__name__}: {str(e)[:200]}"
 697 | +    return {"version": VERSION, "measured": False, "why": f"no verdict in contract after two tries: {why}",
 698 | +            "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path}}
 699 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 700 | index ab65cbf..6647ab8 100644
 701 | --- a/tests/package/proof_ledger.py
 702 | +++ b/tests/package/proof_ledger.py
 703 | @@ -173,7 +173,8 @@ def main(argv=None):
 704 |                step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 705 |                hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 706 |                scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 707 | -              scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir))
 708 | +              scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 709 | +              visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"))       # ruling 70
 710 |      name, at = os.path.relpath(out_dir, REPO), now.isoformat()
 711 |      if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
 712 |          res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
 713 | @@ -222,6 +223,13 @@ def main(argv=None):
 714 |                                                name="MOMENTS_PIN_LEDGER.json")
 715 |              res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 716 |                            "package_sha256": pin["moments_package"]["package_sha256"]}
 717 | +            import shutil                                # ruling 70: each segment's sheet beside the pin
 718 | +            for sg in pin["segments"]:
 719 | +                sh = (sg.get("visual") or {}).get("sheet") or {}
 720 | +                if sh.get("name"):
 721 | +                    src = os.path.join(a.work_dir, "visual", sh["name"])
 722 | +                    if os.path.exists(src):
 723 | +                        shutil.copyfile(src, os.path.join(out_dir, sh["name"]))
 724 |              say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known) "
 725 |                  f"pin {path}")
 726 |          except package_pin.PinRefused as e:
 727 | @@ -235,6 +243,10 @@ def main(argv=None):
 728 |          after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
 729 |      res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
 730 |                                "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
 731 | +    vis = res.get("visual") or {}
 732 | +    say(f"  visual (ruling 70): {vis.get('calls', 0)} sheet(s) asked ({vis.get('unmeasured', 0)} not measured), "
 733 | +        f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); measured cost ${vis.get('usd', 0):.4f} "
 734 | +        f"(the router's figure: vendor-reported where the reply carries it)")
 735 |      say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
 736 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
 737 |      try:                                                 # audit 1420 C2: a registry failure never loses the record;
 738 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 739 | index 33c7418..ee2d718 100644
 740 | --- a/tests/package/test_medley.py
 741 | +++ b/tests/package/test_medley.py
 742 | @@ -465,8 +465,8 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 743 |  
 744 |      def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
 745 |          pk = self.build()
 746 | -        self.assertEqual(package_pin.required_gates(pk)[-5:], ("medley", "ly_shape", "house_style", "hook_onset",
 747 | -                                                               "stand_alone"))
 748 | +        self.assertEqual(package_pin.required_gates(pk)[-6:], ("medley", "ly_shape", "house_style", "hook_onset",
 749 | +                                                               "stand_alone", "visual"))
 750 |          pk["gates"] = self.gates(pk)
 751 |          pin = package_pin.to_pin(spk(pk), "test")
 752 |          self.assertEqual(pin["label"], "bitcoin")     # the render's STAND_ALONE subject rests on it (audit 0310 C2)
 753 | @@ -523,7 +523,7 @@ class Rig:
 754 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 755 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 756 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 757 | -                 cached=False, candidate=None):
 758 | +                 cached=False, candidate=None, visuals=None):
 759 |          import providers as P
 760 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 761 |          self.takeaways, self.spend = list(takeaways or []), spend
 762 | @@ -533,6 +533,7 @@ class Rig:
 763 |          self.hooks, self.hook_err, self.hook_calls = dict(hooks or {}), hook_err, []   # ruling 59 (a): {id: (s, a, u)}
 764 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 765 |          self.candidate, self.seeds = candidate, []          # ruling 66: build from a candidate; the seeds asked with
 766 | +        self.visuals, self.visual_calls = dict(visuals or {}), []   # ruling 70: {moment id: record} (default: clean)
 767 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 768 |          self.screens, self.events, self.a_seen = [], [], []
 769 |          self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
 770 | @@ -615,6 +616,17 @@ class Rig:
 771 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 772 |          return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields
 773 |  
 774 | +    def visual(self, router, m, work_dir, cache, seed=7, log=print):
 775 | +        """visual_pin.visual_for as the build calls it: a measured clean record unless self.visuals says otherwise."""
 776 | +        self.visual_calls.append(m["moment_id"])
 777 | +        base = {"version": "visual-1", "measured": True, "flags": [],
 778 | +                "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 779 | +                                 "finding": "no third person"},
 780 | +                "on_screen_text": [], "lower_third": {"name": None, "text": None},
 781 | +                "sheet": {"name": f"visual_{m['moment_id']}.jpg", "sha256": "0" * 64, "times": [0.0], "path": "/x"},
 782 | +                "backend": "xai_vision:grok-4.7", "replayed": False, "usd": 0.002, "cached": False}
 783 | +        return dict(base, **self.visuals.get(m["moment_id"], {}))
 784 | +
 785 |      def onset(self, m, *a, **k):
 786 |          """hook_onset.measure's record: the hook lead, and for a trimmed moment its trimmed cut ("trim")."""
 787 |          r = ({"pass": False, "measured": True, "lead_ms": 20, "why": "20 ms < 80"} if m["moment_id"] in self.no_hook
 788 | @@ -661,12 +673,15 @@ class Rig:
 789 |              kw["scorer_verdicts_path"] = path
 790 |              stubs["render_scorer_sha"] = lambda *a, **k: "s" * 64       # the render's scorer code, as it is now
 791 |          saved = {k: getattr(PK, k) for k in stubs}
 792 | +        import visual_pin as VP
 793 | +        saved_vp, VP.visual_for = VP.visual_for, self.visual       # ruling 70
 794 |          try:
 795 |              for k, v in stubs.items():
 796 |                  setattr(PK, k, v)
 797 |              return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent",
 798 |                              spend=self.spend, **kw)
 799 |          finally:
 800 | +            VP.visual_for = saved_vp
 801 |              for k, v in saved.items():
 802 |                  setattr(PK, k, v)
 803 |              if path:
 804 | @@ -1588,6 +1603,72 @@ class TestRulings6264Search(unittest.TestCase):
 805 |          self.assertTrue(out["tried"][1].get("verdict_again"))               # the second angle's: free
 806 |  
 807 |  
 808 | +class TestRuling70Visual(unittest.TestCase):
 809 | +    """RULING 70 (15:29): one contact sheet per clip; xAI first, Heimdall image models as failover; fail closed. A finding
 810 | +    is sealed as a FLAG, never a reject by itself; a third_person finding may not be the HOOK (step A confirms no claim
 811 | +    as reported fact: it passes only the speaker's own view)."""
 812 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 813 | +    TP = {"flags": [{"kind": "third_person", "text": "a photo of a CEO beside the host", "name_on_screen": None}],
 814 | +          "third_person": {"shown": True, "how": "photo", "words_negative": True, "name_on_screen": None,
 815 | +                           "finding": "a photo of a CEO beside the host"}}
 816 | +
 817 | +    def test_hooks_are_seen_before_the_angle_and_a_clean_package_seals_every_sheet(self):
 818 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 819 | +        out = rig.run()
 820 | +        self.assertLess(rig.events.index("hook_ratings"), rig.events.index("angle_write"))
 821 | +        self.assertEqual(rig.visual_calls[0], "h")                     # the hook, at the hook stage
 822 | +        self.assertEqual(sorted(set(rig.visual_calls)), ["h", "x", "y"])
 823 | +        pk = out["package"]
 824 | +        self.assertEqual(pk["gates"]["visual"]["status"], "PASS")
 825 | +        self.assertEqual([sg["visual"]["sheet"]["name"] for sg in pk["segments"]],
 826 | +                         ["visual_h.jpg", "visual_x.jpg", "visual_y.jpg"])
 827 | +        self.assertNotIn("path", pk["segments"][0]["visual"]["sheet"])  # never a scratch path in the seal
 828 | +        self.assertIn("visual", package_pin.MEDLEY_GATES)
 829 | +        pin = package_pin.to_pin(spk(pk), "r")
 830 | +        self.assertIn("visual", pin["segments"][1])
 831 | +        segs = [{k: v for k, v in sg.items() if k != "visual"} for sg in pin["segments"]]
 832 | +        mp = pin["moments_package"]
 833 | +        self.assertNotEqual(package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"],
 834 | +                                             mp["gates"], mp.get("btc_screen")), mp["package_sha256"])   # sealed
 835 | +
 836 | +    def test_a_clip_flag_is_sealed_never_a_reject(self):
 837 | +        flag = {"flags": [{"kind": "on_screen_text", "text": "CEO SCANDAL", "why": "the words say no such thing"}]}
 838 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"x": flag}).run()
 839 | +        pk = out["package"]
 840 | +        self.assertIsNotNone(pk)
 841 | +        self.assertEqual(pk["gates"]["visual"]["status"], "PASS")
 842 | +        self.assertEqual(pk["gates"]["visual"]["flags"], [dict(flag["flags"][0], segment=1)])
 843 | +        self.assertEqual(pk["segments"][1]["visual"]["flags"], flag["flags"])
 844 | +
 845 | +    def test_a_third_person_finding_may_not_open_and_no_angle_is_written_for_it(self):
 846 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": self.TP})
 847 | +        out = rig.run()
 848 | +        self.assertIsNone(out["package"])
 849 | +        self.assertIn("h", out["hook_pool"]["visual_blocked"])
 850 | +        self.assertIn("ruling 70", out["hook_pool"]["visual_blocked"]["h"])
 851 | +        self.assertNotIn("angle_write", rig.events)                      # "no hook in the pool": nothing written
 852 | +        self.assertTrue(out["why_none"].startswith("no hook in the pool"), out["why_none"])
 853 | +
 854 | +    def test_a_third_person_clip_that_is_not_the_hook_is_kept_with_its_flag(self):
 855 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"y": self.TP}).run()
 856 | +        self.assertIsNotNone(out["package"])
 857 | +        self.assertEqual([f["kind"] for f in out["package"]["gates"]["visual"]["flags"]], ["third_person"])
 858 | +
 859 | +    def test_an_unmeasured_clip_is_dropped_before_any_write(self):
 860 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 861 | +                  visuals={"y": {"measured": False, "why": "no verdict in contract after two tries"}})
 862 | +        out = rig.run()
 863 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
 864 | +        self.assertTrue(out["tried"][0]["why"].startswith("ruling 70: y: no verdict"), out["tried"][0]["why"])
 865 | +        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])     # no write for the line-up with y
 866 | +        self.assertIsNotNone(out["package"])
 867 | +
 868 | +    def test_an_unmeasured_hook_may_not_open(self):
 869 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": {"measured": False, "why": "no sheet"}}).run()
 870 | +        self.assertIn("not measured", out["hook_pool"]["visual_blocked"]["h"])
 871 | +        self.assertIsNone(out["package"])
 872 | +
 873 | +
 874 |  class TestRuling66Candidate(unittest.TestCase):
 875 |      """RULING 66 (13:18): A PASSED LINE-UP IS KEPT. A line-up that passed the clips-alone verdict is a candidate. A build
 876 |      from it asks no angle, tries exactly its clips in its order with its own seeds (so its recorded calls are served
 877 | @@ -2372,7 +2453,9 @@ class TestNoVoiceRealGates(unittest.TestCase):
 878 |          pk["gates"] = PK.inventory(fid, dup, rt_ok, r4_res, cx, a_lab, exc, tru, True, coh, medley=(True, med),
 879 |                                     shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 880 |                                     hook={"pass": True, "measured": True, "lead_ms": 200, "cut_in": 1.0, "why": "ok"},
 881 | -                                   stand=PK.stand_alone_check(pk["segments"]))
 882 | +                                   stand=PK.stand_alone_check(pk["segments"]),
 883 | +                                   visual=[{"measured": True, "replayed": False, "backend": "xai_vision:grok-4.7",
 884 | +                                            "flags": []} for _ in pk["segments"]])      # ruling 70
 885 |          self.assertEqual(package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk)), [])
 886 |          mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 887 |          self.assertEqual((mp["edl_vo"], mp["no_voice"]["added_clip"]), ({"intro": None, "bridges": []}, None))
 888 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
 889 | new file mode 100644
 890 | index 0000000..d675b61
 891 | --- /dev/null
 892 | +++ b/tests/package/test_visual_pin.py
 893 | @@ -0,0 +1,171 @@
 894 | +#!/usr/bin/env python3
 895 | +"""RULING 70 (orchestrator 15:29 Nov 13): the pin-stage visual check (pipeline/visual_pin.py) and the router's vision
 896 | +prompt (providers.is_vision / prompt_text, the xai_vision and Heimdall back-ends). Offline: no network, no model."""
 897 | +import base64
 898 | +import json
 899 | +import os
 900 | +import sys
 901 | +import tempfile
 902 | +import unittest
 903 | +
 904 | +HERE = os.path.dirname(os.path.abspath(__file__))
 905 | +REPO = os.path.dirname(os.path.dirname(HERE))
 906 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 907 | +sys.path.insert(0, os.path.join(REPO, "tests", "providers"))
 908 | +import providers as P  # noqa: E402
 909 | +import visual_pin as VP  # noqa: E402
 910 | +from test_providers import Fake, router  # noqa: E402
 911 | +
 912 | +CLEAN = {"third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 913 | +                          "finding": "only the host on camera"},
 914 | +         "on_screen_text": [{"text": "SIMPLY BITCOIN", "asserts_beyond_words": False, "why": "the show's name"}],
 915 | +         "lower_third": {"name": "Mark W. Yusko", "text": "Mark W. Yusko, Morgan Creek Capital"}}
 916 | +STILL = dict(CLEAN, third_person={"shown": True, "how": "photo", "words_negative": True, "name_on_screen": "null",
 917 | +                                  "finding": "a photo of a man beside the host while he says a CEO made a mistake"},
 918 | +             on_screen_text=[{"text": "NVIDIA CEO SCANDAL", "asserts_beyond_words": True,
 919 | +                              "why": "the words name no company"}])
 920 | +M = {"moment_id": "m1", "video_id": "vid00000001", "start": 236.688, "end": 253.308, "text": "A CEO makes a mistake."}
 921 | +
 922 | +
 923 | +class VFake(Fake):
 924 | +    vision = True
 925 | +
 926 | +
 927 | +class TestContract(unittest.TestCase):
 928 | +    def test_the_stills_are_the_cut_in_one_every_two_seconds_and_the_last(self):
 929 | +        self.assertEqual(VP.times(16.62), [0.0, 2.37, 4.73, 7.1, 9.47, 11.84, 14.2, 16.57])   # evenly spaced
 930 | +        self.assertEqual(VP.times(5.0), [0.0, 2.0, 4.0, 4.95])
 931 | +        self.assertEqual(len(VP.times(60.0)), VP.TILES)
 932 | +
 933 | +    def test_a_reply_in_contract_and_out_of_it(self):
 934 | +        v = VP.check(STILL)
 935 | +        self.assertIsNone(v["third_person"]["name_on_screen"])               # "null" text is no name
 936 | +        self.assertEqual([f["kind"] for f in VP.flags(v)], ["third_person", "on_screen_text"])
 937 | +        self.assertEqual(VP.flags(VP.check(CLEAN)), [])
 938 | +        self.assertEqual(VP.check(CLEAN)["lower_third"]["name"], "Mark W. Yusko")
 939 | +        for bad in (dict(CLEAN, extra=1), dict(CLEAN, third_person=dict(CLEAN["third_person"], how="video")),
 940 | +                    dict(CLEAN, third_person=dict(CLEAN["third_person"], shown="yes")),
 941 | +                    dict(CLEAN, on_screen_text=[{"text": "x"}]), dict(CLEAN, lower_third="Mark")):
 942 | +            with self.assertRaises(ValueError):
 943 | +                VP.check(bad)
 944 | +
 945 | +    def test_a_third_person_finding_or_no_measure_blocks_the_hook_but_flags_never_reject(self):
 946 | +        self.assertIsNone(VP.hook_block({"measured": True, "flags": VP.flags(VP.check(CLEAN))}))
 947 | +        self.assertIsNone(VP.hook_block({"measured": True, "flags": [{"kind": "on_screen_text", "text": "x"}]}))
 948 | +        self.assertIn("ruling 70", VP.hook_block({"measured": True, "flags": VP.flags(VP.check(STILL))}))
 949 | +        self.assertIn("not measured", VP.hook_block({"measured": False}))
 950 | +        self.assertIn("not measured", VP.hook_block(None))
 951 | +
 952 | +    def test_the_seal_never_holds_a_scratch_path_or_a_cost(self):
 953 | +        s = VP.sealed({"version": "v", "measured": True, "flags": [], "third_person": {}, "on_screen_text": [],
 954 | +                       "lower_third": {}, "backend": "b", "replayed": False, "usd": 0.01, "cached": True,
 955 | +                       "usage": {"in": 1}, "sheet": {"name": "n.jpg", "sha256": "s", "times": [1.0], "path": "/tmp/x"}})
 956 | +        self.assertEqual(s["sheet"], {"name": "n.jpg", "sha256": "s", "times": [1.0]})
 957 | +        self.assertFalse({"usd", "cached", "usage"} & set(s))
 958 | +
 959 | +
 960 | +class TestVisualFor(unittest.TestCase):
 961 | +    def setUp(self):
 962 | +        self.tmp = tempfile.TemporaryDirectory()
 963 | +        self.sheet = os.path.join(self.tmp.name, "visual_x.jpg")
 964 | +        with open(self.sheet, "wb") as f:
 965 | +            f.write(b"\xff\xd8 not a real jpeg")
 966 | +        self.saved = VP.fetch, VP.sheet
 967 | +        VP.fetch = lambda vid, s, e, wd: "/v.mp4"
 968 | +        VP.sheet = lambda v, s, e, wd: (self.sheet, "ab" * 32, [236.69, 253.26])
 969 | +
 970 | +    def tearDown(self):
 971 | +        VP.fetch, VP.sheet = self.saved
 972 | +        self.tmp.cleanup()
 973 | +
 974 | +    def test_xai_first_then_heimdall_and_the_prompt_carries_the_sheet(self):
 975 | +        x = VFake("xai_vision:grok-4.7", "xai_vision", fail="down")
 976 | +        h = VFake("heimdall:qwen", "heimdall", answer=json.dumps(STILL))
 977 | +        text_only = Fake("xai:grok", "xai", answer=json.dumps(CLEAN))     # no image input: never asked
 978 | +        r = router(self.tmp.name, [text_only, x, h], {"visual_check": ["xai:grok", "xai_vision:grok-4.7",
 979 | +                                                                       "heimdall:qwen"]})
 980 | +        cache = {}
 981 | +        rec = VP.visual_for(r, M, self.tmp.name, cache)
 982 | +        self.assertTrue(rec["measured"])
 983 | +        self.assertEqual((rec["backend"], text_only.calls, x.calls, h.calls), ("heimdall:qwen", 0, 1, 1))
 984 | +        self.assertEqual([f["kind"] for f in rec["flags"]], ["third_person", "on_screen_text"])
 985 | +        self.assertEqual(rec["sheet"]["sha256"], "ab" * 32)
 986 | +        os.makedirs(os.path.join(self.tmp.name, "visual"), exist_ok=True)
 987 | +        VP.sheet = lambda v, s, e, wd: (self.sheet, "ab" * 32, [236.69, 253.26])   # the same bytes again
 988 | +        again = VP.visual_for(r, M, self.tmp.name, cache)                   # paid once: the cache
 989 | +        self.assertTrue(again["cached"])
 990 | +        self.assertEqual((again["usd"], h.calls), (0.0, 1))
 991 | +        VP.sheet = lambda v, s, e, wd: (self.sheet, "cd" * 32, [236.69, 253.26])   # other bytes: judged afresh
 992 | +        self.assertFalse(VP.visual_for(r, M, self.tmp.name, cache)["cached"])
 993 | +        self.assertEqual(h.calls, 2)
 994 | +        self.assertNotEqual(VP.key(M), VP.key(dict(M, text="other words")))   # the words are in the key
 995 | +
 996 | +    def test_out_of_contract_twice_is_not_measured(self):
 997 | +        h = VFake("heimdall:qwen", "heimdall", answer="a man is shown")
 998 | +        r = router(self.tmp.name, [h], {"visual_check": ["heimdall:qwen", "heimdall:qwen"]})
 999 | +        rec = VP.visual_for(r, M, self.tmp.name, {})
1000 | +        self.assertFalse(rec["measured"])
1001 | +        self.assertIn("two tries", rec["why"])
1002 | +        self.assertEqual(h.calls, 2)                                          # one retry, a new seed
1003 | +
1004 | +    def test_no_sheet_is_not_measured_and_nothing_is_asked(self):
1005 | +        VP.sheet = lambda *a: (_ for _ in ()).throw(OSError("ffmpeg"))
1006 | +        h = VFake("heimdall:qwen", "heimdall", answer=json.dumps(CLEAN))
1007 | +        r = router(self.tmp.name, [h], {"visual_check": ["heimdall:qwen", "heimdall:qwen"]})
1008 | +        rec = VP.visual_for(r, M, self.tmp.name, {})
1009 | +        self.assertEqual((rec["measured"], h.calls), (False, 0))
1010 | +
1011 | +
1012 | +class TestVisionPrompt(unittest.TestCase):
1013 | +    def test_the_recording_holds_the_images_sha_never_the_image(self):
1014 | +        img = base64.b64encode(b"jpeg bytes").decode()
1015 | +        prompt = {"text": "look", "images": [img]}
1016 | +        self.assertTrue(P.is_vision(prompt))
1017 | +        self.assertFalse(P.is_vision("look"))
1018 | +        self.assertFalse(P.is_vision({"text": "look", "images": [""]}))
1019 | +        self.assertIn("[image sha256=", P.prompt_text(prompt))
1020 | +        self.assertNotIn(img, P.prompt_text(prompt))
1021 | +        with tempfile.TemporaryDirectory() as d:
1022 | +            h = VFake("heimdall:qwen", "heimdall", answer=json.dumps(CLEAN))
1023 | +            r = router(d, [h], {"visual_check": ["heimdall:qwen", "heimdall:qwen"]}, record_dir=os.path.join(d, "rec"))
1024 | +            r.call("visual_check", prompt, 100, 7)
1025 | +            recs = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(d, "rec")) for f in fs]
1026 | +            self.assertEqual(len(recs), 1)
1027 | +            with open(recs[0]) as f:
1028 | +                body = f.read()
1029 | +            self.assertNotIn(img, body)
1030 | +            self.assertIn("[image sha256=", body)
1031 | +            self.assertEqual(r.call("visual_check", prompt, 100, 7).cached, True)   # the same bytes: served
1032 | +
1033 | +    def test_the_upper_bound_counts_each_image(self):
1034 | +        b = Fake("x:y", "openai", price=(1e6, 0))                             # $1 per input token
1035 | +        one = b.upper_usd({"text": "t", "images": ["a"]}, 0)
1036 | +        self.assertEqual(one - b.upper_usd("t", 0), P.IMAGE_TOKENS_UPPER)
1037 | +
1038 | +    def test_the_heimdall_and_xai_vision_bodies(self):
1039 | +        sent = []
1040 | +        saved = P._http_json
1041 | +        P._http_json = lambda url, body, headers, timeout: (sent.append((url, body)) or
1042 | +                                                            {"choices": [{"message": {"content": "{}"}}],
1043 | +                                                             "output_text": "{}", "usage": {}})
1044 | +        try:
1045 | +            h = P.HeimdallBackend("heimdall:qwen", {"model": "qwen", "base_url": "https://h.example/api/v1"}, "/x")
1046 | +            h.key = lambda n: "k"
1047 | +            h.complete({"text": "look", "images": ["QUJD"]}, 100, 7)
1048 | +            x = P.XAIVisionBackend("xai_vision:grok-4.7", {"model": "grok-4.7"}, "/x")
1049 | +            x.key = lambda n: "k"
1050 | +            x.complete({"text": "look", "images": ["QUJD"]}, 100, 7)
1051 | +            with self.assertRaises(P.RequestRejected):
1052 | +                x.complete("text only", 100, 7)
1053 | +        finally:
1054 | +            P._http_json = saved
1055 | +        user = sent[0][1]["messages"][1]["content"]
1056 | +        self.assertEqual(user[1], {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}})
1057 | +        self.assertEqual(sent[1][0], "https://api.x.ai/v1/responses")
1058 | +        self.assertFalse(sent[1][1]["store"])
1059 | +        self.assertEqual(sent[1][1]["input"][1]["content"][1],
1060 | +                         {"type": "input_image", "image_url": "data:image/jpeg;base64,QUJD", "detail": "high"})
1061 | +
1062 | +
1063 | +if __name__ == "__main__":
1064 | +    unittest.main()
1065 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder that seals medley pins the render plays,
built from other channels' clips). Your role: a strict reviewer of a NEW gate that looks at source video and seals
its findings. Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- A build:
  - screens the pool;
  - rates hooks (ruling 59: only a hook rated >= 4 opens);
  - asks a writer for angles;
  - judges each line-up on the clips alone;
  - writes (takeaway / title / caption);
  - gates everything;
  - seals the pin.
- package_pin.seal is sha256 over the pin's body; a SEALED_LATER key enters it only when a segment carries it. The
  integrator's check_pin_only recomputes seals with this file and checks gate_problems() with the default
  REQUIRED_GATES.
- providers.Router routes each role's chain (failover), records every exchange, and runs the spend guard: each paid
  call reserves Backend.upper_usd first and settles after.
- The 13:38 pin's hook (Simply Bitcoin) opened on a split-screen photo of a real CEO while the host said "A CEO makes a
  personal mistake and shareholders pay". The words named nobody, so no text gate saw it; the picture named him.

The ruling this diff implements (ORCHESTRATOR 15:29 Nov 13, verbatim):
"(1) C: YES, build it (RULING 70). One contact sheet per clip, the three questions including lower_third; xAI first,
Heimdall image models as failover; fail closed. A finding on third_person or on_screen_text does not reject the clip
by itself: it is sealed as a FLAG that I and PBX see with the pin (text of the finding + the sheet), and a clip with a
third_person finding may not be the HOOK unless the claim in the words is confirmed as reported fact by step A's
context. lower_third feeds ruling 69 as one more piece of evidence, never alone. Report the measured cost on the first
build."
The three questions, from the proposal it rules on:
(1) third_person: is a person who is NOT speaking shown as a still, photo or graphic while the words make a negative
    claim (reporting on-screen NAME TEXT only, never naming from a face)?
(2) on_screen_text: the source's headline graphics or chyrons, and whether each asserts more than the words.
(3) lower_third: the speaker's on-screen name.

The change:
1. pipeline/visual_pin.py (new):
   - fetch(): the span at <= 480p (yt-dlp download sections, CPU).
   - sheet(): at most 8 stills (the cut-in, one every 2 s, the last; evenly spaced if more), each labelled with its
     source time, in ONE JPEG (ffmpeg + PIL, CPU).
   - visual_for(): ONE verdict (role visual_check). Checked in code (check(): exact keys, enums, types). Out of
     contract or unanswered: retried once with a new seed, then NOT measured. No sheet: not measured, nothing asked.
     Cached per moment + span + VERSION, measured live only.
   - flags(): a third_person finding (shown, as still/photo/graphic, with negative words), and every on_screen_text
     that asserts more than the words.
   - hook_block(): not measured, or a third_person flag, blocks the HOOK.
   - sealed(): the subset a pin seals (findings, flags, the sheet's name/sha256/times, backend; never a scratch path
     or a cost).
2. pipeline/providers.py: a VISION prompt {"text", "images": [base64 JPEG]}.
   - is_vision / prompt_text: the recordings and logs carry each image's sha256, never the image; the record KEY
     still covers the image bytes.
   - Backend.vision (False by default). The router skips a non-vision back-end for a vision prompt, and the vision
     back-end for a text prompt.
   - upper_usd adds IMAGE_TOKENS_UPPER (6000) per image.
   - XAIVisionBackend (vendor xai_vision): the Responses API with "input_image" parts, "detail": "high",
     "store": false (xAI's image-understanding guide uses grok-4.7 and warns a stored record can make image requests
     fail); it refuses a text prompt. Cost from cost_in_usd_ticks when the reply carries it.
   - HeimdallBackend sends a vision prompt as chat-completions content parts (text + image_url data URLs), the form
     the render's pipeline/visual_check.py uses with these models.
3. pipeline/model_providers.json:
   - backends xai_vision:grok-4.7 ([5, 25] per 1M, an upper bound) and heimdall:nvidia/nemotron-3.5-super-vl;
   - role visual_check = [xai_vision:grok-4.7, heimdall:qwen/qwen3.8-27b, heimdall:nvidia/nemotron-3.5-super-vl].
4. pipeline/package.py:
   - build(visual_cache=).
   - The hooks that would open (rated >= 4) are seen right after the hook ratings, BEFORE any angle call.
     hook_block -> m["visual_hook_block"] -> can_open() is False, so no angle is written for it. hook_pool records
     visual_blocked.
   - Every clip of a line-up that passes the clips-alone verdict is seen BEFORE any write. A clip not measured is
     dropped and the line-up re-lined, with no write.
   - The no-voice fallback sees its added clip too.
   - Segments carry visual_pin.sealed(); the inventory has a "visual" row: PASS only when every clip is measured,
     with all flags listed.
   - out["visual"] = {calls, cached, usd, unmeasured, flags}.
5. pipeline/package_pin.py: SEALED_LATER gains "visual"; to_pin carries it; MEDLEY_GATES gains "visual" (required for
   a new medley pin; check_pin_only uses REQUIRED_GATES, so earlier pins are untouched).
6. tests/package/proof_ledger.py: passes visual_cache, copies each sealed sheet beside the pin, and logs the measured
   cost.
7. Tests:
   - test_visual_pin (10): the stills; the contract; the flags; the hook block; the seal subset; xAI first, then
     Heimdall, the text-only back-end never asked, the cache; out-of-contract twice is unmeasured; no sheet asks
     nothing; the recording without the image; the image upper bound; the two request bodies.
   - test_medley +6 (TestRuling70Visual):
     - hooks seen before the angle, and a clean package sealing every sheet;
     - a clip flag sealed, not a reject;
     - a third-person hook blocked with no angle written;
     - a third-person clip (not the hook) kept with its flag;
     - an unmeasured clip dropped before any write;
     - an unmeasured hook blocked.
   - Old tests updated for the new required row. All 14 suites OK.

Stated readings (say so if you read the ruling differently):
- K1: "confirmed as reported fact by step A's context": step A passes only a clip whose view is "own_sincere" (the
  speaker's own assertion; context_integrity.a_failures). No step-A verdict classifies a claim as REPORTED fact, so
  today a third_person finding always blocks the HOOK (fail closed). Asking step A that question is a contract change
  for a later ruling.
- K2: "fail closed" = a clip whose visual check is not measured cannot be sealed: required row, dropped clip, blocked
  hook. A FLAG itself never rejects.
- K3: the sheet and the findings are sealed in the pin (the sheet by sha256; the file beside the pin), so the
  orchestrator and PBX see exactly what the model saw.
- K4: lower_third reaches ruling 69 through the segment's visual record (speakers.attribute_package reads
  visual.lower_third.name). Ruling 69's decide() lets it confirm or veto only.

Check in particular:
- that no path seals a clip without a measured visual check;
- that a third-person hook can never open;
- the router changes (could a text role ever reach a vision back-end, or an image reach a text one; the spend guard;
  the recording);
- the Responses / chat bodies;
- the seal compatibility for earlier pins;
- the cost accounting.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


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
