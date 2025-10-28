import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { motion, AnimatePresence } from "framer-motion";

interface LikeReasonDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultNote?: string;
  onSubmit: (note: string) => void;
  submitting?: boolean;
  onSkip?: () => void;
}

export function LikeReasonDialog({ open, onOpenChange, defaultNote = "", onSubmit, submitting, onSkip }: LikeReasonDialogProps) {
  const [note, setNote] = useState(defaultNote);

  useEffect(() => {
    if (open) {
      setNote(defaultNote);
    }
  }, [open, defaultNote]);

  const handleConfirm = () => {
    if (submitting) return;
    onSubmit(note.trim());
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild>
              <motion.div
                className="fixed inset-x-4 top-1/2 z-50 -translate-y-1/2 rounded-3xl bg-ink px-6 py-6 sm:px-8 sm:py-8 shadow-glass max-w-md mx-auto"
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: "spring", stiffness: 260, damping: 26 }}
              >
                <Dialog.Title className="text-lg sm:text-xl font-semibold text-mist">Add a note</Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-mist-subtle/70">
                  Share why you liked this game (optional).
                </Dialog.Description>
                <textarea
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  className="mt-4 w-full min-h-[120px] rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-mist focus:outline-none focus:ring-2 focus:ring-accent/70"
                  placeholder="What stood out? Mechanics, art style, vibe…"
                  maxLength={500}
                />
                <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      if (submitting) return;
                      if (onSkip) {
                        onSkip();
                      } else {
                        onSubmit("");
                      }
                    }}
                    className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-mist-subtle/80 hover:bg-white/10 hover:text-white transition disabled:opacity-50"
                    disabled={submitting}
                  >
                    Skip
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirm}
                    disabled={submitting}
                    className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-white hover:text-ink transition disabled:opacity-50"
                  >
                    {submitting ? "Saving…" : "Save"}
                  </button>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
