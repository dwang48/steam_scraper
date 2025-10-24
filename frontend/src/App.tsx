import { useCallback, useEffect, useMemo, useState } from "react";
import { format, subDays, addDays, isAfter, parseISO } from "date-fns";
import { AnimatePresence, motion } from "framer-motion";
import { TopBar } from "./components/TopBar";
import { CardStack } from "./components/CardStack";
import { DetailSheet } from "./components/DetailSheet";
import { ActionBar } from "./components/ActionBar";
import { useGameFeed } from "./hooks/useGameFeed";
import { useSwipe } from "./hooks/useSwipe";
import { GameSnapshot, SwipeActionType } from "./types";

function todayISO() {
  return "2025-10-13"; // 使用有数据的日期
}

export default function App() {
  const [activeDate, setActiveDate] = useState(todayISO);
  const [activeSnapshot, setActiveSnapshot] = useState<GameSnapshot | null>(null);
  const [toast, setToast] = useState<{ message: string; tone: "positive" | "neutral" } | null>(null);
  const [cursor, setCursor] = useState(0);

  // 使用 parseISO 正确解析日期字符串，避免时区问题
  const dateObj = useMemo(() => parseISO(activeDate + "T12:00:00"), [activeDate]);

  const { snapshots, isLoading, error, mutate, total } = useGameFeed({
    date: activeDate
  });

  const currentSnapshot = snapshots[cursor] ?? null;

  useEffect(() => {
    setCursor((prev) => Math.min(prev, snapshots.length));
  }, [snapshots.length]);

  const { submit, isSubmitting } = useSwipe({
    onSuccess: () => {
      setToast({ message: "Saved to your favorites.", tone: "positive" });
      setTimeout(() => setToast(null), 2000);
    },
    onError: (err) => {
      setToast({ message: err.message || "Action failed.", tone: "neutral" });
      setTimeout(() => setToast(null), 2600);
    }
  });

  const handleChangeDate = useCallback(
    (direction: "prev" | "next") => {
      const nextDate = direction === "prev" ? subDays(dateObj, 1) : addDays(dateObj, 1);
      if (direction === "next" && isAfter(nextDate, new Date())) return;
      setActiveDate(format(nextDate, "yyyy-MM-dd"));
      setActiveSnapshot(null);
      setCursor(0);
    },
    [dateObj]
  );

  const handleSwipe = useCallback(
    async (snapshot: GameSnapshot, action: SwipeActionType) => {
      if (action === "like") {
        setToast({ message: `${snapshot.game.name} added to favorites.`, tone: "positive" });
      } else {
        setToast({ message: `Skipped ${snapshot.game.name}.`, tone: "neutral" });
      }

      setTimeout(() => setToast(null), 1800);

      // 立即切换到下一个游戏
      setCursor((prev) => prev + 1);

      try {
        await submit({
          game: snapshot.game.id,
          batch: snapshot.batch_id,
          action
        });
      } catch (err) {
        console.error("Swipe error", err);
        setToast({ message: "Could not sync action.", tone: "neutral" });
      }
    },
    [submit]
  );

  return (
    <div className="min-h-screen flex flex-col max-w-md mx-auto">
      <TopBar
        date={dateObj}
        total={total}
        onChangeDate={handleChangeDate}
        disableNext={activeDate >= todayISO()}
      />
      <main className="flex-1 px-6 py-6">
        <section className="relative aspect-[3/4]">
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
          {!isLoading && !error && !activeSnapshot && (
            <CardStack
              snapshots={snapshots}
              activeIndex={cursor}
              onActiveIndexChange={(index) => setCursor(index)}
              onSwipe={handleSwipe}
              onOpenDetails={(snapshot) => setActiveSnapshot(snapshot)}
            />
          )}
        </section>
      </main>

      {!activeSnapshot && (
        <ActionBar
          snapshot={currentSnapshot}
          onLike={() => currentSnapshot && handleSwipe(currentSnapshot, "like")}
          onSkip={() => currentSnapshot && handleSwipe(currentSnapshot, "skip")}
          onDetails={() => setActiveSnapshot(currentSnapshot)}
          disabled={isSubmitting}
        />
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
