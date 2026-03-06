
/**
 * HologramActivation — Premium restrained sequence
 * 2 hero effects only: scanline reveal + holographic resolve
 * 1 support: tiny chromatic split on impact
 * Duration: ~1200ms
 * No barrel distortion. No heavy pixelation. No random noise.
 */

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

    // Phase 1 (0–180ms): Chromatic split impact
    // Phase 2 (180–700ms): Scanline reveal sweeping bottom→top
    // Phase 3 (700–1100ms): Holographic resolve + flicker settle
    // Phase 4 (1100–1200ms): Single blink, system online

    await new Promise(resolve => {
      const animate = (now) => {
        const elapsed = now - start;
        ctx.clearRect(0, 0, w, h);

        // Deep background always present
        ctx.fillStyle = "#07090f";
        ctx.fillRect(0, 0, w, h);

        if (elapsed < 180) {
          // ── Phase 1: Chromatic split ──────────────────────────────────────
          this._renderChromaticSplit(ctx, w, h, elapsed / 180);

        } else if (elapsed < 700) {
          // ── Phase 2: Scanline reveal ──────────────────────────────────────
          const progress = (elapsed - 180) / 520;  // 0→1
          const scanY    = h - h * this._easeOut(progress);

          // Avatar resolves below the scanline
          ctx.save();
          ctx.beginPath();
          ctx.rect(0, scanY, w, h - scanY);
          ctx.clip();
          avatarRenderFn(ctx, progress * 0.6); // partial resolve
          ctx.restore();

          // Scanline itself — thin cyan stripe
          const lineGrad = ctx.createLinearGradient(0, scanY - 3, 0, scanY + 3);
          lineGrad.addColorStop(0, "rgba(0,220,255,0)");
          lineGrad.addColorStop(0.5, "rgba(0,220,255,0.85)");
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

        } else if (elapsed < 1100) {
          // ── Phase 3: Holographic resolve ──────────────────────────────────
          const progress  = (elapsed - 700) / 400;  // 0→1
          const eased     = this._easeOut(progress);
          const resolveP  = 0.6 + eased * 0.4;      // 0.6→1.0

          avatarRenderFn(ctx, resolveP);

          // Holographic edge glow — fades in
          const edgeOpacity = eased * 0.35;
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

        } else if (elapsed < 1200) {
          // ── Phase 4: Online — avatar fully resolved ───────────────────────
          avatarRenderFn(ctx, 1.0);

          // Cyan rim fades out
          const fade = 1 - (elapsed - 1100) / 100;
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
    // Restrained: max ±4px split, fades out by end of phase
    const maxShift = 4 * (1 - progress);
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
