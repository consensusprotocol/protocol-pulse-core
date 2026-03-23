# F-P3-8: External API Layer — Foundation Document

## Purpose
Authenticated REST + SSE stream for institutional access with rate limiting.

## Authentication
- Header: Authorization: Bearer <key>
- Key: UUID4, stored in users table
- Management: /intelligence/api page

## Endpoints (all /api/v1/*)
- GET /state — full SentinelState + price + FNG
- GET /mempool, /convergence, /alerts, /sentiment, /sovereign, /network
- GET /stream — SSE real-time stream
- POST /keys/generate — generate new API key
- GET /docs — JSON schema of all endpoints

## Rate Limiting
- Commander: 100 req/min (to be added via Flask-Limiter)
- Sovereign: 1000 req/min
- Currently: no rate limit (Phase 3 MVP)

## WebSocket
- Implemented as SSE stream (sync gunicorn limitation)
- /api/v1/stream functions identically to /api/intelligence/stream
