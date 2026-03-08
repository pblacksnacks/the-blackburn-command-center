import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Mail, Building2, User, Target, Lightbulb } from 'lucide-react';
import { fetchLead, type Lead } from '../api';
import GradeBadge from '../components/GradeBadge';
import MeddpiccBadge from '../components/MeddpiccBadge';

const formatAcv = (v: number | null) => (v ? `$${v.toLocaleString()}` : '--');
const formatLabel = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const ScoreBar = ({ label, value, max }: { label: string; value: number; max: number }) => (
  <div className="flex items-center gap-2">
    <span className="text-xs text-gray-500 w-28">{label}</span>
    <div className="flex-1 bg-gray-100 rounded-full h-2">
      <div
        className="bg-indigo-500 h-2 rounded-full"
        style={{ width: `${(value / max) * 100}%` }}
      />
    </div>
    <span className="text-xs font-mono w-10 text-right">{value}/{max}</span>
  </div>
);

export default function LeadDetailPage() {
  const { email } = useParams<{ email: string }>();
  const [lead, setLead] = useState<Lead | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!email) return;
    fetchLead(decodeURIComponent(email)).then(setLead).catch((e) => setError(e.message));
  }, [email]);

  if (error) return <div className="text-red-600 p-4">Error: {error}</div>;
  if (!lead) return <div className="text-gray-500 p-4">Loading...</div>;

  return (
    <div className="max-w-5xl mx-auto">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="h-4 w-4" /> Back to dashboard
      </Link>

      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <GradeBadge grade={lead.grade} size="lg" />
              <h1 className="text-2xl font-bold text-gray-900">{lead.company_name || 'Unknown Company'}</h1>
              <span className="text-lg font-mono text-gray-600">{lead.score}/100</span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span className="inline-flex items-center gap-1"><User className="h-4 w-4" /> {lead.sender_name || lead.sender_email}</span>
              {lead.sender_title && <span>{lead.sender_title}</span>}
              <span className="inline-flex items-center gap-1"><Mail className="h-4 w-4" /> {lead.sender_email}</span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">{formatAcv(lead.estimated_acv)}</div>
            <div className="text-xs text-gray-500">{formatLabel(lead.deal_size_tier)} ACV</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Scoring Breakdown */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Scoring Breakdown</h2>
          <div className="space-y-2">
            <ScoreBar label="Intent" value={lead.intent_score} max={30} />
            <ScoreBar label="Domain Quality" value={lead.domain_quality_score} max={25} />
            <ScoreBar label="Urgency" value={lead.urgency_score} max={20} />
            <ScoreBar label="Content Depth" value={lead.content_depth_score} max={15} />
            <ScoreBar label="Authority" value={lead.authority_score} max={10} />
          </div>
        </div>

        {/* Classification */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Classification</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-gray-500">Intent:</span> <span className="font-medium">{formatLabel(lead.intent)}</span></div>
            <div><span className="text-gray-500">Use Case:</span> <span className="font-medium">{formatLabel(lead.use_case)}</span></div>
            <div><span className="text-gray-500">Product Fit:</span> <span className="font-medium">{formatLabel(lead.product_line_fit)}</span></div>
            <div><span className="text-gray-500">Buying Stage:</span> <span className="font-medium">{formatLabel(lead.buying_stage)}</span></div>
            <div><span className="text-gray-500">AI Provider:</span> <span className="font-medium">{lead.current_ai_provider || 'Unknown'}</span></div>
            <div><span className="text-gray-500">TAM:</span> <span className="font-medium">{lead.tam_estimate || '--'}</span></div>
          </div>
          {lead.expansion_potential && (
            <div className="mt-3 text-sm">
              <span className="text-gray-500">Expansion:</span> <span>{lead.expansion_potential}</span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* MEDDPICC */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">MEDDPICC</h2>
          <MeddpiccBadge meddpicc={lead.meddpicc_json} />
        </div>

        {/* Next Action & Discovery */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1">
            <Target className="h-4 w-4" /> Next Best Action
          </h2>
          <p className="text-sm text-gray-800 bg-indigo-50 rounded p-3 mb-4">{lead.next_best_action}</p>

          <h2 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
            <Lightbulb className="h-4 w-4" /> Discovery Questions
          </h2>
          <ul className="space-y-1">
            {(lead.discovery_questions_json || []).map((q, i) => (
              <li key={i} className="text-sm text-gray-700">• {q}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Competitive & Partnership */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Competitive Signals</h2>
          {(lead.competitive_signals_json || []).length > 0
            ? <ul className="space-y-1">{lead.competitive_signals_json.map((s, i) => <li key={i} className="text-sm text-gray-700">• {s}</li>)}</ul>
            : <p className="text-sm text-gray-400">None detected</p>
          }
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Partnership</h2>
          <div className="mb-2">
            <span className="text-xs text-gray-500 uppercase">Synergies</span>
            {(lead.partnership_synergies_json || []).map((s, i) => <p key={i} className="text-sm text-green-700">+ {s}</p>)}
          </div>
          <div>
            <span className="text-xs text-gray-500 uppercase">Detractors</span>
            {(lead.partnership_detractors_json || []).map((s, i) => <p key={i} className="text-sm text-red-700">- {s}</p>)}
          </div>
        </div>
      </div>

      {/* Reasoning */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Scoring Reasoning</h2>
        <p className="text-sm text-gray-700 whitespace-pre-wrap">{lead.last_reasoning}</p>
      </div>

      {/* Email History */}
      {lead.emails && lead.emails.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1">
            <Mail className="h-4 w-4" /> Email History ({lead.emails.length})
          </h2>
          <div className="space-y-3">
            {lead.emails.map((e) => (
              <div key={e.email_id} className="border border-gray-100 rounded p-3">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium">{e.subject}</span>
                  <span className="text-xs text-gray-500">{new Date(e.received_at).toLocaleDateString()}</span>
                </div>
                <p className="text-xs text-gray-600 whitespace-pre-wrap line-clamp-4">{e.body}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
