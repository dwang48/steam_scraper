import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { GameSnapshot } from "../types";
import { getSteamImageCandidates, getSteamStoreUrl } from "../utils/steamAssets";

interface DetailSheetProps {
  snapshot: GameSnapshot | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DetailSheet({ snapshot, open, onOpenChange }: DetailSheetProps) {
  const steamStoreUrl = snapshot ? getSteamStoreUrl(snapshot.game.steam_appid, snapshot.game.steam_url) : "";
  const detectionStageLabel = snapshot?.detection_stage
    ? snapshot.detection_stage.replace("_", " ")
    : "Unknown stage";
  const imageCandidates = useMemo(
    () => (snapshot ? getSteamImageCandidates(snapshot.game.steam_appid) : []),
    [snapshot]
  );
  const [detailImageIndex, setDetailImageIndex] = useState(0);
  const [detailImageFailed, setDetailImageFailed] = useState(false);

  useEffect(() => {
    setDetailImageIndex(0);
    setDetailImageFailed(false);
  }, [snapshot?.id]);

  const detailImageSrc = imageCandidates[detailImageIndex] ?? "";
  const initials = useMemo(() => {
    if (!snapshot) return "";
    const words = (snapshot.game.name || "").split(/\s+/).filter(Boolean);
    if (!words.length) return "??";
    return words.slice(0, 2).map((word) => word[0]?.toUpperCase() ?? "").join("");
  }, [snapshot]);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 bg-black/50 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild>
              <motion.div
                className="fixed inset-x-0 bottom-0 rounded-t-3xl bg-ink max-h-[85vh] overflow-y-auto p-8 shadow-glass"
                initial={{ y: "100%" }}
                animate={{ y: 0 }}
                exit={{ y: "100%" }}
                transition={{ type: "spring", stiffness: 280, damping: 32 }}
              >
                {snapshot && (
                  <div className="space-y-6 text-mist">
                    <header>
                      <div className="flex justify-between items-start gap-4">
                        <Dialog.Title className="text-2xl font-semibold leading-tight">{snapshot.game.name}</Dialog.Title>
                        <Dialog.Close className="text-mist-subtle/70 hover:text-white transition text-xl">✕</Dialog.Close>
                      </div>
                      <p className="text-sm text-mist-subtle/80 mt-2">
                        AppID {snapshot.game.steam_appid} • Followers {snapshot.followers ?? "—"} • WL est.{" "}
                        {snapshot.wishlists_est ?? "—"}
                      </p>
                    </header>

                    <div className="overflow-hidden rounded-2xl border border-white/5 bg-ink-softer/70">
                      {detailImageSrc && !detailImageFailed ? (
                        <img
                          src={detailImageSrc}
                          alt={`${snapshot.game.name} artwork`}
                          className="w-full object-cover"
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
                        <div className="flex h-40 items-center justify-center bg-gradient-to-br from-ink via-ink-soft to-ink-dark text-3xl font-semibold text-mist/80">
                          {initials}
                        </div>
                      )}
                    </div>

                    <section className="space-y-3">
                      <h3 className="uppercase text-xs tracking-[0.35em] text-mist-subtle/70">Overview</h3>
                      <p className="text-sm leading-relaxed text-mist/90 whitespace-pre-wrap">
                        {snapshot.description || "No description provided yet."}
                      </p>
                    </section>

                    <section className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm text-mist-subtle/85">
                      <InfoBlock label="Release" value={snapshot.release_date_raw || "TBA"} />
                      <InfoBlock label="Detection stage" value={detectionStageLabel} />
                      <InfoBlock label="Categories" value={formatList(snapshot.source_categories)} />
                      <InfoBlock label="Genres" value={formatList(snapshot.source_genres)} />
                      <InfoBlock label="Languages" value={snapshot.supported_languages || "Unknown"} />
                      <InfoBlock label="Developers" value={snapshot.game.developers || "Unknown"} />
                    </section>

                    <div className="flex gap-3">
                      {steamStoreUrl && (
                        <a
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
                        >
                          View on Steam
                        </a>
                      )}
                      {snapshot.game.website && (
                        <a
                          href={snapshot.game.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 glass-panel text-center text-sm py-3 hover:bg-ink-softer/80 transition cursor-pointer z-10 relative"
                          onClick={(event) => {
                            event.preventDefault();
                            event.stopPropagation();
                            window.open(snapshot.game.website, "_blank", "noopener,noreferrer");
                          }}
                          onPointerDown={(event) => {
                            event.stopPropagation();
                          }}
                          onMouseDown={(event) => {
                            event.stopPropagation();
                          }}
                        >
                          Official Site
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
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

function formatList(value: string) {
  return value ? value.split(/[;|,]/).map((item) => item.trim()).filter(Boolean).join(" · ") : "Unknown";
}
