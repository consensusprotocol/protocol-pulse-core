/**
 * Protocol Pulse Oracle Avatar Runtime v2.1
 * State machine: idle | listening | thinking | speaking | broadcast | interrupted
 * Features: viseme blending, blinks, gaze drift, audio-reactive head motion,
 *           procedural mouth fallback, sprite overlay support
 * All behavioral values driven by LIVE_CONFIG (tuning panel) + STATE_CONFIG.
 */
import { LIVE_CONFIG } from "./OracleTuningPanel.js";
import { STATE_CONFIG, BROW_PARAMS, getSpeechEmphasis, getBlinkImperfection } from "./behavior.js";

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
    this.head = { x:0, y:0, rot:0, targetX:0, targetY:0, targetRot:0,
                  eyeX:0, eyeY:0, targetEyeX:0, targetEyeY:0, nextSaccadeAt:0 };
    this.blink = { phase:0, inProgress:false,
                   nextAt: performance.now() + this._blinkInterval() };
    this.rightEyeBlink = { phase:0, inProgress:false, startedAt:0, duration:0 };
    this.sprites = { visemes: new Array(15).fill(null),
                     blinkOpen:null, blinkHalf:null, blinkClosed:null, base:null };
    // Imperfection state
    this._imperfection = getBlinkImperfection();
    this._gazeOvershoot = { active:false, targetX:0, targetY:0 };
    // Speech emphasis state
    this._emphasis = { browLift:0, jawAmplitude:1, glowBoost:0, headAccent:0 };
    this._amplitude = 0;
    this.raf = null;
    this.initAudio();
    this.loadPromise = this.useSprites ? this.loadAssets() : Promise.resolve(true);
    this.loop();
  }

  initAudio() {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    this.audioContext = new Ctx();
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.freqData = new Uint8Array(this.analyser.frequencyBinCount);
  }

  async loadAssets() {
    const loadImg = src => new Promise(resolve => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    });
    const names = ["sil","pp","ff","th","dd","kk","ch","ss","nn","rr","aa","e","ih","oh","ou"];
    const [base, ...rest] = await Promise.all([
      loadImg(`${this.assetsBase}/base.png`),
      ...names.map((n,i) => loadImg(`${this.assetsBase}/viseme_${String(i).padStart(2,"0")}_${n}.png`)),
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
    if (this.audioSource) { try { this.audioSource.stop(); } catch(_){} }
    this.audioSource = null; this.audioBuffer = null;
    this.audioStartTime = null; this.visemeTimeline = [];
    this.currentViseme = 0; this.nextViseme = 0; this.visemeBlend = 0;
    this.setState("interrupted");
    setTimeout(() => { if (this.state === "interrupted") this.setState("idle"); }, 220);
  }

  async speak(audioBase64, visemeTimeline) {
    await this.loadPromise;
    if (this.audioContext.state === "suspended") await this.audioContext.resume();
    const bytes = Uint8Array.from(atob(audioBase64), c => c.charCodeAt(0));
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
    return new Promise(resolve => {
      source.onended = () => {
        this.audioSource = null; this.audioBuffer = null;
        this.audioStartTime = null; this.visemeTimeline = [];
        this.currentViseme = 0; this.nextViseme = 0; this.visemeBlend = 0;
        this.setState("idle"); resolve();
      };
    });
  }

  _stateConfig() { return STATE_CONFIG[this.state] || STATE_CONFIG.idle; }

  _blinkInterval() {
    const cfg = this._stateConfig();
    const [min, max] = cfg.blinkIntervalMs;
    return min + Math.random() * (max - min);
  }

  _updateBlink(now) {
    // Left eye (primary) blink
    if (!this.blink.inProgress && now >= this.blink.nextAt) {
      this.blink.inProgress = true;
      this.blink.startedAt = now;
      const cfg = this._stateConfig();
      const [dMin, dMax] = cfg.blinkDurationMs;
      this.blink.duration = dMin + Math.random() * (dMax - dMin);

      // Get new imperfection set for this blink cycle
      this._imperfection = getBlinkImperfection();

      // Right-eye asymmetric lag
      const hasLag = Math.random() < LIVE_CONFIG.blinkAsymmetryChance;
      const lagMs = hasLag ? (Math.random() * LIVE_CONFIG.blinkAsymmetryMax) : 0;
      this.rightEyeBlink.inProgress = false;
      this.rightEyeBlink.delayUntil = now + lagMs;
      this.rightEyeBlink.duration = this.blink.duration;

      // Override with imperfection right-eye delay if present
      if (this._imperfection.rightEyeDelayMs > 0) {
        this.rightEyeBlink.delayUntil = now + this._imperfection.rightEyeDelayMs;
      }
    }

    // Left eye phase
    if (!this.blink.inProgress) {
      this.blink.phase = 0;
    } else {
      const t = (now - this.blink.startedAt) / this.blink.duration;
      if (t >= 1) {
        this.blink.phase = 0;
        this.blink.inProgress = false;
        let nextInterval = this._blinkInterval();
        // Cluster blink
        if (Math.random() < LIVE_CONFIG.blinkClusterChance) {
          nextInterval = LIVE_CONFIG.blinkClusterOffsetMs;
        }
        // Apply imperfection offset
        nextInterval += this._imperfection.nextBlinkOffset;
        this.blink.nextAt = now + nextInterval;
      } else {
        const x = t < 0.5 ? t / 0.5 : 1 - (t - 0.5) / 0.5;
        this.blink.phase = Math.sin(x * Math.PI * 0.5);
      }
    }

    // Right eye phase (may lag behind left)
    if (now >= (this.rightEyeBlink.delayUntil || 0) && this.blink.inProgress && !this.rightEyeBlink.inProgress) {
      this.rightEyeBlink.inProgress = true;
      this.rightEyeBlink.startedAt = now;
    }
    if (!this.rightEyeBlink.inProgress) {
      this.rightEyeBlink.phase = 0;
    } else {
      const t = (now - this.rightEyeBlink.startedAt) / this.rightEyeBlink.duration;
      if (t >= 1) {
        this.rightEyeBlink.phase = 0;
        this.rightEyeBlink.inProgress = false;
      } else {
        const x = t < 0.5 ? t / 0.5 : 1 - (t - 0.5) / 0.5;
        this.rightEyeBlink.phase = Math.sin(x * Math.PI * 0.5);
      }
    }
  }

  _updateGaze(now) {
    const cfg = this._stateConfig();
    const [maxX, maxY] = cfg.gazeMaxOffsetPx;
    const [sMin, sMax] = cfg.saccadeIntervalMs;

    // Broadcast during speech: no saccades
    if (this.state === "broadcast" && LIVE_CONFIG.broadcastPostureTight && this._amplitude > 0.05) {
      // No new saccades during active broadcast speech
    } else if (!this.head.nextSaccadeAt || now >= this.head.nextSaccadeAt) {
      // Skip saccade if interval is [0,0] (speaking state)
      if (sMin === 0 && sMax === 0) {
        this.head.nextSaccadeAt = now + 100;
      } else {
        let tx = (Math.random() - 0.5) * maxX * 2;
        let ty = (Math.random() - 0.5) * maxY * 2;

        // Broadcast: cap gaze drift to 1px max
        if (this.state === "broadcast" && LIVE_CONFIG.broadcastPostureTight) {
          tx = _clamp(tx, -1, 1);
          ty = _clamp(ty, -1, 1);
        }

        // Gaze overshoot from imperfection
        if (this._imperfection.gazeOvershoots) {
          const overshootChance = LIVE_CONFIG.gazeOvershootChance;
          if (Math.random() < overshootChance) {
            const amt = LIVE_CONFIG.gazeOvershootAmtPx;
            const dir = Math.sign(tx) || 1;
            this._gazeOvershoot.active = true;
            this._gazeOvershoot.targetX = tx + dir * amt;
            this._gazeOvershoot.targetY = ty;
            this.head.targetEyeX = this._gazeOvershoot.targetX;
            this.head.targetEyeY = this._gazeOvershoot.targetY;
            // Will lerp back to real target below
            this.head.nextSaccadeAt = now + sMin + Math.random() * (sMax - sMin);
            return;
          }
        }

        this.head.targetEyeX = tx;
        this.head.targetEyeY = ty;
        this._gazeOvershoot.active = false;
        this.head.nextSaccadeAt = now + sMin + Math.random() * (sMax - sMin);
      }
    }

    const returnSpeed = LIVE_CONFIG.saccadeReturnSpeed;

    // If overshooting, lerp back to real target
    if (this._gazeOvershoot.active) {
      const dx = Math.abs(this.head.eyeX - this._gazeOvershoot.targetX);
      if (dx < 0.5) {
        // Close enough to overshoot target, now return to real target
        this._gazeOvershoot.active = false;
        this.head.targetEyeX = (Math.random() - 0.5) * maxX * 2;
        this.head.targetEyeY = (Math.random() - 0.5) * maxY * 2;
      }
    }

    this.head.eyeX += (this.head.targetEyeX - this.head.eyeX) * returnSpeed;
    this.head.eyeY += (this.head.targetEyeY - this.head.eyeY) * returnSpeed;
  }

  _updateMotion(now) {
    const cfg = this._stateConfig();
    const speaking = (this.state === "speaking" || this.state === "broadcast") && this.audioStartTime !== null;
    let low = 0, mid = 0;
    if (speaking) {
      this.analyser.getByteFrequencyData(this.freqData);
      low = _avg(this.freqData.slice(2, 12)) / 255;
      mid = _avg(this.freqData.slice(12, 36)) / 255;
      this._amplitude = low * 0.5 + mid * 0.5;
    } else {
      this._amplitude = 0;
    }

    // getSpeechEmphasis integration
    if (speaking && this._amplitude > 0) {
      const emph = getSpeechEmphasis(this._amplitude);
      this._emphasis.browLift = emph.browLift;
      this._emphasis.jawAmplitude = emph.jawAmplitude;
      this._emphasis.glowBoost = emph.glowBoost;
      this._emphasis.headAccent = emph.headAccent;
    } else {
      this._emphasis.browLift *= 0.85;
      this._emphasis.jawAmplitude += (1 - this._emphasis.jawAmplitude) * 0.15;
      this._emphasis.glowBoost *= 0.85;
      this._emphasis.headAccent *= 0.85;
    }

    const breathAmp = cfg.breathingAmp * LIVE_CONFIG.headBreathingAmp / 1.4;
    const breathSpeed = cfg.breathingSpeed || 0.0018;

    let baseY = 0, baseRot = 0;
    let baseX = Math.sin(now * breathSpeed) * breathAmp;

    if (this.state === "listening") { baseY = -1.5; baseRot = -1.2; }
    else if (this.state === "thinking") { baseY = -1.0; baseRot = 1.0; }
    else if (this.state === "interrupted") { baseY = 1.5; baseRot = 0; }
    else if (this.state === "broadcast") {
      baseY = 0; baseRot = cfg.headTiltDeg;
    }

    let headBob = LIVE_CONFIG.headBobAmp;
    // Broadcast: reduce head bob by 60%
    if (this.state === "broadcast" && LIVE_CONFIG.broadcastPostureTight) {
      headBob *= 0.4;
    }

    const speechY = speaking ? -mid * headBob * 4.0 : 0;
    const speechRot = speaking ? (low - 0.25) * 3.4 : 0;
    // Head accent from speech emphasis (subtle Y nudge)
    const accentY = speaking ? -this._emphasis.headAccent * 1.0 : 0;

    const breathY = Math.cos(now * (breathSpeed * 1.33)) * breathAmp * 0.57;

    this.head.targetX = baseX;
    this.head.targetY = baseY + speechY + breathY + accentY;
    this.head.targetRot = baseRot + speechRot;
    this.head.x += (this.head.targetX - this.head.x) * 0.06;
    this.head.y += (this.head.targetY - this.head.y) * 0.08;
    this.head.rot += (this.head.targetRot - this.head.rot) * 0.07;
  }

  _updateViseme() {
    if ((this.state !== "speaking" && this.state !== "broadcast") || !this.audioStartTime || !this.visemeTimeline.length) {
      this.currentViseme = 0; this.nextViseme = 0;
      this.visemeBlend += (0 - this.visemeBlend) * LIVE_CONFIG.mouthBlendSpeed; return;
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
    const progress = _clamp((elapsed - curr.time) / Math.max(curr.duration, 0.001), 0, 1);
    const blendStart = 0.58;
    const rawBlend = progress > blendStart ? (progress - blendStart) / (1 - blendStart) : 0;
    this.visemeBlend += (rawBlend - this.visemeBlend) * LIVE_CONFIG.mouthBlendSpeed;
  }

  loop = () => {
    const now = performance.now();
    this._updateBlink(now); this._updateGaze(now);
    this._updateMotion(now); this._updateViseme();
    this._render();
    this.raf = requestAnimationFrame(this.loop);
  };

  _render() {
    const ctx = this.ctx, w = this.width, h = this.height;
    ctx.clearRect(0, 0, w, h);
    const bg = ctx.createRadialGradient(w*0.35, h*0.3, 20, w*0.5, h*0.5, w*0.7);
    bg.addColorStop(0, "#1b2230"); bg.addColorStop(1, "#0a0d12");
    ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);

    // Hair shimmer (behind head transform)
    if (LIVE_CONFIG.hairShimmerVisible) {
      this._renderHairShimmer(ctx, w, h);
    }

    ctx.save();
    ctx.translate(w/2 + this.head.x, h/2 + this.head.y);
    ctx.rotate((this.head.rot * Math.PI) / 180);
    ctx.translate(-w/2, -h/2);
    if (this.useSprites && this.sprites.base) this._renderSprite(ctx, w, h);
    else this._renderProcedural(ctx, w, h);
    ctx.restore();

    // Glow pulse
    this._renderGlow(ctx, w, h);

    this._renderBadge(ctx, w, h);
  }

  _renderGlow(ctx, w, h) {
    const cfg = this._stateConfig();
    let glowIntensity = cfg.glowIntensity + this._emphasis.glowBoost * LIVE_CONFIG.glowAmplitudeBoost;

    // Restrained glow cap
    if (LIVE_CONFIG.glowPulseRestrained) {
      glowIntensity = Math.min(glowIntensity, 0.6);
    }
    // Broadcast glow cap
    if (this.state === "broadcast") {
      glowIntensity = Math.min(glowIntensity, LIVE_CONFIG.broadcastGlowCap);
    }

    if (glowIntensity <= 0) return;
    const [r, g, b] = cfg.glowColor;
    const pulse = 1 + Math.sin(performance.now() * (cfg.pulseSpeed || 0.002)) * 0.15;
    const grad = ctx.createRadialGradient(w/2, h*0.35, 10, w/2, h*0.5, w*0.45);
    grad.addColorStop(0, `rgba(${r},${g},${b},${glowIntensity * pulse * 0.4})`);
    grad.addColorStop(1, `rgba(${r},${g},${b},0)`);
    ctx.save();
    ctx.globalCompositeOperation = "screen";
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
    ctx.restore();
  }

  _renderHairShimmer(ctx, w, h) {
    const intensity = LIVE_CONFIG.hairShimmerIntensity;
    if (intensity <= 0) return;
    const t = performance.now() * 0.001;
    const shimmer = Math.sin(t * 2.5) * 0.5 + 0.5;

    ctx.save();
    if (LIVE_CONFIG.hairEdgeGlowOnly) {
      // Edge glow only — subtle highlight on hair edge
      const grad = ctx.createLinearGradient(w*0.3, h*0.12, w*0.7, h*0.12);
      grad.addColorStop(0, `rgba(204,0,0,0)`);
      grad.addColorStop(0.4, `rgba(204,40,40,${shimmer * intensity})`);
      grad.addColorStop(0.6, `rgba(204,40,40,${shimmer * intensity})`);
      grad.addColorStop(1, `rgba(204,0,0,0)`);
      ctx.fillStyle = grad;
      ctx.fillRect(w*0.25, h*0.08, w*0.5, h*0.12);
    } else {
      // Physical wave shimmer
      ctx.fillStyle = `rgba(204,40,40,${shimmer * intensity * 0.6})`;
      ctx.fillRect(w*0.3, h*0.1, w*0.4, h*0.08);
    }
    ctx.restore();
  }

  _renderBadge(ctx, w, h) {
    ctx.save();
    ctx.fillStyle = "rgba(0,0,0,0.28)";
    _roundRect(ctx, 16, 16, 130, 28, 12); ctx.fill();
    const colors = { idle:"#b8c2d9", listening:"#66d9ff", thinking:"#f4c46f",
                     speaking:"#6cff9f", broadcast:"#f7931a", interrupted:"#ff8080" };
    ctx.fillStyle = colors[this.state] || "#fff";
    ctx.font = "600 12px Inter, sans-serif";
    ctx.fillText(this.state.toUpperCase(), 26, 34);
    ctx.restore();
  }

  _renderProcedural(ctx, w, h) {
    const cfg = this._stateConfig();

    // Body
    ctx.fillStyle = "#111722";
    _roundRect(ctx, w*0.22, h*0.65, w*0.56, h*0.28, 40); ctx.fill();
    // Neck
    ctx.fillStyle = "#6a7487";
    _roundRect(ctx, w*0.44, h*0.48, w*0.12, h*0.12, 16); ctx.fill();
    // Head
    const hx = w*0.5, hy = h*0.32, hr = w*0.17;
    const skin = ctx.createRadialGradient(hx-22, hy-28, 10, hx, hy, hr+18);
    skin.addColorStop(0, "#bac7d9"); skin.addColorStop(1, "#7d899c");
    ctx.fillStyle = skin;
    ctx.beginPath(); ctx.ellipse(hx, hy, hr*0.9, hr*1.07, 0, 0, Math.PI*2); ctx.fill();
    // Hair
    ctx.fillStyle = "#1d2431";
    ctx.beginPath(); ctx.ellipse(hx, hy-hr*0.28, hr*0.94, hr*0.58, 0, Math.PI, 0, true);
    ctx.lineTo(hx+hr*0.94, hy-6); ctx.lineTo(hx-hr*0.94, hy-6); ctx.closePath(); ctx.fill();

    // Eyes — left uses primary blink, right uses asymmetric blink
    const leftBlink = this.blink.phase;
    const rightBlink = this.rightEyeBlink.phase || this.blink.phase;
    this._drawEye(ctx, hx-42, hy-6, leftBlink, this.head.eyeX, this.head.eyeY);
    this._drawEye(ctx, hx+42, hy-6, rightBlink, this.head.eyeX, this.head.eyeY);

    // Brows — driven by STATE_CONFIG + LIVE_CONFIG + speech emphasis
    const browCfg = BROW_PARAMS[cfg.browState] || BROW_PARAMS.neutral;
    let browIntensity = cfg.browIntensity * LIVE_CONFIG.browIntensityScale;
    if (this.state === "broadcast") {
      browIntensity = LIVE_CONFIG.broadcastBrowConfidence * LIVE_CONFIG.browIntensityScale;
    }
    // Add speech emphasis brow lift (capped)
    const speechLift = Math.min(this._emphasis.browLift, LIVE_CONFIG.browSpeechLiftMax);
    const totalLift = browCfg.lift * browIntensity + speechLift;
    const furrow = browCfg.furrow * browIntensity;

    ctx.strokeStyle = "#202735"; ctx.lineWidth = 4; ctx.lineCap = "round";
    const bl = -totalLift * 8 + furrow * 4;
    const asymOffset = browCfg.asymmetry * browIntensity * 3;
    ctx.beginPath();
    ctx.moveTo(hx-62, hy-36+bl+asymOffset); ctx.lineTo(hx-22, hy-42+bl);
    ctx.moveTo(hx+22, hy-42+bl); ctx.lineTo(hx+62, hy-36+bl+asymOffset);
    ctx.stroke();

    // Nose
    ctx.strokeStyle = "rgba(70,80,98,0.6)"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(hx, hy-2); ctx.lineTo(hx-3, hy+28); ctx.lineTo(hx+6, hy+34); ctx.stroke();

    // Mouth — jaw amplitude scaled by LIVE_CONFIG + emphasis
    this._drawMouth(ctx, hx, hy+56);
  }

  _drawEye(ctx, cx, cy, blink, dx, dy) {
    const open = 1 - blink;
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
    const cur = _vp(this.currentViseme), nxt = _vp(this.nextViseme), b = this.visemeBlend;
    const open = _lerp(cur.open, nxt.open, b) * LIVE_CONFIG.jawAmplitudeBase * this._emphasis.jawAmplitude;
    const width = _lerp(cur.width, nxt.width, b);
    const round = _lerp(cur.round, nxt.round, b), teeth = _lerp(cur.teeth, nxt.teeth, b);
    const lowerLip = _lerp(cur.lowerLip, nxt.lowerLip, b);
    const mw = 54+width*34, mh = 6+open*38, r = 10+round*18;
    ctx.fillStyle = "rgba(0,0,0,0.16)";
    ctx.beginPath(); ctx.ellipse(cx, cy+16, mw*0.56, 8, 0, 0, Math.PI*2); ctx.fill();
    ctx.fillStyle = "#5d3a44";
    _roundRect(ctx, cx-mw/2, cy-mh/2, mw, mh, r); ctx.fill();
    ctx.fillStyle = "#1a1116";
    _roundRect(ctx, cx-mw*0.45, cy-mh*0.36, mw*0.9, mh*0.72, Math.max(4,r-4)); ctx.fill();
    if (teeth > 0.08) {
      ctx.fillStyle = `rgba(238,243,255,${0.38+teeth*0.42})`;
      _roundRect(ctx, cx-mw*0.32, cy-mh*0.26, mw*0.64, Math.max(4,mh*0.18), 6); ctx.fill();
    }
    if (open > 0.18) {
      ctx.fillStyle = `rgba(164,67,86,${0.22+open*0.4})`;
      _roundRect(ctx, cx-mw*0.24, cy+mh*0.02, mw*0.48, mh*0.2+lowerLip*4, 8); ctx.fill();
    }
  }

  _renderSprite(ctx, w, h) {
    if (this.sprites.base) ctx.drawImage(this.sprites.base, 0, 0, w, h);
    const cur = this.sprites.visemes[this.currentViseme];
    const nxt = this.sprites.visemes[this.nextViseme];
    if (cur) { ctx.globalAlpha = 1 - this.visemeBlend*0.55; ctx.drawImage(cur, 0, 0, w, h); }
    if (nxt && nxt !== cur) { ctx.globalAlpha = this.visemeBlend*0.55; ctx.drawImage(nxt, 0, 0, w, h); }
    ctx.globalAlpha = 1;
    const bf = this.blink.phase > 0.7 ? this.sprites.blinkClosed :
               this.blink.phase > 0.28 ? this.sprites.blinkHalf : null;
    if (bf) { ctx.globalAlpha = 0.85; ctx.drawImage(bf, 0, 0, w, h); ctx.globalAlpha = 1; }
  }

  destroy() {
    if (this.raf) cancelAnimationFrame(this.raf);
    if (this.audioSource) { try { this.audioSource.stop(); } catch(_){} }
    if (this.audioContext) this.audioContext.close();
  }
}

function _avg(a) { if (!a||!a.length) return 0; let s=0; for(let i=0;i<a.length;i++) s+=a[i]; return s/a.length; }
function _clamp(v,lo,hi) { return Math.min(hi,Math.max(lo,v)); }
function _lerp(a,b,t) { return a+(b-a)*t; }
function _roundRect(ctx,x,y,w,h,r) {
  const rr=Math.min(r,w/2,h/2);
  ctx.beginPath(); ctx.moveTo(x+rr,y);
  ctx.arcTo(x+w,y,x+w,y+h,rr); ctx.arcTo(x+w,y+h,x,y+h,rr);
  ctx.arcTo(x,y+h,x,y,rr); ctx.arcTo(x,y,x+w,y,rr); ctx.closePath();
}
function _vp(id) {
  const t = {
    0:{open:0.02,width:0.2,round:0.15,teeth:0.0,lowerLip:0.0},
    1:{open:0.01,width:0.08,round:0.12,teeth:0.0,lowerLip:0.0},
    2:{open:0.12,width:0.26,round:0.14,teeth:0.7,lowerLip:0.15},
    3:{open:0.22,width:0.22,round:0.2,teeth:0.5,lowerLip:0.18},
    4:{open:0.18,width:0.28,round:0.12,teeth:0.45,lowerLip:0.1},
    5:{open:0.18,width:0.18,round:0.3,teeth:0.1,lowerLip:0.05},
    6:{open:0.26,width:0.22,round:0.48,teeth:0.15,lowerLip:0.12},
    7:{open:0.14,width:0.24,round:0.08,teeth:0.5,lowerLip:0.05},
    8:{open:0.12,width:0.22,round:0.1,teeth:0.05,lowerLip:0.08},
    9:{open:0.2,width:0.18,round:0.42,teeth:0.05,lowerLip:0.08},
    10:{open:0.82,width:0.42,round:0.18,teeth:0.05,lowerLip:0.38},
    11:{open:0.46,width:0.36,round:0.08,teeth:0.38,lowerLip:0.16},
    12:{open:0.3,width:0.34,round:0.06,teeth:0.34,lowerLip:0.08},
    13:{open:0.34,width:0.22,round:0.58,teeth:0.05,lowerLip:0.12},
    14:{open:0.22,width:0.16,round:0.78,teeth:0.02,lowerLip:0.06},
  };
  return t[id] || t[0];
}
