import { useState, useEffect } from 'react';
import { Building2, Globe, Users, Newspaper } from 'lucide-react';
import { fetchResearch, type CompanyResearch } from '../api';

const formatLabel = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default function ResearchPage({ refreshKey }: { refreshKey: number }) {
  const [companies, setCompanies] = useState<CompanyResearch[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetchResearch().then(setCompanies).catch(console.error);
  }, [refreshKey]);

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 mb-4">Company Research</h1>
      {companies.length === 0 && (
        <p className="text-sm text-gray-500">No research data yet. Run the pipeline first.</p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {companies.map((c) => (
          <div
            key={c.company_key}
            className="bg-white rounded-lg border border-gray-200 p-4 cursor-pointer hover:shadow-sm"
            onClick={() => setExpanded(expanded === c.company_key ? null : c.company_key)}
          >
            <div className="flex items-start justify-between mb-2">
              <div>
                <h2 className="font-semibold text-gray-900 flex items-center gap-1">
                  <Building2 className="h-4 w-4 text-gray-400" />
                  {c.company_name}
                </h2>
                {c.company_domain && (
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <Globe className="h-3 w-3" /> {c.company_domain}
                  </span>
                )}
              </div>
              <div className="text-right text-xs text-gray-500">
                {c.employee_range && <div className="flex items-center gap-1"><Users className="h-3 w-3" /> {c.employee_range}</div>}
                {c.funding_stage && <div>{formatLabel(c.funding_stage)}</div>}
              </div>
            </div>
            <p className="text-sm text-gray-600 line-clamp-2">{c.description}</p>

            {expanded === c.company_key && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                {c.description && <p className="text-sm text-gray-700 mb-3">{c.description}</p>}
                {(c.recent_news_json || []).length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold text-gray-500 uppercase mb-1 flex items-center gap-1">
                      <Newspaper className="h-3 w-3" /> Recent News
                    </h3>
                    <ul className="space-y-1">
                      {c.recent_news_json.map((n, i) => (
                        <li key={i} className="text-sm">
                          <span className="font-medium">{n.title}</span>
                          <span className="text-gray-500"> — {n.summary}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {c.researched_at && (
                  <p className="text-xs text-gray-400 mt-2">Researched: {new Date(c.researched_at).toLocaleDateString()}</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
