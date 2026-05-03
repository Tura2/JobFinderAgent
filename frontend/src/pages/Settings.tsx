import { useState, useEffect, useRef } from 'react';
import { Play, RefreshCw, CheckCircle2, LogOut } from 'lucide-react';
import { api } from '../api/client';
import type { ScanStatus } from '../types';

function formatTime(iso: string | null) {
  if (!iso) return 'Never';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

const THRESHOLDS = [
  { label: 'Strong match', value: '≥ 85', color: '#22c55e' },
  { label: 'Good fit',     value: '≥ 70', color: '#eab308' },
  { label: 'Moderate',     value: '≥ 55', color: '#f97316' },
  { label: 'Near miss',    value: '< 55', color: '#ef4444' },
];

export default function Settings() {
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [linkedinUrl, setLinkedinUrl] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [prog, setProg] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const progRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = async () => {
    const s = await api.getScanStatus();
    setScanStatus(s);
    return s;
  };

  useEffect(() => {
    fetchStatus().then(s => {
      if (s.is_running) {
        setScanning(true);
        startProgress();
        startPolling();
      }
    });
  }, []);

  useEffect(() => {
    api.getConfig().then(c => setLinkedinUrl(c.linkedin_url)).catch(() => {});
  }, []);

  const startProgress = () => {
    setProg(0);
    let p = 0;
    progRef.current = setInterval(() => {
      p += Math.random() * 8 + 2;
      if (p >= 92) { p = 92; clearInterval(progRef.current!); }
      setProg(Math.min(p, 92));
    }, 300);
  };

  const stopProgress = () => {
    if (progRef.current) { clearInterval(progRef.current); progRef.current = null; }
    setProg(100);
    setTimeout(() => setProg(0), 3000);
  };

  const startPolling = () => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      const s = await fetchStatus();
      if (!s.is_running) {
        clearInterval(pollRef.current!);
        pollRef.current = null;
        setScanning(false);
        stopProgress();
      }
    }, 5000);
  };

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (progRef.current) clearInterval(progRef.current);
  }, []);

  const handleScan = async () => {
    if (scanning) return;
    setScanning(true);
    startProgress();
    try {
      await api.triggerScan();
      startPolling();
    } catch {
      setScanning(false);
      setProg(0);
    }
  };

  const handleLogout = () => {
    fetch('/auth/logout', { method: 'POST', credentials: 'include' })
      .finally(() => { window.location.href = '/login'; });
  };

  const isRunning = scanning || scanStatus?.is_running;
  const scanDone = prog === 100;

  return (
    <div style={{ paddingBottom: 96, paddingTop: 24, paddingInline: 16 }}>
      <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 18 }}>
        Settings
      </h1>

      {/* Scanner card */}
      <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 16, padding: 16, marginBottom: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <span style={{ color: '#f9fafb', fontWeight: 600, fontSize: 15 }}>Scanner</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: isRunning ? '#eab308' : '#22c55e',
              boxShadow: `0 0 8px ${isRunning ? '#eab30866' : '#22c55e55'}`,
              animation: isRunning ? 'pulse 1s ease infinite' : undefined,
            }} />
            <span style={{ color: isRunning ? '#eab308' : '#22c55e', fontSize: 12, fontWeight: 600 }}>
              {isRunning ? 'Scanning' : 'Idle'}
            </span>
          </div>
        </div>

        {scanStatus && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 14 }}>
            {[
              ['LAST SCAN', formatTime(scanStatus.last_scan_at)],
              ['NEW JOBS FOUND', String(scanStatus.last_scan_new_jobs)],
            ].map(([label, value]) => (
              <div key={label} style={{
                background: '#0a0f1a', border: '1px solid #1f2937',
                borderRadius: 10, padding: '10px 12px',
              }}>
                <div style={{ color: '#374151', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
                  {label}
                </div>
                <div style={{ color: '#f9fafb', fontWeight: 700, fontSize: 18 }}>{value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Progress bar */}
        {(isRunning || scanDone) && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ height: 3, background: '#1f2937', borderRadius: 2, overflow: 'hidden', marginBottom: 6 }}>
              <div style={{
                height: '100%', width: `${prog}%`,
                background: scanDone ? '#22c55e' : '#6366f1',
                borderRadius: 2, transition: 'width 0.3s ease',
              }} />
            </div>
            <div style={{ color: '#374151', fontSize: 11 }}>
              {scanDone ? 'Scan complete' : `Scanning job boards… ${Math.round(prog)}%`}
            </div>
          </div>
        )}

        <button
          onClick={handleScan}
          disabled={!!isRunning}
          style={{
            width: '100%', height: 50, fontSize: 15, borderRadius: 12,
            border: 'none', cursor: isRunning ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 8, fontWeight: 600, fontFamily: 'inherit',
            background: scanDone ? '#166534' : isRunning ? '#3730a3' : '#6366f1',
            color: '#fff', opacity: isRunning ? 0.9 : 1,
          }}
        >
          {isRunning && <><RefreshCw size={16} className="animate-spin" /> Scanning…</>}
          {!isRunning && scanDone && <><CheckCircle2 size={16} /> Scan complete!</>}
          {!isRunning && !scanDone && <><Play size={16} fill="currentColor" /> Scan Now</>}
        </button>
      </div>

      {/* Score thresholds */}
      <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 16, padding: 16, marginBottom: 10 }}>
        <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 15, marginBottom: 12 }}>Score Thresholds</div>
        {THRESHOLDS.map(({ label, value, color }, i) => (
          <div key={label} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '9px 0',
            borderBottom: i < THRESHOLDS.length - 1 ? '1px solid #111827' : 'none',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
              <span style={{ color: '#9ca3af', fontSize: 13 }}>{label}</span>
            </div>
            <span style={{ color, fontSize: 13, fontWeight: 700 }}>{value}</span>
          </div>
        ))}
      </div>

      {/* Account */}
      <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 16, padding: 16, marginBottom: 10 }}>
        <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 15, marginBottom: 12 }}>Account</div>
        <button
          onClick={handleLogout}
          style={{
            width: '100%', height: 46, fontSize: 14, borderRadius: 12,
            border: '1px solid #374151', background: 'transparent',
            color: '#9ca3af', cursor: 'pointer', display: 'flex',
            alignItems: 'center', justifyContent: 'center', gap: 8,
            fontWeight: 600, fontFamily: 'inherit',
          }}
        >
          <LogOut size={15} />
          Log out
        </button>
      </div>

      {/* About */}
      <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 16, padding: 16 }}>
        <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 14, marginBottom: 6 }}>JobFinder Agent v0.1.0</div>
        <div style={{ color: '#4b5563', fontSize: 13, marginBottom: linkedinUrl ? 12 : 0 }}>
          Autonomous job hunting pipeline
        </div>
        {linkedinUrl && (
          <a
            href={linkedinUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#6366f1', fontSize: 12, fontWeight: 600, textDecoration: 'none' }}
          >
            Developed by Offir Tura
          </a>
        )}
      </div>

      <style>{`
        @keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:.4 } }
      `}</style>
    </div>
  );
}
