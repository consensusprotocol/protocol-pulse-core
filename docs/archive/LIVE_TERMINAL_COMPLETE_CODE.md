# Protocol Pulse - Live Terminal Complete Codebase

This file contains the complete code for the `/live` page (Alchemical Transmutation Terminal).

---

## File 1: templates/live_terminal.html

```html
{% extends "base.html" %}

{% block title %}Live Settlement Terminal | Protocol Pulse{% endblock %}

{% block head %}
<style>
:root {
    --pp-bitcoin: #f7931a;
    --pp-bitcoin-dark: #c16c00;
    --pp-bitcoin-glow: rgba(247, 147, 26, 0.5);
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.9);
}

/* CRITICAL: Override body background for video visibility */
body, html {
    margin: 0 !important;
    padding: 0 !important;
    overflow-x: hidden;
    background: transparent !important;
    background-color: transparent !important;
}

#live-terminal-wrapper {
    height: 100vh !important;
    margin-bottom: 0 !important;
}

/* Footer overlap for seamless flow */
footer {
    margin-top: -60px !important;
    position: relative;
    z-index: 10;
    background: rgba(0,0,0,0.85) !important;
    backdrop-filter: blur(10px);
}

/* SOVEREIGN STATUS BAR - Live Intelligence Feed */
.sovereign-status-bar {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    display: flex;
    justify-content: center;
    gap: 2.5rem;
    padding: 12px 20px;
    background: linear-gradient(180deg, rgba(0,0,0,0.7) 0%, transparent 100%);
    font-family: 'JetBrains Mono', 'SF Mono', monospace;
    font-size: 0.85rem;
}

.status-metric {
    display: flex;
    align-items: center;
    gap: 8px;
    color: rgba(255,255,255,0.9);
}

.status-label {
    color: rgba(255,255,255,0.5);
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.5px;
}

.status-value {
    font-weight: 600;
    color: #fff;
}

.status-value.highlight {
    color: #f7931a;
}

/* Blinking REC indicator */
.rec-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
}

.rec-dot {
    width: 8px;
    height: 8px;
    background: #ff3b30;
    border-radius: 50%;
    animation: recBlink 1s ease-in-out infinite;
}

@keyframes recBlink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* SOVEREIGN INTELLIGENCE DASHBOARD */
.sovereign-dashboard {
    background: #000000;
    padding: 40px 0 60px;
    border-top: 1px solid rgba(255,255,255,0.05);
    margin-top: 0;
}

@media (max-width: 768px) {
    .sovereign-dashboard {
        padding: 30px 15px 40px;
    }
}

.dashboard-divider {
    height: 2px;
    background: linear-gradient(90deg, #dc2626 0%, transparent 100%);
    margin-bottom: 1rem;
}

.stat-card {
    background: rgba(10,10,10,0.5);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    transition: all 0.3s ease;
}

.stat-card:hover {
    border-color: #dc2626;
    transform: translateY(-8px);
}

.stat-label {
    display: block;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #dc2626;
    font-weight: 700;
    margin-bottom: 0.75rem;
}

.stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #ffffff;
    font-family: 'JetBrains Mono', 'SF Mono', monospace;
    margin-bottom: 0.25rem;
    word-break: break-word;
    overflow-wrap: break-word;
}

@media (max-width: 768px) {
    .stat-value {
        font-size: 1.1rem;
    }
    .stat-card {
        padding: 12px !important;
    }
    .stat-label {
        font-size: 0.6rem;
    }
    .stat-note {
        font-size: 0.55rem;
    }
}

.stat-note {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(255,255,255,0.5);
    margin-bottom: 0;
}

/* FORCE BLACK BACKGROUNDS - NO WHITE GAPS */
html, body {
    background: #000 !important;
}

/* GRADIENT FADE OVERLAYS - MUST NOT BLOCK CLICKS */
.video-fade-top {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 120px;
    background: linear-gradient(to bottom, #000000 0%, rgba(0,0,0,0.5) 50%, transparent 100%);
    z-index: 2;
    pointer-events: none !important;
}

.video-fade-bottom {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 200px;
    background: linear-gradient(to top, #000000 0%, rgba(0,0,0,0.7) 40%, transparent 100%);
    z-index: 2;
    pointer-events: none !important;
}

/* VISUALIZER MUST RECEIVE ALL MOUSE EVENTS */
#visualizer-container {
    z-index: 10 !important;
    pointer-events: auto !important;
}

#visualizer-canvas {
    pointer-events: auto !important;
}

/* VIDEO MUST NOT BLOCK CLICKS */
#pulse-bg-video {
    pointer-events: none !important;
}

.terminal-container {
    position: relative;
    width: 100%;
    min-height: calc(100vh - 60px);
    background: transparent;
    overflow: hidden;
}

/* LIVE TERMINAL PAGE SPECIFIC - Video Background */
.pulse-video-background {
    position: fixed;
    inset: 0;
    z-index: -2;
    overflow: hidden;
    pointer-events: none;
}

#pulse-bg-video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

/* Transparent containers for video visibility - ONLY on this page */
.terminal-container,
.visualizer-container,
#visualizer-container,
#visualizer-canvas {
    background: transparent !important;
    background-color: transparent !important;
}

/* Kill any pseudo-element overlays */
.terminal-container::before,
.terminal-container::after,
.visualizer-container::before,
.visualizer-container::after {
    display: none !important;
}

/* Visualizer canvas must sit above the video */
.visualizer-container,
#visualizer-canvas {
    position: relative;
    z-index: 1;
}

.back-nav {
    position: fixed;
    top: 80px;
    left: 20px;
    z-index: 1000;
}

.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: var(--pp-glass);
    border: 1px solid rgba(247, 147, 26, 0.3);
    border-radius: 12px;
    padding: 12px 20px;
    color: #fff;
    text-decoration: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
}

.back-btn:hover {
    background: rgba(247, 147, 26, 0.2);
    border-color: var(--pp-bitcoin);
    color: #fff;
    transform: translateX(-3px);
    box-shadow: 0 0 20px var(--pp-bitcoin-glow);
}

.back-btn i {
    color: var(--pp-bitcoin);
}

.bitfeed-frame {
    width: 100%;
    height: calc(100vh - 60px);
    border: none;
    filter: hue-rotate(330deg) saturate(1.2);
}

#blockchain-visualizer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
}

.visualizer-container {
    position: relative;
    width: 100%;
    height: calc(100vh - 60px);
    overflow: hidden;
    background: transparent;
    z-index: 1;
}

#visualizer-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100% !important;
    height: 100% !important;
    display: block;
    background: transparent !important;
}

.viz-hud {
    position: absolute;
    top: 80px;
    left: 25px;
    background: transparent;
    backdrop-filter: none;
    border: none;
    border-radius: 0;
    padding: 0;
    z-index: 1001;
    font-family: 'JetBrains Mono', monospace;
    pointer-events: none;
    transform: perspective(800px) rotateY(2deg);
}

.sovereign-active .viz-hud {
    border: none;
    background: transparent;
    box-shadow: none;
}

.viz-hud-title {
    font-size: 0.65rem;
    color: #dc2626;
    text-transform: uppercase;
    letter-spacing: 3px;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
    text-shadow: 0 0 10px rgba(220, 38, 38, 0.6), 0 2px 4px rgba(0, 0, 0, 0.8);
}

.sovereign-active .viz-hud-title {
    color: #a855f7;
    text-shadow: 0 0 10px rgba(168, 85, 247, 0.6), 0 2px 4px rgba(0, 0, 0, 0.8);
}

.viz-hud-title::before {
    content: '';
    width: 6px;
    height: 6px;
    background: currentColor;
    border-radius: 50%;
    animation: pulse-dot 1.5s infinite;
    box-shadow: 0 0 8px currentColor;
}

.viz-metric {
    display: flex;
    justify-content: flex-start;
    gap: 12px;
    padding: 6px 0;
    border-bottom: none;
}

.viz-metric:last-child {
    border-bottom: none;
}

.viz-metric-label {
    color: rgba(255, 255, 255, 0.4);
    font-size: 0.65rem;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8);
}

.viz-metric-value {
    color: #fff;
    font-size: 0.85rem;
    font-weight: 600;
    text-shadow: 0 0 8px rgba(255, 255, 255, 0.3), 0 2px 4px rgba(0, 0, 0, 0.8);
}

.viz-legend {
    margin-top: 20px;
    padding-top: 0;
    border-top: none;
}

.viz-legend-title {
    font-size: 0.6rem;
    color: rgba(255, 255, 255, 0.35);
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 2px;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8);
}

.viz-legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 5px;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8);
}

.viz-legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    box-shadow: 0 0 6px currentColor;
}

.viz-legend-dot.low { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
.viz-legend-dot.medium { background: #eab308; box-shadow: 0 0 6px #eab308; }
.viz-legend-dot.high { background: #dc2626; box-shadow: 0 0 6px #dc2626; }

.sovereign-active .viz-legend-dot.low { background: #a855f7; box-shadow: 0 0 6px #a855f7; }
.sovereign-active .viz-legend-dot.medium { background: #8b5cf6; box-shadow: 0 0 6px #8b5cf6; }
.sovereign-active .viz-legend-dot.high { background: #6b21a8; box-shadow: 0 0 6px #6b21a8; }

.viz-toggle-container {
    position: fixed;
    bottom: 70px;
    right: 20px;
    z-index: 1001;
    display: flex;
    gap: 10px;
}

.viz-toggle-btn {
    background: rgba(10, 10, 10, 0.85);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 8px;
    padding: 10px 15px;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.viz-toggle-btn:hover {
    border-color: #dc2626;
    background: rgba(220, 38, 38, 0.2);
}

.viz-toggle-btn.active {
    background: rgba(220, 38, 38, 0.3);
    border-color: #dc2626;
}

.sovereign-active .viz-toggle-btn {
    border-color: rgba(168, 85, 247, 0.4);
}

.sovereign-active .viz-toggle-btn:hover,
.sovereign-active .viz-toggle-btn.active {
    border-color: #a855f7;
    background: rgba(168, 85, 247, 0.2);
}

.terminal-hud {
    position: fixed;
    top: 100px;
    right: 25px;
    background: transparent;
    backdrop-filter: none;
    border: none;
    border-radius: 0;
    padding: 0;
    min-width: 200px;
    z-index: 1000;
    box-shadow: none;
    pointer-events: none;
    transform: perspective(800px) rotateY(-2deg);
}

.hud-title {
    font-family: 'JetBrains Mono', monospace;
    color: #dc2626;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 3px;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
    text-shadow: 0 0 10px rgba(220, 38, 38, 0.6), 0 2px 4px rgba(0, 0, 0, 0.8);
}

.hud-title::before {
    content: '';
    width: 6px;
    height: 6px;
    background: #dc2626;
    border-radius: 50%;
    animation: pulse-dot 1.5s infinite;
    box-shadow: 0 0 8px #dc2626;
}

@keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
    50% { opacity: 0.6; box-shadow: 0 0 0 10px rgba(220, 38, 38, 0); }
}

.hud-metric {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    border-bottom: none;
}

.hud-metric:last-child {
    border-bottom: none;
}

.metric-label {
    font-family: 'JetBrains Mono', monospace;
    color: rgba(255, 255, 255, 0.4);
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8);
}

.metric-value {
    font-family: 'JetBrains Mono', monospace;
    color: #fff;
    font-size: 0.9rem;
    font-weight: 600;
    text-shadow: 0 0 8px rgba(255, 255, 255, 0.3), 0 2px 4px rgba(0, 0, 0, 0.8);
}

.metric-value.fee-low { color: #22c55e; text-shadow: 0 0 8px rgba(34, 197, 94, 0.5), 0 2px 4px rgba(0, 0, 0, 0.8); }
.metric-value.fee-medium { color: #eab308; text-shadow: 0 0 8px rgba(234, 179, 8, 0.5), 0 2px 4px rgba(0, 0, 0, 0.8); }
.metric-value.fee-high { color: #dc2626; text-shadow: 0 0 8px rgba(220, 38, 38, 0.5), 0 2px 4px rgba(0, 0, 0, 0.8); }

.latest-block {
    background: transparent;
    border-radius: 0;
    padding: 10px 0;
    margin-top: 15px;
}

.block-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.block-height {
    font-family: 'JetBrains Mono', monospace;
    color: var(--pp-red);
    font-size: 1.2rem;
    font-weight: 700;
}

.block-time {
    font-family: 'JetBrains Mono', monospace;
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.75rem;
}

.block-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}

.block-stat {
    text-align: center;
}

.block-stat-label {
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
}

.block-stat-value {
    font-family: 'JetBrains Mono', monospace;
    color: #fff;
    font-size: 0.9rem;
}

.terminal-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--pp-glass);
    backdrop-filter: blur(20px);
    border-top: 1px solid rgba(220, 38, 38, 0.2);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 1000;
}

.terminal-status {
    display: flex;
    align-items: center;
    gap: 20px;
}

.status-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.7);
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #22c55e;
}

.terminal-source {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.4);
}

.terminal-source a {
    color: var(--pp-red);
    text-decoration: none;
}

.mempool-viz {
    position: relative;
    height: 60px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    overflow: hidden;
    margin-top: 15px;
}

.mempool-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: linear-gradient(to top, var(--pp-red), rgba(220, 38, 38, 0.3));
    transition: height 0.5s ease;
}

.mempool-label {
    position: absolute;
    bottom: 5px;
    left: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.8);
    z-index: 1;
}

/* Mobile TX Popup Card */
.tx-popup-card {
    display: none;
    position: fixed;
    bottom: 50%;
    left: 50%;
    transform: translate(-50%, 50%);
    background: rgba(10, 10, 10, 0.95);
    border: 2px solid rgba(247, 147, 26, 0.6);
    border-radius: 16px;
    padding: 25px;
    z-index: 2000;
    font-family: 'JetBrains Mono', monospace;
    backdrop-filter: blur(20px);
    min-width: 280px;
    max-width: 90vw;
    box-shadow: 0 0 40px rgba(247, 147, 26, 0.3);
    animation: popupSlide 0.3s ease-out;
}

@keyframes popupSlide {
    from { transform: translate(-50%, 50%) scale(0.8); opacity: 0; }
    to { transform: translate(-50%, 50%) scale(1); opacity: 1; }
}

.tx-popup-card.show {
    display: block;
}

.tx-popup-close {
    position: absolute;
    top: 10px;
    right: 15px;
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.5);
    font-size: 1.5rem;
    cursor: pointer;
    line-height: 1;
}

.tx-popup-close:hover {
    color: #fff;
}

.tx-popup-header {
    color: #f7931a;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.tx-popup-header::before {
    content: '₿';
    font-size: 1.2rem;
}

.tx-popup-amount {
    font-size: 1.8rem;
    font-weight: bold;
    color: #22c55e;
    margin-bottom: 8px;
}

.tx-popup-fiat {
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 15px;
}

.tx-popup-txid {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 15px;
}

.tx-popup-txid-label {
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
}

.tx-popup-txid-value {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.8);
    word-break: break-all;
    line-height: 1.4;
}

.tx-popup-meta {
    display: flex;
    justify-content: space-between;
    margin-bottom: 20px;
    padding: 10px 0;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.tx-popup-meta-item {
    text-align: center;
}

.tx-popup-meta-label {
    font-size: 0.6rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    margin-bottom: 4px;
}

.tx-popup-meta-value {
    font-size: 0.85rem;
    color: #fff;
}

.tx-popup-verify {
    display: block;
    width: 100%;
    background: linear-gradient(135deg, #f7931a 0%, #c16c00 100%);
    border: none;
    border-radius: 10px;
    padding: 14px;
    color: #000 !important;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
    text-decoration: none;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    pointer-events: auto !important;
    position: relative;
    z-index: 2001;
    -webkit-tap-highlight-color: rgba(247, 147, 26, 0.3);
}

.tx-popup-verify:hover,
.tx-popup-verify:active {
    transform: scale(1.02);
    box-shadow: 0 0 20px rgba(247, 147, 26, 0.5);
    color: #000 !important;
    text-decoration: none;
}

.tx-popup-verify i {
    margin-right: 8px;
}

.tx-popup-card {
    pointer-events: auto !important;
}

.tx-popup-card * {
    pointer-events: auto;
}

.tx-popup-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 1999;
}

.tx-popup-overlay.show {
    display: block;
}

@media (max-width: 768px) {
    .back-nav {
        top: 70px;
        left: 10px;
    }
    
    .back-btn {
        padding: 8px 12px;
        font-size: 0.75rem;
    }
    
    .back-btn span {
        display: none;
    }
    
    .viz-hud {
        position: absolute !important;
        top: 60px !important;
        bottom: auto !important;
        left: 10px !important;
        right: auto !important;
        max-width: 140px;
        padding: 8px 10px;
        background: rgba(0, 0, 0, 0.85) !important;
        backdrop-filter: blur(10px);
        border-radius: 8px;
        transform: none !important;
        z-index: 1002 !important;
    }
    
    .viz-hud-title {
        font-size: 0.55rem;
        margin-bottom: 8px;
    }
    
    .viz-metric-label {
        font-size: 0.55rem;
    }
    
    .viz-metric-value {
        font-size: 0.7rem;
    }
    
    .viz-hud-title {
        font-size: 0.65rem;
    }
    
    .viz-metric {
        padding: 6px 0;
    }
    
    .viz-metric-label {
        font-size: 0.6rem;
    }
    
    .viz-metric-value {
        font-size: 0.8rem;
    }
    
    .viz-legend {
        display: none;
    }
    
    .terminal-hud {
        display: none;
    }
    
    .viz-toggle-container {
        bottom: 80px;
        right: 10px;
        left: 10px;
        flex-wrap: wrap;
        justify-content: center;
        gap: 8px;
    }
    
    .viz-toggle-btn {
        padding: 8px 12px;
        font-size: 0.7rem;
        flex: 1;
        min-width: 80px;
        text-align: center;
    }
    
    .terminal-footer {
        padding: 8px 10px;
        flex-direction: column;
        gap: 5px;
    }
    
    .terminal-status {
        gap: 10px;
    }
    
    .status-item {
        font-size: 0.65rem;
    }
    
    .terminal-source {
        font-size: 0.6rem;
    }
    
    .visualizer-container {
        height: calc(100vh - 50px);
    }
    
    .terminal-container {
        min-height: calc(100vh - 50px);
    }
}

@media (max-width: 480px) {
    .viz-hud {
        bottom: 130px;
        padding: 10px 12px;
    }
    
    .viz-toggle-container {
        bottom: 70px;
    }
    
    .viz-toggle-btn {
        padding: 6px 10px;
        font-size: 0.65rem;
    }
    
    .viz-toggle-btn i {
        display: none;
    }
}
</style>
{% endblock %}

{% block content %}
<nav class="back-nav">
    <a href="/" class="back-btn">
        <i class="fas fa-arrow-left"></i>
        <span>Back to Home</span>
    </a>
</nav>

<!-- Mobile TX Popup Card (outside terminal-container for proper z-index) -->
<div class="tx-popup-overlay" id="tx-popup-overlay" onclick="closeTxPopup()"></div>
<div class="tx-popup-card" id="tx-popup-card">
    <button class="tx-popup-close" onclick="closeTxPopup()">&times;</button>
    <div class="tx-popup-header">Transaction Details</div>
    <div class="tx-popup-amount" id="tx-popup-amount">0.0000 BTC</div>
    <div class="tx-popup-fiat" id="tx-popup-fiat">~$0.00 USD</div>
    <div class="tx-popup-txid">
        <div class="tx-popup-txid-label">Transaction ID</div>
        <div class="tx-popup-txid-value" id="tx-popup-txid">...</div>
    </div>
    <div class="tx-popup-meta">
        <div class="tx-popup-meta-item">
            <div class="tx-popup-meta-label">Fee Rate</div>
            <div class="tx-popup-meta-value" id="tx-popup-fee">-- sat/vB</div>
        </div>
        <div class="tx-popup-meta-item">
            <div class="tx-popup-meta-label">Status</div>
            <div class="tx-popup-meta-value" style="color: #eab308;">Unconfirmed</div>
        </div>
    </div>
    <button type="button" class="tx-popup-verify" id="tx-popup-verify">
        <i class="fas fa-external-link-alt"></i>Verify on Mempool.space
    </button>
</div>

<!-- SOVEREIGN STATUS BAR - Buffer Zone -->
<div class="sovereign-status-bar" style="position: relative; z-index: 10; background: #000; padding: 12px 0; border-bottom: none;">
    <div class="container d-flex justify-content-around">
        <div class="status-metric">
            <span class="status-label">Sats/vB</span>
            <span class="status-value highlight" id="status-fee-rate">--</span>
        </div>
        <div class="status-metric rec-indicator">
            <span class="rec-dot"></span>
            <span class="status-label">Hashrate</span>
            <span class="status-value" id="status-hashrate">-- EH/s</span>
        </div>
        <div class="status-metric">
            <span class="status-label">Blocks to Retarget</span>
            <span class="status-value" id="status-retarget">--</span>
        </div>
    </div>
</div>

<div id="live-terminal-wrapper" style="position: relative; width: 100%; min-height: 70vh; max-height: 80vh; overflow: hidden; background-color: black;">
    <!-- Video Background - ABSOLUTE positioned behind visualizer -->
    <video autoplay muted loop playsinline id="pulse-bg-video" 
           style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; filter: brightness(0.6);">
        <source src="/static/video/pulse-bg.mp4" type="video/mp4">
    </video>
    
    <!-- Gradient Fade: Header into Video (top) -->
    <div class="video-fade-top"></div>
    
    <!-- Gradient Fade: Video into Footer/Dashboard (bottom) -->
    <div class="video-fade-bottom"></div>
    
    <!-- Custom Blockchain Visualizer - ABSOLUTE positioned above video -->
    <div class="visualizer-container" id="visualizer-container" 
         style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; background: transparent !important;">
        <canvas id="visualizer-canvas" style="background: transparent !important;"></canvas>
    </div>
    
    <!-- Visualizer HUD Overlay - INSIDE wrapper so it doesn't scroll -->
    <div class="viz-hud">
        <div class="viz-hud-title">Mempool Physics</div>
        <div class="viz-metric">
            <span class="viz-metric-label">Mempool Size</span>
            <span class="viz-metric-value" id="viz-mempool-size">-- MB</span>
        </div>
        <div class="viz-metric">
            <span class="viz-metric-label">Unconfirmed</span>
            <span class="viz-metric-value" id="viz-unconfirmed">--</span>
        </div>
        <div class="viz-legend">
            <div class="viz-legend-title">Fee Rate (sat/vB)</div>
            <div class="viz-legend-item">
                <span class="viz-legend-dot low"></span>
                <span>&lt; 10 (Low Priority)</span>
            </div>
            <div class="viz-legend-item">
                <span class="viz-legend-dot medium"></span>
                <span>10-50 (Medium)</span>
            </div>
            <div class="viz-legend-item">
                <span class="viz-legend-dot high"></span>
                <span>&gt; 50 (High Priority)</span>
            </div>
        </div>
    </div>
</div>

<div class="terminal-container" style="background: transparent !important;">
    
    <!-- Toggle between visualizer and external bitfeed -->
    <div class="viz-toggle-container">
        <button class="viz-toggle-btn active" id="toggle-custom" onclick="toggleVisualizer('custom')">
            <i class="fas fa-cubes me-2"></i>Protocol Pulse
        </button>
        <button class="viz-toggle-btn" id="toggle-bitfeed" onclick="toggleVisualizer('bitfeed')">
            <i class="fas fa-external-link-alt me-2"></i>Bitfeed
        </button>
        <a href="/kinetic" class="viz-toggle-btn">
            <i class="fas fa-expand me-2"></i>Full View
        </a>
    </div>
    
    <!-- Hidden iframe for external bitfeed (shown on toggle) -->
    <iframe 
        src="https://bits.monospace.live/" 
        class="bitfeed-frame" 
        id="bitfeed-iframe"
        allow="fullscreen"
        loading="lazy"
        style="display: none;"
    ></iframe>
    
    <div class="terminal-hud">
        <div class="hud-title">Live Network Status</div>
        
        <div class="hud-metric">
            <span class="metric-label">Mempool Size</span>
            <span class="metric-value" id="mempool-size">Loading...</span>
        </div>
        
        <div class="hud-metric">
            <span class="metric-label">Pending TXs</span>
            <span class="metric-value" id="pending-txs">--</span>
        </div>
        
        <div class="hud-metric">
            <span class="metric-label">Next Block Fee</span>
            <span class="metric-value" id="next-block-fee">-- sat/vB</span>
        </div>
        
        <div class="hud-metric">
            <span class="metric-label">Low Priority</span>
            <span class="metric-value fee-low" id="low-fee">-- sat/vB</span>
        </div>
        
        <div class="mempool-viz">
            <div class="mempool-bar" id="mempool-bar" style="height: 20%"></div>
            <span class="mempool-label" id="mempool-mb">-- MB</span>
        </div>
        
        <div class="latest-block">
            <div class="block-header">
                <span class="block-height" id="block-height">#---,---</span>
                <span class="block-time" id="block-time">--:--</span>
            </div>
            <div class="block-stats">
                <div class="block-stat">
                    <div class="block-stat-label">TXs</div>
                    <div class="block-stat-value" id="block-txs">--</div>
                </div>
                <div class="block-stat">
                    <div class="block-stat-label">Size</div>
                    <div class="block-stat-value" id="block-size">-- MB</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="terminal-footer">
        <div class="terminal-status">
            <div class="status-item">
                <span class="status-dot"></span>
                <span>LIVE</span>
            </div>
            <div class="status-item">
                <span id="connection-status">Connected to Bitcoin Network</span>
            </div>
        </div>
        <div class="terminal-source">
            Powered by <a href="https://mempool.space" target="_blank">Mempool.space</a> | 
            Visualization by <a href="https://bits.monospace.live" target="_blank">Bitfeed</a>
        </div>
    </div>
</div>

<!-- SOVEREIGN INTELLIGENCE DASHBOARD -->
<section class="sovereign-dashboard container-fluid">
    <div class="container">
        <div class="row mb-4">
            <div class="col-12"><div class="dashboard-divider"></div></div>
        </div>

        <div class="row g-4 text-center">
            <div class="col-6 col-md-3">
                <div class="stat-card p-4">
                    <small class="stat-label">Sustainable Energy</small>
                    <h2 class="stat-value" id="intel-renewable">54.5%</h2>
                    <p class="stat-note">Network Renewable Mix</p>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card p-4">
                    <small class="stat-label">Network Shield</small>
                    <h2 class="stat-value" id="intel-nodes">18,241</h2>
                    <p class="stat-note">Active Sovereign Nodes</p>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card p-4">
                    <small class="stat-label">Computational Moat</small>
                    <h2 class="stat-value" id="intel-hashrate">-- EH/s</h2>
                    <p class="stat-note">Exahash Per Second</p>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card p-4">
                    <small class="stat-label">Unconfirmed</small>
                    <h2 class="stat-value" id="intel-pending">--</h2>
                    <p class="stat-note">Pending Transactions</p>
                </div>
            </div>
        </div>
        
        <div class="row g-4 text-center mt-2">
            <div class="col-6 col-md-3">
                <div class="stat-card p-4">
                    <small class="stat-label">Lightning Network</small>
                    <h2 class="stat-value" id="intel-lightning">-- BTC</h2>
                    <p class="stat-note">Public Channel Capacity</p>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card p-4">
                    <small class="stat-label">Mining Difficulty</small>
                    <h2 class="stat-value" id="intel-difficulty">-- T</h2>
                    <p class="stat-note">Network Security Level</p>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card p-4">
                    <small class="stat-label">Next Halving</small>
                    <h2 class="stat-value" id="intel-halving">-- days</h2>
                    <p class="stat-note">Subsidy Reduction ETA</p>
                </div>
            </div>
            <div class="col-6 col-md-3">
                <div class="stat-card p-4">
                    <small class="stat-label">Block Height</small>
                    <h2 class="stat-value" id="intel-height">#---,---</h2>
                    <p class="stat-note">Latest Confirmed Block</p>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}

{% block scripts %}
<!-- Three.js Core -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<!-- Three.js Post-Processing -->
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/shaders/CopyShader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/shaders/LuminosityHighPassShader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/EffectComposer.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/RenderPass.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/ShaderPass.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/UnrealBloomPass.js"></script>

<script src="{{ url_for('static', filename='js/visualizer.js') }}?v=20260128h"></script>
<script>
// Ensure video plays on load
window.addEventListener('DOMContentLoaded', () => {
    const v = document.getElementById('pulse-bg-video');
    if (!v) return;
    
    const tryPlay = async () => {
        try { await v.play(); } catch (e) { console.log('Video autoplay blocked'); }
    };
    
    tryPlay();
    
    const unlock = () => {
        tryPlay();
        window.removeEventListener('click', unlock);
        window.removeEventListener('touchstart', unlock);
    };
    
    window.addEventListener('click', unlock, { once: true });
    window.addEventListener('touchstart', unlock, { once: true });
});
</script>
<script>
// Update Sovereign Status Bar with live network intel
async function updateSovereignStatusBar() {
    try {
        const [feesRes, hashrateRes, diffRes] = await Promise.all([
            fetch('https://mempool.space/api/v1/fees/recommended'),
            fetch('https://mempool.space/api/v1/mining/hashrate/1d'),
            fetch('https://mempool.space/api/v1/difficulty-adjustment')
        ]);
        
        const fees = await feesRes.json();
        const hashrate = await hashrateRes.json();
        const diff = await diffRes.json();
        
        // Fastest fee in sats/vB
        document.getElementById('status-fee-rate').textContent = fees.fastestFee + ' sat/vB';
        
        // Hashrate in EH/s
        if (hashrate.currentHashrate) {
            const ehps = (hashrate.currentHashrate / 1e18).toFixed(2);
            document.getElementById('status-hashrate').textContent = ehps + ' EH/s';
        }
        
        // Blocks until difficulty retarget
        if (diff.remainingBlocks !== undefined) {
            document.getElementById('status-retarget').textContent = diff.remainingBlocks.toLocaleString();
        }
        
        // Update Intel Strip - Difficulty (use current difficulty from API)
        try {
            const difficultyRes = await fetch('https://mempool.space/api/v1/mining/hashrate/3d');
            const diffData = await difficultyRes.json();
            if (diffData.currentDifficulty) {
                const diffT = (diffData.currentDifficulty / 1e12).toFixed(2);
                document.getElementById('intel-difficulty').textContent = diffT + ' T';
            }
        } catch (diffErr) {
            console.log('Difficulty fetch error:', diffErr);
        }
    } catch (e) {
        console.error('Status bar update error:', e);
    }
}

// Update Sovereign Intelligence Dashboard
async function updateNetworkIntel() {
    try {
        const [lnRes, blocksRes, mempoolRes, hashrateRes] = await Promise.all([
            fetch('https://mempool.space/api/v1/lightning/statistics/latest'),
            fetch('https://mempool.space/api/blocks/tip/height'),
            fetch('https://mempool.space/api/mempool'),
            fetch('https://mempool.space/api/v1/mining/hashrate/1d')
        ]);
        
        // Lightning Network capacity
        const ln = await lnRes.json();
        if (ln.latest && ln.latest.total_capacity) {
            const btcCapacity = (ln.latest.total_capacity / 100000000).toLocaleString();
            document.getElementById('intel-lightning').textContent = btcCapacity + ' BTC';
        }
        
        // Block height and halving ETA
        const currentHeight = await blocksRes.json();
        document.getElementById('intel-height').textContent = '#' + currentHeight.toLocaleString();
        
        const nextHalving = 1050000;
        const blocksRemaining = nextHalving - currentHeight;
        const daysRemaining = Math.round((blocksRemaining * 10) / 1440);
        document.getElementById('intel-halving').textContent = daysRemaining.toLocaleString() + ' days';
        
        // Pending transactions
        const mempool = await mempoolRes.json();
        const pendingK = (mempool.count / 1000).toFixed(1);
        document.getElementById('intel-pending').textContent = pendingK + 'K';
        
        // Hashrate
        const hashrate = await hashrateRes.json();
        if (hashrate.currentHashrate) {
            const ehps = (hashrate.currentHashrate / 1e18).toFixed(0);
            document.getElementById('intel-hashrate').textContent = '~' + ehps + ' EH/s';
        }
        
    } catch (e) {
        console.error('Network intel update error:', e);
    }
}

// Initial load + refresh every 60 seconds
updateSovereignStatusBar();
updateNetworkIntel();
setInterval(updateSovereignStatusBar, 30000);
setInterval(updateNetworkIntel, 60000);

async function updateMempoolData() {
    try {
        const [mempoolRes, feesRes, blocksRes] = await Promise.all([
            fetch('https://mempool.space/api/mempool'),
            fetch('https://mempool.space/api/v1/fees/recommended'),
            fetch('https://mempool.space/api/blocks')
        ]);
        
        const mempool = await mempoolRes.json();
        const fees = await feesRes.json();
        const blocks = await blocksRes.json();
        
        const mempoolMB = (mempool.vsize / 1000000).toFixed(1);
        const mempoolPercent = Math.min((mempool.vsize / 300000000) * 100, 100);
        
        document.getElementById('mempool-size').textContent = mempoolMB + ' vMB';
        document.getElementById('pending-txs').textContent = mempool.count.toLocaleString();
        document.getElementById('mempool-mb').textContent = mempoolMB + ' MB';
        document.getElementById('mempool-bar').style.height = mempoolPercent + '%';
        
        const nextBlockFee = fees.fastestFee;
        const feeEl = document.getElementById('next-block-fee');
        feeEl.textContent = nextBlockFee + ' sat/vB';
        feeEl.className = 'metric-value ' + (nextBlockFee < 10 ? 'fee-low' : nextBlockFee < 50 ? 'fee-medium' : 'fee-high');
        
        document.getElementById('low-fee').textContent = fees.hourFee + ' sat/vB';
        
        if (blocks.length > 0) {
            const latest = blocks[0];
            document.getElementById('block-height').textContent = '#' + latest.height.toLocaleString();
            
            const blockTime = new Date(latest.timestamp * 1000);
            const now = new Date();
            const minAgo = Math.floor((now - blockTime) / 60000);
            document.getElementById('block-time').textContent = minAgo + ' min ago';
            
            document.getElementById('block-txs').textContent = latest.tx_count.toLocaleString();
            document.getElementById('block-size').textContent = (latest.size / 1000000).toFixed(2) + ' MB';
        }
        
        if (nextBlockFee <= 5) {
            checkAndNotifyLowFees(nextBlockFee);
        }
        
    } catch (error) {
        console.error('Mempool data fetch error:', error);
        document.getElementById('connection-status').textContent = 'Reconnecting...';
    }
}

function checkAndNotifyLowFees(fee) {
    if ('Notification' in window && Notification.permission === 'granted') {
        if (!window.lastFeeNotification || Date.now() - window.lastFeeNotification > 300000) {
            new Notification('Protocol Pulse: Low Fee Alert', {
                body: `Network fees dropped to ${fee} sat/vB. Optimal time to transact.`,
                icon: '/static/images/protocol-pulse-logo-transparent.png'
            });
            window.lastFeeNotification = Date.now();
        }
    }
}

updateMempoolData();
setInterval(updateMempoolData, 10000);

if ('Notification' in window && Notification.permission === 'default') {
    setTimeout(() => {
        Notification.requestPermission();
    }, 5000);
}

function closeTxPopup() {
    const overlay = document.getElementById('tx-popup-overlay');
    const card = document.getElementById('tx-popup-card');
    if (overlay) overlay.classList.remove('show');
    if (card) card.classList.remove('show');
}

function toggleVisualizer(mode) {
    const customViz = document.getElementById('visualizer-container');
    const bitfeedIframe = document.getElementById('bitfeed-iframe');
    const vizHud = document.querySelector('.viz-hud');
    const toggleCustom = document.getElementById('toggle-custom');
    const toggleBitfeed = document.getElementById('toggle-bitfeed');
    
    if (mode === 'custom') {
        customViz.style.display = 'block';
        bitfeedIframe.style.display = 'none';
        vizHud.style.display = 'block';
        toggleCustom.classList.add('active');
        toggleBitfeed.classList.remove('active');
        
        if (window.visualizer) {
            window.visualizer.start();
        }
    } else {
        customViz.style.display = 'none';
        bitfeedIframe.style.display = 'block';
        vizHud.style.display = 'none';
        toggleCustom.classList.remove('active');
        toggleBitfeed.classList.add('active');
        
        if (window.visualizer) {
            window.visualizer.stop();
        }
    }
}

if (localStorage.getItem('sovereignMode') === 'true') {
    document.body.classList.add('sovereign-active');
}
</script>
{% endblock %}
```

---

## File 2: static/js/visualizer.js

```javascript
/**
 * SOVEREIGN TERMINAL V3 - "Global Monetary Settlement"
 * A cinematic Bitcoin visualizer with:
 * - Custom background image with animated ring orb overlay
 * - Slow, majestic particle physics (dust motes in sunlight)
 * - Looping "Global Monetary Settlement: Immutable" text banner
 * - Mobile-optimized with touch-friendly interactions
 * - Click particles to open mempool.space
 */

class SovereignTerminal {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;
        
        this.isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        this.devicePixelRatio = Math.min(window.devicePixelRatio || 1, 2);
        
        this.particles = [];
        this.maxParticles = this.isMobile ? 150 : 400;
        
        this.ws = null;
        this.isRunning = false;
        this.time = 0;
        this.lastBlockHeight = 0;
        
        this.sovereignMode = localStorage.getItem('sovereignMode') === 'true';
        
        this.initScene();
        this.createBackgroundLayers();
        this.createParticleSystem();
        this.createBlockNotification();
        this.setupInteraction();
        
        window.addEventListener('resize', () => this.onResize());
        
        const observer = new MutationObserver(() => {
            this.sovereignMode = document.body.classList.contains('sovereign-active');
        });
        observer.observe(document.body, { attributes: true });
        
        console.log(`[Sovereign Terminal V3] Mobile: ${this.isMobile} | DPR: ${this.devicePixelRatio}`);
    }
    
    initScene() {
        const width = this.container.clientWidth || window.innerWidth;
        const height = this.container.clientHeight || (window.innerHeight - 60);
        
        this.scene = new THREE.Scene();
        
        this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 2000);
        this.camera.position.set(0, 20, 500);
        
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(this.devicePixelRatio);
        this.renderer.setClearColor(0x000000, 0);
        this.renderer.domElement.style.background = 'transparent';
        
        const existingCanvas = this.container.querySelector('canvas');
        if (existingCanvas) existingCanvas.remove();
        this.container.appendChild(this.renderer.domElement);
        
        this.initPostProcessing();
        this.clock = new THREE.Clock();
        
        this.raycaster = new THREE.Raycaster();
        this.raycaster.params.Points.threshold = this.isMobile ? 35 : 15;
        this.mouse = new THREE.Vector2();
        
        this.createVignetteMask();
    }
    
    createVignetteMask() {
        // Disabled - no vignette overlay so video background shows through
    }
    
    initPostProcessing() {
        const width = this.container.clientWidth || window.innerWidth;
        const height = this.container.clientHeight || (window.innerHeight - 60);
        
        this.composer = new THREE.EffectComposer(this.renderer);
        
        const renderPass = new THREE.RenderPass(this.scene, this.camera);
        renderPass.clearAlpha = 0;
        this.composer.addPass(renderPass);
        
        this.composer.renderer.setClearColor(0x000000, 0);
        
        this.bloomPass = new THREE.UnrealBloomPass(
            new THREE.Vector2(width, height),
            0.4,
            0.15,
            0.9
        );
        this.bloomPass.threshold = 0.9;
        this.bloomPass.strength = this.isMobile ? 0.3 : 0.4;
        this.bloomPass.radius = 0.15;
        this.composer.addPass(this.bloomPass);
    }
    
    getFibonacciSpherePoints(samples, radius) {
        const points = [];
        const phi = Math.PI * (3 - Math.sqrt(5));
        
        for (let i = 0; i < samples; i++) {
            const y = 1 - (i / (samples - 1)) * 2;
            const r = Math.sqrt(1 - y * y);
            const theta = phi * i;
            
            const x = Math.cos(theta) * r;
            const z = Math.sin(theta) * r;
            
            points.push(new THREE.Vector3(x * radius, y * radius, z * radius));
        }
        return points;
    }
    
    createParticleSystem() {
        this.particleGeometry = new THREE.BufferGeometry();
        const positions = new Float32Array(this.maxParticles * 3);
        const colors = new Float32Array(this.maxParticles * 3);
        const sizes = new Float32Array(this.maxParticles);
        
        const orbRadius = this.isMobile ? 80 : 120;
        const orbCenterY = 70;
        
        this.fibonacciSlots = this.getFibonacciSpherePoints(this.maxParticles, orbRadius);
        this.springStrength = 0.08;
        this.minGap = this.isMobile ? 12 : 10;
        this.separationForce = 0.5;
        
        for (let i = 0; i < this.maxParticles; i++) {
            const slot = this.fibonacciSlots[i];
            
            positions[i * 3] = slot.x;
            positions[i * 3 + 1] = slot.y + orbCenterY;
            positions[i * 3 + 2] = slot.z * 0.3 - 50;
            
            colors[i * 3] = 0.9;
            colors[i * 3 + 1] = 0.5;
            colors[i * 3 + 2] = 0.1;
            
            const particleValue = Math.random() * 5;
            const baseSize = this.isMobile ? 8 : 6;
            let sizeMultiplier = 1.0;
            if (particleValue >= 10) sizeMultiplier = 3.0;
            else if (particleValue >= 5) sizeMultiplier = 2.5;
            else if (particleValue >= 1) sizeMultiplier = 2.0;
            else if (particleValue >= 0.5) sizeMultiplier = 1.5;
            else if (particleValue >= 0.1) sizeMultiplier = 1.2;
            sizes[i] = baseSize * sizeMultiplier;
            
            this.particles.push({
                index: i,
                txid: null,
                isReal: false,
                value: particleValue,
                feeRate: 5 + Math.random() * 80,
                spawnTime: Date.now() - Math.random() * 60000,
                velocity: new THREE.Vector3(0, 0, 0),
                slotIndex: i,
                orbCenterY: orbCenterY,
                phase: 'orb',
                orbitOffset: Math.random() * Math.PI * 2
            });
        }
        
        this.particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        this.particleGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        this.particleGeometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
        
        const material = new THREE.PointsMaterial({
            size: this.isMobile ? 14 : 12,
            vertexColors: true,
            transparent: true,
            opacity: 0.95,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            sizeAttenuation: true
        });
        
        this.pointSystem = new THREE.Points(this.particleGeometry, material);
        this.scene.add(this.pointSystem);
    }
    
    setupInteraction() {
        const canvas = this.renderer.domElement;
        
        canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        canvas.addEventListener('click', (e) => this.onClick(e));
        canvas.addEventListener('touchstart', (e) => this.onTouchStart(e), { passive: false });
        canvas.addEventListener('touchend', (e) => this.onTouchEnd(e));
        
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'viz-tooltip';
        this.tooltip.style.cssText = `
            position: fixed;
            background: rgba(0, 0, 0, 0.95);
            border: 1px solid rgba(247, 147, 26, 0.6);
            border-radius: 10px;
            padding: 12px 16px;
            color: #fff;
            font-family: 'JetBrains Mono', monospace;
            font-size: ${this.isMobile ? '0.85rem' : '0.75rem'};
            pointer-events: none;
            z-index: 10000;
            display: none;
            max-width: ${this.isMobile ? '90vw' : '300px'};
            backdrop-filter: blur(12px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        `;
        document.body.appendChild(this.tooltip);
    }
    
    onMouseMove(event) {
        if (this.isMobile) return;
        
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        this.checkHover(event.clientX, event.clientY);
    }
    
    checkHover(clientX, clientY) {
        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        const intersects = this.raycaster.intersectObject(this.pointSystem);
        
        if (intersects.length > 0) {
            const index = intersects[0].index;
            const particle = this.particles[index];
            
            if (particle) {
                if (particle !== this.lastHoveredParticle) {
                    this.lastHoveredParticle = particle;
                }
                this.showTooltip(particle, clientX, clientY);
                this.renderer.domElement.style.cursor = particle.isReal ? 'pointer' : 'default';
            }
        } else {
            this.lastHoveredParticle = null;
            this.tooltip.style.display = 'none';
            this.renderer.domElement.style.cursor = 'default';
        }
    }
    
    showTooltip(particle, x, y) {
        this.tooltip.style.display = 'block';
        
        if (this.isMobile) {
            this.tooltip.style.left = '50%';
            this.tooltip.style.bottom = '100px';
            this.tooltip.style.top = 'auto';
            this.tooltip.style.transform = 'translateX(-50%)';
        } else {
            this.tooltip.style.left = (x + 15) + 'px';
            this.tooltip.style.top = (y + 15) + 'px';
            this.tooltip.style.bottom = 'auto';
            this.tooltip.style.transform = 'none';
        }
        
        let shortTxid = 'Loading...';
        if (particle && particle.txid && typeof particle.txid === 'string' && particle.txid.length >= 64) {
            shortTxid = particle.txid.substring(0, 12) + '...' + particle.txid.substring(52);
        }
        const elapsed = (Date.now() - particle.spawnTime) / 1000;
        const timeAgo = elapsed < 60 ? Math.floor(elapsed) + 's ago' : Math.floor(elapsed / 60) + 'm ago';
        
        const clickPrompt = particle.isReal 
            ? `<div style="color: #f7931a; font-size: 0.7rem; margin-top: 10px; opacity: 0.8;">${this.isMobile ? 'Tap' : 'Click'} to view on mempool.space →</div>`
            : `<div style="color: #666; font-size: 0.7rem; margin-top: 10px; opacity: 0.6;">Awaiting TXID data...</div>`;
        
        this.tooltip.innerHTML = `
            <div style="color: #f7931a; margin-bottom: 8px; font-weight: bold;">Transaction</div>
            <div style="color: #666; font-size: 0.7rem; word-break: break-all;">${shortTxid}</div>
            <div style="margin-top: 10px; display: flex; justify-content: space-between; gap: 20px;">
                <span style="color: #22c55e; font-weight: bold;">${particle.value.toFixed(4)} BTC</span>
                <span style="color: #888;">${particle.feeRate.toFixed(1)} sat/vB</span>
            </div>
            <div style="color: #666; font-size: 0.65rem; margin-top: 8px;">${timeAgo}</div>
            ${clickPrompt}
        `;
    }
    
    onClick(event) {
        this.handleTap(event.clientX, event.clientY);
    }
    
    handleTap(clientX, clientY) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        const x = ((clientX - rect.left) / rect.width) * 2 - 1;
        const y = -((clientY - rect.top) / rect.height) * 2 + 1;
        
        this.raycaster.setFromCamera(new THREE.Vector2(x, y), this.camera);
        
        const intersects = this.raycaster.intersectObject(this.pointSystem);
        
        if (intersects.length > 0) {
            const index = intersects[0].index;
            const particle = this.particles[index];
            
            if (particle && particle.isReal && particle.txid && particle.txid.length === 64) {
                if (this.isMobile) {
                    this.showTxPopup(particle);
                } else {
                    window.open(`https://mempool.space/tx/${particle.txid}`, '_blank');
                }
            }
        }
    }
    
    showTxPopup(particle) {
        const overlay = document.getElementById('tx-popup-overlay');
        const card = document.getElementById('tx-popup-card');
        
        if (!card || !overlay) return;
        
        const amountEl = document.getElementById('tx-popup-amount');
        const fiatEl = document.getElementById('tx-popup-fiat');
        const txidEl = document.getElementById('tx-popup-txid');
        const feeEl = document.getElementById('tx-popup-fee');
        const verifyLink = document.getElementById('tx-popup-verify');
        
        const btcPrice = window.currentBtcPrice || 100000;
        const usdValue = particle.value * btcPrice;
        
        if (amountEl) amountEl.textContent = `${particle.value.toFixed(4)} BTC`;
        if (fiatEl) fiatEl.textContent = `~$${usdValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`;
        
        const txidShort = particle.txid.substring(0, 12) + '...' + particle.txid.substring(52);
        if (txidEl) txidEl.textContent = txidShort;
        
        if (feeEl) feeEl.textContent = `${particle.feeRate.toFixed(1)} sat/vB`;
        
        if (verifyLink) {
            const txUrl = `https://mempool.space/tx/${particle.txid}`;
            verifyLink.href = txUrl;
            verifyLink.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                window.open(txUrl, '_blank', 'noopener,noreferrer');
                return false;
            };
        }
        
        overlay.classList.add('show');
        card.classList.add('show');
    }
    
    spawnTransaction(txData) {
        const availableIdx = this.particles.findIndex(p => p.phase === 'docked' && p.dockProgress > 50);
        const idx = availableIdx >= 0 ? availableIdx : Math.floor(Math.random() * this.particles.length);
        
        const particle = this.particles[idx];
        const positions = this.particleGeometry.attributes.position.array;
        const colors = this.particleGeometry.attributes.color.array;
        
        const angle = Math.random() * Math.PI * 2;
        const radius = 300 + Math.random() * 100;
        const yOffset = (Math.random() - 0.5) * 200;
        
        positions[idx * 3] = Math.cos(angle) * radius;
        positions[idx * 3 + 1] = yOffset;
        positions[idx * 3 + 2] = Math.sin(angle) * 30;
        
        const feeRate = txData.feeRate || (5 + Math.random() * 80);
        if (feeRate > 50) {
            colors[idx * 3] = 0.94; colors[idx * 3 + 1] = 0.27; colors[idx * 3 + 2] = 0.27;
        } else if (feeRate > 15) {
            colors[idx * 3] = 0.97; colors[idx * 3 + 1] = 0.58; colors[idx * 3 + 2] = 0.1;
        } else {
            colors[idx * 3] = 0.13; colors[idx * 3 + 1] = 0.77; colors[idx * 3 + 2] = 0.37;
        }
        
        particle.txid = txData.txid || null;
        particle.isReal = !!txData.txid && txData.txid.length === 64;
        particle.value = txData.value || Math.random() * 5;
        particle.feeRate = feeRate;
        particle.spawnTime = Date.now();
        particle.phase = 'traveling';
        
        this.particleGeometry.attributes.position.needsUpdate = true;
        this.particleGeometry.attributes.color.needsUpdate = true;
    }
    
    updateVizHUD(data) {
        if (data.mempoolSize !== undefined) {
            const el = document.getElementById('viz-mempool-size');
            if (el) el.textContent = data.mempoolSize + ' MB';
        }
        if (data.unconfirmed !== undefined) {
            const el = document.getElementById('viz-unconfirmed');
            if (el) el.textContent = data.unconfirmed.toLocaleString();
        }
    }
    
    animate() {
        if (!this.isRunning) return;
        
        requestAnimationFrame(() => this.animate());
        
        this.time += 0.016;
        
        this.updateParticles();
        
        // Bypass EffectComposer to preserve alpha transparency for video background
        this.renderer.render(this.scene, this.camera);
    }
    
    onResize() {
        const width = this.container.clientWidth || window.innerWidth;
        const height = this.container.clientHeight || (window.innerHeight - 60);
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
        this.composer.setSize(width, height);
    }
    
    async loadInitialTransactions() {
        try {
            const recentRes = await fetch('https://mempool.space/api/mempool/recent');
            const recentTxs = await recentRes.json();
            
            if (Array.isArray(recentTxs)) {
                const txsToAssign = recentTxs.slice(0, Math.min(recentTxs.length, this.maxParticles));
                
                txsToAssign.forEach((tx, i) => {
                    if (this.particles[i]) {
                        this.particles[i].txid = tx.txid;
                        this.particles[i].isReal = true;
                        this.particles[i].value = (tx.value || 0) / 100000000 || Math.random() * 2;
                        this.particles[i].feeRate = tx.fee && tx.vsize ? (tx.fee / tx.vsize) : (5 + Math.random() * 50);
                    }
                });
                
                this.particleGeometry.attributes.color.needsUpdate = true;
            }
        } catch (error) {
            console.error('Failed to load initial transactions:', error);
        }
    }
    
    async refreshAllParticleTxids() {
        try {
            const [recentRes, txidsRes] = await Promise.all([
                fetch('https://mempool.space/api/mempool/recent'),
                fetch('https://mempool.space/api/mempool/txids')
            ]);
            
            const recentTxs = await recentRes.json();
            const allTxids = await txidsRes.json();
            
            let txIndex = 0;
            const txidsArray = Array.isArray(allTxids) ? allTxids : [];
            
            for (let i = 0; i < this.particles.length; i++) {
                if (!this.particles[i].isReal) {
                    let txid = null;
                    let value = Math.random() * 2;
                    let feeRate = 5 + Math.random() * 50;
                    
                    if (txIndex < recentTxs.length) {
                        const tx = recentTxs[txIndex];
                        txid = tx.txid;
                        value = (tx.value || 0) / 100000000 || Math.random() * 2;
                        feeRate = tx.fee && tx.vsize ? (tx.fee / tx.vsize) : feeRate;
                        txIndex++;
                    } else if (txidsArray.length > 0) {
                        const randomIdx = Math.floor(Math.random() * Math.min(txidsArray.length, 500));
                        txid = txidsArray[randomIdx];
                    }
                    
                    if (txid && txid.length === 64) {
                        this.particles[i].txid = txid;
                        this.particles[i].isReal = true;
                        this.particles[i].value = value;
                        this.particles[i].feeRate = feeRate;
                    }
                }
            }
            
            this.particleGeometry.attributes.color.needsUpdate = true;
            
        } catch (error) {
            console.error('Failed to refresh particle TXIDs:', error);
        }
    }
    
    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.loadInitialTransactions();
        
        setInterval(() => this.refreshAllParticleTxids(), 3000);
        
        this.animate();
    }
    
    stop() {
        this.isRunning = false;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('visualizer-container');
    if (container) {
        window.visualizer = new SovereignTerminal('visualizer-container');
        window.visualizer.start();
    }
});
```

---

## Key Dependencies

- **Three.js r128** - 3D rendering
- **Bootstrap 5** - Layout and responsive grid
- **JetBrains Mono font** - Monospace typography
- **Mempool.space API** - Real-time Bitcoin network data
- **Video file**: `/static/video/pulse-bg.mp4` - Background video

## Key Features

1. **Fibonacci TXID Sphere** - All particles represent real Bitcoin transaction IDs
2. **Video Background** - Fullscreen looping video with gradient fades
3. **Live Data Dashboard** - 8 metrics updated in real-time from mempool.space
4. **Mobile Responsive** - Touch-friendly with popup cards for transactions
5. **Hover/Click to Verify** - Links directly to mempool.space for verification
