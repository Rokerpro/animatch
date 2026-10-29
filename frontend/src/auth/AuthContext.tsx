import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { queryKeys, useMe } from "../api/hooks";
import { useToast } from "../components/useToast";
import { AuthContext } from "./context";
const STORAGE_KEY = "animatch.includeMature";
export function AuthProvider({ children }: { children: ReactNode }) {
  const { data: user } = useMe();
  const [localMature, setLocalMature] = useState(() => localStorage.getItem(STORAGE_KEY) === "true");
  const client = useQueryClient(); const { showToast } = useToast();
  const mature = user?.show_mature ?? localMature;
  useEffect(() => { if (user) setLocalMature(user.show_mature); }, [user]);
  const refresh = useCallback(async () => { await client.invalidateQueries({ queryKey: queryKeys.me }); }, [client]);
  const setMature = useCallback(async (value: boolean) => {
    if (user) {
      try { await api.updateMe({ show_mature: value }); await refresh(); showToast("Mature content preference saved", "success"); }
      catch { showToast("Could not save preference", "error"); }
    } else { localStorage.setItem(STORAGE_KEY, String(value)); setLocalMature(value); }
    await client.invalidateQueries({ queryKey: ["anime"] });
    await client.invalidateQueries({ queryKey: ["similar"] });
  }, [client, refresh, showToast, user]);
  const value = useMemo(() => ({ user: user ?? null, mature, setMature, refresh }), [user, mature, setMature, refresh]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
