import { mockApi } from "../mocks/mockApi";
import type { CurrentUser, LoginPayload, RegisterPayload, SwipePayload, SwipeResponse } from "../types";

// 检查是否启用demo模式
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

const CSRF_COOKIE_NAME = "csrftoken";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);
let cachedCsrfToken: string | null = null;
let csrfFetchPromise: Promise<string | null> | null = null;

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

// 真实API请求函数
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

// 真实API对象
const realApi = {
  listSnapshots: (path: string) => {
    const endpoint = path.startsWith("/games") ? path : `/games/${path}`;
    return request(endpoint);
  },
  createSwipe: (payload: SwipePayload) =>
    request<SwipeResponse>("/swipes/", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  ping: () => request("/health/"),
  currentUser: () => request<CurrentUser>("/auth/me/"),
  login: (payload: LoginPayload) =>
    request<CurrentUser>("/auth/login/", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  register: (payload: RegisterPayload) =>
    request<CurrentUser>("/auth/", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  logout: () =>
    request<CurrentUser>("/auth/logout/", {
      method: "POST"
    })
};

// 导出API对象（根据模式选择真实API或Mock API）
export const api = DEMO_MODE ? mockApi : realApi;
export const IS_DEMO_MODE = DEMO_MODE;

// 在控制台输出当前模式
if (DEMO_MODE) {
  console.log("%c🎭 Demo模式已启用", "color: #10b981; font-size: 16px; font-weight: bold;");
  console.log("%c使用Mock数据，无需后端API", "color: #10b981; font-size: 12px;");
} else {
  console.log("%c🔌 生产模式", "color: #3b82f6; font-size: 16px; font-weight: bold;");
  console.log(`%cAPI地址: ${API_BASE}`, "color: #3b82f6; font-size: 12px;");
}
