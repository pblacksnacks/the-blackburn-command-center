import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpDown, Users, DollarSign, TrendingUp } from 'lucide-react';
import { fetchLeads, fetchLeadStats, type Lead, type LeadStats } from '../api';
import GradeBadge from '../components/GradeBadge';

const formatAcv = (v: number | null) => (v ? `$${(v / 1000).toFixed(0)}K` : '--');
const formatLabel = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default function Dashboard({ refreshKey }: { refreshKey: number }) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<LeadStats | null>(null);
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
  }, [sortBy, order, gradeFilter, intentFilter, refreshKey]);

  const toggleSort = (col: string) => {
    if (sortBy === col) setOrder(order === 'desc' ? 'asc' : 'desc');
    else { setSortBy(col); setOrder('desc'); }
  };

  const SortHeader = ({ col, children }: { col: string; children: React.ReactNode }) => (
    <th
      className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-700 select-none"
      onClick={() => toggleSort(col)}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        {sortBy === col && <ArrowUpDown className="h-3 w-3" />}
      </span>
    </th>
  );

  return (
    <div>
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Users className="h-4 w-4" /> Total Leads
            </div>
            <div className="text-2xl font-bold">{stats.total}</div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <DollarSign className="h-4 w-4" /> Pipeline ACV
            </div>
            <div className="text-2xl font-bold">${((stats.total_pipeline_acv || 0) / 1000000).toFixed(1)}M</div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <TrendingUp className="h-4 w-4" /> A-Grade
            </div>
            <div className="text-2xl font-bold text-green-600">{stats.grades?.A || 0}</div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">Grade Distribution</div>
            <div className="flex gap-2 text-sm">
              {['A', 'B', 'C', 'D'].map((g) => (
                <span key={g}><GradeBadge grade={g} /> {stats.grades?.[g] || 0}</span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          className="rounded border border-gray-300 px-3 py-1.5 text-sm bg-white"
          value={gradeFilter}
          onChange={(e) => setGradeFilter(e.target.value)}
        >
          <option value="">All Grades</option>
          {['A', 'B', 'C', 'D'].map((g) => <option key={g} value={g}>{g}</option>)}
        </select>
        <select
          className="rounded border border-gray-300 px-3 py-1.5 text-sm bg-white"
          value={intentFilter}
          onChange={(e) => setIntentFilter(e.target.value)}
        >
          <option value="">All Intents</option>
          {['new_business', 'support', 'partnership', 'spam', 'other'].map((i) => (
            <option key={i} value={i}>{formatLabel(i)}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <SortHeader col="grade">Grade</SortHeader>
              <SortHeader col="score">Score</SortHeader>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Sender</th>
              <SortHeader col="intent">Intent</SortHeader>
              <SortHeader col="buying_stage">Stage</SortHeader>
              <SortHeader col="estimated_acv">ACV</SortHeader>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Use Case</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {leads.map((lead) => (
              <tr
                key={lead.sender_email}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => navigate(`/leads/${encodeURIComponent(lead.sender_email)}`)}
              >
                <td className="px-3 py-2.5"><GradeBadge grade={lead.grade} /></td>
                <td className="px-3 py-2.5 font-mono text-sm font-bold">{lead.score}</td>
                <td className="px-3 py-2.5 text-sm font-medium text-gray-900">{lead.company_name || '--'}</td>
                <td className="px-3 py-2.5">
                  <div className="text-sm text-gray-900">{lead.sender_name || lead.sender_email}</div>
                  {lead.sender_title && <div className="text-xs text-gray-500">{lead.sender_title}</div>}
                </td>
                <td className="px-3 py-2.5 text-xs">{formatLabel(lead.intent)}</td>
                <td className="px-3 py-2.5 text-xs">{formatLabel(lead.buying_stage)}</td>
                <td className="px-3 py-2.5 text-sm font-medium">{formatAcv(lead.estimated_acv)}</td>
                <td className="px-3 py-2.5 text-xs">{formatLabel(lead.use_case)}</td>
              </tr>
            ))}
            {leads.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-8 text-center text-sm text-gray-500">
                No leads yet. Run the pipeline to get started.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
