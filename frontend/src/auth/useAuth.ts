import { useState } from "react";

/**
 * Auth abstraction. In local dev (VITE_AUTH=dev, the default) there's a one-click
 * dev login and the backend runs with DEV_AUTH_BYPASS — no real token needed.
 * In Azure (VITE_AUTH=msal) this is where @azure/msal-react wires in: loginPopup,
 * acquireTokenSilent, and returning the JWT held in memory only (never localStorage).
 */
const MODE = import.meta.env.VITE_AUTH ?? "dev";

export interface Auth {
  isAuthenticated: boolean;
  token: string | null;
  login: () => void;
  logout: () => void;
  mode: string;
}

export function useAuth(): Auth {
  const [authed, setAuthed] = useState(MODE === "dev"); // dev: start signed-in
  const [token] = useState<string | null>(null);        // dev: bypass → no token

  return {
    isAuthenticated: authed,
    token,
    mode: MODE,
    login: () => setAuthed(true),
    logout: () => setAuthed(false),
  };
}
