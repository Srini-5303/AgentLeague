interface Props {
  location: string;
  activeQuest: string;
  questStage: number;
  questLog: string[];
}

export function QuestJournal({ location, activeQuest, questStage, questLog }: Props) {
  return (
    <div className="panel">
      <h3>Quest Journal</h3>
      <div className="quest-where">
        <div>
          <span className="label">Location</span>
          <span>{location}</span>
        </div>
        <div>
          <span className="label">Quest</span>
          <span>
            {activeQuest} <em>(stage {questStage})</em>
          </span>
        </div>
      </div>
      {questLog.length > 0 && (
        <ul className="quest-log">
          {questLog.map((q, i) => (
            <li key={i}>{q}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
