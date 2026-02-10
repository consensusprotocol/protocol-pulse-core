// Auto-refresh functionality for articles page
let refreshInterval;
let isRefreshing = false;

// Initialize auto-refresh when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Articles auto-refresh initialized');
    startAutoRefresh();
});

function startAutoRefresh() {
    // Refresh every 60 seconds (60000 milliseconds)
    refreshInterval = setInterval(() => {
        if (!isRefreshing) {
            refreshArticles();
        }
    }, 60000);
    
    console.log('Auto-refresh started - will update every 60 seconds');
}

function refreshArticles() {
    if (isRefreshing) return;
    
    isRefreshing = true;
    console.log('Fetching latest articles...');
    
    fetch('/api/latest-articles')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateGrid(data.articles);
                showRefreshIndicator();
                console.log(`Updated grid with ${data.count} articles`);
            } else {
                console.error('Failed to fetch articles:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching articles:', error);
        })
        .finally(() => {
            isRefreshing = false;
        });
}

function updateGrid(articles) {
    if (!articles || articles.length === 0) {
        console.log('No articles to display');
        return;
    }
    
    // Update hero article (first article)
    updateHeroArticle(articles[0]);
    
    // Update article grid (remaining articles)
    if (articles.length > 1) {
        updateArticleGrid(articles.slice(1));
    }
}

function updateHeroArticle(article) {
    const heroSection = document.querySelector('.hero-article');
    if (!heroSection) return;
    
    // Calculate if article is pressing
    const createdAt = new Date(article.created_at);
    const now = new Date();
    const hoursDiff = (now - createdAt) / (1000 * 60 * 60);
    const isPressing = hoursDiff < 1;
    
    const pressingBadge = isPressing ? 
        '<span class="pressing-badge"><i class="fas fa-bolt"></i> PRESSING</span>' : '';
    
    heroSection.innerHTML = `
        <div class="hero-meta">
            <span class="hero-category">${article.category}</span>
            ${pressingBadge}
            <span class="card-time">${article.created_at}</span>
        </div>
        
        <h1><a href="${article.url}" class="text-decoration-none text-dark">${article.title}</a></h1>
        
        ${article.header_image_url ? `<img src="${article.header_image_url}" alt="${article.title}">` : ''}
        
        <p>${article.summary}</p>
        
        <a href="${article.url}" class="btn btn-danger">
            Read Full Story <i class="fas fa-arrow-right ms-1"></i>
        </a>
    `;
}

function updateArticleGrid(articles) {
    const gridContainer = document.getElementById('articleGrid');
    if (!gridContainer) return;
    
    gridContainer.innerHTML = '';
    
    articles.forEach((article, index) => {
        const cardClass = index < 2 ? 'medium' : 'small';
        
        // Calculate if article is pressing
        const createdAt = new Date(article.created_at);
        const now = new Date();
        const hoursDiff = (now - createdAt) / (1000 * 60 * 60);
        const isPressing = hoursDiff < 1;
        
        const pressingBadge = isPressing ? 
            '<span class="pressing-badge"><i class="fas fa-bolt"></i> PRESSING</span>' : '';
        
        const cardHTML = `
            <article class="article-card ${cardClass}">
                ${article.header_image_url ? 
                    `<img src="${article.header_image_url}" alt="${article.title}" class="card-image">` : 
                    ''
                }
                
                <div class="card-content">
                    <div class="card-meta">
                        <span class="card-category">${article.category}</span>
                        ${pressingBadge}
                        <span class="card-time">${formatDate(article.created_at)}</span>
                    </div>
                    
                    <h3 class="card-title">
                        <a href="${article.url}">
                            ${article.title}
                        </a>
                    </h3>
                    
                    <p class="card-excerpt">
                        ${article.summary}
                    </p>
                </div>
            </article>
        `;
        
        gridContainer.innerHTML += cardHTML;
    });
}

function showRefreshIndicator() {
    const indicator = document.getElementById('refreshIndicator');
    if (indicator) {
        indicator.classList.add('show');
        
        // Hide after 2 seconds
        setTimeout(() => {
            indicator.classList.remove('show');
        }, 2000);
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
}

// Manual refresh function (can be called from UI if needed)
function manualRefresh() {
    console.log('Manual refresh triggered');
    refreshArticles();
}

// Stop auto-refresh (useful for debugging or when leaving page)
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
        console.log('Auto-refresh stopped');
    }
}

// Restart auto-refresh
function restartAutoRefresh() {
    stopAutoRefresh();
    startAutoRefresh();
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});