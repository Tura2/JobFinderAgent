import { BrowserRouter, Routes, Route, Navigate, NavLink } from "react-router-dom";
import MatchQueue from "./pages/MatchQueue";
import Tracker from "./pages/Tracker";
import ApplicationDetail from "./pages/ApplicationDetail";
import Companies from "./pages/Companies";
import Settings from "./pages/Settings";
import NearMisses from "./pages/NearMisses";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `text-xs text-center flex flex-col items-center gap-0.5 ${isActive ? "text-white" : "text-gray-500"}`;

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
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

        <nav className="fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-800 flex justify-around py-3 px-4">
          <NavLink to="/matches" className={navClass}>
            <span className="text-lg">📋</span>
            <span>Matches</span>
          </NavLink>
          <NavLink to="/near-misses" className={navClass}>
            <span className="text-lg">📉</span>
            <span>Near Misses</span>
          </NavLink>
          <NavLink to="/tracker" className={navClass}>
            <span className="text-lg">📊</span>
            <span>Tracker</span>
          </NavLink>
          <NavLink to="/companies" className={navClass}>
            <span className="text-lg">🏢</span>
            <span>Companies</span>
          </NavLink>
          <NavLink to="/settings" className={navClass}>
            <span className="text-lg">⚙️</span>
            <span>Settings</span>
          </NavLink>
        </nav>
      </div>
    </BrowserRouter>
  );
}
