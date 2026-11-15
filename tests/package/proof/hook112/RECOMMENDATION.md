# RULING 112 (5): THE RECOMMENDATION (pp-selectid; data in REPORT.md and the JSON files beside it)

## What the data says

1. RATER DRIFT, NOT WEAK SUPPLY. The hook job as it stands today was asked fresh, with no cache, Heimdall only, at 3
   seeds. Today's job is ruling 88's hook list, which puts qwen first; qwen has rated every hook since 11:29 ET Nov 14,
   and Grok rated every hook before that. At production's seed (7), qwen rates 4 of the 5 approved hooks BELOW 4:
   - the protected preview: 2;
   - the protected moments reference 37c5b5f5: 2;
   - the published 0c68b589: 3 (4 at seeds 8 and 9);
   - the last sealed medley 13949b7c: 3 (at every seed).
   Only the protected medley reference 41f29b1f rates 4. Grok, the rater before 11:29 ET Nov 14, had rated the hooks of
   0c68b589 and 13949b7c 4 each. Every drop is on SCROLL (the first 2-3 seconds). By the order's own test, that is
   rater drift.
2. THE HOOK IS NOT WHAT USUALLY ENDS A MEDLEY. Of the 39 builds in the 48 h:
   - 3 ended at "no hook rates >= 4" (one on Nov 13, and today's builds 6 and 7);
   - 17 ended at the 3-channel rule;
   - 14 ended at the clips-alone verdict, after a hook had passed;
   - 3 ended because no line-up fits the seconds;
   - 2 sealed (0c68b589 and 13949b7c).
   Today's "no hook" comes from today's small pool (3 videos, 4 moments that may open).
3. THE PATH IS NARROW AT THE CLIP'S FIRST SECONDS. 1,144 distinct moments; 48 may open (4 %); all 48 rated; 9 rated
   >= 4. Where the rest were lost:
   - the opener screens (the opener eligibility 261, the opener rule 36, a leading 'and' / 'so' with no trim variant
     24);
   - G17a (48 that had passed everything else, with no quiet before the first word);
   - among the rated, scroll holds 15 of the 17 moments rated 3.
4. THE HOOK-MINING PASS (ruling 80) writes few rows, and they die before the hook job. Today: 14 hook rows, of which 1
   was rated (a 2). The other 13 were lost to the word pass (5), the topic rule (2), step A (2), L-v 2 / CUTTABLE (3)
   and G17a (1). Bloomberg's 0 rows are its norm: 116 of its 122 hook events in 48 h were videos not about Bitcoin,
   where no model is called.

## The recommendation (to rule on)

Hold the bar (>= 4) and re-anchor the RATER to what PBX approved, instead of letting a rater change move the bar. One
change, two parts:

(a) Make "every PBX-approved hook rates >= 4 on the hook job, at production's seed" a standing check. Today that is the
    five hooks above: the protected preview, 37c5b5f5, 41f29b1f, 0c68b589 and 13949b7c. This driver's calibration is
    the check, at $0.004 a run. No rater or prompt change may land while it fails.

(b) Bring today's rater back inside it, without touching the bar. Show the hook question, as calibration examples, the
    approved hooks with the rating PBX's approval implies (these OPENED approved videos), and keep the ratings cache
    keyed by the new question version, so every hook is asked again once. If (a) still fails after that, the fallback
    is the routing ruling 88 made before its full table: Grok first for the hook rating. That is the orchestrator's
    call; it costs Grok spend.

Only after (a) passes: (c) a hook-only "later start" candidate. Where a moment's opening fails the opener rule or G17a,
or rates 3 on scroll, offer the same moment starting at its next sentence boundary, as a NEW candidate under every gate
unchanged (step A on its own context, so a back-reference to the dropped sentence is still refused; L-v 2; CUTTABLE;
G17a at the new onset; the hook job; the visual check). It extends ruling 33 / 94's one-word trim to one leading
sentence, for the hook seat only. First measure, free, on these 48 h of word records how many such starts exist.

Not a hook matter, but the largest single cause in these 48 h: the 3-channel rule ended 17 of 39 builds. Channel
breadth is where the next yield is, after the rater.
