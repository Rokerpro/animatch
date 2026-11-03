import { useCallback, useMemo, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { queryKeys, useMe } from "../api/hooks";
import { useToast } from "../components/useToast";
import { AuthContext } from "./context";
export function AuthProvider({ children }: { children: ReactNode }) {
  const { data: user } = useMe();
  const client = useQueryClient(); const { showToast } = useToast();
  const mature = user?.show_mature ?? false;
  const refresh = useCallback(async () => { await client.invalidateQueries({ queryKey: queryKeys.me }); }, [client]);
  const setMature = useCallback(async (value: boolean) => {
    if (!user) return;
    try { await api.updateMe({ show_mature: value }); await refresh(); showToast("Mature content preference saved", "success"); }
    catch { showToast("Could not save preference", "error"); }
    await client.invalidateQueries({ queryKey: ["anime"] });
    await client.invalidateQueries({ queryKey: ["similar"] });
  }, [client, refresh, showToast, user]);
  const value = useMemo(() => ({ user: user ?? null, mature, setMature, refresh }), [user, mature, setMature, refresh]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
