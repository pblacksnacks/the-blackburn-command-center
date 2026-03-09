import { useState, useEffect } from 'react';
import { FileText, Download } from 'lucide-react';
import { fetchBriefings, fetchBriefing, type Briefing } from '../api';

export default function BriefingsPage({ refreshKey }: { refreshKey: number }) {
  const [briefings, setBriefings] = useState<Briefing[]>([]);
  const [selected, setSelected] = useState<Briefing | null>(null);

  useEffect(() => {
    fetchBriefings().then(setBriefings).catch(console.error);
  }, [refreshKey]);

  const loadDetail = async (date: string) => {
    const b = await fetchBriefing(date);
    setSelected(b);
  };

  return (
    <div>
      <h1 className="text-xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Daily Briefings</h1>
      <div className="grid grid-cols-3 gap-4">
        {/* List */}
        <div className="space-y-2">
          {briefings.length === 0 && (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No briefings yet. Run the pipeline first.</p>
          )}
          {briefings.map((b, idx) => (
            <button
              key={b.briefing_date}
              onClick={() => loadDetail(b.briefing_date)}
              className={`w-full text-left rounded-lg border p-3 text-sm transition-colors animate-fade-in-up stagger-${Math.min(idx + 1, 9)}`}
              style={
                selected?.briefing_date === b.briefing_date
                  ? { borderColor: 'rgba(212, 165, 116, 0.3)', background: 'rgba(212, 165, 116, 0.08)' }
                  : { borderColor: 'var(--border)', background: 'var(--bg-card)' }
              }
            >
              <div className="flex items-center gap-2 font-medium" style={{ color: 'var(--text-primary)' }}>
                <FileText className="h-4 w-4" style={{ color: 'var(--text-muted)' }} />
                {b.briefing_date}
              </div>
              <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                Created {new Date(b.created_at).toLocaleString()}
              </div>
            </button>
          ))}
        </div>

        {/* Detail */}
        <div className="col-span-2">
          {selected ? (
            <div
              className="rounded-lg p-6 animate-fade-in-up"
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Briefing — {selected.briefing_date}</h2>
                {selected.pptx_path && (
                  <a
                    href={`/api/reports/${selected.pptx_path.split('/').pop()}`}
                    className="inline-flex items-center gap-1 text-sm transition-colors"
                    style={{ color: 'var(--accent)' }}
                  >
                    <Download className="h-4 w-4" /> Download PPTX
                  </a>
                )}
              </div>
              <div
                className="prose prose-sm prose-invert max-w-none"
                style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}
              >
                {selected.markdown_body || 'No content available.'}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-sm" style={{ color: 'var(--text-muted)' }}>
              Select a briefing to view
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
