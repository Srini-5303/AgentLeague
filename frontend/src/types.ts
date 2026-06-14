// Mirrors the orchestrator's SSE event vocabulary and state shapes.

export interface RollResult {
  actor: string;
  check: string;
  roll: number;
  total: number;
  difficulty: number;
  result: "success" | "partial" | "failure";
  consequence?: string;
}

export interface SpanSummary { name: string; ms: number; }

export interface TraceSummary {
  turn: number;
  trace_id: string;
  total_ms: number;
  spans: SpanSummary[];
  agent_messages: Record<string, string>;
}

export interface CharacterState {
  agent: string;
  name: string;
  char_class: string;
  health: number;
  max_health: number;
  conditions: string[];
  trust_level: string | null;
  is_player: boolean;
}

export interface DoneEvent {
  type: "done";
  turn: number;
  choices: string[];
  rolls: RollResult[];
  trace_summary: TraceSummary;
  party: CharacterState[];
  quest_log: string[];
  location: string;
  active_quest: string;
  quest_stage: number;
  world_flags: Record<string, unknown>;
  state_warning?: boolean;
}

export type TurnEvent =
  | { type: "agent_start"; agents: string[] }
  | { type: "token"; text: string }
  | ({ type: "dice" } & RollResult)
  | { type: "confirm"; prompt: string; action_token: string; action: string }
  | DoneEvent
  | { type: "error"; status: number; message: string };
