# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0829
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 68 s finish=stop usage in 19534 / out 4143 usd~0.121 (upper-bound price)

# Audit: pp-selectid 07:42–08:35 diff

## P0

**P0-1. `vo_fidelity.majority` — a 2-1 "pass" can pass a slot whose whole-reply failure ("-" slot) came from the *deterministic* layer's disagreement, and more importantly: the merged verdict's `ok` ignores per-run verdict `ok` when votes are 2-1 but the two passing runs' violations were on *other* slots.** Actually the concrete, verifiable defect: in `majority`, `verdict["ok"]` requires `2 * n_measured > len(runs) and not failed`, but `failed` is computed only from *slot* votes; a run whose verdict has a violation with `slot` not in `lines`' slots and not `"-"` (e.g. a typo'd slot key from the model, or a slot name mismatch like `"intro "` vs `"intro"`) votes "pass" (the vote condition `v.get("slot") in (s, "-")` finds nothing) yet its violation is silently dropped — it never reaches `viol` because `viol` only collects violations for *failed* slots. So: 3 runs, run 2 has a real violation with slot `"title "` (trailing space); votes = pass×3; slot passes; the violation vanishes from `out["violations"]` (line ~244: `out["violations"] = base["deterministic"]["violations"] + viol`). Failure scenario: model returns `{"slot": "intro "}` in one run → that run's violation is lost, gate passes, the sealed inventory shows PASS with no evidence of the dropped violation. This is a "never change what a check accepts" (LAW 20) exposure, though arguably within the ruling's letter. Rank: **P1** if slot keys are canonically guaranteed upstream (I cannot verify from the diff); **P0** if not. I'll call it P1.

**P0-2. `package.runtime` / `r4_max_vo_words` algebra — the closed-form no longer matches the constraint it claims to mirror.** Old: `VO_s <= SHARE * (content + VO_s + SIGNOFF + FIXED)` solved exactly. New (line 39): `vo_max = SHARE * (content_s + FINAL_TAIL_S) / (1 - SHARE)`; then `r4_max_vo_words` returns `R4_WPS * (vo_max - R4_PREROLL_S * n_vo)` (line 40). But `runtime()` computes VO seconds as `sum(len(t.split())/R4_WPS + R4_PREROLL_S)` — i.e. words→seconds is `w/R4_WPS + PRE*n`, so inverting gives `w = (vo_s - PRE*n) * R4_WPS`. That matches. However the *share* constraint: `VO_s <= SHARE * (content + VO_s + TAIL)` ⇒ `VO_s <= SHARE*(content+TAIL)/(1-SHARE)` — correct. But `runtime()` rounds the total to 2 dp and, critically, `r4()` (the actual gate) reads `pk["runtime_s_estimate"]` which was produced by `runtime()` from the *actual* VO lines, while `r4_max_vo_words`/`budgets` are advisory. The inconsistency to flag: `content_range`'s upper bound (line 58) is `RUNTIME_S[1] - FINAL_TAIL_S - VO_S[0] - R4_PREROLL_S * n_vo` — this uses `VO_S[0]` (a *word* count? a *seconds* range? — `VO_S[1] * WPS` at line 72 implies VO_S is in words/second units, i.e. VO_S[0] is a w/s floor) subtracted from a *seconds* quantity. In the old code the same expression existed, so if it was right before it's right now — but the new term `R4_PREROLL_S * n_vo` subtracts seconds of pre-roll while `VO_S[0]` (w/s) is not multiplied by anything: dimensionally `RUNTIME_S[1] - FINAL_TAIL_S` is seconds, `VO_S[0]` is words-per-second — subtracting a rate from seconds is only coherent if VO_S[0] is actually seconds. I cannot verify VO_S's units from the diff; if VO_S is (min_wps, max_wps) as line 72 (`VO_S[1] * WPS` → words) suggests, then `VO_S[0]` here is a unit error *carried over* — flag as **P1, uncertain**.

## P1

**P1-1. `majority` — `replayed` tri-state: `None if any(not isinstance(x, bool) ...) else any(reps)` (line 239).** `any(reps)` over 3 runs returns True if *one* run replayed. The inventory row (package.py:101-104) passes `replayed` into `row(...)`, and test_angles.py:518 asserts `g[row]["replayed"] is not False` for PASS rows — consistent. But `any()` means a majority of *fresh* (non-replayed) runs is reported as `replayed=True` if one run replayed; the honest aggregate is "all replayed" or a per-run list (which IS recorded in `majority.runs`). Minor honesty issue, not a gate decision. **P2** really. Also: if a run's `replayed` key is *absent* (None), `not isinstance(None, bool)` → True → returns None — good, fail-honest.

**P1-2. `majority` — unmeasured-run vote.** Line 217-219: vote "pass" requires `r.get("measured")` — an unmeasured run votes "fail" ✓ (L-m). But `verdict["ok"]` also requires `2 * n_measured > len(runs)`: with 3 runs, 1 measured + 2 unmeasured → `2*1 > 3` false → ok=False even if the measured run passed. Test (test_gates.py:616-617) confirms. Correct. However: 2 measured + 1 unmeasured, both measured runs pass → ok=True, but the *unmeasured* run's absence is recorded only as a "fail" vote in a 2-1 split — the ruling says a split "is recorded, never hidden" ✓. No defect.

**P1-3. `self_repair` (transcript_truth.py:129-142) — the 4-letter prefix check `fw[:4] == _w(first)[:4]`.** If the clip's first word is shorter than 4 letters (e.g. "It", "So", "AI"), `fw[:4]` 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 155 s finish=stop usage in 19227 / out 813 usd~0.116 (upper-bound price)

**P0: pipeline/package.py:27 (and :15, :38, :109, :64)**  
R4_MOMENTS_SHARE changed from 0.40 to 0.45 and all derived functions (r4_max_vo_words, min_vo_words, content_range, r4, runtime, inventory) updated to the new factory-mirror formula. Concrete failure: construct pk with segments summing to 29.91 s content + VO lines of 27/18/18 words (the original 05:35-06:00 numbers). Old code produced runtime ~68 s, R4=41.0 % → FAIL. New code produces runtime=72.41 s, R4=38.9 % → PASS (and the test in test_angles.py:506 now asserts True). This alters the gate's acceptance region so that a package previously rejected by r4 now passes, violating LAW 20/M2 ("gate thresholds are constants; never change what a check accepts to make a render pass") and the explicit audit constraint "never change what a check accepts in order to make a render pass".

**P1: pipeline/package.py:23 (runtime) / :39 (r4_max_vo_words) / tests/package/test_angles.py:488**  
The new runtime() / r4_max_vo_words arithmetic is asserted to match edl_rules._r4_moments but the test only checks one point (30 s segments + two VO lines → 56.3 s). No proof is given that the algebraic rearrangement (vo_max = SHARE * (content + TAIL) / (1-SHARE)) is algebraically identical for every legal (content_s, n_vo) pair, nor that the rounding to 2 decimals cannot flip a borderline 70.00 s package across the hard runtime gate. Uncertain whether this is exactly faithful on all paths; the diff supplies no exhaustive check.

**P2: pipeline/transcript_truth.py:154 (self_repair call in edges) / :174 (verify_segment)**  
self_repair() correctly rejects every case the new test supplies (different speaker, no dash, full repetition, multiple tokens, no prior sentence end). However the fw[:4] == _w(first)[:4] prefix match is a heuristic; the diff gives no input that would make a non-repair token (e.g. a same-speaker "Bit." that is not a prefix but shares the first 4 cleaned characters) incorrectly trigger the skip, so it is impossible to verify from the diff alone that "nothing else can slip through" as required by ruling 8. The law SENTENCE LAW (fail-closed on unpunctuated stretches) is therefore only partially provable from the supplied code.

**P2: pipeline/vo_fidelity.py:234 (verdict["ok"])**  
majority() correctly treats unmeasured runs as "fail" votes, refuses even run counts, records splits, and never lets a slot that most runs failed count as PASS. The test in test_gates.py:609 exercises 2-1, 1-2, and insufficient-measurement cases. However the merged "violations" list can contain duplicate entries from the minority runs (the seen set only deduplicates inside one slot); the diff does not show that the gate inventory row produced by package.inventory remains byte-identical to what release_auth.py expects under L-j. Minor risk of non-deterministic inventory shape.

No other violations of the listed laws (L-a through L-l, SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, L-j release-on-exact-bytes, M12 fail-closed, LAW 20/M2, L-d protected preview) can be concretely triggered from the diff text alone; the added pin_and_verify.py, --precheck path, renderer_geometry evidence, and canon-aware tests all stay inside the permitted "smallest diff, no new renderer/selector" envelope.

SHIP: no

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 111 s finish=stop usage in 21533 / out 3788 usd~0.121 (upper-bound price)

# Code Audit: pp-selectid-0829 (C1_STEP.diff)

## P0 Findings

### P0-1: `vo_fidelity.majority` allows a slot to pass when the majority of runs failed it
**File:** `pipeline/vo_fidelity.py`, lines 220–235 (in diff)

The voting logic at line 220 is:
```python
failed = [s for s, vs in votes.items() if 2 * vs.count("pass") <= len(runs)]
```
For 3 runs, a slot is marked `failed` only when `pass_count <= 1`. A 2-1 split (2 pass, 1 fail) is **not** added to `failed`.

However, the verdict `ok` at line 234 is:
```python
"ok": 2 * n_measured > len(runs) and not failed
```
This means a slot with votes `["pass", "pass", "fail"]` passes the majority gate. **This is correct per the ruling** ("majority decides"). But the deeper issue is in the **violation aggregation** (lines 221–230):

When a slot is in `failed`, it collects violations from **all** runs where `v.get("slot") in (s, "-")`. But when a slot is **not** in `failed` (i.e., it passed by majority), **no violations are collected for that slot at all**, even if one of the failing runs had a specific violation on that slot. This is actually correct behavior (the majority passed it), so this is not a bug.

**Re-evaluation:** The logic is actually sound. A 2-1 pass means the slot passes. A 1-2 or 0-3 means it fails and violations are collected. The `n_measured` check ensures at least 2 of 3 runs were measured. **No P0 here.**

### P0-2: `self_repair` in `verify_segment` drops the token from `span` but the `compare` function may still see a mismatch
**File:** `pipeline/transcript_truth.py`, lines 171–176 (in diff)

```python
if len(sw) > 1 and toks and self_repair(sw, 0, toks[0]):
    repair, span = sw[0]["text"], " ".join(w["text"] for w in sw[1:]).strip()
cmp_ = compare(text, span)
```

The `span` is rebuilt from `sw[1:]`, dropping the self-repair token. The `text` parameter is the **primary** transcript's text for the clip. The `compare` function compares `text` against `span`. If the primary transcript does **not** contain the self-repair token (which is the premise: "heard by the second recogniser and not by the primary"), then `text` starts with the first real word, and `span` now also starts with the first real word. This should align.

**However**, there is a subtle issue: `self_repair(sw, 0, toks[0])` checks that `sw[0]` is a truncated prefix of `sw[1]` and that `sw[1]` matches `toks[0]` (the first token of the primary text). But `toks` is derived from `text` via `re.findall(r"[\w'’$%.,-]+", text or "")`. If the primary text's first word is "Bitcoin" and the second recogniser's `sw[1]` is "bitcoin" (lowercase), `_w()` normalizes both to "bitcoin", so the 4-letter prefix check `fw[:4] == _w(first)[:4]` passes. This is fine.

**But**: what if the primary text's first word is "Bitcoin" and the second recogniser's `sw[0]` is "Bit-" and `sw[1]` is "bitcoin"? The `self_repair` function checks `fw.startswith(stem)` where `stem = _w("Bit-".rstrip("-")) = "bit"` and `fw = _w("bitcoin") = "bitcoin"`. `"bitcoin".startswith("bit")` is True. `len("bit") < len("bitcoin")` is True. The speaker check passes. So it is correctly identified.

**Potential issue:** The `edges()` function (lines 153–163) also calls `self_repair(ws, j, first)` where `first` is the clip's first word from the **primary** transcript. But in `edges()`, `ws` is the second recogniser's words, and `first` is passed from the `text` parameter. The `self_repair` function compares `fw[:4] == _w(first)[:4]`. If the primary's first word is "Bitcoin" and the second recogniser's `ws[i+1]` is "bitcoin", this works. But what if the primary's first word is "Bit" (a different word entirely)? Then `_w(first)[:4] = "bit"` and `fw[:4] = "bit"`, so it would incorrectly match. However, the `fw.startswith(stem)` check requires that the second recogniser's word is a **fuller** version of the truncated token, and the 4-letter prefix is a heuristic. This is a **weak heuristic** but is bounded by the orchestrator's ruling. **Not a P0, but a P2 concern.**

### P0-3: `package.runtime()` mirror may not be faithful to the deployed factory
**File:** `pipeline/package.py`, lines 17–24 (in diff)

The new `runtime()` uses:
```python
vo = sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in vo_lines if t and t.strip())
return round(sum(m["duration_s"] for m in segs) + vo + FINAL_TAIL_S, 2)
```

The docstring says it mirrors `edl_rules._r4_moments` from main `a5ec0f17`. The key question: does the deployed factory's `_r4_moments` use the **same** `R4_WPS` (2.5), `R4_PREROLL_S` (1.0), and `FINAL_TAIL_S` (14.30)? The diff does not show `edl_rules.py`, so I **cannot verify** the mirror is faithful. The test at line 488–490 hardcodes `14.30` and `2.5`, which matches the docstring, but if the deployed factory uses different constants, the mirror is wrong.

**This is a P1, not P0**, because the test pins the expected values, and the docs

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of the 07:42-08:40 diff: cycle 1 consensus (synthesis by the pp-selectid session, 08:45 ET Nov 12)

**Run.** Cycle 1 ran on C1_STEP.diff: 42,648 bytes, prompt 65,170 bytes. The reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP no;
- qwen/qwen3.8-27b, Heimdall, reasoning effort none: SHIP yes with conditions;
- z-ai/glm-5.3-flash, Heimdall, effort none: SHIP yes with conditions.

The earlier attempt through the router's JSON back-end (08:01) returned empty replies and is void.

**The rule** is the same as tonight's earlier audits: consensus (two or more reviewers) is implemented, and a unique
finding is evaluated on its evidence.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | self_repair's 4-letter match against the clip's first word is a weak heuristic (grok P2, qwen P1-4 / P2-1, glm P1-3) | IMPLEMENTED: the next word must BE the clip's first word (`_w(next) == _w(first)`, non-empty), so a repair is one dash-ended, same-speaker, proper prefix of exactly that word |
| K2 | the R4 algebra (r4_max_vo_words / min_vo_words against runtime()): qwen and glm verified it by hand; grok asked for proof on every path | IMPLEMENTED as a test: `test_the_r4_word_bounds_invert_runtime_and_the_share_exactly`, over content 15-50 s and 1-4 VO lines. The bound passes; one word more (share) or one word less (60 s) fails |

## Unique findings, evaluated

| finding | disposition |
|---|---|
| grok P0: the runtime / R4 change accepts a package the old gate refused (63 words: R4 41.0 % -> 38.9 %) | KEPT, disclosed. That package is still refused, now by the runtime gate (72.41 s > 70; test_the_moments_r4_on_tonights_numbers). The 45 % cap is the orchestrator's ruling 9, and the deployed edl_rules.py reads MOMENTS_VO_SHARE = 0.45. runtime() is the factory's own arithmetic, read in the deployed edl_rules._r4_moments and pinned.py:290: the gate now refuses exactly what the consumer refuses. The 60 s floor moved: the builder's old estimate was 3-4 s lower. That is disclosed in STATE (07:58: 57.88 s vs 61.23 s), and the render measures the final (design section 8, open) |
| glm P0-1 / P1: majority drops a violation whose slot is not a line slot | REFUTED on the code: check_verdict raises on a claim whose line is not a slot (vo_fidelity.py: `c["line"] not in by_slot` -> ValueError -> VERDICT_UNAVAILABLE, slot "-", not measured), and an unmeasured run votes "fail" on every slot. Hardened anyway (H1): a violation on an unknown slot now fails every slot |
| glm P2-1: does FINAL_TAIL_S hold the sign-off? | CONFIRMED: the deployed edl_rules.py:156 reads `FINAL_TAIL_S = 14.30  # ... credits card + sign-off, outro, cut ...`, equal to eligibility.TAIL_S |
| glm P1-6: is renderer_geometry inside the seal? | OUTSIDE, as intended: package_pin.seal hashes segments, VO, sign-off, title, caption and gates; cut_evidence travels beside the seal (to_pin) |
| glm P1-4: the repaired span loses punctuation | REFUTED: span_text joins t

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0742/C2_STEP.diff (865 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index ec029024..51f24c7d 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -106,39 +106,53 @@ def time_sensitive(m):
   6 |          any(kind == "current" for _, kind in VF.price_mentions(t))
   7 |  
   8 |  
   9 | -def runtime(segs, vo_s):
  10 | -    """segments' word spans + every spoken VO second (intro, bridges AND the sign-off) + FIXED_S (audit p2 M4)."""
  11 | -    return round(sum(m["duration_s"] for m in segs) + vo_s + FIXED_S, 2)
  12 | +FINAL_TAIL_S = E.TAIL_S             # what a final adds to its word spans (credits card + sign-off, outro, cut edges, pads)
  13 |  
  14 |  
  15 | -R4_MOMENTS_SHARE = 0.40            # orchestrator 06:00 ruling 4: moments-first VO up to 40 % of the runtime; a VO line
  16 | -                                   # after the hook, after every clip and after the last clip; 60-70 s stays hard
  17 | +def runtime(segs, vo_lines):
  18 | +    """The FACTORY's own estimate, the one its hard 60-70 s check reads (edl_rules._r4_moments, main a5ec0f17: "hook +
  19 | +    clips + VO + FINAL_TAIL_S", each VO line "words / 2.5 + the 1.0 s pre-roll"): segments' word spans + every VO line
  20 | +    (intro, bridges) at R4_WPS w/s + R4_PREROLL_S each + FINAL_TAIL_S (the sign-off is inside it). It replaced (07:42)
  21 | +    this module's own estimate (2.6 w/s, no pre-roll, FIXED_S + the sign-off), which ran 3-4 s lower than the factory's
  22 | +    on three VO lines. Neither is a measurement: the render measures the final (design section 8, open)."""
  23 | +    vo = sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in vo_lines if t and t.strip())
  24 | +    return round(sum(m["duration_s"] for m in segs) + vo + FINAL_TAIL_S, 2)
  25 | +
  26 | +
  27 | +MOMENTS_TAKEAWAY_WORD_CAP = 30     # orchestrator 08:40 ruling 10: the VO line after the LAST clip (the takeaway) of a
  28 | +                                   # moments pin; bridges BETWEEN clips keep config.BRIDGE_WORD_CAP (20)
  29 | +R4_MOMENTS_SHARE = 0.45            # orchestrator 08:29 ruling 9: moments-first VO up to 45 % of the TOTAL runtime (06:00
  30 | +                                   # ruling 4 said 40 %); a VO line after the hook, after every clip and after the last
  31 | +                                   # clip; 60-70 s stays hard
  32 |  
  33 |  
  34 |  def r4_max_vo_words(content_s, n_vo):
  35 |      """The most VO words (intro + bridges) the moments-first R4 allows: edl_rules' own estimate (words / 2.5 + 1 s per
  36 | -    VO line) <= 40 % of the runtime estimate (content + VO and the standard sign-off at WPS + FIXED_S)."""
  37 | -    num = R4_MOMENTS_SHARE * (content_s + SIGNOFF_WORDS / WPS + FIXED_S) - R4_PREROLL_S * n_vo
  38 | -    return max(0, int(num / (1 / R4_WPS - R4_MOMENTS_SHARE / WPS)))
  39 | +    VO line) <= R4_MOMENTS_SHARE of the runtime estimate (runtime(): content + that VO + FINAL_TAIL_S)."""
  40 | +    # VO_s = w / R4_WPS + PRE * n ; runtime = content + VO_s + TAIL ; VO_s <= SHARE * runtime
  41 | +    vo_max = R4_MOMENTS_SHARE * (content_s + FINAL_TAIL_S) / (1 - R4_MOMENTS_SHARE)
  42 | +    return max(0, int(R4_WPS * (vo_max - R4_PREROLL_S * n_vo)))
  43 |  
  44 |  
  45 | -def min_vo_words(content_s):
  46 | -    """The fewest VO words (intro + bridges) that land 60 s: content + VO + the standard sign-off + FIXED_S >= 60."""
  47 | -    return max(0, int(WPS * (RUNTIME_S[0] - content_s - SIGNOFF_WORDS / WPS - FIXED_S) + 0.999))
  48 | +def min_vo_words(content_s, n_vo=2):
  49 | +    """The fewest VO words (intro + bridges) that land 60 s by the factory's estimate (runtime())."""
  50 | +    return max(0, int(R4_WPS * (RUNTIME_S[0] - content_s - FINAL_TAIL_S - R4_PREROLL_S * n_vo) + 0.999))
  51 |  
  52 |  
  53 |  def content_range(n_clips=2):
  54 |      """Seconds the segments may fill so that some VO lands the runtime in 60-70 s AND fits R4 (one VO line for the
  55 |      intro + one bridge per clip but the last)."""
  56 |      n_vo = 1 + (n_clips - 1)
  57 | -    lo = next(c / 10 for c in range(200, 700) if min_vo_words(c / 10) <= r4_max_vo_words(c / 10, n_vo))
  58 | -    return lo, RUNTIME_S[1] - FIXED_S - SIGNOFF_WORDS / WPS - VO_S[0]
  59 | +    lo = next(c / 10 for c in range(200, 700) if min_vo_words(c / 10, n_vo) <= r4_max_vo_words(c / 10, n_vo))
  60 | +    return lo, RUNTIME_S[1] - FINAL_TAIL_S - VO_S[0] - R4_PREROLL_S * n_vo          # runtime()'s own terms
  61 |  
  62 |  
  63 |  def r4(pk):
  64 |      """R4 for a moments-first package, as the orchestrator ordered it at 06:00 (ruling 4; the integrator brings
  65 | -    edl_rules.rule_r4 to it): VO (intro + bridges, edl_rules' estimate 2.5 w/s + 1 s per line) <= 40 % of the runtime
  66 | -    estimate; the word caps of config.py; at most one VO line after each clip (the last clip included).
  67 | +    edl_rules.rule_r4 to it; the cap is 45 % since ruling 9, 08:29): VO (intro + bridges, edl_rules' estimate 2.5 w/s +
  68 | +    1 s per line) <= R4_MOMENTS_SHARE of the runtime
  69 | +    estimate; the word caps of config.py (the takeaway after the LAST clip: MOMENTS_TAKEAWAY_WORD_CAP, ruling 10);
  70 | +    at most one VO line after each clip (the last clip included).
  71 |      -> (ok, reason). The share over clips + VO (today's edl_rules denominator) is reported beside it."""
  72 |      from config import BRIDGE_WORD_CAP, INTRO_WORD_CAP
  73 |      n_clips = len(pk["segments"]) - 1
  74 | @@ -151,7 +165,11 @@ def r4(pk):
  75 |      fails = []
  76 |      if words[0] > INTRO_WORD_CAP:
  77 |          fails.append(f"intro {words[0]} words (max {INTRO_WORD_CAP})")
  78 | -    fails += [f"bridge {i + 1} {w} words (max {BRIDGE_WORD_CAP})" for i, w in enumerate(words[1:]) if w > BRIDGE_WORD_CAP]
  79 | +    for i, w in enumerate(words[1:]):          # ruling 10: the line after the LAST clip is the takeaway (cap 30)
  80 | +        last = i < len(after) and after[i] == n_clips
  81 | +        cap = MOMENTS_TAKEAWAY_WORD_CAP if last else BRIDGE_WORD_CAP
  82 | +        if w > cap:
  83 | +            fails.append(f"{'takeaway' if last else 'bridge'} {i + 1} {w} words (max {cap})")
  84 |      if len(set(after)) != len(after) or any(type(a) is not int or not 1 <= a <= n_clips for a in after):
  85 |          fails.append(f"bridges after clips {after}: one per clip, 1..{n_clips}")
  86 |      if share > R4_MOMENTS_SHARE:
  87 | @@ -164,7 +182,7 @@ def r4(pk):
  88 |  def budgets(content_s, n_bridges=1):
  89 |      """Word budgets (intro, each bridge, (min, max) total) that land 60-70 s and fit R4; 40 % to the intro."""
  90 |      hi = min(r4_max_vo_words(content_s, 1 + n_bridges), int(VO_S[1] * WPS))
  91 | -    lo = min(min_vo_words(content_s), hi)
  92 | +    lo = min(min_vo_words(content_s, 1 + n_bridges), hi)
  93 |      return max(6, int(hi * 0.4)), max(4, int(hi * 0.6 / max(1, n_bridges))), (lo, hi)
  94 |  
  95 |  
  96 | @@ -214,11 +232,11 @@ def assemble(order, by_id, fields, ctx, vo_kind):
  97 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
  98 |            "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
  99 |            "lines": lines}
 100 | -    so_words = len(pk["vo"]["signoff"].split())
 101 | -    pk["runtime_s_estimate"] = runtime(segs, (vo_words + so_words) / WPS)
 102 | -    pk["runtime_note"] = (f"segments {sum(m['duration_s'] for m in segs):.2f} s (word timing) + VO {vo_words} words + "
 103 | -                          f"sign-off {so_words} words at {WPS} w/s (assumed) + fixed {FIXED_S} s (credits card, outro, "
 104 | -                          f"transitions); the render measures the final")
 105 | +    vo_lines = [pk["vo"]["intro"]] + list(pk["vo"]["bridges"])
 106 | +    pk["runtime_s_estimate"] = runtime(segs, vo_lines)
 107 | +    pk["runtime_note"] = (f"segments {sum(m['duration_s'] for m in segs):.2f} s (word timing) + VO {vo_words} words at "
 108 | +                          f"{R4_WPS} w/s + {R4_PREROLL_S} s pre-roll per line + tail {FINAL_TAIL_S} s (sign-off, credits, "
 109 | +                          f"outro, edges): the factory's own R4 estimate; the render measures the final")
 110 |      return pk
 111 |  
 112 |  
 113 | @@ -572,16 +590,46 @@ def paid_gates(router, pk, sources, a_by, levels, now, writers_v, writers_f, poo
 114 |      return f_fid.result(), f_ctx.result()
 115 |  
 116 |  
 117 | -def exclusion_for(router, m, sources, cache):
 118 | -    if m["moment_id"] not in cache:
 119 | +def exclusion_for(router, m, sources, cache, seed=7):
 120 | +    key = m["moment_id"] if seed == 7 else (m["moment_id"], seed)
 121 | +    if key not in cache:
 122 |          import moments as M
 123 |          src = sources[m["video_id"]]
 124 |          a, b = CI.window(src, m["sentences"][0], m["sentences"][1])
 125 |          w0, w1 = m["words"]
 126 | -        cache[m["moment_id"]] = M.exclusion_verdict(
 127 | +        cache[key] = M.exclusion_verdict(
 128 |              router, m["text"], E.spoken(src.tokens[src.sentences[a][0]:w0]),
 129 | -            E.spoken(src.tokens[w1 + 1:src.sentences[b][1] + 1]), avoid_model=(m.get("mined") or {}).get("by"))
 130 | -    return cache[m["moment_id"]]
 131 | +            E.spoken(src.tokens[w1 + 1:src.sentences[b][1] + 1]), seed=seed,
 132 | +            avoid_model=(m.get("mined") or {}).get("by"))
 133 | +    return cache[key]
 134 | +
 135 | +
 136 | +MAJORITY_SEEDS = (7, 8, 9)
 137 | +
 138 | +
 139 | +def once_then_majority(run, ok, seeds=MAJORITY_SEEDS):
 140 | +    """Orchestrator 08:18 item 4 / 08:29: a model-judged verdict that is not PASS on its first run gets the three-run
 141 | +    majority (07:42 item 3) ONCE; whole gate sets are never rerun. run(seed) -> a result; ok(result) -> True only for a
 142 | +    MEASURED pass. -> (passed, results, votes): the first result alone when it passes, else all three and a pass only
 143 | +    when more than half of them pass (an unmeasured run is a "fail" vote, law L-m)."""
 144 | +    first = run(seeds[0])
 145 | +    if ok(first):
 146 | +        return True, [first], ["pass"]
 147 | +    res = [first] + [run(sd) for sd in seeds[1:]]
 148 | +    votes = ["pass" if ok(x) else "fail" for x in res]
 149 | +    return 2 * votes.count("pass") > len(res), res, votes
 150 | +
 151 | +
 152 | +def with_votes(results, votes, passed, seeds=MAJORITY_SEEDS):
 153 | +    """The record a gate reads after once_then_majority: the first PASSING run when the majority passed (else the first
 154 | +    run), with "majority" = {"votes", "seeds", "runs": every result} and a replayed tri-state over ALL runs (C2 K4)."""
 155 | +    rep = next((x for x, v in zip(results, votes) if v == "pass"), results[0]) if passed else results[0]
 156 | +    out = dict(rep)
 157 | +    if len(results) > 1:
 158 | +        reps = [x.get("replayed") for x in results]
 159 | +        out["majority"] = {"votes": votes, "seeds": list(seeds[:len(results)]), "runs": results}
 160 | +        out["replayed"] = None if any(not isinstance(x, bool) for x in reps) else any(reps)
 161 | +    return out
 162 |  
 163 |  
 164 |  def truth_for(router, m, work_dir, cache):
 165 | @@ -770,6 +818,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 166 |          "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
 167 |          "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin
 168 |  
 169 | +    votes_of = lambda x: {"votes": x["majority"]["votes"]} if isinstance(x, dict) and x.get("majority") else {}
 170 | +
 171 |      def rep(values):                                 # tri-state over several replies (audit C2 K4)
 172 |          values = list(values)
 173 |          return None if any(not isinstance(x, bool) for x in values) else any(values)
 174 | @@ -778,24 +828,30 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 175 |      a_rows = list((a_by or {}).values())
 176 |      return {
 177 |          "vo_fidelity_deterministic": row(det["ok"], "code (vo_fidelity.check_deterministic)"),
 178 | -        "vo_fidelity_verdict": row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"), fid.get("replayed"),
 179 | -                                   measured=bool(fid.get("measured"))),
 180 | +        "vo_fidelity_verdict": dict(row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"),
 181 | +                                        fid.get("replayed"), n=fid.get("runs", 1), measured=bool(fid.get("measured"))),
 182 | +                                    **({"votes": fid["majority"]["votes"], "splits": fid["majority"]["splits"]}
 183 | +                                       if fid.get("majority") else {})),          # ruling 07:42 (3): the majority
 184 |          "duplicate": row(not dup, "code (package.duplicates)"),
 185 |          "price_now": row(not any(v["rule"] == "PRICE_NOW" for v in det["violations"]),
 186 |                           "code (vo_fidelity.price_now)", measured=bool(det.get("price_now_measured"))),
 187 | -        "runtime": row(rt_ok, f"code (estimate at {WPS} w/s)"),
 188 | +        "runtime": row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 189 | +                              f"{FINAL_TAIL_S} s tail)"),
 190 |          "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
 191 |          "context_a": row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
 192 |                           sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 193 |                           n=len(a_rows)),
 194 | -        "context_b": row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
 195 | -                         measured=bool(ctx_.get("measured"))),
 196 | -        "context_c": row(ctx_.get("ok") is True and not (viol & {"NOT_ENTAILED", "POLARITY", "STRONGER"}),
 197 | -                         (ctx_.get("backends") or {}).get("C"), ctx_.get("replayed"), measured=bool(ctx_.get("measured"))),
 198 | -        "exclusion": row(all(e.get("verdict") == "keep" for e in exc.values()),
 199 | -                         sorted({str(e.get("backend")) for e in exc.values()}),
 200 | -                         rep(e.get("replayed") for e in exc.values()), n=len(exc),
 201 | -                         measured=all(e.get("measured") for e in exc.values())),
 202 | +        "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
 203 | +                              measured=bool(ctx_.get("measured"))), **votes_of(ctx_)),
 204 | +        "context_c": dict(row(ctx_.get("ok") is True and not (viol & {"NOT_ENTAILED", "POLARITY", "STRONGER"}),
 205 | +                              (ctx_.get("backends") or {}).get("C"), ctx_.get("replayed"),
 206 | +                              measured=bool(ctx_.get("measured"))), **votes_of(ctx_)),
 207 | +        "exclusion": dict(row(all(e.get("verdict") == "keep" for e in exc.values()),
 208 | +                              sorted({str(e.get("backend")) for e in exc.values()}),
 209 | +                              rep(e.get("replayed") for e in exc.values()), n=len(exc),
 210 | +                              measured=all(e.get("measured") for e in exc.values())),
 211 | +                          **({"votes": {k: e["majority"]["votes"] for k, e in exc.items() if e.get("majority")}}
 212 | +                             if any(e.get("majority") for e in exc.values()) else {})),
 213 |          "second_pass": row(all(t.get("ok") for t in truth.values()), sorted({str(t.get("model")) for t in truth.values()}),
 214 |                             rep(t.get("replayed") for t in truth.values()), n=len(truth),
 215 |                             measured=all("error" not in t for t in truth.values())),
 216 | @@ -803,5 +859,6 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 217 |                          "transcript_truth.edges: the independent recogniser's sentence boundary at every IN and OUT "
 218 |                          "(orchestrator 06:45 ruling C / 7)", rep(t.get("replayed") for t in truth.values()), n=len(truth),
 219 |                          measured=all("edges" in t for t in truth.values())),
 220 | -        "coherence": row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 221 | +        "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 222 | +                          **votes_of(coh)),
 223 |      }
 224 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
 225 | index 5b8a4abf..bfc8f44f 100644
 226 | --- a/pipeline/transcript_truth.py
 227 | +++ b/pipeline/transcript_truth.py
 228 | @@ -117,12 +117,29 @@ def speaker_turns(second, start_rel, end_rel):
 229 |  
 230 |  
 231 |  TERMINAL = (".", "!", "?")
 232 | +REPAIR_DASHES = ("-", "\u2013", "\u2014")
 233 |  
 234 |  
 235 |  def _w(t):
 236 |      return re.sub(r"[^\w']", "", (t or "").lower().replace("’", "'"))
 237 |  
 238 |  
 239 | +def self_repair(words, i, first):
 240 | +    """Orchestrator ruling 8 (08:29): words[i] is a SELF-REPAIR of the clip's first word when it is a truncated
 241 | +    repetition of it by the same speaker: it ends in a dash, its letters are a non-empty proper prefix of the next
 242 | +    word's, the next word is the clip's first word, and both carry the same speaker label (a missing label is not the
 243 | +    same speaker). Heard by the second recogniser and not by the primary, it belongs to the sentence it opens: not a
 244 | +    missing sentence start, not an L-v 2 disagreement. Exactly one such token; anything else is not one. The next word
 245 | +    must BE the clip's first word (the same letters, case and punctuation aside; audit 0742 C1 K1: no 4-letter match)."""
 246 | +    if not 0 <= i < len(words) - 1:
 247 | +        return False
 248 | +    r, f = words[i], words[i + 1]
 249 | +    t = (r.get("text") or "").strip()
 250 | +    stem, fw, fst = _w(t.rstrip("".join(REPAIR_DASHES))), _w(f.get("text")), _w(first)
 251 | +    return (t.endswith(REPAIR_DASHES) and bool(stem) and bool(fst) and fw == fst and len(stem) < len(fw)
 252 | +            and fw.startswith(stem) and r.get("speaker") is not None and r.get("speaker") == f.get("speaker"))
 253 | +
 254 | +
 255 |  def edges(second, wav_start, start, end, text):
 256 |      """CUTTABLE (orchestrator 06:45 ruling C, ruling 7 (1)): the INDEPENDENT recogniser's own sentence boundaries at
 257 |      the segment's edges, from its word timing on the SOURCE audio. IN: the recogniser's word at the clip's first word
 258 | @@ -142,11 +159,17 @@ def edges(second, wav_start, start, end, text):
 259 |            and _w(w["text"]).rstrip(".")[:4] == last.rstrip(".")[:4]]
 260 |      if ci:
 261 |          i = ci[0]
 262 | -        prev = ws[i - 1]["text"] if i > 0 else None
 263 | +        j, repair = i - 1, None
 264 | +        if self_repair(ws, j, first):           # ruling 8: the speaker's false start opens the sentence
 265 | +            repair, j = ws[j]["text"], j - 1
 266 | +        prev = ws[j]["text"] if j >= 0 else None
 267 |          out["in"] = {"ok": prev is not None and prev.rstrip().endswith(TERMINAL), "word": ws[i]["text"],
 268 |                       "before": prev, "why": "a sentence ends before the clip" if prev and prev.rstrip().endswith(TERMINAL)
 269 |                       else ("the window starts at the clip: no word before it" if prev is None else
 270 |                             f"the recogniser runs on into the clip ('{prev}')")}
 271 | +        if repair:
 272 | +            out["in"].update(self_repair=repair, why=out["in"]["why"] + f"; the speaker's false start '{repair}' "
 273 | +                             "opens the sentence (ruling 8: a self-repair, part of the sentence)")
 274 |      else:
 275 |          out["in"] = {"ok": False, "why": f"the recogniser has no '{first}' within 0.6 s of the clip's start"}
 276 |      if co:
 277 | @@ -170,10 +193,15 @@ def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_s
 278 |      sec, rep = second_pass(router, wav)
 279 |      off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_S))
 280 |      span = span_text(sec, off, off + (end - start)) or sec["text"]
 281 | +    sw = [w for w in sec.get("words") or [] if _inside(w, off, off + (end - start))]
 282 | +    toks = re.findall(r"[\w'’$%.,-]+", text or "")
 283 | +    repair = None
 284 | +    if len(sw) > 1 and toks and self_repair(sw, 0, toks[0]):     # ruling 8: only a LEADING self-repair, only one
 285 | +        repair, span = sw[0]["text"], " ".join(w["text"] for w in sw[1:]).strip()
 286 |      cmp_ = compare(text, span)
 287 |      turns = speaker_turns(sec, off, off + (end - start))
 288 |      return {"video_id": video_id, "start": start, "end": end, "model": rep.backend, "replayed": rep.replayed,
 289 | -            "second_pass_text": span, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
 290 | +            "second_pass_text": span, "self_repair": repair, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
 291 |              "critical": cmp_["critical"], "speakers": turns, "audio": os.path.basename(wav),
 292 |              "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_S), start, end, text),
 293 |              "ok": cmp_["ok"] and turns["turn_change_inside"] is False}
 294 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
 295 | index 9642b62e..af4ccc14 100644
 296 | --- a/pipeline/vo_fidelity.py
 297 | +++ b/pipeline/vo_fidelity.py
 298 | @@ -727,7 +727,7 @@ def check(router, segments, lines, writer_vendor, seed=7, manifest=None, current
 299 |      (law L-m) and leaves the layer NOT measured."""
 300 |      import providers as P
 301 |      det = check_deterministic(segments, lines, manifest, current_levels)
 302 | -    out = {"deterministic": det, "verdict": None, "backend": None, "measured": False, "replayed": False}
 303 | +    out = {"deterministic": det, "verdict": None, "backend": None, "measured": False, "replayed": False, "seed": seed}
 304 |      r = None
 305 |      try:
 306 |          r = router.call("fidelity_verdict", verdict_prompt(segments, lines, manifest), 2500, seed,
 307 | @@ -743,3 +743,50 @@ def check(router, segments, lines, writer_vendor, seed=7, manifest=None, current
 308 |      out["violations"] = det["violations"] + out["verdict"]["violations"]
 309 |      out["ok"] = det["ok"] and out["verdict"]["ok"]
 310 |      return out
 311 | +
 312 | +
 313 | +def majority(runs, lines):
 314 | +    """Orchestrator ruling 07:42 (3): a verdict that flips on unchanged text is run THREE times (the seed differs, the
 315 | +    text does not) and the majority decides. runs: check() results on the same segments and lines. Per line slot a
 316 | +    run votes "pass" only when it was measured and its verdict holds no violation on that slot nor on the whole reply
 317 | +    ("-"); a slot passes when more than half of the runs vote "pass" (an unmeasured run votes "fail", law L-m).
 318 | +    -> a check()-shaped result: the seed-free deterministic layer, the first run's claims, every violation of a slot
 319 | +    the majority fails (plus VERDICT_MAJORITY with the votes), "runs" (n) and "majority" = {"votes": {slot: [...]},
 320 | +    "splits": [slots whose votes differ], "runs": [per run: seed, backend, measured, replayed, ok, violations]}. A
 321 | +    split is recorded, never hidden (the ruling: recorded in the package and named in the caption)."""
 322 | +    if not runs or len(runs) % 2 == 0:
 323 | +        raise ValueError(f"majority needs an odd number of runs, got {len(runs)}")
 324 | +    slots = [ln["slot"] for ln in lines]
 325 | +    whole = lambda v: v.get("slot") == "-" or v.get("slot") not in slots   # an unknown slot fails every slot (C1 H1)
 326 | +    votes = {}
 327 | +    for s in slots:
 328 | +        votes[s] = ["pass" if r.get("measured") and not any(
 329 | +            v.get("slot") == s or whole(v) for v in (r.get("verdict") or {}).get("violations") or []) else "fail"
 330 | +            for r in runs]
 331 | +    failed = [s for s, vs in votes.items() if 2 * vs.count("pass") <= len(runs)]
 332 | +    viol, seen = [], set()
 333 | +    for s in failed:
 334 | +        viol.append({"slot": s, "rule": "VERDICT_MAJORITY", "detail": f"votes {votes[s]} (seeds "
 335 | +                                                                        f"{[r.get('seed') for r in runs]})"})
 336 | +        for r in runs:
 337 | +            for v in (r.get("verdict") or {}).get("violations") or []:
 338 | +                k = (v.get("slot"), v.get("rule"), v.get("detail"))
 339 | +                if (v.get("slot") == s or whole(v)) and k not in seen:
 340 | +                    seen.add(k)
 341 | +                    viol.append(v)
 342 | +    n_measured = sum(bool(r.get("measured")) for r in runs)
 343 | +    reps = [r.get("replayed") for r in runs]
 344 | +    base = runs[0]
 345 | +    verdict = {"ok": 2 * n_measured > len(runs) and not failed,
 346 | +               "claims": (base.get("verdict") or {}).get("claims") or [], "violations": viol}
 347 | +    out = {"deterministic": base["deterministic"], "verdict": verdict,
 348 | +           "backend": " / ".join(sorted({str(r.get("backend")) for r in runs})),
 349 | +           "measured": 2 * n_measured > len(runs),
 350 | +           "replayed": None if any(not isinstance(x, bool) for x in reps) else any(reps), "runs": len(runs),
 351 | +           "majority": {"votes": votes, "splits": [s for s, vs in votes.items() if len(set(vs)) > 1],
 352 | +                        "runs": [{"seed": r.get("seed"), "backend": r.get("backend"), "measured": r.get("measured"),
 353 | +                                  "replayed": r.get("replayed"), "ok": bool((r.get("verdict") or {}).get("ok")),
 354 | +                                  "violations": (r.get("verdict") or {}).get("violations") or []} for r in runs]}}
 355 | +    out["violations"] = base["deterministic"]["violations"] + viol
 356 | +    out["ok"] = base["deterministic"]["ok"] and verdict["ok"]
 357 | +    return out
 358 | diff --git a/tests/package/pin_and_verify.py b/tests/package/pin_and_verify.py
 359 | new file mode 100644
 360 | index 00000000..4a478de9
 361 | --- /dev/null
 362 | +++ b/tests/package/pin_and_verify.py
 363 | @@ -0,0 +1,71 @@
 364 | +#!/usr/bin/env python3
 365 | +"""Seal a gated package into MOMENTS_PIN.json and verify the pin against the factory AS DEPLOYED (read-only copies of
 366 | +the main tree's pinned.py, edl_rules.py and config.py in a temporary directory, as smoke_r7.py does; nothing is
 367 | +written to the main tree; no download, no Whisper, no GPU, no network).
 368 | +
 369 | +Checks on the REAL pin: package_pin.to_pin authorises it (every required gate exactly PASS, measured live, the lines
 370 | +equal the VO / title / caption); pinned.validate_schema accepts it; pinned.build_edl (moments_vo) carries the VO
 371 | +(a line after every clip, the last included), the ONE title and caption and the seal; edl_rules.rule_r4 (R4 for
 372 | +moments) passes on the pin's own segment durations.
 373 | +Usage: python3 tests/package/pin_and_verify.py PACKAGE.json RUN_NAME OUT_DIR [MAIN_TREE]"""
 374 | +import json
 375 | +import os
 376 | +import shutil
 377 | +import sys
 378 | +import tempfile
 379 | +
 380 | +HERE = os.path.dirname(os.path.abspath(__file__))
 381 | +REPO = os.path.dirname(os.path.dirname(HERE))
 382 | +sys.path.insert(0, HERE)
 383 | +from smoke_r7 import fake_acq  # noqa: E402
 384 | +
 385 | +
 386 | +def main(argv=None):
 387 | +    argv = argv or sys.argv[1:]
 388 | +    pkg_path, run_name, out_dir = argv[:3]
 389 | +    main_tree = argv[3] if len(argv) > 3 else "/home/ultron/protocol_pulse"
 390 | +    tmp = tempfile.mkdtemp(prefix="pp_pin_verify_")
 391 | +    try:
 392 | +        shutil.copytree(os.path.join(REPO, "pipeline"), os.path.join(tmp, "pipeline"),
 393 | +                        ignore=shutil.ignore_patterns("__pycache__", "*.mp4", "*.onnx", "fixtures", "avatars"))
 394 | +        for f in ("pinned.py", "edl_rules.py", "config.py"):          # the DEPLOYED versions (read-only copies)
 395 | +            shutil.copy(os.path.join(main_tree, "pipeline", f), os.path.join(tmp, "pipeline", f))
 396 | +        sys.path.insert(0, os.path.join(tmp, "pipeline"))
 397 | +        import edl_rules
 398 | +        import package_pin
 399 | +        import pinned
 400 | +        assert os.path.dirname(pinned.__file__) == os.path.join(tmp, "pipeline")
 401 | +        pk = json.load(open(pkg_path))
 402 | +        path, pin = package_pin.write_pin(pk, run_name, out_dir)        # refuses unless every gate is exactly PASS
 403 | +        pinned.validate_schema(pin)
 404 | +        # the acquisition is faked (no download): each range's own approved words spread over its own start-end
 405 | +        pinned.validate_range = lambda s, a: {"i0": 0, "i1": len(a["transcript"]["words"]) - 1,
 406 | +                                              "text": s["approved_text"], "first_word": s["approved_text"].split()[0],
 407 | +                                              "last_word": s["approved_text"].split()[-1], "start_file": s["start"],
 408 | +                                              "end_file": s["end"], "source_duration": 99999.0,
 409 | +                                              "words": a["transcript"]["words"],
 410 | +                                              "transcript_word_straddles_boundary": False,
 411 | +                                              "edge_words_from": "verify", "approved_text_similarity": 1.0}
 412 | +        pinned.L.make_lock = lambda *a, **k: {"verify": True}
 413 | +        pinned.L.sha256_file = lambda p: "0" * 64
 414 | +        edl, _, _ = pinned.build_edl(pin, fake_acq(pin))
 415 | +        mp = pin["moments_package"]
 416 | +        assert edl["vo"]["intro"] == pk["vo"]["intro"], edl["vo"]
 417 | +        assert [b["text"] for b in edl["vo"]["bridges"]] == list(pk["vo"]["bridges"]), edl["vo"]
 418 | +        assert [b["after_clip"] for b in edl["vo"]["bridges"]] == list(pk["vo"]["bridges_after_clip"]), edl["vo"]
 419 | +        assert edl["title"] == pk["title"] and edl["caption"] == pk["caption"], (edl.get("title"), edl.get("caption"))
 420 | +        assert edl["moments_package_sha256"] == mp["package_sha256"] == package_pin.seal(
 421 | +            pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"], mp["gates"])
 422 | +        for c in edl["clips"]:
 423 | +            c.setdefault("duration", round(c.get("end_file", 0) - c.get("start_file", 0), 2))
 424 | +        ok, why = edl_rules.rule_r4(edl)
 425 | +        print(f"PIN {path}\n  story_id {pin['story_id']} seal {mp['package_sha256']}")
 426 | +        print(f"  pinned.validate_schema: OK; build_edl (moments_vo): VO, title, caption, seal carried")
 427 | +        print(f"  edl_rules.rule_r4 (deployed): {'PASS' if ok else 'FAIL'}: {why}")
 428 | +        return 0 if ok else 1
 429 | +    finally:
 430 | +        shutil.rmtree(tmp, ignore_errors=True)
 431 | +
 432 | +
 433 | +if __name__ == "__main__":
 434 | +    sys.exit(main())
 435 | diff --git a/tests/package/run_given_package.py b/tests/package/run_given_package.py
 436 | index 18a35a1f..559c420e 100644
 437 | --- a/tests/package/run_given_package.py
 438 | +++ b/tests/package/run_given_package.py
 439 | @@ -131,13 +131,21 @@ def main(argv=None):
 440 |      ap.add_argument("--takeaway-text", help="a line fix for VO 3 (the takeaway)")
 441 |      ap.add_argument("--tag", default="", help="suffix of the output file")
 442 |      ap.add_argument("--to-does", action="store_true", help="07:25: clip_02 through 'does.'")
 443 | +    ap.add_argument("--to-existed", action="store_true", help="07:42: clip_02 = the first sentence, ending 'existed.'")
 444 | +    ap.add_argument("--title-text", help="07:42 (3): the thesis fallback's title")
 445 | +    ap.add_argument("--clip02", help="08:18: clip_02 = this store moment, as stored (an id or a unique id prefix)")
 446 | +    ap.add_argument("--precheck", action="store_true",
 447 | +                    help="08:18 item 3: step A and the second recogniser (CUTTABLE) only, then stop")
 448 | +    ap.add_argument("--verdict-runs", type=int, default=1,
 449 | +                    help="07:42 (3): run the fidelity verdict N times (seeds 7..), the majority decides")
 450 |      ap.add_argument("--xai-heimdall", action="store_true", help="07:25: Anthropic and OpenAI are out of credit")
 451 |      a = ap.parse_args(argv)
 452 |      t_start = time.time()
 453 |      led0 = json.load(open(PM.SPEND))["usd_estimate"]
 454 |      chains = CHAINS
 455 |      if a.xai_heimdall:                          # orchestrator 07:25: xAI, Heimdall and local only
 456 | -        chains = {r: [b for b in c if not b.startswith(("anthropic:", "openai:"))] for r, c in CHAINS.items()}
 457 | +        chains = {r: [b for b in c if not b.startswith(("anthropic:", "openai:", "openai_stt:"))]
 458 | +                  for r, c in CHAINS.items()}
 459 |          chains = {r: (c + ["heimdall:deepseek/deepseek-v4.1-flash"] if len(c) < 2 and r != "transcribe" else c)
 460 |                    for r, c in chains.items()}
 461 |      router = P.Router(env_path=P.ENV_PATH, record_dir=REPLIES, spend_path=PM.SPEND, limit_usd=PM.LIMIT_USD,
 462 | @@ -156,7 +164,19 @@ def main(argv=None):
 463 |          wbd = recut(by_id, sources, WBD2, 7325, w_us, 464, 464,
 464 |                      "clip_01 replaced (06:45 B): the store's sentence 464 cut at 'U.S.': the independent recogniser "
 465 |                      "ends a sentence there ('in the US. Um, you know')")
 466 | -        if a.to_does:                           # orchestrator 07:25: 'emerges' runs into 'And' with no pause
 467 | +        if sum(map(bool, (a.to_does, a.to_existed, a.clip02))) > 1:
 468 | +            raise SystemExit("--to-does, --to-existed and --clip02 are exclusive")
 469 | +        if a.clip02:                            # orchestrator 08:18: the store moment itself, not a re-cut
 470 | +            hits = [m for mid, m in by_id.items() if mid.startswith(a.clip02)]
 471 | +            if len(hits) != 1:
 472 | +                raise SystemExit(f"--clip02 {a.clip02}: {len(hits)} store moments match")
 473 | +            nat = hits[0]
 474 | +        elif a.to_existed:                        # orchestrator 07:42: the only clean end in this moment
 475 | +            nat = recut(by_id, sources, NATALIE, 1417, 1432, 108, 108,
 476 | +                        "clip_02 = the first sentence only, ending 'existed.' (07:42): the integrator's cutter finds "
 477 | +                        "the only clean end of this moment there (cut 15.02-22.04 s file time, pause + "
 478 | +                        "neighbour-clear OK, one speaker); 'does.' carries the host's 'Mm' in its tail")
 479 | +        elif a.to_does:                         # orchestrator 07:25: 'emerges' runs into 'And' with no pause
 480 |              nat = recut(by_id, sources, NATALIE, 1417, 1456, 108, 111,
 481 |                          "clip_02 extended to 'does.' (07:25): the cutter found no pause after 'emerges.'; the "
 482 |                          "recognisers and the cutter's own M19 pause test end it at 'does.'")
 483 | @@ -173,6 +193,8 @@ def main(argv=None):
 484 |          f["intro"] = dict(f["intro"], text=a.intro_text)
 485 |      if a.takeaway_text and len(f["bridges"]) > 1:
 486 |          f["bridges"][-1] = dict(f["bridges"][-1], text=a.takeaway_text)
 487 | +    if a.title_text:
 488 | +        f["title"] = dict(f["title"], text=a.title_text)
 489 |      pk = PK.assemble(f["order"], by_id, f, ctx, f"written by the orchestrator, variant {a.variant}")
 490 |      pk["vo"]["bridges_after_clip"] = list(f["after"])           # a takeaway may follow the last clip (06:00 ruling 4)
 491 |      levels = PK.current_levels(sources.values(), ctx)
 492 | @@ -195,6 +217,33 @@ def main(argv=None):
 493 |      say(f"step A ({a_backend}, {time.time() - t0:.0f} s): " + "; ".join(
 494 |          f"{lb}: fails {CI.a_failures(x) or 'none'}, speaker {x.get('speaker_is')} verified {x.get('speaker_verified')}"
 495 |          f" ({x.get('speaker_evidence')!r:.60})" for lb, x in a_by.items()))
 496 | +    if a.precheck:                              # 08:18 item 3: step A, then the second recogniser's CUTTABLE
 497 | +        pre = {"step_a": a_by, "truth": {}}
 498 | +        for sg in pk["segments"]:
 499 | +            w_, ws_ = None, None
 500 | +            for x in sorted(os.listdir(AUDIO)):
 501 | +                parts = x[:-4].rsplit("_", 2) if x.endswith(".wav") else []
 502 | +                if len(parts) == 3 and parts[0] == sg["video_id"] and int(parts[1]) / 1000.0 <= float(sg["start"]) - 1.0 \
 503 | +                        and int(parts[2]) / 1000.0 >= float(sg["end"]) + 1.0:
 504 | +                    w_, ws_ = os.path.join(AUDIO, x), int(parts[1]) / 1000.0
 505 | +                    break
 506 | +            try:
 507 | +                pre["truth"][sg["label"]] = TT.verify_segment(router, sg["video_id"], float(sg["start"]), float(sg["end"]),
 508 | +                                                              sg["text"], AUDIO, wav=w_, wav_start=ws_)
 509 | +            except Exception as e:
 510 | +                pre["truth"][sg["label"]] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
 511 | +            t_ = pre["truth"][sg["label"]]
 512 | +            say(f"PRECHECK {sg['label']} ({sg['moment_id']}): second pass {'PASS' if t_.get('ok') else 'FAIL'} "
 513 | +                f"({t_.get('model')}, disagree {t_.get('disagree')}, speakers {t_.get('speakers')}, err {t_.get('error')}); "
 514 | +                f"CUTTABLE {'PASS' if (t_.get('edges') or {}).get('cuttable') else 'FAIL'} IN "
 515 | +                f"{(t_.get('edges') or {}).get('in')} OUT {(t_.get('edges') or {}).get('out')}; audio {t_.get('audio')}")
 516 | +        led1 = json.load(open(PM.SPEND))["usd_estimate"]
 517 | +        say(f"PRECHECK spend ${led1 - led0:.2f} (ledger ${led1:.2f}) | wall {time.time() - t_start:.0f} s")
 518 | +        os.makedirs(OUT, exist_ok=True)
 519 | +        name = f"precheck_{a.variant}{a.tag}"
 520 | +        json.dump(pre, open(os.path.join(OUT, name + ".json"), "w"), indent=1, default=str)
 521 | +        open(os.path.join(OUT, name + ".log"), "w").write("\n".join(log) + "\n")
 522 | +        return 0
 523 |      segs_v = {}
 524 |      for sg in pk["segments"]:
 525 |          ver = a_by[sg["label"]].get("speaker_verified")
 526 | @@ -220,17 +269,45 @@ def main(argv=None):
 527 |                                   wav=w, wav_start=ws)
 528 |  
 529 |      exc_cache = {}
 530 | +    majority_log = []
 531 | +
 532 | +    def exclusion(sg):                          # 08:18 item 4: once; the three-run majority only if not PASS
 533 | +        m = by_id[sg["moment_id"]]
 534 | +        passed, runs, votes = PK.once_then_majority(lambda sd: PK.exclusion_for(router, m, sources, exc_cache, sd),
 535 | +                                                    lambda e: e.get("verdict") == "keep" and bool(e.get("measured")))
 536 | +        if len(runs) > 1:
 537 | +            majority_log.append(f"exclusion {sg['label']}: votes {votes} -> {'PASS' if passed else 'FAIL'}")
 538 | +        return PK.with_votes(runs, votes, passed)
 539 | +
 540 | +    def fidelity():
 541 | +        if a.verdict_runs > 1:                  # 07:42 (3): forced N runs; the majority decides per line
 542 | +            runs = [VF.check(router, segs_v, lines, AUTHOR["vendor"], 7 + k, man, levels, AUTHOR["family"])
 543 | +                    for k in range(a.verdict_runs)]
 544 | +            return VF.majority(runs, lines), runs
 545 | +        passed, runs, votes = PK.once_then_majority(
 546 | +            lambda sd: VF.check(router, segs_v, lines, AUTHOR["vendor"], sd, man, levels, AUTHOR["family"]),
 547 | +            lambda r: bool(r.get("measured")) and bool((r.get("verdict") or {}).get("ok")))
 548 | +        if len(runs) == 1:
 549 | +            return runs[0], runs
 550 | +        merged = VF.majority(runs, lines)       # the majority per line, as 07:42 item 3 ran it
 551 | +        majority_log.append(f"fidelity verdict: per-line votes {json.dumps(merged['majority']['votes'])} -> "
 552 | +                            f"{'PASS' if merged['verdict']['ok'] else 'FAIL'}")
 553 | +        return merged, runs
 554 |  
 555 | -    def exclusion(sg):
 556 | -        return PK.exclusion_for(router, by_id[sg["moment_id"]], sources, exc_cache)
 557 | +    def context():
 558 | +        passed, runs, votes = PK.once_then_majority(
 559 | +            lambda sd: CI.check_contexts(router, pk, contexts, AUTHOR["vendor"], sd, dict(a_by), AUTHOR["family"], True),
 560 | +            lambda r: r.get("ok") is True and bool(r.get("measured")))
 561 | +        if len(runs) > 1:
 562 | +            majority_log.append(f"context B/C: votes {votes} -> {'PASS' if passed else 'FAIL'} (violations per run: "
 563 | +                                f"{[[v.get('rule') for v in x.get('violations') or []] for x in runs]})")
 564 | +        return PK.with_votes(runs, votes, passed)
 565 |  
 566 |      with ThreadPoolExecutor(max_workers=10) as ex:
 567 | -        f_fid = ex.submit(VF.check, router, segs_v, lines, AUTHOR["vendor"], 7, man, levels, AUTHOR["family"])
 568 | -        f_ctx = ex.submit(CI.check_contexts, router, pk, contexts, AUTHOR["vendor"], 7,
 569 | -                          {lb: x for lb, x in a_by.items()}, AUTHOR["family"], True)
 570 | +        f_fid, f_ctx = ex.submit(fidelity), ex.submit(context)
 571 |          f_exc = {sg["label"]: ex.submit(exclusion, sg) for sg in pk["segments"]}
 572 |          f_tru = {sg["label"]: ex.submit(truth, sg) for sg in pk["segments"]}
 573 | -        fid, ctx_ = f_fid.result(), f_ctx.result()
 574 | +        (fid, fid_runs), ctx_ = f_fid.result(), f_ctx.result()
 575 |          exc = {k: v.result() for k, v in f_exc.items()}
 576 |          tru = {}
 577 |          for k, v in f_tru.items():
 578 | @@ -240,7 +317,13 @@ def main(argv=None):
 579 |                  tru[k] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
 580 |      say(f"concurrent gates: {time.time() - t0:.0f} s")
 581 |      dup = PK.duplicates(pk)
 582 | -    ok_c, coh = PK.coherence(router, pk, AUTHOR["vendor"], writer_family=AUTHOR["family"])
 583 | +    ok_c, coh_runs, coh_votes = PK.once_then_majority(            # 08:18 item 4: once, the majority only if not PASS
 584 | +        lambda sd: (lambda r: dict(r[1], ok=r[0]))(PK.coherence(router, pk, AUTHOR["vendor"], sd, AUTHOR["family"])),
 585 | +        lambda c: c.get("ok") is True and bool(c.get("measured")))
 586 | +    coh = PK.with_votes(coh_runs, coh_votes, ok_c)
 587 | +    if len(coh_runs) > 1:
 588 | +        majority_log.append(f"coherence: votes {coh_votes} -> {'PASS' if ok_c else 'FAIL'} (ratings per run: "
 589 | +                            f"{[(x.get('clips'), x.get('vo_point')) for x in coh_runs]})")
 590 |      # report
 591 |      say("VO FIDELITY deterministic: " + ("PASS" if fid["deterministic"]["ok"] else "FAIL " + json.dumps(
 592 |          fid["deterministic"]["violations"])))
 593 | @@ -250,6 +333,15 @@ def main(argv=None):
 594 |              f"{json.dumps(c.get('tests')) if c.get('class') == 'commentary' else json.dumps(c.get('support'))[:240]}")
 595 |      for v in (fid["verdict"] or {}).get("violations") or []:
 596 |          say(f"   VIOLATION {v['slot']}: {v['rule']}: {v['detail']}")
 597 | +    if fid.get("majority"):
 598 | +        mj = fid["majority"]
 599 | +        say(f"   MAJORITY of {fid['runs']} (ruling 07:42): votes {json.dumps(mj['votes'])}; splits {mj['splits'] or 'none'}")
 600 | +        for rr, run in zip(mj["runs"], fid_runs):
 601 | +            th = [(c.get("line"), c.get("supported")) for c in (run.get("verdict") or {}).get("claims") or []
 602 | +                  if c.get("line") in ("intro", "title") and c.get("class") != "commentary"]
 603 | +            say(f"   run seed {rr['seed']} ({rr['backend']}, measured {rr['measured']}, replayed {rr['replayed']}): "
 604 | +                f"{'PASS' if rr['ok'] else 'FAIL'}; thesis claims {th}; violations "
 605 | +                f"{[(v['slot'], v['rule']) for v in rr['violations']] or 'none'}")
 606 |      say(f"CONTEXT INTEGRITY (A {ctx_['backends'].get('A')}, B {ctx_['backends'].get('B')}, C "
 607 |          f"{ctx_['backends'].get('C')}): " + ("PASS" if ctx_["ok"] else "FAIL " + json.dumps(ctx_["violations"])))
 608 |      for lb, x in (ctx_.get("segments") or {}).items():
 609 | @@ -267,6 +359,8 @@ def main(argv=None):
 610 |          f"{k}: {'PASS' if (v.get('edges') or {}).get('cuttable') else 'FAIL'} IN {(v.get('edges') or {}).get('in')} "
 611 |          f"OUT {(v.get('edges') or {}).get('out')}" for k, v in tru.items()))
 612 |      say(f"COHERENCE ({coh.get('backend')}): {'PASS' if ok_c else 'FAIL'} {json.dumps(coh)[:500]}")
 613 | +    say("MAJORITY (08:18 item 4; once, only for a model verdict not PASS on its first run): " +
 614 | +        ("; ".join(majority_log) if majority_log else "none needed: every model verdict passed on its first run"))
 615 |      rt_ok = PK.RUNTIME_S[0] <= pk["runtime_s_estimate"] <= PK.RUNTIME_S[1]
 616 |      gates = {"vo_fidelity_deterministic": fid["deterministic"]["ok"], "vo_fidelity_verdict": bool((fid["verdict"] or {}).get("ok")),
 617 |               "price_now_measured": fid["deterministic"].get("price_now_measured"), "duplicate": not dup,
 618 | @@ -281,8 +375,24 @@ def main(argv=None):
 619 |      pk["cut_evidence"] = {lb: {"video_id": t.get("video_id"), "start": t.get("start"), "end": t.get("end"),
 620 |                                 "model": t.get("model"), "audio": t.get("audio"), "in": (t.get("edges") or {}).get("in"),
 621 |                                 "out": (t.get("edges") or {}).get("out")} for lb, t in tru.items()}
 622 | +    if a.to_existed:                            # 07:42 (1): the integrator's cut geometry is the CUTTABLE evidence
 623 | +        import hashlib
 624 | +        facts = "/home/ultron/protocol_pulse/docs/audits/parallel/integrator_RULING7_FACTS.md"
 625 | +        lb2 = pk["segments"][-1]["label"]
 626 | +        pk["cut_evidence"][lb2]["renderer_geometry"] = {
 627 | +            "source": facts, "sha256": hashlib.sha256(open(facts, "rb").read()).hexdigest(),
 628 | +            "entries": ["07:23 ET", "07:41 ET"], "file_time": "YouTube - 514.0",
 629 | +            "cut_in": 15.02, "cut_out": 22.04, "cut_youtube": [529.02, 536.04], "duration_s": 7.02,
 630 | +            "checks": "the renderer's own sentence lock (primary decode 'existed.' 21.18-21.62, next 'And' 21.94) and "
 631 | +                      "cut geometry (edge_plan + accepted_cut, main): pause + neighbour-clear OK, one speaker; the "
 632 | +                      "final '-ed' release ends 21.63, 0.41 s before the cut, in quiet",
 633 | +            "disagreement": "the integrator's second-recogniser pass on its acquired window hears a COMMA after "
 634 | +                            "'existed' ('ever existed, and it- all it has to do'); this builder's three recorded "
 635 | +                            "scribe_v1 passes (windows 527.55-540.84 / -542.50 / -545.04) hear a full stop ('existed. "
 636 | +                            "And it, all it has to do'); the integrator: not a blocker under the existing rule (the "
 637 | +                            "primary's full stop locks the edge); the orchestrator ruled 07:42 with it on file"}
 638 |      say("INVENTORY: " + "; ".join(f"{k} {v['status']}" for k, v in pk["gates"].items()))
 639 | -    pk["checks_given"] = {"fidelity": fid, "context": ctx_, "duplicates": dup, "exclusion": exc, "truth": tru,
 640 | +    pk["checks_given"] = {"fidelity": fid, "fidelity_runs": fid_runs, "majority_log": majority_log, "context": ctx_, "duplicates": dup, "exclusion": exc, "truth": tru,
 641 |                            "coherence": coh, "r4": [r4_ok, r4_why], "runtime_ok": rt_ok, "gates": gates,
 642 |                            "step_a": a_by, "current_levels": levels, "author": AUTHOR,
 643 |                            "wall_s": round(time.time() - t_start, 1), "usd": round(led1 - led0, 4)}
 644 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 645 | index c7cdcb30..aeac412c 100644
 646 | --- a/tests/package/test_angles.py
 647 | +++ b/tests/package/test_angles.py
 648 | @@ -90,25 +90,29 @@ class TestAngles(unittest.TestCase):
 649 |  
 650 |  
 651 |  class TestLengthAndR4(unittest.TestCase):
 652 | -    def test_the_runtime_counts_the_signoff_once(self):
 653 | +    def test_the_runtime_is_the_factorys_own_estimate(self):
 654 |          segs = [{"duration_s": 10.0}, {"duration_s": 20.0}]
 655 | -        self.assertAlmostEqual(PK.runtime(segs, (40 + 18) / PK.WPS), 30.0 + 58 / 2.6 + PK.FIXED_S, places=2)
 656 | -        self.assertAlmostEqual(PK.FIXED_S + 18 / PK.WPS, E.TAIL_S, places=1)     # the tail = fixed + one sign-off
 657 | +        # edl_rules._r4_moments: word spans + each VO line at 2.5 w/s + 1 s pre-roll + the 14.30 s tail (sign-off inside)
 658 | +        self.assertAlmostEqual(PK.runtime(segs, ["w " * 10, "w " * 15]), 30.0 + 10 / 2.5 + 1 + 15 / 2.5 + 1 + 14.30,
 659 | +                               places=2)
 660 | +        self.assertAlmostEqual(PK.FINAL_TAIL_S, 14.30, places=2)
 661 |  
 662 |      def test_the_moments_r4_on_tonights_numbers(self):
 663 |          def pk(vo1, vo2, vo3):
 664 |              p = {"segments": [{"duration_s": 8.38, "channel": "A"}, {"duration_s": 11.24, "channel": "B"},
 665 |                                {"duration_s": 10.29, "channel": "C"}],
 666 |                   "vo": {"intro": vo1, "bridges": [vo2, vo3], "bridges_after_clip": [1, 2]}}
 667 | -            p["runtime_s_estimate"] = PK.runtime(p["segments"], (sum(len(x.split()) for x in (vo1, vo2, vo3)) + 19) / PK.WPS)
 668 | +            p["runtime_s_estimate"] = PK.runtime(p["segments"], [vo1, vo2, vo3])
 669 |              return p
 670 |          w = lambda n: " ".join(["word"] * n)
 671 | -        ok, why = PK.r4(pk(w(27), w(18), w(18)))                                  # 05:35-06:00's 63 words
 672 | -        self.assertFalse(ok)
 673 | -        self.assertIn("41.0%", why)
 674 | -        ok, why = PK.r4(pk(w(13), w(18), w(11)))                                  # the rendered 42 words
 675 | +        p63 = pk(w(27), w(18), w(18))                                              # 05:35-06:00's 63 words
 676 | +        ok, why = PK.r4(p63)                  # the factory's denominator: 28.2 s of VO = 38.9 % of 72.41 s (share ok)
 677 | +        self.assertTrue(ok, why)
 678 | +        self.assertIn("38.9%", why)
 679 | +        self.assertAlmostEqual(p63["runtime_s_estimate"], 72.41, places=2)       # ... but over 70 s: the runtime gate
 680 | +        self.assertFalse(PK.RUNTIME_S[0] <= p63["runtime_s_estimate"] <= PK.RUNTIME_S[1])
 681 | +        ok, why = PK.r4(pk(w(13), w(18), w(11)))                                  # 06:22's 42 words
 682 |          self.assertTrue(ok, why)
 683 | -        self.assertIn("32.6%", why)
 684 |          self.assertFalse(PK.r4(dict(pk(w(13), w(18), w(11)), vo={"intro": w(13), "bridges": [w(5), w(5)],
 685 |                                                                    "bridges_after_clip": [1, 1]}))[0])
 686 |          self.assertLessEqual(PK.min_vo_words(29.91), PK.r4_max_vo_words(29.91, 3))
 687 | @@ -203,6 +207,85 @@ class TestInventory(unittest.TestCase):
 688 |              self.assertTrue(g[row]["status"] != "PASS" or g[row]["replayed"] is not False, (row, g[row]))
 689 |              self.assertTrue(package_pin.gate_problems(g), row)
 690 |  
 691 | +    def test_a_leading_self_repair_is_part_of_the_sentence_and_nothing_else_is(self):
 692 | +        """Ruling 8 (08:29): 'path.' | 'Bit-' 'bitcoin imposes ...' (the same speaker's truncated repetition of the
 693 | +        clip's first word) is CUTTABLE at the IN and no L-v 2 disagreement. Another speaker, a fragment that is not a
 694 | +        prefix, no dash, a full repetition, two fragments, or no sentence end before it: not a self-repair."""
 695 | +        text = "Bitcoin imposes a global free market for the first time ever."
 696 | +
 697 | +        def words(rep=("Bit-",), rep_sp="s0", before="path."):
 698 | +            ws = [{"text": before, "start": 0.4, "end": 0.8, "speaker": "s0"}]
 699 | +            ws += [{"text": r, "start": 1.30 - 0.2 * (len(rep) - 1 - k), "end": 1.42 - 0.2 * (len(rep) - 1 - k),
 700 | +                    "speaker": rep_sp} for k, r in enumerate(rep)]
 701 | +            ws += [{"text": t, "start": 1.72 + 0.3 * k, "end": 1.95 + 0.3 * k, "speaker": "s0"}
 702 | +                   for k, t in enumerate(text.lower().split())]
 703 | +            return ws + [{"text": "Okay,", "start": 6.0, "end": 6.2, "speaker": "s1"}]
 704 | +
 705 | +        class R:
 706 | +            def __init__(self, ws):
 707 | +                self.ws = ws
 708 | +
 709 | +            def transcribe(self, role, wav):
 710 | +                return {"text": " ".join(w["text"] for w in self.ws), "segments": [], "words": self.ws}, \
 711 | +                    type("Rep", (), {"backend": "s", "replayed": False})()
 712 | +        run = lambda ws: TT.verify_segment(R(ws), "v", 1.5, 5.25, text, "/nonexistent", wav="w.wav", wav_start=0.0)
 713 | +        t = run(words())
 714 | +        self.assertTrue(t["edges"]["cuttable"], t["edges"])
 715 | +        self.assertEqual((t["edges"]["in"]["before"], t["edges"]["in"]["self_repair"]), ("path.", "Bit-"))
 716 | +        self.assertEqual(t["self_repair"], "Bit-")
 717 | +        self.assertTrue(t["ok"], t)
 718 | +        self.assertTrue(run(words(rep=()))["edges"]["cuttable"])                 # no false start: unchanged
 719 | +        for kw in ({"rep_sp": "s1"}, {"rep": ("Bo-",)}, {"rep": ("Bit",)}):             # not a self-repair at all
 720 | +            t = run(words(**kw))
 721 | +            self.assertFalse(t["edges"]["cuttable"], kw)
 722 | +            self.assertIsNone(t["edges"]["in"].get("self_repair"), kw)
 723 | +        for kw, before in (({"rep": ("B-", "Bit-")}, "B-"), ({"before": "and"}, "and")):   # exactly ONE token, and only
 724 | +            t = run(words(**kw))                                                           # at a sentence start
 725 | +            self.assertFalse(t["edges"]["cuttable"], kw)
 726 | +            self.assertEqual(t["edges"]["in"]["before"], before, kw)
 727 | +        # a FULL repetition is not truncated, so not a self-repair: the IN's first-word match (4 letters, unchanged
 728 | +        # before ruling 8) reads 'Bitcoin-' as the first word, and L-v 2 still counts it as a disagreement
 729 | +        t = run(words(rep=("Bitcoin-",)))
 730 | +        self.assertIsNone(t["self_repair"])
 731 | +        self.assertIsNone(t["edges"]["in"].get("self_repair"))
 732 | +        self.assertFalse(t["ok"])
 733 | +        self.assertIn("Bitcoin-", t["disagree"]["names"])
 734 | +
 735 | +    def test_the_moments_r4_share_is_45_percent(self):
 736 | +        """Ruling 9 (08:29): 45 % of the TOTAL runtime; 45.1 % is refused; the word caps are unchanged."""
 737 | +        def pk(a, b, c, segs=(8.38, 9.62, 3.50)):
 738 | +            w = lambda n: " ".join(["word"] * n)
 739 | +            p = {"segments": [{"duration_s": d} for d in segs],
 740 | +                 "vo": {"intro": w(a), "bridges": [w(b), w(c)], "bridges_after_clip": [1, 2]}}
 741 | +            p["runtime_s_estimate"] = PK.runtime(p["segments"], [w(a), w(b), w(c)])
 742 | +            return p
 743 | +        self.assertEqual(PK.R4_MOMENTS_SHARE, 0.45)
 744 | +        ok, why = PK.r4(pk(30, 18, 18))                                           # 29.4 s of 65.2 s = 45.09 %
 745 | +        self.assertFalse(ok)
 746 | +        self.assertIn("VO=45.1% of the runtime (max 45%)", why)
 747 | +        ok, why = PK.r4(pk(29, 18, 18))                                           # 29.0 s of 64.8 s = 44.75 %
 748 | +        self.assertTrue(ok, why)
 749 | +        ok, why = PK.r4(pk(13, 18, 24))                                           # 08:29's VO 3: 24 words
 750 | +        self.assertTrue(ok, why)                                                  # a takeaway (ruling 10, cap 30)
 751 | +
 752 | +    def test_the_takeaway_after_the_last_clip_is_capped_at_30_and_bridges_at_20(self):
 753 | +        """Ruling 10 (08:40): 31 words after the LAST clip are refused, 30 pass; a 21-word bridge BETWEEN clips is
 754 | +        still refused."""
 755 | +        def pk(a, b, c, after=(1, 2), segs=(8.38, 9.62, 8.0)):
 756 | +            w = lambda n: " ".join(["word"] * n)
 757 | +            p = {"segments": [{"duration_s": d} for d in segs],
 758 | +                 "vo": {"intro": w(a), "bridges": [w(b), w(c)], "bridges_after_clip": list(after)}}
 759 | +            p["runtime_s_estimate"] = PK.runtime(p["segments"], [w(a), w(b), w(c)])
 760 | +            return p
 761 | +        self.assertEqual(PK.MOMENTS_TAKEAWAY_WORD_CAP, 30)
 762 | +        ok, why = PK.r4(pk(10, 12, 31))
 763 | +        self.assertFalse(ok)
 764 | +        self.assertIn("takeaway 2 31 words (max 30)", why)
 765 | +        self.assertTrue(PK.r4(pk(10, 12, 30))[0])
 766 | +        ok, why = PK.r4(pk(10, 21, 12))
 767 | +        self.assertFalse(ok)
 768 | +        self.assertIn("bridge 1 21 words (max 20)", why)
 769 | +
 770 |      def test_a_second_pass_without_diarisation_is_not_ok(self):
 771 |          class R:
 772 |              def transcribe(self, role, wav):
 773 | @@ -214,5 +297,53 @@ class TestInventory(unittest.TestCase):
 774 |          self.assertFalse(t["ok"])
 775 |  
 776 |  
 777 | +class TestMajorityOnce(unittest.TestCase):
 778 | +    def test_once_then_the_majority_only_when_the_first_run_fails(self):
 779 | +        """08:18 item 4 / 08:29: a model verdict that passes its first run runs once; one that does not gets the
 780 | +        three-run majority once; an unmeasured pass is a fail vote; the record keeps every run and an honest
 781 | +        replayed tri-state."""
 782 | +        calls = []
 783 | +
 784 | +        def run_of(results):
 785 | +            def run(sd):
 786 | +                calls.append(sd)
 787 | +                return results[sd]
 788 | +            return run
 789 | +        ok = lambda r: r.get("ok") is True and r.get("measured", True) is True
 790 | +        passed, res, votes = PK.once_then_majority(run_of({7: {"ok": True}}), ok)
 791 | +        self.assertEqual((passed, votes, calls), (True, ["pass"], [7]))
 792 | +        self.assertNotIn("majority", PK.with_votes(res, votes, passed))
 793 | +        calls.clear()
 794 | +        passed, res, votes = PK.once_then_majority(run_of({7: {"ok": False}, 8: {"ok": True}, 9: {"ok": True}}), ok)
 795 | +        self.assertEqual((passed, votes, calls), (True, ["fail", "pass", "pass"], [7, 8, 9]))
 796 | +        rec = PK.with_votes(res, votes, passed)
 797 | +        self.assertTrue(rec["ok"])
 798 | +        self.assertEqual((rec["majority"]["votes"], rec["majority"]["seeds"]), (["fail", "pass", "pass"], [7, 8, 9]))
 799 | +        calls.clear()
 800 | +        passed, res, votes = PK.once_then_majority(
 801 | +            run_of({7: {"ok": False}, 8: {"ok": True}, 9: {"ok": True, "measured": False}}), ok)
 802 | +        self.assertEqual((passed, votes), (False, ["fail", "pass", "fail"]))
 803 | +        self.assertFalse(PK.with_votes(res, votes, passed)["ok"])
 804 | +        res = [{"ok": False, "replayed": False}, {"ok": True, "replayed": None}, {"ok": True, "replayed": False}]
 805 | +        self.assertIsNone(PK.with_votes(res, ["fail", "pass", "pass"], True)["replayed"])
 806 | +
 807 | +    def test_the_r4_word_bounds_invert_runtime_and_the_share_exactly(self):
 808 | +        """Audit 0742 C1 (grok P1): r4_max_vo_words / min_vo_words invert runtime() and the share on every content
 809 | +        length 15-50 s and 1-4 VO lines: the bound passes, one word more (or less) does not."""
 810 | +        for c10 in range(150, 501, 7):
 811 | +            c = c10 / 10
 812 | +            for n in range(1, 5):
 813 | +                vo = lambda w: w / PK.R4_WPS + PK.R4_PREROLL_S * n
 814 | +                share = lambda w: vo(w) / (c + vo(w) + PK.FINAL_TAIL_S)
 815 | +                rt = lambda w: c + vo(w) + PK.FINAL_TAIL_S
 816 | +                hi, lo = PK.r4_max_vo_words(c, n), PK.min_vo_words(c, n)
 817 | +                if hi > 0:
 818 | +                    self.assertLessEqual(share(hi), PK.R4_MOMENTS_SHARE + 1e-9, (c, n))
 819 | +                self.assertGreater(share(hi + 1), PK.R4_MOMENTS_SHARE - 1e-9, (c, n))
 820 | +                if lo > 0:
 821 | +                    self.assertGreaterEqual(rt(lo), PK.RUNTIME_S[0] - 1e-9, (c, n))
 822 | +                    self.assertLess(rt(lo - 1), PK.RUNTIME_S[0], (c, n))
 823 | +
 824 | +
 825 |  if __name__ == "__main__":
 826 |      unittest.main()
 827 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
 828 | index a959ba4d..3f5e7b23 100644
 829 | --- a/tests/package/test_gates.py
 830 | +++ b/tests/package/test_gates.py
 831 | @@ -239,6 +239,33 @@ class TestFidelityVerdict(unittest.TestCase):
 832 |          res, _ = self.verdict(ok, lines)
 833 |          self.assertTrue(res["ok"], res["violations"])
 834 |  
 835 | +    def test_a_flipping_verdict_is_decided_by_the_majority_of_three(self):
 836 | +        """Ruling 07:42 (3): run three times, the majority decides, a 2-1 split is recorded; an unmeasured run is a
 837 | +        'fail' vote (L-m); an even number of runs is refused."""
 838 | +        good = {"claims": [self.claim("intro", self.LINES[0]["text"], "attribution", support=[
 839 | +            {"segment": "m1", "words": "found support at its 200-day moving average"}])]}
 840 | +        unsure = {"claims": [self.claim("intro", self.LINES[0]["text"], "attribution", sup="uncertain")]}
 841 | +
 842 | +        def three(*answers):
 843 | +            r = Canned(fidelity_verdict=list(answers))
 844 | +            runs = [VF.check(r, self.SEGS, self.LINES, "openai", seed=s) for s in (7, 8, 9)]
 845 | +            return VF.majority(runs, self.LINES)
 846 | +        res = three(good, unsure, good)
 847 | +        self.assertTrue(res["ok"], res["violations"])
 848 | +        self.assertEqual(res["majority"]["votes"], {"intro": ["pass", "fail", "pass"]})
 849 | +        self.assertEqual(res["majority"]["splits"], ["intro"])
 850 | +        self.assertEqual([x["seed"] for x in res["majority"]["runs"]], [7, 8, 9])
 851 | +        res = three(unsure, unsure, good)
 852 | +        self.assertFalse(res["ok"])
 853 | +        self.assertEqual([v["rule"] for v in res["violations"]], ["VERDICT_MAJORITY", "VERDICT_UNCERTAIN"])
 854 | +        res = three(good, good)                                   # the third run has no answer: unmeasured
 855 | +        self.assertTrue(res["ok"] and res["measured"])
 856 | +        self.assertEqual(res["majority"]["votes"]["intro"], ["pass", "pass", "fail"])
 857 | +        res = three(good)                                         # two unmeasured runs: never a pass
 858 | +        self.assertEqual((res["ok"], res["measured"]), (False, False))
 859 | +        with self.assertRaises(ValueError):
 860 | +            VF.majority([res, res], self.LINES)
 861 | +
 862 |      def test_no_verdict_is_a_failure_and_not_measured(self):
 863 |          res = VF.check(Canned(), self.SEGS, self.LINES, writer_vendor="openai")
 864 |          self.assertEqual((res["ok"], res["measured"]), (False, False))
 865 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse, moments-first packaging), written 07:42-08:35 ET
Nov 12 under orchestrator rulings (07:42, 08:18, 08:29). The code gates a video package before a pinned render. Laws: nothing measured
is never a pass (L-m); fail closed (L-j); never change what a check accepts in order to make something pass.

What changed, and what to check:
1. package.runtime() now mirrors the DEPLOYED factory's own estimate (edl_rules._r4_moments, main a5ec0f17: "hook +
   clips + VO + FINAL_TAIL_S", each VO line "words / 2.5 + the 1.0 s pre-roll", FINAL_TAIL_S = 14.30 with the
   sign-off inside it). It replaced the builder's own estimate (2.6 words/s, no pre-roll, FIXED_S + the sign-off),
   which ran 3-4 s lower on three VO lines. Is the mirror faithful? Do min_vo_words / r4_max_vo_words /
   content_range stay consistent with it? Does the change loosen anything beyond what the factory itself accepts?
2. vo_fidelity.majority(runs, lines) implements the orchestrator's rule: "a verdict that flips on unchanged text: run
   that one verdict three times; majority decides; a 2-1 split is recorded in the package". Check: an unmeasured run
   never counts as a pass vote; a whole-reply failure (slot "-") votes fail on every slot; an even run count is
   refused; the votes and splits reach the sealed gate inventory (package.inventory row "vo_fidelity_verdict");
   the replayed tri-state stays honest; the merged result cannot pass a slot that most runs failed.
3. The driver tests/package/run_given_package.py: --to-existed (clip_02 = store words 1417-1432, ending "existed."),
   --verdict-runs (seeds 7, 8, 9), --title-text, the renderer_geometry evidence added to cut_evidence (outside the
   seal), and the transcribe chain without OpenAI under --xai-heimdall.
4. ORCHESTRATOR RULING 8 (08:29): transcript_truth.self_repair. "A token that the second recogniser hears and the
   primary does not, which is a truncated repetition of the clip's first word by the same speaker, is a self-repair:
   not a missing sentence start and not an L-v 2 disagreement. Exactly that token and nothing else." Check edges()
   (the IN skips exactly one such token, then needs a sentence end) and verify_segment (only a LEADING self-repair is
   dropped from the L-v 2 comparison). Can anything other than one same-speaker truncated prefix slip through?
5. ORCHESTRATOR RULING 9 (08:29): the moments R4 VO share cap is 45 % (was 40 %); 60-70 s stays hard; word caps
   unchanged. Check package.R4_MOMENTS_SHARE and everything derived from it.
6. The driver's --clip02 (a store moment as stored) and --precheck (step A + the second recogniser only, then stop).
7. The tests added or changed (test_gates.py majority test; test_angles.py runtime / R4 / self-repair tests).

Output: findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
Only state what you can verify from the diff provided. If uncertain, say so; do not guess. End with a verdict line:
"SHIP: yes | yes with conditions | no".


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
