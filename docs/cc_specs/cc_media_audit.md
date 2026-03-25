Read VISUAL_DESIGN_SYSTEM.md and PIPELINE_LAWS.md.
Read templates/media_hub.html fully.
Read services/rss_service.py fully.
Then run utils/cross_llm_audit.py on templates/media_hub.html with these 8 questions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEDIA PAGE — WORLD-CLASS BITCOIN MEDIA COMMAND CENTER
Goal: The definitive Bitcoin media hub. Every voice. Every signal.
One screen. No competitor comes close. Ship by Friday.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FULL PODCAST RSS FEEDS TO AGGREGATE:
- Cypherpunk'd: https://anchor.fm/s/fa724db8/podcast/rss
- Protocol Pulse: https://feed.podbean.com/protocolpulse/feed.xml
- TFTC (Matt Odell): https://feeds.simplecast.com/mGJ8uw1O
- Stephan Livera: https://feeds.simplecast.com/KV8z39iS
- What Bitcoin Did: https://feeds.simplecast.com/tEJEubMT
- Bitcoin Audible: https://feeds.megaphone.fm/SWN4978045882
- Citadel Dispatch: https://feeds.simplecast.com/M6LkF8NN
- The Bitcoin Layer: https://feeds.simplecast.com/BdGT7E3F
- Simply Bitcoin: https://feeds.simplecast.com/7V5b8Zag
- Bitcoin Magazine Podcast: https://feeds.megaphone.fm/bitcoin-magazine
- Rabbit Hole Recap: https://feeds.simplecast.com/Dh1oHsHZ
- Preston Pysh / TIP: https://feeds.simplecast.com/WXOL8WUD
- Natalie Brunell Coin Stories: https://feeds.simplecast.com/6Z1iM0Fg
- Bitcoin Fundamentals: https://feeds.simplecast.com/WXOL8WUD

YOUTUBE CHANNELS:
- Bitcoin Magazine: UCvRRgjjKvabNkSP0w3QdW3A
- Coin Bureau: UCqK_GSMbpiV8spgD3ZGloSw
- What Bitcoin Did: UCBcRF18a7Qf58cCRy5xuWwQ
- Simply Bitcoin: UCm7SUL4HMiM3UFEWP-E_Qhg
- Robert Breedlove: UCFmHIftfI9HRaL6r3zScKOg
- Natalie Brunell: UCIl1wX8yxEjkbCFBKbhAqeg
- Bitcoin Audible: UCJz4rEsEHpx9ht7a5JIHh5g

AUDIT QUESTIONS for Gemini + GPT-4o + Grok (independently, then cross-validate):

1. ARCHITECTURE: What is the optimal backend architecture for aggregating 
   15 RSS feeds + 7 YouTube channels + live X/Nostr KOL feeds simultaneously
   WITHOUT blocking Flask workers or degrading site performance?
   Consider: background jobs, Redis caching, SQLite caching, async fetching.
   What refresh interval per source type is optimal?

2. D3 NETWORK GRAPH: Design the Bitcoin voice network topology visualization.
   Nodes = Bitcoin voices/channels. Edges = cross-references/mentions.
   How do we detect when voices reference each other (quote tweets, mentions)?
   What data structure backs this? How do we animate node pulses on new posts?
   What's the D3.js force simulation config for ~50 nodes to look stunning?
   How do we handle hover cards with live data without API hammering?

3. LIVE TICKER: Design the hyperlinked scrolling ticker at the top.
   Each item must deep-link to the exact source (podcast episode, tweet, video).
   How do we handle link generation for RSS items, YouTube videos, X posts, Nostr?
   What's the smoothest CSS animation that doesn't stutter on mobile?
   How do we prioritize items (breaking news > new episode > tweet)?

4. SIGNAL SCORE: Design a 0-100 Signal Score for all content.
   Inputs: our KOL sentiment pipeline, engagement metrics, topic relevance,
   source tier (Tier 1 = Odell/Livera/McCormack, etc).
   Formula that's backtestable against price action?
   How do we calculate this on ingest without API costs?

5. CLIPS ENGINE: Design the automated Bitcoin media clip extraction system.
   When our sentiment pipeline flags a high-signal moment (>85% confidence):
   - YouTube: extract timestamp, generate 60-90s clip via yt-dlp + ffmpeg
   - Podcast: extract timestamp from transcript, clip audio
   - Overlay: Protocol Pulse branded animated waveform + quote text
   - Output: vertical 9:16 MP4 for sharing
   What's the queue architecture? GPU usage? Storage requirements?
   Can this run on our 4x RTX 4090 without interfering with render pipeline?

6. EMBEDDED PLAYER: How do we embed podcast episodes without redirect?
   Options: native HTML5 audio element with RSS mp3 URL, Spotify embed,
   Apple Podcasts embed, custom player. Which works reliably for all 15 feeds?
   How do we handle DRM/protected content?

7. ENGAGEMENT LAYER (alternative to blockchain wall):
   Instead of a literal drawing wall, what engagement features would make
   Bitcoin users ACTUALLY return daily and share with others?
   Think: streak tracking, signal accuracy scoring (did you call the move?),
   community price prediction market (Protocol Pulse-native, not Polymarket),
   "soundboard" of famous Bitcoin quotes triggered by price events,
   achievement badges for sovereign behaviors (node runner, self-custody, etc).
   Which 3 features have highest viral coefficient?

8. CLAUDE ON INGEST: The AI-generated 30-word summaries for each episode.
   This uses the Anthropic API (Claude claude-sonnet-4-6), NOT local models.
   How do we batch-process RSS items efficiently to minimize API cost?
   What's the optimal prompt for a 30-word Bitcoin-native signal summary?
   How do we cache summaries so we only generate once per episode?
   Estimated monthly cost for 15 feeds × ~20 episodes/week?

AFTER AUDIT — BUILD PHASE 1 (Friday deadline):

PRIORITY ORDER:
1. Background RSS aggregation service (15 feeds, 15min cache, SQLite storage)
2. YouTube latest videos fetcher (7 channels, 1hr cache)  
3. Three-column Feed Matrix on media_hub.html (podcasts | video | KOL+intel)
4. Live scrolling ticker with hyperlinks (CSS animation, no JS libraries)
5. Signal Score calculation on ingest
6. Episode embedded player (HTML5 audio, direct RSS mp3 URL)
7. AI summary generation (batch, cached, Anthropic API)

PHASE 2 (next week):
- D3 network topology graph
- Clips Engine
- Voice Index directory
- Engagement layer

DESIGN REQUIREMENTS:
- Extends base.html but overrides hero section completely
- Match existing media_hub.html glass morphism dark style
- JetBrains Mono for data, DM Sans for body
- Red/black/white Protocol Pulse brand
- Mobile-first responsive
- NO placeholder data anywhere — real feeds or loading skeletons

IMPORTANT: Run rss_service.py feeds first to see what data format we get.
Then design the DB schema for caching (ExternalFeed, ExternalEpisode tables).
Then build the routes: /media loads cached data, background job refreshes.

git add -A && git commit -m "feat(media): Bitcoin Media Command Center — RSS aggregator, Feed Matrix, ticker, signal scores" && git push
