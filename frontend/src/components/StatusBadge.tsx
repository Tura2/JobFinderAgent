interface StatusBadgeProps {
  score: number;
  status?: string;
}

function scoreConfig(score: number) {
  if (score >= 85) return { bar: "bg-emerald-500", text: "text-emerald-400", ring: "ring-emerald-500/30" };
  if (score >= 70) return { bar: "bg-yellow-400", text: "text-yellow-400", ring: "ring-yellow-400/30" };
  if (score >= 55) return { bar: "bg-orange-400", text: "text-orange-400", ring: "ring-orange-400/30" };
  return { bar: "bg-red-500", text: "text-red-400", ring: "ring-red-500/30" };
}

const statusConfig: Record<string, { label: string; cls: string }> = {
  new:         { label: "New",         cls: "bg-indigo-500/20 text-indigo-300 ring-indigo-500/20" },
  applied:     { label: "Applied",     cls: "bg-violet-500/20 text-violet-300 ring-violet-500/20" },
  interview:   { label: "Interview",   cls: "bg-emerald-500/20 text-emerald-300 ring-emerald-500/20" },
  offer:       { label: "Offer",       cls: "bg-teal-500/20 text-teal-300 ring-teal-500/20" },
  rejected:    { label: "Rejected",    cls: "bg-red-500/20 text-red-400 ring-red-500/20" },
  skipped:     { label: "Skipped",     cls: "bg-gray-700/60 text-gray-500 ring-gray-700/30" },
  no_response: { label: "No response", cls: "bg-gray-700/60 text-gray-500 ring-gray-700/30" },
  low_match:   { label: "Near miss",   cls: "bg-amber-900/30 text-amber-500 ring-amber-700/20" },
};

export default function StatusBadge({ score, status }: StatusBadgeProps) {
  const sc = scoreConfig(score);
  const st = status ? (statusConfig[status] ?? { label: status, cls: "bg-gray-700/60 text-gray-400 ring-gray-700/20" }) : null;

  return (
    <div className="flex items-center gap-2">
      {/* Score pill with mini bar */}
      <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full ring-1 bg-gray-800/80 ${sc.ring}`}>
        <div className="w-16 h-1.5 rounded-full bg-gray-700 overflow-hidden">
          <div className={`h-full rounded-full ${sc.bar}`} style={{ width: `${score}%` }} />
        </div>
        <span className={`text-xs font-semibold tabular-nums ${sc.text}`}>{score}</span>
      </div>

      {st && (
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ${st.cls}`}>
          {st.label}
        </span>
      )}
    </div>
  );
}
