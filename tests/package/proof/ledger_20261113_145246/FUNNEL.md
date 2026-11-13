Build `ledger_20261113_145246`: code a952cb32+90e372f637e1, render clock 2026-11-13T14:52:46.209297+00:00.
Adapter (pp-ingest, before the ledger rows): excluded {"hard exclusion flag (L-u)": 286, "altcoin or not about Bitcoin": 125, "speaker change inside (caption marker)": 34}.

**Stage 0: 936 ledger rows -> 587 moments (349 not moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 116 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 107 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched around the row's time) | "and they're in that safe and it's like yeah yeah yeah it's like what is that safe made of glass I think I've got a hammer back there let me…" |
| 66 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it runs N s > N s (ruling N: the clip length limit) | "Um I find Bitcoin super boring, but I'm always like that's cool because it's boring. Like that was the cool part because it was so boring. …" |
| 56 | duplicate: the same speech as a kept moment (time overlap in the same video) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software and Bitcoin has…" |
| 2 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched -N-N s) | "Bitcoin lost the 50we moving average. It's now right in between the 50we and the 200week moving average." |
| 1 | SUPPLY: no word record yet (no word record in the store; no sentence-ready window record) | n/a |
| 1 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it holds a caption speaker marker at N s: a measured speaker change (ruling N) | "BITCOIN IS DOWN MORE THAN 3%, FALLING BELOW THE 72,000 MARK TO ITS LOWEST LEVEL SINCE AUGUST. STRATEGY." |

**Stage 1: 587 moments -> 265 usable** (package.usable; 322 lost)

A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).

**Stage 1a: not eligible on screen (181 moments)**

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 131 | 108 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it in an aw…" |
| 39 | 26 | `not_statement`: ends on a question | "So look, I think CZ is the best counter trade indicator right now. If CZ gets bullish on the timeline, guys, buckle up, all right?" |
| 33 | 17 | `opener`: opens on a pronoun or reply word that needs what came before (stand_alone.opener) | "Okay, the number one rule of crypto, right? Every time you want to fade the cycle. The number one rule is don't fade the cycle." |
| 4 | 3 | `start_case`: starts lower-case | "it's a it's an i struggle to find the right word to describe it, but bitcoin is not for gambling with. That's not what it's for. it's for p…" |
| 1 | 1 | `too_short`: < 5 words | "Secure. That's it." |

**Stage 1b: the other usable() reasons (141 moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 98 | N s: over the 20.0 s per source video (L-u) or unmeasured | "But ultimately, I think Bitcoin is objectively the best form of money that humanity is ever discovered. It has these unique monetary proper…" |
| 38 | time-sensitive words from a source older than 24.0 h (L-v 3) | "Five years after Bitcoin peaked at 69,000, Bitcoin is up 6%." |
| 5 | delivered in the previous 24 h (or overlaps a delivered moment) | "Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin wins, open source wins. And eve…" |

**Stage 2: 265 usable -> 12 cleared step A** (L-s on the moment's own context; 24 screened, 12 failed)

**Stage 2: step A rules (12 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 8 | 6 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "Bitcoin is, it's immune to that. There will never be an asteroid that you will find a bunch of Bitcoin on." ('that' -> 'asteroid mining or manufacturing invalidating gol…', changes the assertion: yes) |
| 4 | 3 | `NOT_OWN_SINCERE`: not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...) | "In the world of Bitcoin, security isn't just a feature. It's the entire foundation." (view: ad_read) |
| 1 | 1 | `RETRACTION`: retracted or corrected later | "My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank owns the money and they could j…" (retraction: It is actually his second biggest fear, as concerns about A…) |
| 1 | 0 | `STALE_TIME`: time words stale on the show date (L-v 3) | "Days like today are when people get shaken out. Bitcoin dumps on a scandal that has nothing to do with it. You panic or a bill comes due, a…" (time_ok: uncertain) |

**Stage 3: 12 cleared -> 7 pass L-v 2 + CUTTABLE (5 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 4 | L-v 2 FAIL | "The Bitcoin ETFs, in my opinion, first people became bitcoins individually. And then they would go to their investment committee and say, h…" (the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoiners"]}) |
| 1 | not CUTTABLE: OUT edge | "With Bitcoin, no one can take it from you." (OUT: the window ends at the clip: no word after it) |

Every stage-3 loss, exactly:
- Anthony Pompliano: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoiners"]}
- Guy Swann: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- What Bitcoin Did: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- BTC Sessions: not CUTTABLE: OUT edge: OUT: the window ends at the clip: no word after it
- Bankless: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoin-", "Hoddle"]}; speakers measured inside: ['speaker_0', 'speaker_1']

**Stage 4: 7 cuttable -> 4 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 1 | FAIL: 0 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin." |
| 1 | FAIL: 70 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "The Bitcoin capital markets are still in their early stages. But the opportunity to put Bitcoin to work through staking, collateral, and de…" |
| 1 | FAIL: no cut after the trimmed word 'And': the trimmed word 'And' cannot be cut cleanly: no measured pause between it and 'Wall' (co-articulated) | "[And trimmed] Wall Street's answer is diversification. But the ultimate diversification is decentralization. Bitcoin is an asset that can b…" |

Trimmed variants (ruling 33 part 2): 52 of the 166 left out by STAND_ALONE joined the usable moments; 1 cleared to here and failed the trimmed cut (a), at any place:
- Simply Bitcoin: FAIL: no trimmed cut was reached: no cut after the trimmed word 'And': the trimmed word 'And' cannot be cut cleanly: no measured pause between it and 'Wall' (co-articulated): "[And trimmed] Wall Street's answer is diversification. But the ultimate diversification is decentralization. Bitcoin is…"

**Stage 4b: step A from the second vendor (order 06:22 item 45): 0 of 6 pass**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 6 | FAIL: STEP_A_UNAVAILABLE: ValueError | "I will bet you one Bitcoin that RSA has broken in 10 years, and I'll bet you half a Bitcoin that it's broken in five years. That's the leve…" |

**Stage 5: the angle step and the line-ups.** why_none: '0 cleared moments pass the second pass, CUTTABLE and step A from both vendors, from fewer than 3 channels'; angles: 0 from None

The moments offered to the angle step:

Together 0 s from 0 channels (a trimmed variant's seconds not counted).
