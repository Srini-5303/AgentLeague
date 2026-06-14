import { useEffect, useRef } from "react";

interface Props {
  narration: string;
  status: "idle" | "deliberating" | "streaming";
  agents: string[];
}

export function AdventureLog({ narration, status, agents }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [narration, status]);

  return (
    <div className="adventure-log">
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
