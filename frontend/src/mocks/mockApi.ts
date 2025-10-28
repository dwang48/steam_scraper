// Mock API服务 - 用于demo模式
import {
  PaginatedResponse,
  GameSnapshot,
  SwipePayload,
  SwipeResponse,
  CurrentUser,
  LoginPayload,
  RegisterPayload,
  SwipeActionRecord,
  DailySummary,
  UserSummary,
  LeaderboardStats
} from "../types";
import { mockSnapshots } from "./mockData";

// 模拟网络延迟
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const demoUser: CurrentUser = {
  id: 1,
  username: "demo",
  email: "demo@example.com",
  first_name: "Demo",
  last_name: "User",
  display_name: "Demo User",
  is_authenticated: true
};

let mockSignedIn = true;

const mockTeamMembers: UserSummary[] = [
  {
    id: 1,
    username: "demo",
    first_name: "Demo",
    last_name: "User",
    display_name: "Demo User"
  },
  {
    id: 2,
    username: "mira",
    first_name: "Mira",
    last_name: "Chen",
    display_name: "Mira Chen"
  },
  {
    id: 3,
    username: "liang",
    first_name: "Liang",
    last_name: "Hu",
    display_name: "Liang Hu"
  }
];

const mockSwipeHistory: SwipeActionRecord[] = mockSnapshots.slice(0, 8).map((snapshot, index) => ({
  id: index + 1,
  user: mockTeamMembers[0],
  game: snapshot.game.id,
  game_detail: snapshot.game,
  batch: snapshot.batch_id ?? null,
  action: "like",
  note: "",
  created_at: new Date(Date.now() - index * 3600 * 1000).toISOString()
}));

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

// Mock当前用户信息
export async function mockCurrentUser(): Promise<CurrentUser> {
  await delay(120);
  return mockSignedIn ? demoUser : { is_authenticated: false };
}

export async function mockLogin(_payload: LoginPayload): Promise<CurrentUser> {
  await delay(200);
  mockSignedIn = true;
  return demoUser;
}

export async function mockRegister(payload: RegisterPayload): Promise<CurrentUser> {
  await delay(300);
  mockSignedIn = true;
  return {
    ...demoUser,
    username: payload.username,
    email: payload.email,
    first_name: payload.first_name || demoUser.first_name,
    last_name: payload.last_name || demoUser.last_name
  };
}

export async function mockLogout(): Promise<CurrentUser> {
  await delay(150);
  mockSignedIn = false;
  return { is_authenticated: false };
}

export async function mockListSwipes(): Promise<PaginatedResponse<SwipeActionRecord>> {
  await delay(180);
  return {
    count: mockSwipeHistory.length,
    next: null,
    previous: null,
    results: mockSwipeHistory
  };
}

export async function mockDailySummary(params?: { date?: string; window?: "day" | "week" | "month" }): Promise<DailySummary> {
  await delay(220);
  const targetDate = params?.date ?? new Date().toISOString().slice(0, 10);
  const windowValue = params?.window ?? "day";
  const target = new Date(`${targetDate}T12:00:00`);
  const startDate = new Date(target);
  const endDate = new Date(target);
  if (windowValue === "week") {
    startDate.setDate(startDate.getDate() - 6);
  } else if (windowValue === "month") {
    startDate.setDate(1);
    const month = target.getMonth();
    const year = target.getFullYear();
    const lastDay = new Date(year, month + 1, 0).getDate();
    endDate.setDate(lastDay);
  }
  const games = mockSnapshots.slice(0, 6).map((snapshot, index) => {
    const likeUsers = mockTeamMembers.slice(0, (index % mockTeamMembers.length) + 1);
    const watchlistUsers = index % 3 === 0 ? [mockTeamMembers[2]] : [];
    return {
      game: snapshot.game,
      like_users: likeUsers,
      skip_users: [],
      watchlist_users: watchlistUsers,
      total_actions: likeUsers.length + watchlistUsers.length
    };
  });
  const likeCount = games.reduce((acc, entry) => acc + entry.like_users.length, 0);
  const watchlistCount = games.reduce((acc, entry) => acc + entry.watchlist_users.length, 0);

  return {
    date: targetDate,
    window: windowValue,
    start_date: startDate.toISOString().slice(0, 10),
    end_date: endDate.toISOString().slice(0, 10),
    total_actions: likeCount + watchlistCount,
    unique_users: mockTeamMembers.length,
    like_count: likeCount,
    skip_count: 0,
    watchlist_count: watchlistCount,
    games
  };
}

export async function mockLeaderboardStats(params?: { date?: string; window?: "day" | "week" | "month" }): Promise<LeaderboardStats> {
  await delay(180);
  const targetDate = params?.date ?? new Date().toISOString().slice(0, 10);
  const windowValue = params?.window ?? "day";
  const target = new Date(`${targetDate}T12:00:00`);
  const startDate = new Date(target);
  const endDate = new Date(target);
  if (windowValue === "week") {
    startDate.setDate(startDate.getDate() - 6);
  } else if (windowValue === "month") {
    startDate.setDate(1);
    const month = target.getMonth();
    const year = target.getFullYear();
    const lastDay = new Date(year, month + 1, 0).getDate();
    endDate.setDate(lastDay);
  }

  const member_stats = mockTeamMembers.map((member, index) => {
    const handled = 12 - index * 3;
    const likeCount = Math.max(2, handled - 5 - index);
    const skipCount = Math.max(0, index * 2);
    const watchlistCount = Math.max(0, handled - likeCount - skipCount);
    return {
      user: member,
      handled_games: handled,
      like_count: likeCount,
      skip_count: skipCount,
      watchlist_count: watchlistCount,
      total_actions: handled,
      last_action_at: new Date(Date.now() - index * 7200 * 1000).toISOString()
    };
  });

  const overlap_pairs = [
    {
      user_a: mockTeamMembers[0],
      user_b: mockTeamMembers[1],
      shared_likes: 5,
      union_size: 8,
      jaccard: 5 / 8
    },
    {
      user_a: mockTeamMembers[0],
      user_b: mockTeamMembers[2],
      shared_likes: 3,
      union_size: 9,
      jaccard: 3 / 9
    }
  ];

  return {
    date: targetDate,
    window: windowValue,
    start_date: startDate.toISOString().slice(0, 10),
    end_date: endDate.toISOString().slice(0, 10),
    total_actions: member_stats.reduce((acc, item) => acc + item.total_actions, 0),
    unique_games: 18,
    member_count: member_stats.length,
    member_stats,
    overlap_pairs
  };
}

// Mock API对象
export const mockApi = {
  listSnapshots: mockListSnapshots,
  listSwipes: mockListSwipes,
  createSwipe: mockCreateSwipe,
  ping: mockPing,
  currentUser: mockCurrentUser,
  dailySummary: mockDailySummary,
  leaderboardStats: mockLeaderboardStats,
  login: mockLogin,
  register: mockRegister,
  logout: mockLogout
};
