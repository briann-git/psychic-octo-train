import { useState, useEffect, useRef } from 'react';

export default function useSSE(url = '/api/logs/stream', { maxLines = 200, enabled = true } = {}) {
  const [lines, setLines]         = useState([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef(null);

  useEffect(() => {
    if (!enabled) {
      esRef.current?.close();
      setConnected(false);
      return;
    }
    function connect() {
      const es = new EventSource(url);
      esRef.current = es;
      es.onopen    = () => setConnected(true);
      es.onmessage = (e) => {
        try {
          const entry = JSON.parse(e.data);
          if (entry.error) return;
          setLines(prev => {
            const next = [...prev, entry];
            return next.length > maxLines ? next.slice(-maxLines) : next;
          });
        } catch { /* ignore */ }
      };
      es.onerror = () => {
        setConnected(false);
        es.close();
        setTimeout(connect, 5000);
      };
    }
    connect();
    return () => { esRef.current?.close(); setConnected(false); };
  }, [url, maxLines, enabled]);

  return { lines, connected };
}
