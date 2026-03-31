/**
 * SOVEREIGN ORB V5.1 — 6 NODES + TEXT CLIP FIX
 * MCX EPX IHX OPX FDX OCX — all data-driven
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
        this.trails = {};
        this.smoothed = {composite:50,mcx:50,epx:50,ihx:50,opx:50,fdx:50,ocx:50};
        this.colors = {MCX:'#dc2626',EPX:'#f97316',IHX:'#3b82f6',OPX:'#a855f7',FDX:'#06b6d4',OCX:'#22c55e'};
        this.mouse = {x:-999,y:-999};
        this.hoveredNode = null;
        this.hoverCard = null;
        this.hoverTimeout = null;
        ['mcx','epx','ihx','opx','fdx','ocx'].forEach(k=>this.trails[k]=[]);
        this.resize();
        window.addEventListener('resize',()=>this.resize());
        this.canvas.addEventListener('mousemove',e=>this._onMouse(e));
        this.canvas.addEventListener('mouseleave',()=>{this.mouse={x:-999,y:-999};this._clearHover();});
        this.canvas.addEventListener('click',()=>this._onClick());
        this.fetchData();
        this._buildCard();
        this.animate();
    }

    resize() {
        const w=this.canvas.offsetWidth||520, h=this.canvas.offsetHeight||520;
        const dpr=window.devicePixelRatio||1;
        this.canvas.width=w*dpr; this.canvas.height=h*dpr;
        this.ctx.scale(dpr,dpr);
        this.w=w; this.h=h;
    }

    async fetchData() {
        try {
            const r=await fetch(this.endpoint);
            if(r.ok){this.data=await r.json(); this.lastFetch=Date.now();}
        } catch(e){}
        setTimeout(()=>this.fetchData(),30000);
    }

    _buildCard() {
        const el=document.createElement('div');
        el.id='orb-hover-card';
        el.style.cssText='position:absolute;display:none;pointer-events:none;z-index:100;background:rgba(6,6,6,0.97);border-radius:8px;padding:12px 16px;min-width:190px;max-width:230px;font-family:\'JetBrains Mono\',monospace;box-shadow:0 0 24px rgba(220,38,38,0.2),0 4px 20px rgba(0,0,0,0.8);';
        this.canvas.parentElement.style.position='relative';
        this.canvas.parentElement.appendChild(el);
        this.hoverCard=el;
    }

    _onMouse(e) {
        const r=this.canvas.getBoundingClientRect();
        this.mouse.x=e.clientX-r.left; this.mouse.y=e.clientY-r.top;
    }

    _clearHover() {
        clearTimeout(this.hoverTimeout);
        this.hoveredNode=null;
        if(this.hoverCard) this.hoverCard.style.display='none';
        this.canvas.style.cursor='crosshair';
    }

    _showCard(node) {
        if(!this.hoverCard) return;
        const s=Math.round(node.score);
        const regime=s>70?'EXPANSION':s<35?'SUPPRESSION':'NEUTRAL';
        const col=this.colors[node.key];
        const raw=this.data?this.data.raw:{};
        const descs={
            MCX:'Miner Conviction — hashrate vs price compression. High = miners holding through weakness.',
            EPX:'Exchange Pressure — net flow direction + whale ops. High = coins leaving exchanges.',
            IHX:'Insider Heat — social divergence from price. High = smart money positioned.',
            OPX:'Options Pressure — put/call ratio + implied vol. High = call-side dominance.',
            FDX:'Futures/Derivatives — funding rate + basis. High = bullish futures premium.',
            OCX:'On-Chain Activity — accumulation score + NVT + active addresses. High = strong fundamentals.',
        };
        const extras={
            MCX:`Diff adj: ${raw.next_adj_pct>0?'+':''}${(raw.next_adj_pct||0).toFixed(2)}%`,
            EPX:`Whale txs: ${raw.whale_alerts||0} recent`,
            IHX:`Polymarket: ${(raw.poly_prob||0).toFixed(1)}% — ${(raw.poly_top||'').slice(0,30)}`,
            OPX:`P/C ratio: ${(raw.put_call_ratio||0).toFixed(3)} · DVOL: ${raw.dvol||0} · Max pain: $${(raw.options_max_pain||0).toLocaleString()}`,
            FDX:`Funding: ${((raw.funding_rate||0)*100).toFixed(4)}% · Basis: ${(raw.basis_pct||0).toFixed(2)}%`,
            OCX:`Accum score: ${raw.accumulation_score||0} · NVT: ${raw.nvt_ratio||0} · LN: ${raw.lightning_btc||0} BTC`,
        };
        const isCmd=document.body.dataset.userTier==='commander';
        this.hoverCard.style.borderColor=col;
        this.hoverCard.style.boxShadow=`0 0 24px ${col}33,0 4px 20px rgba(0,0,0,0.8)`;
        this.hoverCard.innerHTML=`
<div style="color:${col};font-size:0.55rem;letter-spacing:0.18em;margin-bottom:6px;">${node.key} — ${descs[node.key].split('—')[0].trim()}</div>
<div style="font-size:1.8rem;font-weight:800;color:#fff;line-height:1;margin-bottom:4px;">${s}</div>
<div style="font-size:0.6rem;color:${s>70?'#22c55e':s<35?'#dc2626':'#888'};letter-spacing:0.12em;margin-bottom:8px;">${regime}</div>
<div style="font-size:0.62rem;color:rgba(255,255,255,0.45);line-height:1.5;border-top:1px solid rgba(255,255,255,0.08);padding-top:8px;margin-bottom:8px;">${descs[node.key]}</div>
<div style="font-size:0.58rem;color:rgba(255,255,255,0.3);line-height:1.6;">${extras[node.key]}</div>
${!isCmd?`<div style="margin-top:8px;padding-top:8px;border-top:1px solid ${col}33;font-size:0.58rem;color:${col}99;cursor:pointer;" onclick="window.location='/commander'">🔒 FORENSIC AUDIT — COMMANDER</div>`:''}`;
        // Position card — keep inside canvas bounds
        const cx=node.x, cy=node.y;
        const cw=230, ch=180;
        let lx=cx+24, ly=cy-60;
        if(lx+cw>this.w-10) lx=cx-cw-24;
        if(ly<10) ly=10;
        if(ly+ch>this.h-10) ly=this.h-ch-10;
        this.hoverCard.style.left=lx+'px';
        this.hoverCard.style.top=ly+'px';
        this.hoverCard.style.display='block';
    }

    _onClick() {
        if(!this.hoveredNode) return;
        window.location=document.body.dataset.userTier==='commander'?`/commander?signal=${this.hoveredNode.key.toLowerCase()}`:`/commander`;
    }

    lerp(a,b,t){return a+(b-a)*t;}
    noise(x,y,t){return Math.sin(x*2.1+t*1.3)*Math.cos(y*1.7+t*0.9)*0.5+Math.sin(x*3.7+t*0.7)*Math.sin(y*2.9+t*1.1)*0.3+Math.cos(x*1.3+y*2.1+t*0.5)*0.2;}

    animate() {
        this.t+=0.006;
        const ctx=this.ctx, cx=this.w/2, cy=this.h/2;
        const sp=0.025;
        if(this.data) {
            const n=this.data.nodes;
            this.smoothed.composite=this.lerp(this.smoothed.composite,this.data.composite.score,sp);
            ['mcx','epx','ihx','opx','fdx','ocx'].forEach(k=>{
                if(n[k]) this.smoothed[k]=this.lerp(this.smoothed[k],n[k].score,sp);
            });
        }
        const score=this.smoothed.composite;
        const ageSec=this.data?Math.round((Date.now()-this.lastFetch)/1000):0;
        const isLive=this.data&&ageSec<120;

        // BG + scanlines
        ctx.fillStyle='#060606'; ctx.fillRect(0,0,this.w,this.h);
        ctx.fillStyle='rgba(255,255,255,0.015)';
        for(let i=0;i<this.h;i+=3) ctx.fillRect(0,i,this.w,1);

        // Radial grid — inset to leave room for labels
        const maxR=Math.min(cx,cy)*0.72;
        [0.2,0.35,0.5,0.65,0.8,0.95].forEach((f,i)=>{
            ctx.strokeStyle=`rgba(220,38,38,${0.03+i*0.007})`;
            ctx.lineWidth=0.5; ctx.setLineDash([]);
            ctx.beginPath(); ctx.arc(cx,cy,maxR*f,0,Math.PI*2); ctx.stroke();
        });
        // Radial ticks 30deg
        for(let a=0;a<Math.PI*2;a+=Math.PI/6){
            const r1=maxR*0.95, r2=r1-8;
            ctx.strokeStyle='rgba(220,38,38,0.07)'; ctx.lineWidth=0.5;
            ctx.beginPath(); ctx.moveTo(cx+Math.cos(a)*r1,cy+Math.sin(a)*r1); ctx.lineTo(cx+Math.cos(a)*r2,cy+Math.sin(a)*r2); ctx.stroke();
        }
        ctx.strokeStyle='rgba(220,38,38,0.05)'; ctx.lineWidth=0.5;
        ctx.beginPath(); ctx.moveTo(cx,cy-maxR); ctx.lineTo(cx,cy+maxR); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(cx-maxR,cy); ctx.lineTo(cx+maxR,cy); ctx.stroke();

        // Perimeter signal ring — at 92% of maxR
        const ringR=maxR*0.92;
        ctx.strokeStyle=`rgba(220,38,38,${0.07+score/1200})`; ctx.lineWidth=1;
        ctx.setLineDash([3,7]); ctx.beginPath(); ctx.arc(cx,cy,ringR,0,Math.PI*2); ctx.stroke();
        ctx.setLineDash([]);

        // Perimeter labels — 8 streams, evenly spaced, clipped to canvas
        const streams=this.data?[
            {l:'HASH',v:this.data.streams.hashrate,a:-Math.PI/2},
            {l:'F&G', v:this.data.streams.fear_greed,a:-Math.PI*5/12},
            {l:'OI',  v:Math.min(100,this.data.streams.kol+10),a:-Math.PI/6},
            {l:'POLY',v:this.data.streams.polymarket,a:Math.PI/12},
            {l:'FEES',v:this.data.streams.fees,a:Math.PI/3},
            {l:'WHALE',v:this.data.streams.whale,a:7*Math.PI/12},
            {l:'ACCUM',v:this.data.streams.accum,a:5*Math.PI/6},
            {l:'CORR',v:this.data.streams.macro_corr,a:-3*Math.PI/4},
        ]:[];
        streams.forEach(s=>{
            const dist=ringR+18;
            // Clamp to avoid edge clipping
            const rawX=cx+Math.cos(s.a)*dist, rawY=cy+Math.sin(s.a)*dist;
            const tx=Math.max(30,Math.min(this.w-30,rawX));
            const ty=Math.max(14,Math.min(this.h-20,rawY));
            const col=s.v>65?'#22c55e':s.v<35?'#dc2626':'#555';
            ctx.strokeStyle=col+'55'; ctx.lineWidth=1;
            ctx.beginPath();
            ctx.moveTo(cx+Math.cos(s.a)*ringR,cy+Math.sin(s.a)*ringR);
            ctx.lineTo(cx+Math.cos(s.a)*(ringR-10),cy+Math.sin(s.a)*(ringR-10));
            ctx.stroke();
            ctx.fillStyle=col; ctx.font="700 8px 'JetBrains Mono',monospace";
            ctx.textAlign='center'; ctx.textBaseline='middle';
            ctx.fillText(`${s.l} ${Math.round(s.v)}`,tx,ty);
        });

        // 6 orbital nodes
        const nodeDefs=[
            {key:'MCX',sk:'mcx',offset:0},
            {key:'EPX',sk:'epx',offset:Math.PI/3},
            {key:'IHX',sk:'ihx',offset:2*Math.PI/3},
            {key:'OPX',sk:'opx',offset:Math.PI},
            {key:'FDX',sk:'fdx',offset:4*Math.PI/3},
            {key:'OCX',sk:'ocx',offset:5*Math.PI/3},
        ];
        const positions=[];
        let newHovered=null;

        nodeDefs.forEach(n=>{
            const nscore=this.smoothed[n.sk];
            // Data-driven orbit: high score = closer to center
            const orbitR=maxR*0.65*(1-(nscore-15)/160);
            const spd=0.12+(nscore/700);
            const ang=this.t*spd+n.offset;
            const nx=cx+Math.cos(ang)*orbitR, ny=cy+Math.sin(ang)*orbitR;
            positions.push({x:nx,y:ny,key:n.key,score:nscore});

            // Proximity hover
            const dx=this.mouse.x-nx, dy=this.mouse.y-ny;
            if(Math.sqrt(dx*dx+dy*dy)<26) newHovered={key:n.key,score:nscore,x:nx,y:ny};

            // Trail
            const trail=this.trails[n.sk];
            trail.push({x:nx,y:ny}); if(trail.length>22) trail.shift();
            ctx.lineWidth=1.2;
            trail.forEach((p,i)=>{
                if(!i) return;
                ctx.globalAlpha=(i/trail.length)*0.3;
                ctx.strokeStyle=this.colors[n.key];
                ctx.beginPath(); ctx.moveTo(trail[i-1].x,trail[i-1].y); ctx.lineTo(p.x,p.y); ctx.stroke();
            });
            ctx.globalAlpha=1;

            // Signal line center→node
            ctx.strokeStyle=this.colors[n.key]+'18'; ctx.lineWidth=1;
            ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(nx,ny); ctx.stroke();

            // Glow + dot
            const nr=3+(nscore/30);
            const g=ctx.createRadialGradient(nx,ny,0,nx,ny,nr*4.5);
            g.addColorStop(0,this.colors[n.key]+'aa'); g.addColorStop(1,'transparent');
            ctx.fillStyle=g; ctx.beginPath(); ctx.arc(nx,ny,nr*4.5,0,Math.PI*2); ctx.fill();
            ctx.fillStyle=this.colors[n.key];
            ctx.shadowBlur=8+(nscore/9); ctx.shadowColor=this.colors[n.key];
            ctx.beginPath(); ctx.arc(nx,ny,nr,0,Math.PI*2); ctx.fill();
            ctx.shadowBlur=0;

            // Label — clamped inside canvas, avoid signal ring
            const lRaw=nx+(nx>cx?nr+26:-(nr+26));
            const lx=Math.max(28,Math.min(this.w-28,lRaw));
            const ly=Math.max(14,Math.min(this.h-28,ny));
            ctx.fillStyle='rgba(255,255,255,0.88)'; ctx.font="700 9px 'JetBrains Mono',monospace";
            ctx.textAlign=nx>cx?'left':'right'; ctx.textBaseline='middle';
            ctx.fillText(`${n.key} ${Math.round(nscore)}`,lx,ly);
        });

        // Hexagonal connections between adjacent nodes
        for(let i=0;i<positions.length;i++){
            const a=positions[i],b=positions[(i+1)%positions.length];
            ctx.strokeStyle='rgba(255,255,255,0.03)'; ctx.lineWidth=1;
            ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
        }

        // Hover card logic
        if(newHovered&&(!this.hoveredNode||newHovered.key!==this.hoveredNode.key)){
            this.hoveredNode=newHovered;
            clearTimeout(this.hoverTimeout);
            this.hoverTimeout=setTimeout(()=>this._showCard(newHovered),150);
            this.canvas.style.cursor='pointer';
        } else if(!newHovered&&this.hoveredNode){
            this._clearHover();
        }

        // Deformed breathing core
        const coreR=22+(score/5.5);
        const pulse=Math.sin(this.t*(2.5+score/45))*((100-score)/22+1.5);
        ctx.beginPath();
        for(let i=0;i<=64;i++){
            const a=(i/64)*Math.PI*2;
            const nv=this.noise(Math.cos(a),Math.sin(a),this.t)*(8*(1-score/115));
            const r=coreR+pulse+nv;
            i===0?ctx.moveTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r):ctx.lineTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r);
        }
        ctx.closePath();
        const cg=ctx.createRadialGradient(cx,cy,0,cx,cy,coreR+pulse+10);
        cg.addColorStop(0,'#ffffff');
        cg.addColorStop(0.3,score>75?'#dc2626':score>50?'#f97316':'#3b82f6');
        cg.addColorStop(1,'transparent');
        ctx.fillStyle=cg;
        ctx.shadowBlur=22+(score/3.8); ctx.shadowColor=score>75?'#dc2626':score>50?'rgba(249,115,22,0.9)':'rgba(59,130,246,0.9)';
        ctx.fill(); ctx.shadowBlur=0;

        // Core readout
        const fs=Math.round(18+score/9);
        ctx.font=`800 ${fs}px 'JetBrains Mono',monospace`;
        ctx.textAlign='center'; ctx.textBaseline='middle';
        ctx.fillStyle=score>60?'#000':'#fff';
        ctx.fillText(Math.round(score),cx,cy-2);
        ctx.font="500 6px 'JetBrains Mono',monospace";
        ctx.fillStyle=score>60?'rgba(0,0,0,0.45)':'rgba(255,255,255,0.25)';
        ctx.fillText('COMPOSITE',cx,cy-fs*0.72);
        const pat=this.data?(this.data.composite.pattern||'MONITORING'):'SYNCING';
        ctx.font="600 7px 'JetBrains Mono',monospace";
        ctx.fillStyle=score>60?'rgba(0,0,0,0.55)':'rgba(255,255,255,0.4)';
        ctx.fillText(pat.toUpperCase(),cx,cy+fs*0.65+4);

        // LIVE — clamped above bottom
        const liveStr=!this.data?'CONNECTING':isLive?`LIVE · ${ageSec}s`:'STALE';
        const liveCol=!this.data?'#555':isLive?'#22c55e':'#dc2626';
        ctx.fillStyle=liveCol; ctx.font="600 8px 'JetBrains Mono',monospace";
        ctx.textAlign='center'; ctx.textBaseline='bottom';
        ctx.fillText(liveStr,cx,this.h-6);
        ctx.fillStyle='rgba(255,255,255,0.1)'; ctx.font="500 7px 'JetBrains Mono',monospace";
        ctx.textAlign='left'; ctx.fillText('SOVEREIGN v1.3',8,this.h-6);

        requestAnimationFrame(()=>this.animate());
    }
}
window.SovereignOrb=SovereignOrb;
