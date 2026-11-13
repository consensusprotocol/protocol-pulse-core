Build `ledger_20261113_130318`: code 7bb0131e, render clock 2026-11-13T13:03:18.999790+00:00.
Adapter (pp-ingest, before the ledger rows): excluded {"altcoin or not about Bitcoin": 36, "hard exclusion flag (L-u)": 118, "speaker change inside (caption marker)": 28}.

**Stage 0: 503 ledger rows -> 291 moments (212 not moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 78 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 46 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched around the row's time) | "and they're in that safe and it's like yeah yeah yeah it's like what is that safe made of glass I think I've got a hammer back there let me…" |
| 35 | duplicate: the same speech as a kept moment (time overlap in the same video) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software and Bitcoin has…" |
| 32 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it runs N s > N s (ruling N: the clip length limit) | "Um I find Bitcoin super boring, but I'm always like that's cool because it's boring. Like that was the cool part because it was so boring. …" |
| 19 | SUPPLY: no word record yet (no word record in the store; no sentence-ready window record) | n/a |
| 1 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it holds a caption speaker marker at N s: a measured speaker change (ruling N) | "BITCOIN IS DOWN MORE THAN 3%, FALLING BELOW THE 72,000 MARK TO ITS LOWEST LEVEL SINCE AUGUST. STRATEGY." |
| 1 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched -N-N s) | "Um I think that Bitcoin will go lower than 57k during Trump's term, okay? I think it will." |

**Stage 1: 291 moments -> 158 usable** (package.usable; 133 lost)

A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).

**Stage 1a: not eligible on screen (86 moments)**

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 52 | 36 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it in an aw…" |
| 28 | 19 | `not_statement`: ends on a question | "We don't have Satoshi over here selling his coins, you know? So I think that's the, and that's the issue too with, you know, treasury compa…" |
| 20 | 9 | `opener`: opens on a pronoun or reply word that needs what came before (stand_alone.opener) | "No machine can argue with that. It is the heaviest concentration, just like the sun is the heaviest local thing for us." |
| 3 | 3 | `start_case`: starts lower-case | "it's a it's an i struggle to find the right word to describe it, but bitcoin is not for gambling with. That's not what it's for. it's for p…" |
| 1 | 1 | `too_short`: < 5 words | "Secure. That's it." |

**Stage 1b: the other usable() reasons (47 moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 44 | N s: over the 20.0 s per source video (L-u) or unmeasured | "But in another tweet, you said something super interesting that it was in 2020, if you had $100,000. it could buy you about 25,900 pounds o…" |
| 3 | delivered in the previous 24 h (or overlaps a delivered moment) | "Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin wins, open source wins. And eve…" |

**Stage 2: 158 usable -> 13 cleared step A** (L-s on the moment's own context; 24 screened, 11 failed)

**Stage 2: step A rules (11 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 5 | 4 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "Bitcoin is, it's immune to that. There will never be an asteroid that you will find a bunch of Bitcoin on." ('that' -> 'manufacturing gold or finding huge gold deposits …', changes the assertion: yes) |
| 5 | 5 | `NOT_OWN_SINCERE`: not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...) | "In the world of Bitcoin, security isn't just a feature. It's the entire foundation." (view: ad_read) |
| 1 | 1 | `STALE_TIME`: time words stale on the show date (L-v 3) | "Days like today are when people get shaken out. Bitcoin dumps on a scandal that has nothing to do with it. You panic or a bill comes due, a…" (time_ok: uncertain) |
| 1 | 0 | `RETRACTION`: retracted or corrected later | "[But trimmed] this was not, as a as again, i'd like to point out, in bitcoin, we like to think no one is in charge of it. No one has influe…" (retraction: But underneath that that's not how people work.) |

**Stage 3: 13 cleared -> 8 pass L-v 2 + CUTTABLE (5 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 4 | L-v 2 FAIL | "Like, you know, I've run a Bitcoin meetup for 10 years now. And I've interacted with thousands of Bitcoiners, as I'm sure you have, Giacomo…" (speakers measured inside: ['speaker_0', 'speaker_1']) |
| 1 | NOT MEASURED: CalledProcessError: Command '['yt-dlp', '-q', '--no-playlist', '-f', 'bestaudio', '--download-sections', '*826.83-850.79', '--force-keyframes-at-cuts', '-o', '/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0- | "[So trimmed] all, any Bitcoin exchange operator, you'll know that they have the most. battle tested systems possible because they are the f…" ((edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)) |

Every stage-3 loss, exactly:
- Guy Swann: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- Anthony Pompliano: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoiners"]}
- What Bitcoin Did: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- What Bitcoin Did: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": ["no"], "names": ["Nah"]}
- What Bitcoin Did: NOT MEASURED: CalledProcessError: Command '['yt-dlp', '-q', '--no-playlist', '-f', 'bestaudio', '--download-sections', '*826.83-850.79', '--force-keyframes-at-cuts', '-o', '/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-: (edge detail not recomputed offline: ReplayMiss: transcribe: no recorded transcription ([('openai_stt:gpt-4o-transcribe-diarize', 'replay: not recorded'), ('elevenlabs_s)

**Stage 4: 8 cuttable -> 5 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 1 | FAIL: 0 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin." |
| 1 | FAIL: 50 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets …" |
| 1 | FAIL: no cut after the trimmed word 'So': the trimmed word 'So' cannot be cut cleanly: no measured pause between it and 'if' (co-articulated) | "[So trimmed] if you look at the average income in the lowest 20 economies like $40 a month. So when people go, dude, it's like it's only li…" |

Trimmed variants (ruling 33 part 2): 32 of the 105 left out by STAND_ALONE joined the usable moments; 1 cleared to here and failed the trimmed cut (a), at any place:
- What Bitcoin Did: FAIL: no trimmed cut was reached: no cut after the trimmed word 'So': the trimmed word 'So' cannot be cut cleanly: no measured pause between it and 'if' (co-articulated): "[So trimmed] if you look at the average income in the lowest 20 economies like $40 a month. So when people go, dude, it…"

**Stage 4b: step A from the second vendor (order 06:22 item 45): 7 of 7 pass**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 0 | - | - |

**Stage 5: the angle step and the line-ups.** why_none: "no angle gave a package: angle 1: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 2: the clips alone fail (ratings / joins): dropped ['95d20143d5e2af5612b1', 'c3be6f1c71c4397b081a'], no swap fits the line-up rules: re-lined; angle 2: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 3: the clips alone fail (ratings / joins): swapped {'2e77a0a7af2aab66a3a4': '06f73bef2e37ba14bee4', '95d20143d5e2af5612b1': 'c7646b4ee91f955cf58f'}, re-judged (ruling 41); angle 3: the clips alone fail (ratings / joins): dropped ['06f73bef2e37ba14bee4'], no swap fits the line-up rules: re-lined; angle 3: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"; angles: 3 from heimdall:deepseek/deepseek-v4.1-flash

The moments offered to the angle step:
- Strategy (MicroStrategy) (xfLi0cH_VqM), 13.82 s, can open: False: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"
- Scott Melker (mKNAcOFMYD4), 8.76 s, can open: True: "My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank owns the money and they could just take i…"
- Altcoin Daily (HWuMai_mAug), 6.93 s, can open: False: "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin."
- The Bitcoin Layer (lYca6Bg0FkM), 4.8 s, can open: True: "Bitcoin started turning though before liquidity turned red. And that's an important caveat here."
- What Bitcoin Did (acxge3Orsv8), 9.46 s, can open: True: "I will bet you one Bitcoin that RSA has broken in 10 years, and I'll bet you half a Bitcoin that it's broken in five years. That's the level of convi…"
- Bitcoin Mechanic (WghTi5Ep4ro), 7.26 s, can open: True: "Bitcoin on the Blake 2B chain is incredible. And I say that not to pump it. Don't buy any if you don't want to buy any."
- CNBC Television (GXWj2JO9bz8), 13.94 s, can open: True: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"

Together 64.97 s from 7 channels (a trimmed variant's seconds not counted).
- angle: "Bitcoin is not a partisan issue; it is a financial freedom movement driven by conviction that the old system can fail you." moments 4
- angle: "Bitcoiners have deep conviction and aren't just pumping—they see it as a nonpartisan financial freedom tool." moments 4
- angle: "Everything in the industry eventually bleeds to Bitcoin as people seek financial freedom from a fragile system." moments 5

The build's own log from the angle step on:
```
  3 angles from heimdall:deepseek/deepseek-v4.1-flash (14 s)
  angle 2 line-up 1 (4 clips, 39.4 s): clips alone FAIL {'hook': 4, 'clip_01': 3, 'clip_02': 5, 'clip_03': 5} flagged ['hook -> clip_01', 'clip_01 -> clip_02'] (14 s)
  angle 3 line-up 1 (4 clips, 37.0 s): clips alone FAIL {'hook': 3, 'clip_01': 5, 'clip_02': 5, 'clip_03': 4} flagged ['hook -> clip_01', 'clip_02 -> clip_03'] (14 s)
  angle 3 line-up 2 (4 clips, 36.9 s): clips alone FAIL {'hook': 3, 'clip_01': 5, 'clip_02': 5, 'clip_03': 4} flagged ['hook -> clip_01'] (14 s)
  search: 3 line-up(s) of 8, $0.00 reported / $0.00 estimate (ruling 41: $3.00 reported per build)
no package (no angle gave a package: angle 1: no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules; angle 2: the clips alone fail (ratings / joins): dropped ['95d20143d5e2af5612b1', 'c3be6f1c71c4397b081a'], no 
  spend (ruling 48): $5.95 of $12.00 vendor-reported after this build (before it: $5.95)
```
