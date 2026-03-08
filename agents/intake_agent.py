from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Protocol

from .lead_scorer import RawEmail, ScoringResult, LeadScorer, grade_from_score

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


INSERT_EMAIL_LOG_SQL = """
INSERT INTO email_log (
    email_id, sender_email, subject, body, received_at,
    intent, score, grade,
    intent_score, domain_quality_score, urgency_score,
    content_depth_score, authority_score,
    rubric_json, result_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


UPSERT_LEAD_SQL = """
INSERT INTO leads (
    sender_email, sender_name, sender_title,
    company_name, company_domain,
    intent, score, grade,
    intent_score, domain_quality_score, urgency_score,
    content_depth_score, authority_score,
    use_case, product_line_fit,
    buying_stage, current_ai_provider, competitive_signals_json,
    estimated_acv, deal_size_tier, tam_estimate, expansion_potential,
    meddpicc_json, discovery_questions_json, next_best_action,
    partnership_synergies_json, partnership_detractors_json,
    last_reasoning, notes_json,
    email_count, first_seen_at, last_seen_at, last_email_id
) VALUES (
    :sender_email, :sender_name, :sender_title,
    :company_name, :company_domain,
    :intent, :score, :grade,
    :intent_score, :domain_quality_score, :urgency_score,
    :content_depth_score, :authority_score,
    :use_case, :product_line_fit,
    :buying_stage, :current_ai_provider, :competitive_signals_json,
    :estimated_acv, :deal_size_tier, :tam_estimate, :expansion_potential,
    :meddpicc_json, :discovery_questions_json, :next_best_action,
    :partnership_synergies_json, :partnership_detractors_json,
    :last_reasoning, json(:note_array_json),
    1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :last_email_id
)
ON CONFLICT(sender_email) DO UPDATE SET
    sender_name = COALESCE(excluded.sender_name, leads.sender_name),
    sender_title = COALESCE(excluded.sender_title, leads.sender_title),
    company_name = COALESCE(excluded.company_name, leads.company_name),
    company_domain = COALESCE(excluded.company_domain, leads.company_domain),
    intent = excluded.intent,
    score = CAST(ROUND((excluded.score * 0.70) + (leads.score * 0.30), 0) AS INTEGER),
    grade = CASE
        WHEN ROUND((excluded.score * 0.70) + (leads.score * 0.30), 0) >= 80 THEN 'A'
        WHEN ROUND((excluded.score * 0.70) + (leads.score * 0.30), 0) >= 60 THEN 'B'
        WHEN ROUND((excluded.score * 0.70) + (leads.score * 0.30), 0) >= 40 THEN 'C'
        ELSE 'D'
    END,
    intent_score = excluded.intent_score,
    domain_quality_score = excluded.domain_quality_score,
    urgency_score = excluded.urgency_score,
    content_depth_score = excluded.content_depth_score,
    authority_score = excluded.authority_score,
    use_case = excluded.use_case,
    product_line_fit = excluded.product_line_fit,
    buying_stage = excluded.buying_stage,
    current_ai_provider = COALESCE(excluded.current_ai_provider, leads.current_ai_provider),
    competitive_signals_json = excluded.competitive_signals_json,
    estimated_acv = COALESCE(excluded.estimated_acv, leads.estimated_acv),
    deal_size_tier = excluded.deal_size_tier,
    tam_estimate = COALESCE(excluded.tam_estimate, leads.tam_estimate),
    expansion_potential = COALESCE(excluded.expansion_potential, leads.expansion_potential),
    meddpicc_json = excluded.meddpicc_json,
    discovery_questions_json = excluded.discovery_questions_json,
    next_best_action = excluded.next_best_action,
    partnership_synergies_json = excluded.partnership_synergies_json,
    partnership_detractors_json = excluded.partnership_detractors_json,
    last_reasoning = excluded.last_reasoning,
    notes_json = json_insert(COALESCE(leads.notes_json, '[]'), '$[#]', json(:note_json)),
    email_count = leads.email_count + 1,
    last_seen_at = CURRENT_TIMESTAMP,
    last_email_id = excluded.last_email_id
"""


class EmailSource(Protocol):
    def fetch(self, limit: int = 25) -> Iterable[RawEmail]:
        ...


class SqliteLeadStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def init_schema(self) -> None:
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(schema_sql)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def email_seen(self, email_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM email_log WHERE email_id = ?",
                (email_id,),
            ).fetchone()
            return row is not None

    def persist(self, email: RawEmail, result: ScoringResult) -> None:
        note = {
            "event": "email_scored",
            "email_id": email.email_id,
            "subject": email.subject,
            "received_at": email.received_at,
            "intent": result.intent,
            "new_observed_score": result.total_score,
            "new_observed_grade": result.grade,
            "use_case": result.use_case,
            "buying_stage": result.buying_stage,
            "summary": result.summary,
            "urgency_signals": result.urgency_signals,
            "next_best_action": result.next_best_action,
        }

        meddpicc_dict = asdict(result.meddpicc) if result.meddpicc else {}

        with self.connect() as conn:
            conn.execute("BEGIN")

            conn.execute(
                INSERT_EMAIL_LOG_SQL,
                (
                    email.email_id,
                    email.sender_email,
                    email.subject,
                    email.body,
                    email.received_at,
                    result.intent,
                    result.total_score,
                    result.grade,
                    result.intent_score,
                    result.domain_quality_score,
                    result.urgency_score,
                    result.content_depth_score,
                    result.authority_score,
                    json.dumps({
                        "intent_max": 30,
                        "domain_quality_max": 25,
                        "urgency_max": 20,
                        "content_depth_max": 15,
                        "authority_max": 10,
                    }),
                    json.dumps(asdict(result)),
                ),
            )

            conn.execute(
                UPSERT_LEAD_SQL,
                {
                    "sender_email": result.sender_email,
                    "sender_name": result.sender_name,
                    "sender_title": result.sender_title,
                    "company_name": result.company_name,
                    "company_domain": result.company_domain,
                    "intent": result.intent,
                    "score": result.total_score,
                    "grade": result.grade,
                    "intent_score": result.intent_score,
                    "domain_quality_score": result.domain_quality_score,
                    "urgency_score": result.urgency_score,
                    "content_depth_score": result.content_depth_score,
                    "authority_score": result.authority_score,
                    "use_case": result.use_case,
                    "product_line_fit": result.product_line_fit,
                    "buying_stage": result.buying_stage,
                    "current_ai_provider": result.current_ai_provider,
                    "competitive_signals_json": json.dumps(result.competitive_signals),
                    "estimated_acv": result.estimated_acv,
                    "deal_size_tier": result.deal_size_tier,
                    "tam_estimate": result.tam_estimate,
                    "expansion_potential": result.expansion_potential,
                    "meddpicc_json": json.dumps(meddpicc_dict),
                    "discovery_questions_json": json.dumps(result.discovery_questions),
                    "next_best_action": result.next_best_action,
                    "partnership_synergies_json": json.dumps(result.partnership_synergies),
                    "partnership_detractors_json": json.dumps(result.partnership_detractors),
                    "last_reasoning": result.reasoning,
                    "note_json": json.dumps(note),
                    "note_array_json": json.dumps([note]),
                    "last_email_id": result.email_id,
                },
            )
            conn.commit()

    def get_lead(self, sender_email: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM leads WHERE sender_email = ?",
                (sender_email,),
            ).fetchone()


class IntakeAgent:
    def __init__(
        self,
        email_source: EmailSource,
        scorer: LeadScorer,
        store: SqliteLeadStore,
    ) -> None:
        self.email_source = email_source
        self.scorer = scorer
        self.store = store

    def run(self, limit: int = 25) -> list[ScoringResult]:
        self.store.init_schema()
        results: list[ScoringResult] = []

        for email in self.email_source.fetch(limit=limit):
            if self.store.email_seen(email.email_id):
                continue
            result = self.scorer.score_email(email)
            self.store.persist(email, result)
            results.append(result)

        return results
