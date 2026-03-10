import { useState, useEffect } from 'react';
import { FileText, Download, Calendar } from 'lucide-react';
import { fetchBriefings, fetchBriefing, type Briefing } from '../api';

function renderMarkdown(md: string): string {
  if (!md) return '';
  let html = md
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold mt-6 mb-2" style="color: var(--accent)">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold mt-8 mb-3" style="color: var(--text-primary)">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold mt-8 mb-4" style="color: var(--text-primary)">$1</h1>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong style="color: var(--text-primary)">$1</strong>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 mb-1" style="color: var(--text-secondary)">$1</li>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: var(--accent); text-decoration: underline;">$1</a>');

  // Wrap consecutive <li> into <ul>
  html = html.replace(/((?:<li[^>]*>.*<\/li>\n?)+)/g, '<ul class="list-disc ml-6 mb-4">$1</ul>');

  // Wrap remaining plain lines as paragraphs
  html = html
    .split('\n')
    .map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return '';
      if (/^<[hula]|^<li|^<\/ul|^<strong/.test(trimmed)) return line;
      return `<p class="mb-2" style="color: var(--text-secondary)">${trimmed}</p>`;
    })
    .join('\n');

  return html;
}

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
      <div className="grid grid-cols-4 gap-5">
        {/* Sidebar — briefing list */}
        <div className="space-y-2">
          {briefings.length === 0 && (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No briefings yet. Run the pipeline first.</p>
          )}
          {briefings.map((b, idx) => {
            const isActive = selected?.briefing_date === b.briefing_date;
            return (
              <button
                key={b.briefing_date}
                onClick={() => loadDetail(b.briefing_date)}
                className={`w-full text-left rounded-xl p-4 text-sm transition-all animate-fade-in-up stagger-${Math.min(idx + 1, 9)}`}
                style={{
                  border: `1px solid ${isActive ? 'color-mix(in srgb, var(--accent) 40%, transparent)' : 'var(--border)'}`,
                  background: isActive ? 'color-mix(in srgb, var(--accent) 8%, transparent)' : 'var(--bg-card)',
                }}
                onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--bg-elevated)'; }}
                onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--bg-card)'; }}
              >
                <div className="flex items-center gap-2 font-semibold" style={{ color: isActive ? 'var(--accent)' : 'var(--text-primary)' }}>
                  <Calendar className="h-4 w-4" style={{ color: isActive ? 'var(--accent)' : 'var(--text-muted)' }} />
                  {b.briefing_date}
                </div>
                <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Created {new Date(b.created_at).toLocaleString()}
                </div>
              </button>
            );
          })}
        </div>

        {/* Main content — briefing detail */}
        <div className="col-span-3">
          {selected ? (
            <div
              className="rounded-xl animate-fade-in-up"
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
            >
              {/* Header with accent bar */}
              <div
                className="flex items-center justify-between px-6 py-4 rounded-t-xl"
                style={{ borderBottom: '1px solid var(--border)', background: 'color-mix(in srgb, var(--accent) 4%, transparent)' }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-1 h-8 rounded-full"
                    style={{ background: 'var(--accent)' }}
                  />
                  <div>
                    <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                      Daily Intelligence Briefing
                    </h2>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {selected.briefing_date}
                    </p>
                  </div>
                </div>
                {selected.pptx_path && (
                  <a
                    href={`/api/reports/${selected.pptx_path.split('/').pop()}`}
                    className="inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg transition-all"
                    style={{
                      color: 'var(--accent)',
                      border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)',
                      background: 'color-mix(in srgb, var(--accent) 6%, transparent)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'color-mix(in srgb, var(--accent) 15%, transparent)';
                      e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--accent) 50%, transparent)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'color-mix(in srgb, var(--accent) 6%, transparent)';
                      e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--accent) 30%, transparent)';
                    }}
                  >
                    <Download className="h-4 w-4" /> Download PPTX
                  </a>
                )}
              </div>

              {/* Rendered markdown content — data sourced from our own briefing agent, not user input */}
              <div className="px-8 py-6 max-w-4xl">
                <div
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(selected.markdown_body || 'No content available.') }}
                />
              </div>
            </div>
          ) : (
            <div
              className="flex flex-col items-center justify-center h-72 rounded-xl"
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
            >
              <FileText className="h-10 w-10 mb-3" style={{ color: 'var(--text-muted)' }} />
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Select a briefing to view</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
