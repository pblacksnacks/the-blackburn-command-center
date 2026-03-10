import { useState, useEffect, useMemo, useRef, Component, type ReactNode } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, Mail, User, Target, Lightbulb, Linkedin, ExternalLink,
  Loader2, Search, Briefcase, MapPin, Calendar, RefreshCw,
  Zap, X, Copy, Check, Download, Shield, Swords, TrendingUp,
  MessageSquare, AlertTriangle, Crosshair, Rocket, Ban, ClipboardList,
  Send, ChevronDown, ChevronRight, FileText,
} from 'lucide-react';
import {
  fetchLead, fetchLinkedInProfile, searchLinkedIn, fetchLinkedInSearchStatus,
  fetchResearch, generateCallPrep, downloadCallPrepPdf, downloadCallPrepPptx, generateDraftEmail,
  type Lead, type ContactLinkedIn, type CompanyResearch, type CallPrep, type DraftEmail,
} from '../api';
import GradeBadge from '../components/GradeBadge';
import { useMode } from '../modeContext';
import MeddpiccBadge from '../components/MeddpiccBadge';
import OrgPowerMap from '../components/OrgPowerMap';
import DepartmentHeatMap from '../components/DepartmentHeatMap';

const formatAcv = (v: number | null) => (v ? `$${v.toLocaleString()}` : '--');
const formatLabel = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const cardStyle: React.CSSProperties = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
};

const ScoreBar = ({ label, value, max }: { label: string; value: number; max: number }) => (
  <div className="flex items-center gap-2">
    <span className="text-xs w-28" style={{ color: 'var(--text-secondary)' }}>{label}</span>
    <div className="flex-1 rounded-full h-2" style={{ background: 'var(--border)' }}>
      <div
        className="h-2 rounded-full animate-bar-fill"
        style={{ width: `${(value / max) * 100}%`, background: 'linear-gradient(to right, var(--accent), var(--accent-hover))' }}
      />
    </div>
    <span className="text-xs font-mono w-10 text-right" style={{ color: 'var(--text-secondary)' }}>{value}/{max}</span>
  </div>
);

/* ── Calendar URL builder ─────────────────────────────────────── */

function buildCalendarUrl(lead: Lead): string {
  const title = `Discovery Call: ${lead.company_name || 'Prospect'} - ${lead.sender_name || 'Contact'}`;

  const start = new Date();
  start.setDate(start.getDate() + 1);
  const day = start.getDay();
  if (day === 0) start.setDate(start.getDate() + 1);
  if (day === 6) start.setDate(start.getDate() + 2);
  start.setHours(10, 0, 0, 0);

  const end = new Date(start);
  end.setMinutes(end.getMinutes() + 30);

  const pad = (d: Date) => {
    const y = d.getFullYear();
    const mo = String(d.getMonth() + 1).padStart(2, '0');
    const da = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const mi = String(d.getMinutes()).padStart(2, '0');
    return `${y}${mo}${da}T${h}${mi}00`;
  };

  const questions = (lead.discovery_questions_json || [])
    .slice(0, 3)
    .map((q, i) => `${i + 1}. ${q}`)
    .join('\n');

  const description = [
    'Next Best Action:',
    lead.next_best_action,
    '',
    'Discovery Questions:',
    questions,
  ].join('\n');

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: title,
    dates: `${pad(start)}/${pad(end)}`,
    details: description,
  });

  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

/* ── Employee estimate helper ─────────────────────────────────── */

function parseEmployeeRange(range: string | null): number | null {
  if (!range) return null;
  // Strip HTML/XML tags (e.g. <cite>) that may wrap research output
  const clean = range.replace(/<[^>]*>/g, '');
  // Prefer "approximately N" or "~N" for a precise count
  const approxMatch = clean.match(/(?:approximately|approx\.?|~)\s*([\d,]+)/i);
  if (approxMatch) return parseInt(approxMatch[1].replace(/,/g, ''), 10) || null;
  const nums = clean.match(/(\d[\d,]*)/g);
  if (!nums) return null;
  const parsed = nums.map((s) => parseInt(s.replace(/,/g, ''), 10));
  if (parsed.length >= 2) return Math.round((parsed[0] + parsed[1]) / 2);
  return parsed[0] || null;
}

/* ── Defensive array parsers ──────────────────────────────────── */

function toStringArray(val: unknown): string[] {
  if (Array.isArray(val)) return val.map((v) => String(v));
  if (typeof val === 'string') return val.split('\n').filter(Boolean);
  return [];
}

function toObjectionArray(val: unknown): Array<{ objection: string; response: string }> {
  if (Array.isArray(val)) {
    return val.map((v) => {
      if (typeof v === 'object' && v !== null) {
        return {
          objection: String((v as Record<string, unknown>).objection ?? ''),
          response: String((v as Record<string, unknown>).response ?? ''),
        };
      }
      const s = String(v);
      return { objection: s, response: '' };
    });
  }
  if (typeof val === 'string') {
    return val.split('\n').filter(Boolean).map((s) => ({ objection: s, response: '' }));
  }
  return [];
}

/* ── Error boundary for modal ────────────────────────────────── */

class CallPrepErrorBoundary extends Component<
  { children: ReactNode; onClose: () => void },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <div
            className="rounded-lg p-4"
            style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)' }}
          >
            <p className="text-sm text-red-400 mb-3">Failed to render call prep — the response may have an unexpected format.</p>
            <button
              onClick={this.props.onClose}
              className="inline-flex items-center gap-1.5 text-xs font-medium rounded-lg px-3 py-2 transition-colors"
              style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            >
              Close
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const CallPrepLoadingSkeleton = () => (
  <div className="space-y-6 p-6">
    <div className="flex items-center gap-3 mb-6">
      <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
      <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
        Generating call prep brief with Claude...
      </span>
    </div>
    {Array.from({ length: 6 }).map((_, i) => (
      <div key={i} className="rounded-lg p-5" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
        <div className="h-4 rounded w-40 mb-3" style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)' }} />
        <div className="space-y-2">
          <div className="h-3 rounded w-full animate-pulse" style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', animationDelay: `${i * 0.1}s` }} />
          <div className="h-3 rounded w-4/5 animate-pulse" style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', animationDelay: `${i * 0.1 + 0.05}s` }} />
          <div className="h-3 rounded w-3/5 animate-pulse" style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', animationDelay: `${i * 0.1 + 0.1}s` }} />
        </div>
      </div>
    ))}
  </div>
);

/* ── Call Prep Modal ──────────────────────────────────────────── */

function CallPrepModal({
  data,
  loading,
  error,
  onClose,
  onExportPdf,
  onExportPptx,
  exportingPdf,
  exportingPptx,
  companyName,
}: {
  data: CallPrep | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onExportPdf: () => void;
  onExportPptx: () => void;
  exportingPdf: boolean;
  exportingPptx: boolean;
  companyName: string;
}) {
  const [copied, setCopied] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const agenda = toStringArray(data?.suggested_agenda);
  const questions = toStringArray(data?.discovery_questions);
  const objections = toObjectionArray(data?.objection_prep);
  const doNotSay = toStringArray(data?.do_not_say);

  const handleCopy = () => {
    if (!data) return;
    const text = [
      `CALL PREP: ${companyName}`,
      '',
      '== CONTACT SUMMARY ==',
      data.contact_summary,
      '',
      '== COMPANY SNAPSHOT ==',
      data.company_snapshot,
      '',
      '== WHY THEY\'RE HERE ==',
      data.why_theyre_here,
      '',
      '== CURRENT STACK ==',
      data.current_stack,
      '',
      '== SUGGESTED AGENDA ==',
      ...agenda.map((a, i) => `${i + 1}. ${a}`),
      '',
      '== DISCOVERY QUESTIONS ==',
      ...questions.map((q, i) => `${i + 1}. ${q}`),
      '',
      '== OBJECTION PREP ==',
      ...objections.map((o) => `Objection: ${o.objection}\nResponse: ${o.response}\n`),
      '',
      '== COMPETITIVE POSITIONING ==',
      data.competitive_positioning,
      '',
      '== LAND STRATEGY ==',
      data.land_strategy,
      '',
      '== EXPAND STRATEGY ==',
      data.expand_strategy,
      '',
      '== PROPOSED NEXT STEP ==',
      data.proposed_next_step,
      '',
      '== DO NOT SAY ==',
      ...doNotSay.map((d) => `- ${d}`),
    ].join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sectionCard = (
    icon: React.ReactNode,
    title: string,
    children: React.ReactNode,
    accentBorder = false,
  ) => (
    <div
      className="rounded-lg p-5 animate-fade-in-up"
      style={{
        background: 'var(--bg-card)',
        border: accentBorder ? '1px solid color-mix(in srgb, var(--accent) 20%, transparent)' : '1px solid var(--border)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span style={{ color: 'var(--accent)' }}>{icon}</span>
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h3>
      </div>
      {children}
    </div>
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto"
      style={{ background: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="w-full max-w-4xl my-8 rounded-xl overflow-hidden"
        style={{ background: 'var(--bg-base)', border: '1px solid var(--border)' }}
      >
        {/* Modal header */}
        <div
          className="sticky top-0 z-10 flex items-center justify-between px-6 py-4"
          style={{ background: 'rgba(18, 17, 16, 0.95)', borderBottom: '1px solid var(--border)', backdropFilter: 'blur(8px)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="flex items-center justify-center w-8 h-8 rounded-lg"
              style={{ background: 'color-mix(in srgb, var(--accent) 15%, transparent)' }}
            >
              <Zap className="h-4 w-4" style={{ color: 'var(--accent)' }} />
            </div>
            <div>
              <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                Call Prep: {companyName}
              </h2>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                AI-generated discovery call preparation brief
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {data && (
              <>
                <button
                  onClick={onExportPdf}
                  disabled={exportingPdf}
                  className="inline-flex items-center gap-1.5 text-xs font-medium rounded-lg px-3 py-2 transition-colors disabled:opacity-50"
                  style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                >
                  {exportingPdf ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileText className="h-3 w-3" />}
                  Pre-Call Brief (PDF)
                </button>
                <button
                  onClick={onExportPptx}
                  disabled={exportingPptx}
                  className="inline-flex items-center gap-1.5 text-xs font-medium rounded-lg px-3 py-2 transition-colors disabled:opacity-50"
                  style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                >
                  {exportingPptx ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
                  Customer Deck (PPTX)
                </button>
                <button
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1.5 text-xs font-medium rounded-lg px-3 py-2 transition-colors"
                  style={{ background: 'color-mix(in srgb, var(--accent) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--accent) 20%, transparent)', color: 'var(--accent)' }}
                >
                  {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  {copied ? 'Copied' : 'Copy All'}
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="flex items-center justify-center w-8 h-8 rounded-lg transition-colors"
              style={{ color: 'var(--text-muted)' }}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Modal content */}
        <div ref={contentRef}>
          {loading && <CallPrepLoadingSkeleton />}

          {error && (
            <div className="p-6">
              <div className="rounded-lg p-4" style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                <p className="text-sm text-red-400">Failed to generate call prep: {error}</p>
              </div>
            </div>
          )}

          {data && (<CallPrepErrorBoundary onClose={onClose}>
            <div className="p-6 space-y-4">
              {/* Row 1: Contact + Company */}
              <div className="grid grid-cols-2 gap-4">
                {sectionCard(
                  <User className="h-4 w-4" />,
                  'Contact Summary',
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{data.contact_summary}</p>,
                )}
                {sectionCard(
                  <Briefcase className="h-4 w-4" />,
                  'Company Snapshot',
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{data.company_snapshot}</p>,
                )}
              </div>

              {/* Row 2: Why + Current Stack */}
              <div className="grid grid-cols-2 gap-4">
                {sectionCard(
                  <Target className="h-4 w-4" />,
                  "Why They're Here",
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{data.why_theyre_here}</p>,
                  true,
                )}
                {sectionCard(
                  <Crosshair className="h-4 w-4" />,
                  'Current Stack',
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{data.current_stack}</p>,
                )}
              </div>

              {/* Agenda */}
              {sectionCard(
                <ClipboardList className="h-4 w-4" />,
                '25-Minute Discovery Agenda',
                <div className="space-y-2">
                  {agenda.map((item, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <span
                        className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold"
                        style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)' }}
                      >
                        {i + 1}
                      </span>
                      <p className="text-sm pt-0.5" style={{ color: 'var(--text-secondary)' }}>{item}</p>
                    </div>
                  ))}
                </div>,
                true,
              )}

              {/* Discovery Questions */}
              {sectionCard(
                <MessageSquare className="h-4 w-4" />,
                'Tailored Discovery Questions',
                <div className="space-y-2">
                  {questions.map((q, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <span
                        className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold"
                        style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)' }}
                      >
                        {i + 1}
                      </span>
                      <p className="text-sm pt-0.5 italic" style={{ color: 'var(--text-secondary)' }}>"{q}"</p>
                    </div>
                  ))}
                </div>,
              )}

              {/* Objection Prep */}
              {sectionCard(
                <Shield className="h-4 w-4" />,
                'Objection Prep',
                <div className="space-y-4">
                  {objections.map((obj, i) => (
                    <div key={i} className="rounded-lg p-4" style={{ background: 'color-mix(in srgb, var(--text-primary) 3%, transparent)', border: '1px solid var(--border)' }}>
                      <div className="flex items-start gap-2 mb-2">
                        <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5 text-amber-400" />
                        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{obj.objection}</p>
                      </div>
                      <div className="flex items-start gap-2 ml-5.5">
                        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{obj.response}</p>
                      </div>
                    </div>
                  ))}
                </div>,
              )}

              {/* Competitive Positioning */}
              {sectionCard(
                <Swords className="h-4 w-4" />,
                'Competitive Positioning',
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{data.competitive_positioning}</p>,
                true,
              )}

              {/* Deal Strategy */}
              <div className="grid grid-cols-2 gap-4">
                {sectionCard(
                  <Rocket className="h-4 w-4" />,
                  'Land Strategy',
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{data.land_strategy}</p>,
                )}
                {sectionCard(
                  <TrendingUp className="h-4 w-4" />,
                  'Expand Strategy (12-Month)',
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{data.expand_strategy}</p>,
                )}
              </div>

              {/* Next Step + Do Not Say */}
              <div className="grid grid-cols-2 gap-4">
                {sectionCard(
                  <Target className="h-4 w-4" />,
                  'Proposed Next Step',
                  <p
                    className="text-sm leading-relaxed rounded-lg p-3"
                    style={{ background: 'color-mix(in srgb, var(--accent) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--accent) 15%, transparent)', color: 'var(--text-primary)' }}
                  >
                    {data.proposed_next_step}
                  </p>,
                  true,
                )}
                {sectionCard(
                  <Ban className="h-4 w-4" />,
                  'Do Not Say',
                  <div className="space-y-1.5">
                    {doNotSay.map((item, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <X className="h-3.5 w-3.5 flex-shrink-0 mt-0.5 text-red-400" />
                        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{item}</p>
                      </div>
                    ))}
                  </div>,
                )}
              </div>
            </div>
          </CallPrepErrorBoundary>)}
        </div>
      </div>
    </div>
  );
}

/* ── Draft Email Modal ────────────────────────────────────────── */

function DraftEmailModal({
  data,
  loading,
  error,
  onClose,
  onRegenerate,
  lead,
}: {
  data: DraftEmail | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onRegenerate: () => void;
  lead: Lead;
}) {
  const mode = useMode();
  const [copied, setCopied] = useState(false);
  const [followUpOpen, setFollowUpOpen] = useState(false);

  const handleCopy = () => {
    if (!data) return;
    navigator.clipboard.writeText(`Subject: ${data.subject}\n\n${data.body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const gmailUrl = data
    ? `mailto:${lead.sender_email}?subject=${encodeURIComponent(data.subject)}&body=${encodeURIComponent(data.body)}`
    : '#';

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto"
      style={{ background: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="w-full max-w-2xl my-8 rounded-xl overflow-hidden"
        style={{ background: 'var(--bg-base)', border: '1px solid var(--border)' }}
      >
        {/* Modal header */}
        <div
          className="sticky top-0 z-10 flex items-center justify-between px-6 py-4"
          style={{ background: 'color-mix(in srgb, var(--bg-base) 95%, transparent)', borderBottom: '1px solid var(--border)', backdropFilter: 'blur(8px)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="flex items-center justify-center w-8 h-8 rounded-lg"
              style={{ background: 'color-mix(in srgb, var(--accent) 15%, transparent)' }}
            >
              <Send className="h-4 w-4" style={{ color: 'var(--accent)' }} />
            </div>
            <div>
              <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                Draft Outreach
              </h2>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                AI-generated personalized email for {lead.sender_name || lead.sender_email}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-8 h-8 rounded-lg transition-colors"
            style={{ color: 'var(--text-muted)' }}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <div className="p-6 space-y-4">
            <div className="flex items-center gap-3 mb-4">
              <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
              <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Crafting personalized outreach with Claude...
              </span>
            </div>
            <div className="rounded-lg p-5" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
              <div className="space-y-3">
                <div className="h-4 rounded w-48 animate-pulse" style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)' }} />
                <div className="h-3 rounded w-64 animate-pulse" style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', animationDelay: '0.1s' }} />
                <div className="h-3 rounded w-56 animate-pulse" style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', animationDelay: '0.15s' }} />
                <div className="mt-4 space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-3 rounded animate-pulse" style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', width: `${90 - i * 8}%`, animationDelay: `${0.2 + i * 0.05}s` }} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-6">
            <div className="rounded-lg p-4" style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
              <p className="text-sm text-red-400">Failed to generate email: {error}</p>
            </div>
          </div>
        )}

        {/* Email preview */}
        {data && (
          <div className="p-6 animate-fade-in-up">
            {/* Email envelope */}
            <div
              className="rounded-lg overflow-hidden"
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
            >
              {/* Email header fields */}
              <div className="px-5 py-4 space-y-2" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-16 text-right flex-shrink-0" style={{ color: 'var(--text-muted)' }}>From</span>
                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>Parker Blackburn</span>
                  <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'color-mix(in srgb, var(--accent) 10%, transparent)', color: 'var(--accent)' }}>{mode === 'gitlab' ? 'GitLab' : 'Anthropic'}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-16 text-right flex-shrink-0" style={{ color: 'var(--text-muted)' }}>To</span>
                  <span style={{ color: 'var(--text-primary)' }}>
                    {lead.sender_name && <span className="font-medium">{lead.sender_name} </span>}
                    <span style={{ color: 'var(--text-secondary)' }}>&lt;{lead.sender_email}&gt;</span>
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-16 text-right flex-shrink-0" style={{ color: 'var(--text-muted)' }}>Subject</span>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{data.subject}</span>
                </div>
              </div>

              {/* Email body */}
              <div className="px-5 py-5">
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                  {data.body}
                </p>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 mt-4">
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 text-xs font-medium rounded-lg px-3 py-2 transition-colors"
                style={{ background: 'color-mix(in srgb, var(--accent) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--accent) 20%, transparent)', color: 'var(--accent)' }}
              >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copied ? 'Copied' : 'Copy to Clipboard'}
              </button>
              <a
                href={gmailUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-medium rounded-lg px-3 py-2 transition-colors"
                style={{ background: 'var(--accent)', color: '#121110' }}
              >
                <Mail className="h-3 w-3" />
                Open in Gmail
              </a>
              <button
                onClick={onRegenerate}
                disabled={loading}
                className="inline-flex items-center gap-1.5 text-xs font-medium rounded-lg px-3 py-2 transition-colors disabled:opacity-50"
                style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              >
                <RefreshCw className="h-3 w-3" />
                Regenerate
              </button>
            </div>

            {/* Follow-up collapsible */}
            <div className="mt-6">
              <button
                onClick={() => setFollowUpOpen(!followUpOpen)}
                className="flex items-center gap-2 w-full text-left text-sm font-medium py-2 transition-colors"
                style={{ color: 'var(--text-secondary)' }}
              >
                {followUpOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                Follow-up if no response (3 days)
              </button>

              {followUpOpen && (
                <div
                  className="rounded-lg overflow-hidden mt-2 animate-fade-in-up"
                  style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                >
                  <div className="px-5 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="w-16 text-right flex-shrink-0" style={{ color: 'var(--text-muted)' }}>Subject</span>
                      <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{data.follow_up_subject}</span>
                    </div>
                  </div>
                  <div className="px-5 py-4">
                    <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                      {data.follow_up_body}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Page component ───────────────────────────────────────────── */

export default function LeadDetailPage() {
  const { email } = useParams<{ email: string }>();
  const [lead, setLead] = useState<Lead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [linkedIn, setLinkedIn] = useState<ContactLinkedIn | null>(null);
  const [linkedInLoading, setLinkedInLoading] = useState(false);
  const [linkedInNotFound, setLinkedInNotFound] = useState(false);
  const [linkedInError, setLinkedInError] = useState<string | null>(null);
  const [research, setResearch] = useState<CompanyResearch | null>(null);

  // Call prep state
  const [callPrepOpen, setCallPrepOpen] = useState(false);
  const [callPrep, setCallPrep] = useState<CallPrep | null>(null);
  const [callPrepLoading, setCallPrepLoading] = useState(false);
  const [callPrepError, setCallPrepError] = useState<string | null>(null);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingPptx, setExportingPptx] = useState(false);

  // Draft email state
  const [draftEmailOpen, setDraftEmailOpen] = useState(false);
  const [draftEmail, setDraftEmail] = useState<DraftEmail | null>(null);
  const [draftEmailLoading, setDraftEmailLoading] = useState(false);
  const [draftEmailError, setDraftEmailError] = useState<string | null>(null);

  useEffect(() => {
    if (!email) return;
    const decoded = decodeURIComponent(email);
    fetchLead(decoded).then(setLead).catch((e) => setError(e.message));
    fetchLinkedInProfile(decoded)
      .then((profile) => {
        setLinkedIn(profile);
        setLinkedInNotFound(false);
        setLinkedInError(null);
      })
      .catch((e) => {
        if (e instanceof Error && e.message.startsWith('404')) {
          setLinkedInNotFound(true);
        } else {
          setLinkedInError('unavailable');
        }
      });
  }, [email]);

  useEffect(() => {
    if (!lead) return;
    fetchResearch()
      .then((companies) => {
        const match = companies.find(
          (c) =>
            (lead.company_domain && c.company_domain === lead.company_domain) ||
            (lead.company_name &&
              c.company_name?.toLowerCase() === lead.company_name?.toLowerCase()),
        );
        if (match) setResearch(match);
      })
      .catch(() => {});
  }, [lead?.company_domain, lead?.company_name]);

  const employeeEstimate = useMemo(() => {
    const fromResearch = parseEmployeeRange(research?.employee_range ?? null);
    if (fromResearch) return fromResearch;

    const tierMap: Record<string, number> = {
      enterprise_strategic: 2500,
      enterprise: 1000,
      mid_market: 300,
      growth: 150,
      smb: 50,
    };
    return tierMap[lead?.deal_size_tier || ''] || 500;
  }, [research, lead?.deal_size_tier]);

  const handleSearchLinkedIn = async () => {
    if (!email) return;
    setLinkedInLoading(true);
    setLinkedInError(null);
    try {
      const job = await searchLinkedIn(decodeURIComponent(email));
      let pollCount = 0;
      const poll = setInterval(async () => {
        pollCount++;
        if (pollCount > 60) {
          clearInterval(poll);
          setLinkedInLoading(false);
          setLinkedInError('unavailable');
          return;
        }
        try {
          const status = await fetchLinkedInSearchStatus(job.id);
          if (status.status !== 'running') {
            clearInterval(poll);
            setLinkedInLoading(false);
            if (status.status === 'completed') {
              const profile = await fetchLinkedInProfile(decodeURIComponent(email));
              setLinkedIn(profile);
              setLinkedInNotFound(false);
            } else {
              setLinkedInError('unavailable');
            }
          }
        } catch {
          clearInterval(poll);
          setLinkedInLoading(false);
          setLinkedInError('unavailable');
        }
      }, 2000);
    } catch {
      setLinkedInLoading(false);
      setLinkedInError('unavailable');
    }
  };

  const handleCallPrep = async () => {
    if (!email) return;
    setCallPrepOpen(true);
    setCallPrepLoading(true);
    setCallPrepError(null);
    setCallPrep(null);
    try {
      const result = await generateCallPrep(decodeURIComponent(email));
      setCallPrep(result);
    } catch (e) {
      setCallPrepError(e instanceof Error ? e.message : 'Failed to generate');
    } finally {
      setCallPrepLoading(false);
    }
  };

  const handleExportPdf = async () => {
    if (!email || !callPrep) return;
    setExportingPdf(true);
    try {
      await downloadCallPrepPdf(decodeURIComponent(email), callPrep);
    } catch (e) {
      console.error('PDF export failed:', e);
    } finally {
      setExportingPdf(false);
    }
  };

  const handleExportPptx = async () => {
    if (!email || !callPrep) return;
    setExportingPptx(true);
    try {
      await downloadCallPrepPptx(decodeURIComponent(email), callPrep);
    } catch (e) {
      console.error('PPTX export failed:', e);
    } finally {
      setExportingPptx(false);
    }
  };

  const handleDraftEmail = async () => {
    if (!email) return;
    setDraftEmailOpen(true);
    setDraftEmailLoading(true);
    setDraftEmailError(null);
    setDraftEmail(null);
    try {
      const result = await generateDraftEmail(decodeURIComponent(email));
      setDraftEmail(result);
    } catch (e) {
      setDraftEmailError(e instanceof Error ? e.message : 'Failed to generate');
    } finally {
      setDraftEmailLoading(false);
    }
  };

  // Lock body scroll when modal is open
  useEffect(() => {
    if (callPrepOpen || draftEmailOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [callPrepOpen, draftEmailOpen]);

  if (error) return <div className="text-red-400 p-4">Error: {error}</div>;
  if (!lead) return <div className="p-4" style={{ color: 'var(--text-muted)' }}>Loading...</div>;

  const calendarUrl = buildCalendarUrl(lead);

  return (
    <div className="max-w-5xl mx-auto">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm mb-4 transition-colors"
        style={{ color: 'var(--text-muted)' }}
        onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; }}
      >
        <ArrowLeft className="h-4 w-4" /> Back to dashboard
      </Link>

      {/* Header */}
      <div className="rounded-lg p-6 mb-4 animate-fade-in-up" style={cardStyle}>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <GradeBadge grade={lead.grade} size="lg" />
              <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{lead.company_name || 'Unknown Company'}</h1>
              <span className="text-lg font-mono" style={{ color: 'var(--text-secondary)' }}>{lead.score}/100</span>
            </div>
            <div className="flex items-center gap-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
              <span className="inline-flex items-center gap-1"><User className="h-4 w-4" /> {lead.sender_name || lead.sender_email}</span>
              {lead.sender_title && <span>{lead.sender_title}</span>}
              <span className="inline-flex items-center gap-1"><Mail className="h-4 w-4" /> {lead.sender_email}</span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="text-right">
              <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{formatAcv(lead.estimated_acv)}</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{formatLabel(lead.deal_size_tier)} ACV</div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDraftEmail}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors shadow-sm"
                style={{
                  background: 'color-mix(in srgb, var(--accent) 12%, transparent)',
                  border: '1px solid color-mix(in srgb, var(--accent) 25%, transparent)',
                  color: 'var(--accent)',
                  boxShadow: '0 2px 8px color-mix(in srgb, var(--accent) 10%, transparent)',
                }}
              >
                <Send className="h-4 w-4" />
                Draft Outreach
              </button>
              <button
                onClick={handleCallPrep}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors shadow-sm"
                style={{
                  background: 'color-mix(in srgb, var(--accent) 12%, transparent)',
                  border: '1px solid color-mix(in srgb, var(--accent) 25%, transparent)',
                  color: 'var(--accent)',
                  boxShadow: '0 2px 8px color-mix(in srgb, var(--accent) 10%, transparent)',
                }}
              >
                <Zap className="h-4 w-4" />
                Prepare for Call
              </button>
              <a
                href={calendarUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors shadow-sm"
                style={{ background: 'var(--accent)', color: '#121110', boxShadow: '0 2px 8px color-mix(in srgb, var(--accent) 30%, transparent)' }}
              >
                <Calendar className="h-4 w-4" />
                Schedule Call
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Call Prep Modal */}
      {callPrepOpen && (
        <CallPrepModal
          data={callPrep}
          loading={callPrepLoading}
          error={callPrepError}
          onClose={() => setCallPrepOpen(false)}
          onExportPdf={handleExportPdf}
          onExportPptx={handleExportPptx}
          exportingPdf={exportingPdf}
          exportingPptx={exportingPptx}
          companyName={lead.company_name || 'Prospect'}
        />
      )}

      {/* Draft Email Modal */}
      {draftEmailOpen && (
        <DraftEmailModal
          data={draftEmail}
          loading={draftEmailLoading}
          error={draftEmailError}
          onClose={() => setDraftEmailOpen(false)}
          onRegenerate={handleDraftEmail}
          lead={lead}
        />
      )}

      {/* LinkedIn Profile */}
      <div className="rounded-lg p-4 mb-4 animate-fade-in-up stagger-1" style={cardStyle}>
        <h2 className="text-sm font-semibold mb-3 flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
          <Linkedin className="h-4 w-4 text-blue-400" /> LinkedIn Profile
        </h2>
        {linkedInLoading ? (
          <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            <Loader2 className="h-4 w-4 animate-spin" /> Searching LinkedIn...
            <div className="flex-1 space-y-2 ml-4">
              <div className="h-4 rounded animate-pulse w-48" style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)' }} />
              <div className="h-3 rounded animate-pulse w-64" style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)' }} />
              <div className="h-3 rounded animate-pulse w-40" style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)' }} />
            </div>
          </div>
        ) : linkedIn ? (
          <div className="flex gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{linkedIn.full_name}</span>
                {linkedIn.linkedin_url && (
                  <a
                    href={linkedIn.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded"
                    style={{ background: 'rgba(96, 165, 250, 0.1)', color: '#60a5fa' }}
                  >
                    <ExternalLink className="h-3 w-3" /> View Profile
                  </a>
                )}
              </div>
              {linkedIn.headline && (
                <p className="text-sm mb-1" style={{ color: 'var(--text-secondary)' }}>{linkedIn.headline}</p>
              )}
              <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                {linkedIn.current_title && (
                  <span className="inline-flex items-center gap-1">
                    <Briefcase className="h-3 w-3" /> {linkedIn.current_title}
                    {linkedIn.current_company && ` at ${linkedIn.current_company}`}
                  </span>
                )}
                {linkedIn.location && (
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="h-3 w-3" /> {linkedIn.location}
                  </span>
                )}
              </div>
              {linkedIn.summary && (
                <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>{linkedIn.summary}</p>
              )}
            </div>
            {linkedIn.experience_json && linkedIn.experience_json.length > 0 && (
              <div className="w-64 pl-4" style={{ borderLeft: '1px solid var(--border)' }}>
                <h3 className="text-xs font-semibold uppercase mb-2" style={{ color: 'var(--text-muted)' }}>Experience</h3>
                <div className="space-y-2">
                  {linkedIn.experience_json.slice(0, 3).map((exp, i) => (
                    <div key={i} className="text-xs">
                      <div className="font-medium" style={{ color: 'var(--text-primary)' }}>{exp.title}</div>
                      <div style={{ color: 'var(--text-muted)' }}>{exp.company}{exp.duration ? ` · ${exp.duration}` : ''}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : linkedInError ? (
          <div
            className="flex items-center justify-between rounded-lg px-4 py-3"
            style={{ background: 'color-mix(in srgb, var(--text-primary) 4%, transparent)', border: '1px solid var(--border)' }}
          >
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>LinkedIn profile lookup unavailable</span>
            <button
              onClick={() => {
                if (!email) return;
                setLinkedInError(null);
                setLinkedInLoading(true);
                fetchLinkedInProfile(decodeURIComponent(email))
                  .then((profile) => {
                    setLinkedIn(profile);
                    setLinkedInNotFound(false);
                    setLinkedInError(null);
                    setLinkedInLoading(false);
                  })
                  .catch(() => {
                    setLinkedInError('unavailable');
                    setLinkedInLoading(false);
                  });
              }}
              className="inline-flex items-center gap-1.5 text-xs font-medium rounded-md px-2.5 py-1.5 transition-colors"
              style={{ background: 'color-mix(in srgb, var(--text-primary) 6%, transparent)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            >
              <RefreshCw className="h-3 w-3" /> Retry
            </button>
          </div>
        ) : linkedInNotFound ? (
          <div>
            <button
              onClick={handleSearchLinkedIn}
              className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded font-semibold transition-colors"
              style={{ background: 'var(--accent)', color: '#121110' }}
            >
              <Search className="h-4 w-4" /> Search LinkedIn
            </button>
          </div>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Scoring Breakdown */}
        <div className="rounded-lg p-4 animate-fade-in-up stagger-2" style={cardStyle}>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>Scoring Breakdown</h2>
          <div className="space-y-2">
            <ScoreBar label="Intent" value={lead.intent_score} max={30} />
            <ScoreBar label="Domain Quality" value={lead.domain_quality_score} max={25} />
            <ScoreBar label="Urgency" value={lead.urgency_score} max={20} />
            <ScoreBar label="Content Depth" value={lead.content_depth_score} max={15} />
            <ScoreBar label="Authority" value={lead.authority_score} max={10} />
          </div>
        </div>

        {/* Classification */}
        <div className="rounded-lg p-4 animate-fade-in-up stagger-3" style={cardStyle}>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>Classification</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span style={{ color: 'var(--text-muted)' }}>Intent:</span> <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{formatLabel(lead.intent)}</span></div>
            <div><span style={{ color: 'var(--text-muted)' }}>Use Case:</span> <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{formatLabel(lead.use_case)}</span></div>
            <div><span style={{ color: 'var(--text-muted)' }}>Product Fit:</span> <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{formatLabel(lead.product_line_fit)}</span></div>
            <div><span style={{ color: 'var(--text-muted)' }}>Buying Stage:</span> <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{formatLabel(lead.buying_stage)}</span></div>
            <div><span style={{ color: 'var(--text-muted)' }}>AI Provider:</span> <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{lead.current_ai_provider || 'Unknown'}</span></div>
            <div><span style={{ color: 'var(--text-muted)' }}>TAM:</span> <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{lead.tam_estimate || '--'}</span></div>
          </div>
          {lead.expansion_potential && (
            <div className="mt-3 text-sm">
              <span style={{ color: 'var(--text-muted)' }}>Expansion:</span> <span style={{ color: 'var(--text-primary)' }}>{lead.expansion_potential}</span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* MEDDPICC */}
        <div className="rounded-lg p-4 animate-fade-in-up stagger-4" style={cardStyle}>
          <h2 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>MEDDPICC</h2>
          <MeddpiccBadge meddpicc={lead.meddpicc_json} />
        </div>

        {/* Next Action & Discovery */}
        <div className="rounded-lg p-4 animate-fade-in-up stagger-5" style={cardStyle}>
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
            <Target className="h-4 w-4" /> Next Best Action
          </h2>
          <p
            className="text-sm rounded p-3 mb-4"
            style={{ background: 'color-mix(in srgb, var(--accent) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--accent) 15%, transparent)', color: 'var(--text-primary)' }}
          >
            {lead.next_best_action}
          </p>

          <h2 className="text-sm font-semibold mb-2 flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
            <Lightbulb className="h-4 w-4" /> Discovery Questions
          </h2>
          <ul className="space-y-1">
            {(lead.discovery_questions_json || []).map((q, i) => (
              <li key={i} className="text-sm" style={{ color: 'var(--text-secondary)' }}>&bull; {q}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Competitive & Partnership */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="rounded-lg p-4 animate-fade-in-up stagger-6" style={cardStyle}>
          <h2 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>Competitive Signals</h2>
          {(lead.competitive_signals_json || []).length > 0
            ? <ul className="space-y-1">{lead.competitive_signals_json.map((s, i) => <li key={i} className="text-sm" style={{ color: 'var(--text-secondary)' }}>&bull; {s}</li>)}</ul>
            : <p className="text-sm" style={{ color: 'var(--text-muted)' }}>None detected</p>
          }
        </div>
        <div className="rounded-lg p-4 animate-fade-in-up stagger-7" style={cardStyle}>
          <h2 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>Partnership</h2>
          <div className="mb-2">
            <span className="text-xs uppercase" style={{ color: 'var(--text-muted)' }}>Synergies</span>
            {(lead.partnership_synergies_json || []).map((s, i) => <p key={i} className="text-sm text-emerald-400">+ {s}</p>)}
          </div>
          <div>
            <span className="text-xs uppercase" style={{ color: 'var(--text-muted)' }}>Detractors</span>
            {(lead.partnership_detractors_json || []).map((s, i) => <p key={i} className="text-sm text-red-400">- {s}</p>)}
          </div>
        </div>
      </div>

      {/* Competitive Battle Card */}
      <div className="rounded-xl p-5 mb-4 animate-fade-in-up stagger-8" style={cardStyle}>
        <h2 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          <Swords className="h-4 w-4" style={{ color: 'var(--accent)' }} />
          Competitive Battle Card
          {lead.current_ai_provider && (
            <span className="ml-2 text-xs font-normal px-2 py-0.5 rounded-full" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171' }}>
              vs {lead.current_ai_provider}
            </span>
          )}
        </h2>
        <div className="grid grid-cols-3 gap-4">
          {/* Their Weakness */}
          <div className="rounded-lg p-4" style={{ background: 'rgba(239, 68, 68, 0.06)', border: '1px solid rgba(239, 68, 68, 0.15)' }}>
            <h3 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: '#f87171' }}>Their Weakness</h3>
            <ul className="space-y-2">
              {(lead.competitive_signals_json || []).map((s, i) => (
                <li key={i} className="text-sm flex items-start gap-2" style={{ color: 'var(--text-secondary)' }}>
                  <AlertTriangle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" style={{ color: '#f87171' }} />
                  {s}
                </li>
              ))}
              {/openai|gpt-?4/i.test(lead.current_ai_provider || '') && (
                <li className="text-sm flex items-start gap-2" style={{ color: 'var(--text-secondary)' }}>
                  <AlertTriangle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" style={{ color: '#f87171' }} />
                  General-purpose model not optimized for domain-specific reasoning
                </li>
              )}
              {(lead.competitive_signals_json || []).length === 0 && !/openai|gpt-?4/i.test(lead.current_ai_provider || '') && (
                <li className="text-sm" style={{ color: 'var(--text-muted)' }}>No signals detected</li>
              )}
            </ul>
          </div>
          {/* Our Strength */}
          <div className="rounded-lg p-4" style={{ background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.15)' }}>
            <h3 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: '#34d399' }}>Our Strength</h3>
            <ul className="space-y-2">
              {[
                'Constitutional AI designed for accuracy and safety',
                'Superior performance on complex reasoning tasks',
                'Enterprise-grade security with SSO and compliance controls',
                'Dedicated migration support from competing providers',
              ].map((s, i) => (
                <li key={i} className="text-sm flex items-start gap-2" style={{ color: 'var(--text-secondary)' }}>
                  <Shield className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" style={{ color: '#34d399' }} />
                  {s}
                </li>
              ))}
            </ul>
          </div>
          {/* How to Win */}
          <div className="rounded-lg p-4" style={{ background: 'color-mix(in srgb, var(--accent) 6%, transparent)', border: '1px solid color-mix(in srgb, var(--accent) 15%, transparent)' }}>
            <h3 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--accent)' }}>How to Win</h3>
            <ul className="space-y-2">
              {(lead.partnership_synergies_json || []).slice(0, 2).map((s, i) => (
                <li key={i} className="text-sm flex items-start gap-2" style={{ color: 'var(--text-secondary)' }}>
                  <Rocket className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" style={{ color: 'var(--accent)' }} />
                  {s}
                </li>
              ))}
              <li className="text-sm flex items-start gap-2" style={{ color: 'var(--text-secondary)' }}>
                <Rocket className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" style={{ color: 'var(--accent)' }} />
                Propose rapid proof-of-concept on their highest-risk use case
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Reasoning */}
      <div className="rounded-lg p-4 mb-4 animate-fade-in-up stagger-9" style={cardStyle}>
        <h2 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>Scoring Reasoning</h2>
        <p className="text-sm whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>{lead.last_reasoning}</p>
      </div>

      {/* Email History */}
      {lead.emails && lead.emails.length > 0 && (
        <div className="rounded-lg p-4 mb-4 animate-fade-in-up stagger-9" style={cardStyle}>
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
            <Mail className="h-4 w-4" /> Email History ({lead.emails.length})
          </h2>
          <div className="space-y-3">
            {lead.emails.map((e) => (
              <div key={e.email_id} className="rounded p-3" style={{ border: '1px solid var(--border)' }}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{e.subject}</span>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{new Date(e.received_at).toLocaleDateString()}</span>
                </div>
                <p className="text-xs whitespace-pre-wrap line-clamp-4" style={{ color: 'var(--text-secondary)' }}>{e.body}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Feature 1: Org Power Map ──────────────────────────────── */}
      <OrgPowerMap
        senderName={lead.sender_name}
        senderTitle={lead.sender_title}
        companyName={lead.company_name}
      />

      {/* ── Feature 2: Department Heat Map ────────────────────────── */}
      <DepartmentHeatMap
        employeeEstimate={employeeEstimate}
        companyName={lead.company_name}
      />
    </div>
  );
}
