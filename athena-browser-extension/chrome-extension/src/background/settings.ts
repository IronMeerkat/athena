import 'webextension-polyfill';

// Settings types
export type TimeRange = { start: string; end: string }; // HH:MM 24h
export type DaySchedule = { enabled: boolean; ranges: TimeRange[] };
export type WeeklySchedule = {
  mon: DaySchedule;
  tue: DaySchedule;
  wed: DaySchedule;
  thu: DaySchedule;
  fri: DaySchedule;
  sat: DaySchedule;
  sun: DaySchedule;
};

export type Settings = {
  version: number;
  createdAt: number;
  schedule: WeeklySchedule;
  whitelistPatterns: string[]; // regex strings
  blacklistPatterns: string[]; // regex strings
  strictMode: { enabled: boolean; expiresAt: number | null };
};

// Encrypted payload shape stored in chrome.storage.local
type EncryptedSettings = {
  v: number; // version of encryption format
  salt: string; // base64
  iv: string; // base64
  cipherText: string; // base64
  mac: string; // base64 HMAC-SHA-256 over v|salt|iv|cipherText
};

const STORAGE_KEY = 'secure-settings-v1';
const ENCRYPTION_VERSION = 1;

// Provide a reasonable default schedule: active Mon-Fri 09:00-18:00
const defaultDay = (): DaySchedule => ({ enabled: true, ranges: [{ start: '09:00', end: '18:00' }] });
const weekendDay = (): DaySchedule => ({ enabled: false, ranges: [] });

export const DEFAULT_SETTINGS: Settings = {
  version: 1,
  createdAt: Date.now(),
  schedule: {
    mon: defaultDay(),
    tue: defaultDay(),
    wed: defaultDay(),
    thu: defaultDay(),
    fri: defaultDay(),
    sat: weekendDay(),
    sun: weekendDay(),
  },
  whitelistPatterns: [],
  blacklistPatterns: [],
  strictMode: { enabled: false, expiresAt: null },
};

// Cache of last valid settings to recover from tamper
let lastValidSettings: Settings = DEFAULT_SETTINGS;

// Derived keys cache per salt (string)
const keyCache: Map<string, { aesKey: CryptoKey; macKey: CryptoKey }> = new Map();

const te = new TextEncoder();
const td = new TextDecoder();

const SETTINGS_SECRET = (process.env.CEB_SETTINGS_SECRET ?? '') + (globalThis.chrome?.runtime?.id ?? '');

const b64encode = (bytes: ArrayBuffer): string => {
  const bin = String.fromCharCode(...new Uint8Array(bytes));
  return btoa(bin);
};

const b64decode = (text: string): ArrayBuffer => {
  const bin = atob(text);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
};

const concatArrayBuffers = (buffers: ArrayBuffer[]): ArrayBuffer => {
  const total = buffers.reduce((acc, b) => acc + b.byteLength, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const b of buffers) {
    out.set(new Uint8Array(b), offset);
    offset += b.byteLength;
  }
  return out.buffer;
};

const getDerivedKeys = async (saltB64: string): Promise<{ aesKey: CryptoKey; macKey: CryptoKey }> => {
  const cached = keyCache.get(saltB64);
  if (cached) return cached;

  const salt = b64decode(saltB64);
  const km = await crypto.subtle.importKey('raw', te.encode(SETTINGS_SECRET || 'spai-fallback'), 'PBKDF2', false, [
    'deriveBits',
  ]);
  const bits = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      hash: 'SHA-256',
      salt,
      iterations: 250000,
    },
    km,
    512,
  );
  const bytes = new Uint8Array(bits);
  const aesMaterial = bytes.slice(0, 32);
  const macMaterial = bytes.slice(32);

  const aesKey = await crypto.subtle.importKey('raw', aesMaterial, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
  const macKey = await crypto.subtle.importKey('raw', macMaterial, { name: 'HMAC', hash: 'SHA-256' }, false, [
    'sign',
    'verify',
  ]);
  const derived = { aesKey, macKey };
  keyCache.set(saltB64, derived);
  return derived;
};

const sign = async (macKey: CryptoKey, parts: ArrayBuffer[]): Promise<string> => {
  const data = concatArrayBuffers(parts);
  const mac = await crypto.subtle.sign('HMAC', macKey, data);
  return b64encode(mac);
};

const verify = async (macKey: CryptoKey, parts: ArrayBuffer[], macB64: string): Promise<boolean> => {
  const data = concatArrayBuffers(parts);
  const mac = b64decode(macB64);
  return crypto.subtle.verify('HMAC', macKey, mac, data);
};

const encryptSettings = async (settings: Settings): Promise<EncryptedSettings> => {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const saltB64 = b64encode(salt.buffer);
  const { aesKey, macKey } = await getDerivedKeys(saltB64);

  const plaintext = te.encode(JSON.stringify(settings));
  const cipher = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, aesKey, plaintext);
  const ivB64 = b64encode(iv.buffer);
  const cipherB64 = b64encode(cipher);

  const vBuf = new Uint8Array([ENCRYPTION_VERSION]).buffer;
  const mac = await sign(macKey, [vBuf, te.encode(saltB64), te.encode(ivB64), te.encode(cipherB64)]);

  return {
    v: ENCRYPTION_VERSION,
    salt: saltB64,
    iv: ivB64,
    cipherText: cipherB64,
    mac,
  };
};

const decryptSettings = async (enc: EncryptedSettings): Promise<Settings | null> => {
  try {
    if (!enc || typeof enc !== 'object') return null;
    if (enc.v !== ENCRYPTION_VERSION) return null;
    const { aesKey, macKey } = await getDerivedKeys(enc.salt);
    const ok = await verify(
      macKey,
      [new Uint8Array([enc.v]).buffer, te.encode(enc.salt), te.encode(enc.iv), te.encode(enc.cipherText)],
      enc.mac,
    );
    if (!ok) return null;
    const iv = new Uint8Array(b64decode(enc.iv));
    const cipher = b64decode(enc.cipherText);
    const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, aesKey, cipher);
    const json = td.decode(plain);
    const parsed = JSON.parse(json) as Settings;
    return parsed;
  } catch {
    return null;
  }
};

// Persist encrypted settings into chrome.storage.local
const persistEncrypted = async (enc: EncryptedSettings): Promise<void> => {
  await chrome.storage.local.set({ [STORAGE_KEY]: enc });
};

const readEncrypted = async (): Promise<EncryptedSettings | null> => {
  const obj = await chrome.storage.local.get([STORAGE_KEY]);
  const value = obj?.[STORAGE_KEY];
  if (!value) return null;
  return value as EncryptedSettings;
};

export const getSettings = async (): Promise<{ settings: Settings; locked: boolean; tampered: boolean }> => {
  const enc = await readEncrypted();
  if (!enc) {
    lastValidSettings = DEFAULT_SETTINGS;
    const encrypted = await encryptSettings(lastValidSettings);
    await persistEncrypted(encrypted);
    return { settings: lastValidSettings, locked: false, tampered: false };
  }

  const dec = await decryptSettings(enc);
  if (!dec) {
    // Tamper detected or cannot decrypt; fall back to defaults
    return { settings: lastValidSettings, locked: lastValidSettings.strictMode.enabled, tampered: true };
  }
  lastValidSettings = dec;
  const locked = Boolean(
    dec.strictMode.enabled && (!dec.strictMode.expiresAt || dec.strictMode.expiresAt > Date.now()),
  );
  return { settings: dec, locked, tampered: false };
};

export const updateSettings = async (updater: (prev: Settings) => Promise<Settings> | Settings): Promise<Settings> => {
  const { settings, locked } = await getSettings();
  if (locked) {
    return settings;
  }
  const next = await updater(settings);
  // Validate regex patterns
  for (const p of next.whitelistPatterns) new RegExp(p);
  for (const p of next.blacklistPatterns) new RegExp(p);
  const enc = await encryptSettings(next);
  await persistEncrypted(enc);
  lastValidSettings = next;
  return next;
};

export const enableStrictMode = async (days: number, hours: number): Promise<Settings> => {
  const ms = Math.max(0, Math.floor(days)) * 24 * 60 * 60 * 1000 + Math.max(0, Math.floor(hours)) * 60 * 60 * 1000;
  const expiresAt = Date.now() + ms;
  const next = await updateSettings(prev => ({
    ...prev,
    strictMode: { enabled: true, expiresAt },
  }));
  try {
    chrome.alarms?.create('strict-expiry', { when: expiresAt });
  } catch {
    // ignore
  }
  return next;
};

export const maybeExpireStrictMode = async (): Promise<void> => {
  const { settings } = await getSettings();
  const { strictMode } = settings;
  if (strictMode.enabled && strictMode.expiresAt && strictMode.expiresAt <= Date.now()) {
    await updateSettings(prev => ({ ...prev, strictMode: { enabled: false, expiresAt: null } }));
  }
};

// Helpers for evaluation
export const isWithinActiveSchedule = (settings: Settings, date = new Date()): boolean => {
  const dayIdx = date.getDay(); // 0 = Sunday
  const dayMap: (keyof WeeklySchedule)[] = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
  const dayKey = dayMap[dayIdx];
  const day = settings.schedule[dayKey];
  if (!day.enabled) return false;
  if (!day.ranges || day.ranges.length === 0) return true; // enabled but no ranges => always
  const nowMinutes = date.getHours() * 60 + date.getMinutes();
  for (const r of day.ranges) {
    const [sh, sm] = r.start.split(':').map(n => parseInt(n, 10));
    const [eh, em] = r.end.split(':').map(n => parseInt(n, 10));
    const startMin = sh * 60 + sm;
    const endMin = eh * 60 + em;
    if (endMin >= startMin) {
      if (nowMinutes >= startMin && nowMinutes <= endMin) return true;
    } else {
      // overnight range
      if (nowMinutes >= startMin || nowMinutes <= endMin) return true;
    }
  }
  return false;
};

export const compileRegexList = (patterns: string[]): RegExp[] => {
  const compiled: RegExp[] = [];
  for (const p of patterns) {
    try {
      compiled.push(new RegExp(p));
    } catch {
      // skip invalid pattern
    }
  }
  return compiled;
};

export const urlMatchesAny = (url: string, regexes: RegExp[]): boolean => {
  for (const r of regexes) {
    if (r.test(url)) return true;
  }
  return false;
};

export const isSettingsLocked = async (): Promise<boolean> => {
  const { locked } = await getSettings();
  return locked;
};
