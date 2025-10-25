import useSWR from "swr";
import { api } from "../utils/api";
import type { CurrentUser } from "../types";

const CURRENT_USER_KEY = "/auth/me/";

export function useCurrentUser() {
  const { data, error, isLoading, mutate } = useSWR<CurrentUser>(CURRENT_USER_KEY, () =>
    api.currentUser()
  );

  return {
    user: data ?? null,
    isLoading,
    error,
    refresh: mutate
  };
}
