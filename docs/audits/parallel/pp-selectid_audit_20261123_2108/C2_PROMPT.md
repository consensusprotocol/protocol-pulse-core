# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261123_2108
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 30 s finish=stop usage in 8700 / out 4796 usd_reported=0.000605 usd~0.098 (upper-bound price)

**Findings**

| # | Severity | Issue | Explanation |
|---|----------|-------|-------------|
| 1 | **P1** | `content_flags` can count more than the allowed 3 kinds of review flag | `content_flags` now counts distinct *kinds* (via `flag_kind`) for every flagged row. If a package contains more than three distinct kinds (e.g., many different soft codes or edge codes), the cap check in `review_problems` will still allow the package to pass because the cap is only enforced on the number of kinds, not on the number of distinct soft codes. This violates the “at most 3 KINDS per package” rule. |
| 2 | **P2** | `flag_kind` may collapse distinct flags that share the same gate string but have different sentences | For non‑PER_CLIP_KIND gates, `flag_kind` returns `f"{gate}: {sentence}"`. If two different flags share the same gate string but have identical sentences, they will be counted as a single kind. While this is unlikely, it could hide a distinct flag if the sentence is accidentally identical. |
| 3 | **P3** | `kind_sentences` may raise a `KeyError` if an unexpected code is encountered | `kind_sentences` uses `STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY[c]`. If a new soft or edge code is introduced that is not present in either mapping, the function will raise a `KeyError`. This is a defensive‑coding issue that could surface in future extensions. |
| 4 | **P3** | `seg_marks` counts the hook flag via `hook_own(segs[0])` without checking that the first segment actually represents the hook | If the first segment in a line‑up is not the hook (e.g., a mis‑ordered list), `seg_marks` will incorrectly count a hook flag. The current logic assumes the first segment is always the hook, which may not hold in all pipeline paths. |

**P1_OR_WORSE**: **1** (only the cap‑violation issue is a P1; the others are P2/P3).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 230 s finish=stop usage in 9409 / out 8485 usd_reported=0.007305 usd~0.156 (upper-bound price)



# Code Audit — pp-selectid / RULING 155 (1)

## Findings

### [P1] `kind_sentences` will raise `KeyError` for any soft/edge code absent from the `_MANY` dicts when it appears on ≥ 2 clips

**Location:** `pipeline/package.py`, `kind_sentences`, line 37 of the diff:

```python
out.append(f"{COUNT_WORDS.get(len(lbs), str(len(lbs)))} clips ({chans}): "
           f"{STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY[c]}.")
```

The original `flag_sentence` falls back through `STEP_A_SOFT.get(code) or EDGE_WORDS[code]` — two dicts that together cover every code the pipeline can emit. The new multi-clip path falls back through `STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY[c]`. `STEP_A_SOFT_MANY` has exactly four keys (NOT_OWN_SINCERE, REFERENT_OUTSIDE, CONDITION_OUTSIDE, UNCERTAIN) and `EDGE_WORDS_MANY` has two (EDGE_IN, EDGE_OUT). If `STEP_A_SOFT` (or `EDGE_WORDS`) contains any additional code — a new soft code added later, a legacy code, a code the orchestrator introduces — and that code lands on two or more clips, `STEP_A_SOFT_MANY.get(c)` returns `None`, the `or` evaluates `EDGE_WORDS_MANY[c]`, and the pipeline crashes with `KeyError`.

The crash is fail-closed (M12) so no bad package ships, but it blocks every package that carries the affected code on ≥ 2 clips. The fix is to mirror the original's two-dict coverage:

```python
body = STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY.get(c) or STEP_A_SOFT.get(c) or EDGE_WORDS[c]
```

or, better, build `STEP_A_SOFT_MANY` / `EDGE_WORDS_MANY` as derived views of the canonical dicts so they can never drift.

---

### [P2] `COUNT_WORDS` tops out at 5; a 6-clip medley produces "6 clips" which `_CLIP_REF` cannot strip, silently inflating the kind count

**Location:** `pipeline/package.py` line 9 (`COUNT_WORDS = {2: "Two", …, 5: "Five"}`) and `pipeline/package_pin.py` `_CLIP_REF`.

The medley is hook + up to 5 clips = 6 positions. If all six carry the same code, `COUNT_WORDS.get(6, str(6))` yields `"6"`, producing the sentence `"6 clips (A, B, C, D, E, F): …"`. The `_CLIP_REF` regex expects `[A-Z][a-z]+ clips` (a capitalised word), so `"6 clips"` does not match. The clip reference is never stripped, the kind string retains the channel list, and two different groups of six clips with the same code would count as **two** kinds instead of one — potentially pushing a package over the 3-kind cap that should pass.

Fix: extend `COUNT_WORDS` to at least 6 (or use `num2words`), and add a test with 6 clips.

---

### [P2] `content_flags` now filters to `status == "FLAGGED"` rows; the original counted every flag returned by `review_flags_of` regardless of row status

**Location:** `pipeline/package_pin.py`, new `content_flags`.

Original:
```python
return len([f for f in review_flags_of(gates) if f not in exc])
```

New:
```python
return len({flag_kind(g, f) for g, row in gates.items()
            if g != EXCEPTION_GATE and isinstance(row, dict)
            and row.get("status") == "FLAGGED"
            for f in row.get("flags") or [] if isinstance(f, str)})
```

If any gate row can carry a non-empty `flags` list while its `status` is `"PASS"` or `"MONITORING"` (e.g., an informational note attached to a passing gate), the old code counted those flags toward the cap; the new code does not. The ruling text says "the FLAGGED rows," so this is likely intentional, but it is a silent behavioural change from the original. Verify that no production gate row ever has `flags` without `status == "FLAGGED"`, or add a comment / assertion documenting the invariant.

---

### [P3] No test exercises the multi-clip path for a code that is *not* in `STEP_A_SOFT_MANY` / `EDGE_WORDS_MANY`

The `TestRuling155FlagKinds` suite only uses REFERENT_OUTSIDE, NOT_OWN_SINCERE, EDGE_OUT, and STAND_ALONE — all of which have `_MANY` entries. A regression test that feeds a hypothetical `"TOPIC_DRIFT"` code on two clips would have caught the P1 KeyError above.

---

### [P3] `_CLIP_REF` does not match "The first clip"

The alternation is `opening|second|third|fourth|fifth`. If any code path ever emits `"The first clip (…): …"` (e.g., a future layout where the hook is labelled "first" rather than "opening"), the prefix won't be stripped and the kind will include the channel name, breaking the merge. Low risk given the current naming convention, but worth a comment or a broader pattern (`The \w+ clip`).

---

## Answers to the four review questions

| # | Question | Verdict |
|---|----------|---------|
| 1 | Can a package carry > 3 kinds? | **No.** `content_flags` counts distinct kinds; `review_problems` emits a problem string when `n > cap`; the integrator's `check_pin_only` treats that as a pin failure. The test confirms 4 kinds → refused, 3 → pass. |
| 2 | Can two different kinds collapse to one? | **No, in the current code.** `flag_kind` prefixes non-PER_CLIP_KIND kinds with the gate name, and th

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats answered: 2 of 2 (qwen3.8-27b; gpt-oss-20b at effort low). gemma's breaker was open (the first start refused).
- gpt-oss P1 ("content_flags can count more than 3 kinds and still pass"): DISPROVED. The rule IS kinds (ruling 155
  (1)); review_problems refuses n > cap with n the kinds: test_the_cap_counts_kinds asserts '4 kinds of review flag,
  over 3' for four kinds, and mutation K1 (counting every flag) fails it.
- qwen P1 (kind_sentences raises KeyError for a code with no plural wording on 2+ clips): UNREACHABLE today (the
  context_a row flags only when every code is in STEP_A_SOFT, all four worded in STEP_A_SOFT_MANY; soft_edges yields only
  EDGE_IN / EDGE_OUT, both in EDGE_WORDS_MANY), HARDENED anyway: the merged sentence falls back to the one-clip wording,
  then the code itself.
- qwen P2 (a 6-clip merged sentence is not stripped by _CLIP_REF): a medley has at most 5 segments (hook + 2-4 clips);
  within one package each code is ONE sentence, so the count is right either way. No change.
- qwen P2 (content_flags filters FLAGGED rows): review_flags_of reads only FLAGGED rows too. DISPROVED.
- gpt-oss P2 (identical sentences of one gate collapse): intended (one kind). P3s: no change.
Cycle 2 cross-examines the hardened diff.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261123_2108/C2_STEP.diff (185 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index dfe1255..a2a3077 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -111,6 +111,39 @@ def flag_sentence(label, channel, code):
   6 |             f"{STEP_A_SOFT.get(code) or EDGE_WORDS[code]}."
   7 |  
   8 |  
   9 | +COUNT_WORDS = {2: "Two", 3: "Three", 4: "Four", 5: "Five"}
  10 | +STEP_A_SOFT_MANY = {"NOT_OWN_SINCERE": "the checker doubted each is the speaker's own sincere view (they may be quoting "
  11 | +                                       "someone or joking)",
  12 | +                    "REFERENT_OUTSIDE": "the checker thought each points back to something said before the clip starts",
  13 | +                    "CONDITION_OUTSIDE": "the checker thought each claim depends on a condition said outside the clip",
  14 | +                    "UNCERTAIN": "the checker was not sure what each speaker means"}
  15 | +EDGE_WORDS_MANY = {"EDGE_IN": "the checker heard the sentence run on into each clip's first word, so each may start "
  16 | +                              "mid-sentence",
  17 | +                   "EDGE_OUT": "the checker heard the sentence carry on past each clip's last word, so each may end "
  18 | +                               "mid-sentence"}
  19 | +
  20 | +
  21 | +def kind_sentences(pairs, who):
  22 | +    """RULING 155 (1) (orchestrator 21:06 ET Nov 23: "THE CAP COUNTS KINDS OF FLAG, NOT CLIPS: the same soft code on
  23 | +    several clips is ONE flag in PBX's note, written once with the clips named"): [(label, code)] -> one sentence per
  24 | +    code, in first-seen order: one clip's flag_sentence, or for a code on several clips ONE sentence naming them all
  25 | +    ('Three clips (Strategy, Natalie Brunell, Yahoo Finance): the checker thought each points back ...')."""
  26 | +    by = {}
  27 | +    for lb, c in pairs:
  28 | +        if lb not in by.setdefault(c, []):
  29 | +            by[c].append(lb)
  30 | +    out = []
  31 | +    for c, lbs in by.items():
  32 | +        if len(lbs) == 1:
  33 | +            out.append(flag_sentence(lbs[0], (who or {}).get(lbs[0]), c))
  34 | +        else:
  35 | +            chans = ", ".join(str((who or {}).get(lb) or "its channel") for lb in lbs)
  36 | +            out.append(f"{COUNT_WORDS.get(len(lbs), str(len(lbs)))} clips ({chans}): "
  37 | +                       f"{STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY.get(c) or STEP_A_SOFT.get(c) or EDGE_WORDS.get(c) or c}.")
  38 | +            #   audit 20261123_2108 C1 (qwen P1): never a KeyError, even for a code no table words for several clips
  39 | +    return out
  40 | +
  41 | +
  42 |  def soft_edges(t):
  43 |      """RULING 137 stage 2a: a moment's CUTTABLE failure is soft only when its words match (law L-v 2 ok, measured, no
  44 |      error) and EVERY failing edge failed for the sentence running on at a word boundary (EDGE_SOFT); a word not found,
  45 | @@ -2299,8 +2332,9 @@ def seg_marks(segs):
  46 |      """RULING 141 (3): the flags a line-up's clips already carry from the never-empty pass's per-clip gates, one sentence
  47 |      each as the inventory writes them: step A's soft codes (context_a), a sentence edge (cuttable), STAND_ALONE
  48 |      (stand_alone), the hook under the calibrated bar (the medley row's hook sentence)."""
  49 | -    n = sum(len(set(m.get("step_a_flags") or [])) + len(m.get("edge_flags") or []) + bool(m.get("stand_soft"))
  50 | -            for m in segs or [])
  51 | +    segs = list(segs or [])                         # RULING 155 (1): KINDS, not clips: a code on several clips is one
  52 | +    n = len({c for m in segs for c in (m.get("step_a_flags") or [])}) + \
  53 | +        len({c for m in segs for c in (m.get("edge_flags") or [])}) + any(bool(m.get("stand_soft")) for m in segs)
  54 |      return n + bool((hook_own(segs[0]) or {}).get("flagged")) if segs else n
  55 |  
  56 |  
  57 | @@ -4668,8 +4702,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  58 |          (chain_sentences(chain, who) if chain else [])
  59 |      coh_fl = coherence_sentences(coh["soft"], chain, who) if soft and coh_ok and (coh or {}).get("soft") else []
  60 |      lab = lambda mid: (mids or {}).get(mid, mid)                      # truth is by moment id; flags name the clip
  61 | -    edge_fl = [flag_sentence(lab(mid), (who or {}).get(lab(mid)), c) for mid, t in (truth or {}).items()   # RULING
  62 | -               if soft and (t.get("edges") or {}).get("cuttable") is not True for c in (soft_edges(t) or [])]   # 137 2a
  63 | +    edge_fl = kind_sentences([(lab(mid), c) for mid, t in (truth or {}).items()   # RULING 137 2a; 155 (1): kinds
  64 | +                              if soft and (t.get("edges") or {}).get("cuttable") is not True
  65 | +                              for c in (soft_edges(t) or [])], who)
  66 |      a_rows = list((a_by or {}).values())
  67 |      lab_codes = {lb: sorted({str(c) for c in CI.a_failures(a)} | set((seg_flags or {}).get(lb) or []))   # RULING 137:
  68 |                   for lb, a in (a_by or {}).items()}       # each clip's step-A codes, its verdict's and every screen's soft
  69 | @@ -4692,8 +4727,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  70 |                                sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
  71 |                                n=len(a_rows)),
  72 |                            **({"status": "FLAGGED",            # RULING 137 stage 1; 138 (3): a sentence a clip
  73 | -                              "flags": [flag_sentence(lb, (who or {}).get(lb), c) for lb in (a_by or {})
  74 | -                                        for c in lab_codes[lb]]}
  75 | +                              "flags": kind_sentences([(lb, c) for lb in (a_by or {}) for c in lab_codes[lb]],
  76 | +                                                      who)}                  # RULING 155 (1): one sentence a kind
  77 |                               if soft_a and len(a_rows) >= 1 else {}),
  78 |                            **({"last_resort": last_resort} if last_resort else {})),   # RULING 102: the local judge
  79 |          "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
  80 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  81 | index bbbba23..dd8f4bd 100644
  82 | --- a/pipeline/package_pin.py
  83 | +++ b/pipeline/package_pin.py
  84 | @@ -428,7 +428,7 @@ def review_problems(mp):
  85 |      want, got = review_flags_of(mp.get("gates")), mp.get("review_flags") or []
  86 |      out = [] if got == want else [f"review_flags {got} are not the sealed gates' flags {want}"]
  87 |      n, cap = content_flags(mp.get("gates")), flags_cap(mp.get("gates"))
  88 | -    return out + ([f"{n} review flags, over {cap} (ruling 136 (2) / 147)"] if n > cap else [])
  89 | +    return out + ([f"{n} kinds of review flag, over {cap} (rulings 136 (2) / 147 / 155 (1))"] if n > cap else [])
  90 |  
  91 |  
  92 |  def flags_cap(gates):
  93 | @@ -437,10 +437,26 @@ def flags_cap(gates):
  94 |      return PBX_EXCEPTION_CAP if isinstance(gates, dict) and EXCEPTION_GATE in gates else REVIEW_FLAGS_MAX
  95 |  
  96 |  
  97 | +PER_CLIP_KIND = frozenset({"stand_alone", "sponsor", "graphics"})   # RULING 155 (1): one kind said once per clip
  98 | +_CLIP_REF = re.compile(r"^(?:The (?:opening|second|third|fourth|fifth) clip|A clip|The clip|[A-Z][a-z]+ clips) "
  99 | +                       r"\([^)]*\):?\s*")
 100 | +
 101 | +
 102 | +def flag_kind(gate, flag):
 103 | +    """RULING 155 (1): the KIND of one review flag: the row for a row that says one kind once per clip
 104 | +    (PER_CLIP_KIND: STAND_ALONE's per-clip sentences keep the prefix the integrator matches), else the row and the
 105 | +    sentence without the clip it names ('The second clip (Strategy): ...' and 'Three clips (...): ...' read alike)."""
 106 | +    return gate if gate in PER_CLIP_KIND else f"{gate}: {_CLIP_REF.sub('', flag).strip()}"
 107 | +
 108 | +
 109 |  def content_flags(gates):
 110 | -    """RULING 136 (2) / 144: the flags that count toward REVIEW_FLAGS_MAX: every review flag except an exception's."""
 111 | -    exc = ((gates or {}).get(EXCEPTION_GATE) or {}).get("flags") or [] if isinstance(gates, dict) else []
 112 | -    return len([f for f in review_flags_of(gates) if f not in exc])
 113 | +    """RULING 136 (2) / 144 / 155 (1) (orchestrator 21:06 ET Nov 23: "THE CAP COUNTS KINDS OF FLAG, NOT CLIPS ... At
 114 | +    most 3 KINDS per package, standing"): the KINDS of flag (flag_kind) on the FLAGGED rows that count toward the cap;
 115 | +    an exception's row never counts."""
 116 | +    if not isinstance(gates, dict):
 117 | +        return 0
 118 | +    return len({flag_kind(g, f) for g, row in gates.items() if g != EXCEPTION_GATE and isinstance(row, dict)
 119 | +                and row.get("status") == "FLAGGED" for f in row.get("flags") or [] if isinstance(f, str)})
 120 |  
 121 |  
 122 |  def gate_problems(gates, required=REQUIRED_GATES):
 123 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 124 | index fee382c..2c50916 100644
 125 | --- a/tests/package/test_ruling_137.py
 126 | +++ b/tests/package/test_ruling_137.py
 127 | @@ -208,6 +208,57 @@ class TestStage2a(unittest.TestCase):
 128 |                                                     "flags": ["a word differs"]}), "r")
 129 |  
 130 |  
 131 | +class TestRuling155FlagKinds(unittest.TestCase):
 132 | +    """RULING 155 (1) (orchestrator 21:06 ET Nov 23): "THE CAP COUNTS KINDS OF FLAG, NOT CLIPS: the same soft code on
 133 | +    several clips is ONE flag in PBX's note, written once with the clips named ... At most 3 KINDS per package,
 134 | +    standing." Build 159's MicroStrategy line-ups carried REFERENT_OUTSIDE on nearly every clip."""
 135 | +    WHO = {"hook": "Natalie Brunell", "clip_01": "Strategy", "clip_02": "Yahoo Finance"}
 136 | +    MERGED = ("Three clips (Natalie Brunell, Strategy, Yahoo Finance): the checker thought each points back to "
 137 | +              "something said before the clip starts.")
 138 | +    SINCERE3 = ("The third clip (Yahoo Finance): the checker doubted this is the speaker's own sincere view (they may "
 139 | +                "be quoting someone or joking).")
 140 | +
 141 | +    def inv(self, seg_flags):
 142 | +        b = TestTheStepARow().base()
 143 | +        b["a_by"] = {lb: answer() for lb in self.WHO}
 144 | +        return PK.inventory(**b, soft=True, seg_flags=seg_flags, who=self.WHO)
 145 | +
 146 | +    def test_one_code_on_several_clips_is_one_sentence_naming_them(self):
 147 | +        a = self.inv({"hook": ["REFERENT_OUTSIDE"], "clip_01": ["REFERENT_OUTSIDE"],
 148 | +                      "clip_02": ["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"]})["context_a"]
 149 | +        self.assertEqual((a["status"], a["flags"]), ("FLAGGED", [self.MERGED, self.SINCERE3]))
 150 | +        one = self.inv({"clip_01": ["REFERENT_OUTSIDE"]})["context_a"]
 151 | +        self.assertEqual(one["flags"], ["The second clip (Strategy): the checker thought it points back to something "
 152 | +                                        "said before the clip starts."])                  # one clip: as before
 153 | +
 154 | +    def gates(self):
 155 | +        stand = [PK.STAND_SOFT_PREFIX.format(channel=c) + f"it opens on '{w}'." for c, w in zip(self.WHO.values(),
 156 | +                                                                                                ("and", "so", "but"))]
 157 | +        return {"context_a": {"status": "FLAGGED", "flags": [self.MERGED, self.SINCERE3]},
 158 | +                "stand_alone": {"status": "FLAGGED", "flags": stand},       # one kind, said once per clip (prefix kept)
 159 | +                "medley": {"status": "FLAGGED", "flags": ["The opening clip (Natalie Brunell): the checker rated it "
 160 | +                                                          "under the hook bar (stopping the scroll 2 of 5, needs 3)."]}}
 161 | +
 162 | +    def test_the_cap_counts_kinds(self):
 163 | +        g = self.gates()
 164 | +        self.assertEqual(PP.content_flags(g), 4)                     # REFERENT_OUTSIDE, NOT_OWN_SINCERE, STAND_ALONE, hook
 165 | +        mp = {"gates": g, "review_flags": PP.review_flags_of(g)}
 166 | +        self.assertIn("4 kinds of review flag, over 3", " ".join(PP.review_problems(mp)))
 167 | +        g.pop("medley")
 168 | +        self.assertEqual(PP.content_flags(g), 3)
 169 | +        self.assertEqual(PP.review_problems({"gates": g, "review_flags": PP.review_flags_of(g)}), [])
 170 | +        per_clip = {"context_a": {"status": "FLAGGED", "flags": [   # the old per-clip sentences of one code: one kind
 171 | +            "The second clip (A): the checker thought it points back to something said before the clip starts.",
 172 | +            "The third clip (B): the checker thought it points back to something said before the clip starts."]}}
 173 | +        self.assertEqual(PP.content_flags(per_clip), 1)
 174 | +
 175 | +    def test_the_line_up_search_counts_kinds_too(self):
 176 | +        segs = [{"step_a_flags": ["REFERENT_OUTSIDE"]}, {"step_a_flags": ["REFERENT_OUTSIDE"], "stand_soft": True},
 177 | +                {"step_a_flags": ["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"], "stand_soft": True,
 178 | +                 "edge_flags": ["EDGE_OUT"]}, {"edge_flags": ["EDGE_OUT"]}]
 179 | +        self.assertEqual(PK.seg_marks(segs), 4)        # REFERENT_OUTSIDE, NOT_OWN_SINCERE, EDGE_OUT, STAND_ALONE
 180 | +
 181 | +
 182 |  class TestStage2bHookBar(unittest.TestCase):
 183 |      """RULING 137 STAGE 2b (1) (line 1, 13:20 ET): the calibrated hook bar is SOFT in the never-empty pass. A hook its
 184 |      own rater rated UNDER a floor opens, flagged in plain words (the best HOOK_SOFT_MAX of them); no calibration,
 185 | 
```

---

pp-selectid: RULING 155 (1) (orchestrator 21:06 ET Nov 23): "THE CAP COUNTS KINDS OF FLAG, NOT CLIPS: the same soft code
on several clips is ONE flag in PBX's note, written once with the clips named ('Three clips refer to something said
before them: Strategy, Natalie Brunell, Yahoo Finance'). At most 3 KINDS per package, standing."
THE CHANGE (pipeline/package.py, pipeline/package_pin.py, tests/package/test_ruling_137.py):
- package.kind_sentences: [(label, code)] -> one sentence per code: a single clip keeps the unchanged flag_sentence; a
  code on several clips is ONE sentence naming their channels ('Three clips (A, B, C): the checker thought each ...').
  inventory uses it for context_a (step A's soft codes) and cuttable (the sentence-edge codes EDGE_IN / EDGE_OUT).
- package.seg_marks (the line-up search's own count of the flags a line-up's clips carry, read against chain_cap, the
  unchanged package.py:2324): distinct step A codes + distinct edge codes + 1 if ANY clip is STAND_ALONE-soft + the hook.
- package_pin.content_flags (read by the unchanged review_problems, package_pin.py:425, the pin's cap check, which the
  integrator's check_pin_only calls LIVE from this file): the number of distinct KINDS (flag_kind) over the FLAGGED
  rows, the exception row excluded as before; flag_kind = the row for a row that says one kind once per clip
  (PER_CLIP_KIND: stand_alone, sponsor, graphics; STAND_ALONE's per-clip sentences keep the exact prefix the
  integrator's batch 107 matches, package.py:4796), else the row plus the sentence with the clip reference stripped.
  review_flags_of (package_pin.py:414, the note's list) is unchanged.
TESTS (TestRuling155FlagKinds): one code on three clips is one sentence naming them, one clip as before; the cap counts
kinds (4 kinds over 3 refuse; 3 pass; the old per-clip sentences of one code count once); the search counts kinds.
Mutations 5 of 5 killed.
PLEASE CHECK: (1) can a package now carry more than 3 KINDS of flag? (2) can two DIFFERENT kinds be counted as one
(a wrong merge, or flag_kind collapsing different doubts)? (3) does anything the integrator matches by exact text change
(STAND_ALONE's prefix, the review_flags list equal to the sealed gates' flags)? (4) is the merged sentence correct for
every soft code and edge code?


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
