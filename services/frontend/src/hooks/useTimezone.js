import { createContext, useContext, useState, useCallback, useMemo, createElement } from 'react';

const STORAGE_KEY = 'pipeline_timezone';
const DEFAULT_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

function readStored() {
  try { return localStorage.getItem(STORAGE_KEY) || DEFAULT_TZ; }
  catch { return DEFAULT_TZ; }
}

// ── Formatting helpers ──────────────────────────────────────────────────────

function makeFormatters(tz) {
  return {
    /** "14:30" */
    time(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: tz });
    },
    /** "14:30:05" */
    timeFull(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: tz });
    },
    /** "2 Apr 2026" */
    date(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: tz });
    },
    /** "2 Apr 2026, 14:30" */
    dateTime(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleString('en-GB', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit', timeZone: tz,
      });
    },
    /** "2026-04-02" (for date inputs / API queries) */
    isoDate(d = new Date()) {
      // Build YYYY-MM-DD in the chosen timezone
      const parts = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(d);
      const get = (t) => parts.find(p => p.type === t)?.value || '';
      return `${get('year')}-${get('month')}-${get('day')}`;
    },
    /** Short timezone label, e.g. "BST", "UTC", "EAT" */
    label() {
      try {
        const parts = new Intl.DateTimeFormat('en-GB', { timeZone: tz, timeZoneName: 'short' }).formatToParts(new Date());
        return parts.find(p => p.type === 'timeZoneName')?.value || tz;
      } catch { return tz; }
    },
    /** Current wall-clock time string "14:30:05 BST" */
    clock() {
      const now = new Date();
      const t = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: tz });
      const parts = new Intl.DateTimeFormat('en-GB', { timeZone: tz, timeZoneName: 'short' }).formatToParts(now);
      const tzLabel = parts.find(p => p.type === 'timeZoneName')?.value || tz;
      return `${t} ${tzLabel}`;
    },
  };
}

// ── Context ─────────────────────────────────────────────────────────────────

const TimezoneContext = createContext(null);

export function TimezoneProvider({ children }) {
  const [tz, setTzState] = useState(readStored);

  const setTimezone = useCallback((newTz) => {
    setTzState(newTz);
    try { localStorage.setItem(STORAGE_KEY, newTz); } catch { /* quota */ }
  }, []);

  const fmt = useMemo(() => makeFormatters(tz), [tz]);

  const value = useMemo(() => ({ tz, setTimezone, fmt }), [tz, setTimezone, fmt]);

  return createElement(TimezoneContext.Provider, { value }, children);
}

// Default export: the hook
export default function useTimezone() {
  const ctx = useContext(TimezoneContext);
  if (!ctx) throw new Error('useTimezone must be used within TimezoneProvider');
  return ctx;
}
