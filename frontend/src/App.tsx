import { useEffect, useState } from "react";
import { fetchState, resetSession, streamTurn } from "./api/foundryClient";
import { AdventureLog } from "./components/AdventureLog";
import { AgentTelemetry } from "./components/AgentTelemetry";
import { CharacterSheet } from "./components/CharacterSheet";
import { DiceRoll } from "./components/DiceRoll";
import { PlayerInput } from "./components/PlayerInput";
import { QuestJournal } from "./components/QuestJournal";
import { useAuth } from "./auth/useAuth";
import type { CharacterState, RollResult, TraceSummary, TurnEvent } from "./types";

type Status = "idle" | "deliberating" | "streaming";

interface Confirm {
  prompt: string;
  action_token: string;
  action: string;
}

export default function App() {
  const auth = useAuth();
  const [party, setParty] = useState<CharacterState[]>([]);
  const [narration, setNarration] = useState("");
  const [choices, setChoices] = useState<string[]>([]);
  const [rolls, setRolls] = useState<RollResult[]>([]);
  const [trace, setTrace] = useState<TraceSummary | null>(null);
  const [agents, setAgents] = useState<string[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [location, setLocation] = useState("");
  const [activeQuest, setActiveQuest] = useState("");
  const [questStage, setQuestStage] = useState(1);
  const [questLog, setQuestLog] = useState<string[]>([]);
  const [confirm, setConfirm] = useState<Confirm | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recap, setRecap] = useState<string[]>([]);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetting, setResetting] = useState(false);

  function applyState(s: any) {
    setParty(s.party ?? []);
    setLocation(s.location ?? "");
    setActiveQuest(s.active_quest ?? "");
    setQuestStage(s.quest_stage ?? 1);
    setQuestLog(s.quest_log ?? []);
    setRecap(s.recent_history ?? []);
  }

  // Resume saved campaign on load (PRD US-05: no "load game" screen).
  useEffect(() => {
    if (!auth.isAuthenticated) return;
    fetchState(auth.token).then((s) => {
      if (s) applyState(s);
    });
  }, [auth.isAuthenticated, auth.token]);

  async function startOver() {
    setResetting(true);
    setError(null);
    try {
      const fresh = await resetSession(auth.token);
      applyState(fresh);
      setNarration("");
      setChoices([]);
      setRolls([]);
      setTrace(null);
      setConfirm(null);
      setStatus("idle");
    } catch (err) {
      setError(String(err));
    } finally {
      setResetting(false);
      setShowResetConfirm(false);
    }
  }

  async function act(text: string, confirmToken?: string) {
    setError(null);
    setConfirm(null);
    setNarration("");
    setRolls([]);
    setChoices([]);
    setAgents([]);
    setStatus("deliberating");
    try {
      await streamTurn(
        text,
        auth.token,
        (e: TurnEvent) => {
          switch (e.type) {
            case "agent_start":
              setAgents(e.agents);
              break;
            case "token":
              setStatus("streaming");
              setNarration((n) => n + e.text);
              break;
            case "dice":
              setRolls((r) => [...r, e]);
              break;
            case "confirm":
              setConfirm({ prompt: e.prompt, action_token: e.action_token, action: e.action });
              setStatus("idle");
              break;
            case "done":
              setParty(e.party);
              setChoices(e.choices);
              setTrace(e.trace_summary);
              setLocation(e.location);
              setActiveQuest(e.active_quest);
              setQuestStage(e.quest_stage);
              setQuestLog(e.quest_log);
              if (e.state_warning) setError("Your deeds may not have been fully recorded.");
              setStatus("idle");
              break;
            case "error":
              setError(`(${e.status}) ${e.message}`);
              setStatus("idle");
              break;
          }
        },
        confirmToken,
      );
    } catch (err) {
      setError(String(err));
      setStatus("idle");
    }
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="login">
        <h1>Eldervale</h1>
        <p>The moon is broken. The dead walk. Will you find the Shards?</p>
        <button onClick={auth.login}>Enter the Saga</button>
      </div>
    );
  }

  const busy = status !== "idle";

  return (
    <div className="app">
      <header>
        <h1>Eldervale — The Shards of Máni</h1>
        <div className="header-actions">
          <button
            className="newgame"
            onClick={() => setShowResetConfirm(true)}
            disabled={busy || resetting}
          >
            New Game
          </button>
          <button className="logout" onClick={auth.logout}>
            Leave
          </button>
        </div>
      </header>

      <main>
        <section className="story">
          <AdventureLog narration={narration} status={status} agents={agents} recap={recap} />
          {error && <div className="error-banner">{error}</div>}
          <PlayerInput choices={choices} disabled={busy || !!confirm} onSubmit={(t) => act(t)} />
        </section>

        <aside className="sidebar">
          <CharacterSheet party={party} />
          <QuestJournal
            location={location}
            activeQuest={activeQuest}
            questStage={questStage}
            questLog={questLog}
          />
          <DiceRoll rolls={rolls} />
          <AgentTelemetry trace={trace} />
        </aside>
      </main>

      {confirm && (
        <div className="modal-backdrop">
          <div className="modal">
            <p>{confirm.prompt}</p>
            <p className="modal-action">“{confirm.action}”</p>
            <div className="modal-buttons">
              <button className="danger" onClick={() => act(confirm.action, confirm.action_token)}>
                I am certain
              </button>
              <button onClick={() => setConfirm(null)}>Reconsider</button>
            </div>
          </div>
        </div>
      )}

      {showResetConfirm && (
        <div className="modal-backdrop">
          <div className="modal">
            <p>
              Start a new game? This will <strong>permanently delete</strong> your saved
              progress — your party, quest, and all your choices so far. This cannot be undone.
            </p>
            <div className="modal-buttons">
              <button className="danger" onClick={startOver} disabled={resetting}>
                {resetting ? "Erasing the saga…" : "Yes, delete and start over"}
              </button>
              <button onClick={() => setShowResetConfirm(false)} disabled={resetting}>
                Keep my progress
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
