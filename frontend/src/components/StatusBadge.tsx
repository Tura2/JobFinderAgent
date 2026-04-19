interface StatusBadgeProps {
  score: number;
  status?: string;
}

const scoreColor = (score: number) => {
  if (score >= 85) return "bg-green-500/20 text-green-400";
  if (score >= 70) return "bg-yellow-500/20 text-yellow-400";
  if (score >= 55) return "bg-orange-500/20 text-orange-400";
  return "bg-red-500/20 text-red-400";
};

const statusColor: Record<string, string> = {
  new: "bg-blue-500/20 text-blue-400",
  applied: "bg-purple-500/20 text-purple-400",
  interview: "bg-green-500/20 text-green-400",
  offer: "bg-emerald-500/20 text-emerald-400",
  rejected: "bg-red-500/20 text-red-400",
  skipped: "bg-gray-500/20 text-gray-400",
  no_response: "bg-gray-500/20 text-gray-500",
};

export default function StatusBadge({ score, status }: StatusBadgeProps) {
  return (
    <div className="flex items-center gap-2">
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${scoreColor(score)}`}>
        {score}%
      </span>
      {status && (
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor[status] || "bg-gray-500/20 text-gray-400"}`}
        >
          {status}
        </span>
      )}
    </div>
  );
}
