import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, DollarSign, TrendingUp, BarChart3, Linkedin, ArrowUpDown, Inbox } from 'lucide-react';
import { fetchLeads, fetchLeadStats, fetchLinkedInProfiles, type Lead, type LeadStats } from '../api';
import GradeBadge from '../components/GradeBadge';

const formatAcv = (v: number | null) => (v ? `$${(v / 1000).toFixed(0)}K` : '--');
const formatLabel = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const stageColors: Record<string, string> = {
  ready_to_buy: 'bg-emerald-50 text-emerald-700',
  evaluating: 'bg-blue-50 text-blue-700',
  researching: 'bg-amber-50 text-amber-700',
  not_buying: 'bg-slate-100 text-slate-600',
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

  return (
    <div className="max-w-7xl mx-auto">
      {/* Hero Banner */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-8 mb-8">
        <h1 className="text-3xl font-extrabold text-white tracking-tight mb-1">Lead Pipeline</h1>
        {stats && (
          <p className="text-slate-400 text-sm font-medium">
            {stats.total} qualified leads &middot; ${((stats.total_pipeline_acv || 0) / 1000000).toFixed(1)}M total pipeline value
          </p>
        )}
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-4 gap-5 mb-8">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-50">
                <Users className="h-5 w-5 text-blue-600" />
              </div>
              <span className="text-sm font-medium text-slate-500">Total Leads</span>
            </div>
            <div className="text-3xl font-extrabold text-slate-900 tracking-tight">{stats.total}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-emerald-50">
                <DollarSign className="h-5 w-5 text-emerald-600" />
              </div>
              <span className="text-sm font-medium text-slate-500">Pipeline ACV</span>
            </div>
            <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
              ${((stats.total_pipeline_acv || 0) / 1000000).toFixed(1)}M
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-emerald-50">
                <TrendingUp className="h-5 w-5 text-emerald-600" />
              </div>
              <span className="text-sm font-medium text-slate-500">A-Grade Leads</span>
            </div>
            <div className="text-3xl font-extrabold text-emerald-600 tracking-tight">{stats.grades?.A || 0}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-100">
                <BarChart3 className="h-5 w-5 text-slate-600" />
              </div>
              <span className="text-sm font-medium text-slate-500">Grade Distribution</span>
            </div>
            <div className="flex items-center gap-3">
              {['A', 'B', 'C', 'D'].map((g) => (
                <div key={g} className="flex items-center gap-1.5">
                  <GradeBadge grade={g} />
                  <span className="text-sm font-semibold text-slate-700">{stats.grades?.[g] || 0}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Controls: Filters + Sort */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex gap-3">
          <select
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none pr-8 bg-no-repeat bg-[right_0.5rem_center] bg-[length:1.25rem_1.25rem] bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2024%2024%22%20stroke-width%3D%222%22%20stroke%3D%22%2394a3b8%22%3E%3Cpath%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20d%3D%22m19.5%208.25-7.5%207.5-7.5-7.5%22%2F%3E%3C%2Fsvg%3E')]"
            value={gradeFilter}
            onChange={(e) => setGradeFilter(e.target.value)}
          >
            <option value="">All Grades</option>
            {['A', 'B', 'C', 'D'].map((g) => <option key={g} value={g}>Grade {g}</option>)}
          </select>
          <select
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none pr-8 bg-no-repeat bg-[right_0.5rem_center] bg-[length:1.25rem_1.25rem] bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2024%2024%22%20stroke-width%3D%222%22%20stroke%3D%22%2394a3b8%22%3E%3Cpath%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20d%3D%22m19.5%208.25-7.5%207.5-7.5-7.5%22%2F%3E%3C%2Fsvg%3E')]"
            value={intentFilter}
            onChange={(e) => setIntentFilter(e.target.value)}
          >
            <option value="">All Intents</option>
            {['new_business', 'support', 'partnership', 'spam', 'other'].map((i) => (
              <option key={i} value={i}>{formatLabel(i)}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Sort</span>
          <select
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none pr-8 bg-no-repeat bg-[right_0.5rem_center] bg-[length:1.25rem_1.25rem] bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2024%2024%22%20stroke-width%3D%222%22%20stroke%3D%22%2394a3b8%22%3E%3Cpath%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20d%3D%22m19.5%208.25-7.5%207.5-7.5-7.5%22%2F%3E%3C%2Fsvg%3E')]"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="score">Score</option>
            <option value="grade">Grade</option>
            <option value="estimated_acv">ACV</option>
            <option value="buying_stage">Stage</option>
            <option value="intent">Intent</option>
          </select>
          <button
            onClick={() => setOrder(order === 'desc' ? 'asc' : 'desc')}
            className="flex items-center justify-center w-9 h-9 rounded-lg border border-slate-200 bg-white shadow-sm hover:bg-slate-50 transition-colors"
            title={order === 'desc' ? 'Descending' : 'Ascending'}
          >
            <ArrowUpDown className="h-4 w-4 text-slate-500" />
          </button>
        </div>
      </div>

      {/* Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {leads.map((lead) => (
          <div
            key={lead.sender_email}
            className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5 hover:shadow-md hover:border-slate-300/80 transition-all duration-200 cursor-pointer group"
            onClick={() => navigate(`/leads/${encodeURIComponent(lead.sender_email)}`)}
          >
            {/* Top row: grade badge + ACV */}
            <div className="flex items-start justify-between mb-3">
              <GradeBadge grade={lead.grade} />
              <span className="text-xl font-extrabold text-slate-900 tracking-tight">
                {formatAcv(lead.estimated_acv)}
              </span>
            </div>

            {/* Company name */}
            <h3 className="text-lg font-bold text-slate-900 mb-1 group-hover:text-blue-600 transition-colors">
              {lead.company_name || 'Unknown Company'}
            </h3>

            {/* Sender */}
            <div className="flex items-center gap-1.5 mb-3">
              <p className="text-sm text-slate-500">
                <span className="font-medium text-slate-600">{lead.sender_name || lead.sender_email}</span>
                {lead.sender_title && <span className="font-light text-slate-400"> &middot; {lead.sender_title}</span>}
              </p>
              {linkedInEmails.has(lead.sender_email) && (
                <Linkedin className="h-3.5 w-3.5 text-blue-500 flex-shrink-0" />
              )}
            </div>

            {/* Tags: buying stage + use case */}
            <div className="flex flex-wrap gap-2 mb-4">
              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                stageColors[lead.buying_stage] || 'bg-slate-100 text-slate-600'
              }`}>
                {formatLabel(lead.buying_stage)}
              </span>
              <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
                {formatLabel(lead.use_case)}
              </span>
            </div>

            {/* Score bar */}
            <div className="flex items-center gap-2.5">
              <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                <div
                  className="h-1.5 rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
                  style={{ width: `${lead.score}%` }}
                />
              </div>
              <span className="text-xs font-bold text-slate-500 tabular-nums w-6 text-right">{lead.score}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Empty state */}
      {leads.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-slate-100 mb-4">
            <Inbox className="h-8 w-8 text-slate-400" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 mb-1">No leads yet</h3>
          <p className="text-sm text-slate-500">Run the pipeline to get started.</p>
        </div>
      )}
    </div>
  );
}
