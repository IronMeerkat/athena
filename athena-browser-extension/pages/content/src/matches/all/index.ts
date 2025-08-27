// Capture the entire DOM when the page loads
const captureDOM = () => {
  const fullContent = document.documentElement.outerHTML;
  const payload = {
    url: window.location.href,
    title: document.title,
    content: fullContent,
    timestamp: Date.now(),
  };

  // Send the full DOM in one message
  chrome.runtime.sendMessage({ type: 'DOM_CAPTURED', payload }, () => {
    if (chrome.runtime.lastError) {
      console.warn('DOM_CAPTURED sendMessage error:', chrome.runtime.lastError.message);
    } else {
      console.log('DOM captured and sent to background script');
    }
  });
};

// Detect SPA navigations and URL changes
let lastCapturedUrl = window.location.href;

const captureIfUrlChanged = (delayMs = 50) => {
  const currentUrl = window.location.href;
  if (currentUrl !== lastCapturedUrl) {
    lastCapturedUrl = currentUrl;
    // Slight delay to allow SPA DOM/title to update
    setTimeout(() => captureDOM(), delayMs);
  }
};

// Listen for custom events emitted from the page context
let debounceTimer: number | null = null;
const debouncedCapture = () => {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  debounceTimer = setTimeout(() => {
    captureIfUrlChanged();
  }, 50) as unknown as number;
};

window.addEventListener('spai:locationchange', debouncedCapture);
window.addEventListener('popstate', () => captureIfUrlChanged());
window.addEventListener('hashchange', () => captureIfUrlChanged());

// Fallback: periodic URL check for sites that bypass history hooks
setInterval(() => captureIfUrlChanged(0), 1000);

// Execute immediately on script load
captureDOM();

// Listen for background requests to recapture and re-evaluate
try {
  chrome.runtime.onMessage.addListener((message: unknown) => {
    if (
      typeof message === 'object' &&
      message !== null &&
      'type' in message &&
      (message as { type?: unknown }).type === 'REQUEST_DOM_CAPTURE'
    ) {
      try {
        captureDOM();
      } catch {
        // ignore
      }
    }
  });
} catch {
  // ignore
}
