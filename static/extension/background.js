/**
 * Protocol Pulse Ghost — background bridge.
 * All API calls run here so requests use extension origin (no CORS from twitter.com).
 */
const DEFAULT_ORIGIN = 'https://protocolpulse.com';

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'openPopup') {
    chrome.action.openPopup();
    sendResponse({});
    return true;
  }

  if (request.action === 'getOrigin') {
    chrome.storage.local.get(['pp_origin'], (r) => {
      const o = (r.pp_origin || DEFAULT_ORIGIN).replace(/\/$/, '');
      sendResponse({ origin: o });
    });
    return true;
  }

  if (request.action === 'fetch') {
    const { url, method = 'GET', body } = request;
    const opts = { method };
    if (body) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = typeof body === 'string' ? body : JSON.stringify(body);
    }
    fetch(url, opts)
      .then((r) => r.json())
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  return true;
});

chrome.runtime.onInstalled.addListener(() => {
  console.log('Protocol Pulse Ghost installed');
});
