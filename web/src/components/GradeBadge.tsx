const colors: Record<string, string> = {
  A: 'text-white shadow-green-400/25',
  B: 'text-white shadow-amber-400/25',
  C: 'text-white shadow-red-400/25',
  D: 'text-white shadow-red-600/25',
};

const bgColors: Record<string, string> = {
  A: '#4ade80',
  B: '#fbbf24',
  C: '#f87171',
  D: '#dc2626',
};

export default function GradeBadge({ grade, size = 'sm' }: { grade: string; size?: 'sm' | 'lg' }) {
  const cls = colors[grade] || 'text-white';
  const bg = bgColors[grade] || '#64748b';
  const sz = size === 'lg' ? 'text-lg px-3.5 py-1 shadow-md' : 'text-xs px-2 py-0.5 shadow-sm';
  return (
    <span
      className={`inline-flex items-center justify-center font-bold rounded-md ${cls} ${sz}`}
      style={{ background: bg }}
    >
      {grade}
    </span>
  );
}
