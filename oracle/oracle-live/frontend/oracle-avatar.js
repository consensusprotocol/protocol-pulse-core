/**
 * Protocol Pulse Oracle Avatar Runtime v2.0
 * State machine + barge-in + blinks + gaze drift + audio-reactive head motion
 * + viseme blending + procedural fallback renderer
 * No external dependencies.
 */

export class OracleAvatar {
  constructor(canvas, options = {}) {
    if (!canvas) throw new Error("Canvas element required");
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.width = options.width || 512;
    this.height = options.height || 512;
    this.canvas.width = this.width;
    this.canvas.height = this.height;
    this.assetsBase = options.assetsBase || "/static/avatar/visemes";
    this.useSprites = options.useSprites ?? false;
    this.state = "idle";
    this.currentViseme = 0;
    this.nextViseme = 0;
    this.visemeBlend = 0;
    this.visemeTimeline = [];
    this.audioSource = null;
    this.audioBuffer = null;
    this.audioStartTime = null;
    this.audioContext = null;
    this.analyser = null;
    this.freqData = null;
    this.head = {
      x: 0, y: 0, rot: 0,
      targetX: 0, targetY: 0, targetRot: 0,
      eyeX: 0, eyeY: 0, targetEyeX: 0, targetEyeY: 0,
      nextSaccadeAt: null,
    };
    this.blink = {
      phase: 0, inProgress: false, startedAt: 0, duration: 180,
      nextAt: performance.now() + this._randomBlinkInterval(),
    };
    this.sprites = {
      visemes: new Array(15).fill(null),
      blinkOpen: null, blinkHalf: null, blinkClosed: null, base: null,
    };
    this.raf = null;
    this.lastFrameAt = performance.now();
    this._initAudio();
    this.loadPromise = this.useSprites ? this._loadAssets() : Promise.resolve(true);
    this._loop();
  }

  _initAudio() {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    this.audioContext = new Ctx();
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.freqData = new Uint8Array(this.analyser.frequencyBinCount);
  }

  async _loadAssets() {
    const loadImg = (src) => new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    });
    const names = ["sil","pp","ff","th","dd","kk","ch","ss","nn","rr","aa","e","ih","oh","ou"];
    const [base, ...rest] = await Promise.all([
      loadImg(`${this.assetsBase}/base.png`),
      ...names.map((n, i) => loadImg(`${this.assetsBase}/viseme_${String(i).padStart(2,"0")}_${n}.png`)),
      loadImg(`${this.assetsBase}/blink_00_open.png`),
      loadImg(`${this.assetsBase}/blink_01_half.png`),
      loadImg(`${this.assetsBase}/blink_02_closed.png`),
    ]);
    this.sprites.base = base;
    this.sprites.visemes = rest.slice(0, 15);
    this.sprites.blinkOpen = rest[15];
    this.sprites.blinkHalf = rest[16];
    this.sprites.blinkClosed = rest[17];
    return true;
  }

  setState(next) { this.state = next; }
  startListening() { this.setState("listening"); }
  startThinking() { this.setState("thinking"); }

  interrupt() {
    if (this.audioSource) {
      try { this.audioSource.stop(); } catch (_) {}
    }
    this.audioSource = null;
    this.audioBuffer = null;
    this.audioStartTime = null;
    this.visemeTimeline = [];
    this.currentViseme = 0;
    this.nextViseme = 0;
    this.visemeBlend = 0;
    this.setState("interrupted");
    setTimeout(() => { if (this.state === "interrupted") this.setState("idle"); }, 220);
  }

  async speak(audioBase64, visemeTimeline) {
    await this.loadPromise;
    if (this.audioContext.state === "suspended") await this.audioContext.resume();
    const bytes = Uint8Array.from(atob(audioBase64), (c) => c.charCodeAt(0));
    const buffer = await this.audioContext.decodeAudioData(bytes.buffer.slice(0));
    this.visemeTimeline = visemeTimeline || [];
    this.audioBuffer = buffer;
    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.analyser);
    this.analyser.connect(this.audioContext.destination);
    this.audioSource = source;
    this.audioStartTime = this.audioContext.currentTime + 0.04;
    this.setState("speaking");
    source.start(this.audioStartTime);
    return new Promise((resolve) => {
      source.onended = () => {
        this.audioSource = null;
        this.audioBuffer = null;
        this.audioStartTime = null;
        this.visemeTimeline = [];
        this.currentViseme = 0;
        this.nextViseme = 0;
        this.visemeBlend = 0;
        this.setState("idle");
        resolve();
      };
    });
  }

  _randomBlinkInterval() { return 2600 + Math.random() * 2600; }

  _updateBlink(now) {
    if (!this.blink.inProgress && now >= this.blink.nextAt) {
      this.blink.inProgress = true;
      this.blink.startedAt = now;
      this.blink.duration = 165 + Math.random() * 55;
    }
    if (!this.blink.inProgress) { this.blink.phase = 0; return; }
    const t = (now - this.blink.startedAt) / this.blink.duration;
    if (t >= 1) {
      this.blink.phase = 0;
      this.blink.inProgress = false;
      this.blink.nextAt = now + this._randomBlinkInterval();
      return;
    }
    const x = t < 0.5 ? t / 0.5 : 1 - (t - 0.5) / 0.5;
    this.blink.phase = Math.sin(x * Math.PI * 0.5);
  }

  _updateGaze(now) {
    if (!this.head.nextSaccadeAt || now >= this.head.nextSaccadeAt) {
      this.head.targetEyeX = (Math.random() - 0.5) * 7;
      this.head.targetEyeY = (Math.random() - 0.5) * 4;
      this.head.nextSaccadeAt = now + 900 + Math.random() * 2200;
    }
    this.head.eyeX += (this.head.targetEyeX - this.head.eyeX) * 0.08;
    this.head.eyeY += (this.head.targetEyeY - this.head.eyeY) * 0.08;
  }

  _updateMotion(now) {
    const speaking = this.state === "speaking" && this.audioStartTime !== null;
    let low = 0, mid = 0;
    if (speaking) {
      this.analyser.getByteFrequencyData(this.freqData);
      low = _avg(this.freqData.slice(2, 12)) / 255;
      mid = _avg(this.freqData.slice(12, 36)) / 255;
    }
    let baseY = 0, baseRot = 0;
    const baseX = Math.sin(now / 1800) * 1.2;
    if (this.state === "listening") { baseY = -1.5; baseRot = -1.2; }
    else if (this.state === "thinking") { baseY = -1.0; baseRot = 1.0; }
    else if (this.state === "interrupted") { baseY = 1.5; baseRot = 0; }
    const speechY = speaking ? -mid * 4.0 : 0;
    const speechRot = speaking ? (low - 0.25) * 3.4 : 0;
    this.head.targetX = baseX;
    this.head.targetY = baseY + speechY + Math.cos(now / 2400) * 0.8;
    this.head.targetRot = baseRot + speechRot;
    this.head.x += (this.head.targetX - this.head.x) * 0.06;
    this.head.y += (this.head.targetY - this.head.y) * 0.08;
    this.head.rot += (this.head.targetRot - this.head.rot) * 0.07;
  }

  _updateViseme() {
    if (this.state !== "speaking" || !this.audioStartTime || !this.visemeTimeline.length) {
      this.currentViseme = 0; this.nextViseme = 0;
      this.visemeBlend += (0 - this.visemeBlend) * 0.25;
      return;
    }
    const elapsed = this.audioContext.currentTime - this.audioStartTime;
    let curr = this.visemeTimeline[0], next = null;
    for (let i = 0; i < this.visemeTimeline.length; i++) {
      const v = this.visemeTimeline[i];
      if (elapsed >= v.time && elapsed < v.time + v.duration) {
        curr = v; next = this.visemeTimeline[i + 1] || null; break;
      }
    }
    this.currentViseme = curr?.viseme ?? 0;
    this.nextViseme = next?.viseme ?? this.currentViseme;
    const progress = _clamp((elapsed - (curr?.time||0)) / Math.max(curr?.duration||0.001, 0.001), 0, 1);
    const blendStart = 0.58;
    const rawBlend = progress > blendStart ? (progress - blendStart) / (1 - blendStart) : 0;
    this.visemeBlend += (rawBlend - this.visemeBlend) * 0.22;
  }

  _loop = () => {
    const now = performance.now();
    this._updateBlink(now);
    this._updateGaze(now);
    this._updateMotion(now);
    this._updateViseme();
    this._render();
    this.raf = requestAnimationFrame(this._loop);
  };

  _render() {
    const ctx = this.ctx, w = this.width, h = this.height;
    ctx.clearRect(0, 0, w, h);
    const bg = ctx.createRadialGradient(w*0.35, h*0.3, 20, w*0.5, h*0.5, w*0.7);
    bg.addColorStop(0, "#1b2230");
    bg.addColorStop(1, "#0a0d12");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);
    ctx.save();
    ctx.translate(w/2 + this.head.x, h/2 + this.head.y);
    ctx.rotate((this.head.rot * Math.PI) / 180);
    ctx.translate(-w/2, -h/2);
    if (this.useSprites && this.sprites.base) {
      this._renderSprite(ctx, w, h);
    } else {
      this._renderProcedural(ctx, w, h);
    }
    ctx.restore();
    this._renderGlow(ctx, w, h);
    this._renderBadge(ctx, w, h);
  }

  _renderGlow(ctx, w, h) {
    const speaking = this.state === "speaking" && this.audioStartTime !== null;
    let amp = 0;
    if (speaking) {
      this.analyser.getByteFrequencyData(this.freqData);
      amp = _avg(this.freqData.slice(2, 30)) / 255;
    }
    const baseAlpha = { idle: 0.06, listening: 0.12, thinking: 0.16, speaking: 0.0, interrupted: 0.04 };
    const intensity = (baseAlpha[this.state] || 0.06) + amp * 0.28;
    const pulse = 1 + amp * 0.35;
    const glow = ctx.createRadialGradient(w/2, h/2, w*0.28*pulse, w/2, h/2, w*0.72);
    glow.addColorStop(0, `rgba(204,0,0,0)`);
    glow.addColorStop(0.55, `rgba(204,0,0,${intensity * 0.4})`);
    glow.addColorStop(1.0, `rgba(204,0,0,${intensity * 0.75})`);
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, h);
    if (amp > 0.65) {
      const accent = ctx.createRadialGradient(w/2, h*0.42, 0, w/2, h*0.42, w*0.22);
      accent.addColorStop(0, `rgba(247,147,26,${(amp-0.65)*0.5})`);
      accent.addColorStop(1, `rgba(247,147,26,0)`);
      ctx.fillStyle = accent;
      ctx.fillRect(0, 0, w, h);
    }
  }

  _renderBadge(ctx, w, h) {
    ctx.save();
    ctx.fillStyle = "rgba(0,0,0,0.32)";
    _roundRect(ctx, 14, 14, 126, 28, 12); ctx.fill();
    const colors = { idle:"#b8c2d9", listening:"#66d9ff", thinking:"#f4c46f", speaking:"#6cff9f", interrupted:"#ff8080" };
    ctx.fillStyle = colors[this.state] || "#fff";
    ctx.font = "700 11px Inter,sans-serif";
    ctx.fillText(this.state.toUpperCase(), 24, 33);
    ctx.restore();
  }

  _renderSprite(ctx, w, h) {
    if (this.sprites.base) ctx.drawImage(this.sprites.base, 0, 0, w, h);
    const cur = this.sprites.visemes[this.currentViseme];
    const nxt = this.sprites.visemes[this.nextViseme];
    if (cur) { ctx.globalAlpha = 1 - this.visemeBlend * 0.55; ctx.drawImage(cur, 0, 0, w, h); }
    if (nxt && nxt !== cur) { ctx.globalAlpha = this.visemeBlend * 0.55; ctx.drawImage(nxt, 0, 0, w, h); }
    ctx.globalAlpha = 1;
    const bf = this.blink.phase > 0.7 ? this.sprites.blinkClosed
             : this.blink.phase > 0.28 ? this.sprites.blinkHalf : null;
    if (bf) { ctx.globalAlpha = 0.85; ctx.drawImage(bf, 0, 0, w, h); ctx.globalAlpha = 1; }
  }

  _renderProcedural(ctx, w, h) {
    ctx.fillStyle = "#111722";
    _roundRect(ctx, w*0.22, h*0.65, w*0.56, h*0.28, 40); ctx.fill();
    ctx.fillStyle = "#6a7487";
    _roundRect(ctx, w*0.44, h*0.48, w*0.12, h*0.12, 16); ctx.fill();
    const hx = w*0.5, hy = h*0.32, hr = w*0.17;
    const skin = ctx.createRadialGradient(hx-22, hy-28, 10, hx, hy, hr+18);
    skin.addColorStop(0, "#bac7d9"); skin.addColorStop(1, "#7d899c");
    ctx.fillStyle = skin;
    ctx.beginPath(); ctx.ellipse(hx, hy, hr*0.9, hr*1.07, 0, 0, Math.PI*2); ctx.fill();
    ctx.fillStyle = "#1d2431";
    ctx.beginPath(); ctx.ellipse(hx, hy-hr*0.28, hr*0.94, hr*0.58, 0, Math.PI, 0, true);
    ctx.lineTo(hx+hr*0.94, hy-6); ctx.lineTo(hx-hr*0.94, hy-6); ctx.closePath(); ctx.fill();
    this._drawEye(ctx, hx-42, hy-6, this.blink.phase, this.head.eyeX, this.head.eyeY);
    this._drawEye(ctx, hx+42, hy-6, this.blink.phase, this.head.eyeX, this.head.eyeY);
    ctx.strokeStyle = "#202735"; ctx.lineWidth = 4; ctx.lineCap = "round";
    const bl = this.state === "thinking" ? -2 : this.state === "listening" ? 1 : 0;
    ctx.beginPath();
    ctx.moveTo(hx-62, hy-36+bl); ctx.lineTo(hx-22, hy-42+bl);
    ctx.moveTo(hx+22, hy-42+bl); ctx.lineTo(hx+62, hy-36+bl);
    ctx.stroke();
    ctx.strokeStyle = "rgba(70,80,98,0.6)"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(hx, hy-2); ctx.lineTo(hx-3, hy+28); ctx.lineTo(hx+6, hy+34); ctx.stroke();
    this._drawMouth(ctx, hx, hy+56);
  }

  _drawEye(ctx, cx, cy, blinkAmt, dx, dy) {
    const open = 1 - blinkAmt;
    ctx.fillStyle = "#eef3ff";
    ctx.beginPath(); ctx.ellipse(cx, cy, 24, Math.max(1.2, 9*open), 0, 0, Math.PI*2); ctx.fill();
    if (open > 0.08) {
      ctx.fillStyle = "#1c2431";
      ctx.beginPath(); ctx.arc(cx+dx*0.28, cy+dy*0.25, 5.4, 0, Math.PI*2); ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.arc(cx+dx*0.28-2, cy+dy*0.25-1.5, 1.6, 0, Math.PI*2); ctx.fill();
    }
  }

  _drawMouth(ctx, cx, cy) {
    const cur = _visemeParams(this.currentViseme);
    const nxt = _visemeParams(this.nextViseme);
    const b = this.visemeBlend;
    const open = _lerp(cur.open, nxt.open, b);
    const width = _lerp(cur.width, nxt.width, b);
    const round = _lerp(cur.round, nxt.round, b);
    const teeth = _lerp(cur.teeth, nxt.teeth, b);
    const mouthW = 54 + width*34, mouthH = 6 + open*38;
    const radius = 10 + round*18;
    ctx.fillStyle = "rgba(0,0,0,0.16)";
    ctx.beginPath(); ctx.ellipse(cx, cy+16, mouthW*0.56, 8, 0, 0, Math.PI*2); ctx.fill();
    ctx.fillStyle = "#5d3a44";
    _roundRect(ctx, cx-mouthW/2, cy-mouthH/2, mouthW, mouthH, radius); ctx.fill();
    ctx.fillStyle = "#1a1116";
    _roundRect(ctx, cx-mouthW*0.45, cy-mouthH*0.36, mouthW*0.9, mouthH*0.72, Math.max(4, radius-4)); ctx.fill();
    if (teeth > 0.08) {
      ctx.fillStyle = `rgba(238,243,255,${0.38+teeth*0.42})`;
      _roundRect(ctx, cx-mouthW*0.32, cy-mouthH*0.26, mouthW*0.64, Math.max(4, mouthH*0.18), 6); ctx.fill();
    }
    if (open > 0.18) {
      ctx.fillStyle = `rgba(164,67,86,${0.22+open*0.4})`;
      _roundRect(ctx, cx-mouthW*0.24, cy+mouthH*0.02, mouthW*0.48, mouthH*0.2, 8); ctx.fill();
    }
  }

  destroy() {
    if (this.raf) cancelAnimationFrame(this.raf);
    if (this.audioSource) { try { this.audioSource.stop(); } catch (_) {} }
    if (this.audioContext) this.audioContext.close();
  }
}

function _avg(arr) {
  if (!arr || !arr.length) return 0;
  let s = 0; for (let i = 0; i < arr.length; i++) s += arr[i];
  return s / arr.length;
}
function _clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
function _lerp(a, b, t) { return a + (b - a) * t; }
function _roundRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w/2, h/2);
  ctx.beginPath();
  ctx.moveTo(x+rr, y);
  ctx.arcTo(x+w, y, x+w, y+h, rr);
  ctx.arcTo(x+w, y+h, x, y+h, rr);
  ctx.arcTo(x, y+h, x, y, rr);
  ctx.arcTo(x, y, x+w, y, rr);
  ctx.closePath();
}
function _visemeParams(id) {
  const t = {
    0:  {open:0.02,width:0.2,round:0.15,teeth:0.0},
    1:  {open:0.01,width:0.08,round:0.12,teeth:0.0},
    2:  {open:0.12,width:0.26,round:0.14,teeth:0.7},
    3:  {open:0.22,width:0.22,round:0.2,teeth:0.5},
    4:  {open:0.18,width:0.28,round:0.12,teeth:0.45},
    5:  {open:0.18,width:0.18,round:0.3,teeth:0.1},
    6:  {open:0.26,width:0.22,round:0.48,teeth:0.15},
    7:  {open:0.14,width:0.24,round:0.08,teeth:0.5},
    8:  {open:0.12,width:0.22,round:0.1,teeth:0.05},
    9:  {open:0.2,width:0.18,round:0.42,teeth:0.05},
    10: {open:0.82,width:0.42,round:0.18,teeth:0.05},
    11: {open:0.46,width:0.36,round:0.08,teeth:0.38},
    12: {open:0.3,width:0.34,round:0.06,teeth:0.34},
    13: {open:0.34,width:0.22,round:0.58,teeth:0.05},
    14: {open:0.22,width:0.16,round:0.78,teeth:0.02},
  };
  return t[id] || t[0];
}
