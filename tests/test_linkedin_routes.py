"""Integration tests for LinkedIn API routes using FastAPI TestClient."""

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with schema and a test lead."""
    db = tmp_path / "test_triage.db"
    conn = sqlite3.connect(str(db))
    schema_path = Path(__file__).resolve().parent.parent / "schema.sql"
    conn.executescript(schema_path.read_text())
    conn.execute("""
        INSERT INTO leads (
            sender_email, sender_name, company_name, company_domain,
            intent, score, grade,
            intent_score, domain_quality_score, urgency_score,
            content_depth_score, authority_score,
            next_best_action
        ) VALUES (
            'test@example.com', 'Test User', 'Example Corp', 'example.com',
            'new_business', 75, 'B',
            20, 18, 12, 10, 7,
            'Follow up'
        )
    """)
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def client(test_db):
    """Create a test client with the test database."""
    with patch("server.db.DB_PATH", test_db):
        from server.app import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        yield client


def test_get_linkedin_empty(client):
    response = client.get("/api/linkedin")
    assert response.status_code == 200
    assert response.json() == []


def test_get_linkedin_profile_not_found(client):
    response = client.get("/api/linkedin/test%40example.com")
    assert response.status_code == 404
    assert response.json()["detail"] == "LinkedIn profile not found"


def test_search_linkedin_lead_not_found(client):
    response = client.post(
        "/api/linkedin/search",
        json={"sender_email": "nonexistent@example.com"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


def test_search_linkedin_returns_job(client, test_db):
    """POST /api/linkedin/search returns a job and starts background thread."""
    with patch("server.routes.linkedin.PROJECT_ROOT", str(test_db.parent)):
        response = client.post(
            "/api/linkedin/search",
            json={"sender_email": "test@example.com"},
        )
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "running"
    assert job["sender_email"] == "test@example.com"
    assert "id" in job


def test_search_status_not_found(client):
    response = client.get("/api/linkedin/search/status/nonexistent")
    assert response.status_code == 404


def test_get_linkedin_profile_after_insert(client, test_db):
    """Insert a profile directly and verify GET returns it."""
    conn = sqlite3.connect(str(test_db))
    conn.execute("""
        INSERT INTO contact_linkedin (
            sender_email, company_key, full_name, linkedin_url, headline,
            location, current_title, current_company, summary,
            experience_json, source_urls_json,
            searched_at, updated_at, raw_model_json
        ) VALUES (
            'test@example.com', 'example.com', 'Test User',
            'https://linkedin.com/in/testuser', 'Engineer at Example',
            'NYC', 'Engineer', 'Example Corp', 'Experienced engineer',
            '[{"title":"Engineer","company":"Example Corp","duration":"3 years"}]',
            '["https://linkedin.com/in/testuser"]',
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
            '{}'
        )
    """)
    conn.commit()
    conn.close()

    response = client.get("/api/linkedin/test%40example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Test User"
    assert data["linkedin_url"] == "https://linkedin.com/in/testuser"
    assert data["headline"] == "Engineer at Example"
    assert len(data["experience_json"]) == 1
    assert data["experience_json"][0]["title"] == "Engineer"


def test_get_all_linkedin_profiles(client, test_db):
    """Insert a profile and verify GET /api/linkedin returns it in list."""
    conn = sqlite3.connect(str(test_db))
    conn.execute("""
        INSERT INTO contact_linkedin (
            sender_email, full_name, headline,
            experience_json, source_urls_json,
            searched_at, updated_at
        ) VALUES (
            'test@example.com', 'Test User', 'Engineer',
            '[]', '[]',
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    response = client.get("/api/linkedin")
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) == 1
    assert profiles[0]["sender_email"] == "test@example.com"
