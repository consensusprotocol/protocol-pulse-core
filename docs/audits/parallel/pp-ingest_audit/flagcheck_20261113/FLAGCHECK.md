Run 2026-11-13T09:18:21.934712+00:00 (flagcheck/1); ledger rows 2072 (unreadable 0); flagged imperative / accusation / single_source_breaking and published in the last 72 h: 225; checked: 200 (newest first, cap 200); questions answered by: {'z-ai/glm-5.3-flash': 581, 'meta-models/muse-spark-open-816b-a42b': 19}.

Checker calibration (24 quotes with a clear answer under the ruling's definitions, 4 yes + 4 no per flag):

| back-end | model | right | imperative | accusation | single_source_breaking | unmeasured |
|---|---|---|---|---|---|---|
| heimdall_glm53flash | z-ai/glm-5.3-flash | 24/24 | 8/8 | 8/8 | 8/8 | 0 |
| heimdall_muse | meta-models/muse-spark-open-816b-a42b | 24/24 | 8/8 | 8/8 | 8/8 | 0 |

CONFUSION TABLES (rows: the miner's label; columns: the checker's answer)

imperative: precision 73 % (95 % CI [0.604, 0.83]; counting unsure as yes 73 %; measured 56)

| miner \ checker | yes | no | unsure | unmeasured |
|---|---|---|---|---|
| flagged | 41 | 15 | 0 | 0 |
| not flagged (rows flagged with another of the three) | 1 | 143 | 0 | 0 |

accusation: precision 52 % (95 % CI [0.438, 0.607]; counting unsure as yes 52 %; measured 130)

| miner \ checker | yes | no | unsure | unmeasured |
|---|---|---|---|---|
| flagged | 68 | 62 | 0 | 0 |
| not flagged (rows flagged with another of the three) | 2 | 68 | 0 | 0 |

single_source_breaking: precision 67 % (95 % CI [0.488, 0.808]; counting unsure as yes 67 %; measured 30)

| miner \ checker | yes | no | unsure | unmeasured |
|---|---|---|---|---|
| flagged | 20 | 10 | 0 | 0 |
| not flagged (rows flagged with another of the three) | 64 | 106 | 0 | 0 |

Precision by subset (checker yes / measured, among the rows the miner flagged):

| subset | imperative | accusation | single_source_breaking |
|---|---|---|---|
| miner claude-opus-5-5 | 3/8 (38 %) | 5/11 (46 %) | 5/6 (83 %) |
| miner qwen/qwen3.8-27b | 38/48 (79 %) | 63/119 (53 %) | 15/24 (62 %) |
| seen once | 40/54 (74 %) | 68/129 (53 %) | 19/29 (66 %) |
| seen in two windows | 1/2 (50 %) | 0/1 (0 %) | 1/1 (100 %) |
| the flag is the row's only hard flag | 34/45 (76 %) | 49/105 (47 %) | 12/17 (71 %) |

OPTION B SIMULATED (a flag stands only when both models agree; unsure and unmeasured keep it): the adapter's own read on a copy of the ledger, against the same read of the real ledger. Nothing applied.

| window | rows | removed by hard flags now | if both must agree | returned now | if both must agree |
|---|---|---|---|---|---|
| 24 h | 685 | 123 | 84 | 510 | 535 |
| 72 h | 1550 | 311 | 237 | 1025 | 1077 |

SPEND: $0.0306 (each reply's usage.cost (vendor-reported); failed calls included); attempts {'cache': 211, 'ok': 437, 'invalid': 16, 'timeout': 18}; by back-end {'heimdall_glm53flash': {'calls': 453, 'usd': 0.029035, 'model': 'z-ai/glm-5.3-flash'}, 'heimdall_muse': {'calls': 18, 'usd': 0.001602, 'model': 'meta-models/muse-spark-open-816b-a42b'}}.

EXAMPLES (up to 5 per cell, seeded pick 20261113):

#### imperative | miner_yes | checker yes
- `4af82d4384d6340670cf` Bankless, 2026-11-11; miner claude-opus-5-5 flags ['imperative', 'price_prediction', 'time_sensitive'] (windows 1): "And so like the way I kind of see it is I will put on these more longer term overarching thesis through options trades, but then on a day like you know yesterday for example, you know, Bitcoin at 70, you know, 52 might have been a really interesting per long just for a quick scalp up to back up to like 76. And that's not necessarily a trade that I want to go in and like cross the spread on options as much for. Um, and so I'm always trading in and out of some of the delta that I have from my options um via per. And so I would say most people should combine both of them."  
  checker: **yes** evidence "And so I would say most people should combine both of them."; The speaker gives a directive: most people should combine both trade types (options and perps), telling viewers how to act financially in their trading.
- `04189add8b472f1e8d92` Scott Melker, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "So, to me, I don't really see anything to worry about. I'm very excited to buy these dips."  
  checker: **yes** evidence "I'm very excited to buy these dips."; The speaker states they are excited to buy the dips, conveying the financial action of buying, which meets the definition.
- `324aab69fcc061d39247` Altcoin Daily, 2026-11-12; miner qwen/qwen3.8-27b flags ['ad_read', 'imperative'] (windows 1): "Everybody else see on Coinbase, be sure to get the cheapest fees through my link and earn win up to $2 million for the trading you're going to do anyway."  
  checker: **yes** evidence "be sure to get the cheapest fees through my link and earn win up to $2 million for the trading you're going to do anyway"; The imperative 'be sure to get' directs viewers to act: use the link for cheaper fees and earn rewards on their trading, a financial action.
- `925bb460680d74aa7fbe` Bitcoin Magazine, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "You know, crypto has always been a buy and hold approach and I think that remains the right approach. Um and how this going to shake out, I don't know."  
  checker: **yes** evidence "crypto has always been a buy and hold approach and I think that remains the right approach"; The speaker recommends buy and hold as the right approach, advising viewers how to act financially with their crypto.
- `fbc7f51f686ca1601163` Bitcoin Magazine, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative', 'price_prediction'] (windows 1): "And you know, if you really like Bitcoin so much, you could always buy it back a lot cheaper. You know, you'll have plenty of opportunities to buy your Bitcoin back substantially lower than it is right now."  
  checker: **yes** evidence "you could always buy it back a lot cheaper"; The speaker advises the viewer they could buy Bitcoin back cheaper, pointing to opportunities to buy it substantially lower, which is a financial action (buy).

#### imperative | miner_yes | checker no
- `efccacd8bc42e4daf1f8` Coffeezilla, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'imperative'] (windows 1): "Quote, markets already move on Truth Social posts, said Kevin McEntee, interim chief executive officer of TMTG. They're now selling an API that allows a quote real-time feed of the platform's most market [music] moving truths. The company is reportedly charging $100,000 a month and has multiple buyers."  
  checker: **no**; The quote only reports facts: markets move on Truth Social posts, TMTG sells an API, and it charges $100,000 a month. No instruction to buy, sell, hold or act financially.
- `0341e73babc1f4e22f8e` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'imperative'] (windows 1): "Dude, half of it's money laundering. Like I'm not I'm being real. So like that becomes a thing where they're like all it is is a greater fool theory."  
  checker: **no**; The quote only describes money laundering and greater fool theory; it gives no instruction to buy, sell, hold or act financially.
- `b5d6556583b814c5a094` Simply Bitcoin, 2026-11-12; miner qwen/qwen3.8-27b flags ['ad_read', 'imperative'] (windows 1): "They're the only self-custody by default platform in North America. Yeah, North America. And uh that's why Bitcoin Well team is topnotch. Also, they do have their white glove service over there."  
  checker: **no**; The quote only describes Bitcoin Well's features and praises the team; it gives no instruction to buy, sell, hold or act financially.
- `05b8d78e2a92eaf26a68` BTC Sessions, 2026-11-10; miner claude-opus-5-5 flags ['imperative'] (windows 1): "So what I've been telling people is like, if you aren't using this technology, if you aren't using these large language models to attack yourself, then you should expect that they're going to get used against you, and you're going to be at a severe disadvantage if you haven't been making use of the new capabilities."  
  checker: **no**; The quote advises using technology (LLMs) to avoid disadvantage; it mentions no buying, selling, holding or financial action, so it does not meet the imperative definition.
- `bcbdc047b85057d62bbf` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "Listen to this. Let me give you a sort of sales pitch. I did invest in the company very lucky to >> sold Bitcoin for it actually. This is true story. So, it's a first rotation where I was like, "Whoa, I just let go of my prize jewel.""  
  checker: **no**; The speaker only recounts past personal actions (invested, sold Bitcoin, let go of prize jewel); no instruction to the viewer to buy, sell, hold or act financially.

#### imperative | miner_no | checker yes
- `5767ba900538628c293f` CNBC Television, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "LOOK MSCI HAS BEEN ON A MULTIYEAR CAMPAIGN AGAINST DIGITAL ASSETS. AND IT'S INTERESTING BECAUSE THEIR ROLE IS TO BE AN INDEPENDENT ARBITER OF THE MARKETS NOT PICKING WINNERS AND LOSERS. AND THEY'VE CLEARLY DECIDED THAT BITCOIN ISN'T SOMETHING THAT PEOPLE SHOULD BE INVESTING IN."  
  checker: **yes** evidence "THEY'VE CLEARLY DECIDED THAT BITCOIN ISN'T SOMETHING THAT PEOPLE SHOULD BE INVESTING IN."; The quote states people should be investing in Bitcoin, conveying a financial action (investing) to the viewer, meeting the definition.

#### imperative | miner_no | checker no
- `3959d7c70701a3bc6896` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'time_sensitive'] (windows 1): "Are they recovering the losses? This is the big question going on right now. Is Binance liquidating their users to recover those losses?"  
  checker: **no**; The quote only poses questions about Binance recovering losses and liquidating users; it gives no instruction to the viewer to buy, sell, hold, or act financially.
- `22f18e2fa3042ab8da50` BTC Sessions, 2026-11-10; miner claude-opus-5-5 flags ['accusation', 'doom', 'single_source_breaking', 'time_sensitive'] (windows 1): "So Bitcoin infrastructure has been completely ransacked. While a vulnerability is core lightning liquid hack BTC server capped off with the largest exchange Binance, being hit by the largest heist of any kind of all time at 6.3 billion."  
  checker: **no**; The quote only describes hacks and the Binance heist; it gives no instruction to buy, sell, hold or otherwise act financially.
- `bc7bf5e71d9f4554232f` Bitcoin Magazine, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'politics_non_btc'] (windows 1): "What's wild about the PSL or Party for Socialism and Liberation is that it is essentially organized and run by a man based in Shanghai named Neville Singham. He's an avowed Marxist who's funded nonprofits here in the United States that are anti-American and pro-CCP to the tune of $278 million."  
  checker: **no**; The quote only describes the PSL, Neville Singham, and his $278 million in nonprofit funding; it gives no instruction to buy, sell, hold, or act financially.
- `241bfaee53b5bee735a1` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I mean, you've got the same coins I've got. Like you've got BTC Sh, you got XPTt or whatever. But like the the like kind of the ignorance to what's actually happening felt like very gaslighty."  
  checker: **no**; The quote only states that the listener has the same coins as the speaker and comments that the ignorance felt gaslighty; it gives no instruction to buy, sell, hold or act financially.
- `f674e35be2656986ea12` Altcoin Daily, 2026-11-12; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "They have officially chosen Avalanche Blockchain to settle tokenized stocks. At its core, what the New York Stock Exchange has decided to do is put the Avalanche blockchain at the center of their new infrastructure play for tokenized equities and 24/7 trading."  
  checker: **no**; The quote only reports facts about NYSE choosing Avalanche; it gives no instruction to buy, sell, hold or act financially.

#### accusation | miner_yes | checker yes
- `403f762b59fde51f942e` Bitcoin Mechanic, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I'm not saying we're perfect. I'm saying that the community around Blake2B has the actual integrity and humility to say of course we can screw stuff up. We just need to and having that mentality is just so important. That's why I see the beauty I do see in the in the Blake 2B chain. And I don't and again the the the pathological dishonesty I see back in SHA 256 is it's only getting worse because no one is taking them to task over it."  
  checker: **yes** evidence "the the the pathological dishonesty I see back in SHA 256 is it's only getting worse because no one is taking them to task over it"; The quote attributes 'pathological dishonesty' that is 'only getting worse' to SHA 256, an identifiable entity, alleging wrongdoing, with no one taking 'them to task'.
- `9fcd1656b45fa9a1891d` Coffeezilla, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "One of these investors in TMTG is Don Wilson, who weeks prior had the SEC enforcement case against his crypto company Cumberland dismissed with prejudice. Now in response to my request for comment, Cumberland denied any quid pro quo and connection between the Trump Media investment and the SEC's dismissal. TMTG is largely owned by Donald J."  
  checker: **yes** evidence "the SEC enforcement case against his crypto company Cumberland"; An SEC enforcement case against the named company Cumberland implies alleged wrongdoing; the quid pro quo issue is also raised.
- `1de632dab9335c9c100d` Simply Bitcoin, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): ">> So, a man that just left the White House is telling us that the last administration sold Bitcoin in ways that looked designed to hurt the price. So, if this has happened before, who would want Bitcoin cheap right now?"  
  checker: **yes** evidence "the last administration sold Bitcoin in ways that looked designed to hurt the price"; The identifiable 'last administration' is alleged to have sold Bitcoin in ways designed to hurt the price, i.e. deliberate conduct amounting to wrongdoing.
- `9cdf8b72eb50664c43fa` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "Some new data is circulating that is suggesting that the world's largest Bitcoin exchange could be responsible for Bitcoin's recent dump. And let's not forget Binance recently saw a recordbreaking $6.3 billion hack."  
  checker: **yes** evidence "the world's largest Bitcoin exchange could be responsible for Bitcoin's recent dump"; The quote suggests an identifiable organisation, the world's largest Bitcoin exchange, may be responsible for Bitcoin's recent dump, hedged by 'could be' but still an allegation.
- `edb9fcbe1b3562c5501f` TFTC, 2026-11-11; miner claude-opus-5-5 flags ['accusation', 'politics_non_btc'] (windows 1): "And we were actually very close to a deal like that that would have gotten conservatives more than they ever could have dreamed. Cuz when there was the mass deportation mandate in the beginning of the Trump administration, the left-wing open borders think tanks were ready to make a deal. You know who blew that up? Donald John Trump with his own scaling back of the anti-, you know, illegal immigrant metric."  
  checker: **yes** evidence "You know who blew that up? Donald John Trump with his own scaling back of the anti-, you know, illegal immigrant metric."; The quote attributes fault to a named person: Donald John Trump blew up the near deal by scaling back the metric, which is wrongdoing by an identifiable individual.

#### accusation | miner_yes | checker no
- `00c4fbc5da052487e949` Simply Bitcoin, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "It it's a pretty pretty, you know, I would say lackluster kind of FUD or disagreement with Bitcoin when he is the authorized participant of the Black Rockck ETF, which is the best performing ETF for Black Rockck. Like, he's making a ton of money off Bitcoin and yet he still comes out and says, you know, I don't really like it. It's like, okay, cool, cool story, bro."  
  checker: **no**; The quote merely describes an identifiable person's lackluster disagreement/FUD with Bitcoin despite profiting from it; it criticizes but does not allege wrongdoing.
- `aa0de859851aebbcd0ea` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I can't tell you why, but when one venue keeps forcing liquidations while spot demand keeps getting stronger, that isn't a normal market. And once that pressure stops, spot usually shows you where price wanted to go all along."  
  checker: **no**; The quote attributes the behaviour only to 'one venue', unnamed and unidentified; no specific person or organisation is named, so it does not meet the definition of an accusation.
- `bb072f70e2ae0ffcbece` The Bitcoin Layer, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "We know that the ECB president, Christine Lagarde, just left the institution very recently. Maybe she wanted to get out ahead of some more dangerous events going on in the European financial system."  
  checker: **no**; The quote only notes Lagarde's departure and speculates ('Maybe she wanted...') about her motive; no fault or misconduct by any named party is alleged.
- `c62c26c16bf870c757a1` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "We're from Wall Street. We wear the suits. We're way more trustworthy."  
  checker: **no**; The quote only makes positive self-claims ('way more trustworthy'); it states no wrongdoing by any named or identifiable person or organisation.
- `e704e4b545366868f2b8` Bitcoin Audible, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'politics_non_btc'] (windows 1): "I think it's spooky and you see the lengths that like governments and stuff are going to get hold of people's Bitcoin. wouldn't surprise me if I'm not saying the government themselves are doing it necessarily, but like if they have someone's back and say like, "Look, we're going to turn a blind eye to this because like we're broke and we need some Bitcoin.""  
  checker: **no**; The quote only speculates: 'wouldn't surprise me if' and 'not saying the government themselves are doing it necessarily' — no wrongdoing is asserted, and 'governments' is generic, not named.

#### accusation | miner_no | checker yes
- `fb5462ac859350a4890d` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "One, obviously, don't keep your Bitcoin on exchanges. And two, if you are trading on these exchanges, you should at the very least expect that these exchanges are counterrading you and they are trying to liquidate you because they want your Bitcoin."  
  checker: **yes** evidence "these exchanges are counterrading you and they are trying to liquidate you because they want your Bitcoin"; Exchanges are identifiable organisations; the quote alleges they countertrade and liquidate users because they want their Bitcoin, i.e. they act against users' interests.
- `a5e9ed4abfc5bcbcee5c` BTC Sessions, 2026-11-11; miner qwen/qwen3.8-27b flags ['single_source_breaking', 'time_sensitive'] (windows 1): ">> You know what? I I actually I it I will agree with you even though we're talking strategy. I will I will agree with you because I had a conversation today for a podcast coming out next week with someone. I'll just leave it at that. Um, and he actually shared some things he's never shared publicly before, but it was specifically referring to Al Salvador um, with regards to pressure to prevent Bitcoin from being in these positions."  
  checker: **yes** evidence "it was specifically referring to Al Salvador um, with regards to pressure to prevent Bitcoin from being in these positions."; The quote says there was pressure on El Salvador to prevent Bitcoin, alleging improper pressure by an identifiable party in that context.

#### accusation | miner_no | checker no
- `90e7bbb3468bfdcf3cbc` Bitcoin Magazine, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "Um and thirdly, it has a fixed supply of 21 million which gives it this um you know hedge against long-term debasement trade. Um and if any of those three things are ever called into question then I'd immediately sell all my Bitcoin and buy gold."  
  checker: **no**; The quote only describes Bitcoin's fixed supply and the speaker's selling condition; no wrongdoing by any named or identifiable party is alleged.
- `1d98b77703b3c5fb6651` Simply Bitcoin, 2026-11-10; miner claude-opus-5-5 flags ['imperative', 'time_sensitive'] (windows 1): "Mark Harvey put Bitcoin on the power law curve, a model which is fitted to Bitcoin's entire price history. And on this model, Bitcoin below 76,839 is below its lower level on the power band, which historically has been a great time to buy. It's been when the FTX collapse happened, during the COVID crash, major shocks, and every single time Bitcoin has rebounded powerfully."  
  checker: **no**; The quote only describes Mark Harvey's price model and past market events (FTX collapse, COVID crash) as timing context; it states no wrongdoing by any named person or organisation.
- `ee62d106350a67cc428a` Bitcoin Magazine, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative', 'time_sensitive'] (windows 1): ">> Yeah, I would say that Bitcoin life insurance is 40% on sale. Uh, so they should go and they should go and buy a life insurance policy with us."  
  checker: **no**; The quote only promotes a product, saying Bitcoin life insurance is 40% on sale and urging people to buy a policy; it alleges no wrongdoing by any named or identifiable person or organisation.
- `c9fe4a64430c294a05f0` DataDash, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "We've seen an almost 20% decline. And so, we're at, you know, obviously when we're looking for more de-risking and a little bit of more scale out into strength type of situation."  
  checker: **no**; The quote only reports a ~20% decline and the speaker's own de-risking/scale-out strategy; no wrongdoing by any named or identifiable person or organisation is alleged.
- `a25c69cf74aa3d0111cc` Bitcoin Magazine, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "So that's good news. You can sell your Bitcoin and at least you can buy the dip in gold."  
  checker: **no**; The quote only gives advice about selling Bitcoin and buying gold; it names no person or organisation and alleges no wrongdoing.

#### single_source_breaking | miner_yes | checker yes
- `962102c4a2b80420b390` DataDash, 2026-11-11; miner claude-opus-5-5 flags ['single_source_breaking'] (windows 1): "Bitcoin staking on Stacks began its initial institutional rollout in September 2026, and the first bond attracted approximately 230 Bitcoin. The second bond expanded to roughly 505 Bitcoin. And among the early institutional participants were 21 Shares, HashKey Cloud, UTXO Management, and Cipher Capital. And the second bond required approximately 6.75 million Stacks to be paired with the Bitcoin positions."  
  checker: **yes** evidence "Bitcoin staking on Stacks began its initial institutional rollout in September 2026, and the first bond attracted approximately 230 Bitcoin. The second bond expanded to roughly 505 Bitcoin. And among the early institutional participants were 21 Shares, HashKey Cloud, UTXO Management, and Cipher Capital. And the second bond required approximately 6.75 million Stacks to be paired with the Bitcoin positions."; Speaker reports specific new facts—dates, BTC amounts, named participants—about the recent Stacks institutional rollout, with no cited source, so it rests on this speaker alone.
- `4bac36830b753fb0a66e` BTC Sessions, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'politics_non_btc', 'single_source_breaking'] (windows 1): "Uh, it would appear that uh our our everybody's current favorite uh CEO um of Nvidia uh he had another affair. >> No."  
  checker: **yes** evidence "it would appear that uh our our everybody's current favorite uh CEO um of Nvidia uh he had another affair"; Speaker reports Nvidia's CEO had another affair, a current-event claim with no cited source, so it rests on this speaker alone.
- `64ab8aa47797d93e6a93` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "Binance has been liquidating everyone over and over since the hack. Open interest rate builds and a wick takes the book out."  
  checker: **yes** evidence "Binance has been liquidating everyone over and over since the hack."; The speaker, citing no other source, asserts as fact that Binance has repeatedly liquidated traders since the hack — a current-event claim resting on this speaker alone.
- `44918e1456e858d64101` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "And like in like when the red team were doing their thing, they obviously scanned every repo on Bitcoin, found no critical vulnerabilities. Like I think Rob came out and said libec what P or whatever that that repos."  
  checker: **yes** evidence "when the red team were doing their thing, they obviously scanned every repo on Bitcoin, found no critical vulnerabilities"; Reports a current event: a red team scanned all Bitcoin repos and found no critical vulnerabilities, sourced only to this speaker.
- `9fcd1656b45fa9a1891d` Coffeezilla, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "One of these investors in TMTG is Don Wilson, who weeks prior had the SEC enforcement case against his crypto company Cumberland dismissed with prejudice. Now in response to my request for comment, Cumberland denied any quid pro quo and connection between the Trump Media investment and the SEC's dismissal. TMTG is largely owned by Donald J."  
  checker: **yes** evidence "Now in response to my request for comment, Cumberland denied any quid pro quo and connection between the Trump Media investment and the SEC's dismissal."; Coffeezilla reports his own finding: Cumberland told him directly it denied quid pro quo, a new factual claim about the recent SEC dismissal resting on his sole reporting.

#### single_source_breaking | miner_yes | checker no
- `c1f47e2329192118b0bd` BTC Sessions, 2026-11-11; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "And uh, and this can include your Bitcoin wallets, your keys. So, uh, we'll talk about what is affected and what you should do."  
  checker: **no**; The quote only says wallets and keys can be included and promises to discuss what is affected; it states no specific new factual claim about a current event.
- `b7ae3de139f9e3db388b` Yahoo Finance, 2026-11-11; miner claude-opus-5-5 flags ['single_source_breaking', 'time_sensitive'] (windows 1): "And it has been reported by uh ex White House advisor Patrick Whit that Trump remains interested in buying Bitcoin for US Strategic Reserve, but legal and custody issues stall process progress."  
  checker: **no**; The claim is attributed to another source, not this speaker alone: 'it has been reported by uh ex White House advisor Patrick Whit', so it fails the resting-on-this-speaker-alone test.
- `9cdf8b72eb50664c43fa` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "Some new data is circulating that is suggesting that the world's largest Bitcoin exchange could be responsible for Bitcoin's recent dump. And let's not forget Binance recently saw a recordbreaking $6.3 billion hack."  
  checker: **no**; Quote attributes claim to circulating data, not speaker alone; second sentence is background, not new breaking claim.
- `d3579c7d953ba27163f1` CoinDesk, 2026-11-12; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "I'm waiting on this rotation narrative to emerge and I've been hearing it in various corners that you know after the anthropic IPO, there's not many huge AI related IPOs uh waiting to to happen, right? At some point, uh, AI kind of ends its Cambrian explosion phase, just like we saw with the ICO era and altcoins and memecoins and Bitcoin. Um, and then capital rotates to back to fundamentals or back where uh taking on that risk yields the highest reward, which we all hope will be Bitcoin."  
  checker: **no**; The quote offers speculation about a future rotation narrative, not a new factual claim about a current event; it's the speaker's opinion and prediction.
- `88deba3b23f5f865cfc3` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "18 years ago on November 9th, Satoshi registered Bitcoin on SourceForge. Now, look at that date. I saw the tweet that day and thought, "Oh, that's interesting.""  
  checker: **no**; The quote recounts a historical fact from 18 years ago (Satoshi registering Bitcoin on SourceForge) and the speaker's past reaction, not a new factual claim about a current event.

#### single_source_breaking | miner_no | checker yes
- `bbd396e76827e34df5c9` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "So, Binance is in a very tricky position right now where they've been around for the longest, but a new upstart, someone that literally worked at Binance started a new exchange, Hyperliquid, and everyone is starting to use Hyperlid because they don't trust Binance. So, Binance is in a strange position right now."  
  checker: **yes** evidence "someone that literally worked at Binance started a new exchange, Hyperliquid, and everyone is starting to use Hyperlid because they don't trust Binance"; The speaker alone asserts the current facts that a former Binance employee launched Hyperliquid and users are shifting to it, citing no other source.
- `224912640684b56b0bb9` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I'm talking about all the the other ones where they basically done pipe investments to pump their stocks. Now they're down in the dirt really bad, but they're also now very humbled because they're like, "Okay, I thought we had it all sorted out."  
  checker: **yes** evidence "they basically done pipe investments to pump their stocks. Now they're down in the dirt really bad"; Speaker alone asserts unnamed companies did PIPE investments to pump stocks and are now down badly; a current-state factual claim with no cited source, resting on him alone.
- `e5085743fab00640c4e8` BTC Sessions, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'time_sensitive'] (windows 1): "So again things are looking a little bit worse there getting a little bit bubbly but also on top of that wanted to throw in there we had the Binance hack from not that long ago and it turns out that the Binance CFO apparently has resigned. So another interesting kind of apparently I was finding that there was some information they had planned to resign for a while but again a little suspicious exit."  
  checker: **yes** evidence "it turns out that the Binance CFO apparently has resigned"; The speaker reports the Binance CFO's resignation as recent news without naming any other source, so the new factual claim about a current event rests on him alone.
- `e2168822533fa0b919b3` Bankless, 2026-11-11; miner claude-opus-5-5 flags ['imperative', 'time_sensitive'] (windows 1): "And so like the way I kind of see it is I will put on these more longer term overarching thesis through options trades, but then on a day like you know yesterday for example, you know, Bitcoin at 70, you know, 52 might have been a really interesting per long just for a quick scalp up to back up to like 76. And that's not necessarily a trade that I want to go in and like cross the spread on options as much for. Um, and so I'm always trading in and out of some of the delta that I have from my options um via per."  
  checker: **yes** evidence "on a day like you know yesterday for example, you know, Bitcoin at 70, you know, 52 might have been a really interesting per long just for a quick scalp up to back up to like 76"; Speaker cites yesterday's Bitcoin price (~70,52) as a scalp opportunity to ~76, a new factual claim about a current event resting on this speaker alone.
- `c9adac7e64b60e33cc7e` TFTC, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'time_sensitive'] (windows 1): "I mean, my world, Bitcoin, crypto. The fact that he launched the Trump coin uh the night before the inauguration was completely insane to me, but obviously the reports of Susie Wild's children getting very cushy lobbyist jobs um very close to the administration, it's I mean, they just created such easy soft targets on their backs for when the blue Nami eventually hit."  
  checker: **yes** evidence "The fact that he launched the Trump coin uh the night before the inauguration"; Speaker asserts as fact that the Trump coin launched the night before the inauguration, a current-event claim presented on this speaker's own authority.

#### single_source_breaking | miner_no | checker no
- `a185e29f61267d834b5c` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "And of course, keep buying that Bitcoin, keep hodling that Bitcoin, keep storing that Bitcoin. This is how we win."  
  checker: **no**; The quote is a motivational call to action (keep buying, hodling, storing), not a new factual claim about a current event, so it rests on no factual assertion at all.
- `8dfa9df7dbfcb31507b1` CoinTelegraph, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "So if you think about it, stablecoins are going to continue growing regardless of what happens in crypto or even in AI. Stablecoins are just one of these omnipresent trends. Doesn't really matter."  
  checker: **no**; The quote offers a general opinion/prediction that stablecoins will keep growing, not a new factual claim about a current event, so it does not meet the definition.
- `241bfaee53b5bee735a1` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I mean, you've got the same coins I've got. Like you've got BTC Sh, you got XPTt or whatever. But like the the like kind of the ignorance to what's actually happening felt like very gaslighty."  
  checker: **no**; The quote only offers opinions about shared coins and a feeling that things are 'very gaslighty' - subjective commentary, not a new factual claim about a current event.
- `4fd92203561233275a66` Coffeezilla, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "And one [music] of them is the crypto stuff. The crypto stuff's nuts."  
  checker: **no**; Only a vague opinion, 'The crypto stuff's nuts'; no specific factual claim about a current event, so it does not meet the definition.
- `4f74babec484b3b240f0` Altcoin Daily, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): ">> Uh yeah, I I would just say look, I mean, I I've said this many times like have a plan stick to it. You know, some people will use this analysis and then go panic sell their Bitcoin and then they get mad when it rallies back up, you know, a few thousand dollars. It's happened several times over the last two, you know, month and a half or whatever."  
  checker: **no**; General advice ('have a plan stick to it') and a repeated pattern ('happened several times over the last... month and a half'), not a new factual claim about a specific current event.
