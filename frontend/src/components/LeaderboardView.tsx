import { useMemo, useState } from "react";
import { format, parseISO } from "date-fns";
import useSWR from "swr";
import { motion } from "framer-motion";
import type { DailySummary } from "../types";
import { api } from "../utils/api";

interface LeaderboardViewProps {
  isAuthenticated: boolean;
  onRequireSignIn: () => void;
}

function useTodayString() {
  return format(new Date(), "yyyy-MM-dd");
}

export function LeaderboardView({ isAuthenticated, onRequireSignIn }: LeaderboardViewProps) {
  const today = useTodayString();
  const [selectedDate, setSelectedDate] = useState(today);

  const shouldFetch = isAuthenticated;
  const { data, error, isLoading } = useSWR<DailySummary>(
    shouldFetch ? ["leaderboard", selectedDate] : null,
    ([, date]) => api.dailySummary({ date }),
    { revalidateOnFocus: false }
  );

  const rankedGames = useMemo(() => {
    const list = data?.games ?? [];
    return [...list].sort((a, b) => {
      const likeDiff = b.like_users.length - a.like_users.length;
      if (likeDiff !== 0) return likeDiff;
      const watchlistDiff = b.watchlist_users.length - a.watchlist_users.length;
      if (watchlistDiff !== 0) return watchlistDiff;
      return b.total_actions - a.total_actions;
    });
  }, [data?.games]);

  if (!isAuthenticated) {
    return (
      <section className="mx-auto w-full max-w-4xl px-4 py-10 text-center sm:py-14">
        <div className="glass-panel mx-auto max-w-md px-6 py-10">
          <h2 className="text-xl font-semibold text-mist">Sign-in required</h2>
          <p className="mt-3 text-sm text-mist-subtle/80">Sign in to view the daily like leaderboard.</p>
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
          <h2 className="text-xl font-semibold text-mist">Unable to load leaderboard</h2>
          <p className="mt-3 text-sm text-mist-subtle/80">{error instanceof Error ? error.message : String(error)}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto w-full max-w-4xl px-4 py-8 sm:py-10">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-mist">Daily leaderboard</h1>
          <p className="mt-1 text-sm text-mist-subtle/70">
            Ranked by likes for {data?.date ? format(parseISO(data.date), "MMM d, yyyy") : "the selected date"}.
          </p>
        </div>
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
      </header>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <SummaryCard label="Total likes" value={data?.like_count ?? 0} />
        <SummaryCard label="Total skips" value={data?.skip_count ?? 0} />
        <SummaryCard label="Unique voters" value={data?.unique_users ?? 0} />
      </div>

      {isLoading ? (
        <div className="mt-10 flex flex-col items-center justify-center gap-4">
          <motion.span
            className="block h-10 w-10 rounded-full border-2 border-white/10 border-t-white/70"
            animate={{ rotate: 360 }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
          />
          <p className="text-sm text-mist-subtle/70">Ranking games…</p>
        </div>
      ) : rankedGames.length === 0 ? (
        <div className="mt-10 glass-panel px-6 py-10 text-center">
          <h3 className="text-lg font-medium text-mist">No activity recorded</h3>
          <p className="mt-3 text-sm text-mist-subtle/80">Once the team likes or skips games, they will appear here.</p>
        </div>
      ) : (
        <ol className="mt-8 space-y-4">
          {rankedGames.map((entry, index) => {
            const rank = index + 1;
            const likeCount = entry.like_users.length;
            const skipCount = entry.skip_users.length;
            const steamUrl = entry.game.steam_url;
            return (
              <li key={entry.game.id} className="glass-panel rounded-3xl px-6 py-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent/15 text-lg font-semibold text-accent">
                      #{rank}
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold text-mist leading-tight">{entry.game.name}</h2>
                      <p className="mt-1 text-xs uppercase tracking-[0.35em] text-mist-subtle/70">{entry.game.latest_release_date || "Release TBA"}</p>
                      <p className="mt-2 text-xs text-mist-subtle/70 line-clamp-2">{entry.game.genres}</p>
                    </div>
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
                <div className="mt-4 grid grid-cols-1 gap-3 text-sm text-mist-subtle/85 sm:grid-cols-3">
                  <StatPill label="Likes" value={likeCount} tone="positive" />
                  <StatPill label="Skips" value={skipCount} tone="neutral" />
                  <StatPill label="Watchlisted" value={entry.watchlist_users.length} tone="accent" />
                </div>
              </li>
            );
          })}
        </ol>
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

function StatPill({ label, value, tone }: { label: string; value: number; tone: "positive" | "neutral" | "accent" }) {
  const base = "inline-flex items-center justify-center rounded-full px-3 py-2 text-sm font-medium";
  const toneClass = tone === "positive"
    ? "bg-green-500/15 text-green-300"
    : tone === "accent"
    ? "bg-accent-soft text-accent"
    : "bg-white/5 text-mist-subtle/80";
  return (
    <div className="flex flex-col items-center gap-1 text-center">
      <span className="text-xs uppercase tracking-[0.35em] text-mist-subtle/60">{label}</span>
      <span className={`${base} ${toneClass}`}>{value}</span>
    </div>
  );
}
