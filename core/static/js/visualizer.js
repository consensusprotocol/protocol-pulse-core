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
        
        // Check if post-processing is available
        if (!THREE.EffectComposer || !THREE.RenderPass || !THREE.UnrealBloomPass) {
            console.log('Post-processing not available, using direct rendering');
            this.composer = null;
            return;
        }
        
        try {
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
            
            if (THREE.ShaderPass && THREE.FXAAShader) {
                const fxaaPass = new THREE.ShaderPass(THREE.FXAAShader);
                fxaaPass.uniforms['resolution'].value.set(1 / width, 1 / height);
                this.composer.addPass(fxaaPass);
                this.fxaaPass = fxaaPass;
        }
        
        if (THREE.BokehPass) {
            const bokehPass = new THREE.BokehPass(this.scene, this.camera, {
                focus: 500,
                aperture: 0.00003,
                maxblur: 0.005
            });
            this.composer.addPass(bokehPass);
            this.bokehPass = bokehPass;
        }
        } catch (e) {
            console.error('Post-processing init failed:', e);
            this.composer = null;
        }
    }
    
    initAnimatedUniverse() {
        // Background now handled by HTML5 video element in base.html
        // Three.js scene is transparent to show video behind
        console.log('Video background mode - Three.js scene transparent');
    }
    
    updateBackgroundAnimation() {
        // Background animation removed - video handles visual interest
    }
    
    createBackgroundLayers() {
        // Decorative layers removed - video background used instead
        this.initAnimatedUniverse();
        this.initAudioEngine();
    }
    
    triggerWhaleShockwave() {
        // Camera shake
        this.triggerScreenShake();
        
        // Play whale impact sound
        if (this.pulseAudio) {
            this.pulseAudio.triggerWhaleImpact();
        }
        
        // Add shockwave overlay
        document.body.classList.add('whale-shockwave-active');
        setTimeout(() => document.body.classList.remove('whale-shockwave-active'), 500);
    }
    
    triggerScreenShake() {
        const container = this.container;
        if (!container) return;
        
        let intensity = 10;
        const shakeDuration = 300;
        const start = Date.now();
        
        const shake = () => {
            const elapsed = Date.now() - start;
            if (elapsed < shakeDuration) {
                const x = (Math.random() - 0.5) * intensity;
                const y = (Math.random() - 0.5) * intensity;
                container.style.transform = `translate(${x}px, ${y}px)`;
                intensity *= 0.95;
                requestAnimationFrame(shake);
            } else {
                container.style.transform = '';
            }
        };
        shake();
    }
    
    initAudioEngine() {
        // Audio engine for ambient hum and whale impacts
        this.pulseAudio = {
            ctx: null,
            masterGain: null,
            isInitialized: false,
            
            init: function() {
                if (this.isInitialized) return;
                try {
                    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
                    this.masterGain = this.ctx.createGain();
                    this.masterGain.connect(this.ctx.destination);
                    this.masterGain.gain.value = 0.3;
                    this.ctx.resume();
                    this.startAmbientHum();
                    this.isInitialized = true;
                    console.log('Sovereign Audio Link Established');
                } catch (e) {
                    console.log('Audio not supported:', e);
                }
            },
            
            startAmbientHum: function() {
                if (!this.ctx) return;
                // Deep meditative 55Hz and 110Hz hum
                [55, 110.5].forEach(freq => {
                    const osc = this.ctx.createOscillator();
                    const gain = this.ctx.createGain();
                    
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
                    gain.gain.setValueAtTime(0.02, this.ctx.currentTime);
                    
                    osc.connect(gain);
                    gain.connect(this.masterGain);
                    osc.start();
                });
            },
            
            triggerWhaleImpact: function() {
                if (!this.ctx || !this.isInitialized) return;
                try {
                    const now = this.ctx.currentTime;
                    const osc = this.ctx.createOscillator();
                    const gain = this.ctx.createGain();
                    
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(60, now);
                    osc.frequency.exponentialRampToValueAtTime(30, now + 0.3);
                    
                    gain.gain.setValueAtTime(0.8, now);
                    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
                    
                    osc.connect(gain);
                    gain.connect(this.masterGain);
                    osc.start(now);
                    osc.stop(now + 0.5);
                } catch (e) {
                    console.log('Audio impact error:', e);
                }
            },
            
            triggerSpatialZap: function(isTier2 = false) {
                if (!this.ctx || !this.isInitialized) return;
                try {
                    const now = this.ctx.currentTime;
                    const duration = isTier2 ? 0.3 : 0.15;
                    
                    const panner = this.ctx.createStereoPanner();
                    panner.connect(this.masterGain);
                    
                    const sawOsc = this.ctx.createOscillator();
                    const sawGain = this.ctx.createGain();
                    sawOsc.type = 'sawtooth';
                    sawOsc.frequency.setValueAtTime(isTier2 ? 800 : 600, now);
                    sawOsc.frequency.exponentialRampToValueAtTime(200, now + duration);
                    sawGain.gain.setValueAtTime(isTier2 ? 0.15 : 0.08, now);
                    sawGain.gain.exponentialRampToValueAtTime(0.001, now + duration);
                    sawOsc.connect(sawGain);
                    sawGain.connect(panner);
                    sawOsc.start(now);
                    sawOsc.stop(now + duration);
                    
                    const bufferSize = this.ctx.sampleRate * 0.1;
                    const noiseBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
                    const noiseData = noiseBuffer.getChannelData(0);
                    for (let i = 0; i < bufferSize; i++) {
                        noiseData[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
                    }
                    const noiseSource = this.ctx.createBufferSource();
                    noiseSource.buffer = noiseBuffer;
                    const noiseGain = this.ctx.createGain();
                    noiseGain.gain.setValueAtTime(isTier2 ? 0.2 : 0.1, now);
                    noiseGain.gain.exponentialRampToValueAtTime(0.001, now + duration * 0.8);
                    noiseSource.connect(noiseGain);
                    noiseGain.connect(panner);
                    noiseSource.start(now);
                    
                    panner.pan.setValueAtTime(-1, now);
                    panner.pan.linearRampToValueAtTime(1, now + 0.2);
                    
                    if (isTier2 && Math.random() < 0.02) {
                        this.triggerSarahVoice();
                    }
                } catch (e) {
                    console.log('Spatial zap error:', e);
                }
            },
            
            triggerSarahVoice: function() {
                if (!this.ctx || !this.isInitialized) return;
                try {
                    const now = this.ctx.currentTime;
                    const phrases = ['L2 Settlement Verified.', 'Current established.'];
                    const phrase = phrases[Math.floor(Math.random() * phrases.length)];
                    
                    if ('speechSynthesis' in window) {
                        const utterance = new SpeechSynthesisUtterance(phrase);
                        utterance.rate = 0.85;
                        utterance.pitch = 1.1;
                        utterance.volume = 0.4;
                        
                        const voices = speechSynthesis.getVoices();
                        const femaleVoice = voices.find(v => v.name.includes('Samantha') || v.name.includes('Karen') || v.name.includes('Victoria') || v.lang.includes('en'));
                        if (femaleVoice) utterance.voice = femaleVoice;
                        
                        speechSynthesis.speak(utterance);
                        console.log('[Sarah] ' + phrase);
                    }
                } catch (e) {
                    console.log('Sarah voice error:', e);
                }
            }
        };
        
        // Initialize audio on first user interaction
        const initAudio = () => {
            this.pulseAudio.init();
            document.removeEventListener('click', initAudio);
            document.removeEventListener('touchstart', initAudio);
        };
        document.addEventListener('click', initAudio);
        document.addEventListener('touchstart', initAudio);
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
    
    createBlockNotification() {
        this.blockNotification = document.createElement('div');
        this.blockNotification.className = 'block-notification';
        this.blockNotification.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) scale(0);
            background: radial-gradient(ellipse at center, rgba(247, 147, 26, 0.3) 0%, rgba(0,0,0,0.95) 70%);
            border: 2px solid rgba(247, 147, 26, 0.8);
            border-radius: 20px;
            padding: 40px 60px;
            color: #fff;
            font-family: 'JetBrains Mono', monospace;
            text-align: center;
            z-index: 10001;
            backdrop-filter: blur(20px);
            box-shadow: 0 0 100px rgba(247, 147, 26, 0.5), inset 0 0 60px rgba(247, 147, 26, 0.1);
            opacity: 0;
            transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
        `;
        this.blockNotification.innerHTML = `
            <div style="font-size: 3rem; margin-bottom: 15px;">⛏️</div>
            <div style="font-size: 1.5rem; color: #f7931a; font-weight: bold; margin-bottom: 10px;">BLOCK MINED</div>
            <div style="font-size: 2rem; color: #fff;" id="block-height-display">#---,---</div>
            <div style="font-size: 0.8rem; color: rgba(255,255,255,0.6); margin-top: 15px;">Crystallized into eternity</div>
        `;
        document.body.appendChild(this.blockNotification);
    }
    
    showBlockNotification(blockHeight) {
        const heightEl = this.blockNotification.querySelector('#block-height-display');
        if (heightEl) {
            heightEl.textContent = '#' + blockHeight.toLocaleString();
        }
        
        this.blockNotification.style.opacity = '1';
        this.blockNotification.style.transform = 'translate(-50%, -50%) scale(1)';
        
        setTimeout(() => {
            this.blockNotification.style.opacity = '0';
            this.blockNotification.style.transform = 'translate(-50%, -50%) scale(0.8)';
        }, 3000);
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
        
        window.addEventListener('scroll', () => {
            this.tooltip.style.display = 'none';
            this.lastHoveredParticle = null;
        }, { passive: true });
        
        canvas.addEventListener('mouseleave', () => {
            this.tooltip.style.display = 'none';
            this.lastHoveredParticle = null;
        });
    }
    
    generateFakeTxid() {
        const chars = '0123456789abcdef';
        let txid = '';
        for (let i = 0; i < 64; i++) {
            txid += chars[Math.floor(Math.random() * 16)];
        }
        return txid;
    }
    
    onMouseMove(event) {
        if (this.isMobile) return;
        
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        this.checkHover(event.clientX, event.clientY);
    }
    
    onTouchStart(event) {
        if (event.touches.length === 1) {
            const touch = event.touches[0];
            const rect = this.renderer.domElement.getBoundingClientRect();
            this.mouse.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
            this.mouse.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;
            
            this.touchStartTime = Date.now();
            this.touchStartPos = { x: touch.clientX, y: touch.clientY };
        }
    }
    
    onTouchEnd(event) {
        console.log('Touch end detected');
        if (this.touchStartTime && Date.now() - this.touchStartTime < 300) {
            console.log('Short tap detected, calling handleTap');
            this.handleTap(this.touchStartPos.x, this.touchStartPos.y);
        }
        this.tooltip.style.display = 'none';
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
            </div>
        `;
    }
    
    onClick(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
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
                console.log('Particle hit! isMobile:', this.isMobile, 'TXID:', particle.txid.substring(0, 8));
                if (this.isMobile) {
                    this.showTxPopup(particle);
                } else {
                    window.open(`https://mempool.space/tx/${particle.txid}`, '_blank');
                }
            } else {
                console.log('Particle hit but not a real transaction - visual only');
            }
        }
    }
    
    showTxPopup(particle) {
        console.log('showTxPopup called for:', particle.txid);
        
        const overlay = document.getElementById('tx-popup-overlay');
        const card = document.getElementById('tx-popup-card');
        
        console.log('Popup elements found:', { overlay: !!overlay, card: !!card });
        
        if (!card || !overlay) {
            console.error('TX Popup elements not found in DOM!');
            return;
        }
        
        const amountEl = document.getElementById('tx-popup-amount');
        const fiatEl = document.getElementById('tx-popup-fiat');
        const txidEl = document.getElementById('tx-popup-txid');
        const feeEl = document.getElementById('tx-popup-fee');
        const verifyLink = document.getElementById('tx-popup-verify');
        
        const btcPrice = window.currentBtcPrice || 88000;
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
        
        console.log('Popup should now be visible');
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
        particle.velocity = new THREE.Vector3(
            (Math.random() - 0.5) * 0.02,
            (Math.random() - 0.5) * 0.02,
            0
        );
        particle.targetAngle = Math.random() * Math.PI * 2;
        particle.targetRadius = 80 + Math.random() * 50;
        particle.phase = 'traveling';
        particle.dockProgress = 0;
        
        const sizes = this.particleGeometry.attributes.size.array;
        const baseSize = this.isMobile ? 8 : 6;
        const sizeMultiplier = this.getValueSizeMultiplier(particle.value);
        sizes[idx] = baseSize * sizeMultiplier;
        
        this.particleGeometry.attributes.position.needsUpdate = true;
        this.particleGeometry.attributes.color.needsUpdate = true;
        this.particleGeometry.attributes.size.needsUpdate = true;
    }
    
    getValueSizeMultiplier(btcValue) {
        return SovereignTerminal.getValueSizeMultiplierStatic(btcValue);
    }
    
    getValueSizeMultiplierStatic(btcValue) {
        return SovereignTerminal.getValueSizeMultiplierStatic(btcValue);
    }
    
    static getValueSizeMultiplierStatic(btcValue) {
        if (btcValue >= 10) return 3.0;
        if (btcValue >= 5) return 2.5;
        if (btcValue >= 1) return 2.0;
        if (btcValue >= 0.5) return 1.5;
        if (btcValue >= 0.1) return 1.2;
        return 1.0;
    }
    
    updateParticles() {
        const positions = this.particleGeometry.attributes.position.array;
        const colors = this.particleGeometry.attributes.color.array;
        const time = this.clock.getElapsedTime();
        
        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];
            const idx = i * 3;
            
            const currentX = positions[idx];
            const currentY = positions[idx + 1];
            const currentZ = positions[idx + 2];
            
            const distToCenter = Math.sqrt(currentX * currentX + currentY * currentY);
            
            if (p.phase === 'supernova') {
                p.supernovaTime += 0.016;
                
                positions[idx] += p.velocity.x;
                positions[idx + 1] += p.velocity.y;
                positions[idx + 2] += p.velocity.z;
                
                p.velocity.x *= 0.96;
                p.velocity.y *= 0.96;
                p.velocity.z *= 0.96;
                
                const decay = Math.max(0, 1 - (p.supernovaTime / 2.5));
                const crimsonBlend = Math.min(1, p.supernovaTime / 1.5);
                
                colors[idx] = 1.0 * (1 - crimsonBlend) + 0.7 * crimsonBlend;
                colors[idx + 1] = 0.9 * (1 - crimsonBlend) + 0.1 * crimsonBlend;
                colors[idx + 2] = 0.8 * (1 - crimsonBlend) + 0.05 * crimsonBlend;
                
                if (this.pointSystem && this.pointSystem.material) {
                    this.pointSystem.material.opacity = Math.max(0.2, decay);
                }
                
            } else if (p.phase === 'reforming') {
                p.reformProgress += 0.008;
                const t = Math.min(1, p.reformProgress);
                const ease = t * t * (3 - 2 * t);
                
                positions[idx] = positions[idx] + (p.targetX - positions[idx]) * ease * 0.05;
                positions[idx + 1] = positions[idx + 1] + (p.targetY - positions[idx + 1]) * ease * 0.05;
                positions[idx + 2] = positions[idx + 2] + (p.targetZ - positions[idx + 2]) * ease * 0.05;
                
                colors[idx] = 0.7 + t * 0.2;
                colors[idx + 1] = 0.1 + t * 0.4;
                colors[idx + 2] = 0.05 + t * 0.05;
                
                if (this.pointSystem && this.pointSystem.material) {
                    this.pointSystem.material.opacity = 0.2 + t * 0.75;
                }
                
                if (p.reformProgress >= 1) {
                    p.phase = 'orb';
                    p.orbitSpeed = 0.0003 + Math.random() * 0.0002;
                }
                
            } else if (p.phase === 'orb') {
                const slot = this.fibonacciSlots[p.slotIndex];
                const breathe = 1 + Math.sin(time * 0.3) * 0.03;
                const orbitAngle = time * 0.05 + p.orbitOffset;
                
                const targetX = slot.x * breathe;
                const targetY = slot.y * breathe + p.orbCenterY;
                const targetZ = slot.z * 0.3 * breathe - 50;
                
                const cosA = Math.cos(orbitAngle);
                const sinA = Math.sin(orbitAngle);
                const rotatedX = targetX * cosA - targetZ * sinA;
                const rotatedZ = targetX * sinA + targetZ * cosA;
                
                const dx = rotatedX - currentX;
                const dy = targetY - currentY;
                const dz = rotatedZ - currentZ;
                
                positions[idx] += dx * this.springStrength;
                positions[idx + 1] += dy * this.springStrength;
                positions[idx + 2] += dz * this.springStrength;
                
                colors[idx] = 0.9;
                colors[idx + 1] = 0.5;
                colors[idx + 2] = 0.1;
            } else if (p.phase === 'traveling') {
                const targetX = Math.cos(p.targetAngle) * p.targetRadius;
                const targetY = Math.sin(p.targetAngle) * p.targetRadius * 0.6;
                
                const dx = targetX - currentX;
                const dy = targetY - currentY;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                if (dist < 5) {
                    p.phase = 'docked';
                    p.dockProgress = 0;
                } else {
                    const force = 0.00002;
                    p.velocity.x += dx * force;
                    p.velocity.y += dy * force;
                    
                    p.velocity.x *= 0.995;
                    p.velocity.y *= 0.995;
                    
                    const maxSpeed = 0.15;
                    const speed = p.velocity.length();
                    if (speed > maxSpeed) {
                        p.velocity.multiplyScalar(maxSpeed / speed);
                    }
                    
                    positions[idx] += p.velocity.x;
                    positions[idx + 1] += p.velocity.y;
                }
            } else if (p.phase === 'docked') {
                p.dockProgress += 0.016;
                
                const wobble = Math.sin(time * 0.5 + i * 0.1) * 2;
                const orbitSpeed = 0.02;
                p.targetAngle += orbitSpeed * 0.016;
                
                positions[idx] = Math.cos(p.targetAngle) * (p.targetRadius + wobble);
                positions[idx + 1] = Math.sin(p.targetAngle) * (p.targetRadius * 0.6 + wobble * 0.5);
                
                const dockFade = Math.min(1, p.dockProgress * 0.5);
                colors[idx] = 0.97 * dockFade + colors[idx] * (1 - dockFade);
                colors[idx + 1] = 0.58 * dockFade + colors[idx + 1] * (1 - dockFade);
                colors[idx + 2] = 0.1 * dockFade + colors[idx + 2] * (1 - dockFade);
            }
        }
        
        this.particleGeometry.attributes.position.needsUpdate = true;
        this.particleGeometry.attributes.color.needsUpdate = true;
    }
    
    updateAnimatedElements() {
        const time = this.clock.getElapsedTime();
        
        const camAmplitude = this.isMobile ? 6 : 12;
        
        if (!this.cameraShaking) {
            this.camera.position.x = Math.sin(time * 0.012) * camAmplitude;
            this.camera.position.y = Math.cos(time * 0.01) * (camAmplitude * 0.3);
        }
        this.camera.lookAt(0, 0, 0);
    }
    
    triggerBlockSupernova() {
        console.log('SUPERNOVA TRIGGERED!');
        
        // Sync heartbeat with block crystallization
        this.syncHeartbeatWithBlock();
        
        const positions = this.particleGeometry.attributes.position.array;
        const orbCenterY = 70;
        
        this.particles.forEach((p, i) => {
            const idx = i * 3;
            const currentX = positions[idx];
            const currentY = positions[idx + 1];
            const currentZ = positions[idx + 2];
            
            const dirX = currentX;
            const dirY = currentY - orbCenterY;
            const dirZ = currentZ + 50;
            const len = Math.sqrt(dirX * dirX + dirY * dirY + dirZ * dirZ) || 1;
            
            const force = Math.random() * 20 + 10;
            p.velocity = new THREE.Vector3(
                (dirX / len) * force + (Math.random() - 0.5) * 5,
                (dirY / len) * force + (Math.random() - 0.5) * 5,
                (dirZ / len) * force * 0.3
            );
            
            p.phase = 'supernova';
            p.supernovaTime = 0;
            p.originalSize = this.isMobile ? 8 : 6;
        });
        
        this.triggerScreenShake();
        
        setTimeout(() => this.reformParticleOrb(), 3000);
    }
    
    triggerScreenShake() {
        this.cameraShaking = true;
        const intensity = 8;
        const originalX = this.camera.position.x;
        const originalY = this.camera.position.y;
        let shakeCount = 0;
        const maxShakes = 10;
        
        const shake = () => {
            if (shakeCount >= maxShakes) {
                this.cameraShaking = false;
                return;
            }
            
            this.camera.position.x = originalX + (Math.random() - 0.5) * intensity;
            this.camera.position.y = originalY + (Math.random() - 0.5) * intensity;
            shakeCount++;
            
            setTimeout(shake, 50);
        };
        
        shake();
    }
    
    syncHeartbeatWithBlock() {
        // Trigger heartbeat visual sync when a new block is detected
        const heartbeatCore = document.querySelector('.heartbeat-core');
        const healthBlockTime = document.getElementById('health-block-time');
        const healthStatus = document.getElementById('health-status');
        
        if (heartbeatCore) {
            // Flash the heartbeat core
            heartbeatCore.classList.add('synced');
            heartbeatCore.style.background = 'radial-gradient(circle, #22c55e 0%, #166534 100%)';
            heartbeatCore.style.boxShadow = '0 0 40px rgba(34, 197, 94, 0.8), 0 0 80px rgba(34, 197, 94, 0.4)';
            
            setTimeout(() => {
                heartbeatCore.classList.remove('synced');
                heartbeatCore.style.boxShadow = '';
            }, 1000);
        }
        
        // Reset block time to 0:00
        if (healthBlockTime) {
            healthBlockTime.textContent = '0:00';
        }
        
        // Set status to "Just Mined"
        if (healthStatus) {
            healthStatus.textContent = 'Just Mined';
            healthStatus.className = 'heartbeat-status normal';
        }
        
        // Dispatch custom event for other listeners
        window.dispatchEvent(new CustomEvent('block-crystallized'));
    }
    
    reformParticleOrb() {
        const orbCenterY = 70;
        
        this.particles.forEach((p, i) => {
            const slot = this.fibonacciSlots[p.slotIndex];
            
            p.orbCenterY = orbCenterY;
            p.phase = 'reforming';
            p.reformProgress = 0;
            p.targetX = slot.x;
            p.targetY = slot.y + orbCenterY;
            p.targetZ = slot.z * 0.3 - 50;
        });
    }
    
    connectWebSocket() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) return;
        
        try {
            this.ws = new WebSocket('wss://mempool.space/api/v1/ws');
            
            this.ws.onopen = () => {
                console.log('Connected to mempool.space');
                this.ws.send(JSON.stringify({ action: 'want', data: ['blocks', 'mempool-blocks'] }));
                this.updateVizHUD({ connected: true });
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.block) {
                        if (data.block.height > this.lastBlockHeight) {
                            this.lastBlockHeight = data.block.height;
                            this.triggerBlockSupernova();
                            setTimeout(() => this.showBlockNotification(data.block.height), 800);
                        }
                    }
                    
                    // Check for whale transactions (1000+ BTC = 100,000,000,000 satoshis)
                    if (data.x && data.x.value >= 100000000000) {
                        console.log('!!! MEGA WHALE INTERCEPTED !!!', data.x.value / 100000000, 'BTC');
                        this.triggerWhaleShockwave();
                        
                        // Update whale alert banner if exists
                        const alertBanner = document.getElementById('whale-alert-banner');
                        if (alertBanner) {
                            alertBanner.innerText = `SIGNAL DETECTED: ${(data.x.value / 100000000).toLocaleString()} BTC MOVE`;
                            alertBanner.classList.add('active');
                            setTimeout(() => alertBanner.classList.remove('active'), 5000);
                        }
                    }
                    
                    if (data['mempool-blocks']) {
                        const blocks = data['mempool-blocks'];
                        let totalTxs = 0;
                        let totalSize = 0;
                        
                        blocks.forEach(block => {
                            totalTxs += block.nTx || 0;
                            totalSize += block.blockVSize || 0;
                        });
                        
                        if (!this.lastTxFetch || Date.now() - this.lastTxFetch > 5000) {
                            this.fetchRecentTransactions();
                        }
                        
                        this.updateVizHUD({
                            mempoolSize: (totalSize / 1000000).toFixed(1),
                            unconfirmed: totalTxs
                        });
                    }
                } catch (e) {
                    console.error('WebSocket parse error:', e);
                }
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket closed, reconnecting...');
                this.updateVizHUD({ connected: false });
                setTimeout(() => this.connectWebSocket(), 3000);
            };
            
            this.ws.onerror = () => {
                this.ws.close();
            };
            
        } catch (e) {
            console.error('WebSocket error:', e);
            this.startSimulatedData();
        }
    }
    
    startSimulatedData() {
        console.log('Using simulated mempool data');
        this.updateVizHUD({ connected: true, simulated: true });
        
        const spawnInterval = this.isMobile ? 1200 : 800;
        setInterval(() => {
            this.spawnTransaction({
                value: Math.random() * 5,
                feeRate: 5 + Math.random() * 80,
                txid: this.generateFakeTxid()
            });
        }, spawnInterval);
        
        setInterval(() => {
            this.updateVizHUD({
                mempoolSize: (50 + Math.random() * 150).toFixed(1),
                unconfirmed: Math.floor(50000 + Math.random() * 100000)
            });
        }, 5000);
        
        setInterval(() => {
            this.lastBlockHeight = 880000 + Math.floor(Math.random() * 1000);
            this.showBlockNotification(this.lastBlockHeight);
        }, 90000);
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
        this.updateAnimatedElements();
        this.updateBackgroundAnimation();
        // Holographic disc removed
        
        // Bypass EffectComposer to preserve alpha transparency for video background
        this.renderer.render(this.scene, this.camera);
    }
    
    onResize() {
        const width = this.container.clientWidth || window.innerWidth;
        const height = this.container.clientHeight || (window.innerHeight - 60);
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
        if (this.composer) {
            this.composer.setSize(width, height);
        }
    }
    
    async fetchRecentTransactions() {
        this.lastTxFetch = Date.now();
        
        try {
            const response = await fetch('https://mempool.space/api/mempool/recent');
            const transactions = await response.json();
            
            if (Array.isArray(transactions) && transactions.length > 0) {
                const txsToSpawn = transactions.slice(0, 5);
                
                txsToSpawn.forEach(tx => {
                    const valueBtc = (tx.value || 0) / 100000000;
                    this.spawnTransaction({
                        txid: tx.txid,
                        value: valueBtc || Math.random() * 2,
                        feeRate: tx.fee ? (tx.fee / (tx.vsize || 140)) : (5 + Math.random() * 50)
                    });
                });
                
                console.log(`Spawned ${txsToSpawn.length} real transactions`);
            }
        } catch (error) {
            console.error('Failed to fetch recent transactions:', error);
        }
    }
    
    async loadInitialTransactions() {
        try {
            const [recentRes, mempoolRes] = await Promise.all([
                fetch('https://mempool.space/api/mempool/recent'),
                fetch('https://mempool.space/api/mempool')
            ]);
            
            const recentTxs = await recentRes.json();
            const mempoolData = await mempoolRes.json();
            
            let allTxIds = [];
            
            if (Array.isArray(recentTxs)) {
                allTxIds = recentTxs.map(tx => ({
                    txid: tx.txid,
                    value: (tx.value || 0) / 100000000,
                    fee: tx.fee,
                    vsize: tx.vsize
                }));
            }
            
            const transactions = allTxIds;
            
            if (Array.isArray(transactions)) {
                const txsToAssign = transactions.slice(0, Math.min(transactions.length, this.maxParticles));
                
                txsToAssign.forEach((tx, i) => {
                    if (this.particles[i]) {
                        this.particles[i].txid = tx.txid;
                        this.particles[i].isReal = true;
                        this.particles[i].value = tx.value || Math.random() * 2;
                        this.particles[i].feeRate = tx.fee && tx.vsize ? (tx.fee / tx.vsize) : (5 + Math.random() * 50);
                        
                        const colors = this.particleGeometry.attributes.color.array;
                        const feeRate = this.particles[i].feeRate;
                        if (feeRate > 50) {
                            colors[i * 3] = 0.94; colors[i * 3 + 1] = 0.27; colors[i * 3 + 2] = 0.27;
                        } else if (feeRate > 15) {
                            colors[i * 3] = 0.97; colors[i * 3 + 1] = 0.58; colors[i * 3 + 2] = 0.1;
                        } else {
                            colors[i * 3] = 0.13; colors[i * 3 + 1] = 0.77; colors[i * 3 + 2] = 0.37;
                        }
                    }
                });
                
                this.particleGeometry.attributes.color.needsUpdate = true;
                console.log(`Loaded ${txsToAssign.length} real TXIDs for initial particles`);
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
                        
                        const colors = this.particleGeometry.attributes.color.array;
                        if (feeRate > 50) {
                            colors[i * 3] = 0.94; colors[i * 3 + 1] = 0.27; colors[i * 3 + 2] = 0.27;
                        } else if (feeRate > 15) {
                            colors[i * 3] = 0.97; colors[i * 3 + 1] = 0.58; colors[i * 3 + 2] = 0.1;
                        } else {
                            colors[i * 3] = 0.13; colors[i * 3 + 1] = 0.77; colors[i * 3 + 2] = 0.37;
                        }
                    }
                }
            }
            
            this.particleGeometry.attributes.color.needsUpdate = true;
            
            const realCount = this.particles.filter(p => p.isReal).length;
            console.log(`Particles with real TXIDs: ${realCount}/${this.particles.length}`);
            
            // Dispatch event for external components (like Sovereign Health heartbeat) to sync
            window.dispatchEvent(new CustomEvent('visualizer-refresh', { detail: { realCount } }));
            
        } catch (error) {
            console.error('Failed to refresh particle TXIDs:', error);
        }
    }
    
    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.connectWebSocket();
        this.loadInitialTransactions();
        
        setInterval(() => this.refreshAllParticleTxids(), 3000);
        
        this.animate();
    }
    
    stop() {
        this.isRunning = false;
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('visualizer-container');
    if (container) {
        window.visualizer = new SovereignTerminal('visualizer-container');
        window.visualizer.start();
    }
});

/**
 * PHASE 4: Global PulseFX - High-Voltage Lightning Discharge System
 * Provides triggerZap() and triggerDischarge() methods for L2 visual effects
 */
window.PulseFX = {
    audioEngine: null,
    
    init: function() {
        if (window.visualizer && window.visualizer.pulseAudio) {
            this.audioEngine = window.visualizer.pulseAudio;
        }
    },
    
    triggerZap: function(element, zapAmount = 0) {
        if (!element) return;
        
        const isTier2 = zapAmount > 5000;
        
        element.classList.remove('pp-zap', 'pp-discharge', 'pp-discharge-active');
        void element.offsetWidth;
        
        if (isTier2) {
            element.classList.add('pp-discharge', 'pp-discharge-active');
            
            this.triggerSVGAnimation();
            
            setTimeout(() => {
                element.classList.remove('pp-discharge', 'pp-discharge-active');
            }, 250);
        } else {
            element.classList.add('pp-zap');
            setTimeout(() => element.classList.remove('pp-zap'), 300);
        }
        
        if (this.audioEngine && this.audioEngine.triggerSpatialZap) {
            this.audioEngine.triggerSpatialZap(isTier2);
        }
    },
    
    triggerSVGAnimation: function() {
        try {
            const dischargeFilter = document.getElementById('pp-discharge');
            if (dischargeFilter) {
                const animates = dischargeFilter.querySelectorAll('animate');
                animates.forEach(anim => {
                    if (anim.beginElement) anim.beginElement();
                });
            }
            
            const chromaticFilter = document.getElementById('pp-chromatic');
            if (chromaticFilter) {
                const animates = chromaticFilter.querySelectorAll('animate');
                animates.forEach(anim => {
                    if (anim.beginElement) anim.beginElement();
                });
            }
        } catch (e) {
            console.log('SVG animation trigger:', e);
        }
    },
    
    triggerDischarge: function(element) {
        if (!element) return;
        
        element.classList.remove('pp-discharge', 'pp-discharge-active');
        void element.offsetWidth;
        element.classList.add('pp-discharge', 'pp-discharge-active');
        
        this.triggerSVGAnimation();
        
        setTimeout(() => {
            element.classList.remove('pp-discharge', 'pp-discharge-active');
        }, 250);
        
        if (this.audioEngine && this.audioEngine.triggerSpatialZap) {
            this.audioEngine.triggerSpatialZap(true);
        }
    },
    
    onMajorEvent: function(event) {
        console.log('[PulseFX] Major event:', event);
        const terminalCards = document.querySelectorAll('.terminal-card, .intel-card, .lightning-pulse');
        terminalCards.forEach((card, i) => {
            setTimeout(() => this.triggerZap(card, event.zapAmount || 0), i * 50);
        });
    }
};

document.addEventListener('click', () => {
    if (!window.PulseFX.audioEngine) {
        window.PulseFX.init();
    }
}, { once: true });
