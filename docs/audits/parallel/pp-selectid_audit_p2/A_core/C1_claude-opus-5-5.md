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
- Vendor is not the same as model family. Heimdall hosts deepseek, qwen and gemma. Today's chains do not collide, but nothing prevents a future chain from pairing `local:gemma3` (writer) with `heimdall:google/gemma-4-31b-it` (verdict).
- In replay mode, a missing recording for back-end 1 silently serves back-end 2's recording (L2182-2184). The replay then differs from the live run without saying so.

## Q3: Verbatim and model text

**What holds:**
- Clip text is `sp.text` of whole sentence ids (L780), carried as `approved_text: s["text"]` (L1740).
- The miner `reason` appears in no prompt or audience slot. I checked `_sets_block`, `ANGLE_PROMPT clips`, `_lineup_block` and `package_view`.
- The trend brief only influences `TREND_WEIGHT = 0` ranking.
- `angle` is not in `lines` and not in the pin, so it is not audience-facing in this diff.
- The sign-off is code (L1213-1218).

**What leaks:**
- Verdict-written `claim` text is injected into the writer prompt via `extra` (L1621-1626). The writer's output is still gated, so this is low risk.
- Docstrings promise a REPAIR path ("extend the clip backwards by whole sentences", L28, L1028). It is not implemented: only dropping exists, and `repairable()` (L302-308) is unused. This is a doc mismatch, not a verbatim break.

## Q4: Deterministic rules

Concrete inputs are in the findings. Summary:

| Rule | False PASS | False REJECT |
|---|---|---|
| NAME | Any Title Case line skips the rule entirely (L2654) | "She"/guest names: see the ATTRIBUTION row and P1-4 |
| ATTRIBUTION | Case-sensitive, so "Says" in a title is missed; lowercase subjects missed; colon attribution missed | "She says …" fails (subject "She") |
| NUMBER | `att_pool` = last attributed speaker; spelled numbers ≤ 10 and segment count/day exempt | Two attributions: a number of speaker 1 is checked in speaker 2's pool |
| QUOTE | Single-quoted fabricated quotes not detected (L2605) | — |
| RELATION | "goes further", "sees it the same way", "Both channels …" | "Bitcoin's *answer* to inflation"; "how Bitcoin *responded* to the hike" |
| FRAMING | — | "Bitcoin *exposure*", "*confirmation*" |
| IMPERATIVE | "Saylor Says Buy Every Dip", "Time to buy", "Don't sell" | "*Short*-term holders …", "*Sell*-offs like this …" |
| TIME | "just set", "Monday's", "this month", bare "now" | "Bitcoin *breaking* 80,000" |
| PRICE_NOW | "all-time" / "since" / "once" / any year exempts the whole line | "21 million", "640,000 bitcoin held" (if canon reads them as values) |
| current_levels | `PRESENT` includes "is"/"just", so predictions and past levels become "current" | — |
| DUPLICATE | Paraphrase | Share-of-token-set counts function words |

## Q5: Tests and R7

- **No test files are in this diff, and no R7 `pinned.py` patch is in it.** I cannot say whether tests fail for the right reason or whether R7 refuses an ungated package.
- What the diff does show:
  - The exam adapter calls `VF.check` without `current_levels` (L987), so PRICE_NOW is never exercised.
  - It never calls `duplicates`, the truth pass or `coherence`.
  - It never passes `a_by`, so the production precomputed-A path is untested.
  - It tests `moments.exclusion_verdict`, which `package.build` never calls (P1-3).
- `package_pin`'s hard-coded `True` (L1758) is a vacuous assertion baked into the artefact R7 will consume.

---

# FINDINGS

## P0

**P0-1: The VO fidelity verdict passes on an empty or partial claim list. Combined with deterministic holes, an unsupported, misattributed, imperative title clears both "must pass" layers.**

`pipeline/vo_fidelity.py`:
```python
2822 | if not isinstance(obj, dict) or set(obj) != {"claims"} or not isinstance(obj["claims"], list):
...
2842 | return {"ok": not v, "claims": obj["claims"], "violations": v}
```
No rule requires a claim per line, or even one claim. `{"claims": []}` gives `ok: True`.

**Failing input.** Writer title `{"text": "Saylor Says Buy Every Dip", "cites": []}`, where Saylor is not a speaker. `write_v2` accepts empty `cites` (L1531).

Deterministic layer, rule by rule:
- `_title_case` is true (Saylor, Says, Every are all capitalised), so `names_of` returns `[]` (L2654-2655).
- `_attributions` regex is case-sensitive (`re.escape(v)`, no `re.I`, L2681), so "Says" is not matched.
- IMPERATIVE needs `buy` at the start or after `[.!?:]` (L2571-2572), so it is not matched.
- No number, time word or quote.
- NEEDS_SOURCE is not triggered, so `cites: []` is fine.

Verdict layer: it returns claims for the intro only, or `[]`, so ok.

Result: `fid["ok"]` is True. This fails L-o 11 / L-t ("BOTH must pass"), L-l (a reply counts only whole) and M12.

## P1

**P1-1: Step B relation coverage is not required.** `context_integrity.py` L243-247 checks `takeaways ⊇ labels`, but `relations` may be `[]` or omit pairs. L287-295 only judges the pairs present.

Failing input: bridge "Natalie Brunell sees it the same way." It contains no RELATION regex word (L2564-2567), and step B returns `"relations": []`. No `FALSE_RELATION` is raised.

Fix: require exactly the C(n,2) pairs over `all_labels`.

**P1-2: The second recognition pass (L-v) is one-directional, selective, optional, and passes "not measured".**
- `compare` checks only selected-text tokens ⊆ the second pass (L2325-2329), as a bag of words over a window padded by 1.5 s.
  - A negation Whisper **dropped** is never detected. Clip text "Bitcoin is going to zero" against second pass "Bitcoin is not going to zero" gives `negations=[]`, so ok.
  - Worse, that segment has no numbers or negations, so `if any(TT.critical_tokens(sg["text"])[k] for k in ("numbers", "negations"))` (L1661) never runs the pass. Names never trigger it either.
- `speaker_turns` returns `turn_change_inside: None` when there are no labels (L2339), and `bad` only rejects truthy values (L1671). Not measured counts as a pass.
- `truth_dir=None` by default (L1554), and the plain path (L1637-1651) never runs truth.
- `audio_window` clamps `a = max(0.0, start - pad)` (L2273), but `speaker_turns(sec, PAD_S, …)` (L2347) assumes the offset is always `PAD_S`. Clips within 1.5 s of the video head are measured on the wrong span.

**P1-3: The exclusion verdict (L-u) never runs in production.** The exam measures it anyway.

`package.py` imports no `moments` and never calls `exclusion_verdict`. `usable()` trusts only the miner's self-reported `m["excluded"]` (L1069-1070, from L786). The adapter docstring claims "These are the SAME gates the packager runs (… moments.exclusion_verdict)" (L908-909).

Failing input: the miner (local gemma) returns `"risk": []` for a moment accusing a named company of fraud. It is packaged, and no independent exclusion gate runs.

**P1-4: Speaker is the channel by construction, so a guest's words can be attributed to the host and pass.**

`segs_v = {… {"speaker": s["channel"], "names": [s["channel"]], …}` (L1541). The `record` speaker fields are all `None` (L782-783).

Failing input: Saifedean Ammous, a guest on Natalie Brunell's channel, says "no authority can take your Bitcoin". VO: "Natalie Brunell says no authority can take your Bitcoin." ATTRIBUTION finds the owner "Natalie Brunell" and passes. The blind verdict sees `speaker="Natalie Brunell"` and passes.

The inverse is a false reject. WRITE_V2's own exemplar, "Saifedean Ammous: …" (L1376), fails NAME unless the clip says his name.

**P1-5: NUMBER binds to the last attribution, not the one governing the number.**

```python
2733 | for subj, verb in atts: ... else: att_pool = [t for c in owners ...]
2742 | if not _has_number(att_pool if atts else pool, val, unit):
```

Failing input: "Natalie Brunell says Bitcoin can hit 150,000; Coin Bureau says watch the ETFs." 150,000 appears only in Coin Bureau's segment. `att_pool` is Coin Bureau's, so NUMBER passes, but the number is misattributed to Natalie.

Reverse: a line where the first speaker's number is checked in the second speaker's pool is a false reject.

**P1-6: PRICE_NOW and `current_levels` false passes.**
- `HISTORY` (L2579-2580) exempts the whole line on `all-time|since|once|\d{4}`. Intro "Bitcoin just set an all-time high at $126,000" gives `price_now` → `[]`. "just set" is not in `TIME_WORDS` (L2574-2577), so it passes deterministically.
- `PRESENT` includes `is|are|just` (L1339-1340), so nearly every recent Bitcoin sentence counts as "current".
  - "Bitcoin was 16,000 in the bear and now is 74,000" makes both 16000 and 74000 current. Title "Bitcoin back at $16,000?" passes PRICE_NOW.
  - Predictions ("Bitcoin is going to 250,000") also become current levels.

**P1-7: The runtime arithmetic is internally inconsistent.**

```python
1048 | FIXED_S = round(E.TAIL_S - SIGNOFF_WORDS / WPS, 2)   # credits card + outro + transitions without VO
1257 | vo_s = vo_words / WPS + len(pk["vo"]["signoff"].split()) / WPS - SIGNOFF_WORDS / WPS
```

`runtime = segs + vo_s + FIXED_S = segs + VO + TAIL_S + (signoff − 36)/WPS`. That subtracts the standard sign-off twice, about 6.9 s. `content_range` and `budgets` (L1090-1092, L1180-1182) likewise omit the sign-off. I cannot see `E.TAIL_S`, but no single definition makes both lines right.

Example: 44 s of segments, 40 VO words, and a 20-word sign-off give an estimate of 67.55 s (passes). Under L1048's definition the true length is about 74.5 s, over the 60-70 s rule. The gate also runs on an *assumed* 2.6 w/s.

**P1-8: The pin asserts gate results it never reads.**

```python
1758 | "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
```

`to_pin` accepts any `pk`, including one with no `checks` key, a failed attempt's `pk`, or a plain package. The pin omits coherence and transcript-truth status. This is contrary to L-j's evidence requirement. Derive these values from `pk["checks"]` and refuse when they are absent.

**P1-9: L-x violation in `transcript_truth.py`.** See Q2. It also means the L-v pass cannot be recorded or replayed for the offline exam. When OpenAI is dry, every numbered segment is dropped. That is fail-closed, but it is not "no single model".

## P2

- **FRAMING false reject.** `"expose": r"expos\w*"` (L2568) matches "exposure". Caption "Why institutions want Bitcoin exposure" fails. `confirm\w*` matches "confirmation".
- **IMPERATIVE false reject.** `(^|[.!?:]\s*)(buy|sell|short|…)\b` (L2571) matches "Short-term holders are selling." and "Sell-offs like this have happened before." The `\b` falls before `-`. These are core on-chain phrases.
- **RELATION false reject.**
  - Bridge "Next, Coin Bureau on how Bitcoin responded to the rate hike" with one cite fails "implies an exchange" (L2753-2754).
  - "Bitcoin is the answer to money printing" with two videos also fails.
- **TIME false reject.** "Next, Coin Bureau on Bitcoin breaking 80,000" fails because `breaking` is in `TIME_WORDS`.
- **PRICE_NOW false reject.** Caption "Strategy now holds 640,000 bitcoin" gives 640000 ≥ 1000, so it is a "price level". The same applies to "21 million" if `canon` reads it as 21000000; that behaviour is not in the diff.
- **DUPLICATE false reject.** `share = len([t for t in ct if t in set(lt)]) / max(1, len(ct))` (L1481) counts function words.
  - Clip "Bitcoin is going to a million." against bridge "Next, Coin Bureau on why Bitcoin is going to matter to a lot of people" shares about 5 of 7 tokens, so it fails.
  - WRITE_V2 also asks for attribution "say what each channel says" right before the clip, which collides with this rule.
- **QUOTE false pass.** Single-quoted fabrications are never checked (L2605).
- **ATTRIBUTION false reject.** "She says …" gives "no cited segment is spoken by She".
- **`time_ok` defaults to pass.** `a.get("time_ok", "yes")` (L212, L277) is latent today because `_strict` requires the key, but any externally supplied `a_by` with the field missing passes STALE_TIME, contrary to M12.
- **Context window is "at most", not "at least".** L50/L59 include only sentences starting ≥ `t0−before` or ending ≤ `t1+after`, against the docstring's ">= 90 s / >= 60 s" (L11, L44). A sentence that starts at +50 s and ends at +65 s with a retraction is excluded.
- **Possible truncation of the excerpt.** `_q(contexts[lb]["text"], 6000)` (L186) may cut `<selected>` from a 240 s fast-speech window. `quote_data`'s truncation behaviour is not in the diff, so this is uncertain.
- **Spend guard fails open.**
  - `_spent()` returns `0.0` on an unreadable ledger (L2121-2122), and `_account` then overwrites it, erasing history.
  - The check and the call are not atomic, so parallel runs can overshoot.
- **Staging endpoint.** Heimdall `BASE = "https://api-staging.heimdallm.com/api/v1"` (L1969).
- **Arbitrary drop on outage.** `CONTEXT_UNAVAILABLE` (segment `"-"`) drops `order[-1]` (L1633). A provider outage discards a healthy moment.
- **Crash on missing age.** `window_sources`: `f"… ({age:.1f} h old …"` (L603) raises `TypeError` when `age is None` and the source is not new.
- **File-name collision.** `audio_window` matches files by `startswith(basename(base))` (L2281-2282), so `vid_1000_5000` matches `vid_1000_50000.*`.
- **Weaker legacy gate.** `gates()` (L1264-1275) has no DUPLICATE, no PRICE_NOW and no vendor re-check on `a_by_moment`. It is unused by `build` but importable.
- **Lost provenance.** When precomputed, `backends["A"] = "precomputed …"` (L239), so the package no longer names step A's model. This is contrary to L-x "every artefact names the model".
- **Truncated credit names.** `plain_vo` title `[:70]` (L1229) can cut a channel name mid-word.

---

## Single highest-leverage change

**Make every model verdict prove coverage, and fail closed on omission, in one shared helper used by all four verdicts:**
- `vo_fidelity.check_verdict`: every slot appears with at least one claim, or with an explicit `"no_claim": true`. Code then verifies that a no-claim line has no number, name, quote, attribution or time word.
- Step B: exactly the C(n,2) relation pairs.
- `coherence`: already exact.
- Truth pass: run on every segment. Compare in both directions (second-pass negations, numbers and names must appear in the clip text). `turn_change_inside is None` is a failure.

This closes P0-1, P1-1 and most of P1-2 with one rule: **a verdict that did not look at an item has not passed it.**