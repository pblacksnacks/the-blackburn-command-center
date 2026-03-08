-- =============================================================================
-- Email Triage Pipeline — Unified Schema (v2)
-- All three agents (intake, research, briefing) share this database.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- INTAKE AGENT tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_email TEXT NOT NULL UNIQUE,
    sender_name TEXT,
    sender_title TEXT,
    company_name TEXT,
    company_domain TEXT,

    -- Core scoring
    intent TEXT NOT NULL CHECK (intent IN ('new_business', 'support', 'partnership', 'spam', 'other')),
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    grade TEXT NOT NULL CHECK (grade IN ('A', 'B', 'C', 'D')),
    intent_score INTEGER NOT NULL CHECK (intent_score BETWEEN 0 AND 30),
    domain_quality_score INTEGER NOT NULL CHECK (domain_quality_score BETWEEN 0 AND 25),
    urgency_score INTEGER NOT NULL CHECK (urgency_score BETWEEN 0 AND 20),
    content_depth_score INTEGER NOT NULL CHECK (content_depth_score BETWEEN 0 AND 15),
    authority_score INTEGER NOT NULL CHECK (authority_score BETWEEN 0 AND 10),

    -- Anthropic-specific
    use_case TEXT CHECK (use_case IN ('internal_productivity', 'product_integration', 'dual_motion', 'unknown')),
    product_line_fit TEXT CHECK (product_line_fit IN ('api', 'claude_ai_seats', 'claude_enterprise', 'multiple', 'unknown')),

    -- Market position
    buying_stage TEXT CHECK (buying_stage IN ('researching', 'evaluating', 'ready_to_buy', 'unknown')),
    current_ai_provider TEXT,
    competitive_signals_json TEXT NOT NULL DEFAULT '[]',

    -- Revenue
    estimated_acv INTEGER,
    deal_size_tier TEXT CHECK (deal_size_tier IN ('enterprise', 'mid_market', 'smb', 'unknown')),
    tam_estimate TEXT,
    expansion_potential TEXT,

    -- MEDDPICC
    meddpicc_json TEXT NOT NULL DEFAULT '{}',
    discovery_questions_json TEXT NOT NULL DEFAULT '[]',
    next_best_action TEXT,

    -- Partnership
    partnership_synergies_json TEXT NOT NULL DEFAULT '[]',
    partnership_detractors_json TEXT NOT NULL DEFAULT '[]',

    -- Metadata
    last_reasoning TEXT,
    notes_json TEXT NOT NULL DEFAULT '[]',
    email_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_email_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_leads_company_domain ON leads(company_domain);
CREATE INDEX IF NOT EXISTS idx_leads_grade ON leads(grade);
CREATE INDEX IF NOT EXISTS idx_leads_last_seen_at ON leads(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_leads_use_case ON leads(use_case);
CREATE INDEX IF NOT EXISTS idx_leads_buying_stage ON leads(buying_stage);

CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT NOT NULL UNIQUE,
    sender_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    received_at TEXT NOT NULL,
    intent TEXT NOT NULL CHECK (intent IN ('new_business', 'support', 'partnership', 'spam', 'other')),
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    grade TEXT NOT NULL CHECK (grade IN ('A', 'B', 'C', 'D')),
    intent_score INTEGER NOT NULL CHECK (intent_score BETWEEN 0 AND 30),
    domain_quality_score INTEGER NOT NULL CHECK (domain_quality_score BETWEEN 0 AND 25),
    urgency_score INTEGER NOT NULL CHECK (urgency_score BETWEEN 0 AND 20),
    content_depth_score INTEGER NOT NULL CHECK (content_depth_score BETWEEN 0 AND 15),
    authority_score INTEGER NOT NULL CHECK (authority_score BETWEEN 0 AND 10),
    rubric_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_email) REFERENCES leads(sender_email)
);

CREATE INDEX IF NOT EXISTS idx_email_log_sender_received_at
    ON email_log(sender_email, received_at);

-- ---------------------------------------------------------------------------
-- RESEARCH AGENT table
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS company_research (
    company_key TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    company_domain TEXT,
    website_url TEXT,
    description TEXT,
    employee_range TEXT,
    employee_count_estimate INTEGER,
    funding_stage TEXT,
    annual_revenue_estimate TEXT,
    linkedin_url TEXT,
    recent_news_json TEXT NOT NULL DEFAULT '[]',
    profile_json TEXT NOT NULL DEFAULT '{}',
    source_urls_json TEXT NOT NULL DEFAULT '[]',
    notebook_id TEXT,
    notebook_url TEXT,
    notebook_summary TEXT,
    researched_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    raw_model_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_company_research_domain
    ON company_research(company_domain);

CREATE INDEX IF NOT EXISTS idx_company_research_researched_at
    ON company_research(researched_at);

-- ---------------------------------------------------------------------------
-- BRIEFING AGENT table
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS daily_briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    briefing_date TEXT NOT NULL UNIQUE,
    markdown_body TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}',
    pptx_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
