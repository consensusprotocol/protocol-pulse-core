# PROTOCOL PULSE INTELLIGENCE TERMINAL
# New Chat Handoff — Ready to Build
# Created: 2026-03-23

## WHAT WE'RE BUILDING
The world's most sophisticated autonomous Bitcoin intelligence platform.
Reuters wire room + Bloomberg terminal + Matrix Sentinel running 24/7.

Not a dashboard. A living intelligence system that watches everything
simultaneously and surfaces signal before anyone else sees it.

## INFRASTRUCTURE (already exists on Ultron)
- Server: Ultron (AMD EPYC 9R14, 4x RTX 4090, Ubuntu 22.04)
- Relay: POST https://relay.protocolpulse.io/exec
  Token: 581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552
  Python3 urllib only, ssl._create_unverified_context(), 25s timeout
- Repo: consensusprotocol/protocol-pulse-core (main branch)
- Flask app: ~/protocol_pulse/core/ (self-hosted, Cloudflare Tunnel)
- Live site: protocolpulse.io

## EXISTING DATA FEEDS (already running)
- On-chain: mempool.space API, block explorer, hashrate/difficulty
- Price: CoinGecko + mempool.space fallback (every 15 min)
- Fear & Greed: Alternative.me (every 30 min)
- Social/X: Nitter scraper + x_spaces_scraper (TIER1 handles)
- Macro: TradFi signals (DXY, gold, 10Y yield, SPY)
- ETF: Blockware Intel scraper
- News: Article engine (1,300+ articles, Claude-generated)
- X Spaces: 50+ TIER1 handles monitored noon-11pm ET

## EXISTING SERVICES (already built)
- Morning brief: Qwen3 primary, Claude Haiku fallback
- Tweet machine: 3/day max, global gate, angle diversity
- Video pipeline: autonomous daily Pulse Check episode
- Oracle: AI chat avatar on-site
- Watchdog: autonomous CC healing with QWEN_CONTEXT_BIBLE.md

## THE PRODUCT VISION
Three layers:

LAYER 1 — THE SENTINEL (always-on autonomous monitoring)
Watches 47+ signal sources simultaneously. Pattern detection.
Multi-signal correlation. Anomaly flagging. Never sleeps.
When something matters, it fires. When it doesn't, silence.

LAYER 2 — THE TERMINAL (professional intelligence interface)
War room aesthetic. Real-time feeds. Signal hierarchy.
The thing you open before markets move. The thing that
makes Bloomberg look like a newspaper.

LAYER 3 — THE WIRE (distribution)
When the Sentinel detects something critical, it pushes:
- Telegram alert (immediate)
- Terminal banner (real-time)
- X post (if signal score >= 9/10)
- Video episode injection (for next Pulse Check)
- Commander brief update (for $29 subscribers)

## THE AUDIT IS COMPLETE
The cross-LLM competitive audit has been run:
docs/cc_intelligence_terminal_audit.md — the audit spec
docs/intelligence_terminal_v1_spec.md — the v1 build spec

START HERE:
1. Fetch: https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/docs/handoff/CURRENT_STATE.md
2. Read: ~/protocol_pulse/docs/intelligence_terminal_v1_spec.md
3. Read: ~/protocol_pulse/docs/audits/intelligence_terminal_audit_2026-03-23.md
4. Build the Sentinel first (Layer 1) — it powers everything else

## OPERATIONAL RULES
- AUDIT FIRST: Every feature → competitive product audit first
- CC sessions: tmux, unset ANTHROPIC_API_KEY, --dangerously-skip-permissions
- Never drip-feed — comprehensive all-in-one prompts only
- Commit everything: git add + commit + push, no asking for confirmation
- QWEN_CONTEXT_BIBLE.md: read before any pipeline-touching work
- One CC session at a time on same repo

## THIS IS THE THING
When someone opens this terminal at 6am and sees:
  [CRITICAL] 3 central banks coordinated reserve adjustment — 
  Bitcoin historically +340% in following 18 months last 2x this happened.
  On-chain accumulation accelerating. ETF inflows reversing.
  
That's when they cancel their Bloomberg subscription.
