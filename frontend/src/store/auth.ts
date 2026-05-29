import { create } from "zustand";
import type { User } from "@/types";

interface AuthStore {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
  isAuthenticated: () => boolean;
  isAdmin: () => boolean;
}

const storedToken = localStorage.getItem("pp_token");
const storedUser = localStorage.getItem("pp_user");

export const useAuthStore = create<AuthStore>((set, get) => ({
  token: storedToken,
  user: storedUser ? (JSON.parse(storedUser) as User) : null,

  setAuth: (token, user) => {
    localStorage.setItem("pp_token", token);
    localStorage.setItem("pp_user", JSON.stringify(user));
    set({ token, user });
  },

  clearAuth: () => {
    localStorage.removeItem("pp_token");
    localStorage.removeItem("pp_user");
    set({ token: null, user: null });
  },

  isAuthenticated: () => !!get().token,
  isAdmin: () => get().user?.role === "admin",
}));
