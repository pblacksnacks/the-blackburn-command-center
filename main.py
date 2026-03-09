#!/usr/bin/env python3
"""
Email Triage Pipeline — CLI Runner (v2)

Usage:
    python main.py full --demo          # Run all three agents with sample data
    python main.py intake --demo        # Run intake only
    python main.py research --demo      # Run research only
    python main.py briefing --demo      # Run briefing only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.lead_scorer import RawEmail, ScoringResult, LeadScorer
from agents.intake_agent import IntakeAgent, SqliteLeadStore, EmailSource
from agents.research_agent import ResearchAgent
from agents.briefing_agent import BriefingAgent


# ---------------------------------------------------------------------------
# 15 realistic demo emails — real SF high-tech companies (500-3000 employees)
# ---------------------------------------------------------------------------

DEMO_EMAILS = [
    # 1. Notion — product integration, ready to buy, strong
    RawEmail(
        email_id="demo-001",
        sender_email="cto@notion.so",
        sender_name="Fuzzy Khosrowshahi",
        subject="Claude API integration for Notion AI — need enterprise contract by Q2",
        body=(
            "Hi Anthropic team,\n\n"
            "I'm the CTO at Notion. We're currently using OpenAI's API for our "
            "Notion AI features, but we've been benchmarking Claude Sonnet and Haiku for the past "
            "6 weeks and the quality delta is significant — especially on long-context summarization.\n\n"
            "We're looking to migrate our AI pipeline to Claude by end of Q2. This would cover:\n"
            "- AI writing assistant (all Notion users, ~100M+ monthly)\n"
            "- Q&A over workspace content\n"
            "- Autofill for databases\n\n"
            "We need an enterprise API agreement with committed throughput guarantees. Our current "
            "monthly token volume is in the range of 50B tokens/month. Happy to share exact numbers "
            "on a call.\n\n"
            "Can we schedule a technical deep-dive this week? Our CEO Ivan Zhao would join.\n\n"
            "Best,\nFuzzy Khosrowshahi\nCTO, Notion"
        ),
        received_at="2026-03-07T08:15:00Z",
    ),
    # 2. Webflow — internal productivity + exploring product, evaluating
    RawEmail(
        email_id="demo-002",
        sender_email="arquay.harris@webflow.com",
        sender_name="Arquay Harris",
        subject="Evaluating Claude for internal ops + potential product features",
        body=(
            "Hi,\n\n"
            "I lead the Engineering team at Webflow (~1,000 employees). We're exploring "
            "two tracks:\n\n"
            "1. Internal: our support team handles 3,000+ tickets/week. We want to use Claude to "
            "auto-draft responses, classify tickets, and surface knowledge base gaps.\n\n"
            "2. Product: our design team is prototyping an AI assistant inside the Webflow editor "
            "that could generate CSS, suggest layouts, and explain code — Claude's code generation "
            "quality caught our attention.\n\n"
            "We're comparing Claude, GPT-4o, and Gemini. Our evaluation committee meets March 20th.\n\n"
            "Could you send over enterprise pricing and a technical capabilities deck?\n\n"
            "Thanks,\nArquay Harris\nVP Engineering, Webflow"
        ),
        received_at="2026-03-07T08:45:00Z",
    ),
    # 3. Verkada — product integration, strong signals
    RawEmail(
        email_id="demo-003",
        sender_email="filip@verkada.com",
        sender_name="Filip Kaliszan",
        subject="Claude API for real-time video analytics — procurement timeline Q2",
        body=(
            "Team,\n\n"
            "Filip Kaliszan, CEO & Co-founder at Verkada. We build cloud-managed security cameras "
            "and access control systems for enterprise customers.\n\n"
            "We want to integrate Claude's vision capabilities into our camera analytics pipeline. "
            "Specific use cases:\n"
            "- Real-time scene understanding and anomaly detection\n"
            "- Natural language querying of video footage\n"
            "- Automated incident report generation\n\n"
            "We've been on GPT-4V but the latency and cost at our scale (200K+ cameras deployed) "
            "isn't sustainable. Our VP of Product has approved budget for this switch.\n\n"
            "Procurement needs to have a contract in hand by April 15. Security review is already "
            "underway — can you send your SOC 2 Type II report and BAA?\n\n"
            "Filip Kaliszan\nCEO & Co-founder, Verkada"
        ),
        received_at="2026-03-07T09:00:00Z",
    ),
    # 4. Gusto — dual motion, mid-stage evaluation
    RawEmail(
        email_id="demo-004",
        sender_email="sarah.kim@gusto.com",
        sender_name="Sarah Kim",
        subject="AI-powered HR compliance + internal productivity tools",
        body=(
            "Hello,\n\n"
            "I'm a Product Manager at Gusto working on our AI initiatives. We serve 300K+ small "
            "businesses and are thinking about Claude in two ways:\n\n"
            "Product side: We want to build an AI compliance advisor that helps our customers "
            "navigate employment law across all 50 states. This needs to be extremely accurate "
            "and cite sources — we think Claude's approach to safety and accuracy fits well.\n\n"
            "Internal side: Our 2,500-person team spends significant time on manual document "
            "review, internal knowledge lookups, and drafting customer communications.\n\n"
            "We're early in the evaluation but our CPO is supportive. No formal timeline yet. "
            "Can you share case studies from companies doing similar things?\n\n"
            "Sarah Kim\nProduct Manager, Gusto"
        ),
        received_at="2026-03-07T09:30:00Z",
    ),
    # 5. Airtable — product integration, competitive bake-off
    RawEmail(
        email_id="demo-005",
        sender_email="cto@airtable.com",
        sender_name="David Azose",
        subject="Re: AI features roadmap — Claude vs GPT comparison results",
        body=(
            "Hi,\n\n"
            "Following up from our meeting at the AI Engineering Summit. We ran a head-to-head "
            "evaluation of Claude Sonnet vs GPT-4o for our AI formula generation and data "
            "classification features.\n\n"
            "Results: Claude won on structured output accuracy (94% vs 87%) and was 40% cheaper "
            "on our benchmark workload. GPT-4o was slightly faster on simple tasks.\n\n"
            "We're ready to move forward with a pilot on Claude. 1,000 beta users initially, "
            "expanding to all 500K+ Airtable customers if the pilot succeeds.\n\n"
            "Key question: can you support our volume tier with guaranteed latency SLAs? "
            "We need p95 < 2s for interactive features.\n\n"
            "David Azose\nCTO, Airtable"
        ),
        received_at="2026-03-07T10:00:00Z",
    ),
    # 6. Carta — dual motion, researching phase
    RawEmail(
        email_id="demo-006",
        sender_email="priya.patel@carta.com",
        sender_name="Priya Patel",
        subject="Exploring Claude for equity document analysis",
        body=(
            "Hi Anthropic,\n\n"
            "Priya from Carta's engineering team. We manage equity for 40,000+ companies and "
            "process millions of legal documents — cap tables, 409A valuations, SAFEs, etc.\n\n"
            "We're interested in understanding how Claude handles:\n"
            "- Complex legal document parsing and extraction\n"
            "- Multi-document reasoning (comparing terms across agreements)\n"
            "- Generating plain-language summaries for non-legal stakeholders\n\n"
            "This is still early-stage exploration. We haven't committed to any AI provider yet. "
            "Internally, some teams are using ChatGPT Team but there's no company-wide strategy.\n\n"
            "Is there a sandbox or trial we could access?\n\n"
            "Thanks,\nPriya Patel\nStaff Engineer, Carta"
        ),
        received_at="2026-03-07T10:15:00Z",
    ),
    # 7. Figma — product integration, strong
    RawEmail(
        email_id="demo-007",
        sender_email="david.kossnick@figma.com",
        sender_name="David Kossnick",
        subject="Claude for Figma AI — replacing our current LLM provider",
        body=(
            "Hi,\n\n"
            "David Kossnick, Head of AI Products at Figma. We launched our first AI features last year using "
            "a mix of in-house models and third-party APIs. We're consolidating onto a single "
            "provider for our next generation of AI tools:\n\n"
            "- AI-powered design suggestions and auto-layout\n"
            "- Natural language to design (describe → generate UI)\n"
            "- Smart component recommendations\n"
            "- Design-to-code translation\n\n"
            "We need a provider that excels at visual understanding and structured output. "
            "Our team has been impressed with Claude's capabilities in internal testing.\n\n"
            "Budget is allocated. Decision by end of March. We'd need a dedicated account team "
            "given the scale — Figma has 4M+ users generating AI requests.\n\n"
            "Can we meet this week?\n\n"
            "David Kossnick\nHead of AI Products, Figma"
        ),
        received_at="2026-03-07T10:30:00Z",
    ),
    # 8. Retool — product integration, evaluating
    RawEmail(
        email_id="demo-008",
        sender_email="mark.schaaf@retool.com",
        sender_name="Mark Schaaf",
        subject="Embedding Claude in Retool's AI features",
        body=(
            "Hey Anthropic team,\n\n"
            "Mark Schaaf from Retool. We build internal tools for companies like Amazon, NBC, and "
            "DoorDash. We're adding AI capabilities to let our users:\n\n"
            "- Generate SQL queries from natural language\n"
            "- Build CRUD apps from descriptions\n"
            "- Auto-generate API integrations\n\n"
            "We currently use OpenAI but are evaluating alternatives. Claude's function calling "
            "and code generation have tested well for us.\n\n"
            "Our main concerns are: rate limits at scale, JSON mode reliability, and enterprise "
            "support responsiveness. We have about 500 employees and serve thousands of companies.\n\n"
            "Would love to discuss enterprise terms.\n\n"
            "Mark Schaaf\nCOO, Retool"
        ),
        received_at="2026-03-07T11:00:00Z",
    ),
    # 9. Ironclad — dual motion, strong urgency
    RawEmail(
        email_id="demo-009",
        sender_email="cto@ironcladapp.com",
        sender_name="Jason Boehmig",
        subject="URGENT: Claude Enterprise for contract AI — board presentation next week",
        body=(
            "Hi,\n\n"
            "Jason Boehmig, CEO at Ironclad. We're a contract lifecycle management platform "
            "used by L'Oreal, Mastercard, and OpenAI (ironically).\n\n"
            "Two priorities:\n\n"
            "1. Product: We're building AI contract review and redlining powered by LLMs. "
            "We've been using GPT-4 but accuracy on legal nuance is a concern. Our GC flagged "
            "three errors last month that could have caused real problems.\n\n"
            "2. Internal: 600 employees need access to Claude for legal research, drafting, "
            "and analysis. We want Claude Enterprise with SSO.\n\n"
            "I'm presenting our AI strategy to the board next Thursday. Need to have a vendor "
            "recommendation locked in before then. Budget range: $300-500K annually.\n\n"
            "Can someone senior call me today?\n\n"
            "Jason Boehmig\nCEO, Ironclad"
        ),
        received_at="2026-03-07T11:15:00Z",
    ),
    # 10. Brex — dual motion, evaluating
    RawEmail(
        email_id="demo-010",
        sender_email="vp.product@brex.com",
        sender_name="Karim Atiyeh",
        subject="Claude for expense intelligence + internal automation",
        body=(
            "Hello,\n\n"
            "Karim Atiyeh, VP of Product at Brex. We're the corporate card and spend management "
            "platform for tech companies.\n\n"
            "We see AI fitting in two places:\n"
            "- Product: intelligent expense categorization, policy compliance checking, "
            "anomaly detection on transactions, natural language spend queries\n"
            "- Internal: automating our finance ops, customer support responses, and "
            "compliance documentation across our 1,200-person team\n\n"
            "We've been building with a mix of OpenAI and in-house models. Evaluating whether "
            "to consolidate on a single provider. Cost and accuracy at scale are the key criteria.\n\n"
            "Our AI team lead ran some benchmarks and Claude Haiku looks promising for the "
            "high-volume transaction classification use case.\n\n"
            "Can you share volume pricing and set up a technical call?\n\n"
            "Karim\nVP Product, Brex"
        ),
        received_at="2026-03-07T11:45:00Z",
    ),
    # 11. Amplitude — product integration, researching
    RawEmail(
        email_id="demo-011",
        sender_email="engineering@amplitude.com",
        sender_name="Rachel Torres",
        subject="AI-powered analytics — exploring LLM options",
        body=(
            "Hi,\n\n"
            "Rachel Torres, Engineering Manager at Amplitude. We're building natural language "
            "querying for our product analytics platform — so customers can ask questions like "
            "'what caused our conversion drop last week?' instead of building complex funnels.\n\n"
            "We're in early research mode. Looked at OpenAI, Anthropic, and Cohere. "
            "No timeline yet but our VP of Engineering wants a recommendation by end of quarter.\n\n"
            "Key things we care about: SQL generation accuracy, ability to reason over charts "
            "and data visualizations, and cost at scale (we'd be processing millions of queries).\n\n"
            "Any resources you can share would be helpful.\n\n"
            "Rachel Torres\nEngineering Manager, Amplitude"
        ),
        received_at="2026-03-07T12:00:00Z",
    ),
    # 12. LaunchDarkly — internal productivity
    RawEmail(
        email_id="demo-012",
        sender_email="coo@launchdarkly.com",
        sender_name="Nadia Alramli",
        subject="Claude.ai Team plan for LaunchDarkly",
        body=(
            "Hi,\n\n"
            "Nadia here, COO at LaunchDarkly. We're a feature management platform with about "
            "600 employees. Several teams have been using individual Claude.ai accounts and "
            "the feedback has been overwhelmingly positive.\n\n"
            "I'd like to roll this out as a company-wide tool. Main use cases:\n"
            "- Engineering: code review, documentation, debugging\n"
            "- Marketing: content creation, competitive analysis\n"
            "- Sales: proposal drafting, call preparation\n"
            "- Legal: contract review, policy drafting\n\n"
            "What does Claude.ai Team or Enterprise pricing look like for ~600 seats? "
            "We need SSO (Okta), usage analytics, and data retention controls.\n\n"
            "Nadia Alramli\nCOO, LaunchDarkly"
        ),
        received_at="2026-03-07T12:30:00Z",
    ),
    # 13. Checkr — product integration, strong
    RawEmail(
        email_id="demo-013",
        sender_email="cto@checkr.com",
        sender_name="Daniel Yanisse",
        subject="Claude API for automated background check analysis",
        body=(
            "Hi Anthropic,\n\n"
            "Daniel Yanisse, CTO at Checkr. We run 20M+ background checks annually for "
            "companies like Uber, Instacart, and DoorDash.\n\n"
            "We want to use Claude to:\n"
            "- Extract and normalize data from court records and public databases\n"
            "- Classify adjudication outcomes with high accuracy\n"
            "- Generate candidate-friendly explanations of results\n"
            "- Reduce manual review by our compliance team (currently 40% of checks "
            "need human review)\n\n"
            "This is a regulated space — FCRA compliance is non-negotiable. We need to "
            "understand Claude's approach to hallucination prevention and how you handle "
            "sensitive PII.\n\n"
            "Budget is approved, we're choosing between Claude and a fine-tuned open-source "
            "approach. Timeline: decision by April 1.\n\n"
            "Daniel Yanisse\nCTO, Checkr"
        ),
        received_at="2026-03-07T13:00:00Z",
    ),
    # 14. Samsara — support ticket, not new business
    RawEmail(
        email_id="demo-014",
        sender_email="ops@samsara.com",
        sender_name="Samsara IT Support",
        subject="API rate limit errors on Claude Enterprise account",
        body=(
            "Hi Support,\n\n"
            "We're hitting 429 rate limit errors on our Claude Enterprise API account "
            "since yesterday afternoon. Our IoT data processing pipeline is backed up.\n\n"
            "Account ID: ent-samsara-prod-01\n"
            "Error rate: ~15% of requests in the last 12 hours\n"
            "Affected endpoint: /v1/messages\n"
            "Model: claude-sonnet-4\n\n"
            "This is impacting our production workload. Please escalate.\n\n"
            "Samsara IT Operations"
        ),
        received_at="2026-03-07T13:30:00Z",
    ),
    # 15. Loom — product integration, researching
    RawEmail(
        email_id="demo-015",
        sender_email="sanchan@atlassian.com",
        sender_name="Sanchan Saxena",
        subject="Exploring Claude for video AI features",
        body=(
            "Hey,\n\n"
            "Sanchan Saxena, Head of Loom Product Group at Atlassian. We do async video messaging — 25M+ users. "
            "We're thinking about next-gen AI features:\n\n"
            "- Automatic video summarization and chapters\n"
            "- Smart search across video libraries ('find the meeting where we discussed Q3 OKRs')\n"
            "- Auto-generated follow-up tasks from video content\n\n"
            "We're early stage — no vendor selected yet, no formal budget allocated. But our "
            "leadership is very bullish on AI features driving conversion from free to paid.\n\n"
            "Can we get access to the API to prototype? Also curious about your multimodal "
            "roadmap — video understanding would be a game-changer for us.\n\n"
            "Sanchan Saxena\nHead of Loom Product Group, Atlassian"
        ),
        received_at="2026-03-07T14:00:00Z",
    ),
    # 16. StubHub — enterprise AI standardization, CTO direct, competitive displacement
    RawEmail(
        email_id="demo-016",
        sender_email="art.yegorov@stubhub.com",
        sender_name="Art Yegorov",
        subject="Evaluating Claude for enterprise AI standardization",
        body=(
            "Hi,\n\n"
            "I'm the CTO at StubHub. We recently went public (NYSE: STUB) and I'm leading "
            "an initiative to standardize our AI tooling across the organization.\n\n"
            "We currently have multiple teams using OpenAI across customer support, internal "
            "productivity, and some agentic workflow prototypes — but without central oversight. "
            "We've been hitting hallucination issues that have made it upstream to product, and "
            "I want to evaluate alternatives before we commit to a -term enterprise agreement "
            "with any single provider.\n\n"
            "We're on GCP and use Vertex AI today, so integration there is a requirement. "
            "Our priority use cases are:\n"
            "- Internal productivity tools for engineering and ops (~300 engineers)\n"
            "- Customer support automation — we handle 120M+ buyers annually across 90 countries\n"
            "- Agentic workflows for our ticket pricing intelligence and fraud detection systems\n\n"
            "I'm particularly interested in Claude's consistency and safety track record versus "
            "what we've experienced so far. I have final approval on major technology purchases "
            "and want to see a technical evaluation completed this quarter.\n\n"
            "Let's set up an intro call. What does next week look like?\n\n"
            "Art Yegorov\nCTO, StubHub"
        ),
        received_at="2026-03-08T09:30:00Z",
    ),

]


class DemoEmailSource:
    def __init__(self, emails: list[RawEmail]) -> None:
        self._emails = emails

    def fetch(self, limit: int = 25) -> list[RawEmail]:
        return self._emails[:limit]


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

DB_PATH = "triage.db"
REPORTS_DIR = "reports"


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment or .env file.")
        print("Create a .env file with: ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)
    return key


def run_intake(demo: bool) -> None:
    api_key = _get_api_key()

    if demo:
        email_source = DemoEmailSource(DEMO_EMAILS)
    else:
        print("Live Gmail mode not yet implemented. Use --demo.")
        sys.exit(1)

    store = SqliteLeadStore(DB_PATH)
    scorer = LeadScorer(api_key=api_key)
    agent = IntakeAgent(email_source=email_source, scorer=scorer, store=store)

    print(f"\n{'='*70}")
    print("  INTAKE AGENT — Classifying, scoring & qualifying inbound emails")
    print(f"{'='*70}")

    results = agent.run(limit=25)

    for r in results:
        acv_str = f"${r.estimated_acv:,}" if r.estimated_acv else "TBD"
        provider_str = f" (from {r.current_ai_provider})" if r.current_ai_provider else ""
        print(f"\n  [{r.grade}] {r.total_score:3d}  {r.intent:<15s}  {r.sender_email}")
        print(f"       {r.summary}")
        print(f"       Use case: {r.use_case} | Stage: {r.buying_stage} | ACV: {acv_str}{provider_str}")
        print(f"       Product: {r.product_line_fit} | Tier: {r.deal_size_tier}")
        print(f"       Next: {r.next_best_action}")

        # MEDDPICC summary
        m = r.meddpicc
        known = sum(1 for v in [m.metrics, m.economic_buyer, m.decision_criteria,
                                m.decision_process, m.paper_process, m.implicate_pain,
                                m.champion, m.competition] if v == "known")
        partial = sum(1 for v in [m.metrics, m.economic_buyer, m.decision_criteria,
                                  m.decision_process, m.paper_process, m.implicate_pain,
                                  m.champion, m.competition] if v == "partial")
        print(f"       MEDDPICC: {known}/8 known, {partial}/8 partial")

    print(f"\n  Processed {len(results)} emails.")


def run_research(demo: bool) -> None:
    api_key = _get_api_key()
    agent = ResearchAgent(api_key=api_key, db_path=DB_PATH)

    print(f"\n{'='*70}")
    print("  RESEARCH AGENT — Enriching companies via web search")
    print(f"{'='*70}")

    delay = 8.0 if demo else 2.0
    limit = 5 if demo else 10
    results = agent.run(limit=limit, delay_seconds=delay)

    for r in results:
        print(f"\n  {r.company_name} ({r.company_domain or 'no domain'})")
        print(f"       {r.employee_range} | {r.funding_stage}")
        desc = r.description[:120] + "..." if len(r.description or "") > 120 else r.description
        print(f"       {desc}")

    print(f"\n  Researched {len(results)} companies.")


def run_briefing(demo: bool) -> None:
    api_key = _get_api_key()
    today = date.today().isoformat()

    agent = BriefingAgent(api_key=api_key, db_path=DB_PATH, reports_dir=REPORTS_DIR)

    print(f"\n{'='*70}")
    print(f"  BRIEFING AGENT — Generating daily report for {today}")
    print(f"{'='*70}")

    briefing = agent.run(briefing_date=today)

    print(f"\n  Executive Summary:")
    print(f"  {briefing.executive_summary}")
    print(f"\n  Top leads: {len(briefing.top_leads)}")
    for idx, lead in enumerate(briefing.top_leads[:5], start=1):
        print(f"    {idx}. [{lead.grade}] {lead.score} — {lead.company_name}")

    md_path = Path(REPORTS_DIR) / f"briefing_{today}.md"
    pptx_path = Path(REPORTS_DIR) / f"top_clients_{today}.pptx"
    print(f"\n  Markdown: {md_path}")
    print(f"  PowerPoint: {pptx_path}")


def run_full(demo: bool) -> None:
    start = time.time()

    print("\n" + "=" * 70)
    print("  EMAIL TRIAGE PIPELINE — Full Run (v2)")
    print("  15 real SF high-tech companies | MEDDPICC | ACV/TAM | Competitive Intel")
    print("=" * 70)

    if demo and Path(DB_PATH).exists():
        Path(DB_PATH).unlink()
        print("  (Cleared previous demo database)")

    run_intake(demo)
    run_research(demo)
    run_briefing(demo)

    elapsed = time.time() - start
    print(f"\n{'='*70}")
    print(f"  PIPELINE COMPLETE — {elapsed:.1f}s elapsed")
    print(f"{'='*70}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Email Triage Pipeline — AI-powered lead scoring, qualification, and briefing"
    )
    parser.add_argument(
        "stage",
        choices=["full", "intake", "research", "briefing"],
        help="Which pipeline stage to run",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use sample emails from real SF high-tech companies",
    )

    args = parser.parse_args()
    runners = {
        "full": run_full,
        "intake": run_intake,
        "research": run_research,
        "briefing": run_briefing,
    }
    runners[args.stage](args.demo)


if __name__ == "__main__":
    main()
