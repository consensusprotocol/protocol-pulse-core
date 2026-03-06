
/**
 * HologramActivation — Premium restrained sequence
 * 2 hero effects only: scanline reveal + holographic resolve
 * 1 support: tiny chromatic split on impact
 * Duration driven by LIVE_CONFIG.activationDurationMs
 * No barrel distortion. No heavy pixelation. No random noise.
 */
import { LIVE_CONFIG } from "./OracleTuningPanel.js";

export class HologramActivation {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx    = canvas.getContext("2d");
    this.w      = canvas.width;
    this.h      = canvas.height;
  }

  /**
   * Run full activation sequence, then call onComplete().
   * avatarRenderFn(ctx, progress) — draws the avatar at resolve progress 0→1
   */
  async run(avatarRenderFn, onComplete) {
    const ctx   = this.ctx;
    const w     = this.w;
    const h     = this.h;
    const start = performance.now();

    // Timing derived from LIVE_CONFIG.activationDurationMs (default 1200)
    const totalMs = LIVE_CONFIG.activationDurationMs;
    const p1End   = totalMs * 0.15;       // ~180ms chromatic split
    const p2End   = totalMs * 0.583;      // ~700ms scanline reveal
    const p3End   = totalMs * 0.917;      // ~1100ms holographic resolve
    // p4 = remainder → totalMs           // ~100ms system online blink

    await new Promise(resolve => {
      const animate = (now) => {
        const elapsed = now - start;
        ctx.clearRect(0, 0, w, h);

        // Deep background always present
        ctx.fillStyle = "#07090f";
        ctx.fillRect(0, 0, w, h);

        if (elapsed < p1End) {
          // ── Phase 1: Chromatic split ──────────────────────────────────────
          this._renderChromaticSplit(ctx, w, h, elapsed / p1End);

        } else if (elapsed < p2End) {
          // ── Phase 2: Scanline reveal ──────────────────────────────────────
          const progress = (elapsed - p1End) / (p2End - p1End);
          const scanY    = h - h * this._easeOut(progress);

          // Avatar resolves below the scanline
          ctx.save();
          ctx.beginPath();
          ctx.rect(0, scanY, w, h - scanY);
          ctx.clip();
          avatarRenderFn(ctx, progress * 0.6);
          ctx.restore();

          // Scanline itself — thin cyan stripe
          const lineGrad = ctx.createLinearGradient(0, scanY - 3, 0, scanY + 3);
          lineGrad.addColorStop(0, "rgba(0,220,255,0)");
          lineGrad.addColorStop(0.5, `rgba(0,220,255,${LIVE_CONFIG.scanlineCyanOpacity})`);
          lineGrad.addColorStop(1, "rgba(0,220,255,0)");
          ctx.fillStyle = lineGrad;
          ctx.fillRect(0, scanY - 3, w, 6);

          // Subtle horizontal lines below scanline (CRT feel, very low opacity)
          ctx.save();
          ctx.globalAlpha = 0.06;
          ctx.strokeStyle = "#00dcff";
          ctx.lineWidth   = 1;
          for (let y = scanY + 4; y < h; y += 6) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
          }
          ctx.restore();

        } else if (elapsed < p3End) {
          // ── Phase 3: Holographic resolve ──────────────────────────────────
          const progress  = (elapsed - p2End) / (p3End - p2End);
          const eased     = this._easeOut(progress);
          const resolveP  = 0.6 + eased * 0.4;

          avatarRenderFn(ctx, resolveP);

          // Holographic edge glow — fades in (driven by LIVE_CONFIG)
          const edgeOpacity = eased * LIVE_CONFIG.hologramEdgeGlow;
          const edgeGrad = ctx.createRadialGradient(w/2, h/2, w*0.25, w/2, h/2, w*0.55);
          edgeGrad.addColorStop(0, "rgba(0,220,255,0)");
          edgeGrad.addColorStop(0.7, `rgba(0,220,255,${edgeOpacity * 0.15})`);
          edgeGrad.addColorStop(1,   `rgba(0,220,255,${edgeOpacity})`);
          ctx.fillStyle = edgeGrad;
          ctx.fillRect(0, 0, w, h);

          // Subtle flicker (2 frames only, at 60%)
          if (progress > 0.5 && progress < 0.65 && Math.random() < 0.3) {
            ctx.globalAlpha = 0.15;
            ctx.fillStyle = "white";
            ctx.fillRect(0, 0, w, h);
            ctx.globalAlpha = 1;
          }

        } else if (elapsed < totalMs) {
          // ── Phase 4: Online — avatar fully resolved ───────────────────────
          avatarRenderFn(ctx, 1.0);

          // Cyan rim fades out
          const fade = 1 - (elapsed - p3End) / (totalMs - p3End);
          const rim  = ctx.createRadialGradient(w/2, h/2, w*0.3, w/2, h/2, w*0.55);
          rim.addColorStop(0, "rgba(0,220,255,0)");
          rim.addColorStop(1, `rgba(0,220,255,${fade * 0.2})`);
          ctx.fillStyle = rim;
          ctx.fillRect(0, 0, w, h);

        } else {
          // Done
          resolve();
          return;
        }

        requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
    });

    onComplete && onComplete();
  }

  _renderChromaticSplit(ctx, w, h, progress) {
    const maxShift = LIVE_CONFIG.chromaticSplitMaxPx * (1 - progress);
    const opacity  = 0.5 * (1 - progress);

    // Red channel offset left
    ctx.save();
    ctx.globalCompositeOperation = "screen";
    ctx.fillStyle = `rgba(204,0,0,${opacity})`;
    ctx.fillRect(-maxShift, 0, w, h);

    // Blue channel offset right
    ctx.fillStyle = `rgba(0,100,204,${opacity})`;
    ctx.fillRect(maxShift, 0, w, h);
    ctx.restore();
  }

  _easeOut(t) {
    return 1 - Math.pow(1 - t, 2.5);
  }
}
