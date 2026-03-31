/**
 * SOVEREIGN CONVERGENCE ORB v3.0
 * Dual-layer: intuitive motion + literal numbers
 * Every pixel is a proxy for real protocol data
 */
class SovereignOrb {
    constructor(canvasId, endpoint = '/api/orb') {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.endpoint = endpoint;
        this.data = null;
        this.lastFetch = 0;
        this.animFrame = null;
        this.t = 0;
        this.smoothed = { composite: 50, mcx: 50, epx: 50, ihx: 50 };
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.fetchData();
        this.animate();
    }

    resize() {
        const dpr = window.devicePixelRatio || 1;
        const r = this.canvas.getBoundingClientRect();
        this.canvas.width = r.width * dpr;
        this.canvas.height = r.height * dpr;
        this.ctx.scale(dpr, dpr);
        this.w = r.width;
        this.h = r.height;
    }

    async fetchData() {
        try {
            const res = await fetch(this.endpoint);
            if (res.ok) {
                this.data = await res.json();
                this.lastFetch = Date.now();
            }
        } catch(e) { console.warn('Orb fetch failed:', e); }
        setTimeout(() => this.fetchData(), 30000);
    }

    lerp(a, b, t) { return a + (b - a) * t; }

    animate() {
        this.t += 0.008;
        const ctx = this.ctx;
        const cx = this.w / 2, cy = this.h / 2;

        // Smooth data interpolation
        if (this.data) {
            const d = this.data;
            const sp = 0.03;
            this.smoothed.composite = this.lerp(this.smoothed.composite, d.composite.score, sp);
            this.smoothed.mcx = this.lerp(this.smoothed.mcx, d.nodes.mcx.score, sp);
            this.smoothed.epx = this.lerp(this.smoothed.epx, d.nodes.epx.score, sp);
            this.smoothed.ihx = this.lerp(this.smoothed.ihx, d.nodes.ihx.score, sp);
        }

        const score = this.smoothed.composite;
        const isLive = this.data && (Date.now() - this.lastFetch) < 120000;
        const isStale = this.data && (Date.now() - this.lastFetch) >= 120000;

        // Clear
        ctx.clearRect(0, 0, this.w, this.h);
        ctx.fillStyle = '#060606';
        ctx.fillRect(0, 0, this.w, this.h);

        // Grid
        ctx.strokeStyle = 'rgba(220,38,38,0.04)';
        ctx.lineWidth = 1;
        for (let x = 0; x < this.w; x += 40) {
            ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,this.h); ctx.stroke();
        }
        for (let y = 0; y < this.h; y += 40) {
            ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(this.w,y); ctx.stroke();
        }

        // Outer ring — rotates with score
        const ringR = Math.min(cx, cy) * 0.82;
        const dash = score > 70 ? [4,2] : score > 40 ? [6,4] : [2,8];
        ctx.setLineDash(dash);
        ctx.strokeStyle = `rgba(220,38,38,${0.15 + score/500})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(cx, cy, ringR, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        // Secondary ring
        ctx.strokeStyle = `rgba(220,38,38,0.07)`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(cx, cy, ringR * 0.65, 0, Math.PI * 2);
        ctx.stroke();

        // Radial tick marks on outer ring
        const tickData = this.data ? [
            {label:'HASH', val: this.data.streams.hashrate, angle: -Math.PI/6},
            {label:'F&G',  val: this.data.streams.fear_greed, angle: Math.PI/6},
            {label:'FEES', val: this.data.streams.fees, angle: Math.PI/2},
            {label:'FLOW', val: this.data.streams.exchange_flow, angle: 5*Math.PI/6},
            {label:'KOL',  val: this.data.streams.kol, angle: -5*Math.PI/6},
        ] : [];

        tickData.forEach(t => {
            const tx = cx + Math.cos(t.angle) * (ringR + 18);
            const ty = cy + Math.sin(t.angle) * (ringR + 18);
            const col = t.val > 65 ? '#22c55e' : t.val < 35 ? '#dc2626' : '#888';
            // Tick line
            ctx.strokeStyle = col;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(cx + Math.cos(t.angle)*ringR, cy + Math.sin(t.angle)*ringR);
            ctx.lineTo(cx + Math.cos(t.angle)*(ringR-8), cy + Math.sin(t.angle)*(ringR-8));
            ctx.stroke();
            // Label
            ctx.fillStyle = col;
            ctx.font = `700 9px 'JetBrains Mono', monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(`${t.label} ${Math.round(t.val)}`, tx, ty);
        });

        // Three orbiting nodes (MCX, EPX, IHX)
        const nodes = [
            {key:'MCX', score: this.smoothed.mcx, color:'#dc2626', offset: 0},
            {key:'EPX', score: this.smoothed.epx, color:'#f97316', offset: Math.PI*2/3},
            {key:'IHX', score: this.smoothed.ihx, color:'#3b82f6', offset: Math.PI*4/3},
        ];

        nodes.forEach(n => {
            // High score = pulls closer to center (gravity metaphor)
            const orbitR = ringR * 0.62 * (1 - (n.score - 20) / 160);
            const speed = 0.25 + (n.score / 400);
            const angle = this.t * speed + n.offset;
            const nx = cx + Math.cos(angle) * orbitR;
            const ny = cy + Math.sin(angle) * orbitR;
            const nodeR = 4 + (n.score / 25);

            // Orbit trail
            ctx.strokeStyle = n.color + '22';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(cx, cy, orbitR, 0, Math.PI * 2);
            ctx.stroke();

            // Node glow
            const glow = ctx.createRadialGradient(nx, ny, 0, nx, ny, nodeR * 3);
            glow.addColorStop(0, n.color + 'aa');
            glow.addColorStop(1, 'transparent');
            ctx.fillStyle = glow;
            ctx.beginPath();
            ctx.arc(nx, ny, nodeR * 3, 0, Math.PI * 2);
            ctx.fill();

            // Node
            ctx.fillStyle = n.color;
            ctx.shadowBlur = 12;
            ctx.shadowColor = n.color;
            ctx.beginPath();
            ctx.arc(nx, ny, nodeR, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;

            // Label + score on node
            const labelX = nx + (nx > cx ? nodeR + 22 : -(nodeR + 22));
            ctx.fillStyle = '#fff';
            ctx.font = `700 10px 'JetBrains Mono', monospace`;
            ctx.textAlign = nx > cx ? 'left' : 'right';
            ctx.textBaseline = 'middle';
            ctx.fillText(`${n.key} ${Math.round(n.score)}`, labelX, ny);
        });

        // Core — size driven by composite score
        const coreR = 18 + (score / 6);
        const pulse = Math.sin(this.t * 4) * (3 + score/20);

        // Core glow layers
        [coreR*3.5, coreR*2.5, coreR*1.8].forEach((r, i) => {
            const alpha = [0.04, 0.08, 0.15][i];
            const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
            grad.addColorStop(0, `rgba(255,255,255,${alpha})`);
            grad.addColorStop(1, 'transparent');
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(cx, cy, r + pulse, 0, Math.PI * 2);
            ctx.fill();
        });

        // Core body
        const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR + pulse);
        coreGrad.addColorStop(0, '#ffffff');
        coreGrad.addColorStop(0.4, score > 70 ? '#dc2626' : score > 40 ? '#f97316' : '#3b82f6');
        coreGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = coreGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, coreR + pulse, 0, Math.PI * 2);
        ctx.fill();

        // COMPOSITE SCORE — large, dead center
        ctx.fillStyle = score > 60 ? '#000' : '#fff';
        ctx.font = `700 ${Math.round(14 + score/10)}px 'JetBrains Mono', monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(score), cx, cy - 2);

        // Pattern label below core
        const pattern = this.data ? (this.data.composite.pattern || 'MONITORING') : 'SYNCING';
        ctx.fillStyle = 'rgba(255,255,255,0.5)';
        ctx.font = `600 8px 'JetBrains Mono', monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(pattern.toUpperCase(), cx, cy + coreR + pulse + 10);

        // Freshness indicator
        const staleAge = this.data ? Math.round((Date.now() - this.lastFetch) / 1000) : 0;
        const freshLabel = !this.data ? 'CONNECTING' : isStale ? 'STALE' : `LIVE · ${staleAge}s`;
        const freshColor = !this.data ? '#888' : isStale ? '#dc2626' : '#22c55e';
        ctx.fillStyle = freshColor;
        ctx.font = `600 8px 'JetBrains Mono', monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillText(freshLabel, cx, this.h - 12);

        requestAnimationFrame(() => this.animate());
    }
}
window.SovereignOrb = SovereignOrb;
