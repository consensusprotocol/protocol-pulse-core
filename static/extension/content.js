chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'checkWebLN') {
    sendResponse({ hasWebLN: typeof window.webln !== 'undefined' });
    return true;
  }
  
  if (request.action === 'triggerZap') {
    handleZap(request.amount, request.postId)
      .then(result => sendResponse(result))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }
});

async function handleZap(amount, postId) {
  if (typeof window.webln === 'undefined') {
    return { success: false, error: 'WebLN not available. Install Alby or another Lightning wallet.' };
  }
  
  try {
    await window.webln.enable();
    
    const invoice = await createInvoice(amount, postId);
    if (!invoice) {
      const lnurl = `lightning:protocolpulse@getalby.com?amount=${amount * 1000}`;
      return { success: false, error: 'No Lightning address available for this content.' };
    }
    
    const result = await window.webln.sendPayment(invoice);
    
    return { 
      success: true, 
      paymentHash: result.paymentHash || result.preimage,
      amount: amount
    };
  } catch (err) {
    return { success: false, error: err.message || 'Payment failed' };
  }
}

async function createInvoice(amount, postId) {
  try {
    const response = await fetch(`https://protocolpulse.replit.app/api/value-stream/invoice/${postId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount_sats: amount })
    });
    
    const data = await response.json();
    return data.invoice;
  } catch (err) {
    console.error('Failed to create invoice:', err);
    return null;
  }
}

const zapButton = document.createElement('div');
zapButton.id = 'pulse-zap-button';
zapButton.innerHTML = '⚡';
zapButton.style.cssText = `
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #f7931a, #ff6b00);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(247, 147, 26, 0.4);
  z-index: 999999;
  transition: transform 0.2s;
  display: none;
`;

zapButton.addEventListener('mouseover', () => {
  zapButton.style.transform = 'scale(1.1)';
});

zapButton.addEventListener('mouseout', () => {
  zapButton.style.transform = 'scale(1)';
});

zapButton.addEventListener('click', () => {
  chrome.runtime.sendMessage({ action: 'openPopup' });
});

if (document.body) {
  document.body.appendChild(zapButton);
  zapButton.style.display = 'flex';
}
