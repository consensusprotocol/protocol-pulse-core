/**
 * SOVEREIGN ORB V5.2 — DECISION ENGINE
 * Two-tier hierarchy: Primary (MCX/EPX/IHX) vs Secondary (OPX/FDX/OCX)
 * Direction arrows, system conclusion, gravity well physics
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
        this.prev = {};
        this.smoothed = {composite:50,mcx:50,epx:50,ihx:50,opx:50,fdx:50,ocx:50};
        this.colors = {MCX:'#dc2626',EPX:'#f97316',IHX:'#3b82f6',OPX:'#a855f7',FDX:'#06b6d4',OCX:'#22c55e'};
        this.mouse = {x:-999,y:-999};
        this.hoveredNode = null;
        this.hoverCard = null;
        this.hoverTimeout = null;
        ['mcx','epx','ihx','opx','fdx','ocx'].forEach(k=>{this.trails[k]=[];this.prev[k]=50;});
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
        const dpr=window.devicePixelRatio||1;
        // If canvas already has explicit pixel dimensions, use them
        const w = this.canvas.offsetWidth || (this.canvas.width/dpr) || 680;
        const h = this.canvas.offsetHeight || (this.canvas.height/dpr) || 680;
        this.canvas.width=Math.round(w*dpr);
        this.canvas.height=Math.round(h*dpr);
        this.ctx.scale(dpr,dpr);
        this.w=w;this.h=h;
    }

    async fetchData() {
        try {
            const r=await fetch(this.endpoint);
            if(r.ok){
                const d=await r.json();
                // Store prev for direction arrows
                ['mcx','epx','ihx','opx','fdx','ocx'].forEach(k=>{
                    if(this.data&&this.data.nodes[k]) this.prev[k]=this.data.nodes[k].score;
                });
                this.data=d; this.lastFetch=Date.now();
            }
        } catch(e){}
        setTimeout(()=>this.fetchData(),30000);
    }

    _dir(key) {
        if(!this.data||!this.data.nodes[key]) return '→';
        const cur=this.data.nodes[key].score, prev=this.prev[key];
        const diff=cur-prev;
        return diff>2?'↑':diff<-2?'↓':'→';
    }

    _conclusion() {
        if(!this.data) return 'Initializing sovereign intelligence...';
        const n=this.data.nodes;
        const mcx=n.mcx?n.mcx.score:50, epx=n.epx?n.epx.score:50;
        const ihx=n.ihx?n.ihx.score:50, ocx=n.ocx?n.ocx.score:50;
        const opx=n.opx?n.opx.score:50, fdx=n.fdx?n.fdx.score:50;
        const score=this.data.composite.score;
        if(mcx>75&&ocx>65) return 'Miners & on-chain aligning — supply shock building';
        if(mcx>75&&epx<40) return 'Strong miner conviction, exchange pressure neutral';
        if(opx<35&&fdx<40) return 'Derivatives cooling — spot market leading price';
        if(score>70) return 'Multi-signal convergence — high conviction state';
        if(score<35) return 'Broad divergence — protocol uncertainty elevated';
        if(epx>65) return 'Exchange outflows accelerating — accumulation bias';
        if(ihx>65) return 'Social diverging from price — watch for reversal';
        return 'Mixed signals — monitoring for directional catalyst';
    }

    _buildCard() {
        const el=document.createElement('div');
        el.id='orb-hover-card';
        el.style.cssText="position:absolute;display:none;pointer-events:none;z-index:100;background:rgba(4,4,4,0.97);border:1px solid #dc2626;border-radius:8px;padding:12px 16px;min-width:195px;max-width:235px;font-family:'JetBrains Mono',monospace;box-shadow:0 0 28px rgba(220,38,38,0.15),0 4px 24px rgba(0,0,0,0.9);";
        this.canvas.parentElement.style.position='relative';
        this.canvas.parentElement.appendChild(el);
        this.hoverCard=el;
    }

    _onMouse(e) {
        const r=this.canvas.getBoundingClientRect();
        this.mouse.x=e.clientX-r.left;this.mouse.y=e.clientY-r.top;
    }

    _clearHover() {
        clearTimeout(this.hoverTimeout);this.hoveredNode=null;
        if(this.hoverCard) this.hoverCard.style.display='none';
        this.canvas.style.cursor='crosshair';
    }

    _showCard(node) {
        if(!this.hoverCard||!this.data) return;
        const s=Math.round(node.score),col=this.colors[node.key];
        const dir=this._dir(node.key.toLowerCase());
        const regime=s>70?'EXPANSION':s<35?'SUPPRESSION':'NEUTRAL';
        const raw=this.data.raw||{};
        const tiers={MCX:'PRIMARY · SUPPLY',EPX:'PRIMARY · FLOW',IHX:'PRIMARY · SENTIMENT',OPX:'SECONDARY · DERIVATIVES',FDX:'SECONDARY · FUTURES',OCX:'SECONDARY · ON-CHAIN'};
        const descs={
            MCX:'Miner conviction — hashrate resilience vs price. High = miners absorbing sell pressure.',
            EPX:'Exchange pressure — net flow + whale operations. High = coins leaving exchanges.',
            IHX:'Insider heat — smart money divergence from narrative. High = informed positioning.',
            OPX:'Options pressure — put/call skew + implied vol. High = call-side dominance.',
            FDX:'Futures basis — funding rate + annualized premium. High = bullish futures structure.',
            OCX:'On-chain accumulation — NVT ratio + active addresses + coin days. High = strong fundamentals.',
        };
        const extras={
            MCX:`Next diff adj: ${(raw.next_adj_pct||0)>0?'+':''}${(raw.next_adj_pct||0).toFixed(2)}% in ~${Math.round((raw.next_adj_pct||0)*2)} days`,
            EPX:`Whale txs detected: ${raw.whale_alerts||0} · Flow: ${(this.data.streams||{}).exchange_flow>60?'OUTFLOW':'NEUTRAL'}`,
            IHX:`Polymarket: ${(raw.poly_prob||0).toFixed(1)}% — ${(raw.polymarket_top||'').slice(0,28)}...`,
            OPX:`P/C: ${(raw.put_call_ratio||0).toFixed(3)} · DVOL: ${raw.dvol||0} · Max pain: $${((raw.options_max_pain||0)/1000).toFixed(0)}k`,
            FDX:`Funding: ${((raw.funding_rate||0)*100).toFixed(4)}% · Basis: ${(raw.basis_pct||0).toFixed(2)}% annualized`,
            OCX:`Accum: ${raw.accumulation_score||0}/100 · NVT: ${raw.nvt_ratio||0} · LN cap: ${(raw.lightning_btc||0).toFixed(0)} BTC`,
        };
        const isCmd=document.body.dataset.userTier==='commander';
        this.hoverCard.style.borderColor=col;
        this.hoverCard.innerHTML=`
<div style="color:${col};font-size:0.52rem;letter-spacing:0.18em;margin-bottom:5px;">${tiers[node.key]}</div>
<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:4px;">
  <span style="font-size:1.9rem;font-weight:800;color:#fff;line-height:1;">${s}</span>
  <span style="font-size:1rem;color:${dir==='↑'?'#22c55e':dir==='↓'?'#dc2626':'#666'};font-weight:700;">${dir}</span>
</div>
<div style="font-size:0.58rem;color:${s>70?'#22c55e':s<35?'#dc2626':'#777'};letter-spacing:0.12em;margin-bottom:8px;">${regime}</div>
<div style="font-size:0.6rem;color:rgba(255,255,255,0.4);line-height:1.55;border-top:1px solid rgba(255,255,255,0.07);padding-top:8px;margin-bottom:6px;">${descs[node.key]}</div>
<div style="font-size:0.57rem;color:${col}99;line-height:1.6;">${extras[node.key]}</div>
${!isCmd?`<div style="margin-top:8px;padding-top:8px;border-top:1px solid ${col}22;font-size:0.57rem;color:${col}77;cursor:pointer;" onclick="window.location='/commander'">🔒 FORENSIC AUDIT — COMMANDER ONLY</div>`:''}`;
        // Smart positioning — flip if near edge
        const cw=235,ch=200;
        let lx=node.x+28,ly=node.y-70;
        if(lx+cw>this.w-8) lx=node.x-cw-28;
        if(lx<8) lx=8;
        if(ly<8) ly=8;
        if(ly+ch>this.h-8) ly=this.h-ch-8;
        this.hoverCard.style.left=lx+'px';this.hoverCard.style.top=ly+'px';
        this.hoverCard.style.display='block';
    }

    _onClick() {
        if(!this.hoveredNode) return;
        window.location=document.body.dataset.userTier==='commander'?`/commander?signal=${this.hoveredNode.key.toLowerCase()}`:'/commander';
    }

    lerp(a,b,t){return a+(b-a)*t;}
    noise(x,y,t){return Math.sin(x*2.1+t*1.3)*Math.cos(y*1.7+t*0.9)*0.5+Math.sin(x*3.7+t*0.7)*Math.sin(y*2.9+t*1.1)*0.3+Math.cos(x*1.3+y*2.1+t*0.5)*0.2;}

    animate() {
        this.t+=0.006;
        const ctx=this.ctx,cx=this.w/2,cy=this.h/2;
        if(this.data){
            const sp=0.025,n=this.data.nodes;
            this.smoothed.composite=this.lerp(this.smoothed.composite,this.data.composite.score,sp);
            ['mcx','epx','ihx','opx','fdx','ocx'].forEach(k=>{
                if(n[k]) this.smoothed[k]=this.lerp(this.smoothed[k],n[k].score,sp);
            });
        }
        const score=this.smoothed.composite;
        const ageSec=this.data?Math.round((Date.now()-this.lastFetch)/1000):0;
        const isLive=this.data&&ageSec<120;

        // BG + scanlines
        ctx.fillStyle='#060606';ctx.fillRect(0,0,this.w,this.h);
        ctx.fillStyle='rgba(255,255,255,0.013)';
        for(let i=0;i<this.h;i+=3) ctx.fillRect(0,i,this.w,1);

        // Grid — leave 52px margin for labels
        const margin=52,maxR=Math.min(cx,cy)-margin;
        [0.22,0.38,0.55,0.72,0.88,1.0].forEach((f,i)=>{
            ctx.strokeStyle=`rgba(220,38,38,${0.025+i*0.006})`;
            ctx.lineWidth=0.5;ctx.setLineDash([]);
            ctx.beginPath();ctx.arc(cx,cy,maxR*f,0,Math.PI*2);ctx.stroke();
        });
        for(let a=0;a<Math.PI*2;a+=Math.PI/6){
            ctx.strokeStyle='rgba(220,38,38,0.06)';ctx.lineWidth=0.5;
            ctx.beginPath();ctx.moveTo(cx+Math.cos(a)*maxR*0.88,cy+Math.sin(a)*maxR*0.88);
            ctx.lineTo(cx+Math.cos(a)*(maxR*0.88-9),cy+Math.sin(a)*(maxR*0.88-9));ctx.stroke();
        }
        ctx.strokeStyle='rgba(220,38,38,0.04)';ctx.lineWidth=0.5;
        ctx.beginPath();ctx.moveTo(cx,cy-maxR);ctx.lineTo(cx,cy+maxR);ctx.stroke();
        ctx.beginPath();ctx.moveTo(cx-maxR,cy);ctx.lineTo(cx+maxR,cy);ctx.stroke();

        // Perimeter ring — dimmed (sensor layer)
        const ringR=maxR*0.9;
        ctx.strokeStyle=`rgba(220,38,38,0.06)`;ctx.lineWidth=1;
        ctx.setLineDash([2,8]);ctx.beginPath();ctx.arc(cx,cy,ringR,0,Math.PI*2);ctx.stroke();
        ctx.setLineDash([]);

        // 8 perimeter streams — dimmed, small font, sensor layer
        const streams=this.data?[
            {l:'HASH',v:this.data.streams.hashrate,a:-Math.PI/2},
            {l:'F&G', v:this.data.streams.fear_greed,a:-Math.PI*5/12},
            {l:'POLY',v:this.data.streams.polymarket||50,a:-Math.PI/6},
            {l:'FEES',v:this.data.streams.fees,a:Math.PI/12},
            {l:'FLOW',v:this.data.streams.exchange_flow,a:Math.PI/3},
            {l:'WHALE',v:this.data.streams.whale||50,a:7*Math.PI/12},
            {l:'ACCUM',v:this.data.streams.accum||50,a:5*Math.PI/6},
            {l:'CORR',v:this.data.streams.macro_corr||50,a:-3*Math.PI/4},
        ]:[];
        streams.forEach(s=>{
            const dist=ringR+16;
            const rawX=cx+Math.cos(s.a)*dist,rawY=cy+Math.sin(s.a)*dist;
            const tx=Math.max(28,Math.min(this.w-28,rawX));
            const ty=Math.max(12,Math.min(this.h-16,rawY));
            const col=s.v>65?'#22c55e44':s.v<35?'#dc262644':'#33333388';
            ctx.fillStyle=col;ctx.font="600 7px 'JetBrains Mono',monospace";
            ctx.textAlign='center';ctx.textBaseline='middle';
            ctx.fillText(`${s.l} ${Math.round(s.v)}`,tx,ty);
        });

        // ── TIER 2 NODES (OPX, FDX, OCX) — secondary, outer, dimmer ──
        const tier2=[
            {key:'OPX',sk:'opx',offset:Math.PI/6},
            {key:'FDX',sk:'fdx',offset:Math.PI*5/6},
            {key:'OCX',sk:'ocx',offset:Math.PI*3/2},
        ];
        const t2positions=[];
        tier2.forEach(n=>{
            const ns=this.smoothed[n.sk];
            // Secondary orbit — further from center, smaller
            const orbitR=maxR*0.72*(1-(ns-20)/180);
            const spd=0.08+(ns/900);
            const ang=this.t*spd+n.offset;
            const nx=cx+Math.cos(ang)*orbitR,ny=cy+Math.sin(ang)*orbitR;
            t2positions.push({x:nx,y:ny,key:n.key,score:ns});

            // Proximity
            const dx=this.mouse.x-nx,dy=this.mouse.y-ny;
            // Trail (faint)
            const trail=this.trails[n.sk];
            trail.push({x:nx,y:ny});if(trail.length>15) trail.shift();
            ctx.lineWidth=0.8;
            trail.forEach((p,i)=>{
                if(!i) return;
                ctx.globalAlpha=(i/trail.length)*0.15;
                ctx.strokeStyle=this.colors[n.key];
                ctx.beginPath();ctx.moveTo(trail[i-1].x,trail[i-1].y);ctx.lineTo(p.x,p.y);ctx.stroke();
            });
            ctx.globalAlpha=1;
            // Signal line (very faint)
            ctx.strokeStyle=this.colors[n.key]+'0d';ctx.lineWidth=0.5;
            ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(nx,ny);ctx.stroke();
            // Node (smaller, dimmer)
            const nr=2+(ns/40);
            const g=ctx.createRadialGradient(nx,ny,0,nx,ny,nr*3.5);
            g.addColorStop(0,this.colors[n.key]+'55');g.addColorStop(1,'transparent');
            ctx.fillStyle=g;ctx.beginPath();ctx.arc(nx,ny,nr*3.5,0,Math.PI*2);ctx.fill();
            ctx.fillStyle=this.colors[n.key]+'99';
            ctx.shadowBlur=4+(ns/20);ctx.shadowColor=this.colors[n.key];
            ctx.beginPath();ctx.arc(nx,ny,nr,0,Math.PI*2);ctx.fill();
            ctx.shadowBlur=0;
            // Label — small, muted
            const dir=this._dir(n.sk);
            const lx=Math.max(24,Math.min(this.w-24,nx+(nx>cx?nr+22:-(nr+22))));
            const ly=Math.max(12,Math.min(this.h-16,ny));
            ctx.fillStyle=this.colors[n.key]+'88';ctx.font="600 8px 'JetBrains Mono',monospace";
            ctx.textAlign=nx>cx?'left':'right';ctx.textBaseline='middle';
            ctx.fillText(`${n.key} ${Math.round(ns)} ${dir}`,lx,ly);
        });

        // ── TIER 1 NODES (MCX, EPX, IHX) — primary, inner, dominant ──
        const tier1=[
            {key:'MCX',sk:'mcx',offset:0},
            {key:'EPX',sk:'epx',offset:2*Math.PI/3},
            {key:'IHX',sk:'ihx',offset:4*Math.PI/3},
        ];
        const t1positions=[];
        let newHovered=null;
        tier1.forEach(n=>{
            const ns=this.smoothed[n.sk];
            // Primary orbit — closer, bigger, brighter
            const orbitR=maxR*0.52*(1-(ns-15)/155);
            const spd=0.18+(ns/500);
            const ang=this.t*spd+n.offset;
            const nx=cx+Math.cos(ang)*orbitR,ny=cy+Math.sin(ang)*orbitR;
            t1positions.push({x:nx,y:ny,key:n.key,score:ns});

            // Proximity for hover
            const dx=this.mouse.x-nx,dy=this.mouse.y-ny;
            if(Math.sqrt(dx*dx+dy*dy)<30) newHovered={key:n.key,score:ns,x:nx,y:ny};

            // Check t2 proximity too
            t2positions.forEach(p=>{
                const dx2=this.mouse.x-p.x,dy2=this.mouse.y-p.y;
                if(Math.sqrt(dx2*dx2+dy2*dy2)<24&&!newHovered) newHovered={key:p.key,score:p.score,x:p.x,y:p.y};
            });

            // Trail (stronger)
            const trail=this.trails[n.sk];
            trail.push({x:nx,y:ny});if(trail.length>28) trail.shift();
            ctx.lineWidth=1.5;
            trail.forEach((p,i)=>{
                if(!i) return;
                ctx.globalAlpha=(i/trail.length)*0.38;
                ctx.strokeStyle=this.colors[n.key];
                ctx.beginPath();ctx.moveTo(trail[i-1].x,trail[i-1].y);ctx.lineTo(p.x,p.y);ctx.stroke();
            });
            ctx.globalAlpha=1;
            // Signal line center→node
            ctx.strokeStyle=this.colors[n.key]+'22';ctx.lineWidth=1;
            ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(nx,ny);ctx.stroke();
            // Glow (data-driven intensity)
            const nr=4+(ns/22);
            const g=ctx.createRadialGradient(nx,ny,0,nx,ny,nr*5);
            g.addColorStop(0,this.colors[n.key]+'cc');g.addColorStop(1,'transparent');
            ctx.fillStyle=g;ctx.beginPath();ctx.arc(nx,ny,nr*5,0,Math.PI*2);ctx.fill();
            ctx.fillStyle=this.colors[n.key];
            ctx.shadowBlur=10+(ns/7);ctx.shadowColor=this.colors[n.key];
            ctx.beginPath();ctx.arc(nx,ny,nr,0,Math.PI*2);ctx.fill();
            ctx.shadowBlur=0;
            // Label — bold, full opacity, with direction arrow
            const dir=this._dir(n.sk);
            const dirCol=dir==='↑'?'#22c55e':dir==='↓'?'#dc2626':'#666';
            const lx=Math.max(28,Math.min(this.w-28,nx+(nx>cx?nr+26:-(nr+26))));
            const ly=Math.max(14,Math.min(this.h-18,ny));
            ctx.fillStyle='#fff';ctx.font="700 10px 'JetBrains Mono',monospace";
            ctx.textAlign=nx>cx?'left':'right';ctx.textBaseline='middle';
            ctx.fillText(`${n.key} ${Math.round(ns)}`,lx,ly);
            // Direction arrow separately in color
            const tw=ctx.measureText(`${n.key} ${Math.round(ns)}`).width;
            ctx.fillStyle=dirCol;ctx.font="700 10px 'JetBrains Mono',monospace";
            if(nx>cx) ctx.fillText(` ${dir}`,lx+tw,ly);
            else {
                ctx.textAlign='right';
                ctx.fillText(`${dir} `,lx-tw,ly);
            }
        });

        // Triangle T1 connections
        for(let i=0;i<t1positions.length;i++){
            const a=t1positions[i],b=t1positions[(i+1)%t1positions.length];
            ctx.strokeStyle='rgba(255,255,255,0.06)';ctx.lineWidth=1;
            ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
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

        // Deformed core
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
        ctx.shadowBlur=22+(score/3.8);
        ctx.shadowColor=score>75?'#dc2626':score>50?'rgba(249,115,22,0.9)':'rgba(59,130,246,0.9)';
        ctx.fill();ctx.shadowBlur=0;

        // Core readout
        const fs=Math.round(18+score/9);
        ctx.font=`800 ${fs}px 'JetBrains Mono',monospace`;
        ctx.textAlign='center';ctx.textBaseline='middle';
        ctx.fillStyle=score>60?'#000':'#fff';
        ctx.fillText(Math.round(score),cx,cy-2);
        ctx.font="500 6px 'JetBrains Mono',monospace";
        ctx.fillStyle=score>60?'rgba(0,0,0,0.4)':'rgba(255,255,255,0.22)';
        ctx.fillText('COMPOSITE',cx,cy-fs*0.72);
        const pat=this.data?(this.data.composite.pattern||'MONITORING'):'SYNCING';
        ctx.font="600 7px 'JetBrains Mono',monospace";
        ctx.fillStyle=score>60?'rgba(0,0,0,0.5)':'rgba(255,255,255,0.38)';
        ctx.fillText(pat.toUpperCase(),cx,cy+fs*0.65+4);

        // SYSTEM CONCLUSION — one line below core
        const conclusion=this._conclusion();
        const maxW=maxR*1.4;
        ctx.font="500 8px 'JetBrains Mono',monospace";
        ctx.fillStyle='rgba(255,255,255,0.28)';
        ctx.textAlign='center';ctx.textBaseline='top';
        const conclusionY=cy+coreR+pulse+22;
        // Word wrap if needed
        const words=conclusion.split(' ');
        let line='',lines2=[];
        words.forEach(w=>{
            const test=line+w+' ';
            if(ctx.measureText(test).width>maxW&&line){lines2.push(line.trim());line=w+' ';}
            else line=test;
        });
        if(line) lines2.push(line.trim());
        lines2.forEach((l,i)=>ctx.fillText(l,cx,conclusionY+i*11));

        // LIVE bottom
        const liveStr=!this.data?'CONNECTING':isLive?`LIVE · ${ageSec}s`:'STALE';
        const liveCol=!this.data?'#444':isLive?'#22c55e':'#dc2626';
        ctx.fillStyle=liveCol;ctx.font="600 8px 'JetBrains Mono',monospace";
        ctx.textAlign='center';ctx.textBaseline='bottom';
        ctx.fillText(liveStr,cx,this.h-6);
        ctx.fillStyle='rgba(255,255,255,0.1)';ctx.font="500 7px 'JetBrains Mono',monospace";
        ctx.textAlign='left';ctx.fillText('SOVEREIGN v1.3',8,this.h-6);

        requestAnimationFrame(()=>this.animate());
    }
}
window.SovereignOrb=SovereignOrb;
