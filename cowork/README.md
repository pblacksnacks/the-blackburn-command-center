# Cowork Plugin — Blackburn Command Center

Claude Cowork integration for automated daily inbox scanning and pipeline updates. Bridges the gap between demo mode (`--demo`) and live Gmail processing.

## Setup

1. **Environment** — Ensure `.env` exists in the project root with your API key:
   ```
   ANTHROPIC_API_KEY=your-key-here
   ```

2. **Gmail MCP** — Connect the Gmail MCP server to your Claude Cowork workspace with read access to the target inbox.

3. **Database** — The pipeline uses `triage.db` by default. Set `TRIAGE_DB` to customize:
   ```
   TRIAGE_DB=/path/to/custom.db
   ```

## Usage with Cowork

Tell Cowork any of these commands:

| Command | What Runs | Output |
|---------|-----------|--------|
| "update pipeline" | Intake → Research → Briefing | Full daily update |
| "scan inbox" | Intake → Research | Score + research only |
| "generate briefing" | Briefing only | Report from existing DB |
| "prepare for call with Acme Corp" | Call Prep API | Discovery brief |
| "draft outreach to Acme Corp" | Draft Email API | Personalized email |

### Example Conversation

```
You: update pipeline

Cowork: Scanning Gmail for new emails...
  Found 8 new messages since last scan.

  Running intake agent...
  [A] 87  cto@techcorp.com    Enterprise API integration — active eval, Q2 deadline
  [B] 72  eng@startup.io      Product embedding inquiry — series B, 200 engineers
  [C] 45  info@vendor.com     General partnership inquiry
  ...

  Researching 3 new companies...
  TechCorp — 1200 employees, Series D, $150M raised
  Startup.io — 200 employees, Series B, $40M raised
  Vendor Inc — 50 employees, bootstrapped

  Generating briefing for 2026-03-10...
  Executive Summary: 2 high-priority leads today. TechCorp (A-grade) has an
  active evaluation with Q2 deadline — call within 24 hours. Total pipeline
  value: $450K across 5 qualified opportunities.

  Done — 5 new leads, 3 companies researched.
```

## Standalone CLI

Run directly without Cowork (uses placeholder email fetch):

```bash
# Full pipeline update
python cowork/gmail_scanner.py

# Intake + research only (skip briefing)
python cowork/gmail_scanner.py --scan-only

# Generate briefing from existing DB data
python cowork/gmail_scanner.py --briefing-only
```

### GitLab Mode

```bash
TRIAGE_DB="triage_gitlab.db" GITLAB_MODE="true" python cowork/gmail_scanner.py --briefing-only
```

## Architecture

```
Gmail (MCP) → cowork/gmail_scanner.py → Existing Pipeline Agents
                                              │
                    ┌─────────────────────────┤
                    ▼                         ▼                         ▼
             Intake Agent              Research Agent            Briefing Agent
          (score + classify)       (web search enrich)        (daily report + deck)
                    │                         │                         │
                    └─────────────────────────┤─────────────────────────┘
                                              ▼
                                          SQLite DB
```

### What This Plugin Does

- **`GmailEmailSource`** — Implements the `EmailSource` protocol, accepting pre-fetched emails from Cowork's Gmail MCP
- **`run_pipeline_update()`** — Orchestrates intake → research → briefing without clearing the DB
- **`get_last_scan_timestamp()`** — Queries `email_log` to determine what's already been processed
- **Dedup** — Handled by existing `store.email_seen()` in IntakeAgent

### What This Plugin Does NOT Do

- Modify any existing agents or pipeline code
- Clear the database (unlike `--demo` full mode)
- Require any new Python dependencies

## MCP Servers

| Server | Purpose | Required |
|--------|---------|----------|
| Gmail | Read inbox emails for pipeline processing | Yes |
| SQLite | Direct DB queries (optional, for Cowork inspection) | No |
