// Mock API服务 - 用于demo模式
import { PaginatedResponse, GameSnapshot, SwipePayload, SwipeResponse } from "../types";
import { mockApiResponse, mockSnapshots } from "./mockData";

// 模拟网络延迟
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Mock游戏列表API
export async function mockListSnapshots(path: string): Promise<PaginatedResponse<GameSnapshot>> {
  // 模拟网络延迟（300-800ms之间）
  await delay(Math.random() * 500 + 300);
  
  // 解析查询参数
  const url = new URL(`http://dummy${path}`);
  const date = url.searchParams.get("date");
  const minFollowers = url.searchParams.get("min_followers");
  const tag = url.searchParams.get("tag");
  const category = url.searchParams.get("category");
  const genre = url.searchParams.get("genre");
  
  // 过滤数据（根据参数）
  let filtered = [...mockSnapshots];
  
  if (minFollowers) {
    const min = parseInt(minFollowers);
    filtered = filtered.filter(s => (s.followers || 0) >= min);
  }
  
  if (tag) {
    filtered = filtered.filter(s => 
      s.source_tags.toLowerCase().includes(tag.toLowerCase())
    );
  }
  
  if (category) {
    filtered = filtered.filter(s => 
      s.source_categories.toLowerCase().includes(category.toLowerCase())
    );
  }
  
  if (genre) {
    filtered = filtered.filter(s => 
      s.source_genres.toLowerCase().includes(genre.toLowerCase())
    );
  }
  
  console.log(`[Mock API] 获取游戏列表: ${filtered.length} 个游戏`, {
    date,
    minFollowers,
    tag,
    category,
    genre
  });
  
  return {
    count: filtered.length,
    next: null,
    previous: null,
    results: filtered
  };
}

// Mock创建滑动操作API
export async function mockCreateSwipe(payload: SwipePayload): Promise<SwipeResponse> {
  // 模拟网络延迟
  await delay(Math.random() * 300 + 200);
  
  console.log(`[Mock API] 记录滑动操作:`, payload);
  
  // 返回mock响应
  return {
    id: Math.floor(Math.random() * 10000),
    user: 1,
    created_at: new Date().toISOString(),
    ...payload
  };
}

// Mock健康检查API
export async function mockPing(): Promise<{ status: string }> {
  await delay(100);
  console.log("[Mock API] 健康检查");
  return { status: "ok" };
}

// Mock API对象
export const mockApi = {
  listSnapshots: mockListSnapshots,
  createSwipe: mockCreateSwipe,
  ping: mockPing
};





