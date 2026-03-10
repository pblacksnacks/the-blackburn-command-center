from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic
from pydantic import BaseModel, Field, model_validator

CLAUDE_MODEL = "claude-sonnet-4-20250514"


class NewsItem(BaseModel):
    title: str
    url: str | None = None
    summary: str
    published_at: str | None = None


class CompanyResearchModel(BaseModel):
    company_name: str
    company_domain: str | None = None
    website_url: str | None = None
    description: str
    employee_range: str
    funding_stage: str = Field(
        description="One of: seed, series_a, series_b, series_c, public, bootstrapped, private_unknown"
    )
    linkedin_url: str | None = None
    recent_news: list[NewsItem] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    notebook_summary: str | None = None
    notebook_id: str | None = None
    notebook_url: str | None = None

    @model_validator(mode="after")
    def trim_news(self) -> "CompanyResearchModel":
        self.recent_news = self.recent_news[:3]
        self.source_urls = list(dict.fromkeys(self.source_urls))
        return self


@dataclass(frozen=True, slots=True)
class CompanyCandidate:
    company_key: str
    company_name: str
    company_domain: str | None
    best_grade: str


class SQLiteResearchStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_unresearched_companies(self, limit: int = 10) -> list[CompanyCandidate]:
        sql = """
        WITH ranked AS (
            SELECT
                COALESCE(NULLIF(l.company_domain, ''), LOWER(REPLACE(l.company_name, ' ', '_'))) AS company_key,
                l.company_name,
                l.company_domain,
                MAX(l.score) AS best_score,
                CASE MAX(CASE l.grade
                    WHEN 'A' THEN 4
                    WHEN 'B' THEN 3
                    WHEN 'C' THEN 2
                    ELSE 1
                END)
                    WHEN 4 THEN 'A'
                    WHEN 3 THEN 'B'
                    WHEN 2 THEN 'C'
                    ELSE 'D'
                END AS best_grade
            FROM leads l
            LEFT JOIN company_research cr
                ON cr.company_key = COALESCE(NULLIF(l.company_domain, ''), LOWER(REPLACE(l.company_name, ' ', '_')))
            WHERE l.intent = 'new_business'
              AND COALESCE(l.company_name, '') <> ''
              AND cr.researched_at IS NULL
            GROUP BY 1, 2, 3
        )
        SELECT * FROM ranked
        ORDER BY CASE best_grade
            WHEN 'A' THEN 1
            WHEN 'B' THEN 2
            WHEN 'C' THEN 3
            ELSE 4
        END, best_score DESC
        LIMIT ?;
        """
        with self.connect() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()

        return [
            CompanyCandidate(
                company_key=row["company_key"],
                company_name=row["company_name"],
                company_domain=row["company_domain"],
                best_grade=row["best_grade"],
            )
            for row in rows
        ]

    def upsert_company_research(
        self,
        company_key: str,
        research: CompanyResearchModel,
    ) -> None:
        sql = """
        INSERT INTO company_research (
            company_key,
            company_name,
            company_domain,
            website_url,
            description,
            employee_range,
            funding_stage,
            linkedin_url,
            recent_news_json,
            profile_json,
            source_urls_json,
            notebook_id,
            notebook_url,
            notebook_summary,
            researched_at,
            updated_at,
            raw_model_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
        ON CONFLICT(company_key) DO UPDATE SET
            company_name = excluded.company_name,
            company_domain = excluded.company_domain,
            website_url = excluded.website_url,
            description = excluded.description,
            employee_range = excluded.employee_range,
            funding_stage = excluded.funding_stage,
            linkedin_url = excluded.linkedin_url,
            recent_news_json = excluded.recent_news_json,
            profile_json = excluded.profile_json,
            source_urls_json = excluded.source_urls_json,
            notebook_id = excluded.notebook_id,
            notebook_url = excluded.notebook_url,
            notebook_summary = excluded.notebook_summary,
            researched_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP,
            raw_model_json = excluded.raw_model_json
        """
        profile_json = {
            "company_name": research.company_name,
            "company_domain": research.company_domain,
            "website_url": research.website_url,
            "description": research.description,
            "employee_range": research.employee_range,
            "funding_stage": research.funding_stage,
            "linkedin_url": research.linkedin_url,
        }

        with self.connect() as conn:
            conn.execute(
                sql,
                (
                    company_key,
                    research.company_name,
                    research.company_domain,
                    research.website_url,
                    research.description,
                    research.employee_range,
                    research.funding_stage,
                    research.linkedin_url,
                    json.dumps([item.model_dump() for item in research.recent_news]),
                    json.dumps(profile_json),
                    json.dumps(research.source_urls),
                    research.notebook_id,
                    research.notebook_url,
                    research.notebook_summary,
                    json.dumps(research.model_dump()),
                ),
            )
            conn.commit()


class ResearchAgent:
    def __init__(
        self,
        api_key: str,
        db_path: str,
        model: str = CLAUDE_MODEL,
    ) -> None:
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.store = SQLiteResearchStore(db_path)

    def run(self, limit: int = 10, delay_seconds: float = 2.0) -> list[CompanyResearchModel]:
        enriched: list[CompanyResearchModel] = []
        candidates = self.store.get_unresearched_companies(limit=limit)

        for idx, candidate in enumerate(candidates, start=1):
            research = self.research_one(
                company_name=candidate.company_name,
                domain=candidate.company_domain,
                lead_grade=candidate.best_grade,
            )
            self.store.upsert_company_research(candidate.company_key, research)
            enriched.append(research)

            if idx < len(candidates):
                time.sleep(delay_seconds)

        return enriched

    def research_one(
        self,
        company_name: str,
        domain: str | None,
        lead_grade: str = "C",
    ) -> CompanyResearchModel:
        prompt = self._prompt(company_name=company_name, domain=domain)

        messages = [{"role": "user", "content": prompt}]
        tools = [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 4,
            }
        ]

        response = None
        for _ in range(5):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1400,
                messages=messages,
                tools=tools,
            )

            _raise_on_web_tool_error(response)

            if response.stop_reason != "pause_turn":
                break

            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response.content},
            ]

        if response is None:
            raise RuntimeError("No response from Claude")

        text = self._combined_text(response)
        payload = _extract_json_object(text)
        research = CompanyResearchModel.model_validate_json(payload)

        return research

    def _combined_text(self, response) -> str:
        text_chunks: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_chunks.append(block.text)
        return "\n".join(text_chunks).strip()

    def _prompt(self, company_name: str, domain: str | None) -> str:
        domain_line = domain or "unknown"

        return f"""
Research this company for a B2B SaaS account executive.

Company:
- company_name: {company_name}
- company_domain: {domain_line}

Research requirements:
- 2-3 sentence company description
- approximate employee count range
- funding stage: seed, series_a, series_b, series_c, public, bootstrapped, or private_unknown
- up to 3 recent news items from the last 90 days
- LinkedIn company page URL
- company website URL if confidently known

Rules:
- prefer current, credible sources
- if a field is uncertain, use the best bounded estimate and say so in description
- only include recent news from the last 90 days
- return JSON only
- do not wrap the JSON in markdown fences

Return exactly this shape:
{{
  "company_name": "string",
  "company_domain": "string or null",
  "website_url": "string or null",
  "description": "string",
  "employee_range": "string",
  "funding_stage": "seed|series_a|series_b|series_c|public|bootstrapped|private_unknown",
  "linkedin_url": "string or null",
  "recent_news": [
    {{
      "title": "string",
      "url": "string",
      "summary": "string",
      "published_at": "ISO-8601 date or null"
    }}
  ],
  "source_urls": ["string"]
}}
""".strip()


def _extract_json_object(text: str) -> str:
    fenced = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)

    raw = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if raw:
        return raw.group(1)

    raise ValueError("No JSON object found in Claude response")


def _raise_on_web_tool_error(response) -> None:
    for block in response.content:
        if getattr(block, "type", None) != "web_search_tool_result":
            continue

        content = getattr(block, "content", None)
        if isinstance(content, dict) and content.get("type") == "web_search_tool_result_error":
            raise RuntimeError(f"web_search error: {content.get('error_code')}")


# Monkey-patch retry into ResearchAgent
_orig_research_one = ResearchAgent.research_one

def _research_one_with_retry(self, company_name, domain=None, lead_grade="C", max_retries=3):
    import time as _time
    for attempt in range(1, max_retries + 1):
        try:
            return _orig_research_one(self, company_name=company_name, domain=domain, lead_grade=lead_grade)
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e):
                wait = 60 * attempt
                print(f"    Rate limited on {company_name}, waiting {wait}s (attempt {attempt}/{max_retries})...")
                _time.sleep(wait)
            else:
                raise
    return _orig_research_one(self, company_name=company_name, domain=domain, lead_grade=lead_grade)

ResearchAgent.research_one = _research_one_with_retry
