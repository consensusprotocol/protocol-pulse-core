# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1545
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 77 s finish=stop usage in 13581 / out 2209 usd~0.074 (upper-bound price)

# Audit: pp-selectid-1545 — speakers.py ruling 69/70

## P0

None found. Every naming path I traced requires the turn structure plus a code-verified address or self-introduction; I could not construct a scenario where a name lands on less.

## P1

**P1-1 — `turn_of` backchannel merge can chain across multiple interjections and join genuinely different speakers.**
`pipeline/speakers.py:127-135` (diff lines). The while-loops merge *every* gap of ≤3 words, repeatedly, in both directions. Scenario: A speaks, B interjects "Yeah." (1 word), A continues, then B interjects "Right." (1 word), then B actually takes the floor with a 3-word question, then A resumes. All gaps are ≤3 words, so all are merged into one "turn of A" — but the 3-word B question is now inside A's turn, and the model may quote it as A's address/self-intro. `check_turn` verifies the quote is *in the turn* and *holds a name*, but nothing verifies the quoted words are on A's side of a marker (they can't be — the markers were consumed). The ruling says "at most BACKCHANNEL_WORDS words" for *an* interjection; chaining N interjections plus a 3-word floor-taking is a defensible but stronger reading. Concrete risk: a wrong name sealed in the pin — exactly the failure mode this review guards. Mitigation exists (conflict → "unknown"), but only when the basis rule independently disagrees. **Say so if you read the ruling as permitting chains; the test only exercises one interjection.**

**P1-2 — `decide()` address rule: `others` computed but the two-people constraint can pass with the addressed person not among `people`.**
`pipeline/speakers.py:174-177`. `others = [p for p in people if _norm(p["name"]) != _norm(turn_ev["address"]["name"])]`. If `check_turn` kept the address, the addressed person *is* in `people` (it's checked there), so this is safe — but only via that coupling. If `check_turn`'s `who` lookup and `decide`'s ever diverge (e.g. one uses `_within`, the other `_norm` equality — they do: `check_turn` matches the *model's* name string to a person by `_norm` equality, while the lower-third path at line 187 uses `_within` per word), the invariant "addressed ∈ people" is implicit, not enforced in `decide`. Currently consistent; flagging as fragile, not broken.

**P1-3 — `captions()` returns the first store with *any* marker, not the best copy.**
`pipeline/speakers.py:84-105`. If the main tree holds a truncated/partial `transcript.yt_auto.json` that happens to contain one stray `>>` (e.g. from a description leak into the caption text), it wins over pp-ingest's complete copy. The `if any(u[2] for u in units)` guard only checks ≥1 marker exists. No completeness check (e.g. last unit's time vs. video duration). For the 13:38 pin this is fine; for a live episode where the main tree's copy is a partial ingest, the turn could be silently truncated and `turn_of` returns "no speaker-change marker before the clip" — fail-closed, so it's a P1 not P0. But a *partial* copy that has the clip's turn but misses a later marker yields a too-long turn, which only risks prompt bloat (TURN_MAX_CHARS cuts it). Downgrade-able to P2 if you trust the store discipline.

## P2

**P2-1 — Marker-inside-clip tolerance uses the same `tol` for both edges asymmetrically.**
`pipeline/speakers.py:116`: `start + tol < units[i][0] < end - tol`. A marker at exactly `start + 0.5` (the caption's *display* start, not the word onset) is treated as outside the clip. Since caption timings are display times and the clip bounds are word timings, a 0.5 s tolerance is a guess. If a marker legitimately falls at 0.6 s inside the clip (the clip catches the tail of the previous speaker's "Yeah"), the whole turn evidence is refused — fail-closed, "unknown" where ruling 69 would name. Conservative, acceptable, but note it.

**P2-2 — `check_turn` name-word match: `len(w) > 1` drops single-letter name words.**
`pipeline/speakers.py:160`. A person recorded as "A. Smith" (line: "A. Smith joins...") — the token "a" (after `_norm` presumably lowercases) is 1 char and excluded. If the *only* name word in the quote is the initial, the evidence is dropped. Edge case; TWO-people test data uses full names. Also: the same filter at line 187 uses `len(w) > 2`, so a 2-letter name word ("Bo") works in `check_turn` but not in the lower-third match. Inconsistent thresholds, no stated reason.

**P2-3 — `decide()` lower-third agreement appends to `basis` but the earlier conflict path (line 182-183) returns before the lower-third is consulted.**
`pipeline/speakers.py:181-193`. When the basis rule and the turn rule disagree, the function returns early with "unknown" and the lower third — which might have adjudicated (ruling 70: "one more piece of evidence") — is never read. Reading ruling 70 as "one more piece of evidence" suggests it *could* break a tie. Your K4 says "confirm or veto, never make" — under K4 the 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 153 s finish=stop usage in 13549 / out 617 usd~0.083 (upper-bound price)

**P1: pipeline/speakers.py:102** (inside `captions` for-loop): `float(s["start"])` (and subsequent logic) can raise `KeyError` (absent key) or `TypeError` not covered by the narrow `except (OSError, ValueError, AttributeError): continue` at lines 90-91. This executes *before* the `try` in `attribute` (~223) and outside the narrow `try`/`except KeyError` in `attribute_package` (~245-256), so the exception propagates and aborts the entire package build instead of falling back to no-turn/unknown-speaker. Concrete scenario: any `transcript.yt_auto.json` (main or INGEST_STORE) containing a segment dict lacking a `"start"` key or with a non-numeric value.

**P2: pipeline/speakers.py:139-142** (`turn_of`, the `if len(text) > TURN_MAX_CHARS` block): `text = text[a0:a0 + TURN_MAX_CHARS]` slices the joined string at arbitrary character offsets derived from `len(" ".join(...))`; this can split words mid-token in the prompt (e.g. prompt receives `"telligent, Scott?"` or `"super intelli"`). The `mid` calculation and `TURN_MAX_CHARS=12000` make it rare, but the code path exists and is untested. (The recorded `"start"`/`"end"` remain the unsliced values, so evidence mismatches what the model actually saw.)

**P2: pipeline/speakers.py:217-221 & 228** (`attribute`): `turn, turn_why = turn_of(...) if units else ...` and the subsequent `turn["text"]` / `turn["start"]` accesses occur before the `try` that wraps the model call and `check`/`decide`. A `turn_of` exception (e.g. empty `units` edge cases or bad timestamps) therefore bypasses the measured=False fallback and the `rec["turn"] = {...}` recording that the tests rely on. (The test suite only exercises happy-path `units`.)

No other violations of the supplied ruling text, K1-K4, backchannel-merge logic, marker parsing, prompt construction, conflict rules, lower-third veto, verbatim-quote checks, or HTML-unescape/rolling-repeat handling are visible in the diff. All added test cases in `TestRuling69Turn` pass against the supplied CAPS fixture and match the orchestrator's accepted reading of the 945.28 address across the "Yeah." backchannel. The existing `_norm`/`_within` helpers are assumed to route through `canon.py` per L-k (not altered here).

**SHIP: yes with conditions** (add broad `except Exception` or enlarge the inner try in `captions` to guarantee fallback; add a malformed-JSON test; confirm `_within`/`BASIS_MIN_WORDS` definitions are unchanged and canon-based).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 49 s finish=stop usage in 14871 / out 1590 usd~0.068 (upper-bound price)

# Audit: pp-selectid-1545 / C1_STEP (Ruling 69 — Speaker Attribution via Caption Turns)

## P0 Findings (Blockers)

**None.** The core logic correctly implements the "fail-closed" requirement. A wrong name is prevented by the `decide()` function, which forces `unknown` if the turn evidence conflicts with the basis rule, or if the lower third contradicts the decision. The "address" logic correctly requires exactly two people to infer the speaker by elimination.

## P1 Findings (Major Issues)

### 1. `turn_of` Backchannel Merge Logic is Fragile and Potentially Incorrect
**File:** `pipeline/speakers.py`, lines 127-135 (in diff)
**Scenario:** The logic for merging across backchannels assumes that if a segment between two markers is short (<= 3 words), it is a backchannel from the *other* speaker, and the speaker before and after is the *same*.
```python
while b < len(units) and nxt(b) < len(units) and words(b, nxt(b)) <= bc:   # A | b: B's interjection | A again
    skipped.append(" ".join(units[k][1] for k in range(b, nxt(b))))
    spans.append((nxt(b), nxt(nxt(b))))
    b = nxt(nxt(b))
```
**Issue:** This logic blindly merges across *any* short segment between markers. It does not verify that the speaker *before* the short segment is the same as the speaker *after* it. In a fast-paced conversation, Speaker A might say a 2-word phrase, then Speaker B might say a 2-word phrase, then Speaker A might speak again. The code would merge A's first phrase, B's phrase, and A's second phrase into one "turn" of A, effectively attributing B's words to A's turn context. While the *attribution* of the clip itself might still be correct if the clip is in A's part, the `turn_text` provided to the LLM will contain B's words as if they were part of A's turn. This could confuse the LLM or lead to a false positive if B's words contain a name that matches a person in the source lines.
**Recommendation:** The merge logic should be more conservative. It should only merge if the *next* marker after the short segment is followed by content that is clearly a continuation of the previous speaker (e.g., similar topic, or if the short segment is a known backchannel like "Yeah", "Mm-hm"). Alternatively, do not merge at all, and let the LLM handle the context, or require a higher confidence threshold for merging.

### 2. `captions` Function Does Not Validate Timestamps
**File:** `pipeline/speakers.py`, lines 79-105 (in diff)
**Scenario:** The `captions` function reads `transcript.yt_auto.json` and extracts `start` times. It does not validate that the timestamps are monotonically increasing or that they are within a reasonable range.
**Issue:** If the caption file is corrupted or has out-of-order timestamps, `turn_of` will fail or produce incorrect results. For example, if a later caption has an earlier timestamp, the `before` and `nxt` logic in `turn_of` will break.
**Recommendation:** Add validation to ensure timestamps are monotonically increasing. If not, fail closed (return `None, None`).

### 3. `check_turn` Does Not Verify the Quote is in the *Correct* Part of the Turn
**File:** `pipeline/speakers.py`, lines 146-162 (in diff)
**Scenario:** The `check_turn` function verifies that the quote is verbatim in the `turn_text`. However, it does not verify that the quote is in the part of the turn *spoken by the speaker being attributed*.
**Issue:** If the turn contains words from multiple speakers (due to the backchannel merge issue in P1-1), a quote from Speaker B could be used to attribute Speaker A. For example, if Speaker B says "I'm Mark Yusko" in a backchannel, and the code merges it into Speaker A's turn, the LLM might quote it, and `check_turn` would accept it, attributing the clip to Mark Yusko even though Speaker A was speaking.
**Recommendation:** The `check_turn` function should verify that the quote is in the part of the turn that is *not* a backchannel. Alternatively, the backchannel merge should be removed, and the LLM should be given the full context with markers, and the code should verify that the quote is in a segment that is *not* marked as a backchannel.

## P2 Findings (Minor Issues)

### 1. `TURN_MAX_CHARS` Cut May Lose Context
**File:** `pipeline/speakers.py`, lines 138-142 (in diff)
**Scenario:** If the turn is longer than `TURN_MAX_CHARS` (12000), it is cut around the clip.
**Issue:** The cut is done by character count, not by word count. This may cut in the middle of a word or sentence, losing context.
**Recommendation:** Cut by word count, and ensure the cut does not split a word.

### 2. `MARKER_TOL_S` May Be Too Large
**File:** `pipeline/speakers.py`, line 38 (in diff)
**Scenario:** `MARKER_TOL_S` is 0.5 seconds.
**Issue:** If a marker is 0.4 seconds before the clip start, it is considered "before" the clip. If a marker is 0.4 seconds after the clip end, it is considered "after" the clip. This may be too lar

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1545 (RULING 69: the speaker attribution reads the caption turn): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes with conditions": P1, a malformed caption record could crash the package.
  - glm: "SHIP: yes with conditions": P1-1 chained merges, P1-2, P1-3.
  - qwen: "SHIP: No", on P1-1 to P1-3.
- No P0. Three consensus items are applied before cycle 2.

## Applied

| # | finding | the change |
|---|---|---|
| C1 | The backchannel merge is too loose: any <= 3 words between markers was skipped, so a SHORT FLOOR-TAKING line by the other speaker ("Mark, why?"), or a marker misfire, could join two speakers (qwen P1-1, P2-3; glm P1-1) | An interjection now continues a turn only when it is <= 3 words AND every word is a backchannel token (BACKCHANNEL: yeah, yes, right, okay, sure, mm, mhm, uh-huh, exactly, wow...). Anything else ends the turn. Test: test_only_a_backchannel_continues_a_turn_and_a_bad_record_is_skipped. The real 945.28 case still reads: the turn is 696.24-953.52 across "Yeah.", and holds the address. |
| C2 | A malformed caption record (a segment without "start", a non-numeric time, times out of order) raised outside any guard and could abort the whole package (grok P1, P2; qwen P1-2) | captions() parses inside a guard: a missing or non-numeric start, a NaN, or a time earlier than the one before skips that store, which is the same as having no markers. attribute() reads the turn inside a guard ("the caption turn could not be read: ...", still measured). attribute_package guards captions_for. Tests: an out-of-order store and a store without "start" are skipped; a bad clip time gives a recorded why, no crash. |
| C3 | The cut of a turn longer than TURN_MAX_CHARS could split words (grok P2, qwen P2-1; glm asks for a test) | The cut moves to word boundaries on both sides. Test: test_a_long_turn_is_cut_on_word_boundaries_around_the_clip (the clip's words kept, no word split, within the limit). |

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P1-3: a quote from a backchannel could be attributed to the turn's speaker | turn_of builds the turn text from `spans` only. Each skipped interjection [b, nxt(b)) is appended to `backchannels` and never to `spans`, so its words are not in turn["text"]. check_turn keeps a quote only if _within(quote, turn_text). The test asserts "Tell that to his wife" is not in the turn text. |
| R2 | glm P1-2: decide() could accept an address to a person not among the people | check_turn keeps an address only when `who` (the person, by _norm equality) is in people. decide() then names the other of exactly two; with any other count it names no one. The invariant is enforced where the evidence is admitted. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-3: the first store with any marker wins over a fuller copy | That fails closed: a copy without the clip's turn markers gives "no marker before the clip", or a long

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1545/C2_STEP.diff (427 lines)
```
   1 | diff --git a/pipeline/speakers.py b/pipeline/speakers.py
   2 | index 4bd16b6..30cc69a 100644
   3 | --- a/pipeline/speakers.py
   4 | +++ b/pipeline/speakers.py
   5 | @@ -18,12 +18,24 @@ Evidence is text, and code checks it:
   6 |    A source line alone never names a clip's speaker: a title that names a guest does not show who speaks a given
   7 |    clip. Otherwise the speaker is "unknown", with why, and every person the source names is still listed (people) for
   8 |    tagging.
   9 | --> the segment's "speaker": {"name", "role", "line", "basis", "why", "people", "measured", "backend", "replayed"}.
  10 | +RULING 69 (orchestrator 15:29 Nov 13): "the attribution step reads the caption turn markers and addresses by name
  11 | +across the whole turn that contains the clip, not only the windows around it; a speaker is named when the turn
  12 | +structure plus one address or self-introduction shows it." captions() reads the episode's caption record with its
  13 | +speaker-change markers ('>>'); turn_of() finds, in code, the ONE turn that holds the clip (no marker inside it), across
  14 | +another person's interjections of at most BACKCHANNEL_WORDS words (A, a one-word "Yeah." by B, A again: one turn of A).
  15 | +The verdict quotes any address by name and any self-introduction inside that turn; check_turn() keeps one only when its
  16 | +quote is verbatim in the turn and holds a name of one of the people. A self-introduction names its speaker; an address
  17 | +names the OTHER person only when the source's lines name exactly two people. A lower third (ruling 70) is one more
  18 | +piece of evidence, never alone: it names nobody by itself, and one that contradicts the decision makes it "unknown".
  19 | +-> the segment's "speaker": {"name", "role", "line", "basis", "why", "people", "measured", "backend", "replayed",
  20 | +"turn" (ruling 69's evidence, when a caption turn was read)}.
  21 |  "people" means named in the source's own lines. Code verifies that the name is in the line it cites; the role
  22 |  (host / guest / other) is the verdict's reading of that line, shown beside it for the reader (audit 0007 C1 K3: qwen,
  23 |  glm). A call that fails is retried once with a new seed; a second failure stays "unknown" with measured false, which
  24 |  claims no name (audit 0007 C1 K2).
  25 |  """
  26 | +import hashlib
  27 | +import html
  28 |  import json
  29 |  import os
  30 |  import re
  31 | @@ -37,6 +49,12 @@ MAX_DESCRIPTION_LINES = 60
  32 |  ROLES = ("host", "guest", "other")
  33 |  UNKNOWN = "unknown"
  34 |  STORE = os.path.join(os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse"), "data", "editorial")
  35 | +INGEST_STORE = os.path.join(os.environ.get("PP_INGEST", "/home/ultron/worktrees/pp-ingest"), "data", "editorial")
  36 | +BACKCHANNEL_WORDS = 3                     # ruling 69: another person's interjection this short does not end a turn,
  37 | +BACKCHANNEL = frozenset("""yeah yes yep yup right okay ok sure mm mhm hmm uh-huh mm-hmm exactly absolutely totally
  38 | +wow true indeed correct no nope oh ah huh""".split())    # when every word of it is one of these (audit 1545 C1)
  39 | +TURN_MAX_CHARS = 12000                    # the turn shown to the verdict (a longer one is cut around the clip)
  40 | +MARKER_TOL_S = 0.5                        # caption lines carry their display time: a marker this near an edge is it
  41 |  
  42 |  PROMPT = """You identify who is SPEAKING in one clip of a Bitcoin video, so the people in it can be credited and tagged.
  43 |  
  44 | @@ -49,6 +67,10 @@ THE SOURCE'S OWN LINES (its title, its channel and its description, one per line
  45 |  THE TRANSCRIPT AROUND THE CLIP (the clip is between <clip> and </clip>; speaker turns are not marked):
  46 |  {context}
  47 |  
  48 | +THE CLIP'S TURN (from the episode's own captions, whose markers show where the speaker changes; the clip lies inside
  49 | +this one turn of ONE speaker, other people's interjections of at most three words left out):
  50 | +{turn}
  51 | +
  52 |  Do this:
  53 |  1. List every person these source lines name who appears in the video (host, guest or other), each with the ONE
  54 |     source line that names them, copied character for character.
  55 | @@ -58,6 +80,10 @@ Do this:
  56 |     Copy the exact words from the clip or the transcript around it that show it (the basis, at least three words).
  57 |     A title or description that names a guest does NOT show who speaks a given clip. If nothing in the transcript
  58 |     shows it, the speaker is "unknown", and "why" says what is missing.
  59 | +3. In THE CLIP'S TURN only (when one is given), find: (a) an ADDRESS BY NAME, where the speaker of the turn speaks TO one
  60 | +   of the people by name ("..., Scott?", "Mark, what do you think"), not merely about them; (b) a SELF-INTRODUCTION,
  61 | +   where the speaker of the turn names themself ("I'm Mark Yusko", "this is Natalie"). For each, copy at least three
  62 | +   exact words from the turn holding the name, and give the person as listed in step 1. None found: null.
  63 |  
  64 |  Example: an interview whose title names a guest, where the clip and the transcript around it hold no name, no
  65 |  first-person tie and no address -> "speaker": {{"name": "unknown", "basis": "", "why": "both the host and the guest
  66 | @@ -66,7 +92,9 @@ speak in this episode, and nothing in or around the clip shows which one this is
  67 |  Return ONLY this JSON object:
  68 |  {{"people": [{{"name": "...", "role": "host|guest|other", "line": "..."}}],
  69 |   "speaker": {{"name": "<one of the people, or unknown>", "basis": "<exact words from the transcript, or empty>",
  70 | - "why": "..."}}}}
  71 | + "why": "..."}},
  72 | + "turn": {{"address": {{"name": "<the person addressed>", "quote": "<exact words>"}} or null,
  73 | +          "self_intro": {{"name": "<the person>", "quote": "<exact words>"}} or null}}}}
  74 |  
  75 |  Remember: copy every line and the basis exactly; "unknown" whenever the transcript does not show who speaks."""
  76 |  
  77 | @@ -117,6 +145,137 @@ def context(src, k0, k1, before=CONTEXT_BEFORE, after=CONTEXT_AFTER):
  78 |      return say(a, k0 - 1), say(k0, k1), say(k1 + 1, b)
  79 |  
  80 |  
  81 | +def captions(video_id, stores=None):
  82 | +    """RULING 69: the episode's caption record WITH speaker-change markers ('>>'): transcript.yt_auto.json from the
  83 | +    first store whose copy carries any (the main tree's, then pp-ingest's: a live episode's captions arrive later).
  84 | +    -> ([(t, text, opens_turn)] in caption order, {"file", "sha256"}), or (None, None). Rolling repeats of a line are
  85 | +    read once; a '>>' inside a line opens a turn there."""
  86 | +    for st in stores or (STORE, INGEST_STORE):
  87 | +        p = os.path.join(st, "transcripts", video_id, "transcript.yt_auto.json")
  88 | +        try:
  89 | +            with open(p, "rb") as f:
  90 | +                raw = f.read()
  91 | +            segs = json.loads(raw).get("segments") or []
  92 | +        except (OSError, ValueError, AttributeError):
  93 | +            continue
  94 | +        units, last, pending = [], None, False
  95 | +        try:                                          # audit 1545 C1: a malformed record is skipped, never a crash
  96 | +            for s in segs:
  97 | +                t = html.unescape(str(s.get("text") or "")).strip()
  98 | +                if not t or t == last:
  99 | +                    continue
 100 | +                last, t0 = t, float(s["start"])
 101 | +                if t0 != t0 or (units and t0 < units[-1][0]):      # NaN, or out of order: not a record to read
 102 | +                    raise ValueError("caption times are not in order")
 103 | +                for k, part in enumerate(t.split(">>")):
 104 | +                    opens, part = (k > 0) or pending, part.strip()
 105 | +                    pending = opens and not part              # a bare '>>': the next words open the turn
 106 | +                    if part:
 107 | +                        units.append((t0, part, opens))
 108 | +        except (KeyError, TypeError, ValueError, AttributeError):
 109 | +            continue
 110 | +        if any(u[2] for u in units):
 111 | +            return units, {"file": p, "sha256": hashlib.sha256(raw).hexdigest()}
 112 | +    return None, None
 113 | +
 114 | +
 115 | +def turn_of(units, start, end, bc=BACKCHANNEL_WORDS, tol=MARKER_TOL_S):
 116 | +    """RULING 69: the ONE turn of one speaker that holds the clip [start, end], from the caption markers -> ({"text",
 117 | +    "start", "end", "backchannels": [the interjections skipped]}, None) or (None, why). The turn runs from the last
 118 | +    marker at or before the clip to the next marker after it; across a stretch of at most `bc` words between two
 119 | +    markers (another person's interjection) it goes on, both ways: the speaker before and after it is the same."""
 120 | +    if not units:
 121 | +        return None, "no caption record with speaker-change markers"
 122 | +    opens = [i for i, u in enumerate(units) if u[2]]
 123 | +    if any(start + tol < units[i][0] < end - tol for i in opens):
 124 | +        return None, "a speaker-change marker falls inside the clip"
 125 | +    before = [i for i in opens if units[i][0] <= start + tol]
 126 | +    if not before:
 127 | +        return None, "no speaker-change marker before the clip"
 128 | +    nxt = lambda i: min([j for j in opens if j > i], default=len(units))
 129 | +    prv = lambda i: max([j for j in opens if j < i], default=None)
 130 | +    words = lambda i, j: sum(len(units[k][1].split()) for k in range(i, j))
 131 | +
 132 | +    def backchannel(i, j):                               # audit 1545 C1: short AND only backchannel words
 133 | +        ws = [re.sub(r"[^\w'-]", "", w.casefold()) for k in range(i, j) for w in units[k][1].split()]
 134 | +        return 0 < len(ws) <= bc and all(w in BACKCHANNEL for w in ws if w)
 135 | +    a = before[-1]
 136 | +    b = nxt(a)
 137 | +    spans, skipped = [(a, b)], []
 138 | +    while b < len(units) and nxt(b) < len(units) and backchannel(b, nxt(b)):   # A | b: B's interjection | A again
 139 | +        skipped.append(" ".join(units[k][1] for k in range(b, nxt(b))))
 140 | +        spans.append((nxt(b), nxt(nxt(b))))
 141 | +        b = nxt(nxt(b))
 142 | +    while prv(a) is not None and prv(prv(a)) is not None and backchannel(prv(a), a):   # A again | B's | the turn
 143 | +        p = prv(a)
 144 | +        skipped.insert(0, " ".join(units[k][1] for k in range(p, a)))
 145 | +        spans.insert(0, (prv(p), p))
 146 | +        a = prv(p)
 147 | +    idx = [k for x, y in spans for k in range(x, y)]
 148 | +    text = " ".join(units[k][1] for k in idx)
 149 | +    if len(text) > TURN_MAX_CHARS:                       # cut around the clip, never losing it
 150 | +        mid = next((n for n, k in enumerate(idx) if units[k][0] >= start - tol), 0)
 151 | +        lo = len(" ".join(units[k][1] for k in idx[:mid]))
 152 | +        a0 = max(0, min(lo - TURN_MAX_CHARS // 2, len(text) - TURN_MAX_CHARS))
 153 | +        a1 = a0 + TURN_MAX_CHARS
 154 | +        if a0 > 0:                                       # audit 1545 C1: on word boundaries only
 155 | +            a0 = text.find(" ", a0) + 1 or a0
 156 | +        if a1 < len(text):
 157 | +            a1 = text.rfind(" ", a0, a1) if text.rfind(" ", a0, a1) > a0 else a1
 158 | +        text = text[a0:a1].strip()
 159 | +    return {"text": text, "start": units[idx[0]][0], "end": units[idx[-1]][0], "backchannels": skipped}, None
 160 | +
 161 | +
 162 | +def check_turn(t, people, turn_text):
 163 | +    """RULING 69: the verdict's turn evidence, kept only where code sees it -> {"address", "self_intro"} (each a
 164 | +    {"name", "quote"} or None). A quote stands when it is >= BASIS_MIN_WORDS words, verbatim in the turn, and holds a
 165 | +    word of the person's name; the person must be one of the people."""
 166 | +    out = {"address": None, "self_intro": None}
 167 | +    if not isinstance(t, dict) or not turn_text:
 168 | +        return out
 169 | +    for k in out:
 170 | +        x = t.get(k)
 171 | +        if not isinstance(x, dict) or not isinstance(x.get("name"), str) or not isinstance(x.get("quote"), str):
 172 | +            continue
 173 | +        who = next((p for p in people if _norm(p["name"]) == _norm(x["name"])), None)
 174 | +        q = x["quote"]
 175 | +        if who is not None and len(_norm(q).split()) >= BASIS_MIN_WORDS and _within(q, turn_text) and \
 176 | +                any(_within(w, q) for w in _norm(who["name"]).split() if len(w) > 1):
 177 | +            out[k] = {"name": who["name"], "quote": q.strip()}
 178 | +    return out
 179 | +
 180 | +
 181 | +def decide(rec, turn_ev, people, lower_third=None):
 182 | +    """RULING 69: the speaker from the turn evidence, beside the basis rule's (check) -> the record. A self-introduction
 183 | +    names its speaker; an address names the other person only when the source's lines name exactly two. Two rules that
 184 | +    name different people, or a lower third that contradicts the decision, are "unknown". A lower third alone names
 185 | +    nobody (ruling 70: one more piece of evidence, never alone)."""
 186 | +    by = None
 187 | +    if turn_ev.get("self_intro"):
 188 | +        by = (turn_ev["self_intro"]["name"], f"self-introduction in the clip's turn: {turn_ev['self_intro']['quote']}")
 189 | +    elif turn_ev.get("address"):
 190 | +        others = [p for p in people if _norm(p["name"]) != _norm(turn_ev["address"]["name"])]
 191 | +        if len(people) == 2 and len(others) == 1:
 192 | +            by = (others[0]["name"], f"addresses {turn_ev['address']['name']} in the clip's turn: "
 193 | +                                     f"{turn_ev['address']['quote']}")
 194 | +    out = dict(rec)
 195 | +    if by is not None:
 196 | +        p = next(p for p in people if _norm(p["name"]) == _norm(by[0]))
 197 | +        if rec["name"] != UNKNOWN and _norm(rec["name"]) != _norm(p["name"]):
 198 | +            return dict(rec, name=UNKNOWN, role=None, line=None, basis=None,
 199 | +                        why=f"the clip's turn shows {p['name']!r} but the transcript basis shows {rec['name']!r}")
 200 | +        out.update(name=p["name"], role=p["role"], line=p["line"], basis=by[1])
 201 | +    lt = lower_third if isinstance(lower_third, str) and _norm(lower_third) else None
 202 | +    if lt is not None:
 203 | +        hit = next((p for p in people if any(_within(w, lt) for w in _norm(p["name"]).split() if len(w) > 2)), None)
 204 | +        if out["name"] != UNKNOWN and hit is not None and _norm(hit["name"]) != _norm(out["name"]):
 205 | +            return dict(out, name=UNKNOWN, role=None, line=None, basis=None,
 206 | +                        why=f"the lower third {lt!r} contradicts {out['name']!r}")
 207 | +        if out["name"] != UNKNOWN and hit is not None:
 208 | +            out["basis"] = f"{out['basis']}; the lower third reads {lt!r}"
 209 | +    return out
 210 | +
 211 | +
 212 |  def _json(text):
 213 |      """The reply's JSON object: its outermost {...}, whatever fence or prose surrounds it (audit 0007 C1 glm P1-2,
 214 |      C2 grok P2-1)."""
 215 | @@ -158,8 +317,9 @@ def check(v, lines, clip, around):
 216 |      return rec
 217 |  
 218 |  
 219 | -def attribute(router, seg, src, meta, seed=7):
 220 | -    """One segment's speaker record. A call that fails, or a reply out of contract, is "unknown" with measured false."""
 221 | +def attribute(router, seg, src, meta, seed=7, caps=None, lower_third=None):
 222 | +    """One segment's speaker record. A call that fails, or a reply out of contract, is "unknown" with measured false.
 223 | +    caps: captions(video id) (ruling 69: the turn markers), read by the caller."""
 224 |      import providers as P
 225 |      base = {"name": UNKNOWN, "role": None, "line": None, "basis": None, "people": [], "measured": False}
 226 |      if src is None or "k0" not in seg or "k1" not in seg:
 227 | @@ -168,11 +328,25 @@ def attribute(router, seg, src, meta, seed=7):
 228 |      if not lines:
 229 |          return dict(base, why="the source's title, channel and description are not in the store", measured=True)
 230 |      before, clip, after = context(src, int(seg["k0"]), int(seg["k1"]))
 231 | -    prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip())
 232 | +    units, cap_src = caps if caps else (None, None)
 233 | +    try:                                                 # audit 1545 C1: a turn that cannot be read is no turn
 234 | +        turn, turn_why = turn_of(units, float(seg["start"]), float(seg["end"])) if units else \
 235 | +            (None, "no caption record with speaker-change markers")
 236 | +    except (KeyError, TypeError, ValueError, IndexError) as e:
 237 | +        turn, turn_why = None, f"the caption turn could not be read: {type(e).__name__}: {str(e)[:120]}"
 238 | +    prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip(),
 239 | +                           turn=turn["text"] if turn else f"(none: {turn_why})")
 240 |      r = None
 241 |      try:
 242 |          r = router.call("speaker_verdict", prompt, 900, seed)
 243 | -        rec = check(_json(r.text), lines, clip, f"{before} {after}")
 244 | +        v = _json(r.text)
 245 | +        rec = check(v, lines, clip, f"{before} {after}")
 246 | +        ev = check_turn(v.get("turn"), rec["people"], turn["text"] if turn else "")
 247 | +        rec = decide(rec, ev, rec["people"], lower_third)
 248 | +        rec["turn"] = {"read": turn is not None, "why": turn_why, **({"source": cap_src, "start": turn["start"],
 249 | +                                                                      "end": turn["end"],
 250 | +                                                                      "backchannels": turn["backchannels"]}
 251 | +                                                                     if turn else {}), **ev}
 252 |      except Exception as e:                      # any failure claims no name (audit 0007 C1, glm P1-1): Router.call
 253 |          if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)):    # re-raises a back-end's own
 254 |              router.reject(r)                                                         # error
 255 | @@ -180,7 +354,7 @@ def attribute(router, seg, src, meta, seed=7):
 256 |      return dict(rec, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)))
 257 |  
 258 |  
 259 | -def attribute_package(router, pk, sources, meta_for=store_meta, log=print):
 260 | +def attribute_package(router, pk, sources, meta_for=store_meta, log=print, captions_for=captions):
 261 |      """Every segment of a package gets its speaker record, in place (before the pin is sealed)."""
 262 |      for i, s in enumerate(pk["segments"]):
 263 |          try:
 264 | @@ -188,9 +362,14 @@ def attribute_package(router, pk, sources, meta_for=store_meta, log=print):
 265 |          except KeyError:
 266 |              src = None                                        # -> "unknown", not measured: never a name
 267 |          meta = meta_for(s["video_id"])
 268 | -        sp = attribute(router, s, src, meta)
 269 | +        try:
 270 | +            caps = captions_for(s["video_id"])                # ruling 69: the caption turn markers
 271 | +        except Exception:                                     # noqa: BLE001  audit 1545 C1: never the package
 272 | +            caps = None
 273 | +        lt = ((s.get("visual") or {}).get("lower_third") or {}).get("name")   # ruling 70: one more piece, never alone
 274 | +        sp = attribute(router, s, src, meta, caps=caps, lower_third=lt)
 275 |          if not sp["measured"] and sp["why"].startswith("not measured"):      # once more, a new sample (C1 K2)
 276 | -            sp = attribute(router, s, src, meta, seed=8)
 277 | +            sp = attribute(router, s, src, meta, seed=8, caps=caps, lower_third=lt)
 278 |          s["speaker"] = sp
 279 |          log(f"    speaker {i}: {s['video_id']} -> {sp['name']}"
 280 |              + (f" ({sp['role']}; basis {sp['basis']!r})" if sp["name"] != UNKNOWN else f" ({sp.get('why')})")
 281 | diff --git a/tests/package/test_speakers.py b/tests/package/test_speakers.py
 282 | index f3230cd..6f80060 100644
 283 | --- a/tests/package/test_speakers.py
 284 | +++ b/tests/package/test_speakers.py
 285 | @@ -166,6 +166,141 @@ class TestAttribute(unittest.TestCase):
 286 |          self.assertEqual(r.calls, [])                                # nothing to ask: no call is paid
 287 |  
 288 |  
 289 | +CAPS = [  # the episode's own captions around the clip of the 13:38 pin (mKNAcOFMYD4), with their turn markers
 290 | +    (694.40, "&gt;&gt; Tell that to his wife."), (696.24, "&gt;&gt; No. And here's the thing is cheaters"),
 291 | +    (700.72, "cheat. Liars lie."), (750.64, "I'll tell you, this is my biggest fear"),
 292 | +    (753.60, "like of all No, second biggest. My"), (755.76, "biggest fear is that I go to the bank"),
 293 | +    (762.08, "me and that's why that's why we Bitcoin."), (764.80, "My second biggest fear and th this is"),
 294 | +    (894.64, "And you know, Reddit's a great example."), (908.24, "&gt;&gt; Yeah."),
 295 | +    (909.36, "&gt;&gt; And now Reddit stock is going like this"),
 296 | +    (944.00, "supposed to call him super intelligent,"), (945.28, "Scott? Well, because the president and"),
 297 | +    (956.32, "&gt;&gt; it's I Yeah, I I just, you know, it just")]
 298 | +TWO = [{"name": "Scott Melker", "role": "host", "line": "channel: Scott Melker"},
 299 | +       {"name": "Mark Yusko", "role": "guest", "line": "title: Wall Street's Bitcoin Bet l Mark Yusko"}]
 300 | +
 301 | +
 302 | +def store_with(d, vid, caps, repeat=False):
 303 | +    os.makedirs(os.path.join(d, "transcripts", vid))
 304 | +    segs = [{"start": t, "end": t + 1, "text": x} for t, x in caps]
 305 | +    if repeat:                                    # rolling auto captions repeat a line
 306 | +        segs = [x for sg in segs for x in (sg, dict(sg))]
 307 | +    with open(os.path.join(d, "transcripts", vid, "transcript.yt_auto.json"), "w") as f:
 308 | +        json.dump({"segments": segs, "transcript_method": "yt_auto:en-orig"}, f)
 309 | +
 310 | +
 311 | +class TestRuling69Turn(unittest.TestCase):
 312 | +    """RULING 69 (15:29): the attribution reads the caption turn markers and the addresses by name across the whole
 313 | +    turn that contains the clip; a speaker is named when the turn structure plus one address or self-introduction
 314 | +    shows it; a lower third is one more piece of evidence, never alone."""
 315 | +
 316 | +    def turn(self):
 317 | +        import tempfile
 318 | +        with tempfile.TemporaryDirectory() as d:
 319 | +            store_with(d, "v", CAPS, repeat=True)
 320 | +            units, src = SP.captions("v", stores=(os.path.join(d, "missing"), d))
 321 | +        return units, src
 322 | +
 323 | +    def test_the_turn_holding_the_clip_runs_across_a_one_word_interjection(self):
 324 | +        units, src = self.turn()
 325 | +        self.assertEqual(len(units), len(CAPS))                                   # a repeated line is read once
 326 | +        self.assertEqual(sum(u[2] for u in units), 5)
 327 | +        self.assertEqual(len(src["sha256"]), 64)
 328 | +        t, why = SP.turn_of(units, 755.454, 764.214)
 329 | +        self.assertIsNone(why)
 330 | +        self.assertEqual((t["start"], t["end"], t["backchannels"]), (696.24, 945.28, ["Yeah."]))
 331 | +        self.assertTrue(SP._within("super intelligent, Scott?", t["text"]))       # the address, across "Yeah."
 332 | +        self.assertNotIn("Tell that to his wife", t["text"])
 333 | +        self.assertFalse(SP._within("it's I Yeah", t["text"]))                    # the next real turn is out
 334 | +        self.assertEqual(SP.turn_of(units, 905.0, 912.0)[1], "a speaker-change marker falls inside the clip")
 335 | +        self.assertEqual(SP.turn_of(units, 600.0, 610.0)[1], "no speaker-change marker before the clip")
 336 | +        t2, _ = SP.turn_of(units, 944.0, 946.0)                                    # the same turn, seen from after
 337 | +        self.assertEqual((t2["start"], t2["backchannels"]), (696.24, ["Yeah."]))  # the interjection: both ways
 338 | +
 339 | +    def test_only_a_backchannel_continues_a_turn_and_a_bad_record_is_skipped(self):
 340 | +        caps = [(t, x.replace("&gt;&gt; Yeah.", "&gt;&gt; Mark, why?")) for t, x in CAPS]   # B takes the floor
 341 | +        import tempfile
 342 | +        with tempfile.TemporaryDirectory() as d:
 343 | +            store_with(d, "v", caps)
 344 | +            units, _ = SP.captions("v", stores=(d,))
 345 | +            t, _ = SP.turn_of(units, 755.454, 764.214)
 346 | +            self.assertEqual((t["end"], t["backchannels"]), (894.64, []))          # a question ends the turn
 347 | +            self.assertFalse(SP._within("super intelligent, Scott?", t["text"]))
 348 | +            bad = os.path.join(d, "b")
 349 | +            store_with(bad, "v", [(10.0, "&gt;&gt; one"), (5.0, "&gt;&gt; two")])     # out of order
 350 | +            os.makedirs(os.path.join(d, "c", "transcripts", "v"))
 351 | +            with open(os.path.join(d, "c", "transcripts", "v", "transcript.yt_auto.json"), "w") as f:
 352 | +                json.dump({"segments": [{"text": "&gt;&gt; no start"}]}, f)          # no start
 353 | +            self.assertEqual(SP.captions("v", stores=(bad, os.path.join(d, "c")))[0], None)   # skipped, no crash
 354 | +        sp = SP.attribute(Canned(json.dumps(verdict("unknown", ""))), {"k0": 2, "k1": 2, "start": "x", "end": 1},
 355 | +                          source(SENTS), META, caps=([(1.0, "a", True)], {"file": "f", "sha256": "s"}))
 356 | +        self.assertTrue(sp["turn"]["why"].startswith("the caption turn could not be read"))   # measured, no crash
 357 | +
 358 | +    def test_a_long_turn_is_cut_on_word_boundaries_around_the_clip(self):
 359 | +        units = [(0.0, "intro words", True)] + [(float(i), f"filler{i} word", False) for i in range(1, 3000)] + \
 360 | +            [(3000.0, "the clip words here", False)] + [(3000.0 + i, f"tail{i} word", False) for i in range(1, 3000)]
 361 | +        t, _ = SP.turn_of(units, 3000.0, 3000.5)
 362 | +        self.assertLessEqual(len(t["text"]), SP.TURN_MAX_CHARS)
 363 | +        self.assertIn("the clip words here", t["text"])
 364 | +        for w in t["text"].split():                                                    # no word cut in two
 365 | +            self.assertRegex(w, r"^(filler\d+|tail\d+|word|the|clip|words|here)$")
 366 | +
 367 | +    def test_an_address_names_the_other_of_two_people_and_code_checks_the_quote(self):
 368 | +        units, _ = self.turn()
 369 | +        text = SP.turn_of(units, 755.454, 764.214)[0]["text"]
 370 | +        rec = {"name": SP.UNKNOWN, "role": None, "line": None, "basis": None, "why": "w", "people": TWO}
 371 | +        ev = SP.check_turn({"address": {"name": "Scott Melker", "quote": "call him super intelligent, Scott?"}},
 372 | +                           TWO, text)
 373 | +        out = SP.decide(rec, ev, TWO)
 374 | +        self.assertEqual((out["name"], out["role"]), ("Mark Yusko", "guest"))
 375 | +        self.assertIn("addresses Scott Melker in the clip's turn", out["basis"])
 376 | +        three = TWO + [{"name": "Arthur Hayes", "role": "other", "line": "Arthur Hayes on the AI trade"}]
 377 | +        self.assertEqual(SP.decide(rec, ev, three)["name"], SP.UNKNOWN)          # one of three is not excluded enough
 378 | +        for bad in ({"name": "Scott Melker", "quote": "call him super smart, Scott?"},      # not in the turn
 379 | +                    {"name": "Scott Melker", "quote": "the president and his"},              # no name of his
 380 | +                    {"name": "Jeff Booth", "quote": "call him super intelligent, Scott?"},   # not one of the people
 381 | +                    {"name": "Scott Melker", "quote": "Scott?"}):                            # under three words
 382 | +            self.assertIsNone(SP.check_turn({"address": bad}, TWO, text)["address"], bad)
 383 | +        intro = SP.check_turn({"self_intro": {"name": "Mark Yusko", "quote": "biggest fear is that"}}, TWO, text)
 384 | +        self.assertIsNone(intro["self_intro"])                                    # the quote must hold the name
 385 | +
 386 | +    def test_a_self_introduction_names_its_speaker_and_conflicts_are_unknown(self):
 387 | +        text = "Good morning everyone, I'm Mark Yusko and today we talk about Bitcoin."
 388 | +        rec = {"name": SP.UNKNOWN, "role": None, "line": None, "basis": None, "why": "w", "people": TWO}
 389 | +        ev = SP.check_turn({"self_intro": {"name": "Mark Yusko", "quote": "I'm Mark Yusko and today"}}, TWO, text)
 390 | +        self.assertEqual(SP.decide(rec, ev, TWO)["name"], "Mark Yusko")
 391 | +        named = dict(rec, name="Scott Melker", role="host", line="channel: Scott Melker", basis="b c d")
 392 | +        self.assertEqual(SP.decide(named, ev, TWO)["name"], SP.UNKNOWN)          # the two rules disagree
 393 | +
 394 | +    def test_a_lower_third_never_names_alone_and_a_contradicting_one_is_unknown(self):
 395 | +        rec = {"name": SP.UNKNOWN, "role": None, "line": None, "basis": None, "why": "w", "people": TWO}
 396 | +        none = {"address": None, "self_intro": None}
 397 | +        self.assertEqual(SP.decide(rec, none, TWO, lower_third="Mark W. Yusko")["name"], SP.UNKNOWN)
 398 | +        ev = {"address": {"name": "Scott Melker", "quote": "super intelligent, Scott?"}, "self_intro": None}
 399 | +        agree = SP.decide(rec, ev, TWO, lower_third="Mark W. Yusko")
 400 | +        self.assertEqual(agree["name"], "Mark Yusko")
 401 | +        self.assertIn("the lower third reads 'Mark W. Yusko'", agree["basis"])
 402 | +        self.assertEqual(SP.decide(rec, ev, TWO, lower_third="SCOTT MELKER")["name"], SP.UNKNOWN)
 403 | +
 404 | +    def test_attribute_reads_the_turn_and_records_its_evidence(self):
 405 | +        units, src = self.turn()
 406 | +        v = {"people": [{"name": "Scott Melker", "role": "host", "line": "channel: Natalie Brunell"},
 407 | +                        {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me to revisit"}],
 408 | +             "speaker": {"name": "unknown", "basis": "", "why": "nothing in the window"},
 409 | +             "turn": {"address": {"name": "Jeff Booth", "quote": "call him super intelligent, Scott?"},
 410 | +                      "self_intro": None}}
 411 | +        seg = {"k0": 2, "k1": 2, "start": 755.454, "end": 764.214}
 412 | +        r = Canned(json.dumps(v))
 413 | +        sp = SP.attribute(r, seg, source(SENTS), META, caps=(units, src))
 414 | +        self.assertIn("THE CLIP'S TURN", r.calls[0][1])
 415 | +        self.assertIn("super intelligent, Scott?", r.calls[0][1])
 416 | +        self.assertEqual(sp["name"], "unknown")       # "Scott Melker" is not on a source line here: not a person,
 417 | +        self.assertTrue(sp["turn"]["read"])            # and the quote holds no name of Jeff Booth: nothing stands
 418 | +        self.assertEqual((sp["turn"]["source"]["sha256"], sp["turn"]["backchannels"]), (src["sha256"], ["Yeah."]))
 419 | +        sp2 = SP.attribute(Canned(json.dumps(v)), seg, source(SENTS), META)               # no captions: as before
 420 | +        self.assertEqual((sp2["turn"]["read"], sp2["turn"]["why"]), (False, "no caption record with speaker-change "
 421 | +                                                                             "markers"))
 422 | +
 423 | +
 424 |  class TestPinCarriesTheSpeaker(unittest.TestCase):
 425 |      def pk(self, sp):
 426 |          g = {k: {"status": "PASS", "replayed": False} for k in package_pin.REQUIRED_GATES}
 427 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder that seals medley pins). Your role: a
strict reviewer of a step that NAMES real people in a sealed pin (PBX tags them publicly). A wrong name is worse than
"unknown". Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static): pipeline/speakers.py attributes each clip's speaker.
- One verdict (role speaker_verdict, one model call) gets the source's own lines (title, channel, description) and 8
  sentences of the word record around the clip, in which turns are NOT marked.
- It proposes the people the source names and who speaks the clip, with a basis quote.
- check() keeps a person only if a source line names them, and a speaker only if the basis (>= 3 words) is verbatim in
  the clip or the transcript around it. Otherwise the speaker is "unknown".
- The 13:38 pin's clip 3 (mKNAcOFMYD4, Scott Melker's live show with the guest Mark Yusko) came out "unknown", though
  the episode's own YouTube captions mark speaker turns with ">>". The clip lies in one turn (opening at 696.24) that
  runs, across the other person's one-word ">> Yeah." (908.24), to an address "...super intelligent, Scott?" (945.28).

The ruling this diff implements (ORCHESTRATOR 15:29 Nov 13, verbatim):
"RULING 69: the attribution step reads the caption turn markers and addresses by name across the whole turn that
contains the clip, not only the windows around it; a speaker is named when the turn structure plus one address or
self-introduction shows it. Audit, then it applies to new pins."
And ruling 70's part that touches this step: "lower_third feeds ruling 69 as one more piece of evidence, never alone."

The change (pipeline/speakers.py, tests/package/test_speakers.py):
1. captions(video_id): reads transcript.yt_auto.json from the first store whose copy carries any '>>' (the main tree's
   store, then pp-ingest's, where a live episode's captions arrive later).
   - It returns units [(t, text, opens_turn)] plus {file, sha256}.
   - Rolling repeats of a line are read once; '>>' is HTML-unescaped; a '>>' inside a line opens a turn there; a bare
     '>>' opens the turn at the next words.
2. turn_of(units, start, end), in code. It returns None with a reason when a marker falls inside the clip, or no marker
   precedes it. Otherwise:
   - the turn runs from the last marker at or before the clip to the next marker;
   - it continues across another person's interjection of <= BACKCHANNEL_WORDS (3) words between two markers, in BOTH
     directions (A, then B's "Yeah.", then A again: one turn of A);
   - the interjections are recorded; the turn is cut to TURN_MAX_CHARS around the clip.
3. The verdict's prompt adds THE CLIP'S TURN and a step 3: quote (>= 3 exact words) any ADDRESS BY NAME (the turn's
   speaker speaking TO one of the people) and any SELF-INTRODUCTION in the turn. The reply gains
   "turn": {"address", "self_intro"}.
4. check_turn() keeps one only when its quote is >= 3 words, verbatim in the turn, holds a word of the person's name,
   and the person is one of the people check() kept.
5. decide():
   - A self-introduction names its speaker.
   - An address names the OTHER person ONLY when the source's lines name exactly two people.
   - When the basis rule (check) names someone else: "unknown".
   - A lower third names nobody alone; one that contradicts the decision makes it "unknown"; one that agrees is added
     to the basis.
6. attribute(..., caps, lower_third) records "turn": {read, why, source {file, sha256}, start, end, backchannels,
   address, self_intro}. attribute_package passes captions(video id) and the segment's ruling-70 visual.lower_third.name
   (absent until ruling 70).
7. Tests: TestRuling69Turn (5), on the real clip's caption lines:
   - the turn across "Yeah.", seen from both sides;
   - the refusals of a marker inside the clip and of no marker before it;
   - an address naming the other of two, and not one of three;
   - the quote checks: not in the turn, no name word, not a person, under 3 words;
   - a self-introduction, and a conflict with the basis rule;
   - the lower third never alone, agreeing, contradicting;
   - attribute() end to end.
   test_speakers 21 OK.
On the real record: turn_of finds the turn 696.24-953.52, skips "Yeah.", and holds "super intelligent, Scott?".

Stated readings (say so if you read the ruling differently):
- K1: "the whole turn that contains the clip" = between the captions' own speaker-change markers. One person's
  interjection of at most three words (a backchannel such as "Yeah.") does not end the other's turn: the words on
  both sides of it are the same speaker's. This is the reading the orchestrator accepted for the 945.28 evidence.
- K2: "an address" names the speaker only by elimination, so only when the source's lines name exactly two people.
  With three or more, an address excludes one and names no one.
- K3: the model finds the quotes; code checks every quote against the turn and the people, as check() already does
  for the basis.
- K4: a lower third is evidence that can CONFIRM or VETO a decision, never make one.

Check in particular:
- any path that NAMES someone on less than the turn structure plus an address or self-introduction;
- the backchannel merge (could it join two different speakers' turns?);
- marker parsing (an unescaped '>>', a line split across markers, rolling repeats);
- the turn cut; the prompt; the conflicts.

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
