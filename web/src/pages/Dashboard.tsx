import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, DollarSign, TrendingUp, BarChart3, Linkedin, ArrowUpDown, Inbox, ArrowRight, Database } from 'lucide-react';
import { fetchLeads, fetchLeadStats, fetchLinkedInProfiles, type Lead, type LeadStats } from '../api';
import GradeBadge from '../components/GradeBadge';

const formatAcv = (v: number | null) => {
  if (!v) return '--';
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  return `$${(v / 1000).toFixed(0)}K`;
};
const formatLabel = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const stageColors: Record<string, string> = {
  ready_to_buy: 'bg-emerald-900/40 text-emerald-300',
  evaluating: 'bg-blue-900/40 text-blue-300',
  researching: 'bg-amber-900/30 text-amber-300',
  not_buying: 'bg-white/5 text-[var(--text-muted)]',
};

export default function Dashboard({ refreshKey }: { refreshKey: number }) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<LeadStats | null>(null);
  const [linkedInEmails, setLinkedInEmails] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState('score');
  const [order, setOrder] = useState('desc');
  const [gradeFilter, setGradeFilter] = useState('');
  const [intentFilter, setIntentFilter] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const params: Record<string, string> = { sort_by: sortBy, order };
    if (gradeFilter) params.grade = gradeFilter;
    if (intentFilter) params.intent = intentFilter;
    fetchLeads(params).then(setLeads).catch(console.error);
    fetchLeadStats().then(setStats).catch(console.error);
    fetchLinkedInProfiles()
      .then((profiles) => setLinkedInEmails(new Set(profiles.map((p) => p.sender_email))))
      .catch(() => {});
  }, [sortBy, order, gradeFilter, intentFilter, refreshKey]);

  const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
  const encodedAccent = encodeURIComponent(accent);
  const selectStyle: React.CSSProperties = {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    color: 'var(--text-primary)',
    borderRadius: 8,
    padding: '8px 32px 8px 12px',
    fontSize: 14,
    fontWeight: 500,
    appearance: 'none' as const,
    backgroundImage: `url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke-width='2' stroke='${encodedAccent}'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='m19.5 8.25-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 8px center',
    backgroundSize: '1.25rem',
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Hero Banner */}
      <div
        className="rounded-2xl p-8 mb-8 animate-fade-in-up"
        style={{
          background: 'linear-gradient(135deg, color-mix(in srgb, var(--accent) 12%, transparent) 0%, rgba(30, 27, 24, 0.8) 50%, rgba(18, 17, 16, 1) 100%)',
          border: '1px solid var(--border)',
        }}
      >
        <h1 className="text-3xl font-extrabold tracking-tight mb-1" style={{ color: 'var(--text-primary)' }}>
          Lead Pipeline
        </h1>
        {stats && (
          <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
            {stats.total} qualified leads &middot; ${((stats.total_pipeline_acv || 0) / 1000000).toFixed(1)}M total pipeline value
          </p>
        )}
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-4 gap-5 mb-8">
          {[
            { icon: Users, label: 'Total Leads', value: stats.total, iconBg: 'color-mix(in srgb, var(--accent) 15%, transparent)', iconColor: 'var(--accent)', delay: 'stagger-1' },
            { icon: DollarSign, label: 'Pipeline ACV', value: `$${((stats.total_pipeline_acv || 0) / 1000000).toFixed(1)}M`, iconBg: 'rgba(74, 222, 128, 0.12)', iconColor: '#4ade80', delay: 'stagger-2' },
            { icon: TrendingUp, label: 'A-Grade Leads', value: stats.grades?.A || 0, iconBg: 'rgba(74, 222, 128, 0.12)', iconColor: '#4ade80', delay: 'stagger-3', valueColor: '#4ade80' },
            { icon: BarChart3, label: 'Grade Distribution', value: null, iconBg: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', iconColor: 'var(--text-secondary)', delay: 'stagger-4' },
          ].map(({ icon: Icon, label, value, iconBg, iconColor, delay, valueColor }, i) => (
            <div
              key={i}
              className={`rounded-xl p-5 animate-fade-in-up ${delay}`}
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className="flex items-center justify-center w-10 h-10 rounded-lg"
                  style={{ background: iconBg }}
                >
                  <Icon className="h-5 w-5" style={{ color: iconColor }} />
                </div>
                <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>{label}</span>
              </div>
              {value !== null ? (
                <div className="text-3xl font-extrabold tracking-tight" style={{ color: valueColor || 'var(--text-primary)' }}>
                  {value}
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  {['A', 'B', 'C', 'D'].map((g) => (
                    <div key={g} className="flex items-center gap-1.5">
                      <GradeBadge grade={g} />
                      <span className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>{stats.grades?.[g] || 0}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Controls: Filters + Sort */}
      <div className="flex items-center justify-between mb-5 animate-fade-in-up stagger-5">
        <div className="flex gap-3">
          <select style={selectStyle} value={gradeFilter} onChange={(e) => setGradeFilter(e.target.value)}>
            <option value="">All Grades</option>
            {['A', 'B', 'C', 'D'].map((g) => <option key={g} value={g}>Grade {g}</option>)}
          </select>
          <select style={selectStyle} value={intentFilter} onChange={(e) => setIntentFilter(e.target.value)}>
            <option value="">All Intents</option>
            {['new_business', 'support', 'partnership', 'spam', 'other'].map((i) => (
              <option key={i} value={i}>{formatLabel(i)}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Sort</span>
          <select style={selectStyle} value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="score">Score</option>
            <option value="grade">Grade</option>
            <option value="estimated_acv">ACV</option>
            <option value="buying_stage">Stage</option>
            <option value="intent">Intent</option>
          </select>
          <button
            onClick={() => setOrder(order === 'desc' ? 'asc' : 'desc')}
            className="flex items-center justify-center w-9 h-9 rounded-lg transition-colors"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
            title={order === 'desc' ? 'Descending' : 'Ascending'}
          >
            <ArrowUpDown className="h-4 w-4" style={{ color: 'var(--text-muted)' }} />
          </button>
        </div>
      </div>

      {/* Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {leads.map((lead, idx) => (
          <div
            key={lead.sender_email}
            className={`card-hover rounded-xl p-5 cursor-pointer group relative animate-fade-in-up stagger-${Math.min(idx + 1, 9)}`}
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
            onClick={() => navigate(`/leads/${encodeURIComponent(lead.sender_email)}`)}
          >
            {/* Top row: grade badge + ACV */}
            <div className="flex items-start justify-between mb-3">
              <GradeBadge grade={lead.grade} />
              <span className="text-xl font-extrabold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                {formatAcv(lead.estimated_acv)}
              </span>
            </div>

            {/* Company name */}
            <h3
              className="text-lg font-bold mb-1 transition-colors"
              style={{ color: 'var(--text-primary)' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-primary)'; }}
            >
              {lead.company_name || 'Unknown Company'}
            </h3>

            {/* Sender */}
            <div className="flex items-center gap-1.5 mb-3">
              <p className="text-sm">
                <span className="font-medium" style={{ color: 'var(--text-secondary)' }}>{lead.sender_name || lead.sender_email}</span>
                {lead.sender_title && <span style={{ color: 'var(--text-muted)' }}> &middot; {lead.sender_title}</span>}
              </p>
              {linkedInEmails.has(lead.sender_email) && (
                <Linkedin className="h-3.5 w-3.5 text-blue-400 flex-shrink-0" />
              )}
            </div>

            {/* Tags: buying stage + use case */}
            <div className="flex flex-wrap gap-2 mb-4">
              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                stageColors[lead.buying_stage] || 'bg-white/5 text-[var(--text-muted)]'
              }`}>
                {formatLabel(lead.buying_stage)}
              </span>
              <span
                className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', color: 'var(--text-muted)' }}
              >
                {formatLabel(lead.use_case)}
              </span>
            </div>

            {/* Score bar + CRM pill */}
            <div className="flex items-center gap-2.5">
              <div className="flex-1 rounded-full h-1.5" style={{ background: 'var(--border)' }}>
                <div
                  className="h-1.5 rounded-full animate-bar-fill"
                  style={{ width: `${lead.score}%`, background: 'linear-gradient(to right, var(--accent), var(--accent-hover))' }}
                />
              </div>
              <span className="text-xs font-bold tabular-nums w-6 text-right" style={{ color: 'var(--text-secondary)' }}>{lead.score}</span>
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 transition-all"
                style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'color-mix(in srgb, var(--text-primary) 5%, transparent)', border: '1px solid var(--border)' }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--border-hover)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'color-mix(in srgb, var(--text-primary) 5%, transparent)'; }}
                onClick={(e) => e.stopPropagation()}
              >
                <Database className="h-3 w-3" />
                Sync with CRM
              </span>
            </div>

            {/* Hover action bar */}
            <div
              className="absolute bottom-0 left-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-2 py-2 rounded-b-xl"
              style={{ background: 'linear-gradient(to top, color-mix(in srgb, var(--accent) 10%, transparent), transparent)' }}
            >
              <span className="text-xs font-semibold flex items-center gap-1" style={{ color: 'var(--accent)' }}>
                View Details <ArrowRight className="h-3 w-3" />
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Empty state */}
      {leads.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div
            className="flex items-center justify-center w-16 h-16 rounded-2xl mb-4"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
          >
            <Inbox className="h-8 w-8" style={{ color: 'var(--text-muted)' }} />
          </div>
          <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>No leads yet</h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Run the pipeline to get started.</p>
        </div>
      )}
    </div>
  );
}
