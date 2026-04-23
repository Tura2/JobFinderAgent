import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { Inbox, TrendingDown, BarChart2, Building2, Settings as SettingsIcon } from 'lucide-react';
import { MatchesProvider, useMatches } from './contexts/MatchesContext';
import MatchQueue from './pages/MatchQueue';
import Tracker from './pages/Tracker';
import ApplicationDetail from './pages/ApplicationDetail';
import Companies from './pages/Companies';
import Settings from './pages/Settings';
import NearMisses from './pages/NearMisses';

function NavBadge({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span style={{
      position: 'absolute', top: -2, right: 'calc(50% - 18px)',
      background: '#ef4444', color: '#fff', fontSize: 9, fontWeight: 800,
      minWidth: 16, height: 16, borderRadius: 8,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '0 3px', border: '2px solid #0d1117',
    }}>
      {count > 99 ? '99+' : count}
    </span>
  );
}

function AppNav() {
  const { matches } = useMatches();
  const pending = matches.length;

  const navStyle = ({ isActive }: { isActive: boolean }) =>
    `flex flex-col items-center gap-1 px-3 py-1 rounded-xl transition-colors relative ${
      isActive ? 'text-indigo-400' : 'text-gray-600 hover:text-gray-400'
    }`;

  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: 0, right: 0,
      background: '#0d1117', borderTop: '1px solid #1f2937',
      display: 'flex', justifyContent: 'space-around',
      paddingTop: 8, paddingBottom: 'max(8px, env(safe-area-inset-bottom, 8px))',
      zIndex: 40,
    }}>
      <NavLink to="/matches" className={navStyle}>
        <span style={{ position: 'relative' }}>
          <Inbox size={22} strokeWidth={1.75} />
          <NavBadge count={pending} />
        </span>
        <span className="text-[10px] font-medium">Matches</span>
      </NavLink>
      <NavLink to="/near-misses" className={navStyle}>
        <TrendingDown size={22} strokeWidth={1.75} />
        <span className="text-[10px] font-medium">Near Misses</span>
      </NavLink>
      <NavLink to="/tracker" className={navStyle}>
        <BarChart2 size={22} strokeWidth={1.75} />
        <span className="text-[10px] font-medium">Tracker</span>
      </NavLink>
      <NavLink to="/companies" className={navStyle}>
        <Building2 size={22} strokeWidth={1.75} />
        <span className="text-[10px] font-medium">Companies</span>
      </NavLink>
      <NavLink to="/settings" className={navStyle}>
        <SettingsIcon size={22} strokeWidth={1.75} />
        <span className="text-[10px] font-medium">Settings</span>
      </NavLink>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <MatchesProvider>
        <div style={{ minHeight: '100dvh', background: '#030712', color: '#f9fafb' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/matches" replace />} />
            <Route path="/matches" element={<MatchQueue />} />
            <Route path="/matches/:id" element={<MatchQueue />} />
            <Route path="/near-misses" element={<NearMisses />} />
            <Route path="/tracker" element={<Tracker />} />
            <Route path="/tracker/:id" element={<ApplicationDetail />} />
            <Route path="/companies" element={<Companies />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
          <AppNav />
        </div>
      </MatchesProvider>
    </BrowserRouter>
  );
}
