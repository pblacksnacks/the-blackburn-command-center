const colors: Record<string, string> = {
  A: 'bg-green-100 text-green-800 border-green-300',
  B: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  C: 'bg-orange-100 text-orange-800 border-orange-300',
  D: 'bg-red-100 text-red-800 border-red-300',
};

export default function GradeBadge({ grade, size = 'sm' }: { grade: string; size?: 'sm' | 'lg' }) {
  const cls = colors[grade] || 'bg-gray-100 text-gray-800 border-gray-300';
  const sz = size === 'lg' ? 'text-xl px-3 py-1' : 'text-xs px-2 py-0.5';
  return (
    <span className={`inline-flex items-center font-bold rounded border ${cls} ${sz}`}>
      {grade}
    </span>
  );
}
