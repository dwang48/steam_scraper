export type DetectionStage = "public_unreleased" | "early_stage" | "minimal_data" | string;

export interface TrailerVideo {
  id?: number;
  name?: string;
  thumbnail?: string;
  mp4?: string;
  webm?: string;
  highlight?: boolean;
}

export interface UserSummary {
  id?: number;
  username?: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  display_name?: string;
  is_staff?: boolean;
}

export interface GameSummary {
  id: number;
  steam_appid: number;
  name: string;
  steam_url: string;
  website: string;
  developers: string;
  publishers: string;
  categories: string;
  genres: string;
  tags: string;
  latest_release_date: string;
  latest_detection_stage: DetectionStage;
  latest_api_response_type: string;
  capsule_image_url?: string;
  header_image_url?: string;
  background_image_url?: string;
  screenshot_urls?: string[];
  trailer_videos?: TrailerVideo[];
}

export interface GameSnapshot {
  id: number;
  game: GameSummary;
  batch_id: number;
  detection_stage: DetectionStage;
  api_response_type: string;
  potential_duplicate: boolean;
  discovery_date: string | null;
  ingested_for_date: string;
  release_date_raw: string;
  description: string;
  supported_languages: string;
  followers: number | null;
  wishlists_est: number | null;
  wishlist_rank: number | null;
  source_categories: string;
  source_genres: string;
  source_tags: string;
  handled?: boolean | null;
  user_action?: SwipeActionType | null;
  user_note?: string | null;
  user_handled_at?: string | null;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type SwipeActionType = "like" | "skip" | "watchlist";

export interface SwipePayload {
  game: number;
  batch?: number | null;
  action: SwipeActionType;
  note?: string;
}

export interface SwipeResponse extends SwipePayload {
  id: number;
  user: number;
  created_at: string;
}

export interface SwipeActionRecord {
  id: number;
  user: UserSummary | null;
  game: number;
  game_detail?: GameSummary;
  batch: number | null;
  action: SwipeActionType;
  note: string;
  created_at: string;
}

export interface DailySummaryGameEntry {
  game: GameSummary;
  like_users: UserSummary[];
  skip_users: UserSummary[];
  watchlist_users: UserSummary[];
  total_actions: number;
}

export interface DailySummary {
  date: string;
  window: "day" | "week" | "month" | string;
  start_date: string;
  end_date: string;
  total_actions: number;
  unique_users: number;
  like_count: number;
  skip_count: number;
  watchlist_count: number;
  games: DailySummaryGameEntry[];
}

export interface CurrentUser extends UserSummary {
  is_authenticated: boolean;
}

export interface LoginPayload {
  username: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

export interface LeaderboardMemberStat {
  user: UserSummary;
  handled_games: number;
  like_count: number;
  skip_count: number;
  watchlist_count: number;
  total_actions: number;
  last_action_at?: string | null;
}

export interface LikeOverlapEntry {
  user_a: UserSummary;
  user_b: UserSummary;
  shared_likes: number;
  union_size: number;
  jaccard: number;
}

export interface LeaderboardStats {
  date: string;
  window: "day" | "week" | "month" | string;
  start_date: string;
  end_date: string;
  total_actions: number;
  unique_games: number;
  member_count: number;
  member_stats: LeaderboardMemberStat[];
  overlap_pairs: LikeOverlapEntry[];
}
