# Blackburn Command Center

AI-powered sales intelligence pipeline that automatically scores, researches, and preps discovery calls for inbound leads — so reps spend time selling, not sorting. Built entirely with Claude by a non-developer sales professional.

## What It Does

Takes raw inbound sales emails, runs them through three AI agents, and outputs a prioritized, researched, actionable pipeline in under 60 seconds.

- Scores and classifies inbound leads across 25+ fields including MEDDPICC, ACV, buying stage, competitive signals, and discovery questions
- Researches companies via Claude web search — funding, headcount, tech stack, recent news, LinkedIn profiles
- Generates call prep briefs with meeting agendas, objection handling, competitive positioning, and deal strategy
- Exports deliverables — internal pre-call brief and customer-facing slide deck (PPTX) with full speaker notes
- Drafts outreach emails — personalized first-touch and follow-up with one-click Gmail integration
- Visualizes account intelligence — org power maps, department revenue heat maps, competitive battle cards

## Architecture

```
Gmail Inbox → Intake Agent → SQLite DB → Research Agent → Briefing Agent
                                 ↕
                         FastAPI (server/) ← React/Vite (web/)
```

Three agents, sequential pipeline:

| Agent | File | What It Does |
|-------|------|--------------|
| Intake | `agents/intake_agent.py` | Scores 0-100, classifies intent, MEDDPICC, ACV, buying stage |
| Research | `agents/research_agent.py` | Web search → company enrichment via Claude web_search tool |
| Briefing | `agents/briefing_agent.py` | Daily executive briefing → Markdown + PPTX |

## Dual-Mode Pipeline

The system supports two independent instances running simultaneously:

| Instance | Database | Backend | Frontend | Demo Data |
|----------|----------|---------|----------|-----------|
| Anthropic | `triage.db` | Port 8000 | Port 5173 | 15 SF high-tech companies |
| GitLab | `triage_gitlab.db` | Port 8001 | Port 5174 | 15 Colorado high-tech companies |

Same codebase, same scoring engine, different product context — proving the tool works for any sales organization.

## Quick Start

```bash
git clone https://github.com/pblacksnacks/the-blackburn-command-center.git
cd the-blackburn-command-center
cp .env.example .env                                       # add your ANTHROPIC_API_KEY
cp demo_data/anthropic.example.json demo_data/anthropic.json  # add your own lead data
cp demo_data/gitlab.example.json demo_data/gitlab.json        # add your own lead data
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py full --demo
venv/bin/uvicorn server.app:app --reload --port 8000
cd web && npm install && npm run dev
open http://localhost:5173
```

### GitLab Mode

```bash
TRIAGE_DB="triage_gitlab.db" GITLAB_MODE="true" python main.py full --demo
TRIAGE_DB="triage_gitlab.db" GITLAB_MODE="true" venv/bin/uvicorn server.app:app --reload --port 8001
cd web && VITE_API_PORT=8001 npm run dev -- --port 5174
```

## Scoring Rubric (100 pts)

| Dimension | Points | Why |
|-----------|--------|-----|
| Intent Score | 0-30 | Strongest predictor of close |
| Domain Quality | 0-25 | Company tier filtering |
| Urgency Signals | 0-20 | Timeline, budget, competitive mentions |
| Content Depth | 0-15 | Detail correlates with seriousness |
| Sender Authority | 0-10 | Decision-makers close faster |

Grades: A = 80-100, B = 60-79, C = 40-59, D = 0-39

## Features

1. **AI Lead Scoring** — 100-point rubric with 5 dimensions, grade A-D
2. **MEDDPICC Qualification** — per-dimension status with evidence, gaps, and discovery questions
3. **Competitive Battle Cards** — Their Weakness / Our Strength / How to Win
4. **AI Call Prep Briefs** — full discovery call prep with objections, competitive positioning, agenda
5. **Pre-Call Brief PDF** — dense two-page landscape PDF (internal AE use)
6. **Customer Deck PPTX** — branded slide deck with speaker notes (customer-facing)
7. **Draft Outreach Email** — AI-generated email with Gmail integration
8. **Org Power Map** — 8-department org chart with entry point highlighting
9. **Department Revenue Heat Map** — Product x Department TAM grid
10. **Company Research** — web search enrichment with news, funding, employee count
11. **LinkedIn Enrichment** — contact profile search via Claude web_search
12. **CRM Sync Indicator** — visual integration readiness on every lead card
13. **Daily Executive Briefings** — AI-generated pipeline summary with ranked leads

## Tech Stack

| Layer | Technology |
|-------|------------|
| AI | Anthropic SDK (Claude Sonnet 4) |
| Backend | FastAPI + Uvicorn |
| Database | SQLite |
| PDF Export | fpdf2 |
| PPTX Export | python-pptx |
| Frontend | React 19 + TypeScript 5.9 |
| Build Tool | Vite 7 |
| CSS | Tailwind CSS v4 |
| Icons | lucide-react |
| Font | DM Sans (Google Fonts) |

## Project Structure

```
├── main.py                          # CLI runner, pipeline orchestrator
├── schema.sql
├── requirements.txt
├── demo_data/
│   ├── anthropic.example.json        # Template — copy to anthropic.json
│   └── gitlab.example.json          # Template — copy to gitlab.json
├── agents/
│   ├── intake_agent.py              # Classification + scoring
│   ├── lead_scorer.py               # 100-point scoring rubric
│   ├── research_agent.py            # Company research via web search
│   ├── linkedin_agent.py            # LinkedIn profile enrichment
│   ├── briefing_agent.py            # Daily report + slides
│   └── report_formatter.py          # Markdown + PPTX output
├── server/
│   ├── app.py                       # FastAPI application
│   ├── db.py                        # SQLite CRUD helpers
│   └── routes/
│       ├── call_prep.py             # AI call prep + PDF/PPTX export
│       └── draft_email.py           # AI outreach email generation
├── web/src/
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── LeadDetailPage.tsx
│   │   ├── ResearchPage.tsx
│   │   └── BriefingsPage.tsx
│   └── components/
│       ├── MeddpiccBadge.tsx
│       ├── OrgPowerMap.tsx
│       ├── DepartmentHeatMap.tsx
│       ├── PipelineRunner.tsx
│       └── Layout.tsx
└── tests/                           # 35 tests passing
```

## How It Was Built

This entire project was built by a non-developer sales professional using Claude's own tools:

- **Claude Code** — terminal-based coding agent for the full codebase
- **Claude API** — powers the three scoring/research/briefing agents
- **Claude Web Search** — company enrichment and LinkedIn research
- **Cowork** — planning, strategy, and document generation

No code was written manually. Every line was generated through AI-assisted development.

---

Built with: Claude Code · Claude API · Claude Web Search · Cowork · FastAPI · React · SQLite · python-pptx · fpdf2
