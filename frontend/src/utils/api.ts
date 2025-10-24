import { mockApi } from "../mocks/mockApi";
import type { SwipePayload, SwipeResponse } from "../types";

// 检查是否启用demo模式
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

// 真实API请求函数
async function request<T>(endpoint: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
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
  ping: () => request("/health/")
};

// 导出API对象（根据模式选择真实API或Mock API）
export const api = DEMO_MODE ? mockApi : realApi;

// 在控制台输出当前模式
if (DEMO_MODE) {
  console.log("%c🎭 Demo模式已启用", "color: #10b981; font-size: 16px; font-weight: bold;");
  console.log("%c使用Mock数据，无需后端API", "color: #10b981; font-size: 12px;");
} else {
  console.log("%c🔌 生产模式", "color: #3b82f6; font-size: 16px; font-weight: bold;");
  console.log(`%cAPI地址: ${API_BASE}`, "color: #3b82f6; font-size: 12px;");
}
