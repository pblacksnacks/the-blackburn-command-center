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
      <h1 className="text-xl font-bold text-gray-900 mb-4">Daily Briefings</h1>
      <div className="grid grid-cols-3 gap-4">
        {/* List */}
        <div className="space-y-2">
          {briefings.length === 0 && (
            <p className="text-sm text-gray-500">No briefings yet. Run the pipeline first.</p>
          )}
          {briefings.map((b) => (
            <button
              key={b.briefing_date}
              onClick={() => loadDetail(b.briefing_date)}
              className={`w-full text-left rounded-lg border p-3 text-sm ${
                selected?.briefing_date === b.briefing_date
                  ? 'border-indigo-300 bg-indigo-50'
                  : 'border-gray-200 bg-white hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-2 font-medium">
                <FileText className="h-4 w-4 text-gray-400" />
                {b.briefing_date}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Created {new Date(b.created_at).toLocaleString()}
              </div>
            </button>
          ))}
        </div>

        {/* Detail */}
        <div className="col-span-2">
          {selected ? (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Briefing — {selected.briefing_date}</h2>
                {selected.pptx_path && (
                  <a
                    href={`/api/reports/${selected.pptx_path.split('/').pop()}`}
                    className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800"
                  >
                    <Download className="h-4 w-4" /> Download PPTX
                  </a>
                )}
              </div>
              <div
                className="prose prose-sm max-w-none text-gray-700"
                style={{ whiteSpace: 'pre-wrap' }}
              >
                {selected.markdown_body || 'No content available.'}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
              Select a briefing to view
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
