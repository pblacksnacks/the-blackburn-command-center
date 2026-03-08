import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.research_agent import CompanyResearchModel, ResearchAgent, _extract_json_object, _raise_on_web_tool_error


def test_extract_json_object_from_plain_text():
    text = '{"company_name":"Acme","description":"Test","employee_range":"51-200","funding_stage":"series_a","recent_news":[],"source_urls":[]}'
    payload = _extract_json_object(text)
    assert json.loads(payload)["company_name"] == "Acme"


def test_extract_json_object_from_fenced():
    text = 'Here is the result:\n```json\n{"company_name":"Acme","description":"Test","employee_range":"51-200","funding_stage":"series_a","recent_news":[],"source_urls":[]}\n```'
    payload = _extract_json_object(text)
    assert json.loads(payload)["company_name"] == "Acme"


def test_parse_company_research_model():
    payload = {
        "company_name": "Acme",
        "company_domain": "acme.com",
        "website_url": "https://acme.com",
        "description": "Acme sells workflow software to mid-market operations teams.",
        "employee_range": "201-500",
        "funding_stage": "series_b",
        "linkedin_url": "https://www.linkedin.com/company/acme/",
        "recent_news": [
            {
                "title": "Acme launches new AI ops product",
                "url": "https://example.com/news1",
                "summary": "Launch summary",
                "published_at": "2026-02-10",
            }
        ],
        "source_urls": ["https://acme.com", "https://example.com/news1"],
    }
    model = CompanyResearchModel.model_validate(payload)
    assert model.company_name == "Acme"
    assert model.funding_stage == "series_b"


def test_news_trimmed_to_three():
    payload = {
        "company_name": "BigCo",
        "description": "Test",
        "employee_range": "1000+",
        "funding_stage": "public",
        "recent_news": [
            {"title": f"News {i}", "url": f"https://example.com/{i}", "summary": f"Summary {i}"}
            for i in range(6)
        ],
        "source_urls": [],
    }
    model = CompanyResearchModel.model_validate(payload)
    assert len(model.recent_news) == 3


def test_pause_turn_loop_pattern():
    pause_response = SimpleNamespace(
        stop_reason="pause_turn",
        content=[SimpleNamespace(type="text", text="Searching...")],
    )
    assert pause_response.stop_reason == "pause_turn"


def test_web_tool_error_block_detection():
    error_response = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="web_search_tool_result",
                content={"type": "web_search_tool_result_error", "error_code": "too_many_requests"},
            )
        ]
    )
    with pytest.raises(RuntimeError, match="too_many_requests"):
        _raise_on_web_tool_error(error_response)
