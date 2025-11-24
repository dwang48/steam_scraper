import { mockApi } from "../mocks/mockApi";
import type {
  CurrentUser,
  DailySummary,
  LeaderboardStats,
  LoginPayload,
  PaginatedResponse,
  RegisterPayload,
  RegisterResponse,
  SwipeActionRecord,
  SwipePayload,
  SwipeResponse,
  SwipeActionType
} from "../types";

// Determine whether we should use demo mode
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

const CSRF_COOKIE_NAME = "csrftoken";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);
let cachedCsrfToken: string | null = null;
let csrfFetchPromise: Promise<string | null> | null = null;

function buildQuery(params?: Record<string, string | number | undefined | null>) {
  if (!params) {
    return "";
  }
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    searchParams.set(key, String(value));
  });
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }
  const cookieString = document.cookie;
  if (!cookieString) {
    return null;
  }
  const cookies = cookieString.split(";").map((cookie) => cookie.trim());
  for (const cookie of cookies) {
    if (cookie.startsWith(`${name}=`)) {
      return decodeURIComponent(cookie.substring(name.length + 1));
    }
  }
  return null;
}

async function ensureCsrfToken(): Promise<string | null> {
  const cookieToken = getCookie(CSRF_COOKIE_NAME);
  if (cookieToken && cookieToken !== cachedCsrfToken) {
    cachedCsrfToken = cookieToken;
    return cookieToken;
  }
  if (cachedCsrfToken) {
    return cachedCsrfToken;
  }

  if (!csrfFetchPromise) {
    csrfFetchPromise = fetch(`${API_BASE}/auth/csrf/`, {
      credentials: "include"
    })
      .then(async (response) => {
        if (!response.ok) {
          const errorText = await response.text().catch(() => "");
          throw new Error(errorText || `Failed to fetch CSRF token (${response.status})`);
        }
        try {
          const payload = await response.json();
          return payload?.csrfToken ?? null;
        } catch {
          return null;
        }
      })
      .catch((error) => {
        console.error("CSRF token fetch failed:", error);
        return null;
      })
      .finally(() => {
        csrfFetchPromise = null;
      });
  }

  const token = await csrfFetchPromise;
  const refreshedToken = getCookie(CSRF_COOKIE_NAME) ?? token;
  cachedCsrfToken = refreshedToken;
  return cachedCsrfToken;
}

// Low-level helper for authenticated API requests
async function request<T>(endpoint: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (!SAFE_METHODS.has(method)) {
    const csrfToken = await ensureCsrfToken();
    if (csrfToken) {
      headers.set("X-CSRFToken", csrfToken);
    }
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    credentials: "include",
    ...init,
    headers
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

// Real API surface used outside demo mode
const realApi = {
  listSnapshots: (path: string) => {
    const endpoint = path.startsWith("/games") ? path : `/games/${path}`;
    return request(endpoint);
  },
  listSwipes: (params?: Record<string, string | number | undefined | null>) => {
    const query = buildQuery(params);
    return request<PaginatedResponse<SwipeActionRecord>>(`/swipes/${query}`);
  },
  createSwipe: (payload: SwipePayload) =>
    request<SwipeResponse>("/swipes/", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  exportLikesCsv: async (params?: { action?: SwipeActionType; ids?: string | number[]; date?: string }) => {
    const idsParam = Array.isArray(params?.ids)
      ? params?.ids.join(",")
      : params?.ids
      ? String(params.ids)
      : undefined;
    const query = buildQuery({
      action: params?.action ?? "like",
      ids: idsParam,
      date: params?.date
    });
    const response = await fetch(`${API_BASE}/swipes/export/${query}`, {
      credentials: "include"
    });
    if (!response.ok) {
      const message = await response.text().catch(() => "");
      throw new Error(message || `Export failed (${response.status})`);
    }
    return response.blob();
  },
  ping: () => request("/health/"),
  currentUser: () => request<CurrentUser>("/auth/me/"),
  dailySummary: (params?: { date?: string; window?: "day" | "week" | "month" }) => {
    const query = buildQuery(params);
    return request<DailySummary>(`/reports/daily-summary/${query}`);
  },
  leaderboardStats: (params?: { date?: string; window?: "day" | "week" | "month" }) => {
    const query = buildQuery(params);
    return request<LeaderboardStats>(`/reports/leaderboard/${query}`);
  },
  login: (payload: LoginPayload) =>
    request<CurrentUser>("/auth/login/", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  register: (payload: RegisterPayload) =>
    request<RegisterResponse>("/auth/", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  logout: () =>
    request<CurrentUser>("/auth/logout/", {
      method: "POST"
    })
};

// Expose either the real API or the mock API depending on mode
export const api = DEMO_MODE ? mockApi : realApi;
export const IS_DEMO_MODE = DEMO_MODE;

// Log the active mode for quick diagnostics
if (DEMO_MODE) {
  console.log("%c🎭 Demo mode enabled", "color: #10b981; font-size: 16px; font-weight: bold;");
  console.log("%cMock data in use, no backend API required", "color: #10b981; font-size: 12px;");
} else {
  console.log("%c🔌 Production mode", "color: #3b82f6; font-size: 16px; font-weight: bold;");
  console.log(`%cAPI base: ${API_BASE}`, "color: #3b82f6; font-size: 12px;");
}
