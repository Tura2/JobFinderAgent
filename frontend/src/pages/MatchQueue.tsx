import { useState } from "react";
import { useMatches } from "../hooks/useMatches";
import MatchCard from "../components/MatchCard";
import BottomSheet from "../components/BottomSheet";
import ConfirmApplied from "../components/ConfirmApplied";
import { api } from "../api/client";
import type { MatchDetail } from "../types";

export default function MatchQueue() {
  const { matches, loading, error, refresh } = useMatches();
  const [selectedMatch, setSelectedMatch] = useState<MatchDetail | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [applyingId, setApplyingId] = useState<number | null>(null);
  const [chosenVariantId, setChosenVariantId] = useState<number | null>(null);

  const handleTap = async (matchId: number) => {
    try {
      const detail = await api.getMatch(matchId);
      setSelectedMatch(detail);
      setChosenVariantId(null);
      setSheetOpen(true);
    } catch {
      // ignore
    }
  };

  const handleSkip = async (matchId: number) => {
    await api.skipMatch(matchId);
    refresh();
  };

  const handleApply = (matchId: number) => {
    setApplyingId(matchId);
    setConfirmOpen(true);
  };

  const handleConfirm = async () => {
    if (applyingId) {
      await api.applyMatch(applyingId, undefined, chosenVariantId ?? undefined);
      setConfirmOpen(false);
      setApplyingId(null);
      setChosenVariantId(null);
      refresh();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-400">
        <p>{error}</p>
        <button onClick={refresh} className="mt-2 text-blue-400 underline">
          Retry
        </button>
      </div>
    );
  }

  const applyingMatch = selectedMatch;
  const isAmbiguous = (applyingMatch?.ambiguous_variants?.length ?? 0) > 1;
  const canApply = !isAmbiguous || chosenVariantId !== null;

  return (
    <div className="pb-20 pt-4 px-4">
      <h1 className="text-xl font-bold mb-4">
        New Matches <span className="text-gray-500 text-base">({matches.length})</span>
      </h1>

      {matches.length === 0 ? (
        <div className="text-center text-gray-500 mt-12">
          <p className="text-4xl mb-2">🎯</p>
          <p>No pending matches.</p>
          <p className="text-sm">Check back after the next scan.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {matches.map((match) => (
            <MatchCard
              key={match.id}
              match={match}
              onTap={handleTap}
              onSkip={handleSkip}
              onApply={handleApply}
            />
          ))}
        </div>
      )}

      <BottomSheet isOpen={sheetOpen} onClose={() => setSheetOpen(false)}>
        {selectedMatch && (
          <div>
            <h2 className="text-lg font-bold">{selectedMatch.job.title}</h2>
            <p className="text-sm text-gray-400 mb-2">
              {selectedMatch.company.name} · {selectedMatch.job.location}
            </p>
            <p className="text-sm text-gray-300 mb-4">{selectedMatch.reasoning}</p>

            {isAmbiguous && !chosenVariantId && (
              <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-xl p-4 mb-4">
                <p className="text-sm text-yellow-300 font-medium mb-3">
                  Two CVs are equally good — pick one:
                </p>
                <div className="space-y-2">
                  {selectedMatch.ambiguous_variants.map((v) => (
                    <button
                      key={v.id}
                      onClick={() => setChosenVariantId(v.id)}
                      className="w-full text-left px-4 py-3 rounded-lg bg-gray-800 border border-gray-700 text-sm hover:border-yellow-600"
                    >
                      <span className="font-medium text-white">{v.name}</span>
                      <span className="ml-2 text-gray-400">
                        {JSON.parse(v.focus_tags || "[]").join(", ")}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {selectedMatch.cv_variant && (
              <p className="text-xs text-gray-500 mb-4">CV: {selectedMatch.cv_variant.name}</p>
            )}

            <div
              className="prose prose-invert prose-sm max-w-none"
              dangerouslySetInnerHTML={{
                __html: selectedMatch.job.description_raw || "No description available.",
              }}
            />
          </div>
        )}
      </BottomSheet>

      <ConfirmApplied
        isOpen={confirmOpen}
        jobTitle={matches.find((m) => m.id === applyingId)?.job_title || ""}
        onConfirm={handleConfirm}
        onCancel={() => {
          setConfirmOpen(false);
          setApplyingId(null);
        }}
      />
    </div>
  );
}
