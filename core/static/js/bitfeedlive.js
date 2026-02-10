/**
 * Protocol Pulse Kinetic Terminal
 * Bitcoin-shaped gravity well visualization
 * Pure physics, zero text clutter
 */

class KineticTerminal {
    constructor() {
        this.canvas = document.getElementById('bitfeed-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        this.engine = Matter.Engine.create();
        this.world = this.engine.world;
        this.engine.world.gravity.y = 1.2;
        
        this.blocks = [];
        this.bitcoinBoundary = [];
        this.sovereignMode = localStorage.getItem('sovereignMode') === 'true';
        this.hoveredBlock = null;
        
        this.currentMempool = {
            count: 0,
            vsize: 0,
            avgFeeRate: 0
        };
        
        this.colors = {
            standard: '#ffffff',
            medium: '#f97316',
            high: '#dc2626',
            megaWhale: '#fbbf24',
            sovereign: '#a855f7'
        };
        
        this.resize();
        this.createBitcoinBoundary();
        this.fetchMempoolData();
        this.animate();
        
        window.addEventListener('resize', () => {
            this.resize();
            this.rebuildBoundary();
        });
        
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseleave', () => this.hoveredBlock = null);
        
        const sovereignToggle = document.getElementById('sovereign-toggle');
        if (sovereignToggle) {
            sovereignToggle.checked = this.sovereignMode;
            sovereignToggle.addEventListener('change', (e) => {
                this.sovereignMode = e.target.checked;
                localStorage.setItem('sovereignMode', this.sovereignMode);
                this.updateBlockColors();
            });
        }
        
        setInterval(() => this.fetchMempoolData(), 3000);
    }
    
    resize() {
        const container = this.canvas.parentElement;
        this.canvas.width = container.clientWidth;
        this.canvas.height = Math.min(container.clientWidth * 9/16, 650);
    }
    
    createBitcoinBoundary() {
        const centerX = this.canvas.width / 2;
        const bottomY = this.canvas.height - 20;
        const scale = Math.min(this.canvas.width / 800, 1) * 0.8;
        
        const bitcoinPaths = [
            { x: -80, y: 0, w: 20, h: 180 },
            { x: 80, y: 0, w: 20, h: 180 },
            { x: -80, y: -90, w: 180, h: 20 },
            { x: -80, y: 0, w: 180, h: 20 },
            { x: -80, y: 90, w: 180, h: 20 },
            { x: 100, y: -45, w: 40, h: 20, angle: 0.3 },
            { x: 100, y: 45, w: 40, h: 20, angle: -0.3 },
            { x: -20, y: -120, w: 10, h: 40 },
            { x: 20, y: -120, w: 10, h: 40 },
            { x: -20, y: 120, w: 10, h: 40 },
            { x: 20, y: 120, w: 10, h: 40 },
        ];
        
        bitcoinPaths.forEach((path, i) => {
            const body = Matter.Bodies.rectangle(
                centerX + path.x * scale,
                bottomY + path.y * scale - 100,
                path.w * scale,
                path.h * scale,
                { 
                    isStatic: true, 
                    label: 'bitcoin-boundary',
                    angle: path.angle || 0,
                    render: { visible: false }
                }
            );
            Matter.World.add(this.world, body);
            this.bitcoinBoundary.push(body);
        });
        
        const ground = Matter.Bodies.rectangle(
            centerX,
            this.canvas.height + 50,
            this.canvas.width * 2,
            100,
            { isStatic: true, label: 'ground' }
        );
        
        const leftWall = Matter.Bodies.rectangle(
            -25,
            this.canvas.height / 2,
            50,
            this.canvas.height * 2,
            { isStatic: true, label: 'wall' }
        );
        
        const rightWall = Matter.Bodies.rectangle(
            this.canvas.width + 25,
            this.canvas.height / 2,
            50,
            this.canvas.height * 2,
            { isStatic: true, label: 'wall' }
        );
        
        Matter.World.add(this.world, [ground, leftWall, rightWall]);
    }
    
    rebuildBoundary() {
        const bodiesToRemove = this.world.bodies.filter(b => 
            b.label === 'bitcoin-boundary' || b.label === 'ground' || b.label === 'wall'
        );
        Matter.World.remove(this.world, bodiesToRemove);
        this.bitcoinBoundary = [];
        this.createBitcoinBoundary();
    }
    
    handleMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        this.hoveredBlock = null;
        
        for (const block of this.blocks) {
            if (!block.customData) continue;
            
            const pos = block.position;
            const size = block.customData.size;
            
            if (mouseX >= pos.x - size/2 && mouseX <= pos.x + size/2 &&
                mouseY >= pos.y - size/2 && mouseY <= pos.y + size/2) {
                this.hoveredBlock = block;
                break;
            }
        }
    }
    
    async fetchMempoolData() {
        try {
            const [mempoolRes, feesRes, blocksRes, difficultyRes] = await Promise.all([
                fetch('https://mempool.space/api/mempool'),
                fetch('https://mempool.space/api/v1/fees/recommended'),
                fetch('https://mempool.space/api/blocks'),
                fetch('https://mempool.space/api/v1/difficulty-adjustment')
            ]);
            
            const mempool = await mempoolRes.json();
            const fees = await feesRes.json();
            const blocks = await blocksRes.json();
            const difficulty = await difficultyRes.json();
            
            this.currentMempool = {
                count: mempool.count,
                vsize: mempool.vsize,
                avgFeeRate: fees.halfHourFee || 0
            };
            
            this.updateNetworkPanel(mempool, fees, blocks, difficulty);
            this.spawnBlocks();
            
        } catch (error) {
            console.error('Mempool fetch error:', error);
        }
    }
    
    updateNetworkPanel(mempool, fees, blocks, difficulty) {
        const mempoolCount = document.getElementById('mempool-count');
        const avgFeeRate = document.getElementById('avg-fee-rate');
        const lowPriorityCount = document.getElementById('low-priority-count');
        const mediumPriorityCount = document.getElementById('medium-priority-count');
        const highPriorityCount = document.getElementById('high-priority-count');
        const latestBlockHeight = document.getElementById('latest-block-height');
        const latestBlockTime = document.getElementById('latest-block-time');
        const networkHashrate = document.getElementById('network-hashrate');
        const networkDifficulty = document.getElementById('network-difficulty');
        
        if (mempoolCount) mempoolCount.textContent = mempool.count.toLocaleString();
        if (avgFeeRate) avgFeeRate.textContent = Math.round(fees.halfHourFee) + ' sat/vB';
        
        const lowCount = Math.round(mempool.count * 0.4);
        const medCount = Math.round(mempool.count * 0.35);
        const highCount = Math.round(mempool.count * 0.25);
        
        if (lowPriorityCount) lowPriorityCount.textContent = lowCount.toLocaleString();
        if (mediumPriorityCount) mediumPriorityCount.textContent = medCount.toLocaleString();
        if (highPriorityCount) highPriorityCount.textContent = highCount.toLocaleString();
        
        if (blocks && blocks.length > 0) {
            const latest = blocks[0];
            if (latestBlockHeight) latestBlockHeight.textContent = '#' + latest.height.toLocaleString();
            
            if (latestBlockTime) {
                const blockTime = new Date(latest.timestamp * 1000);
                const now = new Date();
                const minAgo = Math.floor((now - blockTime) / 60000);
                latestBlockTime.textContent = minAgo + ' min ago';
            }
            
            if (latest.difficulty && networkDifficulty) {
                const trillion = (latest.difficulty / 1e12).toFixed(2);
                networkDifficulty.textContent = trillion;
            }
        }
        
        if (difficulty && difficulty.estimatedHashrate) {
            const ehps = (difficulty.estimatedHashrate / 1e18).toFixed(1);
            if (networkHashrate) networkHashrate.textContent = ehps;
        }
    }
    
    spawnBlocks() {
        const spawnProbability = Math.min(this.currentMempool.count / 50000, 1);
        const blocksToSpawn = Math.floor(spawnProbability * 3) + 1;
        
        for (let i = 0; i < blocksToSpawn; i++) {
            if (this.blocks.length >= 150) break;
            
            const rand = Math.random();
            let priority, color, size, btcValue, feeRate, isMegaWhale;
            
            const megaWhaleChance = 0.02;
            isMegaWhale = Math.random() < megaWhaleChance;
            
            if (isMegaWhale) {
                priority = 'mega-whale';
                btcValue = 1000 + Math.random() * 4000;
                feeRate = 50 + Math.random() * 100;
                color = this.sovereignMode ? this.colors.sovereign : this.colors.megaWhale;
                size = 45 + Math.random() * 20;
            } else if (rand < 0.5) {
                priority = 'standard';
                btcValue = 0.001 + Math.random() * 0.5;
                feeRate = 1 + Math.random() * 5;
                color = this.sovereignMode ? this.colors.sovereign : this.colors.standard;
                size = 8 + Math.random() * 6;
            } else if (rand < 0.8) {
                priority = 'medium';
                btcValue = 0.5 + Math.random() * 5;
                feeRate = 6 + Math.random() * 15;
                color = this.sovereignMode ? this.colors.sovereign : this.colors.medium;
                size = 14 + Math.random() * 10;
            } else {
                priority = 'high';
                btcValue = 5 + Math.random() * 50;
                feeRate = 21 + Math.random() * 80;
                color = this.sovereignMode ? this.colors.sovereign : this.colors.high;
                size = 20 + Math.random() * 15;
            }
            
            const x = Math.random() * (this.canvas.width - 150) + 75;
            const y = -50 - (Math.random() * 100);
            
            const mass = isMegaWhale ? 30 : (size / 10);
            
            const block = Matter.Bodies.rectangle(x, y, size, size, {
                restitution: isMegaWhale ? 0.6 : 0.3,
                friction: 0.1,
                frictionAir: 0.001,
                angle: Math.random() * Math.PI * 2,
                mass: mass,
                label: 'tx-block'
            });
            
            block.customData = {
                priority: priority,
                baseColor: color,
                color: color,
                size: size,
                btcValue: btcValue,
                feeRate: feeRate,
                isMegaWhale: isMegaWhale,
                txid: this.generateTxId(),
                spawnTime: Date.now()
            };
            
            Matter.World.add(this.world, block);
            this.blocks.push(block);
        }
        
        this.cleanupOldBlocks();
    }
    
    generateTxId() {
        const chars = '0123456789abcdef';
        let txid = '';
        for (let i = 0; i < 64; i++) {
            txid += chars[Math.floor(Math.random() * chars.length)];
        }
        return txid;
    }
    
    cleanupOldBlocks() {
        const maxBlocks = 120;
        while (this.blocks.length > maxBlocks) {
            const oldBlock = this.blocks.shift();
            Matter.World.remove(this.world, oldBlock);
        }
        
        this.blocks = this.blocks.filter(block => {
            if (block.position.y > this.canvas.height + 100) {
                Matter.World.remove(this.world, block);
                return false;
            }
            return true;
        });
    }
    
    updateBlockColors() {
        for (const block of this.blocks) {
            if (block.customData) {
                if (this.sovereignMode) {
                    block.customData.color = this.colors.sovereign;
                } else {
                    if (block.customData.priority === 'mega-whale') {
                        block.customData.color = this.colors.megaWhale;
                    } else if (block.customData.priority === 'standard') {
                        block.customData.color = this.colors.standard;
                    } else if (block.customData.priority === 'medium') {
                        block.customData.color = this.colors.medium;
                    } else {
                        block.customData.color = this.colors.high;
                    }
                }
            }
        }
    }
    
    draw() {
        this.ctx.fillStyle = '#000000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.drawBitcoinOutline();
        
        for (const block of this.blocks) {
            if (!block.customData) continue;
            this.drawBlock(block);
        }
        
        if (this.hoveredBlock) {
            this.drawHoverCard(this.hoveredBlock);
        }
    }
    
    drawBitcoinOutline() {
        const centerX = this.canvas.width / 2;
        const bottomY = this.canvas.height - 120;
        const scale = Math.min(this.canvas.width / 800, 1) * 0.7;
        
        this.ctx.save();
        this.ctx.strokeStyle = this.sovereignMode ? 'rgba(168, 85, 247, 0.15)' : 'rgba(255, 255, 255, 0.08)';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([5, 10]);
        
        this.ctx.beginPath();
        this.ctx.moveTo(centerX - 60 * scale, bottomY - 100 * scale);
        this.ctx.lineTo(centerX - 60 * scale, bottomY + 100 * scale);
        this.ctx.lineTo(centerX + 60 * scale, bottomY + 100 * scale);
        this.ctx.lineTo(centerX + 100 * scale, bottomY + 50 * scale);
        this.ctx.lineTo(centerX + 100 * scale, bottomY + 10 * scale);
        this.ctx.lineTo(centerX + 60 * scale, bottomY);
        this.ctx.lineTo(centerX + 100 * scale, bottomY - 10 * scale);
        this.ctx.lineTo(centerX + 100 * scale, bottomY - 50 * scale);
        this.ctx.lineTo(centerX + 60 * scale, bottomY - 100 * scale);
        this.ctx.closePath();
        this.ctx.stroke();
        
        this.ctx.beginPath();
        this.ctx.moveTo(centerX - 20 * scale, bottomY - 100 * scale);
        this.ctx.lineTo(centerX - 20 * scale, bottomY - 130 * scale);
        this.ctx.moveTo(centerX + 20 * scale, bottomY - 100 * scale);
        this.ctx.lineTo(centerX + 20 * scale, bottomY - 130 * scale);
        this.ctx.moveTo(centerX - 20 * scale, bottomY + 100 * scale);
        this.ctx.lineTo(centerX - 20 * scale, bottomY + 130 * scale);
        this.ctx.moveTo(centerX + 20 * scale, bottomY + 100 * scale);
        this.ctx.lineTo(centerX + 20 * scale, bottomY + 130 * scale);
        this.ctx.stroke();
        
        this.ctx.setLineDash([]);
        this.ctx.restore();
    }
    
    drawBlock(block) {
        const pos = block.position;
        const angle = block.angle;
        const size = block.customData.size;
        const color = block.customData.color;
        const isMegaWhale = block.customData.isMegaWhale;
        
        this.ctx.save();
        this.ctx.translate(pos.x, pos.y);
        this.ctx.rotate(angle);
        
        if (this.sovereignMode) {
            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = isMegaWhale ? 3 : 2;
            this.ctx.shadowColor = color;
            this.ctx.shadowBlur = isMegaWhale ? 25 : 12;
            this.ctx.strokeRect(-size/2, -size/2, size, size);
        } else {
            this.ctx.fillStyle = color;
            this.ctx.shadowColor = color;
            this.ctx.shadowBlur = isMegaWhale ? 20 : 6;
            this.ctx.fillRect(-size/2, -size/2, size, size);
            
            if (isMegaWhale) {
                this.ctx.strokeStyle = '#fff';
                this.ctx.lineWidth = 2;
                this.ctx.strokeRect(-size/2, -size/2, size, size);
            }
        }
        
        this.ctx.restore();
    }
    
    drawHoverCard(block) {
        const data = block.customData;
        const pos = block.position;
        
        const cardWidth = 200;
        const cardHeight = 100;
        let cardX = pos.x + 20;
        let cardY = pos.y - cardHeight - 10;
        
        if (cardX + cardWidth > this.canvas.width) cardX = pos.x - cardWidth - 20;
        if (cardY < 10) cardY = pos.y + 20;
        
        this.ctx.save();
        
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.95)';
        this.ctx.strokeStyle = this.sovereignMode ? '#a855f7' : '#333';
        this.ctx.lineWidth = 1;
        
        this.ctx.beginPath();
        this.ctx.roundRect(cardX, cardY, cardWidth, cardHeight, 8);
        this.ctx.fill();
        this.ctx.stroke();
        
        this.ctx.font = '11px "JetBrains Mono", monospace';
        this.ctx.fillStyle = '#888';
        this.ctx.fillText('TRANSACTION', cardX + 12, cardY + 20);
        
        this.ctx.font = '13px "JetBrains Mono", monospace';
        this.ctx.fillStyle = '#fff';
        this.ctx.fillText(`${data.btcValue.toFixed(4)} BTC`, cardX + 12, cardY + 40);
        
        this.ctx.fillStyle = data.color;
        this.ctx.fillText(`${data.feeRate.toFixed(1)} sat/vB`, cardX + 12, cardY + 58);
        
        this.ctx.font = '9px "JetBrains Mono", monospace';
        this.ctx.fillStyle = '#555';
        this.ctx.fillText(data.txid.substring(0, 16) + '...', cardX + 12, cardY + 78);
        
        if (data.isMegaWhale) {
            this.ctx.fillStyle = '#fbbf24';
            this.ctx.font = 'bold 10px "JetBrains Mono", monospace';
            this.ctx.fillText('MEGA-WHALE', cardX + 120, cardY + 20);
        }
        
        this.ctx.restore();
    }
    
    animate() {
        Matter.Engine.update(this.engine, 1000 / 60);
        this.draw();
        requestAnimationFrame(() => this.animate());
    }
}

window.kineticTerminal = null;

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        window.kineticTerminal = new KineticTerminal();
    }, 100);
});
