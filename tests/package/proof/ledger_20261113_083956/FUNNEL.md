Build `ledger_20261113_083956`: code 0a15f27b+f936463621ca, render clock 2026-11-13T08:39:56.153392+00:00.
Adapter (pp-ingest, before the ledger rows): excluded {"hard exclusion flag (L-u)": 123, "altcoin or not about Bitcoin": 30, "speaker change inside (caption marker)": 22}.

**Stage 0: 510 ledger rows -> 262 moments (248 not moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 148 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 38 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched around the row's time) | "and they're in that safe and it's like yeah yeah yeah it's like what is that safe made of glass I think I've got a hammer back there let me…" |
| 32 | duplicate: the same speech as a kept moment (time overlap in the same video) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software and Bitcoin has…" |
| 26 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it runs N s > N s (ruling N: the clip length limit) | "Um I find Bitcoin super boring, but I'm always like that's cool because it's boring. Like that was the cool part because it was so boring. …" |
| 2 | SUPPLY: no word record yet (no word record in the store; no sentence-ready window record) | n/a |
| 1 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it holds a caption speaker marker at N s: a measured speaker change (ruling N) | "BITCOIN IS DOWN MORE THAN 3%, FALLING BELOW THE 72,000 MARK TO ITS LOWEST LEVEL SINCE AUGUST. STRATEGY." |
| 1 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched -N-N s) | "Um I think that Bitcoin will go lower than 57k during Trump's term, okay? I think it will." |

**Stage 1: 262 moments -> 76 usable** (package.usable; 186 lost)

A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).

**Stage 1a: not eligible on screen (158 moments)**

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 103 | 77 | `no_bitcoin`: does not name Bitcoin: regex `\b(bitcoins?|btcs?)\b` (T11, the old story selector's subject screen; 'Bitcoiners', 'sats', 'Satoshi' do not count) | "There's eight and a half billion people. We all have a money problem. It's not like we sort of maybe have a money problem." |
| 48 | 26 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it in an aw…" |
| 29 | 13 | `not_statement`: ends on a question | "We don't have Satoshi over here selling his coins, you know? So I think that's the, and that's the issue too with, you know, treasury compa…" |
| 16 | 3 | `opener`: opens on a pronoun or reply word that needs what came before (stand_alone.opener) | "But right now, if AI is the most volatile thing in the market, which right now, I mean, look, ASRs move more than Bitcoin did." |
| 3 | 1 | `start_case`: starts lower-case | "it's a it's an i struggle to find the right word to describe it, but bitcoin is not for gambling with. That's not what it's for. it's for p…" |
| 1 | 0 | `too_short`: < 5 words | "Secure. That's it." |

**Stage 1b: the other usable() reasons (28 moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 25 | N s: over the 20.0 s per source video (L-u) or unmeasured | "But I think this MSCI Global Index ruling shows one thing. that not everyone is really embracing Bitcoin. And again, I keep bringing up the…" |
| 3 | delivered in the previous 24 h (or overlaps a delivered moment) | "Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin wins, open source wins. And eve…" |

**Stage 2: 76 usable -> 17 cleared step A** (L-s on the moment's own context; 24 screened, 7 failed)

**Stage 2: step A rules (7 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 4 | 4 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "Bitcoin is, it's immune to that. There will never be an asteroid that you will find a bunch of Bitcoin on." ('that' -> 'technology invalidating prior ideas of gold scarc…', changes the assertion: yes) |
| 3 | 3 | `NOT_OWN_SINCERE`: not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...) | "In the world of Bitcoin, security isn't just a feature. It's the entire foundation." (view: ad_read) |

**Stage 3: 17 cleared -> 12 pass L-v 2 + CUTTABLE (5 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 4 | L-v 2 FAIL | "Bitcoin is like a place where you come. Like, you know, the Bitcoin, everyone gets Bitcoin at the price they deserve because you find Bitco…" (speakers measured inside: ['speaker_0', 'speaker_1']) |
| 1 | NOT MEASURED: CalledProcessError: Command '['yt-dlp', '-q', '--no-playlist', '-f', 'bestaudio', '--download-sections', '*4966.27-4982.95', '--force-keyframes-at-cuts', '-o', '/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea | "Php, server vulnerability, 70 % of the internet. Wordpress, cooked, 40 % of the internet. Bang, btc, paper foundation. I was just like, thi…" ((edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)) |

Every stage-3 loss, exactly:
- What Bitcoin Did: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- Guy Swann: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- Anthony Pompliano: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoiners"]}
- What Bitcoin Did: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": ["no"], "names": ["Nah"]}
- What Bitcoin Did: NOT MEASURED: CalledProcessError: Command '['yt-dlp', '-q', '--no-playlist', '-f', 'bestaudio', '--download-sections', '*4966.27-4982.95', '--force-keyframes-at-cuts', '-o', '/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea: (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)

**Stage 4: 12 cuttable -> 9 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 1 | FAIL: 0 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin." |
| 1 | FAIL: 50 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets …" |
| 1 | FAIL: 40 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "In the first week of November, about $1.28 billion left the spot Bitcoin ETFs, the most since late June. And more went out on the following…" |

**Stage 5: the angle step and the line-ups.** why_none: None; angles: 3 from heimdall:deepseek/deepseek-v4.1-flash

The moments offered to the angle step:
- What Bitcoin Did (acxge3Orsv8), 9.46 s, can open: True: "I will bet you one Bitcoin that RSA has broken in 10 years, and I'll bet you half a Bitcoin that it's broken in five years. That's the level of convi…"
- CNBC Television (GXWj2JO9bz8), 13.94 s, can open: True: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- Bitcoin Mechanic (WghTi5Ep4ro), 7.26 s, can open: True: "Bitcoin on the Blake 2B chain is incredible. And I say that not to pump it. Don't buy any if you don't want to buy any."
- Strategy (MicroStrategy) (xfLi0cH_VqM), 13.82 s, can open: False: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- Simply Bitcoin (BS0XC_tixa8), 11.25 s, can open: True: "Days like today are when people get shaken out. Bitcoin dumps on a scandal that has nothing to do with it. You panic or a bill comes due, and suddenl…"
- Altcoin Daily (HWuMai_mAug), 6.93 s, can open: False: "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin."
- Coin Bureau (RTck1cfw3GY), 9.7 s, can open: True: "The funds are selling strategies stock. The Bitcoin never changes hands. Nothing in MSCI's decision forces strategy to sell its Bitcoin."
- The Bitcoin Layer (lYca6Bg0FkM), 4.8 s, can open: True: "Bitcoin started turning though before liquidity turned red. And that's an important caveat here."
- Coin Bureau (RTck1cfw3GY), 19.53 s, can open: False: "In the first week of November, about $1.28 billion left the spot Bitcoin ETFs, the most since late June. And more went out on the following Monday an…"
- Simply Bitcoin (WTCwyxW-lHk), 6.7 s, can open: True: "Nobody tells anybody put a, you know, duffel bag with all their gold or all their cash in their mattress. But for some reason, everyone said you got …"
- Scott Melker (mKNAcOFMYD4), 8.76 s, can open: True: "My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank owns the money and they could just take i…"
- BTC Sessions (1vg1cufkadc), 12.72 s, can open: True: "The number of people that I talk to that haven't taken Bitcoin off the exchange is honestly quite frightening. And those that do, a lot of them buy o…"

Together 124.87 s from 10 channels.
- angle: "Bitcoin security is not a one-time setup—cryptography can break and self-custody requires ongoing vigilance." moments 4
- angle: "Don't get shaken out by headlines; Bitcoin's scarcity and long-term conviction matter more than short-term dumps." moments 4
- angle: "Bitcoin is about financial freedom, not partisan politics, and that freedom depends on controlling your own money." moments 4

The build's own log from the angle step on:
```
  3 angles from heimdall:deepseek/deepseek-v4.1-flash (314 s)
  angle 1 line-up 1 (4 clips, 37.6 s): clips alone PASS {'hook': 5, 'clip_01': 4, 'clip_02': 5, 'clip_03': 4} flagged ['clip_01 -> clip_02'] (337 s)
  angle 1 line-up 1 write 1 (heimdall:deepseek/deepseek-v4.1-flash, takeaway 17 words, 64.34 s): cheap PASS (393 s)
no package (None); usable 76, cleared 17
```
