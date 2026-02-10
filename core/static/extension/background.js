chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'openPopup') {
    chrome.action.openPopup();
  }
});

chrome.action.onClicked.addListener((tab) => {
});

chrome.runtime.onInstalled.addListener(() => {
  console.log('Pulse Zapper extension installed');
});
