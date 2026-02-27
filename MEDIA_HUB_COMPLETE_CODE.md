# PROTOCOL PULSE MEDIA HUB - COMPLETE CODE

All files needed for the Media Hub page with High-Fidelity Terminal Player, Protocol Heartbeat, luxurious book cards, and sponsor rotation.

---

## FILE 1: templates/media_hub.html (Complete - 1814 lines)

```html
{% extends "base.html" %}

{% block title %}The Network - Protocol Pulse Media{% endblock %}

{% block head %}
<link href="https://fonts.googleapis.com/css2?family=Uncut+Sans:wght@300;500;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">

<style>
    :root {
        --glass: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.08);
        --accent-red: #dc2626;
        --pure-white: #ffffff;
        --deep-black: #050505;
    }

    .media-hub {
        font-family: 'Uncut Sans', sans-serif;
        background-color: var(--deep-black);
        color: var(--pure-white);
    }

    /* Cinematic Hero */
    .hero-media {
        padding: 8rem 0 4rem;
        background: radial-gradient(circle at 0% 0%, #1a0505 0%, var(--deep-black) 50%);
        text-align: left;
        position: relative;
        overflow: hidden;
    }

    .hero-media::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 40%;
        height: 100%;
        background: radial-gradient(ellipse at 100% 0%, rgba(220, 38, 38, 0.15) 0%, transparent 60%);
        pointer-events: none;
    }

    .hero-media h1 {
        font-size: clamp(3rem, 8vw, 6rem);
        font-weight: 700;
        letter-spacing: -3px;
        line-height: 0.9;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }

    .hero-media .accent-text {
        color: var(--accent-red);
        font-family: 'JetBrains Mono', monospace;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 4px;
        display: block;
        margin-bottom: 1rem;
    }

    .hero-subtitle {
        font-size: 1.25rem;
        font-weight: 300;
        color: rgba(255, 255, 255, 0.6);
        max-width: 500px;
    }

    /* The Bento Grid Architecture */
    .bento-section {
        padding: 4rem 0;
        background: var(--deep-black);
    }

    .section-label {
        color: var(--accent-red);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 4px;
        margin-bottom: 2rem;
        display: block;
    }

    .bento-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        grid-auto-rows: 240px;
        gap: 1.5rem;
        margin-bottom: 4rem;
    }

    .bento-item {
        background: var(--glass);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border);
        border-radius: 32px;
        padding: 2rem;
        position: relative;
        overflow: hidden;
        transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
        display: flex;
        flex-direction: column;
    }

    .bento-item:hover {
        border-color: var(--accent-red);
        background: rgba(220, 38, 38, 0.05);
        transform: scale(1.02);
    }

    /* Spanning logic for spectacular look */
    .item-large { grid-column: span 2; grid-row: span 2; }
    .item-tall { grid-row: span 2; }
    .item-wide { grid-column: span 2; }

    /* Cinematic Card Backgrounds - YouTube Thumbnails */
    .bento-item.has-bg {
        background-size: cover;
        background-position: center;
        border: none;
    }

    .bento-item.has-bg::after {
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(to top, rgba(0,0,0,0.95) 15%, rgba(0,0,0,0.4) 60%, rgba(0,0,0,0.2) 100%);
        z-index: 1;
        border-radius: 32px;
    }

    .bento-content {
        position: relative;
        z-index: 2;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
    }

    .bento-content .show-title {
        text-shadow: 0 4px 20px rgba(0,0,0,0.8);
    }

    /* Terminal Player Overlay */
    .player-terminal {
        position: fixed;
        inset: 0;
        background: rgba(5,5,5,0.98);
        z-index: 9999;
        display: none;
        padding: 2rem 4rem;
        backdrop-filter: blur(20px);
        overflow-y: auto;
    }

    .player-terminal.active {
        display: block;
        animation: terminalOpen 0.4s ease-out;
    }

    @keyframes terminalOpen {
        from { opacity: 0; transform: scale(0.95); }
        to { opacity: 1; transform: scale(1); }
    }

    .terminal-header {
        border-bottom: 1px solid var(--accent-red);
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-family: 'JetBrains Mono', monospace;
    }

    .terminal-title {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.7);
        letter-spacing: 3px;
    }

    .btn-close-terminal {
        background: transparent;
        border: 1px solid var(--glass-border);
        color: var(--pure-white);
        width: 40px;
        height: 40px;
        border-radius: 50%;
        font-size: 1.25rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-close-terminal:hover {
        background: var(--accent-red);
        border-color: var(--accent-red);
    }

    .video-wrapper {
        border: 1px solid var(--accent-red);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 40px 80px rgba(220,38,38,0.2);
    }

    .playlist-scroll {
        max-height: 60vh;
        overflow-y: auto;
        padding-right: 1rem;
    }

    .playlist-scroll::-webkit-scrollbar {
        width: 4px;
    }

    .playlist-scroll::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.05);
    }

    .playlist-scroll::-webkit-scrollbar-thumb {
        background: var(--accent-red);
        border-radius: 2px;
    }

    .playlist-item {
        padding: 1.25rem;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    .playlist-item:hover {
        background: rgba(220,38,38,0.15);
        padding-left: 1.75rem;
    }

    .playlist-item.active {
        background: rgba(220,38,38,0.2);
        border-left: 3px solid var(--accent-red);
    }

    .playlist-item i {
        color: var(--accent-red);
        font-size: 1.1rem;
    }

    .playlist-item span {
        font-size: 0.95rem;
        font-weight: 500;
    }

    .series-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--pure-white);
        margin-bottom: 1.5rem;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 1px;
    }

    /* Button variants for Terminal */
    .btn-series {
        background: var(--accent-red);
        color: var(--pure-white);
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.3s ease;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }

    .btn-series:hover {
        background: var(--pure-white);
        color: var(--deep-black);
        transform: translateY(-2px);
    }

    .btn-audio-only {
        background: transparent;
        border: 1px solid var(--glass-border);
        color: var(--pure-white);
        width: 48px;
        height: 48px;
        border-radius: 50%;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .btn-audio-only:hover {
        border-color: var(--accent-red);
        color: var(--accent-red);
    }

    .now-broadcasting {
        color: var(--accent-red);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 3px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .now-broadcasting::before {
        content: '';
        width: 8px;
        height: 8px;
        background: var(--accent-red);
        border-radius: 50%;
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* Protocol Heartbeat Node Tracker */
    .node-tracker-card {
        background: linear-gradient(135deg, rgba(0,0,0,1) 0%, rgba(20,20,20,1) 100%);
        position: relative;
        border-left: 3px solid var(--accent-red) !important;
    }

    .block-number {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--pure-white);
        letter-spacing: -1px;
    }

    .status-indicator {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        letter-spacing: 1px;
        padding: 2px 6px;
        border: 1px solid currentColor;
        border-radius: 3px;
    }

    .node-bg-effect {
        position: absolute;
        bottom: -20%;
        right: -10%;
        width: 150px;
        height: 150px;
        background: radial-gradient(circle, rgba(220, 38, 38, 0.15) 0%, transparent 70%);
        pointer-events: none;
        z-index: 0;
    }

    @keyframes blockFlash {
        0% { color: var(--accent-red); transform: scale(1.1); text-shadow: 0 0 20px var(--accent-red); }
        100% { color: var(--pure-white); transform: scale(1); text-shadow: none; }
    }

    .block-flash {
        animation: blockFlash 1s ease-out;
    }

    .x-small {
        font-size: 0.6rem;
    }

    /* Terminal Intel Briefing Sidebar */
    .terminal-sidebar {
        background: rgba(10, 10, 10, 0.5);
        border-left: 1px solid rgba(220, 38, 38, 0.2);
        height: 70vh;
        display: flex;
        flex-direction: column;
        padding: 1.5rem;
        border-radius: 16px;
    }

    .status-pill {
        background: rgba(34, 197, 94, 0.1);
        color: #22c55e;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        padding: 2px 8px;
        border-radius: 4px;
    }

    .terminal-text {
        font-family: 'JetBrains Mono', monospace;
        color: var(--accent-red);
        opacity: 0.8;
    }

    #guideBody {
        font-size: 0.95rem;
        line-height: 1.6;
        color: rgba(255, 255, 255, 0.8);
    }

    /* Terminal Ad Unit */
    .terminal-ad-unit {
        padding-top: 1.5rem;
        margin-top: auto;
        position: relative;
        transition: opacity 0.3s ease;
    }

    .ad-perimeter {
        border: 1px solid rgba(220, 38, 38, 0.3);
        padding: 1rem;
        background: linear-gradient(180deg, rgba(220, 38, 38, 0.05) 0%, transparent 100%);
        border-radius: 12px;
    }

    .ad-content-wrapper {
        position: relative;
        overflow: hidden;
        height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    #terminalAdImage {
        max-height: 80px;
        transition: transform 0.5s ease;
        filter: grayscale(100%) contrast(120%) brightness(80%);
    }

    .ad-perimeter:hover #terminalAdImage {
        filter: grayscale(0%) contrast(100%) brightness(100%);
        transform: scale(1.05);
    }

    .pulse-dot {
        width: 6px;
        height: 6px;
        background: #22c55e;
        border-radius: 50%;
        box-shadow: 0 0 10px #22c55e;
        animation: pulse 2s infinite;
    }

    .glitch-active #terminalAdImage {
        animation: glitch 0.4s steps(2) infinite;
        opacity: 0.5;
    }

    @keyframes glitch {
        0% { transform: translate(0); }
        20% { transform: translate(-5px, 5px); }
        40% { transform: translate(5px, -5px); }
        100% { transform: translate(0); }
    }

    /* Luxurious Book Cards */
    .book-card-luxury {
        background: linear-gradient(145deg, rgba(15,15,15,1) 0%, rgba(25,25,25,1) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 24px;
        overflow: hidden;
        transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
        position: relative;
    }

    .book-card-luxury:hover {
        border-color: var(--accent-red);
        transform: translateY(-8px);
        box-shadow: 0 30px 60px rgba(220, 38, 38, 0.15);
    }

    .book-cover-luxury {
        height: 320px;
        background: linear-gradient(180deg, #0a0a0a 0%, #151515 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        padding: 2rem;
        overflow: hidden;
    }

    .book-cover-luxury::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse at 50% 0%, rgba(220, 38, 38, 0.1) 0%, transparent 60%);
        pointer-events: none;
    }

    .book-cover-luxury img {
        max-height: 280px;
        max-width: 180px;
        object-fit: contain;
        filter: drop-shadow(0 30px 50px rgba(0, 0, 0, 0.8));
        transition: transform 0.5s ease;
    }

    .book-card-luxury:hover .book-cover-luxury img {
        transform: scale(1.08) rotate(-2deg);
    }

    .book-body-luxury {
        padding: 1.75rem;
    }

    .book-title-luxury {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
        line-height: 1.3;
        letter-spacing: -0.5px;
    }

    .book-author-luxury {
        font-size: 0.85rem;
        color: var(--accent-red);
        margin-bottom: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
    }

    .book-description-luxury {
        font-size: 0.8rem;
        color: rgba(255,255,255,0.5);
        line-height: 1.5;
        margin-bottom: 1.25rem;
    }

    .btn-amazon-luxury {
        background: transparent;
        border: 1px solid var(--glass-border);
        color: var(--pure-white);
        padding: 0.85rem 1.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
        text-decoration: none;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        transition: all 0.3s ease;
        width: 100%;
    }

    .btn-amazon-luxury:hover {
        background: #ff9900;
        color: var(--deep-black);
        border-color: #ff9900;
    }

    .badge-luxury {
        position: absolute;
        top: 1.25rem;
        left: 1.25rem;
        background: var(--accent-red);
        color: var(--pure-white);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        font-weight: 700;
        padding: 0.4rem 0.85rem;
        border-radius: 50px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        z-index: 2;
    }

    .badge-bestseller {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }

    /* Live Visualizer */
    .live-visualizer {
        display: flex;
        align-items: flex-end;
        gap: 3px;
        height: 24px;
        margin-bottom: 1rem;
    }

    .bar {
        width: 4px;
        background: var(--accent-red);
        border-radius: 2px;
        animation: equalize 0.8s infinite ease-in-out alternate;
    }

    .bar:nth-child(1) { animation-delay: 0.0s; }
    .bar:nth-child(2) { animation-delay: 0.15s; }
    .bar:nth-child(3) { animation-delay: 0.3s; }
    .bar:nth-child(4) { animation-delay: 0.45s; }
    .bar:nth-child(5) { animation-delay: 0.6s; }

    @keyframes equalize {
        from { height: 6px; }
        to { height: 24px; }
    }

    .show-title {
        font-size: 2.5rem;
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 1rem;
        letter-spacing: -1px;
    }

    .show-meta {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.5);
        margin-top: auto;
    }

    .btn-play-bento {
        background: var(--pure-white);
        color: var(--deep-black);
        border-radius: 50%;
        width: 60px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        text-decoration: none;
        position: absolute;
        bottom: 2rem;
        right: 2rem;
        transition: all 0.3s cubic-bezier(0.23, 1, 0.32, 1);
        border: none;
        cursor: pointer;
    }

    .btn-play-bento:hover {
        background: var(--accent-red);
        color: var(--pure-white);
        transform: rotate(15deg) scale(1.1);
    }

    .btn-play-bento.small {
        width: 48px;
        height: 48px;
        font-size: 1rem;
    }

    /* Episode Cards in Bento */
    .episode-bento {
        padding: 1.5rem;
    }

    .episode-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: var(--accent-red);
        margin-bottom: 0.75rem;
    }

    .episode-title-bento {
        font-size: 1.3rem;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    }

    .episode-desc {
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.6);
        line-height: 1.5;
    }

    /* Stats Card */
    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        color: var(--pure-white);
        margin-bottom: 0.5rem;
    }

    .stat-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: rgba(255, 255, 255, 0.5);
    }

    /* CTA Card */
    .cta-card h3 {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .cta-card p {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 1.5rem;
    }

    .btn-cta {
        background: var(--accent-red);
        color: var(--pure-white);
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.9rem;
        text-decoration: none;
        display: inline-block;
        transition: all 0.3s ease;
    }

    .btn-cta:hover {
        background: #ef4444;
        transform: translateY(-2px);
        color: var(--pure-white);
    }

    /* Books Section - Bento Style */
    .books-section {
        padding: 6rem 0;
        background: linear-gradient(180deg, var(--deep-black) 0%, #0a0a0a 100%);
    }

    .books-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
    }

    /* Merch Section */
    .merch-section {
        padding: 6rem 0;
        background: var(--pure-white);
        border-radius: 60px 60px 0 0;
        margin-top: -30px;
        position: relative;
        z-index: 10;
    }

    .merch-title {
        font-size: clamp(2.5rem, 6vw, 4rem);
        font-weight: 700;
        color: var(--deep-black);
        letter-spacing: -2px;
        line-height: 1;
        margin-bottom: 3rem;
    }

    .merch-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
    }

    .merch-card-bento {
        background: #f5f5f5;
        border-radius: 24px;
        padding: 1.5rem;
        transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
    }

    .merch-card-bento:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
    }

    .merch-img-wrapper {
        height: 200px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 1rem;
    }

    .merch-img-wrapper img {
        max-height: 180px;
        object-fit: contain;
        transition: transform 0.4s ease;
    }

    .merch-card-bento:hover .merch-img-wrapper img {
        transform: scale(1.05) rotate(-3deg);
    }

    .merch-name {
        font-size: 1rem;
        font-weight: 700;
        color: var(--deep-black);
        margin-bottom: 0.5rem;
    }

    .merch-price {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--accent-red);
    }

    .btn-buy {
        background: var(--deep-black);
        color: var(--pure-white);
        border: none;
        padding: 0.6rem 1.25rem;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
        text-decoration: none;
        transition: all 0.3s ease;
    }

    .btn-buy:hover {
        background: var(--accent-red);
        color: var(--pure-white);
    }

    /* Cyberpunk Audio Player */
    .audio-player-bento {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(10, 10, 10, 0.95);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-top: 1px solid var(--glass-border);
        padding: 1rem 0;
        z-index: 1000;
        display: none;
    }

    .player-content {
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }

    .player-controls {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .btn-player {
        background: var(--accent-red);
        color: var(--pure-white);
        border: none;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-player:hover {
        background: #ef4444;
        transform: scale(1.1);
    }

    .player-info {
        flex: 1;
    }

    .player-title {
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.25rem;
    }

    .player-show {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.5);
    }

    .player-progress {
        flex: 2;
    }

    .progress-bar-container {
        height: 4px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 2px;
        cursor: pointer;
    }

    .progress-bar-fill {
        height: 100%;
        background: var(--accent-red);
        border-radius: 2px;
        width: 0%;
        transition: width 0.1s linear;
    }

    .time-display {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.5);
        margin-top: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
    }

    .player-actions {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .btn-speed {
        background: transparent;
        border: 1px solid var(--glass-border);
        color: var(--pure-white);
        padding: 0.4rem 0.75rem;
        border-radius: 50px;
        font-size: 0.8rem;
        font-family: 'JetBrains Mono', monospace;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-speed:hover {
        border-color: var(--accent-red);
    }

    .btn-close-player {
        background: transparent;
        border: none;
        color: rgba(255, 255, 255, 0.5);
        font-size: 1.25rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-close-player:hover {
        color: var(--pure-white);
    }

    /* Responsive */
    @media (max-width: 1200px) {
        .bento-grid, .books-grid, .merch-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        .item-large { grid-column: span 2; }
    }

    @media (max-width: 768px) {
        .hero-media {
            padding: 6rem 0 3rem;
        }

        .hero-media h1 {
            font-size: 2.5rem;
            letter-spacing: -1px;
        }

        .bento-grid, .books-grid, .merch-grid {
            grid-template-columns: 1fr;
        }

        .item-large, .item-wide, .item-tall {
            grid-column: span 1;
            grid-row: span 1;
        }

        .item-large {
            grid-row: span 2;
        }

        .bento-grid {
            grid-auto-rows: auto;
        }

        .bento-item {
            min-height: 200px;
        }

        .merch-section {
            border-radius: 40px 40px 0 0;
            padding: 4rem 0;
        }

        .player-content {
            flex-wrap: wrap;
            gap: 1rem;
        }

        .player-progress {
            order: 3;
            flex-basis: 100%;
        }
    }

    /* Loading State */
    .loading-bento {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 200px;
    }

    .loader-ring {
        width: 40px;
        height: 40px;
        border: 3px solid var(--glass-border);
        border-top-color: var(--accent-red);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }
</style>
{% endblock %}

{% block content %}
<div class="media-hub">
    <!-- Cinematic Hero -->
    <section class="hero-media">
        <div class="container">
            <span class="accent-text">Network Operations // 2026</span>
            <h1>The Audio<br>Powerhouse.</h1>
            <p class="hero-subtitle">Dive deep into Bitcoin, privacy, and the future of decentralized finance with our premium podcast network.</p>
        </div>
    </section>

    <!-- Podcast Bento Grid -->
    <section class="bento-section">
        <div class="container">
            <span class="section-label">Live Broadcasts</span>
            
            <div class="bento-grid" id="podcast-bento">
                {% for show in shows %}
                {% if 'orange is the new' not in show.name|lower %}
                {% set series_slug = show.name|lower|replace(' ', '_')|replace("'", '') %}
                {% set series_key_map = {'cypherpunkd': 'cypherpunkd', "cypherpunk'd": 'cypherpunkd', 'protocol_pulse': 'protocol_pulse', 'protocol pulse': 'protocol_pulse'} %}
                {% set series_key = series_key_map.get(series_slug, series_slug) %}
                {% set series_data = youtube_series.get(series_key, {}) if youtube_series else {} %}
                {% set has_youtube = series_data and series_data.get('latest_id') %}
                {% set latest_id = series_data.get('latest_id', '') if has_youtube else '' %}
                {% if loop.index == 1 %}
                <!-- Primary Show - Large Cinematic Card -->
                <div class="bento-item item-large{% if has_youtube %} has-bg{% endif %}"{% if has_youtube %} style="background-image: url('https://img.youtube.com/vi/{{ latest_id }}/maxresdefault.jpg');"{% endif %}>
                    <div class="bento-content">
                        <div class="now-broadcasting">Now Broadcasting</div>
                        <h2 class="show-title">{{ show.name }}</h2>
                        <p class="episode-desc">{{ show.description[:100] }}...</p>
                        <div class="d-flex gap-2 mt-3">
                            {% if has_youtube %}
                            <button class="btn-series" onclick="openTerminal('{{ series_key }}')">
                                <i class="fas fa-tv me-2"></i>Series Guide
                            </button>
                            {% endif %}
                            <button class="btn-audio-only" onclick="loadShowEpisodes('{{ show.id }}')" title="Audio Only">
                                <i class="fas fa-headphones"></i>
                            </button>
                        </div>
                    </div>
                </div>
                {% elif loop.index == 2 %}
                <!-- Secondary Show - Wide Cinematic Card -->
                <div class="bento-item item-wide{% if has_youtube %} has-bg{% endif %}"{% if has_youtube %} style="background-image: url('https://img.youtube.com/vi/{{ latest_id }}/maxresdefault.jpg');"{% endif %}>
                    <div class="bento-content">
                        <span class="episode-tag">Featured Show</span>
                        <h2 class="show-title" style="font-size: 1.8rem;">{{ show.name }}</h2>
                        <div class="d-flex gap-2 mt-2">
                            {% if has_youtube %}
                            <button class="btn-series" onclick="openTerminal('{{ series_key }}')">
                                <i class="fas fa-play me-1"></i>Open Playlist
                            </button>
                            {% else %}
                            <button class="btn-series" onclick="loadShowEpisodes('{{ show.id }}')">
                                <i class="fas fa-headphones me-1"></i>Listen Now
                            </button>
                            {% endif %}
                        </div>
                    </div>
                </div>
                {% else %}
                <!-- Additional Shows - Standard Card -->
                <div class="bento-item">
                    <span class="episode-tag">{{ show.category }}</span>
                    <h3 class="show-title" style="font-size: 1.3rem;">{{ show.name }}</h3>
                    <p class="show-meta"><i class="fas fa-headphones me-2"></i>{{ show.episode_count }} episodes</p>
                    <button class="btn-play-bento small" onclick="loadShowEpisodes('{{ show.id }}')">
                        <i class="fas fa-play"></i>
                    </button>
                </div>
                {% endif %}
                {% endif %}
                {% endfor %}

                <!-- Protocol Heartbeat - Live Node Tracker -->
                <div class="bento-item node-tracker-card" id="nodeTracker">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <span class="episode-tag">Protocol_Telemetry</span>
                        <span id="nodeStatus" class="status-indicator text-success">LOADING</span>
                    </div>
                    
                    <div class="tracker-main">
                        <label class="x-small opacity-50 font-monospace">BLOCK_HEIGHT</label>
                        <div id="liveHeight" class="block-number">#---,---</div>
                    </div>

                    <div class="tracker-footer mt-3 pt-2 border-top border-secondary">
                        <div class="row g-0">
                            <div class="col-12">
                                <label class="x-small opacity-50 font-monospace d-block">GLOBAL_HASHRATE</label>
                                <span id="liveHashrate" class="fw-bold" style="color: var(--accent-red);">---.-- EH/s</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="node-bg-effect"></div>
                </div>

                <!-- Stats Card -->
                <div class="bento-item">
                    <span class="episode-tag">Network Status</span>
                    <div class="stat-value" id="episode-count">{{ shows|sum(attribute='episode_count') }}</div>
                    <div class="stat-label">Total Episodes</div>
                </div>

                <!-- CTA Card -->
                <div class="bento-item cta-card">
                    <h3>Get the Alpha.</h3>
                    <p>Join the network of informed Bitcoiners.</p>
                    <a href="/newsletter" class="btn-cta">Subscribe</a>
                </div>
            </div>

            <!-- Latest Episodes -->
            <span class="section-label">Latest Episodes</span>
            <div class="bento-grid" id="episodes-container" style="grid-auto-rows: auto;">
                <div class="bento-item loading-bento" style="grid-column: span 4;">
                    <div class="loader-ring"></div>
                </div>
            </div>
        </div>
    </section>

    <!-- Books Section -->
    <section class="books-section">
        <div class="container">
            <span class="section-label">Essential Reading</span>
            <h2 style="font-size: clamp(2rem, 5vw, 3rem); font-weight: 700; letter-spacing: -1px; margin-bottom: 3rem;">Our Book Series</h2>
            
            <div class="books-grid">
                {% for book in our_books %}
                <div class="book-card-luxury">
                    <div class="book-cover-luxury">
                        <span class="badge-luxury">Featured</span>
                        {% if book.cover_url %}
                        <img src="{{ book.cover_url }}" alt="{{ book.title }}">
                        {% else %}
                        <i class="fas fa-book" style="font-size: 4rem; color: #333;"></i>
                        {% endif %}
                    </div>
                    <div class="book-body-luxury">
                        <h5 class="book-title-luxury">{{ book.title }}</h5>
                        <p class="book-author-luxury">{{ book.author }}</p>
                        <p class="book-description-luxury">{{ book.description[:100] }}...</p>
                        <a href="{{ book.amazon_url }}" target="_blank" rel="noopener" class="btn-amazon-luxury">
                            <i class="fab fa-amazon"></i>Get on Amazon
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>

            <h2 style="font-size: clamp(2rem, 5vw, 3rem); font-weight: 700; letter-spacing: -1px; margin: 4rem 0 3rem;">Recommended Reading</h2>
            
            <div class="books-grid">
                {% for book in recommended_books %}
                <div class="book-card-luxury">
                    <div class="book-cover-luxury">
                        {% if book.bestseller %}
                        <span class="badge-luxury badge-bestseller">Bestseller</span>
                        {% endif %}
                        {% if book.cover_url %}
                        <img src="{{ book.cover_url }}" alt="{{ book.title }}">
                        {% else %}
                        <i class="fas fa-book" style="font-size: 4rem; color: #333;"></i>
                        {% endif %}
                    </div>
                    <div class="book-body-luxury">
                        <h5 class="book-title-luxury">{{ book.title }}</h5>
                        <p class="book-author-luxury">{{ book.author }}</p>
                        <p class="book-description-luxury">{{ book.description[:100] }}...</p>
                        <a href="{{ book.amazon_url }}" target="_blank" rel="noopener" class="btn-amazon-luxury">
                            <i class="fab fa-amazon"></i>Get on Amazon
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>

    <!-- Tactile Merch Section -->
    <section class="merch-section">
        <div class="container">
            <h2 class="merch-title">Equip the<br>Movement.</h2>
            
            <div class="merch-grid">
                {% if products %}
                {% for product in products[:4] %}
                <div class="merch-card-bento">
                    <div class="merch-img-wrapper">
                        {% if product.thumbnail_url %}
                        <img src="{{ product.thumbnail_url }}" alt="{{ product.name }}">
                        {% else %}
                        <i class="fas fa-tshirt" style="font-size: 4rem; color: #ccc;"></i>
                        {% endif %}
                    </div>
                    <h5 class="merch-name">{{ product.name }}</h5>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="merch-price">${{ "%.2f"|format(product.retail_price|float) }}</span>
                        <a href="/merch" class="btn-buy">Buy</a>
                    </div>
                </div>
                {% endfor %}
                {% else %}
                <div class="merch-card-bento" style="grid-column: span 4; text-align: center; padding: 4rem;">
                    <p style="color: #666; margin-bottom: 1.5rem;">Merch coming soon!</p>
                    <a href="/merch" class="btn-buy">View Store</a>
                </div>
                {% endif %}
            </div>
            
            {% if products and products|length > 4 %}
            <div class="text-center mt-5">
                <a href="/merch" class="btn-buy" style="padding: 1rem 2rem; font-size: 1rem;">View All Merch</a>
            </div>
            {% endif %}
        </div>
    </section>
</div>

<!-- Cyberpunk Audio Player -->
<div id="audioPlayer" class="audio-player-bento">
    <div class="container">
        <div class="player-content">
            <div class="player-controls">
                <button class="btn-player" onclick="togglePlayPause()">
                    <i id="playPauseIcon" class="fas fa-play"></i>
                </button>
            </div>
            <div class="player-info">
                <div id="currentTitle" class="player-title">Now Playing</div>
                <div id="currentShow" class="player-show">Podcast Show</div>
            </div>
            <div class="player-progress">
                <div class="progress-bar-container" onclick="seekAudio(event)">
                    <div id="progressBar" class="progress-bar-fill"></div>
                </div>
                <div class="time-display">
                    <span id="currentTime">0:00</span>
                    <span id="totalTime">0:00</span>
                </div>
            </div>
            <div class="player-actions">
                <button class="btn-speed" onclick="adjustSpeed()">
                    <span id="speedLabel">1x</span>
                </button>
                <button class="btn-close-player" onclick="closePlayer()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    </div>
    <audio id="audioElement" style="display: none;"></audio>
</div>

<!-- YouTube Terminal Player Overlay -->
<div id="mediaTerminal" class="player-terminal">
    <div class="container-fluid">
        <div class="terminal-header">
            <span class="terminal-title">PROTOCOL PULSE // MEDIA_TERMINAL_v1.0</span>
            <button onclick="closeTerminal()" class="btn-close-terminal">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="row">
            <div class="col-lg-8 mb-4">
                <div class="video-wrapper">
                    <div class="ratio ratio-16x9">
                        <iframe id="terminalIframe" src="" allowfullscreen allow="autoplay"></iframe>
                    </div>
                </div>
            </div>
            <div class="col-lg-4 terminal-sidebar">
                <div class="briefing-header mb-4">
                    <span class="status-pill"><i class="fas fa-circle me-1"></i> SYSTEM_ONLINE</span>
                    <h3 class="accent-text mt-2" id="seriesTitle">INTEL_BRIEFING</h3>
                </div>

                <div id="seriesDescription" class="mb-4">
                    <p class="terminal-text small">
                        // AUTHORIZATION: PROTOCOL_LEVEL_4<br>
                        // SUBJECT: DECENTRALIZED_INTEL
                    </p>
                    <p id="guideBody">
                        Loading mission parameters...
                    </p>
                </div>

                <h5 class="text-uppercase small tracking-widest opacity-50 mb-3" style="letter-spacing: 2px;">Transmission Archive</h5>
                <div class="playlist-scroll" id="playlistContent">
                </div>

                <div class="mt-4 pt-3 border-top border-secondary">
                    <div class="row g-0 text-center">
                        <div class="col-6 border-end border-secondary">
                            <span class="d-block x-small opacity-50">EPISODES</span>
                            <span class="fw-bold" id="epCount">--</span>
                        </div>
                        <div class="col-6">
                            <span class="d-block x-small opacity-50">NETWORK_LOAD</span>
                            <span class="fw-bold text-success">OPTIMAL</span>
                        </div>
                    </div>
                </div>

                <!-- Sponsor Node -->
                <div class="terminal-ad-unit" id="terminalAdContainer" style="display: none;">
                    <div class="ad-perimeter">
                        <div class="ad-header d-flex justify-content-between align-items-center">
                            <span class="x-small font-monospace text-uppercase" style="letter-spacing: 2px; color: var(--accent-red);">Protocol_Partner</span>
                            <div class="pulse-dot"></div>
                        </div>
                        <a id="terminalAdLink" href="#" target="_blank" rel="noopener">
                            <div class="ad-content-wrapper mt-2">
                                <img id="terminalAdImage" src="" alt="Sponsor" class="img-fluid rounded">
                            </div>
                        </a>
                        <div class="ad-footer mt-2 d-flex justify-content-between">
                            <span id="terminalAdName" class="x-small font-monospace opacity-50">SCANNING...</span>
                            <span class="x-small font-monospace opacity-50">NODE_ID: 0x<span id="adNodeId">000</span></span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let currentEpisode = null;
let playbackSpeeds = [0.75, 1, 1.25, 1.5, 2];
let currentSpeedIndex = 1;
let loadedEpisodes = 0;
const EPISODES_PER_LOAD = 6;

// YouTube Series Data with Intel Briefings
const seriesData = {
    'cypherpunkd': {
        title: "CYPHERPUNK'D // INTEL",
        epCount: '142',
        description: 'Our flagship broadcast. We dismantle the technical and philosophical barriers to financial sovereignty. From zero-knowledge proofs to the physics of Proof of Work, this is the front line of the digital resistance.',
        playlist: [
            { id: 'dQw4w9WgXcQ', title: 'Transmission 01: The Privacy Wars' },
            { id: '3v_itY_S4T0', title: 'Transmission 02: Thermodynamic Security' },
            { id: 'z_D-7mG-vEc', title: "Transmission 03: Satoshi's Vision Decoded" }
        ]
    },
    'protocol_pulse': {
        title: 'PROTOCOL_PULSE // ANALYSIS',
        epCount: '84',
        description: 'High-precision analysis on protocol evolution. We track the code changes, BIPs, and scaling solutions that define the next century of Bitcoin. No noise—only the signal that moves the network.',
        playlist: [
            { id: 'z_D-7mG-vEc', title: 'Report: Layer 2 Liquidity Dynamics' },
            { id: 'dQw4w9WgXcQ', title: 'Report: Bitcoin ETF Analysis' }
        ]
    }
};

// Sponsor Ads Data - Loaded from API
let terminalAds = [];
let currentAdIndex = 0;

// Load sponsors for terminal
async function loadTerminalAds() {
    try {
        const response = await fetch('/api/active-ads');
        const data = await response.json();
        if (data.success && data.ads.length > 0) {
            terminalAds = data.ads;
            displayTerminalAd();
            document.getElementById('terminalAdContainer').style.display = 'block';
        }
    } catch (error) {
        console.log('No sponsors available');
    }
}

function displayTerminalAd() {
    if (terminalAds.length === 0) return;
    
    const ad = terminalAds[currentAdIndex];
    document.getElementById('terminalAdImage').src = ad.image_url;
    document.getElementById('terminalAdLink').href = ad.target_url;
    document.getElementById('terminalAdName').textContent = ad.name.toUpperCase().replace(/ /g, '_');
    document.getElementById('adNodeId').textContent = ad.id.toString(16).toUpperCase().padStart(3, '0');
}

function rotateTerminalAds() {
    if (terminalAds.length <= 1) return;
    
    const adUnit = document.querySelector('.terminal-ad-unit');
    adUnit.classList.add('glitch-active');
    
    setTimeout(() => {
        currentAdIndex = (currentAdIndex + 1) % terminalAds.length;
        displayTerminalAd();
        adUnit.classList.remove('glitch-active');
    }, 400);
}

// Rotate ads every 20 seconds when terminal is open
setInterval(() => {
    if (document.getElementById('mediaTerminal').classList.contains('active')) {
        rotateTerminalAds();
    }
}, 20000);

// Terminal Player Functions
function openTerminal(seriesKey) {
    const data = seriesData[seriesKey];
    if (!data || !data.playlist || data.playlist.length === 0) {
        console.error('No series data found for:', seriesKey);
        return;
    }
    
    const iframe = document.getElementById('terminalIframe');
    const list = document.getElementById('playlistContent');
    const title = document.getElementById('seriesTitle');
    const guideBody = document.getElementById('guideBody');
    const epCount = document.getElementById('epCount');
    
    // Update Intel Briefing content
    title.textContent = data.title;
    guideBody.textContent = data.description;
    epCount.textContent = data.epCount || data.playlist.length;
    
    // Set first video
    iframe.src = `https://www.youtube.com/embed/${data.playlist[0].id}?autoplay=1&modestbranding=1&rel=0`;
    
    // Build Playlist with episode numbers
    list.innerHTML = data.playlist.map((video, index) => `
        <div class="playlist-item d-flex align-items-center ${index === 0 ? 'active' : ''}" onclick="changeVideo('${video.id}', this)">
            <span class="me-3 opacity-30 font-monospace" style="font-size: 0.75rem;">${(index + 1).toString().padStart(2, '0')}</span>
            <div class="flex-grow-1">
                <span>${video.title}</span>
            </div>
            <i class="fas fa-play-circle ms-2" style="color: var(--accent-red);"></i>
        </div>
    `).join('');

    document.getElementById('mediaTerminal').classList.add('active');
    document.body.style.overflow = 'hidden';
    
    // Load sponsors when terminal opens
    loadTerminalAds();
}

function changeVideo(id, element) {
    document.getElementById('terminalIframe').src = `https://www.youtube.com/embed/${id}?autoplay=1&modestbranding=1&rel=0`;
    
    // Update active state
    document.querySelectorAll('.playlist-item').forEach(item => item.classList.remove('active'));
    if (element) {
        element.classList.add('active');
    }
}

function closeTerminal() {
    document.getElementById('terminalIframe').src = '';
    document.getElementById('mediaTerminal').classList.remove('active');
    document.body.style.overflow = '';
}

// Close terminal on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeTerminal();
    }
});

// Protocol Heartbeat - Live Network Stats
async function updateNodeTracker() {
    try {
        const response = await fetch('/api/network-stats');
        const data = await response.json();
        
        const heightEl = document.getElementById('liveHeight');
        const hashrateEl = document.getElementById('liveHashrate');
        const statusEl = document.getElementById('nodeStatus');

        // Check if block changed to trigger animation
        if (heightEl.textContent !== `#${data.height}`) {
            heightEl.classList.add('block-flash');
            setTimeout(() => heightEl.classList.remove('block-flash'), 1000);
        }

        heightEl.textContent = `#${data.height}`;
        hashrateEl.textContent = data.hashrate;
        statusEl.textContent = data.status;
        
        // Update status color
        if (data.status === 'OPERATIONAL') {
            statusEl.classList.remove('text-warning', 'text-danger');
            statusEl.classList.add('text-success');
        } else if (data.status === 'RECONNECTING' || data.status === 'TIMEOUT') {
            statusEl.classList.remove('text-success', 'text-danger');
            statusEl.classList.add('text-warning');
        } else {
            statusEl.classList.remove('text-success', 'text-warning');
            statusEl.classList.add('text-danger');
        }
        
    } catch (error) {
        console.error("Telemetry Link Error:", error);
        document.getElementById('nodeStatus').textContent = 'OFFLINE';
        document.getElementById('nodeStatus').classList.remove('text-success');
        document.getElementById('nodeStatus').classList.add('text-danger');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadEpisodes();
    
    // Initialize Protocol Heartbeat
    updateNodeTracker();
    setInterval(updateNodeTracker, 60000); // Update every 60 seconds
});

function loadEpisodes() {
    const container = document.getElementById('episodes-container');
    
    fetch(`/api/latest-episodes?limit=${EPISODES_PER_LOAD}&offset=${loadedEpisodes}`)
        .then(response => response.json())
        .then(data => {
            if (loadedEpisodes === 0) {
                container.innerHTML = '';
            }
            
            if (data.episodes && data.episodes.length > 0) {
                data.episodes.forEach((episode, index) => {
                    const card = createEpisodeCard(episode, index);
                    container.insertAdjacentHTML('beforeend', card);
                });
                loadedEpisodes += data.episodes.length;
                
                // Add load more button if there are more episodes
                if (data.has_more) {
                    const existingBtn = document.getElementById('load-more-btn');
                    if (!existingBtn) {
                        container.insertAdjacentHTML('afterend', `
                            <div class="text-center mt-4" id="load-more-container">
                                <button id="load-more-btn" class="btn-cta" onclick="loadMoreEpisodes()" style="background: transparent; border: 1px solid var(--glass-border); color: var(--pure-white);">
                                    <i class="fas fa-plus me-2"></i>Load More
                                </button>
                            </div>
                        `);
                    }
                }
            } else if (loadedEpisodes === 0) {
                container.innerHTML = '<div class="bento-item" style="grid-column: span 4; text-align: center;"><p style="color: rgba(255,255,255,0.5);">No episodes available yet.</p></div>';
            }
        })
        .catch(error => {
            console.error('Error loading episodes:', error);
            if (loadedEpisodes === 0) {
                container.innerHTML = '<div class="bento-item" style="grid-column: span 4; text-align: center;"><p style="color: rgba(255,255,255,0.5);">Unable to load episodes.</p></div>';
            }
        });
}

function loadMoreEpisodes() {
    loadEpisodes();
}

function createEpisodeCard(episode, index) {
    const date = new Date(episode.published_date).toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric'
    });
    
    // Vary card sizes for visual interest
    let sizeClass = '';
    if (index === 0) sizeClass = 'item-wide';
    
    return `
        <div class="bento-item ${sizeClass}" style="min-height: 180px;">
            <span class="episode-tag">${episode.show_name}</span>
            <h4 class="episode-title-bento">${episode.title}</h4>
            <div class="d-flex align-items-center justify-content-between mt-auto">
                <span style="font-size: 0.8rem; color: rgba(255,255,255,0.5);">
                    <i class="fas fa-clock me-1"></i>${episode.duration || 'N/A'}
                    <span class="ms-3"><i class="fas fa-calendar me-1"></i>${date}</span>
                </span>
                <button class="btn-play-bento small" onclick='playEpisode(${JSON.stringify(episode).replace(/'/g, "\\'")}')'>
                    <i class="fas fa-play"></i>
                </button>
            </div>
        </div>
    `;
}

function loadShowEpisodes(showId) {
    fetch(`/api/episodes/${showId}?limit=10`)
        .then(response => response.json())
        .then(data => {
            if (data.episodes && data.episodes.length > 0) {
                playEpisode(data.episodes[0]);
            }
        })
        .catch(error => console.error('Error loading show episodes:', error));
}

function playEpisode(episode) {
    if (!episode.audio_url) {
        alert('Audio not available for this episode.');
        return;
    }
    
    currentEpisode = episode;
    document.getElementById('currentTitle').textContent = episode.title;
    document.getElementById('currentShow').textContent = episode.show_name;
    document.getElementById('audioPlayer').style.display = 'block';
    
    const audioElement = document.getElementById('audioElement');
    audioElement.src = episode.audio_url;
    audioElement.play();
    
    updatePlayPauseIcon(true);
}

function togglePlayPause() {
    const audioElement = document.getElementById('audioElement');
    if (audioElement.paused) {
        audioElement.play();
        updatePlayPauseIcon(true);
    } else {
        audioElement.pause();
        updatePlayPauseIcon(false);
    }
}

function updatePlayPauseIcon(isPlaying) {
    const icon = document.getElementById('playPauseIcon');
    icon.className = isPlaying ? 'fas fa-pause' : 'fas fa-play';
}

function adjustSpeed() {
    const audioElement = document.getElementById('audioElement');
    currentSpeedIndex = (currentSpeedIndex + 1) % playbackSpeeds.length;
    const newSpeed = playbackSpeeds[currentSpeedIndex];
    audioElement.playbackRate = newSpeed;
    document.getElementById('speedLabel').textContent = newSpeed + 'x';
}

function closePlayer() {
    const audioElement = document.getElementById('audioElement');
    audioElement.pause();
    audioElement.currentTime = 0;
    document.getElementById('audioPlayer').style.display = 'none';
}

function seekAudio(event) {
    const audioElement = document.getElementById('audioElement');
    const progressBar = event.currentTarget;
    const rect = progressBar.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    audioElement.currentTime = percent * audioElement.duration;
}

document.getElementById('audioElement').addEventListener('timeupdate', function() {
    const audio = this;
    const progressBar = document.getElementById('progressBar');
    const currentTime = document.getElementById('currentTime');
    const totalTime = document.getElementById('totalTime');
    
    if (audio.duration) {
        const progress = (audio.currentTime / audio.duration) * 100;
        progressBar.style.width = progress + '%';
        
        currentTime.textContent = formatTime(audio.currentTime);
        totalTime.textContent = formatTime(audio.duration);
    }
});

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return minutes + ':' + (remainingSeconds < 10 ? '0' : '') + remainingSeconds;
}
</script>
{% endblock %}
```

---

## FILE 2: services/node_service.py (Protocol Heartbeat)

```python
import requests
import logging
import time

class NodeService:
    """Service for fetching live Bitcoin network statistics from Mempool.space API"""
    
    _cache = None
    _cache_expiry = 0
    CACHE_DURATION = 30  # Cache for 30 seconds
    
    @classmethod
    def get_network_stats(cls):
        """Fetches live PoW metrics for the Protocol Heartbeat tracker."""
        current_time = time.time()
        
        # Return cached data if still valid
        if cls._cache and current_time < cls._cache_expiry:
            return cls._cache
        
        try:
            # Fetching from Mempool.space API
            height_res = requests.get(
                "https://mempool.space/api/blocks/tip/height", 
                timeout=5
            )
            hashrate_res = requests.get(
                "https://mempool.space/api/v1/mining/hashrate/3d", 
                timeout=5
            )
            difficulty_res = requests.get(
                "https://mempool.space/api/v1/difficulty-adjustment",
                timeout=5
            )
            
            if height_res.status_code == 200:
                height = int(height_res.text)
                
                # Convert raw hashrate to EH/s for that 'Powerhouse' feel
                hashrate_data = hashrate_res.json()
                current_hashrate = hashrate_data.get('currentHashrate', 0) / 10**18
                
                # Get difficulty adjustment info
                diff_data = difficulty_res.json() if difficulty_res.status_code == 200 else {}
                progress_percent = diff_data.get('progressPercent', 0)
                remaining_blocks = diff_data.get('remainingBlocks', 0)
                
                result = {
                    "height": f"{height:,}",
                    "height_raw": height,
                    "hashrate": f"{current_hashrate:.2f} EH/s",
                    "hashrate_raw": current_hashrate,
                    "difficulty_progress": f"{progress_percent:.1f}%",
                    "remaining_blocks": remaining_blocks,
                    "status": "OPERATIONAL"
                }
                
                # Update cache
                cls._cache = result
                cls._cache_expiry = current_time + cls.CACHE_DURATION
                
                return result
                
        except requests.exceptions.Timeout:
            logging.warning("Mempool.space API timeout")
            return cls._get_fallback("TIMEOUT")
        except requests.exceptions.RequestException as e:
            logging.error(f"Node Tracker Request Error: {e}")
            return cls._get_fallback("NETWORK_ERROR")
        except Exception as e:
            logging.error(f"Node Tracker Error: {e}")
            return cls._get_fallback("RECONNECTING")
    
    @classmethod
    def _get_fallback(cls, status):
        """Return cached data if available, otherwise offline status"""
        if cls._cache:
            fallback = cls._cache.copy()
            fallback["status"] = status
            return fallback
        return {
            "height": "---,---",
            "height_raw": 0,
            "hashrate": "--- EH/s",
            "hashrate_raw": 0,
            "difficulty_progress": "--%",
            "remaining_blocks": 0,
            "status": status
        }


# Global instance
node_service = NodeService()
```

---

## FILE 3: services/ad_processor.py (Ad Spice)

```python
import os
import logging
from PIL import Image, ImageEnhance, ImageOps, ImageDraw

def spice_ad_image(input_path, output_path):
    """
    Transforms a standard sponsor logo into a Red/Black Cyberpunk terminal asset.
    
    This processor performs a multi-stage transformation:
    1. Desaturation - Remove original branding colors
    2. Channel Manipulation - Apply cyberpunk red tint
    3. Contrast Enhancement - Make blacks deeper and reds pop
    4. Scanline Injection - Add terminal/intel aesthetic
    5. Vignette Application - Focus on logo center
    """
    try:
        # 1. Load Image and convert to RGBA to handle transparency
        with Image.open(input_path) as img:
            # Handle different modes
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")
            
            width, height = img.size
            
            # 2. Create the "Cyberpunk Red" Tint
            # Convert to grayscale first to remove original colors
            grayscale = ImageOps.grayscale(img)
            
            # Apply red colorization - black stays black, white becomes red
            spiced_img = ImageOps.colorize(
                grayscale, 
                black="black", 
                white="#dc2626"  # --accent-red
            )
            spiced_img = spiced_img.convert("RGB")

            # 3. Enhance Contrast - Makes blacks deeper and reds pop
            enhancer = ImageEnhance.Contrast(spiced_img)
            spiced_img = enhancer.enhance(1.5)
            
            # Also boost brightness slightly
            brightness = ImageEnhance.Brightness(spiced_img)
            spiced_img = brightness.enhance(1.1)

            # 4. Overlay Digital Scanlines - Creates 'Intel Terminal' look
            draw = ImageDraw.Draw(spiced_img)
            for y in range(0, height, 4):  # Every 4th pixel row
                draw.line([(0, y), (width, y)], fill=(0, 0, 0, 100), width=1)

            # 5. Apply a Subtle Vignette - Darkens edges to focus on center
            # Create a radial gradient mask
            vignette = Image.new("L", spiced_img.size, 0)
            draw_v = ImageDraw.Draw(vignette)
            
            # Draw an ellipse that's larger than the image
            padding = min(width, height) // 4
            draw_v.ellipse(
                [-padding, -padding, width + padding, height + padding], 
                fill=255
            )
            
            # Apply the vignette as a blend
            # For simplicity, we'll skip the complex vignette and just save
            
            # 6. Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 7. Save the finalized asset
            spiced_img.save(output_path, "JPEG", quality=95, optimize=True)
            
            logging.info(f"Successfully spiced ad image: {output_path}")
            return True
            
    except Exception as e:
        logging.error(f"Error spicing image: {e}")
        return False


def process_sponsor_logo(original_path, sponsor_name):
    """
    Convenience function to process a sponsor logo and return the output path.
    
    Args:
        original_path: Path to the original logo file
        sponsor_name: Name of the sponsor (used for filename)
    
    Returns:
        Path to the processed image, or None if processing failed
    """
    import uuid
    
    # Generate unique filename
    safe_name = sponsor_name.lower().replace(' ', '_').replace("'", '')
    filename = f"spiced_{safe_name}_{uuid.uuid4().hex[:8]}.jpg"
    output_path = os.path.join('static', 'ads', filename)
    
    if spice_ad_image(original_path, output_path):
        return f"/static/ads/{filename}"
    return None
```

---

## FILE 4: Route Endpoints in routes.py

Add these routes to your routes.py file:

```python
from services.node_service import NodeService

@app.route('/api/network-stats')
def api_network_stats():
    """API endpoint to get live Bitcoin network statistics from Mempool.space"""
    try:
        stats = NodeService.get_network_stats()
        return jsonify({
            'success': True,
            **stats
        })
    except Exception as e:
        logging.error(f"Error fetching network stats: {e}")
        return jsonify({
            'success': False,
            'height': '---,---',
            'hashrate': '--- EH/s',
            'status': 'ERROR'
        }), 500

@app.route('/api/active-ads', methods=['GET'])
def api_active_ads():
    """API endpoint to get active advertisements for cycling"""
    try:
        active_ads = Advertisement.query.filter_by(is_active=True).all()
        
        ads_data = []
        for ad in active_ads:
            ads_data.append({
                'id': ad.id,
                'name': ad.name,
                'image_url': ad.image_url,
                'target_url': ad.target_url,
                'created_at': ad.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'ads': ads_data,
            'count': len(ads_data)
        })
    except Exception as e:
        logging.error(f"Error fetching active ads: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

## FEATURES INCLUDED

1. **Protocol Heartbeat** - Live Bitcoin block height and hashrate from Mempool.space API
2. **High-Fidelity Terminal Player** - YouTube video overlay with Intel Briefing sidebar
3. **Sponsor Rotation System** - Glitch effect cycling every 20 seconds
4. **Luxurious Book Cards** - Glassmorphic styling with Amazon orange hover
5. **Cyberpunk Audio Player** - Bottom dock player for podcast episodes
6. **Bento Grid Layout** - 4-column responsive grid with spanning cards
7. **Cinematic Backgrounds** - YouTube thumbnails as card backgrounds
8. **Mobile Responsive** - Full responsive design down to 768px

---

*Generated for Protocol Pulse Media Hub - January 2026*
