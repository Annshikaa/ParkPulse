import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { authApi } from "@/api/auth";
import type { User } from "@/types";

export function useAuth() {
  const { token, user, setAuth, clearAuth, isAuthenticated, isAdmin } = useAuthStore();
  const navigate = useNavigate();

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    const data = res.data;
    // Store token first so the /me request is authenticated
    localStorage.setItem("pp_token", data.access_token);
    const userRes = await authApi.me();
    setAuth(data.access_token, userRes.data);
    return userRes.data;
  };

  const logout = () => {
    clearAuth();
    navigate("/login");
  };

  return { token, user, login, logout, isAuthenticated: isAuthenticated(), isAdmin: isAdmin() };
}
