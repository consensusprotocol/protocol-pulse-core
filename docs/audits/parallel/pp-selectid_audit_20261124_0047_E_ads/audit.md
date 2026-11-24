# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), RULING 158 (2) (orchestrator 23:12 ET Nov 23, STANDING, HARD): "on-screen advertising refuses a clip in every format (advertiser names or logos as ads, sign-up bonus, promo or referral code, 'use code', affiliate link, QR code, 'sponsored by', paid-partner banner or panel). The vision question asks for it explicitly on EVERY clip and names what it saw. The show's own branding, ticker and lower third stay a 16:9 flag. When unsure, treat it as an ad. Ruling 146 (1) is narrowed." Uncommitted diff below. THE CODE: visual_pin VERSION visual-4 (the cache key carries VERSION, so every clip is asked again), question 5 "advertising" in the prompt, check() requires it, ad_block() refuses on anything question 5 lists or on offer phrases (AD_WORDS) in any copied text except the source's burned captions (the spoken words; a spoken ad read is the exclusion model's, ruling 146 (3)), and on "IRA" in capitals on a bug, ticker or crawl (the iTrustCapital panel was copied as a bug "CRYPTO IRA"); layout_block (every role) puts it first; graphics_only (146 (1)'s 16:9 softening) and crop_only (ruling 123 (2)'s 16:9 hook) never take an ad. Unchanged context: package._build's line-up check at line 4445 refuses every clip whose layout_block is set unless soft_graphics (line 1944, which reads graphics_only) or the hook's opens_16x9 (crop_only) applies. package.inventory's visual row now FAILS a clip with an ad (a backstop: package_pin.gate_problems refuses a pin whose required row is not PASS). ALSO a bug fix found while testing this: ruling 156 (2)'s plain fallback lines were built whenever the write count was spent in the never-empty pass, and a line-up the render's lock HELD, whose frames were refused, or with NO lock verdict is re-lined by setting that count with no write made, so the plain lines sealed the refused line-up; now they need "not relined and not no_verdict".
CHECK, quoting the code: can a clip with an advertiser's banner, panel, code or bonus reach a package in any pass, role or format; can the show's own name, a plain price ticker, "block reward", "a discount" or an IRA the speaker talks about be refused as an ad; can a record from visual-3 be served from the cache; can the fallback lines still seal a line-up that was refused before any write, and can the new condition stop the fallback where every write really failed. Report only what the code shows.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0270
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
