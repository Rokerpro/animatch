import { useCallback, useMemo, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "../api/client";
import { queryKeys, useMe } from "../api/hooks";
import { useToast } from "../components/useToast";
import { AuthContext } from "./context";
import { clearSavedQuiz } from "../quizStorage";
import { clearSavedStart } from "../startStorage";
export function AuthProvider({ children }: { children: ReactNode }) {
  const { data: user, isLoading } = useMe();
  const client = useQueryClient(); const { showToast } = useToast();
  const mature = user?.show_mature ?? false;
  const refresh = useCallback(async () => { await client.invalidateQueries({ queryKey: queryKeys.me }); }, [client]);
  const setMature = useCallback(async (value: boolean) => {
    if (!user) return;
    try { await api.updateMe({ show_mature: value }); await refresh(); showToast("Mature content preference saved", "success"); }
    catch (error) { showToast(getErrorMessage(error, "Could not save preference"), "error"); }
    await client.invalidateQueries({ queryKey: ["anime"] });
    await client.invalidateQueries({ queryKey: ["similar"] });
  }, [client, refresh, showToast, user]);
  const signOut = useCallback(async () => {
    try { await api.logout(); } finally {
      clearSavedQuiz(); clearSavedStart();
      client.setQueryData(queryKeys.me, null);
      await client.invalidateQueries();
    }
  }, [client]);
  const value = useMemo(() => ({ user: user ?? null, authLoading: isLoading, mature, setMature, refresh, signOut }), [user, isLoading, mature, setMature, refresh, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
