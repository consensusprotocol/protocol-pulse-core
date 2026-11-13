Build `ledger_20261113_121442`: code 60f2eaed+4aac3ae936cc, render clock 2026-11-13T12:14:42.181888+00:00.
Adapter (pp-ingest, before the ledger rows): excluded {"altcoin or not about Bitcoin": 36, "hard exclusion flag (L-u)": 118, "speaker change inside (caption marker)": 28}.

**Stage 0: 521 ledger rows -> 308 moments (213 not moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 78 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 46 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched around the row's time) | "and they're in that safe and it's like yeah yeah yeah it's like what is that safe made of glass I think I've got a hammer back there let me…" |
| 36 | duplicate: the same speech as a kept moment (time overlap in the same video) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software and Bitcoin has…" |
| 32 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it runs N s > N s (ruling N: the clip length limit) | "Um I find Bitcoin super boring, but I'm always like that's cool because it's boring. Like that was the cool part because it was so boring. …" |
| 19 | SUPPLY: no word record yet (no word record in the store; no sentence-ready window record) | n/a |
| 1 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it holds a caption speaker marker at N s: a measured speaker change (ruling N) | "BITCOIN IS DOWN MORE THAN 3%, FALLING BELOW THE 72,000 MARK TO ITS LOWEST LEVEL SINCE AUGUST. STRATEGY." |
| 1 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched -N-N s) | "Um I think that Bitcoin will go lower than 57k during Trump's term, okay? I think it will." |

**Stage 1: 308 moments -> 173 usable** (package.usable; 135 lost)

A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).

**Stage 1a: not eligible on screen (88 moments)**

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 52 | 36 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it in an aw…" |
| 28 | 19 | `not_statement`: ends on a question | "We don't have Satoshi over here selling his coins, you know? So I think that's the, and that's the issue too with, you know, treasury compa…" |
| 22 | 11 | `opener`: opens on a pronoun or reply word that needs what came before (stand_alone.opener) | "No machine can argue with that. It is the heaviest concentration, just like the sun is the heaviest local thing for us." |
| 3 | 3 | `start_case`: starts lower-case | "it's a it's an i struggle to find the right word to describe it, but bitcoin is not for gambling with. That's not what it's for. it's for p…" |
| 1 | 1 | `too_short`: < 5 words | "Secure. That's it." |

**Stage 1b: the other usable() reasons (47 moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 44 | N s: over the 20.0 s per source video (L-u) or unmeasured | "But in another tweet, you said something super interesting that it was in 2020, if you had $100,000. it could buy you about 25,900 pounds o…" |
| 3 | delivered in the previous 24 h (or overlaps a delivered moment) | "Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin wins, open source wins. And eve…" |

**Stage 2: 173 usable -> 13 cleared step A** (L-s on the moment's own context; 24 screened, 11 failed)

**Stage 2: step A rules (11 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 7 | 6 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "Bitcoin is, it's immune to that. There will never be an asteroid that you will find a bunch of Bitcoin on." ('that' -> 'manufacturing gold or mining asteroids to increas…', changes the assertion: yes) |
| 3 | 3 | `NOT_OWN_SINCERE`: not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...) | "[But trimmed] if you were to find one asteroid that had huge gold deposits in it, you could double the world's gold supply overnight. You c…" (view: hypothetical) |
| 2 | 1 | `STALE_TIME`: time words stale on the show date (L-v 3) | "Michael Saylor just had a pretty rough day. Strategy has been officially booted from MSCI's indexes. That means index funds now have to dum…" (time_ok: no) |

**Stage 3: 13 cleared -> 9 pass L-v 2 + CUTTABLE (4 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 3 | L-v 2 FAIL | "Like, you know, I've run a Bitcoin meetup for 10 years now. And I've interacted with thousands of Bitcoiners, as I'm sure you have, Giacomo…" (speakers measured inside: ['speaker_0', 'speaker_1']) |
| 1 | NOT MEASURED: CalledProcessError: Command '['yt-dlp', '-q', '--no-playlist', '-f', 'bestaudio', '--download-sections', '*400.23-411.20', '--force-keyframes-at-cuts', '-o', '/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0- | "[So trimmed] we've been the better part of this year in this $300 window. Sometimes you think Bitcoin can be boring." ((edge detail not recomputed offline: CalledProcessError: Command '['yt-dlp', '-q', '--no-playlist', '-f', 'bestaudio', '--download-sections', '*400.23-411.20', '--force-keyframe)) |

Every stage-3 loss, exactly:
- Guy Swann: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- Anthony Pompliano: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoiners"]}
- What Bitcoin Did: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- DataDash: NOT MEASURED: CalledProcessError: Command '['yt-dlp', '-q', '--no-playlist', '-f', 'bestaudio', '--download-sections', '*400.23-411.20', '--force-keyframes-at-cuts', '-o', '/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-: (edge detail not recomputed offline: CalledProcessError: Command '['yt-dlp', '-q', '--no-playlist', '-f', 'bestaudio', '--download-sections', '*400.23-411.20', '--force-keyframe)

**Stage 4: 9 cuttable -> 6 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 1 | FAIL: 0 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin." |
| 1 | FAIL: 50 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets …" |
| 1 | FAIL: no cut after the trimmed word 'So': the trimmed word 'So' cannot be cut cleanly: no measured pause between it and 'if' (co-articulated) | "[So trimmed] if you look at the average income in the lowest 20 economies like $40 a month. So when people go, dude, it's like it's only li…" |

Trimmed variants (ruling 33 part 2): 34 of the 113 left out by STAND_ALONE joined the usable moments; 1 cleared to here and failed the trimmed cut (a), at any place:
- What Bitcoin Did: FAIL: no trimmed cut was reached: no cut after the trimmed word 'So': the trimmed word 'So' cannot be cut cleanly: no measured pause between it and 'if' (co-articulated): "[So trimmed] if you look at the average income in the lowest 20 economies like $40 a month. So when people go, dude, it…"

**Stage 4b: step A from the second vendor (order 06:22 item 45): 7 of 8 pass**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 1 | FAIL: NOT_OWN_SINCERE | "In the world of Bitcoin, security isn't just a feature. It's the entire foundation." |

**Stage 5: the angle step and the line-ups.** why_none: "no angle gave a package: angle 1: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 2: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 3: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"; angles: 3 from xai:grok-4.20-0309-reasoning

The moments offered to the angle step:
- Strategy (MicroStrategy) (xfLi0cH_VqM), 13.82 s, can open: False: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- Scott Melker (mKNAcOFMYD4), 8.76 s, can open: True: "My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank owns the money and they could just take i…"
- The Bitcoin Layer (lYca6Bg0FkM), 4.8 s, can open: True: "Bitcoin started turning though before liquidity turned red. And that's an important caveat here."
- Altcoin Daily (HWuMai_mAug), 6.93 s, can open: False: "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin."
- What Bitcoin Did (acxge3Orsv8), 9.46 s, can open: True: "I will bet you one Bitcoin that RSA has broken in 10 years, and I'll bet you half a Bitcoin that it's broken in five years. That's the level of convi…"
- CNBC Television (GXWj2JO9bz8), 13.94 s, can open: True: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- Bitcoin Mechanic (WghTi5Ep4ro), 7.26 s, can open: True: "Bitcoin on the Blake 2B chain is incredible. And I say that not to pump it. Don't buy any if you don't want to buy any."

Together 64.97 s from 7 channels (a trimmed variant's seconds not counted).
- angle: "Bitcoin and crypto are not partisan issues but about modernizing financial markets to create financial freedom for billions, which is why we Bitcoin instead of trusting banks as the industry bleeds t…" moments 4
- angle: "Bitcoin creates financial freedom for 8 billion people by modernizing markets as companies bleed to it and we escape bank ownership of our money." moments 4
- angle: "We Bitcoin to protect against banks owning our money and create financial freedom for billions as everything in the industry bleeds to it." moments 4

The build's own log from the angle step on:
```
  3 angles from xai:grok-4.20-0309-reasoning (1277 s)
  search: 0 line-up(s) of 8, $0.58 reported / $1.38 estimate (ruling 41: $3.00 reported per build)
no package (no angle gave a package: angle 1: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 2: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 3: no line-
  spend (ruling 48): $5.85 of $12.00 vendor-reported after this build (before it: $5.26)
```
