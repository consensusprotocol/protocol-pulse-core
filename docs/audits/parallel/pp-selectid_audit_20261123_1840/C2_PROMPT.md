# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261123_1840
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 184 s finish=stop usage in 12873 / out 3783 usd_reported=0.002044 usd~0.095 (upper-bound price)

The code implements RULING 146 (3) to allow clips that follow a sponsor mention (but do not contain one) to be kept in the "never-empty" pass, provided a model confirms the clip itself is not an ad.

### Analysis against "PLEASE CHECK" requirements:

1.  **Can any words of the clip ITSELF that belong to an ad read reach a sealed package?**
    **No.** In `pipeline/moments.py:369`, `soft_why` is only assigned if `ad_read_marker(moment_text) is None`. If the clip contains a marker, `soft_why` remains `None`, and the `if why and not soft_why` block (line 370) triggers a deterministic `exclude` before the model is even called. Furthermore, the model is prompted to identify `ad_read` risks within the moment's own words, which results in a hard `exclude`.

2.  **Can the clean pass, or a cached verdict from the other pass, let a marked moment in?**
    **No.** 
    - **Clean Pass:** In `pipeline/package.py:1299`, `ad_before_soft` is called with `soft=False`, returning an empty dict. The filter in `_build` (line 3452) then defaults to `m["moment_id"] not in ad_read`, maintaining the strict deterministic exclusion.
    - **Cache Leakage:** In `pipeline/package.py:3150`, the cache key is explicitly modified when `soft` is True: `(m["moment_id"], seed, "ad_before")`. This ensures that a "keep" verdict generated for the never-empty pass cannot be retrieved by the clean pass, which uses the standard `(m["moment_id"], seed)` key.

3.  **Is the flag right (one per kept marked clip, counted toward the cap of 3)?**
    **Yes.** `pipeline/package.py:1336` generates a list of flags by iterating over `exc.items()`, creating one string per clip that has both `ad_before` and a `keep` verdict. These are passed into the `sponsor` gate row. Since this is a standard `FLAGGED` row in the gate inventory, it is processed by the existing `review_flags_of` and `content_flags` logic (as noted in the audit notes), which enforces the cap.

4.  **Does the gate_problems addition refuse anything a live pin legitimately carries?**
    **No.** The addition to `pipeline/package_pin.py:459` ensures that any `FLAGGED` row not in the `REQUIRED` set must be a recognized `SOFT_GATE` with valid flags. Since `"sponsor"` was added to `SOFT_GATES` (line 150), it is explicitly permitted. Other existing soft gates (graphics, runtime, etc.) remain permitted.

### Technical Correctness:
- **State Management:** `ad_before_soft` correctly pops existing `ad_before` marks (line 1295) to prevent stale marks from persisting across different build attempts or passes.
- **Data Flow:** The `chan_of` mapping is correctly implemented in `_build` (lines 106, 116) and passed to `inventory` to ensure the flags correctly identify the channel.
- **Test Coverage:** `TestRuling146SponsorBefore` comprehensively covers the deterministic vs. model-based decision paths, the cache key isolation, and the final gate status.

P1_OR_WORSE: 0

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 72 s finish=stop usage in 11028 / out 11342 usd_reported=0.001240 usd~0.203 (upper-bound price)

**Answers to the four questions**

1. **Can any words of the clip itself that belong to an ad read reach a sealed package?**  
   No. `exclusion_verdict` will exclude any moment that contains an ad‑read marker in its own words (`ad_read_marker(moment_text)` is non‑None), regardless of the `before_marker_soft` flag. Thus no ad‑read words can survive into a sealed package.

2. **Can the clean pass, or a cached verdict from the other pass, let a marked moment in?**  
   No. The clean pass calls `exclusion_verdict` with `before_marker_soft=False`, so a marker only in the sentence before the moment causes an exclusion. Cached verdicts from the other pass are keyed with `"ad_before"` and therefore are not reused by the clean pass.

3. **Is the flag right (one per kept marked clip, counted toward the cap of 3)?**  
   Yes. `inventory` creates a single flag per kept marked clip (`e.get("ad_before")` and `e.get("verdict") == "keep"`). The test `TestRuling146SponsorBefore` confirms that exactly one flag is produced per kept clip and that it is counted correctly.

4. **Does the `gate_problems` addition refuse anything a live pin legitimately carries?**  
   No. The new check only flags rows that are not in the required set, are `FLAGGED`, and are not a soft gate with flags (`flagged_ok`). Since the sponsor gate is soft and its flags are present, it passes the check. The test `test_an_extra_flagged_row_stands_only_on_a_soft_gate_with_flags` demonstrates that legitimate flagged rows are not rejected.

**Findings**

| Severity | Finding | Comment |
|----------|---------|---------|
| **P0** | None | All logic paths behave as intended; no data loss or gate bypass. |
| **P1** | None | No critical defects requiring pre‑merge fix. |
| **P2** | None | No minor improvements needed. |
| **P3** | None | No nitpicks. |

**P1_OR_WORSE: 0**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 241 s finish=stop usage in 12100 / out 8426 usd_reported=0.007529 usd~0.163 (upper-bound price)



# Code Audit — pp-selectid / RULING 146 (3) "Sponsor Before" Soft Gate

## Scope

Reviewed the 276-line diff across `pipeline/moments.py`, `pipeline/package.py`, `pipeline/package_pin.py`, and two test files. Checked all four requested questions plus general correctness against the governing laws.

---

## Findings

### [P2] `n` field in the "sponsor" gate row reports the wrong count

**Location:** `package.py`, `inventory()` — the new `"sponsor"` row (diff line 135).

```python
"n": len(exc)
```

`exc` is the **entire** exclusion-results dict (every moment that went through the exclusion model, regardless of verdict or flag). The other FLAGGED rows in the same inventory use `n` for the count of items *in that category* (e.g. `"n": len(visual)` for graphics). Here, if 12 moments pass through exclusion and only 1 is kept with an `ad_before` mark, the report reads `"n": 12` next to a single flag. A reviewer scanning the gate report will misread the scope.

**Fix:** count only the flagged entries:

```python
"n": sum(1 for e in exc.values() if e.get("ad_before") and e.get("verdict") == "keep")
```

This does not affect the cap (which counts the `flags` list, not `n`), but it makes the sealed report internally consistent and prevents a human from thinking 12 clips are sponsor-adjacent when only 1 is.

---

### [P3] `ad_before_soft` distinguishes before-markers from moment-markers by `str.endswith`

**Location:** `package.py:1305` (diff line 55).

```python
out = {k: v for k, v in ad_read.items() if soft and v.endswith("in the sentence before it")}
```

The entire soft/hard split hinges on the reason string ending with the exact phrase `"in the sentence before it"`. If `ad_read_marker` (moments.py:358, unchanged) ever reformats its return (e.g. appends a channel name, changes word order, or localises), the filter silently stops matching and **every** before-marker reverts to a hard exclude — the never-empty pass loses its only concession with no error, no log, no test failure (the existing tests hard-code the same string, so they'd pass against the old format but the production `ad_read_out` would produce the new one).

Not a correctness bug today, but a one-word refactor in `ad_read_marker` would silently disable the feature. A structured return (e.g. `{"reason": ..., "location": "before"|"moment"}`) or a dedicated sentinel would be more robust.

---

### [P3] `ad_before_soft` mutates the caller's list in place

**Location:** `package.py:1303-1308` (diff lines 53-58).

```python
for m in ms:
    m.pop("ad_before", None)
...
for m in ms:
    if m["moment_id"] in out:
        m["ad_before"] = out[m["moment_id"]]
```

The function both clears and re-sets `ad_before` on the dicts in `ms`. In the current sequential pipeline this is safe (the list is immediately re-filtered and the original is not reused), but the side-effect is invisible from the signature. A future caller that reuses the same list of moment dicts across two `_build` invocations (e.g. a retry or a dry-run) would see stale marks. A `dataclasses.replace`-style copy or a return-only design (no mutation) would remove the foot-gun.

---

## Answers to the four requested checks

| # | Question | Verdict |
|---|----------|---------|
| 1 | Can words of the clip **itself** that belong to an ad read reach a sealed package? | **No.** `ad_read_marker(moment_text)` (no `before_text`) is checked independently; a truthy result forces `soft_why = None` → deterministic hard exclude before any model call. Even if the deterministic marker list misses a phrase, the model's `ad_read` risk is a hard exclude (test `test_the_model_decides_a_marker_in_the_sentence_before`, second assertion). Two independent layers. |
| 2 | Can the clean pass, or a cached verdict from the other pass, let a marked moment in? | **No.** Clean pass: `soft=False` → `ad_before_soft` returns `{}` → no moment is marked → `before_marker_soft=False` → deterministic screen still hard-excludes. Cache key: soft pass uses `(mid, seed, "ad_before")`; clean pass uses `mid` or `(mid, seed)`. Disjoint key spaces; a cached verdict from one pass is never read by the other. Verified by `test_the_mark_is_the_passs_own_and_the_cache_key_its_own`. |
| 3 | Is the flag right (one per kept marked clip, counted toward the cap of 3)? | **Yes, with the P2 caveat on `n`.** The `flags` list is built with a list-comprehension over `exc.items()` filtered to `ad_before` + `verdict == "keep"` — exactly one entry per kept marked clip. The existing `content_flags` cap (package_pin.py:440) counts every FLAGGED row's `flags` list, so the new row's flags are included in the cap of 3. The `n` field is wrong (see P2) but does not affect the cap. |
| 4 | Does the `gate_problems` addition refuse anything a live pin legitimately carries? | **No.** The new loop only fires for gates **outside** the required s

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats answered: 3 of 3 (gpt-oss-20b in the first run; qwen3.8-27b and gemma-4-31b-it were HTTP 429 there and answered
in a retry of the same prompt, seats limited to those two). P0/P1: 0, 0, 0.
- qwen P2 (the sponsor row's "n" is len(exc), every clip's exclusion verdict, not the flagged count): DISPROVED as a
  defect. "n" in these rows is how many items the row's check read: the sibling graphics row has n = len(visual), one
  visual record per clip, flagged or not. The flags list carries one sentence per kept marked clip (qwen's own answer
  to check 3: "exactly one entry per kept marked clip"). No change.
- qwen P3 (ad_before_soft tells a before-marker by str.endswith): the reason strings are moments.ad_read_marker's own
  two fixed forms (moments.py:365: "ad-read marker '<hit>' in the moment" | "... in the sentence before it"); the test
  test_the_mark_is_the_passs_own_and_the_cache_key_its_own feeds both forms. No change.
- qwen P3 (ad_before_soft mutates the list in place): by design, the pass's own copies (with_verdict gives _build its
  own copy of every moment; the mark is popped first, test-pinned, mutation S5 killed). No change.
All seats: check 1 (clip's own ad words) NO; check 2 (clean pass / cross-pass cache) NO; check 3 flag right YES;
check 4 (gate_problems refuses a legitimate live pin) NO. Cycle 2 cross-examines the same diff.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261123_1840/C2_STEP.diff (276 lines)
```
   1 | diff --git a/pipeline/moments.py b/pipeline/moments.py
   2 | index 7d55d31..db6a324 100644
   3 | --- a/pipeline/moments.py
   4 | +++ b/pipeline/moments.py
   5 | @@ -366,16 +366,23 @@ def ad_read_marker(moment_text, before_text=""):
   6 |      return None
   7 |  
   8 |  
   9 | -def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7, avoid_model=None):
  10 | +def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7, avoid_model=None,
  11 | +                      before_marker_soft=False):
  12 |      """-> {"verdict": "keep" | "exclude", "why", "risks", "backend", "measured", "replayed"}: a deterministic ad-read
  13 |      screen (a marker in the moment, or in the sentence right before it: an ad read runs on), then the blind model
  14 |      verdict (role "exclusion_verdict", never on the moment's own miner: avoid_model; audit p2 C3); any hard risk, a
  15 |      moment not about Bitcoin, an unreadable or uncertain verdict excludes (law L-m). An unreadable or unavailable verdict
  16 | -    is also NOT measured (the exam adapter reports it as such)."""
  17 | +    is also NOT measured (the exam adapter reports it as such).
  18 | +    before_marker_soft (RULING 146 (3), orchestrator 07:55 ET Nov 18; PBX 08:34: 'we never include any sponsor material
  19 | +    ever, but if it doesn't have any in it then it is fine to use'; the never-empty pass only): a marker ONLY in the
  20 | +    sentence before the moment no longer excludes by itself; the model reads the moment with its context, and its
  21 | +    'ad_read' risk (the moment's own words in the ad, e.g. an ad read's opening line) excludes as always. Kept, the
  22 | +    verdict carries "ad_before" (the screen's reason) for the package's flag. A marker in the moment stays HARD."""
  23 |      import providers as P
  24 |      from story_semantics import quote_data
  25 |      why = ad_read_marker(moment_text, before_text)
  26 | -    if why:
  27 | +    soft_why = why if (why and before_marker_soft and ad_read_marker(moment_text) is None) else None   # RULING 146 (3)
  28 | +    if why and not soft_why:
  29 |          return {"verdict": "exclude", "why": why, "risks": ["ad_read"], "backend": "deterministic", "measured": True,
  30 |                  "replayed": False}
  31 |      def parse(text):
  32 | @@ -400,4 +407,5 @@ def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7
  33 |      if obj["about_bitcoin"] != "yes":
  34 |          return dict(meas, verdict="exclude", why=f"about Bitcoin: {obj['about_bitcoin']}: {str(obj['why'])[:200]}",
  35 |                      risks=[], backend=r.backend)
  36 | -    return dict(meas, verdict="keep", why=str(obj["why"])[:200], risks=[], backend=r.backend)
  37 | +    return dict(meas, verdict="keep", why=str(obj["why"])[:200], risks=[], backend=r.backend,
  38 | +                **({"ad_before": soft_why} if soft_why else {}))           # RULING 146 (3): the package flags it
  39 | diff --git a/pipeline/package.py b/pipeline/package.py
  40 | index 3c652a6..dfe1255 100644
  41 | --- a/pipeline/package.py
  42 | +++ b/pipeline/package.py
  43 | @@ -1296,6 +1296,21 @@ def ad_read_out(ms, sources):
  44 |      return out
  45 |  
  46 |  
  47 | +def ad_before_soft(ms, ad_read, soft):
  48 | +    """RULING 146 (3) (orchestrator 07:55 ET Nov 18): in the never-empty pass, a moment the deterministic ad-read screen
  49 | +    refuses ONLY for a marker in the sentence before it stays in the pool, marked ad_before (this pass's own mark on
  50 | +    its own copies: popped first, never carried in). exclusion_for() then asks the model with the context; its ad_read
  51 | +    risk (the moment's own words in the ad) still excludes. A marker in the moment's own words stays HARD; the clean
  52 | +    pass marks nothing. -> {moment id: the screen's reason}."""
  53 | +    for m in ms:
  54 | +        m.pop("ad_before", None)
  55 | +    out = {k: v for k, v in ad_read.items() if soft and v.endswith("in the sentence before it")}
  56 | +    for m in ms:
  57 | +        if m["moment_id"] in out:
  58 | +            m["ad_before"] = out[m["moment_id"]]
  59 | +    return out
  60 | +
  61 | +
  62 |  def trim_variant(m, sources):
  63 |      """RULING 33 PART 2 (the render merged it at 11e361cc; the orchestrator's 04:58 item 42, "use it now"). A moment
  64 |      whose first word is ONE of TRIM_WORDS, left out by the render's STAND_ALONE opener rule, may be cut one word in.
  65 | @@ -3133,7 +3148,8 @@ def paid_gates(router, pk, sources, a_by, levels, now, writers_v, writers_f, poo
  66 |  
  67 |  
  68 |  def exclusion_for(router, m, sources, cache, seed=7):
  69 | -    key = m["moment_id"] if seed == 7 else (m["moment_id"], seed)
  70 | +    soft = bool(m.get("ad_before"))                   # RULING 146 (3): the never-empty pass's sponsor-before mark, and
  71 | +    key = (m["moment_id"] if seed == 7 else (m["moment_id"], seed)) if not soft else (m["moment_id"], seed, "ad_before")
  72 |      if key not in cache:
  73 |          import moments as M
  74 |          src = src_of(m, sources)
  75 | @@ -3142,8 +3158,8 @@ def exclusion_for(router, m, sources, cache, seed=7):
  76 |              cache[key] = {"verdict": "exclude", "why": "no context: the moment's context is unavailable",   # caption
  77 |                            "risks": [], "backend": None, "measured": False, "replayed": False}            # record)
  78 |          else:
  79 | -            cache[key] = M.exclusion_verdict(router, m["text"], before, after, seed=seed,
  80 | -                                             avoid_model=(m.get("mined") or {}).get("by"))
  81 | +            cache[key] = M.exclusion_verdict(router, m["text"], before, after, seed=seed,   # its own cache key
  82 | +                                             avoid_model=(m.get("mined") or {}).get("by"), before_marker_soft=soft)
  83 |      return cache[key]
  84 |  
  85 |  
  86 | @@ -3433,7 +3449,12 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  87 |      #   a variant of a moment that keeps its own place (ruling 94 a) sits beside it: one line-up never takes both (one
  88 |      #   video at most once, L-y 4)
  89 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
  90 | -    ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
  91 | +    ad_soft = ad_before_soft(ms, ad_read, soft)       # RULING 146 (3): the never-empty pass's sponsor-before moments
  92 | +    if ad_soft:
  93 | +        log(f"  RULING 146 (3) NEVER EMPTY: {len(ad_soft)} moment(s) with a sponsor marker only in the sentence before "
  94 | +            f"them go to the exclusion model (its ad_read risk stays HARD), flagged if kept: "
  95 | +            f"{', '.join(k[:8] for k in sorted(ad_soft))}")
  96 | +    ms = [m for m in ms if m["moment_id"] not in ad_read or m["moment_id"] in ad_soft]   # around a moment it refuses
  97 |      n_ch = len({m["channel_id"] for m in ms})
  98 |      if candidate is None and n_ch < 3:
  99 |          # RULING 109 (free gates first) on the medley's 3-channel rule (orchestrator 08:56 ET Nov 15: "one channel
 100 | @@ -3954,7 +3975,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 101 |                                  stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 102 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 103 |                                  last_resort=pin_last_resort(pk), soft=soft,   # RULING 102; RULING 137 stage 1
 104 | -                                who={sg["label"]: sg.get("channel") for sg in pk["segments"]},   # RULING 138 (3)
 105 | +                                who={sg["label"]: sg.get("channel") for sg in pk["segments"]},
 106 | +                                chan_of={sg["moment_id"]: sg.get("channel") for sg in pk["segments"]},   # 146 (3)   # RULING 138 (3)
 107 |                                  seg_flags={sg["label"]: (cleared.get(sg["moment_id"]) or {}).get("step_a_flags")
 108 |                                             for sg in pk["segments"]},                          # RULING 137 stage 2a
 109 |                                  mids={sg["moment_id"]: sg["label"] for sg in pk["segments"]})
 110 | @@ -4477,7 +4499,9 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 111 |                                              visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 112 |                                              value=val,                       # ruling 91: the takeaway earned its place
 113 |                                              last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 114 | -                                            soft=soft, who={sg["label"]: sg.get("channel")   # RULING 137 / 138 (3)
 115 | +                                            soft=soft,
 116 | +                                            chan_of={sg["moment_id"]: sg.get("channel") for sg in pk["segments"]},
 117 | +                                            who={sg["label"]: sg.get("channel")   # RULING 137 / 138 (3)
 118 |                                                              for sg in pk["segments"]},
 119 |                                              seg_flags={sg["label"]: (cleared.get(sg["moment_id"]) or {}).get(
 120 |                                                  "step_a_flags") for sg in pk["segments"]},    # RULING 137 stage 2a
 121 | @@ -4613,6 +4637,7 @@ def _spent(spend):
 122 |  
 123 |  
 124 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None, short=None,
 125 | +              chan_of=None,
 126 |                hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None,
 127 |                seg_flags=None, mids=None):
 128 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 129 | @@ -4712,6 +4737,12 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 130 |                                 **({"status": "FLAGGED", "flags": ["The opening clip may start abruptly."]}   # RULING
 131 |                                    if soft and hook.get("soft") is True and hook.get("pass") is not True else {}))}   # 146
 132 |             if hook is not None else {}),                                                                      # (2)
 133 | +        **({"sponsor": {"status": "FLAGGED", "by": "moments.exclusion_verdict (ruling 146 (3)): a sponsor mention in "
 134 | +                                                   "the sentence before the clip only; its own words judged by the "
 135 | +                                                   "exclusion model", "replayed": False, "n": len(exc), "flags": [
 136 | +                            f"The clip ({(chan_of or {}).get(mid) or 'its channel'}) comes right after a sponsor "
 137 | +                            f"mention." for mid, e in exc.items() if e.get("ad_before") and e.get("verdict") == "keep"]}}
 138 | +           if any(e.get("ad_before") and e.get("verdict") == "keep" for e in exc.values()) else {}),
 139 |          **({"graphics": {"status": "FLAGGED", "by": "visual_pin.graphics_only (ruling 146 (1)): the show's own "
 140 |                                                      "on-screen graphics, whole in a package sealed 16:9 only",
 141 |                           "replayed": False, "n": len(visual), "flags": [
 142 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 143 | index 9cdc53c..bbbba23 100644
 144 | --- a/pipeline/package_pin.py
 145 | +++ b/pipeline/package_pin.py
 146 | @@ -49,6 +49,8 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 147 |                          "graphics",                        # RULING 146 (1): the show's own graphics, 16:9 only
 148 |                          "takeaway_value",                  # RULING 150: the closing line's value verdict (ruling
 149 |                          #   91), a measured one; fidelity, length and the banned words stay HARD
 150 | +                        "sponsor",                         # RULING 146 (3): a sponsor mention in the sentence before
 151 | +                        #   a clip only, the clip kept by the exclusion model (its ad_read risk stays HARD)
 152 |                          "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
 153 |  #   package.LY_FLOOR_S (30 s) or more, never-empty pass only (the render's G5 follows this sealed row)
 154 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 155 | @@ -454,6 +456,10 @@ def gate_problems(gates, required=REQUIRED_GATES):
 156 |              out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
 157 |          elif row.get("replayed") is not False:
 158 |              out.append(f"{g}: replayed or not stated (never deliverable, law L-j)")
 159 | +    for g, row in gates.items():                     # RULING 146 (3) (its audit's S8): a FLAGGED row outside the
 160 | +        if g not in required and isinstance(row, dict) and row.get("status") == "FLAGGED" and \
 161 | +                not flagged_ok(g, row):              # required set stands, as any other, only on a SOFT gate with flags
 162 | +            out.append(f"{g}: FLAGGED without a soft gate and its plain flags (ruling 137)")
 163 |      return out
 164 |  
 165 |  
 166 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 167 | index 0e4d42a..f965429 100644
 168 | --- a/tests/package/test_medley.py
 169 | +++ b/tests/package/test_medley.py
 170 | @@ -834,7 +834,8 @@ class Rig:
 171 |              "paid_gates": lambda *a, **k: (self.fids.pop(0) if self.fids else fid, cx),
 172 |              "exclusion_for": lambda router, m, *a, **k: {"verdict": "drop" if m["moment_id"] in self.excluded else
 173 |                                                           "keep", "measured": True, "replayed": False,
 174 | -                                                         "backend": "xai:grok"},
 175 | +                                                         "backend": "xai:grok",     # RULING 146 (3): as the real one
 176 | +                                                         **({"ad_before": m["ad_before"]} if m.get("ad_before") else {})},
 177 |              "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
 178 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 179 |              "hook_onset_for": self.onset,
 180 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 181 | index a614ec0..fee382c 100644
 182 | --- a/tests/package/test_ruling_137.py
 183 | +++ b/tests/package/test_ruling_137.py
 184 | @@ -684,6 +684,91 @@ class TestRuling150ValueSoft(unittest.TestCase):
 185 |      def test_no_verdict_stays_hard(self):
 186 |          _, pk = self.run_rig(measured=False)
 187 |          self.assertIsNone(pk)
 188 | +class TestRuling146SponsorBefore(unittest.TestCase):
 189 | +    """RULING 146 (3) (orchestrator 07:55 ET Nov 18; PBX 08:34 'we never include any sponsor material ever, but if it
 190 | +    doesn't have any in it then it is fine to use'), the never-empty pass: a sponsor marker ONLY in the sentence before
 191 | +    a clip goes to the exclusion model with the context; its ad_read risk (the clip's own words in the ad: Natalie
 192 | +    Brunell 6e79ceaa was the opening line of The Bitcoin Way's read) excludes, HARD; kept, the package flags 'The clip
 193 | +    (X) comes right after a sponsor mention.' A marker in the clip's own words stays HARD; the clean pass is unchanged."""
 194 | +    BEFORE = "Use my promo code stories to get 10% off. This episode is sponsored by BitKey."
 195 | +    CLIP = "If your Bitcoin can be frozen or monitored by an exchange, it's not yours."
 196 | +    SPONSOR = "ad-read marker 'sponsored' in the sentence before it"
 197 | +
 198 | +    def verdict(self, text, before, soft, reply):
 199 | +        import json
 200 | +        import types
 201 | +        import moments as M
 202 | +        import providers as P
 203 | +        calls = []
 204 | +
 205 | +        def fake(router, role, prompt, parse, n, seed, avoid_model=None):
 206 | +            calls.append(role)
 207 | +            return types.SimpleNamespace(backend="heimdall:deepseek", replayed=False), parse(json.dumps(reply))
 208 | +        with mock.patch.object(P, "call_parsed", fake):
 209 | +            return M.exclusion_verdict(None, text, before, "", before_marker_soft=soft), calls
 210 | +
 211 | +    def test_the_model_decides_a_marker_in_the_sentence_before(self):
 212 | +        keep = {"risks": [], "about_bitcoin": "yes", "why": "her own view on custody"}
 213 | +        v, calls = self.verdict(self.CLIP, self.BEFORE, True, keep)
 214 | +        self.assertEqual((v["verdict"], v.get("ad_before"), calls), ("keep", self.SPONSOR, ["exclusion_verdict"]))
 215 | +        ad = {"risks": ["ad_read"], "about_bitcoin": "yes", "why": "the opening line of the next ad read"}
 216 | +        v, _ = self.verdict(self.CLIP, self.BEFORE, True, ad)
 217 | +        self.assertEqual((v["verdict"], v.get("ad_before")), ("exclude", None))           # the clip IS the ad: HARD
 218 | +
 219 | +    def test_a_marker_in_the_clip_and_the_clean_pass_stay_hard(self):
 220 | +        keep = {"risks": [], "about_bitcoin": "yes", "why": "x"}
 221 | +        for text, before, soft in ((self.CLIP + " Use my promo code stories.", "", True),
 222 | +                                   (self.CLIP, self.BEFORE, False)):
 223 | +            v, calls = self.verdict(text, before, soft, keep)
 224 | +            self.assertEqual((v["verdict"], v["backend"], calls), ("exclude", "deterministic", []), (text, soft))
 225 | +
 226 | +    def test_the_mark_is_the_passs_own_and_the_cache_key_its_own(self):
 227 | +        ms = [{"moment_id": "a", "ad_before": "stale"}, {"moment_id": "b"}]
 228 | +        ad_read = {"a": self.SPONSOR, "b": "ad-read marker 'promo code' in the moment"}
 229 | +        self.assertEqual(PK.ad_before_soft(ms, ad_read, False), {})
 230 | +        self.assertNotIn("ad_before", ms[0])                                              # popped, never carried in
 231 | +        self.assertEqual(PK.ad_before_soft(ms, ad_read, True), {"a": self.SPONSOR})
 232 | +        self.assertEqual((ms[0].get("ad_before"), ms[1].get("ad_before")), (self.SPONSOR, None))
 233 | +        seen, cache = [], {}
 234 | +        with mock.patch.object(PK, "src_of", lambda m, s: "src"), \
 235 | +                mock.patch.object(PK.CI, "context_around", lambda *a: (self.BEFORE, "")):
 236 | +            import moments as M
 237 | +            with mock.patch.object(M, "exclusion_verdict", lambda *a, **k: seen.append(k) or {"verdict": "keep"}):
 238 | +                PK.exclusion_for(None, dict(ms[0], text=self.CLIP, sentences=[1, 1], words=[0, 3]), {}, cache)
 239 | +                PK.exclusion_for(None, dict(ms[1], text=self.CLIP, sentences=[1, 1], words=[0, 3]), {}, cache)
 240 | +        self.assertEqual([k["before_marker_soft"] for k in seen], [True, False])
 241 | +        self.assertEqual(sorted(map(str, cache)), sorted(map(str, [("a", 7, "ad_before"), "b"])))
 242 | +
 243 | +    def run_rig(self, never_empty, excluded=()):
 244 | +        import test_medley as TM
 245 | +        from test_moments import pm
 246 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 247 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 248 | +                   excluded=excluded, follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]})
 249 | +        r.build_kw = {"never_empty": never_empty}
 250 | +        with mock.patch.object(PK, "ad_read_out", lambda ms, sources: {"x": self.SPONSOR}):
 251 | +            return r.run()["package"]
 252 | +
 253 | +    def test_a_clip_after_a_sponsor_mention_seals_flagged_never_empty_only(self):
 254 | +        self.assertIsNone(self.run_rig(False))                                            # the clean pass: refused
 255 | +        pk = self.run_rig(True)
 256 | +        self.assertIsNotNone(pk)
 257 | +        ch = next(s["channel"] for s in pk["segments"] if s["moment_id"] == "x")
 258 | +        self.assertEqual((pk["gates"]["sponsor"]["status"], pk["gates"]["sponsor"]["flags"]),
 259 | +                         ("FLAGGED", [f"The clip ({ch}) comes right after a sponsor mention."]))
 260 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 261 | +        self.assertIsNone(self.run_rig(True, excluded={"x"}))                              # the model excludes: HARD
 262 | +
 263 | +    def test_an_extra_flagged_row_stands_only_on_a_soft_gate_with_flags(self):
 264 | +        pk = self.run_rig(True)
 265 | +        req = PP.required_gates(pk)
 266 | +        self.assertNotIn("sponsor", req)                              # an extra row: gate_problems reads it as well
 267 | +        made_up = {"status": "FLAGGED", "flags": ["A plain sentence."], "replayed": False}
 268 | +        self.assertEqual(PP.gate_problems(dict(pk["gates"], made_up=made_up), req),
 269 | +                         ["made_up: FLAGGED without a soft gate and its plain flags (ruling 137)"])
 270 | +        no_flags = dict(pk["gates"], sponsor=dict(pk["gates"]["sponsor"], flags=[]))
 271 | +        self.assertEqual(PP.gate_problems(no_flags, req),
 272 | +                         ["sponsor: FLAGGED without a soft gate and its plain flags (ruling 137)"])
 273 |  
 274 |  
 275 |  class TestRuling148RuntimeFloor(unittest.TestCase):
 276 | 
```

---

pp-selectid: RULING 146 (3) (orchestrator 07:55 ET Nov 18; restated 18:18 ET Nov 23: "HARD: ANY sponsor or ad-read
words inside the clip (PBX: 'we never include any sponsor material, ever')"; "SOFT, flagged: a clip right after a
sponsor mention"). Builder-only: the integrator's render never re-checks sponsor mentions (its DoD: "nothing checks for
a sponsor mention").
THE CHANGE (never-empty pass only; the clean pass unchanged):
- moments.exclusion_verdict(..., before_marker_soft=False) (moments.py:369): with before_marker_soft, a deterministic
  ad-read marker (ad_read_marker, moments.py:358, unchanged) found ONLY in the sentence before the moment (none in the
  moment's own words) no longer excludes by itself: the blind model reads the moment with its context; ANY risk it
  names (ad_read among them: the moment's own words in the ad) excludes as always; a kept verdict carries "ad_before"
  (the screen's reason). A marker in the moment's own words stays a deterministic exclude.
- package.ad_before_soft (package.py:1299): pops every moment's old mark first; in the never-empty pass only, marks the
  moments the free screen ad_read_out (package.py:1280, unchanged) refused ONLY for a marker "in the sentence before
  it"; _build (package.py:3452) keeps those moments in the pool; exclusion_for (package.py:3150) passes the mark as
  before_marker_soft under its OWN cache key.
- inventory (package.py:4740): an extra "sponsor" row, FLAGGED, one flag per kept marked clip: "The clip (<channel>)
  comes right after a sponsor mention." package_pin.SOFT_GATES += "sponsor".
- package_pin.gate_problems (package_pin.py:446): ALSO checks every FLAGGED row outside the required set with the
  unchanged flagged_ok (package_pin.py:407: a SOFT gate and non-empty plain flags). The integrator's check_pin_only
  calls gate_problems live: this only adds refusals (the live soft rows graphics / runtime / hook_onset /
  pbx_exception are all in SOFT_GATES). review_flags_of (414) and the cap (content_flags, 440) already count every
  FLAGGED row's flags.
Files: pipeline/moments.py, pipeline/package.py, pipeline/package_pin.py, tests/package/test_medley.py (the rig's
exclusion stub returns the mark as the real one does), tests/package/test_ruling_137.py.
TESTS (TestRuling146SponsorBefore): the model decides a marker in the sentence before (keep: marked; ad_read: exclude);
a marker in the clip, and the clean pass, stay deterministic excludes with no model call; the mark is the pass's own
and the cache key its own; the real build() seals FLAGGED in the never-empty pass only and refuses when the model
excludes; an extra FLAGGED row stands only on a soft gate with flags. Mutations 11 of 11 killed.
PLEASE CHECK: (1) can any words of the clip ITSELF that belong to an ad read reach a sealed package? (2) can the clean
pass, or a cached verdict from the other pass, let a marked moment in? (3) is the flag right (one per kept marked clip,
counted toward the cap of 3)? (4) does the gate_problems addition refuse anything a live pin legitimately carries?


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
