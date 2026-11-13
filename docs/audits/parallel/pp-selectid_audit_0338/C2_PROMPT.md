# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0338
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 166 s finish=stop usage in 10459 / out 3729 usd~0.087 (upper-bound price)

# Audit: pp-selectid — transcript_truth rulings 38/39

## P0

None found.

## P1

**P1-1 — (b) can pass when a recognised word sits *inside* the 700 ms gap (contradicts the ruling's "no speech" reading).**
`transcript_truth.py:88` computes `gap = t_open - (ws[j].end or ws[j].start)`, where `j` is the immediately preceding recognised word. But `edges()` receives `second["words"]` filtered only by `w.get("start") is not None` (line 60) — it does **not** filter to words inside the window, and the candidate lists `ci`/`co` are built over the *whole* word list. If the recogniser returns a word whose `start` lies *after* `t_in` (e.g. a word the primary transcript places inside the clip, or a word straddling the clip start), it can become `ws[j]` for a *different* candidate `i`... — actually, more precisely: the construction guarantees no *recognised* word between `ws[j]` and `ws[i]` **only if** the words list is time-sorted and `i` is the first candidate. `ci[0]` is the earliest candidate within 0.6 s of `t_in`; a word between `ws[j]` and `ws[i]` that failed the 4-letter/canon match (e.g. the recogniser wrote the opening word differently, so it appears in `ws` but not in `ci`) would be skipped: the gap then spans *two* words, and the "pause" includes the duration of a spoken word the matcher didn't match. Scenario: recogniser hears "and Bitcoin is money…" where the clip text's first word "Bitcoin" matches the *second* "Bitcoin" occurrence; the unmatched "and" sits inside the measured gap; a 750 ms gap that actually contains ~300 ms of speech passes (b). I can verify this from the diff; I cannot verify whether the upstream recogniser can produce such unmatched interlopers — if it cannot, this is P2, not P1.

**P1-2 — (c) file-head test uses `wav_start <= 0.0` but the clamp produces `wav_start == 0.0` only when `start - 4.0 <= 0`; a clip starting < 4 s into the file gets `wav_start = 0.0` and (c) fires even when the window *does* hold words before the clip — no, it doesn't: (c) additionally requires `prev is None`.** Verified: `head = prev is None and wav_start <= 0.0` (line 90) — both conditions, so a 2.35 s-into-file clip with recognised words before it correctly falls to (a)/(b). Downgraded; no finding. However: when `prev is None` and `wav_start > 0` (window starts mid-pause, no word), the gap is measured from the window's start (line 88, `else 0.0`), i.e. from `wav_start`, but `t_open` is in window time — consistent. But when `prev is None` and the window *starts at the clip* (`wav_start == start`, the old 1.5 s... no, with PAD_BEFORE_S=4.0 the window never starts at the clip unless `start <= 0`). Verified: with the new 4 s pad, `wav_start == start` only when `start <= 0`, which the clamp makes `wav_start = 0.0` — so the "window starts at the clip" branch (line 99) is now reachable only for `start <= 0`... yet the test at line 166–168 constructs `wav_start=2.0, first_at=0.30` and asserts the "window starts at the clip" reason. That test exercises `edges()` directly with a synthetic `wav_start` that `audio_window` can no longer produce (with pad 4.0, `wav_start = max(0, start-4) = 2.0` requires `start = 6.0`, and then `first_at = 0.30` means the clip's first word at 6.3 s while the clip starts at 6.0 s — a 300 ms lead, plausible). So the branch is reachable; the test is valid. No finding.

**P1-3 — `pause_ms`/`gap` when `j < 0` measures from window start, not from the last word's end — but the ruling says "measured pause ... with no speech", and the window's start is not evidence of silence before it.** When `j < 0` (no recognised word before the clip in the window) and `wav_start > 0`, `gap = t_open - 0.0 = t_open`, i.e. the pause is measured from the *window's* start. If the window starts mid-speech (the recogniser simply failed to hear the word at the window's head, or the window's first word's timing was dropped by the `start is not None` filter at line 60), the measured "pause" includes speech. This is the same class as P1-1: the ruling's "measured pause of at least 700 ms with no speech" is verified only against the recogniser's word list, not against the audio. The ruling itself says "the recogniser heard no word", so measuring on word timing alone is arguably what ruling 38 mandates — I can verify the code implements the ruling as quoted; whether it matches the acoustic intent (the -54 to -59 dBFS measurement) is not verifiable from this diff. Flagging as a documented-uncertainty, not a defect: **the code measures the pause on the recogniser's word timing alone; speech the recogniser missed (or words dropped by the `start is not None` filter) inside the gap would pass (b) unnoticed.** The ruling's own wording ("the recogniser heard no word") sanctions this, so: condition, not blocker.

## P2

**P2-1 — `_canon_from`/`_canon_to` can match a *different* number/word.** `transcript_truth.py:33-43`:

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 43 s finish=stop usage in 10578 / out 611 usd~0.068 (upper-bound price)

**P0: None**

**P1: None**

**P2:**
- transcript_truth.py:74-76 (ci/co list comprehensions): canon match is OR-ed with the original 4-letter prefix rule and limited to time windows 0.6s (IN) / 0.8s (OUT). The provided TestEdgesRulings38And39.test_a_spoken_number_matches_the_clips_digits_at_both_edges verifies that a different number ("26 %") does not match spoken "Twenty-five percent" (e3 fails as expected). No test case is present for repeated identical edge tokens or a run that reaches a second identical canonical token inside the time window; uncertain whether first-listed i (ci[0]) could select the wrong instance.
- transcript_truth.py:88-92 (gap calculation): pause = (opening_word_start - prev_end); accepts if >= PAUSE_MIN_S with no intervening recognised word (by construction). Test cases at 650 ms (fails, "runs on into the clip") and 750 ms (passes) confirm <700 ms following a recognised word cannot pass via (b). File-head case (wav_start <= 0 and prev is None) also covered. Implementation uses only recogniser word timing; no dBFS / acoustic check of the gap appears in the diff, so speech missed by the recogniser in a >=700 ms gap would still be treated as a valid pause (matches the ruling text "with no recognised word" but cannot verify against unshown acoustic intent).
- transcript_truth.py:87 (t_open = ws[j+1]["start"] after self_repair): self_repair decrements j, then j+1 correctly selects the opening word (or the false-start itself when measuring before it). Test case passes with expected pause_ms=800 before the repair; no off-by-one or negative-index error triggered in the exercised paths (j >= -1 guarded by prev=None logic). Slicing in _canon_from (ws[i:i+6]) and _canon_to (ws[max(0,i-5):i+1]) is safe for edge indices.
- transcript_truth.py:108-119 & edges(): PAD_BEFORE_S=4.0 is used consistently for window, offset, and WAV naming (new files for new windows). OUT rule, speaker/turn checks, and verify_segment compare logic are untouched except for the expanded word-matching and new IN conditions. TestEdgesRulings38And39 exercises audio_window clamping, verify_segment end-to-end, and all three IN acceptance paths (terminal, pause, head).
- All new constants (PAD_BEFORE_S, PAUSE_MIN_S, CANON_RUN) are defined with ruling references; uses canon.canon_tokens (satisfies L-k). No other acceptance criteria widened; fail-closed behavior for missing words/timing preserved. New tests cover the measured 02:37 defects (IN pause inside 1.5 s window, OUT number canonical mismatch).

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 171 s finish=stop usage in 11412 / out 6546 usd~0.132 (upper-bound price)

# Code Audit: pp-selectid-0338 (C1_STEP.diff)

## P0 Findings

**1. `pipeline/transcript_truth.py` (lines 87-91): `head` condition is logically dead code and fails closed incorrectly.**
The condition `head = prev is None and wav_start <= 0.0` is unreachable as a *distinct* success path because the `pause` condition (line 91) subsumes it. When `prev is None`, the code calculates `gap` as `t_open - 0.0` (line 88). If the window reaches the file head (`wav_start <= 0.0`), the clip's opening word is at `t_open > 0`. Therefore `gap = t_open`.
*   **Scenario A (False Negative):** If the file's first spoken word occurs at `t_open = 0.5s` (500ms into the file), `gap = 0.5s`. Since `0.5 < 0.7` (`PAUSE_MIN_S`), `pause` is `False`. `head` is `True`. The logic `ok = ends or pause or head` *would* pass it. **However**, the `why` string logic (lines 94-100) checks `ends` first, then `head`, then `pause`. This part is fine.
*   **Scenario B (The Real Bug - Logic Inversion in `why`):** Look at line 99: `("the window starts at the clip: no word before it" if prev is None else ...)`. This branch is reached if `ends` is False, `head` is False, and `pause` is False. If `prev is None` and `wav_start > 0` (window does *not* reach head) and `gap < 0.7`, it correctly fails.
*   **Wait, let's re-read the `head` logic carefully.**
    Line 90: `head = prev is None and wav_start <= 0.0`.
    Line 91: `pause = gap >= PAUSE_MIN_S - 1e-9`.
    Line 92: `out["in"] = {"ok": ends or pause or head, ...}`.
    
    If `prev is None` and `wav_start <= 0.0` (File Head), `head` is `True`. `ok` is `True`.
    If `prev is None` and `wav_start > 0.0` (Not File Head), `head` is `False`. `ok` depends on `pause`.
    
    **Is there a P0 here?**
    The prompt asks: *"that (b) and (c) cannot pass a clip whose opening word FOLLOWS a recognised word by less than 700 ms"*.
    If a word follows, `prev` is not `None`. `head` is `False`. `pause` is calculated based on the gap from `prev`. If gap < 0.7, `pause` is `False`. `ends` is `False` (assuming no punctuation). `ok` is `False`. This is correct.
    
    **However**, there is a subtle issue with `wav_start`.
    In `audio_window` (line 25), `a = max(0.0, start - pad_before)`.
    If `start = 2.0` and `pad_before = 4.0`, `a = 0.0`. `wav_start` returned is `0.0`.
    If `start = 10.0` and `pad_before = 4.0`, `a = 6.0`. `wav_start` returned is `6.0`.
    
    In `edges()`, `wav_start` is passed in.
    Line 90: `head = prev is None and wav_start <= 0.0`.
    This correctly identifies if the window starts at the absolute beginning of the video file.
    
    **Let's look at the `gap` calculation when `prev is None` (Line 88):**
    `gap = t_open - (float(ws[j].get("end") or ws[j]["start"]) if j >= 0 else 0.0)`
    If `prev is None`, it implies `j` was `-1` (or `i` was 0 and no self-repair).
    If `j == -1`, the term is `0.0`.
    `t_open` is `float(ws[j+1]["start"])` which is `ws[0]["start"]`.
    So `gap = ws[0]["start"] - 0.0`.
    This measures the time from the **start of the WAV file** to the first word.
    
    **P0 Candidate:** Does `wav_start` represent the start of the WAV file in *video* time or *WAV* time?
    Docstring line 22: `-> (path, the window's real start in video seconds)`.
    So `wav_start` is video time.
    `t_in` (line 69) is `start - wav_start`. This is the clip start relative to the WAV file.
    `ws` words have `start` times relative to the WAV file (0.0 is start of WAV).
    
    If `wav_start = 0.0` (File Head), `t_in = start`.
    `ws[0]["start"]` is the time of the first word in the WAV.
    `gap = ws[0]["start"]`.
    This is the silence at the very beginning of the video file.
    Ruling 38 says: *"A clip that starts at the first spoken word of the file counts as a sentence start when the window reaches the file head and holds no speech."*
    The code implements this as `head = prev is None and wav_start <= 0.0`.
    This passes **regardless of the length of the silence** at the head.
    Is this a violation?
    Ruling 38 text: *"or a measured pause of at least 700 ms with no speech. A clip that starts at the first spoken word of the file counts as a sentence start when the window reaches the file head and holds no speech."*
    It does **not** specify a minimum pause for the file head case. It says "holds no speech".
    So `head` being `True` without a pause check is compliant with the quoted ruling.
    
    **However**, consider the case where `wav_start > 0` but `prev is None`.
    This means the window starts *after* the file head, but the recogniser found no words before the clip's first word.
    `head` is `False`.
    `gap = ws[0]["start"]` (time from WAV start to first word).
    `pause = gap >= 0.7`.
    This correctly applies the 700ms rule.
    
    **Conclusion on P0 #1:** The logic seems compliant with the specific wording of Ruling 38.

**2. `pip

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0338 (rulings 38 + 39: the IN edge's 4 s window, 700 ms pause and file head; canonical edge match): cycle 1 consensus

Synthesis by the pp-selectid session, 03:31 ET Nov 13, written before cycle 2.

**Run.** C1_STEP.diff covers transcript_truth.py and test_angles.py. No P0. Verdicts:
- grok: no P0 and no P1, "SHIP: yes";
- qwen: "yes with conditions";
- glm: "yes with conditions".

## Consensus (each verified from the code or the data, no code change needed)

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | The pause (b) and the file head (c) are measured on the recogniser's word timing alone. Speech it missed could pass (glm P1-3, qwen P1-3 / P2; both "condition, not blocker", both note the ruling's wording) | KEPT, as the ruling's measure. Ruling 38: "the independent recogniser must show a sentence end before the clip, or a measured pause of at least 700 ms with no speech". The pin stage's CUTTABLE judges SENTENCE boundaries with the independent recogniser. The acoustic check of every cut is the render's: cut acceptance (check_cut_acoustics) and G16 hold any cut not inside a measured pause. An acoustic confirmation of (b) at the pin stage is offered to the orchestrator in STATE. |
| K2 | self_repair at j = -1 could wrap to the last word (glm P2-3, its condition 1) | VERIFIED, no defect. self_repair starts with `if not 0 <= i < len(words) - 1: return False` (transcript_truth.py:138), so j = -1 is never a self-repair. |
| K3 | A caller passing wav= without wav_start, with a file cut with the old 1.5 s pad, would misalign (glm P2-4, its condition 2) | VERIFIED, no such caller. The only explicit-wav caller, tests/package/run_given_package.py:268, passes wav_start from covering_wav(); the tests pass it; package.truth_for uses audio_window(). main's pipeline does not import transcript_truth (grep). |
| K4 | Does canon treat a bare "%" or "$", and hyphen splits, safely (glm P2-1 / condition 3, qwen P1-1)? | VERIFIED. canon_tokens("% of their portfolio") = ['percent', 'of', 'their', 'portfolio'], so a bare "%" never matches a clip's "25"; "$ 5 million" = ['5000000', 'dollars']. canon does NOT merge "Bit- coin" (['bit', 'coin']). That is a false negative the old 4-letter rule shares, and no regression: the canonical match only ADDS a candidate, it never removes one. |

## Refuted or kept (with evidence)

- **glm P1-1 (a recognised word inside the gap could be skipped):** REFUTED with data. gap = the opening word's start minus the end of ws[j], with j = i - 1 (or the word before a self-repair). With the recogniser's words in time order, no recognised word lies between them. All 99 recorded transcriptions in tests/package/fixtures/replies have their words in time order (0 out of order).
- **glm P2-2 (the canonical OR widens the candidate set; ci[0] is the earliest):** KEPT. A false earlier candidate needs the same canonical token within 0.6 s before the clip's first word. The old 4-letter rule had the same selection rule.

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0338/C2_STEP.diff (223 lines)
```
   1 | diff --git a/pipeline/transcript_truth.py b/pipeline/transcript_truth.py
   2 | index bfc8f44f..e002ec4b 100644
   3 | --- a/pipeline/transcript_truth.py
   4 | +++ b/pipeline/transcript_truth.py
   5 | @@ -22,14 +22,18 @@ NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neith
   6 |                         "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "shouldn't",
   7 |                         "wouldn't", "couldn't", "hasn't", "haven't", "hadn't"})
   8 |  _NUM = re.compile(r"^-?\d+(\.\d+)?$")
   9 | -PAD_S = 1.5
  10 | +PAD_S = 1.5                  # the audio fetched after the clip
  11 | +PAD_BEFORE_S = 4.0           # ruling 38 (03:12 ET Nov 13): the audio before the clip, so the recogniser hears the
  12 | +                             # sentence before it (1.5 s ended inside measured pauses: "the window starts at the clip")
  13 | +PAUSE_MIN_S = 0.700          # ruling 38: a measured pause this long with no recognised word also opens a clip
  14 | +CANON_RUN = 6                # recogniser words read together at an edge, so a spoken number is one canonical token
  15 |  
  16 |  
  17 | -def audio_window(video_id, start, end, out_dir, pad=PAD_S):
  18 | -    """WAV (16 kHz mono) of [start - pad, end + pad] (clamped at the video head), fetched with yt-dlp's download
  19 | -    sections -> (path, the window's real start in video seconds)."""
  20 | +def audio_window(video_id, start, end, out_dir, pad=PAD_S, pad_before=PAD_BEFORE_S):
  21 | +    """WAV (16 kHz mono) of [start - pad_before, end + pad] (clamped at the video head), fetched with yt-dlp's
  22 | +    download sections -> (path, the window's real start in video seconds)."""
  23 |      os.makedirs(out_dir, exist_ok=True)
  24 | -    a, b = max(0.0, start - pad), end + pad
  25 | +    a, b = max(0.0, start - pad_before), end + pad
  26 |      stem = f"{video_id}_{int(a * 1000)}_{int(b * 1000)}"
  27 |      base = os.path.join(out_dir, stem)
  28 |      wav = base + ".wav"
  29 | @@ -140,33 +144,63 @@ def self_repair(words, i, first):
  30 |              and fw.startswith(stem) and r.get("speaker") is not None and r.get("speaker") == f.get("speaker"))
  31 |  
  32 |  
  33 | +def _canon_from(ws, i):
  34 | +    """The first canonical token of the recogniser's words from i on (a spoken number read as one token, the L-v 2
  35 | +    canonicaliser: 'Twenty-five percent' -> '25')."""
  36 | +    c = canon.canon_tokens(" ".join(w.get("text") or "" for w in ws[i:i + CANON_RUN]))
  37 | +    return c[0] if c else None
  38 | +
  39 | +
  40 | +def _canon_to(ws, i):
  41 | +    """The last canonical token of the recogniser's words up to i ('to sixty-eight thousand.' -> '68000')."""
  42 | +    c = canon.canon_tokens(" ".join(w.get("text") or "" for w in ws[max(0, i - CANON_RUN + 1):i + 1]))
  43 | +    return c[-1] if c else None
  44 | +
  45 | +
  46 |  def edges(second, wav_start, start, end, text):
  47 |      """CUTTABLE (orchestrator 06:45 ruling C, ruling 7 (1)): the INDEPENDENT recogniser's own sentence boundaries at
  48 | -    the segment's edges, from its word timing on the SOURCE audio. IN: the recogniser's word at the clip's first word
  49 | -    (same word, within 0.6 s) follows a word ending in terminal punctuation. OUT: the recogniser's word at the clip's last
  50 | -    word (within 0.8 s) ends in terminal punctuation, and the recogniser heard a next word (it did not stop at the
  51 | -    window's edge). Store or caption punctuation is never evidence. -> {"cuttable", "in", "out"}."""
  52 | +    the segment's edges, from its word timing on the SOURCE audio. The clip's first / last word is found by its first
  53 | +    four letters OR by the L-v 2 canonicaliser on a short run of the recogniser's words (ruling 39: 'sixty-eight
  54 | +    thousand.' is the clip's '68,000.'). IN: the recogniser's word at the clip's first word (within 0.6 s) follows a
  55 | +    word ending in terminal punctuation; or (ruling 38) the recogniser heard no word for at least PAUSE_MIN_S before the
  56 | +    clip's opening word (a measured pause), or the window reaches the FILE HEAD and holds no word before the clip (the
  57 | +    clip opens on the file's first spoken word). OUT: the recogniser's word at the clip's last word (within 0.8 s) ends
  58 | +    in terminal punctuation, and the recogniser heard a next word (it did not stop at the window's edge). Store or
  59 | +    caption punctuation is never evidence. -> {"cuttable", "in", "out"}."""
  60 |      ws = [w for w in second.get("words") or [] if w.get("start") is not None]
  61 |      toks = re.findall(r"[\w'’$%.,-]+", re.sub(r"\s+\.(?=\w)", ".", text or ""))     # 'U .S.' is one word 'U.S.' 
  62 |      first, last = _w(toks[0]) if toks else "", _w(toks[-1]) if toks else ""
  63 | +    ct = canon.canon_tokens(text or "")
  64 | +    c_first, c_last = (ct[0], ct[-1]) if ct else (None, None)
  65 |      out = {"in": {"ok": False, "why": "no word timing from the recogniser"},
  66 |             "out": {"ok": False, "why": "no word timing from the recogniser"}}
  67 |      if not ws or not first:
  68 |          return dict(out, cuttable=False)
  69 |      t_in, t_out = start - wav_start, end - wav_start
  70 | -    ci = [i for i, w in enumerate(ws) if abs(float(w["start"]) - t_in) <= 0.6 and _w(w["text"]).startswith(first[:4])]
  71 | -    co = [i for i, w in enumerate(ws) if abs(float(w.get("end") or w["start"]) - t_out) <= 0.8
  72 | -          and _w(w["text"]).rstrip(".")[:4] == last.rstrip(".")[:4]]
  73 | +    ci = [i for i, w in enumerate(ws) if abs(float(w["start"]) - t_in) <= 0.6 and
  74 | +          (_w(w["text"]).startswith(first[:4]) or (c_first is not None and _canon_from(ws, i) == c_first))]
  75 | +    co = [i for i, w in enumerate(ws) if abs(float(w.get("end") or w["start"]) - t_out) <= 0.8 and
  76 | +          (_w(w["text"]).rstrip(".")[:4] == last.rstrip(".")[:4] or (c_last is not None and _canon_to(ws, i) == c_last))]
  77 |      if ci:
  78 |          i = ci[0]
  79 |          j, repair = i - 1, None
  80 |          if self_repair(ws, j, first):           # ruling 8: the speaker's false start opens the sentence
  81 |              repair, j = ws[j]["text"], j - 1
  82 |          prev = ws[j]["text"] if j >= 0 else None
  83 | -        out["in"] = {"ok": prev is not None and prev.rstrip().endswith(TERMINAL), "word": ws[i]["text"],
  84 | -                     "before": prev, "why": "a sentence ends before the clip" if prev and prev.rstrip().endswith(TERMINAL)
  85 | -                     else ("the window starts at the clip: no word before it" if prev is None else
  86 | -                           f"the recogniser runs on into the clip ('{prev}')")}
  87 | +        t_open = float(ws[j + 1]["start"])      # the clip's opening word (its self-repair, when there is one)
  88 | +        gap = t_open - (float(ws[j].get("end") or ws[j]["start"]) if j >= 0 else 0.0)   # no word before: from the
  89 | +        ends = prev is not None and prev.rstrip().endswith(TERMINAL)                     # window's start
  90 | +        head = prev is None and wav_start <= 0.0
  91 | +        pause = gap >= PAUSE_MIN_S - 1e-9
  92 | +        out["in"] = {"ok": ends or pause or head, "word": ws[i]["text"], "before": prev,
  93 | +                     "pause_ms": int(round(gap * 1000)),
  94 | +                     "why": "a sentence ends before the clip" if ends else
  95 | +                     ("the clip opens on the file's first spoken word (the window reaches the file head and holds no "
  96 | +                      "word before it, ruling 38)" if head else
  97 | +                      (f"a measured pause of {gap * 1000:.0f} ms with no recognised word before the clip "
  98 | +                       f"(>= {PAUSE_MIN_S * 1000:.0f} ms, ruling 38)" if pause else
  99 | +                       ("the window starts at the clip: no word before it" if prev is None else
 100 | +                        f"the recogniser runs on into the clip ('{prev}', {gap * 1000:.0f} ms before it)")))}
 101 |          if repair:
 102 |              out["in"].update(self_repair=repair, why=out["in"]["why"] + f"; the speaker's false start '{repair}' "
 103 |                               "opens the sentence (ruling 8: a self-repair, part of the sentence)")
 104 | @@ -191,7 +225,7 @@ def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_s
 105 |      if wav is None:
 106 |          wav, wav_start = audio_window(video_id, start, end, work_dir)
 107 |      sec, rep = second_pass(router, wav)
 108 | -    off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_S))
 109 | +    off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S))
 110 |      span = span_text(sec, off, off + (end - start)) or sec["text"]
 111 |      sw = [w for w in sec.get("words") or [] if _inside(w, off, off + (end - start))]
 112 |      toks = re.findall(r"[\w'’$%.,-]+", text or "")
 113 | @@ -203,5 +237,6 @@ def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_s
 114 |      return {"video_id": video_id, "start": start, "end": end, "model": rep.backend, "replayed": rep.replayed,
 115 |              "second_pass_text": span, "self_repair": repair, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
 116 |              "critical": cmp_["critical"], "speakers": turns, "audio": os.path.basename(wav),
 117 | -            "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_S), start, end, text),
 118 | +            "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S), start, end,
 119 | +                           text),
 120 |              "ok": cmp_["ok"] and turns["turn_change_inside"] is False}
 121 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 122 | index 60a9f85a..3c5b64b4 100644
 123 | --- a/tests/package/test_angles.py
 124 | +++ b/tests/package/test_angles.py
 125 | @@ -330,6 +330,97 @@ class TestInventory(unittest.TestCase):
 126 |          self.assertFalse(t["ok"])
 127 |  
 128 |  
 129 | +class TestEdgesRulings38And39(unittest.TestCase):
 130 | +    """Rulings 38 and 39 (03:12 ET Nov 13). The L-v 2 window reaches PAD_BEFORE_S = 4 s before the clip. The IN edge
 131 | +    opens on a recognised sentence end, OR a measured pause of >= 700 ms with no recognised word before the clip's
 132 | +    opening word, OR the file's first spoken word (the window reaches the file head and holds no word before it). The
 133 | +    edge matcher reads a short run of recogniser words with the L-v 2 canonicaliser, so a spoken number matches the
 134 | +    clip's digits."""
 135 | +
 136 | +    TEXT = "Bitcoin is money for everyone."
 137 | +
 138 | +    def ws(self, before, first_at, text=None, after="Next.", step=0.3):
 139 | +        out = [dict(w, speaker="s0") for w in before]
 140 | +        words = (text or self.TEXT).split()
 141 | +        out += [{"text": t, "start": first_at + step * k, "end": first_at + step * k + 0.22, "speaker": "s0"}
 142 | +                for k, t in enumerate(words)]
 143 | +        end = first_at + step * (len(words) - 1) + 0.22
 144 | +        return out + [{"text": after, "start": end + 0.5, "end": end + 0.8, "speaker": "s0"}], end
 145 | +
 146 | +    def edges(self, before, first_at, wav_start=2.0, text=None, after="Next."):
 147 | +        ws, end = self.ws(before, first_at, text, after)
 148 | +        return TT.edges({"words": ws}, wav_start, wav_start + first_at, wav_start + end, text or self.TEXT)
 149 | +
 150 | +    def test_a_measured_pause_of_700_ms_opens_the_clip_and_less_does_not(self):
 151 | +        e = self.edges([{"text": "and", "start": 0.40, "end": 0.80}], 1.55)          # 750 ms after a non-ending word
 152 | +        self.assertTrue(e["in"]["ok"], e["in"])
 153 | +        self.assertIn("measured pause of 750 ms", e["in"]["why"])
 154 | +        self.assertEqual(e["in"]["pause_ms"], 750)
 155 | +        e = self.edges([{"text": "and", "start": 0.40, "end": 0.80}], 1.45)          # 650 ms
 156 | +        self.assertFalse(e["in"]["ok"], e["in"])
 157 | +        self.assertIn("runs on into the clip ('and', 650 ms", e["in"]["why"])
 158 | +        e = self.edges([{"text": "path.", "start": 0.40, "end": 0.80}], 0.95)        # a sentence end needs no pause
 159 | +        self.assertTrue(e["in"]["ok"])
 160 | +        self.assertEqual(e["in"]["why"], "a sentence ends before the clip")
 161 | +
 162 | +    def test_the_files_first_spoken_word_opens_and_a_window_that_starts_at_the_clip_does_not(self):
 163 | +        e = self.edges([], 0.30, wav_start=0.0)                       # the window reaches the file head, no word
 164 | +        self.assertTrue(e["in"]["ok"], e["in"])
 165 | +        self.assertIn("file's first spoken word", e["in"]["why"])
 166 | +        e = self.edges([], 0.30, wav_start=2.0)                       # not the file head: 300 ms measured, no pause
 167 | +        self.assertFalse(e["in"]["ok"], e["in"])
 168 | +        self.assertEqual(e["in"]["why"], "the window starts at the clip: no word before it")
 169 | +        e = self.edges([], 1.00, wav_start=2.0)                       # 1000 ms with no recognised word: a pause
 170 | +        self.assertTrue(e["in"]["ok"], e["in"])
 171 | +        self.assertIn("measured pause of 1000 ms", e["in"]["why"])
 172 | +
 173 | +    def test_a_self_repair_opens_the_clip_and_the_pause_is_measured_before_it(self):
 174 | +        ws = [{"text": "and", "start": 0.10, "end": 0.40, "speaker": "s0"},
 175 | +              {"text": "Bit-", "start": 1.20, "end": 1.30, "speaker": "s0"}]       # 800 ms before the false start
 176 | +        e = self.edges(ws, 1.50)
 177 | +        self.assertTrue(e["in"]["ok"], e["in"])
 178 | +        self.assertEqual((e["in"]["self_repair"], e["in"]["pause_ms"]), ("Bit-", 800))
 179 | +
 180 | +    def test_the_window_reaches_4_s_before_the_clip_and_stops_at_the_file_head(self):
 181 | +        import tempfile
 182 | +        self.assertEqual((TT.PAD_BEFORE_S, TT.PAD_S, TT.PAUSE_MIN_S), (4.0, 1.5, 0.7))
 183 | +        with tempfile.TemporaryDirectory() as d:
 184 | +            for start, end, stem, a in ((10.0, 20.0, "v_6000_21500", 6.0), (2.35, 11.81, "v_0_13310", 0.0)):
 185 | +                open(os.path.join(d, stem + ".wav"), "w").close()          # cached: no fetch
 186 | +                self.assertEqual(TT.audio_window("v", start, end, d), (os.path.join(d, stem + ".wav"), a))
 187 | +
 188 | +    def test_a_spoken_number_matches_the_clips_digits_at_both_edges(self):
 189 | +        text = "Bitcoin is down around 67 to 68,000."
 190 | +        spoken = "Bitcoin is down around sixty-seven to sixty-eight thousand."
 191 | +        ws, end = self.ws([{"text": "real.", "start": 0.2, "end": 0.6}], 1.4, text=spoken, after="James")
 192 | +        e = TT.edges({"words": ws}, 2.0, 3.4, 2.0 + end, text)
 193 | +        self.assertTrue(e["out"]["ok"], e["out"])                   # the 02:37 build's lost OUT edge
 194 | +        self.assertEqual((e["out"]["word"], e["out"]["after"]), ("thousand.", "James"))
 195 | +        self.assertTrue(e["cuttable"])
 196 | +        text2 = "25 % of their portfolio is Bitcoin."
 197 | +        ws2, end2 = self.ws([{"text": "now.", "start": 0.2, "end": 0.6}], 1.4,
 198 | +                            text="Twenty-five percent of their portfolio is Bitcoin.")
 199 | +        e2 = TT.edges({"words": ws2}, 2.0, 3.4, 2.0 + end2, text2)
 200 | +        self.assertTrue(e2["in"]["ok"], e2["in"])
 201 | +        self.assertEqual(e2["in"]["word"], "Twenty-five")
 202 | +        e3 = TT.edges({"words": ws2}, 2.0, 3.4, 2.0 + end2, "26 % of their portfolio is Bitcoin.")
 203 | +        self.assertFalse(e3["in"]["ok"])                              # another number never matches
 204 | +
 205 | +    def test_verify_segment_reads_the_edges_against_the_new_window(self):
 206 | +        class R:
 207 | +            def __init__(self, ws):
 208 | +                self.ws = ws
 209 | +
 210 | +            def transcribe(self, role, wav):
 211 | +                return {"text": " ".join(w["text"] for w in self.ws), "segments": [], "words": self.ws}, \
 212 | +                    type("Rep", (), {"backend": "s", "replayed": False})()
 213 | +        ws, end = self.ws([{"text": "and", "start": 3.00, "end": 3.20}], 4.0)       # a 4 s pre-pad; 800 ms pause
 214 | +        t = TT.verify_segment(R(ws), "v", 10.0, 6.0 + end, self.TEXT, "/nonexistent", wav="w.wav", wav_start=6.0)
 215 | +        self.assertTrue(t["edges"]["cuttable"], t["edges"])
 216 | +        self.assertEqual(t["edges"]["in"]["pause_ms"], 800)
 217 | +        self.assertTrue(t["ok"], t)
 218 | +
 219 | +
 220 |  class TestMajorityOnce(unittest.TestCase):
 221 |      def test_once_then_the_majority_only_when_the_first_run_fails(self):
 222 |          """08:18 item 4 / 08:29: a model verdict that passes its first run runs once; one that does not gets the
 223 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
pipeline/transcript_truth.py runs law L-v 2 on every selected clip: a SECOND, independent recogniser (scribe, with
word timing and diarisation) transcribes the SOURCE audio around the clip. Its edges() is CUTTABLE (orchestrator
rulings C / 7):
- the clip's IN must follow the independent recogniser's own sentence end;
- the clip's OUT must end on one, with a next word heard after it.
Store or caption punctuation is never evidence.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why (orchestrator rulings 03:12 ET Nov 13, from the measured funnel of the 02:37 build):
- 38. IN edge "no word before it": measure a longer window before the clip (pad 4 s). "The acceptance rule is
  unchanged: the independent recogniser must show a sentence end before the clip, or a measured pause of at least
  700 ms with no speech. A clip that starts at the first spoken word of the file counts as a sentence start when the
  window reaches the file head and holds no speech."
  - Measured: 3 of the build's 5 stage-3 losses were IN edges where the 1.5 s window ended inside a pause. The audio
    there was -54 to -59 dBFS for ~1.0 s, and the recogniser heard no word. One clip was an episode's first words
    (2.35 s into the file).
- 39. OUT edge number match (K2, a defect): the edge matcher uses the same number canonicaliser as L-v 2.
  - Measured: the primary's "…67 to 68,000." vs the recogniser's "…sixty-seven to sixty-eight thousand." ending at
    9.48 s (the clip ends at 9.44 s), next word "James". The matcher compared the first 4 letters ("thou" vs "6800")
    and lost a clean sentence end. L-v 2's own comparison canonicalises and had passed the clip.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. The two acceptance additions here (the 700 ms
  pause and the file head) are the orchestrator's own ruling 38, quoted above.

The change (pipeline/transcript_truth.py):
1. PAD_BEFORE_S = 4.0. audio_window() fetches [start - 4.0, end + 1.5] (PAD_S after, unchanged), clamped at the file
   head. verify_segment's fallbacks use PAD_BEFORE_S. The WAV's name holds its bounds, so new windows are new files
   and new recogniser calls.
2. edges() IN: the clip's opening word (its ruling-8 self-repair when there is one) is accepted when:
   (a) the recogniser's word before it ends in terminal punctuation (unchanged); or
   (b) gap >= PAUSE_MIN_S = 0.700 s, where gap = the opening word's start minus the previous recognised word's end
       (no recognised word in between, by construction); with no recognised word before it in the window, the gap is
       measured from the window's start; or
   (c) the window reaches the file head (wav_start <= 0) and holds no recognised word before the clip.
   The record adds pause_ms and a reason for each case. Everything else in the IN and OUT logic is unchanged.
3. edges() matching (ruling 39): the clip's first / last word is found by the old 4-letter rule OR by canon.canon_tokens
   (the L-v 2 canonicaliser) on a run of up to CANON_RUN = 6 recogniser words starting at (IN) / ending at (OUT) the
   candidate word, compared with the clip text's first / last canonical token. The time windows (0.6 s IN, 0.8 s OUT)
   are unchanged.
4. tests/package/test_angles.py, new class TestEdgesRulings38And39:
   - the 750 / 650 ms boundary;
   - a sentence end needs no pause;
   - the file head vs a window that starts at the clip, and a 1000 ms no-word stretch;
   - a self-repair (the pause is measured before it);
   - audio_window's 4 s pre-pad and the clamp at the file head (cached files, no network);
   - the spoken-number match at OUT ("thousand." + "James") and at IN ("Twenty-five percent" = "25 %"), and a
     different number never matching;
   - verify_segment end to end.

Check in particular:
- that (b) and (c) cannot pass a clip whose opening word FOLLOWS a recognised word by less than 700 ms;
- whether measuring the pause on the recogniser's word timing alone is enough for "a measured pause ... with no
  speech", or whether speech the recogniser missed could pass. Say what you can verify;
- that the canonical match cannot match a DIFFERENT word or number at an edge (a run reaching another number, a
  repeated word);
- off-by-one and index errors in the run slicing (ws[i:i+6], ws[i-5:i+1]) and in j / j+1 with a self-repair;
- that nothing else that the OUT rule or L-v 2's compare / speaker checks accept has changed.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".


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
