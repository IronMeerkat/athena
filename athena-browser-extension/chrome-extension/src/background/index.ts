import 'webextension-polyfill';
import { exampleThemeStorage } from '@extension/storage';
import { isDistraction, evaluateAppeal, type AppealTurn } from '../services/openai';
import { getRegistry, handleMessage } from './orchestrator';
import { EchoAgent, SummarizeTitleAgent } from './agents';
import {
  compileRegexList,
  enableStrictMode,
  getSettings,
  isSettingsLocked,
  isWithinActiveSchedule,
  maybeExpireStrictMode,
  updateSettings,
  urlMatchesAny,
} from './settings';

exampleThemeStorage.get().then(theme => {
  console.log('theme', theme);
});

console.log('Background loaded');
console.log("Edit 'chrome-extension/src/background/index.ts' and save to reload.");

// Register sample agents once on startup
try {
  const registry = getRegistry();
  registry.register(new EchoAgent());
  registry.register(new SummarizeTitleAgent());
} catch {
  // ignore
}

type CurrentDOMDataType = {
  url: string;
  title: string;
  content: string;
  timestamp: number;
};

let currentDOMData: CurrentDOMDataType = {
  url: '',
  title: '',
  content: '',
  timestamp: 0,
};

const getHostnameFromUrl = (url: string): string => {
  try {
    return new URL(url).hostname;
  } catch {
    return '';
  }
};

// In-memory per-tab allowlist granted by appeals: hostname -> expiry timestamp (ms)
const appealAllowMap: Map<string, number> = new Map();
const allowExpiryTimeouts: Map<string, number> = new Map();

const isTemporarilyAllowed = (hostname: string): boolean => {
  const expiry = appealAllowMap.get(hostname);
  if (!expiry) return false;
  if (expiry > Date.now()) return true;
  appealAllowMap.delete(hostname);
  return false;
};

const scheduleAllowExpiry = (hostname: string, expiresAt: number): void => {
  const delay = Math.max(0, expiresAt - Date.now());
  const existing = allowExpiryTimeouts.get(hostname);
  if (existing) {
    clearTimeout(existing);
    allowExpiryTimeouts.delete(hostname);
  }
  if (chrome?.alarms?.create) {
    chrome.alarms.create(`allow:${hostname}`, { when: expiresAt });
    return;
  }
  const timeoutId = setTimeout(() => {
    appealAllowMap.delete(hostname);
    allowExpiryTimeouts.delete(hostname);
    // Ask all tabs on this hostname to recapture so we can re-block
    void chrome.tabs.query({}, tabs => {
      for (const t of tabs) {
        const url = t.url || '';
        try {
          const h = getHostnameFromUrl(url);
          if (h && h === hostname && t.id) {
            chrome.tabs.sendMessage(t.id, { type: 'REQUEST_DOM_CAPTURE' });
          }
        } catch {
          // ignore
        }
      }
    });
  }, delay) as unknown as number;
  allowExpiryTimeouts.set(hostname, timeoutId);
};

const addTemporaryAllow = (hostname: string, minutes: number): void => {
  const ms = Math.max(1, minutes) * 60_000;
  const expiresAt = Date.now() + ms;
  appealAllowMap.set(hostname, expiresAt);
  scheduleAllowExpiry(hostname, expiresAt);
};

if (chrome?.alarms?.onAlarm) {
  chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name.startsWith('allow:')) {
      const hostname = alarm.name.slice('allow:'.length);
      appealAllowMap.delete(hostname);
      // Ask all tabs on this hostname to recapture so we can re-block
      try {
        chrome.tabs.query({}, tabs => {
          for (const t of tabs) {
            const url = t.url || '';
            try {
              const h = getHostnameFromUrl(url);
              if (h && h === hostname && t.id) {
                chrome.tabs.sendMessage(t.id, { type: 'REQUEST_DOM_CAPTURE' });
              }
            } catch {
              // ignore
            }
          }
        });
      } catch {
        // ignore
      }
    }
  });
}

// Track appeal sessions per tab to prevent arbitrary whitelisting requests
type AppealSession = {
  tabId: number;
  hostname: string;
  createdAt: number;
};
const appealSessionsByTab: Map<number, AppealSession> = new Map();

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const sendMessageToTabWithRetry = async (tabId: number, message: unknown, attempts = 5): Promise<boolean> => {
  for (let i = 0; i < attempts; i++) {
    try {
      await new Promise<void>((resolve, reject) => {
        chrome.tabs.sendMessage(tabId, message, () => {
          const err = chrome.runtime.lastError?.message;
          if (err) {
            reject(new Error(err));
            return;
          }
          resolve();
        });
      });
      return true;
    } catch {
      if (i === attempts - 1) return false;
      await delay(150 * (i + 1));
    }
  }
  return false;
};

// Check if a URL is from Reddit or YouTube
const isRedditOrYouTube = (url: string): { isMatch: boolean; type: 'reddit' | 'youtube' | null } => {
  const redditRegex = /^https?:\/\/([a-z]+\.)?reddit\.com/i;
  const youtubeRegex = /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)/i;

  if (redditRegex.test(url)) {
    return { isMatch: true, type: 'reddit' };
  } else if (youtubeRegex.test(url)) {
    return { isMatch: true, type: 'youtube' };
  }

  return { isMatch: false, type: null };
};

// Process captured DOM to check if it's a distraction
const processCapturedDOM = async (data: CurrentDOMDataType, tabId: number) => {
  const { url, title } = data;
  const { type } = isRedditOrYouTube(url);

  let contentToCheck = title;
  let isDistractionSite = false;

  // Settings checks and schedule
  await maybeExpireStrictMode();
  const { settings } = await getSettings();
  const active = isWithinActiveSchedule(settings, new Date());
  if (!active) {
    return;
  }

  const hostname = getHostnameFromUrl(url);
  if (!hostname) return;

  // Permanent whitelist
  const wl = compileRegexList(settings.whitelistPatterns);
  if (urlMatchesAny(url, wl) || urlMatchesAny(hostname, wl)) {
    return;
  }

  // Blacklist always distract
  const bl = compileRegexList(settings.blacklistPatterns);
  const isAlwaysDistract = urlMatchesAny(url, bl) || urlMatchesAny(hostname, bl);

  // Temporary allow?
  if (isTemporarilyAllowed(hostname)) {
    return;
  }

  if (!isAlwaysDistract) {
    if (type === 'reddit') {
      const match = url.match(/\/r\/([^/]+)/i);
      if (match && match[1]) {
        contentToCheck = `r/${match[1]} - ${title}`;
      }
      isDistractionSite = await isDistraction(contentToCheck);
    } else {
      isDistractionSite = await isDistraction(title);
    }
  } else {
    isDistractionSite = true;
  }

  if (isDistractionSite) {
    // Create an appeal session scoped to this tab and hostname
    appealSessionsByTab.set(tabId, { tabId, hostname, createdAt: Date.now() });
    // Ask the content UI to display the scrim + chatbot modal
    void sendMessageToTabWithRetry(tabId, { type: 'SHOW_BLOCK_MODAL', payload: { url, title } });
  }
};

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Agent invocation path (typed handler)
  if (
    message &&
    typeof message === 'object' &&
    'type' in message &&
    (message as { type: string }).type === 'agent:invoke'
  ) {
    void (async () => {
      const res = await handleMessage(message as { type: 'agent:invoke'; payload: { agent: string; input: unknown } }, {
        tabId: sender.tab?.id,
        env: process.env.NODE_ENV === 'development' ? 'development' : 'production',
      });
      if (res) {
        sendResponse(res);
      }
    })();
    return true; // keep the message channel open for async response
  }
  // fall through for existing handlers
  // Handle DOM capture (sync ack)
  if (message.type === 'DOM_CAPTURED') {
    currentDOMData = message.payload;
    console.log('DOM captured from:', message.payload.url);

    if (sender.tab && sender.tab.id) {
      void processCapturedDOM(currentDOMData, sender.tab.id);
    }

    chrome.storage.local.set({ domData: currentDOMData });
    // Acknowledge to avoid async-response error when the listener doesn't need to be async
    sendResponse({ ok: true });
    return; // no async response expected
  }

  // Handle requests for DOM data (sync)
  if (message.type === 'GET_DOM_DATA') {
    sendResponse(currentDOMData);
    return;
  }

  // Evaluate appeal from the chatbot UI (async)
  if (message.type === 'EVALUATE_APPEAL') {
    const conversation = message.payload.conversation as AppealTurn[];
    const url = message.payload.url as string;
    const title = message.payload.title as string;
    const tabId = sender.tab?.id;
    if (!tabId) {
      sendResponse({ assistant: 'Invalid request.', allow: false, minutes: 0 });
      return true;
    }
    const session = appealSessionsByTab.get(tabId);
    const hostname = getHostnameFromUrl(url);
    if (!session || !hostname || session.hostname !== hostname) {
      sendResponse({ assistant: 'Session invalid. Reload and try again.', allow: false, minutes: 0 });
      return true;
    }

    evaluateAppeal(conversation, { url, title })
      .then(result => sendResponse(result))
      .catch(() => sendResponse({ assistant: 'Error evaluating appeal.', allow: false, minutes: 0 }));
    return true; // async response will be sent
  }

  // Whitelisting is background-controlled only after a successful allow decision (sync)
  if (message.type === 'APPEAL_ALLOW') {
    const { url, minutes } = message.payload as { url: string; minutes: number };
    const tabId = sender.tab?.id;
    if (!tabId) {
      sendResponse({ ok: false });
      return; // sync
    }
    const session = appealSessionsByTab.get(tabId);
    const hostname = getHostnameFromUrl(url);
    if (!session || !hostname || session.hostname !== hostname) {
      sendResponse({ ok: false });
      return; // sync
    }
    addTemporaryAllow(hostname, minutes || 20);
    appealSessionsByTab.delete(tabId);
    // Tell content UI to close modal
    if (sender.tab?.id) {
      void sendMessageToTabWithRetry(sender.tab.id, { type: 'CLOSE_BLOCK_MODAL' });
    }
    sendResponse({ ok: true, hostname });
    return; // sync
  }

  // Options page messaging
  if (message.type === 'GET_SETTINGS') {
    getSettings()
      .then(res => sendResponse(res))
      .catch(() => sendResponse(null));
    return true;
  }
  if (message.type === 'UPDATE_SETTINGS') {
    updateSettings(async prev => ({ ...prev, ...(message.payload ?? {}) }))
      .then(next => sendResponse({ ok: true, settings: next }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }
  if (message.type === 'ENABLE_STRICT') {
    const { days, hours } = message.payload as { days: number; hours: number };
    enableStrictMode(days, hours)
      .then(next => sendResponse({ ok: true, settings: next }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }
  if (message.type === 'IS_LOCKED') {
    isSettingsLocked()
      .then(locked => sendResponse({ locked }))
      .catch(() => sendResponse({ locked: false }));
    return true;
  }

  // No async response
  return;
});

// Also listen for tab updates to capture DOM on page refresh or initial load
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && !tab.url.startsWith('chrome://')) {
    // The DOM is already captured by the content script, this is just an additional check
    console.log('Tab updated:', tab.url);
  }
});

// Inject history hooks into the main world so SPA navigations emit a custom event
chrome.webNavigation.onCommitted.addListener(details => {
  if (details.frameId !== 0) return;
  // Skip chrome:// and chrome-extension:// pages (cannot inject there)
  if (!details.url || details.url.startsWith('chrome://') || details.url.startsWith('chrome-extension://')) return;
  if (!chrome.scripting?.executeScript) return;

  try {
    void chrome.scripting.executeScript({
      target: { tabId: details.tabId },
      world: 'MAIN',
      func: () => {
        try {
          // Avoid double-hooking
          const w = window as Window & { __spaiHistoryHooked?: boolean };
          if (w.__spaiHistoryHooked) return;
          w.__spaiHistoryHooked = true;

          const emit = () => window.dispatchEvent(new Event('spai:locationchange'));
          const originalPushState = history.pushState;
          const wrappedPushState: typeof history.pushState = function (
            this: History,
            ...args: Parameters<History['pushState']>
          ) {
            originalPushState.apply(this, args);
            emit();
          };
          history.pushState = wrappedPushState;
          const originalReplaceState = history.replaceState;
          const wrappedReplaceState: typeof history.replaceState = function (
            this: History,
            ...args: Parameters<History['replaceState']>
          ) {
            originalReplaceState.apply(this, args);
            emit();
          };
          history.replaceState = wrappedReplaceState;
          window.addEventListener('popstate', emit);
          window.addEventListener('hashchange', emit);
        } catch {
          // no-op
        }
      },
    });
  } catch {
    // Best-effort; ignore
  }
});
