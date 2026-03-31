/**
 * SOVEREIGN ORB V5.0 — HARDENED INTELLIGENCE ASSET
 * Hover micro-intelligence cards + Commander click paywall
 * Data-driven motion: distance/speed/brightness all tied to real scores
 * Perlin breathing + motion trails + HUD ring + signal lines
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
        this.trails = {mcx:[],epx:[],ihx:[]};
        this.smoothed = {composite:50,mcx:50,epx:50,ihx:50};
        this.colors = {MCX:'#dc2626',EPX:'#f97316',IHX:'#3b82f6'};
        this.mouse = {x:-999,y:-999};
        this.hoveredNode = null;
        this.nodePositionsLast = [];
        this.hoverCard = null;
        this.hoverTimeout = null;

        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.canvas.addEventListener('mousemove', e => this._onMouseMove(e));
        this.canvas.addEventListener('mouseleave', () => { this.mouse={x:-999,y:-999}; this._clearHover(); });
        this.canvas.addEventListener('click', () => this._onClick());
        this.fetchData();
        this.animate();
        this._buildHoverCard();
    }

    resize() {
        const w = this.canvas.offsetWidth||520;
        const h = this.canvas.offsetHeight||520;
        const dpr = window.devicePixelRatio||1;
        this.canvas.width=w*dpr; this.canvas.height=h*dpr;
        this.ctx.scale(dpr,dpr);
        this.w=w; this.h=h;
    }

    async fetchData() {
        try {
            const r = await fetch(this.endpoint);
            if(r.ok){this.data=await r.json(); this.lastFetch=Date.now();}
        } catch(e) {}
        setTimeout(()=>this.fetchData(),30000);
    }

    _buildHoverCard() {
        const el = document.createElement('div');
        el.id = 'orb-hover-card';
        el.style.cssText = `
            position:absolute;display:none;pointer-events:none;z-index:100;
            background:rgba(6,6,6,0.96);border:1px solid #dc2626;border-radius:8px;
            padding:12px 16px;min-width:180px;max-width:220px;
            font-family:'JetBrains Mono',monospace;
            box-shadow:0 0 24px rgba(220,38,38,0.2),0 4px 20px rgba(0,0,0,0.8);
            backdrop-filter:blur(8px);
        `;
        this.canvas.parentElement.style.position='relative';
        this.canvas.parentElement.appendChild(el);
        this.hoverCard = el;
    }

    _onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        this.mouse.x = e.clientX - rect.left;
        this.mouse.y = e.clientY - rect.top;
    }

    _clearHover() {
        clearTimeout(this.hoverTimeout);
        this.hoveredNode = null;
        if(this.hoverCard) this.hoverCard.style.display='none';
        this.canvas.style.cursor = 'crosshair';
    }

    _showHoverCard(node, nx, ny) {
        if(!this.hoverCard) return;
        const score = Math.round(node.score);
        const regime = score>70?'EXPANSION':score<35?'SUPPRESSION':'NEUTRAL';
        const trend = score>70?'↑ CONVICTION':'↓ NEUTRAL';
        const interp = {
            MCX: score>70?'Miners expanding into compression — supply shock precursor':'Miner activity within normal range',
            EPX: score>60?'Net outflow detected — accumulation bias':'Exchange flow neutral — monitoring',
            IHX: score>60?'Social sentiment diverging from price — watch carefully':'Social aligned with price action'
        };
        const isCommander = document.body.dataset.userTier==='commander';
        this.hoverCard.innerHTML = `
            <div style="color:${this.colors[node.key]};font-size:0.6rem;letter-spacing:0.15em;margin-bottom:6px;">${node.key} — ${node.key==='MCX'?'MINER CONVICTION':node.key==='EPX'?'EXCHANGE PRESSURE':'INSIDER HEAT'}</div>
            <div style="font-size:1.6rem;font-weight:800;color:#fff;line-height:1;">${score}</div>
            <div style="font-size:0.6rem;color:${score>70?'#22c55e':score<35?'#dc2626':'#888'};margin:4px 0 8px;letter-spacing:0.1em;">${regime} · ${trend}</div>
            <div style="font-size:0.65rem;color:rgba(255,255,255,0.5);line-height:1.5;border-top:1px solid rgba(255,255,255,0.08);padding-top:8px;">${interp[node.key]}</div>
            ${!isCommander?`<div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(220,38,38,0.2);font-size:0.6rem;color:rgba(220,38,38,0.7);letter-spacing:0.08em;cursor:pointer;" onclick="window.location='/commander'">🔒 FORENSIC AUDIT — COMMANDER ONLY</div>`:''}
        `;
        const cRect = this.canvas.getBoundingClientRect();
        const cardX = nx + 20 < this.w - 240 ? nx + 20 : nx - 240;
        const cardY = Math.max(10, ny - 40);
        this.hoverCard.style.left = cardX + 'px';
        this.hoverCard.style.top = cardY + 'px';
        this.hoverCard.style.display = 'block';
        this.canvas.style.cursor = 'crosshair';
    }

    _onClick() {
        if(!this.hoveredNode) return;
        const isCommander = document.body.dataset.userTier==='commander';
        if(isCommander) {
            window.location = '/commander?signal=' + this.hoveredNode.key.toLowerCase();
        } else {
            window.location = '/commander';
        }
    }

    lerp(a,b,t){return a+(b-a)*t;}

    noise(x,y,t){
        return Math.sin(x*2.1+t*1.3)*Math.cos(y*1.7+t*0.9)*0.5+
               Math.sin(x*3.7+t*0.7)*Math.sin(y*2.9+t*1.1)*0.3+
               Math.cos(x*1.3+y*2.1+t*0.5)*0.2;
    }

    animate() {
        this.t += 0.006;
        const ctx=this.ctx, cx=this.w/2, cy=this.h/2;
        const s=0.025;
        if(this.data){
            this.smoothed.composite=this.lerp(this.smoothed.composite,this.data.composite.score,s);
            this.smoothed.mcx=this.lerp(this.smoothed.mcx,this.data.nodes.mcx.score,s);
            this.smoothed.epx=this.lerp(this.smoothed.epx,this.data.nodes.epx.score,s);
            this.smoothed.ihx=this.lerp(this.smoothed.ihx,this.data.nodes.ihx.score,s);
        }
        const score=this.smoothed.composite;
        const ageSec=this.data?Math.round((Date.now()-this.lastFetch)/1000):0;
        const isLive=this.data&&ageSec<120;

        // BG
        ctx.fillStyle='#060606'; ctx.fillRect(0,0,this.w,this.h);
        // Scanlines
        ctx.fillStyle='rgba(255,255,255,0.015)';
        for(let i=0;i<this.h;i+=3) ctx.fillRect(0,i,this.w,1);

        // Radial grid
        [0.15,0.27,0.39,0.51,0.63,0.75].forEach((f,i)=>{
            const r=Math.min(cx,cy)*f*2;
            ctx.strokeStyle=`rgba(220,38,38,${0.03+i*0.008})`;
            ctx.lineWidth=0.5; ctx.setLineDash([]);
            ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.stroke();
        });
        // Radial ticks (30deg increments)
        for(let a=0;a<Math.PI*2;a+=Math.PI/6){
            const r1=Math.min(cx,cy)*0.72, r2=r1-8;
            ctx.strokeStyle='rgba(220,38,38,0.08)'; ctx.lineWidth=0.5;
            ctx.beginPath();
            ctx.moveTo(cx+Math.cos(a)*r1,cy+Math.sin(a)*r1);
            ctx.lineTo(cx+Math.cos(a)*r2,cy+Math.sin(a)*r2);
            ctx.stroke();
        }
        // Crosshair
        ctx.strokeStyle='rgba(220,38,38,0.05)'; ctx.lineWidth=0.5;
        ctx.beginPath(); ctx.moveTo(cx,0); ctx.lineTo(cx,this.h); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0,cy); ctx.lineTo(this.w,cy); ctx.stroke();

        // Perimeter ring + signals
        const ringR=Math.min(cx,cy)*0.86;
        ctx.strokeStyle=`rgba(220,38,38,${0.08+score/1000})`; ctx.lineWidth=1;
        ctx.setLineDash([3,7]); ctx.beginPath(); ctx.arc(cx,cy,ringR,0,Math.PI*2); ctx.stroke();
        ctx.setLineDash([]);
        const sigs=this.data?[
            {label:'HASH',val:this.data.streams.hashrate,angle:-Math.PI/2},
            {label:'F&G', val:this.data.streams.fear_greed,angle:-Math.PI/6},
            {label:'FEES',val:this.data.streams.fees,angle:Math.PI/6},
            {label:'FLOW',val:this.data.streams.exchange_flow,angle:Math.PI/2},
            {label:'KOL', val:this.data.streams.kol,angle:5*Math.PI/6},
        ]:[];
        sigs.forEach(s=>{
            const tx=cx+Math.cos(s.angle)*(ringR+22), ty=cy+Math.sin(s.angle)*(ringR+22);
            const col=s.val>65?'#22c55e':s.val<35?'#dc2626':'#555';
            ctx.strokeStyle=col+'66'; ctx.lineWidth=1;
            ctx.beginPath();
            ctx.moveTo(cx+Math.cos(s.angle)*ringR,cy+Math.sin(s.angle)*ringR);
            ctx.lineTo(cx+Math.cos(s.angle)*(ringR-12),cy+Math.sin(s.angle)*(ringR-12));
            ctx.stroke();
            ctx.fillStyle=col; ctx.font="700 8px 'JetBrains Mono',monospace";
            ctx.textAlign='center'; ctx.textBaseline='middle';
            ctx.fillText(`${s.label} ${Math.round(s.val)}`,tx,ty);
        });

        // Nodes
        const nodeDefs=[
            {key:'MCX',score:this.smoothed.mcx,trailKey:'mcx',offset:0},
            {key:'EPX',score:this.smoothed.epx,trailKey:'epx',offset:Math.PI*2/3},
            {key:'IHX',score:this.smoothed.ihx,trailKey:'ihx',offset:Math.PI*4/3},
        ];
        const newPositions=[];
        let newHovered=null;
        nodeDefs.forEach(n=>{
            // DATA-DRIVEN: orbit radius inversely proportional to score (high score = closer to center)
            const orbitR=ringR*0.58*(1-(n.score-15)/155);
            // DATA-DRIVEN: speed proportional to score
            const spd=0.15+(n.score/600);
            const ang=this.t*spd+n.offset;
            const nx=cx+Math.cos(ang)*orbitR, ny=cy+Math.sin(ang)*orbitR;
            newPositions.push({x:nx,y:ny,color:this.colors[n.key],key:n.key,score:n.score});

            // Proximity check for hover
            const dx=this.mouse.x-nx, dy=this.mouse.y-ny;
            if(Math.sqrt(dx*dx+dy*dy)<28){
                newHovered={key:n.key,score:n.score,x:nx,y:ny};
            }

            // Trails
            const trail=this.trails[n.trailKey];
            trail.push({x:nx,y:ny}); if(trail.length>30) trail.shift();
            ctx.lineWidth=1.5;
            trail.forEach((p,i)=>{
                if(i===0) return;
                ctx.globalAlpha=(i/trail.length)*0.35;
                ctx.strokeStyle=this.colors[n.key];
                ctx.beginPath(); ctx.moveTo(trail[i-1].x,trail[i-1].y); ctx.lineTo(p.x,p.y); ctx.stroke();
            });
            ctx.globalAlpha=1;

            // Signal line center→node
            ctx.strokeStyle=this.colors[n.key]+'1a'; ctx.lineWidth=1;
            ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(nx,ny); ctx.stroke();

            // DATA-DRIVEN: node size proportional to score
            const nr=3+(n.score/24);
            // Glow
            const g=ctx.createRadialGradient(nx,ny,0,nx,ny,nr*5);
            g.addColorStop(0,this.colors[n.key]+'bb'); g.addColorStop(1,'transparent');
            ctx.fillStyle=g; ctx.beginPath(); ctx.arc(nx,ny,nr*5,0,Math.PI*2); ctx.fill();
            // DATA-DRIVEN: brightness/shadowBlur proportional to score
            ctx.fillStyle=this.colors[n.key];
            ctx.shadowBlur=8+(n.score/8); ctx.shadowColor=this.colors[n.key];
            ctx.beginPath(); ctx.arc(nx,ny,nr,0,Math.PI*2); ctx.fill();
            ctx.shadowBlur=0;
            // Label
            const lx=nx+(nx>cx?nr+28:-(nr+28));
            ctx.fillStyle='rgba(255,255,255,0.9)'; ctx.font="700 10px 'JetBrains Mono',monospace";
            ctx.textAlign=nx>cx?'left':'right'; ctx.textBaseline='middle';
            ctx.fillText(`${n.key} ${Math.round(n.score)}`,lx,ny);
        });

        // Triangle connections
        for(let i=0;i<newPositions.length;i++){
            const a=newPositions[i],b=newPositions[(i+1)%newPositions.length];
            ctx.strokeStyle='rgba(255,255,255,0.04)'; ctx.lineWidth=1;
            ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
        }

        // Hover card logic
        if(newHovered && (!this.hoveredNode||newHovered.key!==this.hoveredNode.key)){
            this.hoveredNode=newHovered;
            clearTimeout(this.hoverTimeout);
            this.hoverTimeout=setTimeout(()=>this._showHoverCard(newHovered,newHovered.x,newHovered.y),150);
            this.canvas.style.cursor='pointer';
        } else if(!newHovered && this.hoveredNode){
            this._clearHover();
        }

        // Deformed core (Perlin breathing — DATA-DRIVEN deformation)
        const coreR=24+(score/5);
        const pulse=Math.sin(this.t*(2.5+score/45))*((100-score)/22+1.5);
        ctx.beginPath();
        for(let i=0;i<=64;i++){
            const a=(i/64)*Math.PI*2;
            const nv=this.noise(Math.cos(a),Math.sin(a),this.t)*(9*(1-score/115));
            const r=coreR+pulse+nv;
            i===0?ctx.moveTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r):ctx.lineTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r);
        }
        ctx.closePath();
        const cg=ctx.createRadialGradient(cx,cy,0,cx,cy,coreR+pulse+10);
        cg.addColorStop(0,'#ffffff');
        cg.addColorStop(0.3,score>75?'#dc2626':score>50?'#f97316':'#3b82f6');
        cg.addColorStop(1,'transparent');
        ctx.fillStyle=cg;
        // DATA-DRIVEN: glow intensity proportional to composite score
        ctx.shadowBlur=25+(score/3.5); ctx.shadowColor=score>75?'#dc2626':score>50?'rgba(249,115,22,0.9)':'rgba(59,130,246,0.9)';
        ctx.fill(); ctx.shadowBlur=0;

        // COMPOSITE SCORE — dominant
        const fs=Math.round(20+score/8.5);
        ctx.font=`800 ${fs}px 'JetBrains Mono',monospace`;
        ctx.textAlign='center'; ctx.textBaseline='middle';
        ctx.fillStyle=score>60?'#000':'#fff';
        ctx.fillText(Math.round(score),cx,cy-3);

        // COMPOSITE label above
        ctx.font="500 6px 'JetBrains Mono',monospace";
        ctx.fillStyle=score>60?'rgba(0,0,0,0.5)':'rgba(255,255,255,0.3)';
        ctx.fillText('COMPOSITE',cx,cy-fs*0.7-2);

        // Pattern label below score
        const pattern=this.data?(this.data.composite.pattern||'MONITORING'):'SYNCING';
        ctx.font="600 7px 'JetBrains Mono',monospace";
        ctx.fillStyle=score>60?'rgba(0,0,0,0.6)':'rgba(255,255,255,0.45)';
        ctx.fillText(pattern.toUpperCase(),cx,cy+fs*0.65+4);

        // LIVE indicator bottom center
        const liveStr=!this.data?'CONNECTING':isLive?`LIVE · ${ageSec}s`:'STALE';
        const liveCol=!this.data?'#555':isLive?'#22c55e':'#dc2626';
        ctx.fillStyle=liveCol; ctx.font="600 8px 'JetBrains Mono',monospace";
        ctx.textAlign='center'; ctx.textBaseline='bottom';
        ctx.fillText(liveStr,cx,this.h-8);

        // Metadata bottom-left
        ctx.fillStyle='rgba(255,255,255,0.12)'; ctx.font="500 7px 'JetBrains Mono',monospace";
        ctx.textAlign='left'; ctx.textBaseline='bottom';
        ctx.fillText('SOVEREIGN v1.3',10,this.h-8);

        requestAnimationFrame(()=>this.animate());
    }
}
window.SovereignOrb = SovereignOrb;
