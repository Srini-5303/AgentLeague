import type { TurnEvent } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? ""; // "" → vite proxy in dev

/**
 * POST /turn and parse the SSE stream, invoking onEvent for each event.
 * Works against the FastAPI GM (local) or the Container App (Azure) identically.
 */
export async function streamTurn(
  input: string,
  token: string | null,
  onEvent: (e: TurnEvent) => void,
  confirmToken?: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/turn`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ input, confirm_token: confirmToken ?? null }),
  });

  if (!res.body) throw new Error("no response body");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? ""; // keep incomplete trailing frame
    for (const frame of frames) {
      for (const line of frame.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        try {
          onEvent(JSON.parse(line.slice(6)) as TurnEvent);
        } catch {
          /* ignore keep-alive comments / partial frames */
        }
      }
    }
  }
}

export async function fetchState(token: string | null) {
  const res = await fetch(`${API_BASE}/state`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) return null;
  return res.json();
}

/** Delete the saved campaign and start a fresh one. Returns the new state. */
export async function resetSession(token: string | null) {
  const res = await fetch(`${API_BASE}/reset`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`reset failed (${res.status})`);
  return res.json();
}
