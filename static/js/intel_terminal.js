/**
 * Protocol Pulse Intelligence Terminal
 * Real-time feed polling and Holographic Sentiment Dial visualization
 */

class IntelTerminal {
    constructor() {
        this.feedPollInterval = 30000;
        this.sentimentPollInterval = 60000;
        this.signalTickerPollInterval = 45000;
        this.currentTier = 'all';
        this.verifiedOnly = false;
        this.feedItems = [];
        this.signalItems = [];
        this.sentiment = { 
            score: 50, 
            state: { key: 'EQUILIBRIUM', label: 'EQUILIBRIUM', color: '#ffffff' }, 
            keywords: [], 
            sample_size: 0,
            verified_count: 0
        };
        
        this.stateConfig = {
            'CRITICAL_CONTENTION': { class: 'state-critical', cssClass: 'sentiment-critical-contention', color: '#dc2626' },
            'FRAGMENTED_SIGNAL': { class: 'state-fragmented', cssClass: 'sentiment-fragmented-signal', color: '#eab308' },
            'EQUILIBRIUM': { class: 'state-equilibrium', cssClass: 'sentiment-equilibrium', color: '#ffffff' },
            'CONSENSUS_FORMING': { class: 'state-consensus', cssClass: 'sentiment-consensus-forming', color: '#f97316' },
            'ABSOLUTE_SINGULARITY': { class: 'state-singularity', cssClass: 'sentiment-absolute-singularity', color: '#f7931a' }
        };
        
        this.init();
    }
    
    init() {
        this.pollSentiment();
        this.pollFeed();
        this.pollSignalTicker();
        
        setInterval(() => this.pollSentiment(), this.sentimentPollInterval);
        setInterval(() => this.pollFeed(), this.feedPollInterval);
        setInterval(() => this.pollSignalTicker(), this.signalTickerPollInterval);
        
        this.setupFilters();
    }
    
    async pollSignalTicker() {
        const tickerContainer = document.getElementById('signalTicker');
        if (!tickerContainer) return;
        
        try {
            const [articlesRes, feedRes] = await Promise.all([
                fetch('/api/latest-articles?limit=5'),
                fetch('/api/media/feed?limit=15')
            ]);
            
            const articlesData = await articlesRes.json();
            const feedData = await feedRes.json();
            
            let combined = [];
            
            if (articlesData.articles) {
                combined = combined.concat(articlesData.articles.map(a => ({
                    ...a,
                    source_type: 'article',
                    url: `/article/${a.slug || a.id}`
                })));
            }
            
            if (feedRes.ok && Array.isArray(feedData)) {
                combined = combined.concat(feedData.map(f => ({
                    ...f,
                    source_type: f.source_type || 'rss',
                    category: f.tier || 'media'
                })));
            } else if (feedRes.ok && feedData && typeof feedData === 'object') {
                const items = feedData.items || feedData.feed || feedData.data || [];
                if (Array.isArray(items)) {
                    combined = combined.concat(items.map(f => ({
                        ...f,
                        source_type: f.source_type || 'rss',
                        category: f.tier || 'media'
                    })));
                }
            }
            
            combined.sort((a, b) => {
                const dateA = new Date(a.published_at || a.created_at || 0);
                const dateB = new Date(b.published_at || b.created_at || 0);
                return dateB - dateA;
            });
            
            if (combined.length > 0) {
                this.signalItems = combined.slice(0, 20);
                this.renderSignalTicker();
            } else {
                tickerContainer.innerHTML = `
                    <div class="ticker-empty" style="color: rgba(255,255,255,0.5); font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; padding: 0.75rem;">
                        <i class="fas fa-satellite-dish me-2"></i> Signal feed active. Scanning frequencies...
                    </div>
                `;
            }
        } catch (error) {
            console.error('Signal ticker poll error:', error);
            tickerContainer.innerHTML = `
                <div class="ticker-error" style="color: rgba(220, 38, 38, 0.7); font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; padding: 0.75rem;">
                    <i class="fas fa-exclamation-triangle me-2"></i> Signal connection interrupted. Retrying...
                </div>
            `;
        }
    }
    
    renderSignalTicker() {
        const tickerContainer = document.getElementById('signalTicker');
        if (!tickerContainer || this.signalItems.length === 0) return;
        
        const categoryIcons = {
            'macro': 'fas fa-globe',
            'dev': 'fas fa-code',
            'mining': 'fas fa-microchip',
            'quant': 'fas fa-chart-line',
            'markets': 'fas fa-chart-bar',
            'bitcoin': 'fab fa-bitcoin',
            'lightning': 'fas fa-bolt',
            'education': 'fas fa-graduation-cap',
            'media': 'fas fa-podcast',
            'youtube': 'fab fa-youtube',
            'rss': 'fas fa-rss',
            'article': 'fas fa-newspaper',
            'default': 'fas fa-signal'
        };
        
        const categoryColors = {
            'macro': '#dc2626',
            'dev': '#3b82f6',
            'mining': '#f59e0b',
            'quant': '#8b5cf6',
            'markets': '#10b981',
            'bitcoin': '#f7931a',
            'lightning': '#a855f7',
            'education': '#06b6d4',
            'media': '#ec4899',
            'youtube': '#ff0000',
            'rss': '#ff6b35',
            'article': '#ffffff',
            'default': '#ffffff'
        };
        
        // Store items for modal access
        window.signalFeedItems = this.signalItems;
        
        tickerContainer.innerHTML = this.signalItems.map((item, index) => {
            const category = (item.tier || item.category || item.source_type || 'default').toLowerCase();
            const sourceType = (item.source_type || 'article').toLowerCase();
            const icon = categoryIcons[sourceType] || categoryIcons[category] || categoryIcons['default'];
            const color = categoryColors[sourceType] || categoryColors[category] || categoryColors['default'];
            const timeAgo = this.getTimeAgo(item.published_at || item.created_at);
            const isVerified = item.verified || item.is_featured || item.status === 'published';
            const displaySource = item.source || (item.category || 'NEWS').toUpperCase();
            const itemUrl = item.url || `/articles/${item.slug || item.id}`;
            const isExternal = itemUrl.startsWith('http');
            const isInternal = !isExternal;
            
            // For internal articles, use direct link. For external, use modal expansion
            if (isInternal) {
                return `
                    <a href="${itemUrl}" class="signal-item" style="border-left-color: ${color};">
                        <span class="signal-category" style="color: ${color};">
                            <i class="${icon}"></i> ${displaySource.substring(0, 15).toUpperCase()}
                        </span>
                        <span class="signal-title">${(item.title || '').substring(0, 60)}${item.title && item.title.length > 60 ? '...' : ''}</span>
                        ${isVerified ? '<span class="signal-verified"><i class="fas fa-check-circle"></i></span>' : ''}
                        <span class="signal-time">${timeAgo}</span>
                    </a>
                `;
            } else {
                // External items use modal expansion - clicking opens modal, external icon opens actual URL
                return `
                    <div class="signal-item" style="border-left-color: ${color}; cursor: pointer;" onclick="openSignalModal(${index})">
                        <span class="signal-category" style="color: ${color};">
                            <i class="${icon}"></i> ${displaySource.substring(0, 15).toUpperCase()}
                        </span>
                        <span class="signal-title">${(item.title || '').substring(0, 60)}${item.title && item.title.length > 60 ? '...' : ''}</span>
                        ${isVerified ? '<span class="signal-verified"><i class="fas fa-check-circle"></i></span>' : ''}
                        <a href="${itemUrl}" target="_blank" rel="noopener" class="signal-external" onclick="event.stopPropagation()" title="Open in new tab"><i class="fas fa-external-link-alt"></i></a>
                        <span class="signal-time">${timeAgo}</span>
                    </div>
                `;
            }
        }).join('');
    }
    
    async pollFeed() {
        try {
            const params = new URLSearchParams({
                tier: this.currentTier,
                verified_only: this.verifiedOnly ? '1' : '0',
                limit: '30'
            });
            
            const response = await fetch(`/api/media/feed?${params}`);
            const data = await response.json();
            
            const newItems = data.filter(item => 
                !this.feedItems.find(existing => existing.id === item.id)
            );
            
            if (newItems.length > 0) {
                this.feedItems = data;
                this.renderFeed();
                this.animateNewItems(newItems);
            }
        } catch (error) {
            console.error('Feed poll error:', error);
        }
    }
    
    async pollSentiment() {
        try {
            const response = await fetch('/api/media/sentiment');
            const data = await response.json();
            
            const previousState = this.sentiment.state?.key;
            this.sentiment = data;
            
            this.renderHolographicDial();
            
            if (previousState && previousState !== data.state?.key && previousState !== 'EQUILIBRIUM') {
                this.triggerStateChange(previousState, data.state?.key);
            }
        } catch (error) {
            console.error('Sentiment poll error:', error);
        }
    }
    
    renderHolographicDial() {
        const dialCard = document.getElementById('holoDial');
        const scoreElement = document.getElementById('sentimentScore');
        const stateElement = document.getElementById('sentimentState');
        const needleElement = document.getElementById('sentimentNeedle');
        const keywordsElement = document.getElementById('primaryKeywords');
        const verifiedElement = document.getElementById('verifiedWeight');
        const sampleElement = document.getElementById('sampleSize');
        
        const score = this.sentiment.score || 50;
        const stateKey = this.sentiment.state?.key || 'EQUILIBRIUM';
        const stateLabel = this.sentiment.state?.label || 'EQUILIBRIUM';
        const stateColor = this.sentiment.state?.color || '#ffffff';
        const config = this.stateConfig[stateKey] || this.stateConfig['EQUILIBRIUM'];
        
        if (scoreElement) {
            scoreElement.textContent = Math.round(score);
        }
        
        if (stateElement) {
            stateElement.textContent = stateLabel;
            stateElement.className = `sentiment-state ${config.cssClass}`;
        }
        
        if (dialCard) {
            Object.values(this.stateConfig).forEach(c => dialCard.classList.remove(c.class));
            dialCard.classList.add(config.class);
        }
        
        if (needleElement) {
            const rotation = -90 + (score / 100) * 180;
            needleElement.style.transform = `rotate(${rotation}deg)`;
            
            const glowLine = needleElement.querySelector('.needle-glow');
            if (glowLine) {
                glowLine.style.color = stateColor;
            }
        }
        
        this.updateArcSegments(stateKey);
        
        if (keywordsElement && this.sentiment.keywords) {
            keywordsElement.innerHTML = this.sentiment.keywords
                .slice(0, 3)
                .map(kw => `<span class="keyword-tag">${kw.keyword} <span class="keyword-weight">+${kw.weight}</span></span>`)
                .join('');
            
            if (this.sentiment.keywords.length === 0) {
                keywordsElement.innerHTML = '<span class="keyword-tag" style="opacity: 0.5;">Analyzing signals...</span>';
            }
        }
        
        if (verifiedElement) {
            verifiedElement.textContent = this.sentiment.verified_count || 0;
        }
        
        if (sampleElement) {
            sampleElement.textContent = this.sentiment.sample_size || 0;
        }
    }
    
    updateArcSegments(stateKey) {
        const arcMap = {
            'CRITICAL_CONTENTION': ['arc1'],
            'FRAGMENTED_SIGNAL': ['arc2'],
            'EQUILIBRIUM': ['arc3'],
            'CONSENSUS_FORMING': ['arc4'],
            'ABSOLUTE_SINGULARITY': ['arc5']
        };
        
        document.querySelectorAll('.arc-segment').forEach(arc => {
            arc.classList.remove('active');
        });
        
        const activeArcs = arcMap[stateKey] || ['arc3'];
        activeArcs.forEach(arcId => {
            const arc = document.getElementById(arcId);
            if (arc) arc.classList.add('active');
        });
    }
    
    renderFeed() {
        const feedContainer = document.getElementById('radarFeed');
        const feedCount = document.getElementById('feedCount');
        if (!feedContainer) return;
        
        feedContainer.innerHTML = this.feedItems.map(item => this.renderFeedItem(item)).join('');
        
        if (feedCount) {
            feedCount.textContent = `${this.feedItems.length} signals`;
        }
    }
    
    renderFeedItem(item) {
        const platformIcons = {
            'youtube': 'fab fa-youtube',
            'rss': 'fas fa-rss',
            'rumble': 'fas fa-video',
            'nostr': 'fas fa-bolt',
            'x': 'fab fa-x-twitter',
            'article': 'fas fa-newspaper'
        };
        
        const platformColors = {
            'youtube': '#ff0000',
            'rss': '#ff6b35',
            'rumble': '#85c742',
            'nostr': '#a855f7',
            'x': '#1da1f2',
            'article': '#f7931a'
        };
        
        const tierColors = {
            'macro': '#dc2626',
            'dev': '#3b82f6',
            'mining': '#f59e0b',
            'quant': '#8b5cf6',
            'media': '#10b981'
        };
        
        const tierLabels = {
            'macro': 'MACRO INTEL',
            'dev': 'DEV OPS',
            'mining': 'HASH POWER',
            'quant': 'QUANT DATA',
            'media': 'SIGNAL'
        };
        
        const icon = platformIcons[item.source_type] || 'fas fa-signal';
        const platformColor = platformColors[item.source_type] || '#fff';
        const tierColor = tierColors[item.tier] || '#fff';
        const tierLabel = tierLabels[item.tier] || 'INTEL';
        const timeAgo = this.getTimeAgo(item.published_at);
        const summary = item.summary ? item.summary.substring(0, 120) + '...' : '';
        const signalStrength = item.verified ? 5 : Math.floor(Math.random() * 3) + 2;
        
        // Generate signal strength bars
        const signalBars = Array(5).fill(0).map((_, i) => 
            `<span class="signal-bar ${i < signalStrength ? 'active' : ''}" style="--bar-color: ${tierColor}"></span>`
        ).join('');
        
        return `
            <div class="radar-packet" data-id="${item.id}" onclick="window.openRadarModal(${JSON.stringify(item).replace(/"/g, '&quot;')})">
                <div class="packet-platform-strip" style="background: ${platformColor}">
                    <i class="${icon}"></i>
                </div>
                <div class="packet-body">
                    <div class="packet-meta-row">
                        <span class="packet-source-label">${item.source || 'Unknown'}</span>
                        <div class="packet-signal-strength">
                            ${signalBars}
                        </div>
                        <span class="packet-tier-badge" style="background: ${tierColor}20; color: ${tierColor}; border-color: ${tierColor}">${tierLabel}</span>
                    </div>
                    <div class="packet-headline">${item.title || 'Untitled Signal'}</div>
                    ${summary ? `<div class="packet-preview">${summary}</div>` : ''}
                    <div class="packet-footer">
                        ${item.verified ? '<span class="packet-verified"><i class="fas fa-shield-alt"></i> Verified</span>' : ''}
                        <span class="packet-timestamp"><i class="far fa-clock"></i> ${timeAgo}</span>
                        <span class="packet-action"><i class="fas fa-expand-alt"></i></span>
                    </div>
                </div>
            </div>
        `;
    }
    
    animateNewItems(newItems) {
        newItems.forEach((item, index) => {
            setTimeout(() => {
                const element = document.querySelector(`.intel-packet[data-id="${item.id}"]`);
                if (element) {
                    element.classList.add('packet-new');
                    setTimeout(() => element.classList.remove('packet-new'), 2000);
                }
            }, index * 150);
        });
    }
    
    triggerStateChange(fromState, toState) {
        console.log(`Network state change: ${fromState} -> ${toState}`);
        
        if (window.PulseFX && typeof window.PulseFX.onMajorEvent === 'function') {
            window.PulseFX.onMajorEvent({ type: 'sentiment_shift', from: fromState, to: toState });
        }
        
        const stateElement = document.getElementById('sentimentState');
        const dialCard = document.getElementById('holoDial');
        
        if (stateElement) {
            stateElement.classList.add('state-flash');
            setTimeout(() => stateElement.classList.remove('state-flash'), 1500);
        }
        
        if (dialCard) {
            dialCard.style.animation = 'stateTransition 0.8s ease';
            setTimeout(() => dialCard.style.animation = '', 800);
        }
    }
    
    setupFilters() {
        document.querySelectorAll('.tier-filter').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.tier-filter').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentTier = e.target.dataset.tier;
                this.pollFeed();
            });
        });
        
        const verifiedToggle = document.getElementById('verifiedOnlyToggle');
        if (verifiedToggle) {
            verifiedToggle.addEventListener('change', (e) => {
                this.verifiedOnly = e.target.checked;
                this.pollFeed();
            });
        }
    }
    
    getTimeAgo(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('intelTerminal')) {
        window.intelTerminal = new IntelTerminal();
    }
});
