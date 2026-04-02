import { useState, useEffect, useCallback } from 'react';
import { fetchConfig, updateConfig } from '../api/endpoints';

export default function useTradingMode() {
  const [mode, setMode]         = useState('paper');
  const [loading, setLoading]   = useState(true);
  const [switching, setSwitching] = useState(false);

  useEffect(() => {
    fetchConfig()
      .then(cfg => {
        setMode(cfg.PAPER_TRADING === 'false' || cfg.PAPER_TRADING === false ? 'live' : 'paper');
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const applyMode = useCallback(async (next) => {
    if (next === mode) return;
    setSwitching(true);
    try {
      await updateConfig({ PAPER_TRADING: next === 'paper' ? 'true' : 'false' });
      setMode(next);
    } catch (err) {
      console.error('Failed to switch trading mode:', err);
    } finally {
      setSwitching(false);
    }
  }, [mode]);

  const toggleMode = useCallback(() => applyMode(mode === 'paper' ? 'live' : 'paper'), [applyMode, mode]);

  return { mode, loading, switching, toggleMode, setMode: applyMode };
}
