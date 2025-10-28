import clsx from "clsx";
import { getAdminUrl } from "../utils/admin";

export type AppView = "daily" | "team" | "leaderboard" | "personal";

const NAV_ITEMS: Array<{ key: AppView; label: string }> = [
  { key: "daily", label: "Daily Picks" },
  { key: "team", label: "Team Likes" },
  { key: "leaderboard", label: "Leaderboard" },
  { key: "personal", label: "My Likes" }
];

interface PrimaryNavProps {
  activeView: AppView;
  onChange: (view: AppView) => void;
}

export function PrimaryNav({ activeView, onChange }: PrimaryNavProps) {
  const adminUrl = getAdminUrl();

  return (
    <nav className="sticky top-0 z-50 bg-ink/95 backdrop-blur-xl border-b border-white/5">
      <div className="mx-auto flex w-full max-w-4xl flex-wrap items-center justify-center gap-1.5 sm:gap-2 px-3 py-2 sm:px-4 sm:py-4">
        {NAV_ITEMS.map((item) => {
          const isActive = item.key === activeView;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onChange(item.key)}
              className={clsx(
                "rounded-full px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70",
                isActive
                  ? "bg-accent text-white shadow-[0_6px_12px_rgba(10,132,255,0.25)]"
                  : "bg-white/5 text-mist-subtle/80 hover:bg-white/10 hover:text-white"
              )}
            >
              {item.label}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => {
            window.open(adminUrl, "_blank", "noopener,noreferrer");
          }}
          className="hidden sm:inline-flex rounded-full bg-white/5 px-4 py-2 text-sm text-mist-subtle/80 transition hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
        >
          Open Admin
        </button>
      </div>
    </nav>
  );
}
