# Heimdall audit

**Question:** Batch 68 = the publishing kit and law L-t. Law L-t (orchestrator 2026-11-12): a moments package's ONE title and caption travel in the EDL, sealed and gated, and all audience-facing text is in the integrity class. Measured (2026-11-13 17:12, pin 0c68b589, the first full pass): the kit delivered as Telegram 67848 suggested the title 'bitcoin | Pulse Check' and opened its description with 'bitcoin.'. telegram.publish_kit took edl['headline'] or edl['topic'] ('bitcoin'). The EDL carried title 'No single owner controls the bitcoin network' and the sealed caption, which the kit never read. The videos and their captions were not affected.
The change (pipeline/telegram.py, publish_kit only): title = edl['title'] when present (moments pins). The suggested title is that title + ' | Pulse Check' (the kit's existing format), and the description's lead is the sealed caption. When there is no title (story pins), headline / topic exactly as before. If a title is present and the caption is empty, the lead falls back to '<title>.'.
Tests: test_telegram_delivery.test_a_moments_kit_carries_the_sealed_title_and_caption. It FAILS on the old telegram.py ('SUGGESTED TITLE: bitcoin | Pulse Check') and passes on the fix. test_telegram_delivery + test_review_drop: 41 passed (the story-pin kit test unchanged).
FIND: a moments kit that can still carry a title or caption other than the sealed ones; a change to a story pin's kit; any other audience-facing text in the kit that is not sealed; a test that does not test what it claims. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0006
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] Story-pin kit behavior changed: headline no longer has trailing period stripped when title absent? No—when title absent, headline path is unchanged, but the description lead now uses f"{headline}." where the old code stripped the trailing period before re-adding it; if headline/topic already ends with '.', old code stripped it, new code also strips then re-adds, so unchanged. However when title is present, headline = title.strip() without .rstrip('.') — if the sealed title ends with '.', the suggested title shows 'X. | Pulse Check' (double spacing), a cosmetic deviation from the kit's existing format. (agree: 1)

## Added in cross-examination (not voted on)
- none
