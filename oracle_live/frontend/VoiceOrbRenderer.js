
/**
 * VoiceOrbRenderer — Protocol Pulse HER-mode
 * Signal instrument: inner core + radial waveform + outer halo
 * No assets. Pure canvas math. Runs on anything.
 * States: idle | listening | thinking | speaking | interrupted
 */

export class VoiceOrbRenderer {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.w = options.width  || 512;
    this.h = options.height || 512;
    this.canvas.width  = this.w;
    this.canvas.height = this.h;
    this.cx = this.w / 2;
    this.cy = this.h / 2;

    this.state      = "idle";
    this.amplitude  = 0;
    this.freqData   = null;
    this.analyser   = null;
    this.audioCtx   = null;

    this._t          = 0;
    this._phase      = 0;
    this._targetAmp  = 0;
    this._smoothAmp  = 0;
    this._haloPhase  = 0;
    this._thinkPhase = 0;
    this._interruptT = 0;
    this._visionActive = false;

    this._raf = null;
    this._lastNow = performance.now();
    this._loop();
  }

  // ── Public API ────────────────────────────────────────────────────────────

  setState(s) { this.state = s; }
  setVisionActive(v) { this._visionActive = v; }

  connectAudio(audioContext, analyserNode) {
    this.audioCtx  = audioContext;
    this.analyser  = analyserNode;
    this.freqData  = new Uint8Array(analyserNode.frequencyBinCount);
  }

  triggerInterrupt() {
    this._interruptT = 1.0;  // Ripple decays from 1→0
    this.setState("interrupted");
    setTimeout(() => { if (this.state === "interrupted") this.setState("idle"); }, 250);
  }

  destroy() {
    if (this._raf) cancelAnimationFrame(this._raf);
  }

  // ── Loop ─────────────────────────────────────────────────────────────────

  _loop = () => {
    const now = performance.now();
    const dt  = Math.min((now - this._lastNow) / 1000, 0.05);
    this._lastNow = now;
    this._t += dt;

    this._updateAudio();
    this._render(dt);
    this._raf = requestAnimationFrame(this._loop);
  };

  _updateAudio() {
    if (this.analyser && this.freqData && this.state === "speaking") {
      this.analyser.getByteFrequencyData(this.freqData);
      const low  = _avg(this.freqData.slice(2,  12)) / 255;
      const mid  = _avg(this.freqData.slice(12, 40)) / 255;
      this._targetAmp = low * 0.55 + mid * 0.45;
    } else {
      this._targetAmp = 0;
    }
    this._smoothAmp += (this._targetAmp - this._smoothAmp) * 0.18;
    this._interruptT = Math.max(0, this._interruptT - 0.04);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  _render(dt) {
    const ctx = this.ctx;
    const t   = this._t;
    const amp = this._smoothAmp;
    const cx  = this.cx, cy = this.cy;

    ctx.clearRect(0, 0, this.w, this.h);

    // Deep background
    const bg = ctx.createRadialGradient(cx, cy, 0, cx, cy, this.w * 0.6);
    bg.addColorStop(0, "#0d1220");
    bg.addColorStop(1, "#07090f");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, this.w, this.h);

    // ── Layer 1: Outer halo (reasoning / thinking pressure) ───────────────
    this._renderOuterHalo(ctx, cx, cy, t, amp);

    // ── Layer 2: Radial waveform (speech energy) ───────────────────────────
    if (this.state === "speaking") {
      this._renderRadialWaveform(ctx, cx, cy, amp);
    }

    // ── Layer 3: Inner core (presence / state) ────────────────────────────
    this._renderInnerCore(ctx, cx, cy, t, amp);

    // ── Layer 4: Vision accent ────────────────────────────────────────────
    if (this._visionActive) {
      this._renderVisionAccent(ctx, cx, cy, t);
    }

    // ── Layer 5: Interrupt ripple ─────────────────────────────────────────
    if (this._interruptT > 0) {
      this._renderInterruptRipple(ctx, cx, cy, this._interruptT);
    }

    // ── Label ──────────────────────────────────────────────────────────────
    this._renderLabel(ctx);
  }

  _renderOuterHalo(ctx, cx, cy, t, amp) {
    const STATE_HALO = {
      idle:        { r: 0.38, opacity: 0.06, color: [204,   0,   0], speed: 0.5  },
      listening:   { r: 0.40, opacity: 0.14, color: [  0, 180, 255], speed: 0.9  },
      thinking:    { r: 0.36, opacity: 0.18, color: [204,   0,   0], speed: 0.3  },
      speaking:    { r: 0.42, opacity: 0.10, color: [204,   0,   0], speed: 1.2  },
      broadcast:   { r: 0.44, opacity: 0.22, color: [247, 147,  26], speed: 1.5  },
      interrupted: { r: 0.34, opacity: 0.05, color: [204,   0,   0], speed: 0.2  },
    };
    const cfg = STATE_HALO[this.state] || STATE_HALO.idle;
    const baseR = this.w * cfg.r;
    const pulse = 1 + Math.sin(t * cfg.speed * Math.PI * 2) * 0.04;

    // Thinking: slow compression inward
    const thinkOffset = this.state === "thinking"
      ? Math.sin(t * 0.6) * this.w * 0.03
      : 0;

    const g = ctx.createRadialGradient(cx, cy, baseR * 0.7 + thinkOffset, cx, cy, baseR * pulse);
    const [r, gr, b] = cfg.color;
    g.addColorStop(0, `rgba(${r},${gr},${b},0)`);
    g.addColorStop(0.6, `rgba(${r},${gr},${b},${cfg.opacity * 0.4})`);
    g.addColorStop(1.0, `rgba(${r},${gr},${b},${cfg.opacity})`);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(cx, cy, baseR * pulse * 1.15, 0, Math.PI * 2);
    ctx.fill();
  }

  _renderRadialWaveform(ctx, cx, cy, amp) {
    if (!this.freqData) return;
    const baseR   = this.w * 0.22;
    const POINTS  = 128;
    const maxWave = this.w * 0.10 * (0.3 + amp * 0.7);

    ctx.save();
    ctx.strokeStyle = `rgba(204,0,0,${0.4 + amp * 0.4})`;
    ctx.lineWidth   = 1.5 + amp * 1.5;
    ctx.shadowBlur  = 8;
    ctx.shadowColor = "rgba(204,0,0,0.6)";
    ctx.beginPath();

    for (let i = 0; i <= POINTS; i++) {
      const angle   = (i / POINTS) * Math.PI * 2;
      const binIdx  = Math.floor((i / POINTS) * (this.freqData.length * 0.6));
      const freq    = (this.freqData[binIdx] || 0) / 255;
      const r       = baseR + freq * maxWave;
      const x       = cx + Math.cos(angle) * r;
      const y       = cy + Math.sin(angle) * r;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }

    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  }

  _renderInnerCore(ctx, cx, cy, t, amp) {
    const STATE_CORE = {
      idle:        { r: 0.13, color: [204,  0,  0], glow: 0.18, pulse: 0.9  },
      listening:   { r: 0.15, color: [  0,160,240], glow: 0.35, pulse: 1.4  },
      thinking:    { r: 0.11, color: [204,  0,  0], glow: 0.28, pulse: 0.4  },
      speaking:    { r: 0.14, color: [204,  0,  0], glow: 0.55, pulse: 2.2  },
      broadcast:   { r: 0.16, color: [247,147, 26], glow: 0.70, pulse: 2.8  },
      interrupted: { r: 0.10, color: [204,  0,  0], glow: 0.08, pulse: 0.3  },
    };
    const cfg   = STATE_CORE[this.state] || STATE_CORE.idle;
    const pulse = 1 + Math.sin(t * cfg.pulse * Math.PI * 2) * 0.06 + amp * 0.12;
    const baseR = this.w * cfg.r * pulse;
    const [r, gr, b] = cfg.color;

    // Core gradient
    const g = ctx.createRadialGradient(cx - baseR * 0.2, cy - baseR * 0.2, 0, cx, cy, baseR);
    g.addColorStop(0,   `rgba(${Math.min(255, r+60)},${Math.min(255,gr+40)},${Math.min(255,b+40)},0.9)`);
    g.addColorStop(0.5, `rgba(${r},${gr},${b},0.75)`);
    g.addColorStop(1,   `rgba(${r},${gr},${b},0)`);

    ctx.save();
    ctx.shadowBlur  = 24 + amp * 20;
    ctx.shadowColor = `rgba(${r},${gr},${b},0.7)`;
    ctx.fillStyle   = g;
    ctx.beginPath();
    ctx.arc(cx, cy, baseR, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Thinking: add slow rotating inner ring
    if (this.state === "thinking") {
      this._thinkPhase += 0.008;
      ctx.save();
      ctx.strokeStyle = `rgba(204,0,0,0.25)`;
      ctx.lineWidth   = 1;
      ctx.setLineDash([4, 8]);
      ctx.lineDashOffset = -this._thinkPhase * 40;
      ctx.beginPath();
      ctx.arc(cx, cy, baseR * 1.35, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }
  }

  _renderVisionAccent(ctx, cx, cy, t) {
    // Subtle cyan ring indicating Gemini vision is active
    const pulse = 0.5 + Math.sin(t * 1.8 * Math.PI * 2) * 0.5;
    ctx.save();
    ctx.strokeStyle = `rgba(0,220,255,${0.15 + pulse * 0.12})`;
    ctx.lineWidth   = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, this.w * 0.19, 0, Math.PI * 2);
    ctx.stroke();

    // Small "eye" icon at top
    const ey = cy - this.w * 0.195;
    ctx.fillStyle = `rgba(0,220,255,${0.4 + pulse * 0.3})`;
    ctx.beginPath();
    ctx.ellipse(cx, ey, 5, 3, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  _renderInterruptRipple(ctx, cx, cy, strength) {
    const r = this.w * 0.18 + (1 - strength) * this.w * 0.22;
    ctx.save();
    ctx.strokeStyle = `rgba(204,0,0,${strength * 0.6})`;
    ctx.lineWidth   = strength * 3;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  _renderLabel(ctx) {
    const labels = {
      idle:        { text: "ORACLE",    color: "#8899bb" },
      listening:   { text: "LISTENING", color: "#66d9ff" },
      thinking:    { text: "THINKING",  color: "#f2c36f" },
      speaking:    { text: "SPEAKING",  color: "#7dffb3" },
      broadcast:   { text: "ON AIR",    color: "#f7931a" },
      interrupted: { text: "STANDBY",   color: "#ff8888" },
    };
    const cfg = labels[this.state] || labels.idle;
    ctx.save();
    ctx.fillStyle = cfg.color;
    ctx.font      = "700 13px Inter, monospace";
    ctx.textAlign = "center";
    ctx.letterSpacing = "0.15em";
    ctx.fillText(cfg.text, this.w / 2, this.h * 0.78);
    ctx.restore();
  }
}

function _avg(arr) {
  if (!arr || !arr.length) return 0;
  let s = 0;
  for (let i = 0; i < arr.length; i++) s += arr[i];
  return s / arr.length;
}
