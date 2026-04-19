import type { MatchListItem } from "../types";
import StatusBadge from "./StatusBadge";

interface MatchCardProps {
  match: MatchListItem;
  onTap: (id: number) => void;
  onSkip: (id: number) => void;
  onApply: (id: number) => void;
}

export default function MatchCard({ match, onTap, onSkip, onApply }: MatchCardProps) {
  return (
    <div
      className="bg-gray-900 rounded-xl p-4 border border-gray-800 shadow-lg"
      onClick={() => onTap(match.id)}
      role="button"
      tabIndex={0}
      data-testid="match-card"
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-white">{match.job_title}</h3>
          <p className="text-sm text-gray-400">{match.company_name}</p>
        </div>
        <StatusBadge score={match.score} status={match.status} />
      </div>
      <p className="text-sm text-gray-300 mb-4 line-clamp-2">{match.reasoning}</p>
      <div className="flex gap-3">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSkip(match.id);
          }}
          className="flex-1 py-2 rounded-lg bg-gray-800 text-gray-400 hover:bg-gray-700 text-sm font-medium"
        >
          Skip
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onApply(match.id);
          }}
          className="flex-1 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-500 text-sm font-medium"
        >
          Apply
        </button>
      </div>
    </div>
  );
}
