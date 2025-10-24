import { format } from "date-fns";
import { motion } from "framer-motion";

interface TopBarProps {
  date: Date;
  total: number;
  onChangeDate: (direction: "prev" | "next") => void;
  disableNext?: boolean;
}

export function TopBar({ date, total, onChangeDate, disableNext }: TopBarProps) {
  return (
    <header className="sticky top-0 z-40 px-6 py-5 bg-gradient-to-b from-ink/90 via-ink/70 to-transparent backdrop-blur-xl">
      {/* 用户信息栏 */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent to-accent-soft flex items-center justify-center text-white font-semibold text-sm">
          DG
        </div>
        <div>
          <p className="text-sm font-medium text-mist">Demo Gamer</p>
          <p className="text-xs text-mist-subtle/70">Steam Curator</p>
        </div>
      </div>
      
      {/* 日期和导航 */}
      <div className="flex items-center justify-between">
        <div>
          <p className="uppercase tracking-[0.35em] text-xs text-mist-subtle/70 mb-1">Daily Curated</p>
          <motion.h1
            className="text-3xl font-semibold text-mist"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            {format(date, "EEEE, MMM d")}
          </motion.h1>
          <p className="text-sm text-mist-subtle/80 mt-1">{total} experiences awaiting</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onChangeDate("prev")}
            className="glass-panel px-3 py-2 text-sm text-mist hover:bg-ink-softer/90 transition"
            aria-label="Previous day"
          >
            ‹
          </button>
          <button
            onClick={() => onChangeDate("next")}
            className="glass-panel px-3 py-2 text-sm text-mist hover:bg-ink-softer/90 transition disabled:opacity-50"
            aria-label="Next day"
            disabled={disableNext}
          >
            ›
          </button>
        </div>
      </div>
    </header>
  );
}
