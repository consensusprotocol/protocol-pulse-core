# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), four rows of RULING 159 (3)(a) (orchestrator 23:42 ET Nov 23), uncommitted (diff below):
(1) THE AD-READ GAP: "a clip that is the first line of an ad read must be REFUSED, not softened to 'may not be sincere': step A calling the surrounding read an ad read is HARD for the clip". context_integrity.a_failures: view "ad_read" gives its own code AD_READ, which is NOT in package.STEP_A_SOFT (package.soft_codes returns None for any code outside it, so the never-empty pass never brings the clip back); any other non-sincere view stays NOT_OWN_SINCERE (soft).
(2) RULING 155 (2), ADOPTED: "REFERENT_OUTSIDE stays as information on the pin, out of PBX's note and out of the cap, UNLESS the context check also finds the referent changes what the clip asserts AND nothing else in the line-up or our lines resolves it; then it is a flag." package.referent_flag: a flag only when a step-A referent says changes_assertion "yes" explicitly AND the package context check's step C for that clip is not entails "yes"; the inventory's context_a row then names only the flag codes and keeps the rest under "info". package.seg_marks (the line-up search's count of kinds) now counts step A's soft codes as ONE kind, as the pin does (ruling 157 (5)).
(3) THE SELECTION-SIDE WORD CHECK UNDER RULING 143: "your selection-side word check takes ruling 143 so it agrees with the render's lock". words_only: an L-v 2 record whose only failure is the word check (a number, negation or name the transcript and the second recogniser read differently), measured, one speaker inside. The prescreen keeps such a moment PENDING when the build has the render's lock (lock_check); its line-up's lock pre-check settles it: lv2_settled reads it as passed only for the lock's verdict "pass" or "adopt" (a hold drops the clip: unchanged code; no verdict stops the search: unchanged); the no-voice path does the same; the pin's second_pass row then PASSes with "word_check" naming the settlement. Real case: Simply Bitcoin 513842ff, "$15,000 and a half thousand" against "15,500", adopted by the lock on Nov 23, refused at selection until now.
(4) Fixes from audit 20261124_0016 A2 (qwen, gemma) on ruling 156's fallback_fields: no fallback when a clip has no channel_name (never a raw channel id on screen) or the join is not between two clips of the line-up (never an IndexError); the shortened title re-checked against the house limits, else "Bitcoin, in their words".
CHECK, quoting the code: can an ad-read clip return in any pass; can a REFERENT_OUTSIDE that changes the claim and is not resolved reach the pin WITHOUT a flag, or one that does not change it still count toward the cap; can a span the lock HOLDS, or a speaker change, or an unmeasured or errored L-v 2 record pass the second_pass row now; can a pending moment reach a package without its line-up's lock verdict; can fallback_fields still raise or put an id on screen. Report only what the code shows.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0515
## Consensus findings (majority of panel agrees)
- **[high] pipeline/package.py:0** fallback_fields' join guard can raise before returning None: it indexes join[0] without checking that join is a non-empty sequence, so an empty or non-subscriptable join still causes an IndexError/TypeError.
  - evidence: `    if join is not None and not (isinstance(join[0], int) and 0 <= join[0] < len(segs) - 1):
        return None`
  - fix: Check isinstance(join, (list, tuple)) and len(join) >= 1 before indexing, and validate both indices if join is a pair.
  - raised by qwen27b:F1; agree: qwen27b, gemma
- **[high] pipeline/package.py:0** lv2_settled treats verdict 'pending' as passed in line-up calls, so a words-only L-v 2 record can pass the line-up gate and reach a package without a settling 'pass' or 'adopt' lock verdict.
  - evidence: `    if not (words_only(t) and verdict in ("pass", "adopt", "pending")):
        return t

            nv_lv = lock_verdicts(nv_pre, order)            # RULING 143 at selection, as a voiced line-up
   `
  - fix: Allow 'pending' only in the prescreen; in line-up calls pass only 'pass' or 'adopt' (e.g. separate function or a flag) so pending/None/hold leave the record unchanged.
  - raised by qwen27b:F2; agree: qwen27b, gemma
- **[medium] pipeline/package.py:0** seg_marks counts any non-empty step_a_flags as one kind, and the comment says an information-only REFERENT_OUTSIDE is counted here; a non-claim-changing REFERENT_OUTSIDE can therefore still count toward the line-up cap.
  - evidence: `    n = any(bool(m.get("step_a_flags")) for m in segs) + \
        len({c for m in segs for c in (m.get("edge_flags") or [])}) + any(bool(m.get("stand_soft")) for m in segs)
    #   RULING 157 (5) (st`
  - fix: Filter information-only REFERENT_OUTSIDE codes out of step_a_flags before counting, or count only codes that remain flags.
  - raised by qwen27b:F3; agree: qwen27b, gemma

## Raised but not agreed
- qwen27b:F4 [low] The prescreen second_pass row for a words-only record is just 'PASS'; it does not include the word_check settlement text set on the record, so the row does not name the settlement. (agree: 1)

## Added in cross-examination (not voted on)
- qwen27b: [high] lock_verdicts can raise when pre has no usable segments list: it uses pre.get('segments') or [] for the length check but then zips with pre['segments'], so pre={} with segs=[] raises KeyError and pre={'segments': None} with segs=[] raises TypeError.
- qwen27b: [medium] fallback_fields' join guard only validates join[0]; it does not require join to be a two-element sequence or validate join[1], so a join that is not between two line-up clips can pass the guard and still cause an IndexError if the bridge uses join[1].
