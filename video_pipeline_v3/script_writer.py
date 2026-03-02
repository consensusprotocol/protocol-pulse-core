#!/usr/bin/env python3
"""Script writer V4 — dual-host dialogue format for Pulse Check.
Generates Joe Rogan-style banter between two hosts discussing Bitcoin news.
Uses Claude API when available, falls back to curated sample scripts."""
import json, os, sys
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from relay import get_key

DIALOGUE_PROMPT = """You are the head writer for "Pulse Check" — a dual-host Bitcoin show.
Two hosts discuss the day's Bitcoin/crypto intelligence in a casual, Joe Rogan podcast style.

HOST 1 (Jessica) — The anchor. Sharp, data-driven, sets up stories with authority.
HOST 2 (Chris) — The co-host. Reacts naturally, asks follow-ups, drops hot takes.

Style rules:
- CASUAL BANTER. Not news anchors. Think two smart friends at a bar discussing Bitcoin.
- Short sentences. Conversational rhythm. Interruptions. Reactions.
- Real opinions and takes — not neutral reporting.
- Natural transitions: "Wait, hold on—", "Dude, that's wild", "OK but here's the thing..."
- NO banned phrases: "Let's dive in", "Without further ado", "Buckle up", "game changer", "paradigm shift", "to the moon", "LFG", "Hey guys", "What's going on everybody"
- End with "Stay sovereign."
- Include CLIP markers where a YouTube clip would naturally fit (e.g., after introducing a story that has video evidence)

Given these top stories from today's Bitcoin intelligence:
{stories}

Current BTC price: {btc_price}

Return ONLY valid JSON:
{{
  "episode_title": "short punchy title",
  "dialogue": [
    {{"host": 1, "text": "Jessica's line here"}},
    {{"host": 2, "text": "Chris's reaction/follow-up"}},
    {{"host": 1, "text": "Jessica continues..."}},
    {{"host": "CLIP", "text": "[PLAYS: description of clip]", "source": "@ChannelName", "query": "search terms for yt-dlp"}},
    {{"host": 2, "text": "Chris reacts to clip..."}}
  ],
  "chapters": [
    {{"title": "Intro", "time_hint": "start"}},
    {{"title": "Topic 1 headline", "time_hint": "after_intro"}},
    {{"title": "Topic 2 headline", "time_hint": "mid"}},
    {{"title": "Outro", "time_hint": "end"}}
  ],
  "thumbnail": {{
    "headline": "BOLD THUMBNAIL TEXT (5-8 words max)",
    "subtext": "secondary line",
    "style": "dramatic"
  }},
  "segments_summary": ["headline1", "headline2", "headline3"],
  "total_estimated_duration_seconds": 120
}}

IMPORTANT: The dialogue array is the ENTIRE show script in order. Mix hosts naturally.
Aim for 15-25 dialogue entries for a ~2 minute show. Include 1-2 CLIP markers."""


def generate_script_claude(stories: list[dict], btc_price: str = "N/A") -> dict:
    """Generate dual-host dialogue script via Claude API."""
    key = get_key("ANTHROPIC_API_KEY")
    if not key or not HAS_ANTHROPIC:
        return None
    client = anthropic.Anthropic(api_key=key)
    stories_text = "\n\n".join(
        f"STORY {i+1}: {s.get('title','Untitled')}\n{s.get('summary', s.get('content',''))[:500]}"
        for i, s in enumerate(stories[:7])
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": DIALOGUE_PROMPT.format(
            stories=stories_text, btc_price=btc_price
        )}]
    )
    text = resp.content[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text)


def generate_sample_script(style: str = "default") -> dict:
    """Curated dual-host sample scripts for testing without APIs."""
    if style == "breaking":
        return {
            "episode_title": "The Hash Rate Hammer",
            "dialogue": [
                {"host": 1, "text": "Bitcoin just posted the largest mining difficulty adjustment in eighteen months. Three nation-states are quietly stacking sats through sovereign wealth funds. And that lightning network number everyone ignored? It just became the most important metric in Bitcoin. This is Pulse Check."},
                {"host": 2, "text": "OK so let's start with this difficulty adjustment because the numbers are insane."},
                {"host": 1, "text": "Four point seven percent. Highest absolute difficulty in the network's history. More hash power securing this chain than ever before."},
                {"host": 2, "text": "Miners aren't leaving. They're doubling down. Every joule of energy pointed at this chain is a vote of confidence the market hasn't priced in yet."},
                {"host": 1, "text": "And while miners are building, governments are buying. Three sovereign wealth funds disclosed Bitcoin positions this quarter."},
                {"host": 2, "text": "Wait — which ones?"},
                {"host": 1, "text": "Norway. Singapore. Abu Dhabi. Combined allocation north of twelve billion dollars."},
                {"host": 2, "text": "Dude. When the entities that print fiat start hoarding the exit asset, that tells you everything you need to know."},
                {"host": "CLIP", "text": "[PLAYS: Mining facility walkthrough]", "source": "@BitcoinMagazine", "query": "bitcoin mining facility 2024"},
                {"host": 1, "text": "Look at that hash rate climbing. Now here's where it gets interesting — lightning network just hit five thousand eight hundred Bitcoin in capacity."},
                {"host": 2, "text": "Record high. But the real story is the velocity. Capacity doubled in ninety days. Payment volume tripled."},
                {"host": 1, "text": "Layer two is doing exactly what it was designed to do. Scale Bitcoin without compromising the base layer."},
                {"host": 2, "text": "And this is happening while BlackRock's ETF just logged twenty consecutive days of net inflows. Twenty days. No breaks."},
                {"host": 1, "text": "These are pension funds, endowments, family offices. This isn't a trade. This is an allocation. There's a difference."},
                {"host": 2, "text": "Massive difference. The smart money isn't asking if anymore. They're asking how much."},
                {"host": 1, "text": "The hash rate is screaming. Sovereign money is moving. Lightning is scaling. This has been Pulse Check from Protocol Pulse. Stay sovereign."},
            ],
            "chapters": [
                {"title": "Intro", "time_hint": "start"},
                {"title": "Mining Difficulty All-Time High", "time_hint": "after_intro"},
                {"title": "Sovereign Wealth Funds Buying BTC", "time_hint": "mid"},
                {"title": "Lightning Network Record", "time_hint": "mid"},
                {"title": "ETF Flows Signal Conviction", "time_hint": "late"},
                {"title": "Outro", "time_hint": "end"},
            ],
            "thumbnail": {
                "headline": "HASH RATE BREAKS ALL RECORDS",
                "subtext": "Nations are stacking",
                "style": "dramatic",
            },
            "segments_summary": [
                "Mining Difficulty Hits All-Time Record",
                "Sovereign Wealth Funds Accumulating Bitcoin",
                "Lightning Network Breaks Capacity Record",
                "ETF Flows Signal Institutional Conviction",
            ],
            "total_estimated_duration_seconds": 105,
        }
    else:
        return {
            "episode_title": "The Quiet Accumulation",
            "dialogue": [
                {"host": 1, "text": "While the market sleeps, the smart money moves. Bitcoin just reclaimed a critical level. MicroStrategy filed for another billion dollar raise. And a leaked central bank memo suggests the monetary endgame is closer than anyone thinks. This is Pulse Check."},
                {"host": 2, "text": "Alright Jessica, let's talk about this two hundred day moving average reclaim because that's a big deal."},
                {"host": 1, "text": "Every time Bitcoin has closed above the two hundred day MA after being below it for six weeks, the next ninety days averaged forty-seven percent returns."},
                {"host": 2, "text": "History doesn't repeat but it rhymes. And right now the chart is singing a familiar tune."},
                {"host": 1, "text": "Speaking of conviction — Michael Saylor is not done. MicroStrategy just filed to raise another one point two billion in convertible notes. All going to Bitcoin."},
                {"host": 2, "text": "The company now holds over two hundred thousand Bitcoin. Say what you will about the strategy but Saylor is playing a game most CEOs can't even understand."},
                {"host": "CLIP", "text": "[PLAYS: Saylor interview clip]", "source": "@MicroStrategy", "query": "michael saylor bitcoin interview 2024"},
                {"host": 1, "text": "Let me put that in perspective. MicroStrategy's Bitcoin treasury is now worth more than the GDP of sixty countries. One company. One asset."},
                {"host": 2, "text": "That's wild. And meanwhile the cypherpunks are building. Nostr just crossed two million monthly active users."},
                {"host": 1, "text": "Might sound small in a world of billions. But remember — Bitcoin had fewer users than that in twenty thirteen."},
                {"host": 2, "text": "Censorship-resistant social media isn't a nice-to-have anymore. It's infrastructure for free speech built on Bitcoin's rails."},
                {"host": 1, "text": "Now this next one might be the most important. A leaked ECB memo suggests policymakers are far more worried about Bitcoin adoption than they publicly admit."},
                {"host": 2, "text": "What did it say exactly?"},
                {"host": 1, "text": "Quote: the inability to control monetary transmission in a dual-currency environment. They're not worried about Bitcoin crashing. They're worried about Bitcoin succeeding."},
                {"host": 2, "text": "And they should be. The technicals are aligning. Corporate treasuries are converting. The builders are building."},
                {"host": 1, "text": "This has been Pulse Check from Protocol Pulse. Stay sovereign."},
            ],
            "chapters": [
                {"title": "Intro", "time_hint": "start"},
                {"title": "Bitcoin Reclaims 200-Day MA", "time_hint": "after_intro"},
                {"title": "MicroStrategy's Billion Dollar Bet", "time_hint": "mid"},
                {"title": "Nostr Hits 2M Users", "time_hint": "mid"},
                {"title": "ECB Leaked Memo", "time_hint": "late"},
                {"title": "Outro", "time_hint": "end"},
            ],
            "thumbnail": {
                "headline": "SMART MONEY IS MOVING",
                "subtext": "Central banks are worried",
                "style": "dramatic",
            },
            "segments_summary": [
                "Bitcoin Reclaims Key Technical Level",
                "MicroStrategy Raises Another Billion",
                "Nostr Protocol Explosive Growth",
                "Central Bank Memo Reveals Concern",
            ],
            "total_estimated_duration_seconds": 110,
        }


def generate_script(stories: list[dict] = None, style: str = "default",
                    btc_price: str = "N/A") -> dict:
    """Generate a dual-host dialogue script. Tries Claude API first, falls back to sample."""
    if stories:
        result = generate_script_claude(stories, btc_price)
        if result:
            print("[script] Generated via Claude API (dual-host dialogue)")
            return result
    print(f"[script] Using curated sample script (style={style})")
    return generate_sample_script(style)


if __name__ == "__main__":
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    print(json.dumps(script, indent=2))
