# Heimdall audit

**Question:** Batch 57 = RULING 34 (orchestrator 2026-11-13 '03:42'), verbatim: "stand_alone.topical no longer requires EVERY segment to name Bitcoin. Per segment the test is the miner's about-Bitcoin screen carried on the pin (BTC_SCREEN: bitcoin, btc, sats, Satoshi, halving, hash rate, self-custody, Bitcoiners...). The MEDLEY must name Bitcoin: the hook or at least one clip says it in the speaker's own words. Moments pins only; the story path is unchanged."
The change:
- pinned.build_edl copies the moments package's btc_screen (sealed by the builder: {"pattern", "source"}) into the EDL as moments_btc_screen, the way moments_bridge is copied.
- run_fresh.moments_screen(edl) returns (compiled pattern with re.I, why) ONLY for an EDL carrying moments_package_sha256 that stand_alone_subject binds to 'bitcoin'. Otherwise None, and also None when the screen is absent, not a non-empty str of at most 500 chars, or not compiling. None means the old rule: every segment names Bitcoin.
- stand_alone.check_edl(..., screen=None): with a screen, each segment's TOPIC test is topical_screen:
  - the screen matches the segment's own text; or
  - (clip only) topical()'s existing completion rule.
  The EDL-level medley_names_bitcoin requires BITCOIN (bitcoin / btc) in at least one segment's text, and ok includes it. The opener rule and the scorer are unchanged.
- stage_validate passes the screen and prints and HOLDs on the medley row.
Tests: test_stand_alone +7 (screen pass, off-screen fail, the medley must name Bitcoin, no screen = old rule, the opener unchanged, moments_screen None cases incl. the story path).
FIND:
- any way a segment that is not about Bitcoin passes;
- the story path affected;
- a medley that never names Bitcoin passing;
- a malformed or hostile screen loosening the rule;
- the completion rule widened;
- tests that do not test what they claim.
Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0030
## Consensus findings (majority of panel agrees)
- **[low] pipeline/run_fresh.py:411** moments_screen treats a whitespace-only pattern as malformed (None) but a pattern of exactly 500 chars passes while 501 fails; the ruling says 'at most 500 chars' so this is compliant, but a pattern that is only whitespace (e.g. '   ') returns None with why 'btc_screen malformed' even though it is a str of at most 500 chars — the ruling's malformed definition is 'not a non-empty str of at most 500 chars', and '   ' is arguably non-empty, so the divergence is only in the why-string, not the outcome
  - evidence: `if not isinstance(pat, str) or not pat.strip() or len(pat) > 500:`
  - fix: none needed; behavior matches the ruling's intent (a whitespace-only pattern would match nothing, so None is the safe reading)
  - raised by glm:F1; agree: qwen27b, glm
- **[low] pipeline/stand_alone.py:99** topical_screen for a clip falls back to topical()'s completion rule with the hard-coded subject ("bitcoin", "btc") instead of the EDL's subject argument, so a moments EDL whose subject_terms differ would be tested against bitcoin/btc in the completion branch; harmless here because moments_screen only returns a screen when stand_alone_subject binds to 'bitcoin', so the subject is always ('bitcoin','btc') in the screen path
  - evidence: `ok, why = topical(kind, text, prev_text, ("bitcoin", "btc"))`
  - fix: none needed; the guard in moments_screen makes the hard-coded subject coincide with the bound subject
  - raised by glm:F2; agree: qwen27b, glm
- **[low] pipeline/stand_alone.py:141** medley_names_bitcoin uses BITCOIN.search on the raw segment text, so a segment whose only mention is inside a quoted/bracketed annotation or a channel label would count as 'the speaker's own words' even if it is not; the ruling says 'in the speaker's own words' but the implementation cannot distinguish, a known limitation, not a defect
  - evidence: `named = [r["segment"] for (label, kind, s), r in zip(segs, rows) if BITCOIN.search(s.get("text") or "")]`
  - fix: none needed; the ruling's 'own words' clause is satisfied by searching the segment text, which is the speaker's words
  - raised by glm:F3; agree: qwen27b, glm

## Raised but not agreed
- qwen27b:F1 [high] The medley-level check for 'naming Bitcoin' uses the BITCOIN regex (bitcoin/btc) but does not verify that the match is in the 'speaker's own words' (e.g., it might match a quoted title or a non-speech field if the text field is not strictly the transcript). More critically, the ruling states 'the hook or at least one clip says it in the speaker's own words'. The implementation `BITCOIN.search(s.get("text") or "")` checks the text field. However, the primary defect is that `topical_screen` allows a segment to pass if it matches the broad `screen` (e.g., 'halving'), but the medley check requires `BITCOIN` (bitcoin/btc). If a segment passes via 'halving' but the medley check fails because no segment says 'bitcoin' or 'btc', the EDL fails. This is correct per the ruling. 

Wait, let's look closer at `topical_screen`. It calls `topical(kind, text, prev_text, ("bitcoin", "btc"))` as a fallback. The `topical` function has a 'completion rule' for clips. The ruling says: 'the test is the miner's about-Bitcoin screen... The MEDLEY must name Bitcoin... Moments pins only'. It does not explicitly forbid the completion rule, but it says 'Per segment the test is the miner's about-Bitcoin screen'. The code implements: `screen.search(text)` OR `topical(...)` (which includes completion). This means a clip that does NOT match the screen (e.g., 'The stock market fell') but completes a previous claim (e.g., previous: 'Bitcoin fell', current: 'and the stock market fell') would pass the segment topic test via the completion rule, even though it is not about Bitcoin per the screen. The ruling says 'Per segment the test is the miner's about-Bitcoin screen'. It does not say 'screen OR completion'. It says 'the test is the screen'. The completion rule is a specific exception in `topical` for clips that are continuations. If the ruling intends to replace the topic test entirely with the screen, then allowing the completion rule to bypass the screen is a defect. The ruling says: 'Per segment the test is the miner's about-Bitcoin screen... The MEDLEY must name Bitcoin'. It does not mention the completion rule. The code allows the completion rule to pass a segment that fails the screen. This is a potential loosening. 

However, the most clear defect is in `moments_screen` in `run_fresh.py`. It checks `stand_alone_subject(edl, {})`. `stand_alone_subject` returns the subject terms. The code checks `if not stand_alone_subject(edl, {})`. If `stand_alone_subject` returns an empty tuple or list for a non-bitcoin subject, this condition is true, and it returns None. But `stand_alone_subject` is defined to return the subject terms. If the subject is 'bitcoin', it returns ('bitcoin', 'btc'). If it is something else, it returns that. The check `if not stand_alone_subject(edl, {})` will be False if the subject is non-empty. So it proceeds. Then it checks the screen. This seems okay. 

Let's re-read the ruling: 'stand_alone.topical no longer requires EVERY segment to name Bitcoin. Per segment the test is the miner's about-Bitcoin screen... The MEDLEY must name Bitcoin: the hook or at least one clip says it in the speaker's own words.' 

The code in `topical_screen` allows a segment to pass if `screen.search(text)` OR `topical(...)` (completion). The ruling says 'Per segment the test is the miner's about-Bitcoin screen'. It does not say 'screen OR completion'. The completion rule is a specific case in `topical` where a clip is considered 'about' the subject if it completes a previous claim. If the previous claim was about Bitcoin, and the current clip completes it, is it 'about Bitcoin'? The ruling says the test is the screen. If the screen does not match, it should fail. The code allows it to pass via completion. This is a defect: a segment that is not about Bitcoin (per the screen) can pass if it completes a previous claim. 

Also, the medley check `BITCOIN.search` is correct. 

Another defect: `moments_screen` returns `None` if `stand_alone_subject` is falsy. But `stand_alone_subject` returns a tuple of strings. If the subject is 'bitcoin', it returns ('bitcoin', 'btc'). This is truthy. So it proceeds. If the subject is 'ethereum', it returns ('ethereum', 'eth'). This is truthy. So it proceeds. Then it checks the screen. If the screen is present, it compiles it. But the ruling says 'only for a moments package stand_alone_subject binds to the subject 'bitcoin''. The code does NOT check if the subject is 'bitcoin'. It only checks if `stand_alone_subject` is truthy. So a moments package with subject 'ethereum' and a btc_screen would get the screen applied. This is a defect: the screen is applied to non-bitcoin subjects. 

Evidence: `if "moments_package_sha256" not in edl or not stand_alone_subject(edl, {}):` 
Fix: Check if the subject is 'bitcoin' or contains 'bitcoin'. (agree: 1)

## Added in cross-examination (not voted on)
- glm: [medium] medley_names_bitcoin searches BITCOIN against the raw segment text including the hook, but the ruling requires the medley to name Bitcoin 'in the speaker's own words' — the hook's text is the speaker's words, so this is fine; however the check runs even when a segment passed via the completion rule, meaning a medley whose only 'bitcoin' mention is a completion-branch match still counts, which is consistent. The real missed defect: out["ok"] is computed as all(rows) AND medley, but stage_validate's HOLD message builds the medley clause with sa.get("medley_names_bitcoin", {"pass": True})["pass"] — when screen is None the key is absent and the default passes, which is correct, so no defect there either. Actual missed item: topical_screen's completion fallback calls topical(kind, text, prev_text, ("bitcoin", "btc")) — for a hook, topical returns (False, ...) before the completion branch, so the hook's failure why-string is overwritten by the generic completion message, losing the earlier 'the hook does not pass the miner's about-Bitcoin screen' diagnostic in the row's topic.why when the hook also fails the completion check... actually topical_screen returns early for kind=='hook', so this path never runs. No missed defect found beyond those already voted.
