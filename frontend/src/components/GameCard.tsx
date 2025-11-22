import { format, parseISO } from "date-fns";
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
  const isHandled = snapshot.handled ?? false;

  const steamStoreUrl = useMemo(
    () => getSteamStoreUrl(game.steam_appid, game.steam_url),
    [game.steam_appid, game.steam_url]
  );
  const detectionStageLabel = snapshot.detection_stage
    ? snapshot.detection_stage.replace("_", " ")
    : "Unknown stage";

  const imageCandidates = useMemo(() => {
    const screenshots = (game.screenshot_urls ?? []).slice(0, 4);
    const preferred: string[] = [...screenshots];
    if (game.capsule_image_url) preferred.push(game.capsule_image_url);
    if (game.header_image_url) preferred.push(game.header_image_url);
    if (game.background_image_url) preferred.push(game.background_image_url);
    const fallbacks = getSteamImageCandidates(game.steam_appid);
    return Array.from(new Set([...preferred, ...fallbacks]));
  }, [game.background_image_url, game.capsule_image_url, game.header_image_url, game.screenshot_urls, game.steam_appid]);
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
  const handledAtLabel = useMemo(() => {
    const handledAt = snapshot.user_handled_at;
    if (!handledAt) return "";
    try {
      return format(parseISO(handledAt), "MMM d");
    } catch {
      return "";
    }
  }, [snapshot.user_handled_at]);
  const handledActionLabel = useMemo(() => {
    switch (snapshot.user_action) {
      case "like":
        return "Liked";
      case "watchlist":
        return "Watchlisted";
      case "skip":
        return "Skipped";
      default:
        return "";
    }
  }, [snapshot.user_action]);
  const categoriesLabel = formatList(snapshot.source_categories || game.categories);
  const genresLabel = formatList(snapshot.source_genres || game.genres);
  const languagesLabel = formatList(snapshot.supported_languages);

  return (
    <motion.article
      className={clsx(
        "glass-panel card-gradient w-full h-full max-w-5xl lg:max-w-6xl mx-auto px-4 pt-4 pb-32 sm:px-6 sm:pt-8 sm:pb-40 flex flex-col gap-4 sm:gap-6 overflow-y-auto md:overflow-visible max-h-[calc(100vh-220px)] sm:max-h-[calc(100vh-240px)] md:max-h-none",
        active ? "shadow-glass" : "opacity-80",
        isHandled && !active && "opacity-70"
      )}
      style={{
        transformOrigin: "center",
        pointerEvents: active ? "auto" : "none"
      }}
      initial={{ scale: 0.96, y: 20, opacity: 0 }}
      animate={{ scale: active ? 1 : 0.98, y: active ? 0 : offset * 12, opacity: 1 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
    >
      <div className="flex flex-col md:flex-row md:items-start md:gap-6">
        <div className="md:w-[58%] lg:w-[60%]">
          <div className="relative aspect-[16/9] w-full overflow-hidden rounded-2xl bg-ink-softer/80 max-h-[360px] sm:max-h-[440px] md:max-h-[520px]">
            {isHandled && handledActionLabel && (
              <div className="absolute left-2 top-2 z-20 rounded-full bg-black/70 px-2 py-0.5 text-[0.625rem] text-mist-subtle/90 backdrop-blur-sm">
                {handledActionLabel}
                {handledAtLabel ? ` • ${handledAtLabel}` : ""}
              </div>
            )}
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
                className="absolute bottom-2 right-2 sm:bottom-3 sm:right-3 rounded-full bg-black/60 px-2 py-0.5 sm:px-3 sm:py-1 text-[0.625rem] sm:text-xs text-mist hover:bg-black/80 transition cursor-pointer z-10"
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
        </div>
        <div className="md:flex-1 flex flex-col gap-3 sm:gap-4">
          <span className="inline-flex items-center self-start rounded-full bg-accent-soft text-accent px-2.5 py-0.5 sm:px-3 sm:py-1 text-[0.625rem] sm:text-xs font-medium uppercase tracking-widest">
            {detectionStageLabel}
          </span>
          <div className="flex items-start justify-between gap-2 sm:gap-3">
            <h2 className="text-lg sm:text-2xl font-semibold text-mist leading-tight">{game.name}</h2>
            {steamStoreUrl && (
              <a
                href={steamStoreUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[0.625rem] sm:text-xs text-accent hover:text-white transition whitespace-nowrap cursor-pointer z-10 relative"
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
          <p className="text-xs sm:text-sm text-mist-subtle/80">
            Followers {snapshot.followers ?? "—"} · WL est. {snapshot.wishlists_est ?? "—"}
          </p>
          <p className="text-xs sm:text-sm text-mist-subtle/90 leading-relaxed md:line-clamp-none md:pr-2">
            {snapshot.description || "No description yet."}
          </p>
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 sm:gap-2">
              {tags.map((tag) => (
                <span key={tag} className="rounded-full bg-white/5 border border-white/10 px-2 py-0.5 sm:px-3 sm:py-1 text-[0.625rem] sm:text-xs text-mist/90">
                  {tag}
                </span>
              ))}
            </div>
          )}
          {/* Inline detail view shown on mobile and desktop */}
          <div className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[0.7rem] sm:text-xs text-mist-subtle/85">
              <DetailRow label="Release" value={snapshot.release_date_raw || "TBA"} />
              <DetailRow label="Detection" value={detectionStageLabel} />
              <DetailRow label="Categories" value={categoriesLabel} />
              <DetailRow label="Genres" value={genresLabel} />
              <DetailRow label="Languages" value={languagesLabel} />
              <DetailRow label="Developers" value={game.developers || "Unknown"} />
            </div>
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between mt-auto pt-2 sm:pt-4">
        <div className="text-[0.625rem] sm:text-xs text-mist-subtle/70">
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
          className="text-xs sm:text-sm text-accent font-medium hover:text-white transition cursor-pointer z-10 relative"
          style={{ touchAction: "none" }}
        >
          More
        </button>
      </div>
    </motion.article>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="uppercase tracking-[0.3em] text-[0.6rem] text-mist-subtle/60 whitespace-nowrap">{label}</span>
      <span className="text-mist/90 leading-snug">{value || "—"}</span>
    </div>
  );
}

function formatList(value?: string | null) {
  if (!value) return "Unknown";
  const cleaned = value
    .split(/[;|,]/)
    .map((item) => item.trim())
    .filter(Boolean);
  return cleaned.length ? cleaned.join(" · ") : "Unknown";
}
