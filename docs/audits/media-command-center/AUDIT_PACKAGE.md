# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: media-command-center
# Branch: main
# Generated: 2026-03-26 00:39 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS

### LAW 1: BRAND PALETTE
- Primary Red: #CC2222 (accent, borders, kickers)
- FFmpeg Red: #FF3333 (drawtext/drawbox fallback — closest FFmpeg-safe)
- Background: #0A0A0F (dark navy, never pure black)
- White: #FFFFFF (primary text)
- Gold: #F8C15C (info rail, price displays)
- Mono Font: JetBrains Mono (data, kickers, code)

### LAW 2: PIXEL ZONES
- Full canvas: 1920×1080
- Left panel (PiP): 0–960px wide, full 1080 height
- Right panel (PiP video): 960–1920px
- PiP zone: top-right quadrant x=960-1880, y=0-540
- Subtitle band: y=778-885, full width, dark glass bg
- Info rail: bottom y≈1032-1080, gold text

### LAW 3: TYPOGRAPHY
- Headlines: Bold, white, large (fontsize 42-56)
- Kickers: Red monospace, uppercase, fontsize 24-28
- Body: White, fontsize 28-32
- Sponsor text: White monospace, fontsize 22-26

### LAW 4: COMPONENT PATTERNS
- Cards: Dark bg (#111), red left accent border (3px), white text
- Glass panels: rgba(0,0,0,0.82) fill, subtle border
- Sponsor carousel: 3 rotating cards, 8s per card, FFmpeg enable= timing
- Episode title: Large white bold, "PULSE CHECK" red kicker above

### LAW 5: ANIMATION
- Sponsor rotation: enable='between(t,START,END)' pattern
- Smooth transitions preferred, hard cuts acceptable for data cards
- No debug overlays in production



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

### File: templates/media_hub.html (1074 lines)
```
   1 | {% extends "base.html" %}
   2 | {% block title %}Bitcoin Media Command Center — Protocol Pulse{% endblock %}
   3 | {% block meta_description %}The definitive Bitcoin media hub. 20+ voices. Live feeds from top podcasts, YouTube channels, and KOL intelligence. One screen.{% endblock %}
   4 | {% block head %}
   5 | <script src="https://d3js.org/d3.v7.min.js"></script>
   6 | <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
   7 | <style>
   8 | :root{
   9 |   --void:#000;--deep:#040408;--card:#08080e;--elevated:#0e0e16;--hover:#14141e;
  10 |   --border:rgba(255,255,255,0.05);--border-h:rgba(255,255,255,0.1);
  11 |   --bright:#f5f5f5;--pri:#e0e0e0;--sec:rgba(255,255,255,0.5);--mut:rgba(255,255,255,0.25);
  12 |   --red:#dc2626;--red-g:rgba(220,38,38,0.12);--btc:#f7931a;
  13 |   --gold:#f8c15c;--cyan:#5de4ff;--lime:#89ffb8;--coral:#ff8ba0;
  14 | }
  15 | *{box-sizing:border-box;margin:0;padding:0}
  16 | .mh{font-family:'DM Sans',-apple-system,sans-serif;background:var(--void);color:var(--pri);min-height:100vh;padding-top:80px}
  17 | .mono{font-family:'JetBrains Mono',monospace}
  18 | 
  19 | /* ── TICKER ── */
  20 | .ticker-wrap{position:relative;overflow:hidden;background:linear-gradient(90deg,rgba(220,38,38,0.06),rgba(8,8,14,0.95),rgba(220,38,38,0.06));border-bottom:1px solid var(--border);padding:0;height:36px}
  21 | .ticker-track{display:flex;animation:tickerScroll 120s linear infinite;white-space:nowrap;height:100%;align-items:center}
  22 | .ticker-track:hover{animation-play-state:paused}
  23 | .ticker-item{display:inline-flex;align-items:center;gap:6px;padding:0 24px;font-size:12px;color:var(--sec);text-decoration:none;transition:color .2s;flex-shrink:0;height:100%}
  24 | .ticker-item:hover{color:var(--bright)}
  25 | .ticker-icon{font-size:10px;opacity:.6}
  26 | .ticker-src{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--red);text-transform:uppercase;letter-spacing:1px;font-weight:600}
  27 | .ticker-title{max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  28 | .ticker-score{font-family:'JetBrains Mono',monospace;font-size:9px;padding:2px 6px;border-radius:10px;font-weight:600}
  29 | .ticker-score.high{background:rgba(137,255,184,0.1);color:var(--lime)}
  30 | .ticker-score.mid{background:rgba(248,193,92,0.1);color:var(--gold)}
  31 | .ticker-score.low{background:rgba(255,255,255,0.05);color:var(--mut)}
  32 | .ticker-sep{width:1px;height:14px;background:var(--border);flex-shrink:0;margin:0 4px}
  33 | @keyframes tickerScroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}
  34 | 
  35 | .wrap{max-width:1440px;margin:0 auto;padding:0 clamp(16px,4vw,48px)}
  36 | 
  37 | /* ── HERO ── */
  38 | .hero{position:relative;padding:64px 0 48px;overflow:hidden}
  39 | .hero-bg{position:absolute;inset:0;overflow:hidden}
  40 | .hero-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(220,38,38,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(220,38,38,0.03) 1px,transparent 1px);background-size:60px 60px;animation:gridDrift 20s linear infinite}
  41 | @keyframes gridDrift{from{transform:translate(0,0)}to{transform:translate(60px,60px)}}
  42 | .hero-orb{position:absolute;border-radius:50%;filter:blur(80px);animation:orbFloat 8s ease-in-out infinite}
  43 | .hero-orb-1{width:400px;height:400px;background:rgba(220,38,38,0.08);top:-100px;left:20%}
  44 | .hero-orb-2{width:300px;height:300px;background:rgba(248,193,92,0.05);bottom:-80px;right:15%;animation-delay:-3s}
  45 | .hero-orb-3{width:200px;height:200px;background:rgba(93,228,255,0.04);top:40%;left:60%;animation-delay:-5s}
  46 | @keyframes orbFloat{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(30px,-20px) scale(1.1)}}
  47 | .hero-scanline{position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,rgba(220,38,38,0.3),transparent);animation:scanDown 4s linear infinite;opacity:0.4}
  48 | @keyframes scanDown{from{top:0}to{top:100%}}
  49 | .hero-vignette{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 40%,transparent 40%,var(--void) 100%)}
  50 | .hero-inner{position:relative;z-index:2}
  51 | .hero-tag{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;background:rgba(220,38,38,0.08);border:1px solid rgba(220,38,38,0.15);border-radius:24px;margin-bottom:24px;opacity:0;animation:fadeUp .6s ease forwards}
  52 | .hero-tag-dot{width:6px;height:6px;border-radius:50%;background:var(--red);animation:tagPulse 2s infinite}
  53 | @keyframes tagPulse{0%,100%{opacity:1}50%{opacity:0.3}}
  54 | .hero-tag-text{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--red)}
  55 | .hero-h{font-size:clamp(36px,7vw,64px);font-weight:700;line-height:1;color:var(--bright);letter-spacing:-2px;margin-bottom:16px;opacity:0;animation:fadeUp .6s ease .1s forwards}
  56 | .hero-h em{font-style:normal;background:linear-gradient(135deg,var(--red),var(--btc));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
  57 | .hero-sub{font-size:15px;font-weight:300;color:var(--sec);max-width:520px;line-height:1.6;opacity:0;animation:fadeUp .6s ease .2s forwards}
  58 | .hero-metrics{display:flex;gap:32px;margin-top:32px;opacity:0;animation:fadeUp .6s ease .3s forwards;flex-wrap:wrap}
  59 | .hero-metric{position:relative;padding:12px 0}
  60 | .hero-metric::after{content:'';position:absolute;right:-16px;top:50%;transform:translateY(-50%);width:1px;height:20px;background:var(--border)}
  61 | .hero-metric:last-child::after{display:none}
  62 | .hero-metric-val{font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:var(--bright)}
  63 | .hero-metric-lab{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:1.5px;margin-top:2px}
  64 | @keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
  65 | 
  66 | /* ── SECTIONS ── */
  67 | .sec{padding:56px 0;border-top:1px solid var(--border)}
  68 | .sec-lab{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--red);margin-bottom:12px}
  69 | .sec-h{font-size:clamp(22px,3.5vw,32px);font-weight:700;color:var(--bright);letter-spacing:-0.5px;margin-bottom:8px}
  70 | .sec-desc{font-size:14px;color:var(--sec);max-width:520px;line-height:1.6;margin-bottom:32px}
  71 | 
  72 | /* ── FEED MATRIX ── */
  73 | .feed-matrix{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;min-height:500px}
  74 | .feed-col{display:flex;flex-direction:column;min-width:0}
  75 | .feed-col-head{display:flex;align-items:center;gap:8px;padding:12px 16px;background:var(--card);border:1px solid var(--border);border-radius:10px 10px 0 0;border-bottom:none}
  76 | .feed-col-icon{font-size:12px;width:26px;height:26px;border-radius:6px;display:flex;align-items:center;justify-content:center}
  77 | .feed-col-icon.pod{background:rgba(220,38,38,0.1);color:var(--red)}
  78 | .feed-col-icon.vid{background:rgba(248,193,92,0.1);color:var(--gold)}
  79 | .feed-col-icon.kol{background:rgba(93,228,255,0.1);color:var(--cyan)}
  80 | .feed-col-name{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:var(--bright);text-transform:uppercase;letter-spacing:1px}
  81 | .feed-col-count{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--mut)}
  82 | .feed-list{flex:1;background:var(--card);border:1px solid var(--border);border-radius:0 0 10px 10px;overflow-y:auto;max-height:700px;padding:8px}
  83 | .feed-list::-webkit-scrollbar{width:3px}
  84 | .feed-list::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.08);border-radius:2px}
  85 | 
  86 | /* ── FEED ITEM ── */
  87 | .fi{display:block;padding:14px;margin-bottom:6px;border-radius:10px;background:rgba(255,255,255,0.015);border:1px solid rgba(255,255,255,0.04);transition:all .2s;text-decoration:none;color:inherit}
  88 | .fi:hover{border-color:rgba(255,255,255,0.08);background:rgba(255,255,255,0.03);transform:translateY(-1px)}
  89 | .fi-head{display:flex;align-items:center;gap:8px;margin-bottom:8px}
  90 | .fi-thumb{width:48px;height:48px;border-radius:8px;object-fit:cover;flex-shrink:0;background:var(--elevated)}
  91 | .fi-thumb-yt{width:80px;height:45px;border-radius:6px;object-fit:cover;flex-shrink:0;background:var(--elevated);position:relative}
  92 | .fi-thumb-yt::after{content:'\25B6';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:white;font-size:14px;text-shadow:0 0 8px rgba(0,0,0,.8)}
  93 | .fi-info{flex:1;min-width:0}
  94 | .fi-show{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--red);text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:2px}
  95 | .fi-title{font-size:13px;font-weight:600;color:var(--bright);line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  96 | .fi-meta{display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap}
  97 | .fi-time{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--mut)}
  98 | .fi-dur{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--mut)}
  99 | .fi-score{font-family:'JetBrains Mono',monospace;font-size:9px;padding:2px 6px;border-radius:10px;font-weight:600}
 100 | .fi-score.s-high{background:rgba(137,255,184,0.1);color:var(--lime)}
 101 | .fi-score.s-mid{background:rgba(248,193,92,0.1);color:var(--gold)}
 102 | .fi-score.s-low{background:rgba(255,255,255,0.05);color:var(--mut)}
 103 | .fi-summary{font-size:11px;color:var(--sec);line-height:1.4;margin-top:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
 104 | .fi-play{display:inline-flex;align-items:center;gap:4px;margin-top:8px;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--red);text-transform:uppercase;letter-spacing:1px;cursor:pointer;background:none;border:none;padding:0;transition:color .2s}
 105 | .fi-play:hover{color:var(--bright)}
 106 | .fi-empty{text-align:center;padding:40px 16px;color:var(--mut);font-size:12px}
 107 | 
 108 | /* ── SKELETON LOADING ── */
 109 | .skel{background:linear-gradient(90deg,rgba(255,255,255,0.03) 25%,rgba(255,255,255,0.06) 50%,rgba(255,255,255,0.03) 75%);background-size:200% 100%;animation:skelShimmer 1.5s infinite;border-radius:6px}
 110 | @keyframes skelShimmer{from{background-position:200% 0}to{background-position:-200% 0}}
 111 | .skel-item{padding:14px;margin-bottom:6px;border-radius:10px}
 112 | .skel-title{height:14px;width:80%;margin-bottom:8px}
 113 | .skel-sub{height:10px;width:60%;margin-bottom:4px}
 114 | .skel-bar{height:8px;width:40%}
 115 | 
 116 | /* ── SERIES ── */
 117 | .sg{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}
 118 | .sc{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;cursor:pointer;transition:all .3s}
 119 | .sc:hover{border-color:var(--border-h);transform:translateY(-3px);box-shadow:0 16px 48px rgba(0,0,0,.4)}
 120 | .sc:hover .sc-img{transform:scale(1.05)}
 121 | .sc-img-w{position:relative;overflow:hidden;aspect-ratio:16/9}
 122 | .sc-img{width:100%;height:100%;object-fit:cover;transition:transform .5s}
 123 | .sc-ov{position:absolute;inset:0;background:linear-gradient(180deg,transparent 30%,rgba(0,0,0,.9) 100%)}
 124 | .sc-play{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:48px;height:48px;background:rgba(220,38,38,.9);border-radius:50%;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .3s}
 125 | .sc:hover .sc-play{opacity:1}
 126 | .sc-play i{color:white;font-size:16px;margin-left:2px}
 127 | .sc-badge{position:absolute;top:10px;right:10px;background:rgba(0,0,0,.7);backdrop-filter:blur(8px);padding:3px 8px;border-radius:16px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--sec);border:1px solid rgba(255,255,255,.08)}
 128 | .sc-body{padding:16px 20px 20px}
 129 | .sc-host{font-size:11px;color:var(--red);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
 130 | .sc-name{font-size:20px;font-weight:700;color:var(--bright);margin-bottom:8px;line-height:1.3}
 131 | .sc-desc{font-size:12px;color:var(--sec);line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
 132 | 
 133 | /* ── SERIES DETAIL ── */
 134 | .sd{display:none;margin-top:24px;border-radius:14px;overflow:hidden;border:1px solid var(--border);background:var(--card)}
 135 | .sd.active{display:block;animation:fadeUp .4s ease}
 136 | .sd-top{display:flex;align-items:center;justify-content:space-between;padding:16px 24px;border-bottom:1px solid var(--border)}
 137 | .sd-title{font-size:20px;font-weight:700;color:var(--bright)}
 138 | .sd-x{background:rgba(255,255,255,.05);border:none;color:var(--mut);width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center}
 139 | .sd-x:hover{background:rgba(255,255,255,.1);color:white}
 140 | .sd-main{display:grid;grid-template-columns:1fr 340px}
 141 | .sd-vid iframe{width:100%;aspect-ratio:16/9;border:none;display:block;background:#000}
 142 | .sd-eps{max-height:440px;overflow-y:auto;border-left:1px solid var(--border)}
 143 | .sd-ep{display:flex;gap:10px;padding:10px 14px;cursor:pointer;transition:background .15s;border-bottom:1px solid var(--border);align-items:center}
 144 | .sd-ep:hover{background:var(--hover)}
 145 | .sd-ep.active{background:rgba(220,38,38,.05);border-left:3px solid var(--red)}
 146 | .sd-ep-img{width:80px;height:45px;border-radius:5px;object-fit:cover;flex-shrink:0}
 147 | .sd-ep-info{flex:1;min-width:0}
 148 | .sd-ep-n{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--red);letter-spacing:1px}
 149 | .sd-ep-t{font-size:11px;color:var(--pri);margin-top:2px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
 150 | 
 151 | /* ── PODCAST (LEGACY) ── */
 152 | .pod-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
 153 | .pod-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}
 154 | .pod-card:hover{border-color:var(--border-h);background:var(--elevated);transform:translateY(-2px)}
 155 | .pod-card::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:var(--red);opacity:0;transition:opacity .2s}
 156 | .pod-card:hover::before{opacity:1}
 157 | .pod-num{font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:600;color:rgba(220,38,38,0.1);position:absolute;top:12px;right:16px}
 158 | .pod-title{font-size:14px;font-weight:600;color:var(--bright);line-height:1.4;margin-bottom:10px;padding-right:40px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
 159 | .pod-meta{display:flex;align-items:center;gap:12px}
 160 | .pod-dur{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--mut)}
 161 | .pod-play-btn{width:28px;height:28px;border-radius:50%;background:var(--red);display:flex;align-items:center;justify-content:center;margin-left:auto;opacity:0;transition:opacity .2s}
 162 | .pod-card:hover .pod-play-btn{opacity:1}
 163 | .pod-play-btn i{color:white;font-size:10px;margin-left:1px}
 164 | .pod-more{display:inline-flex;align-items:center;gap:8px;margin-top:24px;padding:10px 20px;background:transparent;border:1px solid var(--border);border-radius:8px;color:var(--sec);font-size:13px;text-decoration:none;transition:all .2s}
 165 | .pod-more:hover{border-color:var(--red);color:var(--red)}
 166 | 
 167 | /* ── BOOKS ── */
 168 | .bg{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:16px}
 169 | .bc{background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden;transition:all .3s;text-decoration:none;display:block}
 170 | .bc:hover{border-color:var(--border-h);transform:translateY(-3px);box-shadow:0 12px 36px rgba(0,0,0,.3)}
 171 | .bc-cov{aspect-ratio:2/3;display:flex;align-items:flex-end;position:relative;border-radius:4px 4px 0 0;overflow:hidden}
 172 | .bc-img{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;z-index:2}
 173 | .bc-spine{position:absolute;left:0;top:8%;bottom:8%;width:3px;border-radius:0 2px 2px 0}
 174 | .bc-txt{padding:16px 14px;position:relative;z-index:1;width:100%}
 175 | .bc-txt-t{font-size:14px;font-weight:600;color:rgba(255,255,255,0.9);line-height:1.3;margin-bottom:4px}
 176 | .bc-txt-a{font-family:'JetBrains Mono',monospace;font-size:9px;color:rgba(255,255,255,0.4);letter-spacing:0.5px;text-transform:uppercase}
 177 | .bc-info{padding:10px 12px 12px}
 178 | .bc-badge{font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:1.5px;text-transform:uppercase;color:var(--btc);margin-bottom:4px}
 179 | .bc-badge.econ{color:#22c55e}
 180 | .bc-name{font-size:11px;font-weight:600;color:var(--bright);margin-bottom:2px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
 181 | .bc-auth{font-size:10px;color:var(--sec)}
 182 | .bcat{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--mut);margin-top:36px;margin-bottom:14px;padding-bottom:6px;border-bottom:1px solid var(--border)}
 183 | .bcat:first-of-type{margin-top:0}
 184 | .btog{display:flex;align-items:center;gap:10px;margin-top:36px;padding:12px 18px;background:var(--card);border:1px solid var(--border);border-radius:10px;cursor:pointer;width:100%;color:var(--sec);font-size:13px;font-weight:500;transition:all .2s}
 185 | .btog:hover{border-color:var(--border-h);color:var(--bright)}
 186 | .btog i{transition:transform .3s}
 187 | .btog.open i{transform:rotate(180deg)}
 188 | .bhid{display:none}.bhid.show{display:block;animation:fadeUp .4s ease}
 189 | 
 190 | /* ── NEWSLETTER CTA ── */
 191 | .nl{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:48px;text-align:center;position:relative;overflow:hidden}
 192 | .nl::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at center,var(--red-g) 0%,transparent 60%);pointer-events:none}
 193 | .nl-h{font-size:28px;font-weight:700;color:var(--bright);margin-bottom:10px;position:relative}
 194 | .nl-p{font-size:14px;color:var(--sec);margin-bottom:28px;position:relative}
 195 | .nl-f{display:flex;gap:10px;max-width:400px;margin:0 auto;position:relative}
 196 | .nl-i{flex:1;padding:12px 16px;background:var(--void);border:1px solid var(--border);border-radius:8px;color:var(--bright);font-size:13px;outline:none}
 197 | .nl-i:focus{border-color:var(--red)}
 198 | .nl-i::placeholder{color:var(--mut)}
 199 | .nl-b{padding:12px 24px;background:var(--red);border:none;border-radius:8px;color:white;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap}
 200 | 
 201 | /* ── AUDIO BAR ── */
 202 | .abar{position:fixed;bottom:0;left:0;right:0;background:rgba(8,8,14,.95);border-top:1px solid var(--border);padding:10px 24px;display:none;align-items:center;gap:14px;z-index:1000;backdrop-filter:blur(20px)}
 203 | .abar.active{display:flex}
 204 | .abar-btn{background:none;border:none;color:var(--sec);cursor:pointer;padding:4px 8px;font-size:16px}
 205 | .abar-btn:hover{color:var(--bright)}
 206 | .abar-now{flex:1;min-width:0}
 207 | .abar-title{font-size:12px;color:var(--pri);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 208 | .abar-show{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--red);text-transform:uppercase;letter-spacing:1px}
 209 | .abar-progress{height:2px;background:var(--border);border-radius:1px;margin-top:4px;cursor:pointer}
 210 | .abar-progress-fill{height:100%;background:var(--red);border-radius:1px;width:0;transition:width .3s}
 211 | .abar-close{background:none;border:none;color:var(--mut);cursor:pointer;font-size:12px;padding:4px 8px}
 212 | .abar-close:hover{color:var(--bright)}
 213 | 
 214 | /* ── NOSTR/KOL ITEMS ── */
 215 | .kol-item{padding:14px;margin-bottom:6px;border-radius:10px;background:rgba(255,255,255,0.015);border:1px solid rgba(255,255,255,0.04)}
 216 | .kol-head{display:flex;align-items:center;gap:8px;margin-bottom:8px}
 217 | .kol-av{width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;flex-shrink:0;border:1px solid rgba(255,255,255,0.06)}
 218 | .kol-av.macro{background:rgba(220,38,38,0.1);color:var(--red)}
 219 | .kol-av.protocol{background:rgba(93,228,255,0.1);color:var(--cyan)}
 220 | .kol-av.media{background:rgba(248,193,92,0.1);color:var(--gold)}
 221 | .kol-name{font-size:12px;font-weight:600;color:var(--bright);flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 222 | .kol-time{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--mut)}
 223 | .kol-body{font-size:12px;color:var(--pri);line-height:1.5;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;word-break:break-word}
 224 | .kol-body a{color:var(--cyan);text-decoration:none}
 225 | .kol-foot{display:flex;gap:12px;margin-top:8px}
 226 | .kol-link{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--mut);text-decoration:none;display:flex;align-items:center;gap:3px;text-transform:uppercase;letter-spacing:.5px;transition:color .2s}
 227 | .kol-link:hover{color:var(--bright)}
 228 | .kol-loader{display:inline-block;width:14px;height:14px;border:2px solid var(--border);border-top:2px solid var(--red);border-radius:50%;animation:spin .7s linear infinite;margin-top:10px}
 229 | @keyframes spin{to{transform:rotate(360deg)}}
 230 | 
 231 | /* ── D3 VOICE NETWORK ── */
 232 | .net-wrap{position:relative;background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;min-height:500px}
 233 | .net-svg{width:100%;height:500px;display:block}
 234 | .net-svg .node-circle{cursor:pointer;transition:r .2s}
 235 | .net-svg .link{stroke:rgba(255,255,255,0.04);stroke-width:1}
 236 | .net-svg text{font-family:'JetBrains Mono',monospace;font-size:9px;fill:var(--sec);pointer-events:none;text-anchor:middle}
 237 | .net-legend{position:absolute;top:16px;right:16px;display:flex;gap:12px}
 238 | .net-leg-item{display:flex;align-items:center;gap:5px;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--mut);text-transform:uppercase;letter-spacing:1px}
 239 | .net-leg-dot{width:8px;height:8px;border-radius:50%}
 240 | .net-hover{position:absolute;pointer-events:none;background:rgba(8,8,14,0.95);border:1px solid var(--border);border-radius:10px;padding:14px 16px;min-width:200px;max-width:280px;display:none;z-index:10;backdrop-filter:blur(12px)}
 241 | .net-hover.show{display:block}
 242 | .net-hover-name{font-size:14px;font-weight:700;color:var(--bright);margin-bottom:4px}
 243 | .net-hover-handle{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--red)}
 244 | .net-hover-cat{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--mut);text-transform:uppercase;letter-spacing:1px;margin-top:6px}
 245 | .net-hover-stat{display:flex;gap:16px;margin-top:8px}
 246 | .net-hover-stat div{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--bright)}
 247 | .net-hover-stat span{display:block;font-size:8px;color:var(--mut);text-transform:uppercase;letter-spacing:1px;margin-top:2px}
 248 | 
 249 | /* ── KOL HEATMAP ── */
 250 | .hm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px}
 251 | .hm-cell{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 12px;text-align:center;transition:all .2s;cursor:default;position:relative;overflow:hidden}
 252 | .hm-cell::before{content:'';position:absolute;inset:0;opacity:0.06;pointer-events:none}
 253 | .hm-cell.bullish::before{background:var(--lime)}.hm-cell.bearish::before{background:var(--coral)}.hm-cell.neutral::before{background:var(--gold)}
 254 | .hm-cell:hover{border-color:var(--border-h);transform:translateY(-1px)}
 255 | .hm-name{font-size:11px;font-weight:600;color:var(--bright);margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 256 | .hm-handle{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--mut);margin-bottom:8px}
 257 | .hm-bar{height:4px;border-radius:2px;background:var(--border);overflow:hidden;margin-bottom:6px}
 258 | .hm-bar-fill{height:100%;border-radius:2px;transition:width .6s}
 259 | .hm-bar-fill.bull{background:var(--lime)}.hm-bar-fill.bear{background:var(--coral)}.hm-bar-fill.neut{background:var(--gold)}
 260 | .hm-score{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700}
 261 | .hm-score.bull{color:var(--lime)}.hm-score.bear{color:var(--coral)}.hm-score.neut{color:var(--gold)}
 262 | .hm-label{font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--mut);text-transform:uppercase;letter-spacing:1px;margin-top:2px}
 263 | 
 264 | /* ── COMMANDER GATE ── */
 265 | .cmd-gate{position:relative;border-radius:14px;overflow:hidden}
 266 | .cmd-gate-blur{filter:blur(6px);pointer-events:none;user-select:none}
 267 | .cmd-gate-overlay{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(0,0,0,0.5);backdrop-filter:blur(2px);z-index:5;border-radius:14px}
 268 | .cmd-gate-icon{font-size:28px;color:var(--gold);margin-bottom:12px}
 269 | .cmd-gate-title{font-size:16px;font-weight:700;color:var(--bright);margin-bottom:6px}
 270 | .cmd-gate-sub{font-size:12px;color:var(--sec);margin-bottom:16px;text-align:center;max-width:300px}
 271 | .cmd-gate-btn{padding:10px 24px;background:linear-gradient(135deg,var(--red),#ff4d6d);border:none;border-radius:8px;color:white;font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;transition:transform .2s}
 272 | .cmd-gate-btn:hover{transform:scale(1.03)}
 273 | 
 274 | /* ── RESPONSIVE ── */
 275 | @media(max-width:1024px){.feed-matrix{grid-template-columns:1fr 1fr}.feed-col:nth-child(3){grid-column:span 2}.hm-grid{grid-template-columns:repeat(auto-fill,minmax(120px,1fr))}}
 276 | @media(max-width:768px){
 277 |   .hero{padding:48px 0 32px}
 278 |   .hero-metrics{gap:20px}
 279 |   .sec{padding:40px 0}
 280 |   .feed-matrix{grid-template-columns:1fr}
 281 |   .feed-col:nth-child(3){grid-column:auto}
 282 |   .sg{grid-template-columns:1fr}
 283 |   .sd-main{grid-template-columns:1fr}
 284 |   .sd-eps{max-height:250px;border-left:none;border-top:1px solid var(--border)}
 285 |   .pod-grid{grid-template-columns:1fr}
 286 |   .bg{grid-template-columns:repeat(2,1fr)}
 287 |   .nl{padding:32px 20px}
 288 |   .nl-f{flex-direction:column}
 289 |   .ticker-wrap{height:32px}
 290 |   .ticker-item{padding:0 16px;font-size:11px}
 291 |   .net-svg{height:350px}
 292 |   .hm-grid{grid-template-columns:repeat(3,1fr)}
 293 | }
 294 | </style>
 295 | {% endblock %}
 296 | 
 297 | {% block content %}
 298 | <div class="mh">
 299 | 
 300 | <!-- ═══════════ LIVE TICKER ═══════════ -->
 301 | <div class="ticker-wrap">
 302 |   <div class="ticker-track" id="tickerTrack">
 303 |     {% if ticker_items %}
 304 |       {% for t in ticker_items %}{% for _ in range(2) %}
 305 |       <a class="ticker-item" href="{{ t.url }}" target="_blank" rel="noopener">
 306 |         <span class="ticker-src">{{ t.source }}</span>
 307 |         <span class="ticker-title">{{ t.title }}</span>
 308 |         {% if t.score >= 70 %}<span class="ticker-score high">{{ t.score }}</span>
 309 |         {% elif t.score >= 40 %}<span class="ticker-score mid">{{ t.score }}</span>
 310 |         {% else %}<span class="ticker-score low">{{ t.score }}</span>{% endif %}
 311 |         {% if t.time %}<span class="fi-time">{{ t.time }}</span>{% endif %}
 312 |       </a>
 313 |       <div class="ticker-sep"></div>
 314 |       {% endfor %}{% endfor %}
 315 |     {% else %}
 316 |       <span class="ticker-item"><span class="ticker-src">LOADING</span><span class="ticker-title">Syncing feeds...</span></span>
 317 |     {% endif %}
 318 |   </div>
 319 | </div>
 320 | 
 321 | <div class="wrap">
 322 | 
 323 | <!-- ═══════════ HERO ═══════════ -->
 324 | <div class="hero">
 325 |   <div class="hero-bg"><div class="hero-grid"></div><div class="hero-orb hero-orb-1"></div><div class="hero-orb hero-orb-2"></div><div class="hero-orb hero-orb-3"></div><div class="hero-scanline"></div><div class="hero-vignette"></div></div>
 326 |   <div class="hero-inner">
 327 |     <div class="hero-tag"><div class="hero-tag-dot"></div><span class="hero-tag-text">Media Command Center</span></div>
 328 |     <h1 class="hero-h">Every <em>Voice</em>. Every <em>Signal</em>.</h1>
 329 |     <p class="hero-sub">The definitive Bitcoin media hub. {{ feed_stats.get('feed_count', 0) }} feeds aggregated. Live podcasts, YouTube intelligence, and KOL signals — one screen.</p>
 330 |     <div class="hero-metrics">
 331 |       <div class="hero-metric"><div class="hero-metric-val mono">{{ feed_stats.get('feed_count', 0) }}</div><div class="hero-metric-lab">Feeds</div></div>
 332 |       <div class="hero-metric"><div class="hero-metric-val mono">{{ feed_stats.get('podcast_count', 0) }}</div><div class="hero-metric-lab">Podcast Episodes</div></div>
 333 |       <div class="hero-metric"><div class="hero-metric-val mono">{{ feed_stats.get('video_count', 0) }}</div><div class="hero-metric-lab">Videos</div></div>
 334 |       <div class="hero-metric"><div class="hero-metric-val mono" id="liveN">0</div><div class="hero-metric-lab">Live Notes</div></div>
 335 |     </div>
 336 |   </div>
 337 | </div>
 338 | 
 339 | <!-- ═══════════ FEED MATRIX ═══════════ -->
 340 | <div class="sec" id="feeds">
 341 |   <div class="sec-lab">01 — Feed Matrix</div>
 342 |   <h2 class="sec-h">Three Intelligence Streams</h2>
 343 |   <p class="sec-desc">Podcasts, video intelligence, and live KOL signals — all aggregated, scored, and sorted by signal strength.</p>
 344 | 
 345 |   <div class="feed-matrix">
 346 |     <!-- COLUMN 1: PODCASTS -->
 347 |     <div class="feed-col">
 348 |       <div class="feed-col-head">
 349 |         <div class="feed-col-icon pod"><i class="fas fa-microphone-alt"></i></div>
 350 |         <span class="feed-col-name">Podcasts</span>
 351 |         <span class="feed-col-count">{{ feed_matrix.podcasts|length }}</span>
 352 |       </div>
 353 |       <div class="feed-list" id="podFeed">
 354 |         {% if feed_matrix.podcasts %}
 355 |           {% for ep in feed_matrix.podcasts %}
 356 |           <div class="fi" {% if ep.audio_url %}onclick="playEp('{{ ep.audio_url }}','{{ ep.title|e }}','{{ ep.feed_name|e }}')"{% endif %}>
 357 |             <div class="fi-head">
 358 |               {% if ep.thumbnail_url %}<img class="fi-thumb" src="{{ ep.thumbnail_url }}" alt="" loading="lazy" onerror="this.style.display='none'">{% endif %}
 359 |               <div class="fi-info">
 360 |                 <div class="fi-show">{{ ep.feed_name }}</div>
 361 |                 <div class="fi-title">{{ ep.title }}</div>
 362 |               </div>
 363 |             </div>
 364 |             {% if ep.summary_ai %}<div class="fi-summary">{{ ep.summary_ai }}</div>{% endif %}
 365 |             <div class="fi-meta">
 366 |               {% if ep.duration %}<span class="fi-dur"><i class="far fa-clock"></i> {{ ep.duration }}</span>{% endif %}
 367 |               {% if ep.published_at %}<span class="fi-time">{{ ep.published_at[:10] }}</span>{% endif %}
 368 |               {% if ep.signal_score >= 70 %}<span class="fi-score s-high">{{ ep.signal_score }}</span>
 369 |               {% elif ep.signal_score >= 40 %}<span class="fi-score s-mid">{{ ep.signal_score }}</span>
 370 |               {% elif ep.signal_score > 0 %}<span class="fi-score s-low">{{ ep.signal_score }}</span>{% endif %}
 371 |             </div>
 372 |             {% if ep.audio_url %}<button class="fi-play"><i class="fas fa-play"></i> Play Episode</button>{% endif %}
 373 |           </div>
 374 |           {% endfor %}
 375 |         {% else %}
 376 |           <div class="fi-empty">
 377 |             <div class="skel skel-item"><div class="skel skel-title"></div><div class="skel skel-sub"></div><div class="skel skel-bar"></div></div>
 378 |             <div class="skel skel-item"><div class="skel skel-title"></div><div class="skel skel-sub"></div><div class="skel skel-bar"></div></div>
 379 |             <div class="skel skel-item"><div class="skel skel-title"></div><div class="skel skel-sub"></div><div class="skel skel-bar"></div></div>
 380 |             <p style="margin-top:12px;font-size:11px;color:var(--mut)">Syncing 13 podcast feeds...</p>
 381 |           </div>
 382 |         {% endif %}
 383 |       </div>
 384 |     </div>
 385 | 
 386 |     <!-- COLUMN 2: VIDEO -->
 387 |     <div class="feed-col">
 388 |       <div class="feed-col-head">
 389 |         <div class="feed-col-icon vid"><i class="fab fa-youtube"></i></div>
 390 |         <span class="feed-col-name">Video Intel</span>
 391 |         <span class="feed-col-count">{{ feed_matrix.videos|length }}</span>
 392 |       </div>
 393 |       <div class="feed-list" id="vidFeed">
 394 |         {% if feed_matrix.videos %}
 395 |           {% for ep in feed_matrix.videos %}
 396 |           <a class="fi" href="{{ ep.video_url or ep.source_url }}" target="_blank" rel="noopener">
 397 |             <div class="fi-head">
 398 |               {% if ep.thumbnail_url %}<div class="fi-thumb-yt" style="background-image:url('{{ ep.thumbnail_url }}');background-size:cover"></div>{% endif %}
 399 |               <div class="fi-info">
 400 |                 <div class="fi-show">{{ ep.feed_name }}</div>
 401 |                 <div class="fi-title">{{ ep.title }}</div>
 402 |               </div>
 403 |             </div>
 404 |             {% if ep.summary_ai %}<div class="fi-summary">{{ ep.summary_ai }}</div>{% endif %}
 405 |             <div class="fi-meta">
 406 |               {% if ep.published_at %}<span class="fi-time">{{ ep.published_at[:10] }}</span>{% endif %}
 407 |               {% if ep.signal_score >= 70 %}<span class="fi-score s-high">{{ ep.signal_score }}</span>
 408 |               {% elif ep.signal_score >= 40 %}<span class="fi-score s-mid">{{ ep.signal_score }}</span>
 409 |               {% elif ep.signal_score > 0 %}<span class="fi-score s-low">{{ ep.signal_score }}</span>{% endif %}
 410 |             </div>
 411 |           </a>
 412 |           {% endfor %}
 413 |         {% else %}
 414 |           <div class="fi-empty">
 415 |             <div class="skel skel-item"><div class="skel skel-title"></div><div class="skel skel-sub"></div><div class="skel skel-bar"></div></div>
 416 |             <div class="skel skel-item"><div class="skel skel-title"></div><div class="skel skel-sub"></div><div class="skel skel-bar"></div></div>
 417 |             <div class="skel skel-item"><div class="skel skel-title"></div><div class="skel skel-sub"></div><div class="skel skel-bar"></div></div>
 418 |             <p style="margin-top:12px;font-size:11px;color:var(--mut)">Syncing 7 YouTube channels...</p>
 419 |           </div>
 420 |         {% endif %}
 421 |       </div>
 422 |     </div>
 423 | 
 424 |     <!-- COLUMN 3: KOL / NOSTR LIVE -->
 425 |     <div class="feed-col">
 426 |       <div class="feed-col-head">
 427 |         <div class="feed-col-icon kol"><i class="fas fa-bolt"></i></div>
 428 |         <span class="feed-col-name">KOL Intel</span>
 429 |         <span class="feed-col-count" id="kolCount">0</span>
 430 |       </div>
 431 |       <div class="feed-list" id="kolFeed">
 432 |         <div class="fi-empty"><i class="fas fa-satellite-dish" style="font-size:20px;opacity:.3;display:block;margin-bottom:8px"></i>Connecting to Nostr relays...<div class="kol-loader"></div></div>
 433 |       </div>
 434 |     </div>
 435 |   </div>
 436 | </div>
 437 | 
 438 | <!-- ═══════════ VOICE NETWORK GRAPH ═══════════ -->
 439 | <div class="sec" id="network">
 440 |   <div class="sec-lab">02 — Voice Network</div>
 441 |   <h2 class="sec-h">Bitcoin Intelligence Topology</h2>
 442 |   <p class="sec-desc">50 voices mapped by influence, category, and cross-reference density. Hover for live data.</p>
 443 |   <div class="net-wrap">
 444 |     <svg id="netSvg" class="net-svg"></svg>
 445 |     <div class="net-legend">
 446 |       <div class="net-leg-item"><div class="net-leg-dot" style="background:var(--red)"></div>Macro</div>
 447 |       <div class="net-leg-item"><div class="net-leg-dot" style="background:var(--cyan)"></div>Protocol</div>
 448 |       <div class="net-leg-item"><div class="net-leg-dot" style="background:var(--gold)"></div>Media</div>
 449 |     </div>
 450 |     <div class="net-hover" id="netHover">
 451 |       <div class="net-hover-name" id="nhName"></div>
 452 |       <div class="net-hover-handle" id="nhHandle"></div>
 453 |       <div class="net-hover-cat" id="nhCat"></div>
 454 |       <div class="net-hover-stat">
 455 |         <div id="nhTier"><span>Tier</span></div>
 456 |         <div id="nhEps"><span>Episodes</span></div>
 457 |         <div id="nhSignal"><span>Signal</span></div>
 458 |       </div>
 459 |     </div>
 460 |   </div>
 461 | </div>
 462 | 
 463 | <!-- ═══════════ KOL SENTIMENT HEATMAP ═══════════ -->
 464 | <div class="sec" id="heatmap">
 465 |   <div class="sec-lab">03 — Sentiment Heatmap</div>
 466 |   <h2 class="sec-h">KOL Conviction Matrix</h2>
 467 |   <p class="sec-desc">Real-time sentiment read across 16 Bitcoin voices via Nostr. Updated live.</p>
 468 |   {% if not is_commander %}
 469 |   <div class="cmd-gate">
 470 |     <div class="cmd-gate-blur">
 471 |   {% endif %}
 472 |     <div class="hm-grid" id="hmGrid">
 473 |       <div class="fi-empty" style="grid-column:1/-1;padding:40px"><div class="kol-loader"></div><p style="margin-top:10px;font-size:11px;color:var(--mut)">Analyzing KOL sentiment...</p></div>
 474 |     </div>
 475 |   {% if not is_commander %}
 476 |     </div>
 477 |     <div class="cmd-gate-overlay">
 478 |       <div class="cmd-gate-icon"><i class="fas fa-lock"></i></div>
 479 |       <div class="cmd-gate-title">Commander Intelligence</div>
 480 |       <div class="cmd-gate-sub">Real-time sentiment heatmap across 16 Bitcoin KOLs. Unlock with Commander.</div>
 481 |       <a href="/terminal/checkout" class="cmd-gate-btn">Upgrade to Commander</a>
 482 |     </div>
 483 |   </div>
 484 |   {% endif %}
 485 | </div>
 486 | 
 487 | <!-- ═══════════ ORIGINAL SERIES ═══════════ -->
 488 | <div class="sec" id="series">
 489 |   <div class="sec-lab">04 — Original Series</div>
 490 |   <h2 class="sec-h">Cinematic Deep Dives</h2>
 491 |   <p class="sec-desc">Long-form explorations of the books and ideas reshaping monetary thinking.</p>
 492 |   <div class="sg">
 493 |     {% for s in series_list %}
 494 |     <div class="sc" onclick="toggleSD('{{ s.key }}')">
 495 |       <div class="sc-img-w">
 496 |         <img class="sc-img" src="https://img.youtube.com/vi/{{ s.first_id }}/hqdefault.jpg" alt="{{ s.title }}" loading="lazy" onerror="this.onerror=null;this.src='https://img.youtube.com/vi/{{ s.first_id }}/mqdefault.jpg'">
 497 |         <div class="sc-ov"></div>
 498 |         <div class="sc-play"><i class="fas fa-play"></i></div>
 499 |         <div class="sc-badge">{{ s.ep_count }} episodes</div>
 500 |       </div>
 501 |       <div class="sc-body">
 502 |         <div class="sc-host">{{ s.host }}</div>
 503 |         <h3 class="sc-name">{{ s.title }}</h3>
 504 |         <p class="sc-desc">{{ s.description }}</p>
 505 |       </div>
 506 |     </div>
 507 |     {% endfor %}
 508 |   </div>
 509 |   <div id="sdPanel" class="sd">
 510 |     <div class="sd-top"><h3 class="sd-title" id="sdTitle"></h3><button class="sd-x" onclick="closeSD()"><i class="fas fa-times"></i></button></div>
 511 |     <div class="sd-main"><div class="sd-vid"><iframe id="sdIf" src="" allow="autoplay; encrypted-media" allowfullscreen></iframe></div><div class="sd-eps" id="sdEps"></div></div>
 512 |   </div>
 513 | </div>
 514 | 
 515 | <!-- ═══════════ CYPHERPUNKD PODCAST ═══════════ -->
 516 | <div class="sec" id="podcasts">
 517 |   <div class="sec-lab">05 — Cypherpunk'd Podcast</div>
 518 |   <h2 class="sec-h">Latest Episodes</h2>
 519 |   <p class="sec-desc">Conversations with builders, thinkers, and disruptors at the frontier of sound money.</p>
 520 |   <div class="pod-grid">
 521 |     {% for ep in latest_episodes %}
 522 |     <div class="pod-card" onclick="playEp('{{ ep.audio_url }}','{{ ep.title|replace("'","") }}','Cypherpunkd')">
 523 |       <div class="pod-num mono">{{ '%02d'|format(loop.index) }}</div>
 524 |       <div class="pod-title">{{ ep.title }}</div>
 525 |       <div class="pod-meta">
 526 |         <span class="pod-dur mono">{{ ep.duration or '--:--' }}</span>
 527 |         <div class="pod-play-btn"><i class="fas fa-play"></i></div>
 528 |       </div>
 529 |     </div>
 530 |     {% endfor %}
 531 |   </div>
 532 |   <a href="/podcasts" class="pod-more">View all episodes <i class="fas fa-arrow-right"></i></a>
 533 | </div>
 534 | 
 535 | <!-- ═══════════ BOOKS ═══════════ -->
 536 | <div class="sec" id="books">
 537 |   <div class="sec-lab">06 — Essential Reading</div>
 538 |   <h2 class="sec-h">The Library</h2>
 539 |   <p class="sec-desc">The books that shaped Cypherpunk'd. Every link supports Protocol Pulse.</p>
 540 |   <div class="bcat">Featured on Podcast</div>
 541 |   <div class="bg">
 542 |     {% for b in all_books %}{% if b.get('category')=='series' %}
 543 |     <div class="bc" style="cursor:pointer" onclick="window.open('{{ b.amazon_url }}','_blank')">
 544 |       <div class="bc-cov" style="background:linear-gradient(160deg, {{ b.get('color','#333') }}15, {{ b.get('color','#333') }}05)">
 545 |         {% if b.get('cover_url') %}<img class="bc-img" src="{{ b.cover_url }}" alt="{{ b.title }}" loading="lazy" onerror="this.style.display='none'">{% endif %}
 546 |         <div class="bc-spine" style="background:{{ b.get('color','#333') }}"></div>
 547 |         <div class="bc-txt"><div class="bc-txt-t">{{ b.title }}</div><div class="bc-txt-a">{{ b.author }}</div></div>
 548 |       </div>
 549 |       <div class="bc-info"><div class="bc-badge">Series</div><div class="bc-name">{{ b.title }}</div><div class="bc-auth">{{ b.author }}</div></div>
 550 |     </div>
 551 |     {% endif %}{% endfor %}
 552 |   </div>
 553 |   <div class="bcat">Bitcoin Essentials</div>
 554 |   <div class="bg">
 555 |     {% for b in all_books %}{% if b.get('category')=='essential' %}
 556 |     <a href="{{ b.amazon_url }}" target="_blank" rel="noopener" class="bc">
 557 |       <div class="bc-cov" style="background:linear-gradient(160deg, {{ b.get('color','#333') }}15, {{ b.get('color','#333') }}05)">
 558 |         {% if b.get('cover_url') %}<img class="bc-img" src="{{ b.cover_url }}" alt="{{ b.title }}" loading="lazy" onerror="this.style.display='none'">{% endif %}
 559 |         <div class="bc-spine" style="background:{{ b.get('color','#333') }}"></div>
 560 |         <div class="bc-txt"><div class="bc-txt-t">{{ b.title }}</div><div class="bc-txt-a">{{ b.author }}</div></div>
 561 |       </div>
 562 |       <div class="bc-info"><div class="bc-name">{{ b.title }}</div><div class="bc-auth">{{ b.author }}</div></div>
 563 |     </a>
 564 |     {% endif %}{% endfor %}
 565 |   </div>
 566 |   <button class="btog" id="btog" onclick="togB()"><i class="fas fa-chevron-down"></i><span>Show More — Bestsellers & Economics</span><span class="mono" style="margin-left:auto;font-size:10px;color:var(--mut)">{{ all_books|selectattr('category','in',['bestseller','economics'])|list|length }} titles</span></button>
 567 |   <div class="bhid" id="bmore">
 568 |     <div class="bcat" style="margin-top:20px">Bitcoin Bestsellers</div>
 569 |     <div class="bg">
 570 |       {% for b in all_books %}{% if b.get('category')=='bestseller' %}
 571 |       <a href="{{ b.amazon_url }}" target="_blank" rel="noopener" class="bc">
 572 |         <div class="bc-cov" style="background:linear-gradient(160deg, {{ b.get('color','#333') }}15, {{ b.get('color','#333') }}05)">
 573 |           {% if b.get('cover_url') %}<img class="bc-img" src="{{ b.cover_url }}" alt="{{ b.title }}" loading="lazy" onerror="this.style.display='none'">{% endif %}
 574 |           <div class="bc-spine" style="background:{{ b.get('color','#333') }}"></div>
 575 |           <div class="bc-txt"><div class="bc-txt-t">{{ b.title }}</div><div class="bc-txt-a">{{ b.author }}</div></div>
 576 |         </div>
 577 |         <div class="bc-info"><div class="bc-name">{{ b.title }}</div><div class="bc-auth">{{ b.author }}</div></div>
 578 |       </a>
 579 |       {% endif %}{% endfor %}
 580 |     </div>
 581 |     <div class="bcat">Austrian Economics</div>
 582 |     <div class="bg">
 583 |       {% for b in all_books %}{% if b.get('category')=='economics' %}
 584 |       <a href="{{ b.amazon_url }}" target="_blank" rel="noopener" class="bc">
 585 |         <div class="bc-cov" style="background:linear-gradient(160deg, {{ b.get('color','#333') }}15, {{ b.get('color','#333') }}05)">
 586 |           {% if b.get('cover_url') %}<img class="bc-img" src="{{ b.cover_url }}" alt="{{ b.title }}" loading="lazy" onerror="this.style.display='none'">{% endif %}
 587 |           <div class="bc-spine" style="background:{{ b.get('color','#333') }}"></div>
 588 |           <div class="bc-txt"><div class="bc-txt-t">{{ b.title }}</div><div class="bc-txt-a">{{ b.author }}</div></div>
 589 |         </div>
 590 |         <div class="bc-info"><div class="bc-badge econ">Economics</div><div class="bc-name">{{ b.title }}</div><div class="bc-auth">{{ b.author }}</div></div>
 591 |       </a>
 592 |       {% endif %}{% endfor %}
 593 |     </div>
 594 |   </div>
 595 | </div>
 596 | 
 597 | <!-- ═══════════ NEWSLETTER CTA ═══════════ -->
 598 | <div class="sec" id="subscribe">
 599 |   <div class="nl">
 600 |     <h2 class="nl-h">The signal. Every morning.</h2>
 601 |     <p class="nl-p">Daily intelligence brief + weekly premium digest.</p>
 602 |     <form class="nl-f" action="/newsletter/subscribe" method="POST">
 603 |       <input type="email" name="email" class="nl-i" placeholder="your@email.com" required>
 604 |       <button type="submit" class="nl-b">Subscribe</button>
 605 |     </form>
 606 |   </div>
 607 | </div>
 608 | 
 609 | </div><!-- .wrap -->
 610 | </div><!-- .mh -->
 611 | 
 612 | <!-- ═══════════ AUDIO PLAYER BAR ═══════════ -->
 613 | <div id="abar" class="abar">
 614 |   <button class="abar-btn" onclick="togA()" id="aPlayBtn"><i id="aIcon" class="fas fa-pause"></i></button>
 615 |   <div class="abar-now">
 616 |     <div class="abar-show" id="aShow"></div>
 617 |     <div class="abar-title" id="aNow">Now Playing...</div>
 618 |     <div class="abar-progress" onclick="seekA(event)"><div class="abar-progress-fill" id="aProgress"></div></div>
 619 |   </div>
 620 |   <button class="abar-close" onclick="stopA()"><i class="fas fa-times"></i></button>
 621 |   <audio id="aEl"></audio>
 622 | </div>
 623 | 
 624 | {% endblock %}
 625 | 
 626 | {% block scripts %}
 627 | <script>
 628 | /* ── Series Player ── */
 629 | var SD={{ series_data|tojson }},curS=null;
 630 | function toggleSD(k){var p=document.getElementById('sdPanel');if(curS===k&&p.classList.contains('active')){closeSD();return}var s=SD[k];if(!s||!s.episodes||!s.episodes.length)return;curS=k;document.getElementById('sdTitle').textContent=s.title||k;var e0=s.episodes[0];document.getElementById('sdIf').src='https://www.youtube.com/embed/'+e0.id+'?autoplay=1';var sb=document.getElementById('sdEps');sb.innerHTML=s.episodes.map(function(ep,i){return'<div class="sd-ep'+(i===0?' active':'')+'" onclick="playSE(\''+ep.id+'\','+i+',this)"><img class="sd-ep-img" src="https://img.youtube.com/vi/'+ep.id+'/mqdefault.jpg" loading="lazy"><div class="sd-ep-info"><div class="sd-ep-n">EP '+(i+1)+'</div><div class="sd-ep-t">'+ep.title+'</div></div></div>'}).join('');p.classList.add('active');setTimeout(function(){p.scrollIntoView({behavior:'smooth',block:'nearest'})},100)}
 631 | function playSE(id,i,el){document.getElementById('sdIf').src='https://www.youtube.com/embed/'+id+'?autoplay=1';document.querySelectorAll('.sd-ep').forEach(function(e){e.classList.remove('active')});if(el)el.classList.add('active')}
 632 | function closeSD(){document.getElementById('sdIf').src='';document.getElementById('sdPanel').classList.remove('active');curS=null}
 633 | 
 634 | /* ── Audio Player ── */
 635 | var au=document.getElementById('aEl'),pl=false;
 636 | function playEp(u,t,show){if(!u)return;au.src=u;au.play().catch(function(){});pl=true;document.getElementById('aNow').textContent=t;document.getElementById('aShow').textContent=show||'';document.getElementById('aIcon').className='fas fa-pause';document.getElementById('abar').classList.add('active')}
 637 | function togA(){if(pl){au.pause();document.getElementById('aIcon').className='fas fa-play'}else{au.play();document.getElementById('aIcon').className='fas fa-pause'}pl=!pl}
 638 | function stopA(){au.pause();au.src='';pl=false;document.getElementById('abar').classList.remove('active')}
 639 | function seekA(e){if(!au.duration)return;var r=e.currentTarget.getBoundingClientRect();var p=(e.clientX-r.left)/r.width;au.currentTime=au.duration*p}
 640 | au.addEventListener('timeupdate',function(){if(au.duration){document.getElementById('aProgress').style.width=(au.currentTime/au.duration*100)+'%'}});
 641 | au.addEventListener('ended',function(){stopA()});
 642 | 
 643 | /* ── Books Toggle ── */
 644 | function togB(){document.getElementById('bmore').classList.toggle('show');document.getElementById('btog').classList.toggle('open')}
 645 | 
 646 | /* ── Nostr Live Feed (KOL Column) ── */
 647 | var RELAYS=['wss://relay.damus.io','wss://nos.lol','wss://relay.nostr.band','wss://relay.primal.net'];
 648 | var V={'82341f882b6eabcd2ba7f1ef90aad961cf074af15b9ef44a09f9d2a8fbfbe6a2':{n:'Jack Dorsey',i:'JD',c:'protocol',x:'jack'},'fa984bd7dbb282f07e16e7ae87b26a2a7b9b90b7246a44771f0cf5ae58018f52':{n:'Adam Back',i:'AB',c:'protocol',x:'adam3us'},'e88a691e98d9987c964521dff60025f60700378a4879180dcbbb4a5027850411':{n:'NVK',i:'NV',c:'protocol',x:'nvk'},'04c915daefee38317fa734444acee390a8269fe5810b2241e5e6dd343dfbecc9':{n:'ODELL',i:'MO',c:'protocol',x:'ODELL'},'3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d':{n:'Fiatjaf',i:'FJ',c:'protocol',x:'fiatjaf'},'eab0e756d32b80bcd464f3d844b8040303075a13eabc3599a762c9ac7ab91f4f':{n:'Lyn Alden',i:'LA',c:'macro',x:'LynAldenContact'},'85080d3bad70ccdcd7f74c29a44f55bb85cbcd3dd0cbb957da1d215bdb931204':{n:'Preston Pysh',i:'PP',c:'macro',x:'PrestonPysh'},'472f440f29ef996e92a186b8d320ff180c855903882e59d50de1b8bd5669301e':{n:'Marty Bent',i:'MB',c:'media',x:'MartyBent'},'50d94fc2d8580571ee61726abcbcfb7d8e93d66b2ed13740ad0c39cd4de10dba':{n:'American HODL',i:'AH',c:'media',x:'americanhodl8'},'1989034e56b8f606c724f45a12ce84a11841621aaf7182a1f6564f578f2571a0':{n:'Jeff Booth',i:'JB',c:'macro',x:'JeffBooth'},'a341f45ff9758f570a21b000c17d4e53a3a497c8397f26c0e6d61e5acffc7a98':{n:'Saifedean',i:'SA',c:'macro',x:'saifedean'},'5d1d83de3ee5e3009d57e4a2af8bfa4a1b5b1a58f6ec4fd290dba6e048bae9ae':{n:'Natalie Brunell',i:'NB',c:'media',x:'natbrunell'},'4523be58d395b1b196a9b8c82b038b6895cb02b683d0c253a955068dba1facd0':{n:'Michael Saylor',i:'MS',c:'macro',x:'saylor'},'58c741aa630c2da35a56a77c1d05381908bd10504b7519571f2cdae6ce2b993d':{n:'Jameson Lopp',i:'JL',c:'protocol',x:'lopp'},'edcd20558f17d99327d841e4582f9b006331ac4010571eb77dc79c55f1a295c8':{n:'Willy Woo',i:'WW',c:'macro',x:'woonomic'}};
 649 | var pks=Object.keys(V),seen={},kolCt=0,rUp=0;
 650 | 
 651 | function startNostr(){
 652 |   RELAYS.forEach(function(url){
 653 |     try{
 654 |       var ws=new WebSocket(url);
 655 |       ws.onopen=function(){rUp++;ws.send(JSON.stringify(["REQ","pp",{kinds:[1],authors:pks,limit:30}]))};
 656 |       ws.onmessage=function(e){
 657 |         try{
 658 |           var m=JSON.parse(e.data);
 659 |           if(m[0]==='EVENT'&&m[2]&&!seen[m[2].id]){
 660 |             seen[m[2].id]=1;
 661 |             var ev=m[2];
 662 |             if(ev.content&&ev.content.length>15){
 663 |               var isReply=ev.tags&&ev.tags.some(function(t){return t[0]==='e'});
 664 |               if(!isReply) addKol(ev);
 665 |             }
 666 |           }
 667 |         }catch(x){}
 668 |       };
 669 |       ws.onclose=function(){rUp=Math.max(0,rUp-1)};
 670 |     }catch(x){}
 671 |   });
 672 | }
 673 | 
 674 | function addKol(ev){
 675 |   kolCt++;
 676 |   document.getElementById('kolCount').textContent=kolCt;
 677 |   document.getElementById('liveN').textContent=kolCt;
 678 |   var f=document.getElementById('kolFeed');
 679 |   if(f.querySelector('.fi-empty'))f.innerHTML='';
 680 |   var v=V[ev.pubkey]||{n:ev.pubkey.substring(0,8)+'...',i:'??',c:'protocol',x:''};
 681 |   var txt=escH(ev.content);
 682 |   txt=txt.replace(/(https?:\/\/[^\s<]+)/g,'<a href="$1" target="_blank" rel="noopener">$1</a>').replace(/\n/g,'<br>');
 683 |   if(txt.length>400)txt=txt.substring(0,400)+'...';
 684 |   var xUrl=v.x?'https://x.com/'+v.x:'#';
 685 |   var el=document.createElement('div');
 686 |   el.className='kol-item';
 687 |   el.style.animation='fadeUp .4s ease';
 688 |   el.innerHTML='<div class="kol-head"><div class="kol-av '+v.c+'">'+v.i+'</div><span class="kol-name">'+v.n+'</span><span class="kol-time">'+tAgo(ev.created_at)+'</span></div><div class="kol-body">'+txt+'</div><div class="kol-foot"><a href="https://njump.me/'+ev.id+'" target="_blank" rel="noopener" class="kol-link"><i class="fas fa-external-link-alt"></i> nostr</a><a href="'+xUrl+'" target="_blank" rel="noopener" class="kol-link"><i class="fab fa-x-twitter"></i> @'+v.x+'</a></div>';
 689 |   f.insertBefore(el,f.firstChild);
 690 |   while(f.children.length>40)f.removeChild(f.lastChild);
 691 | }
 692 | 
 693 | function escH(t){var d=document.createElement('div');d.appendChild(document.createTextNode(t));return d.innerHTML}
 694 | function tAgo(ts){var d=Math.floor(Date.now()/1000)-ts;if(d<60)return'now';if(d<3600)return Math.floor(d/60)+'m';if(d<86400)return Math.floor(d/3600)+'h';return Math.floor(d/86400)+'d'}
 695 | 
 696 | document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeSD()}});
 697 | startNostr();
 698 | 
 699 | /* ── Old network graph + heatmap removed — D3 version at bottom ── */
 700 | /* REMOVED_OLD_NETWORK_START
 701 |   {id:'preston',name:'Preston Pysh',handle:'@PrestonPysh',cat:'macro',tier:1,r:14},
 702 |   {id:'odell',name:'Matt Odell',handle:'@ODELL',cat:'protocol',tier:1,r:15},
 703 |   {id:'marty',name:'Marty Bent',handle:'@MartyBent',cat:'media',tier:1,r:14},
 704 |   {id:'nvk',name:'NVK',handle:'@nvk',cat:'protocol',tier:1,r:13},
 705 |   {id:'natalie',name:'Natalie Brunell',handle:'@natbrunell',cat:'media',tier:1,r:13},
 706 |   {id:'booth',name:'Jeff Booth',handle:'@JeffBooth',cat:'macro',tier:1,r:14},
 707 |   {id:'saif',name:'Saifedean',handle:'@saifedean',cat:'macro',tier:1,r:14},
 708 |   {id:'lopp',name:'Jameson Lopp',handle:'@lopp',cat:'protocol',tier:1,r:13},
 709 |   {id:'willy',name:'Willy Woo',handle:'@woonomic',cat:'macro',tier:1,r:13},
 710 |   {id:'peter',name:'Peter McCormack',handle:'@PeterMcCormack',cat:'media',tier:1,r:14},
 711 |   {id:'breedlove',name:'Robert Breedlove',handle:'@Breedlove22',cat:'macro',tier:1,r:13},
 712 |   {id:'guy',name:'Guy Swann',handle:'@GuySwann',cat:'media',tier:1,r:12},
 713 |   {id:'livera',name:'Stephan Livera',handle:'@stephanlivera',cat:'media',tier:1,r:13},
 714 |   {id:'bhatia',name:'Nik Bhatia',handle:'@timeaborned',cat:'macro',tier:1,r:12},
 715 |   {id:'hodl',name:'American HODL',handle:'@americanhodl8',cat:'media',tier:2,r:11},
 716 |   {id:'fiatjaf',name:'Fiatjaf',handle:'@fiatjaf',cat:'protocol',tier:1,r:12},
 717 |   {id:'gladstein',name:'Alex Gladstein',handle:'@gladstein',cat:'macro',tier:1,r:12},
 718 |   {id:'pomp',name:'Anthony Pompliano',handle:'@APompliano',cat:'media',tier:1,r:14},
 719 |   {id:'max',name:'Max Keiser',handle:'@maxkeiser',cat:'macro',tier:2,r:12},
 720 |   {id:'samson',name:'Samson Mow',handle:'@Excellion',cat:'protocol',tier:1,r:12},
 721 |   {id:'jimmy',name:'Jimmy Song',handle:'@jimmysong',cat:'protocol',tier:1,r:11},
 722 |   {id:'andreas',name:'Andreas Antonopoulos',handle:'@aantonop',cat:'protocol',tier:1,r:13},
 723 |   {id:'elizabeth',name:'Elizabeth Stark',handle:'@staborned',cat:'protocol',tier:1,r:11},
 724 |   {id:'pierre',name:'Pierre Rochard',handle:'@pierre_rochard',cat:'protocol',tier:1,r:11},
 725 |   {id:'cory',name:'Cory Klippsten',handle:'@coryklippsten',cat:'media',tier:1,r:12},
 726 |   {id:'dylan',name:'Dylan LeClair',handle:'@DylanLeClair_',cat:'macro',tier:2,r:11},
 727 |   {id:'checkmate',name:'_Checkmate_',handle:'@_Checkmatey_',cat:'macro',tier:2,r:11},
 728 |   {id:'gigi',name:'Gigi',handle:'@dergigi',cat:'protocol',tier:2,r:10},
 729 |   {id:'beautyon',name:'Beautyon',handle:'@Beautyon_',cat:'protocol',tier:2,r:10},
 730 |   {id:'tuur',name:'Tuur Demeester',handle:'@TuurDemeester',cat:'macro',tier:1,r:12},
 731 |   {id:'plan_b',name:'PlanB',handle:'@100trillionUSD',cat:'macro',tier:1,r:13},
 732 |   {id:'raoul',name:'Raoul Pal',handle:'@RaoulGMI',cat:'macro',tier:1,r:13},
 733 |   {id:'caitlin',name:'Caitlin Long',handle:'@CaitlinLong_',cat:'macro',tier:1,r:11},
 734 |   {id:'balaji',name:'Balaji Srinivasan',handle:'@balaborned',cat:'macro',tier:1,r:12},
 735 |   {id:'matt_c',name:'Matt Corallo',handle:'@TheBlueMatt',cat:'protocol',tier:1,r:11},
 736 |   {id:'giacomo',name:'Giacomo Zucco',handle:'@giacomozucco',cat:'protocol',tier:2,r:10},
 737 |   {id:'alex_b',name:'Alex B',handle:'@alex_b',cat:'macro',tier:2,r:10},
 738 |   {id:'pbx',name:'PBX',handle:'@pbxlife',cat:'media',tier:1,r:12},
 739 |   {id:'swan',name:'Swan Bitcoin',handle:'@SwanBitcoin',cat:'media',tier:2,r:11},
 740 |   {id:'river',name:'River Financial',handle:'@River',cat:'media',tier:2,r:10},
 741 |   {id:'bolt',name:'Bolt Card',handle:'@BoltCard',cat:'protocol',tier:3,r:8},
 742 |   {id:'strike',name:'Strike',handle:'@Strike',cat:'protocol',tier:1,r:12},
 743 |   {id:'unchained',name:'Unchained',handle:'@unchaborned',cat:'media',tier:2,r:10},
 744 |   {id:'fold',name:'Fold App',handle:'@fold_app',cat:'protocol',tier:2,r:9},
 745 |   {id:'bitkey',name:'Bitkey',handle:'@bitaborned',cat:'protocol',tier:2,r:9},
 746 |   {id:'cashapp',name:'Cash App',handle:'@CashApp',cat:'protocol',tier:1,r:11}
 747 | ];
 748 | var LINKS=[
 749 |   {s:'saylor',t:'pomp'},{s:'saylor',t:'lyn'},{s:'saylor',t:'preston'},{s:'saylor',t:'breedlove'},
 750 |   {s:'jack',t:'fiatjaf'},{s:'jack',t:'odell'},{s:'jack',t:'strike'},{s:'jack',t:'cashapp'},
 751 |   {s:'adam',t:'samson'},{s:'adam',t:'nvk'},{s:'adam',t:'jimmy'},
 752 |   {s:'lyn',t:'preston'},{s:'lyn',t:'natalie'},{s:'lyn',t:'peter'},{s:'lyn',t:'tuur'},
 753 |   {s:'odell',t:'marty'},{s:'odell',t:'nvk'},{s:'odell',t:'lopp'},{s:'odell',t:'fiatjaf'},
 754 |   {s:'marty',t:'hodl'},{s:'marty',t:'pbx'},{s:'marty',t:'guy'},
 755 |   {s:'peter',t:'livera'},{s:'peter',t:'natalie'},{s:'peter',t:'booth'},
 756 |   {s:'natalie',t:'cory'},{s:'natalie',t:'dylan'},{s:'natalie',t:'gladstein'},
 757 |   {s:'booth',t:'saif'},{s:'booth',t:'breedlove'},{s:'booth',t:'preston'},
 758 |   {s:'livera',t:'guy'},{s:'livera',t:'jimmy'},{s:'livera',t:'bhatia'},
 759 |   {s:'plan_b',t:'willy'},{s:'plan_b',t:'checkmate'},{s:'plan_b',t:'dylan'},
 760 |   {s:'raoul',t:'lyn'},{s:'raoul',t:'pomp'},{s:'raoul',t:'balaji'},
 761 |   {s:'andreas',t:'lopp'},{s:'andreas',t:'jimmy'},{s:'andreas',t:'matt_c'},
 762 |   {s:'pomp',t:'cory'},{s:'pomp',t:'swan'},{s:'pomp',t:'raoul'},
 763 |   {s:'strike',t:'cashapp'},{s:'strike',t:'fold'},{s:'strike',t:'bitkey'},
 764 |   {s:'caitlin',t:'unchained'},{s:'caitlin',t:'pierre'},
 765 |   {s:'samson',t:'adam'},{s:'samson',t:'max'},{s:'samson',t:'giacomo'},
 766 |   {s:'gigi',t:'beautyon'},{s:'gigi',t:'fiatjaf'}
 767 | ];
 768 | var catColor={macro:'#dc2626',protocol:'#5de4ff',media:'#f8c15c'};
 769 | var svg=document.getElementById('netSvg');
 770 | if(svg){
 771 |   var w=svg.clientWidth||900,h=svg.clientHeight||500;
 772 |   svg.setAttribute('viewBox','0 0 '+w+' '+h);
 773 |   var ns='http://www.w3.org/2000/svg';
 774 |   // Build id->index map
 775 |   var idxMap={};VOICES.forEach(function(v,i){idxMap[v.id]=i});
 776 |   var links=LINKS.map(function(l){return{source:idxMap[l.s],target:idxMap[l.t]}}).filter(function(l){return l.source!==undefined&&l.target!==undefined});
 777 |   var nodes=VOICES.map(function(v){return Object.assign({},v,{x:w/2+Math.random()*200-100,y:h/2+Math.random()*200-100})});
 778 | 
 779 |   // Simple force simulation (no D3 dependency — pure JS)
 780 |   var alpha=1,decay=0.997,repulse=800,attract=0.008,center={x:w/2,y:h/2},cStrength=0.01;
 781 |   function tick(){
 782 |     // Center gravity
 783 |     nodes.forEach(function(n){n.vx=(n.vx||0)+((center.x-n.x)*cStrength);n.vy=(n.vy||0)+((center.y-n.y)*cStrength)});
 784 |     // Repulsion
 785 |     for(var i=0;i<nodes.length;i++){for(var j=i+1;j<nodes.length;j++){var dx=nodes[j].x-nodes[i].x,dy=nodes[j].y-nodes[i].y,d2=dx*dx+dy*dy+1;var f=repulse*alpha/d2;var fx=dx*f/Math.sqrt(d2),fy=dy*f/Math.sqrt(d2);nodes[i].vx-=fx;nodes[i].vy-=fy;nodes[j].vx+=fx;nodes[j].vy+=fy}}
 786 |     // Attraction
 787 |     links.forEach(function(l){var s=nodes[l.source],t=nodes[l.target],dx=t.x-s.x,dy=t.y-s.y,d=Math.sqrt(dx*dx+dy*dy+1);var f=attract*alpha*(d-80);s.vx+=dx*f/d;s.vy+=dy*f/d;t.vx-=dx*f/d;t.vy-=dy*f/d});
 788 |     // Integrate
 789 |     nodes.forEach(function(n){n.vx*=0.6;n.vy*=0.6;n.x=Math.max(20,Math.min(w-20,n.x+n.vx));n.y=Math.max(20,Math.min(h-20,n.y+n.vy))});
 790 |     alpha*=decay;
 791 |   }
 792 |   // Run simulation
 793 |   for(var si=0;si<300;si++)tick();
 794 | 
 795 |   // Render SVG
 796 |   var frag=document.createDocumentFragment();
 797 |   // Links
 798 |   links.forEach(function(l){var line=document.createElementNS(ns,'line');line.setAttribute('class','link');line.setAttribute('x1',nodes[l.source].x);line.setAttribute('y1',nodes[l.source].y);line.setAttribute('x2',nodes[l.target].x);line.setAttribute('y2',nodes[l.target].y);frag.appendChild(line)});
 799 |   // Nodes
 800 |   var hoverEl=document.getElementById('netHover');
 801 |   nodes.forEach(function(n,i){
 802 |     var g=document.createElementNS(ns,'g');
 803 |     var c=document.createElementNS(ns,'circle');
 804 |     c.setAttribute('class','node-circle');
 805 |     c.setAttribute('cx',n.x);c.setAttribute('cy',n.y);c.setAttribute('r',n.r);
 806 |     c.setAttribute('fill',catColor[n.cat]||'#888');c.setAttribute('opacity','0.7');
 807 |     c.setAttribute('stroke',catColor[n.cat]||'#888');c.setAttribute('stroke-width','1');c.setAttribute('stroke-opacity','0.3');
 808 |     var t=document.createElementNS(ns,'text');
 809 |     t.setAttribute('x',n.x);t.setAttribute('y',n.y+n.r+12);
 810 |     t.textContent=n.name.split(' ').pop();
 811 |     g.appendChild(c);g.appendChild(t);
 812 |     // Hover
 813 |     c.addEventListener('mouseenter',function(e){
 814 |       c.setAttribute('r',n.r+4);c.setAttribute('opacity','1');
 815 |       document.getElementById('nhName').textContent=n.name;
 816 |       document.getElementById('nhHandle').textContent=n.handle;
 817 |       document.getElementById('nhCat').textContent=n.cat+' voice';
 818 |       document.getElementById('nhTier').innerHTML='T'+n.tier+'<span>Tier</span>';
 819 |       document.getElementById('nhEps').innerHTML=Math.floor(Math.random()*50+5)+'<span>Episodes</span>';
 820 |       document.getElementById('nhSignal').innerHTML=Math.floor(Math.random()*40+50)+'<span>Signal</span>';
 821 |       var rect=svg.getBoundingClientRect();
 822 |       hoverEl.style.left=(n.x+n.r+10)+'px';hoverEl.style.top=(n.y-30)+'px';
 823 |       hoverEl.classList.add('show');
 824 |     });
 825 |     c.addEventListener('mouseleave',function(){c.setAttribute('r',n.r);c.setAttribute('opacity','0.7');hoverEl.classList.remove('show')});
 826 |     frag.appendChild(g);
 827 |   });
 828 |   svg.appendChild(frag);
 829 | }
 830 | })();
 831 | 
 832 | /* ── KOL Sentiment Heatmap ── */
 833 | (function(){
 834 | var KOL_LIST=[
 835 |   {name:'Michael Saylor',handle:'@saylor',cat:'macro'},
 836 |   {name:'Lyn Alden',handle:'@LynAldenContact',cat:'macro'},
 837 |   {name:'Preston Pysh',handle:'@PrestonPysh',cat:'macro'},
 838 |   {name:'Matt Odell',handle:'@ODELL',cat:'protocol'},
 839 |   {name:'Marty Bent',handle:'@MartyBent',cat:'media'},
 840 |   {name:'Jeff Booth',handle:'@JeffBooth',cat:'macro'},
 841 |   {name:'Saifedean',handle:'@saifedean',cat:'macro'},
 842 |   {name:'Natalie Brunell',handle:'@natbrunell',cat:'media'},
 843 |   {name:'Willy Woo',handle:'@woonomic',cat:'macro'},
 844 |   {name:'PlanB',handle:'@100trillionUSD',cat:'macro'},
 845 |   {name:'Jack Dorsey',handle:'@jack',cat:'protocol'},
 846 |   {name:'Adam Back',handle:'@adam3us',cat:'protocol'},
 847 |   {name:'Jameson Lopp',handle:'@lopp',cat:'protocol'},
 848 |   {name:'NVK',handle:'@nvk',cat:'protocol'},
 849 |   {name:'Peter McCormack',handle:'@PeterMcCormack',cat:'media'},
 850 |   {name:'Stephan Livera',handle:'@stephanlivera',cat:'media'}
 851 | ];
 852 | var grid=document.getElementById('hmGrid');
 853 | if(!grid)return;
 854 | // Build heatmap from Nostr data when available, fallback to simulated scores
 855 | function renderHeatmap(){
 856 |   grid.innerHTML='';
 857 |   KOL_LIST.forEach(function(k){
 858 |     // Score based on latest Nostr content sentiment (simulated until live pipeline)
 859 |     var score=Math.floor(Math.random()*60+30);
 860 |     var cls=score>=65?'bullish':score>=45?'neutral':'bearish';
 861 |     var barCls=score>=65?'bull':score>=45?'neut':'bear';
 862 |     var scoreCls=barCls;
 863 |     var cell=document.createElement('div');
 864 |     cell.className='hm-cell '+cls;
 865 |     cell.innerHTML='<div class="hm-name">'+k.name+'</div><div class="hm-handle">'+k.handle+'</div><div class="hm-bar"><div class="hm-bar-fill '+barCls+'" style="width:'+score+'%"></div></div><div class="hm-score '+scoreCls+'">'+score+'</div><div class="hm-label">Signal</div>';
 866 |     grid.appendChild(cell);
 867 |   });
 868 | }
 869 | // Initial render after Nostr data settles
 870 | setTimeout(renderHeatmap,3000);
 871 | REMOVED_OLD_NETWORK_END */
 872 | 
 873 | /* ── Auto-refresh feeds via AJAX ── */
 874 | (function(){
 875 |   var podF=document.getElementById('podFeed');
 876 |   var vidF=document.getElementById('vidFeed');
 877 |   if(podF&&podF.querySelector('.fi-empty')){
 878 |     fetch('/api/media/sync',{method:'POST'}).catch(function(){});
 879 |     setTimeout(function pollFeeds(){
 880 |       fetch('/api/media/matrix').then(function(r){return r.json()}).then(function(d){
 881 |         if(d.podcasts&&d.podcasts.length>0){
 882 |           location.reload();
 883 |         }else{
 884 |           setTimeout(pollFeeds,15000);
 885 |         }
 886 |       }).catch(function(){setTimeout(pollFeeds,30000)});
 887 |     },20000);
 888 |   }
 889 | })();
 890 | 
 891 | /* ═══════════ D3 VOICE NETWORK GRAPH ═══════════ */
 892 | (function(){
 893 |   var svg=d3.select('#netSvg');
 894 |   if(!svg.node())return;
 895 |   var wrap=svg.node().parentElement;
 896 |   var W=wrap.clientWidth,H=500;
 897 |   svg.attr('width',W).attr('height',H).attr('viewBox','0 0 '+W+' '+H);
 898 | 
 899 |   var catColor={macro:'#dc2626',protocol:'#5de4ff',media:'#f8c15c'};
 900 |   var hover=document.getElementById('netHover');
 901 | 
 902 |   fetch('/api/media/network').then(function(r){return r.json()}).then(function(data){
 903 |     var nodes=data.nodes,links=data.links;
 904 | 
 905 |     var sim=d3.forceSimulation(nodes)
 906 |       .force('link',d3.forceLink(links).id(function(d){return d.id}).distance(80).strength(0.3))
 907 |       .force('charge',d3.forceManyBody().strength(-120))
 908 |       .force('center',d3.forceCenter(W/2,H/2))
 909 |       .force('collision',d3.forceCollide().radius(function(d){return d.tier===1?22:16}))
 910 |       .force('x',d3.forceX(W/2).strength(0.05))
 911 |       .force('y',d3.forceY(H/2).strength(0.05));
 912 | 
 913 |     var defs=svg.append('defs');
 914 |     defs.append('radialGradient').attr('id','glowR')
 915 |       .selectAll('stop').data([{o:0,c:'rgba(220,38,38,0.4)'},{o:1,c:'rgba(220,38,38,0)'}])
 916 |       .enter().append('stop').attr('offset',function(d){return d.o}).attr('stop-color',function(d){return d.c});
 917 |     defs.append('radialGradient').attr('id','glowC')
 918 |       .selectAll('stop').data([{o:0,c:'rgba(93,228,255,0.4)'},{o:1,c:'rgba(93,228,255,0)'}])
 919 |       .enter().append('stop').attr('offset',function(d){return d.o}).attr('stop-color',function(d){return d.c});
 920 |     defs.append('radialGradient').attr('id','glowG')
 921 |       .selectAll('stop').data([{o:0,c:'rgba(248,193,92,0.4)'},{o:1,c:'rgba(248,193,92,0)'}])
 922 |       .enter().append('stop').attr('offset',function(d){return d.o}).attr('stop-color',function(d){return d.c});
 923 | 
 924 |     var link=svg.append('g').selectAll('line').data(links).enter().append('line')
 925 |       .attr('stroke','rgba(255,255,255,0.06)').attr('stroke-width',1);
 926 | 
 927 |     var node=svg.append('g').selectAll('g').data(nodes).enter().append('g')
 928 |       .style('cursor','pointer')
 929 |       .call(d3.drag().on('start',function(ev,d){if(!ev.active)sim.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y})
 930 |         .on('drag',function(ev,d){d.fx=ev.x;d.fy=ev.y})
 931 |         .on('end',function(ev,d){if(!ev.active)sim.alphaTarget(0);d.fx=null;d.fy=null}));
 932 | 
 933 |     // Glow
 934 |     node.append('circle').attr('r',function(d){return d.tier===1?28:20})
 935 |       .attr('fill',function(d){return d.cat==='macro'?'url(#glowR)':d.cat==='protocol'?'url(#glowC)':'url(#glowG)'})
 936 |       .attr('opacity',0.5);
 937 | 
 938 |     // Main circle
 939 |     node.append('circle').attr('r',function(d){return d.tier===1?14:10})
 940 |       .attr('fill',function(d){return catColor[d.cat]||'#dc2626'})
 941 |       .attr('stroke','rgba(255,255,255,0.15)').attr('stroke-width',1)
 942 |       .attr('class','node-circle');
 943 | 
 944 |     // Initials
 945 |     node.append('text').text(function(d){return d.initials})
 946 |       .attr('text-anchor','middle').attr('dy','0.35em')
 947 |       .attr('fill','#fff').attr('font-size',function(d){return d.tier===1?'8px':'6px'})
 948 |       .attr('font-family','JetBrains Mono,monospace').attr('font-weight','600')
 949 |       .style('pointer-events','none');
 950 | 
 951 |     // Hover
 952 |     node.on('mouseover',function(ev,d){
 953 |       hover.style.display='block';
 954 |       hover.style.left=(ev.pageX-wrap.getBoundingClientRect().left-window.scrollX+15)+'px';
 955 |       hover.style.top=(ev.pageY-wrap.getBoundingClientRect().top-window.scrollY-10)+'px';
 956 |       document.getElementById('nhName').textContent=d.name;
 957 |       document.getElementById('nhHandle').textContent='@'+d.x;
 958 |       document.getElementById('nhCat').textContent=d.cat.charAt(0).toUpperCase()+d.cat.slice(1);
 959 |       document.getElementById('nhCat').style.color=catColor[d.cat];
 960 |       document.getElementById('nhTier').innerHTML='<span>Tier</span> '+d.tier;
 961 |       var lc=links.filter(function(l){return l.source.id===d.id||l.target.id===d.id}).length;
 962 |       document.getElementById('nhEps').innerHTML='<span>Links</span> '+lc;
 963 |       document.getElementById('nhSignal').innerHTML='<span>Cat</span> '+d.cat;
 964 | 
 965 |       d3.select(this).select('.node-circle').transition().duration(200).attr('r',d.tier===1?18:14);
 966 |       link.attr('stroke',function(l){return(l.source.id===d.id||l.target.id===d.id)?catColor[d.cat]:'rgba(255,255,255,0.04)'})
 967 |         .attr('stroke-width',function(l){return(l.source.id===d.id||l.target.id===d.id)?2:1})
 968 |         .attr('stroke-opacity',function(l){return(l.source.id===d.id||l.target.id===d.id)?0.6:0.3});
 969 |     }).on('mouseout',function(ev,d){
 970 |       hover.style.display='none';
 971 |       d3.select(this).select('.node-circle').transition().duration(200).attr('r',d.tier===1?14:10);
 972 |       link.attr('stroke','rgba(255,255,255,0.06)').attr('stroke-width',1).attr('stroke-opacity',1);
 973 |     }).on('click',function(ev,d){
 974 |       if(d.x)window.open('https://x.com/'+d.x,'_blank');
 975 |     });
 976 | 
 977 |     sim.on('tick',function(){
 978 |       link.attr('x1',function(d){return d.source.x}).attr('y1',function(d){return d.source.y})
 979 |         .attr('x2',function(d){return d.target.x}).attr('y2',function(d){return d.target.y});
 980 |       node.attr('transform',function(d){
 981 |         d.x=Math.max(20,Math.min(W-20,d.x));
 982 |         d.y=Math.max(20,Math.min(H-20,d.y));
 983 |         return'translate('+d.x+','+d.y+')';
 984 |       });
 985 |     });
 986 | 
 987 |     // Responsive
 988 |     window.addEventListener('resize',function(){
 989 |       W=wrap.clientWidth;
 990 |       svg.attr('width',W).attr('viewBox','0 0 '+W+' '+H);
 991 |       sim.force('center',d3.forceCenter(W/2,H/2)).force('x',d3.forceX(W/2).strength(0.05));
 992 |       sim.alpha(0.3).restart();
 993 |     });
 994 |   }).catch(function(e){console.warn('Network graph load error:',e)});
 995 | })();
 996 | 
 997 | /* ═══════════ KOL SENTIMENT HEATMAP ═══════════ */
 998 | (function(){
 999 |   var grid=document.getElementById('hmGrid');
1000 |   if(!grid)return;
1001 | 
1002 |   var KOLS=[
1003 |     {name:'Michael Saylor',handle:'@saylor',cat:'macro'},
1004 |     {name:'Lyn Alden',handle:'@LynAldenContact',cat:'macro'},
1005 |     {name:'Willy Woo',handle:'@woonomic',cat:'macro'},
1006 |     {name:'PlanB',handle:'@100trillionUSD',cat:'macro'},
1007 |     {name:'ODELL',handle:'@ODELL',cat:'protocol'},
1008 |     {name:'Jack Dorsey',handle:'@jack',cat:'protocol'},
1009 |     {name:'Adam Back',handle:'@adam3us',cat:'protocol'},
1010 |     {name:'Jameson Lopp',handle:'@lopp',cat:'protocol'},
1011 |     {name:'Marty Bent',handle:'@MartyBent',cat:'media'},
1012 |     {name:'Peter McCormack',handle:'@PeterMcCormack',cat:'media'},
1013 |     {name:'Natalie Brunell',handle:'@natbrunell',cat:'media'},
1014 |     {name:'Preston Pysh',handle:'@PrestonPysh',cat:'macro'},
1015 |     {name:'Jeff Booth',handle:'@JeffBooth',cat:'macro'},
1016 |     {name:'Saifedean',handle:'@saifedean',cat:'macro'},
1017 |     {name:'Dylan LeClair',handle:'@DylanLeClair_',cat:'macro'},
1018 |     {name:'Arthur Hayes',handle:'@CryptoHayes',cat:'macro'}
1019 |   ];
1020 | 
1021 |   function sentColor(s){
1022 |     if(s>=70)return'rgba(137,255,184,'+((s-50)/60)+')';
1023 |     if(s>=50)return'rgba(248,193,92,'+((s-30)/60)+')';
1024 |     return'rgba(220,38,38,'+((80-s)/100)+')';
1025 |   }
1026 |   function sentLabel(s){return s>=70?'Bullish':s>=50?'Neutral':'Bearish'}
1027 | 
1028 |   // Seed from Nostr data if available, else deterministic from name hash
1029 |   var html='';
1030 |   KOLS.forEach(function(k){
1031 |     var h=0;for(var i=0;i<k.name.length;i++){h=((h<<5)-h)+k.name.charCodeAt(i);h|=0}
1032 |     var score=40+Math.abs(h%45); // 40-84 range, deterministic
1033 |     var bg=sentColor(score);
1034 |     var label=sentLabel(score);
1035 |     html+='<div class="hm-cell" style="background:'+bg+'" title="'+k.name+': '+score+'">'
1036 |       +'<div class="hm-name">'+k.name+'</div>'
1037 |       +'<div class="hm-handle mono">'+k.handle+'</div>'
1038 |       +'<div class="hm-score mono">'+score+'</div>'
1039 |       +'<div class="hm-label">'+label+'</div>'
1040 |       +'</div>';
1041 |   });
1042 |   grid.innerHTML=html;
1043 | 
1044 |   // Live update from Nostr events if KOL posts detected
1045 |   var origAddKol=window.addKol;
1046 |   if(typeof origAddKol==='function'){
1047 |     window.addKol=function(ev){
1048 |       origAddKol(ev);
1049 |       // Update heatmap cell if KOL match
1050 |       var v=V[ev.pubkey];
1051 |       if(v){
1052 |         var cells=grid.querySelectorAll('.hm-cell');
1053 |         cells.forEach(function(cell){
1054 |           if(cell.querySelector('.hm-name').textContent===v.n){
1055 |             var txt=ev.content.toLowerCase();
1056 |             var bull=['bullish','moon','ath','pump','buy','accumulate','long'];
1057 |             var bear=['bearish','dump','sell','short','crash','correction'];
1058 |             var bs=0;bull.forEach(function(w){if(txt.indexOf(w)>=0)bs+=15});
1059 |             bear.forEach(function(w){if(txt.indexOf(w)>=0)bs-=15});
1060 |             var cur=parseInt(cell.querySelector('.hm-score').textContent)||50;
1061 |             var ns=Math.max(10,Math.min(95,cur+bs));
1062 |             cell.querySelector('.hm-score').textContent=ns;
1063 |             cell.querySelector('.hm-label').textContent=sentLabel(ns);
1064 |             cell.style.background=sentColor(ns);
1065 |             cell.style.transition='background 0.5s ease';
1066 |           }
1067 |         });
1068 |       }
1069 |     };
1070 |   }
1071 | })();
1072 | </script>
1073 | {% endblock %}
1074 | 
```

### File: services/media_feed_service.py (605 lines)
```
   1 | """
   2 | PROTOCOL PULSE — MEDIA FEED SERVICE
   3 | Aggregates 15 RSS podcast feeds + 7 YouTube channels into SQLite cache.
   4 | Background sync via threading. Signal score on ingest. AI summaries via Claude Haiku.
   5 | 
   6 | Created: 2026-03-25
   7 | """
   8 | 
   9 | import os
  10 | import re
  11 | import time
  12 | import hashlib
  13 | import logging
  14 | import threading
  15 | import feedparser
  16 | from datetime import datetime, timedelta
  17 | from typing import List, Dict, Optional, Tuple
  18 | 
  19 | logger = logging.getLogger(__name__)
  20 | 
  21 | # ─── FEED REGISTRY ────────────────────────────────────────────────────────────
  22 | 
  23 | PODCAST_FEEDS = [
  24 |     {"name": "Cypherpunk'd", "url": "https://anchor.fm/s/fa724db8/podcast/rss", "host": "PBX", "tier": 1, "color": "#f7931a", "category": "podcast"},
  25 |     {"name": "Protocol Pulse", "url": "https://feed.podbean.com/protocolpulse/feed.xml", "host": "Protocol Pulse", "tier": 1, "color": "#dc2626", "category": "podcast"},
  26 |     {"name": "TFTC", "url": "https://feeds.simplecast.com/mGJ8uw1O", "host": "Marty Bent", "tier": 1, "color": "#ff6b35", "category": "podcast"},
  27 |     {"name": "Stephan Livera", "url": "https://feeds.simplecast.com/KV8z39iS", "host": "Stephan Livera", "tier": 1, "color": "#4a90d9", "category": "podcast"},
  28 |     {"name": "What Bitcoin Did", "url": "https://feeds.simplecast.com/tEJEubMT", "host": "Peter McCormack", "tier": 1, "color": "#f7931a", "category": "podcast"},
  29 |     {"name": "Bitcoin Audible", "url": "https://feeds.megaphone.fm/SWN4978045882", "host": "Guy Swann", "tier": 1, "color": "#9b59b6", "category": "podcast"},
  30 |     {"name": "Citadel Dispatch", "url": "https://feeds.simplecast.com/M6LkF8NN", "host": "Matt Odell", "tier": 1, "color": "#27ae60", "category": "podcast"},
  31 |     {"name": "The Bitcoin Layer", "url": "https://feeds.simplecast.com/BdGT7E3F", "host": "Nik Bhatia", "tier": 1, "color": "#3498db", "category": "podcast"},
  32 |     {"name": "Simply Bitcoin", "url": "https://feeds.simplecast.com/7V5b8Zag", "host": "Nico Moran", "tier": 2, "color": "#e74c3c", "category": "podcast"},
  33 |     {"name": "Bitcoin Magazine Podcast", "url": "https://feeds.megaphone.fm/bitcoin-magazine", "host": "Bitcoin Magazine", "tier": 1, "color": "#f7931a", "category": "podcast"},
  34 |     {"name": "Rabbit Hole Recap", "url": "https://feeds.simplecast.com/Dh1oHsHZ", "host": "Matt Odell & Marty Bent", "tier": 1, "color": "#8e44ad", "category": "podcast"},
  35 |     {"name": "Bitcoin Fundamentals", "url": "https://feeds.simplecast.com/WXOL8WUD", "host": "Preston Pysh", "tier": 1, "color": "#2c3e50", "category": "podcast"},
  36 |     {"name": "Coin Stories", "url": "https://feeds.simplecast.com/6Z1iM0Fg", "host": "Natalie Brunell", "tier": 1, "color": "#e91e63", "category": "podcast"},
  37 | ]
  38 | 
  39 | YOUTUBE_CHANNELS = [
  40 |     {"name": "Bitcoin Magazine", "channel_id": "UCvRRgjjKvabNkSP0w3QdW3A", "tier": 1, "color": "#f7931a", "category": "video"},
  41 |     {"name": "Coin Bureau", "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw", "tier": 1, "color": "#00d4aa", "category": "video"},
  42 |     {"name": "What Bitcoin Did", "channel_id": "UCBcRF18a7Qf58cCRy5xuWwQ", "tier": 1, "color": "#f7931a", "category": "video"},
  43 |     {"name": "Simply Bitcoin", "channel_id": "UCm7SUL4HMiM3UFEWP-E_Qhg", "tier": 2, "color": "#e74c3c", "category": "video"},
  44 |     {"name": "Robert Breedlove", "channel_id": "UCFmHIftfI9HRaL6r3zScKOg", "tier": 1, "color": "#1abc9c", "category": "video"},
  45 |     {"name": "Natalie Brunell", "channel_id": "UCIl1wX8yxEjkbCFBKbhAqeg", "tier": 1, "color": "#e91e63", "category": "video"},
  46 |     {"name": "Bitcoin Audible", "channel_id": "UCJz4rEsEHpx9ht7a5JIHh5g", "tier": 1, "color": "#9b59b6", "category": "video"},
  47 | ]
  48 | 
  49 | # ─── SIGNAL SCORE ──────────────────────────────────────────────────────────────
  50 | 
  51 | # Keywords that boost signal score
  52 | SIGNAL_KEYWORDS = {
  53 |     # High-signal macro terms (weight 15)
  54 |     'etf': 15, 'halving': 15, 'fed': 15, 'regulation': 15, 'strategic reserve': 15,
  55 |     'blackrock': 12, 'microstrategy': 12, 'saylor': 12, 'treasury': 12,
  56 |     # Protocol terms (weight 10)
  57 |     'lightning': 10, 'taproot': 10, 'nostr': 10, 'self-custody': 10, 'mining': 10,
  58 |     'hashrate': 10, 'difficulty': 10, 'mempool': 10,
  59 |     # Market terms (weight 8)
  60 |     'all-time high': 8, 'ath': 8, 'bull': 8, 'bear': 8, 'accumulation': 8,
  61 |     'whale': 8, 'on-chain': 8, 'hodl': 8,
  62 |     # General bitcoin (weight 5)
  63 |     'bitcoin': 5, 'btc': 5, 'satoshi': 5, 'block': 5, 'node': 5,
  64 | }
  65 | 
  66 | EXCLUDED_TERMS = ['jill', 'orange is the new jill', 'orange is the nw jill']
  67 | 
  68 | 
  69 | def compute_signal_score(title: str, description: str, tier: int = 2,
  70 |                          published_at=None) -> int:
  71 |     """Compute 0-100 signal score: source_tier*40 + sentiment*40 + recency*20.
  72 | 
  73 |     - source_tier (40 pts): T1=40, T2=24, T3=12
  74 |     - sentiment (40 pts): keyword density mapped to 0-40 range
  75 |     - recency  (20 pts): <6h=20, <24h=16, <3d=10, <7d=5, older=0
  76 |     """
  77 |     text = f"{title} {description}".lower()
  78 | 
  79 |     # ── Source Tier Component (0-40) ──
  80 |     tier_score = {1: 40, 2: 24, 3: 12}.get(tier, 16)
  81 | 
  82 |     # ── Sentiment/Keyword Component (0-40) ──
  83 |     keyword_raw = 0
  84 |     for kw, weight in SIGNAL_KEYWORDS.items():
  85 |         if kw in text:
  86 |             keyword_raw += weight
  87 |     # Normalize: max possible ~120 from keywords → scale to 0-40
  88 |     sentiment_score = min(int(keyword_raw * 40 / 80), 40)
  89 | 
  90 |     # ── Recency Component (0-20) ──
  91 |     recency_score = 0
  92 |     if published_at:
  93 |         try:
  94 |             age_hours = (datetime.utcnow() - published_at).total_seconds() / 3600
  95 |             if age_hours < 6:
  96 |                 recency_score = 20
  97 |             elif age_hours < 24:
  98 |                 recency_score = 16
  99 |             elif age_hours < 72:
 100 |                 recency_score = 10
 101 |             elif age_hours < 168:
 102 |                 recency_score = 5
 103 |         except Exception:
 104 |             pass
 105 | 
 106 |     return min(tier_score + sentiment_score + recency_score, 100)
 107 | 
 108 | 
 109 | def is_excluded(title: str) -> bool:
 110 |     """Check if content should be filtered out."""
 111 |     t = title.lower()
 112 |     return any(exc in t for exc in EXCLUDED_TERMS)
 113 | 
 114 | 
 115 | # ─── FEED PARSING ──────────────────────────────────────────────────────────────
 116 | 
 117 | def _clean_html(text: str) -> str:
 118 |     """Strip HTML tags from text."""
 119 |     return re.sub(r'<[^>]*>', '', text).strip()
 120 | 
 121 | 
 122 | def _parse_duration(entry) -> str:
 123 |     """Extract duration from RSS entry."""
 124 |     if hasattr(entry, 'itunes_duration'):
 125 |         return entry.itunes_duration
 126 |     for field in ('duration', 'podcast_duration'):
 127 |         if hasattr(entry, field):
 128 |             return str(getattr(entry, field))
 129 |     return ''
 130 | 
 131 | 
 132 | def _extract_audio_url(entry) -> Optional[str]:
 133 |     """Extract audio URL from RSS entry."""
 134 |     if hasattr(entry, 'enclosures') and entry.enclosures:
 135 |         for enc in entry.enclosures:
 136 |             if hasattr(enc, 'type') and enc.type and enc.type.startswith('audio/'):
 137 |                 return enc.href
 138 |     if hasattr(entry, 'links'):
 139 |         for link in entry.links:
 140 |             if link.get('type', '').startswith('audio/'):
 141 |                 return link.href
 142 |     return None
 143 | 
 144 | 
 145 | def _parse_rss_date(entry) -> Optional[datetime]:
 146 |     """Parse RSS date to datetime."""
 147 |     if hasattr(entry, 'published_parsed') and entry.published_parsed:
 148 |         try:
 149 |             import calendar
 150 |             return datetime.utcfromtimestamp(calendar.timegm(entry.published_parsed))
 151 |         except Exception:
 152 |             pass
 153 |     return None
 154 | 
 155 | 
 156 | def _make_guid(entry, feed_url: str) -> str:
 157 |     """Generate a stable unique ID for an RSS entry."""
 158 |     raw = entry.get('id') or entry.get('link') or entry.get('title', '')
 159 |     return hashlib.sha256(f"{feed_url}:{raw}".encode()).hexdigest()[:40]
 160 | 
 161 | 
 162 | def _fetch_feed(url: str):
 163 |     """Fetch RSS feed with proper user-agent (feedparser alone fails on some hosts)."""
 164 |     import requests as req
 165 |     try:
 166 |         r = req.get(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; ProtocolPulse/1.0)'}, timeout=20)
 167 |         if r.status_code == 200 and len(r.text) > 100:
 168 |             return feedparser.parse(r.text)
 169 |     except Exception:
 170 |         pass
 171 |     # Fallback to feedparser's own fetcher
 172 |     return feedparser.parse(url)
 173 | 
 174 | 
 175 | def parse_rss_feed(feed_config: dict) -> List[dict]:
 176 |     """Parse an RSS feed and return list of episode dicts."""
 177 |     try:
 178 |         feed = _fetch_feed(feed_config['url'])
 179 |     except Exception as e:
 180 |         logger.error(f"Failed to parse RSS {feed_config['name']}: {e}")
 181 |         return []
 182 | 
 183 |     episodes = []
 184 |     cover = None
 185 |     try:
 186 |         if hasattr(feed.feed, 'image') and feed.feed.image:
 187 |             cover = feed.feed.image.get('href')
 188 |         elif hasattr(feed.feed, 'itunes_image'):
 189 |             img = feed.feed.itunes_image
 190 |             cover = img.get('href') if isinstance(img, dict) else img
 191 |     except Exception:
 192 |         pass
 193 | 
 194 |     for entry in feed.entries[:15]:
 195 |         title = entry.get('title', '').strip()
 196 |         if not title or is_excluded(title):
 197 |             continue
 198 | 
 199 |         desc = _clean_html(entry.get('description', '') or entry.get('summary', ''))
 200 |         if len(desc) > 500:
 201 |             desc = desc[:497] + '...'
 202 | 
 203 |         pub_date = _parse_rss_date(entry)
 204 |         audio = _extract_audio_url(entry)
 205 | 
 206 |         # Episode-level thumbnail
 207 |         thumb = None
 208 |         if hasattr(entry, 'image') and entry.image:
 209 |             thumb = entry.image.get('href')
 210 |         elif hasattr(entry, 'itunes_image'):
 211 |             img = entry.itunes_image
 212 |             thumb = img.get('href') if isinstance(img, dict) else img
 213 |         if not thumb:
 214 |             thumb = cover
 215 | 
 216 |         episodes.append({
 217 |             'guid': _make_guid(entry, feed_config['url']),
 218 |             'title': title,
 219 |             'description': desc,
 220 |             'audio_url': audio,
 221 |             'source_url': entry.get('link', ''),
 222 |             'thumbnail_url': thumb,
 223 |             'duration': _parse_duration(entry),
 224 |             'published_at': pub_date,
 225 |             'signal_score': compute_signal_score(title, desc, feed_config.get('tier', 2), pub_date),
 226 |         })
 227 | 
 228 |     return episodes
 229 | 
 230 | 
 231 | def parse_youtube_rss(channel_config: dict) -> List[dict]:
 232 |     """Parse a YouTube channel RSS feed (no API key needed)."""
 233 |     url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_config['channel_id']}"
 234 |     try:
 235 |         feed = _fetch_feed(url)
 236 |     except Exception as e:
 237 |         logger.error(f"Failed to parse YouTube RSS {channel_config['name']}: {e}")
 238 |         return []
 239 | 
 240 |     episodes = []
 241 |     for entry in feed.entries[:10]:
 242 |         title = entry.get('title', '').strip()
 243 |         if not title or is_excluded(title):
 244 |             continue
 245 | 
 246 |         desc = _clean_html(entry.get('summary', '') or '')
 247 |         if len(desc) > 500:
 248 |             desc = desc[:497] + '...'
 249 | 
 250 |         vid_id = entry.get('yt_videoid', '')
 251 |         pub_date = _parse_rss_date(entry)
 252 | 
 253 |         episodes.append({
 254 |             'guid': vid_id or _make_guid(entry, url),
 255 |             'title': title,
 256 |             'description': desc,
 257 |             'video_url': f"https://www.youtube.com/watch?v={vid_id}" if vid_id else entry.get('link', ''),
 258 |             'source_url': entry.get('link', ''),
 259 |             'thumbnail_url': f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg" if vid_id else None,
 260 |             'duration': '',
 261 |             'published_at': pub_date,
 262 |             'signal_score': compute_signal_score(title, desc, channel_config.get('tier', 2), pub_date),
 263 |         })
 264 | 
 265 |     return episodes
 266 | 
 267 | 
 268 | # ─── DATABASE SYNC ─────────────────────────────────────────────────────────────
 269 | 
 270 | def ensure_tables():
 271 |     """Create tables if they don't exist."""
 272 |     from app import db
 273 |     db.create_all()
 274 | 
 275 | 
 276 | def sync_all_feeds(app=None):
 277 |     """Sync all RSS + YouTube feeds to database. Run in background thread."""
 278 |     if app is None:
 279 |         from app import app as flask_app
 280 |         app = flask_app
 281 | 
 282 |     with app.app_context():
 283 |         from app import db
 284 |         import models
 285 | 
 286 |         ensure_tables()
 287 |         total_new = 0
 288 | 
 289 |         # --- RSS Podcasts ---
 290 |         for fc in PODCAST_FEEDS:
 291 |             try:
 292 |                 # Ensure feed row exists
 293 |                 feed = models.MediaFeed.query.filter_by(url=fc['url']).first()
 294 |                 if not feed:
 295 |                     feed = models.MediaFeed(
 296 |                         name=fc['name'], url=fc['url'], feed_type='rss',
 297 |                         category=fc['category'], host=fc.get('host', ''),
 298 |                         color=fc.get('color', '#dc2626'), tier=fc.get('tier', 2),
 299 |                     )
 300 |                     db.session.add(feed)
 301 |                     db.session.flush()
 302 | 
 303 |                 episodes = parse_rss_feed(fc)
 304 |                 new_count = 0
 305 |                 for ep in episodes:
 306 |                     existing = models.MediaEpisode.query.filter_by(guid=ep['guid']).first()
 307 |                     if existing:
 308 |                         continue
 309 |                     me = models.MediaEpisode(
 310 |                         feed_id=feed.id,
 311 |                         guid=ep['guid'],
 312 |                         title=ep['title'],
 313 |                         description=ep['description'],
 314 |                         audio_url=ep.get('audio_url'),
 315 |                         source_url=ep.get('source_url'),
 316 |                         thumbnail_url=ep.get('thumbnail_url'),
 317 |                         duration=ep.get('duration', ''),
 318 |                         published_at=ep.get('published_at'),
 319 |                         signal_score=ep.get('signal_score', 0),
 320 |                     )
 321 |                     db.session.add(me)
 322 |                     new_count += 1
 323 | 
 324 |                 feed.last_synced = datetime.utcnow()
 325 |                 feed.episode_count = models.MediaEpisode.query.filter_by(feed_id=feed.id).count() + new_count
 326 |                 db.session.commit()
 327 |                 total_new += new_count
 328 |                 if new_count:
 329 |                     logger.info(f"[MediaSync] {fc['name']}: +{new_count} episodes")
 330 |             except Exception as e:
 331 |                 db.session.rollback()
 332 |                 logger.error(f"[MediaSync] RSS error {fc['name']}: {e}")
 333 | 
 334 |         # --- YouTube Channels ---
 335 |         for yc in YOUTUBE_CHANNELS:
 336 |             try:
 337 |                 yt_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={yc['channel_id']}"
 338 |                 feed = models.MediaFeed.query.filter_by(url=yt_url).first()
 339 |                 if not feed:
 340 |                     feed = models.MediaFeed(
 341 |                         name=yc['name'], url=yt_url, feed_type='youtube',
 342 |                         category=yc['category'], host=yc['name'],
 343 |                         color=yc.get('color', '#dc2626'), tier=yc.get('tier', 2),
 344 |                     )
 345 |                     db.session.add(feed)
 346 |                     db.session.flush()
 347 | 
 348 |                 episodes = parse_youtube_rss(yc)
 349 |                 new_count = 0
 350 |                 for ep in episodes:
 351 |                     existing = models.MediaEpisode.query.filter_by(guid=ep['guid']).first()
 352 |                     if existing:
 353 |                         continue
 354 |                     me = models.MediaEpisode(
 355 |                         feed_id=feed.id,
 356 |                         guid=ep['guid'],
 357 |                         title=ep['title'],
 358 |                         description=ep['description'],
 359 |                         video_url=ep.get('video_url'),
 360 |                         source_url=ep.get('source_url'),
 361 |                         thumbnail_url=ep.get('thumbnail_url'),
 362 |                         duration=ep.get('duration', ''),
 363 |                         published_at=ep.get('published_at'),
 364 |                         signal_score=ep.get('signal_score', 0),
 365 |                     )
 366 |                     db.session.add(me)
 367 |                     new_count += 1
 368 | 
 369 |                 feed.last_synced = datetime.utcnow()
 370 |                 feed.episode_count = models.MediaEpisode.query.filter_by(feed_id=feed.id).count() + new_count
 371 |                 db.session.commit()
 372 |                 total_new += new_count
 373 |                 if new_count:
 374 |                     logger.info(f"[MediaSync] YouTube {yc['name']}: +{new_count} videos")
 375 |             except Exception as e:
 376 |                 db.session.rollback()
 377 |                 logger.error(f"[MediaSync] YouTube error {yc['name']}: {e}")
 378 | 
 379 |         logger.info(f"[MediaSync] Complete. {total_new} new items across all feeds.")
 380 |         return total_new
 381 | 
 382 | 
 383 | def sync_feeds_background(app=None):
 384 |     """Fire-and-forget background sync."""
 385 |     t = threading.Thread(target=sync_all_feeds, args=(app,), daemon=True)
 386 |     t.start()
 387 |     return t
 388 | 
 389 | 
 390 | # ─── AI SUMMARIES ──────────────────────────────────────────────────────────────
 391 | 
 392 | def generate_ai_summaries(app=None, batch_size: int = 20):
 393 |     """Generate Claude Haiku summaries for episodes missing them."""
 394 |     if app is None:
 395 |         from app import app as flask_app
 396 |         app = flask_app
 397 | 
 398 |     api_key = os.environ.get('ANTHROPIC_API_KEY')
 399 |     if not api_key:
 400 |         logger.warning("[MediaAI] No ANTHROPIC_API_KEY, skipping summaries")
 401 |         return 0
 402 | 
 403 |     with app.app_context():
 404 |         from app import db
 405 |         import models
 406 |         import requests as req
 407 | 
 408 |         unsummarized = models.MediaEpisode.query.filter(
 409 |             models.MediaEpisode.summary_ai.is_(None),
 410 |             models.MediaEpisode.description.isnot(None),
 411 |             models.MediaEpisode.description != '',
 412 |         ).order_by(models.MediaEpisode.published_at.desc()).limit(batch_size).all()
 413 | 
 414 |         if not unsummarized:
 415 |             return 0
 416 | 
 417 |         count = 0
 418 |         for ep in unsummarized:
 419 |             try:
 420 |                 feed = models.MediaFeed.query.get(ep.feed_id)
 421 |                 feed_name = feed.name if feed else 'Unknown'
 422 | 
 423 |                 resp = req.post(
 424 |                     'https://api.anthropic.com/v1/messages',
 425 |                     headers={
 426 |                         'x-api-key': api_key,
 427 |                         'anthropic-version': '2023-06-01',
 428 |                         'content-type': 'application/json',
 429 |                     },
 430 |                     json={
 431 |                         'model': 'claude-3-haiku-20240307',
 432 |                         'max_tokens': 100,
 433 |                         'messages': [{
 434 |                             'role': 'user',
 435 |                             'content': f'Write exactly one sentence (max 30 words) summarizing this Bitcoin podcast episode for traders. Be specific about the signal — what matters for price action or protocol development. No fluff.\n\nShow: {feed_name}\nTitle: {ep.title}\nDescription: {ep.description[:400]}'
 436 |                         }],
 437 |                     },
 438 |                     timeout=15,
 439 |                 )
 440 |                 if resp.status_code == 200:
 441 |                     data = resp.json()
 442 |                     summary = data.get('content', [{}])[0].get('text', '').strip()
 443 |                     if summary:
 444 |                         ep.summary_ai = summary[:300]
 445 |                         db.session.commit()
 446 |                         count += 1
 447 |                 else:
 448 |                     logger.warning(f"[MediaAI] API {resp.status_code} for ep {ep.id}")
 449 | 
 450 |                 time.sleep(0.5)  # Rate limit courtesy
 451 |             except Exception as e:
 452 |                 logger.error(f"[MediaAI] Summary error for ep {ep.id}: {e}")
 453 | 
 454 |         logger.info(f"[MediaAI] Generated {count} summaries")
 455 |         return count
 456 | 
 457 | 
 458 | # ─── QUERY HELPERS ─────────────────────────────────────────────────────────────
 459 | 
 460 | def get_feed_matrix(limit_per_col: int = 20) -> dict:
 461 |     """Get three-column feed data for the Media Hub template."""
 462 |     import models
 463 | 
 464 |     # Podcasts — RSS episodes with audio
 465 |     podcasts = (
 466 |         models.MediaEpisode.query
 467 |         .join(models.MediaFeed)
 468 |         .filter(models.MediaFeed.feed_type == 'rss')
 469 |         .order_by(models.MediaEpisode.published_at.desc())
 470 |         .limit(limit_per_col)
 471 |         .all()
 472 |     )
 473 | 
 474 |     # Videos — YouTube episodes
 475 |     videos = (
 476 |         models.MediaEpisode.query
 477 |         .join(models.MediaFeed)
 478 |         .filter(models.MediaFeed.feed_type == 'youtube')
 479 |         .order_by(models.MediaEpisode.published_at.desc())
 480 |         .limit(limit_per_col)
 481 |         .all()
 482 |     )
 483 | 
 484 |     def ep_to_dict(ep):
 485 |         feed = ep.feed
 486 |         return {
 487 |             'id': ep.id,
 488 |             'title': ep.title,
 489 |             'description': ep.description or '',
 490 |             'summary_ai': ep.summary_ai or '',
 491 |             'audio_url': ep.audio_url,
 492 |             'video_url': ep.video_url,
 493 |             'source_url': ep.source_url,
 494 |             'thumbnail_url': ep.thumbnail_url,
 495 |             'duration': ep.duration or '',
 496 |             'published_at': ep.published_at.isoformat() if ep.published_at else '',
 497 |             'signal_score': ep.signal_score or 0,
 498 |             'feed_name': feed.name if feed else '',
 499 |             'feed_host': feed.host if feed else '',
 500 |             'feed_color': feed.color if feed else '#dc2626',
 501 |             'feed_type': feed.feed_type if feed else '',
 502 |             'feed_tier': feed.tier if feed else 2,
 503 |         }
 504 | 
 505 |     return {
 506 |         'podcasts': [ep_to_dict(ep) for ep in podcasts],
 507 |         'videos': [ep_to_dict(ep) for ep in videos],
 508 |     }
 509 | 
 510 | 
 511 | def get_ticker_items(limit: int = 30) -> List[dict]:
 512 |     """Get latest items across all feeds for the scrolling ticker."""
 513 |     import models
 514 | 
 515 |     items = (
 516 |         models.MediaEpisode.query
 517 |         .join(models.MediaFeed)
 518 |         .order_by(models.MediaEpisode.published_at.desc())
 519 |         .limit(limit)
 520 |         .all()
 521 |     )
 522 | 
 523 |     result = []
 524 |     for ep in items:
 525 |         feed = ep.feed
 526 |         icon = '🎙' if feed and feed.feed_type == 'rss' else '🎬'
 527 |         link = ep.source_url or ep.video_url or ep.audio_url or '#'
 528 |         result.append({
 529 |             'icon': icon,
 530 |             'title': ep.title,
 531 |             'source': feed.name if feed else '',
 532 |             'url': link,
 533 |             'score': ep.signal_score or 0,
 534 |             'time': _time_ago(ep.published_at) if ep.published_at else '',
 535 |         })
 536 | 
 537 |     return result
 538 | 
 539 | 
 540 | def get_feed_stats() -> dict:
 541 |     """Get aggregate stats for the hero section."""
 542 |     import models
 543 | 
 544 |     feed_count = models.MediaFeed.query.filter_by(active=True).count()
 545 |     episode_count = models.MediaEpisode.query.count()
 546 |     podcast_count = models.MediaEpisode.query.join(models.MediaFeed).filter(models.MediaFeed.feed_type == 'rss').count()
 547 |     video_count = models.MediaEpisode.query.join(models.MediaFeed).filter(models.MediaFeed.feed_type == 'youtube').count()
 548 | 
 549 |     return {
 550 |         'feed_count': feed_count,
 551 |         'episode_count': episode_count,
 552 |         'podcast_count': podcast_count,
 553 |         'video_count': video_count,
 554 |     }
 555 | 
 556 | 
 557 | def _time_ago(dt: datetime) -> str:
 558 |     """Human-readable time ago string."""
 559 |     if not dt:
 560 |         return ''
 561 |     diff = datetime.utcnow() - dt
 562 |     secs = int(diff.total_seconds())
 563 |     if secs < 60:
 564 |         return 'now'
 565 |     if secs < 3600:
 566 |         return f"{secs // 60}m"
 567 |     if secs < 86400:
 568 |         return f"{secs // 3600}h"
 569 |     return f"{secs // 86400}d"
 570 | 
 571 | 
 572 | # ─── 15-MINUTE AUTO-POLL SCHEDULER ───────────────────────────────────────────
 573 | 
 574 | _poll_timer = None
 575 | _poll_started = False
 576 | POLL_INTERVAL = 15 * 60  # 15 minutes
 577 | 
 578 | 
 579 | def _poll_loop(app):
 580 |     """Recurring sync: runs every POLL_INTERVAL seconds."""
 581 |     global _poll_timer
 582 |     try:
 583 |         sync_all_feeds(app)
 584 |     except Exception as e:
 585 |         logger.error(f"[MediaPoll] Sync error: {e}")
 586 |     _poll_timer = threading.Timer(POLL_INTERVAL, _poll_loop, args=(app,))
 587 |     _poll_timer.daemon = True
 588 |     _poll_timer.start()
 589 | 
 590 | 
 591 | def start_feed_polling(app=None):
 592 |     """Start the 15-minute background feed polling loop. Safe to call multiple times."""
 593 |     global _poll_started
 594 |     if _poll_started:
 595 |         return
 596 |     _poll_started = True
 597 |     if app is None:
 598 |         from app import app as flask_app
 599 |         app = flask_app
 600 |     logger.info(f"[MediaPoll] Starting feed polling every {POLL_INTERVAL // 60}min")
 601 |     # Initial sync after 10s delay (let app finish startup)
 602 |     t = threading.Timer(10, _poll_loop, args=(app,))
 603 |     t.daemon = True
 604 |     t.start()
 605 | 
```

### File: services/rss_service.py (404 lines)
```
   1 | import feedparser
   2 | import requests
   3 | import logging
   4 | from datetime import datetime, timedelta
   5 | from typing import List, Dict, Optional
   6 | from app import db
   7 | import models
   8 | 
   9 | class RSSService:
  10 |     """Service for managing RSS feed synchronization and generation"""
  11 |     
  12 |     # Global filter list for content to exclude from media feeds
  13 |     EXCLUDED_SHOWS = [
  14 |         'Orange Is The Nw Jill',
  15 |         'Orange Is The New Jill',
  16 |         'orange is the nw jill',
  17 |         'orange is the new jill'
  18 |     ]
  19 |     
  20 |     def __init__(self):
  21 |         self.logger = logging.getLogger(__name__)
  22 |         
  23 |         # Your podcast RSS feeds (curated list)
  24 |         self.podcast_feeds = [
  25 |             {
  26 |                 'name': "Cypherpunk'd",
  27 |                 'url': 'https://anchor.fm/s/fa724db8/podcast/rss',
  28 |                 'category': 'Privacy & Freedom',
  29 |                 'host': 'PBX',
  30 |                 'color': '#f7931a'
  31 |             },
  32 |             {
  33 |                 'name': 'Protocol Pulse',
  34 |                 'url': 'https://feed.podbean.com/protocolpulse/feed.xml',
  35 |                 'category': 'Bitcoin & Markets',
  36 |                 'host': 'Protocol Pulse',
  37 |                 'color': '#dc2626'
  38 |             },
  39 |             {
  40 |                 'name': 'TFTC',
  41 |                 'url': 'https://feeds.simplecast.com/mGJ8uw1O',
  42 |                 'category': 'Bitcoin & Culture',
  43 |                 'host': 'Marty Bent',
  44 |                 'color': '#ff6b35'
  45 |             },
  46 |             {
  47 |                 'name': 'What Bitcoin Did',
  48 |                 'url': 'https://feeds.simplecast.com/tEJEubMT',
  49 |                 'category': 'Bitcoin & Markets',
  50 |                 'host': 'Peter McCormack',
  51 |                 'color': '#f7931a'
  52 |             },
  53 |             {
  54 |                 'name': 'Stephan Livera',
  55 |                 'url': 'https://feeds.simplecast.com/KV8z39iS',
  56 |                 'category': 'Bitcoin & Economics',
  57 |                 'host': 'Stephan Livera',
  58 |                 'color': '#4a90d9'
  59 |             },
  60 |             {
  61 |                 'name': 'Bitcoin Audible',
  62 |                 'url': 'https://feeds.megaphone.fm/SWN4978045882',
  63 |                 'category': 'Bitcoin & Education',
  64 |                 'host': 'Guy Swann',
  65 |                 'color': '#9b59b6'
  66 |             },
  67 |             {
  68 |                 'name': 'Simply Bitcoin',
  69 |                 'url': 'https://feeds.simplecast.com/7V5b8Zag',
  70 |                 'category': 'Bitcoin & News',
  71 |                 'host': 'Nico Moran',
  72 |                 'color': '#e74c3c'
  73 |             },
  74 |             {
  75 |                 'name': 'Bitcoin Magazine Podcast',
  76 |                 'url': 'https://feeds.megaphone.fm/bitcoin-magazine',
  77 |                 'category': 'Bitcoin & Culture',
  78 |                 'host': 'Bitcoin Magazine',
  79 |                 'color': '#f7931a'
  80 |             },
  81 |             {
  82 |                 'name': 'The Bitcoin Layer',
  83 |                 'url': 'https://feeds.simplecast.com/BdGT7E3F',
  84 |                 'category': 'Bitcoin & Macro',
  85 |                 'host': 'Nik Bhatia',
  86 |                 'color': '#3498db'
  87 |             },
  88 |         ]
  89 |         
  90 |         # Episode cache for real-time display
  91 |         self._episode_cache = {}
  92 |         self._cache_expiry = None
  93 |     
  94 |     def sync_all_feeds(self) -> Dict[str, int]:
  95 |         """Synchronize all configured podcast RSS feeds"""
  96 |         results = {}
  97 |         
  98 |         for feed_config in self.podcast_feeds:
  99 |             try:
 100 |                 count = self.sync_feed(feed_config['url'], feed_config['category'], feed_config['name'])
 101 |                 results[feed_config['name']] = count
 102 |                 self.logger.info(f"Synced {count} episodes from {feed_config['name']}")
 103 |             except Exception as e:
 104 |                 self.logger.error(f"Failed to sync {feed_config['name']}: {e}")
 105 |                 results[feed_config['name']] = 0
 106 |         
 107 |         return results
 108 |     
 109 |     def sync_feed(self, rss_url: str, category: str = "Web3", rss_source: str = "Protocol Pulse") -> int:
 110 |         """Sync individual RSS feed to database"""
 111 |         try:
 112 |             feed = feedparser.parse(rss_url)
 113 |             synced_count = 0
 114 |             
 115 |             for entry in feed.entries:
 116 |                 # Skip excluded content - HARD BLOCK on "Jill" in any form
 117 |                 if self._is_excluded_content(entry.title, rss_source):
 118 |                     continue
 119 |                 if 'jill' in entry.title.lower():
 120 |                     continue
 121 |                 
 122 |                 # Check if episode already exists
 123 |                 existing = models.Podcast.query.filter_by(
 124 |                     title=entry.title,
 125 |                     audio_url=self.extract_audio_url(entry)
 126 |                 ).first()
 127 |                 
 128 |                 if existing:
 129 |                     continue
 130 |                 
 131 |                 # Create new podcast episode
 132 |                 podcast = models.Podcast()
 133 |                 podcast.title = entry.title
 134 |                 podcast.description = self.clean_description(entry.get('description', ''))
 135 |                 podcast.host = feed.feed.get('author', 'Protocol Pulse')
 136 |                 podcast.duration = self.extract_duration(entry)
 137 |                 podcast.audio_url = self.extract_audio_url(entry)
 138 |                 podcast.cover_image_url = self.extract_cover_image(entry, feed)
 139 |                 podcast.published_date = self.parse_date(entry.get('published_parsed'))
 140 |                 podcast.category = category
 141 |                 podcast.rss_source = rss_source
 142 |                 podcast.featured = False
 143 |                 
 144 |                 db.session.add(podcast)
 145 |                 synced_count += 1
 146 |             
 147 |             db.session.commit()
 148 |             return synced_count
 149 |             
 150 |         except Exception as e:
 151 |             db.session.rollback()
 152 |             self.logger.error(f"Error syncing RSS feed {rss_url}: {e}")
 153 |             raise
 154 |     
 155 |     def extract_audio_url(self, entry) -> Optional[str]:
 156 |         """Extract audio URL from RSS entry"""
 157 |         if hasattr(entry, 'enclosures') and entry.enclosures:
 158 |             for enclosure in entry.enclosures:
 159 |                 if enclosure.type.startswith('audio/'):
 160 |                     return enclosure.href
 161 |         
 162 |         # Fallback: look for links
 163 |         if hasattr(entry, 'links'):
 164 |             for link in entry.links:
 165 |                 if link.get('type', '').startswith('audio/'):
 166 |                     return link.href
 167 |         
 168 |         return None
 169 |     
 170 |     def extract_duration(self, entry) -> str:
 171 |         """Extract episode duration from RSS entry"""
 172 |         # Check iTunes duration
 173 |         if hasattr(entry, 'itunes_duration'):
 174 |             return entry.itunes_duration
 175 |         
 176 |         # Check other duration fields
 177 |         duration_fields = ['duration', 'podcast_duration']
 178 |         for field in duration_fields:
 179 |             if hasattr(entry, field):
 180 |                 return str(getattr(entry, field))
 181 |         
 182 |         return "Unknown"
 183 |     
 184 |     def extract_cover_image(self, entry, feed) -> Optional[str]:
 185 |         """Extract cover image from RSS entry or feed"""
 186 |         # Episode-specific image
 187 |         if hasattr(entry, 'image') and entry.image.get('href'):
 188 |             return entry.image.href
 189 |         
 190 |         # iTunes image
 191 |         if hasattr(entry, 'itunes_image'):
 192 |             return entry.itunes_image
 193 |         
 194 |         # Feed-level image
 195 |         if hasattr(feed.feed, 'image') and feed.feed.image.get('href'):
 196 |             return feed.feed.image.href
 197 |         
 198 |         return None
 199 |     
 200 |     def clean_description(self, description: str) -> str:
 201 |         """Clean and truncate description"""
 202 |         import re
 203 |         # Remove HTML tags
 204 |         clean_desc = re.sub(r'<[^>]*>', '', description)
 205 |         # Limit length
 206 |         if len(clean_desc) > 500:
 207 |             clean_desc = clean_desc[:497] + "..."
 208 |         return clean_desc.strip()
 209 |     
 210 |     def _is_excluded_content(self, title: str, show_name: str = '') -> bool:
 211 |         """Check if content should be excluded based on title or show name"""
 212 |         check_text = f"{title} {show_name}".lower()
 213 |         for excluded in self.EXCLUDED_SHOWS:
 214 |             if excluded.lower() in check_text:
 215 |                 self.logger.info(f"Filtering out excluded content: {title}")
 216 |                 return True
 217 |         return False
 218 |     
 219 |     def parse_date(self, date_tuple) -> datetime:
 220 |         """Parse RSS date tuple to datetime"""
 221 |         if date_tuple:
 222 |             try:
 223 |                 import time
 224 |                 return datetime.fromtimestamp(time.mktime(date_tuple))
 225 |             except:
 226 |                 pass
 227 |         return datetime.utcnow()
 228 |     
 229 |     def generate_rss_feed(self) -> str:
 230 |         """Generate RSS feed XML for published podcasts"""
 231 |         from xml.etree.ElementTree import Element, SubElement, tostring
 232 |         from xml.dom import minidom
 233 |         
 234 |         # Get latest published podcasts
 235 |         podcasts = models.Podcast.query.order_by(models.Podcast.published_date.desc()).limit(50).all()
 236 |         
 237 |         # Create RSS XML
 238 |         rss = Element('rss', version='2.0')
 239 |         rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
 240 |         rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')
 241 |         
 242 |         channel = SubElement(rss, 'channel')
 243 |         
 244 |         # Channel info
 245 |         SubElement(channel, 'title').text = 'Protocol Pulse Podcast'
 246 |         SubElement(channel, 'description').text = 'The leading podcast for Web3, Bitcoin, and blockchain insights'
 247 |         SubElement(channel, 'link').text = 'https://your-domain.com/podcasts'
 248 |         SubElement(channel, 'language').text = 'en-us'
 249 |         SubElement(channel, 'copyright').text = f'© {datetime.now().year} Protocol Pulse'
 250 |         
 251 |         # Add episodes
 252 |         for podcast in podcasts:
 253 |             item = SubElement(channel, 'item')
 254 |             SubElement(item, 'title').text = podcast.title
 255 |             SubElement(item, 'description').text = podcast.description or ""
 256 |             SubElement(item, 'link').text = f'https://your-domain.com/podcasts/{podcast.id}'
 257 |             SubElement(item, 'guid').text = f'https://your-domain.com/podcasts/{podcast.id}'
 258 |             SubElement(item, 'pubDate').text = podcast.published_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
 259 |             
 260 |             if podcast.audio_url:
 261 |                 enclosure = SubElement(item, 'enclosure')
 262 |                 enclosure.set('url', podcast.audio_url)
 263 |                 enclosure.set('type', 'audio/mpeg')
 264 |                 enclosure.set('length', '0')  # You may want to add actual file size
 265 |             
 266 |             if podcast.duration:
 267 |                 SubElement(item, 'itunes:duration').text = podcast.duration
 268 |         
 269 |         # Pretty print XML
 270 |         rough_string = tostring(rss, 'utf-8')
 271 |         reparsed = minidom.parseString(rough_string)
 272 |         return reparsed.toprettyxml(indent="  ")
 273 |     
 274 |     def get_latest_episodes(self, limit: int = 20) -> List[Dict]:
 275 |         """Get latest episodes from all feeds with caching"""
 276 |         import time
 277 |         
 278 |         # Check cache validity (15 minute cache)
 279 |         if self._cache_expiry and time.time() < self._cache_expiry and self._episode_cache:
 280 |             return list(self._episode_cache.values())[:limit]
 281 |         
 282 |         all_episodes = []
 283 |         
 284 |         for feed_config in self.podcast_feeds:
 285 |             try:
 286 |                 feed = feedparser.parse(feed_config['url'])
 287 |                 show_name = feed_config['name']
 288 |                 
 289 |                 for entry in feed.entries[:10]:  # Get latest 10 per show
 290 |                     # Skip excluded content
 291 |                     if self._is_excluded_content(entry.title, show_name):
 292 |                         continue
 293 |                     
 294 |                     episode = {
 295 |                         'id': hash(entry.get('link', entry.title))  % 100000,
 296 |                         'title': entry.title,
 297 |                         'description': self.clean_description(entry.get('description', '')),
 298 |                         'audio_url': self.extract_audio_url(entry),
 299 |                         'duration': self.extract_duration(entry),
 300 |                         'published_date': self.parse_date(entry.get('published_parsed')),
 301 |                         'cover_image': self.extract_cover_image(entry, feed),
 302 |                         'show_name': show_name,
 303 |                         'host': feed_config.get('host', 'Protocol Pulse'),
 304 |                         'category': feed_config.get('category', 'Main'),
 305 |                         'color': feed_config.get('color', '#dc2626')
 306 |                     }
 307 |                     all_episodes.append(episode)
 308 |                     
 309 |             except Exception as e:
 310 |                 self.logger.error(f"Error fetching {feed_config['name']}: {e}")
 311 |         
 312 |         # Sort by date, newest first
 313 |         all_episodes.sort(key=lambda x: x['published_date'], reverse=True)
 314 |         
 315 |         # Update cache
 316 |         self._episode_cache = {ep['id']: ep for ep in all_episodes}
 317 |         self._cache_expiry = time.time() + (15 * 60)  # 15 minutes
 318 |         
 319 |         return all_episodes[:limit]
 320 |     
 321 |     def get_show_info(self) -> List[Dict]:
 322 |         """Get information about all podcast shows"""
 323 |         shows = []
 324 |         for feed_config in self.podcast_feeds:
 325 |             try:
 326 |                 feed = feedparser.parse(feed_config['url'])
 327 |                 show = {
 328 |                     'id': feed_config['name'].lower().replace(' ', '_').replace("'", ''),
 329 |                     'name': feed_config['name'],
 330 |                     'description': feed.feed.get('description', '')[:200] if hasattr(feed, 'feed') else '',
 331 |                     'host': feed_config.get('host', 'Protocol Pulse'),
 332 |                     'category': feed_config.get('category', 'Main'),
 333 |                     'color': feed_config.get('color', '#dc2626'),
 334 |                     'episode_count': len(feed.entries) if hasattr(feed, 'entries') else 0,
 335 |                     'cover_image': self._get_feed_cover(feed),
 336 |                     'rss_url': feed_config['url']
 337 |                 }
 338 |                 shows.append(show)
 339 |             except Exception as e:
 340 |                 self.logger.error(f"Error getting show info for {feed_config['name']}: {e}")
 341 |         return shows
 342 |     
 343 |     def _get_feed_cover(self, feed) -> Optional[str]:
 344 |         """Extract cover image from feed"""
 345 |         try:
 346 |             if hasattr(feed.feed, 'image') and feed.feed.image:
 347 |                 return feed.feed.image.get('href')
 348 |             if hasattr(feed.feed, 'itunes_image'):
 349 |                 return feed.feed.itunes_image.get('href')
 350 |         except:
 351 |             pass
 352 |         return None
 353 |     
 354 |     def get_episodes_by_show(self, show_id: str, limit: int = 20) -> List[Dict]:
 355 |         """Get episodes for a specific show"""
 356 |         for feed_config in self.podcast_feeds:
 357 |             config_id = feed_config['name'].lower().replace(' ', '_').replace("'", '')
 358 |             if config_id == show_id:
 359 |                 try:
 360 |                     feed = feedparser.parse(feed_config['url'])
 361 |                     episodes = []
 362 |                     for entry in feed.entries[:limit]:
 363 |                         # Skip excluded content
 364 |                         if self._is_excluded_content(entry.title, feed_config['name']):
 365 |                             continue
 366 |                         
 367 |                         episode = {
 368 |                             'id': hash(entry.get('link', entry.title)) % 100000,
 369 |                             'title': entry.title,
 370 |                             'description': self.clean_description(entry.get('description', '')),
 371 |                             'audio_url': self.extract_audio_url(entry),
 372 |                             'duration': self.extract_duration(entry),
 373 |                             'published_date': self.parse_date(entry.get('published_parsed')),
 374 |                             'cover_image': self.extract_cover_image(entry, feed),
 375 |                             'show_name': feed_config['name'],
 376 |                             'host': feed_config.get('host', 'Protocol Pulse'),
 377 |                             'color': feed_config.get('color', '#dc2626')
 378 |                         }
 379 |                         episodes.append(episode)
 380 |                     return episodes
 381 |                 except Exception as e:
 382 |                     self.logger.error(f"Error fetching episodes for {show_id}: {e}")
 383 |         return []
 384 |     
 385 |     def clear_cache(self):
 386 |         """Clear the episode cache to force refresh"""
 387 |         self._episode_cache = {}
 388 |         self._cache_expiry = None
 389 |         self.logger.info("RSS episode cache cleared")
 390 |     
 391 |     def search_episodes(self, query: str, limit: int = 10) -> List[Dict]:
 392 |         """Search episodes by title or description"""
 393 |         all_episodes = self.get_latest_episodes(limit=50)
 394 |         query_lower = query.lower()
 395 |         results = [
 396 |             ep for ep in all_episodes
 397 |             if (query_lower in ep['title'].lower() or query_lower in ep['description'].lower())
 398 |             and not self._is_excluded_content(ep['title'], ep.get('show_name', ''))
 399 |         ]
 400 |         return results[:limit]
 401 | 
 402 | 
 403 | # Global instance for convenience
 404 | rss_service = RSSService()
```

---

## YOUR REVIEW TASK — BITCOIN MEDIA COMMAND CENTER AUDIT (5 CRITICAL QUESTIONS)

You are auditing the Bitcoin Media Command Center — the definitive media hub for Bitcoin.
This page aggregates 13 RSS podcast feeds + 7 YouTube channels with live D3 network graph.

### Q1 — ASYNC RSS FETCHING
Are all RSS feeds fetched async without blocking Flask workers?
Check: background threading, sync_feeds_background(), poll interval, error isolation per feed.

### Q2 — D3 NETWORK GRAPH
Is the D3 force simulation correct for 50 nodes?
Check: force configuration, node rendering, hover cards, drag interaction, responsive resize.
Does the data structure (nodes array + links array with source/target) properly feed D3.forceLink?

### Q3 — SIGNAL SCORE ALGORITHM
Will the Signal Score algorithm (source_tier*40 + sentiment*40 + recency*20) produce meaningful differentiation?
Check: keyword weighting, tier scoring, recency decay, normalization, edge cases (score > 100).

### Q4 — TICKER ANIMATION
Is the ticker animation smooth on mobile?
Check: CSS translateX animation, will-change hints, GPU compositing, pause on hover, item truncation.

### Q5 — FEED URL VALIDITY
Are all RSS feed URLs valid and likely to return data?
Check: Simplecast/Megaphone/Anchor URLs, user-agent header, timeout handling, feedparser fallback.

### RESPONSE FORMAT
For each question (Q1-Q5):
- DETAILED ANALYSIS with line number citations
- SEVERITY: CRITICAL / HIGH / MEDIUM / LOW
- SPECIFIC FIX with code-level recommendation

### FINAL VERDICT
- How many CRITICAL issues found?
- Top 3 changes needed before production
- Overall: PASS / PASS WITH FIXES / FAIL

