from __future__ import annotations

import json
import re
import sqlite3
import time
from typing import Any

from anthropic import Anthropic
from pydantic import BaseModel, Field, model_validator

CLAUDE_MODEL = "claude-sonnet-4-20250514"


class ExperienceItem(BaseModel):
    title: str
    company: str
    duration: str | None = None


class LinkedInProfileModel(BaseModel):
    full_name: str
    linkedin_url: str | None = None
    headline: str | None = None
    location: str | None = None
    current_title: str | None = None
    current_company: str | None = None
    summary: str | None = None
    experience: list[ExperienceItem] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def dedupe_sources(self) -> "LinkedInProfileModel":
        self.source_urls = list(dict.fromkeys(self.source_urls))
        return self


class SQLiteLinkedInStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_unsearched_contacts(self, limit: int = 10) -> list[dict]:
        sql = """
        SELECT
            l.sender_email,
            l.sender_name,
            l.company_name,
            l.company_domain,
            COALESCE(NULLIF(l.company_domain, ''), LOWER(REPLACE(l.company_name, ' ', '_'))) AS company_key
        FROM leads l
        LEFT JOIN contact_linkedin cl ON cl.sender_email = l.sender_email
        WHERE cl.searched_at IS NULL
          AND l.intent = 'new_business'
          AND COALESCE(l.sender_name, '') <> ''
        ORDER BY l.score DESC
        LIMIT ?;
        """
        with self.connect() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        return [dict(row) for row in rows]

    def upsert_contact(
        self,
        sender_email: str,
        company_key: str | None,
        profile: LinkedInProfileModel,
    ) -> None:
        sql = """
        INSERT INTO contact_linkedin (
            sender_email, company_key, full_name, linkedin_url, headline,
            location, current_title, current_company, summary,
            experience_json, source_urls_json,
            searched_at, updated_at, raw_model_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
        ON CONFLICT(sender_email) DO UPDATE SET
            company_key = excluded.company_key,
            full_name = excluded.full_name,
            linkedin_url = excluded.linkedin_url,
            headline = excluded.headline,
            location = excluded.location,
            current_title = excluded.current_title,
            current_company = excluded.current_company,
            summary = excluded.summary,
            experience_json = excluded.experience_json,
            source_urls_json = excluded.source_urls_json,
            searched_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP,
            raw_model_json = excluded.raw_model_json
        """
        with self.connect() as conn:
            conn.execute(
                sql,
                (
                    sender_email,
                    company_key,
                    profile.full_name,
                    profile.linkedin_url,
                    profile.headline,
                    profile.location,
                    profile.current_title,
                    profile.current_company,
                    profile.summary,
                    json.dumps([item.model_dump() for item in profile.experience]),
                    json.dumps(profile.source_urls),
                    json.dumps(profile.model_dump()),
                ),
            )
            conn.commit()


class LinkedInSearchAgent:
    def __init__(
        self,
        api_key: str,
        db_path: str,
        model: str = CLAUDE_MODEL,
    ) -> None:
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.store = SQLiteLinkedInStore(db_path)

    def run(self, limit: int = 10, delay_seconds: float = 2.0) -> list[LinkedInProfileModel]:
        enriched: list[LinkedInProfileModel] = []
        contacts = self.store.get_unsearched_contacts(limit=limit)

        for idx, contact in enumerate(contacts, start=1):
            profile = self.search_one(
                sender_email=contact["sender_email"],
                sender_name=contact["sender_name"],
                company_name=contact["company_name"],
                company_domain=contact["company_domain"],
            )
            self.store.upsert_contact(
                sender_email=contact["sender_email"],
                company_key=contact["company_key"],
                profile=profile,
            )
            enriched.append(profile)

            if idx < len(contacts):
                time.sleep(delay_seconds)

        return enriched

    def search_one(
        self,
        sender_email: str,
        sender_name: str,
        company_name: str | None = None,
        company_domain: str | None = None,
    ) -> LinkedInProfileModel:
        prompt = self._prompt(
            name=sender_name,
            company=company_name,
            domain=company_domain,
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
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
        profile = LinkedInProfileModel.model_validate_json(payload)

        return profile

    def _combined_text(self, response: Any) -> str:
        text_chunks: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_chunks.append(block.text)
        return "\n".join(text_chunks).strip()

    def _prompt(self, name: str, company: str | None, domain: str | None) -> str:
        company_info = company or domain or "unknown"
        return f"""
Find the LinkedIn profile for this person and extract structured information.

Person:
- Name: {name}
- Company: {company_info}
- Domain: {domain or "unknown"}

Search strategy:
1. Search for "{name}" site:linkedin.com/in {company_info}
2. If no results, try broader searches with just the name and company

Extract from the LinkedIn profile and any supporting sources:

Rules:
- prefer the most relevant LinkedIn profile match
- if multiple matches, pick the one at the matching company
- if no LinkedIn profile is found, still return what you can with linkedin_url as null
- return JSON only
- do not wrap the JSON in markdown fences

Return exactly this shape:
{{
  "full_name": "string",
  "linkedin_url": "string or null",
  "headline": "string or null",
  "location": "string or null",
  "current_title": "string or null",
  "current_company": "string or null",
  "summary": "brief professional summary or null",
  "experience": [
    {{
      "title": "string",
      "company": "string",
      "duration": "string or null"
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


def _raise_on_web_tool_error(response: Any) -> None:
    for block in response.content:
        if getattr(block, "type", None) != "web_search_tool_result":
            continue

        content = getattr(block, "content", None)
        if isinstance(content, dict) and content.get("type") == "web_search_tool_result_error":
            raise RuntimeError(f"web_search error: {content.get('error_code')}")


# Retry wrapper for rate limits
import functools

_orig_search_one = LinkedInSearchAgent.search_one


def _search_one_with_retry(self, sender_email, sender_name, company_name=None, company_domain=None, max_retries=3):
    import time as _time
    for attempt in range(1, max_retries + 1):
        try:
            return _orig_search_one(
                self,
                sender_email=sender_email,
                sender_name=sender_name,
                company_name=company_name,
                company_domain=company_domain,
            )
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e):
                wait = 60 * attempt
                print(f"    Rate limited on {sender_name}, waiting {wait}s (attempt {attempt}/{max_retries})...")
                _time.sleep(wait)
            else:
                raise
    return _orig_search_one(
        self,
        sender_email=sender_email,
        sender_name=sender_name,
        company_name=company_name,
        company_domain=company_domain,
    )


LinkedInSearchAgent.search_one = _search_one_with_retry
