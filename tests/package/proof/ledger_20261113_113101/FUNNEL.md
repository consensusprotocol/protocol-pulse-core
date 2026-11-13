Build `ledger_20261113_113101`: code ef6e3dc7, render clock 2026-11-13T11:31:01.821766+00:00.
Adapter (pp-ingest, before the ledger rows): excluded {"altcoin or not about Bitcoin": 27, "hard exclusion flag (L-u)": 114, "speaker change inside (caption marker)": 22}.

**Stage 0: 502 ledger rows -> 308 moments (194 not moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 78 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 46 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched around the row's time) | "and they're in that safe and it's like yeah yeah yeah it's like what is that safe made of glass I think I've got a hammer back there let me…" |
| 36 | duplicate: the same speech as a kept moment (time overlap in the same video) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software and Bitcoin has…" |
| 32 | does not re-anchor: snapped outward to whole sentences (N word(s) before the anchored text, N after) it runs N s > N s (ruling N: the clip length limit) | "Um I find Bitcoin super boring, but I'm always like that's cool because it's boring. Like that was the cool part because it was so boring. …" |
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

**Stage 2: 173 usable -> 4 cleared step A** (L-s on the moment's own context; 24 screened, 20 failed)

**Stage 2: step A rules (20 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 16 | 16 | `STEP_A_UNAVAILABLE: SpendLimit`: STEP_A_UNAVAILABLE: SpendLimit | "I think treasury companies will also bleed to Bitcoin. I mean, basically, everything in the industry eventually bleeds to Bitcoin." |
| 4 | 4 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "Bitcoin is, it's immune to that. There will never be an asteroid that you will find a bunch of Bitcoin on." ('that' -> 'manufacturing gold or mining asteroids to increas…', changes the assertion: yes) |

**Stage 3: 4 cleared -> 2 pass L-v 2 + CUTTABLE (2 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 2 | L-v 2 FAIL | "Like, you know, I've run a Bitcoin meetup for 10 years now. And I've interacted with thousands of Bitcoiners, as I'm sure you have, Giacomo…" (speakers measured inside: ['speaker_0', 'speaker_1']) |

Every stage-3 loss, exactly:
- Guy Swann: L-v 2 FAIL: speakers measured inside: ['speaker_0', 'speaker_1']
- Anthony Pompliano: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Bitcoiners"]}

**Stage 4: 2 cuttable -> 2 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 0 | - | - |

**Stage 5: the angle step and the line-ups.** why_none: '2 cleared moments pass the second pass and CUTTABLE, from fewer than 3 channels'; angles: 0 from None

The moments offered to the angle step:
- What Bitcoin Did (acxge3Orsv8), 9.46 s, can open: True: "I will bet you one Bitcoin that RSA has broken in 10 years, and I'll bet you half a Bitcoin that it's broken in five years. That's the level of convi…"
- CNBC Television (GXWj2JO9bz8), 13.94 s, can open: True: "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets and how we…"

Together 23.4 s from 2 channels.
