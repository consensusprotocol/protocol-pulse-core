// CoinDesk-Style JavaScript for Protocol Pulse

document.addEventListener('DOMContentLoaded', function() {
    // Initialize smooth scrolling
    initSmoothScrolling();
    
    // Initialize search functionality
    initSearch();
    
    // Initialize article animations
    initAnimations();
    
    // Carousel rotation (already in Bootstrap, but add auto if needed)
    const heroSlider = document.getElementById('heroSlider');
    if (heroSlider) {
        new bootstrap.Carousel(heroSlider, { interval: 5000 });
    }

    // Grid refresh (every 60s fetch new articles)
    function refreshGrid() {
        fetch('/api/latest-articles')
            .then(res => res.json())
            .then(data => {
                // Update DOM with new articles (simplified)
                const grid = document.querySelector('.article-grid');
                if (grid) {
                    grid.innerHTML = '';  // Clear and repopulate
                    data.forEach(article => {
                        grid.innerHTML += `<div class="article-card"><img src="${article.header_image_url || '/static/images/placeholder.jpg'}" alt="${article.title}"><h3><a href="/articles/${article.id}">${article.title}</a></h3><p>${article.summary ? article.summary.substring(0, 150) : 'Web3 news update'}...</p></div>`;
                    });
                }
            })
            .catch(error => {
                console.log('Grid refresh failed:', error);
            });
    }
    setInterval(refreshGrid, 60000);  // 60s
    
    // Initialize ad cycling (only on article pages)
    if (document.querySelector('.ad-container, .sidebar-ad')) {
        setInterval(cycleAds, 10000);
    }
});

function initSmoothScrolling() {
    // Add smooth scrolling to all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            // Check if href is valid (not just '#')
            if (href && href !== '#') {
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
}

function initSearch() {
    const searchForm = document.querySelector('form.d-flex');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchInput = this.querySelector('input[type="search"]');
            const searchTerm = searchInput.value.trim();
            
            if (searchTerm) {
                // Redirect to articles page with search query
                window.location.href = `/articles?search=${encodeURIComponent(searchTerm)}`;
            }
        });
    }
}

function initAnimations() {
    // Add fade-in animation to cards on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    // Observe all cards
    document.querySelectorAll('.card').forEach(card => {
        observer.observe(card);
    });
}

// Advertisement cycling functionality (only for article pages)
function cycleAds() {
    // Only run if we're on a page with ads
    if (!document.querySelector('.ad-container, .sidebar-ad')) {
        return;
    }
    
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

// Utility function for responsive navigation
function toggleMobileMenu() {
    const navbarCollapse = document.querySelector('.navbar-collapse');
    if (navbarCollapse) {
        navbarCollapse.classList.toggle('show');
    }
}

// Add click handler for mobile menu toggle
document.addEventListener('click', function(e) {
    if (e.target.closest('.navbar-toggler')) {
        toggleMobileMenu();
    }
});

// Close mobile menu when clicking outside
document.addEventListener('click', function(e) {
    const navbar = document.querySelector('.navbar');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbar && navbarCollapse && !navbar.contains(e.target)) {
        navbarCollapse.classList.remove('show');
    }
});

// Enhanced button hover effects
document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
    });
    
    btn.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

// Form validation enhancement
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = this.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });
        
        if (!isValid) {
            e.preventDefault();
        }
    });
});