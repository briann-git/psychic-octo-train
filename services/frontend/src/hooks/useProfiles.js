import { useState, useEffect, useCallback } from 'react';
import { fetchProfiles, activateProfile, createProfile as apiCreateProfile, deleteProfile as apiDeleteProfile } from '../api/endpoints';

export default function useProfiles() {
  const [profiles, setProfiles]         = useState([]);
  const [viewedProfile, setViewed]      = useState(null);
  const [loading, setLoading]           = useState(true);

  const load = useCallback(async () => {
    try {
      const list = await fetchProfiles();
      setProfiles(list);
      // Keep viewed profile if still valid, otherwise pick first active or first overall
      setViewed(prev => {
        if (prev && list.find(p => p.id === prev.id)) {
          return list.find(p => p.id === prev.id);
        }
        return list.find(p => p.is_active) || list[0] || null;
      });
    } catch (err) {
      console.error('Failed to load profiles:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  /** Select which profile to display in the dashboard (local state, no API call). */
  const selectProfile = useCallback((id) => {
    const p = profiles.find(pr => pr.id === id);
    if (p) setViewed(p);
  }, [profiles]);

  /** Toggle is_active on a profile (API call — controls whether scheduler processes it). */
  const toggleActive = useCallback(async (id) => {
    await activateProfile(id);
    await load();
  }, [load]);

  const createProfile = useCallback(async ({ name, type, agents }) => {
    const created = await apiCreateProfile({ name, type, agents });
    await load();
    return created;
  }, [load]);

  const removeProfile = useCallback(async (id) => {
    await apiDeleteProfile(id);
    await load();
  }, [load]);

  // Derive mode from viewed profile type
  const mode = viewedProfile ? viewedProfile.type : 'paper';

  return { profiles, viewedProfile, mode, loading, selectProfile, toggleActive, createProfile, removeProfile, reload: load };
}
