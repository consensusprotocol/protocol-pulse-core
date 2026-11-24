# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261123_2143
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 290 s finish=stop usage in 11187 / out 8700 usd_reported=0.001976 usd~0.164 (upper-bound price)

# Code Audit — pp-selectid (RULING 156 fallback lines)

**Scope reviewed:** C1_STEP.diff (package.py, package_pin.py, test_medley.py, test_ruling_137.py) against the governing laws (LAW 20/M2, M12, L-k, L-l, ruling 66/91/146/150/155/156).

---

## Findings

### [P1] F1 — `fallback_fields` crashes when `segs` has exactly one segment (IndexError), and when `chans` is empty the closing line reads "in the words of " (grammar/None)

`fallback_fields` builds `names`:
```python
names = chans[0] if len(chans) == 1 else ", ".join(chans[:-1]) + " and " + chans[-1]
```
- **len(chans) == 0** (every segment lacks both `channel_name` and `channel_id`): `", ".join([]) + " and " + []` → `"" + " and " + IndexError` — actually `chans[-1]` raises **IndexError** on an empty list. M12 FAIL CLOSED would catch the exception, but the ruling says the fallback must be *the* never-empty pass; an exception here converts "never empty" into "no video", defeating the ruling's stated purpose ("Our writing must never be the reason PBX gets no video"). The never-empty pass exists precisely when the model writes keep failing; a crash there is the worst place to fail.
- **len(chans) == 1** is handled; **len == 2** gives `"A and B"` — fine. But note the test only exercises 3 channels; the 2-channel case yields `"A and B"` (correct), 0-channel case is untested and broken.

Also: if a segment's `channel_name`/`channel_id` is `None`/`""` for *some* segments, `chans` silently drops them, so `names` under-reports the line-up — the closing line then names fewer channels than the clips used. Compare L-a's spirit (names all) — not a law violation here (L-a is the sign-off), but the flag sentence and closing line would misname the line-up. **Severity: P1** (empty-list crash) with the under-reporting as part of the same finding.

**Fix:** `names = chans[0] if len(chans) == 1 else (", ".join(chans[:-1]) + " and " + chans[-1] if chans else "our channels")` — or fail closed *deliberately* and document it; but then the never-empty pass must have a second, code-only last resort.

### [P1] F2 — `fallback_subject`'s "first never opening a sentence" rule is implemented as "not preceded by sentence punctuation", which also excludes every sentence-*initial* occurrence, and the tie-break `first[w]` can KeyError

```python
if not before or before[-1] in ".!?" or any(...):
    continue
```
The ruling text in `fallback_subject`'s docstring says: "its first never opening a sentence". The code skips a run when `before` is empty **or** ends in `.!?"` — i.e. it requires the run to be *mid-sentence*. But in the test, "Analysts say Michael Saylor will keep buying Bitcoin." — "Michael Saylor" is mid-sentence, fine. However consider a clip whose *first* words are the subject: "Michael Saylor said we buy more Bitcoin." — the run at position 0 has `before == ""` → skipped. That's the intended rule ("its first never opening a sentence"), so this is per-spec. **But** the tie-break:

```python
best = sorted((w for w, n in count.items() said if n >= ties), key=lambda w: (count[w], first[w]))
```
`first` is populated via `first.setdefault(run, (i, mm.start()))` **inside the same loop where `count` is incremented** — but only for runs that pass the filter. Since `count[w] >= 2` implies the run passed the filter at least twice, `first[w]` always exists. OK — no KeyError. However, there's a subtler defect: `names` (the per-segment set) is populated, then `for w in names: count[w] += 1` — counting **distinct runs per clip**, not occurrences. That matches "the most of the line-up's clips say" — correct. But the *skip* set:

```python
skip = {"i", "bitcoin"} | {w.lower() for c in chans for channel words}
```
`re.findall(r"[A-Za-z]+", str(c))` on a channel like "S&P" yields `["S", "P"]` → skip = {"s","p"} — a clip saying "S&P 500" has runs "S&P"→ wait, the regex `[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*` on "S&P 500" matches "S" then "P" separately (the `&` breaks the run). "S" as a run: `before` check, `w.lower() in skip` → "s" in skip → skipped. Fine. But a channel named "Bitcoin Magazine" puts "bitcoin" and "magazine" in skip; a clip saying "Bitcoin Magazine" — the run "Bitcoin Magazine" contains "bitcoin" → skipped entirely, so "Magazine" can never be the subject even if 3 clips say it. That's per the ruling ("no channel's word ... in it"). OK.

The real defect: **`first.setdefault(run, (i, mm.finditer position))` is set even when the run is later filtered by `n >= 2`** — no, that's fine, it's just a tie-break. The actual P1: **the regex `[A-Z][A-Za-z]*` requires the run to start with a capital; a subject like "iPhone" or "ETF" mid-sentence works, but "ETF" — all caps — matches `[A-Z][A-Za-z]*` as "ETF"?** `[A-Z][A-Za-z]*` on "ETF" matches "ETF" (E, then TF). Yes. OK.

**Downgrade F2 to P2:** the logic is convoluted but matches the ruling; the only genuine 

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 34 s finish=stop usage in 11204 / out 5373 usd_reported=0.000707 usd~0.114 (upper-bound price)

**Findings**

| # | Severity | Issue | Explanation |
|---|----------|-------|-------------|
| 1 | P3 | `fallback_subject` skip set includes channel words | The skip set is built from all channel names (`{w.lower() for c in chans for w in re.findall(r"[A-Za-z]+", str(c))}`) plus `"i"` and `"bitcoin"`. If a channel name contains the word “Bitcoin” or “i”, that word will be skipped when searching for the subject. While unlikely, it could cause the subject to be incorrectly inferred as “Bitcoin” when the intended subject is a proper name that includes “Bitcoin”. |
| 2 | P3 | `fallback_fields` uses `budget is not None` check inside the generator expression | The generator expression `next((t for t in (f.format(subject=subject, names=names) for f in FALLBACK_CLOSING) if budget is not None and budget[0] <= len(t.split()) <= budget[1]), None)` will evaluate `budget` for every template, even if `budget` is `None`. This is harmless but slightly inefficient. |
| 3 | P3 | `fallback_fields` returns `None` when no template fits the budget | The function returns `None` if no closing template fits the word‑budget. The caller (`_build`) treats this as a failure and breaks the loop. This is intentional, but the code could be clearer by explicitly documenting that `None` signals “no fallback available”. |
| 4 | P3 | `inventory` adds a `fallback_line` flag only when `soft` and `fallback_line` are truthy | The flag is added with `**({"fallback_line": {"status": "FLAGGED", ...}} if soft and fallback_line else {})`. If `fallback_line` is an empty string (unlikely but possible if the fallback text is empty), the flag would not be added. The code assumes a non‑empty string, which is reasonable given the templates. |
| 5 | P3 | `LINE_ONLY_WRITES` increased from 2 to 3 but comments still refer to “4 writes a line” | The comment on line 98 mentions “up to 4 writes a line”, which is inconsistent with the code that allows 3 writes of the line alone plus the initial write (total 4). The comment could be clarified to avoid confusion. |

**P1_OR_WORSE**: 0 (no P0 or P1 findings)

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats answered: 2 of 2 (gpt-oss-20b at effort low: 0 P0/P1; glm-5.3-flash at effort none: 3 counted, 8 headed P1).
FIXED (real, cheap):
- glm F1: fallback_fields raised IndexError for a line-up with no channel name at all (chans empty): now 'the
  channels'; a single channel keeps its name.
- glm F2: a name run with a doubled space counted as another subject: the run is normalised to single spaces.
TRACED, NO DEFECT:
- F3 (the budget with `written`): the model-write path computes the same takeaway_budget(sum, written); glm marks P2.
- F4 (the flag condition reads `fields`): fields is assigned by the branch that ran (fallback or write) before the
  paid gates; the flag is on the package exactly when the sealed takeaway text equals the fallback's (tested).
- F5 (the clean-pass test): the fallback needs `soft`; glm's own trace agrees.
- F6 (kind_sentences' final `or c`): reached only for a code no table words (none today); renders the code, never a
  crash (ruling 155's audit asked exactly this).
- F7 (the caption lowercased with its names): house style's rule ('caption-lowercase ... all lowercase, names too');
  lint_lines passes it (tested).
- F8 (can the fallback run twice / loop forever): fb_state goes None -> 'due' -> 'used' once; after it only the
  takeaway-alone writes may run (alone_n, bounded by LINE_ONLY_WRITES), then the break (fb_state not None).
Cycle 2 cross-examines the hardened diff.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261123_2143/C2_STEP.diff (303 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index f4cf9694b..60252bfe0 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -56,6 +56,7 @@ import json
   6 |  import math
   7 |  import os
   8 |  import re
   9 | +import types
  10 |  import threading
  11 |  import time
  12 |  from concurrent.futures import ThreadPoolExecutor
  13 | @@ -139,7 +140,8 @@ def kind_sentences(pairs, who):
  14 |          else:
  15 |              chans = ", ".join(str((who or {}).get(lb) or "its channel") for lb in lbs)
  16 |              out.append(f"{COUNT_WORDS.get(len(lbs), str(len(lbs)))} clips ({chans}): "
  17 | -                       f"{STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY[c]}.")
  18 | +                       f"{STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY.get(c) or STEP_A_SOFT.get(c) or EDGE_WORDS.get(c) or c}.")
  19 | +            #   audit 20261123_2108 C1 (qwen P1): never a KeyError, even for a code no table words for several clips
  20 |      return out
  21 |  
  22 |  
  23 | @@ -2776,6 +2778,70 @@ def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7,
  24 |                     type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))
  25 |  
  26 |  
  27 | +FALLBACK_FLAG = 'A line of ours is the plain fallback: "{line}"'   # RULING 156 (2): one flag kind, the line verbatim
  28 | +FALLBACK_CLOSING = ("{subject}, in their own words.",                       # graded lengths, the shortest that
  29 | +                    "{subject}, in the words of {names}.",                   # lands takeaway_budget is the line
  30 | +                    "{subject}, in the words of {names}, in their own clips.",
  31 | +                    "That was {subject}, in the words of {names}, in the clips you just heard.",
  32 | +                    "That was {subject}, in the words of {names}, each in their own clip, as you just heard.")
  33 | +
  34 | +
  35 | +def fallback_subject(segs, chans):
  36 | +    """RULING 156 (2): the story's subject in the clips' own words: 'Bitcoin', or '<Name> and Bitcoin' where <Name> is
  37 | +    the run of capitalised words (its first never opening a sentence; no channel's word, 'I' or 'Bitcoin' in it) the most
  38 | +    of the line-up's clips say, at least two of them, in their spelling ('Michael Saylor'); ties: the earliest said."""
  39 | +    import collections
  40 | +    skip = {"i", "bitcoin"} | {w.lower() for c in chans for w in re.findall(r"[A-Za-z]+", str(c))}
  41 | +    count, first = collections.Counter(), {}
  42 | +    for i, m in enumerate(segs):
  43 | +        t, names = str(m.get("text") or ""), set()
  44 | +        for mm in re.finditer(r"[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*", t):
  45 | +            run, before = " ".join(mm.group(0).split()), t[:mm.start()].rstrip()   # glm F2: one spelling a run
  46 | +            if not before or before[-1] in ".!?" or any(w.lower() in skip for w in run.split()):
  47 | +                continue
  48 | +            names.add(run)
  49 | +            first.setdefault(run, (i, mm.start()))
  50 | +        for w in names:
  51 | +            count[w] += 1
  52 | +    best = sorted((w for w, n in count.items() if n >= 2), key=lambda w: (-count[w], first[w]))
  53 | +    return f"{best[0]} and Bitcoin" if best else "Bitcoin"
  54 | +
  55 | +
  56 | +def fallback_fields(angle, segs, join=None, other=()):
  57 | +    """RULING 156 (2) (orchestrator 21:34 ET Nov 23): THE SAFE FALLBACK LINES, built by code from fixed templates that
  58 | +    state no fact of their own (only the subject in the clips' own words and the channels' names), gated as any write:
  59 | +    the closing line (the shortest FALLBACK_CLOSING variant inside takeaway_budget), a title ('<Subject>: <names>', or
  60 | +    '<Subject>, in their words' past ruling 6's 8 words), a caption ('<Subject>, in the words of <names>.') and, only
  61 | +    where a join needs one, a bridge ('Next, <channel>.'). -> write_takeaway's fields, or None when no closing variant
  62 | +    lands the budget."""
  63 | +    chans = []
  64 | +    for m in segs:
  65 | +        c = m.get("channel_name") or m.get("channel_id")
  66 | +        if c and c not in chans:
  67 | +            chans.append(c)
  68 | +    names = chans[0] if len(chans) == 1 else (", ".join(chans[:-1]) + " and " + chans[-1] if chans else
  69 | +                                              "the channels")   # audit 20261123_2143 C1 (glm F1): never an IndexError
  70 | +    subject, ids = fallback_subject(segs, chans), [m["moment_id"] for m in segs]
  71 | +    bridge = None
  72 | +    if join is not None:
  73 | +        nxt = segs[join[0] + 1]
  74 | +        bridge = {"text": f"Next, {nxt.get('channel_name') or 'the next channel'}.", "cites": [nxt["moment_id"]],
  75 | +                  "why": "the plain fallback bridge (ruling 156 (2))"}
  76 | +    budget = takeaway_budget(sum(m["duration_s"] for m in segs), list(other) + ([bridge["text"]] if bridge else []))
  77 | +    take = next((t for t in (f.format(subject=subject, names=names) for f in FALLBACK_CLOSING)
  78 | +                 if budget is not None and budget[0] <= len(t.split()) <= budget[1]), None)
  79 | +    if take is None:
  80 | +        return None
  81 | +    title = f"{subject}: {names}"
  82 | +    if len(title.split()) > HS.TITLE_MAX_WORDS or len(title) > LINE_CHARS["title"]:
  83 | +        title = f"{subject}, in their words"
  84 | +    return {"takeaway": {"text": take, "cites": ids}, "title": {"text": title, "cites": ids},
  85 | +            "caption": {"text": f"{subject}, in the words of {names}.".lower(), "cites": ids},   # house style:
  86 | +            "bridge": bridge,                                                          # a caption is all lowercase
  87 | +            "bridge_after": join[0] if bridge else None, "type": "moments", "angle": angle["angle"], "style": "medley",
  88 | +            "takeaway_budget": list(budget), "fallback": True}
  89 | +
  90 | +
  91 |  WRITE_LINE = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
  92 |  THE ANGLE (the point this video makes): "{angle}"
  93 |  The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
  94 | @@ -2798,7 +2864,8 @@ LINE_WHY = {"AGAIN": "your first rewrite of it was refused too",   # 17:20: a ti
  95 |              "STYLE": "it breaks the house style"}
  96 |  LINE_LIMIT = {"caption": "at most 220 characters", "title": "at most 70 characters"}
  97 |  LINE_CHARS = {"caption": 220, "title": 70, "takeaway": 240}
  98 | -LINE_ONLY_WRITES = 2                  # RULING 66 amended (17:02 Nov 13): "up to TWO fresh writes of the failed line only"
  99 | +LINE_ONLY_WRITES = 3                  # RULING 156 (1) (21:34 ET Nov 23): up to 4 writes a line per angle (the write and
 100 | +#   3 of the line alone, each told its refusal and the words; the other model after a failure); RULING 66 amended had 2
 101 |  TAKEAWAY_LIMIT = ("{lo}-{hi} words, one or two sentences: host commentary attributed to nobody that states no fact, no "
 102 |                    "speaker's view, no advice or prediction and no accusation, and that no viewer could take for a "
 103 |                    "speaker's words")
 104 | @@ -4283,11 +4350,14 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 105 |                  v_lost, v_redo, v_novoice, v_plan, val = [], False, None, None, None   # RULING 91 (medley half):
 106 |                  #   the value verdicts the takeaway lost, its ONE rewrite still due, the loss that sends the line-up to
 107 |                  #   the no-voice shape with the plan decided for it (nv_order), and the verdict of the takeaway now written
 108 | +                fb_state, fb_text = None, None           # RULING 156 (2): the plain lines, once, after every write
 109 |                  while True:                                # RULING 66 amended (17:02): the writes; then, when the
 110 |                      lone = w_used >= writes or v_redo      # takeaway alone failed, the takeaway ALONE, up to twice
 111 |                      if lone and not v_redo and not (alone_n < LINE_ONLY_WRITES and t_alone and last_fields is not None
 112 |                                                      and not last_rw65):
 113 | -                        break
 114 | +                        if not (soft and fb_state is None and w_used >= writes):
 115 | +                            break
 116 | +                        fb_state = "due"                   # never-empty pass: every write failed: the template lines
 117 |                      if over_budget(ai):
 118 |                          break
 119 |                      w_over = package_over(line)
 120 | @@ -4295,7 +4365,18 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 121 |                          rec["why"], rec["budget"] = w_over, True      # ruling 66: a budget, not an outcome
 122 |                          break
 123 |                      redo91 = False
 124 | -                    if lone:                               # the other lines kept as gated; told each refusal and why
 125 | +                    if fb_state == "due":                  # RULING 156 (2): built by code, gated as any full write
 126 | +                        fields, fb_state = fallback_fields(angle, segs, join, written), "used"
 127 | +                        if fields is None:
 128 | +                            rec["fallback_line"] = {"why_not": "no closing template lands the takeaway's word budget"}
 129 | +                            break
 130 | +                        fb_text = fields["takeaway"]["text"]
 131 | +                        rec["fallback_line"] = {"text": fb_text, "title": fields["title"]["text"]}
 132 | +                        log(f"    RULING 156 (2): every write failed: the plain lines built by code, gated as any: "
 133 | +                            f"{fb_text!r} | title {fields['title']['text']!r}")
 134 | +                        wr = types.SimpleNamespace(vendor="code", family="code", backend="code:fallback (ruling 156)")
 135 | +                        lone = False
 136 | +                    elif lone:                             # the other lines kept as gated; told each refusal and why
 137 |                          alone_n += 1
 138 |                          redo91, v_redo = v_redo, False     # ruling 91's one rewrite is spent here, whatever comes of it
 139 |                          b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 140 | @@ -4533,6 +4614,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 141 |                                              value=val,                       # ruling 91: the takeaway earned its place
 142 |                                              last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 143 |                                              soft=soft,
 144 | +                                            fallback_line=fb_text if fb_text is not None and
 145 | +                                            fields["takeaway"]["text"] == fb_text else None,   # RULING 156 (2)
 146 |                                              chan_of={sg["moment_id"]: sg.get("channel") for sg in pk["segments"]},
 147 |                                              who={sg["label"]: sg.get("channel")   # RULING 137 / 138 (3)
 148 |                                                              for sg in pk["segments"]},
 149 | @@ -4670,7 +4753,7 @@ def _spent(spend):
 150 |  
 151 |  
 152 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None, short=None,
 153 | -              chan_of=None,
 154 | +              chan_of=None, fallback_line=None,
 155 |                hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None,
 156 |                seg_flags=None, mids=None):
 157 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 158 | @@ -4771,6 +4854,11 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 159 |                                 **({"status": "FLAGGED", "flags": ["The opening clip may start abruptly."]}   # RULING
 160 |                                    if soft and hook.get("soft") is True and hook.get("pass") is not True else {}))}   # 146
 161 |             if hook is not None else {}),                                                                      # (2)
 162 | +        **({"fallback_line": {"status": "FLAGGED", "by": "package.fallback_fields (ruling 156 (2)): the plain lines "
 163 | +                                                         "built by code from fixed templates that state no fact, gated "
 164 | +                                                         "as any line", "replayed": False, "n": 1,
 165 | +                              "flags": [FALLBACK_FLAG.format(line=fallback_line)]}}
 166 | +           if soft and fallback_line else {}),
 167 |          **({"sponsor": {"status": "FLAGGED", "by": "moments.exclusion_verdict (ruling 146 (3)): a sponsor mention in "
 168 |                                                     "the sentence before the clip only; its own words judged by the "
 169 |                                                     "exclusion model", "replayed": False, "n": len(exc), "flags": [
 170 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 171 | index dd8f4bd10..272c8b5ef 100644
 172 | --- a/pipeline/package_pin.py
 173 | +++ b/pipeline/package_pin.py
 174 | @@ -49,6 +49,7 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 175 |                          "graphics",                        # RULING 146 (1): the show's own graphics, 16:9 only
 176 |                          "takeaway_value",                  # RULING 150: the closing line's value verdict (ruling
 177 |                          #   91), a measured one; fidelity, length and the banned words stay HARD
 178 | +                        "fallback_line",                   # RULING 156 (2): our plain lines built by code, gated
 179 |                          "sponsor",                         # RULING 146 (3): a sponsor mention in the sentence before
 180 |                          #   a clip only, the clip kept by the exclusion model (its ad_read risk stays HARD)
 181 |                          "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
 182 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 183 | index f965429b5..30e5a4aaa 100644
 184 | --- a/tests/package/test_medley.py
 185 | +++ b/tests/package/test_medley.py
 186 | @@ -2860,7 +2860,7 @@ class TestRuling66Amended(unittest.TestCase):
 187 |                                           alone_ok=(False, False))
 188 |          self.assertIsNone(out["package"])
 189 |          self.assertEqual(len(seen), 2)                                         # up to TWO, never more
 190 | -        self.assertIn("2 write(s) and 2 of the takeaway alone (ruling 66, 17:02) failed", out["tried"][0]["why"])
 191 | +        self.assertIn("2 write(s) and 3 of the takeaway alone (ruling 66, 17:02) failed", out["tried"][0]["why"])   # 156 (1)
 192 |          self.assertIn("no one clip of the angle lands", out["tried"][0]["no_voice"]["why_not"])   # then rest
 193 |  
 194 |      def test_a_failure_on_another_line_gets_no_takeaway_alone_write(self):
 195 | @@ -2879,7 +2879,7 @@ class TestRuling66Amended(unittest.TestCase):
 196 |                                                    {"takeaway": {"text": "In the end nobody bends them.", "cites": []}}],
 197 |                                               ms=ms, takeaways=bad,
 198 |                                               medleys=[(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)])
 199 | -        self.assertEqual(len(avoid["takeaway"]), 2)                            # the takeaway alone, twice (STYLE)
 200 | +        self.assertEqual(len(avoid["takeaway"]), 3)                            # the takeaway alone, 3 times (156 (1))
 201 |          self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")   # then ruling 3
 202 |          self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])
 203 |  
 204 | @@ -2899,7 +2899,7 @@ class TestRuling66Amended(unittest.TestCase):
 205 |          rig, out, seen, avoid = self.run_rig([refused], replies, alone_ok=(False, False))
 206 |          self.assertIsNone(out["package"])                                      # then held (ruling 65 c)
 207 |          self.assertEqual(len(seen), 2)                                          # two writes of the title, no more
 208 | -        self.assertIn("the title failed alone 3 times", out["tried"][0]["why"])
 209 | +        self.assertIn("the title failed alone 4 times", out["tried"][0]["why"])   # RULING 156 (1): 4 writes a line
 210 |          self.assertIn("held (ruling 65 c)", out["tried"][0]["why"])
 211 |          rig, out, seen, avoid = self.run_rig([self.failing("caption")], [{"caption": {"text": "anyone can join it.",
 212 |                                                                                        "cites": []}}],
 213 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 214 | index 2c509168e..e9fede70c 100644
 215 | --- a/tests/package/test_ruling_137.py
 216 | +++ b/tests/package/test_ruling_137.py
 217 | @@ -259,6 +259,85 @@ class TestRuling155FlagKinds(unittest.TestCase):
 218 |          self.assertEqual(PK.seg_marks(segs), 4)        # REFERENT_OUTSIDE, NOT_OWN_SINCERE, EDGE_OUT, STAND_ALONE
 219 |  
 220 |  
 221 | +FAILING = 2
 222 | +
 223 | +
 224 | +class TestRuling156FallbackLines(unittest.TestCase):
 225 | +    """RULING 156 (2) (orchestrator 21:34 ET Nov 23): when every write fails, the never-empty pass gates ONE set of plain
 226 | +    lines built by code from fixed templates that state no fact (the subject in the clips' own words and the channels'
 227 | +    names); a package on them carries the one flag 'A line of ours is the plain fallback: "<line>"'. The clean pass never
 228 | +    uses them; fidelity stays HARD (they are gated as any write)."""
 229 | +    def segs(self, total=39.0):
 230 | +        from test_moments import pm
 231 | +        ms = [pm("h", "Natalie Brunell", total / 3), pm("x", "Strategy", total / 3), pm("y", "Yahoo Finance", total / 3)]
 232 | +        for m, t in zip(ms, ("Analysts say Michael Saylor will keep buying Bitcoin.",
 233 | +                             "We sold credit, and Michael Saylor said we buy more Bitcoin.",
 234 | +                             "This guy, Michael Saylor, is buying again.")):
 235 | +            m["text"] = t
 236 | +        return ms
 237 | +
 238 | +    def test_the_templates_state_no_fact_fit_the_budget_and_pass_house_style(self):
 239 | +        import house_style as HS
 240 | +        for total in (31.5, 34.5, 39.0, 45.0):
 241 | +            with mock.patch.object(PK, "_FLOOR", PK.LY_FLOOR_S):           # the never-empty pass's budget
 242 | +                f = PK.fallback_fields({"angle": "a"}, self.segs(total))
 243 | +            lo, hi = f["takeaway_budget"]
 244 | +            words = f["takeaway"]["text"].split()
 245 | +            self.assertTrue(lo <= len(words) <= hi, (total, f["takeaway"]["text"]))
 246 | +            self.assertIn(f["takeaway"]["text"], [v.format(subject="Michael Saylor and Bitcoin",
 247 | +                                                           names="Natalie Brunell, Strategy and Yahoo Finance")
 248 | +                                                  for v in PK.FALLBACK_CLOSING])
 249 | +            self.assertEqual(HS.lint_lines([{"slot": k, "text": f[k]["text"]} for k in ("takeaway", "title", "caption")]),
 250 | +                             [], total)
 251 | +            self.assertEqual((f["title"]["text"], f["caption"]["text"]), (
 252 | +                "Michael Saylor and Bitcoin, in their words",
 253 | +                "michael saylor and bitcoin, in the words of natalie brunell, strategy and yahoo finance."))
 254 | +        one = self.segs()
 255 | +        one[1]["text"] = "We sold credit."
 256 | +        self.assertEqual(PK.fallback_subject(one, ["Natalie Brunell", "Strategy", "Yahoo Finance"]),
 257 | +                         "Michael Saylor and Bitcoin")                 # still two clips say it
 258 | +        one[2]["text"] = "This guy is buying again."
 259 | +        self.assertEqual(PK.fallback_subject(one, ["Natalie Brunell"]), "Bitcoin")   # one clip only: Bitcoin alone
 260 | +
 261 | +    def test_a_join_that_needs_a_bridge_gets_the_plain_one(self):
 262 | +        with mock.patch.object(PK, "_FLOOR", PK.LY_FLOOR_S):
 263 | +            f = PK.fallback_fields({"angle": "a"}, self.segs(), join=(1, "x"))
 264 | +        self.assertEqual((f["bridge"]["text"], f["bridge_after"]), ("Next, Yahoo Finance.", 1))
 265 | +
 266 | +    def run_rig(self, never_empty, failing=FAILING, a_fail=True):
 267 | +        import test_medley as TM
 268 | +        from test_moments import pm
 269 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 270 | +        bad = TM.TestRuling66Amended().failing()
 271 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2,
 272 | +                   fids=[dict(bad) for _ in range(failing)],         # every model write fails fidelity (COMMENTARY)
 273 | +                   a_fail={("xai", "y"): ["REFERENT_OUTSIDE"]} if a_fail else None)   # the clean pass stops at 2
 274 | +        #   channels, before any
 275 | +        #   write; the never-empty pass takes y back, flagged (stage 1), and writes
 276 | +        if never_empty:
 277 | +            r.build_kw = {"never_empty": True}
 278 | +        return r, r.run()
 279 | +
 280 | +    def test_every_write_failing_seals_on_the_plain_lines_flagged(self):
 281 | +        r, out = self.run_rig(True)
 282 | +        pk = out["package"]
 283 | +        self.assertIsNotNone(pk, out.get("why_none"))
 284 | +        take = next(x["text"] for x in pk["lines"] if x["slot"] == "takeaway")
 285 | +        self.assertEqual(pk["gates"]["fallback_line"]["flags"], [PK.FALLBACK_FLAG.format(line=take)])
 286 | +        self.assertTrue(any(take == v.format(subject="Bitcoin", names="A, B and C") for v in PK.FALLBACK_CLOSING))
 287 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 288 | +
 289 | +    def test_the_clean_pass_never_uses_them(self):
 290 | +        r, out = self.run_rig(False, a_fail=False)                   # the clean pass reaches the writes, all fail
 291 | +        self.assertIsNone(out["package"])
 292 | +        self.assertNotIn("fallback_line", out["tried"][0])
 293 | +
 294 | +    def test_fidelity_stays_hard_for_the_plain_lines(self):
 295 | +        r, out = self.run_rig(True, failing=FAILING + 1)             # the plain lines' own verdict fails too
 296 | +        self.assertIsNone(out["package"])
 297 | +        self.assertIn("fallback_line", ((out.get("never_empty") or {}).get("soft_record") or {})["tried"][0])
 298 | +
 299 | +
 300 |  class TestStage2bHookBar(unittest.TestCase):
 301 |      """RULING 137 STAGE 2b (1) (line 1, 13:20 ET): the calibrated hook bar is SOFT in the never-empty pass. A hook its
 302 |      own rater rated UNDER a floor opens, flagged in plain words (the best HOOK_SOFT_MAX of them); no calibration,
 303 | 
```

---

pp-selectid: RULING 156 (orchestrator 21:34 ET Nov 23): "Our writing must never be the reason PBX gets no video."
(1) each line of ours gets up to 4 writes per angle, every rewrite told the gate's refusal and the words; (2) THE SAFE
FALLBACK LINE: when the writes fail, a PLAIN line built by code from a fixed template that states no fact of its own
(only the story's subject in the clips' own words and the channels' names), gated as any line, the package flagged
'A line of ours is the plain fallback: "<line>"'; (3) fidelity stays HARD.
THE CHANGE (pipeline/package.py, pipeline/package_pin.py; tests in tests/package/test_ruling_137.py, test_medley.py):
- LINE_ONLY_WRITES 2 -> 3 (the write and 3 of the line alone = 4; the alone writes are unchanged code: told the refused
  sentence and why, the other model after a failure).
- fallback_subject / fallback_fields (package.py:2810): FALLBACK_CLOSING's 5 graded variants, the shortest inside the
  unchanged takeaway_budget; title '<Subject>: <names>' or '<Subject>, in their words' past 8 words; caption lowercase
  (house style); a bridge 'Next, <channel>.' only for a join that needs one; cites = the line-up's ids.
- The write loop (package.py:4367): ONLY in the never-empty pass (soft), once, when every write is spent
  (w_used >= writes and no takeaway-alone write left): fields = fallback_fields(...), a writer namespace 'code' (no
  judge's vendor), lone = False, so the plain lines go through the SAME full paid gates as a model write
  (paid_gates, package.py:3237, unchanged: fidelity, context) and every later gate (value, coherence, the lock).
- inventory: a FLAGGED 'fallback_line' row (its sentence quotes the closing line) when the sealed takeaway is the
  fallback's text; package_pin.SOFT_GATES += 'fallback_line' (gate_problems, package_pin.py:463, accepts a FLAGGED row
  only on a soft gate; the integrator's pin check reads this file live).
Also in this diff: one line from ruling 155's audit C1 (kind_sentences never raises KeyError).
TESTS: the templates fit the budget at 31.5-45 s and pass house style; the subject rule; the plain bridge; every write
failing seals on the plain lines with the flag and gate_problems none; the clean pass never uses them; the plain lines
failing fidelity refuse (HARD). Mutations 7 of 7 killed.
PLEASE CHECK: (1) can the clean pass, or a line-up whose failure is a CLIP's (not our line's), reach a sealed package
through the fallback without every gate? (2) do the templates ever state a fact or a claim? (3) can the fallback loop
run more than once or never end? (4) is the flag on the package exactly when the sealed closing line is the fallback?


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
