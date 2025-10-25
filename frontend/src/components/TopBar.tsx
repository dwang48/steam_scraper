import { format } from "date-fns";
import { motion } from "framer-motion";
import type { CurrentUser } from "../types";

interface TopBarProps {
  date: Date;
  total: number;
  onChangeDate: (direction: "prev" | "next") => void;
  disableNext?: boolean;
  user?: CurrentUser | null;
  loadingUser?: boolean;
  onSignIn?: () => void;
  onSignOut?: () => void;
  signOutInFlight?: boolean;
}

function getDisplayName(user?: CurrentUser | null) {
  if (!user) return "Guest";
  return (
    user.display_name ||
    [user.first_name, user.last_name].filter(Boolean).join(" ").trim() ||
    user.username ||
    "Guest"
  );
}

function getInitials(source: string) {
  const words = source.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "??";
  return words
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("") || "??";
}

export function TopBar({
  date,
  total,
  onChangeDate,
  disableNext,
  user,
  loadingUser,
  onSignIn,
  onSignOut,
  signOutInFlight
}: TopBarProps) {
  const displayName = loadingUser ? "Loading…" : getDisplayName(user);
  const subtitle = loadingUser
    ? "Checking session…"
    : user?.is_authenticated
    ? user.email || "Steam Curator"
    : "Not signed in";
  const initials = loadingUser ? "…" : getInitials(displayName);
  const showSignIn = !loadingUser && !user?.is_authenticated;

  return (
    <header className="sticky top-0 z-40 px-4 py-4 sm:px-6 sm:py-5 bg-gradient-to-b from-ink/95 via-ink/70 to-transparent backdrop-blur-xl">
      {/* 用户信息栏 */}
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent to-accent-soft flex items-center justify-center text-white font-semibold text-sm uppercase">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-mist truncate max-w-[180px] sm:max-w-xs">{displayName}</p>
            <p className="text-xs text-mist-subtle/70 truncate max-w-[200px]">{subtitle}</p>
          </div>
        </div>
        <div className="flex-shrink-0">
          {showSignIn ? (
            <button
              type="button"
              onClick={onSignIn}
              className="rounded-full border border-accent/60 bg-transparent px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent hover:text-white transition"
            >
              Sign in
            </button>
          ) : user?.is_authenticated ? (
            <button
              type="button"
              onClick={onSignOut}
              disabled={signOutInFlight}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-mist-subtle/80 hover:bg-white/10 hover:text-white transition disabled:opacity-50"
            >
              {signOutInFlight ? "Signing out…" : "Sign out"}
            </button>
          ) : null}
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
