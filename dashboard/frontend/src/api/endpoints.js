import { get, patch } from './client';

export const fetchStatus   = () => get('/status');
export const fetchAgents   = () => get('/agents');
export const fetchPnl      = () => get('/pnl');
export const fetchConfig   = () => get('/config');
export const updateConfig  = (body) => patch('/config', body);

export function fetchPicks({ status, agent, limit } = {}) {
  const p = new URLSearchParams();
  if (status) p.set('status', status);
  if (agent)  p.set('agent', agent);
  if (limit)  p.set('limit', String(limit));
  const qs = p.toString();
  return get(`/picks${qs ? '?' + qs : ''}`);
}

export function fetchFixtures({ league, date } = {}) {
  const p = new URLSearchParams();
  if (league) p.set('league', league);
  if (date)   p.set('date', date);
  const qs = p.toString();
  return get(`/fixtures${qs ? '?' + qs : ''}`);
}

export function fetchLogs({ level, limit } = {}) {
  const p = new URLSearchParams();
  if (level) p.set('level', level);
  if (limit) p.set('limit', String(limit));
  const qs = p.toString();
  return get(`/logs${qs ? '?' + qs : ''}`);
}
