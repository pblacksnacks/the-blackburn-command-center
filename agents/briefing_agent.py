from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Literal

from anthropic import Anthropic
from pydantic import BaseModel, Field, model_validator

from .report_formatter import DailyBriefing, LeadCard, build_pptx_deck, write_markdown_report

CLAUDE_MODEL = "claude-sonnet-4-20250514"


class LeadContextModel(BaseModel):
    sender_email: str
    sender_name: str | None = None
    sender_title: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    intent: str
    score: int
    grade: Literal["A", "B", "C", "D"]
    last_reasoning: str | None = None
    email_count: int
    trending_up: bool = False

    # New v2 fields
    use_case: str | None = None
    product_line_fit: str | None = None
    buying_stage: str | None = None
    current_ai_provider: str | None = None
    competitive_signals: list[str] = Field(default_factory=list)
    estimated_acv: int | None = None
    deal_size_tier: str | None = None
    tam_estimate: str | None = None
    expansion_potential: str | None = None
    meddpicc: dict = Field(default_factory=dict)
    discovery_questions: list[str] = Field(default_factory=list)
    next_best_action: str | None = None
    partnership_synergies: list[str] = Field(default_factory=list)
    partnership_detractors: list[str] = Field(default_factory=list)

    # Research data
    description: str | None = None
    employee_range: str | None = None
    funding_stage: str | None = None
    notebook_summary: str | None = None
    recent_news: list[dict] = Field(default_factory=list)


class LeadCardModel(BaseModel):
    company_name: str | None = None
    sender_name: str | None = None
    sender_title: str | None = None
    sender_email: str
    grade: Literal["A", "B", "C", "D"]
    score: int
    why_hot: str
    company_context: str
    suggested_approach: str
    suggested_opener: str
    key_signals: list[str] = Field(default_factory=list)

    # v2 additions
    use_case: str | None = None
    estimated_acv: int | None = None
    meddpicc_summary: str | None = None
    competitive_landscape: str | None = None
    top_discovery_question: str | None = None


class BriefingPayloadModel(BaseModel):
    briefing_date: str
    total_new: int
    total_updated: int
    grade_distribution: dict[str, int]
    top_intents: dict[str, int]
    executive_summary: str
    pipeline_value: str
    quick_wins: list[str]
    needs_attention: list[str]
    top_leads: list[LeadCardModel]

    @model_validator(mode="after")
    def max_top_leads(self) -> "BriefingPayloadModel":
        self.top_leads = self.top_leads[:10]
        return self

    def to_dataclass(self) -> DailyBriefing:
        return DailyBriefing(
            briefing_date=self.briefing_date,
            total_new=self.total_new,
            total_updated=self.total_updated,
            grade_distribution=self.grade_distribution,
            top_intents=self.top_intents,
            executive_summary=self.executive_summary,
            pipeline_value=self.pipeline_value,
            quick_wins=self.quick_wins,
            needs_attention=self.needs_attention,
            top_leads=[
                LeadCard(**lead.model_dump()) for lead in self.top_leads
            ],
        )


class BriefingRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_today_context(self, limit: int = 50) -> list[LeadContextModel]:
        sql = """
        WITH today_emails AS (
            SELECT
                el.sender_email,
                COUNT(*) AS emails_today,
                MAX(el.processed_at) AS last_processed_at
            FROM email_log el
            WHERE DATE(el.processed_at) >= DATE('now', '-1 day')
            GROUP BY el.sender_email
        ),
        score_trend AS (
            SELECT
                sender_email,
                COUNT(*) AS total_events,
                AVG(CASE WHEN rn_desc <= 2 THEN score END) AS recent_avg,
                AVG(CASE WHEN rn_asc <= 2 THEN score END) AS early_avg
            FROM (
                SELECT
                    sender_email, score, processed_at,
                    ROW_NUMBER() OVER (PARTITION BY sender_email ORDER BY processed_at DESC) AS rn_desc,
                    ROW_NUMBER() OVER (PARTITION BY sender_email ORDER BY processed_at ASC) AS rn_asc
                FROM email_log
                WHERE processed_at >= datetime('now', '-30 days')
            ) x
            GROUP BY sender_email
        )
        SELECT
            l.sender_email, l.sender_name, l.sender_title,
            l.company_name, l.company_domain,
            l.intent, l.score, l.grade,
            l.last_reasoning, l.notes_json, l.email_count,
            l.use_case, l.product_line_fit,
            l.buying_stage, l.current_ai_provider, l.competitive_signals_json,
            l.estimated_acv, l.deal_size_tier, l.tam_estimate, l.expansion_potential,
            l.meddpicc_json, l.discovery_questions_json, l.next_best_action,
            l.partnership_synergies_json, l.partnership_detractors_json,
            CASE
                WHEN st.total_events >= 2 AND st.recent_avg >= st.early_avg + 10 THEN 1
                ELSE 0
            END AS trending_up,
            cr.description, cr.employee_range, cr.funding_stage,
            cr.notebook_summary, cr.recent_news_json
        FROM leads l
        JOIN today_emails te ON te.sender_email = l.sender_email
        LEFT JOIN score_trend st ON st.sender_email = l.sender_email
        LEFT JOIN company_research cr
            ON cr.company_key = COALESCE(NULLIF(l.company_domain, ''), LOWER(REPLACE(l.company_name, ' ', '_')))
        ORDER BY l.score DESC, l.last_seen_at DESC
        LIMIT ?;
        """
        with self.connect() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()

        items: list[LeadContextModel] = []
        for row in rows:
            items.append(
                LeadContextModel(
                    sender_email=row["sender_email"],
                    sender_name=row["sender_name"],
                    sender_title=row["sender_title"],
                    company_name=row["company_name"],
                    company_domain=row["company_domain"],
                    intent=row["intent"],
                    score=row["score"],
                    grade=row["grade"],
                    last_reasoning=row["last_reasoning"],
                    email_count=row["email_count"],
                    trending_up=bool(row["trending_up"]),
                    use_case=row["use_case"],
                    product_line_fit=row["product_line_fit"],
                    buying_stage=row["buying_stage"],
                    current_ai_provider=row["current_ai_provider"],
                    competitive_signals=json.loads(row["competitive_signals_json"] or "[]"),
                    estimated_acv=row["estimated_acv"],
                    deal_size_tier=row["deal_size_tier"],
                    tam_estimate=row["tam_estimate"],
                    expansion_potential=row["expansion_potential"],
                    meddpicc=json.loads(row["meddpicc_json"] or "{}"),
                    discovery_questions=json.loads(row["discovery_questions_json"] or "[]"),
                    next_best_action=row["next_best_action"],
                    partnership_synergies=json.loads(row["partnership_synergies_json"] or "[]"),
                    partnership_detractors=json.loads(row["partnership_detractors_json"] or "[]"),
                    description=row["description"],
                    employee_range=row["employee_range"],
                    funding_stage=row["funding_stage"],
                    notebook_summary=row["notebook_summary"],
                    recent_news=json.loads(row["recent_news_json"] or "[]"),
                )
            )
        return items

    def save_daily_briefing(
        self, briefing_date: str, markdown_body: str,
        summary_json: dict, pptx_path: str,
    ) -> None:
        sql = """
        INSERT INTO daily_briefings (briefing_date, markdown_body, summary_json, pptx_path)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(briefing_date) DO UPDATE SET
            markdown_body = excluded.markdown_body,
            summary_json = excluded.summary_json,
            pptx_path = excluded.pptx_path,
            created_at = CURRENT_TIMESTAMP
        """
        with self.connect() as conn:
            conn.execute(sql, (briefing_date, markdown_body, json.dumps(summary_json), pptx_path))
            conn.commit()


class BriefingAgent:
    def __init__(self, api_key: str, db_path: str, reports_dir: str = "reports") -> None:
        self.client = Anthropic(api_key=api_key)
        self.repo = BriefingRepository(db_path)
        self.reports_dir = Path(reports_dir)

    def run(self, briefing_date: str) -> DailyBriefing:
        context = self.repo.fetch_today_context(limit=50)
        if not context:
            raise RuntimeError("No leads found for today's briefing")

        payload = self._generate_briefing_payload(briefing_date, context)
        briefing = payload.to_dataclass()

        md_path = self.reports_dir / f"briefing_{briefing_date}.md"
        pptx_path = self.reports_dir / f"top_clients_{briefing_date}.pptx"

        write_markdown_report(briefing, md_path)
        build_pptx_deck(briefing, pptx_path)

        self.repo.save_daily_briefing(
            briefing_date=briefing_date,
            markdown_body=md_path.read_text(encoding="utf-8"),
            summary_json=payload.model_dump(),
            pptx_path=str(pptx_path),
        )
        return briefing

    def _generate_briefing_payload(
        self, briefing_date: str, context: list[LeadContextModel],
    ) -> BriefingPayloadModel:
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8000,
            system=self._system_prompt(),
            messages=[{"role": "user", "content": self._user_prompt(briefing_date, context)}],
            tools=[self._briefing_tool()],
            tool_choice={"type": "tool", "name": "record_daily_briefing"},
        )

        tool_block = next(
            (b for b in response.content
             if getattr(b, "type", None) == "tool_use"
             and getattr(b, "name", None) == "record_daily_briefing"),
            None,
        )
        if tool_block is None:
            raise RuntimeError("Claude did not return record_daily_briefing")

        return BriefingPayloadModel.model_validate(dict(tool_block.input))

    def _system_prompt(self) -> str:
        if os.environ.get("GITLAB_MODE", "false").lower() == "true":
            team_desc = "GitLab's enterprise sales team"
        else:
            team_desc = "Anthropic's mid-market sales team"
        return f"""
You are writing an executive daily sales briefing for {team_desc}
targeting high-tech companies (500-3000 employees) in San Francisco.

Your job:
- Rank highest priority leads by deal quality, not just score
- For each lead: explain why it's hot, the competitive situation, MEDDPICC gaps, and next action
- Calculate total pipeline value from estimated ACVs
- Flag competitive threats (especially OpenAI switches and bake-offs)
- Separate product_integration, internal_productivity, and dual_motion opportunities
- Highlight deals with active timelines or budget confirmation

Rules:
- A deal with budget + timeline + champion beats a vague high-score lead
- Active bake-offs need immediate attention regardless of score
- Dual motion deals (product + internal) are highest strategic value
- Include estimated ACV and use_case for each lead card
- Include MEDDPICC summary showing what's known vs gaps
- pipeline_value should sum all estimated ACVs for Grade A and B leads
- quick_wins = leads with clear next step and high probability
- needs_attention = competitive threats, expiring timelines, trending senders
- Return the final answer ONLY by calling record_daily_briefing
""".strip()

    def _user_prompt(self, briefing_date: str, context: list[LeadContextModel]) -> str:
        serialized = json.dumps([item.model_dump() for item in context], indent=2)
        return f"""
Create the daily lead briefing for {briefing_date}.

Lead context includes scoring, MEDDPICC qualification, ACV estimates, competitive signals,
and company research where available. Use all of it.

Lead context JSON:
{serialized}
""".strip()

    def _briefing_tool(self) -> dict:
        return {
            "name": "record_daily_briefing",
            "description": (
                "Return the structured daily sales briefing. "
                "Include pipeline value, MEDDPICC summaries, competitive intel, and ACV per lead."
            ),
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "briefing_date": {"type": "string"},
                    "total_new": {"type": "integer"},
                    "total_updated": {"type": "integer"},
                    "grade_distribution": {"type": "object", "additionalProperties": {"type": "integer"}},
                    "top_intents": {"type": "object", "additionalProperties": {"type": "integer"}},
                    "executive_summary": {"type": "string"},
                    "pipeline_value": {"type": "string"},
                    "quick_wins": {"type": "array", "items": {"type": "string"}},
                    "needs_attention": {"type": "array", "items": {"type": "string"}},
                    "top_leads": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "company_name": {"type": ["string", "null"]},
                                "sender_name": {"type": ["string", "null"]},
                                "sender_title": {"type": ["string", "null"]},
                                "sender_email": {"type": "string"},
                                "grade": {"type": "string", "enum": ["A", "B", "C", "D"]},
                                "score": {"type": "integer"},
                                "why_hot": {"type": "string"},
                                "company_context": {"type": "string"},
                                "suggested_approach": {"type": "string"},
                                "suggested_opener": {"type": "string"},
                                "key_signals": {"type": "array", "items": {"type": "string"}},
                                "use_case": {"type": ["string", "null"]},
                                "estimated_acv": {"type": ["integer", "null"]},
                                "meddpicc_summary": {"type": ["string", "null"]},
                                "competitive_landscape": {"type": ["string", "null"]},
                                "top_discovery_question": {"type": ["string", "null"]},
                            },
                            "required": [
                                "sender_email", "grade", "score",
                                "why_hot", "company_context",
                                "suggested_approach", "suggested_opener", "key_signals",
                            ],
                        },
                    },
                },
                "required": [
                    "briefing_date", "total_new", "total_updated",
                    "grade_distribution", "top_intents",
                    "executive_summary", "pipeline_value",
                    "quick_wins", "needs_attention", "top_leads",
                ],
            },
        }
