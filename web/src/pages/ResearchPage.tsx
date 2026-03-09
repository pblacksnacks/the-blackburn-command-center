import { useState, useEffect } from 'react';
import { Building2, Globe, Users, Newspaper, Linkedin, ExternalLink, Briefcase, MapPin } from 'lucide-react';
import { fetchResearch, fetchLinkedInProfiles, type CompanyResearch, type ContactLinkedIn } from '../api';

const formatLabel = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const cardStyle: React.CSSProperties = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
};

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
      <h1 className="text-xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Research</h1>

      {/* Tab buttons */}
      <div
        className="flex gap-1 mb-4 rounded-lg p-1 w-fit"
        style={{ background: 'rgba(245, 240, 232, 0.05)' }}
      >
        <button
          className="px-4 py-1.5 text-sm rounded-md font-medium transition-colors"
          style={
            tab === 'companies'
              ? { background: 'var(--bg-card-solid)', color: 'var(--text-primary)', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' }
              : { color: 'var(--text-muted)' }
          }
          onClick={() => setTab('companies')}
        >
          <span className="inline-flex items-center gap-1"><Building2 className="h-4 w-4" /> Companies</span>
        </button>
        <button
          className="px-4 py-1.5 text-sm rounded-md font-medium transition-colors"
          style={
            tab === 'contacts'
              ? { background: 'var(--bg-card-solid)', color: 'var(--text-primary)', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' }
              : { color: 'var(--text-muted)' }
          }
          onClick={() => setTab('contacts')}
        >
          <span className="inline-flex items-center gap-1"><Linkedin className="h-4 w-4" /> Contacts ({contacts.length})</span>
        </button>
      </div>

      {/* Companies tab */}
      {tab === 'companies' && (
        <>
          {companies.length === 0 && (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No research data yet. Run the pipeline first.</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {companies.map((c, idx) => (
              <div
                key={c.company_key}
                className={`card-hover rounded-lg p-4 cursor-pointer animate-fade-in-up stagger-${Math.min(idx + 1, 9)}`}
                style={cardStyle}
                onClick={() => setExpanded(expanded === c.company_key ? null : c.company_key)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h2 className="font-semibold flex items-center gap-1" style={{ color: 'var(--text-primary)' }}>
                      <Building2 className="h-4 w-4" style={{ color: 'var(--text-muted)' }} />
                      {c.company_name}
                    </h2>
                    {c.company_domain && (
                      <span className="text-xs flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                        <Globe className="h-3 w-3" /> {c.company_domain}
                      </span>
                    )}
                  </div>
                  <div className="text-right text-xs" style={{ color: 'var(--text-muted)' }}>
                    {c.employee_range && <div className="flex items-center gap-1"><Users className="h-3 w-3" /> {c.employee_range}</div>}
                    {c.funding_stage && <div>{formatLabel(c.funding_stage)}</div>}
                  </div>
                </div>
                <p className="text-sm line-clamp-2" style={{ color: 'var(--text-secondary)' }}>{c.description}</p>

                {expanded === c.company_key && (
                  <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
                    {c.description && <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>{c.description}</p>}
                    {(c.recent_news_json || []).length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold uppercase mb-1 flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                          <Newspaper className="h-3 w-3" /> Recent News
                        </h3>
                        <ul className="space-y-1">
                          {c.recent_news_json.map((n, i) => (
                            <li key={i} className="text-sm">
                              <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{n.title}</span>
                              <span style={{ color: 'var(--text-muted)' }}> — {n.summary}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {c.researched_at && (
                      <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>Researched: {new Date(c.researched_at).toLocaleDateString()}</p>
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
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No LinkedIn profiles yet. Search from a lead detail page.</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {contacts.map((c, idx) => (
              <div
                key={c.sender_email}
                className={`rounded-lg p-4 animate-fade-in-up stagger-${Math.min(idx + 1, 9)}`}
                style={cardStyle}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{c.full_name || c.sender_email}</h2>
                    {c.headline && <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{c.headline}</p>}
                  </div>
                  {c.linkedin_url && (
                    <a
                      href={c.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded"
                      style={{ background: 'rgba(96, 165, 250, 0.1)', color: '#60a5fa' }}
                    >
                      <ExternalLink className="h-3 w-3" /> LinkedIn
                    </a>
                  )}
                </div>
                <div className="flex items-center gap-4 text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
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
                  <div className="pt-2 mt-2" style={{ borderTop: '1px solid var(--border)' }}>
                    {c.experience_json.slice(0, 2).map((exp, i) => (
                      <div key={i} className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{exp.title}</span> at {exp.company}
                        {exp.duration && <span style={{ color: 'var(--text-muted)' }}> · {exp.duration}</span>}
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
