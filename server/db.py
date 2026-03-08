"""Thin query layer over the existing triage SQLite database."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "triage.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # Parse JSON columns
    for key in list(d.keys()):
        if key.endswith("_json") and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


# --- Leads ---

def get_leads(
    grade: str | None = None,
    intent: str | None = None,
    buying_stage: str | None = None,
    use_case: str | None = None,
    sort_by: str = "score",
    order: str = "desc",
) -> list[dict]:
    allowed_sort = {
        "score", "grade", "company_name", "sender_email",
        "intent", "buying_stage", "estimated_acv", "last_seen_at",
    }
    if sort_by not in allowed_sort:
        sort_by = "score"
    if order.lower() not in ("asc", "desc"):
        order = "desc"

    conditions: list[str] = []
    params: list[str] = []

    if grade:
        conditions.append("grade = ?")
        params.append(grade.upper())
    if intent:
        conditions.append("intent = ?")
        params.append(intent)
    if buying_stage:
        conditions.append("buying_stage = ?")
        params.append(buying_stage)
    if use_case:
        conditions.append("use_case = ?")
        params.append(use_case)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM leads {where} ORDER BY {sort_by} {order}"

    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_lead(sender_email: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM leads WHERE sender_email = ?", (sender_email,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_lead_emails(sender_email: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM email_log WHERE sender_email = ? ORDER BY received_at DESC",
            (sender_email,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_lead_stats() -> dict:
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM leads").fetchone()["c"]
        grades = {}
        for row in conn.execute(
            "SELECT grade, COUNT(*) as c FROM leads GROUP BY grade"
        ).fetchall():
            grades[row["grade"]] = row["c"]
        acv_row = conn.execute(
            "SELECT SUM(estimated_acv) as total_acv FROM leads WHERE estimated_acv IS NOT NULL"
        ).fetchone()
        total_acv = acv_row["total_acv"] or 0
    return {"total": total, "grades": grades, "total_pipeline_acv": total_acv}


# --- Research ---

def get_research_all() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM company_research ORDER BY updated_at DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_research_one(company_key: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM company_research WHERE company_key = ?", (company_key,)
        ).fetchone()
    return _row_to_dict(row) if row else None


# --- Briefings ---

def get_briefings() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, briefing_date, summary_json, pptx_path, created_at "
            "FROM daily_briefings ORDER BY briefing_date DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_briefing(briefing_date: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM daily_briefings WHERE briefing_date = ?",
            (briefing_date,),
        ).fetchone()
    return _row_to_dict(row) if row else None
