import { useMemo, useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import clsx from "clsx";
import { GameSnapshot, SwipeActionType } from "../types";
import { GameCard } from "./GameCard";

interface CardStackProps {
  snapshots: GameSnapshot[];
  activeIndex: number;
  onActiveIndexChange: (nextIndex: number) => void;
  onSwipe: (snapshot: GameSnapshot, action: SwipeActionType) => Promise<boolean> | boolean;
  onOpenDetails: (snapshot: GameSnapshot) => void;
}

const SWIPE_THRESHOLD = 120;

export function CardStack({ snapshots, activeIndex, onActiveIndexChange, onSwipe, onOpenDetails }: CardStackProps) {
  const [direction, setDirection] = useState<"left" | "right" | null>(null);
  const [isProcessing, setProcessing] = useState(false);

  const activeSnapshot = snapshots[activeIndex];

  useEffect(() => {
    if (activeIndex >= snapshots.length) {
      onActiveIndexChange(Math.max(snapshots.length - 1, 0));
    }
  }, [activeIndex, snapshots.length, onActiveIndexChange]);

  const handleSwipe = useCallback(
    async (action: SwipeActionType) => {
      if (!activeSnapshot || isProcessing) {
        return;
      }
      setProcessing(true);
      let result = false;
      try {
        result = await onSwipe(activeSnapshot, action);
      } catch (error) {
        console.error("Swipe handler failed", error);
      }
      if (!result) {
        setProcessing(false);
        return;
      }
      setDirection(action === "like" ? "right" : "left");
      setTimeout(() => {
        const nextIndex = activeIndex + 1;
        onActiveIndexChange(nextIndex);
        setDirection(null);
        setProcessing(false);
      }, 260);
    },
    [activeSnapshot, activeIndex, isProcessing, onActiveIndexChange, onSwipe]
  );

  const displaySnapshots = useMemo(
    () => snapshots.slice(activeIndex, activeIndex + 3),
    [snapshots, activeIndex]
  );

  if (!activeSnapshot) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center text-mist-subtle/70">
        <p className="text-lg">All curated games reviewed.</p>
        <p className="text-sm mt-2">Come back later for new discoveries.</p>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <AnimatePresence>
        {displaySnapshots.map((snapshot, index) => {
          const isActive = index === 0;
          return (
            <motion.div
              key={snapshot.id}
              className={clsx("absolute inset-0")}
              style={{ zIndex: displaySnapshots.length - index }}
              initial={{ opacity: 0, scale: 0.95, y: 40 }}
              animate={{ opacity: 1, scale: 1 - index * 0.04, y: index * 20 }}
              exit={{ opacity: 0, scale: 1.05, x: direction === "right" ? 300 : -300, rotate: direction === "right" ? 12 : -12 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
              drag={isActive && !isProcessing ? "x" : false}
              dragConstraints={{ left: 0, right: 0 }}
              dragElastic={0.18}
              onDragEnd={(_, info) => {
                if (!isActive) return;
                if (isProcessing) return;
                if (info.offset.x > SWIPE_THRESHOLD) {
                  void handleSwipe("like");
                } else if (info.offset.x < -SWIPE_THRESHOLD) {
                  void handleSwipe("skip");
                }
              }}
            >
              <GameCard
                snapshot={snapshot}
                active={isActive}
                offset={index}
                onShowDetails={() => onOpenDetails(snapshot)}
              />
              {isActive && (
                <div className="absolute inset-x-0 -bottom-20 flex items-center justify-between text-xs uppercase tracking-[0.3em] text-mist-subtle/60 pointer-events-none">
                  <span>Swipe left to pass</span>
                  <span>Swipe right to save</span>
                </div>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
