import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.linkedin_agent import (
    LinkedInProfileModel,
    ExperienceItem,
    LinkedInSearchAgent,
    SQLiteLinkedInStore,
    _extract_json_object,
    _raise_on_web_tool_error,
)


# --- Model tests ---

def test_parse_linkedin_profile_model():
    payload = {
        "full_name": "Raj Mehta",
        "linkedin_url": "https://linkedin.com/in/rajmehta",
        "headline": "VP Engineering at Notion",
        "location": "San Francisco, CA",
        "current_title": "VP Engineering",
        "current_company": "Notion",
        "summary": "Experienced engineering leader",
        "experience": [
            {"title": "VP Engineering", "company": "Notion", "duration": "2 years"},
            {"title": "Senior Director", "company": "Stripe", "duration": "3 years"},
        ],
        "source_urls": ["https://linkedin.com/in/rajmehta"],
    }
    model = LinkedInProfileModel.model_validate(payload)
    assert model.full_name == "Raj Mehta"
    assert model.linkedin_url == "https://linkedin.com/in/rajmehta"
    assert len(model.experience) == 2
    assert model.experience[0].company == "Notion"


def test_profile_model_minimal():
    """Profile with only required field."""
    model = LinkedInProfileModel(full_name="Jane Doe")
    assert model.full_name == "Jane Doe"
    assert model.linkedin_url is None
    assert model.experience == []
    assert model.source_urls == []


def test_source_urls_deduped():
    model = LinkedInProfileModel(
        full_name="Test",
        source_urls=["https://a.com", "https://b.com", "https://a.com"],
    )
    assert model.source_urls == ["https://a.com", "https://b.com"]


# --- JSON extraction ---

def test_extract_json_object_plain():
    text = '{"full_name":"Raj","linkedin_url":null,"headline":"VP Eng","experience":[],"source_urls":[]}'
    payload = _extract_json_object(text)
    assert json.loads(payload)["full_name"] == "Raj"


def test_extract_json_object_fenced():
    text = 'Result:\n```json\n{"full_name":"Raj","experience":[],"source_urls":[]}\n```'
    payload = _extract_json_object(text)
    assert json.loads(payload)["full_name"] == "Raj"


def test_extract_json_no_json_raises():
    with pytest.raises(ValueError, match="No JSON"):
        _extract_json_object("No json here")


# --- Web tool error ---

def test_web_tool_error_detection():
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


def test_web_tool_no_error():
    ok_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Hello")]
    )
    _raise_on_web_tool_error(ok_response)  # Should not raise


# --- SQLite store ---

@pytest.fixture
def db_path(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    # Create tables
    schema_path = Path(__file__).resolve().parent.parent / "schema.sql"
    conn.executescript(schema_path.read_text())
    # Insert a test lead
    conn.execute("""
        INSERT INTO leads (
            sender_email, sender_name, company_name, company_domain,
            intent, score, grade,
            intent_score, domain_quality_score, urgency_score,
            content_depth_score, authority_score,
            next_best_action
        ) VALUES (
            'raj@notion.so', 'Raj Mehta', 'Notion', 'notion.so',
            'new_business', 85, 'A',
            25, 20, 15, 12, 8,
            'Schedule call'
        )
    """)
    conn.commit()
    conn.close()
    return str(db)


def test_store_get_unsearched_contacts(db_path):
    store = SQLiteLinkedInStore(db_path)
    contacts = store.get_unsearched_contacts(limit=10)
    assert len(contacts) == 1
    assert contacts[0]["sender_email"] == "raj@notion.so"
    assert contacts[0]["sender_name"] == "Raj Mehta"


def test_store_upsert_and_retrieve(db_path):
    store = SQLiteLinkedInStore(db_path)

    profile = LinkedInProfileModel(
        full_name="Raj Mehta",
        linkedin_url="https://linkedin.com/in/rajmehta",
        headline="VP Engineering at Notion",
        location="San Francisco, CA",
        current_title="VP Engineering",
        current_company="Notion",
        summary="Engineering leader",
        experience=[
            ExperienceItem(title="VP Engineering", company="Notion", duration="2 years"),
        ],
        source_urls=["https://linkedin.com/in/rajmehta"],
    )

    store.upsert_contact(
        sender_email="raj@notion.so",
        company_key="notion.so",
        profile=profile,
    )

    # Verify stored
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM contact_linkedin WHERE sender_email = ?", ("raj@notion.so",)
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["full_name"] == "Raj Mehta"
    assert row["linkedin_url"] == "https://linkedin.com/in/rajmehta"
    assert row["headline"] == "VP Engineering at Notion"
    assert row["current_title"] == "VP Engineering"
    assert row["searched_at"] is not None
    exp = json.loads(row["experience_json"])
    assert len(exp) == 1
    assert exp[0]["title"] == "VP Engineering"


def test_store_upsert_updates_existing(db_path):
    store = SQLiteLinkedInStore(db_path)

    profile1 = LinkedInProfileModel(full_name="Raj Mehta", headline="VP Eng")
    store.upsert_contact("raj@notion.so", "notion.so", profile1)

    profile2 = LinkedInProfileModel(full_name="Raj Mehta", headline="SVP Engineering")
    store.upsert_contact("raj@notion.so", "notion.so", profile2)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM contact_linkedin WHERE sender_email = ?", ("raj@notion.so",)
    ).fetchone()
    conn.close()

    assert row["headline"] == "SVP Engineering"


def test_store_unsearched_excludes_searched(db_path):
    store = SQLiteLinkedInStore(db_path)

    profile = LinkedInProfileModel(full_name="Raj Mehta")
    store.upsert_contact("raj@notion.so", "notion.so", profile)

    # Should be empty now since the contact has been searched
    contacts = store.get_unsearched_contacts(limit=10)
    assert len(contacts) == 0


# --- Agent mock test ---

def test_agent_search_one_mocked(db_path, monkeypatch):
    """Test the agent with a mocked Claude response."""
    mock_json = json.dumps({
        "full_name": "Raj Mehta",
        "linkedin_url": "https://linkedin.com/in/rajmehta",
        "headline": "VP Engineering at Notion",
        "location": "San Francisco, CA",
        "current_title": "VP Engineering",
        "current_company": "Notion",
        "summary": "Engineering leader",
        "experience": [
            {"title": "VP Engineering", "company": "Notion", "duration": "2 years"}
        ],
        "source_urls": ["https://linkedin.com/in/rajmehta"],
    })

    mock_response = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=mock_json)],
    )

    class MockClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                return mock_response

    agent = LinkedInSearchAgent.__new__(LinkedInSearchAgent)
    agent.client = MockClient()
    agent.model = "test-model"
    agent.store = SQLiteLinkedInStore(db_path)

    # Use the original search_one (not the retry-wrapped one)
    from agents.linkedin_agent import _orig_search_one
    profile = _orig_search_one(
        agent,
        sender_email="raj@notion.so",
        sender_name="Raj Mehta",
        company_name="Notion",
        company_domain="notion.so",
    )

    assert profile.full_name == "Raj Mehta"
    assert profile.linkedin_url == "https://linkedin.com/in/rajmehta"
    assert profile.current_title == "VP Engineering"
    assert len(profile.experience) == 1
