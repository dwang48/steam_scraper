import { GameSnapshot } from "../types";

interface ActionBarProps {
  snapshot: GameSnapshot | null;
  onLike: () => void;
  onSkip: () => void;
  onDetails: () => void;
  disabled?: boolean;
}

export function ActionBar({ snapshot, onLike, onSkip, onDetails, disabled }: ActionBarProps) {
  return (
    <nav className="p-6 pb-10">
      <div className="glass-panel px-6 py-4 flex items-center justify-between gap-4">
        <button
          onClick={onSkip}
          disabled={!snapshot || disabled}
          className="w-12 h-12 rounded-full bg-white/5 text-mist-subtle/80 hover:bg-white/10 transition disabled:opacity-40 disabled:cursor-not-allowed text-xl"
          aria-label="Skip"
        >
          –
        </button>
        <button
          onClick={onDetails}
          disabled={!snapshot}
          className="flex-1 text-sm text-mist-subtle/90 hover:text-white transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Details
        </button>
        <button
          onClick={onLike}
          disabled={!snapshot || disabled}
          className="w-12 h-12 rounded-full bg-accent text-white hover:bg-white hover:text-ink transition disabled:opacity-40 disabled:cursor-not-allowed text-xl"
          aria-label="Like"
        >
          ♥
        </button>
      </div>
    </nav>
  );
}
