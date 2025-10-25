import * as Dialog from "@radix-ui/react-dialog";
import { useState, FormEvent } from "react";
import clsx from "clsx";
import type { LoginPayload, RegisterPayload } from "../types";

type AuthMode = "login" | "register";

interface AuthDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLogin: (payload: LoginPayload) => Promise<void>;
  onRegister: (payload: RegisterPayload) => Promise<void>;
}

export function AuthDialog({ open, onOpenChange, onLogin, onRegister }: AuthDialogProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  const [loginFields, setLoginFields] = useState<LoginPayload>({
    username: "",
    password: "",
    remember_me: true
  });

  const [registerFields, setRegisterFields] = useState<RegisterPayload>({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: ""
  });

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await onLogin(loginFields);
      } else {
        await onRegister(registerFields);
      }
      onOpenChange(false);
    } catch (error) {
      if (error instanceof Error) {
        setFormError(error.message || "Authentication failed.");
      } else {
        setFormError("Authentication failed.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setFormError(null);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed inset-x-4 top-[10vh] sm:top-[15vh] sm:inset-x-auto sm:right-1/2 sm:translate-x-1/2 z-50 max-w-md rounded-3xl bg-ink p-6 sm:p-8 shadow-glass focus:outline-none">
          <header className="mb-6">
            <Dialog.Title className="text-2xl font-semibold text-mist">
              {mode === "login" ? "Sign in" : "Create your account"}
            </Dialog.Title>
            <p className="mt-2 text-sm text-mist-subtle/80">
              {mode === "login"
                ? "Enter your credentials to access the curator tools."
                : "Join the curator team with a new account."}
            </p>
          </header>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-3">
              <label className="block text-sm text-mist-subtle/80">
                Username
                <input
                  type="text"
                  value={mode === "login" ? loginFields.username : registerFields.username}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (mode === "login") {
                      setLoginFields((prev) => ({ ...prev, username: value }));
                    } else {
                      setRegisterFields((prev) => ({ ...prev, username: value }));
                    }
                  }}
                  required
                  className="mt-1 w-full rounded-xl border border-white/10 bg-ink-subtle/60 px-3 py-2 text-sm text-mist outline-none focus:border-accent"
                  autoComplete="username"
                />
              </label>

              {mode === "register" && (
                <>
                  <label className="block text-sm text-mist-subtle/80">
                    Email
                    <input
                      type="email"
                      value={registerFields.email}
                      onChange={(event) =>
                        setRegisterFields((prev) => ({ ...prev, email: event.target.value }))
                      }
                      required
                      className="mt-1 w-full rounded-xl border border-white/10 bg-ink-subtle/60 px-3 py-2 text-sm text-mist outline-none focus:border-accent"
                      autoComplete="email"
                    />
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label className="block text-sm text-mist-subtle/80">
                      First name
                      <input
                        type="text"
                        value={registerFields.first_name || ""}
                        onChange={(event) =>
                          setRegisterFields((prev) => ({ ...prev, first_name: event.target.value }))
                        }
                        className="mt-1 w-full rounded-xl border border-white/10 bg-ink-subtle/60 px-3 py-2 text-sm text-mist outline-none focus:border-accent"
                        autoComplete="given-name"
                      />
                    </label>
                    <label className="block text-sm text-mist-subtle/80">
                      Last name
                      <input
                        type="text"
                        value={registerFields.last_name || ""}
                        onChange={(event) =>
                          setRegisterFields((prev) => ({ ...prev, last_name: event.target.value }))
                        }
                        className="mt-1 w-full rounded-xl border border-white/10 bg-ink-subtle/60 px-3 py-2 text-sm text-mist outline-none focus:border-accent"
                        autoComplete="family-name"
                      />
                    </label>
                  </div>
                </>
              )}

              <label className="block text-sm text-mist-subtle/80">
                Password
                <input
                  type="password"
                  value={mode === "login" ? loginFields.password : registerFields.password}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (mode === "login") {
                      setLoginFields((prev) => ({ ...prev, password: value }));
                    } else {
                      setRegisterFields((prev) => ({ ...prev, password: value }));
                    }
                  }}
                  required
                  className="mt-1 w-full rounded-xl border border-white/10 bg-ink-subtle/60 px-3 py-2 text-sm text-mist outline-none focus:border-accent"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                />
              </label>

              {mode === "login" && (
                <label className="inline-flex items-center gap-2 text-sm text-mist-subtle/70">
                  <input
                    type="checkbox"
                    checked={!!loginFields.remember_me}
                    onChange={(event) =>
                      setLoginFields((prev) => ({ ...prev, remember_me: event.target.checked }))
                    }
                    className="rounded border-white/20 bg-transparent text-accent focus:ring-accent"
                  />
                  Keep me signed in
                </label>
              )}
            </div>

            {formError && (
              <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl px-3 py-2">
                {formError}
              </p>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className={clsx(
                "w-full rounded-xl bg-accent text-white py-3 text-sm font-medium transition",
                "hover:bg-accent/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
                isSubmitting && "opacity-70 cursor-not-allowed"
              )}
            >
              {isSubmitting
                ? "Working…"
                : mode === "login"
                ? "Sign in"
                : "Create account"}
            </button>
          </form>

          <footer className="mt-6 text-center text-sm text-mist-subtle/70">
            {mode === "login" ? (
              <>
                Need an account?{" "}
                <button
                  type="button"
                  onClick={() => switchMode("register")}
                  className="text-accent hover:text-white transition underline-offset-4 hover:underline"
                >
                  Register
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => switchMode("login")}
                  className="text-accent hover:text-white transition underline-offset-4 hover:underline"
                >
                  Sign in
                </button>
              </>
            )}
          </footer>

          <Dialog.Close asChild>
            <button
              type="button"
              className="absolute top-4 right-4 text-mist-subtle/70 hover:text-white transition text-lg"
              aria-label="Close dialog"
            >
              ✕
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
