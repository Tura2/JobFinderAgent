import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { MatchListItem } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function NearMisses() {
  const [items, setItems] = useState<MatchListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getNearMisses().then(setItems).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-4 text-center text-gray-500">Loading...</div>;
  }

  return (
    <div className="pb-20 pt-4 px-4">
      <div className="mb-4">
        <h1 className="text-xl font-bold">Near Misses</h1>
        <p className="text-xs text-gray-500 mt-1">Jobs scored below your threshold — review manually</p>
      </div>
      {items.length === 0 ? (
        <p className="text-center text-gray-500 mt-12">No near misses yet.</p>
      ) : (
        <div className="space-y-2">
          {items.map((m) => (
            <div key={m.id} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-sm">{m.job_title}</p>
                  <p className="text-xs text-gray-400">{m.company_name}</p>
                </div>
                <StatusBadge score={m.score} status={m.status} />
              </div>
              <p className="text-xs text-gray-500 mt-2 line-clamp-2">{m.reasoning}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
