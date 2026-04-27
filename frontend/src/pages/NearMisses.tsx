import { useEffect, useRef, useState } from 'react';
import { TrendingDown, ArrowUpCircle, X, Zap } from 'lucide-react';
import { api } from '../api/client';
import BottomSheet from '../components/BottomSheet';
import ScoreRing, { scoreColor, scoreLabel } from '../components/ScoreRing';
import { Avatar } from '../components/MatchCard';
import type { MatchListItem, MatchDetail } from '../types';

// --- Swipe thresholds ---
const SWIPE_THRESHOLD = 88;

interface CardProps {
  match: MatchListItem;
  onTap: (id: number) => void;
  onDismiss: (id: number) => void;
  onPromote: (id: number) => void;
}

function NearMissCard({ match, onTap, onDismiss, onPromote }: CardProps) {
  const [dx, setDx] = useState(0);
  const active = useRef(false);
  const startX = useRef(0);

  const scoreC = match.score >= 85 ? '#22c55e' : match.score >= 70 ? '#eab308' : match.score >= 55 ? '#f97316' : '#ef4444';

  const begin = (x: number) => { active.current = true; startX.current = x; };
  const drag = (x: number) => {
    if (!active.current) return;
    setDx(Math.max(-140, Math.min(140, x - startX.current)));
  };
  const release = () => {
    if (!active.current) return;
    active.current = false;
    if (dx > SWIPE_THRESHOLD) onPromote(match.id);
    else if (dx < -SWIPE_THRESHOLD) onDismiss(match.id);
    setDx(0);
  };

  const prog = Math.min(Math.abs(dx) / SWIPE_THRESHOLD, 1);
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
      {/* Swipe hint background */}
      {dx !== 0 && (
        <div style={{
          position: 'absolute', inset: 0, borderRadius: 16,
          background: right
            ? `rgba(99,102,241,${prog * 0.22})`
            : `rgba(239,68,68,${prog * 0.18})`,
          display: 'flex', alignItems: 'center',
          justifyContent: right ? 'flex-start' : 'flex-end',
          padding: '0 22px',
        }}>
          {right
            ? <ArrowUpCircle size={28} color={`rgba(99,102,241,${prog})`} />
            : <X size={28} color={`rgba(239,68,68,${prog})`} />
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
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 7 }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 14, marginBottom: 2 }}>{match.job_title}</div>
              <div style={{ color: '#4b5563', fontSize: 12 }}>{match.company_name}</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
              <div style={{ height: 5, width: 60, background: '#1f2937', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${match.score}%`, background: scoreC, borderRadius: 3 }} />
              </div>
              <span style={{ fontSize: 12, fontWeight: 700, color: scoreC, minWidth: 20 }}>{match.score}</span>
              <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 6, letterSpacing: '0.02em', background: '#431407', color: '#fb923c' }}>
                Near miss
              </span>
            </div>
          </div>
          <p style={{
            color: '#4b5563', fontSize: 12, lineHeight: 1.55,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical' as const,
            overflow: 'hidden',
          } as React.CSSProperties}>
            {match.reasoning}
          </p>
        </div>
      </div>
    </div>
  );
}

// --- Main page ---

export default function NearMisses() {
  const [items, setItems] = useState<MatchListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState(30);
  const [selectedMatch, setSelectedMatch] = useState<MatchDetail | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [promoting, setPromoting] = useState(false);

  const reload = (score = minScore) => {
    setLoading(true);
    api.getNearMisses(score).then(setItems).finally(() => setLoading(false));
  };

  useEffect(() => { reload(); }, [minScore]);

  const handleTap = async (id: number) => {
    try {
      const detail = await api.getMatch(id);
      setSelectedMatch(detail);
      setSheetOpen(true);
    } catch { /* ignore */ }
  };

  const handleDismiss = async (id: number) => {
    await api.skipMatch(id);
    setItems(prev => prev.filter(m => m.id !== id));
  };

  const handlePromote = async (id: number) => {
    await api.promoteMatch(id);
    setItems(prev => prev.filter(m => m.id !== id));
  };

  const handlePromoteFromSheet = async () => {
    if (!selectedMatch) return;
    setPromoting(true);
    try {
      await api.promoteMatch(selectedMatch.id);
      setItems(prev => prev.filter(m => m.id !== selectedMatch.id));
      setSheetOpen(false);
    } finally {
      setPromoting(false);
    }
  };

  const handleDismissFromSheet = async () => {
    if (!selectedMatch) return;
    await api.skipMatch(selectedMatch.id);
    setItems(prev => prev.filter(m => m.id !== selectedMatch.id));
    setSheetOpen(false);
  };

  return (
    <div style={{ paddingBottom: 96, paddingTop: 24, paddingInline: 16 }}>
      <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 700, letterSpacing: '-0.03em' }}>Near Misses</h1>
      <p style={{ color: '#4b5563', fontSize: 13, marginTop: 2, marginBottom: 12 }}>
        Below threshold — review manually if interested
      </p>

      {/* Score filter slider */}
      <div style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ color: '#6b7280', fontSize: 12, whiteSpace: 'nowrap' }}>Min score</span>
        <input
          type="range" min={0} max={64} step={5} value={minScore}
          onChange={e => setMinScore(Number(e.target.value))}
          style={{ flex: 1, accentColor: '#6366f1' }}
        />
        <span style={{ color: '#e5e7eb', fontSize: 13, fontWeight: 700, minWidth: 24, textAlign: 'right' }}>{minScore}</span>
      </div>

      {/* Swipe hint */}
      {!loading && items.length > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: '#0a0f1a', border: '1px dashed #1f2937', borderRadius: 12,
          padding: '9px 14px', marginBottom: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
            <ArrowUpCircle size={13} color="rgba(99,102,241,0.5)" />
            <span style={{ color: 'rgba(99,102,241,0.6)' }}>Swipe right</span>
            <span style={{ color: '#374151' }}>to promote</span>
          </div>
          <div style={{ color: '#1f2937' }}>·</div>
          <div style={{ color: '#374151', fontSize: 12 }}>Swipe left to dismiss</div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center" style={{ height: 120 }}>
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
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
          {items.map(m => (
            <NearMissCard
              key={m.id}
              match={m}
              onTap={handleTap}
              onDismiss={handleDismiss}
              onPromote={handlePromote}
            />
          ))}
        </div>
      )}

      {/* Detail sheet */}
      <BottomSheet isOpen={sheetOpen} onClose={() => setSheetOpen(false)}>
        {selectedMatch && (
          <div style={{ paddingBottom: 16 }}>
            {/* Title row */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 18 }}>
              <Avatar name={selectedMatch.company.name} size={50} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: '#f9fafb', fontWeight: 700, fontSize: 17, lineHeight: 1.3, marginBottom: 2 }}>
                  {selectedMatch.job.title}
                </div>
                <div style={{ color: '#6b7280', fontSize: 13, marginBottom: 2 }}>{selectedMatch.company.name}</div>
                {selectedMatch.job.location && (
                  <div style={{ color: '#374151', fontSize: 12 }}>{selectedMatch.job.location}</div>
                )}
              </div>
            </div>

            {/* Score block */}
            <div style={{
              background: '#0a0f1a', border: '1px solid #1f2937', borderRadius: 14,
              padding: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 16,
            }}>
              <ScoreRing score={selectedMatch.score} size={80} />
              <div>
                <div style={{ color: '#4b5563', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 5 }}>
                  Match Score
                </div>
                <div style={{ color: '#f9fafb', fontWeight: 800, fontSize: 28, lineHeight: 1, marginBottom: 4, letterSpacing: '-0.02em' }}>
                  {selectedMatch.score}<span style={{ color: '#1f2937', fontSize: 14, fontWeight: 400 }}>/100</span>
                </div>
                <div style={{ color: scoreColor(selectedMatch.score), fontSize: 12, fontWeight: 600 }}>
                  {scoreLabel(selectedMatch.score)}
                </div>
              </div>
            </div>

            {/* AI Reasoning */}
            <div style={{ marginBottom: 20 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                color: '#374151', fontSize: 11, fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8,
              }}>
                <Zap size={11} color="#6366f1" /> AI Reasoning
              </div>
              <p style={{ color: '#d1d5db', fontSize: 14, lineHeight: 1.7 }}>{selectedMatch.reasoning}</p>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <button
                disabled={promoting}
                style={{
                  width: '100%', height: 52, background: promoting ? '#3730a3' : '#6366f1', color: '#fff',
                  border: 'none', borderRadius: 14, cursor: promoting ? 'default' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  gap: 8, fontSize: 15, fontWeight: 600, fontFamily: 'inherit',
                  opacity: promoting ? 0.7 : 1,
                }}
                onClick={handlePromoteFromSheet}
              >
                <ArrowUpCircle size={16} color="#fff" />
                {promoting ? 'Promoting…' : 'Promote to Match Queue'}
              </button>
              <button
                style={{
                  width: '100%', height: 44, background: 'transparent', color: '#6b7280',
                  border: '1px solid #1f2937', borderRadius: 14, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  gap: 8, fontSize: 14, fontWeight: 500, fontFamily: 'inherit',
                }}
                onClick={handleDismissFromSheet}
              >
                <X size={14} color="#6b7280" /> Dismiss
              </button>
            </div>
          </div>
        )}
      </BottomSheet>
    </div>
  );
}
