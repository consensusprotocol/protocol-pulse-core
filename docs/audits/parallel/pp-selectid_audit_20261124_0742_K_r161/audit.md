# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), RULING 161 (orchestrator 07:36 ET Nov 24, from the owner's words): sponsor or advertiser material that is only VISIBLE in a clip (a logo wall or backdrop behind a speaker, a banner, a panel, a bug, a graphic that flashes on screen) is NOT a refusal and NOT a flag counted toward the cap, in any format; it is recorded on the pin as information ("visible sponsor graphics: <what>"). Still HARD and NOT in this diff: the clip's own spoken words in an ad (moments.ad_read_marker, the exclusion model's ad_read risk) and step A's AD_READ code. The 9:16 crop rule is unchanged: OUR crop may not slice through burned text.
THE CHANGE (diff below; it replaces ruling 158 (2)'s refusal of on-screen ads): visual_pin.ad_block is removed. sponsor_item(x, rec) marks a burned-in item as sponsor material: its text equals (loosely normalized by _norm) or, when both are 8+ characters, contains or is contained in a question-5 "advertising" text, or it carries offer words (AD_WORDS; "IRA" on a bug, ticker or crawl via AD_CAPS); never a caption. burned_block(x, rec) no longer refuses a sponsor item (ruling 93's ticker/crawl, frame-edge and covers-speaker rules). formats() makes a clip 16:9 only when a sponsor item is "cut" by the 9:16 crop, as for a caption. flags() never flags a sponsor item. sponsor_graphics(rec) builds the information line. current(rec) re-derives flags and formats of a record cached before today (used on visual_for's two cache-hit returns). package._package puts "visible_sponsor_graphics" on each segment that shows any; package_pin.SEALED_LATER seals it (seal() adds a SEALED_LATER field to a segment's body only when the key is present) and to_pin copies it; the inventory's visual row no longer fails on an ad and lists "sponsor_info". The PROMPT is unchanged, so cached visual-4 answers (visual_pin.key digests PROMPT) stay valid.
CHECK, quoting the code: (1) can any visible sponsor item still refuse a clip or add a counted flag (layout_block, crop_only, graphics_only, the inventory's visual row); (2) can a NON-sponsor item (a news ticker, the show's own bug) now escape ruling 93 through sponsor_item, e.g. by sharing a short word with an ad's text; (3) can our 9:16 crop slice a sponsor item's text without the clip becoming 16:9 only (formats, current, the cache paths in visual_for); (4) does the seal change for a segment WITHOUT the new field. Report only what the code shows; if unsure, say so.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0263
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
