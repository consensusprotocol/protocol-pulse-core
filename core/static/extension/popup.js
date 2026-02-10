const API_BASE = 'https://protocolpulse.replit.app';

let currentTab = null;
let hasWebLN = false;

document.addEventListener('DOMContentLoaded', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTab = tab;
  
  document.getElementById('current-url').textContent = new URL(tab.url).hostname;
  document.getElementById('page-title').textContent = tab.title || 'Untitled';
  
  const platform = detectPlatform(tab.url);
  document.getElementById('page-platform').textContent = platform;
  
  checkWebLN();
  
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('amount').value = btn.dataset.amount;
    });
  });
  
  document.getElementById('zap-btn').addEventListener('click', handleZap);
  document.getElementById('curate-btn').addEventListener('click', handleCurate);
});

function detectPlatform(url) {
  const domain = new URL(url).hostname.toLowerCase();
  
  if (domain.includes('twitter.com') || domain.includes('x.com')) return 'twitter';
  if (domain.includes('youtube.com') || domain.includes('youtu.be')) return 'youtube';
  if (domain.includes('reddit.com')) return 'reddit';
  if (domain.includes('stacker.news')) return 'stacker_news';
  if (domain.includes('primal.net') || domain.includes('snort.social') || domain.includes('iris.to')) return 'nostr';
  if (domain.includes('substack.com')) return 'substack';
  if (domain.includes('medium.com')) return 'medium';
  
  return 'website';
}

async function checkWebLN() {
  try {
    if (typeof window.webln !== 'undefined') {
      hasWebLN = true;
    } else {
      chrome.tabs.sendMessage(currentTab.id, { action: 'checkWebLN' }, response => {
        hasWebLN = response?.hasWebLN || false;
        if (!hasWebLN) {
          document.getElementById('no-wallet').style.display = 'block';
        }
      });
    }
  } catch (e) {
    console.log('WebLN check failed:', e);
  }
}

async function handleZap() {
  const amount = parseInt(document.getElementById('amount').value);
  const btn = document.getElementById('zap-btn');
  
  if (amount < 1) {
    showStatus('Please enter a valid amount', 'error');
    return;
  }
  
  btn.disabled = true;
  btn.textContent = '⏳ Processing...';
  
  try {
    const response = await fetch(`${API_BASE}/api/value-stream/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: currentTab.url,
        title: currentTab.title
      })
    });
    
    const data = await response.json();
    
    if (data.success || data.post_id) {
      const postId = data.post_id;
      
      chrome.tabs.sendMessage(currentTab.id, { 
        action: 'triggerZap', 
        amount: amount,
        postId: postId 
      }, response => {
        if (response?.success) {
          showStatus(`⚡ Zapped ${amount} sats!`, 'success');
          
          fetch(`${API_BASE}/api/value-stream/zap/${postId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              amount_sats: amount,
              payment_hash: response.paymentHash
            })
          });
        } else {
          showStatus(response?.error || 'Zap failed', 'error');
        }
      });
    } else {
      showStatus(data.error || 'Failed to register content', 'error');
    }
  } catch (err) {
    showStatus('Error: ' + err.message, 'error');
  }
  
  btn.disabled = false;
  btn.textContent = '⚡ ZAP NOW';
}

async function handleCurate() {
  const btn = document.getElementById('curate-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Curating...';
  
  try {
    const response = await fetch(`${API_BASE}/api/value-stream/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: currentTab.url,
        title: currentTab.title
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showStatus('✓ Added to Value Stream!', 'success');
    } else if (data.post_id) {
      showStatus('Already in Value Stream', 'error');
    } else {
      showStatus(data.error || 'Failed to curate', 'error');
    }
  } catch (err) {
    showStatus('Error: ' + err.message, 'error');
  }
  
  btn.disabled = false;
  btn.textContent = '📤 Curate to Value Stream';
}

function showStatus(message, type) {
  const container = document.getElementById('status-container');
  container.innerHTML = `<div class="status ${type}">${message}</div>`;
  
  setTimeout(() => {
    container.innerHTML = '';
  }, 4000);
}
