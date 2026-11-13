Build `ledger_20261113_134638`: code 886775c5+a051121925b2, render clock 2026-11-13T13:46:38.521845+00:00.
Adapter (pp-ingest, before the ledger rows): excluded {"altcoin or not about Bitcoin": 36, "hard exclusion flag (L-u)": 118, "speaker change inside (caption marker)": 28}.

**Stage 0: 503 ledger rows -> 305 moments (198 not moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 78 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 50 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched around the row's time) | "and they're in that safe and it's like yeah yeah yeah it's like what is that safe made of glass I think I've got a hammer back there let me…" |
| 35 | duplicate: the same speech as a kept moment (time overlap in the same video) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software and Bitcoin has…" |
| 32 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it runs N s > N s (ruling N: the clip length limit) | "Um I find Bitcoin super boring, but I'm always like that's cool because it's boring. Like that was the cool part because it was so boring. …" |
| 2 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched -N-N s) | "Bitcoin lost the 50we moving average. It's now right in between the 50we and the 200week moving average." |
| 1 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it holds a caption speaker marker at N s: a measured speaker change (ruling N) | "BITCOIN IS DOWN MORE THAN 3%, FALLING BELOW THE 72,000 MARK TO ITS LOWEST LEVEL SINCE AUGUST. STRATEGY." |

**Stage 1: 305 moments -> 169 usable** (package.usable; 136 lost)

A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).

**Stage 1a: not eligible on screen (88 moments)**

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 52 | 36 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it in an aw…" |
| 29 | 20 | `not_statement`: ends on a question | "We don't have Satoshi over here selling his coins, you know? So I think that's the, and that's the issue too with, you know, treasury compa…" |
| 21 | 10 | `opener`: opens on a pronoun or reply word that needs what came before (stand_alone.opener) | "Okay, the number one rule of crypto, right? Every time you want to fade the cycle. The number one rule is don't fade the cycle." |
| 3 | 3 | `start_case`: starts lower-case | "it's a it's an i struggle to find the right word to describe it, but bitcoin is not for gambling with. That's not what it's for. it's for p…" |
| 1 | 1 | `too_short`: < 5 words | "Secure. That's it." |

**Stage 1b: the other usable() reasons (48 moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 45 | N s: over the 20.0 s per source video (L-u) or unmeasured | "But in another tweet, you said something super interesting that it was in 2020, if you had $100,000. it could buy you about 25,900 pounds o…" |
| 3 | delivered in the previous 24 h (or overlaps a delivered moment) | "Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin wins, open source wins. And eve…" |

**Stage 2: 169 usable -> 13 cleared step A** (L-s on the moment's own context; 24 screened, 11 failed)

**Stage 2: step A rules (11 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 7 | 6 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "Bitcoin is, it's immune to that. There will never be an asteroid that you will find a bunch of Bitcoin on." ('that' -> 'manufacturing gold or finding huge gold deposits …', changes the assertion: yes) |
| 3 | 3 | `NOT_OWN_SINCERE`: not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...) | "Bitcoin is only generational wealth if it can be passed down." (view: ad_read) |
| 1 | 1 | `STALE_TIME`: time words stale on the show date (L-v 3) | "Days like today are when people get shaken out. Bitcoin dumps on a scandal that has nothing to do with it. You panic or a bill comes due, a…" (time_ok: uncertain) |
| 1 | 0 | `RETRACTION`: retracted or corrected later | "[But trimmed] this was not, as a as again, i'd like to point out, in bitcoin, we like to think no one is in charge of it. No one has influe…" (retraction: But underneath that that's not how people work.) |

**Stage 3: 13 cleared -> 7 pass L-v 2 + CUTTABLE (6 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 5 | L-v 2 FAIL | "Like core scientific. They're not even Bitcoin mining anymore. They said, no, we're going to be data centers." (the two recognisers disagree on {"numbers": [], "negations": ["no"], "names": ["Nah"]}) |
| 1 | not cuttable at an edge (ruling C / 7) | "[But trimmed] if you were to find one asteroid that had huge gold deposits in it, you could double the world's gold supply overnight. You c…" ((edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)) |

Every stage-3 loss, exactly:
- What Bitcoin Did: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": ["no"], "names": ["Nah"]}
- Guy Swann: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- What Bitcoin Did: L-v 2 FAIL: (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)
- What Bitcoin Did: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- Anthony Pompliano: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoiners"]}
- CoinTelegraph: not cuttable at an edge (ruling C / 7): (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)

**Stage 4: 7 cuttable -> 5 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 1 | FAIL: 0 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin." |
| 1 | FAIL: no cut after the trimmed word 'So': the trimmed word 'So' cannot be cut cleanly: no measured pause between it and 'if' (co-articulated) | "[So trimmed] if you look at the average income in the lowest 20 economies like $40 a month. So when people go, dude, it's like it's only li…" |

Trimmed variants (ruling 33 part 2): 33 of the 112 left out by STAND_ALONE joined the usable moments; 1 cleared to here and failed the trimmed cut (a), at any place:
- What Bitcoin Did: FAIL: no trimmed cut was reached: no cut after the trimmed word 'So': the trimmed word 'So' cannot be cut cleanly: no measured pause between it and 'if' (co-articulated): "[So trimmed] if you look at the average income in the lowest 20 economies like $40 a month. So when people go, dude, it…"

**Stage 4b: step A from the second vendor (order 06:22 item 45): 5 of 6 pass**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 1 | FAIL: NOT_OWN_SINCERE | "In the world of Bitcoin, security isn't just a feature. It's the entire foundation." |

**Stage 5: the angle step and the line-ups.** why_none: "no readable angles: ValueError: exactly {'angles': [1-3 items]}"; angles: 0 from None

The moments offered to the angle step:
- What Bitcoin Did (acxge3Orsv8), 9.46 s, can open: True: "I will bet you one Bitcoin that RSA has broken in 10 years, and I'll bet you half a Bitcoin that it's broken in five years. That's the level of convi…"
- CNBC Television (GXWj2JO9bz8), 13.94 s, can open: True: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- Bitcoin Mechanic (WghTi5Ep4ro), 7.26 s, can open: True: "Bitcoin on the Blake 2B chain is incredible. And I say that not to pump it. Don't buy any if you don't want to buy any."
- The Bitcoin Layer (lYca6Bg0FkM), 4.8 s, can open: True: "Bitcoin started turning though before liquidity turned red. And that's an important caveat here."
- Altcoin Daily (HWuMai_mAug), 6.93 s, can open: False: "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin."

Together 42.39 s from 5 channels (a trimmed variant's seconds not counted).

The build's own log from the angle step on:
```
no package (no readable angles: ValueError: exactly {'angles': [1-3 items]}); usable 169, cleared 13
  spend (ruling 48): $6.03 of $12.00 vendor-reported after this build (before it: $6.03)
```
