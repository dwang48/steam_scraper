import { useEffect, useMemo, useState } from "react";
import { format, parseISO } from "date-fns";
import useSWR from "swr";
import { motion } from "framer-motion";
import { api } from "../utils/api";
import type { GameSummary, PaginatedResponse, SwipeActionRecord } from "../types";
import { getSteamImageCandidates } from "../utils/steamAssets";
import { LikeReasonDialog } from "./LikeReasonDialog";

interface MyLikesViewProps {
  isAuthenticated: boolean;
  onRequireSignIn: () => void;
}

export function MyLikesView({ isAuthenticated, onRequireSignIn }: MyLikesViewProps) {
  const [filterDate, setFilterDate] = useState("");
  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<SwipeActionRecord>>(
    isAuthenticated ? ["my-likes", filterDate] : null,
    () => api.listSwipes({ action: "like", date: filterDate || undefined }),
    { revalidateOnFocus: false }
  );

  const [feedback, setFeedback] = useState<{ message: string; tone: "positive" | "neutral" } | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedLike, setSelectedLike] = useState<SwipeActionRecord | null>(null);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [copyingId, setCopyingId] = useState<number | null>(null);
  const [copyingAll, setCopyingAll] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

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

  const likes = useMemo(() => {
    const items = data?.results ?? [];
    return [...items].sort((a, b) => {
      const timeA = Date.parse(a.created_at);
      const timeB = Date.parse(b.created_at);
      return (isNaN(timeB) ? 0 : timeB) - (isNaN(timeA) ? 0 : timeA);
    });
  }, [data?.results]);
  const allSelected = likes.length > 0 && selectedIds.size === likes.length;
  const hasSelection = selectedIds.size > 0;

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(likes.map((like) => like.id)));
    }
  };

  const toggleSelectOne = (likeId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(likeId)) {
        next.delete(likeId);
      } else {
        next.add(likeId);
      }
      return next;
    });
  };

  useEffect(() => {
    // Clear selection when data set changes (e.g., filter date change)
    setSelectedIds(new Set());
  }, [likes]);

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

  const handleExport = async () => {
    if (exporting) return;
    setExporting(true);
    setFeedback(null);
    try {
      const ids = hasSelection ? Array.from(selectedIds) : undefined;
      const blob = await api.exportLikesCsv({
        action: "like",
        ids,
        date: filterDate || undefined
      });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      const suffix = new Date().toISOString().slice(0, 10);
      link.download = `my-liked-games-${suffix}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      setFeedback({ message: "Export ready — download started.", tone: "positive" });
    } catch (err) {
      console.error("Export likes failed", err);
      setFeedback({ message: "Could not export likes. Try again.", tone: "neutral" });
    } finally {
      setExporting(false);
    }
  };

  const formatShareText = (like: SwipeActionRecord) => {
    const game = like.game_detail;
    const name = game?.name ?? `Game #${like.game}`;
    const url = game?.steam_url;
    return url ? `${name} — ${url}` : name;
  };

  const copyText = async (text: string) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (err) {
      console.warn("Clipboard API failed, falling back", err);
    }
    try {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.select();
      const success = document.execCommand("copy");
      textarea.remove();
      return success;
    } catch (err) {
      console.error("Fallback copy failed", err);
      return false;
    }
  };

  const handleCopySingle = async (like: SwipeActionRecord) => {
    if (copyingId || copyingAll) return;
    setCopyingId(like.id);
    setFeedback(null);
    const ok = await copyText(formatShareText(like));
    setCopyingId(null);
    setFeedback({
      message: ok ? "Copied game info." : "Could not copy. Try again.",
      tone: ok ? "positive" : "neutral"
    });
  };

  const handleCopyAll = async () => {
    if (copyingAll || likes.length === 0) return;
    setCopyingAll(true);
    setFeedback(null);
    const payload = likes.map(formatShareText).join("\n");
    const ok = await copyText(payload);
    setCopyingAll(false);
    setFeedback({
      message: ok ? "All liked games copied." : "Could not copy list. Try again.",
      tone: ok ? "positive" : "neutral"
    });
  };

  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-8 sm:py-10">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-mist">My likes</h1>
          <p className="text-sm text-mist-subtle/70">Track every game you decided to like.</p>
          <div className="mt-2 flex flex-wrap gap-2 items-center">
            <label className="text-[0.8rem] text-mist-subtle/75 flex items-center gap-2">
              <span>Date filter</span>
              <input
                type="date"
                value={filterDate}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(event) => {
                  setFilterDate(event.target.value);
                  setFeedback(null);
                }}
                className="rounded-lg bg-white/5 px-2 py-1 text-[0.75rem] text-mist focus:outline-none focus:ring-2 focus:ring-accent/60"
              />
              {filterDate && (
                <button
                  type="button"
                  onClick={() => setFilterDate("")}
                  className="text-[0.75rem] text-accent hover:text-white"
                >
                  Clear
                </button>
              )}
            </label>
            {likes.length > 0 && (
              <label className="flex items-center gap-2 text-[0.8rem] text-mist-subtle/75">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-white/20 bg-white/5 text-accent focus:ring-accent"
                  checked={allSelected}
                  onChange={toggleSelectAll}
                />
                <span>{allSelected ? "Deselect all" : "Select all"}</span>
                <span className="rounded-full bg-white/5 px-2 py-1 text-[0.7rem] text-mist-subtle/80">
                  {selectedIds.size} selected
                </span>
              </label>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting || isLoading || likes.length === 0}
            className="rounded-full bg-white/5 px-3 py-1.5 text-xs text-mist-subtle/85 hover:bg-white/10 hover:text-white transition disabled:opacity-40"
          >
            {exporting ? "Preparing CSV…" : hasSelection ? "Export selected" : filterDate ? "Export day CSV" : "Export CSV"}
          </button>
          <button
            type="button"
            onClick={handleCopyAll}
            disabled={copyingAll || isLoading || likes.length === 0}
            className="rounded-full bg-white/5 px-3 py-1.5 text-xs text-mist-subtle/85 hover:bg-white/10 hover:text-white transition disabled:opacity-40"
          >
            {copyingAll ? "Copying…" : "Copy all links"}
          </button>
          <span className="rounded-full bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.35em] text-mist-subtle/60">
            Total {likes.length}
          </span>
        </div>
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
            const likedAtLabel = format(parseISO(like.created_at), "yyyy-MM-dd HH:mm");
            const releaseDate = (game?.latest_release_date || "").trim();
            const releaseLabel = releaseDate || "TBA / Unannounced";
            return (
              <li key={like.id} className="glass-panel rounded-3xl px-6 py-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex gap-3">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 rounded border-white/20 bg-white/5 text-accent focus:ring-accent"
                      checked={selectedIds.has(like.id)}
                      onChange={() => toggleSelectOne(like.id)}
                    />
                    <LikeCover game={game} alt={gameName} />
                    <div>
                      <h2 className="text-lg font-semibold text-mist leading-tight">{gameName}</h2>
                      <p className="mt-1 text-xs text-mist-subtle/70">
                        Release {releaseLabel} • Liked on {likedAtLabel}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-end">
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
                    <button
                      type="button"
                      onClick={() => handleCopySingle(like)}
                      disabled={saving || copyingId === like.id}
                      className="rounded-full bg-white/5 px-3 py-1 text-xs text-mist-subtle/85 hover:bg-white/10 hover:text-white transition disabled:opacity-40"
                    >
                      {copyingId === like.id ? "Copying…" : "Copy link"}
                    </button>
                  </div>
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

function LikeCover({ game, alt }: { game?: GameSummary; alt: string }) {
  const [imageIndex, setImageIndex] = useState(0);
  const [failed, setFailed] = useState(false);

  const candidates = useMemo(() => {
    const list: string[] = [];
    if (game?.capsule_image_url) list.push(game.capsule_image_url);
    if (game?.header_image_url) list.push(game.header_image_url);
    if (game?.background_image_url) list.push(game.background_image_url);
    if (game?.steam_appid) {
      list.push(...getSteamImageCandidates(game.steam_appid));
    }
    return Array.from(new Set(list));
  }, [game]);

  const src = candidates[imageIndex] ?? "";

  return (
    <div className="h-16 w-28 flex-shrink-0 overflow-hidden rounded-xl border border-white/10 bg-ink-softer/70">
      {src && !failed ? (
        <img
          src={src}
          alt={alt}
          className="h-full w-full object-cover"
          loading="lazy"
          onError={() => {
            if (imageIndex + 1 < candidates.length) {
              setImageIndex((prev) => prev + 1);
            } else {
              setFailed(true);
            }
          }}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-ink via-ink-soft to-ink-dark text-sm font-semibold text-mist/80">
          {alt.slice(0, 2).toUpperCase()}
        </div>
      )}
    </div>
  );
}
