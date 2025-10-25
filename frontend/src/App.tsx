import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { format, subDays, addDays, isAfter, parseISO } from "date-fns";
import { AnimatePresence, motion } from "framer-motion";
import { TopBar } from "./components/TopBar";
import { CardStack } from "./components/CardStack";
import { DetailSheet } from "./components/DetailSheet";
import { ActionBar } from "./components/ActionBar";
import { AuthDialog } from "./components/AuthDialog";
import { useGameFeed } from "./hooks/useGameFeed";
import { useSwipe } from "./hooks/useSwipe";
import { useCurrentUser } from "./hooks/useCurrentUser";
import { GameSnapshot, LoginPayload, RegisterPayload, SwipeActionType } from "./types";
import { api, IS_DEMO_MODE } from "./utils/api";

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

  // 使用 parseISO 正确解析日期字符串，避免时区问题
  const dateObj = useMemo(() => parseISO(activeDate + "T12:00:00"), [activeDate]);
  const todayDate = useMemo(() => parseISO(format(new Date(), "yyyy-MM-dd") + "T12:00:00"), []);

  const { snapshots, isLoading, error, mutate, total } = useGameFeed({
    date: activeDate
  });
  const {
    user: currentUser,
    isLoading: isUserLoading,
    refresh: refreshCurrentUser
  } = useCurrentUser();

  const currentSnapshot = snapshots[cursor] ?? null;

  useEffect(() => {
    setCursor((prev) => {
      if (snapshots.length === 0) {
        return 0;
      }
      return Math.min(prev, snapshots.length - 1);
    });
  }, [snapshots.length]);

  const clearToastTimer = useCallback(() => {
    if (toastTimer.current) {
      window.clearTimeout(toastTimer.current);
      toastTimer.current = null;
    }
  }, []);

  useEffect(() => clearToastTimer, [clearToastTimer]);

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

  const handleSwipe = useCallback(
    async (snapshot: GameSnapshot, action: SwipeActionType) => {
      if (!currentUser?.is_authenticated) {
        showToast("Please sign in to record actions.", "neutral", 2600);
        setAuthOpen(true);
        return false;
      }

      try {
        await submit({
          game: snapshot.game.id,
          batch: snapshot.batch_id,
          action
        });

        if (action === "like") {
          showToast(`${snapshot.game.name} added to favorites.`, "positive");
        } else if (action === "skip") {
          showToast(`Skipped ${snapshot.game.name}.`, "neutral", 1800);
        } else {
          showToast("Watchlist updated.", "positive");
        }

        setActiveSnapshot((current) => (current?.id === snapshot.id ? null : current));
        return true;
      } catch (err) {
        console.error("Swipe error", err);
        showToast("Could not sync action.", "neutral", 2600);
        return false;
      }
    },
    [submit, showToast, currentUser]
  );

  const handleActionBarSwipe = useCallback(
    async (action: SwipeActionType) => {
      if (!currentSnapshot) return;
      const succeeded = await handleSwipe(currentSnapshot, action);
      if (succeeded) {
        setCursor((prev) => prev + 1);
      }
    },
    [currentSnapshot, handleSwipe]
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
    <div className="min-h-screen flex flex-col w-full max-w-lg mx-auto bg-transparent">
      <TopBar
        date={dateObj}
        total={total}
        onChangeDate={handleChangeDate}
        disableNext={!isAfter(todayDate, dateObj)}
        user={currentUser}
        loadingUser={isUserLoading}
        onSignIn={() => setAuthOpen(true)}
        onSignOut={handleSignOut}
        signOutInFlight={signOutPending}
      />
      <main className="flex-1 px-4 py-4 sm:px-6 sm:py-6 flex flex-col gap-6">
        <section className="relative flex-1 min-h-[360px] sm:min-h-[420px] md:aspect-[3/4]">
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
            onLike={() => handleActionBarSwipe("like")}
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

      <AuthDialog
        open={isAuthOpen}
        onOpenChange={setAuthOpen}
        onLogin={handleLogin}
        onRegister={handleRegister}
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
