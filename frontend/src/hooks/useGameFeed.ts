import useSWR from "swr";
import { useMemo } from "react";
import { GameSnapshot, PaginatedResponse } from "../types";
import { api } from "../utils/api";

interface UseGameFeedParams {
  date: string;
  minFollowers?: number;
  tag?: string;
  category?: string;
  genre?: string;
}

export function useGameFeed(params: UseGameFeedParams) {
  const query = useMemo(() => {
    const searchParams = new URLSearchParams({ date: params.date });
    if (params.minFollowers) searchParams.set("min_followers", String(params.minFollowers));
    if (params.tag) searchParams.set("tag", params.tag);
    if (params.category) searchParams.set("category", params.category);
    if (params.genre) searchParams.set("genre", params.genre);
    return `?${searchParams.toString()}`;
  }, [params.date, params.minFollowers, params.tag, params.category, params.genre]);

  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<GameSnapshot>>(
    `/games/${query}`,
    (path: string) => api.listSnapshots(path) as Promise<PaginatedResponse<GameSnapshot>>
  );

  return {
    snapshots: data?.results ?? [],
    isLoading,
    error,
    mutate,
    total: data?.count ?? 0
  };
}
