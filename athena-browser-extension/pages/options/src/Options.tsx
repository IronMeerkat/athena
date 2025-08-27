import '@src/Options.css';
import { withErrorBoundary, withSuspense } from '@extension/shared';
import { cn, ErrorDisplay, LoadingSpinner } from '@extension/ui';
import { useEffect, useMemo, useState } from 'react';

type TimeRange = { start: string; end: string };
type DaySchedule = { enabled: boolean; ranges: TimeRange[] };
type WeeklySchedule = {
  mon: DaySchedule;
  tue: DaySchedule;
  wed: DaySchedule;
  thu: DaySchedule;
  fri: DaySchedule;
  sat: DaySchedule;
  sun: DaySchedule;
};

type Settings = {
  version: number;
  createdAt: number;
  schedule: WeeklySchedule;
  whitelistPatterns: string[];
  blacklistPatterns: string[];
  strictMode: { enabled: boolean; expiresAt: number | null };
};

const dayOrder: (keyof WeeklySchedule)[] = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
const dayLabel: Record<keyof WeeklySchedule, string> = {
  mon: 'Mon',
  tue: 'Tue',
  wed: 'Wed',
  thu: 'Thu',
  fri: 'Fri',
  sat: 'Sat',
  sun: 'Sun',
};

const Options = () => {
  const [loading, setLoading] = useState(true);
  const [locked, setLocked] = useState(false);
  const [tampered, setTampered] = useState(false);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [daysInput, setDaysInput] = useState('0');
  const [hoursInput, setHoursInput] = useState('0');

  const goGithubSite = () => chrome.tabs.create({ url: 'https://github.com/IronMeerkat/athena-browser-extension' });

  const fetchSettings = async () => {
    setLoading(true);
    const res = await chrome.runtime.sendMessage({ type: 'GET_SETTINGS' }).catch(() => null);
    if (res) {
      setSettings(res.settings);
      setLocked(res.locked);
      setTampered(res.tampered);
    }
    setLoading(false);
  };

  useEffect(() => {
    void fetchSettings();
  }, []);

  const updatePartial = async (patch: Partial<Settings>) => {
    if (locked) return;
    const res = await chrome.runtime
      .sendMessage({ type: 'UPDATE_SETTINGS', payload: patch })
      .catch(() => ({ ok: false }));
    if (res?.ok) setSettings(res.settings as Settings);
  };

  const addRange = (day: keyof WeeklySchedule) => {
    if (!settings || locked) return;
    const next: Settings = {
      ...settings,
      schedule: {
        ...settings.schedule,
        [day]: {
          ...settings.schedule[day],
          ranges: [...settings.schedule[day].ranges, { start: '09:00', end: '17:00' }],
        },
      },
    };
    void updatePartial({ schedule: next.schedule });
  };

  const removeRange = (day: keyof WeeklySchedule, idx: number) => {
    if (!settings || locked) return;
    const ranges = settings.schedule[day].ranges.filter((_, i) => i !== idx);
    const next = { ...settings.schedule, [day]: { ...settings.schedule[day], ranges } } as WeeklySchedule;
    void updatePartial({ schedule: next });
  };

  const setRange = (day: keyof WeeklySchedule, idx: number, key: 'start' | 'end', value: string) => {
    if (!settings || locked) return;
    const ranges = settings.schedule[day].ranges.map((r, i) => (i === idx ? { ...r, [key]: value } : r));
    const next = { ...settings.schedule, [day]: { ...settings.schedule[day], ranges } } as WeeklySchedule;
    void updatePartial({ schedule: next });
  };

  const toggleDay = (day: keyof WeeklySchedule) => {
    if (!settings || locked) return;
    const next = {
      ...settings.schedule,
      [day]: { ...settings.schedule[day], enabled: !settings.schedule[day].enabled },
    } as WeeklySchedule;
    void updatePartial({ schedule: next });
  };

  const regexTextToList = (text: string): string[] =>
    text
      .split('\n')
      .map(s => s.trim())
      .filter(Boolean);

  const whitelistText = useMemo(() => (settings?.whitelistPatterns ?? []).join('\n'), [settings]);
  const blacklistText = useMemo(() => (settings?.blacklistPatterns ?? []).join('\n'), [settings]);

  const onChangeWhitelist = (value: string) => {
    if (!settings || locked) return;
    void updatePartial({ whitelistPatterns: regexTextToList(value) });
  };
  const onChangeBlacklist = (value: string) => {
    if (!settings || locked) return;
    void updatePartial({ blacklistPatterns: regexTextToList(value) });
  };

  const enableStrict = async () => {
    if (locked) return;
    const days = parseInt(daysInput || '0', 10) || 0;
    const hours = parseInt(hoursInput || '0', 10) || 0;
    const confirmed = window.confirm(
      `Enable strict mode for ${days} day(s) and ${hours} hour(s)? You won't be able to edit settings until it expires.`,
    );
    if (!confirmed) return;
    const res = await chrome.runtime
      .sendMessage({ type: 'ENABLE_STRICT', payload: { days, hours } })
      .catch(() => ({ ok: false }));
    if (res?.ok) {
      setSettings(res.settings as Settings);
      setLocked(true);
    }
  };

  return (
    <div className={cn('h-screen w-screen overflow-auto', 'bg-slate-50 text-gray-900')}>
      <header
        className={cn(
          'sticky top-0 z-10 flex items-center justify-between border-b bg-white/80 px-6 py-3 backdrop-blur',
        )}>
        <button onClick={goGithubSite} className="flex items-center gap-2">
          <img src={chrome.runtime.getURL('options/logo_horizontal.svg')} className="h-8" alt="logo" />
          <span className="text-sm text-gray-500">Athena Browser Extension</span>
        </button>
        {tampered && <span className="text-xs text-red-600">Settings file was tampered; using last valid.</span>}
      </header>

      {loading || !settings ? (
        <div className="p-8">
          <LoadingSpinner />
        </div>
      ) : (
        <main className="mx-auto max-w-5xl space-y-8 p-6">
          <section className="rounded-lg border bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">Timetable</h2>
            <p className="mb-4 text-sm text-gray-600">When the blocker is active.</p>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {dayOrder.map(day => (
                <div key={day} className="rounded border p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <label className="font-medium" htmlFor={`day-${day}`}>
                      {dayLabel[day]}
                    </label>
                    <label className="inline-flex items-center gap-2 text-sm" htmlFor={`day-${day}-enabled`}>
                      <input
                        id={`day-${day}-enabled`}
                        type="checkbox"
                        checked={settings.schedule[day].enabled}
                        onChange={() => toggleDay(day)}
                        disabled={locked}
                      />
                      Enabled
                    </label>
                  </div>
                  <div className="space-y-2">
                    {settings.schedule[day].ranges.map((r, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <input
                          type="time"
                          className="w-28 rounded border px-2 py-1"
                          value={r.start}
                          onChange={e => setRange(day, idx, 'start', e.target.value)}
                          disabled={locked}
                        />
                        <span className="text-sm">to</span>
                        <input
                          type="time"
                          className="w-28 rounded border px-2 py-1"
                          value={r.end}
                          onChange={e => setRange(day, idx, 'end', e.target.value)}
                          disabled={locked}
                        />
                        <button
                          className="ml-2 rounded border px-2 py-1 text-sm hover:bg-gray-50 disabled:opacity-50"
                          onClick={() => removeRange(day, idx)}
                          disabled={locked}>
                          Remove
                        </button>
                      </div>
                    ))}
                    <button
                      className="rounded border px-2 py-1 text-sm hover:bg-gray-50 disabled:opacity-50"
                      onClick={() => addRange(day)}
                      disabled={locked}>
                      Add range
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-lg border bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">Whitelist (never blocked)</h2>
            <p className="mb-2 text-sm text-gray-600">One regex per line. Matches are never checked or blocked.</p>
            <textarea
              className="min-h-28 w-full rounded border p-2 font-mono text-sm"
              defaultValue={whitelistText}
              onChange={e => onChangeWhitelist(e.target.value)}
              disabled={locked}
            />
          </section>

          <section className="rounded-lg border bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">Blacklist (always distractions)</h2>
            <p className="mb-2 text-sm text-gray-600">One regex per line. Matches are blocked but still appealable.</p>
            <textarea
              className="min-h-28 w-full rounded border p-2 font-mono text-sm"
              defaultValue={blacklistText}
              onChange={e => onChangeBlacklist(e.target.value)}
              disabled={locked}
            />
          </section>

          <section className="rounded-lg border bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">Strict mode</h2>
            <p className="mb-4 text-sm text-gray-600">
              When enabled, settings cannot be modified until the timer expires.
            </p>
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label className="block text-sm text-gray-600" htmlFor="strict-days">
                  Days
                </label>
                <input
                  id="strict-days"
                  type="number"
                  min={0}
                  className="w-24 rounded border px-2 py-1"
                  value={daysInput}
                  onChange={e => setDaysInput(e.target.value)}
                  disabled={locked}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600" htmlFor="strict-hours">
                  Hours
                </label>
                <input
                  id="strict-hours"
                  type="number"
                  min={0}
                  max={23}
                  className="w-24 rounded border px-2 py-1"
                  value={hoursInput}
                  onChange={e => setHoursInput(e.target.value)}
                  disabled={locked}
                />
              </div>
              <button
                className="rounded bg-red-600 px-3 py-2 text-white hover:bg-red-700 disabled:opacity-50"
                onClick={enableStrict}
                disabled={locked}>
                Enable strict mode
              </button>
              {settings.strictMode.enabled && (
                <span className="text-sm text-gray-700">
                  Enabled until{' '}
                  {settings.strictMode.expiresAt
                    ? new Date(settings.strictMode.expiresAt).toLocaleString()
                    : 'indefinite'}
                </span>
              )}
            </div>
          </section>
        </main>
      )}
    </div>
  );
};

export default withErrorBoundary(withSuspense(Options, <LoadingSpinner />), ErrorDisplay);
