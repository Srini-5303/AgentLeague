import type { RollResult } from "../types";

export function DiceRoll({ rolls }: { rolls: RollResult[] }) {
  if (rolls.length === 0) return null;
  return (
    <div className="panel">
      <h3>Dice</h3>
      {rolls.map((r, i) => (
        <div key={i} className={`roll ${r.result}`}>
          <span className="d20">{r.roll}</span>
          <div className="roll-detail">
            <strong>
              {r.actor} · {r.check}
            </strong>
            <span>
              {r.total} vs DC {r.difficulty} → <em>{r.result}</em>
            </span>
            {r.consequence && <span className="consequence">{r.consequence}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
