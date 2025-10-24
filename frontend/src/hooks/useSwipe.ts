import { useState } from "react";
import { mutate as globalMutate } from "swr";
import { SwipePayload, SwipeResponse } from "../types";
import { api } from "../utils/api";

interface UseSwipeOptions {
  onSuccess?: (response: SwipeResponse) => void;
  onError?: (error: Error) => void;
}

export function useSwipe(options?: UseSwipeOptions) {
  const [isSubmitting, setSubmitting] = useState(false);

  const submit = async (payload: SwipePayload) => {
    try {
      setSubmitting(true);
      const response = await api.createSwipe(payload);
      globalMutate("/swipes/");
      options?.onSuccess?.(response);
      return response;
    } catch (error) {
      options?.onError?.(error as Error);
      throw error;
    } finally {
      setSubmitting(false);
    }
  };

  return {
    submit,
    isSubmitting
  };
}
