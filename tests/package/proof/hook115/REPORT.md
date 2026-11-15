# RULING 115 (3): THE HOOK QUESTION WITH PBX'S EXAMPLES (report before use)

Measured 2026-11-15T20:07:36+00:00 (UTC), seed 7, each hook asked alone. A model takes the job only when every approved hook's own-job rating (min(scroll, alone)) is >= 4 AND every negative's is <= 3. The ten rated are the examples the question carries; LEAVE-ONE-OUT asks each with itself left out of the examples.

| model | variant | approved (5) | negatives (5) | passes |
|---|---|---|---|---|
| xai:grok-4.20-0309-reasoning | as ordered | [4, 4, 4, 4, None] | [1, 1, 1, 1, 1] | no |
| xai:grok-4.20-0309-reasoning | leave-one-out | [None, 3, 4, 3, 3] | [2, 1, 2, 1, 1] | no |
| heimdall:qwen/qwen3.8-27b | as ordered | [4, 4, 4, 4, 4] | [1, 1, 1, 1, 1] | YES |
| heimdall:qwen/qwen3.8-27b | leave-one-out | [2, 3, 3, 3, 4] | [2, 1, 1, 1, 1] | no |

Every rating (scroll / alone / setup, and the model's reason):

- xai:grok-4.20-0309-reasoning, as ordered, approved ref-preview (DataDash): 4 (4/5/4) by xai:grok-4.20-0309-reasoning: somewhat dry factual open lacks strong intrigue
- xai:grok-4.20-0309-reasoning, as ordered, approved ref-37c5b5f5 (Saifedean Ammous): 4 (4/5/5) by xai:grok-4.20-0309-reasoning: first seconds somewhat abstract to instantly stop scrolls
- xai:grok-4.20-0309-reasoning, as ordered, approved ref-41f29b1f (Natalie Brunell): 4 (4/5/5) by xai:grok-4.20-0309-reasoning: first seconds somewhat abstract to instantly stop scroll
- xai:grok-4.20-0309-reasoning, as ordered, approved ref-0c68b589 (Simply Bitcoin): 4 (4/5/5) by xai:grok-4.20-0309-reasoning: first 2-3s on CEO mistake not instantly gripping
- xai:grok-4.20-0309-reasoning, as ordered, approved ref-13949b7c (Simply Bitcoin): NO RATING: ProviderError: coherence_verdict: every back-end unavailable: [('xai:grok-4.20-0309-reasoning', 'same model as the generator: skipped')]; answers out of contract: [('xai:grok-4.20-0309-reasoning', 'JSONDecodeError: 
- xai:grok-4.20-0309-reasoning, as ordered, negative neg-adf6d9c5 (Scott Melker): 1 (2/1/2) by xai:grok-4.20-0309-reasoning: starts mid-conversation with 'You know'
- xai:grok-4.20-0309-reasoning, as ordered, negative neg-f5f005b9 (CoinTelegraph): 1 (2/1/3) by xai:grok-4.20-0309-reasoning: assumes prior context with 'all that said'
- xai:grok-4.20-0309-reasoning, as ordered, negative neg-d7578b88 (CNBC Television): 1 (2/1/3) by xai:grok-4.20-0309-reasoning: starts mid-conversation with 'though' and 'here'
- xai:grok-4.20-0309-reasoning, as ordered, negative neg-2e77a0a7 (The Bitcoin Layer): 1 (2/1/2) by xai:grok-4.20-0309-reasoning: leans on prior context with though and here
- xai:grok-4.20-0309-reasoning, as ordered, negative neg-994ca307 (Simply Bitcoin): 1 (1/1/2) by xai:grok-4.20-0309-reasoning: references prior statements on show
- xai:grok-4.20-0309-reasoning, leave-one-out, approved ref-preview (DataDash): NO RATING: ProviderError: coherence_verdict: every back-end unavailable: [('xai:grok-4.20-0309-reasoning', 'same model as the generator: skipped')]; answers out of contract: [('xai:grok-4.20-0309-reasoning', 'JSONDecodeError: 
- xai:grok-4.20-0309-reasoning, leave-one-out, approved ref-37c5b5f5 (Saifedean Ammous): 3 (3/5/4) by xai:grok-4.20-0309-reasoning: lacks punch to immediately stop scroll
- xai:grok-4.20-0309-reasoning, leave-one-out, approved ref-41f29b1f (Natalie Brunell): 4 (4/5/4) by xai:grok-4.20-0309-reasoning: abstract claim lacks urgent punch to stop scroll
- xai:grok-4.20-0309-reasoning, leave-one-out, approved ref-0c68b589 (Simply Bitcoin): 3 (3/5/4) by xai:grok-4.20-0309-reasoning: first seconds lack direct Bitcoin punch
- xai:grok-4.20-0309-reasoning, leave-one-out, approved ref-13949b7c (Simply Bitcoin): 3 (3/5/4) by xai:grok-4.20-0309-reasoning: first seconds too general/academic to stop scroll
- xai:grok-4.20-0309-reasoning, leave-one-out, negative neg-adf6d9c5 (Scott Melker): 2 (2/2/3) by xai:grok-4.20-0309-reasoning: You know and still imply prior context
- xai:grok-4.20-0309-reasoning, leave-one-out, negative neg-f5f005b9 (CoinTelegraph): 1 (2/1/3) by xai:grok-4.20-0309-reasoning: starts mid-conversation with 'all that said'
- xai:grok-4.20-0309-reasoning, leave-one-out, negative neg-d7578b88 (CNBC Television): 2 (2/2/3) by xai:grok-4.20-0309-reasoning: mid-conversation start with 'though' and 'here'
- xai:grok-4.20-0309-reasoning, leave-one-out, negative neg-2e77a0a7 (The Bitcoin Layer): 1 (2/1/2) by xai:grok-4.20-0309-reasoning: mid-conversation with 'though' and 'here'
- xai:grok-4.20-0309-reasoning, leave-one-out, negative neg-994ca307 (Simply Bitcoin): 1 (1/1/2) by xai:grok-4.20-0309-reasoning: starts mid-conversation referencing prior show comments
- heimdall:qwen/qwen3.8-27b, as ordered, approved ref-preview (DataDash): 4 (4/5/3) by heimdall:qwen/qwen3.8-27b: setup is weakest — a concrete data point informs but doesn't create strong narrative tension pulling the viewer into the next clip
- heimdall:qwen/qwen3.8-27b, as ordered, approved ref-37c5b5f5 (Saifedean Ammous): 4 (4/5/3) by heimdall:qwen/qwen3.8-27b: Self-contained assertion; completes its own thought without leaving a strong pull toward the next clip.
- heimdall:qwen/qwen3.8-27b, as ordered, approved ref-41f29b1f (Natalie Brunell): 4 (4/5/4) by heimdall:qwen/qwen3.8-27b: scroll: bold declarative but a single clean sentence without a number, contradiction, or question to break the scroll pattern in a Bitcoin-heavy feed
- heimdall:qwen/qwen3.8-27b, as ordered, approved ref-0c68b589 (Simply Bitcoin): 4 (4/5/4) by heimdall:qwen/qwen3.8-27b: The clip is so self-contained and resolves with a punchy tricolon that it slightly undercuts the pull toward the next clip.
- heimdall:qwen/qwen3.8-27b, as ordered, approved ref-13949b7c (Simply Bitcoin): 4 (4/5/4) by heimdall:qwen/qwen3.8-27b: strong standalone line, but slightly abstract and less urgent than a concrete hook
- heimdall:qwen/qwen3.8-27b, as ordered, negative neg-adf6d9c5 (Scott Melker): 1 (2/1/2) by heimdall:qwen/qwen3.8-27b: Opens with 'You know' and 'it's still an asset' — both signal mid-conversation; a first-time listener has no referent for 'still' and no reason to stop scrolling.
- heimdall:qwen/qwen3.8-27b, as ordered, negative neg-f5f005b9 (CoinTelegraph): 1 (2/1/2) by heimdall:qwen/qwen3.8-27b: starts mid-conversation with 'all that said' and 'if you remember'
- heimdall:qwen/qwen3.8-27b, as ordered, negative neg-d7578b88 (CNBC Television): 1 (2/1/3) by heimdall:qwen/qwen3.8-27b: Opens with 'though' and 'here'—explicit mid-conversation markers; a first-time listener has no idea what it's contrasting with or where 'here' is.
- heimdall:qwen/qwen3.8-27b, as ordered, negative neg-2e77a0a7 (The Bitcoin Layer): 1 (2/1/2) by heimdall:qwen/qwen3.8-27b: starts with 'though' and 'here', mid-conversation
- heimdall:qwen/qwen3.8-27b, as ordered, negative neg-994ca307 (Simply Bitcoin): 1 (1/1/2) by heimdall:qwen/qwen3.8-27b: starts with 'As I've said', referencing prior show context
- heimdall:qwen/qwen3.8-27b, leave-one-out, approved ref-preview (DataDash): 2 (2/4/2) by heimdall:qwen/qwen3.8-27b: Flat data point; no tension, question, or implication to pull the viewer into the next clip.
- heimdall:qwen/qwen3.8-27b, leave-one-out, approved ref-37c5b5f5 (Saifedean Ammous): 3 (3/5/2) by heimdall:qwen/qwen3.8-27b: self-contained, little open loop
- heimdall:qwen/qwen3.8-27b, leave-one-out, approved ref-41f29b1f (Natalie Brunell): 3 (3/5/4) by heimdall:qwen/qwen3.8-27b: Bold but familiar Bitcoin claim; lacks the specificity or surprise to truly stop a scroll.
- heimdall:qwen/qwen3.8-27b, leave-one-out, approved ref-0c68b589 (Simply Bitcoin): 3 (3/5/4) by heimdall:qwen/qwen3.8-27b: awkward first line dulls immediate scroll stop
- heimdall:qwen/qwen3.8-27b, leave-one-out, approved ref-13949b7c (Simply Bitcoin): 4 (4/5/4) by heimdall:qwen/qwen3.8-27b: Strong self-contained opener, but the first line is a general principle about currencies rather than a specific, immediately gripping claim or data point.
- heimdall:qwen/qwen3.8-27b, leave-one-out, negative neg-adf6d9c5 (Scott Melker): 2 (2/2/2) by heimdall:qwen/qwen3.8-27b: 'You know' and 'still' are mid-conversation markers; 'nothing's changed' answers a prior objection the viewer hasn't heard.
- heimdall:qwen/qwen3.8-27b, leave-one-out, negative neg-f5f005b9 (CoinTelegraph): 1 (2/1/2) by heimdall:qwen/qwen3.8-27b: 'Now, all that said' and 'So if you remember' are textbook mid-conversation markers; a first-time listener has no referent for 'all that' or what to remember.
- heimdall:qwen/qwen3.8-27b, leave-one-out, negative neg-d7578b88 (CNBC Television): 1 (2/1/2) by heimdall:qwen/qwen3.8-27b: 'though' and 'here' mark it as mid-conversation, answering a prior point the viewer never heard
- heimdall:qwen/qwen3.8-27b, leave-one-out, negative neg-2e77a0a7 (The Bitcoin Layer): 1 (2/1/2) by heimdall:qwen/qwen3.8-27b: 'though' and 'here' are mid-conversation markers; 'caveat' references prior context the viewer never heard
- heimdall:qwen/qwen3.8-27b, leave-one-out, negative neg-994ca307 (Simply Bitcoin): 1 (2/1/2) by heimdall:qwen/qwen3.8-27b: 'As I've said multiple times on this show' explicitly references prior content, a textbook mid-conversation opener that a first-time viewer can't follow.

Spent $0.1062 (vendor-reported, SPEND_H115.json).

The question as asked (as ordered: every example in):

```
You judge OPENING clips for 60-second videos made of other channels' own words (each clip is a person's
own words from a show). Each candidate below would play FIRST, before anything else is said. Judge each one ALONE, as
the opener of a video; the candidates are not compared with each other and never play together.

HOW PBX JUDGES OPENERS (his own verdicts; these are examples, NOT candidates, and are not rated here):
OPENERS PBX APPROVED: each one opened a video he approved for publishing.
  - "Bitcoin has now seen a 16 % decline from the overall high from $88 ,000, touching down towards about $73 ,400, $500, give or take." (DataDash)
  - "Bitcoin does not have any authority that allows people to take the wealth of others. If some people end up with more Bitcoin, that's because they chose to do that." (Saifedean Ammous)
  - "Bitcoin imposes a global free market for the first time ever." (Natalie Brunell)
  - "A CEO makes a personal mistake in shareholders pay. A government mismanages its currencies. and its savers pay. Bitcoin's rules aren't kept by a single executive or a single central bank. They're enforced by thousands of independent computers running the same code. No CEO, no compromise, no committee to debate." (Simply Bitcoin)
  - "Currencies are often born for political reasons, but fail for economic reasons. Bitcoin launched in January of 2009. It's never been renamed. It's never gone into another currency. It's never been redenominated or reissued." (Simply Bitcoin)
OPENERS THAT FAIL: each starts mid-conversation, leaning on something said before it ("you know", "all that said",
"though", "here", "as I've said"), so a viewer who hears it first has missed what it answers.
  - "You know, it's still an asset that you can buy. It's still an asset. Nothing's changed about the properties of Bitcoin. You can buy it now. Send it to anyone anywhere in the world. It's irreversible." (Scott Melker)
  - "Now, all that said, Bitcoin has gone through a lot of ups and downs, but I think the story here for crypto is not really about Bitcoin. So if you remember, Bitcoin was deemed a commodity a long time ago." (CoinTelegraph)
  - "There is, though, one potential bright spot here. Traders are increasingly betting against Bitcoin with funding rates in the futures market turning negative for the first time in a month. That kind of pessimism has in the past marked a short -term bottom, raising hopes that the worst of the selling may be over here." (CNBC Television)
  - "Bitcoin started turning though before liquidity turned red. And that's an important caveat here." (The Bitcoin Layer)
  - "As I've said multiple times on this show, if you are the lone Bitcoiner, it does get lonely. When you come into Bitcoin, you're the only one that has this realization." (Simply Bitcoin)

{hooks}

For EACH candidate: THE HOOK is judged on its own job, NOT on the through-line. Rate each of its three parts 1-5 separately:
   "scroll": do its first 2-3 seconds stop a viewer from scrolling past? (5 = certainly, 1 = not at all)
   "alone": does it stand alone, so that a viewer needs nothing said before it? (5 = fully, 1 = not at all)
   "setup": does it set up what follows, so that a viewer who hears it wants the next clip? (5 = certainly, 1 = not
   at all)
Give "why": a few words on the candidate's weakest part.
Return ONLY this JSON object: {{"hooks": {{{keys}}}}}
```
