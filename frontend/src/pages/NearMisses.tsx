import { useEffect, useState } from 'react';
import { TrendingDown } from 'lucide-react';
import { api } from '../api/client';
import type { MatchListItem } from '../types';

const scoreColor = (s: number) =>
  s >= 85 ? '#22c55e' : s >= 70 ? '#eab308' : s >= 55 ? '#f97316' : '#ef4444';

export default function NearMisses() {
  const [items, setItems] = useState<MatchListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getNearMisses().then(setItems).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-dvh">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div style={{ paddingBottom: 96, paddingTop: 24, paddingInline: 16 }}>
      <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 700, letterSpacing: '-0.03em' }}>Near Misses</h1>
      <p style={{ color: '#4b5563', fontSize: 13, marginTop: 2, marginBottom: 18 }}>
        Below threshold — review manually if interested
      </p>

      {items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '64px 0' }}>
          <div style={{
            background: '#1a1f2e', border: '1px solid #1f2937', borderRadius: '50%',
            width: 72, height: 72, display: 'flex', alignItems: 'center',
            justifyContent: 'center', margin: '0 auto 16px',
          }}>
            <TrendingDown size={30} color="#374151" />
          </div>
          <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 16, marginBottom: 6 }}>No near misses</div>
          <div style={{ color: '#4b5563', fontSize: 13 }}>Jobs just under threshold will appear here.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map(m => {
            const c = scoreColor(m.score);
            return (
              <div key={m.id} style={{
                background: '#111827', border: '1px solid #1f2937',
                borderRadius: 16, padding: 14,
              }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  alignItems: 'flex-start', gap: 8, marginBottom: 7,
                }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 14, marginBottom: 2 }}>
                      {m.job_title}
                    </div>
                    <div style={{ color: '#4b5563', fontSize: 12 }}>{m.company_name}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                    <div style={{ height: 5, width: 60, background: '#1f2937', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${m.score}%`, background: c, borderRadius: 3 }} />
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: c, minWidth: 20 }}>{m.score}</span>
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 6,
                      letterSpacing: '0.02em', background: '#431407', color: '#fb923c',
                    }}>Near miss</span>
                  </div>
                </div>
                <p style={{
                  color: '#4b5563', fontSize: 12, lineHeight: 1.55,
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical' as const,
                  overflow: 'hidden',
                } as React.CSSProperties}>
                  {m.reasoning}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
