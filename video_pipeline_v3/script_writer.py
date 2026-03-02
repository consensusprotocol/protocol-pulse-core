#!/usr/bin/env python3
"""Step 4: Script writer — generates MMA-Central-style narration scripts.
Uses Claude API when available, falls back to curated sample scripts."""
import json, os, sys
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from relay import get_key

NARRATION_PROMPT = """You are the lead anchor for "Pulse Check" — Bitcoin's version of ESPN SportsCenter meets MMA Central.

Your delivery style:
- HIGH ENERGY but INTELLIGENT. Think Skip Bayless meets Max Keiser meets a war correspondent.
- Short, punchy, rapid-fire sentences. Every word earns its place.
- You don't just introduce stories — you SET THE STAGE.
- You have TAKES. You're not a neutral newsreader.
- Urgency is your default.
- Conversational. Never stiff. Never corporate.
- End every episode with "Stay sovereign."

BANNED phrases: "Let's dive in", "Without further ado", "Buckle up", "In today's episode",
"Hey guys", "What's going on everybody", "game changer", "paradigm shift", "to the moon", "LFG".

Given these top stories from today's Bitcoin intelligence:
{stories}

Write a BROADCAST SCRIPT. Return ONLY valid JSON:
{{
  "episode_title": "string",
  "cold_open": "string (15-20 seconds of speech)",
  "segments": [
    {{
      "headline": "5-8 word headline",
      "narration": "full narration for this segment",
      "keywords_for_visuals": ["keyword1", "keyword2"],
      "duration_seconds": 18,
      "bridge_to_next": "string or null",
      "editorial_drop": "string or null"
    }}
  ],
  "outro": "string ending with Stay sovereign.",
  "total_estimated_duration_seconds": 90
}}"""


def generate_script_claude(stories: list[dict]) -> dict:
    """Generate script via Claude API."""
    key = get_key("ANTHROPIC_API_KEY")
    if not key or not HAS_ANTHROPIC:
        return None
    client = anthropic.Anthropic(api_key=key)
    stories_text = "\n\n".join(
        f"STORY {i+1}: {s.get('title','Untitled')}\n{s.get('summary', s.get('content',''))[:500]}"
        for i, s in enumerate(stories[:7])
    )
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": NARRATION_PROMPT.format(stories=stories_text)}]
    )
    text = resp.content[0].text
    # Extract JSON from response
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text)


def generate_sample_script(style: str = "default") -> dict:
    """Curated sample scripts for testing when APIs are unavailable."""
    if style == "breaking":
        return {
            "episode_title": "The Hash Rate Hammer",
            "cold_open": (
                "Bitcoin just posted the largest mining difficulty adjustment in eighteen months. "
                "Meanwhile, three nation-states are quietly stacking sats through sovereign wealth funds. "
                "And that lightning network capacity number everyone ignored last week? "
                "It just became the most important metric in Bitcoin. This is Pulse Check."
            ),
            "segments": [
                {
                    "headline": "Mining Difficulty Hits All-Time Record",
                    "narration": (
                        "The numbers don't lie. Bitcoin's mining difficulty just ratcheted up "
                        "another four point seven percent. That's the highest absolute difficulty "
                        "in the network's history. Translation? More hash power is securing "
                        "this network than ever before. Miners aren't leaving. They're doubling down. "
                        "Every joule of energy pointed at this chain is a vote of confidence "
                        "that the market hasn't priced in yet."
                    ),
                    "keywords_for_visuals": ["bitcoin mining", "data center", "server room"],
                    "duration_seconds": 20,
                    "bridge_to_next": "And while miners are building, governments are buying.",
                    "editorial_drop": None
                },
                {
                    "headline": "Sovereign Wealth Funds Accumulating Bitcoin",
                    "narration": (
                        "Three sovereign wealth funds have disclosed Bitcoin positions this quarter. "
                        "Norway. Singapore. Abu Dhabi. Combined allocation? North of twelve billion dollars. "
                        "This isn't speculation. This is central planning meeting decentralized money. "
                        "When the entities that print fiat start hoarding the exit asset, "
                        "pay attention."
                    ),
                    "keywords_for_visuals": ["government finance", "global economy", "gold vault"],
                    "duration_seconds": 18,
                    "bridge_to_next": "But here is where it gets really interesting.",
                    "editorial_drop": (
                        "Here's what nobody is connecting. The same week sovereign funds disclose "
                        "Bitcoin positions, the Fed quietly extends dollar swap lines to nine central banks. "
                        "The dollar system is cracking and the smart money knows where the lifeboat is."
                    )
                },
                {
                    "headline": "Lightning Network Breaks Capacity Record",
                    "narration": (
                        "Five thousand eight hundred Bitcoin. That is the new lightning network capacity. "
                        "Record high. But the real story isn't the number. It's the velocity. "
                        "Capacity doubled in ninety days. Payment volume tripled. "
                        "Layer two is doing exactly what it was designed to do. "
                        "Scale Bitcoin for the everyday transaction without compromising the base layer."
                    ),
                    "keywords_for_visuals": ["lightning network", "digital payments", "technology network"],
                    "duration_seconds": 18,
                    "bridge_to_next": None,
                    "editorial_drop": None
                },
                {
                    "headline": "ETF Flows Signal Institutional Conviction",
                    "narration": (
                        "BlackRock's Bitcoin ETF just logged its twentieth consecutive day of net inflows. "
                        "Twenty days. No breaks. No profit-taking. These are pension funds, endowments, "
                        "family offices systematically moving capital into Bitcoin. "
                        "This is not a trade. This is an allocation. There is a difference."
                    ),
                    "keywords_for_visuals": ["stock market", "wall street", "financial trading"],
                    "duration_seconds": 17,
                    "bridge_to_next": None,
                    "editorial_drop": None
                }
            ],
            "outro": (
                "The hash rate is screaming. Sovereign money is moving. Lightning is scaling. "
                "And the institutions? They're not asking if anymore. They're asking how much. "
                "This has been Pulse Check from Protocol Pulse. Stay sovereign."
            ),
            "total_estimated_duration_seconds": 105
        }
    else:
        return {
            "episode_title": "The Quiet Accumulation",
            "cold_open": (
                "While the market sleeps, the smart money moves. Bitcoin just reclaimed a critical "
                "technical level that historically precedes explosive moves. MicroStrategy filed for "
                "another billion dollar raise. And a leaked central bank memo suggests the monetary "
                "endgame is closer than anyone thinks. This is Pulse Check."
            ),
            "segments": [
                {
                    "headline": "Bitcoin Reclaims Key Technical Level",
                    "narration": (
                        "Bitcoin just closed above its two hundred day moving average for the "
                        "first time in six weeks. Every time this has happened in the last decade, "
                        "the subsequent ninety-day return averaged forty-seven percent. "
                        "History doesn't repeat, but it rhymes. And right now, "
                        "the chart is singing a very familiar tune."
                    ),
                    "keywords_for_visuals": ["bitcoin chart", "cryptocurrency", "financial graph"],
                    "duration_seconds": 18,
                    "bridge_to_next": "Speaking of conviction, one company is putting its balance sheet where its mouth is.",
                    "editorial_drop": None
                },
                {
                    "headline": "MicroStrategy Raises Another Billion",
                    "narration": (
                        "Michael Saylor is not done. MicroStrategy just filed to raise another "
                        "one point two billion dollars in convertible notes. Proceeds? All Bitcoin. "
                        "The company now holds over two hundred thousand Bitcoin. "
                        "Say what you will about the strategy, but Saylor is playing a game "
                        "most CEOs don't have the conviction to even understand."
                    ),
                    "keywords_for_visuals": ["corporate office", "business meeting", "digital currency"],
                    "duration_seconds": 20,
                    "bridge_to_next": "And while corporations stack, the cypherpunks are building.",
                    "editorial_drop": (
                        "Let me put Saylor's position in perspective. MicroStrategy's Bitcoin "
                        "treasury is now worth more than the GDP of over sixty countries. "
                        "One company. One asset. Think about that."
                    )
                },
                {
                    "headline": "Nostr Protocol Sees Explosive Growth",
                    "narration": (
                        "The Nostr protocol just crossed two million monthly active users. "
                        "That might sound small in a world of billions. But remember, "
                        "Bitcoin had fewer users than that in twenty thirteen. "
                        "Censorship-resistant social media isn't a nice-to-have anymore. "
                        "It's infrastructure for free speech. And it's being built on "
                        "Bitcoin's rails."
                    ),
                    "keywords_for_visuals": ["social media", "network connection", "digital freedom"],
                    "duration_seconds": 18,
                    "bridge_to_next": "Now, this next story might be the most important of the day.",
                    "editorial_drop": None
                },
                {
                    "headline": "Central Bank Memo Reveals Monetary Concern",
                    "narration": (
                        "A leaked internal memo from the European Central Bank suggests "
                        "policymakers are far more worried about Bitcoin adoption than they publicly admit. "
                        "The memo references quote the inability to control monetary transmission "
                        "in a dual-currency environment end quote. Read that again. "
                        "They're not worried about Bitcoin crashing. "
                        "They're worried about Bitcoin succeeding."
                    ),
                    "keywords_for_visuals": ["european central bank", "government building", "monetary policy"],
                    "duration_seconds": 22,
                    "bridge_to_next": None,
                    "editorial_drop": None
                }
            ],
            "outro": (
                "The technicals are aligning. Corporate treasuries are converting. "
                "The builders are building. And the central bankers? They're worried. "
                "As they should be. "
                "This has been Pulse Check from Protocol Pulse. Stay sovereign."
            ),
            "total_estimated_duration_seconds": 110
        }


def generate_script(stories: list[dict] = None, style: str = "default") -> dict:
    """Generate a narration script. Tries Claude API first, falls back to sample."""
    if stories:
        result = generate_script_claude(stories)
        if result:
            print("[script] Generated via Claude API")
            return result
    print(f"[script] Using curated sample script (style={style})")
    return generate_sample_script(style)


if __name__ == "__main__":
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    print(json.dumps(script, indent=2))
