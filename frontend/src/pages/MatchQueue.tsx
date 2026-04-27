import { useEffect, useState } from 'react';
import { CheckCircle2, Send, Zap, FileText, SortAsc } from 'lucide-react';
import { useMatches } from '../contexts/MatchesContext';
import MatchCard, { Avatar } from '../components/MatchCard';
import BottomSheet from '../components/BottomSheet';
import ConfirmApplied from '../components/ConfirmApplied';
import ScoreRing, { scoreColor, scoreLabel } from '../components/ScoreRing';
import { api } from '../api/client';
import type { MatchDetail } from '../types';

export default function MatchQueue() {
  const { matches, loading, error, refresh } = useMatches();
  const [selectedMatch, setSelectedMatch] = useState<MatchDetail | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [pendingApplyId, setPendingApplyId] = useState<number | null>(null);
  const [chosenVariantId, setChosenVariantId] = useState<number | null>(null);
  const [appliedIds, setAppliedIds] = useState<Set<number>>(new Set());
  const [didSubmitOpen, setDidSubmitOpen] = useState(false);
  const [sort, setSort] = useState<'score' | 'new'>('score');

  const sorted = [...matches].sort((a, b) =>
    sort === 'score' ? b.score - a.score : b.matched_at.localeCompare(a.matched_at)
  );

  // When user returns to the app after opening the ATS form, prompt "Did you submit?"
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible' && pendingApplyId !== null) {
        setDidSubmitOpen(true);
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [pendingApplyId]);

  const handleTap = async (matchId: number) => {
    try {
      const detail = await api.getMatch(matchId);
      setSelectedMatch(detail);
      setChosenVariantId(null);
      setSheetOpen(true);
    } catch { /* ignore */ }
  };

  const handleSkip = async (matchId: number) => {
    await api.skipMatch(matchId);
    refresh();
  };

  // Card Apply / swipe-right: open detail sheet so user sees what they're applying to
  // and so we have ats_url available for a synchronous window.open.
  const handleApply = (matchId: number) => {
    handleTap(matchId);
  };

  // Called from the detail sheet Apply button — ats_url is already known, open synchronously.
  const handleOpenApplication = () => {
    if (!selectedMatch) return;
    window.open(selectedMatch.ats_url || selectedMatch.job.url, '_blank');
    setPendingApplyId(selectedMatch.id);
    setSheetOpen(false);
  };

  // User confirmed they submitted the application.
  const handleDidSubmitYes = async () => {
    if (!pendingApplyId) return;
    await api.applyMatch(pendingApplyId, undefined, chosenVariantId ?? undefined);
    setAppliedIds(s => new Set([...s, pendingApplyId]));
    setPendingApplyId(null);
    setChosenVariantId(null);
    setDidSubmitOpen(false);
    refresh();
  };

  // User dismissed — match stays in queue for later.
  const handleDidSubmitNo = () => {
    setPendingApplyId(null);
    setDidSubmitOpen(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-dvh">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-dvh gap-3 px-8 text-center">
        <p className="text-red-400 text-sm">{error}</p>
        <button onClick={refresh} className="text-indigo-400 text-sm underline">Retry</button>
      </div>
    );
  }

  const isAmbiguous = (selectedMatch?.ambiguous_variants?.length ?? 0) > 1;

  return (
    <div style={{ paddingBottom: 96, paddingTop: 24, paddingInline: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 16 }}>
        <div>
          <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 700, letterSpacing: '-0.03em' }}>Matches</h1>
          <p style={{ color: '#4b5563', fontSize: 13, marginTop: 2 }}>
            <span style={{ color: '#6366f1', fontWeight: 600 }}>{sorted.length}</span> pending
          </p>
        </div>
        <button
          onClick={() => setSort(s => s === 'score' ? 'new' : 'score')}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            background: '#111827', border: '1px solid #1f2937', borderRadius: 10,
            padding: '7px 12px', cursor: 'pointer', color: '#6b7280',
            fontSize: 12, fontWeight: 500, fontFamily: 'inherit',
          }}
        >
          <SortAsc size={13} color="#6b7280" />
          {sort === 'score' ? 'Score' : 'Newest'}
        </button>
      </div>

      {/* Swipe hint */}
      {sorted.length > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: '#0a0f1a', border: '1px dashed #1f2937', borderRadius: 12,
          padding: '9px 14px', marginBottom: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#374151', fontSize: 12 }}>
            <Send size={13} color="rgba(34,197,94,0.3)" />
            <span style={{ color: 'rgba(34,197,94,0.4)' }}>Swipe right</span> to apply
          </div>
          <div style={{ color: '#1f2937', fontSize: 12 }}>·</div>
          <div style={{ color: '#374151', fontSize: 12 }}>
            Swipe left to skip
          </div>
        </div>
      )}

      {/* Empty state */}
      {sorted.length === 0 && (
        <div style={{ textAlign: 'center', padding: '64px 0' }}>
          <div style={{
            background: '#0d2e0d', border: '1px solid #14532d', borderRadius: '50%',
            width: 72, height: 72, display: 'flex', alignItems: 'center',
            justifyContent: 'center', margin: '0 auto 16px',
          }}>
            <CheckCircle2 size={32} color="#22c55e" />
          </div>
          <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 17, marginBottom: 6 }}>All caught up!</div>
          <div style={{ color: '#4b5563', fontSize: 13 }}>No pending matches to review.</div>
        </div>
      )}

      {/* Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {sorted.map(match => (
          <MatchCard
            key={match.id}
            match={match}
            onTap={handleTap}
            onSkip={handleSkip}
            onApply={handleApply}
          />
        ))}
      </div>

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
            <div style={{ marginBottom: 14 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                color: '#374151', fontSize: 11, fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8,
              }}>
                <Zap size={11} color="#6366f1" /> AI Reasoning
              </div>
              <p style={{ color: '#d1d5db', fontSize: 14, lineHeight: 1.7 }}>{selectedMatch.reasoning}</p>
            </div>

            {/* CV Recommendation */}
            {selectedMatch.cv_variant && !isAmbiguous && (
              <div style={{
                background: '#03152b', border: '1px solid #1e3a5f', borderRadius: 14,
                padding: 14, marginBottom: 16,
              }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  color: '#374151', fontSize: 11, fontWeight: 700,
                  textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8,
                }}>
                  <FileText size={11} color="#3b82f6" /> CV Recommendation
                </div>
                <p style={{ color: '#93c5fd', fontSize: 13, lineHeight: 1.65 }}>
                  Use <strong style={{ color: '#bfdbfe' }}>{selectedMatch.cv_variant.name}</strong> for this application.
                </p>
              </div>
            )}

            {/* CV ambiguity picker */}
            {isAmbiguous && !chosenVariantId && (
              <div style={{
                background: '#1a1200', border: '1px solid #78350f', borderRadius: 14,
                padding: 14, marginBottom: 16,
              }}>
                <p style={{ color: '#fbbf24', fontSize: 13, fontWeight: 600, marginBottom: 12 }}>
                  Two CVs are equally strong — pick one:
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {selectedMatch.ambiguous_variants.map(v => (
                    <button
                      key={v.id}
                      onClick={() => setChosenVariantId(v.id)}
                      style={{
                        textAlign: 'left', padding: '10px 14px', borderRadius: 10,
                        background: '#111827', border: '1px solid #374151', cursor: 'pointer',
                        fontFamily: 'inherit',
                      }}
                    >
                      <span style={{ color: '#f9fafb', fontSize: 14, fontWeight: 600 }}>{v.name}</span>
                      <span style={{ marginLeft: 8, color: '#6b7280', fontSize: 12 }}>
                        {JSON.parse(v.focus_tags || '[]').join(', ')}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Apply / Applied */}
            {appliedIds.has(selectedMatch.id) ? (
              <div style={{
                background: '#031a0e', border: '1px solid #14532d', borderRadius: 12,
                padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 10,
              }}>
                <CheckCircle2 size={18} color="#22c55e" />
                <div>
                  <div style={{ color: '#22c55e', fontWeight: 600, fontSize: 14 }}>Application tracked</div>
                  <div style={{ color: '#14532d', fontSize: 12, marginTop: 1 }}>Added to your tracker</div>
                </div>
              </div>
            ) : (
              <button
                style={{
                  width: '100%', height: 52, background: '#6366f1', color: '#fff',
                  border: 'none', borderRadius: 14, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  gap: 8, fontSize: 15, fontWeight: 600, fontFamily: 'inherit',
                }}
                onClick={handleOpenApplication}
              >
                <Send size={15} color="#fff" /> Apply Now
              </button>
            )}
          </div>
        )}
      </BottomSheet>

      <ConfirmApplied
        isOpen={didSubmitOpen}
        jobTitle={matches.find(m => m.id === pendingApplyId)?.job_title || ''}
        onConfirm={handleDidSubmitYes}
        onCancel={handleDidSubmitNo}
      />
    </div>
  );
}
