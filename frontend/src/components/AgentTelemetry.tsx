import { useState } from "react";
import type { TraceSummary } from "../types";

export function AgentTelemetry({ trace }: { trace: TraceSummary | null }) {
  // On by default in dev mode (the PRD's demo behavior).
  const [open, setOpen] = useState(import.meta.env.DEV);
  if (!trace) return null;
  const max = Math.max(1, ...trace.spans.map((s) => s.ms));

  return (
    <div className="panel telemetry">
      <button className="toggle" onClick={() => setOpen((o) => !o)}>
        {open ? "▾" : "▸"} Agent Telemetry · turn {trace.turn} · {trace.total_ms}ms
      </button>
      {open && (
        <>
          <div className="gantt">
            {trace.spans.map((s, i) => (
              <div key={i} className="gantt-row">
                <span className="gantt-label">{s.name}</span>
                <div className="gantt-track">
                  <div className="gantt-bar" style={{ width: `${(s.ms / max) * 100}%` }}>
                    {s.ms}ms
                  </div>
                </div>
              </div>
            ))}
          </div>
          {Object.keys(trace.agent_messages).length > 0 && (
            <div className="agent-msgs">
              {Object.entries(trace.agent_messages).map(([agent, msg]) => (
                <div key={agent} className="agent-msg">
                  <strong>{agent}:</strong> “{msg}”
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
