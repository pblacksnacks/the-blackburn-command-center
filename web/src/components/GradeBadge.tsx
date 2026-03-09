const colors: Record<string, string> = {
  A: 'bg-emerald-500 text-white shadow-emerald-500/25',
  B: 'bg-amber-500 text-white shadow-amber-500/25',
  C: 'bg-red-400 text-white shadow-red-400/25',
  D: 'bg-red-600 text-white shadow-red-600/25',
};

export default function GradeBadge({ grade, size = 'sm' }: { grade: string; size?: 'sm' | 'lg' }) {
  const cls = colors[grade] || 'bg-slate-400 text-white';
  const sz = size === 'lg' ? 'text-lg px-3.5 py-1 shadow-md' : 'text-xs px-2 py-0.5 shadow-sm';
  return (
    <span className={`inline-flex items-center justify-center font-bold rounded-md ${cls} ${sz}`}>
      {grade}
    </span>
  );
}
