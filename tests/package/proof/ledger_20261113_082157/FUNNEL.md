Build `ledger_20261113_082157`: code 6175104e+2f0c59402644, render clock 2026-11-13T08:21:57.711773+00:00.
Adapter (pp-ingest, before the ledger rows): excluded {"hard exclusion flag (L-u)": 123, "altcoin or not about Bitcoin": 30, "speaker change inside (caption marker)": 22}.

**Stage 0: 510 ledger rows -> 178 moments (332 not moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 255 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 26 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched around the row's time) | "Like so it's not it's not just like oh China banned Bitcoin or whatever you know it's not the the madeup stuff that we've had previously bu…" |
| 23 | does not re-anchor: the anchored text is not whole sentences of the word record (N word(s) before it and N after it inside its edge sentences; at most N) | "But you talk to someone in Venezuela and they're like, wait, oh, you're like, oh, it's volatile. It's like, what do you mean it's volatile?…" |
| 21 | duplicate: the same speech as a kept moment (time overlap in the same video) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software and Bitcoin has…" |
| 6 | SUPPLY: no word record yet (no word record in the store; no sentence-ready window record) | n/a |
| 1 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched -N-N s) | "Um I think that Bitcoin will go lower than 57k during Trump's term, okay? I think it will." |

The rows that are not whole sentences of the word record, exactly (words of the edge sentences outside the anchored text, before / after, and why each stays out):
- 0 before / 6 after: "Now, you don't you don't need the skill. You don't need the time. You you you can devote …" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 6 after it inside its edge sentences; at most 3))
- 0 before / 6 after: "So in Bitcoin, how I look at it is we have kings. We have Michael Sailor came along and a…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 6 after it inside its edge sentences; at most 3))
- 0 before / 8 after: "But when you're a business that deals with money, specifically a bearer asset, you don't …" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 8 after it inside its edge sentences; at most 3))
- 0 before / 9 after: "But you talk to someone in Venezuela and they're like, wait, oh, you're like, oh, it's vo…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 9 after it inside its edge sentences; at most 3))
- 9 before / 0 after: "So whether it's a bond or preferred equity or for our companies common equity that have m…" (why: the anchored text is not whole sentences of the word record (9 word(s) before it and 0 after it inside its edge sentences; at most 3))
- 0 before / 9 after: "Do I think that the bare market is officially or sorry, the bull market is officially ove…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 9 after it inside its edge sentences; at most 3))
- 0 before / 9 after: "We are seeing a lot of shorts pile up above the current price action all the way up into …" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 9 after it inside its edge sentences; at most 3))
- 0 before / 11 after: "I think like in the grand scheme of global financial markets, you look at total global as…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 11 after it inside its edge sentences; at most 3))
- 0 before / 11 after: "So MSCI didn't force any Bitcoin selling this week. But it has taken firepower away from …" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 11 after it inside its edge sentences; at most 3))
- 2 before / 12 after: "I think we we we can rest assured that we are relatively immune, not absolutely but relat…" (why: the anchored text is not whole sentences of the word record (2 word(s) before it and 12 after it inside its edge sentences; at most 3))
- 14 before / 0 after: "Just last week, Binance warned that there's a newly published iPhone flaw that it could e…" (why: the anchored text is not whole sentences of the word record (14 word(s) before it and 0 after it inside its edge sentences; at most 3))
- 16 before / 0 after: "I'm not really sure I fully believe this, but it's when you have these major IPOs like Sp…" (why: the anchored text is not whole sentences of the word record (16 word(s) before it and 0 after it inside its edge sentences; at most 3))
- 22 before / 0 after: "I just realized that trillions of dollars have to come into this asset if we want it to b…" (why: the anchored text is not whole sentences of the word record (22 word(s) before it and 0 after it inside its edge sentences; at most 3))
- 0 before / 23 after: "And so volatility then ultimately can create opportunities you know like if you remain hy…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 23 after it inside its edge sentences; at most 3))
- 0 before / 28 after: "It's like you know the idea of u what doesn't kill you makes you stronger you just die an…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 28 after it inside its edge sentences; at most 3))
- 0 before / 32 after: "And so Strive just voting on what's going to maximize shareholder value period I think is…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 32 after it inside its edge sentences; at most 3))
- 0 before / 39 after: "So we could ride out any historical bare market without even have to sell a single Bitcoi…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 39 after it inside its edge sentences; at most 3))
- 27 before / 13 after: "For all the cats that are that don't have a voice yet, but I know what I got Bitcoin as i…" (why: the anchored text is not whole sentences of the word record (27 word(s) before it and 13 after it inside its edge sentences; at most 3))
- 0 before / 47 after: "And so one of the things that you quickly realize is that even my old job when I was at K…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 47 after it inside its edge sentences; at most 3))
- 0 before / 47 after: "I mean people have been mentioning recently like if you look at Bitcoin over the last fiv…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 47 after it inside its edge sentences; at most 3))
- 37 before / 17 after: "Um I find Bitcoin super boring, but I'm always like that's cool because it's boring. Like…" (why: the anchored text is not whole sentences of the word record (37 word(s) before it and 17 after it inside its edge sentences; at most 3))
- 0 before / 57 after: "And the euro currency is really under pressure right now, giving up all sorts of technica…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 57 after it inside its edge sentences; at most 3))
- 0 before / 87 after: "So you know as an investor we should be aware of that and as you know, right, mid term ye…" (why: the anchored text is not whole sentences of the word record (0 word(s) before it and 87 after it inside its edge sentences; at most 3))

**Stage 1: 178 moments -> 57 usable** (package.usable; 121 lost)

A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).

**Stage 1a: not eligible on screen (100 moments)**

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 57 | 45 | `no_bitcoin`: does not name Bitcoin: regex `\b(bitcoins?|btcs?)\b` (T11, the old story selector's subject screen; 'Bitcoiners', 'sats', 'Satoshi' do not count) | "There's eight and a half billion people. We all have a money problem. It's not like we sort of maybe have a money problem." |
| 35 | 21 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it in an aw…" |
| 18 | 11 | `not_statement`: ends on a question | "We don't have Satoshi over here selling his coins, you know? So I think that's the, and that's the issue too with, you know, treasury compa…" |
| 10 | 3 | `opener`: opens on a pronoun or reply word that needs what came before (stand_alone.opener) | "But right now, if AI is the most volatile thing in the market, which right now, I mean, look, ASRs move more than Bitcoin did." |
| 1 | 1 | `start_case`: starts lower-case | "it's a it's an i struggle to find the right word to describe it, but bitcoin is not for gambling with. That's not what it's for. it's for p…" |

**Stage 1b: the other usable() reasons (21 moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 18 | N s: over the 20.0 s per source video (L-u) or unmeasured | "But I think this MSCI Global Index ruling shows one thing. that not everyone is really embracing Bitcoin. And again, I keep bringing up the…" |
| 3 | delivered in the previous 24 h (or overlaps a delivered moment) | "Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin wins, open source wins. And eve…" |

**Stage 2: 57 usable -> 17 cleared step A** (L-s on the moment's own context; 24 screened, 7 failed)

**Stage 2: step A rules (7 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 4 | 3 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "Bitcoin is, it's immune to that. There will never be an asteroid that you will find a bunch of Bitcoin on." ('that' -> 'technology invalidating prior ideas of gold scarc…', changes the assertion: yes) |
| 4 | 3 | `NOT_OWN_SINCERE`: not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...) | "In the world of Bitcoin, security isn't just a feature. It's the entire foundation." (view: ad_read) |
| 1 | 0 | `CONDITION_OUTSIDE`: a condition outside the clip | "For many people, you're the bitcoin guy." ('in a future where AI has broken encryption and banking infr…') |

**Stage 3: 17 cleared -> 8 pass L-v 2 + CUTTABLE (9 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 5 | L-v 2 FAIL | "Bitcoin is like a place where you come. Like, you know, the Bitcoin, everyone gets Bitcoin at the price they deserve because you find Bitco…" ((edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)) |
| 4 | not cuttable at an edge (ruling C / 7) | "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets …" ((edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)) |

Every stage-3 loss, exactly:
- What Bitcoin Did: L-v 2 FAIL: (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)
- CNBC Television: not cuttable at an edge (ruling C / 7): (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)
- What Bitcoin Did: not cuttable at an edge (ruling C / 7): (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)
- Strategy (MicroStrategy): not cuttable at an edge (ruling C / 7): (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)
- Bitcoin Mechanic: L-v 2 FAIL: (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)
- What Bitcoin Did: L-v 2 FAIL: (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)
- Guy Swann: L-v 2 FAIL: (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)
- Anthony Pompliano: L-v 2 FAIL: (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)
- What Bitcoin Did: not cuttable at an edge (ruling C / 7): (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)

**Stage 4: 8 cuttable -> 6 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 1 | FAIL: 0 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin." |
| 1 | FAIL: 40 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "In the first week of November, about $1.28 billion left the spot Bitcoin ETFs, the most since late June. And more went out on the following…" |

**Stage 5: the angle step and the line-ups.** why_none: 'stopped in angle 1 of 3: 907 s of 900 s wall / $0.66 of $1.50 reported / $1.56 of the $5.00 estimate ceiling (ruling 5, 22:40)'; angles: 3 from xai:grok-4.20-0309-reasoning

The moments offered to the angle step:
- Simply Bitcoin (BS0XC_tixa8), 11.25 s, can open: True: "Days like today are when people get shaken out. Bitcoin dumps on a scandal that has nothing to do with it. You panic or a bill comes due, and suddenl…"
- Altcoin Daily (HWuMai_mAug), 6.93 s, can open: False: "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin."
- Coin Bureau (RTck1cfw3GY), 9.7 s, can open: True: "The funds are selling strategies stock. The Bitcoin never changes hands. Nothing in MSCI's decision forces strategy to sell its Bitcoin."
- The Bitcoin Layer (lYca6Bg0FkM), 4.8 s, can open: True: "Bitcoin started turning though before liquidity turned red. And that's an important caveat here."
- Coin Bureau (RTck1cfw3GY), 19.53 s, can open: False: "In the first week of November, about $1.28 billion left the spot Bitcoin ETFs, the most since late June. And more went out on the following Monday an…"
- BTC Sessions (1vg1cufkadc), 12.72 s, can open: True: "The number of people that I talk to that haven't taken Bitcoin off the exchange is honestly quite frightening. And those that do, a lot of them buy o…"
- Simply Bitcoin (WTCwyxW-lHk), 6.7 s, can open: True: "Nobody tells anybody put a, you know, duffel bag with all their gold or all their cash in their mattress. But for some reason, everyone said you got …"
- Scott Melker (mKNAcOFMYD4), 8.76 s, can open: True: "My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank owns the money and they could just take i…"

Together 80.39 s from 6 channels.
- angle: "We Bitcoin to avoid getting shaken out and selling the scarcest asset at the worst time since everything in the industry bleeds to it despite major ETF outflows." moments 4
- angle: "Bitcoin is not a set-it-and-forget-it asset so take it off exchanges and hold it yourself rather than in a bank since it never changes hands even if stock is sold." moments 4
- angle: "Days like today shake people out into selling the scarcest asset at the worst time but Bitcoin starts turning before liquidity turns red as an important caveat while everything bleeds to it." moments 4

The build's own log from the angle step on:
```
  3 angles from xai:grok-4.20-0309-reasoning (907 s)
no package (stopped in angle 1 of 3: 907 s of 900 s wall / $0.66 of $1.50 reported / $1.56 of the $5.00 estimate ceiling (ruling 5, 22:40)); usable 57, cleared 17
```
