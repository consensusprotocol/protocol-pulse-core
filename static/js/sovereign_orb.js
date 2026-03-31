/**
 * SOVEREIGN ORB V4.0 — ALPHA INTELLIGENCE SURFACE
 * Every pixel is a proxy for real protocol data.
 * Perlin breathing + motion trails + HUD telemetry ring + signal lines
 */
class SovereignOrb {
    constructor(canvasId, endpoint='/api/orb') {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.endpoint = endpoint;
        this.data = null;
        this.lastFetch = 0;
        this.t = 0;
        this.trails = {mcx:[], epx:[], ihx:[]};
        this.smoothed = {composite:50, mcx:50, epx:50, ihx:50};
        this.colors = {MCX:'#dc2626', EPX:'#f97316', IHX:'#3b82f6'};
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.fetchData();
        this.animate();
    }

    resize() {
        const w = this.canvas.offsetWidth || 420;
        const h = this.canvas.offsetHeight || 420;
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = w * dpr;
        this.canvas.height = h * dpr;
        this.ctx.scale(dpr, dpr);
        this.w = w; this.h = h;
    }

    async fetchData() {
        try {
            const r = await fetch(this.endpoint);
            if (r.ok) { this.data = await r.json(); this.lastFetch = Date.now(); }
        } catch(e) {}
        setTimeout(() => this.fetchData(), 30000);
    }

    lerp(a,b,t) { return a + (b-a)*t; }

    noise(x, y, t) {
        return Math.sin(x*2.1 + t*1.3) * Math.cos(y*1.7 + t*0.9) * 0.5 +
               Math.sin(x*3.7 + t*0.7) * Math.sin(y*2.9 + t*1.1) * 0.3 +
               Math.cos(x*1.3 + y*2.1 + t*0.5) * 0.2;
    }

    animate() {
        this.t += 0.006;
        const ctx = this.ctx;
        const cx = this.w/2, cy = this.h/2;

        // Smooth data
        if (this.data) {
            const s = 0.025;
            this.smoothed.composite = this.lerp(this.smoothed.composite, this.data.composite.score, s);
            this.smoothed.mcx = this.lerp(this.smoothed.mcx, this.data.nodes.mcx.score, s);
            this.smoothed.epx = this.lerp(this.smoothed.epx, this.data.nodes.epx.score, s);
            this.smoothed.ihx = this.lerp(this.smoothed.ihx, this.data.nodes.ihx.score, s);
        }

        const score = this.smoothed.composite;
        const ageSec = this.data ? Math.round((Date.now()-this.lastFetch)/1000) : 0;
        const isLive = this.data && ageSec < 120;

        // ── BACKGROUND ──
        ctx.fillStyle = '#060606';
        ctx.fillRect(0,0,this.w,this.h);

        // ── SCANLINES ──
        ctx.fillStyle = 'rgba(255,255,255,0.018)';
        for (let i=0; i<this.h; i+=3) ctx.fillRect(0,i,this.w,1);

        // ── RADIAL GRID ──
        [0.18, 0.3, 0.42, 0.54, 0.66].forEach((f,i) => {
            const r = Math.min(cx,cy)*f*2;
            ctx.strokeStyle = `rgba(220,38,38,${0.04+i*0.01})`;
            ctx.lineWidth = 0.5;
            ctx.setLineDash([]);
            ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.stroke();
        });

        // Crosshair
        ctx.strokeStyle = 'rgba(220,38,38,0.06)';
        ctx.lineWidth = 0.5;
        ctx.beginPath(); ctx.moveTo(cx,0); ctx.lineTo(cx,this.h); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0,cy); ctx.lineTo(this.w,cy); ctx.stroke();

        // ── PERIMETER SIGNAL RING ──
        const ringR = Math.min(cx,cy)*0.88;
        const signals = this.data ? [
            {label:'HASH', val:this.data.streams.hashrate, angle:-Math.PI/2},
            {label:'F&G',  val:this.data.streams.fear_greed, angle:-Math.PI/6},
            {label:'FEES', val:this.data.streams.fees, angle:Math.PI/6},
            {label:'FLOW', val:this.data.streams.exchange_flow, angle:Math.PI/2},
            {label:'KOL',  val:this.data.streams.kol, angle:5*Math.PI/6},
            {label:'HASH', val:this.data.streams.hashrate, angle:-5*Math.PI/6},
        ] : [];

        // Dashed outer ring
        ctx.strokeStyle = `rgba(220,38,38,${0.1+score/800})`;
        ctx.lineWidth = 1;
        ctx.setLineDash([4,6]);
        ctx.beginPath(); ctx.arc(cx,cy,ringR,0,Math.PI*2); ctx.stroke();
        ctx.setLineDash([]);

        signals.slice(0,5).forEach(s => {
            const tx = cx + Math.cos(s.angle)*(ringR+20);
            const ty = cy + Math.sin(s.angle)*(ringR+20);
            const col = s.val>65?'#22c55e':s.val<35?'#dc2626':'#666';
            // tick
            ctx.strokeStyle = col+'88';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(cx+Math.cos(s.angle)*ringR, cy+Math.sin(s.angle)*ringR);
            ctx.lineTo(cx+Math.cos(s.angle)*(ringR-10), cy+Math.sin(s.angle)*(ringR-10));
            ctx.stroke();
            // label
            ctx.fillStyle = col;
            ctx.font = "700 8px 'JetBrains Mono',monospace";
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(`${s.label} ${Math.round(s.val)}`, tx, ty);
        });

        // ── THREE ORBITAL NODES ──
        const nodes = [
            {key:'MCX', score:this.smoothed.mcx, trailKey:'mcx', offset:0},
            {key:'EPX', score:this.smoothed.epx, trailKey:'epx', offset:Math.PI*2/3},
            {key:'IHX', score:this.smoothed.ihx, trailKey:'ihx', offset:Math.PI*4/3},
        ];

        const nodePositions = [];
        nodes.forEach(n => {
            const orbitR = ringR*0.6*(1-(n.score-20)/160);
            const spd = 0.2+(n.score/500);
            const ang = this.t*spd+n.offset;
            const nx = cx+Math.cos(ang)*orbitR;
            const ny = cy+Math.sin(ang)*orbitR;
            nodePositions.push({x:nx, y:ny, color:this.colors[n.key]});

            // Trail
            const trail = this.trails[n.trailKey];
            trail.push({x:nx,y:ny});
            if(trail.length>25) trail.shift();
            ctx.lineWidth = 1.5;
            trail.forEach((p,i) => {
                if(i===0) return;
                ctx.globalAlpha = (i/trail.length)*0.4;
                ctx.strokeStyle = this.colors[n.key];
                ctx.beginPath();
                ctx.moveTo(trail[i-1].x, trail[i-1].y);
                ctx.lineTo(p.x, p.y);
                ctx.stroke();
            });
            ctx.globalAlpha = 1;

            // Signal line center→node
            ctx.strokeStyle = this.colors[n.key]+'22';
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(nx,ny); ctx.stroke();

            // Node glow
            const nr = 4+(n.score/28);
            const g = ctx.createRadialGradient(nx,ny,0,nx,ny,nr*4);
            g.addColorStop(0, this.colors[n.key]+'cc');
            g.addColorStop(1, 'transparent');
            ctx.fillStyle = g;
            ctx.beginPath(); ctx.arc(nx,ny,nr*4,0,Math.PI*2); ctx.fill();

            // Node dot
            ctx.fillStyle = this.colors[n.key];
            ctx.shadowBlur = 16; ctx.shadowColor = this.colors[n.key];
            ctx.beginPath(); ctx.arc(nx,ny,nr,0,Math.PI*2); ctx.fill();
            ctx.shadowBlur = 0;

            // Node label
            const lx = nx+(nx>cx?nr+26:-(nr+26));
            ctx.fillStyle = '#fff';
            ctx.font = "700 10px 'JetBrains Mono',monospace";
            ctx.textAlign = nx>cx?'left':'right';
            ctx.textBaseline = 'middle';
            ctx.fillText(`${n.key} ${Math.round(n.score)}`, lx, ny);
        });

        // Node triangle connections
        for(let i=0;i<nodePositions.length;i++) {
            const a=nodePositions[i], b=nodePositions[(i+1)%nodePositions.length];
            ctx.strokeStyle='rgba(255,255,255,0.05)';
            ctx.lineWidth=1;
            ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
        }

        // ── DEFORMED CORE (Perlin breathing) ──
        const coreR = 22+(score/5.5);
        const pulse = Math.sin(this.t*(3+score/40))*((100-score)/20+2);
        const segs = 64;
        ctx.beginPath();
        for(let i=0;i<=segs;i++) {
            const a = (i/segs)*Math.PI*2;
            const noiseV = this.noise(Math.cos(a), Math.sin(a), this.t)*(8*(1-score/120));
            const r = coreR+pulse+noiseV;
            const x=cx+Math.cos(a)*r, y=cy+Math.sin(a)*r;
            i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
        }
        ctx.closePath();
        const cg = ctx.createRadialGradient(cx,cy,0,cx,cy,coreR+pulse+8);
        cg.addColorStop(0,'#ffffff');
        cg.addColorStop(0.3, score>75?'#dc2626':score>50?'#f97316':'#3b82f6');
        cg.addColorStop(1,'transparent');
        ctx.fillStyle = cg;
        ctx.shadowBlur = 30+(score/4);
        ctx.shadowColor = score>75?'#dc2626':score>50?'rgba(249,115,22,0.8)':'rgba(59,130,246,0.8)';
        ctx.fill();
        ctx.shadowBlur = 0;

        // ── CORE SCORE (dominant, centered) ──
        const scoreStr = Math.round(score).toString();
        const fontSize = Math.round(18+score/9);
        ctx.font = `800 ${fontSize}px 'JetBrains Mono',monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = score>60?'#000':'#fff';
        ctx.fillText(scoreStr, cx, cy-4);

        // State label
        const pattern = this.data?(this.data.composite.pattern||'MONITORING'):'SYNCING';
        ctx.font = "600 7px 'JetBrains Mono',monospace";
        ctx.fillStyle = score>60?'rgba(0,0,0,0.6)':'rgba(255,255,255,0.5)';
        ctx.fillText(pattern.toUpperCase(), cx, cy+fontSize*0.6+4);

        // ── LIVE INDICATOR ──
        const liveStr = !this.data?'CONNECTING':isLive?`LIVE · ${ageSec}s`:'STALE';
        const liveCol = !this.data?'#666':isLive?'#22c55e':'#dc2626';
        ctx.fillStyle = liveCol;
        ctx.font = "600 8px 'JetBrains Mono',monospace";
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillText(liveStr, cx, this.h-10);

        // Model metadata
        ctx.fillStyle = 'rgba(255,255,255,0.15)';
        ctx.font = "500 7px 'JetBrains Mono',monospace";
        ctx.textAlign = 'left';
        ctx.textBaseline = 'bottom';
        ctx.fillText('SOVEREIGN v1.3', 10, this.h-10);

        requestAnimationFrame(() => this.animate());
    }
}
window.SovereignOrb = SovereignOrb;
