import { useState, useEffect } from 'react';
import { BarChart2 } from 'lucide-react';
import { api } from '../api/client';
import type { Application } from '../types';
import { Avatar } from '../components/MatchCard';

const scoreColor = (s: number) =>
  s >= 85 ? '#22c55e' : s >= 70 ? '#eab308' : s >= 55 ? '#f97316' : '#ef4444';

const COLUMNS = [
  { key: 'applied',   label: 'Applied',      color: '#6366f1' },
  { key: 'pending',   label: 'Pending',       color: '#6366f1' },
  { key: 'phone',     label: 'Phone Screen',  color: '#0ea5e9' },
  { key: 'interview', label: 'Interview',     color: '#f59e0b' },
  { key: 'offer',     label: 'Offer 🎉',      color: '#22c55e' },
  { key: 'rejected',  label: 'Rejected',      color: '#4b5563' },
];

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function Tracker() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTracker().then(setApplications).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-dvh">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  const total = applications.length;

  if (total === 0) {
    return (
      <div style={{ paddingBottom: 96, paddingTop: 24, paddingInline: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100dvh' }}>
        <div style={{
          background: '#1a1f2e', border: '1px solid #1f2937', width: 72, height: 72,
          borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16,
        }}>
          <BarChart2 size={30} color="#374151" />
        </div>
        <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 16, marginBottom: 6 }}>No applications yet</div>
        <div style={{ color: '#4b5563', fontSize: 13 }}>Applied jobs will appear here.</div>
      </div>
    );
  }

  const visibleCols = COLUMNS.filter(col => applications.some(a => a.outcome_status === col.key));

  return (
    <div style={{ paddingBottom: 96, paddingTop: 24 }}>
      <div style={{ paddingInline: 16, marginBottom: 14 }}>
        <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 700, letterSpacing: '-0.03em' }}>Tracker</h1>
        <p style={{ color: '#4b5563', fontSize: 13, marginTop: 2 }}>
          {total} application{total !== 1 ? 's' : ''} tracked
        </p>
      </div>

      {/* Horizontal kanban */}
      <div style={{
        display: 'flex', gap: 10, overflowX: 'auto',
        paddingInline: 16, paddingBottom: 8,
        scrollbarWidth: 'none',
      }}>
        {visibleCols.map(col => {
          const items = applications.filter(a => a.outcome_status === col.key);
          return (
            <div key={col.key} style={{ minWidth: 188, flexShrink: 0 }}>
              <div style={{
                color: '#4b5563', fontSize: 10, fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: '0.1em',
                marginBottom: 8, display: 'flex', alignItems: 'center', gap: 5,
              }}>
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: col.color, flexShrink: 0 }} />
                {col.label}
                <span style={{ color: '#374151', fontWeight: 400 }}>({items.length})</span>
              </div>

              {items.map(app => {
                const sc = scoreColor(app.score);
                return (
                  <a
                    key={app.id}
                    href={`/tracker/${app.id}`}
                    style={{
                      display: 'block',
                      background: '#1a2030', border: '1px solid #1f2937',
                      borderRadius: 10, padding: 10, marginBottom: 6,
                      textDecoration: 'none',
                    }}
                  >
                    <div style={{ display: 'flex', gap: 7, alignItems: 'center', marginBottom: 7 }}>
                      <Avatar name={app.company_name} size={26} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{
                          color: '#e5e7eb', fontSize: 12, fontWeight: 600,
                          lineHeight: 1.3, overflow: 'hidden', textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap', maxWidth: 120,
                        }}>
                          {app.job_title}
                        </div>
                        <div style={{ color: '#4b5563', fontSize: 11 }}>{app.company_name}</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#374151', fontSize: 11 }}>
                        {app.applied_at ? formatDate(app.applied_at) : '—'}
                      </span>
                      <div style={{ height: 3, width: 36, background: '#1f2937', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${app.score}%`, background: sc, borderRadius: 2 }} />
                      </div>
                    </div>
                  </a>
                );
              })}

              {items.length === 0 && (
                <div style={{
                  border: '1px dashed #1a2030', borderRadius: 10, height: 52,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <span style={{ color: '#1f2937', fontSize: 11 }}>—</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
