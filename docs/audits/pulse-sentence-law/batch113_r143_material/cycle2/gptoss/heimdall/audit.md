# Heimdall audit

**Question:** Review this diff. ORCHESTRATOR RULING 143 (15:55 ET Nov 17), verbatim in part: "(1) MATERIAL = a number, a negation, a name (letters differ after the canon), a ticker or a currency amount. Everything else is NON-MATERIAL. (2) NON-MATERIAL disagreement NEVER holds. The sealed text takes the two-of-three reading; if all three differ, the run decode's (it is what the render will cut). Sound-alikes (ad/add), fillers of any length (you know, I mean, sort of like), word forms: all here. More than 3 unsettled non-material pairs in one clip adds ONE soft flag: 'The clip (X): the transcript and the audio readers differ on a few small words.' (3) MATERIAL disagreement: if the TWO AUDIO READINGS (the run decode and the second recogniser) AGREE with each other against the transcript, the transcript was wrong: the sealed text takes the audio's reading, numbers included ('$2.35 billion') ... mark it in the note ('transcript corrected from the audio: ...'). If the two audio readings DISAGREE with each other on a material word, HOLD ... 'i've' / 'IBIT' is a ticker: material: holds unless both audio readings agree. (4) Unchanged and HARD: a cut mid-word, an empty or shifted source (the offset guard), a span whose audio readings share under 85 percent of their words (wrong audio, not small words; propose a better number from the records if you have one)."
The integrator's reading of (4), recorded: the share is the run decode's words the second reading heard, in order (the second recogniser also writes the speaker's repeats, false starts and the window's spill: those are not the wrong audio), and a hold needs more than 3 words missing (a short span's one or two small words are not the wrong audio). G18 (a HARD render gate comparing the final's audio decode with the lock text when the lock was adjudicated) decides small-word-only differences by the audio, as ruling 22 already decides omissions, so that (2) holds at render too.
FACTS (unchanged code): reads(x, xmap, lo, hi) is True when the second reading reads x's tokens lo..hi-1 at that position (with one aligned neighbour each side, nothing between); _majority_text writes the settled text from the approved text and the pairs that took 'run', or returns None; _lv2_critical(tok, texts) marks digits, negations, ordinals and capitalised mid-sentence words; canon.word_form marks a possessive / plural / contraction pair; lock_precheck answers outcome 'hold' (final for the builder), 'error' (no verdict) or a pass; G18's ruling 22 block runs span_fidelity (the prepared clip's interior against the source span) and clears the identity difference only when the audio is the same.
Cycle 2: try to BREAK it. Report ONLY a defect you can show with CONCRETE texts (run decode, transcript, second reading) traced through the diff's code. Keep each "issue" under 80 words. If you cannot break it, answer PASS with no findings.
TARGETS:
T1. A wrong number, negation, name, ticker or amount sealed or delivered.
T2. A small-word difference that still holds a span or a render.
T3. The wrong audio passing, or the right audio held.

**Panel:** gptoss  |  **Cost:** $0.0017
## Consensus findings (majority of panel agrees)
- **[high] pipeline/lock_precheck.py:80** as_spoken incorrectly holds when a material word is present but the two audio readings agree, violating ruling 143 (3). The function only checks for material_pair, not whether the two audio readings differ, causing a false hold on correct transcripts.
  - evidence: ````python
-    cls = ["material" if pinned.material_pair(L[a:b], S2[c:d], (lock["text"], spoken)) else "small"
-           for _, a, b, c, d in ops]
-    return ("hold" if "material" in cls else "same`
  - fix: Modify as_spoken to distinguish between material pairs where the two audio readings agree and those where they disagree. For each op, if pinned.material_pair(...) is True, compare L[a:b] and S2[c:d]. If they differ, mark the pair as "material_disagree" and set verdict to "hold"; if they are equal, mark as "material_agree" and set verdict to "adopt" (or "same" if no other differences). Example patch:
```python
-    cls = ["material" if pinned.material_pair(L[a:b], S2[c:d], (lock["text"], spoken)) else "small"
-           for _, a, b, c, d in ops]
-    return ("hold" if "material" in cls else "same"), diffs, cls, spoken
+    cls = []
+    for _, a, b, c, d in ops:
+        if pinned.material_pair(L[a:b], S2[c:d], (lock["text"], spoken)):
+            if L[a:b] != S2[c:d]:
+                cls.append("material_disagree")
+            else:
+                cls.append("material_agree")
+        else:
+            cls.append("small")
+    verdict = "hold" if any(c == "material_disagree" for c in cls) else "adopt"
+    return verdict, diffs, cls, spoken
```
  - raised by gptoss:F1; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
