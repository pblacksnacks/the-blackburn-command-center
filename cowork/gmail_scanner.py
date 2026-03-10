#!/usr/bin/env python3
"""
Cowork Gmail Scanner — Pipeline bridge for Claude Cowork integration.

Bridges the gap between demo mode (pre-loaded JSON) and live inbox processing.
When run by Cowork, Gmail MCP provides the emails; this script feeds them
through the existing pipeline agents unchanged.

Usage:
    python cowork/gmail_scanner.py                  # Full pipeline update
    python cowork/gmail_scanner.py --scan-only      # Intake + research only
    python cowork/gmail_scanner.py --briefing-only  # Generate briefing from existing DB
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from agents.lead_scorer import RawEmail, LeadScorer
from agents.intake_agent import IntakeAgent, SqliteLeadStore
from agents.research_agent import ResearchAgent
from agents.briefing_agent import BriefingAgent


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITLAB_MODE = os.environ.get("GITLAB_MODE", "false").lower() == "true"
DB_PATH = os.environ.get("TRIAGE_DB", str(PROJECT_ROOT / "triage.db"))
REPORTS_DIR = str(PROJECT_ROOT / "reports")


# ---------------------------------------------------------------------------
# GmailEmailSource — implements the EmailSource protocol
# ---------------------------------------------------------------------------

class GmailEmailSource:
    """Email source backed by pre-fetched Gmail messages (from Cowork MCP)."""

    def __init__(self, emails: list[RawEmail]) -> None:
        self._emails = emails

    def fetch(self, limit: int = 25) -> list[RawEmail]:
        return self._emails[:limit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_last_scan_timestamp(db_path: str) -> str | None:
    """Return the most recent received_at from email_log, or None if empty."""
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT MAX(received_at) FROM email_log").fetchone()
        conn.close()
        return row[0] if row and row[0] else None
    except Exception:
        return None


def fetch_gmail_emails(after_timestamp: str | None = None) -> list[RawEmail]:
    """Placeholder for Gmail MCP integration.

    When Cowork calls this pipeline, it passes emails directly via
    run_pipeline_update(emails=[...]). This function exists for standalone
    CLI usage and will be wired to Gmail MCP in a future update.

    The Cowork integration flow is:
        1. Cowork calls gmail_search_messages(query="is:inbox newer_than:1d")
        2. For each message, calls gmail_read_message(message_id=...)
        3. Maps to RawEmail:
            RawEmail(
                email_id=message["id"],
                sender_email=message["from"],
                sender_name=<parsed from "from" header>,
                subject=message["subject"],
                body=message["body"],
                received_at=message["date"],
            )
        4. Passes list to run_pipeline_update(emails=[...])
    """
    # TODO: Wire to Gmail MCP for standalone CLI mode
    # query = "is:inbox newer_than:1d"
    # if after_timestamp:
    #     query = f"is:inbox after:{after_timestamp}"
    # messages = gmail_search_messages(query=query)
    # emails = []
    # for msg in messages:
    #     full = gmail_read_message(message_id=msg["id"])
    #     emails.append(RawEmail(
    #         email_id=full["id"],
    #         sender_email=full["from"],
    #         sender_name=parse_name(full["from"]),
    #         subject=full["subject"],
    #         body=full["body"],
    #         received_at=full["date"],
    #     ))
    # return emails
    return []


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment or .env file.")
        sys.exit(1)
    return key


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

def run_pipeline_update(
    emails: list[RawEmail] | None = None,
    scan_only: bool = False,
    briefing_only: bool = False,
) -> dict:
    """Run the pipeline incrementally (no DB clear).

    Args:
        emails: Pre-fetched emails (from Cowork MCP). Falls back to
                fetch_gmail_emails() if None.
        scan_only: Run intake + research only, skip briefing.
        briefing_only: Generate briefing from existing DB data only.

    Returns:
        Summary dict with counts and briefing date.
    """
    api_key = _get_api_key()
    today = date.today().isoformat()
    summary: dict = {
        "new_emails": 0,
        "new_leads": 0,
        "companies_researched": 0,
        "briefing_date": today,
    }

    # --- Briefing only: skip intake and research ---
    if briefing_only:
        print(f"\n{'='*60}")
        print(f"  BRIEFING AGENT — Generating report for {today}")
        print(f"{'='*60}")

        agent = BriefingAgent(api_key=api_key, db_path=DB_PATH, reports_dir=REPORTS_DIR)
        briefing = agent.run(briefing_date=today)

        print(f"  Executive Summary: {briefing.executive_summary}")
        print(f"  Top leads: {len(briefing.top_leads)}")
        summary["briefing_generated"] = True
        return summary

    # --- Intake ---
    if emails is None:
        last_ts = get_last_scan_timestamp(DB_PATH)
        emails = fetch_gmail_emails(after_timestamp=last_ts)

    if not emails:
        print("  No new emails to process.")
        if not scan_only:
            # Still generate briefing from existing data
            try:
                agent = BriefingAgent(api_key=api_key, db_path=DB_PATH, reports_dir=REPORTS_DIR)
                agent.run(briefing_date=today)
                summary["briefing_generated"] = True
            except RuntimeError as e:
                print(f"  Briefing skipped: {e}")
        return summary

    print(f"\n{'='*60}")
    print(f"  INTAKE AGENT — Processing {len(emails)} emails")
    print(f"{'='*60}")

    source = GmailEmailSource(emails)
    store = SqliteLeadStore(DB_PATH)
    scorer = LeadScorer(api_key=api_key, gitlab_mode=GITLAB_MODE)
    intake = IntakeAgent(email_source=source, scorer=scorer, store=store)
    results = intake.run(limit=25)

    summary["new_emails"] = len(emails)
    summary["new_leads"] = len(results)

    for r in results:
        print(f"  [{r.grade}] {r.total_score:3d}  {r.sender_email}  {r.summary}")

    # --- Research ---
    print(f"\n{'='*60}")
    print(f"  RESEARCH AGENT — Enriching companies")
    print(f"{'='*60}")

    research = ResearchAgent(api_key=api_key, db_path=DB_PATH)
    enriched = research.run(limit=10, delay_seconds=2.0)
    summary["companies_researched"] = len(enriched)

    for r in enriched:
        print(f"  {r.company_name} — {r.employee_range}, {r.funding_stage}")

    # --- Briefing (unless scan-only) ---
    if not scan_only:
        print(f"\n{'='*60}")
        print(f"  BRIEFING AGENT — Generating report for {today}")
        print(f"{'='*60}")

        briefing_agent = BriefingAgent(api_key=api_key, db_path=DB_PATH, reports_dir=REPORTS_DIR)
        try:
            briefing = briefing_agent.run(briefing_date=today)
            print(f"  Executive Summary: {briefing.executive_summary}")
            summary["briefing_generated"] = True
        except RuntimeError as e:
            print(f"  Briefing skipped: {e}")

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cowork Gmail Scanner — pipeline bridge for live inbox processing"
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Run intake + research only, skip briefing generation",
    )
    parser.add_argument(
        "--briefing-only",
        action="store_true",
        help="Generate briefing from existing DB data (no inbox scan)",
    )
    args = parser.parse_args()

    if args.scan_only and args.briefing_only:
        print("ERROR: --scan-only and --briefing-only are mutually exclusive.")
        sys.exit(1)

    print("\n  Blackburn Command Center — Cowork Pipeline Update")
    print(f"  Mode: {'GitLab' if GITLAB_MODE else 'Anthropic'}")
    print(f"  Database: {DB_PATH}")

    summary = run_pipeline_update(
        scan_only=args.scan_only,
        briefing_only=args.briefing_only,
    )

    print(f"\n{'='*60}")
    print(f"  DONE — {summary['new_leads']} new leads, "
          f"{summary['companies_researched']} companies researched")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
