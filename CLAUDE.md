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

# Anthropic instance (FastAPI on :8000 + Vite on :5173)
./run-dev.sh

# GitLab instance (FastAPI on :8001 + Vite on :5174, separate DB)
./run-gitlab.sh
# Initialize GitLab demo data first:
./run-gitlab.sh init

# Tests (mock API calls — no real Claude usage)
pytest tests/
pytest tests/test_intake_agent.py  # single file

# Frontend lint
cd web && npm run lint

# Backfill MEDDPICC scores for existing leads
python scripts/backfill_meddpicc.py --write
```

**Setup:** Create `.env` with `ANTHROPIC_API_KEY=...` before running anything.

## Architecture

Three-agent pipeline backed by a full-stack web dashboard with dual-mode branding (Anthropic / GitLab):

```
Gmail Inbox → Intake Agent → SQLite DB → Research Agent → Briefing Agent
                                 ↕
                         FastAPI (server/) ← React/Vite (web/)
```

**Dual Mode:** Set `GITLAB_MODE=true` to switch all user-facing surfaces to GitLab branding (purple/orange theme, GitLab product names, GitLab-specific slide decks). The `/api/config` endpoint exposes the current mode. The frontend reads this on load and sets `[data-theme="gitlab"]` on `<html>`.

**Agents** (`agents/`): All agents are standalone classes; `main.py` wires them together. They use the Anthropic SDK with tool use for structured output.

| Agent | File | Output |
|-------|------|--------|
| Intake | `agents/intake_agent.py` | Classifies intent, scores 1–100, extracts MEDDPICC |
| Research | `agents/research_agent.py` | Web search → company enrichment |
| Briefing | `agents/briefing_agent.py` | Daily `.md` report + `.pptx` deck |
| LinkedIn | `agents/linkedin_agent.py` | Web search → contact LinkedIn profile enrichment |

**Supporting modules:**
- `agents/lead_scorer.py` — 100-point scoring rubric (see below); contains `RawEmail` and `ScoringResult` Pydantic models
- `agents/report_formatter.py` — Markdown + python-pptx output
- `server/db.py` — SQLite CRUD helpers shared by all agents and the API

**Backend** (`server/`): FastAPI app. Key routes:
- `/api/leads`, `/api/leads/{email}` — Lead CRUD and detail
- `/api/leads/{email}/call-prep` — AI-generated discovery call brief (Claude tool use)
- `/api/leads/{email}/call-prep-pdf`, `/api/leads/{email}/call-prep-pptx` — Export call prep as PDF/PPTX
- `/api/leads/{email}/draft-email` — AI-generated personalized outreach email
- `/api/research` — Company research data
- `/api/linkedin`, `/api/linkedin/search` — LinkedIn profile enrichment
- `/api/briefings` — Daily briefing reports
- `/api/pipeline/run`, `/api/pipeline/status/{id}` — Pipeline execution (background thread + polling)
- `/api/config` — Returns `{"mode": "anthropic" | "gitlab"}`

**Frontend** (`web/`): React 19 + Vite + Tailwind CSS. Pages: Dashboard, LeadDetail, Research, Briefings. Uses `web/src/api.ts` for all backend calls. Vite proxies `/api/*` to the backend port. Theme-aware via CSS custom properties and `ModeContext`.

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
- SQLite for local dev (`triage.db` for Anthropic, `triage_gitlab.db` for GitLab); schema (`schema.sql`) is Postgres-compatible
- Demo data: `demo_data/anthropic.json` and `demo_data/gitlab.json`; `--demo` clears the DB before each full run
- Tests mock the Claude API — no real API calls in `pytest`
- `reports/` and `data/` are gitignored; they're created at runtime
- PPTX decks use `fpdf2` for PDF and `python-pptx` for PowerPoint generation
