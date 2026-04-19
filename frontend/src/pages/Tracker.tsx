import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { Application } from "../types";
import StatusBadge from "../components/StatusBadge";

const STATUS_COLUMNS = ["pending", "interview", "offer", "rejected"];

function isUnconfirmedOverdue(app: Application): boolean {
  if (app.confirmed_at) return false;
  if (!app.applied_at) return false;
  const elapsed = Date.now() - new Date(app.applied_at).getTime();
  return elapsed > 48 * 60 * 60 * 1000;
}

export default function Tracker() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTracker().then(setApplications).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-4 text-center text-gray-500">Loading...</div>;
  }

  return (
    <div className="pb-20 pt-4 px-4">
      <h1 className="text-xl font-bold mb-4">Application Tracker</h1>

      {STATUS_COLUMNS.map((status) => {
        const items = applications.filter((a) => a.outcome_status === status);
        return (
          <div key={status} className="mb-6">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">
              {status} ({items.length})
            </h2>
            {items.length === 0 ? (
              <p className="text-xs text-gray-600">None</p>
            ) : (
              <div className="space-y-2">
                {items.map((app) => (
                  <a
                    key={app.id}
                    href={`/tracker/${app.id}`}
                    className="block bg-gray-900 rounded-lg p-3 border border-gray-800"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-sm">{app.job_title}</p>
                        <p className="text-xs text-gray-400">{app.company_name}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge score={app.score} />
                        {isUnconfirmedOverdue(app) && (
                          <span className="text-xs bg-yellow-900/50 text-yellow-400 px-2 py-0.5 rounded-full">
                            Did you submit?
                          </span>
                        )}
                      </div>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
