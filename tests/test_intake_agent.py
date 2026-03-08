import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.intake_agent import IntakeAgent, SqliteLeadStore
from agents.lead_scorer import LeadScorer, RawEmail, ScoringResult, MeddpiccScore


class FakeEmailSource:
    def __init__(self, emails):
        self._emails = emails

    def fetch(self, limit: int = 25):
        return self._emails[:limit]


class FakeLeadScorer:
    def __init__(self, results_by_id):
        self.results_by_id = results_by_id

    def score_email(self, email: RawEmail) -> ScoringResult:
        return self.results_by_id[email.email_id]


DEFAULT_MEDDPICC = MeddpiccScore(
    metrics="unknown", economic_buyer="unknown",
    decision_criteria="unknown", decision_process="unknown",
    paper_process="unknown", implicate_pain="unknown",
    champion="unknown", competition="unknown",
)

STRONG_MEDDPICC = MeddpiccScore(
    metrics="partial", economic_buyer="known",
    decision_criteria="known", decision_process="known",
    paper_process="partial", implicate_pain="known",
    champion="known", competition="known",
)


@pytest.fixture
def sample_emails():
    return [
        RawEmail(
            email_id="e1",
            sender_email="vp.engineering@notion.so",
            sender_name="Raj Mehta",
            subject="Claude API integration for Notion AI",
            body="We need an enterprise API agreement. 50B tokens/month. CTO joining.",
            received_at="2026-03-07T08:00:00Z",
        ),
        RawEmail(
            email_id="e2",
            sender_email="dev@gmail.com",
            sender_name="Random Dev",
            subject="Quick question about pricing",
            body="How much does Claude API cost for a side project?",
            received_at="2026-03-07T09:00:00Z",
        ),
        RawEmail(
            email_id="e3",
            sender_email="ops@samsara.com",
            sender_name="Samsara IT",
            subject="API rate limit errors",
            body="We're hitting 429 errors. Account ID: ent-samsara-prod-01.",
            received_at="2026-03-07T10:00:00Z",
        ),
    ]


@pytest.fixture
def sample_results():
    return {
        "e1": ScoringResult(
            email_id="e1",
            sender_email="vp.engineering@notion.so",
            sender_name="Raj Mehta",
            sender_title="VP Engineering",
            company_name="Notion",
            company_domain="notion.so",
            intent="new_business",
            intent_score=29, domain_quality_score=24, urgency_score=18,
            content_depth_score=14, authority_score=9, total_score=94, grade="A",
            urgency_signals=["Q2 deadline", "CTO involvement", "50B tokens/month"],
            summary="Notion VP Engineering wants enterprise API for AI features, switching from OpenAI.",
            reasoning="Strong buying signals across all dimensions.",
            use_case="product_integration",
            product_line_fit="api",
            buying_stage="ready_to_buy",
            current_ai_provider="OpenAI",
            competitive_signals=["switching from OpenAI", "benchmarked Claude vs GPT"],
            estimated_acv=350000,
            deal_size_tier="enterprise",
            tam_estimate="$2M+ based on 800 employees and product integration at scale",
            expansion_potential="Initial API deal could expand to internal Claude Enterprise seats",
            meddpicc=STRONG_MEDDPICC,
            discovery_questions=["What's the migration timeline?", "Who owns the API budget?"],
            next_best_action="Schedule technical deep-dive this week — CTO wants to join.",
            partnership_synergies=["Notion is a major productivity platform, co-marketing potential"],
            partnership_detractors=["Currently on OpenAI, migration effort required"],
        ),
        "e2": ScoringResult(
            email_id="e2",
            sender_email="dev@gmail.com",
            sender_name="Random Dev",
            sender_title=None,
            company_name=None,
            company_domain="gmail.com",
            intent="new_business",
            intent_score=10, domain_quality_score=3, urgency_score=0,
            content_depth_score=2, authority_score=1, total_score=16, grade="D",
            urgency_signals=[],
            summary="Individual developer asking about API pricing for side project.",
            reasoning="No company, no budget, no urgency.",
            use_case="unknown",
            product_line_fit="api",
            buying_stage="researching",
            current_ai_provider=None,
            competitive_signals=[],
            estimated_acv=None,
            deal_size_tier="smb",
            tam_estimate=None,
            expansion_potential=None,
            meddpicc=DEFAULT_MEDDPICC,
            discovery_questions=[],
            next_best_action="Auto-respond with API docs link. No rep follow-up needed.",
            partnership_synergies=[],
            partnership_detractors=[],
        ),
        "e3": ScoringResult(
            email_id="e3",
            sender_email="ops@samsara.com",
            sender_name="Samsara IT",
            sender_title=None,
            company_name="Samsara",
            company_domain="samsara.com",
            intent="support",
            intent_score=2, domain_quality_score=20, urgency_score=12,
            content_depth_score=8, authority_score=0, total_score=42, grade="C",
            urgency_signals=["production impact", "rate limit errors"],
            summary="Existing Samsara customer hitting rate limits on production API.",
            reasoning="Support issue, not new pipeline.",
            use_case="product_integration",
            product_line_fit="api",
            buying_stage="unknown",
            current_ai_provider=None,
            competitive_signals=[],
            estimated_acv=None,
            deal_size_tier="unknown",
            tam_estimate=None,
            expansion_potential=None,
            meddpicc=DEFAULT_MEDDPICC,
            discovery_questions=[],
            next_best_action="Route to support team — production issue needs immediate attention.",
            partnership_synergies=[],
            partnership_detractors=[],
        ),
    }


def test_run_persists_all_first_pass(tmp_path, sample_emails, sample_results):
    db_path = tmp_path / "leads.db"
    store = SqliteLeadStore(str(db_path))
    agent = IntakeAgent(
        email_source=FakeEmailSource(sample_emails),
        scorer=FakeLeadScorer(sample_results),
        store=store,
    )
    results = agent.run(limit=3)

    assert len(results) == 3
    lead = store.get_lead("vp.engineering@notion.so")
    assert lead["score"] == 94
    assert lead["grade"] == "A"
    assert lead["use_case"] == "product_integration"
    assert lead["buying_stage"] == "ready_to_buy"
    assert lead["estimated_acv"] == 350000


def test_meddpicc_persisted(tmp_path, sample_emails, sample_results):
    db_path = tmp_path / "leads.db"
    store = SqliteLeadStore(str(db_path))
    agent = IntakeAgent(
        email_source=FakeEmailSource([sample_emails[0]]),
        scorer=FakeLeadScorer(sample_results),
        store=store,
    )
    agent.run(limit=1)

    lead = store.get_lead("vp.engineering@notion.so")
    meddpicc = json.loads(lead["meddpicc_json"])
    assert meddpicc["economic_buyer"] == "known"
    assert meddpicc["champion"] == "known"


def test_competitive_signals_persisted(tmp_path, sample_emails, sample_results):
    db_path = tmp_path / "leads.db"
    store = SqliteLeadStore(str(db_path))
    agent = IntakeAgent(
        email_source=FakeEmailSource([sample_emails[0]]),
        scorer=FakeLeadScorer(sample_results),
        store=store,
    )
    agent.run(limit=1)

    lead = store.get_lead("vp.engineering@notion.so")
    signals = json.loads(lead["competitive_signals_json"])
    assert len(signals) >= 1
    assert "OpenAI" in signals[0]


def test_duplicate_email_is_skipped(tmp_path, sample_emails, sample_results):
    db_path = tmp_path / "leads.db"
    store = SqliteLeadStore(str(db_path))
    agent = IntakeAgent(
        email_source=FakeEmailSource([sample_emails[0]]),
        scorer=FakeLeadScorer(sample_results),
        store=store,
    )
    first = agent.run(limit=1)
    second = agent.run(limit=1)

    assert len(first) == 1
    assert len(second) == 0


def test_support_email_stays_support(tmp_path, sample_emails, sample_results):
    db_path = tmp_path / "leads.db"
    store = SqliteLeadStore(str(db_path))
    agent = IntakeAgent(
        email_source=FakeEmailSource([sample_emails[2]]),
        scorer=FakeLeadScorer(sample_results),
        store=store,
    )
    agent.run(limit=1)

    lead = store.get_lead("ops@samsara.com")
    assert lead["intent"] == "support"
