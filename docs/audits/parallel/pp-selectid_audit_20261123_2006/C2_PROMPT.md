# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261123_2006
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 308 s finish=stop usage in 15064 / out 6411 usd_reported=0.002788 usd~0.141 (upper-bound price)

The code implements **RULING 143** (and its integration via Ruling 153) to allow the "builder's side" to re-verify transcript settlements derived from two audio readings.

### Analysis against Governing Laws & Requirements

1.  **Material Word Definition (L-v 2 / Ruling 143 (1))**:
    *   `attest.critical` is correctly updated to include **tickers** (defined as $\ge 2$ uppercase characters, regardless of position). This matches the render's `_lv2_critical` logic.
    *   `material_pair` correctly identifies a difference as material if it is not a word-form variation and contains at least one critical token.

2.  **Wrong Audio Detection (Ruling 143 (4))**:
    *   `audio_share` calculates the ratio of matched tokens from the run decode found in the second reading.
    *   `wrong_audio` correctly triggers a `HOLD` if the share is $< 85\%$ **and** more than 3 tokens are missing. This prevents accidental holds on very short clips while catching genuine audio mismatches.

3.  **Settlement Logic (Ruling 143 (2) & (3))**:
    *   **Material Pairs**: `class_143` only takes the run decode's reading if the second recognizer agrees (`run_ok`). Otherwise, it returns `took=None`, which `lock_precheck.decide` treats as a `HOLD`. This ensures material changes are only automated when audio evidence is redundant.
    *   **Non-Material Pairs**: These never hold. They prefer the approved text if the second recognizer agrees (`pin_ok`), otherwise they default to the run decode. This matches the "small word" rule.
    *   **No-Difference Pairs**: Currency and spelling pairs are correctly excluded from the settlement logic and the `mine` comparison list.

4.  **Verification & Security (L-c / L-j)**:
    *   **No Trust in Records**: `class_143` re-derives the settlement (`mine`) from the raw readings (`run_decode`, `approved`, `second_recogniser`) rather than trusting the `pairs` or `class` fields in the record.
    *   **Integrity Check**: The code compares the re-derived `mine` against the record's `theirs`. Any discrepancy (unless the specific fallback is met) results in a `HOLD`.
    *   **Spoken Text Lock**: The final `spoken` text is compared against the `merged` settled reading. If they differ, it fails closed.
    *   **Fallback**: The fallback logic correctly handles cases where the settled words cannot be written into the approved text (requiring all pairs to be 'run' and the spoken text to match the run decode).

5.  **Integration & Tests**:
    *   `lock_precheck.decide` correctly routes "ruling 143" adjudications to `class_143`.
    *   `lock_precheck.attested` provides the required legal "carried" text for the sealed record.
    *   `TestRuling143` covers the critical edge cases: the 'FDX' $\rightarrow$ 'FTX' correction, ticker/number materiality, small word non-holds, and various `HOLD` triggers (wrong audio, lying records, etc.).
    *   The `DECODER` hash update ensures that results from the previous (now invalid) decoder are ignored.

### Findings

No violations of the Governing Laws or the specific requirements of Ruling 143 were found. The implementation is fail-closed and strictly adheres to the provided logic.

P1_OR_WORSE: 0

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 45 s finish=stop usage in 12783 / out 6914 usd_reported=0.000877 usd~0.142 (upper-bound price)

**Findings**

| # | Severity | Issue | Description |
|---|----------|-------|-------------|
| 1 | **P0** | Undefined variable `why` in `lock_precheck.decide` | The function references `why` in the return dictionary for the “adopt” verdict, but `why` is never defined in that scope. This will raise a `NameError` and cause the gate to fail unexpectedly. |
| 2 | **P0** | Undefined variable `why` in `lock_precheck.decide` (duplicate) | The same undefined variable appears in the `return` statement for the adopt verdict, leading to a runtime error. |
| 3 | **P0** | Undefined variable `why` in `lock_precheck.decide` (duplicate) | The variable is referenced again in the same return statement, reinforcing the same bug. |
| 4 | **P0** | Undefined variable `why` in `lock_precheck.decide` (duplicate) | Repeated reference to the undefined variable. |
| 5 | **P0** | Undefined variable `why` in `lock_precheck.decide` (duplicate) | Repeated reference to the undefined variable. |
| 6 | **P0** | Undefined variable `why` in `lock_precheck.decide` (duplicate) | Repeated reference to the undefined variable. |
| 7 | **P0** | Undefined variable `why` in `lock_precheck.decide` (duplicate) | Repeated reference to the undefined variable. |
| 8 | **P0** | Undefined variable `why` in `lock_precheck.decide` (duplicate) | Repeated reference to the undefined variable. |
| 9 | **P0** | Undefined variable `why` in `lock_precheck.decide` (duplicate) | Repeated reference to the undefined variable. |
|10 | **P0** | Undefined variable `why` in `lock_precheck.decide` (duplicate) | Repeated reference to the undefined variable. |

> **P1_OR_WORSE:** 10

*(All 10 findings are the same underlying bug – the undefined `why` variable – but each line in the diff triggers a separate instance of the error.)*

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats: gemma-4-31b-it answered (0 P0/P1, no violation found; a short review). gpt-oss-20b at effort medium spent its
32,000 tokens reasoning (EMPTY); re-asked at effort low it answered. mimo-v2.6-flash-rl, added as a third family on
the retry, spent its 32,000 tokens reasoning (EMPTY). qwen's ruling-99 breaker is open. Seats answered: 2.
- gpt-oss (low) P0 x10, one finding repeated: "undefined variable `why` in lock_precheck.decide (the adopt return)".
  DISPROVED in the code: decide() binds it on its first line after the None check, unchanged by this diff:
  `out, why = e.get("outcome"), str(e.get("reason") or "")[:400]` (lock_precheck.py, decide); the reviewer saw only the
  hunk. Executed: TestRuling143.test_the_two_audio_readings_correct_the_transcript_and_the_pin_says_so returns the
  adopt verdict through that very return (no NameError), and mutation T7 (the 143 branch removed) fails 4 tests.
- No other finding. Nothing to fix; cycle 2 cross-examines the same diff.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261123_2006/C2_STEP.diff (332 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index cca269f..4ff7387 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -59,8 +59,10 @@ FILLERS = frozenset(("um", "uh", "er", "ah", "mm", "hmm"))
   6 |  
   7 |  
   8 |  def critical(tok, texts):
   9 | -    """Law L-v 2 as the render tests it (pinned._lv2_critical): a number, a negation, or a name (in either text, a
  10 | -    capitalised word that does not open a sentence; 'I' excepted). A doubtful token is critical."""
  11 | +    """Law L-v 2 / ruling 143 (1)'s MATERIAL word as the render tests it (pinned._lv2_critical): a number, a negation,
  12 | +    a name (in either text, a capitalised word that does not open a sentence; 'I' excepted) or a ticker (in either
  13 | +    text, a word of two or more capitals, wherever it stands: 'IBIT'; the integrator's batch 113). A doubtful token is
  14 | +    critical."""
  15 |      if re.search(r"\d", tok) or tok in LV2_NEGATIONS or tok.endswith("n't") or tok in LV2_ORDINALS:
  16 |          return True
  17 |      for t in texts:
  18 | @@ -68,7 +70,7 @@ def critical(tok, texts):
  19 |              w = m.group(0)
  20 |              if w.lower() == tok and w[0].isupper() and w != "I":
  21 |                  before = t[:m.start()].rstrip()
  22 | -                if before and before[-1] not in ".!?":
  23 | +                if (before and before[-1] not in ".!?") or (len(w) >= 2 and w.isupper()):
  24 |                      return True
  25 |      return False
  26 |  
  27 | @@ -279,6 +281,111 @@ def class_131(spoken, approved, adj):
  28 |      return out
  29 |  
  30 |  
  31 | +RULE_143 = "ruling 143"
  32 | +AUDIO_SHARE_MIN = 0.85     # RULING 143 (4), pinned.AUDIO_SHARE_MIN: two audio readings sharing less are the wrong audio
  33 | +AUDIO_APART_MIN = 3        # ... and only when more than this many of the run decode's words are missing (pinned's)
  34 | +
  35 | +
  36 | +def audio_share(x, y):
  37 | +    """RULING 143 (4) as pinned.audio_share: the share of the run decode's tokens x the second reading y heard, in
  38 | +    order (matched / len(x)); y's extra words (repeats, false starts, the window's spill) never lower it."""
  39 | +    x, y = list(x or []), list(y or [])
  40 | +    if not x or not y:
  41 | +        return 0.0
  42 | +    return sum(m.size for m in SequenceMatcher(None, x, y, autojunk=False).get_matching_blocks()) / len(x)
  43 | +
  44 | +
  45 | +def wrong_audio(x, y):
  46 | +    """RULING 143 (4) as pinned.wrong_audio: the share when under AUDIO_SHARE_MIN AND more than AUDIO_APART_MIN of the
  47 | +    run decode's tokens are missing (HARD), else None (the same audio)."""
  48 | +    share = audio_share(x, y)
  49 | +    apart = len(list(x or [])) - round(share * len(list(x or [])))
  50 | +    return share if share < AUDIO_SHARE_MIN and apart > AUDIO_APART_MIN else None
  51 | +
  52 | +
  53 | +def material_pair(x, y, texts):
  54 | +    """RULING 143 (1) as pinned.material_pair: a differing pair is MATERIAL when either side holds a number, a negation,
  55 | +    a name, a ticker or an amount (critical); a word-form pair (ruling 142 (2)) is not."""
  56 | +    return not canon.word_form(x, y) and any(critical(t, texts) for t in list(x) + list(y))
  57 | +
  58 | +
  59 | +def class_143(spoken, approved, adj):
  60 | +    """RULING 143 (orchestrator 2026-11-17 '15:55'; landed by ruling 153, 20:03 ET Nov 23): this side's own re-check of
  61 | +    the render lock's settlement, from its record (the pre-check entry's "adjudication": "run_decode", "approved",
  62 | +    "second_recogniser", "pairs"), never from the record's own classes. Each step is pinned.adjudicate_lock's, re-run on
  63 | +    the recorded readings:
  64 | +    1. The ruling-17 diff (canon tokens of the run decode against the approved text); a currency pair (ruling 131 (B))
  65 | +       and a spelling-only pair (ruling 135) are no difference.
  66 | +    2. HARD (4): the run decode and the second recogniser (its fillers dropped, ruling 135 (d)) sharing under
  67 | +       AUDIO_SHARE_MIN of the run's words, more than AUDIO_APART_MIN apart: the wrong audio.
  68 | +    3. Per pair (reads: the render's test of the second reading there): a MATERIAL pair (material_pair) takes the run
  69 | +       decode's reading only when the second recogniser reads it too (the two audio readings agree: the transcript is
  70 | +       corrected), else it holds; a NON-MATERIAL pair never holds: the approved reading where the second recogniser
  71 | +       reads it, else the run decode's.
  72 | +    4. The record's pairs must be exactly these, in order (the same words, materiality and reading taken); the render's
  73 | +       fallback (the settled words cannot be written into the approved text: the run decode's text, every pair
  74 | +       'run') is accepted only with every pair settled and the spoken text the run decode's.
  75 | +    5. The spoken text's canon tokens are the settled reading (the approved tokens, each run-taken pair as the run's).
  76 | +    -> [{"spoken", "approved", "material", "class", "took", "edge_distance"} (+ "why" when it holds)]; a class None
  77 | +    holds."""
  78 | +    def held(why, **kw):
  79 | +        return dict({"spoken": "", "approved": "", "took": None, "edge_distance": None, "material": None}, **kw,
  80 | +                    **{"class": None}, why=why)
  81 | +    adj = adj if isinstance(adj, dict) else {}
  82 | +    run_t, pin_t, sec_t = adj.get("run_decode"), adj.get("approved"), adj.get("second_recogniser")
  83 | +    if not all(isinstance(t, str) for t in (run_t, pin_t, sec_t, spoken, approved)) or \
  84 | +            canon.canon_tokens(pin_t) != canon.canon_tokens(approved):
  85 | +        return [held("the lock record does not hold the three readings of this segment's approved text")]
  86 | +    texts = (run_t, pin_t, sec_t)
  87 | +    r, p, ops = diff(run_t, pin_t)
  88 | +    s = [x for x in canon.canon_tokens(sec_t) if not canon.nonlexical(x)]
  89 | +    share = wrong_audio(r, s)
  90 | +    if share is not None:
  91 | +        return [held(f"the run decode and the second recogniser share {share:.0%} of their words: the wrong audio "
  92 | +                     f"(ruling 143 (4))")]
  93 | +    out, took_run = [], set()
  94 | +    for op in ops:
  95 | +        _tag, a, b, c, d = op
  96 | +        row = {"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "edge_distance": None}
  97 | +        if currency_pair(r, p, op):
  98 | +            out.append(dict(row, took="currency", material=None, **{"class": "currency format (ruling 131 (B))"}))
  99 | +            continue
 100 | +        if canon.same_words(r[a:b], p[c:d]):
 101 | +            out.append(dict(row, took="spelling", material=None, **{"class": "spelling only (ruling 135)"}))
 102 | +            continue
 103 | +        material = material_pair(r[a:b], p[c:d], texts)
 104 | +        pin_ok, run_ok = reads(p, s, c, d), reads(r, s, a, b)
 105 | +        if material and run_ok:
 106 | +            out.append(dict(row, took="run", material=True, **{"class": "ruling 143 (3): the two audio readings "
 107 | +                                                                         "agree: the transcript corrected"}))
 108 | +        elif material:
 109 | +            out.append(dict(row, took=None, material=True, **{"class": None},
 110 | +                            why="a material word (a number, a negation, a name, a ticker or an amount) on which the "
 111 | +                                "two audio readings disagree (ruling 143 (3))"))
 112 | +        else:
 113 | +            out.append(dict(row, took="approved" if pin_ok else "run", material=False, **{"class": (
 114 | +                "ruling 143 (2): a small word, the approved reading the second recogniser reads" if pin_ok else
 115 | +                "ruling 143 (2): a small word, never a hold: the run decode's reading")}))
 116 | +        if out[-1]["took"] == "run":
 117 | +            took_run.add((a, c))
 118 | +    merged = []
 119 | +    for tag, a, b, c, d in SequenceMatcher(None, r, p, autojunk=False).get_opcodes():
 120 | +        merged += r[a:b] if (tag != "equal" and (a, c) in took_run) else p[c:d]
 121 | +    rec = adj.get("pairs")
 122 | +    theirs = [(x.get("run"), x.get("approved"), x.get("material"), x.get("took")) for x in rec] \
 123 | +        if isinstance(rec, list) and all(isinstance(x, dict) for x in rec) else None
 124 | +    mine = [(x["spoken"], x["approved"], x["material"], x["took"]) for x in out if x["took"] not in ("currency",
 125 | +                                                                                                    "spelling")]
 126 | +    sp = canon.canon_tokens(spoken)
 127 | +    fallback = (theirs is not None and len(theirs) == len(mine) and all(t[3] == "run" for t in theirs) and
 128 | +                [t[:3] for t in theirs] == [m[:3] for m in mine] and all(m[3] is not None for m in mine) and sp == r)
 129 | +    if theirs != mine and not fallback:
 130 | +        out.append(held(f"the lock record's pairs are not this side's: {theirs} against {mine}"[:400]))
 131 | +    if sp != merged and not fallback:
 132 | +        out.append(held("the spoken text is not the settled reading (ruling 143 seals the settled reading only)"))
 133 | +    return out
 134 | +
 135 | +
 136 |  def reads(x, s, lo, hi):
 137 |      """The second recogniser's tokens s read x's tokens lo..hi-1 AT this position (pinned.adjudicate_lock's reads):
 138 |      they and one neighbour on each side are aligned and consecutive in s; at x's start / end nothing may precede /
 139 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
 140 | index aae6ba7..f18e406 100644
 141 | --- a/pipeline/lock_precheck.py
 142 | +++ b/pipeline/lock_precheck.py
 143 | @@ -50,7 +50,9 @@ import attest as AT
 144 |  import canon as C
 145 |  
 146 |  RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135 + "
 147 | -         "ruling 142 + ruling 146")             # RULING 146 (2): G17a's hook lead flags in the render's lock (batch 114)                         # RULING 142 (orchestrator 14:32 ET Nov 17): '24 -7' is no sign; a
 148 | +         "ruling 139 + ruling 142 + ruling 143 + ruling 146")   # RULING 153 (20:03 ET Nov 23): rulings 139 and 143
 149 | +#   join the integrator's string (its lockstep message of 20:1x ET Nov 23, branch r143-material 36896978e)
 150 | +             # RULING 146 (2): G17a's hook lead flags in the render's lock (batch 114)                         # RULING 142 (orchestrator 14:32 ET Nov 17): '24 -7' is no sign; a
 151 |  #   possessive or plural ending is a word-form pair for 131 (A) (the integrator's batch 110 values, 14:5x ET). RULING 135
 152 |  #   (orchestrator 10:50 ET Nov 17): the comparison canon (canon.same_words), the integrator's message of 10:5x Nov 17.
 153 |  #   RULING 131
 154 | @@ -61,7 +63,7 @@ RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 10
 155 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
 156 |  #   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
 157 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
 158 | -DECODER = "50fa01b400bd"                      # side): the render's own cut placement joins the pre-check (a passing
 159 | +DECODER = "9326604699a7"                      # side): the render's own cut placement joins the pre-check (a passing
 160 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
 161 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
 162 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
 163 | @@ -83,6 +85,10 @@ DECODER = "50fa01b400bd"                      # side): the render's own cut plac
 164 |  #   lockstep): fc204e4a4385a1906ef858923936cd6d6ed3a65ea78f2007281e2d4945038e09
 165 |  #   RULING 146 (2), the integrator's batch 114 (sentence_law.lock_cut: a hook lead under 80 ms FLAGS, never holds;
 166 |  #   branch r146-g17a 90aa0486; sentence_law.py byte-identical): 50fa01b400bd4231e38a9a8b77f6a0df6f16a57d6f0e22de0eb376788f039256
 167 | +#   RULING 153 (orchestrator 20:03 ET Nov 23): the integrator's batches 113 (ruling 143, the material-words lock), 116
 168 | +#   (ruling 139 on the render lock), the ruling-145 allowance (gpu0.py) and 119 (post_live; no decoder file), ONE
 169 | +#   lockstep (branch r143-material 36896978e; pinned.py, sentence_law.py and gpu0.py byte-identical):
 170 | +#   9326604699a7756c18d887cd09bdb280f74d9c732bfb0e1235e4a9f3095850c9
 171 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
 172 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
 173 |                          "lock_requests")      # this worktree's; the service only reads it
 174 | @@ -185,6 +191,20 @@ def decide(seg, e):
 175 |      if not isinstance(spoken, str) or not spoken.strip():
 176 |          return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
 177 |      adj = e.get("adjudication")
 178 | +    if isinstance(adj, dict) and str(adj.get("rule") or "").startswith(AT.RULE_143):   # RULING 143: the settlement
 179 | +        diffs = AT.class_143(spoken, approved, adj)
 180 | +        bad = [x for x in diffs if x["class"] is None]
 181 | +        if bad:                                       # this side's re-check of the lock's record disagrees: fail closed
 182 | +            return {"verdict": "hold", "outcome": out, "differences": diffs,
 183 | +                    "why": "adopt_spoken under ruling 143, but by this side's attest.class_143 it holds: " +
 184 | +                           str([[x["spoken"], x["approved"], x["why"]] for x in bad])[:300]}
 185 | +        if not any(x["took"] == "run" for x in diffs):  # no pair took the run decode's reading: the approved text stands
 186 | +            return {"verdict": "pass", "outcome": out, "why": "adopt_spoken under ruling 143 with no pair taking the "
 187 | +                                                              "run decode's reading: the approved text stands"}
 188 | +        return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs,
 189 | +                "adoption": AT.RULE_143,
 190 | +                "transcript_corrected": [[x["approved"], x["spoken"]] for x in diffs if x.get("material") and
 191 | +                                         x["took"] == "run"]}
 192 |      if isinstance(adj, dict) and str(adj.get("rule") or "").startswith(AT.RULE_131):   # RULING 131 (A): two of three
 193 |          diffs = AT.class_131(spoken, approved, adj)
 194 |          bad = [x for x in diffs if x["class"] is None]
 195 | @@ -304,7 +324,16 @@ def relisten_of(e):
 196 |  def attested(row, run_rule=None):
 197 |      """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it:
 198 |      ruling 84's class, or ruling 131 (A)'s two of three readings (row["adoption"])."""
 199 | -    if row.get("adoption") == AT.RULE_131:
 200 | +    if row.get("adoption") == AT.RULE_143:
 201 | +        rule = run_rule or ("ruling 143 (orchestrator 2026-11-17 '15:55', landed by ruling 153): adopt_spoken, the "
 202 | +                            "render lock's settlement")
 203 | +        carried = ("every verdict and gate of this line-up, judged on the text it replaces: each changed material word "
 204 | +                   "(a number, a negation, a name, a ticker or an amount) is the reading the two audio readings agree "
 205 | +                   "on (the run decode and the second recogniser; the transcript corrected from the audio), each small "
 206 | +                   "word the approved reading the second recogniser reads or the run decode's, re-checked on this side "
 207 | +                   "from the lock's record; no line quotes the changed words (marked on the release: 'transcript "
 208 | +                   "corrected from the audio' where a material word changed)")
 209 | +    elif row.get("adoption") == AT.RULE_131:
 210 |          rule = run_rule or "ruling 72 + ruling 131 (A) (08:25 ET Nov 17): adopt_spoken, two of the three readings agree"
 211 |          carried = ("every verdict and gate of this line-up, judged on the text it replaces: each changed pair is the "
 212 |                     "reading two of the three readings (the approved text, the render's run decode, the second "
 213 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 214 | index a70ed0c..8a5f929 100644
 215 | --- a/tests/package/test_lock_precheck.py
 216 | +++ b/tests/package/test_lock_precheck.py
 217 | @@ -60,7 +60,7 @@ class TestRequest(Dirs):
 218 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 219 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 220 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 221 | -                         "DcUbBkyeh9M.216.054-228.674.50fa01b400bd.json")             # batch 114's decoder
 222 | +                         "DcUbBkyeh9M.216.054-228.674.9326604699a7.json")             # ruling 153's lockstep
 223 |  
 224 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 225 |          segs = LP.segments_of([HOOK, CLIP])
 226 | @@ -138,7 +138,7 @@ class TestRuling84(unittest.TestCase):
 227 |          """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14), RULING 131 (08:25 Nov 17), RULING 135 (10:50 Nov 17) and
 228 |          RULING 142 (14:32 Nov 17) joined the integrator's rules string (its batch 110 values, 14:5x ET Nov 17)."""
 229 |          self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
 230 | -                                   "ruling 131 + ruling 135 + ruling 142 + ruling 146")
 231 | +                                   "ruling 131 + ruling 135 + ruling 139 + ruling 142 + ruling 143 + ruling 146")
 232 |  
 233 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 234 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 235 | @@ -627,3 +627,96 @@ class TestApply(Dirs):
 236 |  
 237 |  if __name__ == "__main__":
 238 |      unittest.main()
 239 | +
 240 | +
 241 | +class TestRuling143(Dirs):
 242 | +    """RULING 143 (orchestrator 2026-11-17 '15:55'), landed by RULING 153 (20:03 ET Nov 23) in ONE lockstep with the
 243 | +    integrator's batch 113: when the TWO AUDIO readings (the run decode and the second recogniser) agree with each other
 244 | +    on a material word, the sealed text takes the audio's reading (the transcript is corrected); only when they disagree
 245 | +    does it hold; a small word never holds; the wrong audio (under 85 % shared) holds. This side re-derives every pair
 246 | +    (attest.class_143) and never trusts the record. The case: the FTX-bottom story's Simply Bitcoin 190beaa7
 247 | +    (0shaXx_n870 words 0-30), held at 19:54 on 'fdx' / 'ftx' (the transcript's 'FDX', both audio readings 'FTX')."""
 248 | +    APPROVED = ("On Saturday at 1 in the morning, Bitcoin got flushed down to $55,000. That was four years to the day "
 249 | +                "after the FDX bottom.")
 250 | +    RUN = APPROVED.replace("FDX", "FTX")
 251 | +    SB = {"moment_id": "190beaa7", "video_id": "0shaXx_n870", "start": 0.0, "end": 9.76, "text": APPROVED}
 252 | +
 253 | +    def adj(self, run=None, app=None, sec=None, **kw):
 254 | +        run, app = run or self.RUN, app or self.APPROVED
 255 | +        sec = run if sec is None else sec
 256 | +        r, p, ops = AT.diff(run, app)
 257 | +        pairs = [{"run": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "material": True, "second_reads": "run",
 258 | +                  "took": "run"} for _, a, b, c, d in ops]
 259 | +        return dict({"rule": "ruling 143 (orchestrator 2026-11-17 '15:55')", "verdict": "settled", "pairs": pairs,
 260 | +                     "run_decode": run, "approved": app, "second_recogniser": sec}, **kw)
 261 | +
 262 | +    def decide(self, spoken=None, seg=None, **kw):
 263 | +        s = LP.segments_of([seg or self.SB])[0]
 264 | +        return LP.decide(s, entry(s, "adopt_spoken", spoken_text=spoken or self.RUN, adjudication=self.adj(**kw)))
 265 | +
 266 | +    def test_the_two_audio_readings_correct_the_transcript_and_the_pin_says_so(self):
 267 | +        d = self.decide()
 268 | +        self.assertEqual(d["verdict"], "adopt", d.get("why"))
 269 | +        self.assertEqual(d["transcript_corrected"], [["fdx", "ftx"]])
 270 | +        s = LP.segments_of([self.SB])[0]
 271 | +        self.put(s, entry(s, "adopt_spoken", spoken_text=self.RUN, adjudication=self.adj()))
 272 | +        pre = LP.check([self.SB], "r", self.req, self.res, log=lambda m: None)
 273 | +        pk = LP.apply({"segments": [{k: self.SB[k] for k in ("video_id", "start", "end", "text")}], "lines": []}, pre)
 274 | +        seg = pk["segments"][0]
 275 | +        self.assertEqual((seg["text"], seg["attested"]["was"]), (self.RUN, self.APPROVED))
 276 | +        self.assertIn("ruling 143", seg["attested"]["rule"])
 277 | +        self.assertIn("transcript corrected from the audio", seg["attested"]["carried"])
 278 | +        self.assertEqual(LP.pin_problems(pk), [])
 279 | +
 280 | +    def test_a_number_and_a_ticker_are_settled_the_same_way(self):
 281 | +        for app, run in (("Bitcoin bottomed at about 15,000,500 dollars on November 21st of 2022, a deep low.",
 282 | +                          "Bitcoin bottomed at about 15,500 dollars on November 21st of 2022, a deep low."),
 283 | +                         ("IBIT saw its largest outflow since the launch in January of last year, the data shows.",
 284 | +                          "IBTC saw its largest outflow since the launch in January of last year, the data shows.")):
 285 | +            #   a sentence-opening ticker: only the ticker rule makes it material (the integrator's batch 113)
 286 | +            d = self.decide(spoken=run, seg=dict(self.SB, text=app), run=run, app=app)
 287 | +            self.assertEqual(d["verdict"], "adopt", (app, d.get("why")))
 288 | +            self.assertTrue(d["transcript_corrected"], app)
 289 | +            self.assertTrue(all(x["material"] for x in d["differences"]), app)
 290 | +
 291 | +    def test_a_small_word_never_holds(self):
 292 | +        app = "That was four years to the day after the bottom, and nobody saw it coming at all this time."
 293 | +        run, sec = app.replace(", and nobody", ", but nobody"), app.replace(", and nobody", ", so nobody")
 294 | +        r, p, ops = AT.diff(run, app)
 295 | +        pairs = [{"run": "but", "approved": "and", "material": False, "second_reads": "neither", "took": "run"}]
 296 | +        d = self.decide(spoken=run, seg=dict(self.SB, text=app), run=run, app=app, sec=sec, pairs=pairs)
 297 | +        self.assertEqual((d["verdict"], [(x["took"], x["material"]) for x in d["differences"]]),
 298 | +                         ("adopt", [("run", False)]), d.get("why"))
 299 | +        d = self.decide(spoken=app, seg=dict(self.SB, text=app), run=run, app=app, sec=app,
 300 | +                        pairs=[dict(pairs[0], second_reads="approved", took="approved")])
 301 | +        self.assertEqual(d["verdict"], "pass", d.get("why"))              # the second reads 'and': the approved stands
 302 | +
 303 | +    def test_what_holds(self):
 304 | +        other = ("Gold and the stock market both rallied on Friday while the dollar slid against the yen and the "
 305 | +                 "euro after the jobs report.")
 306 | +        for spoken, kw, why in (
 307 | +                (None, {"sec": APPROVED_SB_FDX}, "the two audio readings disagree"),          # the second reads 'FDX'
 308 | +                (None, {"sec": other}, "the wrong audio (ruling 143 (4))"),
 309 | +                (None, {"pairs": [{"run": "ftx", "approved": "fdx", "material": True, "took": "approved"}]},
 310 | +                 "the lock record's pairs are not this side's"),
 311 | +                (None, {"pairs": []}, "the lock record's pairs are not this side's"),
 312 | +                (APPROVED_SB_FDX.replace("four years", "five years"), {}, "the spoken text is not the settled reading"),
 313 | +                (None, {"second_recogniser": None}, "does not hold the three readings")):
 314 | +            d = self.decide(spoken, **kw)
 315 | +            self.assertEqual(d["verdict"], "hold", (spoken, kw))
 316 | +            self.assertIn(why, d["why"])
 317 | +
 318 | +    def test_only_a_ruling_143_record_goes_to_class_143(self):
 319 | +        d = self.decide(rule="ruling 131 (A) (orchestrator 2026-11-17 '08:25')")     # a 131 record: class_131 decides
 320 | +        self.assertNotEqual(d.get("adoption"), AT.RULE_143)
 321 | +
 322 | +    def test_the_old_decoders_answers_are_never_read(self):
 323 | +        s = LP.segments_of([self.SB])[0]
 324 | +        name = os.path.basename(LP.result_file(s, self.res)).replace(LP.DECODER, "50fa01b400bd")
 325 | +        with open(os.path.join(self.res, name), "w") as f:
 326 | +            json.dump([entry(s, "no_difference")], f)
 327 | +        self.assertIsNone(LP.answer(s, self.res))                       # batch 114's decoder: never read again
 328 | +
 329 | +
 330 | +APPROVED_SB_FDX = TestRuling143.APPROVED
 331 | +
 332 | 
```

---

pp-selectid: RULING 143's MIRROR on the builder's side (orchestrator ruling 153, 20:03 ET Nov 23: "RULING 143 LANDS
NOW ... when the TWO AUDIO READINGS agree with each other, the sealed text takes the audio's reading and the
transcript is corrected; only when the two audio readings DISAGREE on a material word does it hold"), in ONE decoder
lockstep with the integrator's batch 113 (pinned.adjudicate_lock under ruling 143: branch r143-material 36896978e).
pinned.py, sentence_law.py and gpu0.py are copied byte-identical (not part of this review).
THE CHANGE (pipeline/attest.py, pipeline/lock_precheck.py, tests/package/test_lock_precheck.py):
- attest.critical (attest.py:61): the render's _lv2_critical now also takes a TICKER (a word of two or more capitals,
  wherever it stands, a sentence opener included).
- attest.audio_share / wrong_audio / material_pair (attest.py:~290-310): pinned's, re-implemented: share = matched run
  tokens / len(run); wrong audio = share < 0.85 AND more than 3 run tokens missing; material = not canon.word_form and
  any critical token.
- attest.class_143 (attest.py:312): this side's re-check of a settlement from the lock record (run_decode, approved,
  second_recogniser, pairs), never from the record's classes: the ruling-17 diff (unchanged attest.diff, :78); currency
  (unchanged currency_pair, :155) and spelling pairs are no difference; the wrong audio holds; per pair (unchanged
  attest.reads, :389, pinned's test): material -> the run's reading only when the second recogniser reads it, else
  HOLD; small -> the approved reading when the second reads it, else the run's (never a hold); the record's pairs
  must equal this side's (words, materiality, reading taken), or the render's fallback (every pair 'run', the spoken
  text the run decode's); the spoken text must be the settled reading.
- lock_precheck.decide (lock_precheck.py:172, branch :194): an adopt_spoken whose adjudication rule starts
  "ruling 143" goes to class_143: any class None holds; no run-taken pair = pass (the approved text stands); else
  adopt with transcript_corrected = the material pairs taken from the audio. attested (:324): the sealed record's rule
  and carried text for a 143 adoption. RULES gains rulings 139 and 143; DECODER 9326604699a7 (the integrator's).
TESTS (TestRuling143): the FTX-bottom case ('FDX' in the transcript, both audio readings 'FTX') adopts, is sealed by
apply with its attested record, pin_problems none; a number format and a sentence-opening ticker settle the same
way; a small word never holds; holds: the second reads 'FDX', the wrong audio, a record that lies, an empty record,
a spoken text that is not the settled reading, a record without the readings; a 131 record is not class_143's; an
answer under the old decoder is never read. Mutations 9 of 9 killed.
PLEASE CHECK: (1) can a material word the two AUDIO readings disagree on reach a sealed text? (2) can a record that
lies (pairs, readings, spoken text) pass? (3) does class_143 match pinned.adjudicate_lock's ruling 143 (incl. the
fallback when the settled words cannot be written into the approved text)? (4) is the ticker rule the render's?


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
