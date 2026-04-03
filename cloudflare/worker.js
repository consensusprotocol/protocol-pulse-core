/**
 * Protocol Pulse — Cloudflare Worker Edge Cache
 *
 * Intercepts /api/* requests, serves from CF Cache API when possible,
 * falls back to origin (Ultron) on miss, and serves stale on origin error.
 *
 * Free tier: 100K requests/day, Cache API included.
 */

// ---------------------------------------------------------------------------
// Cache TTL configuration (seconds)
// ---------------------------------------------------------------------------
const CACHE_RULES = [
  // Fast-moving price data — 60s
  { pattern: '/api/btc-price',              ttl: 60  },
  { pattern: '/api/v2/terminal/price',      ttl: 60  },

  // Medium-frequency data — 300s
  { pattern: '/api/v2/terminal/fear-greed', ttl: 300 },
  { pattern: '/api/v2/terminal/mempool',    ttl: 300 },
  { pattern: '/api/v2/terminal/latest',     ttl: 300 },
  { pattern: '/api/v2/terminal/topics',     ttl: 300 },
  { pattern: '/api/v2/terminal/sentiment',  ttl: 300 },
  { pattern: '/api/v2/terminal/breaking',   ttl: 300 },
  { pattern: '/api/media/stats',            ttl: 300 },
  { pattern: '/api/charts/fear-greed',      ttl: 300 },
  { pattern: '/api/charts/mempool-data',    ttl: 300 },

  // Slow-moving data — 600s
  { pattern: '/api/v2/terminal/macro',      ttl: 600 },
  { pattern: '/api/v2/terminal/onchain',    ttl: 600 },
  { pattern: '/api/v2/terminal/lightning',  ttl: 600 },
  { pattern: '/api/sovereign-context',      ttl: 600 },
  { pattern: '/api/charts/price-history',   ttl: 600 },
  { pattern: '/api/charts/hashrate-history', ttl: 600 },
  { pattern: '/api/charts/pool-distribution', ttl: 600 },
  { pattern: '/api/charts/fee-history',     ttl: 600 },
  { pattern: '/api/charts/lightning',       ttl: 600 },
];

// Authenticated / mutating endpoints — never cache
const NEVER_CACHE = [
  '/api/v2/terminal/keys',
  '/api/v2/terminal/signal',       // commander-only, user-specific
  '/api/v2/terminal/alerts',       // commander-only
  '/api/v2/terminal/stream',       // SSE stream
  '/api/v2/terminal/subscribe',    // POST
  '/api/v2/terminal/docs',         // tiny, auth-gated
  '/api/charts/price-alert',       // POST
  '/api/charts/ai-explain',        // POST
  '/api/media/ingest',             // POST
];

// Stale grace period — serve stale cache up to this long after TTL expires
const STALE_TTL = 3600; // 1 hour

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Find the cache TTL for a given URL pathname, or null if not cacheable.
 */
function getCacheTTL(pathname) {
  // Never cache mutating / auth-gated endpoints
  for (const prefix of NEVER_CACHE) {
    if (pathname.startsWith(prefix)) return null;
  }

  // Exact-prefix match against rules (longest match wins naturally since
  // we iterate in order and patterns don't overlap)
  for (const rule of CACHE_RULES) {
    if (pathname === rule.pattern || pathname.startsWith(rule.pattern + '/')) {
      return rule.ttl;
    }
  }

  // Default for unknown /api/* paths: don't cache (safe default)
  return null;
}

/**
 * Build CORS headers applied to every response.
 */
function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
  };
}

/**
 * Clone a Response with extra headers merged in.
 */
function withHeaders(response, extra) {
  const headers = new Headers(response.headers);
  for (const [k, v] of Object.entries(extra)) {
    headers.set(k, v);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

// ---------------------------------------------------------------------------
// Main handler
// ---------------------------------------------------------------------------

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    // Only intercept /api/* GET requests
    if (!url.pathname.startsWith('/api/') || request.method !== 'GET') {
      return fetch(request);
    }

    const ttl = getCacheTTL(url.pathname);

    // Not cacheable — pass through to origin
    if (ttl === null) {
      const originResp = await fetch(request);
      return withHeaders(originResp, {
        ...corsHeaders(),
        'X-Cache': 'BYPASS',
      });
    }

    // Use the default CF cache (caches.default)
    const cache = caches.default;

    // Normalize cache key — strip cookies / auth headers by using a plain Request
    const cacheKey = new Request(url.toString(), {
      method: 'GET',
      headers: {},
    });

    // --- Try cache first ---
    let cachedResponse = await cache.match(cacheKey);

    if (cachedResponse) {
      // Check if the cached response is still fresh via our custom header
      const cachedAt = parseInt(cachedResponse.headers.get('X-Cached-At') || '0', 10);
      const age = Math.floor(Date.now() / 1000) - cachedAt;

      if (age < ttl) {
        // Fresh — serve from cache
        return withHeaders(cachedResponse, {
          ...corsHeaders(),
          'X-Cache': 'HIT',
          'X-Cache-Age': String(age),
          'X-Cache-TTL': String(ttl),
          'Cache-Control': `public, max-age=${ttl - age}, stale-while-revalidate=${STALE_TTL}`,
        });
      }

      // Stale but within grace period — serve stale, revalidate in background
      if (age < ttl + STALE_TTL) {
        ctx.waitUntil(revalidate(cache, cacheKey, request, ttl));
        return withHeaders(cachedResponse, {
          ...corsHeaders(),
          'X-Cache': 'STALE',
          'X-Cache-Age': String(age),
          'X-Cache-TTL': String(ttl),
          'Cache-Control': `public, max-age=0, stale-while-revalidate=${STALE_TTL}`,
        });
      }

      // Expired beyond grace — fall through to origin fetch
    }

    // --- Cache miss or fully expired — fetch from origin ---
    try {
      const originResp = await fetch(request);

      if (!originResp.ok) {
        // Origin returned an error — serve stale if we have it
        if (cachedResponse) {
          return withHeaders(cachedResponse, {
            ...corsHeaders(),
            'X-Cache': 'STALE-ERROR',
            'X-Origin-Status': String(originResp.status),
            'Cache-Control': `public, max-age=0, stale-while-revalidate=${STALE_TTL}`,
          });
        }
        // No stale cache — return the error
        return withHeaders(originResp, {
          ...corsHeaders(),
          'X-Cache': 'MISS',
        });
      }

      // Success — cache and return
      const now = Math.floor(Date.now() / 1000);
      const responseToCache = withHeaders(originResp.clone(), {
        'X-Cached-At': String(now),
        'Cache-Control': `public, max-age=${ttl + STALE_TTL}`,
      });

      ctx.waitUntil(cache.put(cacheKey, responseToCache));

      return withHeaders(originResp, {
        ...corsHeaders(),
        'X-Cache': 'MISS',
        'X-Cache-TTL': String(ttl),
        'Cache-Control': `public, max-age=${ttl}, stale-while-revalidate=${STALE_TTL}`,
      });

    } catch (err) {
      // Origin unreachable — serve stale if available
      if (cachedResponse) {
        return withHeaders(cachedResponse, {
          ...corsHeaders(),
          'X-Cache': 'STALE-ERROR',
          'X-Origin-Error': err.message || 'fetch failed',
          'Cache-Control': `public, max-age=0, stale-while-revalidate=${STALE_TTL}`,
        });
      }

      // Nothing to serve
      return new Response(
        JSON.stringify({ error: 'Origin unreachable', detail: err.message }),
        {
          status: 502,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders(),
            'X-Cache': 'ERROR',
          },
        }
      );
    }
  },
};

// ---------------------------------------------------------------------------
// Background revalidation
// ---------------------------------------------------------------------------

async function revalidate(cache, cacheKey, originalRequest, ttl) {
  try {
    const resp = await fetch(originalRequest);
    if (resp.ok) {
      const now = Math.floor(Date.now() / 1000);
      const toCache = withHeaders(resp, {
        'X-Cached-At': String(now),
        'Cache-Control': `public, max-age=${ttl + STALE_TTL}`,
      });
      await cache.put(cacheKey, toCache);
    }
  } catch {
    // Revalidation failed — stale entry remains
  }
}
