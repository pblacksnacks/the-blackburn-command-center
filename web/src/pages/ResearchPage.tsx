import { useState, useEffect } from 'react';
import { Building2, Globe, Users, Newspaper, Linkedin, ExternalLink, Briefcase, MapPin } from 'lucide-react';
import { fetchResearch, fetchLinkedInProfiles, type CompanyResearch, type ContactLinkedIn } from '../api';

const formatLabel = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default function ResearchPage({ refreshKey }: { refreshKey: number }) {
  const [tab, setTab] = useState<'companies' | 'contacts'>('companies');
  const [companies, setCompanies] = useState<CompanyResearch[]>([]);
  const [contacts, setContacts] = useState<ContactLinkedIn[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetchResearch().then(setCompanies).catch(console.error);
    fetchLinkedInProfiles().then(setContacts).catch(console.error);
  }, [refreshKey]);

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 mb-4">Research</h1>

      {/* Tab buttons */}
      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          className={`px-4 py-1.5 text-sm rounded-md font-medium transition-colors ${
            tab === 'companies' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
          onClick={() => setTab('companies')}
        >
          <span className="inline-flex items-center gap-1"><Building2 className="h-4 w-4" /> Companies</span>
        </button>
        <button
          className={`px-4 py-1.5 text-sm rounded-md font-medium transition-colors ${
            tab === 'contacts' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
          onClick={() => setTab('contacts')}
        >
          <span className="inline-flex items-center gap-1"><Linkedin className="h-4 w-4" /> Contacts ({contacts.length})</span>
        </button>
      </div>

      {/* Companies tab */}
      {tab === 'companies' && (
        <>
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
        </>
      )}

      {/* Contacts tab */}
      {tab === 'contacts' && (
        <>
          {contacts.length === 0 && (
            <p className="text-sm text-gray-500">No LinkedIn profiles yet. Search from a lead detail page.</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {contacts.map((c) => (
              <div key={c.sender_email} className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h2 className="font-semibold text-gray-900">{c.full_name || c.sender_email}</h2>
                    {c.headline && <p className="text-sm text-gray-600">{c.headline}</p>}
                  </div>
                  {c.linkedin_url && (
                    <a
                      href={c.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 bg-blue-50 px-2 py-0.5 rounded"
                    >
                      <ExternalLink className="h-3 w-3" /> LinkedIn
                    </a>
                  )}
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500 mb-2">
                  {c.current_title && (
                    <span className="inline-flex items-center gap-1">
                      <Briefcase className="h-3 w-3" /> {c.current_title}
                    </span>
                  )}
                  {c.current_company && (
                    <span className="inline-flex items-center gap-1">
                      <Building2 className="h-3 w-3" /> {c.current_company}
                    </span>
                  )}
                  {c.location && (
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3 w-3" /> {c.location}
                    </span>
                  )}
                </div>
                {c.experience_json && c.experience_json.length > 0 && (
                  <div className="border-t border-gray-100 pt-2 mt-2">
                    {c.experience_json.slice(0, 2).map((exp, i) => (
                      <div key={i} className="text-xs text-gray-600">
                        <span className="font-medium">{exp.title}</span> at {exp.company}
                        {exp.duration && <span className="text-gray-400"> · {exp.duration}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
