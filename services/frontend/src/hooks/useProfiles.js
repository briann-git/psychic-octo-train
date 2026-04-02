import { useState, useEffect, useCallback } from 'react';
import { fetchProfiles, activateProfile, createProfile as apiCreateProfile, deleteProfile as apiDeleteProfile } from '../api/endpoints';

export default function useProfiles() {
  const [profiles, setProfiles]       = useState([]);
  const [activeProfile, setActive]    = useState(null);
  const [loading, setLoading]         = useState(true);
  const [switching, setSwitching]     = useState(false);

  const load = useCallback(async () => {
    try {
      const list = await fetchProfiles();
      setProfiles(list);
      const active = list.find(p => p.is_active) || list[0] || null;
      setActive(active);
    } catch (err) {
      console.error('Failed to load profiles:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const switchProfile = useCallback(async (id) => {
    if (activeProfile && id === activeProfile.id) return;
    setSwitching(true);
    try {
      const updated = await activateProfile(id);
      setActive(updated);
      await load();
    } catch (err) {
      console.error('Failed to switch profile:', err);
    } finally {
      setSwitching(false);
    }
  }, [activeProfile, load]);

  const createProfile = useCallback(async ({ name, type, agents }) => {
    const created = await apiCreateProfile({ name, type, agents });
    await load();
    return created;
  }, [load]);

  const removeProfile = useCallback(async (id) => {
    await apiDeleteProfile(id);
    await load();
  }, [load]);

  // Derive mode from active profile type
  const mode = activeProfile ? activeProfile.type : 'paper';

  return { profiles, activeProfile, mode, loading, switching, switchProfile, createProfile, removeProfile, reload: load };
}
