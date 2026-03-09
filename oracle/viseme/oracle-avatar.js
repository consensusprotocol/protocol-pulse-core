/**
 * OracleAvatar — Canvas 2D viseme-driven avatar engine for Protocol Pulse.
 * Self-contained: includes inline SimplexNoise, Web Audio API sync, state machine.
 * No external dependencies.
 */

// ─── Inline SimplexNoise (2D) ───────────────────────────────────────
class SimplexNoise {
  constructor(seed) {
    this.grad3 = [
      [1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0],
      [1,0,1],[-1,0,1],[1,0,-1],[-1,0,-1],
      [0,1,1],[0,-1,1],[0,1,-1],[0,-1,-1]
    ];
    this.p = new Uint8Array(256);
    const s = seed || Math.random() * 65536;
    let v = s;
    for (let i = 0; i < 256; i++) {
      v = (v * 16807 + 0) % 2147483647;
      this.p[i] = v & 255;
    }
    this.perm = new Uint8Array(512);
    this.permMod12 = new Uint8Array(512);
    for (let i = 0; i < 512; i++) {
      this.perm[i] = this.p[i & 255];
      this.permMod12[i] = this.perm[i] % 12;
    }
  }

  noise2D(xin, yin) {
    const F2 = 0.5 * (Math.sqrt(3.0) - 1.0);
    const G2 = (3.0 - Math.sqrt(3.0)) / 6.0;
    const s = (xin + yin) * F2;
    const i = Math.floor(xin + s);
    const j = Math.floor(yin + s);
    const t = (i + j) * G2;
    const X0 = i - t;
    const Y0 = j - t;
    const x0 = xin - X0;
    const y0 = yin - Y0;
    let i1, j1;
    if (x0 > y0) { i1 = 1; j1 = 0; }
    else { i1 = 0; j1 = 1; }
    const x1 = x0 - i1 + G2;
    const y1 = y0 - j1 + G2;
    const x2 = x0 - 1.0 + 2.0 * G2;
    const y2 = y0 - 1.0 + 2.0 * G2;
    const ii = i & 255;
    const jj = j & 255;
    const dot = (g, x, y) => g[0] * x + g[1] * y;
    let n0 = 0, n1 = 0, n2 = 0;
    let t0 = 0.5 - x0 * x0 - y0 * y0;
    if (t0 >= 0) {
      t0 *= t0;
      n0 = t0 * t0 * dot(this.grad3[this.permMod12[ii + this.perm[jj]]], x0, y0);
    }
    let t1 = 0.5 - x1 * x1 - y1 * y1;
    if (t1 >= 0) {
      t1 *= t1;
      n1 = t1 * t1 * dot(this.grad3[this.permMod12[ii + i1 + this.perm[jj + j1]]], x1, y1);
    }
    let t2 = 0.5 - x2 * x2 - y2 * y2;
    if (t2 >= 0) {
      t2 *= t2;
      n2 = t2 * t2 * dot(this.grad3[this.permMod12[ii + 1 + this.perm[jj + 1]]], x2, y2);
    }
    return 70.0 * (n0 + n1 + n2);
  }
}

// ─── State Constants ────────────────────────────────────────────────
const STATES = {
  IDLE: 'IDLE',
  LISTENING: 'LISTENING',
  THINKING: 'THINKING',
  SPEAKING: 'SPEAKING',
  INTERRUPTED: 'INTERRUPTED',
};

const STATE_CONFIG = {
  IDLE:        { headTilt: 0.3, blinkRate: 3.5, saccadeRate: 3.0, glowIntensity: 0.15, expressionFrame: 17 },
  LISTENING:   { headTilt: 0.5, blinkRate: 4.0, saccadeRate: 2.0, glowIntensity: 0.25, expressionFrame: 0 },
  THINKING:    { headTilt: 0.8, blinkRate: 2.0, saccadeRate: 1.5, glowIntensity: 0.50, expressionFrame: 12 },
  SPEAKING:    { headTilt: 0.4, blinkRate: 3.0, saccadeRate: 4.0, glowIntensity: 0.60, expressionFrame: 10 },
  INTERRUPTED: { headTilt: 0.1, blinkRate: 5.0, saccadeRate: 5.0, glowIntensity: 0.10, expressionFrame: 0 },
};

// ─── OracleAvatar Class ─────────────────────────────────────────────
class OracleAvatar {
  constructor(canvasId, options = {}) {
    this.canvas = typeof canvasId === 'string'
      ? document.getElementById(canvasId)
      : canvasId;
    this.ctx = this.canvas.getContext('2d');
    this.width = this.canvas.width;
    this.height = this.canvas.height;

    // Options
    this.basePath = options.basePath || '/oracle/viseme/assets/frames/';
    this.apiUrl = options.apiUrl || '';

    // State
    this.state = STATES.IDLE;
    this.stateConfig = { ...STATE_CONFIG.IDLE };
    this.targetConfig = { ...STATE_CONFIG.IDLE };
    this.transitionSpeed = 0.05;

    // Assets
    this.visemeFrames = {};  // viseme_id -> Image
    this.blinkFrames = {};   // 'open', 'half', 'closed' -> Image
    this.baseFrame = null;
    this.assetsLoaded = false;

    // Audio
    this.audioCtx = null;
    this.audioSource = null;
    this.audioAnalyser = null;
    this.audioAmplitude = 0;
    this.audioPitch = 0;
    this.isPlaying = false;

    // Viseme timeline
    this.visemeTimeline = [];
    this.visemeIndex = 0;
    this.currentViseme = 0;
    this.audioStartTime = 0;

    // Perlin noise for head movement
    this.noise = new SimplexNoise(42);
    this.noiseTime = 0;

    // Blink engine
    this.blinkState = 0; // 0=open, 0.5=half, 1.0=closed
    this.nextBlinkTime = 0;
    this.blinkPhase = 'idle'; // 'idle', 'closing', 'closed', 'opening'
    this.blinkTimer = 0;
    this._scheduleNextBlink();

    // Saccade (micro eye movements)
    this.saccadeOffsetX = 0;
    this.saccadeOffsetY = 0;
    this.nextSaccadeTime = 0;
    this._scheduleNextSaccade();

    // Glow
    this.glowPhase = 0;

    // Animation
    this.animFrame = null;
    this.lastTime = 0;
    this.startTime = performance.now();
  }

  // ─── Asset Loading ──────────────────────────────────────────────
  async loadAssets(basePath) {
    if (basePath) this.basePath = basePath;
    const promises = [];

    // Load 18 viseme frames
    for (let i = 0; i <= 17; i++) {
      promises.push(this._loadImage(`${this.basePath}viseme_${i}.png`, `viseme_${i}`));
    }

    // Load blink frames
    for (const state of ['open', 'half', 'closed']) {
      promises.push(this._loadImage(`${this.basePath}blink_${state}.png`, `blink_${state}`));
    }

    // Load base frame
    promises.push(this._loadImage(`${this.basePath}base.png`, 'base'));

    try {
      await Promise.all(promises);
      this.assetsLoaded = true;
      console.log('[OracleAvatar] Assets loaded');
    } catch (e) {
      console.warn('[OracleAvatar] Some assets failed to load, using fallback rendering:', e.message);
      this.assetsLoaded = false;
    }
  }

  _loadImage(src, key) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        if (key.startsWith('viseme_')) {
          this.visemeFrames[parseInt(key.split('_')[1])] = img;
        } else if (key.startsWith('blink_')) {
          this.blinkFrames[key.split('_')[1]] = img;
        } else if (key === 'base') {
          this.baseFrame = img;
        }
        resolve(img);
      };
      img.onerror = () => reject(new Error(`Failed to load: ${src}`));
      img.src = src;
    });
  }

  // ─── State Machine ──────────────────────────────────────────────
  _transitionToState(newState) {
    if (this.state === newState) return;
    const prev = this.state;
    this.state = newState;
    this.targetConfig = { ...STATE_CONFIG[newState] };

    // Immediate actions for specific transitions
    if (newState === STATES.INTERRUPTED) {
      this.currentViseme = 0;  // Close mouth
    }

    console.log(`[OracleAvatar] ${prev} → ${newState}`);
  }

  _updateStateTransition(dt) {
    for (const key of Object.keys(this.stateConfig)) {
      const current = this.stateConfig[key];
      const target = this.targetConfig[key];
      if (typeof current === 'number' && typeof target === 'number') {
        this.stateConfig[key] += (target - current) * this.transitionSpeed;
      }
    }
  }

  // ─── Audio Playback + Viseme Sync ───────────────────────────────
  async speak(audioBase64, visemeTimeline) {
    // Stop any current playback
    this._stopAudio();

    if (!this.audioCtx) {
      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }

    // Decode audio
    const raw = atob(audioBase64);
    const buf = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);
    const audioBuffer = await this.audioCtx.decodeAudioData(buf.buffer);

    // Setup analyser
    this.audioAnalyser = this.audioCtx.createAnalyser();
    this.audioAnalyser.fftSize = 256;

    // Create source
    this.audioSource = this.audioCtx.createBufferSource();
    this.audioSource.buffer = audioBuffer;
    this.audioSource.connect(this.audioAnalyser);
    this.audioAnalyser.connect(this.audioCtx.destination);

    // Set timeline
    this.visemeTimeline = visemeTimeline || [];
    this.visemeIndex = 0;

    // Start playback
    this.audioStartTime = this.audioCtx.currentTime;
    this.audioSource.start(0);
    this.isPlaying = true;
    this._transitionToState(STATES.SPEAKING);

    this.audioSource.onended = () => {
      this.isPlaying = false;
      this.currentViseme = 0;
      this._transitionToState(STATES.IDLE);
    };
  }

  interrupt() {
    this._stopAudio();
    this.currentViseme = 0;
    this._transitionToState(STATES.INTERRUPTED);
    setTimeout(() => {
      if (this.state === STATES.INTERRUPTED) {
        this._transitionToState(STATES.IDLE);
      }
    }, 1500);
  }

  thinking() {
    this._transitionToState(STATES.THINKING);
  }

  _stopAudio() {
    if (this.audioSource) {
      try { this.audioSource.stop(); } catch (e) {}
      this.audioSource = null;
    }
    this.isPlaying = false;
    this.visemeTimeline = [];
    this.visemeIndex = 0;
  }

  _updateAudio() {
    if (!this.audioAnalyser || !this.isPlaying) {
      this.audioAmplitude *= 0.9;  // Decay
      this.audioPitch = 0;
      return;
    }

    const data = new Uint8Array(this.audioAnalyser.frequencyBinCount);
    this.audioAnalyser.getByteFrequencyData(data);

    // Amplitude: average of all bins
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i];
    this.audioAmplitude = sum / (data.length * 255);

    // Pitch: weighted centroid of frequency bins
    let weightedSum = 0, totalWeight = 0;
    for (let i = 0; i < data.length; i++) {
      weightedSum += i * data[i];
      totalWeight += data[i];
    }
    this.audioPitch = totalWeight > 0 ? weightedSum / totalWeight / data.length : 0;

    // Viseme sync via Web Audio API clock
    if (this.visemeTimeline.length > 0) {
      const elapsed = this.audioCtx.currentTime - this.audioStartTime;
      while (
        this.visemeIndex < this.visemeTimeline.length - 1 &&
        this.visemeTimeline[this.visemeIndex + 1].time <= elapsed
      ) {
        this.visemeIndex++;
      }
      this.currentViseme = this.visemeTimeline[this.visemeIndex].viseme;
    }
  }

  // ─── Head Movement (Perlin Noise) ──────────────────────────────
  _getHeadTransform(dt) {
    this.noiseTime += dt;
    const t = this.noiseTime;
    const tilt = this.stateConfig.headTilt;

    // Perlin noise-based drift (NOT sine)
    const rotZ = this.noise.noise2D(t * 0.3, 0) * tilt * 2.5;
    const tx = this.noise.noise2D(t * 0.25, 10) * tilt * 4.0;
    let ty = this.noise.noise2D(t * 0.2, 20) * tilt * 2.0;

    // Audio amplitude drives Y translation (head bob)
    ty += this.audioAmplitude * 3.0;

    // Audio pitch drives rotation-X (nodding)
    const rotX = this.audioPitch * 2.0;

    return { rotZ, rotX, tx, ty };
  }

  // ─── Eye Saccades ──────────────────────────────────────────────
  _scheduleNextSaccade() {
    const rate = this.stateConfig.saccadeRate || 3.0;
    this.nextSaccadeTime = performance.now() + (rate + Math.random() * rate) * 500;
  }

  _updateSaccades(now) {
    if (now >= this.nextSaccadeTime) {
      // Tiny instant iris jump
      this.saccadeOffsetX = (Math.random() - 0.5) * 2.0;
      this.saccadeOffsetY = (Math.random() - 0.5) * 1.5;
      this._scheduleNextSaccade();
    }
  }

  // ─── Blink Engine ──────────────────────────────────────────────
  _scheduleNextBlink() {
    const rate = this.stateConfig.blinkRate || 3.5;
    this.nextBlinkTime = performance.now() + (rate + Math.random() * rate * 0.5) * 1000;
  }

  _updateBlink(now, dt) {
    const CLOSE_SPEED = 12.0;
    const OPEN_SPEED = 6.0;
    const CLOSED_HOLD = 0.04; // seconds

    switch (this.blinkPhase) {
      case 'idle':
        if (now >= this.nextBlinkTime) {
          this.blinkPhase = 'closing';
        }
        break;
      case 'closing':
        this.blinkState = Math.min(1.0, this.blinkState + dt * CLOSE_SPEED);
        if (this.blinkState >= 1.0) {
          this.blinkPhase = 'closed';
          this.blinkTimer = 0;
        }
        break;
      case 'closed':
        this.blinkTimer += dt;
        if (this.blinkTimer >= CLOSED_HOLD) {
          this.blinkPhase = 'opening';
        }
        break;
      case 'opening':
        this.blinkState = Math.max(0.0, this.blinkState - dt * OPEN_SPEED);
        if (this.blinkState <= 0.0) {
          this.blinkPhase = 'idle';
          this._scheduleNextBlink();
        }
        break;
    }
  }

  // ─── Dynamic Glow ──────────────────────────────────────────────
  _drawGlow(ctx) {
    this.glowPhase += 0.02;
    const intensity = this.stateConfig.glowIntensity;
    const pulse = 0.5 + 0.5 * Math.sin(this.glowPhase);
    const alpha = intensity * (0.6 + 0.4 * pulse);

    // Base red glow
    const cx = this.width / 2;
    const cy = this.height * 0.45;
    const r = this.width * 0.6;

    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    grad.addColorStop(0, `rgba(204, 0, 0, ${alpha * 0.3})`);
    grad.addColorStop(0.5, `rgba(204, 0, 0, ${alpha * 0.1})`);
    grad.addColorStop(1, 'rgba(204, 0, 0, 0)');

    ctx.globalCompositeOperation = 'screen';
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, this.width, this.height);

    // Gold accent on audio peaks
    if (this.audioAmplitude > 0.3) {
      const peakAlpha = (this.audioAmplitude - 0.3) * 1.5;
      const goldGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 0.4);
      goldGrad.addColorStop(0, `rgba(247, 147, 26, ${peakAlpha * 0.4})`);
      goldGrad.addColorStop(1, 'rgba(247, 147, 26, 0)');
      ctx.fillStyle = goldGrad;
      ctx.fillRect(0, 0, this.width, this.height);
    }

    ctx.globalCompositeOperation = 'source-over';
  }

  // ─── Render Loop ───────────────────────────────────────────────
  _render(timestamp) {
    const dt = Math.min((timestamp - this.lastTime) / 1000, 0.1);
    this.lastTime = timestamp;

    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    // Update systems
    this._updateStateTransition(dt);
    this._updateAudio();
    this._updateBlink(timestamp, dt);
    this._updateSaccades(timestamp);

    // Get head transform
    const head = this._getHeadTransform(dt);

    // Clear
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, w, h);

    // Apply head transforms
    ctx.save();
    ctx.translate(w / 2 + head.tx, h / 2 + head.ty);
    ctx.rotate(head.rotZ * Math.PI / 180);
    ctx.translate(-w / 2, -h / 2);

    // Layer 1: Base frame
    if (this.baseFrame) {
      ctx.drawImage(this.baseFrame, 0, 0, w, h);
    } else {
      // Fallback: dark placeholder
      ctx.fillStyle = '#0a0a0a';
      ctx.fillRect(0, 0, w, h);
      this._drawFallbackFace(ctx, w, h);
    }

    // Layer 2: Viseme overlay
    if (this.assetsLoaded && this.visemeFrames[this.currentViseme]) {
      ctx.drawImage(this.visemeFrames[this.currentViseme], 0, 0, w, h);
    } else if (this.currentViseme > 0) {
      this._drawFallbackMouth(ctx, w, h, this.currentViseme);
    }

    // Layer 3: Blink overlay
    if (this.blinkState > 0.01) {
      if (this.assetsLoaded) {
        const blinkKey = this.blinkState > 0.7 ? 'closed' : (this.blinkState > 0.3 ? 'half' : 'open');
        if (this.blinkFrames[blinkKey]) {
          ctx.globalAlpha = Math.min(1.0, this.blinkState * 1.2);
          ctx.drawImage(this.blinkFrames[blinkKey], 0, 0, w, h);
          ctx.globalAlpha = 1.0;
        }
      } else {
        this._drawFallbackBlink(ctx, w, h, this.blinkState);
      }
    }

    ctx.restore();

    // Layer 4: Glow (not transformed with head)
    this._drawGlow(ctx);

    this.animFrame = requestAnimationFrame((t) => this._render(t));
  }

  // ─── Fallback Rendering (no assets loaded) ─────────────────────
  _drawFallbackFace(ctx, w, h) {
    // Simple circle face
    const cx = w / 2, cy = h * 0.42, r = w * 0.28;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = '#1a1a1a';
    ctx.fill();
    ctx.strokeStyle = '#cc0000';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Eyes with saccade offset
    const eyeY = cy - r * 0.15;
    for (const ex of [cx - r * 0.3 + this.saccadeOffsetX, cx + r * 0.3 + this.saccadeOffsetX]) {
      ctx.beginPath();
      ctx.arc(ex, eyeY + this.saccadeOffsetY, r * 0.06, 0, Math.PI * 2);
      ctx.fillStyle = '#cc0000';
      ctx.fill();
    }
  }

  _drawFallbackMouth(ctx, w, h, viseme) {
    const cx = w / 2, cy = h * 0.42 + w * 0.28 * 0.25;
    const maxW = w * 0.12, maxH = w * 0.08;

    // Viseme shapes by category
    let mw, mh;
    if (viseme <= 1) { mw = maxW * 0.3; mh = maxH * 0.2; }        // Closed/bilabial
    else if (viseme <= 3) { mw = maxW * 0.5; mh = maxH * 0.3; }    // Dental
    else if (viseme <= 7) { mw = maxW * 0.6; mh = maxH * 0.4; }    // Consonants
    else if (viseme <= 9) { mw = maxW * 0.5; mh = maxH * 0.5; }    // Rhotics
    else if (viseme <= 11) { mw = maxW * 0.9; mh = maxH * 0.8; }   // Open vowels
    else if (viseme <= 12) { mw = maxW * 0.7; mh = maxH * 0.5; }   // High front
    else if (viseme <= 14) { mw = maxW * 0.6; mh = maxH * 0.7; }   // Rounded
    else { mw = maxW * 0.8; mh = maxH * 0.6; }                     // Others

    ctx.beginPath();
    ctx.ellipse(cx, cy, mw, mh, 0, 0, Math.PI * 2);
    ctx.fillStyle = '#330000';
    ctx.fill();
    ctx.strokeStyle = '#cc0000';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  _drawFallbackBlink(ctx, w, h, intensity) {
    const cx = w / 2, cy = h * 0.42, r = w * 0.28;
    const eyeY = cy - r * 0.15;

    ctx.fillStyle = '#1a1a1a';
    for (const ex of [cx - r * 0.3, cx + r * 0.3]) {
      const lidH = r * 0.12 * intensity;
      ctx.fillRect(ex - r * 0.1, eyeY - r * 0.06, r * 0.2, lidH);
    }
  }

  // ─── Public API ────────────────────────────────────────────────
  start() {
    this.lastTime = performance.now();
    this._render(this.lastTime);
  }

  stop() {
    if (this.animFrame) {
      cancelAnimationFrame(this.animFrame);
      this.animFrame = null;
    }
    this._stopAudio();
  }

  destroy() {
    this.stop();
    if (this.audioCtx) {
      this.audioCtx.close();
      this.audioCtx = null;
    }
  }

  getState() {
    return {
      state: this.state,
      viseme: this.currentViseme,
      amplitude: this.audioAmplitude,
      blinkState: this.blinkState,
      isPlaying: this.isPlaying,
    };
  }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { OracleAvatar, STATES };
}
