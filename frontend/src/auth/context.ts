import { createContext } from "react";
import type { UserResponse } from "../api/types";
export type AuthValue = { user: UserResponse | null; authLoading: boolean; mature: boolean; setMature: (value: boolean) => Promise<void>; refresh: () => Promise<void>; signOut: () => Promise<void> };
export const AuthContext = createContext<AuthValue | null>(null);
