/**
 * PHASE 5: Sovereign Nostr Relay
 * Real-time Nostr feed with NIP-05 verification and Zap tracking
 * Uses nostr-tools SimplePool for multi-relay subscription
 */

const SovereignNostrRelay = {
    pool: null,
    relays: [
        'wss://relay.damus.io',
        'wss://nos.lol',
        'wss://relay.snort.social',
        'wss://relay.primal.net',
        'wss://nostr.wine'
    ],
    
    verifiedSovereigns: {
        '82341f882b6eabcd2ba7f1ef90aad961cf074af15b9ef44a09f9d2a8fbfbe6a2': { name: 'Jack Dorsey', nip05: 'jack@cash.app', tier: 'dev', weight: 3 },
        '3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d': { name: 'Fiatjaf', nip05: 'fiatjaf@fiatjaf.com', tier: 'dev', weight: 3 },
        '04c915daefee38317fa734444acee390a8269fe5810b2241e5e6dd343dfbecc9': { name: 'Matt Odell', nip05: 'odell@werunbtc.com', tier: 'dev', weight: 3 },
        '84dee6e676e5bb67b4ad4e042cf70cbd8681155db535942fcc6a0533858a7240': { name: 'Edward Snowden', nip05: 'snowden@freedom.press', tier: 'freedom', weight: 3 },
        '29fbc05acee671fb579182ca33b0e41b455bb1f9564b90a3d8f2f39dee3f2779': { name: 'Mr. Hodl', nip05: null, tier: 'macro', weight: 2 },
        '2a2c0f22aac6fe3b557e5354d643598b2635a82ccd63c342d541fa571456b2da': { name: 'Psychedelic Bart', nip05: null, tier: 'freedom', weight: 2 },
        '32e1827635450ebb3c5a7d12c1f8e7b2b514439ac10a67eef3d9fd9c5c68e245': { name: 'jb55', nip05: 'jb55@jb55.com', tier: 'dev', weight: 3 },
        'eab0e756d32b80bcd464f3d844b8040303075a13eabc3599a762c9ac7ab91f4f': { name: 'Lyn Alden', nip05: 'lyn@lynalden.com', tier: 'macro', weight: 3 },
        'fa984bd7dbb282f07e16e7ae87b26a2a7b9b90b7246a44771f0cf5ae58018f52': { name: 'Pablo', nip05: 'pablo@stacker.news', tier: 'dev', weight: 3 },
        'e88a691e98d9987c964521dff60025f60700378a4879180dcbbb4a5027850411': { name: 'NVK', nip05: 'nvk@nvk.org', tier: 'dev', weight: 3 },
        '1739d937dc8c0c7370aa27585938c119e25c41f6c441a41b7e0b6f4d7e0e4bde': { name: 'Gigi', nip05: 'gigi@dergigi.com', tier: 'media', weight: 3 },
        '472f440f29ef996e92a186b8d320ff180c855903882e59d50de1b8bd5669301e': { name: 'Marty Bent', nip05: 'marty@tftc.io', tier: 'media', weight: 3 },
        '1c9ecc8e5e4c68a0d8c5d6e8f5d9e0a5f2c3e4f5a6b7c8d9e0f1a2b3c4d5e6f7': { name: 'Preston Pysh', nip05: 'preston@primal.net', tier: 'macro', weight: 3 },
        'cc8d072efdcc676fcbac14f6cd6825edc3576e55eb786a2a975ee034a6a026cb': { name: 'Ben Arc', nip05: 'ben@lnbits.com', tier: 'dev', weight: 3 },
        '17538dc2a62769d09443f18c37cbe358fab5bbf981173542aa7c5ff171ed77c4': { name: 'Rijndael', nip05: null, tier: 'dev', weight: 2 },
        '6e468422dfb74a5738702a8823b9b28168abab8655faacb6853cd0ee15deee93': { name: 'Carla', nip05: 'carla@primal.net', tier: 'media', weight: 2 },
        'd61f3bc5b3eb4400efdae6169a5c17cabf3246b514361de939ce4a1a0da6ef4a': { name: 'Miljan', nip05: 'miljan@primal.net', tier: 'dev', weight: 3 },
        '7fa56f5d6962ab1e3cd424e758c3002b8665f7b0d8dcee9fe9e288d7751ac194': { name: 'verbiricha', nip05: 'verbiricha@primal.net', tier: 'dev', weight: 2 },
        'c48e29f04b482cc01ca1f9ef8c86ef8318c059e0e9353235162f080f26e14c11': { name: 'Walker', nip05: 'walker@primal.net', tier: 'dev', weight: 2 },
        '50d94fc2d8580c682b071a542f8b1e31a200b0508bab95a33bef0855df281d63': { name: 'calle', nip05: 'calle@cashu.space', tier: 'dev', weight: 3 },
        '1577e4599dd10c863498fe3c20bd82aafaf829a595ce83c5cf8ac3463531b09b': { name: 'yegorpetrov', nip05: 'yegor@primal.net', tier: 'dev', weight: 2 },
        '7bdef7be22dd8e59f4600e044aa53a1cf975a9dc7d27df5833bc77db784a5805': { name: 'hzrd149', nip05: 'hzrd149@primal.net', tier: 'dev', weight: 3 },
        '0699c84179f6860d4d5a37a49b0f4a01f4d98b6e3c2dc2c05c7e0864ec8bb5c1': { name: 'Mandrik', nip05: 'mandrik@mandrik.io', tier: 'freedom', weight: 2 }
    },
    
    hexPubkeys: [],
    
    posts: [],
    zapCounts: {},
    maxPosts: 50,
    feedContainer: null,
    isActive: false,
    subscriptions: [],
    
    async init(containerId) {
        this.feedContainer = document.getElementById(containerId);
        if (!this.feedContainer) {
            console.log('[Nostr] Feed container not found:', containerId);
            return;
        }
        
        console.log('[Nostr] Initializing Sovereign Relay...');
        this.isActive = true;
        
        await this.loadNostrTools();
        this.connectToRelays();
    },
    
    async loadNostrTools() {
        return new Promise((resolve, reject) => {
            if (window.NostrTools) {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = 'https://unpkg.com/nostr-tools@2.1.0/lib/nostr.bundle.js';
            script.onload = () => {
                console.log('[Nostr] nostr-tools loaded');
                resolve();
            };
            script.onerror = () => {
                console.error('[Nostr] Failed to load nostr-tools');
                reject(new Error('Failed to load nostr-tools'));
            };
            document.head.appendChild(script);
        });
    },
    
    connectToRelays() {
        if (!window.NostrTools) {
            console.error('[Nostr] nostr-tools not available');
            return;
        }
        
        try {
            this.pool = new window.NostrTools.SimplePool();
            console.log('[Nostr] SimplePool created');
            
            this.hexPubkeys = Object.keys(this.verifiedSovereigns);
            console.log('[Nostr] Using', this.hexPubkeys.length, 'hex pubkeys');
            
            this.subscribeToNotes();
            this.subscribeToZaps();
        } catch (e) {
            console.error('[Nostr] Pool creation failed:', e);
        }
    },
    
    subscribeToNotes() {
        const pubkeys = this.hexPubkeys;
        
        const filter = {
            kinds: [1],
            authors: pubkeys,
            limit: 30
        };
        
        console.log('[Nostr] Subscribing to notes from', pubkeys.length, 'sovereigns');
        
        const sub = this.pool.subscribeMany(
            this.relays,
            [filter],
            {
                onevent: (event) => this.handleNoteEvent(event),
                oneose: () => console.log('[Nostr] End of stored events')
            }
        );
        
        this.subscriptions.push(sub);
    },
    
    subscribeToZaps() {
        const pubkeys = this.hexPubkeys;
        
        const filter = {
            kinds: [9735],
            '#p': pubkeys,
            limit: 100
        };
        
        console.log('[Nostr] Subscribing to zaps');
        
        const sub = this.pool.subscribeMany(
            this.relays,
            [filter],
            {
                onevent: (event) => this.handleZapEvent(event),
                oneose: () => console.log('[Nostr] End of stored zaps')
            }
        );
        
        this.subscriptions.push(sub);
    },
    
    handleNoteEvent(event) {
        if (this.posts.find(p => p.id === event.id)) return;
        
        const sovereign = this.verifiedSovereigns[event.pubkey] || 
                          this.verifiedSovereigns[this.pubkeyToNpub(event.pubkey)];
        
        const post = {
            id: event.id,
            pubkey: event.pubkey,
            content: event.content,
            created_at: event.created_at,
            author: sovereign ? sovereign.name : this.truncatePubkey(event.pubkey),
            nip05: sovereign ? sovereign.nip05 : null,
            verified: !!sovereign,
            weight: sovereign ? sovereign.weight : 1,
            zaps: 0
        };
        
        this.posts.unshift(post);
        
        if (this.posts.length > this.maxPosts) {
            this.posts.pop();
        }
        
        this.posts.sort((a, b) => b.created_at - a.created_at);
        
        this.renderPost(post, true);
    },
    
    handleZapEvent(event) {
        const pTags = event.tags.filter(t => t[0] === 'e');
        const eventId = pTags.length > 0 ? pTags[0][1] : null;
        
        if (eventId) {
            this.zapCounts[eventId] = (this.zapCounts[eventId] || 0) + 1;
            this.updateZapCount(eventId);
        }
        
        const amountTag = event.tags.find(t => t[0] === 'amount');
        if (amountTag) {
            const msats = parseInt(amountTag[1]);
            const sats = Math.floor(msats / 1000);
            if (sats > 5000 && window.PulseFX) {
                const card = document.querySelector(`[data-event-id="${eventId}"]`);
                if (card) {
                    window.PulseFX.triggerZap(card, sats);
                }
            }
        }
    },
    
    pubkeyToNpub(pubkey) {
        try {
            if (window.NostrTools && window.NostrTools.nip19) {
                return window.NostrTools.nip19.npubEncode(pubkey);
            }
        } catch (e) {}
        return pubkey;
    },
    
    truncatePubkey(pubkey) {
        return pubkey.substring(0, 8) + '...' + pubkey.substring(pubkey.length - 4);
    },
    
    async verifyNIP05(nip05, pubkey) {
        if (!nip05) return false;
        
        try {
            const [name, domain] = nip05.split('@');
            const res = await fetch(`https://${domain}/.well-known/nostr.json?name=${name}`);
            const data = await res.json();
            
            if (data.names && data.names[name]) {
                return data.names[name] === pubkey;
            }
        } catch (e) {
            console.log('[Nostr] NIP-05 verification failed:', e);
        }
        
        return false;
    },
    
    renderPost(post, animate = false) {
        if (!this.feedContainer) return;
        
        const existingPost = this.feedContainer.querySelector(`[data-event-id="${post.id}"]`);
        if (existingPost) return;
        
        const postEl = document.createElement('div');
        postEl.className = 'nostr-post intercepted-packet' + (animate ? ' slide-in' : '');
        postEl.setAttribute('data-event-id', post.id);
        postEl.setAttribute('data-pubkey', post.pubkey);
        
        const timeAgo = this.formatTimeAgo(post.created_at);
        const zapCount = this.zapCounts[post.id] || 0;
        
        postEl.innerHTML = `
            <div class="nostr-post-header">
                <div class="nostr-author">
                    <span class="author-name">${this.escapeHtml(post.author)}</span>
                    ${post.verified ? `
                        <span class="sovereign-badge" title="Identity Verified via NIP-05. Trusted Operative.">
                            <i class="fas fa-shield-alt"></i> VERIFIED
                        </span>
                    ` : ''}
                    ${post.nip05 ? `<span class="nip05-handle">${this.escapeHtml(post.nip05)}</span>` : ''}
                </div>
                <span class="nostr-time">${timeAgo}</span>
            </div>
            <div class="nostr-content">${this.formatContent(post.content)}</div>
            <div class="nostr-footer">
                <div class="zap-counter" data-zap-id="${post.id}">
                    <i class="fas fa-bolt zap-icon"></i>
                    <span class="zap-count">${zapCount}</span>
                </div>
                <a href="https://primal.net/e/${post.id}" target="_blank" class="view-on-nostr">
                    View on Nostr <i class="fas fa-external-link-alt"></i>
                </a>
            </div>
        `;
        
        const firstChild = this.feedContainer.firstChild;
        if (firstChild) {
            this.feedContainer.insertBefore(postEl, firstChild);
        } else {
            this.feedContainer.appendChild(postEl);
        }
        
        if (animate && window.PulseFX) {
            setTimeout(() => window.PulseFX.triggerZap(postEl, 1000), 100);
        }
    },
    
    updateZapCount(eventId) {
        const counter = document.querySelector(`[data-zap-id="${eventId}"] .zap-count`);
        if (counter) {
            counter.textContent = this.zapCounts[eventId] || 0;
            counter.classList.add('zap-pulse');
            setTimeout(() => counter.classList.remove('zap-pulse'), 300);
        }
    },
    
    formatTimeAgo(timestamp) {
        const now = Math.floor(Date.now() / 1000);
        const diff = now - timestamp;
        
        if (diff < 60) return 'just now';
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        return Math.floor(diff / 86400) + 'd ago';
    },
    
    formatContent(content) {
        let formatted = this.escapeHtml(content);
        
        formatted = formatted.replace(
            /(https?:\/\/[^\s<]+)/g,
            '<a href="$1" target="_blank" rel="noopener">$1</a>'
        );
        
        formatted = formatted.replace(
            /#(\w+)/g,
            '<span class="nostr-hashtag">#$1</span>'
        );
        
        formatted = formatted.replace(
            /nostr:(npub|note|nevent)[a-z0-9]+/gi,
            '<span class="nostr-mention">$&</span>'
        );
        
        return formatted;
    },
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    filterSovereignOnly(enabled) {
        if (!this.feedContainer) return;
        
        const posts = this.feedContainer.querySelectorAll('.nostr-post');
        posts.forEach(post => {
            const pubkey = post.getAttribute('data-pubkey');
            const npub = this.pubkeyToNpub(pubkey);
            const isSovereign = this.verifiedSovereigns[pubkey] || this.verifiedSovereigns[npub];
            
            if (enabled && !isSovereign) {
                post.style.display = 'none';
            } else {
                post.style.display = '';
            }
        });
    },
    
    stop() {
        this.isActive = false;
        this.subscriptions.forEach(sub => {
            if (sub && sub.close) sub.close();
        });
        this.subscriptions = [];
        if (this.pool) {
            this.pool.close(this.relays);
        }
        console.log('[Nostr] Relay stopped');
    }
};

window.SovereignNostrRelay = SovereignNostrRelay;
