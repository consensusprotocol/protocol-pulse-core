# F-P3-4: P2P Exchange Volume Aggregator — Foundation Document

## Purpose
Non-KYC P2P volume by region as a capital flight signal. Uses HodlHodl offer
counts as volume proxy.

## Data Source
- HodlHodl: https://hodlhodl.com/api/v1/offers
- Volume proxy: offer_count * 0.05 BTC (conservative median)

## Capital Flight Detection
- Cross-reference offer counts with hostile jurisdictions from jurisdiction_db.json
- Spike in hostile jurisdiction offers → CAPITAL_FLIGHT signal

## Output: Embedded in SentinelState.sovereign.p2p_volume sub-dict

## Integration
- Extends services/sovereign_engine.py (no new file)
- Runs as part of sovereign cycle every 5 min
