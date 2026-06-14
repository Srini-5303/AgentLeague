import { useEffect, useRef } from "react";

interface Props {
  narration: string;
  status: "idle" | "deliberating" | "streaming";
  agents: string[];
  recap: string[];
}

export function AdventureLog({ narration, status, agents, recap }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [narration, status]);

  // On resume (no narration yet) show "Previously on…" from the rolling history.
  const showRecap = !narration && status === "idle" && recap.length > 0;

  return (
    <div className="adventure-log">
      {showRecap && (
        <div className="recap">
          <h4 className="recap-title">Previously on… The Shards of Máni</h4>
          {recap.map((line, i) => (
            <p key={i} className="recap-line">
              {line}
            </p>
          ))}
        </div>
      )}
      {narration && <p className="narration">{narration}</p>}
      {status === "deliberating" && (
        <p className="deliberating">
          The party deliberates
          {agents.length > 0 && <span className="agents"> ({agents.join(", ")})</span>}
          <span className="dots">…</span>
        </p>
      )}
      <div ref={endRef} />
    </div>
  );
}
