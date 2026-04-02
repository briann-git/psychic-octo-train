import { useState, useEffect, useCallback, useRef } from 'react';

export default function useApi(fetcher, { interval = 30000, enabled = true } = {}) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const mounted = useRef(true);

  const load = useCallback(async () => {
    if (!enabled) return;
    try {
      const result = await fetcher();
      if (mounted.current) { setData(result); setError(null); }
    } catch (err) {
      if (mounted.current) setError(err.message);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [fetcher, enabled]);

  useEffect(() => {
    mounted.current = true;
    load();
    if (interval > 0 && enabled) {
      const id = setInterval(load, interval);
      return () => { mounted.current = false; clearInterval(id); };
    }
    return () => { mounted.current = false; };
  }, [load, interval, enabled]);

  return { data, loading, error, refetch: load };
}
