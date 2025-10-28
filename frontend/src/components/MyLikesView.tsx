import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import useSWR from "swr";
import { motion } from "framer-motion";
import { api } from "../utils/api";
import type { PaginatedResponse, SwipeActionRecord } from "../types";
import { LikeReasonDialog } from "./LikeReasonDialog";

interface MyLikesViewProps {
  isAuthenticated: boolean;
  onRequireSignIn: () => void;
}

export function MyLikesView({ isAuthenticated, onRequireSignIn }: MyLikesViewProps) {
  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<SwipeActionRecord>>(
    isAuthenticated ? "my-likes" : null,
    () => api.listSwipes({ action: "like" }),
    { revalidateOnFocus: false }
  );

  const [feedback, setFeedback] = useState<{ message: string; tone: "positive" | "neutral" } | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedLike, setSelectedLike] = useState<SwipeActionRecord | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!feedback) return;
    const timer = window.setTimeout(() => setFeedback(null), 2600);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  if (!isAuthenticated) {
    return (
      <section className="mx-auto w-full max-w-3xl px-4 py-10 text-center sm:py-14">
        <div className="glass-panel mx-auto max-w-md px-6 py-10">
          <h2 className="text-xl font-semibold text-mist">Sign-in required</h2>
          <p className="mt-3 text-sm text-mist-subtle/80">Sign in to view the games you&apos;ve liked.</p>
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
      <section className="mx-auto w-full max-w-3xl px-4 py-10 sm:py-14">
        <div className="glass-panel px-6 py-10 text-center">
          <h2 className="text-xl font-semibold text-mist">Unable to load your likes</h2>
          <p className="mt-3 text-sm text-mist-subtle/80">{error instanceof Error ? error.message : String(error)}</p>
        </div>
      </section>
    );
  }

  const likes = data?.results ?? [];

  const handleRemove = async (like: SwipeActionRecord) => {
    if (saving) return;
    setSaving(true);
    setFeedback(null);
    try {
      await api.createSwipe({
        game: like.game,
        batch: like.batch ?? null,
        action: "skip",
        note: "",
      });
      await mutate();
      setFeedback({ message: `${like.game_detail?.name ?? "Game"} removed from likes.`, tone: "neutral" });
    } catch (err) {
      console.error("Remove like failed", err);
      setFeedback({ message: "Could not remove like. Try again.", tone: "neutral" });
    } finally {
      setSaving(false);
    }
  };

  const handleEditNote = (like: SwipeActionRecord) => {
    if (saving) return;
    setSelectedLike(like);
    setDialogOpen(true);
    setFeedback(null);
  };

  const handleSubmitNote = async (note: string) => {
    if (!selectedLike) return;
    setSaving(true);
    try {
      await api.createSwipe({
        game: selectedLike.game,
        batch: selectedLike.batch ?? null,
        action: "like",
        note,
      });
      await mutate();
      setFeedback({
        message: note ? "Reason saved." : "Reason cleared.",
        tone: "positive",
      });
      setDialogOpen(false);
      setSelectedLike(null);
    } catch (err) {
      console.error("Save like reason failed", err);
      setFeedback({ message: "Could not save the reason. Try again.", tone: "neutral" });
    } finally {
      setSaving(false);
    }
  };

  const handleCloseDialog = () => {
    if (saving) return;
    setDialogOpen(false);
    setSelectedLike(null);
  };

  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-8 sm:py-10">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-mist">My likes</h1>
          <p className="text-sm text-mist-subtle/70">Track every game you decided to like.</p>
        </div>
        <span className="rounded-full bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.35em] text-mist-subtle/60">
          Total {likes.length}
        </span>
      </header>

      {feedback && (
        <div
          className={`mt-6 rounded-2xl px-4 py-3 text-sm ${
            feedback.tone === "positive" ? "bg-green-500/15 text-green-200" : "bg-white/5 text-mist-subtle/80"
          }`}
        >
          {feedback.message}
        </div>
      )}

      {isLoading ? (
        <div className="mt-10 flex flex-col items-center justify-center gap-4">
          <motion.span
            className="block h-10 w-10 rounded-full border-2 border-white/10 border-t-white/70"
            animate={{ rotate: 360 }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
          />
          <p className="text-sm text-mist-subtle/70">Loading your likes…</p>
        </div>
      ) : likes.length === 0 ? (
        <div className="mt-10 glass-panel px-6 py-10 text-center">
          <h3 className="text-lg font-medium text-mist">You haven&apos;t liked anything yet</h3>
          <p className="mt-3 text-sm text-mist-subtle/80">Games you like from the Daily tab will appear here.</p>
        </div>
      ) : (
        <ul className="mt-8 space-y-4">
          {likes.map((like) => {
            const game = like.game_detail;
            const gameName = game?.name ?? `Game #${like.game}`;
            const steamUrl = game?.steam_url;
            const createdAt = format(parseISO(like.created_at), "yyyy-MM-dd HH:mm");
            return (
              <li key={like.id} className="glass-panel rounded-3xl px-6 py-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-mist leading-tight">{gameName}</h2>
                    <p className="mt-1 text-xs text-mist-subtle/70">Liked on {createdAt}</p>
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
                {like.note ? (
                  <p className="mt-3 rounded-2xl bg-white/5 px-4 py-3 text-sm text-mist-subtle/85">{like.note}</p>
                ) : (
                  <p className="mt-3 rounded-2xl bg-white/5 px-4 py-3 text-sm text-mist-subtle/60 italic">
                    No reason recorded yet.
                  </p>
                )}
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleEditNote(like)}
                    disabled={saving}
                    className="rounded-full bg-white/5 px-3 py-1.5 text-xs text-mist-subtle/85 hover:bg-white/10 hover:text-white transition disabled:opacity-40"
                  >
                    Edit note
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemove(like)}
                    disabled={saving}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-mist-subtle/80 hover:bg-white/10 hover:text-white transition disabled:opacity-40"
                  >
                    Remove like
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <LikeReasonDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          if (open) {
            setDialogOpen(true);
          } else {
            handleCloseDialog();
          }
        }}
        defaultNote={selectedLike?.note ?? ""}
        onSubmit={handleSubmitNote}
        onSkip={handleCloseDialog}
        submitting={saving}
      />
    </section>
  );
}
