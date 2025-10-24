import { motion } from "framer-motion";
import clsx from "clsx";
import { useEffect, useMemo, useState } from "react";
import { GameSnapshot } from "../types";
import { getSteamImageCandidates, getSteamStoreUrl } from "../utils/steamAssets";

interface GameCardProps {
  snapshot: GameSnapshot;
  active?: boolean;
  offset?: number;
  onShowDetails?: () => void;
}

export function GameCard({ snapshot, active, offset = 0, onShowDetails }: GameCardProps) {
  const { game } = snapshot;

  const steamStoreUrl = useMemo(
    () => getSteamStoreUrl(game.steam_appid, game.steam_url),
    [game.steam_appid, game.steam_url]
  );
  const detectionStageLabel = snapshot.detection_stage
    ? snapshot.detection_stage.replace("_", " ")
    : "Unknown stage";

  const imageCandidates = useMemo(
    () => getSteamImageCandidates(game.steam_appid),
    [game.steam_appid]
  );
  const [imageIndex, setImageIndex] = useState(0);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setImageIndex(0);
    setImageFailed(false);
  }, [snapshot.id]);

  const currentImageSrc = imageCandidates[imageIndex] ?? "";
  const initials = useMemo(() => {
    const words = (game.name || "").split(/\s+/).filter(Boolean);
    if (!words.length) return "??";
    const letters = words.slice(0, 2).map((word) => word[0]?.toUpperCase() ?? "");
    return letters.join("");
  }, [game.name]);

  const tags = (snapshot.source_tags || snapshot.source_genres || snapshot.source_categories || "")
    .split(/[;|,]/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .slice(0, 4);

  return (
    <motion.article
      className={clsx(
        "glass-panel card-gradient w-full h-full px-6 py-8 flex flex-col gap-6",
        active ? "shadow-glass" : "opacity-80"
      )}
      style={{
        transformOrigin: "center",
        pointerEvents: active ? "auto" : "none"
      }}
      initial={{ scale: 0.96, y: 20, opacity: 0 }}
      animate={{ scale: active ? 1 : 0.98, y: active ? 0 : offset * 12, opacity: 1 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
    >
      <div>
        <div className="relative aspect-[16/9] w-full overflow-hidden rounded-2xl bg-ink-softer/80">
          {currentImageSrc && !imageFailed ? (
            <img
              src={currentImageSrc}
              alt={game.name}
              loading="lazy"
              className="h-full w-full object-cover"
              onError={(event) => {
                if (imageIndex + 1 < imageCandidates.length) {
                  setImageIndex((prev) => prev + 1);
                } else {
                  setImageFailed(true);
                }
              }}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-ink-softer via-ink to-ink-dark text-3xl font-semibold text-mist/80">
              {initials}
            </div>
          )}
          {steamStoreUrl && (
            <a
              href={steamStoreUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute bottom-3 right-3 rounded-full bg-black/60 px-3 py-1 text-xs text-mist hover:bg-black/80 transition cursor-pointer z-10"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                window.open(steamStoreUrl, "_blank", "noopener,noreferrer");
              }}
              onPointerDown={(event) => {
                event.stopPropagation();
              }}
              onMouseDown={(event) => {
                event.stopPropagation();
              }}
              onTouchStart={(event) => {
                event.stopPropagation();
              }}
            >
              Open Steam
            </a>
          )}
        </div>
        <span className="mt-4 inline-flex items-center rounded-full bg-accent-soft text-accent px-3 py-1 text-xs font-medium uppercase tracking-widest">
          {detectionStageLabel}
        </span>
        <div className="mt-4 flex items-start justify-between gap-3">
          <h2 className="text-2xl font-semibold text-mist leading-tight">{game.name}</h2>
          {steamStoreUrl && (
            <a
              href={steamStoreUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-accent hover:text-white transition whitespace-nowrap cursor-pointer z-10 relative"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                window.open(steamStoreUrl, "_blank", "noopener,noreferrer");
              }}
              onPointerDown={(event) => {
                event.stopPropagation();
              }}
              onMouseDown={(event) => {
                event.stopPropagation();
              }}
              onTouchStart={(event) => {
                event.stopPropagation();
              }}
            >
              View on Steam ↗
            </a>
          )}
        </div>
        <p className="text-sm text-mist-subtle/80 mt-1">
          Followers {snapshot.followers ?? "—"} · WL est. {snapshot.wishlists_est ?? "—"}
        </p>
        <p className="mt-4 text-sm text-mist-subtle/90 leading-relaxed line-clamp-3">{snapshot.description || "No description yet."}</p>
        {tags.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span key={tag} className="rounded-full bg-white/5 border border-white/10 px-3 py-1 text-xs text-mist/90">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="flex items-center justify-between mt-auto pt-4">
        <div className="text-xs text-mist-subtle/70">
          {snapshot.release_date_raw || "TBA"}
        </div>
        <button
          type="button"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            onShowDetails?.();
          }}
          onPointerDown={(event) => {
            event.stopPropagation();
          }}
          onMouseDown={(event) => {
            event.stopPropagation();
          }}
          onTouchStart={(event) => {
            event.stopPropagation();
          }}
          className="text-sm text-accent font-medium hover:text-white transition cursor-pointer z-10 relative"
          style={{ touchAction: "none" }}
        >
          More
        </button>
      </div>
    </motion.article>
  );
}
