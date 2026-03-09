# Media Intelligence Terminal - Complete Codebase Audit

## Overview
Bloomberg×Apple aesthetic media interface with deep space design, real-time network telemetry, and Web Audio API-powered audio visualization.

**Route:** `/media-terminal`  
**Template:** `templates/media_terminal.html` (1455 lines)  
**Route Handler:** `routes.py` lines 1037-1086

---

## Route Handler (routes.py)

```python
@app.route('/media-terminal')
def media_terminal():
    """Media Intelligence Terminal - Bloomberg×Apple aesthetic media interface"""
    from services.value_stream_service import value_stream_service
    from models import SentimentSnapshot
    
    value_stream_items = []
    try:
        posts = value_stream_service.get_value_stream(limit=5)
        for p in posts:
            hours_ago = 2
            try:
                from datetime import datetime
                submitted = datetime.fromisoformat(p.get('submitted_at', '').replace('Z', '+00:00'))
                hours_ago = int((datetime.utcnow() - submitted.replace(tzinfo=None)).total_seconds() / 3600)
            except:
                pass
            value_stream_items.append({
                'platform': p.get('platform', 'VALUE STREAM').upper(),
                'title': p.get('title', 'Untitled'),
                'time_ago': f"{hours_ago}h ago" if hours_ago < 24 else f"{hours_ago // 24}d ago"
            })
    except Exception as e:
        logging.warning(f"Could not load value stream for media terminal: {e}")
    
    sentiment_state = 'EQUILIBRIUM'
    sentiment_score = 50
    sarah_note = "Network congestion is currently low. Optimal window for UTXO consolidation. Fee environment suggests accumulation phase behavior. Act accordingly."
    
    try:
        snapshot = SentimentSnapshot.query.order_by(SentimentSnapshot.created_at.desc()).first()
        if snapshot:
            sentiment_state = snapshot.state_key or 'EQUILIBRIUM'
            sentiment_score = snapshot.score or 50
    except Exception as e:
        logging.warning(f"Could not load sentiment for media terminal: {e}")
    
    original_series = [
        {'key': 'cypherpunkd', 'title': "Cypherpunk'd", 'mission': 'Sovereignty in the digital age', 'badge': 'EXCLUSIVE', 'thumbnail': '/static/images/series-cypherpunkd.jpg'},
        {'key': 'bigprint', 'title': 'The Big Print', 'mission': 'Where macro meets Bitcoin', 'badge': 'MACRO INTEL', 'thumbnail': '/static/images/series-bigprint.jpg'},
        {'key': '21million', 'title': '21 Million', 'mission': 'Bitcoin news, distilled', 'badge': 'WEEKLY BRIEF', 'thumbnail': '/static/images/series-21m.jpg'},
        {'key': 'pulse', 'title': 'Protocol Pulse', 'mission': 'Leaders speak truth', 'badge': 'FLAGSHIP', 'thumbnail': '/static/images/series-pulse.jpg'},
    ]
    
    return render_template('media_terminal.html',
                          value_stream_items=value_stream_items,
                          sentiment_state=sentiment_state,
                          sentiment_score=sentiment_score,
                          sarah_note=sarah_note,
                          original_series=original_series)
```

---

## Template: media_terminal.html (Complete)

### CSS Variables & Design System
```css
:root {
    --deep-space: #010101;
    --panel-bg: rgba(5, 5, 8, 0.95);
    --glass-border: rgba(220, 38, 38, 0.12);
    --glass-border-hover: rgba(220, 38, 38, 0.5);
    --accent-red: #dc2626;
    --accent-red-glow: rgba(220, 38, 38, 0.4);
    --bitcoin-gold: #f7931a;
    --text-primary: #ffffff;
    --text-secondary: rgba(255, 255, 255, 0.7);
    --text-muted: rgba(255, 255, 255, 0.4);
    --signal-green: #00ff88;
}
```

### Typography
- **Primary Font:** Inter (per design_guidelines.md)
- **Mono Font:** IBM Plex Mono (for labels, metrics, timestamps)
- Google Fonts CDN: `https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap`

### Key Components

#### 1. SVG Noise Grain Overlay
```css
.noise-overlay {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 1;
    opacity: 0.035;
    background: url("data:image/svg+xml,...feTurbulence type='fractalNoise'...");
}
```

#### 2. Ambient Glow Orbs (3 floating orbs with blur animation)
```css
.ambient-orb {
    position: fixed;
    border-radius: 50%;
    filter: blur(120px);
    pointer-events: none;
}
.orb-1 { width: 800px; background: rgba(220, 38, 38, 0.06); animation: orbFloat 25s infinite; }
```

#### 3. Tactical Telemetry Strip (Fixed header with live metrics)
- **Height:** 48px
- **Position:** Fixed, top: 65px
- **Metrics:** MEMPOOL, PENDING TXS, FEE, HASHRATE
- **Sentiment Dial:** SVG arc with gradient (red → gold → green)
- **Live Updates:** Fetches from `/api/network-stats` every 60 seconds

```html
<div class="telemetry-strip">
    <div class="telemetry-metrics">
        <div class="metric-item">
            <span class="metric-label">MEMPOOL</span>
            <span class="metric-value" id="mempoolSize">{{ mempool_size or '45 MB' }}</span>
        </div>
        <!-- ... more metrics ... -->
    </div>
    <div class="sentiment-dial">
        <svg class="dial-svg" viewBox="0 0 80 40">
            <path d="M 5 35 A 35 35 0 0 1 75 35" stroke="url(#dialGradient)" stroke-dashoffset="{{ 110 - sentiment_score * 1.1 }}"/>
        </svg>
        <span class="dial-state">{{ sentiment_state }}</span>
    </div>
</div>
```

#### 4. Holographic Series Rail (Horizontal carousel)
- **Card Width:** 280px flex-shrink-0
- **Hover Effects:** translateY(-6px), scale(1.02), glow sweep animation
- **Play Icon:** Centered 56px red circle with opacity transition

```css
.series-card-holo:hover {
    border-color: var(--glass-border-hover);
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 30px 60px rgba(0,0,0,0.6), 0 0 40px rgba(220,38,38,0.15);
}
```

#### 5. Media Grid (3-column episode cards)
- **Featured Card:** Breathing glow animation via ::before pseudo-element
- **HUD Labels:** [EPISODE], [QUICK HIT], [INTEL BRIEF]
- **Dynamic Loop:** Renders episodes with `data-audio-url` for Web Audio API

```html
{% for episode in episodes or [] %}
<div class="episode-card {% if loop.first %}featured{% endif %}" 
     data-type="{{ episode.type }}" 
     {% if episode.audio_url %}data-audio-url="{{ episode.audio_url }}"{% endif %}>
    <span class="episode-hud-label">[{{ episode.type|upper }}]</span>
    ...
</div>
{% endfor %}
```

#### 6. Intel Sidebar (320px right column)
- **Live Intel Stream:** Value Stream posts with platform badges
- **Sarah's Tactical Note:** AI Analyst card with gradient background

```html
<aside class="intel-sidebar">
    <div class="sidebar-section">
        <div class="sidebar-title"><i class="fas fa-satellite-dish"></i> LIVE INTEL STREAM</div>
        {% for item in value_stream_items %}
        <div class="intel-packet">
            <div class="intel-source">{{ item.platform }}</div>
            <div class="intel-title">{{ item.title }}</div>
            <div class="intel-time">{{ item.time_ago }}</div>
        </div>
        {% endfor %}
    </div>
    <div class="sarah-note">
        <div class="sarah-avatar">S</div>
        <div class="sarah-text">{{ sarah_note }}</div>
    </div>
</aside>
```

#### 7. Books & Merch Section (3D Tilt Cards)
```css
.tilt-card {
    transform-style: preserve-3d;
    perspective: 1000px;
}
.tilt-card:hover .tilt-card-inner {
    transform: rotateY(-5deg) rotateX(5deg) translateZ(20px);
}
```

#### 8. Web Audio API Visualizer (Oscilloscope Bar)
```javascript
// Initialize AudioContext with AnalyserNode
function initAudioContext() {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 64;
    analyser.smoothingTimeConstant = 0.8;
    
    audioSource = audioContext.createMediaElementSource(audioElement);
    audioSource.connect(analyser);
    analyser.connect(audioContext.destination);
}

// Real frequency data visualization
function animateVisualizer() {
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(dataArray);
    
    for (let i = 0; i < bars.length; i++) {
        const height = (dataArray[i] / 255) * 35 + 5;
        bars[i].style.height = height + 'px';
    }
    requestAnimationFrame(animateVisualizer);
}
```

---

## JavaScript Features

### 1. Filter Chips (Episode Type Filtering)
```javascript
document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', function() {
        const filter = this.dataset.filter;
        document.querySelectorAll('.episode-card').forEach(card => {
            card.style.display = (filter === 'all' || card.dataset.type === filter) ? 'block' : 'none';
        });
    });
});
```

### 2. Episode Click → Audio Player Binding
```javascript
document.querySelectorAll('.episode-card').forEach(card => {
    card.addEventListener('click', function() {
        const audioUrl = this.dataset.audioUrl;
        if (audioUrl) {
            podcastAudio.src = audioUrl;
            podcastAudio.load();
            initAudioContext();
        }
        audioBar.style.display = 'flex';
        audioTitle.textContent = this.querySelector('.episode-title').textContent;
    });
});
```

### 3. Live Telemetry Updates
```javascript
async function updateTelemetry() {
    const res = await fetch('/api/network-stats');
    if (res.ok) {
        const data = await res.json();
        document.getElementById('mempoolSize').textContent = data.mempool_size;
        document.getElementById('feeRate').textContent = data.fee_rate + ' sat/vB';
        // ... more metrics
    }
}
setInterval(updateTelemetry, 60000);
```

### 4. Audio Progress Tracking
```javascript
audioElement.addEventListener('timeupdate', function() {
    const progress = (audioElement.currentTime / audioElement.duration) * 100;
    progressFill.style.width = progress + '%';
    currentTime.textContent = formatTime(audioElement.currentTime);
});
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     /media-terminal                          │
├─────────────────────────────────────────────────────────────┤
│  1. value_stream_service.get_value_stream(limit=5)          │
│     → Fetches recent Value Stream posts                     │
│     → Calculates time_ago display strings                   │
│                                                              │
│  2. SentimentSnapshot.query.order_by().first()              │
│     → Gets latest sentiment state (EQUILIBRIUM, etc.)       │
│     → Gets sentiment_score (0-100) for dial visualization   │
│                                                              │
│  3. Static original_series array                            │
│     → 4 shows: Cypherpunk'd, Big Print, 21M, Protocol Pulse │
│                                                              │
│  4. Template renders with Jinja2                            │
│     → SVG sentiment dial with dynamic stroke-dashoffset     │
│     → Episode cards with data-audio-url attributes          │
│     → Fallback demo episodes if no dynamic data             │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Client-Side Updates                        │
├─────────────────────────────────────────────────────────────┤
│  • /api/network-stats (every 60s) → Telemetry strip updates │
│  • Web Audio API → Real-time frequency visualization        │
│  • Episode click → Audio source binding + playback          │
└─────────────────────────────────────────────────────────────┘
```

---

## API Dependencies

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/network-stats` | GET | Live mempool, fees, hashrate data |
| `/series-guide/<key>` | GET | Series detail pages (navigation target) |

---

## Database Models Used

| Model | Fields Used |
|-------|-------------|
| `SentimentSnapshot` | `state_key`, `score`, `created_at` |
| `CuratedPost` (via Value Stream) | `platform`, `title`, `submitted_at` |

---

## Responsive Breakpoints

| Breakpoint | Layout Changes |
|------------|----------------|
| 1400px | Media grid: 3 → 2 columns |
| 1200px | Main grid: sidebar hidden, assets grid: 4 → 2 columns |
| 900px | Media grid: 2 → 1 column |
| 600px | Assets grid: 2 → 1 column |

---

## Key Technical Details

### Sentiment Dial Math
```html
stroke-dashoffset="{{ 110 - (sentiment_score or 65) * 1.1 }}"
<!-- score 0 → offset 110 (empty), score 100 → offset 0 (full) -->

<!-- Dial pointer position (on arc) -->
cx="{{ 40 + 30 * (0.0175 * score - 0.5) * 2 }}"
cy="{{ 35 - 30 * sqrt(1 - ((0.0175 * score - 0.5) * 2)^2) }}"
```

### Web Audio API Flow
1. User clicks episode card with `data-audio-url`
2. Audio element's `src` is set, `load()` called
3. `initAudioContext()` creates AudioContext + AnalyserNode
4. User clicks play → `audioElement.play()` + `animateVisualizer()`
5. `getByteFrequencyData()` drives 20 visualizer bars
6. Progress bar updates via `timeupdate` event

### 3D Tilt Effect
```css
.tilt-card:hover .tilt-card-inner {
    transform: rotateY(-5deg) rotateX(5deg) translateZ(20px);
}
/* Creates parallax depth effect on book/merch cards */
```

---

## Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `templates/media_terminal.html` | 1455 | Complete UI template |
| `routes.py` (lines 1037-1086) | 50 | Route handler |
| `services/value_stream_service.py` | N/A | Value Stream data |
| `models.py` (SentimentSnapshot) | N/A | Sentiment data |

---

*Last Updated: January 29, 2026*
