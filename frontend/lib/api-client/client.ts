import { useAuthStore } from "@/lib/stores/auth";

import type {
  InstrumentsResponse,
  LoginResponse,
  OhlcvResponse,
  SettingsResponse,
  UserProfile,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8100/api/v1";

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().token;
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    let code = "unknown_error";
    let message = response.statusText;
    try {
      const body = await response.json();
      code = body?.error?.code ?? code;
      message = body?.error?.message ?? message;
    } catch {
      // Non-JSON error body: keep the HTTP status text.
    }
    if (response.status === 401) {
      useAuthStore.getState().setToken(null);
    }
    throw new ApiRequestError(response.status, code, message);
  }
  return response.json();
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(): Promise<UserProfile> {
  return request("/auth/me");
}

export function getSettings(): Promise<SettingsResponse> {
  return request("/settings");
}

export function updateSetting(
  key: string,
  value: string,
): Promise<SettingsResponse> {
  return request(`/settings/${encodeURIComponent(key)}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}

export function getInstruments(): Promise<InstrumentsResponse> {
  return request("/instruments");
}

export function getOhlcv(
  instrumentId: number,
  timeframe: string,
  from: Date,
  to: Date,
  limit = 500,
): Promise<OhlcvResponse> {
  const params = new URLSearchParams({
    timeframe,
    from: from.toISOString(),
    to: to.toISOString(),
    limit: String(limit),
  });
  return request(`/instruments/${instrumentId}/ohlcv?${params}`);
}
