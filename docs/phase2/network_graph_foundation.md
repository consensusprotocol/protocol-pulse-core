# Network State Graph — Phase 2 F5 Foundation

## Overview
D3.js v7 force-directed visualization of live Bitcoin network topology.
Hub-and-spoke: mining pools + exchanges + LN hubs connected to central Sentinel node.

## Node Types
1. **SENTINEL** (center): Red (#FF0000), size 20, always present
2. **MINING POOLS**: From recent blocks in SentinelState. Size proportional to hashrate %.
   Color: green (<25%), amber (25-40%), red (>40%)
3. **EXCHANGES**: From custodian_wallets.json. Size 12, blue (#3B82F6)
4. **LN HUBS** (future): Top routing nodes from mempool.space LN API

## D3 Force Parameters
- forceCenter: center of SVG
- forceManyBody: strength -150
- forceLink: distance 100, strength 0.4
- forceCollide: radius = node_size + 8
- alphaDecay: 0.05

## Update & Throttle
- Data refreshes every 60s (same as PCAF)
- Render throttled: skip if last render < 5s ago
- Smooth: only repositions nodes, doesn't recreate simulation

## Interactivity
- Hover: tooltip with node label + metric
- Labels rendered for nodes > size 10
- No click-expand in v1

## Audit Decisions
- Hub-and-spoke is honest about data model (we monitor, not represent P2P topology)
- SVG only (no canvas/WebGL per PIPELINE_LAWS — Three.js BANNED)
- D3 loaded from CDN with defer attribute
