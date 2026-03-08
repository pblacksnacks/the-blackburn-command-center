# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Full pipeline with demo data (clears DB, runs all three agents)
python main.py full --demo

# Individual stages
python main.py intake --demo
python main.py research --demo
python main.py briefing --demo

# Full-stack dev server (FastAPI on :8000 + Vite on :5173, opens browser)
./run-dev.sh

# Tests (mock API calls — no real Claude usage)
pytest tests/
pytest tests/test_intake_agent.py  # single file

# Frontend lint
cd web && npm run lint
```

**Setup:** Create `.env` with `ANTHROPIC_API_KEY=...` before running anything.

## Architecture

Three-agent pipeline backed by a full-stack web dashboard:

```
Gmail Inbox → Intake Agent → SQLite DB → Research Agent → Briefing Agent
                                 ↕
                         FastAPI (server/) ← React/Vite (web/)
```

**Agents** (`agents/`): All agents are standalone classes; `main.py` wires them together. They use the Anthropic SDK with tool use for structured output.

| Agent | File | Output |
|-------|------|--------|
| Intake | `agents/intake_agent.py` | Classifies intent, scores 1–100, extracts MEDDPICC |
| Research | `agents/research_agent.py` | Web search → company enrichment |
| Briefing | `agents/briefing_agent.py` | Daily `.md` report + `.pptx` deck |

**Supporting modules:**
- `agents/lead_scorer.py` — 100-point scoring rubric (see below); contains `RawEmail` and `ScoringResult` Pydantic models
- `agents/report_formatter.py` — Markdown + python-pptx output
- `src/db.py` — SQLite CRUD helpers shared by all agents and the API

**Backend** (`server/`): FastAPI app. Routes: `/api/leads`, `/api/research`, `/api/briefings`, `/api/pipeline`. The pipeline route runs agents in a background thread and polls via job ID.

**Frontend** (`web/`): React 19 + Vite + Tailwind CSS. Pages: Dashboard, LeadDetail, Research, Briefings. Uses `web/src/api.ts` for all backend calls. Vite proxies `/api/*` to `:8000`.

## Scoring Rubric (100 pts)

| Dimension | Points |
|-----------|--------|
| Intent Score | 0–30 |
| Domain Quality | 0–25 |
| Urgency Signals | 0–20 |
| Content Depth | 0–15 |
| Sender Authority | 0–10 |

Grades: A = 80–100, B = 60–79, C = 40–59, D = 0–39

## Key Conventions

- Python 3.11+, type hints everywhere
- All agent outputs are structured Pydantic dicts, not raw strings
- SQLite for local dev (`triage.db`); schema (`schema.sql`) is Postgres-compatible
- Demo mode uses hardcoded emails in `main.py` (`DEMO_EMAILS` list); `--demo` also clears the DB before each full run
- Tests mock the Claude API — no real API calls in `pytest`
- `reports/` and `data/` are gitignored; they're created at runtime

## MCP Servers (live mode)

- `gws` — Gmail read access (Intake Agent, not yet wired)
- `sqlite` — Database at `data/triage.db`
- `notebooklm-mcp` — Research notebooks (Research Agent, optional)
