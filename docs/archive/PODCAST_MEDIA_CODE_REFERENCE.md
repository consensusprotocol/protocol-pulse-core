# Protocol Pulse - Podcast & Media Pages Code Reference

This file contains all the code for the podcast page, media hub page, and clips gallery page.

---

## TABLE OF CONTENTS

1. [Podcasts Page](#podcasts-page) - `/podcasts` route
2. [Media Hub Page](#media-hub-page) - `/media` route  
3. [Clips Gallery Page](#clips-gallery-page) - `/clips` route

---

# PODCASTS PAGE

**File:** `templates/podcasts.html`
**Route:** `/podcasts`

```html
{% extends "base.html" %}

{% block title %}Podcasts - Protocol Pulse{% endblock %}

{% block head %}
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.85);
}

.podcast-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
}

.sovereign-card {
    background: var(--pp-glass);
    backdrop-filter: blur(15px);
    -webkit-backdrop-filter: blur(15px);
    border: 1px solid rgba(220, 38, 38, 0.15);
    border-radius: 16px;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
}

.sovereign-card:hover {
    border-color: var(--pp-red);
    box-shadow: 0 0 30px rgba(220, 38, 38, 0.3), inset 0 0 20px rgba(220, 38, 38, 0.05);
    transform: translateY(-4px);
}

.podcast-bento {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
    padding: 20px 0;
}

.podcast-tile {
    position: relative;
}

.podcast-cover-glass {
    position: relative;
    height: 200px;
    overflow: hidden;
}

.podcast-cover-glass img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.5s ease;
}

.sovereign-card:hover .podcast-cover-glass img {
    transform: scale(1.05);
}

.play-overlay-glass {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.sovereign-card:hover .play-overlay-glass {
    opacity: 1;
}

.play-btn-glass {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: var(--pp-red);
    border: none;
    color: white;
    font-size: 1.4rem;
    cursor: pointer;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.play-btn-glass:hover {
    transform: scale(1.1);
    box-shadow: 0 0 30px rgba(220, 38, 38, 0.6);
}

.podcast-meta-glass {
    padding: 20px;
}

.podcast-meta-glass .episode-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--pp-red);
    margin-bottom: 8px;
}

.podcast-meta-glass h5 {
    color: #fff;
    font-weight: 600;
    margin-bottom: 12px;
    line-height: 1.4;
}

.podcast-meta-glass .description {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.5);
    line-height: 1.6;
    margin-bottom: 16px;
}

.podcast-meta-glass .meta-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
    margin-bottom: 16px;
}

.podcast-actions {
    display: flex;
    gap: 10px;
}

.podcast-actions .btn {
    flex: 1;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.smart-playlist-tile {
    grid-column: 1 / -1;
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.1) 0%, var(--pp-glass) 100%);
    padding: 30px;
    margin-bottom: 20px;
}

.smart-playlist-tile h4 {
    font-family: 'JetBrains Mono', monospace;
    color: var(--pp-red);
    margin-bottom: 15px;
}

.smart-playlist-tile .sarah-hook {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.7);
    font-style: italic;
    padding: 15px;
    background: rgba(220, 38, 38, 0.1);
    border-left: 3px solid var(--pp-red);
    margin-top: 15px;
}

.section-header {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 30px;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(220, 38, 38, 0.2);
}

.section-header h2 {
    font-family: 'JetBrains Mono', monospace;
    color: #fff;
    margin: 0;
}

.section-header .rss-icon {
    color: var(--pp-red);
}
</style>
{% endblock %}

{% block content %}
<section class="podcast-page py-5">
    <div class="container">
        <div class="row mb-5">
            <div class="col-12">
                <h1 class="display-5 fw-bold text-center mb-3" style="font-family: 'JetBrains Mono', monospace; color: #fff;">
                    <i class="fas fa-podcast me-3" style="color: var(--pp-red);"></i>Protocol Pulse Podcasts
                </h1>
                <p class="lead text-center" style="font-family: 'JetBrains Mono', monospace; color: rgba(255,255,255,0.5);">Deep dives into Bitcoin, DeFi, and the future of decentralized finance</p>
            </div>
        </div>
        
        <!-- Smart Playlist Recommendation -->
        {% if smart_playlist %}
        <div class="sovereign-card smart-playlist-tile mb-4">
            <h4><i class="fas fa-brain me-2"></i>Recommended for Your Rank</h4>
            <p style="color: rgba(255,255,255,0.6); font-family: 'JetBrains Mono', monospace; font-size: 0.9rem;">
                {{ smart_playlist.series_name }}
            </p>
            <div class="sarah-hook">
                <i class="fas fa-user-tie me-2"></i>Sarah (The Macro): "{{ smart_playlist.sarah_intro }}"
            </div>
        </div>
        {% endif %}

        {% if podcast_sections %}
        {% for section_name, podcasts in podcast_sections.items() %}
        <div class="mb-5">
            <div class="section-header">
                <i class="fas fa-rss rss-icon fa-lg"></i>
                <h2>{{ section_name }}</h2>
            </div>
            <div class="podcast-bento">
                {% for podcast in podcasts %}
                <div class="podcast-tile">
                    <div class="sovereign-card h-100">
                        <div class="podcast-cover-glass">
                            {% if podcast.cover_image_url %}
                                <img src="{{ podcast.cover_image_url }}" alt="{{ podcast.title }}">
                            {% else %}
                                <div style="width: 100%; height: 100%; background: linear-gradient(135deg, #1a1a1a 0%, #2a0808 100%); display: flex; align-items: center; justify-content: center;">
                                    <i class="fas fa-microphone fa-3x" style="color: var(--pp-red); opacity: 0.5;"></i>
                                </div>
                            {% endif %}
                            
                            <div class="play-overlay-glass">
                                <button class="play-btn-glass" onclick="playPodcastGlobal('{{ podcast.id }}')">
                                    <i class="fas fa-play"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="podcast-meta-glass">
                            <div class="episode-tag">
                                Episode {{ podcast.episode_number or 'N/A' }}
                                {% if podcast.duration %} &bull; {{ podcast.duration }}{% endif %}
                            </div>
                            
                            <h5>{{ podcast.title }}</h5>
                            
                            <p class="description">
                                {{ podcast.description[:100] if podcast.description else 'Deep dive into Bitcoin and decentralized finance.' }}...
                            </p>
                            
                            <div class="meta-row">
                                <span><i class="fas fa-user me-1"></i>{{ podcast.host or 'Protocol Pulse' }}</span>
                                <span>{{ podcast.published_date.strftime('%b %d, %Y') }}</span>
                            </div>
                            
                            <div class="podcast-actions">
                                <button class="btn btn-primary btn-sm" onclick="playPodcastGlobal('{{ podcast.id }}')">
                                    <i class="fas fa-play me-1"></i>Play
                                </button>
                                <button class="btn btn-outline-light btn-sm" onclick="downloadPodcast('{{ podcast.id }}')">
                                    <i class="fas fa-download"></i>
                                </button>
                                <button class="btn btn-outline-light btn-sm" onclick="sharePodcast('{{ podcast.id }}')">
                                    <i class="fas fa-share"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <!-- Additional episodes container (hidden initially) -->
            <div id="more-episodes-{{ section_name | replace(' ', '-') | replace("'", '') }}" class="row g-4 mt-2" style="display: none;"></div>
            
            <!-- See More button -->
            <div class="row mt-4">
                <div class="col-12 text-center">
                    <button class="btn btn-outline-primary" 
                            id="see-more-btn-{{ section_name | replace(' ', '-') | replace("'", '') }}"
                            onclick="loadMoreEpisodes('{{ section_name }}', '{{ section_name | replace(' ', '-') | replace("'", '') }}')">
                        <i class="fas fa-chevron-down me-2"></i>See More Episodes
                    </button>
                </div>
            </div>
        </div>
        {% endfor %}

        {% else %}
        <div class="text-center py-5">
            <i class="fas fa-microphone text-muted mb-4" style="font-size: 4rem;"></i>
            <h3 class="text-muted mb-3">Podcasts Coming Soon</h3>
            <p class="text-muted mb-4">We're working on bringing you exciting discussions about Bitcoin, DeFi, and the future of decentralized finance.</p>
            <a href="{{ url_for('index') }}" class="btn btn-primary me-3">
                <i class="fas fa-home me-2"></i>Back to Home
            </a>
            <a href="{{ url_for('articles') }}" class="btn btn-outline-primary">
                <i class="fas fa-newspaper me-2"></i>Read Articles
            </a>
        </div>
        {% endif %}
    </div>
</section>

<!-- Sovereign Audio Bar - Persistent Global Player -->
<div id="sovereignAudioBar" class="position-fixed bottom-0 start-0 end-0" style="display: none; background: rgba(10, 10, 10, 0.98); backdrop-filter: blur(20px); border-top: 1px solid rgba(220, 38, 38, 0.3); z-index: 9999;">
    <div class="container py-3">
        <div class="row align-items-center">
            <div class="col-1">
                <div id="albumArt" style="width: 50px; height: 50px; background: linear-gradient(135deg, #1a1a1a, #2a0808); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <i class="fas fa-podcast" style="color: var(--pp-red);"></i>
                </div>
            </div>
            <div class="col-3">
                <h6 id="currentTitle" class="mb-0 text-white text-truncate" style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">Podcast Title</h6>
                <small id="currentHost" style="color: rgba(255,255,255,0.5); font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;">Host Name</small>
            </div>
            <div class="col-4">
                <div class="d-flex align-items-center gap-3 justify-content-center">
                    <button class="btn btn-link text-white p-0" onclick="seekBackward()"><i class="fas fa-backward"></i></button>
                    <button class="btn p-0" onclick="togglePlayPause()" style="width: 45px; height: 45px; background: var(--pp-red); border-radius: 50%; border: none;">
                        <i id="playPauseIcon" class="fas fa-play text-white"></i>
                    </button>
                    <button class="btn btn-link text-white p-0" onclick="seekForward()"><i class="fas fa-forward"></i></button>
                </div>
                <div class="d-flex align-items-center gap-2 mt-2">
                    <span id="currentTime" style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: rgba(255,255,255,0.5);">0:00</span>
                    <div class="flex-grow-1" style="height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; cursor: pointer;" onclick="seekTo(event)">
                        <div id="progressBar" style="height: 100%; width: 0%; background: var(--pp-red); border-radius: 2px; transition: width 0.1s;"></div>
                    </div>
                    <span id="totalTime" style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: rgba(255,255,255,0.5);">0:00</span>
                </div>
            </div>
            <div class="col-2 text-center">
                <button class="btn btn-link text-white p-0 me-3" onclick="adjustSpeed()" title="Playback Speed">
                    <span id="speedLabel" style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">1x</span>
                </button>
                <button class="btn btn-link text-white p-0" onclick="toggleVolume()" title="Volume">
                    <i id="volumeIcon" class="fas fa-volume-up"></i>
                </button>
            </div>
            <div class="col-2 text-end">
                <button class="btn btn-link p-0" onclick="closePlayer()" style="color: rgba(255,255,255,0.5);">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    </div>
    <audio id="audioElement" style="display: none;"></audio>
</div>
{% endblock %}

{% block scripts %}
<script>
let currentPodcast = null;
let playbackSpeeds = [0.75, 1, 1.25, 1.5, 2];
let currentSpeedIndex = 1;
let isMuted = false;

// Global podcast player function - works without page refresh
function playPodcastGlobal(podcastId) {
    fetch(`/api/podcast/${podcastId}`)
        .then(response => response.json())
        .then(podcast => {
            if (!podcast.audio_url) {
                alert('Audio not available for this episode yet.');
                return;
            }
            
            currentPodcast = podcast;
            document.getElementById('currentTitle').textContent = podcast.title;
            document.getElementById('currentHost').textContent = podcast.host || 'Protocol Pulse';
            
            // Update album art if available
            const albumArt = document.getElementById('albumArt');
            if (podcast.cover_image_url && albumArt) {
                albumArt.innerHTML = `<img src="${podcast.cover_image_url}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;">`;
            }
            
            document.getElementById('sovereignAudioBar').style.display = 'block';
            
            const audioElement = document.getElementById('audioElement');
            audioElement.src = podcast.audio_url;
            audioElement.play();
            
            updatePlayPauseIcon(true);
        })
        .catch(error => {
            console.error('Error loading podcast:', error);
            alert('Unable to load podcast. Please try again.');
        });
}

// Alias for backwards compatibility
function playPodcast(podcastId) {
    playPodcastGlobal(podcastId);
}

function togglePlayPause() {
    const audioElement = document.getElementById('audioElement');
    if (audioElement.paused) {
        audioElement.play();
        updatePlayPauseIcon(true);
    } else {
        audioElement.pause();
        updatePlayPauseIcon(false);
    }
}

function updatePlayPauseIcon(isPlaying) {
    const icon = document.getElementById('playPauseIcon');
    icon.className = isPlaying ? 'fas fa-pause' : 'fas fa-play';
}

function adjustSpeed() {
    const audioElement = document.getElementById('audioElement');
    currentSpeedIndex = (currentSpeedIndex + 1) % playbackSpeeds.length;
    const newSpeed = playbackSpeeds[currentSpeedIndex];
    audioElement.playbackRate = newSpeed;
    document.getElementById('speedLabel').textContent = newSpeed + 'x';
}

function closePlayer() {
    const audioElement = document.getElementById('audioElement');
    audioElement.pause();
    audioElement.currentTime = 0;
    document.getElementById('sovereignAudioBar').style.display = 'none';
}

function seekForward() {
    const audioElement = document.getElementById('audioElement');
    audioElement.currentTime = Math.min(audioElement.currentTime + 15, audioElement.duration);
}

function seekBackward() {
    const audioElement = document.getElementById('audioElement');
    audioElement.currentTime = Math.max(audioElement.currentTime - 15, 0);
}

function seekTo(event) {
    const audioElement = document.getElementById('audioElement');
    const progressBar = event.currentTarget;
    const rect = progressBar.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    audioElement.currentTime = percent * audioElement.duration;
}

function toggleVolume() {
    const audioElement = document.getElementById('audioElement');
    const volumeIcon = document.getElementById('volumeIcon');
    isMuted = !isMuted;
    audioElement.muted = isMuted;
    volumeIcon.className = isMuted ? 'fas fa-volume-mute' : 'fas fa-volume-up';
}

function downloadPodcast(podcastId) {
    alert('Download feature coming soon! Subscribe to get notified.');
}

function sharePodcast(podcastId) {
    if (navigator.share) {
        navigator.share({
            title: 'Protocol Pulse Podcast',
            text: 'Check out this podcast episode!',
            url: window.location.href
        });
    } else {
        navigator.clipboard.writeText(window.location.href);
        alert('Link copied to clipboard!');
    }
}

// Update progress bar
document.getElementById('audioElement').addEventListener('timeupdate', function() {
    const audio = this;
    const progressBar = document.getElementById('progressBar');
    const currentTime = document.getElementById('currentTime');
    const totalTime = document.getElementById('totalTime');
    
    if (audio.duration) {
        const progress = (audio.currentTime / audio.duration) * 100;
        progressBar.style.width = progress + '%';
        
        currentTime.textContent = formatTime(audio.currentTime);
        totalTime.textContent = formatTime(audio.duration);
    }
});

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return minutes + ':' + (remainingSeconds < 10 ? '0' : '') + remainingSeconds;
}

// Podcast progressive loading functionality
let loadingStates = {};

function loadMoreEpisodes(sectionName, sectionId) {
    if (loadingStates[sectionId]) return;
    
    loadingStates[sectionId] = true;
    const button = document.getElementById(`see-more-btn-${sectionId}`);
    const container = document.getElementById(`more-episodes-${sectionId}`);
    
    const originalHTML = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
    button.disabled = true;
    
    const existingEpisodes = container.children.length + 3;
    const loadLimit = button.dataset.showingAll === 'true' ? 999 : 3;
    
    fetch(`/api/podcasts/${encodeURIComponent(sectionName)}?offset=${existingEpisodes}&limit=${loadLimit}`)
        .then(response => response.json())
        .then(data => {
            if (data.podcasts && data.podcasts.length > 0) {
                container.style.display = 'flex';
                
                data.podcasts.forEach(podcast => {
                    const podcastCard = createPodcastCard(podcast);
                    container.appendChild(podcastCard);
                });
                
                if (button.dataset.showingAll === 'true' || !data.has_more) {
                    button.style.display = 'none';
                } else {
                    button.innerHTML = '<i class="fas fa-expand-alt me-2"></i>See All Episodes';
                    button.dataset.showingAll = 'true';
                }
            } else {
                button.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error loading more episodes:', error);
            button.innerHTML = originalHTML;
            alert('Failed to load more episodes. Please try again.');
        })
        .finally(() => {
            loadingStates[sectionId] = false;
            button.disabled = false;
        });
}

function createPodcastCard(podcast) {
    const col = document.createElement('div');
    col.className = 'col-lg-4 col-md-6';
    
    col.innerHTML = `
        <div class="card bg-secondary border-0 h-100 podcast-card">
            <div class="podcast-cover-container">
                ${podcast.cover_image_url ? 
                    `<img src="${podcast.cover_image_url}" alt="${podcast.title}" class="podcast-cover w-100">` :
                    `<div class="placeholder-cover bg-primary d-flex align-items-center justify-content-center">
                        <i class="fas fa-microphone fa-3x text-white"></i>
                    </div>`
                }
                <div class="play-overlay">
                    <button class="btn btn-primary rounded-circle play-btn" onclick="playPodcast('${podcast.id}')">
                        <i class="fas fa-play"></i>
                    </button>
                </div>
            </div>
            
            <div class="card-body d-flex flex-column">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <span class="badge bg-primary">Episode ${podcast.episode_number || 'N/A'}</span>
                    ${podcast.duration ? 
                        `<small class="text-muted"><i class="fas fa-clock me-1"></i>${podcast.duration}</small>` : 
                        ''
                    }
                </div>
                
                <h5 class="card-title mb-3">${podcast.title}</h5>
                
                <p class="card-text text-muted mb-3 flex-grow-1">
                    ${podcast.description || 'An exciting discussion about the latest developments in Bitcoin and decentralized finance.'}
                </p>
            </div>
        </div>
    `;
    
    return col;
}
</script>
{% endblock %}
```

---

# MEDIA HUB PAGE

**File:** `templates/media_hub.html`
**Route:** `/media`

```html
{% extends "base.html" %}

{% block title %}The Network - Protocol Pulse Media{% endblock %}

{% block head %}
<link href="https://fonts.googleapis.com/css2?family=Uncut+Sans:wght@300;500;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "PodcastSeries",
  "name": "Protocol Pulse",
  "description": "Where Bitcoin leaders speak truth. Unfiltered conversations with pioneers in the Bitcoin and Web3 space.",
  "url": "{{ url_for('media_hub', _external=True) }}",
  "genre": ["Bitcoin", "Cryptocurrency", "Technology", "Finance"],
  "inLanguage": "en",
  "publisher": {
    "@type": "Organization",
    "name": "Protocol Pulse",
    "url": "{{ url_for('index', _external=True) }}"
  }
}
</script>

<style>
    :root {
        --glass: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.08);
        --accent-red: #dc2626;
        --accent-red-glow: rgba(220, 38, 38, 0.4);
        --pure-white: #ffffff;
        --deep-black: #050505;
        --gold-accent: #f59e0b;
    }

    .media-hub {
        font-family: 'Uncut Sans', sans-serif;
        background-color: var(--deep-black);
        color: var(--pure-white);
        position: relative;
    }

    /* Floating Particles Background */
    .media-hub::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            radial-gradient(2px 2px at 20px 30px, rgba(220, 38, 38, 0.3), transparent),
            radial-gradient(2px 2px at 40px 70px, rgba(255, 255, 255, 0.15), transparent),
            radial-gradient(1px 1px at 90px 40px, rgba(220, 38, 38, 0.4), transparent),
            radial-gradient(2px 2px at 130px 80px, rgba(255, 255, 255, 0.1), transparent),
            radial-gradient(1px 1px at 160px 120px, rgba(220, 38, 38, 0.25), transparent);
        background-repeat: repeat;
        background-size: 200px 150px;
        animation: floatParticles 60s linear infinite;
        pointer-events: none;
        opacity: 0.5;
        z-index: 0;
    }

    @keyframes floatParticles {
        from { transform: translateY(0) translateX(0); }
        to { transform: translateY(-100px) translateX(50px); }
    }

    /* Scan Lines Overlay */
    .media-hub::after {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 0, 0, 0.03) 2px,
            rgba(0, 0, 0, 0.03) 4px
        );
        pointer-events: none;
        z-index: 1;
    }

    .media-hub > * {
        position: relative;
        z-index: 2;
    }

    /* Cinematic Hero */
    .hero-media {
        padding: 10rem 0 5rem;
        background: 
            radial-gradient(circle at 0% 0%, rgba(26, 5, 5, 0.9) 0%, transparent 50%),
            radial-gradient(circle at 100% 100%, rgba(220, 38, 38, 0.08) 0%, transparent 40%),
            linear-gradient(180deg, var(--deep-black) 0%, rgba(10, 5, 5, 1) 100%);
        text-align: left;
        position: relative;
        overflow: hidden;
    }

    .hero-media h1 {
        font-size: clamp(3.5rem, 10vw, 7rem);
        font-weight: 800;
        letter-spacing: -4px;
        line-height: 0.85;
        text-transform: uppercase;
        margin-bottom: 1.5rem;
        text-shadow: 0 0 60px rgba(220, 38, 38, 0.3);
        background: linear-gradient(180deg, #ffffff 0%, rgba(255, 255, 255, 0.8) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .hero-media .accent-text {
        color: var(--accent-red);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 6px;
        display: inline-flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
        text-shadow: 0 0 20px var(--accent-red-glow);
    }

    .hero-media .accent-text::before {
        content: '';
        width: 8px;
        height: 8px;
        background: var(--accent-red);
        border-radius: 50%;
        animation: pulse 2s infinite;
        box-shadow: 0 0 15px var(--accent-red);
    }

    .hero-subtitle {
        font-size: 1.35rem;
        font-weight: 300;
        color: rgba(255, 255, 255, 0.85);
        max-width: 550px;
        line-height: 1.7;
        letter-spacing: 0.3px;
    }

    /* Series Showcase */
    .series-showcase {
        padding: 6rem 0;
        background: 
            radial-gradient(ellipse at 20% 80%, rgba(220, 38, 38, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 20%, rgba(220, 38, 38, 0.05) 0%, transparent 40%),
            linear-gradient(180deg, rgba(8,8,8,1) 0%, rgba(5,5,5,1) 100%);
        position: relative;
        overflow: hidden;
    }

    .series-carousel {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 2rem;
    }

    /* Series Card - Glassmorphism Sovereign Design */
    .series-card {
        background: rgba(10, 10, 10, 0.85);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(220, 38, 38, 0.2);
        border-radius: 8px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
        position: relative;
        box-shadow: 
            inset 0 0 15px rgba(220, 38, 38, 0.05),
            0 10px 30px rgba(0, 0, 0, 0.5);
    }

    .series-card:hover {
        border-color: rgba(220, 38, 38, 0.8);
        box-shadow: 
            0 0 25px rgba(220, 38, 38, 0.2),
            inset 0 0 20px rgba(220, 38, 38, 0.1);
        transform: translateY(-2px);
    }

    .series-thumbnail {
        aspect-ratio: 16 / 9;
        width: 100%;
        background-size: cover;
        background-position: center;
        position: relative;
        overflow: hidden;
    }

    .series-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(180deg, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.7) 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.4s ease;
    }

    .series-card:hover .series-overlay {
        opacity: 1;
    }

    .play-ring {
        width: 70px;
        height: 70px;
        border: 2px solid rgba(255, 255, 255, 0.8);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(220, 38, 38, 0.9);
        transform: scale(0.8);
        transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
        box-shadow: 0 10px 40px rgba(220, 38, 38, 0.5);
    }

    .series-card:hover .play-ring {
        transform: scale(1);
    }

    .series-info {
        padding: 1.5rem;
    }

    .series-info h3 {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: var(--pure-white);
        line-height: 1.3;
    }

    .series-author {
        font-size: 0.8rem;
        color: var(--accent-red);
        font-family: 'JetBrains Mono', monospace;
        margin-bottom: 0.75rem;
    }

    .series-desc {
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.6);
        line-height: 1.5;
        margin: 0;
    }

    /* Luxurious Book Cards */
    .book-card-luxury {
        background: linear-gradient(145deg, rgba(12,12,12,1) 0%, rgba(20,20,20,1) 100%);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 28px;
        overflow: hidden;
        transition: all 0.7s cubic-bezier(0.23, 1, 0.32, 1);
        position: relative;
        box-shadow: 
            0 4px 30px rgba(0, 0, 0, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }

    .book-card-luxury:hover {
        border-color: rgba(220, 38, 38, 0.6);
        transform: translateY(-16px) scale(1.02);
        box-shadow: 
            0 40px 80px rgba(220, 38, 38, 0.2),
            0 20px 40px rgba(0, 0, 0, 0.5),
            inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }

    .book-cover-luxury {
        height: 360px;
        background: 
            radial-gradient(ellipse at 50% 100%, rgba(220, 38, 38, 0.08) 0%, transparent 50%),
            linear-gradient(180deg, #080808 0%, #121212 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        padding: 2.5rem;
        overflow: hidden;
        perspective: 1500px;
        transform-style: preserve-3d;
    }

    .book-cover-luxury img {
        max-height: 300px;
        max-width: 190px;
        object-fit: contain;
        filter: drop-shadow(0 35px 60px rgba(0, 0, 0, 0.85));
        transition: transform 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94), filter 0.5s ease;
        transform-origin: center center;
    }

    .book-card-luxury:hover .book-cover-luxury img {
        transform: scale(1.15) rotateY(-10deg) rotateX(5deg) translateZ(50px);
        filter: 
            drop-shadow(0 50px 80px rgba(0, 0, 0, 0.95)) 
            drop-shadow(0 0 40px rgba(220, 38, 38, 0.25))
            drop-shadow(0 0 10px rgba(220, 38, 38, 0.3));
    }

    .book-body-luxury {
        padding: 2rem;
        background: linear-gradient(180deg, rgba(15,15,15,1) 0%, rgba(10,10,10,1) 100%);
    }

    .book-title-luxury {
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
        line-height: 1.3;
        letter-spacing: -0.5px;
        background: linear-gradient(180deg, #ffffff 0%, rgba(255,255,255,0.85) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .book-author-luxury {
        font-size: 0.8rem;
        color: var(--accent-red);
        margin-bottom: 1rem;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 1px;
        text-shadow: 0 0 20px var(--accent-red-glow);
    }

    .btn-amazon-luxury {
        background: linear-gradient(145deg, rgba(25,25,25,1) 0%, rgba(15,15,15,1) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        color: var(--pure-white);
        padding: 1rem 1.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
        text-decoration: none;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
        transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
        width: 100%;
    }

    .btn-amazon-luxury:hover {
        background: #ff9900;
        color: var(--deep-black);
        border-color: #ff9900;
    }

    /* Terminal Player Overlay */
    .player-terminal {
        position: fixed;
        inset: 0;
        background: rgba(5,5,5,0.98);
        z-index: 9999;
        display: none;
        padding: 2rem 4rem;
        backdrop-filter: blur(20px);
        overflow-y: auto;
    }

    .player-terminal.active {
        display: block;
        animation: terminalOpen 0.4s ease-out;
    }

    @keyframes terminalOpen {
        from { opacity: 0; transform: scale(0.95); }
        to { opacity: 1; transform: scale(1); }
    }

    .terminal-header {
        border-bottom: 1px solid var(--accent-red);
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-family: 'JetBrains Mono', monospace;
    }

    .video-wrapper {
        border: 1px solid var(--accent-red);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 40px 80px rgba(220,38,38,0.2);
    }

    /* Responsive */
    @media (max-width: 1200px) {
        .series-carousel {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    @media (max-width: 768px) {
        .hero-media {
            padding: 6rem 0 3rem;
        }
        .hero-media h1 {
            font-size: 2.5rem;
            letter-spacing: -1px;
        }
        .series-carousel {
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }
    }
</style>
{% endblock %}

{% block content %}
<div class="media-hub">
    <!-- Cinematic Hero -->
    <section class="hero-media">
        <div class="container">
            <span class="accent-text">Network Operations // 2026</span>
            <h1>The<br>Network</h1>
            <p class="hero-subtitle">
                Where Bitcoin leaders speak truth. Unfiltered conversations with pioneers reshaping finance and technology.
            </p>
        </div>
    </section>

    <!-- Series Showcase -->
    <section class="series-showcase">
        <div class="container">
            <div class="showcase-header">
                <span class="showcase-badge"><i class="fas fa-broadcast-tower me-2"></i>Original Series</span>
                <h2 class="showcase-title">Book Series</h2>
                <p class="showcase-subtitle">Cinematic deep dives into the most important Bitcoin literature</p>
            </div>

            <div class="series-carousel">
                <!-- Everything Divided by 21 Million -->
                <div class="series-card" onclick="openTerminal('everything_21m')">
                    <div class="series-thumbnail" style="background-image: url('https://i.ytimg.com/vi/FA8tvWEydcA/maxresdefault.jpg');">
                        <div class="series-overlay">
                            <div class="play-ring">
                                <i class="fas fa-play"></i>
                            </div>
                        </div>
                        <div class="series-badge">10 Episodes</div>
                    </div>
                    <div class="series-info">
                        <h3>Everything Divided by 21 Million</h3>
                        <p class="series-author"><i class="fas fa-user me-2"></i>Knut Svanholm</p>
                        <p class="series-desc">Bitcoin's relationship to time, money, freedom, and human progress.</p>
                    </div>
                </div>

                <!-- The Big Print -->
                <div class="series-card" onclick="openTerminal('big_print')">
                    <div class="series-thumbnail" style="background-image: url('https://i.ytimg.com/vi/W09CNU_q6Yo/maxresdefault.jpg');">
                        <div class="series-overlay">
                            <div class="play-ring">
                                <i class="fas fa-play"></i>
                            </div>
                        </div>
                        <div class="series-badge">12 Episodes</div>
                    </div>
                    <div class="series-info">
                        <h3>The Big Print Series</h3>
                        <p class="series-author"><i class="fas fa-user me-2"></i>Lawrence Lepard</p>
                        <p class="series-desc">How the Fed engineered the greatest wealth extraction in history.</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Books Section -->
    <section class="books-section">
        <div class="container">
            <span class="section-label">Essential Reading</span>
            <h2 style="font-size: clamp(2rem, 5vw, 3rem); font-weight: 700; letter-spacing: -1px; margin-bottom: 3rem;">Our Book Series</h2>
            
            <div class="books-grid">
                {% for book in our_books %}
                <div class="book-card-luxury">
                    <div class="book-cover-luxury">
                        <span class="badge-luxury">Featured</span>
                        {% if book.cover_url %}
                        <img src="{{ book.cover_url }}" alt="{{ book.title }}" loading="lazy">
                        {% endif %}
                    </div>
                    <div class="book-body-luxury">
                        <h5 class="book-title-luxury">{{ book.title }}</h5>
                        <p class="book-author-luxury">{{ book.author }}</p>
                        <p class="book-description-luxury">{{ book.description[:100] }}...</p>
                        <a href="{{ book.amazon_url }}" target="_blank" rel="noopener" class="btn-amazon-luxury">
                            <i class="fab fa-amazon"></i>Get on Amazon
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>
</div>

<!-- YouTube Terminal Player Overlay -->
<div id="mediaTerminal" class="player-terminal">
    <div class="container-fluid">
        <div class="terminal-header">
            <span class="terminal-title">PROTOCOL PULSE // MEDIA_TERMINAL_v1.0</span>
            <button onclick="closeTerminal()" class="btn-close-terminal">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="row">
            <div class="col-lg-8 mb-4">
                <div class="video-wrapper">
                    <div class="ratio ratio-16x9">
                        <iframe id="terminalIframe" src="" allowfullscreen allow="autoplay"></iframe>
                    </div>
                </div>
            </div>
            <div class="col-lg-4 terminal-sidebar">
                <h3 class="accent-text mt-2" id="seriesTitle">INTEL_BRIEFING</h3>
                <div id="seriesDescription" class="mb-4">
                    <p id="guideBody">Loading mission parameters...</p>
                </div>
                <h5 class="text-uppercase small tracking-widest opacity-50 mb-3" style="letter-spacing: 2px;">
                    <i class="fas fa-list me-2"></i>Transmission Archive
                </h5>
                <div class="playlist-scroll" id="playlistContent"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let currentEpisode = null;
let playbackSpeeds = [0.75, 1, 1.25, 1.5, 2];
let currentSpeedIndex = 1;

const seriesData = {
    'everything_21m': {
        title: "EVERYTHING DIVIDED BY 21 MILLION",
        epCount: '10',
        host: 'Matty Ice & Knut Svanholm',
        description: 'A full 12-episode cinematic exploration of Knut Svanholm\'s book.',
        playlistId: 'PLQ4MjCv9Oedo-k8zCLu3VKW8W98KgbOlb',
        playlist: [
            { id: 'FA8tvWEydcA', title: 'Time | Episode 1 of 12' },
            { id: 'VDordtHAJhg', title: 'Alchemy | Episode 2 of 12' },
            { id: 'yKbQq66AInU', title: 'Ownership | Episode 3 of 12' }
        ]
    },
    'big_print': {
        title: "THE BIG PRINT SERIES",
        epCount: '12',
        host: 'Matty Ice & Lawrence Lepard',
        description: 'An explosive 12-part deep dive revealing how the Federal Reserve engineered wealth extraction.',
        playlistId: 'PLQ4MjCv9OedoQphIMpfvUrsgIIMUim2P9',
        playlist: [
            { id: 'W09CNU_q6Yo', title: 'Why Fixing the Money is the Only Way | Episode 1' },
            { id: 'tnthM3uaHbI', title: 'How Govt Has Been Stealing 98.5% Since 1971 | Episode 2' }
        ]
    }
};

function openTerminal(seriesKey) {
    const series = seriesData[seriesKey];
    if (!series) return;
    
    document.getElementById('mediaTerminal').classList.add('active');
    document.getElementById('seriesTitle').textContent = series.title;
    document.getElementById('guideBody').textContent = series.description;
    
    const firstVideo = series.playlist[0];
    if (firstVideo) {
        document.getElementById('terminalIframe').src = 
            `https://www.youtube.com/embed/${firstVideo.id}?autoplay=1&rel=0`;
    }
    
    // Build playlist
    const playlistHtml = series.playlist.map((ep, i) => `
        <div class="playlist-item ${i === 0 ? 'active' : ''}" onclick="playEpisode('${ep.id}', this)">
            <span class="ep-number">${String(i + 1).padStart(2, '0')}</span>
            <span class="ep-title">${ep.title}</span>
        </div>
    `).join('');
    document.getElementById('playlistContent').innerHTML = playlistHtml;
    
    document.body.style.overflow = 'hidden';
}

function closeTerminal() {
    document.getElementById('mediaTerminal').classList.remove('active');
    document.getElementById('terminalIframe').src = '';
    document.body.style.overflow = '';
}

function playEpisode(videoId, element) {
    document.getElementById('terminalIframe').src = 
        `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
    
    document.querySelectorAll('.playlist-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeTerminal();
});
</script>
{% endblock %}
```

---

# CLIPS GALLERY PAGE

**File:** `templates/clips_gallery.html`
**Route:** `/clips`

```html
{% extends "base.html" %}

{% block title %}Signal Clips | Protocol Pulse{% endblock %}

{% block head %}
<style>
:root {
    --pp-red: #dc2626;
    --pp-dark: #0a0a0a;
    --pp-glass: rgba(10, 10, 10, 0.95);
}

.clips-page {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0505 100%);
    padding: 100px 20px 60px;
}

.clips-header {
    text-align: center;
    margin-bottom: 50px;
}

.back-nav {
    position: fixed;
    top: 80px;
    left: 20px;
    z-index: 1000;
}

.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 12px;
    padding: 12px 20px;
    color: #fff;
    text-decoration: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
}

.back-btn:hover {
    background: rgba(220, 38, 38, 0.2);
    border-color: var(--pp-red);
    color: #fff;
    transform: translateX(-3px);
}

.clips-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.5rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 15px;
}

.clips-title i {
    color: var(--pp-red);
    margin-right: 15px;
}

.clips-subtitle {
    color: rgba(255, 255, 255, 0.5);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    letter-spacing: 1px;
}

.clips-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 25px;
    max-width: 1400px;
    margin: 0 auto;
}

.clip-card {
    background: var(--pp-glass);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 16px;
    overflow: hidden;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
}

.clip-card:hover {
    border-color: var(--pp-red);
    transform: translateY(-5px);
    box-shadow: 0 10px 40px rgba(220, 38, 38, 0.2);
}

.clip-video-container {
    position: relative;
    padding-top: 177.78%;
    background: #000;
}

.clip-video {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.clip-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 50%);
    display: flex;
    align-items: flex-end;
    padding: 20px;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.clip-card:hover .clip-overlay {
    opacity: 1;
}

.play-btn {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 70px;
    height: 70px;
    background: rgba(220, 38, 38, 0.9);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 1.8rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.play-btn:hover {
    transform: translate(-50%, -50%) scale(1.1);
    background: var(--pp-red);
}

.clip-info {
    padding: 20px;
}

.clip-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    color: #fff;
    margin-bottom: 10px;
    font-weight: 600;
}

.clip-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.clip-date {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
}

.clip-badge {
    background: rgba(220, 38, 38, 0.2);
    color: var(--pp-red);
    padding: 5px 12px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
}

.clip-actions {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}

.clip-action-btn {
    flex: 1;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px;
    color: rgba(255, 255, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: center;
    text-decoration: none;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}

.clip-action-btn:hover {
    background: rgba(220, 38, 38, 0.2);
    border-color: var(--pp-red);
    color: #fff;
}

.empty-state {
    text-align: center;
    padding: 100px 20px;
    color: rgba(255, 255, 255, 0.4);
    font-family: 'JetBrains Mono', monospace;
}

.empty-state i {
    font-size: 5rem;
    margin-bottom: 25px;
    opacity: 0.2;
}

.clips-status {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-top: 20px;
    flex-wrap: wrap;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 6px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.5);
}

.status-badge.active {
    border-color: rgba(34, 197, 94, 0.4);
    color: #22c55e;
}

.admin-btn {
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.2) 0%, rgba(220, 38, 38, 0.1) 100%);
    border: 1px solid rgba(220, 38, 38, 0.4);
    border-radius: 10px;
    padding: 14px 28px;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.3s ease;
    display: inline-flex;
    align-items: center;
    gap: 10px;
}

.admin-btn:hover {
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.3) 0%, rgba(220, 38, 38, 0.2) 100%);
    border-color: var(--pp-red);
    transform: translateY(-2px);
}

@media (max-width: 768px) {
    .clips-title {
        font-size: 1.8rem;
    }
    .clips-grid {
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 15px;
    }
}
</style>
{% endblock %}

{% block content %}
<nav class="back-nav">
    <a href="/" class="back-btn">
        <i class="fas fa-arrow-left"></i>
        <span>Back to Home</span>
    </a>
</nav>

<div class="clips-page">
    <div class="clips-header">
        <h1 class="clips-title"><i class="fas fa-film"></i>Signal Clips</h1>
        <p class="clips-subtitle">High-signal moments extracted from the noise</p>
        
        {% if status %}
        <div class="clips-status">
            <span class="status-badge {{ 'active' if status.ffmpeg_available else 'inactive' }}">
                <i class="fas fa-check-circle"></i> FFmpeg
            </span>
            <span class="status-badge {{ 'active' if status.ytdlp_available else 'inactive' }}">
                <i class="fas fa-check-circle"></i> yt-dlp
            </span>
            <span class="status-badge {{ 'active' if status.openai_configured else 'inactive' }}">
                <i class="fas fa-brain"></i> AI
            </span>
            <span class="status-badge">
                <i class="fas fa-video"></i> {{ status.clips_count }} clips
            </span>
        </div>
        {% endif %}
        
        {% if current_user.is_authenticated and current_user.is_admin %}
        <div class="admin-controls">
            <button class="admin-btn" onclick="generateClips()" id="generate-btn">
                <i class="fas fa-magic"></i> Generate Daily Clips
            </button>
            <span class="admin-note">Pulls from Protocol Pulse + partner channels</span>
        </div>
        {% endif %}
    </div>
    
    {% if clips %}
    <div class="clips-grid">
        {% for clip in clips %}
        <div class="clip-card">
            <div class="clip-video-container">
                <video class="clip-video" poster="" preload="metadata" muted>
                    <source src="{{ clip.url }}" type="video/mp4">
                </video>
                <div class="play-btn" onclick="playClip(this)">
                    <i class="fas fa-play"></i>
                </div>
            </div>
            <div class="clip-info">
                <div class="clip-title">{{ clip.filename | replace('_', ' ') | replace('.mp4', '') | truncate(40) }}</div>
                <div class="clip-meta">
                    <span class="clip-date">{{ clip.created[:10] }}</span>
                    {% if clip.is_final %}
                    <span class="clip-badge">BRANDED</span>
                    {% endif %}
                </div>
                <div class="clip-actions">
                    <a href="{{ clip.url }}" download class="clip-action-btn">
                        <i class="fas fa-download"></i> Download
                    </a>
                    <button class="clip-action-btn" onclick="shareClip('{{ clip.url }}')">
                        <i class="fas fa-share"></i> Share
                    </button>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="empty-state">
        <i class="fas fa-video-slash"></i>
        <h3>No Clips Yet</h3>
        <p>Signal clips from partner channels will appear here once processed.</p>
    </div>
    {% endif %}
</div>
{% endblock %}

{% block scripts %}
<script>
function playClip(btn) {
    const video = btn.parentElement.querySelector('video');
    if (video.paused) {
        document.querySelectorAll('.clip-video').forEach(v => {
            v.pause();
            v.parentElement.querySelector('.play-btn i').className = 'fas fa-play';
        });
        video.muted = false;
        video.play();
        btn.querySelector('i').className = 'fas fa-pause';
    } else {
        video.pause();
        btn.querySelector('i').className = 'fas fa-play';
    }
}

function shareClip(url) {
    const fullUrl = window.location.origin + url;
    if (navigator.share) {
        navigator.share({
            title: 'Protocol Pulse Signal Clip',
            text: 'Check out this Bitcoin intelligence clip',
            url: fullUrl
        });
    } else {
        navigator.clipboard.writeText(fullUrl).then(() => {
            alert('Link copied to clipboard!');
        });
    }
}

document.querySelectorAll('.clip-video').forEach(video => {
    video.addEventListener('ended', () => {
        video.parentElement.querySelector('.play-btn i').className = 'fas fa-play';
    });
});

async function generateClips() {
    const btn = document.getElementById('generate-btn');
    if (!btn) return;
    
    btn.disabled = true;
    btn.classList.add('loading');
    btn.innerHTML = '<i class="fas fa-spinner"></i> Generating...';
    
    try {
        const response = await fetch('/admin/api/clips/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.clips_created > 0) {
            alert(`Generated ${data.clips_created} new clips! Refreshing page...`);
            window.location.reload();
        } else if (data.errors && data.errors.length > 0) {
            alert('Some errors occurred. Check console for details.');
            console.log('Clip generation errors:', data.errors);
        } else {
            alert('No new clips generated. Daily limits may have been reached or no new videos available.');
        }
    } catch (error) {
        console.error('Generate clips error:', error);
        alert('Error generating clips. Check console for details.');
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.innerHTML = '<i class="fas fa-magic"></i> Generate Daily Clips';
    }
}
</script>
{% endblock %}
```

---

## SUMMARY

This reference file contains:

1. **Podcasts Page** (`/podcasts`) - Full audio podcast player with glassmorphism cards, progressive loading, sovereign audio bar player
2. **Media Hub Page** (`/media`) - Cinematic video series showcase with YouTube terminal player, book sections, merch integration  
3. **Clips Gallery Page** (`/clips`) - Signal clips gallery with video playback, sharing, admin clip generation

All pages use the Protocol Pulse sovereign design system with:
- JetBrains Mono typography
- Red accent color (#dc2626)
- Glassmorphism cards with 40px blur
- Dark theme backgrounds
- Scan line overlays and particle effects
