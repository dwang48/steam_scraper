import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { GameSnapshot } from "../types";
import { getSteamImageCandidates, getSteamStoreUrl } from "../utils/steamAssets";

interface DetailSheetProps {
  snapshot: GameSnapshot | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DetailSheet({ snapshot, open, onOpenChange }: DetailSheetProps) {
  const [isClient, setIsClient] = useState(false);
  const [renderSnapshot, setRenderSnapshot] = useState<GameSnapshot | null>(snapshot);
  const [detailImageIndex, setDetailImageIndex] = useState(0);
  const [detailImageFailed, setDetailImageFailed] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (snapshot) {
      setRenderSnapshot(snapshot);
    }
  }, [snapshot]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  useEffect(() => {
    setDetailImageIndex(0);
    setDetailImageFailed(false);
  }, [renderSnapshot?.id]);

  const steamStoreUrl = renderSnapshot
    ? getSteamStoreUrl(renderSnapshot.game.steam_appid, renderSnapshot.game.steam_url)
    : "";
  const detectionStageLabel = renderSnapshot?.detection_stage
    ? renderSnapshot.detection_stage.replace("_", " ")
    : "Unknown stage";
  const imageCandidates = useMemo(() => {
    if (!renderSnapshot) return [];
    const preferred: string[] = [];
    const { game } = renderSnapshot;
    if (game.header_image_url) preferred.push(game.header_image_url);
    if (game.capsule_image_url) preferred.push(game.capsule_image_url);
    if (game.background_image_url) preferred.push(game.background_image_url);
    const fallbacks = getSteamImageCandidates(game.steam_appid);
    return Array.from(new Set([...preferred, ...fallbacks]));
  }, [renderSnapshot]);

  const detailImageSrc = imageCandidates[detailImageIndex] ?? "";
  const screenshots = renderSnapshot?.game.screenshot_urls ?? [];
  const trailers = renderSnapshot?.game.trailer_videos ?? [];
  const initials = useMemo(() => {
    if (!renderSnapshot) return "";
    const words = (renderSnapshot.game.name || "").split(/\s+/).filter(Boolean);
    if (!words.length) return "??";
    return words.slice(0, 2).map((word) => word[0]?.toUpperCase() ?? "").join("");
  }, [renderSnapshot]);

  const handleClose = useCallback(() => {
    onOpenChange(false);
  }, [onOpenChange]);

  if (!isClient || (!renderSnapshot && !open)) {
    return null;
  }

  return createPortal(
    <AnimatePresence
      initial={false}
      onExitComplete={() => {
        if (!open) {
          setRenderSnapshot(null);
        }
      }}
      mode="sync"
    >
      {renderSnapshot && open && (
        <>
          <motion.div
            key="detail-sheet-overlay"
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            aria-hidden="true"
          />
          <motion.div
            key="detail-sheet-content"
            className="fixed inset-x-0 bottom-0 z-50 max-h-[85vh] overflow-y-auto rounded-t-3xl bg-ink p-8 shadow-glass"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 280, damping: 32 }}
            role="dialog"
            aria-modal="true"
            aria-labelledby={`detail-sheet-title-${renderSnapshot.id}`}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="space-y-6 text-mist">
              <header>
                <div className="flex justify-between items-start gap-4">
                  <h2
                    id={`detail-sheet-title-${renderSnapshot.id}`}
                    className="text-2xl font-semibold leading-tight"
                  >
                    {renderSnapshot.game.name}
                  </h2>
                  <button
                    type="button"
                    onClick={handleClose}
                    className="text-mist-subtle/70 hover:text-white transition text-xl"
                    aria-label="Close details"
                  >
                    ✕
                  </button>
                </div>
                <p className="text-sm text-mist-subtle/80 mt-2">
                  AppID {renderSnapshot.game.steam_appid} • Followers {renderSnapshot.followers ?? "—"} • WL est.{" "}
                  {renderSnapshot.wishlists_est ?? "—"}
                </p>
              </header>

              <div className="overflow-hidden rounded-2xl border border-white/5 bg-ink-softer/70 aspect-[16/9] w-full max-w-3xl mx-auto">
                {detailImageSrc && !detailImageFailed ? (
                  <img
                    src={detailImageSrc}
                    alt={`${renderSnapshot.game.name} artwork`}
                    className="h-full w-full object-cover"
                    loading="lazy"
                    onError={() => {
                      if (detailImageIndex + 1 < imageCandidates.length) {
                        setDetailImageIndex((prev) => prev + 1);
                      } else {
                        setDetailImageFailed(true);
                      }
                    }}
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-ink via-ink-soft to-ink-dark text-3xl font-semibold text-mist/80">
                    {initials}
                  </div>
                )}
              </div>

              <section className="space-y-3">
                <h3 className="uppercase text-xs tracking-[0.35em] text-mist-subtle/70">Overview</h3>
                <p className="text-sm leading-relaxed text-mist/90 whitespace-pre-wrap">
                  {renderSnapshot.description || "No description provided yet."}
                </p>
              </section>

              <section className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm text-mist-subtle/85">
                <InfoBlock label="Release" value={renderSnapshot.release_date_raw || "TBA"} />
                <InfoBlock label="Detection stage" value={detectionStageLabel} />
                <InfoBlock label="Categories" value={formatList(renderSnapshot.source_categories)} />
                <InfoBlock label="Genres" value={formatList(renderSnapshot.source_genres)} />
                <InfoBlock label="Languages" value={formatList(renderSnapshot.supported_languages)} />
                <InfoBlock label="Developers" value={renderSnapshot.game.developers || "Unknown"} />
              </section>

              {screenshots.length > 0 && (
                <section className="space-y-3">
                  <h3 className="uppercase text-xs tracking-[0.35em] text-mist-subtle/70">Screenshots</h3>
                  <div className="flex gap-3 overflow-x-auto pb-2">
                    {screenshots.slice(0, 6).map((url) => (
                      <img
                        key={url}
                        src={url}
                        alt={`${renderSnapshot.game.name} screenshot`}
                        className="h-32 w-auto rounded-2xl border border-white/10 object-cover sm:h-40"
                        loading="lazy"
                      />
                    ))}
                  </div>
                </section>
              )}

              {trailers.length > 0 && (
                <section className="space-y-3">
                  <h3 className="uppercase text-xs tracking-[0.35em] text-mist-subtle/70">Videos</h3>
                  <div className="grid gap-4">
                    {trailers.slice(0, 2).map((clip, index) => {
                      const key = clip?.id ?? clip?.mp4 ?? clip?.webm ?? `${index}`;
                      return (
                        <div key={key} className="space-y-2">
                          <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/40">
                            <video
                              controls
                              poster={clip?.thumbnail ?? undefined}
                              className="w-full h-auto max-h-72"
                              preload="metadata"
                            >
                              {clip?.mp4 && <source src={clip.mp4} type="video/mp4" />}
                              {clip?.webm && <source src={clip.webm} type="video/webm" />}
                              Your browser does not support the video tag.
                            </video>
                          </div>
                          {clip?.name && (
                            <p className="text-xs uppercase tracking-[0.3em] text-mist-subtle/70">{clip.name}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              <div className="flex gap-3">
                {steamStoreUrl && (
                  <motion.a
                    whileHover={{ scale: 1.01 }}
                    href={steamStoreUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 glass-panel text-center text-sm py-3 hover:bg-ink-softer/80 transition cursor-pointer z-10 relative"
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
                    View on Steam
                  </motion.a>
                )}
                {renderSnapshot.game.website && (
                  <motion.a
                    whileHover={{ scale: 1.01 }}
                    href={renderSnapshot.game.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 glass-panel text-center text-sm py-3 hover:bg-ink-softer/80 transition cursor-pointer z-10 relative"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      window.open(renderSnapshot.game.website ?? "", "_blank", "noopener,noreferrer");
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
                    Official Site
                  </motion.a>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="uppercase text-[0.65rem] tracking-[0.35em] text-mist-subtle/60">{label}</p>
      <p className="mt-1 text-sm text-mist/90 leading-relaxed">{value}</p>
    </div>
  );
}

function formatList(value?: string | null) {
  if (!value) return "Unknown";
  const cleaned = value
    .split(/[;|,]/)
    .map((item) => item.trim().replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, ""))
    .filter(Boolean);
  return cleaned.length ? cleaned.join(" · ") : "Unknown";
}
