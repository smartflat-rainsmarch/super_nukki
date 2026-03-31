const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  plan_type: string;
  name: string | null;
  profile_image: string | null;
  auth_provider: string;
}

export interface UserInfo {
  id: string;
  email: string;
  plan_type: string;
  name: string | null;
  profile_image: string | null;
  auth_provider: string;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function setToken(token: string): void {
  localStorage.setItem("access_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("access_token");
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

// --- Email Auth ---

export async function register(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Registration failed" }));
    throw new Error(err.detail ?? "Registration failed");
  }

  const data: AuthResponse = await res.json();
  setToken(data.access_token);
  return data;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail ?? "Login failed");
  }

  const data: AuthResponse = await res.json();
  setToken(data.access_token);
  return data;
}

// --- Social Auth ---

export async function getGoogleLoginUrl(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/auth/google/url`);
  const data = await res.json();
  return data.url;
}

export async function getKakaoLoginUrl(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/auth/kakao/url`);
  const data = await res.json();
  return data.url;
}

export async function handleOAuthCallback(
  code: string,
  provider: string,
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/${provider}/callback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "OAuth login failed" }));
    throw new Error(err.detail ?? "OAuth login failed");
  }

  const data: AuthResponse = await res.json();
  setToken(data.access_token);
  return data;
}

// --- User ---

export async function getMe(): Promise<UserInfo | null> {
  const token = getToken();
  if (!token) return null;

  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) return null;
  return res.json();
}

export function logout(): void {
  clearToken();
  window.location.href = "/";
}
