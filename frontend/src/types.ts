export type DetectionStage = "public_unreleased" | "early_stage" | "minimal_data" | string;

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
