const scoreColor = (s: number) =>
  s >= 85 ? '#22c55e' : s >= 70 ? '#eab308' : s >= 55 ? '#f97316' : '#ef4444';

export default function ScoreRing({ score, size = 60 }: { score: number; size?: number }) {
  const c = scoreColor(score);
  const r = size / 2 - 5;
  const circ = 2 * Math.PI * r;
  const dash = circ * (score / 100);

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1f2937" strokeWidth="4" />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={c} strokeWidth="4"
          strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ color: c, fontWeight: 800, fontSize: size * 0.28, lineHeight: 1 }}>
          {score}
        </span>
      </div>
    </div>
  );
}

export function scoreLabel(score: number) {
  if (score >= 85) return 'Strong match';
  if (score >= 70) return 'Good fit — minor gaps';
  if (score >= 55) return 'Moderate fit';
  return 'Below threshold';
}

export { scoreColor };
