#!/usr/bin/env python3
"""
Email Triage Pipeline — CLI Runner (v2)

Usage:
    python main.py full --demo          # Run all three agents with sample data
    python main.py intake --demo        # Run intake only
    python main.py research --demo      # Run research only
    python main.py briefing --demo      # Run briefing only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.lead_scorer import RawEmail, LeadScorer
from agents.intake_agent import IntakeAgent, SqliteLeadStore, EmailSource
from agents.research_agent import ResearchAgent
from agents.briefing_agent import BriefingAgent


# ---------------------------------------------------------------------------
# Demo data loading — reads from demo_data/*.json
# ---------------------------------------------------------------------------

DEMO_DATA_DIR = PROJECT_ROOT / "demo_data"

GITLAB_MODE = os.environ.get("GITLAB_MODE", "false").lower() == "true"

DB_PATH = os.environ.get("TRIAGE_DB", "triage.db")
REPORTS_DIR = "reports"


def _load_demo_emails() -> list[RawEmail]:
    """Load demo emails from the appropriate JSON file."""
    filename = "gitlab.json" if GITLAB_MODE else "anthropic.json"
    path = DEMO_DATA_DIR / filename
    if not path.exists():
        print(f"ERROR: Demo data file not found: {path}")
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    return [RawEmail(**entry) for entry in data]


class DemoEmailSource:
    def __init__(self, emails: list[RawEmail]) -> None:
        self._emails = emails

    def fetch(self, limit: int = 25) -> list[RawEmail]:
        return self._emails[:limit]


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment or .env file.")
        print("Create a .env file with: ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)
    return key


def run_intake(demo: bool) -> None:
    api_key = _get_api_key()

    if demo:
        email_source = DemoEmailSource(_load_demo_emails())
    else:
        print("Live Gmail mode not yet implemented. Use --demo.")
        sys.exit(1)

    store = SqliteLeadStore(DB_PATH)
    scorer = LeadScorer(api_key=api_key, gitlab_mode=GITLAB_MODE)
    agent = IntakeAgent(email_source=email_source, scorer=scorer, store=store)

    print(f"\n{'='*70}")
    print("  INTAKE AGENT — Classifying, scoring & qualifying inbound emails")
    print(f"{'='*70}")

    results = agent.run(limit=25)

    for r in results:
        acv_str = f"${r.estimated_acv:,}" if r.estimated_acv else "TBD"
        provider_str = f" (from {r.current_ai_provider})" if r.current_ai_provider else ""
        print(f"\n  [{r.grade}] {r.total_score:3d}  {r.intent:<15s}  {r.sender_email}")
        print(f"       {r.summary}")
        print(f"       Use case: {r.use_case} | Stage: {r.buying_stage} | ACV: {acv_str}{provider_str}")
        print(f"       Product: {r.product_line_fit} | Tier: {r.deal_size_tier}")
        print(f"       Next: {r.next_best_action}")

        # MEDDPICC summary
        m = r.meddpicc
        known = sum(1 for v in [m.metrics, m.economic_buyer, m.decision_criteria,
                                m.decision_process, m.paper_process, m.implicate_pain,
                                m.champion, m.competition] if v == "known")
        partial = sum(1 for v in [m.metrics, m.economic_buyer, m.decision_criteria,
                                  m.decision_process, m.paper_process, m.implicate_pain,
                                  m.champion, m.competition] if v == "partial")
        print(f"       MEDDPICC: {known}/8 known, {partial}/8 partial")

    print(f"\n  Processed {len(results)} emails.")


def run_research(demo: bool) -> None:
    api_key = _get_api_key()
    agent = ResearchAgent(api_key=api_key, db_path=DB_PATH)

    print(f"\n{'='*70}")
    print("  RESEARCH AGENT — Enriching companies via web search")
    print(f"{'='*70}")

    delay = 8.0 if demo else 2.0
    limit = 5 if demo else 10
    results = agent.run(limit=limit, delay_seconds=delay)

    for r in results:
        print(f"\n  {r.company_name} ({r.company_domain or 'no domain'})")
        print(f"       {r.employee_range} | {r.funding_stage}")
        desc = r.description[:120] + "..." if len(r.description or "") > 120 else r.description
        print(f"       {desc}")

    print(f"\n  Researched {len(results)} companies.")


def run_briefing(demo: bool) -> None:
    api_key = _get_api_key()
    today = date.today().isoformat()

    agent = BriefingAgent(api_key=api_key, db_path=DB_PATH, reports_dir=REPORTS_DIR)

    print(f"\n{'='*70}")
    print(f"  BRIEFING AGENT — Generating daily report for {today}")
    print(f"{'='*70}")

    briefing = agent.run(briefing_date=today)

    print(f"\n  Executive Summary:")
    print(f"  {briefing.executive_summary}")
    print(f"\n  Top leads: {len(briefing.top_leads)}")
    for idx, lead in enumerate(briefing.top_leads[:5], start=1):
        print(f"    {idx}. [{lead.grade}] {lead.score} — {lead.company_name}")

    md_path = Path(REPORTS_DIR) / f"briefing_{today}.md"
    pptx_path = Path(REPORTS_DIR) / f"top_clients_{today}.pptx"
    print(f"\n  Markdown: {md_path}")
    print(f"  PowerPoint: {pptx_path}")


def run_full(demo: bool) -> None:
    start = time.time()

    print("\n" + "=" * 70)
    print("  EMAIL TRIAGE PIPELINE — Full Run (v2)")
    print("  15 real SF high-tech companies | MEDDPICC | ACV/TAM | Competitive Intel")
    print("=" * 70)

    if demo and Path(DB_PATH).exists():
        Path(DB_PATH).unlink()
        print("  (Cleared previous demo database)")

    run_intake(demo)
    run_research(demo)
    run_briefing(demo)

    elapsed = time.time() - start
    print(f"\n{'='*70}")
    print(f"  PIPELINE COMPLETE — {elapsed:.1f}s elapsed")
    print(f"{'='*70}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Email Triage Pipeline — AI-powered lead scoring, qualification, and briefing"
    )
    parser.add_argument(
        "stage",
        choices=["full", "intake", "research", "briefing"],
        help="Which pipeline stage to run",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use sample emails from real SF high-tech companies",
    )

    args = parser.parse_args()
    runners = {
        "full": run_full,
        "intake": run_intake,
        "research": run_research,
        "briefing": run_briefing,
    }
    runners[args.stage](args.demo)


if __name__ == "__main__":
    main()
