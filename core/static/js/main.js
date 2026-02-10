document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('particles-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    let particles = [];

    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 5 + 1;
            this.speedX = Math.random() * 3 - 1.5;
            this.speedY = Math.random() * 3 - 1.5;
            this.color = 'rgba(220, 38, 38, 0.5)';
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            if (this.size > 0.2) this.size -= 0.1;
        }
        draw() {
            ctx.fillStyle = this.color;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (particles.length < 100) particles.push(new Particle());
        particles.forEach((p, i) => {
            p.update();
            p.draw();
            if (p.size <= 0.2) particles.splice(i, 1);
        });
        requestAnimationFrame(animate);
    }

    function wave() {
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);
        for (let i = 0; i < canvas.width; i++) {
            ctx.lineTo(i, canvas.height / 2 + Math.sin(i * 0.01 + Date.now() * 0.001) * 20);
        }
        ctx.strokeStyle = 'rgba(220, 38, 38, 0.3)';
        ctx.stroke();
    }

    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });

    animate();
    setInterval(wave, 100);
    
    // Advertisement cycling functionality
    setInterval(cycleAds, 10000);
});

// Cycle advertisements with fade effect
function cycleAds() {
    fetch('/api/active-ads')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.ads && data.ads.length > 0) {
                const adContainers = document.querySelectorAll('.ad-container, .sidebar-ad');
                
                adContainers.forEach(container => {
                    const link = container.querySelector('a');
                    const img = container.querySelector('img');
                    const label = container.querySelector('.ad-label, small');
                    
                    if (link && img && data.ads.length > 1) {
                        // Fade out current ad
                        container.style.transition = 'opacity 0.5s ease';
                        container.style.opacity = '0.3';
                        
                        setTimeout(() => {
                            // Get random ad
                            const randomAd = data.ads[Math.floor(Math.random() * data.ads.length)];
                            
                            // Update ad content
                            link.href = randomAd.target_url;
                            img.src = randomAd.image_url;
                            img.alt = randomAd.name;
                            
                            // Fade in new ad
                            container.style.opacity = '1';
                        }, 250);
                    }
                });
            }
        })
        .catch(error => {
            console.log('Ad cycling error:', error);
        });
}