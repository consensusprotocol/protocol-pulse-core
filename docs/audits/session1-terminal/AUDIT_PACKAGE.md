# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: session1-terminal
# Branch: feature/session1-terminal
# Generated: 2026-03-10 04:14 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)


---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: core/services/signal_engine.py (185 lines)
```
   1 | """
   2 | signal_engine.py — PP Signal Intelligence Score Engine
   3 | 
   4 | Computes a weighted composite signal score from 5 live data sources.
   5 | Weights: article sentiment 30%, price momentum 25%, onchain health 20%,
   6 |          social volume 15%, fear/greed 10%.
   7 | Caches result for 2 minutes to avoid quota burn.
   8 | """
   9 | 
  10 | import logging
  11 | import time
  12 | from datetime import datetime, timezone
  13 | 
  14 | import requests
  15 | 
  16 | logger = logging.getLogger("SignalEngine")
  17 | 
  18 | # Weight table (must sum to 1.0)
  19 | WEIGHTS = {
  20 |     "article_sentiment":  0.30,
  21 |     "price_momentum":     0.25,
  22 |     "onchain_health":     0.20,
  23 |     "social_volume":      0.15,
  24 |     "fear_greed_contrib": 0.10,
  25 | }
  26 | 
  27 | # In-process cache — avoids re-computing on every request
  28 | _cache: dict = {"data": None, "ts": 0.0, "ttl": 120}  # 2-minute TTL
  29 | 
  30 | 
  31 | # ── Component functions ───────────────────────────────────────────────────────
  32 | 
  33 | def _article_sentiment_score(db, models) -> int:
  34 |     """Average sentiment_score from SentimentReport (last 30 records) → 0-100."""
  35 |     try:
  36 |         reports = (models.SentimentReport.query
  37 |                    .filter(models.SentimentReport.sentiment_score.isnot(None))
  38 |                    .order_by(models.SentimentReport.created_at.desc())
  39 |                    .limit(30)
  40 |                    .all())
  41 |         if not reports:
  42 |             return 52  # slight bullish lean fallback
  43 |         values = []
  44 |         for r in reports:
  45 |             v = float(r.sentiment_score)
  46 |             # Normalise: stored as -1..1 → 0-100
  47 |             if -1.0 <= v <= 1.0:
  48 |                 v = (v + 1.0) * 50.0
  49 |             values.append(min(100.0, max(0.0, v)))
  50 |         return round(sum(values) / len(values))
  51 |     except Exception as exc:
  52 |         logger.warning("article_sentiment fallback: %s", exc)
  53 |         return 52
  54 | 
  55 | 
  56 | def _price_momentum_score() -> int:
  57 |     """BTC 24h price change mapped to 0-100 (centre at 0% = 50)."""
  58 |     try:
  59 |         r = requests.get(
  60 |             "https://api.coingecko.com/api/v3/simple/price",
  61 |             params={"ids": "bitcoin", "vs_currencies": "usd",
  62 |                     "include_24hr_change": "true"},
  63 |             timeout=6,
  64 |             headers={"Accept": "application/json"},
  65 |         )
  66 |         change = float(r.json().get("bitcoin", {}).get("usd_24h_change", 0) or 0)
  67 |         # ±10% range maps to 0-100
  68 |         score = 50.0 + change * 5.0
  69 |         return round(min(100, max(0, score)))
  70 |     except Exception as exc:
  71 |         logger.warning("price_momentum fallback: %s", exc)
  72 |         return 50
  73 | 
  74 | 
  75 | def _onchain_health_score() -> int:
  76 |     """Hashrate 3-day trend from mempool.space → 0-100."""
  77 |     try:
  78 |         r = requests.get(
  79 |             "https://mempool.space/api/v1/mining/hashrate/3d",
  80 |             timeout=6,
  81 |             headers={"Accept": "application/json"},
  82 |         )
  83 |         rates = r.json().get("hashrates", [])
  84 |         if len(rates) >= 2:
  85 |             latest = float(rates[-1].get("avgHashrate", 0) or 0)
  86 |             prev = float(rates[-2].get("avgHashrate", 1) or 1)
  87 |             if prev > 0:
  88 |                 pct = (latest - prev) / prev * 100.0
  89 |                 # ±5% maps to 0-100
  90 |                 score = 50.0 + pct * 10.0
  91 |                 return round(min(100, max(0, score)))
  92 |         return 60
  93 |     except Exception as exc:
  94 |         logger.warning("onchain_health fallback: %s", exc)
  95 |         return 60
  96 | 
  97 | 
  98 | def _social_volume_score(db, models) -> int:
  99 |     """Article count in the last 4 hours as proxy for social/media volume → 0-100."""
 100 |     try:
 101 |         from datetime import timedelta
 102 |         cutoff = datetime.utcnow() - timedelta(hours=4)
 103 |         count = (models.Article.query
 104 |                  .filter(models.Article.created_at >= cutoff,
 105 |                          models.Article.published == True)
 106 |                  .count())
 107 |         # 0 articles → 20, 20+ articles → 90 (cap)
 108 |         score = min(90, 20 + count * 3)
 109 |         return round(score)
 110 |     except Exception as exc:
 111 |         logger.warning("social_volume fallback: %s", exc)
 112 |         return 50
 113 | 
 114 | 
 115 | def _fear_greed_score() -> int:
 116 |     """Fear & Greed index from alternative.me → 0-100 (already on that scale)."""
 117 |     try:
 118 |         r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=6)
 119 |         value = int(r.json()["data"][0]["value"])
 120 |         return max(0, min(100, value))
 121 |     except Exception as exc:
 122 |         logger.warning("fear_greed fallback: %s", exc)
 123 |         return 50
 124 | 
 125 | 
 126 | # ── Classification ────────────────────────────────────────────────────────────
 127 | 
 128 | def classify_signal(score: int) -> str:
 129 |     if score >= 80:
 130 |         return "EXTREME BULLISH"
 131 |     elif score >= 65:
 132 |         return "BULLISH"
 133 |     elif score >= 45:
 134 |         return "NEUTRAL"
 135 |     elif score >= 30:
 136 |         return "BEARISH"
 137 |     else:
 138 |         return "EXTREME FEAR"
 139 | 
 140 | 
 141 | # ── Public API ────────────────────────────────────────────────────────────────
 142 | 
 143 | def compute_signal_score(db=None, models=None) -> dict:
 144 |     """
 145 |     Compute the PP Signal Intelligence score. Cached for 2 minutes.
 146 | 
 147 |     Returns:
 148 |         {
 149 |           "score":          int,        # 0-100 composite
 150 |           "classification": str,        # EXTREME FEAR / BEARISH / NEUTRAL / BULLISH / EXTREME BULLISH
 151 |           "components":     dict,       # per-component 0-100 scores
 152 |           "delta":          int,        # change from previous cached value (+/-)
 153 |           "ts":             str,        # ISO-8601 UTC timestamp
 154 |         }
 155 |     """
 156 |     now = time.monotonic()
 157 |     if _cache["data"] is not None and (now - _cache["ts"]) < _cache["ttl"]:
 158 |         return _cache["data"]
 159 | 
 160 |     components = {
 161 |         "article_sentiment":  _article_sentiment_score(db, models) if db else 52,
 162 |         "price_momentum":     _price_momentum_score(),
 163 |         "onchain_health":     _onchain_health_score(),
 164 |         "social_volume":      _social_volume_score(db, models) if db else 50,
 165 |         "fear_greed_contrib": _fear_greed_score(),
 166 |     }
 167 | 
 168 |     score = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
 169 |     score_int = round(score)
 170 |     classification = classify_signal(score_int)
 171 | 
 172 |     prev = _cache["data"]
 173 |     delta = (score_int - prev["score"]) if prev else 0
 174 | 
 175 |     result = {
 176 |         "score": score_int,
 177 |         "classification": classification,
 178 |         "components": components,
 179 |         "delta": delta,
 180 |         "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
 181 |     }
 182 |     _cache["data"] = result
 183 |     _cache["ts"] = now
 184 |     return result
 185 | 
```

### File: core/templates/terminal.html (1168 lines)
```
   1 | <!DOCTYPE html>
   2 | <html lang="en">
   3 | <head>
   4 | <meta charset="UTF-8">
   5 | <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
   6 | <title>Protocol Pulse Terminal — Bitcoin Intelligence</title>
   7 | <meta name="description" content="Bloomberg-style Bitcoin intelligence terminal. Live price, mempool, on-chain metrics, signal intelligence. Free tier + Commander $29/mo.">
   8 | <link rel="preconnect" href="https://fonts.googleapis.com">
   9 | <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  10 | <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  11 | <style>
  12 | /* ============================================================
  13 |    PP TERMINAL — BLOOMBERG AESTHETIC — SESSION 1
  14 |    ============================================================ */
  15 | :root {
  16 |   --bg-base:    #080810;
  17 |   --bg-panel:   #0D0D1A;
  18 |   --bg-header:  #050508;
  19 |   --border:     #1C1C2E;
  20 |   --text-primary: #E2E8F0;
  21 |   --text-label:   #64748B;
  22 |   --text-dim:     #2D3748;
  23 |   --gold:   #F59E0B;
  24 |   --green:  #10B981;
  25 |   --red:    #EF4444;
  26 |   --cyan:   #22D3EE;
  27 |   --amber:  #FB923C;
  28 |   --phosphor: #00FF41;
  29 |   --font: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
  30 | }
  31 | *{box-sizing:border-box;margin:0;padding:0;}
  32 | html,body{background:var(--bg-base);color:var(--text-primary);font-family:var(--font);font-size:13px;overflow-x:hidden;}
  33 | a{color:inherit;text-decoration:none;}
  34 | button{font-family:var(--font);cursor:pointer;}
  35 | 
  36 | /* ── Status bar ──────────────────────────────────────────── */
  37 | #statusbar{
  38 |   position:fixed;top:0;left:0;right:0;z-index:100;
  39 |   height:36px;background:var(--bg-header);
  40 |   border-bottom:1px solid rgba(34,211,238,.2);
  41 |   display:flex;align-items:center;justify-content:space-between;
  42 |   padding:0 16px;
  43 | }
  44 | .sb-brand{color:var(--phosphor);font:700 11px/1 var(--font);letter-spacing:.1em;}
  45 | .sb-price{color:var(--gold);font:700 13px/1 var(--font);}
  46 | .sb-right{display:flex;align-items:center;gap:12px;}
  47 | .sb-clock{color:var(--text-label);font:400 11px/1 var(--font);}
  48 | .live-dot{width:6px;height:6px;border-radius:50%;background:var(--cyan);animation:pulse-live 2s ease-in-out infinite;}
  49 | @keyframes pulse-live{0%,100%{opacity:1;}50%{opacity:.3;}}
  50 | @keyframes value-flash{0%{color:#FFF;}100%{color:var(--text-primary);}}
  51 | .value-updated{animation:value-flash .6s ease-out;}
  52 | 
  53 | /* ── Page wrapper ────────────────────────────────────────── */
  54 | #page{padding:52px 12px 32px;max-width:1600px;margin:0 auto;}
  55 | 
  56 | /* ── Grid ────────────────────────────────────────────────── */
  57 | .terminal-grid{display:grid;gap:8px;grid-template-columns:repeat(4,1fr);}
  58 | @media(max-width:1439px){.terminal-grid{grid-template-columns:repeat(3,1fr);}}
  59 | @media(max-width:1023px){.terminal-grid{grid-template-columns:repeat(2,1fr);gap:6px;}}
  60 | @media(max-width:767px) {.terminal-grid{grid-template-columns:1fr;}}
  61 | 
  62 | .col-2{grid-column:span 2;}
  63 | .col-full{grid-column:1/-1;}
  64 | @media(max-width:767px){.col-2,.col-full{grid-column:1;}}
  65 | 
  66 | /* ── Panel ───────────────────────────────────────────────── */
  67 | .panel{
  68 |   background:var(--bg-panel);border:1px solid var(--border);
  69 |   border-radius:0;overflow:hidden;position:relative;
  70 | }
  71 | .panel-hdr{
  72 |   height:28px;border-bottom:1px solid var(--border);
  73 |   display:flex;align-items:center;justify-content:space-between;
  74 |   padding:0 12px;background:rgba(0,0,0,.4);flex-shrink:0;
  75 | }
  76 | .panel-title{font:700 10px/1 var(--font);color:var(--text-label);letter-spacing:.12em;text-transform:uppercase;}
  77 | .panel-ts{font:400 9px/1 var(--font);color:var(--text-dim);}
  78 | .panel-live{display:flex;align-items:center;gap:5px;}
  79 | .panel-live-label{font:400 9px/1 var(--font);color:var(--cyan);}
  80 | .panel-body{padding:12px;}
  81 | 
  82 | /* ── Data rows ───────────────────────────────────────────── */
  83 | .data-row{display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(28,28,46,.6);}
  84 | .data-row:last-child{border-bottom:none;}
  85 | .data-label{font:400 9px/1 var(--font);color:var(--text-label);letter-spacing:.08em;text-transform:uppercase;}
  86 | .data-val{font:600 13px/1 var(--font);color:var(--text-primary);}
  87 | .data-val.gold{color:var(--gold);}
  88 | .data-val.green{color:var(--green);}
  89 | .data-val.red{color:var(--red);}
  90 | .data-delta{font:400 10px/1 var(--font);margin-left:6px;}
  91 | .data-delta.up{color:var(--green);}
  92 | .data-delta.dn{color:var(--red);}
  93 | .data-sep{border:none;border-top:1px solid var(--border);margin:8px 0;}
  94 | 
  95 | /* ── Hero price ──────────────────────────────────────────── */
  96 | .hero-price{font:700 34px/1 var(--font);color:var(--gold);padding:10px 0 8px;}
  97 | @media(max-width:767px){.hero-price{font-size:26px;}}
  98 | 
  99 | /* ── Bar gauge (F&G) ─────────────────────────────────────── */
 100 | .fg-bar-wrap{margin:10px 0 6px;position:relative;height:16px;background:var(--bg-base);border:1px solid var(--border);}
 101 | .fg-bar-fill{height:100%;background:linear-gradient(to right,#EF4444,#FB923C,#F59E0B,#10B981);opacity:.7;}
 102 | .fg-bar-pointer{position:absolute;top:-3px;width:2px;height:22px;background:var(--text-primary);}
 103 | .fg-labels{display:flex;justify-content:space-between;font:400 8px/1 var(--font);color:var(--text-dim);margin-top:3px;}
 104 | 
 105 | /* ── Sparkline ───────────────────────────────────────────── */
 106 | .sparkline{display:block;margin-top:8px;}
 107 | 
 108 | /* ── Locked panels ───────────────────────────────────────── */
 109 | .panel-locked{border:1px solid rgba(245,158,11,.25);}
 110 | .panel-locked .panel-content{filter:blur(4px);user-select:none;pointer-events:none;opacity:.4;transition:filter .3s ease,opacity .3s ease;}
 111 | .panel-locked .lock-overlay{
 112 |   position:absolute;inset:0;display:flex;flex-direction:column;
 113 |   align-items:center;justify-content:center;
 114 |   background:rgba(8,8,16,.75);backdrop-filter:blur(2px);gap:8px;
 115 |   transition:opacity .3s ease;
 116 | }
 117 | .lock-icon{font-size:18px;color:var(--gold);}
 118 | .lock-tier{font:700 10px/1 var(--font);color:var(--gold);letter-spacing:.15em;}
 119 | .lock-cta{font:400 9px/1 var(--font);color:#94A3B8;text-align:center;padding:0 12px;}
 120 | .lock-button{
 121 |   margin-top:4px;padding:7px 16px;
 122 |   background:transparent;border:1px solid var(--gold);
 123 |   color:var(--gold);font:600 10px/1 var(--font);
 124 |   letter-spacing:.1em;text-transform:uppercase;
 125 |   transition:background .15s,color .15s;
 126 | }
 127 | .lock-button:hover{background:var(--gold);color:#080810;}
 128 | 
 129 | /* Signal panel special lock */
 130 | .panel-signal-lock .lock-overlay{
 131 |   background:rgba(8,8,16,.65);
 132 |   gap:10px;
 133 | }
 134 | .panel-signal-lock .panel-content{filter:blur(3px);opacity:.55;}
 135 | .lock-box{
 136 |   border:1px solid rgba(245,158,11,.5);padding:16px 20px;
 137 |   display:flex;flex-direction:column;align-items:center;gap:8px;
 138 |   font:400 10px/1.5 var(--font);color:#94A3B8;text-align:center;
 139 |   max-width:280px;
 140 | }
 141 | .lock-box-title{font:700 12px/1 var(--font);color:var(--gold);letter-spacing:.1em;}
 142 | 
 143 | /* Preview mode (5s unlock) */
 144 | .panel-locked.preview-mode .panel-content{filter:none!important;opacity:1!important;}
 145 | .panel-locked.preview-mode .lock-overlay{opacity:0!important;pointer-events:none!important;}
 146 | .preview-bar{
 147 |   position:absolute;top:0;left:0;height:2px;
 148 |   background:var(--gold);transition:width 1s linear;
 149 |   z-index:5;pointer-events:none;
 150 | }
 151 | 
 152 | /* ── CTA section ─────────────────────────────────────────── */
 153 | #cta-section{
 154 |   border:1px solid rgba(245,158,11,.4);background:#0D0D1A;
 155 |   padding:20px;margin:8px 0;
 156 | }
 157 | .cta-inner{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;}
 158 | .cta-left h2{font:700 14px/1 var(--font);color:var(--gold);letter-spacing:.1em;margin-bottom:10px;}
 159 | .cta-features{list-style:none;display:flex;flex-direction:column;gap:6px;}
 160 | .cta-features li{font:400 10px/1 var(--font);color:var(--text-primary);}
 161 | .cta-features li::before{content:"✓  ";color:var(--green);}
 162 | .cta-price{font:700 22px/1 var(--font);color:var(--gold);}
 163 | .cta-price-sub{font:400 9px/1 var(--font);color:var(--text-label);}
 164 | .cta-buttons{display:flex;flex-direction:column;gap:8px;margin-top:12px;}
 165 | .btn-commander{
 166 |   padding:12px 24px;background:var(--gold);border:none;
 167 |   color:#080810;font:700 11px/1 var(--font);letter-spacing:.1em;
 168 |   text-transform:uppercase;cursor:pointer;
 169 |   transition:opacity .15s;
 170 | }
 171 | .btn-commander:hover{opacity:.85;}
 172 | .btn-preview{
 173 |   padding:10px 24px;background:transparent;
 174 |   border:1px solid var(--gold);color:var(--gold);
 175 |   font:600 10px/1 var(--font);letter-spacing:.1em;text-transform:uppercase;
 176 |   transition:background .15s,color .15s;
 177 | }
 178 | .btn-preview:hover{background:rgba(245,158,11,.1);}
 179 | 
 180 | /* Re-engagement banner */
 181 | #re-engage-banner{
 182 |   display:none;position:fixed;top:36px;left:0;right:0;z-index:99;
 183 |   background:rgba(13,13,26,.97);border-bottom:1px solid var(--gold);
 184 |   padding:10px 16px;text-align:center;
 185 |   font:600 11px/1 var(--font);color:var(--gold);
 186 | }
 187 | #re-engage-banner a{
 188 |   margin-left:16px;padding:6px 16px;
 189 |   background:var(--gold);color:#080810;
 190 |   font:700 11px/1 var(--font);
 191 |   letter-spacing:.08em;
 192 | }
 193 | #re-engage-close{
 194 |   position:absolute;right:12px;top:50%;transform:translateY(-50%);
 195 |   cursor:pointer;color:var(--text-label);background:none;border:none;
 196 |   font:400 14px/1 var(--font);
 197 | }
 198 | 
 199 | /* ── Activated banner ────────────────────────────────────── */
 200 | #activated-banner{
 201 |   background:rgba(16,185,129,.1);border:1px solid var(--green);
 202 |   padding:14px 16px;margin-bottom:8px;
 203 |   font:400 11px/1.5 var(--font);color:var(--text-primary);
 204 | }
 205 | .activated-title{font:700 12px/1 var(--font);color:var(--green);margin-bottom:6px;}
 206 | .api-key-display{
 207 |   background:var(--bg-base);border:1px solid var(--border);
 208 |   padding:8px 12px;margin-top:8px;color:var(--phosphor);
 209 |   font:400 12px/1 var(--font);display:flex;align-items:center;
 210 |   justify-content:space-between;gap:12px;word-break:break-all;
 211 | }
 212 | .copy-btn{
 213 |   padding:5px 10px;background:transparent;border:1px solid var(--cyan);
 214 |   color:var(--cyan);font:600 9px/1 var(--font);letter-spacing:.08em;
 215 |   white-space:nowrap;text-transform:uppercase;
 216 | }
 217 | .copy-btn:hover{background:var(--cyan);color:#080810;}
 218 | 
 219 | /* ── Section label ───────────────────────────────────────── */
 220 | .section-label{
 221 |   font:700 9px/1 var(--font);color:var(--text-dim);
 222 |   letter-spacing:.2em;text-transform:uppercase;
 223 |   padding:14px 0 6px;
 224 | }
 225 | 
 226 | /* ── Article feed ────────────────────────────────────────── */
 227 | .article-row{
 228 |   display:flex;align-items:center;gap:10px;
 229 |   padding:8px 0;border-bottom:1px solid var(--border);
 230 |   cursor:pointer;transition:background .1s;
 231 | }
 232 | .article-row:hover{background:rgba(255,255,255,.02);}
 233 | .article-row:last-child{border-bottom:none;}
 234 | .article-time{font:400 9px/1 var(--font);color:var(--text-dim);min-width:42px;}
 235 | .article-title{font:400 11px/1.4 var(--font);color:var(--text-primary);flex:1;}
 236 | .article-arrow{color:var(--text-dim);font-size:12px;flex-shrink:0;}
 237 | .article-all{
 238 |   display:block;text-align:right;padding-top:8px;
 239 |   font:400 9px/1 var(--font);color:var(--cyan);
 240 |   letter-spacing:.06em;text-transform:uppercase;
 241 | }
 242 | 
 243 | /* ── Signal score display ────────────────────────────────── */
 244 | .signal-score-hero{
 245 |   display:flex;align-items:center;gap:16px;padding:14px 0 10px;
 246 | }
 247 | .signal-num{font:700 42px/1 var(--font);color:var(--text-primary);}
 248 | .signal-class{font:700 14px/1 var(--font);color:var(--green);letter-spacing:.08em;}
 249 | .signal-delta{font:400 10px/1 var(--font);}
 250 | 
 251 | /* Signal bar */
 252 | .signal-bar-wrap{height:4px;background:var(--bg-base);border:1px solid var(--border);margin:8px 0;}
 253 | .signal-bar-fill{height:100%;transition:width .5s ease;}
 254 | 
 255 | /* Component rows */
 256 | .component-row{display:flex;align-items:center;gap:8px;padding:5px 0;}
 257 | .comp-label{font:400 9px/1 var(--font);color:var(--text-label);width:140px;flex-shrink:0;text-transform:uppercase;}
 258 | .comp-score{font:600 11px/1 var(--font);color:var(--text-primary);width:32px;text-align:right;flex-shrink:0;}
 259 | .comp-bar{flex:1;height:4px;background:var(--border);}
 260 | .comp-bar-fill{height:100%;}
 261 | 
 262 | /* ── Alert feed ──────────────────────────────────────────── */
 263 | .alert-row{
 264 |   display:flex;gap:8px;padding:7px 0;border-bottom:1px solid var(--border);align-items:flex-start;
 265 | }
 266 | .alert-row:last-child{border-bottom:none;}
 267 | .alert-time{font:400 9px/1 var(--font);color:var(--text-dim);min-width:42px;flex-shrink:0;padding-top:2px;}
 268 | .alert-text{font:400 11px/1.4 var(--font);color:var(--text-primary);}
 269 | .alert-row.is-alert .alert-text{color:var(--amber);}
 270 | 
 271 | /* ── Topics ──────────────────────────────────────────────── */
 272 | .topic-row{
 273 |   display:flex;align-items:center;gap:10px;
 274 |   padding:6px 0;border-bottom:1px solid var(--border);
 275 | }
 276 | .topic-row:last-child{border-bottom:none;}
 277 | .topic-rank{font:700 10px/1 var(--font);color:var(--text-dim);width:20px;text-align:right;flex-shrink:0;}
 278 | .topic-term{font:600 11px/1 var(--font);color:var(--text-primary);flex:1;}
 279 | .topic-count{font:400 9px/1 var(--font);color:var(--text-dim);}
 280 | .topic-vel{color:var(--green);margin-right:4px;}
 281 | 
 282 | /* ── LN panel ────────────────────────────────────────────── */
 283 | .ln-capacity{font:700 20px/1 var(--font);color:var(--cyan);padding:8px 0 4px;}
 284 | .ln-cap-unit{font:400 11px/1 var(--font);color:var(--text-label);}
 285 | 
 286 | /* ── Macro ───────────────────────────────────────────────── */
 287 | .macro-ratio-row{
 288 |   display:flex;justify-content:space-between;padding:4px 0;
 289 |   border-top:1px solid var(--border);margin-top:6px;
 290 | }
 291 | 
 292 | /* ── Mobile status bar collapse ──────────────────────────── */
 293 | @media(max-width:767px){
 294 |   .sb-brand{display:none;}
 295 |   #statusbar{justify-content:space-between;}
 296 | }
 297 | 
 298 | /* ── Scrollbar ───────────────────────────────────────────── */
 299 | ::-webkit-scrollbar{width:4px;height:4px;}
 300 | ::-webkit-scrollbar-track{background:var(--bg-base);}
 301 | ::-webkit-scrollbar-thumb{background:var(--border);}
 302 | </style>
 303 | </head>
 304 | <body>
 305 | 
 306 | <!-- ── Fixed status bar ──────────────────────────────────── -->
 307 | <div id="statusbar">
 308 |   <span class="sb-brand">PROTOCOL PULSE TERMINAL</span>
 309 |   <span class="sb-price" id="sb-price">
 310 |     {% if price.price %}
 311 |       BTC ${{ "{:,.2f}".format(price.price) }}
 312 |       <span id="sb-delta" class="{{ 'up' if price.change_24h_pct >= 0 else 'dn' }}" style="font-size:11px;color:{{ '#10B981' if price.change_24h_pct >= 0 else '#EF4444' }}">
 313 |         {{ '▲' if price.change_24h_pct >= 0 else '▼' }}{{ "{:.2f}%".format(price.change_24h_pct | abs) }}
 314 |       </span>
 315 |     {% else %}
 316 |       BTC —
 317 |     {% endif %}
 318 |   </span>
 319 |   <div class="sb-right">
 320 |     <div class="live-dot"></div>
 321 |     <span class="sb-clock" id="sb-clock"></span>
 322 |   </div>
 323 | </div>
 324 | 
 325 | <!-- Re-engagement banner (shown after preview) -->
 326 | <div id="re-engage-banner">
 327 |   You just saw Commander access for 5 seconds. Never lose that again.
 328 |   <a href="/terminal/checkout">→ $29/MO</a>
 329 |   <button id="re-engage-close">✕</button>
 330 | </div>
 331 | 
 332 | <div id="page">
 333 | 
 334 |   <!-- Activated welcome banner -->
 335 |   {% if activated %}
 336 |   <div id="activated-banner">
 337 |     <div class="activated-title">🎯 COMMANDER ACCESS ACTIVATED</div>
 338 |     {% if is_commander %}
 339 |       All panels unlocked. Signal Intelligence live. Welcome to the terminal.
 340 |       {% if api_key %}
 341 |       <div class="api-key-display">
 342 |         <span id="api-key-text">{{ api_key }}</span>
 343 |         <button class="copy-btn" onclick="copyKey()">COPY</button>
 344 |       </div>
 345 |       <div style="margin-top:6px;font-size:9px;color:var(--text-label);">Store this key securely. It grants API access at 10,000 req/hr. Shown here once — find it again at /terminal/account.</div>
 346 |       {% endif %}
 347 |     {% else %}
 348 |       Subscription processing. Refresh in a moment.
 349 |     {% endif %}
 350 |   </div>
 351 |   {% endif %}
 352 | 
 353 |   <!-- ═══════════════════ ROW 1 — MARKET OVERVIEW (FREE) ═══════════════════ -->
 354 |   <div class="section-label">MARKET OVERVIEW</div>
 355 |   <div class="terminal-grid" id="row1">
 356 | 
 357 |     <!-- 1A: BTC Price (2-col) -->
 358 |     <div class="panel col-2" id="panel-price">
 359 |       <div class="panel-hdr">
 360 |         <span class="panel-title">BTC / USD</span>
 361 |         <div class="panel-live"><div class="live-dot"></div><span class="panel-live-label">LIVE</span></div>
 362 |       </div>
 363 |       <div class="panel-body">
 364 |         <div class="hero-price" id="btc-price-hero">
 365 |           {% if price.price %}${{ "{:,.2f}".format(price.price) }}{% else %}—{% endif %}
 366 |         </div>
 367 |         <hr class="data-sep">
 368 |         <div class="data-row">
 369 |           <span class="data-label">24H CHANGE</span>
 370 |           <span>
 371 |             <span class="data-val {% if price.change_24h_usd >= 0 %}green{% else %}red{% endif %}" id="chg-24h-usd">
 372 |               {{ '▲' if price.change_24h_usd >= 0 else '▼' }} ${{ "{:,.0f}".format(price.change_24h_usd | abs) }}
 373 |             </span>
 374 |             <span class="data-delta {% if price.change_24h_pct >= 0 %}up{% else %}dn{% endif %}" id="chg-24h-pct">
 375 |               {{ '▲' if price.change_24h_pct >= 0 else '▼' }} {{ "{:.2f}%".format(price.change_24h_pct | abs) }}
 376 |             </span>
 377 |           </span>
 378 |         </div>
 379 |         <div class="data-row">
 380 |           <span class="data-label">7D CHANGE</span>
 381 |           <span class="data-val {% if price.change_7d_pct >= 0 %}green{% else %}red{% endif %}">
 382 |             {{ '▲' if price.change_7d_pct >= 0 else '▼' }} {{ "{:.2f}%".format(price.change_7d_pct | abs) }}
 383 |           </span>
 384 |         </div>
 385 |         <div class="data-row">
 386 |           <span class="data-label">30D CHANGE</span>
 387 |           <span class="data-val {% if price.change_30d_pct >= 0 %}green{% else %}red{% endif %}">
 388 |             {{ '▲' if price.change_30d_pct >= 0 else '▼' }} {{ "{:.2f}%".format(price.change_30d_pct | abs) }}
 389 |           </span>
 390 |         </div>
 391 |         <hr class="data-sep">
 392 |         <div class="data-row">
 393 |           <span class="data-label">24H HIGH</span>
 394 |           <span class="data-val gold">${{ "{:,.0f}".format(price.high_24h) }}</span>
 395 |           <span class="data-label" style="margin-left:16px;">24H LOW</span>
 396 |           <span class="data-val">${{ "{:,.0f}".format(price.low_24h) }}</span>
 397 |         </div>
 398 |         <div class="data-row">
 399 |           <span class="data-label">MKT CAP</span>
 400 |           <span class="data-val">${{ "{:.2f}T".format(price.market_cap / 1e12) if price.market_cap else "—" }}</span>
 401 |           <span class="data-label" style="margin-left:16px;">DOMINANCE</span>
 402 |           <span class="data-val">{{ price.dominance }}%</span>
 403 |         </div>
 404 |         <svg class="sparkline" id="sparkline-price" width="100%" height="28" viewBox="0 0 300 28" preserveAspectRatio="none">
 405 |           <polyline id="spark-price-line" points="" stroke="#F59E0B" stroke-width="1.5" fill="none"/>
 406 |         </svg>
 407 |       </div>
 408 |     </div>
 409 | 
 410 |     <!-- 1B: Mempool (1-col) -->
 411 |     <div class="panel" id="panel-mempool">
 412 |       <div class="panel-hdr">
 413 |         <span class="panel-title">MEMPOOL</span>
 414 |         <div class="panel-live"><div class="live-dot"></div><span class="panel-live-label">LIVE</span></div>
 415 |       </div>
 416 |       <div class="panel-body">
 417 |         <div class="data-row">
 418 |           <span class="data-label">UNCONFIRMED TXS</span>
 419 |           <span class="data-val" id="mp-count">{{ "{:,}".format(mempool.count) }}</span>
 420 |         </div>
 421 |         <div class="data-row">
 422 |           <span class="data-label">MEMPOOL SIZE</span>
 423 |           <span class="data-val">{{ "{:.1f} MB".format(mempool.vsize / 1e6) if mempool.vsize else "—" }}</span>
 424 |         </div>
 425 |         <hr class="data-sep">
 426 |         <div class="data-label" style="padding:4px 0 6px;">FEE MARKET (sat/vB)</div>
 427 |         <div class="data-row">
 428 |           <span class="data-label">NO PRIORITY</span>
 429 |           <span class="data-val">{{ mempool.fee_no_priority }}</span>
 430 |         </div>
 431 |         <div class="data-row">
 432 |           <span class="data-label">LOW PRIORITY</span>
 433 |           <span class="data-val">{{ mempool.fee_low }}</span>
 434 |         </div>
 435 |         <div class="data-row">
 436 |           <span class="data-label">MED PRIORITY</span>
 437 |           <span class="data-val gold">{{ mempool.fee_medium }}</span>
 438 |         </div>
 439 |         <div class="data-row">
 440 |           <span class="data-label">HIGH PRIORITY</span>
 441 |           <span class="data-val" style="color:var(--amber);">{{ mempool.fee_high }}</span>
 442 |         </div>
 443 |         <hr class="data-sep">
 444 |         <div class="data-row">
 445 |           <span class="data-label">NEXT BLOCK ETA</span>
 446 |           <span class="data-val">~10 min</span>
 447 |         </div>
 448 |         <svg class="sparkline" id="sparkline-mempool" width="100%" height="22" viewBox="0 0 200 22" preserveAspectRatio="none">
 449 |           <polyline id="spark-mempool-line" points="" stroke="#22D3EE" stroke-width="1.5" fill="none"/>
 450 |         </svg>
 451 |       </div>
 452 |     </div>
 453 | 
 454 |     <!-- 1C: Fear & Greed (1-col) -->
 455 |     <div class="panel" id="panel-fg">
 456 |       <div class="panel-hdr">
 457 |         <span class="panel-title">FEAR &amp; GREED INDEX</span>
 458 |         <span class="panel-ts">○ 15M</span>
 459 |       </div>
 460 |       <div class="panel-body">
 461 |         <div class="data-row">
 462 |           <span class="data-label">TODAY</span>
 463 |           <span class="data-val gold">{{ fg.today }} / 100</span>
 464 |         </div>
 465 |         <div class="data-row">
 466 |           <span class="data-label">CLASSIFICATION</span>
 467 |           <span class="data-val" id="fg-class" style="color:{{ '#EF4444' if fg.today < 30 else ('#FB923C' if fg.today < 50 else ('#F59E0B' if fg.today < 70 else '#10B981')) }}">
 468 |             {{ fg.today_class.upper() }}
 469 |           </span>
 470 |         </div>
 471 |         <div class="fg-bar-wrap" style="margin-top:10px;">
 472 |           <div class="fg-bar-fill" style="width:100%;"></div>
 473 |           <div class="fg-bar-pointer" style="left:calc({{ fg.today }}% - 1px);"></div>
 474 |         </div>
 475 |         <div class="fg-labels">
 476 |           <span>FEAR</span><span>50</span><span>GREED</span>
 477 |         </div>
 478 |         <hr class="data-sep">
 479 |         <div class="data-row">
 480 |           <span class="data-label">YESTERDAY</span>
 481 |           <span class="data-val">{{ fg.yesterday }}
 482 |             <span class="data-delta {% if fg.today - fg.yesterday >= 0 %}up{% else %}dn{% endif %}">
 483 |               {{ '▲' if fg.today - fg.yesterday >= 0 else '▼' }} {{ (fg.today - fg.yesterday) | abs }}
 484 |             </span>
 485 |           </span>
 486 |         </div>
 487 |         <div class="data-row">
 488 |           <span class="data-label">LAST WEEK</span>
 489 |           <span class="data-val">{{ fg.last_week }}
 490 |             <span class="data-delta {% if fg.today - fg.last_week >= 0 %}up{% else %}dn{% endif %}">
 491 |               {{ '▲' if fg.today - fg.last_week >= 0 else '▼' }} {{ (fg.today - fg.last_week) | abs }}
 492 |             </span>
 493 |           </span>
 494 |         </div>
 495 |         <div class="data-row">
 496 |           <span class="data-label">LAST MONTH</span>
 497 |           <span class="data-val">{{ fg.last_month }}
 498 |             <span class="data-delta {% if fg.today - fg.last_month >= 0 %}up{% else %}dn{% endif %}">
 499 |               {{ '▲' if fg.today - fg.last_month >= 0 else '▼' }} {{ (fg.today - fg.last_month) | abs }}
 500 |             </span>
 501 |           </span>
 502 |         </div>
 503 |       </div>
 504 |     </div>
 505 | 
 506 |   </div><!-- /row1 -->
 507 | 
 508 |   <!-- ═══════════════════ ROW 2 — ON-CHAIN METRICS (LOCKED) ═══════════════════ -->
 509 |   <div class="section-label">ON-CHAIN METRICS</div>
 510 |   <div class="terminal-grid" id="row2">
 511 | 
 512 |     <!-- 2A: Hashrate & Difficulty -->
 513 |     <div class="panel {% if not is_commander %}panel-locked{% endif %}" id="panel-hashrate">
 514 |       <div class="panel-hdr">
 515 |         <span class="panel-title">NETWORK SECURITY</span>
 516 |         <span class="panel-ts">{% if is_commander %}<span class="panel-live-label" style="color:var(--gold);">COMMANDER</span>{% else %}🔒 COMMANDER{% endif %}</span>
 517 |       </div>
 518 |       <div class="panel-content panel-body">
 519 |         <div class="data-row">
 520 |           <span class="data-label">HASHRATE</span>
 521 |           <span class="data-val gold">{{ onchain.hashrate_ehs }} EH/s</span>
 522 |         </div>
 523 |         <div class="data-row">
 524 |           <span class="data-label">DIFFICULTY</span>
 525 |           <span class="data-val">{{ onchain.difficulty_t }} T</span>
 526 |         </div>
 527 |         <hr class="data-sep">
 528 |         <div class="data-row">
 529 |           <span class="data-label">NEXT ADJUSTMENT</span>
 530 |           <span class="data-val {% if onchain.next_adj_pct >= 0 %}green{% else %}red{% endif %}">
 531 |             {{ '+' if onchain.next_adj_pct >= 0 else '' }}{{ "{:.2f}%".format(onchain.next_adj_pct) }}
 532 |           </span>
 533 |         </div>
 534 |         <div class="data-row">
 535 |           <span class="data-label">REMAIN</span>
 536 |           <span class="data-val">{{ onchain.remain_blocks }} blocks</span>
 537 |         </div>
 538 |         <div class="data-row">
 539 |           <span class="data-label">BLOCK HEIGHT</span>
 540 |           <span class="data-val">{{ "{:,}".format(onchain.block_height) if onchain.block_height else "—" }}</span>
 541 |         </div>
 542 |       </div>
 543 |       {% if not is_commander %}
 544 |       <div class="lock-overlay">
 545 |         <span class="lock-icon">🔒</span>
 546 |         <span class="lock-tier">COMMANDER</span>
 547 |         <span class="lock-cta">Network security data</span>
 548 |         <button class="lock-button" onclick="location.href='/terminal/checkout'">UNLOCK $29/MO</button>
 549 |       </div>
 550 |       {% endif %}
 551 |     </div>
 552 | 
 553 |     <!-- 2B: MVRV Z-Score -->
 554 |     <div class="panel {% if not is_commander %}panel-locked{% endif %}" id="panel-mvrv">
 555 |       <div class="panel-hdr">
 556 |         <span class="panel-title">VALUATION MODEL</span>
 557 |         <span class="panel-ts">{% if not is_commander %}🔒 COMMANDER{% endif %}</span>
 558 |       </div>
 559 |       <div class="panel-content panel-body">
 560 |         <div class="data-row">
 561 |           <span class="data-label">MVRV Z-SCORE</span>
 562 |           <span class="data-val gold">{{ onchain.mvrv }}</span>
 563 |         </div>
 564 |         <div class="data-row">
 565 |           <span class="data-label">SIGNAL</span>
 566 |           <span class="data-val green">ACCUMULATE</span>
 567 |         </div>
 568 |         <hr class="data-sep">
 569 |         <div class="data-row">
 570 |           <span class="data-label">REALIZED PRICE</span>
 571 |           <span class="data-val">${{ "{:,}".format(onchain.realized_price) }}</span>
 572 |         </div>
 573 |         <div class="data-row">
 574 |           <span class="data-label">CYCLE ZONE</span>
 575 |           <span class="data-val" style="color:var(--cyan);">MID-BULL</span>
 576 |         </div>
 577 |       </div>
 578 |       {% if not is_commander %}
 579 |       <div class="lock-overlay">
 580 |         <span class="lock-icon">🔒</span>
 581 |         <span class="lock-tier">COMMANDER</span>
 582 |         <span class="lock-cta">See where we are in the cycle</span>
 583 |         <button class="lock-button" onclick="location.href='/terminal/checkout'">$29/MO</button>
 584 |       </div>
 585 |       {% endif %}
 586 |     </div>
 587 | 
 588 |     <!-- 2C: Stock to Flow -->
 589 |     <div class="panel {% if not is_commander %}panel-locked{% endif %}" id="panel-s2f">
 590 |       <div class="panel-hdr">
 591 |         <span class="panel-title">STOCK-TO-FLOW</span>
 592 |         <span class="panel-ts">{% if not is_commander %}🔒 COMMANDER{% endif %}</span>
 593 |       </div>
 594 |       <div class="panel-content panel-body">
 595 |         <div class="data-row">
 596 |           <span class="data-label">S2F RATIO</span>
 597 |           <span class="data-val gold">{{ onchain.s2f_ratio }}</span>
 598 |         </div>
 599 |         <div class="data-row">
 600 |           <span class="data-label">MODEL PRICE</span>
 601 |           <span class="data-val">${{ "{:,}".format(onchain.s2f_model_price) }}</span>
 602 |         </div>
 603 |         <hr class="data-sep">
 604 |         <div class="data-row">
 605 |           <span class="data-label">NEXT HALVING</span>
 606 |           <span class="data-val">~{{ ((840000 - onchain.block_height) // 144) if onchain.block_height else "—" }} days</span>
 607 |         </div>
 608 |         <div class="data-row">
 609 |           <span class="data-label">HALVING EPOCH</span>
 610 |           <span class="data-val" style="color:var(--amber);">5th</span>
 611 |         </div>
 612 |       </div>
 613 |       {% if not is_commander %}
 614 |       <div class="lock-overlay">
 615 |         <span class="lock-icon">🔒</span>
 616 |         <span class="lock-tier">COMMANDER</span>
 617 |         <span class="lock-cta">S2F model + halving countdown</span>
 618 |         <button class="lock-button" onclick="location.href='/terminal/checkout'">$29/MO</button>
 619 |       </div>
 620 |       {% endif %}
 621 |     </div>
 622 | 
 623 |     <!-- 2D: Exchange Flows -->
 624 |     <div class="panel {% if not is_commander %}panel-locked{% endif %}" id="panel-flows">
 625 |       <div class="panel-hdr">
 626 |         <span class="panel-title">EXCHANGE FLOWS</span>
 627 |         <span class="panel-ts">{% if not is_commander %}🔒 COMMANDER{% endif %}</span>
 628 |       </div>
 629 |       <div class="panel-content panel-body">
 630 |         <div class="data-row">
 631 |           <span class="data-label">INFLOW</span>
 632 |           <span class="data-val red">{{ "{:,}".format(onchain.exchange_inflow) }} BTC</span>
 633 |         </div>
 634 |         <div class="data-row">
 635 |           <span class="data-label">OUTFLOW</span>
 636 |           <span class="data-val green">{{ "{:,}".format(onchain.exchange_outflow) }} BTC</span>
 637 |         </div>
 638 |         <div class="data-row">
 639 |           <span class="data-label">NET FLOW</span>
 640 |           <span class="data-val {% if onchain.exchange_net < 0 %}green{% else %}red{% endif %}">
 641 |             {{ '+' if onchain.exchange_net >= 0 else '' }}{{ "{:,}".format(onchain.exchange_net) }} BTC
 642 |           </span>
 643 |         </div>
 644 |         <hr class="data-sep">
 645 |         <div class="data-row">
 646 |           <span class="data-label">SIGNAL</span>
 647 |           <span class="data-val green">NET OUTFLOW — BULLISH</span>
 648 |         </div>
 649 |       </div>
 650 |       {% if not is_commander %}
 651 |       <div class="lock-overlay">
 652 |         <span class="lock-icon">🔒</span>
 653 |         <span class="lock-tier">COMMANDER</span>
 654 |         <span class="lock-cta">Follow smart money on-chain</span>
 655 |         <button class="lock-button" onclick="location.href='/terminal/checkout'">$29/MO</button>
 656 |       </div>
 657 |       {% endif %}
 658 |     </div>
 659 | 
 660 |   </div><!-- /row2 -->
 661 | 
 662 |   <!-- ═══════════════════ ROW 3 — PP SIGNAL INTELLIGENCE (LOCKED) ════════════ -->
 663 |   <div class="section-label">SIGNAL INTELLIGENCE</div>
 664 |   <div class="terminal-grid" id="row3">
 665 | 
 666 |     <!-- 3A: Signal Score (2-col, special lock) -->
 667 |     <div class="panel col-2 {% if not is_commander %}panel-locked panel-signal-lock{% endif %}" id="panel-signal">
 668 |       <div class="panel-hdr">
 669 |         <span class="panel-title">PP SIGNAL INTELLIGENCE</span>
 670 |         <div class="panel-live">
 671 |           {% if is_commander %}<div class="live-dot"></div><span class="panel-live-label">LIVE</span>{% else %}<span class="panel-ts">🔒 COMMANDER EXCLUSIVE</span>{% endif %}
 672 |         </div>
 673 |       </div>
 674 |       <div class="panel-content panel-body">
 675 |         <div class="signal-score-hero">
 676 |           <div class="signal-num" id="signal-score-num">{{ signal.score }}</div>
 677 |           <div>
 678 |             <div class="signal-class" id="signal-class" style="color:{{ '#10B981' if signal.score >= 65 else ('#64748B' if signal.score >= 45 else '#EF4444') }}">
 679 |               {{ signal.classification }}
 680 |             </div>
 681 |             <div class="signal-delta data-delta {% if signal.delta >= 0 %}up{% else %}dn{% endif %}" style="margin-top:4px;">
 682 |               {{ '▲ +' if signal.delta >= 0 else '▼ ' }}{{ signal.delta | abs }} FROM YESTERDAY
 683 |             </div>
 684 |           </div>
 685 |         </div>
 686 |         <div class="signal-bar-wrap">
 687 |           <div class="signal-bar-fill" id="signal-bar" style="width:{{ signal.score }}%;background:{{ '#10B981' if signal.score >= 65 else ('#F59E0B' if signal.score >= 45 else '#EF4444') }};"></div>
 688 |         </div>
 689 |         <hr class="data-sep">
 690 |         <div class="data-label" style="padding:6px 0 8px;">COMPONENT BREAKDOWN</div>
 691 |         {% set comps = [
 692 |           ("ARTICLE SENTIMENT", "article_sentiment"),
 693 |           ("PRICE MOMENTUM",    "price_momentum"),
 694 |           ("SOCIAL VOLUME",     "social_volume"),
 695 |           ("ON-CHAIN HEALTH",   "onchain_health"),
 696 |           ("FEAR/GREED CONTRIB","fear_greed_contrib"),
 697 |         ] %}
 698 |         {% for label, key in comps %}
 699 |         {% set val = signal.components[key] | int %}
 700 |         <div class="component-row">
 701 |           <span class="comp-label">{{ label }}</span>
 702 |           <span class="comp-score">{{ val }}</span>
 703 |           <div class="comp-bar">
 704 |             <div class="comp-bar-fill" style="width:{{ val }}%;background:{{ '#10B981' if val >= 65 else ('#F59E0B' if val >= 45 else '#EF4444') }};"></div>
 705 |           </div>
 706 |         </div>
 707 |         {% endfor %}
 708 |         <div class="panel-ts" style="text-align:right;margin-top:8px;">Updated {{ signal.ts }}</div>
 709 |       </div>
 710 |       {% if not is_commander %}
 711 |       <div class="lock-overlay">
 712 |         <div class="lock-box">
 713 |           <div class="lock-box-title">🔒  PP SIGNAL INTELLIGENCE</div>
 714 |           <div>The only composite Bitcoin signal<br>built from 80 live sources.<br>Updated every 2 minutes.</div>
 715 |           <button class="lock-button" style="margin-top:8px;padding:10px 24px;" onclick="location.href='/terminal/checkout'">UNLOCK FOR $29/MO</button>
 716 |         </div>
 717 |       </div>
 718 |       {% endif %}
 719 |     </div>
 720 | 
 721 |     <!-- 3B: Trending Topics -->
 722 |     <div class="panel {% if not is_commander %}panel-locked{% endif %}" id="panel-topics">
 723 |       <div class="panel-hdr">
 724 |         <span class="panel-title">TRENDING INTEL (LAST 2H)</span>
 725 |         <span class="panel-ts">{% if not is_commander %}🔒 COMMANDER{% endif %}</span>
 726 |       </div>
 727 |       <div class="panel-content panel-body">
 728 |         {% for t in topics.topics[:6] %}
 729 |         <div class="topic-row">
 730 |           <span class="topic-rank">0{{ loop.index }}</span>
 731 |           <span class="topic-term">{{ t.term }}</span>
 732 |           <span class="topic-count"><span class="topic-vel">{{ '↑↑↑' if loop.index == 1 else ('↑↑' if loop.index <= 3 else '↑') }}</span>{{ t.count }} art.</span>
 733 |         </div>
 734 |         {% else %}
 735 |         {% for dummy in [("BITCOIN ETF", 14), ("HALVING", 11), ("BLACKROCK", 9), ("LIGHTNING", 7), ("MEMPOOL", 5)] %}
 736 |         <div class="topic-row">
 737 |           <span class="topic-rank">{{ loop.index }}</span>
 738 |           <span class="topic-term">{{ dummy[0] }}</span>
 739 |           <span class="topic-count"><span class="topic-vel">{{ '↑↑↑' if loop.index == 1 else '↑↑' }}</span>{{ dummy[1] }} art.</span>
 740 |         </div>
 741 |         {% endfor %}
 742 |         {% endfor %}
 743 |         <hr class="data-sep">
 744 |         <div class="data-row">
 745 |           <span class="data-label">TOTAL ARTICLES TODAY</span>
 746 |           <span class="data-val">{{ topics.total_articles }}</span>
 747 |         </div>
 748 |         <div class="data-row">
 749 |           <span class="data-label">SOURCES MONITORED</span>
 750 |           <span class="data-val gold">80</span>
 751 |         </div>
 752 |       </div>
 753 |       {% if not is_commander %}
 754 |       <div class="lock-overlay">
 755 |         <span class="lock-icon">🔒</span>
 756 |         <span class="lock-tier">COMMANDER</span>
 757 |         <span class="lock-cta">80 sources. Ranked by velocity.</span>
 758 |         <button class="lock-button" onclick="location.href='/terminal/checkout'">$29/MO</button>
 759 |       </div>
 760 |       {% endif %}
 761 |     </div>
 762 | 
 763 |     <!-- 3C: Early Warning Feed -->
 764 |     <div class="panel {% if not is_commander %}panel-locked{% endif %}" id="panel-alerts">
 765 |       <div class="panel-hdr">
 766 |         <span class="panel-title">EARLY WARNINGS</span>
 767 |         <span class="panel-ts">{% if not is_commander %}🔒 COMMANDER{% endif %}</span>
 768 |       </div>
 769 |       <div class="panel-content panel-body">
 770 |         {% for alert in alerts[:7] %}
 771 |         <div class="alert-row {{ 'is-alert' if alert.is_alert else '' }}">
 772 |           <span class="alert-time">{{ alert.time }}</span>
 773 |           <a href="{{ alert.url }}" class="alert-text">{{ alert.title[:70] }}{% if alert.title | length > 70 %}...{% endif %}</a>
 774 |         </div>
 775 |         {% else %}
 776 |         <div style="color:var(--text-dim);font-size:11px;padding:8px 0;">No alerts at this time.</div>
 777 |         {% endfor %}
 778 |       </div>
 779 |       {% if not is_commander %}
 780 |       <div class="lock-overlay">
 781 |         <span class="lock-icon">🔒</span>
 782 |         <span class="lock-tier">COMMANDER</span>
 783 |         <span class="lock-cta">Know before Twitter does</span>
 784 |         <button class="lock-button" onclick="location.href='/terminal/checkout'">$29/MO</button>
 785 |       </div>
 786 |       {% endif %}
 787 |     </div>
 788 | 
 789 |   </div><!-- /row3 -->
 790 | 
 791 |   <!-- ═══════════════════ ROW 4 — LATEST INTEL (FREE) ══════════════════════ -->
 792 |   <div class="section-label">LATEST INTEL</div>
 793 |   <div class="terminal-grid">
 794 |     <div class="panel col-full" id="panel-latest">
 795 |       <div class="panel-hdr">
 796 |         <span class="panel-title">LATEST INTEL</span>
 797 |         <div class="panel-live"><div class="live-dot"></div><span class="panel-live-label">LIVE</span></div>
 798 |       </div>
 799 |       <div class="panel-body">
 800 |         <div id="article-feed">
 801 |           {% for art in latest.articles %}
 802 |           <a href="{{ art.slug }}" class="article-row">
 803 |             <span class="article-time">{{ art.time }}</span>
 804 |             <span class="article-title">{{ art.title }}</span>
 805 |             <span class="article-arrow">→</span>
 806 |           </a>
 807 |           {% else %}
 808 |           <div style="color:var(--text-dim);font-size:11px;padding:8px 0;">Loading latest intelligence...</div>
 809 |           {% endfor %}
 810 |         </div>
 811 |         <a href="/articles" class="article-all">→ VIEW ALL {{ "{:,}".format(latest.total) if latest.total else "" }} ARTICLES</a>
 812 |       </div>
 813 |     </div>
 814 |   </div>
 815 | 
 816 |   <!-- ═══════════════════ CTA SECTION ══════════════════════════════════════ -->
 817 |   {% if not is_commander %}
 818 |   <div id="cta-section">
 819 |     <div class="cta-inner">
 820 |       <div class="cta-left">
 821 |         <h2>COMMANDER ACCESS</h2>
 822 |         <ul class="cta-features">
 823 |           <li>PP Signal Intelligence — composite score from 80 sources</li>
 824 |           <li>Full on-chain metrics (MVRV, S2F, exchange flows)</li>
 825 |           <li>Trending topics ranked by velocity</li>
 826 |           <li>Early warning alert feed</li>
 827 |           <li>API access — 10,000 req/hr</li>
 828 |           <li>No rate limits on this terminal</li>
 829 |         </ul>
 830 |       </div>
 831 |       <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
 832 |         <div class="cta-price">$29<span class="cta-price-sub">/MO</span></div>
 833 |         <div class="cta-buttons">
 834 |           <button class="btn-commander" onclick="location.href='/terminal/checkout'">ACTIVATE COMMANDER → $29/MO</button>
 835 |           <button class="btn-preview" id="btn-preview" onclick="startPreview()">SEE WHAT YOU'RE MISSING</button>
 836 |         </div>
 837 |       </div>
 838 |     </div>
 839 |   </div>
 840 |   {% endif %}
 841 | 
 842 |   <!-- ═══════════════════ ROW 5 — MACRO + LIGHTNING ════════════════════════ -->
 843 |   <div class="section-label">MACRO &amp; NETWORK</div>
 844 |   <div class="terminal-grid" id="row5">
 845 | 
 846 |     <!-- 5A: Macro (FREE) -->
 847 |     <div class="panel col-2" id="panel-macro">
 848 |       <div class="panel-hdr">
 849 |         <span class="panel-title">MACRO CONTEXT</span>
 850 |         <span class="panel-ts">○ 1H</span>
 851 |       </div>
 852 |       <div class="panel-body">
 853 |         <div class="data-row">
 854 |           <span class="data-label">DXY (USD INDEX)</span>
 855 |           <span class="data-val">{{ macro.DXY.price if macro.DXY else "—" }}</span>
 856 |           {% if macro.DXY and macro.DXY.change_pct %}
 857 |           <span class="data-delta {% if macro.DXY.change_pct >= 0 %}up{% else %}dn{% endif %}">
 858 |             {{ '▲' if macro.DXY.change_pct >= 0 else '▼' }} {{ "{:.2f}%".format(macro.DXY.change_pct | abs) }}
 859 |           </span>
 860 |           {% endif %}
 861 |         </div>
 862 |         <div class="data-row">
 863 |           <span class="data-label">GOLD</span>
 864 |           <span class="data-val">${{ "{:,.0f}".format(macro.GOLD.price) if macro.GOLD and macro.GOLD.price else "—" }}</span>
 865 |           {% if macro.GOLD and macro.GOLD.change_pct %}
 866 |           <span class="data-delta {% if macro.GOLD.change_pct >= 0 %}up{% else %}dn{% endif %}">
 867 |             {{ '▲' if macro.GOLD.change_pct >= 0 else '▼' }} {{ "{:.2f}%".format(macro.GOLD.change_pct | abs) }}
 868 |           </span>
 869 |           {% endif %}
 870 |         </div>
 871 |         <div class="data-row">
 872 |           <span class="data-label">S&amp;P 500</span>
 873 |           <span class="data-val">{{ "{:,.0f}".format(macro.SP500.price) if macro.SP500 and macro.SP500.price else "—" }}</span>
 874 |           {% if macro.SP500 and macro.SP500.change_pct %}
 875 |           <span class="data-delta {% if macro.SP500.change_pct >= 0 %}up{% else %}dn{% endif %}">
 876 |             {{ '▲' if macro.SP500.change_pct >= 0 else '▼' }} {{ "{:.2f}%".format(macro.SP500.change_pct | abs) }}
 877 |           </span>
 878 |           {% endif %}
 879 |         </div>
 880 |         <div class="macro-ratio-row">
 881 |           <span>
 882 |             <span class="data-label">BTC/GOLD RATIO</span>
 883 |             <span class="data-val" style="margin-left:8px;">{{ macro.BTC_GOLD_RATIO if macro.BTC_GOLD_RATIO else "—" }}</span>
 884 |           </span>
 885 |           <span>
 886 |             <span class="data-label">BTC/SP500 RATIO</span>
 887 |             <span class="data-val" style="margin-left:8px;">{{ macro.BTC_SP500_RATIO if macro.BTC_SP500_RATIO else "—" }}</span>
 888 |           </span>
 889 |         </div>
 890 |       </div>
 891 |     </div>
 892 | 
 893 |     <!-- 5B: Lightning Network (LOCKED) -->
 894 |     <div class="panel col-2 {% if not is_commander %}panel-locked{% endif %}" id="panel-lightning">
 895 |       <div class="panel-hdr">
 896 |         <span class="panel-title">LIGHTNING NETWORK</span>
 897 |         <span class="panel-ts">{% if not is_commander %}🔒 COMMANDER{% endif %}</span>
 898 |       </div>
 899 |       <div class="panel-content panel-body">
 900 |         <div class="data-row">
 901 |           <span class="data-label">NODES</span>
 902 |           <span class="data-val gold">{{ "{:,}".format(lightning.node_count) if lightning.node_count else "—" }}</span>
 903 |         </div>
 904 |         <div class="data-row">
 905 |           <span class="data-label">CHANNELS</span>
 906 |           <span class="data-val">{{ "{:,}".format(lightning.channel_count) if lightning.channel_count else "—" }}</span>
 907 |         </div>
 908 |         <hr class="data-sep">
 909 |         <div>
 910 |           <div class="data-label" style="padding:4px 0 2px;">TOTAL CAPACITY</div>
 911 |           <div class="ln-capacity">{{ "{:.1f}".format(lightning.total_capacity / 1e8) if lightning.total_capacity else "—" }} <span class="ln-cap-unit">BTC</span></div>
 912 |         </div>
 913 |         <div class="data-row" style="margin-top:6px;">
 914 |           <span class="data-label">AVG CHANNEL SIZE</span>
 915 |           <span class="data-val">{{ "{:,}".format(lightning.avg_capacity) if lightning.avg_capacity else "—" }} sats</span>
 916 |         </div>
 917 |         <div class="data-row">
 918 |           <span class="data-label">AVG FEE RATE</span>
 919 |           <span class="data-val">{{ lightning.avg_fee_rate if lightning.avg_fee_rate else "—" }} ppm</span>
 920 |         </div>
 921 |       </div>
 922 |       {% if not is_commander %}
 923 |       <div class="lock-overlay">
 924 |         <span class="lock-icon">🔒</span>
 925 |         <span class="lock-tier">COMMANDER</span>
 926 |         <span class="lock-cta">LN network health metrics</span>
 927 |         <button class="lock-button" onclick="location.href='/terminal/checkout'">$29/MO</button>
 928 |       </div>
 929 |       {% endif %}
 930 |     </div>
 931 | 
 932 |   </div><!-- /row5 -->
 933 | 
 934 |   <!-- Footer -->
 935 |   <div style="text-align:center;padding:24px 0 12px;font:400 9px/1 var(--font);color:var(--text-dim);letter-spacing:.08em;">
 936 |     PROTOCOL PULSE TERMINAL — BITCOIN INTELLIGENCE — DATA UPDATES CONTINUOUSLY
 937 |     {% if is_commander %} — COMMANDER ACCESS ACTIVE{% endif %}
 938 |   </div>
 939 | 
 940 | </div><!-- /page -->
 941 | 
 942 | <!-- ================================================================
 943 |      JAVASCRIPT
 944 |      ================================================================ -->
 945 | <script>
 946 | // ── UTC clock ─────────────────────────────────────────────────────
 947 | function tickClock() {
 948 |   const now = new Date();
 949 |   const h = now.getUTCHours().toString().padStart(2,'0');
 950 |   const m = now.getUTCMinutes().toString().padStart(2,'0');
 951 |   const s = now.getUTCSeconds().toString().padStart(2,'0');
 952 |   const el = document.getElementById('sb-clock');
 953 |   if (el) el.textContent = `${h}:${m}:${s} UTC`;
 954 | }
 955 | setInterval(tickClock, 1000);
 956 | tickClock();
 957 | 
 958 | // ── Flash utility ─────────────────────────────────────────────────
 959 | function flash(el) {
 960 |   el.classList.remove('value-updated');
 961 |   void el.offsetWidth;
 962 |   el.classList.add('value-updated');
 963 |   setTimeout(() => el.classList.remove('value-updated'), 700);
 964 | }
 965 | 
 966 | // ── Format helpers ────────────────────────────────────────────────
 967 | const fmt = (n, d=2) => n == null ? '—' : Number(n).toLocaleString('en-US', {minimumFractionDigits:d, maximumFractionDigits:d});
 968 | const fmtk = n => n == null ? '—' : Number(n).toLocaleString('en-US', {maximumFractionDigits:0});
 969 | 
 970 | // ── BTC price live fetch ──────────────────────────────────────────
 971 | let lastPrice = {{ price.price or 0 }};
 972 | let priceHistory = [];
 973 | 
 974 | function updatePriceDisplay(data) {
 975 |   const newPrice = data.price || 0;
 976 |   const el = document.getElementById('btc-price-hero');
 977 |   const sbEl = document.getElementById('sb-price');
 978 |   const deltaEl = document.getElementById('sb-delta');
 979 |   if (el && newPrice) {
 980 |     const old = lastPrice;
 981 |     lastPrice = newPrice;
 982 |     el.textContent = '$' + fmtk(newPrice) + '.00';
 983 |     flash(el);
 984 |     if (sbEl) sbEl.firstChild.textContent = 'BTC $' + fmtk(newPrice);
 985 |     if (deltaEl) {
 986 |       const pct = data.change_24h_pct || 0;
 987 |       deltaEl.textContent = (pct >= 0 ? '▲' : '▼') + Math.abs(pct).toFixed(2) + '%';
 988 |       deltaEl.style.color = pct >= 0 ? '#10B981' : '#EF4444';
 989 |     }
 990 |     priceHistory.push(newPrice);
 991 |     if (priceHistory.length > 20) priceHistory.shift();
 992 |     drawSparkline('spark-price-line', priceHistory, 300, 28);
 993 |   }
 994 | }
 995 | 
 996 | function fetchPrice() {
 997 |   fetch('/api/v2/terminal/price')
 998 |     .then(r => r.json())
 999 |     .then(d => updatePriceDisplay(d))
1000 |     .catch(() => {});
1001 | }
1002 | 
1003 | // ── Mempool fetch ─────────────────────────────────────────────────
1004 | function fetchMempool() {
1005 |   fetch('/api/v2/terminal/mempool')
1006 |     .then(r => r.json())
1007 |     .then(d => {
1008 |       const el = document.getElementById('mp-count');
1009 |       if (el && d.count) { el.textContent = fmtk(d.count); flash(el); }
1010 |     })
1011 |     .catch(() => {});
1012 | }
1013 | 
1014 | // ── Articles refresh ──────────────────────────────────────────────
1015 | function fetchLatest() {
1016 |   fetch('/api/v2/terminal/latest')
1017 |     .then(r => r.json())
1018 |     .then(d => {
1019 |       const feed = document.getElementById('article-feed');
1020 |       if (!feed || !d.articles || !d.articles.length) return;
1021 |       feed.innerHTML = d.articles.map(a =>
1022 |         `<a href="${a.slug}" class="article-row">
1023 |           <span class="article-time">${a.time || '—'}</span>
1024 |           <span class="article-title">${escHtml(a.title)}</span>
1025 |           <span class="article-arrow">→</span>
1026 |         </a>`
1027 |       ).join('');
1028 |     })
1029 |     .catch(() => {});
1030 | }
1031 | 
1032 | function escHtml(s) {
1033 |   return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
1034 | }
1035 | 
1036 | // ── Sparkline renderer ────────────────────────────────────────────
1037 | function drawSparkline(id, data, w, h) {
1038 |   if (!data || data.length < 2) return;
1039 |   const poly = document.getElementById(id);
1040 |   if (!poly) return;
1041 |   const mn = Math.min(...data), mx = Math.max(...data);
1042 |   const range = mx - mn || 1;
1043 |   const pts = data.map((v, i) => {
1044 |     const x = (i / (data.length - 1)) * w;
1045 |     const y = h - ((v - mn) / range) * (h - 2) - 1;
1046 |     return `${x.toFixed(1)},${y.toFixed(1)}`;
1047 |   }).join(' ');
1048 |   poly.setAttribute('points', pts);
1049 | }
1050 | 
1051 | // ── WebSocket for live BTC price ──────────────────────────────────
1052 | let wsConnected = false;
1053 | function connectWS() {
1054 |   try {
1055 |     const ws = new WebSocket('wss://ws.blockchain.info/inv');
1056 |     ws.onopen = () => {
1057 |       ws.send(JSON.stringify({op:'unconfirmed_sub'}));
1058 |       wsConnected = true;
1059 |     };
1060 |     ws.onmessage = (e) => {
1061 |       try {
1062 |         const d = JSON.parse(e.data);
1063 |         if (d.x && d.x.out) {
1064 |           // Use as a trigger to refresh price
1065 |           fetchPrice();
1066 |         }
1067 |       } catch(ex){}
1068 |     };
1069 |     ws.onclose = () => { wsConnected = false; };
1070 |     ws.onerror = () => { wsConnected = false; };
1071 |   } catch(e) {}
1072 | }
1073 | connectWS();
1074 | 
1075 | // ── Polling schedule ──────────────────────────────────────────────
1076 | fetchPrice();
1077 | fetchMempool();
1078 | fetchLatest();
1079 | setInterval(fetchPrice, 15000);
1080 | setInterval(fetchMempool, 30000);
1081 | setInterval(fetchLatest, 60000);
1082 | // Reconnect WS if disconnected
1083 | setInterval(() => { if (!wsConnected) connectWS(); }, 30000);
1084 | 
1085 | // ── "See What You're Missing" 5-second preview ────────────────────
1086 | let previewActive = false;
1087 | 
1088 | function startPreview() {
1089 |   if (previewActive) return;
1090 |   previewActive = true;
1091 | 
1092 |   const btn = document.getElementById('btn-preview');
1093 |   if (btn) btn.disabled = true;
1094 | 
1095 |   const locked = document.querySelectorAll('.panel-locked');
1096 |   const bars = [];
1097 | 
1098 |   locked.forEach(panel => {
1099 |     // Add preview mode
1100 |     panel.classList.add('preview-mode');
1101 | 
1102 |     // Add gold countdown bar
1103 |     const bar = document.createElement('div');
1104 |     bar.className = 'preview-bar';
1105 |     bar.style.width = '100%';
1106 |     panel.appendChild(bar);
1107 |     bars.push(bar);
1108 |   });
1109 | 
1110 |   let countdown = 5;
1111 |   const interval = setInterval(() => {
1112 |     countdown--;
1113 |     // Update bar width
1114 |     const pct = (countdown / 5) * 100;
1115 |     bars.forEach(b => b.style.width = pct + '%');
1116 | 
1117 |     if (countdown <= 0) {
1118 |       clearInterval(interval);
1119 |       // Re-lock all panels
1120 |       locked.forEach(panel => {
1121 |         panel.classList.remove('preview-mode');
1122 |       });
1123 |       // Remove bars
1124 |       bars.forEach(b => b.remove());
1125 |       previewActive = false;
1126 |       if (btn) btn.disabled = false;
1127 |       // Show re-engagement banner
1128 |       showReEngage();
1129 |     }
1130 |   }, 1000);
1131 | }
1132 | 
1133 | function showReEngage() {
1134 |   const banner = document.getElementById('re-engage-banner');
1135 |   if (banner) {
1136 |     banner.style.display = 'block';
1137 |     // Auto-dismiss after 12s
1138 |     setTimeout(() => { if (banner) banner.style.display = 'none'; }, 12000);
1139 |   }
1140 | }
1141 | 
1142 | document.getElementById('re-engage-close')?.addEventListener('click', () => {
1143 |   document.getElementById('re-engage-banner').style.display = 'none';
1144 | });
1145 | 
1146 | // ── Copy API key ──────────────────────────────────────────────────
1147 | function copyKey() {
1148 |   const el = document.getElementById('api-key-text');
1149 |   if (el) {
1150 |     navigator.clipboard.writeText(el.textContent.trim()).then(() => {
1151 |       const btn = document.querySelector('.copy-btn');
1152 |       if (btn) { btn.textContent = 'COPIED'; setTimeout(() => btn.textContent = 'COPY', 2000); }
1153 |     }).catch(() => {
1154 |       const rng = document.createRange();
1155 |       rng.selectNode(el);
1156 |       window.getSelection().removeAllRanges();
1157 |       window.getSelection().addRange(rng);
1158 |       document.execCommand('copy');
1159 |     });
1160 |   }
1161 | }
1162 | 
1163 | // ── Rank formatting (zero-pad) ────────────────────────────────────
1164 | String.prototype.zfill = function(n) { return this.padStart(n,'0'); };
1165 | </script>
1166 | </body>
1167 | </html>
1168 | 
```

### File: core/templates/terminal_account.html (31 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}Terminal Account — Protocol Pulse{% endblock %}
   3 | {% block content %}
   4 | <style>
   5 | body { background: #080810; font-family: 'JetBrains Mono', monospace; }
   6 | .term-account { max-width: 680px; margin: 80px auto; padding: 24px; color: #E2E8F0; }
   7 | .ta-title { font: 700 14px/1 'JetBrains Mono', monospace; color: #F59E0B; letter-spacing: .12em; text-transform: uppercase; margin-bottom: 20px; }
   8 | .ta-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #1C1C2E; font: 400 12px/1 'JetBrains Mono', monospace; }
   9 | .ta-label { color: #64748B; text-transform: uppercase; font-size: 10px; letter-spacing: .08em; }
  10 | .ta-val { color: #E2E8F0; }
  11 | .ta-key { background: #050508; border: 1px solid #1C1C2E; padding: 10px 14px; margin-top: 16px; color: #00FF41; font: 400 12px/1 'JetBrains Mono', monospace; word-break: break-all; }
  12 | .btn-back { display: inline-block; margin-top: 20px; padding: 10px 20px; border: 1px solid #F59E0B; color: #F59E0B; font: 600 10px/1 'JetBrains Mono', monospace; letter-spacing: .1em; text-transform: uppercase; text-decoration: none; }
  13 | </style>
  14 | <div class="term-account">
  15 |   <div class="ta-title">COMMANDER ACCOUNT</div>
  16 |   {% if sub %}
  17 |   <div class="ta-row"><span class="ta-label">EMAIL</span><span class="ta-val">{{ sub.email }}</span></div>
  18 |   <div class="ta-row"><span class="ta-label">TIER</span><span class="ta-val" style="color:#F59E0B;">{{ sub.tier.upper() }}</span></div>
  19 |   <div class="ta-row"><span class="ta-label">STATUS</span><span class="ta-val" style="color:#10B981;">{{ sub.subscription_status.upper() }}</span></div>
  20 |   <div class="ta-row"><span class="ta-label">RATE LIMIT</span><span class="ta-val">10,000 req/hr</span></div>
  21 |   <div class="ta-row"><span class="ta-label">API KEY</span><span class="ta-val">{{ sub.api_key[:16] }}...</span></div>
  22 |   <div style="margin-top:14px;font:400 10px/1 'JetBrains Mono',monospace;color:#64748B;">
  23 |     Your full API key (shown only at activation). Use Bearer auth: <code>Authorization: Bearer YOUR_KEY</code>
  24 |   </div>
  25 |   {% else %}
  26 |   <p style="color:#64748B;font-size:12px;">No API subscriber record found. Activate Commander to generate your key.</p>
  27 |   {% endif %}
  28 |   <a href="/terminal" class="btn-back">← BACK TO TERMINAL</a>
  29 | </div>
  30 | {% endblock %}
  31 | 
```

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?
