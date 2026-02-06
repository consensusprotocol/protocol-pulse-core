/**
 * Sovereign Gravity Well - Luminous Monolith Edition
 * A massive glowing holographic ₿ with centripetal attraction physics
 */

class SovereignGravityWell {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.dpr = window.devicePixelRatio || 1;
        
        this.blocks = [];
        this.maxBlocks = 50;
        this.spawnRate = 800;
        this.sovereignMode = false;
        
        this.primaryColor = '#dc2626';
        this.purpleColor = '#a855f7';
        
        this.mouseX = 0;
        this.mouseY = 0;
        this.hoveredBlock = null;
        
        this.chromatic = { active: false, intensity: 0 };
        this.shockwave = { active: false, x: 0, y: 0, radius: 0, maxRadius: 0 };
        
        this.mempoolData = {
            feeRate: 15,
            txCount: 45000,
            blockHeight: 880000
        };
        
        this.noiseCanvas = document.createElement('canvas');
        this.noiseCtx = this.noiseCanvas.getContext('2d');
        this.generateNoiseTexture();
        
        this.resize();
        this.setupEventListeners();
        this.fetchMempoolData();
        this.animate();
        
        setInterval(() => this.fetchMempoolData(), 5000);
        setInterval(() => this.spawnBlock(), this.spawnRate);
    }
    
    resize() {
        const container = this.canvas.parentElement;
        const width = container.clientWidth;
        const height = Math.max(container.clientHeight, 700);
        
        this.canvas.style.width = width + 'px';
        this.canvas.style.height = height + 'px';
        this.canvas.width = width * this.dpr;
        this.canvas.height = height * this.dpr;
        
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx.scale(this.dpr, this.dpr);
        
        this.width = width;
        this.height = height;
        this.centerX = width / 2;
        this.centerY = height / 2;
        this.symbolRadius = Math.min(width, height) * 0.25;
    }
    
    generateNoiseTexture() {
        this.noiseCanvas.width = 200;
        this.noiseCanvas.height = 200;
        const imageData = this.noiseCtx.createImageData(200, 200);
        for (let i = 0; i < imageData.data.length; i += 4) {
            const val = Math.random() * 255;
            imageData.data[i] = val;
            imageData.data[i + 1] = val;
            imageData.data[i + 2] = val;
            imageData.data[i + 3] = 255;
        }
        this.noiseCtx.putImageData(imageData, 0, 0);
    }
    
    setupEventListeners() {
        window.addEventListener('resize', () => this.resize());
        
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.mouseX = e.clientX - rect.left;
            this.mouseY = e.clientY - rect.top;
            this.hoveredBlock = this.findBlockUnderMouse();
            this.canvas.style.cursor = this.hoveredBlock ? 'pointer' : 'default';
        });
        
        this.canvas.addEventListener('click', () => {
            if (this.hoveredBlock) {
                window.open('https://mempool.space/', '_blank');
            }
        });
        
        this.canvas.addEventListener('mouseleave', () => {
            this.hoveredBlock = null;
        });
        
        const toggle = document.getElementById('sovereignToggle');
        if (toggle) {
            toggle.addEventListener('change', (e) => {
                this.sovereignMode = e.target.checked;
                this.primaryColor = this.sovereignMode ? this.purpleColor : '#dc2626';
            });
        }
    }
    
    findBlockUnderMouse() {
        for (let i = this.blocks.length - 1; i >= 0; i--) {
            const block = this.blocks[i];
            const dx = this.mouseX - block.x;
            const dy = this.mouseY - block.y;
            if (Math.abs(dx) < block.size / 2 && Math.abs(dy) < block.size / 2) {
                return block;
            }
        }
        return null;
    }
    
    async fetchMempoolData() {
        try {
            const response = await fetch('/api/network-data');
            if (response.ok) {
                const data = await response.json();
                if (data.mempool) {
                    this.mempoolData.feeRate = data.mempool.fastestFee || 15;
                    this.mempoolData.txCount = data.mempool.count || 45000;
                }
                if (data.blocks && data.blocks[0]) {
                    this.mempoolData.blockHeight = data.blocks[0].height || 880000;
                }
            }
        } catch (e) {
            console.log('Using simulated mempool data');
        }
    }
    
    spawnBlock() {
        if (this.blocks.length >= this.maxBlocks) {
            this.blocks.shift();
        }
        
        const btcValue = this.generateBtcValue();
        const size = this.getBlockSize(btcValue);
        
        const side = Math.floor(Math.random() * 4);
        let x, y;
        
        switch (side) {
            case 0: x = Math.random() * this.width; y = -size; break;
            case 1: x = this.width + size; y = Math.random() * this.height; break;
            case 2: x = Math.random() * this.width; y = this.height + size; break;
            case 3: x = -size; y = Math.random() * this.height; break;
        }
        
        const block = {
            x, y,
            vx: 0,
            vy: 0,
            size,
            btcValue,
            feeRate: Math.floor(this.mempoolData.feeRate * (0.5 + Math.random())),
            color: this.getBlockColor(btcValue),
            txid: this.generateTxId(),
            rotation: Math.random() * Math.PI * 2,
            rotationSpeed: (Math.random() - 0.5) * 0.02,
            settled: false,
            glow: btcValue > 10 ? 0.8 : 0.4
        };
        
        this.blocks.push(block);
        
        if (btcValue >= 1000) {
            this.triggerChromaticAberration();
        }
    }
    
    generateBtcValue() {
        const rand = Math.random();
        if (rand < 0.001) return 1000 + Math.random() * 9000;
        if (rand < 0.01) return 100 + Math.random() * 900;
        if (rand < 0.1) return 10 + Math.random() * 90;
        if (rand < 0.4) return 1 + Math.random() * 9;
        return 0.001 + Math.random() * 0.999;
    }
    
    getBlockSize(btc) {
        if (btc >= 1000) return 60;
        if (btc >= 100) return 45;
        if (btc >= 10) return 35;
        if (btc >= 1) return 25;
        return 15;
    }
    
    getBlockColor(btc) {
        if (btc >= 1000) return '#ff0000';
        if (btc >= 100) return '#ff6b00';
        if (btc >= 10) return '#ffa500';
        if (btc >= 1) return '#ffcc00';
        return '#22c55e';
    }
    
    generateTxId() {
        const chars = '0123456789abcdef';
        let txid = '';
        for (let i = 0; i < 64; i++) {
            txid += chars[Math.floor(Math.random() * 16)];
        }
        return txid;
    }
    
    triggerChromaticAberration() {
        this.chromatic = { active: true, intensity: 1 };
        this.shockwave = {
            active: true,
            x: this.centerX,
            y: this.centerY,
            radius: 0,
            maxRadius: Math.max(this.width, this.height)
        };
    }
    
    updatePhysics() {
        const attractionStrength = 0.15;
        const airFriction = 0.98;
        const settleDistance = this.symbolRadius * 0.6;
        
        for (const block of this.blocks) {
            const dx = this.centerX - block.x;
            const dy = this.centerY - block.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance > 5) {
                const force = attractionStrength / Math.max(distance * 0.01, 1);
                block.vx += (dx / distance) * force;
                block.vy += (dy / distance) * force;
            }
            
            block.vx *= airFriction;
            block.vy *= airFriction;
            
            block.x += block.vx;
            block.y += block.vy;
            
            block.rotation += block.rotationSpeed;
            
            if (distance < settleDistance) {
                block.settled = true;
                block.vx *= 0.9;
                block.vy *= 0.9;
            }
            
            for (const other of this.blocks) {
                if (other === block) continue;
                const odx = block.x - other.x;
                const ody = block.y - other.y;
                const odist = Math.sqrt(odx * odx + ody * ody);
                const minDist = (block.size + other.size) / 2;
                
                if (odist < minDist && odist > 0) {
                    const push = (minDist - odist) * 0.3;
                    block.x += (odx / odist) * push;
                    block.y += (ody / odist) * push;
                }
            }
        }
        
        if (this.chromatic.active) {
            this.chromatic.intensity *= 0.92;
            if (this.chromatic.intensity < 0.01) {
                this.chromatic.active = false;
            }
        }
        
        if (this.shockwave.active) {
            this.shockwave.radius += 15;
            if (this.shockwave.radius > this.shockwave.maxRadius) {
                this.shockwave.active = false;
            }
        }
    }
    
    animate() {
        this.updatePhysics();
        this.render();
        requestAnimationFrame(() => this.animate());
    }
    
    render() {
        const ctx = this.ctx;
        
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, this.width, this.height);
        
        ctx.globalAlpha = 0.03;
        const pattern = ctx.createPattern(this.noiseCanvas, 'repeat');
        ctx.fillStyle = pattern;
        ctx.fillRect(0, 0, this.width, this.height);
        ctx.globalAlpha = 1;
        
        if (this.sovereignMode) {
            this.drawScanlines();
        }
        
        this.drawLuminousMonolith();
        
        this.drawBlocks();
        
        if (this.shockwave.active) {
            this.drawShockwave();
        }
        
        if (this.chromatic.active) {
            this.applyChromaticAberration();
        }
        
        if (this.hoveredBlock) {
            this.drawTooltip(this.hoveredBlock);
        }
        
        this.drawStats();
    }
    
    drawScanlines() {
        const ctx = this.ctx;
        ctx.fillStyle = 'rgba(168, 85, 247, 0.03)';
        for (let y = 0; y < this.height; y += 4) {
            ctx.fillRect(0, y, this.width, 2);
        }
    }
    
    drawLuminousMonolith() {
        const ctx = this.ctx;
        const cx = this.centerX;
        const cy = this.centerY;
        const r = this.symbolRadius;
        const color = this.primaryColor;
        
        for (let i = 5; i >= 0; i--) {
            const glowRadius = r * (1.5 + i * 0.15);
            const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, glowRadius);
            gradient.addColorStop(0, color + '30');
            gradient.addColorStop(0.5, color + '10');
            gradient.addColorStop(1, 'transparent');
            
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(cx, cy, glowRadius, 0, Math.PI * 2);
            ctx.fill();
        }
        
        const innerGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        innerGlow.addColorStop(0, color + '40');
        innerGlow.addColorStop(0.7, color + '15');
        innerGlow.addColorStop(1, 'transparent');
        ctx.fillStyle = innerGlow;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.save();
        ctx.translate(cx, cy);
        
        const scale = r / 100;
        ctx.scale(scale, scale);
        
        ctx.shadowColor = color;
        ctx.shadowBlur = 30;
        ctx.strokeStyle = color;
        ctx.lineWidth = 6;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        ctx.beginPath();
        ctx.moveTo(-10, -90);
        ctx.lineTo(-10, 90);
        ctx.moveTo(10, -90);
        ctx.lineTo(10, 90);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(-30, -60);
        ctx.lineTo(20, -60);
        ctx.quadraticCurveTo(55, -60, 55, -30);
        ctx.quadraticCurveTo(55, 0, 20, 0);
        ctx.lineTo(-30, 0);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(-30, 0);
        ctx.lineTo(25, 0);
        ctx.quadraticCurveTo(65, 0, 65, 35);
        ctx.quadraticCurveTo(65, 70, 25, 70);
        ctx.lineTo(-30, 70);
        ctx.stroke();
        
        ctx.lineWidth = 8;
        ctx.beginPath();
        ctx.moveTo(-30, -60);
        ctx.lineTo(-30, 70);
        ctx.stroke();
        
        ctx.restore();
        
        ctx.strokeStyle = color + '40';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 10]);
        ctx.beginPath();
        ctx.arc(cx, cy, r * 1.1, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
    }
    
    drawBlocks() {
        const ctx = this.ctx;
        
        for (const block of this.blocks) {
            ctx.save();
            ctx.translate(block.x, block.y);
            ctx.rotate(block.rotation);
            
            ctx.shadowColor = block.color;
            ctx.shadowBlur = block.settled ? 15 : 8;
            
            const gradient = ctx.createLinearGradient(
                -block.size / 2, -block.size / 2,
                block.size / 2, block.size / 2
            );
            gradient.addColorStop(0, block.color);
            gradient.addColorStop(1, this.adjustBrightness(block.color, -30));
            
            ctx.fillStyle = gradient;
            ctx.beginPath();
            const cornerRadius = 3;
            const s = block.size / 2;
            ctx.moveTo(-s + cornerRadius, -s);
            ctx.lineTo(s - cornerRadius, -s);
            ctx.quadraticCurveTo(s, -s, s, -s + cornerRadius);
            ctx.lineTo(s, s - cornerRadius);
            ctx.quadraticCurveTo(s, s, s - cornerRadius, s);
            ctx.lineTo(-s + cornerRadius, s);
            ctx.quadraticCurveTo(-s, s, -s, s - cornerRadius);
            ctx.lineTo(-s, -s + cornerRadius);
            ctx.quadraticCurveTo(-s, -s, -s + cornerRadius, -s);
            ctx.closePath();
            ctx.fill();
            
            ctx.strokeStyle = 'rgba(255,255,255,0.3)';
            ctx.lineWidth = 1;
            ctx.stroke();
            
            ctx.restore();
        }
    }
    
    adjustBrightness(hex, amount) {
        const num = parseInt(hex.replace('#', ''), 16);
        const r = Math.max(0, Math.min(255, (num >> 16) + amount));
        const g = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) + amount));
        const b = Math.max(0, Math.min(255, (num & 0x0000FF) + amount));
        return '#' + (1 << 24 | r << 16 | g << 8 | b).toString(16).slice(1);
    }
    
    drawShockwave() {
        const ctx = this.ctx;
        const alpha = 1 - (this.shockwave.radius / this.shockwave.maxRadius);
        
        ctx.strokeStyle = `rgba(255, 255, 255, ${alpha * 0.5})`;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(this.shockwave.x, this.shockwave.y, this.shockwave.radius, 0, Math.PI * 2);
        ctx.stroke();
    }
    
    applyChromaticAberration() {
        const ctx = this.ctx;
        const intensity = this.chromatic.intensity * 10;
        
        ctx.save();
        ctx.globalCompositeOperation = 'screen';
        ctx.globalAlpha = this.chromatic.intensity * 0.3;
        
        ctx.fillStyle = 'rgba(255, 0, 0, 0.1)';
        ctx.fillRect(-intensity, 0, this.width, this.height);
        
        ctx.fillStyle = 'rgba(0, 255, 255, 0.1)';
        ctx.fillRect(intensity, 0, this.width, this.height);
        
        ctx.restore();
    }
    
    drawTooltip(block) {
        const ctx = this.ctx;
        const padding = 12;
        const lineHeight = 18;
        
        const lines = [
            `₿ ${block.btcValue.toFixed(block.btcValue >= 1 ? 2 : 4)} BTC`,
            `Fee: ${block.feeRate} sat/vB`,
            `TX: ${block.txid.substring(0, 12)}...`
        ];
        
        ctx.font = '12px "JetBrains Mono", monospace';
        let maxWidth = 0;
        for (const line of lines) {
            maxWidth = Math.max(maxWidth, ctx.measureText(line).width);
        }
        
        const width = maxWidth + padding * 2;
        const height = lines.length * lineHeight + padding * 2 + 20;
        
        let x = this.mouseX + 15;
        let y = this.mouseY - height / 2;
        
        if (x + width > this.width) x = this.mouseX - width - 15;
        if (y < 10) y = 10;
        if (y + height > this.height - 10) y = this.height - height - 10;
        
        ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
        ctx.strokeStyle = this.primaryColor + '60';
        ctx.lineWidth = 1;
        
        ctx.beginPath();
        const cornerRadius = 8;
        ctx.moveTo(x + cornerRadius, y);
        ctx.lineTo(x + width - cornerRadius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + cornerRadius);
        ctx.lineTo(x + width, y + height - cornerRadius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - cornerRadius, y + height);
        ctx.lineTo(x + cornerRadius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - cornerRadius);
        ctx.lineTo(x, y + cornerRadius);
        ctx.quadraticCurveTo(x, y, x + cornerRadius, y);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        
        ctx.fillStyle = this.primaryColor;
        ctx.font = 'bold 14px "JetBrains Mono", monospace';
        ctx.fillText(lines[0], x + padding, y + padding + 12);
        
        ctx.fillStyle = '#888';
        ctx.font = '11px "JetBrains Mono", monospace';
        ctx.fillText(lines[1], x + padding, y + padding + 12 + lineHeight);
        
        ctx.fillStyle = '#555';
        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.fillText(lines[2], x + padding, y + padding + 12 + lineHeight * 2);
        
        ctx.fillStyle = '#444';
        ctx.font = '9px "JetBrains Mono", monospace';
        ctx.fillText('Click to browse mempool', x + padding, y + height - 8);
    }
    
    drawStats() {
        const ctx = this.ctx;
        
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.fillRect(10, 10, 200, 80);
        ctx.strokeStyle = this.primaryColor + '40';
        ctx.lineWidth = 1;
        ctx.strokeRect(10, 10, 200, 80);
        
        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.fillStyle = '#666';
        ctx.fillText('SOVEREIGN GRAVITY WELL', 20, 28);
        
        ctx.font = '11px "JetBrains Mono", monospace';
        ctx.fillStyle = this.primaryColor;
        ctx.fillText(`Blocks: ${this.blocks.length}/${this.maxBlocks}`, 20, 48);
        ctx.fillText(`Fee Rate: ${this.mempoolData.feeRate} sat/vB`, 20, 64);
        ctx.fillText(`Height: ${this.mempoolData.blockHeight.toLocaleString()}`, 20, 80);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new SovereignGravityWell('bitfeed-canvas');
});
