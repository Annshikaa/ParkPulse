import client from "./client";
import type { User } from "@/types";

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  role: string;
  full_name: string;
}

export const authApi = {
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    phone: string;
    license_plate?: string;
    make_model?: string;
    color?: string;
  }) => client.post<AuthResponse>("/auth/register", data),

  login: (email: string, password: string) =>
    client.post<AuthResponse>("/auth/login", { email, password }),

  logout: () => client.post("/auth/logout"),

  me: () => client.get<User>("/auth/me"),
};
