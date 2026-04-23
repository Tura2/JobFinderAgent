import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { MatchListItem } from '../types';

interface MatchesCtx {
  matches: MatchListItem[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

const Ctx = createContext<MatchesCtx>({
  matches: [], loading: true, error: null, refresh: () => {},
});

export function MatchesProvider({ children }: { children: React.ReactNode }) {
  const [matches, setMatches] = useState<MatchListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    api.getMatches()
      .then(setMatches)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load matches'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return <Ctx.Provider value={{ matches, loading, error, refresh }}>{children}</Ctx.Provider>;
}

export const useMatches = () => useContext(Ctx);
