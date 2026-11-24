# Heimdall audit

**Question:** TASK: audit batch 125 of the Protocol Pulse video pipeline (Python): ruling 158 (2) on the render's side. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

RULING 158 (2) (orchestrator 23:12 ET Nov 23), verbatim in part: "STANDING, HARD, BOTH SIDES: ON-SCREEN ADVERTISING REFUSES A CLIP IN EVERY FORMAT: any advertiser's or sponsor's name or logo presented as an ad, a sign-up bonus, promo or referral code, 'use code', affiliate link or QR code, 'sponsored by', a paid-partner banner or panel ... The show's OWN branding, its own ticker of headlines or prices, its own lower third: still a flag in 16:9 as ruled. When the vision model cannot tell an ad from the show's own graphic, it is treated as an ad."

BACKGROUND (unchanged): visual_check.py's V1 asks two Heimdall vision models (VISION_MODELS) every CHECKLIST line about the FINAL video's contact sheet (stills every 2 s, both formats separately); verdict() passes a line only on "yes" (or "n/a" where allowed: two layout lines on 16:9); any "no", missing or malformed answer from EITHER model fails V1, a REQUIRED release row that no review drop may waive.

THE DIFF: one CHECKLIST line, "no_on_screen_advertising", phrased so that "yes" means no ad (the other lines' convention). "n/a" is not allowed for it. Tests: a "no", "n/a" or missing answer fails in both formats; the question reaches every model and either model's "no" fails the panel. LIVE (free Heimdall vision, this line): tonight's DO NOT PUBLISH video's sheets (16:9, 9:16) and two frames of its Digital Asset News clip: both models answered "no" 4 of 4, naming the Kraken "$25 SIGN UP BONUS" banner and the iTrustCapital IRA panel; control, the published 13 Nov video (CNBC's own ticker and lower thirds): both models "yes" 2 of 2.

CHECK, AND ANSWER EACH:
Q1. Does the line's wording match the ruling (every format, every clip, the listed ad kinds, the show's own graphics excluded, "cannot tell" = ad)? Name any listed kind it misses.
Q2. Can a model's answer ever make V1 pass while an ad is on a sheet (a "yes" with a reason naming an ad, an answer key spelled differently, "n/a")?
Q3. Any other defect (prompt length, the other lines' answers, the verify pack's key list).

OUTPUT: for each finding, severity (critical|high|medium|low), file:line, the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** glm  |  **Cost:** $0.0003
## Consensus findings (majority of panel agrees)
- **[low] pipeline/visual_check.py:55** Q1: wording covers all listed kinds in the ruling (advertiser/sponsor name or logo, sign-up bonus, promo/referral/discount code, 'use code', affiliate link, QR code, 'sponsored by', paid-partner banner/panel) and excludes the show's own branding/ticker/lower third; 'cannot tell' = 'no' = treated as ad, matching the ruling. It adds 'brought to you by' and 'open an account / IRA' beyond the ruling, which is harmless. No listed kind is missed. However, the ruling says 'cannot tell ... it is treated as an ad' — i.e. treated as a FAIL; here 'cannot tell' maps to answer 'no', and since verdict() passes only on 'yes', 'no' fails, so semantics match. Uncertain: the diff shows only the CHECKLIST entry; whether 'n/a' is truly disallowed for this line (BACKGROUND says it is not allowed) cannot be verified from the diff, since the verdict()/n-a-allowlist code is not shown.
  - evidence: `("no_on_screen_advertising", "RULING 158: no still, in ANY clip (not only the first), shows PAID ADVERTISING ... Answer 'yes' only if there is none; when you cannot tell an ad from the show's own grap`
  - fix: None required in the diff; if the n/a allowlist lives elsewhere, confirm this key is absent from it (not verifiable here).
  - raised by glm:F1; agree: glm
- **[low] pipeline/visual_check.py:55** Q2: cannot fully verify. The diff shows only the question text; the answer-key spelling ('no_on_screen_advertising'), the verdict() 'yes'-only rule, and the n/a handling are not in the diff. If, per BACKGROUND, verdict() passes only on 'yes' and 'n/a' is not allowed for this line, then a 'yes' with a reason naming an ad, a differently spelled key, or an 'n/a' cannot make V1 pass — but that behavior is asserted, not shown in the cited code.
  - evidence: `("no_on_screen_advertising", "RULING 158: ... Answer 'yes' only if there is none; ...")`
  - fix: Include or reference the verdict()/answer-parsing code in the diff to make this auditable; no code change evidenced as needed.
  - raised by glm:F2; agree: glm
- **[low] pipeline/visual_check.py:55** Q3: the added question is long (~90 words) relative to the other CHECKLIST lines, which could dilute per-line attention in a multi-question prompt, but no prompt-assembly code is in the diff, so any prompt-length or other-lines impact is unverifiable. The verify pack's key list is not shown, so whether 'no_on_screen_advertising' is registered there cannot be checked from the diff.
  - evidence: `"a sign-up bonus or any bonus / reward offer, a promo, referral or discount code, 'use code', an affiliate link, a QR code, 'sponsored by' or 'brought to you by', a paid-partner banner or panel, an 'o`
  - fix: None demonstrable from the diff; if the verify pack enumerates CHECKLIST keys, add 'no_on_screen_advertising' there (not verifiable here).
  - raised by glm:F3; agree: glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- glm: [low] The question instructs 'Answer yes only if there is none' but does not restate the yes/no polarity convention relative to other lines; if any prompt wrapper appends a global convention like 'answer yes if the condition holds', the inverted polarity of this line (yes = no ad) could conflict
