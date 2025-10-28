import { useMemo, useState } from "react";
import { format, parseISO } from "date-fns";
import useSWR from "swr";
import { motion } from "framer-motion";
import type { LeaderboardStats } from "../types";
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
  const [windowSize, setWindowSize] = useState<"day" | "week" | "month">("day");

  const swrKey: readonly ["leaderboard", string, "day" | "week" | "month"] | null = isAuthenticated
    ? (["leaderboard", selectedDate, windowSize] as const)
    : null;
  const { data, error, isLoading } = useSWR<LeaderboardStats, Error, typeof swrKey>(
    swrKey,
    ([_key, date, range]) => api.leaderboardStats({ date, window: range }),
    { revalidateOnFocus: false }
  );

  const memberStats = useMemo(() => data?.member_stats ?? [], [data?.member_stats]);
  const overlapPairs = useMemo(() => data?.overlap_pairs ?? [], [data?.overlap_pairs]);

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
          <h1 className="text-2xl font-semibold text-mist">Team leaderboard</h1>
          <p className="mt-1 text-sm text-mist-subtle/70">
            Activity snapshot for {rangeLabel || (data?.date ? format(parseISO(data.date), "MMM d, yyyy") : "the selected range")}.
          </p>
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
        <SummaryCard label="Total actions" value={data?.total_actions ?? 0} />
        <SummaryCard label="Unique games" value={data?.unique_games ?? 0} />
        <SummaryCard label="Active teammates" value={data?.member_count ?? 0} />
      </div>

      {isLoading ? (
        <div className="mt-10 flex flex-col items-center justify-center gap-4">
          <motion.span
            className="block h-10 w-10 rounded-full border-2 border-white/10 border-t-white/70"
            animate={{ rotate: 360 }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
          />
          <p className="text-sm text-mist-subtle/70">Ranking teammates…</p>
        </div>
      ) : memberStats.length === 0 ? (
        <div className="mt-10 glass-panel px-6 py-10 text-center">
          <h3 className="text-lg font-medium text-mist">No activity recorded</h3>
          <p className="mt-3 text-sm text-mist-subtle/80">Once teammates review games in the selected range, their stats will appear here.</p>
        </div>
      ) : (
        <>
          <section className="mt-8 space-y-4">
            <h2 className="text-lg font-semibold text-mist">Processing leaderboard</h2>
            <ol className="space-y-3">
              {memberStats.map((member, index) => {
                const rank = index + 1;
                const displayName = member.user.display_name || member.user.username || "Member";
                const lastActionLabel = member.last_action_at ? format(parseISO(member.last_action_at), "MMM d, HH:mm") : "—";
                return (
                  <li key={member.user.id ?? displayName} className="glass-panel rounded-3xl px-6 py-5">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div className="flex gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent/15 text-lg font-semibold text-accent">
                          #{rank}
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-mist leading-tight">{displayName}</h3>
                          <p className="mt-1 text-xs uppercase tracking-[0.35em] text-mist-subtle/70">
                            {member.handled_games} games handled • Last action {lastActionLabel}
                          </p>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs text-mist-subtle/70">
                        <StatPill label="Likes" value={member.like_count} tone="positive" />
                        <StatPill label="Skips" value={member.skip_count} tone="neutral" />
                        <StatPill label="Watchlist" value={member.watchlist_count} tone="accent" />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>

          <section className="mt-10 space-y-4">
            <h2 className="text-lg font-semibold text-mist">Like overlap</h2>
            {overlapPairs.length === 0 ? (
              <div className="glass-panel rounded-3xl px-6 py-5 text-sm text-mist-subtle/80">
                Not enough shared likes yet. Once teammates align on favorites, overlap pairs will appear here.
              </div>
            ) : (
              <div className="glass-panel rounded-3xl px-6 py-5 overflow-hidden">
                <table className="w-full border-separate border-spacing-y-2 text-sm text-mist-subtle/85">
                  <thead>
                    <tr className="text-xs uppercase tracking-[0.3em] text-mist-subtle/60">
                      <th className="text-left">Pair</th>
                      <th className="text-right">Shared likes</th>
                      <th className="text-right">Union size</th>
                      <th className="text-right">Jaccard</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overlapPairs.map((pair) => {
                      const nameA = pair.user_a.display_name || pair.user_a.username || "Member A";
                      const nameB = pair.user_b.display_name || pair.user_b.username || "Member B";
                      const pairKey = `${pair.user_a.id ?? nameA}-${pair.user_b.id ?? nameB}`;
                      return (
                        <tr key={pairKey} className="bg-white/5">
                          <td className="rounded-l-2xl px-4 py-3 text-mist">
                            {nameA} &amp; {nameB}
                          </td>
                          <td className="px-4 py-3 text-right">{pair.shared_likes}</td>
                          <td className="px-4 py-3 text-right">{pair.union_size}</td>
                          <td className="rounded-r-2xl px-4 py-3 text-right">{pair.jaccard.toFixed(2)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
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
  const toneClass =
    tone === "positive"
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
