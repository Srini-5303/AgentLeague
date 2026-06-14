import type { CharacterState } from "../types";

export function CharacterSheet({ party }: { party: CharacterState[] }) {
  if (party.length === 0) return null;
  return (
    <div className="panel">
      <h3>The Party</h3>
      {party.map((c) => {
        const pct = Math.round((c.health / Math.max(1, c.max_health)) * 100);
        return (
          <div key={c.agent} className={`char ${c.is_player ? "player" : ""}`}>
            <div className="char-head">
              <span className="char-name">{c.name}</span>
              <span className="char-class">{c.char_class}</span>
            </div>
            <div className="hp-bar">
              <div className="hp-fill" style={{ width: `${pct}%` }} />
              <span className="hp-text">
                {c.health}/{c.max_health}
              </span>
            </div>
            {c.conditions.length > 0 && (
              <div className="conditions">
                {c.conditions.map((cond) => (
                  <span key={cond} className="condition">
                    {cond}
                  </span>
                ))}
              </div>
            )}
            {c.trust_level && <div className="trust">trust: {c.trust_level}</div>}
          </div>
        );
      })}
    </div>
  );
}
