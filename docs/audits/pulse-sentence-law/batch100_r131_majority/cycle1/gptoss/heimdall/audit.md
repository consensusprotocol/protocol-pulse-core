# Heimdall audit

**Question:** Review this diff (orchestrator RULING 131, 08:25 ET Nov 17), verbatim: "(A) ADOPTED as written: per differing pair, two of the three readings (approved text, the render's run decode, the second recogniser) decide it and the sealed text takes that reading, for fillers, function words, repetitions and content words, each at least 3 words from a cut edge; never a number (save B), a name or a negation; a pair where all three differ HOLDS. (B) ADOPTED: a currency symbol is formatting ('$2 billion' equals a spoken '2 billion'), a canon like 401k. Both MARKED in the Telegram note in plain words when used."

Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.

FACTS (unchanged code, not in the diff):
- pinned.adjudicate_lock's inner reads(x, xmap, lo, hi): True only when the second recogniser's tokens hold x[lo:hi] with one neighbour on each side, all aligned and consecutive; at a span end nothing may precede / follow it. pin_side = every pair reads(p...); run_side = every pair reads(r...).
- pinned._lv2_critical(t, texts): a digit, a negation, an ordinal or a capitalised non-sentence-initial name.
- The critical check (crit -> PinError "number, name or negation") runs on the pairs left in ops BEFORE the second recogniser is called (pinned.py, right after "tag = ...").
- Below the (A) block, unchanged: ruling 18 (one replaced token, run_side -> both readings recorded), the HOLD when not pin_side, ruling 84 (b) (pin_side: one function word kept as the decode's with both readings; two or more hold), ruling 17 (pin_side: the approved text).
- lock_precheck.second_reading: ONE paid call per acquisition, cached in the work dir by the source file's sha256; a cached call returns usd 0.0.
- pinned.segment_lock = make_lock -> trimmed_lock -> adjudicate_lock is the render's own lock path (build_edl uses it).
- word_diff.norm used to drop every 'dollars' right after a token matching \d+(\.\d+)?: the same rule is now canon.dollars_after_number.
- telegram.bar_lines (unchanged) reads PINNED_DECISION.json the same way and binds it to the attested EDL by moments_package.package_sha256 == edl["moments_package_sha256"].

CHECKS:
A1. (B) Is a pair dropped only when EVERY token on BOTH sides is a 'dollars' right after a number in its own token list? Can a different number ever be dropped with it ('$2 billion' vs '3 billion')?
A2. (A) Does a pair take the run decode's reading only when reads(r, rmap, a, b) is true AND _edge_distance >= 3? Does any pair with took None make the lock HOLD (PinError), never pass?
A3. _edge_distance: for a pair with an empty side, does every slide step keep both texts identical and stay inside the adjacent "equal" opcode? Can it return more than the best valid placement's distance?
A4. _majority_text: is text returned only when canon_tokens(text) equals the settled token list exactly? Can a took-run pair be written in the wrong place, or a took-approved pair changed?
A5. lock_precheck.answer: is "adopt_spoken" with spoken_text = the first lock's merged text reached only when as_spoken's verdict is "same", the first lock carries a ruling 131 (A) record, AND the render's own segment_lock re-made with that text as approved_text succeeds? Does a PinError there HOLD?
A6. telegram.lock_lines: is each line printed only when used (a lock's (A) record; a sealed pin rule naming ruling 131 (A) bound to the EDL by the package digest; a lock's currency_format)? Does an unreadable record STOP?
A7. Does anything else change behaviour?

**Panel:** gptoss  |  **Cost:** $0.0023
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
