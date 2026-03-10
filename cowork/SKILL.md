# Blackburn Command Center — Cowork Skill

You are the operator for the **Blackburn Command Center**, an AI-powered sales intelligence pipeline that scores, researches, and preps discovery calls for inbound leads.

## Schedule

Run **daily at 7:00 AM Pacific**:
> update pipeline

## Commands

| Command | What It Does | Pipeline Stages |
|---------|--------------|-----------------|
| `update pipeline` | Full daily update — scan inbox, score leads, research companies, generate briefing | Intake → Research → Briefing |
| `scan inbox` | Scan Gmail for new emails, score and research them (no briefing) | Intake → Research |
| `generate briefing` | Generate today's executive briefing from existing DB data | Briefing only |
| `prepare for call with [company]` | Generate a discovery call prep brief for a specific company | Call Prep (via API) |
| `draft outreach to [company]` | Draft a personalized outreach email for a specific lead | Draft Email (via API) |

## How to Run the Pipeline

### Step 1: Scan Gmail for New Emails

Use the Gmail MCP to fetch recent emails:

```
gmail_search_messages(query="is:inbox newer_than:1d")
```

For each message returned, read the full content:

```
gmail_read_message(message_id=<id>)
```

### Step 2: Run the Pipeline

Execute the scanner script with the fetched emails mapped to RawEmail format:

```python
from cowork.gmail_scanner import run_pipeline_update, RawEmail

emails = [
    RawEmail(
        email_id=msg["id"],
        sender_email=msg["from"],
        sender_name=parse_name(msg["from"]),
        subject=msg["subject"],
        body=msg["body"],
        received_at=msg["date"],
    )
    for msg in fetched_messages
]

summary = run_pipeline_update(emails=emails)
```

Or via CLI:

```bash
python cowork/gmail_scanner.py                  # Full update
python cowork/gmail_scanner.py --scan-only      # Intake + research only
python cowork/gmail_scanner.py --briefing-only  # Briefing from existing data
```

### Step 3: Report Results

After the pipeline runs, summarize:
- How many new emails were processed
- How many new leads were created (with grades)
- How many companies were researched
- Whether a briefing was generated
- Any A-grade leads that need immediate attention

## Daily Workflow

1. **7:00 AM** — Scan Gmail inbox for new messages from the last 24 hours
2. **Intake** — Score and classify each email (intent, MEDDPICC, ACV, buying stage)
3. **Research** — Enrich new companies via web search (funding, headcount, news)
4. **Briefing** — Generate executive summary with ranked leads, pipeline value, and action items
5. **Report** — Surface the briefing and flag any urgent leads

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
                                        (triage.db)
```

## Prerequisites

### Gmail MCP Connection

The Gmail MCP server must be connected to Claude Cowork with read access to the inbox being monitored.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | API key for Claude (scoring, research, briefing) |
| `TRIAGE_DB` | No | `triage.db` | Path to SQLite database |
| `GITLAB_MODE` | No | `false` | Set to `true` for GitLab product context |

### Key Behaviors

- **Incremental** — Never clears the database. New emails are appended; duplicates are skipped via `email_seen()`.
- **Idempotent** — Safe to run multiple times. Already-processed emails are detected by `email_id`.
- **Dual-mode** — Set `GITLAB_MODE=true` to switch all scoring, research, and briefing to GitLab product context.
