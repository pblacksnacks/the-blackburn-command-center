# Gmail Pipeline Scanner — Installation

## Prerequisites

- Python 3.11+
- Anthropic API key
- Gmail MCP server connected to Claude Cowork

## Step 1: Environment Setup

Ensure your `.env` file in the project root has your API key:

```
ANTHROPIC_API_KEY=your-key-here
```

## Step 2: Install Dependencies

From the project root:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

All dependencies are shared with the main Command Center — no additional packages required.

## Step 3: Connect Gmail MCP

In your Claude Cowork workspace, connect the Gmail MCP server with read access to the inbox you want to monitor.

The plugin uses these Gmail MCP calls:
- `gmail_search_messages` — Find new emails since last scan
- `gmail_read_message` — Read full email content for scoring

## Step 4: Verify Installation

```bash
# Should print help text with no errors
python cowork/gmail_scanner.py --help

# Generate a briefing from existing DB data (no Gmail needed)
python cowork/gmail_scanner.py --briefing-only

# Full standalone run (prints "no new emails" without Gmail MCP)
python cowork/gmail_scanner.py
```

## Step 5: Enable Daily Schedule

The plugin's skill definition (`cowork/SKILL.md`) configures a daily 7 AM Pacific schedule. Tell Cowork:

> "update pipeline"

Cowork will scan Gmail, run the three agents, and report results.

## GitLab Mode

To run against GitLab product context:

```bash
TRIAGE_DB="triage_gitlab.db" GITLAB_MODE="true" python cowork/gmail_scanner.py --briefing-only
```

## CLI Reference

| Command | What It Does |
|---------|--------------|
| `python cowork/gmail_scanner.py` | Full pipeline (intake + research + briefing) |
| `python cowork/gmail_scanner.py --scan-only` | Intake + research only |
| `python cowork/gmail_scanner.py --briefing-only` | Briefing from existing DB data |

## Troubleshooting

**"ANTHROPIC_API_KEY not found"** — Add your key to `.env` in the project root.

**"No leads found for today's briefing"** — Run a full pipeline or `--demo` first to populate the database, then try `--briefing-only`.

**Import errors** — Make sure you're running from the project root and the virtual environment is activated.
