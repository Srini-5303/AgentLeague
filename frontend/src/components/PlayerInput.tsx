import { useState } from "react";

interface Props {
  choices: string[];
  disabled: boolean;
  onSubmit: (text: string) => void;
}

export function PlayerInput({ choices, disabled, onSubmit }: Props) {
  const [text, setText] = useState("");

  function submit(value: string) {
    const v = value.trim();
    if (!v || disabled) return;
    onSubmit(v);
    setText("");
  }

  return (
    <div className="player-input">
      <div className="quick-actions">
        {choices.map((c) => (
          <button key={c} disabled={disabled} onClick={() => submit(c)} className="quick-action">
            {c}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(text);
        }}
      >
        <input
          value={text}
          disabled={disabled}
          placeholder="What do you do?"
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit" disabled={disabled || !text.trim()}>
          Act
        </button>
      </form>
    </div>
  );
}
