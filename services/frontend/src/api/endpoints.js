import { get, post, patch, del } from './client';

export const fetchStatus   = () => get('/status');
export const fetchConfig   = () => get('/config');
export const updateConfig  = (body) => patch('/config', body);
export const fetchJobs     = () => get('/jobs');
export const fetchQuota    = () => get('/quota');

// ── Profiles ────────────────────────────────────────────────────────────────

export const fetchProfiles     = () => get('/profiles');
export const createProfile     = (body) => post('/profiles', body);
export const fetchProfile      = (id) => get(`/profiles/${id}`);
export const updateProfile     = (id, body) => patch(`/profiles/${id}`, body);
export const deleteProfile     = (id) => del(`/profiles/${id}`);
export const activateProfile   = (id) => post(`/profiles/${id}/activate`);

// ── Profile-scoped data ─────────────────────────────────────────────────────

function _profileQs(profileId) {
  return profileId ? `profile=${encodeURIComponent(profileId)}` : '';
}

export function fetchAgents(profileId) {
  const qs = _profileQs(profileId);
  return get(`/agents${qs ? '?' + qs : ''}`);
}

export function decommissionAgent(agentId, profileId) {
  const qs = _profileQs(profileId);
  return post(`/agents/${encodeURIComponent(agentId)}/decommission${qs ? '?' + qs : ''}`);
}

export function recommissionAgent(agentId, profileId) {
  const qs = _profileQs(profileId);
  return post(`/agents/${encodeURIComponent(agentId)}/recommission${qs ? '?' + qs : ''}`);
}

export function fetchPnl(profileId) {
  const qs = _profileQs(profileId);
  return get(`/pnl${qs ? '?' + qs : ''}`);
}

export function fetchPicks({ status, agent, date, limit, profileId } = {}) {
  const p = new URLSearchParams();
  if (profileId) p.set('profile', profileId);
  if (status) p.set('status', status);
  if (agent)  p.set('agent', agent);
  if (date)   p.set('date', date);
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

// ── Backtest ──────────────────────────────────────────────────────────────────

export const runBacktest = (profileId, config) =>
  post('/backtest/run', { profile_id: profileId, ...config });

export const fetchBacktestReports = (profileId) => {
  const qs = profileId ? `?profile=${encodeURIComponent(profileId)}` : '';
  return get(`/backtest/reports${qs}`);
};

export const fetchBacktestReport = (reportId) =>
  get(`/backtest/reports/${encodeURIComponent(reportId)}`);

export const deleteBacktestReport = (reportId) =>
  del(`/backtest/reports/${encodeURIComponent(reportId)}`);

