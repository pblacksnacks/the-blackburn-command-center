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
  meddpicc_json: Record<string, string>;
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
