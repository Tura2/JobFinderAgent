import { useRef, useState } from 'react';
import { SkipForward, Send, ChevronRight } from 'lucide-react';
import ScoreRing from './ScoreRing';
import type { MatchListItem } from '../types';

const AVATAR_PALETTE = [
  '#7c3aed', '#16a34a', '#0ea5e9', '#dc2626', '#d97706',
  '#059669', '#db2777', '#2563eb', '#0284c7', '#9333ea',
];

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const ini = name.split(' ').slice(0, 2).map(w => w[0] ?? '').join('').toUpperCase();
  const idx = name.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR_PALETTE.length;
  const color = AVATAR_PALETTE[idx];
  return (
    <div style={{
      width: size, height: size, borderRadius: size * 0.25,
      background: color + '1a', border: `1.5px solid ${color}33`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0, color, fontWeight: 700, fontSize: size * 0.34,
    }}>
      {ini}
    </div>
  );
}

const THRESHOLD = 88;

interface Props {
  match: MatchListItem;
  onTap: (id: number) => void;
  onSkip: (id: number) => void;
  onApply: (id: number) => void;
}

export default function MatchCard({ match, onTap, onSkip, onApply }: Props) {
  const [dx, setDx] = useState(0);
  const active = useRef(false);
  const startX = useRef(0);

  const begin = (x: number) => { active.current = true; startX.current = x; };
  const drag = (x: number) => {
    if (!active.current) return;
    setDx(Math.max(-140, Math.min(140, x - startX.current)));
  };
  const release = () => {
    if (!active.current) return;
    active.current = false;
    if (dx > THRESHOLD) onApply(match.id);
    else if (dx < -THRESHOLD) onSkip(match.id);
    setDx(0);
  };

  const prog = Math.min(Math.abs(dx) / THRESHOLD, 1);
  const right = dx > 0;

  return (
    <div
      style={{ position: 'relative', userSelect: 'none', touchAction: 'pan-y' }}
      onTouchStart={e => begin(e.touches[0].clientX)}
      onTouchMove={e => { if (active.current) drag(e.touches[0].clientX); }}
      onTouchEnd={release}
      onMouseDown={e => begin(e.clientX)}
      onMouseMove={e => { if (active.current) drag(e.clientX); }}
      onMouseUp={release}
      onMouseLeave={release}
    >
      {dx !== 0 && (
        <div style={{
          position: 'absolute', inset: 0, borderRadius: 16,
          background: right
            ? `rgba(34,197,94,${prog * 0.22})`
            : `rgba(239,68,68,${prog * 0.18})`,
          display: 'flex', alignItems: 'center',
          justifyContent: right ? 'flex-start' : 'flex-end',
          padding: '0 22px',
        }}>
          {right
            ? <Send size={28} color={`rgba(34,197,94,${prog})`} />
            : <SkipForward size={28} color={`rgba(239,68,68,${prog})`} />
          }
        </div>
      )}

      <div style={{
        transform: `translateX(${dx}px) rotate(${dx * 0.012}deg)`,
        transition: active.current ? 'none' : 'transform 0.3s cubic-bezier(0.4,0,0.2,1)',
        willChange: 'transform',
      }}>
        <div
          style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 16, padding: 14, cursor: 'pointer' }}
          onClick={() => { if (Math.abs(dx) < 4) onTap(match.id); }}
          role="button"
          tabIndex={0}
          onKeyDown={e => e.key === 'Enter' && onTap(match.id)}
          data-testid="match-card"
        >
          <div style={{ display: 'flex', gap: 14, alignItems: 'center', marginBottom: 10 }}>
            <ScoreRing score={match.score} size={62} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: '#f9fafb', fontWeight: 700, fontSize: 15, lineHeight: 1.3, marginBottom: 3 }}>
                {match.job_title}
              </div>
              <div style={{ color: '#6b7280', fontSize: 12 }}>
                {match.company_name}
              </div>
              {match.status === 'new' && (
                <span style={{
                  display: 'inline-block', marginTop: 6,
                  fontSize: 10, fontWeight: 700, padding: '2px 7px',
                  borderRadius: 6, letterSpacing: '0.02em',
                  background: '#1e1b4b', color: '#818cf8',
                }}>New</span>
              )}
            </div>
            <ChevronRight size={15} color="#374151" />
          </div>

          <p style={{
            color: '#6b7280', fontSize: 12, lineHeight: 1.55, marginBottom: 10,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical' as const,
            overflow: 'hidden',
          } as React.CSSProperties}>
            {match.reasoning}
          </p>

          <div style={{ display: 'flex', gap: 8 }} onClick={e => e.stopPropagation()}>
            <button
              style={{
                flex: 1, height: 40, background: '#1f2937', color: '#6b7280',
                border: 'none', borderRadius: 12, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                gap: 6, fontSize: 14, fontWeight: 600, fontFamily: 'inherit',
              }}
              onClick={() => onSkip(match.id)}
              aria-label="Skip"
            >
              <SkipForward size={13} color="#6b7280" /> Skip
            </button>
            <button
              style={{
                flex: 1, height: 40, background: '#6366f1', color: '#fff',
                border: 'none', borderRadius: 12, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                gap: 6, fontSize: 14, fontWeight: 600, fontFamily: 'inherit',
              }}
              onClick={() => onApply(match.id)}
              aria-label="Apply"
            >
              <Send size={13} color="#fff" /> Apply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
