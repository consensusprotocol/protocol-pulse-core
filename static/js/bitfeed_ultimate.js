/**
 * BITFEED ULTIMATE: Orbital Transaction Visualizer
 * 
 * A beautiful galaxy-style visualization where transactions orbit in rings.
 * No clustering - each ring has defined positions.
 * When a new block is mined, the entire formation pulses and particles scatter.
 */
(function() {
    'use strict';
    
    var canvas = document.getElementById('bitfeed-canvas');
    if (!canvas) return;
    
    var ctx = canvas.getContext('2d');
    var dpr = window.devicePixelRatio || 1;
    
    var width = 0;
    var height = 0;
    var centerX = 0;
    var centerY = 0;
    
    var particles = [];
    var maxParticles = 300;
    var rings = [0.12, 0.22, 0.32, 0.42, 0.52, 0.65, 0.8];
    var ringCounts = [12, 20, 28, 36, 44, 56, 70];
    
    var currentHeight = 0;
    var lastHeight = 0;
    var pulseIntensity = 0;
    var time = 0;
    
    var sovereignMode = false;
    
    function resize() {
        var rect = canvas.getBoundingClientRect();
        width = rect.width;
        height = rect.height;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.scale(dpr, dpr);
        centerX = width / 2;
        centerY = height / 2;
    }
    
    function init() {
        resize();
        setupEvents();
        fetchHeight();
        spawnInitialParticles();
        setInterval(fetchHeight, 30000);
        setInterval(spawnParticle, 100);
        requestAnimationFrame(loop);
    }
    
    function setupEvents() {
        window.addEventListener('resize', resize);
        var toggle = document.getElementById('sovereign-toggle');
        if (toggle) {
            toggle.addEventListener('change', function(e) {
                sovereignMode = e.target.checked;
            });
        }
    }
    
    function fetchHeight() {
        fetch('https://mempool.space/api/blocks/tip/height')
            .then(function(r) { return r.text(); })
            .then(function(t) {
                var h = parseInt(t);
                if (h && h !== currentHeight) {
                    lastHeight = currentHeight;
                    currentHeight = h;
                    var el = document.getElementById('block-height');
                    if (el) el.textContent = h.toLocaleString();
                    if (lastHeight > 0 && h > lastHeight) {
                        triggerBlockMined();
                    }
                }
            })
            .catch(function() {});
    }
    
    function triggerBlockMined() {
        console.log('BLOCK MINED: #' + currentHeight);
        pulseIntensity = 1;
        
        var note = document.getElementById('block-notification');
        if (note) {
            var ht = document.getElementById('notification-height');
            if (ht) ht.textContent = 'Block #' + currentHeight.toLocaleString();
            note.classList.add('show');
            setTimeout(function() { note.classList.remove('show'); }, 4000);
        }
        
        // Scatter all particles outward
        for (var i = 0; i < particles.length; i++) {
            var p = particles[i];
            p.scatterVel = 8 + Math.random() * 6;
            p.scattering = true;
            p.fadeSpeed = 0.015 + Math.random() * 0.01;
        }
    }
    
    function spawnInitialParticles() {
        for (var i = 0; i < 80; i++) {
            spawnParticle();
        }
    }
    
    function spawnParticle() {
        if (particles.length >= maxParticles) {
            // Remove oldest non-scattering particle
            for (var i = 0; i < particles.length; i++) {
                if (!particles[i].scattering) {
                    particles.splice(i, 1);
                    break;
                }
            }
        }
        
        // Pick a random ring
        var ringIdx = Math.floor(Math.random() * rings.length);
        var ringRadius = rings[ringIdx] * Math.min(width, height) * 0.5;
        
        // Random angle
        var angle = Math.random() * Math.PI * 2;
        
        // Transaction data
        var btc = generateBTC();
        var fee = 1 + Math.random() * 80;
        
        particles.push({
            ring: ringIdx,
            radius: ringRadius,
            angle: angle,
            x: centerX + Math.cos(angle) * ringRadius,
            y: centerY + Math.sin(angle) * ringRadius,
            size: getSize(btc),
            color: getColor(btc, fee),
            btc: btc,
            orbitSpeed: (0.0003 + Math.random() * 0.0004) * (ringIdx % 2 === 0 ? 1 : -1),
            alpha: 0,
            fadeIn: true,
            scattering: false,
            scatterVel: 0,
            fadeSpeed: 0
        });
        
        updateUI();
    }
    
    function generateBTC() {
        var r = Math.random();
        if (r < 0.002) return 500 + Math.random() * 500;
        if (r < 0.02) return 50 + Math.random() * 100;
        if (r < 0.1) return 5 + Math.random() * 20;
        if (r < 0.4) return 0.5 + Math.random() * 3;
        return 0.001 + Math.random() * 0.3;
    }
    
    function getSize(btc) {
        if (btc >= 100) return 16;
        if (btc >= 50) return 12;
        if (btc >= 10) return 9;
        if (btc >= 1) return 7;
        return 4;
    }
    
    function getColor(btc, fee) {
        if (btc >= 100) return '#ff2222';
        if (btc >= 50) return '#ff6600';
        if (fee < 15) return '#22cc66';
        if (fee < 40) return '#ff9900';
        return '#dd3333';
    }
    
    function update() {
        time += 0.016;
        
        for (var i = particles.length - 1; i >= 0; i--) {
            var p = particles[i];
            
            if (p.scattering) {
                // Move outward
                var dx = p.x - centerX;
                var dy = p.y - centerY;
                var dist = Math.sqrt(dx * dx + dy * dy) || 1;
                p.x += (dx / dist) * p.scatterVel;
                p.y += (dy / dist) * p.scatterVel;
                p.scatterVel *= 0.97;
                p.alpha -= p.fadeSpeed;
                
                if (p.alpha <= 0) {
                    particles.splice(i, 1);
                }
                continue;
            }
            
            // Fade in
            if (p.fadeIn) {
                p.alpha += 0.03;
                if (p.alpha >= 1) {
                    p.alpha = 1;
                    p.fadeIn = false;
                }
            }
            
            // Orbit around center
            p.angle += p.orbitSpeed;
            p.x = centerX + Math.cos(p.angle) * p.radius;
            p.y = centerY + Math.sin(p.angle) * p.radius;
        }
        
        // Decay pulse
        if (pulseIntensity > 0) {
            pulseIntensity *= 0.95;
            if (pulseIntensity < 0.01) pulseIntensity = 0;
        }
    }
    
    function updateUI() {
        var count = particles.filter(function(p) { return !p.scattering; }).length;
        var bar = document.getElementById('progress-bar');
        if (bar) bar.style.width = Math.min(100, (count / maxParticles) * 100) + '%';
        
        var statusEl = document.getElementById('status');
        if (statusEl) {
            statusEl.textContent = 'Orbiting: ' + count + ' transactions';
        }
    }
    
    function render() {
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, width, height);
        
        drawRings();
        drawCenter();
        drawParticles();
        
        // Pulse flash
        if (pulseIntensity > 0) {
            ctx.fillStyle = 'rgba(255, 255, 255, ' + pulseIntensity * 0.6 + ')';
            ctx.fillRect(0, 0, width, height);
        }
    }
    
    function drawRings() {
        var baseColor = sovereignMode ? 'rgba(168, 85, 247,' : 'rgba(220, 38, 38,';
        
        for (var i = 0; i < rings.length; i++) {
            var radius = rings[i] * Math.min(width, height) * 0.5;
            var alpha = 0.06 + pulseIntensity * 0.2;
            
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
            ctx.strokeStyle = baseColor + alpha + ')';
            ctx.lineWidth = 1;
            ctx.stroke();
        }
    }
    
    function drawCenter() {
        var baseColor = sovereignMode ? '#a855f7' : '#dc2626';
        var pulse = 0.6 + Math.sin(time * 2) * 0.2 + pulseIntensity * 0.3;
        
        // Inner core glow
        var gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, 60);
        gradient.addColorStop(0, baseColor);
        gradient.addColorStop(0.3, baseColor + '66');
        gradient.addColorStop(1, 'transparent');
        
        ctx.save();
        ctx.globalAlpha = pulse * 0.6;
        ctx.fillStyle = gradient;
        ctx.fillRect(centerX - 80, centerY - 80, 160, 160);
        ctx.restore();
        
        // Bitcoin symbol in center
        ctx.save();
        ctx.font = 'bold 36px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = baseColor;
        ctx.shadowBlur = 20;
        ctx.shadowColor = baseColor;
        ctx.globalAlpha = 0.8 + pulseIntensity * 0.2;
        ctx.fillText('₿', centerX, centerY);
        ctx.restore();
    }
    
    function drawParticles() {
        for (var i = 0; i < particles.length; i++) {
            var p = particles[i];
            
            ctx.save();
            ctx.globalAlpha = p.alpha;
            
            // Glow
            ctx.shadowBlur = 15;
            ctx.shadowColor = p.color;
            
            // Particle
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size / 2, 0, Math.PI * 2);
            ctx.fill();
            
            // Bright center
            ctx.fillStyle = 'rgba(255,255,255,0.4)';
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size / 4, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.restore();
            
            // Trail for large transactions
            if (p.btc >= 50 && !p.scattering) {
                ctx.save();
                ctx.globalAlpha = p.alpha * 0.3;
                ctx.strokeStyle = p.color;
                ctx.lineWidth = 2;
                ctx.shadowBlur = 10;
                ctx.shadowColor = p.color;
                ctx.beginPath();
                ctx.arc(centerX, centerY, p.radius, p.angle - 0.3, p.angle);
                ctx.stroke();
                ctx.restore();
            }
        }
    }
    
    function loop() {
        update();
        render();
        requestAnimationFrame(loop);
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    console.log('Bitfeed Orbital Visualizer ready');
})();
