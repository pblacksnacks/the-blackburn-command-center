"""
Database helpers for the Email Triage System.

Provides CRUD operations for leads, company_research, email_log,
and daily_briefings tables using Python's built-in sqlite3 module.

Usage:
    from src.db import init_db, upsert_lead, get_unresearched_companies
    init_db()  # Creates tables if they don't exist
"""

import sqlite3
import json
import os
from pathlib import Path

DB_PATH = Path(os.getenv("TRIAGE_DB_PATH", "data/triage.db"))


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    schema_path = Path(__file__).parent.parent / "schema.sql"
    with open(schema_path) as f:
        schema = f.read()
    conn = get_connection()
    conn.executescript(schema)
    conn.close()


# --- Lead CRUD ---

def upsert_lead(email: str, name: str = None, company: str = None,
                score: int = None, grade: str = None, intent: str = None,
                notes: list = None) -> int:
    """Insert or update a lead. Returns the lead ID."""
    # TODO: Implement weighted average scoring for repeat senders
    raise NotImplementedError("Build this in Step 6")


def get_lead_by_email(email: str) -> dict | None:
    """Fetch a lead by email address."""
    raise NotImplementedError("Build this in Step 6")


def get_leads_by_grade(grade: str) -> list[dict]:
    """Fetch all leads with the given grade."""
    raise NotImplementedError("Build this in Step 6")


# --- Company Research CRUD ---

def get_unresearched_companies() -> list[dict]:
    """Get companies that haven't been researched yet."""
    raise NotImplementedError("Build this in Step 7")


def save_company_research(company_name: str, data: dict):
    """Save research results for a company."""
    raise NotImplementedError("Build this in Step 7")


# --- Email Log ---

def log_email(lead_id: int, gmail_message_id: str, subject: str,
              body_preview: str, received_at: str, classification: str,
              score_contribution: int):
    """Log a processed email."""
    raise NotImplementedError("Build this in Step 6")


# --- Briefings ---

def save_briefing(briefing_text: str, lead_count: int, top_leads: list) -> int:
    """Save a daily briefing. Returns the briefing ID."""
    raise NotImplementedError("Build this in Step 8")


def get_latest_briefing() -> dict | None:
    """Get the most recent briefing."""
    raise NotImplementedError("Build this in Step 8")
