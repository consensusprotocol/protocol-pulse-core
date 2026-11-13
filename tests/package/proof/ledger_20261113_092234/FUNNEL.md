Build `ledger_20261113_092234`: code 56582b6b+188c19f04be6, render clock 2026-11-13T09:22:34.044539+00:00.
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

**Stage 1: 313 moments -> 95 usable** (package.usable; 218 lost)

A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).

**Stage 1a: not eligible on screen (187 moments)**

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 125 | 92 | `no_bitcoin`: does not name Bitcoin: regex `\b(bitcoins?|btcs?)\b` (T11, the old story selector's subject screen; 'Bitcoiners', 'sats', 'Satoshi' do not count) | "There's eight and a half billion people. We all have a money problem. It's not like we sort of maybe have a money problem." |
| 52 | 29 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it in an aw…" |
| 35 | 15 | `not_statement`: ends on a question | "We don't have Satoshi over here selling his coins, you know? So I think that's the, and that's the issue too with, you know, treasury compa…" |
| 22 | 4 | `opener`: opens on a pronoun or reply word that needs what came before (stand_alone.opener) | "But right now, if AI is the most volatile thing in the market, which right now, I mean, look, ASRs move more than Bitcoin did." |
| 3 | 1 | `start_case`: starts lower-case | "it's a it's an i struggle to find the right word to describe it, but bitcoin is not for gambling with. That's not what it's for. it's for p…" |
| 1 | 0 | `too_short`: < 5 words | "Secure. That's it." |

**Stage 1b: the other usable() reasons (31 moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 28 | N s: over the 20.0 s per source video (L-u) or unmeasured | "But I think this MSCI Global Index ruling shows one thing. that not everyone is really embracing Bitcoin. And again, I keep bringing up the…" |
| 3 | delivered in the previous 24 h (or overlaps a delivered moment) | "Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin wins, open source wins. And eve…" |

**Stage 2: 95 usable -> 17 cleared step A** (L-s on the moment's own context; 24 screened, 7 failed)

**Stage 2: step A rules (7 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 4 | 4 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "Bitcoin is, it's immune to that. There will never be an asteroid that you will find a bunch of Bitcoin on." ('that' -> 'manufacturing gold or asteroid mining vastly incr…', changes the assertion: yes) |
| 2 | 2 | `NOT_OWN_SINCERE`: not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...) | "Bitcoin is only generational wealth if it can be passed down." (view: ad_read) |
| 1 | 1 | `RETRACTION`: retracted or corrected later | "My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank owns the money and they could j…" (retraction: My second biggest fear and th this is becoming it's startin…) |

**Stage 3: 17 cleared -> 12 pass L-v 2 + CUTTABLE (5 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 4 | L-v 2 FAIL | "Like, you know, I've run a Bitcoin meetup for 10 years now. And I've interacted with thousands of Bitcoiners, as I'm sure you have, Giacomo…" (speakers measured inside: ['speaker_0', 'speaker_1']) |
| 1 | not CUTTABLE: OUT edge | "Php, server vulnerability, 70 % of the internet. Wordpress, cooked, 40 % of the internet. Bang, btc, paper foundation. I was just like, thi…" (OUT: the recogniser's sentence continues past the clip) |

Every stage-3 loss, exactly:
- Guy Swann: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- What Bitcoin Did: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": ["no"], "names": ["Nah"]}
- Anthony Pompliano: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoiners"]}
- What Bitcoin Did: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- What Bitcoin Did: not CUTTABLE: OUT edge: OUT: the recogniser's sentence continues past the clip

**Stage 4: 12 cuttable -> 8 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 2 | FAIL: 0 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin." |
| 1 | FAIL: 50 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets …" |
| 1 | FAIL: 40 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "In the first week of November, about $1.28 billion left the spot Bitcoin ETFs, the most since late June. And more went out on the following…" |

**Stage 5: the angle step and the line-ups.** why_none: 'stopped in angle 3 of 3: 1133 s of 900 s wall / $0.42 of $1.50 reported / $1.90 of the $5.00 estimate ceiling (ruling 5, 22:40)'; angles: 3 from xai:grok-4.20-0309-reasoning

The moments offered to the angle step:
- Bitcoin Mechanic (WghTi5Ep4ro), 7.26 s, can open: True: "Bitcoin on the Blake 2B chain is incredible. And I say that not to pump it. Don't buy any if you don't want to buy any."
- Coin Bureau (RTck1cfw3GY), 9.7 s, can open: True: "The funds are selling strategies stock. The Bitcoin never changes hands. Nothing in MSCI's decision forces strategy to sell its Bitcoin."
- Strategy (MicroStrategy) (xfLi0cH_VqM), 13.82 s, can open: False: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- Coin Bureau (RTck1cfw3GY), 19.53 s, can open: False: "In the first week of November, about $1.28 billion left the spot Bitcoin ETFs, the most since late June. And more went out on the following Monday an…"
- What Bitcoin Did (acxge3Orsv8), 9.46 s, can open: True: "I will bet you one Bitcoin that RSA has broken in 10 years, and I'll bet you half a Bitcoin that it's broken in five years. That's the level of convi…"
- The Bitcoin Layer (lYca6Bg0FkM), 4.8 s, can open: True: "Bitcoin started turning though before liquidity turned red. And that's an important caveat here."
- Altcoin Daily (HWuMai_mAug), 6.93 s, can open: False: "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin."
- CNBC Television (GXWj2JO9bz8), 13.94 s, can open: True: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- Simply Bitcoin (WTCwyxW-lHk), 6.7 s, can open: True: "Nobody tells anybody put a, you know, duffel bag with all their gold or all their cash in their mattress. But for some reason, everyone said you got …"
- What Bitcoin Did (acxge3Orsv8), 2.36 s, can open: True: "For many people, you're the bitcoin guy."
- What Bitcoin Did (acxge3Orsv8), 3.68 s, can open: True: "In the world of Bitcoin, security isn't just a feature. It's the entire foundation."
- Simply Bitcoin (WTCwyxW-lHk), 18.56 s, can open: False: "It's like, you know, the idea of what doesn't kill you makes you stronger. You just die. And like I don't think Bitcoin's going to die. I think it's …"

Together 116.74 s from 8 channels.
- angle: "Bitcoin is not going to die as it inspires high conviction, turns before liquidity does, and its Bitcoin never changes hands despite stock sales." moments 4
- angle: "Bitcoin and crypto are not partisan issues but about modernizing financial markets and creating financial freedom for billions as industry capital bleeds to it despite ETF outflows." moments 3
- angle: "Security is the foundation of Bitcoin ensuring it will not die as treasury companies bleed to it and institutions buy even amid major ETF outflows." moments 4

The build's own log from the angle step on:
```
  3 angles from xai:grok-4.20-0309-reasoning (671 s)
  angle 1 line-up 1 (4 clips, 42.5 s): clips alone FAIL {'hook': 4, 'clip_01': 5, 'clip_02': 1, 'clip_03': 4} flagged ['clip_01 -> clip_02', 'clip_02 -> clip_03'] (839 s)
  angle 3 line-up 1 (3 clips, 41.8 s): clips alone PASS {'hook': 4, 'clip_01': 5, 'clip_02': 4} flagged ['hook -> clip_01'] (888 s)
no package (stopped in angle 3 of 3: 1133 s of 900 s wall / $0.42 of $1.50 reported / $1.90 of the $5.00 estimate ceiling (ruling 5, 22:40)); usable 95, cleared 17
```
