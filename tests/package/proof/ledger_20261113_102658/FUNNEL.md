Build `ledger_20261113_102658`: code bfac353e+1093f20ef0ad, render clock 2026-11-13T10:26:58.811701+00:00.
Adapter (pp-ingest, before the ledger rows): excluded {"hard exclusion flag (L-u)": 123, "altcoin or not about Bitcoin": 30, "speaker change inside (caption marker)": 22}.

**Stage 0: 510 ledger rows -> 313 moments (197 not moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 78 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 46 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched around the row's time) | "and they're in that safe and it's like yeah yeah yeah it's like what is that safe made of glass I think I've got a hammer back there let me…" |
| 36 | duplicate: the same speech as a kept moment (time overlap in the same video) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software and Bitcoin has…" |
| 35 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it runs N s > N s (ruling N: the clip length limit) | "Um I find Bitcoin super boring, but I'm always like that's cool because it's boring. Like that was the cool part because it was so boring. …" |
| 1 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it holds a caption speaker marker at N s: a measured speaker change (ruling N) | "BITCOIN IS DOWN MORE THAN 3%, FALLING BELOW THE 72,000 MARK TO ITS LOWEST LEVEL SINCE AUGUST. STRATEGY." |
| 1 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched -N-N s) | "Um I think that Bitcoin will go lower than 57k during Trump's term, okay? I think it will." |

**Stage 1: 313 moments -> 176 usable** (package.usable; 137 lost)

A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).

**Stage 1a: not eligible on screen (88 moments)**

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 52 | 36 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it in an aw…" |
| 28 | 19 | `not_statement`: ends on a question | "We don't have Satoshi over here selling his coins, you know? So I think that's the, and that's the issue too with, you know, treasury compa…" |
| 22 | 11 | `opener`: opens on a pronoun or reply word that needs what came before (stand_alone.opener) | "No machine can argue with that. It is the heaviest concentration, just like the sun is the heaviest local thing for us." |
| 3 | 3 | `start_case`: starts lower-case | "it's a it's an i struggle to find the right word to describe it, but bitcoin is not for gambling with. That's not what it's for. it's for p…" |
| 1 | 1 | `too_short`: < 5 words | "Secure. That's it." |

**Stage 1b: the other usable() reasons (49 moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 46 | N s: over the 20.0 s per source video (L-u) or unmeasured | "But in another tweet, you said something super interesting that it was in 2020, if you had $100,000. it could buy you about 25,900 pounds o…" |
| 3 | delivered in the previous 24 h (or overlaps a delivered moment) | "Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin wins, open source wins. And eve…" |

**Stage 2: 176 usable -> 16 cleared step A** (L-s on the moment's own context; 24 screened, 8 failed)

**Stage 2: step A rules (8 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 5 | 4 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "Bitcoin is, it's immune to that. There will never be an asteroid that you will find a bunch of Bitcoin on." ('that' -> 'manufacturing gold or asteroid mining vastly incr…', changes the assertion: yes) |
| 4 | 3 | `NOT_OWN_SINCERE`: not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...) | "In the world of Bitcoin, security isn't just a feature. It's the entire foundation." (view: ad_read) |

**Stage 3: 16 cleared -> 11 pass L-v 2 + CUTTABLE (5 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 4 | L-v 2 FAIL | "Like, you know, I've run a Bitcoin meetup for 10 years now. And I've interacted with thousands of Bitcoiners, as I'm sure you have, Giacomo…" (speakers measured inside: ['speaker_0', 'speaker_1']) |
| 1 | not CUTTABLE: OUT edge | "Php, server vulnerability, 70 % of the internet. Wordpress, cooked, 40 % of the internet. Bang, btc, paper foundation. I was just like, thi…" (OUT: the recogniser's sentence continues past the clip) |

Every stage-3 loss, exactly:
- Guy Swann: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- What Bitcoin Did: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": ["no"], "names": ["Nah"]}
- What Bitcoin Did: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- What Bitcoin Did: not CUTTABLE: OUT edge: OUT: the recogniser's sentence continues past the clip
- Anthony Pompliano: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoiners"]}

**Stage 4: 11 cuttable -> 7 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 2 | FAIL: 0 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin." |
| 1 | FAIL: 50 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets …" |
| 1 | FAIL: 40 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "In the first week of November, about $1.28 billion left the spot Bitcoin ETFs, the most since late June. And more went out on the following…" |

**Stage 5: the angle step and the line-ups.** why_none: "no angle gave a package: angle 1: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 2: the clips alone fail (ratings / joins): swapped {'fda2c6856295ea156a9d': '44216aab8847bd718241'}, re-judged (ruling 41); angle 2: the clips alone fail (ratings / joins): dropped ['44216aab8847bd718241'], no swap fits the line-up rules: re-lined; angle 2: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 3: the clips alone fail (ratings / joins): swapped {'2e77a0a7af2aab66a3a4': '06f73bef2e37ba14bee4', 'b805e69a19c24703d799': 'a45d26b88cd5b176ae13'}, re-judged (ruling 41); angle 3: the clips alone fail (ratings / joins): dropped ['06f73bef2e37ba14bee4', 'a45d26b88cd5b176ae13'], no swap fits the line-up rules: re-lined; angle 3: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"; angles: 3 from heimdall:deepseek/deepseek-v4.1-flash

The moments offered to the angle step:
- Bitcoin Mechanic (WghTi5Ep4ro), 7.26 s, can open: True: "Bitcoin on the Blake 2B chain is incredible. And I say that not to pump it. Don't buy any if you don't want to buy any."
- What Bitcoin Did (acxge3Orsv8), 9.46 s, can open: True: "I will bet you one Bitcoin that RSA has broken in 10 years, and I'll bet you half a Bitcoin that it's broken in five years. That's the level of convi…"
- Strategy (MicroStrategy) (xfLi0cH_VqM), 13.82 s, can open: False: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- CNBC Television (GXWj2JO9bz8), 13.94 s, can open: True: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- Coin Bureau (RTck1cfw3GY), 15.96 s, can open: True: "Michael Saylor just had a pretty rough day. Strategy has been officially booted from MSCI's indexes. That means index funds now have to dump billions…"
- Coin Bureau (RTck1cfw3GY), 9.7 s, can open: True: "The funds are selling strategies stock. The Bitcoin never changes hands. Nothing in MSCI's decision forces strategy to sell its Bitcoin."
- Altcoin Daily (HWuMai_mAug), 6.93 s, can open: False: "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin."
- Coin Bureau (RTck1cfw3GY), 19.53 s, can open: False: "In the first week of November, about $1.28 billion left the spot Bitcoin ETFs, the most since late June. And more went out on the following Monday an…"
- The Bitcoin Layer (lYca6Bg0FkM), 4.8 s, can open: True: "Bitcoin started turning though before liquidity turned red. And that's an important caveat here."
- Simply Bitcoin (WTCwyxW-lHk), 18.56 s, can open: False: "It's like, you know, the idea of what doesn't kill you makes you stronger. You just die. And like I don't think Bitcoin's going to die. I think it's …"
- Scott Melker (mKNAcOFMYD4), 8.76 s, can open: True: "My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank owns the money and they could just take i…"

Together 128.72 s from 9 channels.
- angle: "Bitcoin is a nonpartisan path to financial freedom, and the industry is bleeding into it because banks can't be trusted." moments 4
- angle: "Strategy's MSCI boot means index funds dump its shares, but Bitcoin keeps attracting believers and capital." moments 4
- angle: "Treasury companies and believers keep bleeding into Bitcoin even when ETF money leaves and liquidity turns." moments 4

The build's own log from the angle step on:
```
  3 angles from heimdall:deepseek/deepseek-v4.1-flash (336 s)
  angle 2 line-up 1 (3 clips, 43.3 s): clips alone FAIL {'hook': 3, 'clip_01': 4, 'clip_02': 5} flagged ['hook -> clip_01'] (369 s)
  angle 2 line-up 2 (3 clips, 37.0 s): clips alone FAIL {'hook': 3, 'clip_01': 5, 'clip_02': 4} flagged ['hook -> clip_01'] (401 s)
  angle 3 line-up 1 (3 clips, 42.9 s): clips alone FAIL {'hook': 3, 'clip_01': 4, 'clip_02': 5} flagged ['hook -> clip_01', 'clip_01 -> clip_02'] (428 s)
  angle 3 line-up 2 (3 clips, 40.7 s): clips alone FAIL {'hook': 3, 'clip_01': 4, 'clip_02': 5} flagged ['hook -> clip_01', 'clip_01 -> clip_02'] (450 s)
  search: 4 line-up(s) of 8, $0.06 reported / $0.71 estimate (ruling 41: $3.00 reported per build)
no package (no angle gave a package: angle 1: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 2: the clips alone fail (ratings / joins): swapped {'fda2c6856295ea156a9d': '44216aab8847bd718241'}, re-
```
