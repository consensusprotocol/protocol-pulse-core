Build `ledger_20261113_073738`: code 2cc6c0a3+d80eba78be87, render clock 2026-11-13T07:37:38.262997+00:00.
Adapter (pp-ingest, before the ledger rows): excluded {"hard exclusion flag (L-u)": 123, "altcoin or not about Bitcoin": 30, "speaker change inside (caption marker)": 22}.

**Stage 0: 507 ledger rows -> 70 moments (437 not moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 332 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 71 | SUPPLY: no word record yet (no word record in the store; no sentence-ready window record) | n/a |
| 15 | duplicate: the same speech as a kept moment (time overlap in the same video) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software and Bitcoin has…" |
| 12 | does not re-anchor: the anchored text is not whole sentences of the word record (more than SNAP_WORDS = 3 words of its edge sentences outside it) | "But you talk to someone in Venezuela and they're like, wait, oh, you're like, oh, it's volatile. It's like, what do you mean it's volatile?…" |
| 7 | does not re-anchor: the row's text does not anchor in the word record (sentence_law.anchor, searched around the row's time) | "Um, but we're willing to underwrite Bitcoin going down 80%. We put cash on the balance sheet. So it's kind of like you mix for us about 85%…" |

The 'not whole sentences' rows (ruling 32's case), exactly: words of the edge sentences outside the anchored text, before / after:
- 0 before / 6 after: "Now, you don't you don't need the skill. You don't need the time. You you you can devote a hundredth or a tho…"
- 0 before / 9 after: "But you talk to someone in Venezuela and they're like, wait, oh, you're like, oh, it's volatile. It's like, w…"
- 9 before / 0 after: "So whether it's a bond or preferred equity or for our companies common equity that have material exposure to …"
- 0 before / 11 after: "I think like in the grand scheme of global financial markets, you look at total global assets right now, it's…"
- 0 before / 11 after: "So MSCI didn't force any Bitcoin selling this week. But it has taken firepower away from Bitcoin's biggest bu…"
- 2 before / 12 after: "I think we we we can rest assured that we are relatively immune, not absolutely but relatively immune because…"
- 16 before / 0 after: "I'm not really sure I fully believe this, but it's when you have these major IPOs like SpaceX and Thropic and…"
- 0 before / 32 after: "And so Strive just voting on what's going to maximize shareholder value period I think is a fundamentally imp…"
- 0 before / 39 after: "So we could ride out any historical bare market without even have to sell a single Bitcoin. And so my belief …"
- 0 before / 47 after: "And so one of the things that you quickly realize is that even my old job when I was at Kalpers managing a bo…"
- 0 before / 47 after: "I mean people have been mentioning recently like if you look at Bitcoin over the last five years it's effecti…"
- 0 before / 57 after: "And the euro currency is really under pressure right now, giving up all sorts of technical trend lines and su…"

**Stage 1: 70 moments -> 23 usable** (package.usable; 47 lost)

A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding reasons. 'alone' = the moments that flag alone keeps out (lifting only it would bring them back).

**Stage 1a: not eligible on screen (44 moments)**

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 17 | 11 | `no_bitcoin`: does not name Bitcoin: regex `\b(bitcoins?|btcs?)\b` (T11, the old story selector's subject screen; 'Bitcoiners', 'sats', 'Satoshi' do not count) | "There's eight and a half billion people. We all have a money problem. It's not like we sort of maybe have a money problem." |
| 17 | 7 | `too_many_sentences`: more than 3 sentences (T9, the old selector's MAX_WINDOW_SENTENCES = 3) | "Like, you know, I've run a Bitcoin meetup for 10 years now. And I've interacted with thousands of Bitcoiners, as I'm sure you have, Giacomo…" |
| 16 | 7 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it in an aw…" |
| 7 | 3 | `not_statement`: ends on a question | "I believe open source will win, and I believe Bitcoin will win too. Will that help us find our way back to each other, to nature, and to Go…" |
| 4 | 1 | `opener`: opens on a pronoun or reply word that needs what came before (stand_alone.opener) | "Well, every time Nvidia has taken a hit over the last month, Bitcoin has gone down with it. It doesn't match point for point, but the patte…" |

**Stage 1b: the other usable() reasons (3 moments)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 3 | N s: over the 20.0 s per source video (L-u) or unmeasured | "Can Bitcoin front run it perhaps? But I believe Bitcoin does need the dollar to come back down. to give the market that behavior sense that…" |

**Stage 2: 23 usable -> 9 cleared step A** (L-s on the moment's own context; 23 screened, 14 failed)

**Stage 2: step A rules (14 moments)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 9 | 9 | `REFERENT_OUTSIDE`: a word refers to something outside the clip AND resolving it could change the assertion (anything but an explicit 'no' fails, L-m) | "And so we've seen kind of the four -year cycles play out, which my belief is that those will become less meaningful over the course of into…" ('we' -> 'the speaker's company or underwriting team', changes the assertion: yes) |
| 5 | 5 | `NOT_OWN_SINCERE`: not the speaker's own sincere view (quoting, hypothetical, sarcasm, a read, ...) | "In the world of Bitcoin, security isn't just a feature. It's the entire foundation." (view: ad_read) |

**Stage 3: 9 cleared -> 4 pass L-v 2 + CUTTABLE (5 lost)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 3 | not CUTTABLE: IN edge | "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin and crypto are about how do we modernize the financial markets …" (IN: the window starts at the clip: no word before it) |
| 1 | L-v 2 FAIL | "Bitcoin is like a place where you come. Like, you know, the Bitcoin, everyone gets Bitcoin at the price they deserve because you find Bitco…" (the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Fu-", "Mm-hmm"]}; speakers measured inside: ['speaker_0', 'speaker_1']) |
| 1 | not CUTTABLE: OUT edge | "Bitcoin has dipped below its 50 -week and its 200 -day moving averages. And the next big one below us is the 200 week, down around 67 to 68…" (OUT: the recogniser has no '68000' within 0.8 s of the clip's end) |

Every stage-3 loss, exactly:
- CNBC Television: not CUTTABLE: IN edge: IN: the window starts at the clip: no word before it
- Strategy (MicroStrategy): not CUTTABLE: IN edge: IN: the window starts at the clip: no word before it
- What Bitcoin Did: not CUTTABLE: IN edge: IN: the window starts at the clip: no word before it
- What Bitcoin Did: L-v 2 FAIL: the two recognisers disagree on {"numbers": [], "negations": [], "names": ["Fu-", "Mm-hmm"]}; speakers measured inside: ['speaker_0', 'speaker_1']
- Simply Bitcoin: not CUTTABLE: OUT edge: OUT: the recogniser has no '68000' within 0.8 s of the clip's end

**Stage 4: 4 cuttable -> 3 can open a medley (G17a; the others stay in play as non-hook clips)**

| lost | exact reason | one example (moment text) |
|---|---|---|
| 1 | FAIL: 0 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame) | "But we have very rarely in Bitcoin's history seen six negative weeks back to back to back to back to back. to back. I think that was six." |

**Stage 5: the angle step and the line-ups.** why_none: None; angles: 3 from heimdall:deepseek/deepseek-v4.1-flash

The moments offered to the angle step:
- The Bitcoin Layer (lYca6Bg0FkM), 4.8 s, can open: True: "Bitcoin started turning though before liquidity turned red. And that's an important caveat here."
- Simply Bitcoin (BS0XC_tixa8), 11.58 s, can open: True: "Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin wins, open source wins. And every stat yo…"
- Anthony Pompliano (mJviDNOhIyw), 16.23 s, can open: True: "But then if someone doesn't understand Bitcoin and you drop... 25 % of their portfolio in Bitcoin and Bitcoin goes down 50%. You get fired and they s…"
- Simply Bitcoin (WTCwyxW-lHk), 9.73 s, can open: False: "But we have very rarely in Bitcoin's history seen six negative weeks back to back to back to back to back. to back. I think that was six."

Together 42.34 s from 3 channels.
- angle: "Bitcoin's unstoppable open-source design doesn't prevent rare six-week losing streaks or early turns before liquidity, so even institutions keep allocations small." moments 4
- angle: "Bitcoin can turn before macro liquidity does, but its rare six-week losing streaks mean investors must keep allocations small enough to avoid forced selling." moments 4
- angle: "Bitcoin's rare six-week losing streaks and early turns before liquidity explain why institutions cap allocations at 1-5% for people who don't understand it." moments 4

The build's own log from the angle step on:
```
  3 angles from heimdall:deepseek/deepseek-v4.1-flash (336 s)
  angle 1 line-up 1 (3 clips, 37.5 s): clips alone PASS {'hook': 5, 'clip_01': 4, 'clip_02': 5} flagged ['hook -> clip_01'] (373 s)
  angle 1 line-up 1 write 1 (heimdall:deepseek/deepseek-v4.1-flash, takeaway 19 words, 65.44 s): cheap PASS (442 s)
    fidelity FAIL (takeaway ['COMMENTARY']), context PASS (574 s)
  angle 1 line-up 1 write 2 (heimdall:deepseek/deepseek-v4.1-flash, takeaway 12 words, 63.44 s): cheap PASS (683 s)
    fidelity PASS (takeaway PASS), context PASS (814 s)
    coherence with the takeaway PASS {'hook': 4, 'clip_01': 5, 'clip_02': 5} vo 5 (833 s)
    speaker 0: BS0XC_tixa8 -> unknown (nothing in the transcript or clip names a speaker, addresses anyone by name, or ties the first-person statements to any specific person named in the source lines); the source names []
    speaker 1: WTCwyxW-lHk -> unknown (both the host and the guest speak in this episode, and nothing in or around the clip shows which one this is); the source names ['Dan Held']
    speaker 2: mJviDNOhIyw -> unknown (both the host and the guest speak in this episode, and nothing in or around the clip shows which one this is); the source names ['Anthony Pompliano', 'Matt Cole']
PACKAGE (833.4 s, $2.12 estimate, $0.2059 best known) pin /home/ultron/worktrees/pp-selectid/tests/package/proof/ledger_20261113_073738/MOMENTS_PIN_LEDGER.json
```
