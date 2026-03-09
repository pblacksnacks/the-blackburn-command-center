const BASE = '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export interface MeddpiccDimension {
  status: 'known' | 'partial' | 'unknown';
  evidence: string;
  gap: string;
  question: string;
}

export interface Lead {
  id: number;
  sender_email: string;
  sender_name: string | null;
  sender_title: string | null;
  company_name: string | null;
  company_domain: string | null;
  intent: string;
  score: number;
  grade: string;
  intent_score: number;
  domain_quality_score: number;
  urgency_score: number;
  content_depth_score: number;
  authority_score: number;
  use_case: string;
  product_line_fit: string;
  buying_stage: string;
  current_ai_provider: string | null;
  competitive_signals_json: string[];
  estimated_acv: number | null;
  deal_size_tier: string;
  tam_estimate: string | null;
  expansion_potential: string | null;
  meddpicc_json: Record<string, MeddpiccDimension>;
  discovery_questions_json: string[];
  next_best_action: string;
  partnership_synergies_json: string[];
  partnership_detractors_json: string[];
  last_reasoning: string;
  email_count: number;
  first_seen_at: string;
  last_seen_at: string;
  emails?: EmailLog[];
}

export interface EmailLog {
  id: number;
  email_id: string;
  sender_email: string;
  subject: string;
  body: string;
  received_at: string;
  score: number;
  grade: string;
  result_json: Record<string, unknown>;
}

export interface LeadStats {
  total: number;
  grades: Record<string, number>;
  total_pipeline_acv: number;
}

export interface CompanyResearch {
  company_key: string;
  company_name: string;
  company_domain: string | null;
  description: string | null;
  employee_range: string | null;
  funding_stage: string | null;
  recent_news_json: Array<{ title: string; summary: string; url?: string }>;
  source_urls_json: string[];
  researched_at: string | null;
}

export interface Briefing {
  id: number;
  briefing_date: string;
  markdown_body?: string;
  summary_json: Record<string, unknown>;
  pptx_path: string | null;
  created_at: string;
}

export interface PipelineJob {
  id: string;
  stage: string;
  demo: boolean;
  status: 'running' | 'completed' | 'failed';
  started_at: number;
  finished_at: number | null;
  error: string | null;
}

export interface ContactLinkedIn {
  id: number;
  sender_email: string;
  company_key: string | null;
  full_name: string | null;
  linkedin_url: string | null;
  headline: string | null;
  location: string | null;
  current_title: string | null;
  current_company: string | null;
  summary: string | null;
  experience_json: Array<{ title: string; company: string; duration?: string }>;
  source_urls_json: string[];
  searched_at: string | null;
  updated_at: string;
}

export interface LinkedInSearchJob {
  id: string;
  sender_email: string;
  status: 'running' | 'completed' | 'failed';
  started_at: number;
  finished_at: number | null;
  error: string | null;
}

export const fetchLinkedInProfiles = () => get<ContactLinkedIn[]>('/linkedin');
export const fetchLinkedInProfile = (email: string) =>
  get<ContactLinkedIn>(`/linkedin/${encodeURIComponent(email)}`);
export const searchLinkedIn = (senderEmail: string) =>
  post<LinkedInSearchJob>('/linkedin/search', { sender_email: senderEmail });
export const fetchLinkedInSearchStatus = (jobId: string) =>
  get<LinkedInSearchJob>(`/linkedin/search/status/${jobId}`);

export const fetchLeads = (params?: Record<string, string>) => {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return get<Lead[]>(`/leads${qs}`);
};
export const fetchLeadStats = () => get<LeadStats>('/leads/stats');
export const fetchLead = (email: string) => get<Lead>(`/leads/${email}`);
export const fetchResearch = () => get<CompanyResearch[]>('/research');
export const fetchResearchOne = (key: string) => get<CompanyResearch>(`/research/${key}`);
export const fetchBriefings = () => get<Briefing[]>('/briefings');
export const fetchBriefing = (date: string) => get<Briefing>(`/briefings/${date}`);
export const runPipeline = (stage: string, demo: boolean) =>
  post<PipelineJob>('/pipeline/run', { stage, demo });
export const fetchPipelineStatus = (jobId: string) =>
  get<PipelineJob>(`/pipeline/status/${jobId}`);

export interface CallPrep {
  contact_summary: string;
  company_snapshot: string;
  why_theyre_here: string;
  current_stack: string;
  suggested_agenda: string[];
  discovery_questions: string[];
  objection_prep: Array<{ objection: string; response: string }>;
  competitive_positioning: string;
  land_strategy: string;
  expand_strategy: string;
  proposed_next_step: string;
  do_not_say: string[];
}

export const generateCallPrep = (email: string) =>
  post<CallPrep>(`/leads/${encodeURIComponent(email)}/call-prep`, {});

export interface DraftEmail {
  subject: string;
  body: string;
  follow_up_subject: string;
  follow_up_body: string;
}

export const generateDraftEmail = (email: string) =>
  post<DraftEmail>(`/leads/${encodeURIComponent(email)}/draft-email`, {});

function toArray(v: unknown): string[] {
  if (Array.isArray(v)) return v.map(String);
  if (typeof v === 'string') return v.split('\n').filter(Boolean);
  return [];
}

function toObjArray(v: unknown): Array<{ objection: string; response: string }> {
  if (Array.isArray(v))
    return v.map((x) =>
      typeof x === 'object' && x !== null
        ? { objection: String((x as Record<string, unknown>).objection ?? ''), response: String((x as Record<string, unknown>).response ?? '') }
        : { objection: String(x), response: '' },
    );
  if (typeof v === 'string')
    return v.split('\n').filter(Boolean).map((s) => ({ objection: s, response: '' }));
  return [];
}

function normalizeCallPrep(data: CallPrep) {
  return {
    ...data,
    suggested_agenda: toArray(data.suggested_agenda),
    discovery_questions: toArray(data.discovery_questions),
    objection_prep: toObjArray(data.objection_prep),
    do_not_say: toArray(data.do_not_say),
  };
}

async function downloadBlob(url: string, body: unknown, filename: string): Promise<void> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(blobUrl);
}

export async function downloadCallPrepPdf(email: string, data: CallPrep): Promise<void> {
  const normalized = normalizeCallPrep(data);
  const slug = email.split('@')[0];
  await downloadBlob(
    `${BASE}/leads/${encodeURIComponent(email)}/call-prep-pdf`,
    normalized,
    `pre-call-brief-${slug}.pdf`,
  );
}

export async function downloadCallPrepPptx(email: string, data: CallPrep): Promise<void> {
  const normalized = normalizeCallPrep(data);
  const slug = email.split('@')[0];
  await downloadBlob(
    `${BASE}/leads/${encodeURIComponent(email)}/call-prep-pptx`,
    normalized,
    `customer-deck-${slug}.pptx`,
  );
}
