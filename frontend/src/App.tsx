import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { format, subDays, addDays, isAfter, parseISO } from "date-fns";
import { AnimatePresence, motion } from "framer-motion";
import { TopBar } from "./components/TopBar";
import { CardStack } from "./components/CardStack";
import { DetailSheet } from "./components/DetailSheet";
import { ActionBar } from "./components/ActionBar";
import { AuthDialog } from "./components/AuthDialog";
import { PrimaryNav, AppView } from "./components/PrimaryNav";
import { TeamLikesView } from "./components/TeamLikesView";
import { LeaderboardView } from "./components/LeaderboardView";
import { MyLikesView } from "./components/MyLikesView";
import { useGameFeed } from "./hooks/useGameFeed";
import { useSwipe } from "./hooks/useSwipe";
import { useCurrentUser } from "./hooks/useCurrentUser";
import { GameSnapshot, LoginPayload, RegisterPayload, SwipeActionType } from "./types";
import { api, IS_DEMO_MODE } from "./utils/api";
import { LikeReasonDialog } from "./components/LikeReasonDialog";
import { getSteamStoreUrl } from "./utils/steamAssets";

type SwipeOutcome = { success: boolean; advance?: boolean };

function initialActiveDate() {
  if (IS_DEMO_MODE) {
    return "2025-10-13";
  }
  return format(new Date(), "yyyy-MM-dd");
}

export default function App() {
  const [activeDate, setActiveDate] = useState(initialActiveDate);
  const [activeSnapshot, setActiveSnapshot] = useState<GameSnapshot | null>(null);
  const [toast, setToast] = useState<{ message: string; tone: "positive" | "neutral" } | null>(null);
  const [cursor, setCursor] = useState(0);
  const toastTimer = useRef<number | null>(null);
  const [isAuthOpen, setAuthOpen] = useState(false);
  const [signOutPending, setSignOutPending] = useState(false);
  const [activeView, setActiveView] = useState<AppView>("daily");
  const [likeDialogOpen, setLikeDialogOpen] = useState(false);
  const [likeDialogTarget, setLikeDialogTarget] = useState<GameSnapshot | null>(null);
  const [isSavingLike, setSavingLike] = useState(false);
  const [showHandled, setShowHandled] = useState(false);
  const [autoOpenStorefront, setAutoOpenStorefront] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.localStorage.getItem("auto-open-storefront") === "1";
    } catch {
      return false;
    }
  });
  const lastAutoOpenedIdRef = useRef<number | null>(null);

  // Parse at midday to avoid timezone drifting the intended date
  const dateObj = useMemo(() => parseISO(activeDate + "T12:00:00"), [activeDate]);
  const todayDate = useMemo(() => parseISO(format(new Date(), "yyyy-MM-dd") + "T12:00:00"), []);

  const {
    user: currentUser,
    isLoading: isUserLoading,
    refresh: refreshCurrentUser
  } = useCurrentUser();

  const excludeHandled = currentUser?.is_authenticated ? !showHandled : false;

  const { snapshots, isLoading, error, mutate, total } = useGameFeed({
    date: activeDate,
    excludeHandled
  });

  const currentSnapshot = snapshots[cursor] ?? null;
  const isDailyView = activeView === "daily";

  const pendingCount = useMemo(() => {
    if (excludeHandled) {
      return total;
    }
    return snapshots.filter((snapshot) => !snapshot.handled).length;
  }, [excludeHandled, total, snapshots]);

  const handledCount = useMemo(() => {
    if (excludeHandled) {
      return 0;
    }
    return Math.max(0, total - pendingCount);
  }, [excludeHandled, total, pendingCount]);

  const handleToggleShowHandled = useCallback(() => {
    setShowHandled((prev) => !prev);
    setActiveSnapshot(null);
    setCursor(0);
  }, []);

  useEffect(() => {
    setCursor((prev) => {
      if (snapshots.length === 0) {
        return 0;
      }
      const maxIndex = snapshots.length - 1;
      return Math.min(prev, maxIndex);
    });
  }, [snapshots.length]);

  useEffect(() => {
    setCursor(0);
  }, [activeDate]);

  const clearToastTimer = useCallback(() => {
    if (toastTimer.current) {
      window.clearTimeout(toastTimer.current);
      toastTimer.current = null;
    }
  }, []);

  useEffect(() => clearToastTimer, [clearToastTimer]);
  useEffect(() => {
    if (activeView !== "daily") {
      setActiveSnapshot(null);
      setToast(null);
    }
  }, [activeView]);

  const showToast = useCallback(
    (message: string, tone: "positive" | "neutral", duration = 2000) => {
      clearToastTimer();
      setToast({ message, tone });
      toastTimer.current = window.setTimeout(() => {
        setToast(null);
        toastTimer.current = null;
      }, duration);
    },
    [clearToastTimer]
  );

  const { submit, isSubmitting } = useSwipe();
  const handleRequireSignIn = useCallback(() => {
    setAuthOpen(true);
  }, []);

  useEffect(() => {
    if (!currentUser?.is_authenticated && showHandled) {
      setShowHandled(false);
    }
  }, [currentUser?.is_authenticated, showHandled]);

  const handleChangeDate = useCallback(
    (direction: "prev" | "next") => {
      const nextDate = direction === "prev" ? subDays(dateObj, 1) : addDays(dateObj, 1);
      if (direction === "next" && isAfter(nextDate, todayDate)) return;
      setActiveDate(format(nextDate, "yyyy-MM-dd"));
      setActiveSnapshot(null);
      setCursor(0);
    },
    [dateObj, todayDate]
  );

  const handleSelectDate = useCallback(
    (nextDateStr: string) => {
      if (!nextDateStr) return;
      const parsed = parseISO(nextDateStr + "T12:00:00");
      if (isAfter(parsed, todayDate)) return;
      setActiveDate(format(parsed, "yyyy-MM-dd"));
      setActiveSnapshot(null);
      setCursor(0);
    },
    [todayDate]
  );

  const handleSwipe = useCallback(
    async (
      snapshot: GameSnapshot,
      action: SwipeActionType,
      note?: string,
      options?: { advanceCursor?: boolean; message?: string; tone?: "positive" | "neutral" }
    ): Promise<SwipeOutcome> => {
      if (!currentUser?.is_authenticated) {
        showToast("Please sign in to record actions.", "neutral", 2600);
        setAuthOpen(true);
        return { success: false, advance: false };
      }

      const advancePreference = options?.advanceCursor ?? true;
      try {
        await submit({
          game: snapshot.game.id,
          batch: snapshot.batch_id,
          action,
          note
        });

        const handledAt = new Date().toISOString();
        await mutate(
          (current) => {
            if (!current) return current;
            const results = current.results ?? [];
            if (excludeHandled) {
              const filtered = results.filter((item) => item.id !== snapshot.id);
              const nextCount = typeof current.count === "number" ? Math.max(0, current.count - 1) : current.count;
              return {
                ...current,
                results: filtered,
                count: nextCount
              };
            }
            const nextResults = results.map((item) =>
              item.id === snapshot.id
                ? {
                    ...item,
                    handled: true,
                    user_action: action,
                    user_note: note ?? null,
                    user_handled_at: handledAt
                  }
                : item
            );
            return {
              ...current,
              results: nextResults
            };
          },
          { revalidate: false }
        );
        void mutate();

        const message =
          options?.message ??
          (action === "like"
            ? `${snapshot.game.name} added to favorites.`
            : action === "skip"
            ? `Skipped ${snapshot.game.name}.`
            : "Watchlist updated.");
        const tone: "positive" | "neutral" =
          options?.tone ??
          (action === "like" || action === "watchlist" ? "positive" : "neutral");
        const duration = action === "skip" ? 1800 : 2000;
        showToast(message, tone, duration);

        if (advancePreference || excludeHandled) {
          setActiveSnapshot((current) => (current?.id === snapshot.id ? null : current));
        }

        return { success: true, advance: excludeHandled ? false : advancePreference };
      } catch (err) {
        console.error("Swipe error", err);
        showToast("Could not sync action.", "neutral", 2600);
        return { success: false, advance: false };
      }
    },
    [submit, showToast, currentUser, mutate, excludeHandled]
  );

  const handleActionBarSwipe = useCallback(
    async (action: SwipeActionType) => {
      if (!currentSnapshot) return;
      const outcome = await handleSwipe(currentSnapshot, action);
      if (!outcome.success) return;
      const shouldAdvance = outcome.advance ?? outcome.success;
      if (shouldAdvance) {
        setCursor((prev) => prev + 1);
      }
    },
    [currentSnapshot, handleSwipe]
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem("auto-open-storefront", autoOpenStorefront ? "1" : "0");
    } catch {
      // Ignore storage errors (e.g., private browsing)
    }
  }, [autoOpenStorefront]);

  useEffect(() => {
    if (!isDailyView) return;
    if (!autoOpenStorefront) return;
    if (!currentSnapshot) return;
    if (lastAutoOpenedIdRef.current === currentSnapshot.id) return;
    const storeUrl = getSteamStoreUrl(currentSnapshot.game.steam_appid, currentSnapshot.game.steam_url);
    if (!storeUrl) return;
    const isDesktop = typeof window !== "undefined" ? window.matchMedia?.("(min-width: 1024px)")?.matches ?? true : false;
    if (!isDesktop) return;
    window.open(storeUrl, "_blank", "noopener,noreferrer");
    lastAutoOpenedIdRef.current = currentSnapshot.id;
  }, [autoOpenStorefront, currentSnapshot, isDailyView]);

  const handleToggleAutoOpen = useCallback(() => {
    lastAutoOpenedIdRef.current = null;
    setAutoOpenStorefront((prev) => !prev);
  }, []);

  const handleRequestLike = useCallback(
    (snapshot: GameSnapshot | null) => {
      if (!snapshot) return;
      if (!currentUser?.is_authenticated) {
        showToast("Please sign in to record actions.", "neutral", 2600);
        setAuthOpen(true);
        return;
      }
      setLikeDialogTarget(snapshot);
      setLikeDialogOpen(true);
    },
    [currentUser, showToast]
  );

  const handleLikeSubmit = useCallback(
    async (note: string) => {
      if (!likeDialogTarget) return;
      setSavingLike(true);
      const outcome = await handleSwipe(likeDialogTarget, "like", note, { advanceCursor: true });
      setSavingLike(false);
      if (!outcome.success) return;
      setLikeDialogOpen(false);
      setLikeDialogTarget(null);
      const shouldAdvance = outcome.advance ?? outcome.success;
      if (shouldAdvance) {
        setCursor((prev) => prev + 1);
      }
    },
    [likeDialogTarget, handleSwipe]
  );


  const handleLogin = useCallback(
    async (payload: LoginPayload) => {
      try {
        await api.login(payload);
        await refreshCurrentUser();
        showToast("Signed in successfully.", "positive");
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
        throw new Error("Unable to sign in.");
      }
    },
    [refreshCurrentUser, showToast]
  );

  const handleRegister = useCallback(
    async (payload: RegisterPayload) => {
      try {
        await api.register(payload);
        await refreshCurrentUser();
        showToast("Welcome aboard!", "positive");
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
        throw new Error("Unable to register.");
      }
    },
    [refreshCurrentUser, showToast]
  );

  const handleSignOut = useCallback(async () => {
    try {
      setSignOutPending(true);
      await api.logout();
      await refreshCurrentUser();
      showToast("Signed out.", "neutral", 2000);
    } catch (error) {
      console.error("Sign out failed", error);
      showToast("Sign out failed. Try again.", "neutral", 2600);
    } finally {
      setSignOutPending(false);
    }
  }, [refreshCurrentUser, showToast]);

  return (
    <div className="min-h-screen bg-transparent">
      <PrimaryNav activeView={activeView} onChange={setActiveView} />
      <div className="pb-16">
        {isDailyView ? (
          <div className="mx-auto flex w-full max-w-screen-2xl flex-col px-3 sm:px-6 lg:px-10">
            <TopBar
              date={dateObj}
              dateValue={activeDate}
              total={pendingCount}
              onChangeDate={handleChangeDate}
              onSelectDate={handleSelectDate}
              disableNext={!isAfter(todayDate, dateObj)}
              user={currentUser}
              loadingUser={isUserLoading}
              onSignIn={handleRequireSignIn}
              onSignOut={handleSignOut}
              signOutInFlight={signOutPending}
              showingHandled={showHandled}
              handledCount={handledCount}
              onToggleShowHandled={currentUser?.is_authenticated ? handleToggleShowHandled : undefined}
              maxDate={format(todayDate, "yyyy-MM-dd")}
              autoOpenStorefront={autoOpenStorefront}
              onToggleAutoOpen={handleToggleAutoOpen}
            />
            <main className="flex-1 py-2 sm:py-6 flex flex-col gap-3 sm:gap-6">
              <section className="relative flex-1 min-h-[520px] sm:min-h-[640px] lg:min-h-[720px] max-w-6xl mx-auto w-full pb-28 lg:pb-32">
                {isLoading && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center glass-panel">
                    <LoadingSpinner />
                    <p className="mt-4 text-sm text-mist-subtle/70">Preparing today&apos;s discoveries…</p>
                  </div>
                )}
                {!isLoading && error && (
                  <div className="absolute inset-0 glass-panel flex flex-col items-center justify-center text-center px-6">
                    <p className="text-sm text-mist-subtle/70">We couldn&apos;t reach the curator service.</p>
                    <button
                      onClick={() => mutate()}
                      className="mt-4 text-sm text-accent hover:text-white transition"
                    >
                      Try again
                    </button>
                  </div>
                )}
                {!isLoading && !error && (
                  <div className="absolute inset-0">
                    <CardStack
                      snapshots={snapshots}
                      activeIndex={cursor}
                      onActiveIndexChange={(index) => setCursor(index)}
                      onSwipe={handleSwipe}
                      onOpenDetails={(snapshot) => setActiveSnapshot(snapshot)}
                    />
                  </div>
                )}
              </section>
            </main>

            {!activeSnapshot && (
              <div className="sticky bottom-0 z-30 pt-2 bg-gradient-to-t from-ink/95 via-ink/60 to-transparent">
                <ActionBar
                  snapshot={currentSnapshot}
                  onLike={() => handleRequestLike(currentSnapshot)}
                  onSkip={() => handleActionBarSwipe("skip")}
                  onDetails={() => setActiveSnapshot(currentSnapshot)}
                  disabled={isSubmitting}
                />
              </div>
            )}

            <DetailSheet snapshot={activeSnapshot} open={!!activeSnapshot} onOpenChange={(open) => !open && setActiveSnapshot(null)} />

            <AnimatePresence>
              {toast && (
                <motion.div
                  className="fixed bottom-24 left-1/2 -translate-x-1/2 glass-panel px-4 py-3 text-sm text-mist-subtle/90"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 20 }}
                >
                  {toast.message}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ) : activeView === "team" ? (
          <TeamLikesView
            isAuthenticated={Boolean(currentUser?.is_authenticated)}
            onRequireSignIn={handleRequireSignIn}
          />
        ) : activeView === "leaderboard" ? (
          <LeaderboardView
            isAuthenticated={Boolean(currentUser?.is_authenticated)}
            onRequireSignIn={handleRequireSignIn}
          />
        ) : (
          <MyLikesView
            isAuthenticated={Boolean(currentUser?.is_authenticated)}
            onRequireSignIn={handleRequireSignIn}
          />
        )}
      </div>

      <AuthDialog
        open={isAuthOpen}
        onOpenChange={setAuthOpen}
        onLogin={handleLogin}
        onRegister={handleRegister}
      />
      <LikeReasonDialog
        open={likeDialogOpen}
        onOpenChange={(open) => {
          if (isSavingLike) return;
          if (!open) {
            setLikeDialogOpen(false);
            setLikeDialogTarget(null);
          } else {
            setLikeDialogOpen(true);
          }
        }}
        defaultNote={""}
        onSubmit={handleLikeSubmit}
        onSkip={() => handleLikeSubmit("")}
        submitting={isSavingLike}
      />
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="relative">
      <motion.span
        className="block w-10 h-10 rounded-full border-2 border-white/10 border-t-white/70"
        animate={{ rotate: 360 }}
        transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
      />
    </div>
  );
}
