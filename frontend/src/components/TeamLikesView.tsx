import { format, parseISO } from "date-fns";
import useSWR from "swr";
import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../utils/api";
import type { DailySummary } from "../types";

interface TeamLikesViewProps {
  isAuthenticated: boolean;
  onRequireSignIn: () => void;
}

function useTodayString() {
  return format(new Date(), "yyyy-MM-dd");
}

export function TeamLikesView({ isAuthenticated, onRequireSignIn }: TeamLikesViewProps) {
  const today = useTodayString();
  const [selectedDate, setSelectedDate] = useState(today);
  const [windowSize, setWindowSize] = useState<"day" | "week" | "month">("day");

  const shouldFetch = isAuthenticated;
  const { data, error, isLoading } = useSWR<DailySummary>(
    shouldFetch ? ["daily-summary", selectedDate, windowSize] : null,
    (key) => {
      const [, date, range] = key as [string, string, "day" | "week" | "month"];
      return api.dailySummary({ date, window: range });
    },
    { revalidateOnFocus: false }
  );

  const likeEntries = useMemo(
    () => (data?.games ?? []).filter((entry) => entry.like_users.length > 0),
    [data?.games]
  );

  const rangeLabel = useMemo(() => {
    if (!data) return "";
    try {
      const start = parseISO(data.start_date);
      const end = parseISO(data.end_date);
      if (data.window === "month") {
        return format(start, "LLLL yyyy");
      }
      if (data.window === "week") {
        return `${format(start, "MMM d")} – ${format(end, "MMM d, yyyy")}`;
      }
      return format(end, "MMM d, yyyy");
    } catch {
      return "";
    }
  }, [data]);

  if (!isAuthenticated) {
    return (
      <section className="mx-auto w-full max-w-4xl px-4 py-10 text-center sm:py-14">
        <div className="glass-panel mx-auto max-w-md px-6 py-10">
          <h2 className="text-xl font-semibold text-mist">Sign-in required</h2>
          <p className="mt-3 text-sm text-mist-subtle/80">Sign in to review your team&apos;s likes for the selected date.</p>
          <button
            type="button"
            onClick={onRequireSignIn}
            className="mt-6 inline-flex items-center justify-center rounded-full bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-white hover:text-ink transition"
          >
            Sign in
          </button>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="mx-auto w-full max-w-4xl px-4 py-10 sm:py-14">
        <div className="glass-panel px-6 py-10 text-center">
          <h2 className="text-xl font-semibold text-mist">Unable to load team data</h2>
          <p className="mt-3 text-sm text-mist-subtle/80">{error instanceof Error ? error.message : String(error)}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto w-full max-w-4xl px-4 py-8 sm:py-10">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-mist">Team likes overview</h1>
          <p className="mt-1 text-sm text-mist-subtle/70">
            {windowSize === "day"
              ? "See who liked each game on the selected date."
              : "See who liked each game across the selected range."}
          </p>
          {rangeLabel && (
            <p className="mt-1 text-xs uppercase tracking-[0.3em] text-mist-subtle/60">{rangeLabel}</p>
          )}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex flex-col text-xs uppercase tracking-[0.35em] text-mist-subtle/60">
            Select date
            <input
              type="date"
              value={selectedDate}
              onChange={(event) => setSelectedDate(event.target.value)}
              max={today}
              className="mt-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-mist focus:outline-none focus:ring-2 focus:ring-accent/60"
            />
          </label>
          <label className="flex flex-col text-xs uppercase tracking-[0.35em] text-mist-subtle/60">
            Range
            <select
              value={windowSize}
              onChange={(event) => setWindowSize(event.target.value as "day" | "week" | "month")}
              className="mt-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-mist focus:outline-none focus:ring-2 focus:ring-accent/60"
            >
              <option value="day">Single day</option>
              <option value="week">Last 7 days</option>
              <option value="month">This month</option>
            </select>
          </label>
        </div>
      </header>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <SummaryCard label="Total likes" value={data?.like_count ?? 0} />
        <SummaryCard label="Active teammates" value={data?.unique_users ?? 0} />
        <SummaryCard label="Other actions" value={(data?.watchlist_count ?? 0) + (data?.skip_count ?? 0)} />
      </div>

      {isLoading ? (
        <div className="mt-10 flex flex-col items-center justify-center gap-4">
          <motion.span
            className="block h-10 w-10 rounded-full border-2 border-white/10 border-t-white/70"
            animate={{ rotate: 360 }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
          />
          <p className="text-sm text-mist-subtle/70">Gathering team activity…</p>
        </div>
      ) : likeEntries.length === 0 ? (
        <div className="mt-10 glass-panel px-6 py-10 text-center">
          <h3 className="text-lg font-medium text-mist">No likes recorded yet</h3>
          <p className="mt-3 text-sm text-mist-subtle/80">Once a teammate likes a game, it will show up here.</p>
        </div>
      ) : (
        <ul className="mt-8 space-y-4">
          {likeEntries.map((entry) => {
            const displayDate = rangeLabel;
            const likeNames = entry.like_users.map((user) => user.display_name || user.username || "Member").join(", ");
            const steamUrl = entry.game.steam_url;
            return (
              <li key={entry.game.id} className="glass-panel px-6 py-5 rounded-3xl border border-white/5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-mist leading-tight">{entry.game.name}</h2>
                    <p className="mt-1 text-xs text-mist-subtle/70 uppercase tracking-[0.35em]">
                      {displayDate}
                    </p>
                  </div>
                  {steamUrl && (
                    <a
                      href={steamUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 rounded-full bg-white/5 px-3 py-1 text-xs text-accent hover:bg-white/10 hover:text-white transition"
                    >
                      View on Steam ↗
                    </a>
                  )}
                </div>
                <p className="mt-4 text-sm text-mist-subtle/85">{likeNames}</p>
                <div className="mt-4 flex items-center gap-3 text-xs text-mist-subtle/60">
                  <span className="inline-flex items-center rounded-full bg-accent-soft px-3 py-1 font-medium text-accent">{entry.like_users.length} likes</span>
                  {entry.watchlist_users.length > 0 && (
                    <span className="inline-flex items-center rounded-full bg-white/5 px-3 py-1 font-medium text-mist-subtle/75">{entry.watchlist_users.length} watchlisted</span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="glass-panel rounded-3xl px-5 py-6 text-center">
      <p className="text-xs uppercase tracking-[0.35em] text-mist-subtle/60">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-mist">{value}</p>
    </div>
  );
}
