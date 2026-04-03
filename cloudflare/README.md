# Protocol Pulse — Cloudflare Worker Edge Cache

Caches `/api/*` responses at CF edge PoPs worldwide. Free tier (100K req/day).

## What it does

- Intercepts GET requests to `/api/*` on protocolpulse.io
- Serves from CF Cache API on HIT (sub-10ms latency)
- Falls back to Ultron origin on MISS, caches the response
- Serves stale cache (up to 1 hour old) when origin is down or slow
- Adds `X-Cache` header: HIT, MISS, STALE, STALE-ERROR, BYPASS, ERROR
- Never caches authenticated endpoints (keys, signal, alerts, streams)

## Cache TTLs

| Endpoint | TTL |
|----------|-----|
| `/api/btc-price`, `/api/v2/terminal/price` | 60s |
| `/api/v2/terminal/fear-greed`, `/mempool`, `/latest`, `/topics`, `/sentiment`, `/breaking` | 300s |
| `/api/media/stats`, `/api/charts/fear-greed`, `/api/charts/mempool-data` | 300s |
| `/api/v2/terminal/macro`, `/onchain`, `/lightning` | 600s |
| `/api/sovereign-context`, `/api/charts/price-history`, `/hashrate-history`, etc. | 600s |

## Deployment

```bash
# 1. Install wrangler
npm install -g wrangler

# 2. Authenticate with Cloudflare
wrangler login

# 3. Deploy (uses wrangler.toml config)
cd ~/protocol_pulse/cloudflare
wrangler deploy

# 4. Deploy to production (with route binding)
wrangler deploy --env production
```

## Verify

```bash
# Check X-Cache header
curl -s -D - https://protocolpulse.io/api/btc-price 2>&1 | grep -i x-cache

# First request: X-Cache: MISS
# Second request: X-Cache: HIT
# After TTL: X-Cache: STALE (revalidates in background)

# Full response with headers
curl -v https://protocolpulse.io/api/v2/terminal/price 2>&1 | grep -E '< (X-Cache|Cache-Control)'
```

## Rollback

```bash
# Remove the worker (traffic goes direct to origin)
wrangler delete
```

## Architecture

```
Client --> CF Edge (Worker) --> Cache API
                |                  |
                | (MISS)           | (HIT)
                v                  v
            Ultron:5000        Cached Response
```

No KV store, no Durable Objects, no paid features. Pure Cache API.
