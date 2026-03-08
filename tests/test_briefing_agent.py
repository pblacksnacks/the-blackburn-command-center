import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.report_formatter import DailyBriefing, LeadCard, format_markdown_briefing, build_pptx_deck


def _sample_briefing() -> DailyBriefing:
    return DailyBriefing(
        briefing_date="2026-03-07",
        total_new=15,
        total_updated=0,
        grade_distribution={"A": 4, "B": 5, "C": 3, "D": 3},
        top_intents={"new_business": 12, "support": 1, "partnership": 1, "spam": 1},
        executive_summary="Strong pipeline day with four Grade A opportunities. Notion and Figma are ready-to-buy product integration deals totaling $650K+ ACV. Three active bake-offs need immediate attention.",
        pipeline_value="$1.85M estimated (A+B leads)",
        quick_wins=[
            "Notion — Grade A, $350K ACV, VP Engineering ready to sign enterprise API deal",
            "Ironclad — Grade A, $400K ACV, CEO presenting to board next week",
        ],
        needs_attention=[
            "Figma bake-off — decision by end of March, need technical deep-dive",
            "Verkada switching from GPT-4V — procurement deadline April 15",
        ],
        top_leads=[
            LeadCard(
                company_name="Notion",
                sender_name="Raj Mehta",
                sender_title="VP Engineering",
                sender_email="vp.engineering@notion.so",
                grade="A",
                score=94,
                why_hot="VP Engineering wants to migrate from OpenAI to Claude for Notion AI features. 50B tokens/month, CTO involved.",
                company_context="Leading productivity platform with 100M+ users. Currently on OpenAI, benchmarked Claude Sonnet with better results.",
                suggested_approach="Fast-track technical deep-dive. Emphasize long-context quality advantage and enterprise throughput guarantees.",
                suggested_opener="Raj, great to hear Claude won your benchmark. Let's map the migration path — I can get our API partnerships team on a call this week.",
                key_signals=["switching from OpenAI", "50B tokens/month", "CTO joining call", "Q2 deadline"],
                use_case="product_integration",
                estimated_acv=350000,
                meddpicc_summary="6/8 known: strong on EB, DC, DP, IP, CH, CO. Gaps: Metrics (need ROI framework), Paper Process (contract terms TBD).",
                competitive_landscape="Active switch from OpenAI. Claude won quality benchmark on summarization. GPT-4o slightly faster on simple tasks.",
                top_discovery_question="What does your procurement process look like for a deal this size, and who needs to sign off?",
            ),
        ],
    )


def test_markdown_contains_pipeline_value():
    briefing = _sample_briefing()
    md = format_markdown_briefing(briefing)
    assert "$1.85M" in md
    assert "Notion" in md
    assert "MEDDPICC" in md


def test_markdown_contains_acv():
    briefing = _sample_briefing()
    md = format_markdown_briefing(briefing)
    assert "$350,000" in md
    assert "product_integration" in md or "Product Integration" in md


def test_markdown_contains_competitive():
    briefing = _sample_briefing()
    md = format_markdown_briefing(briefing)
    assert "Competitive landscape" in md
    assert "OpenAI" in md


def test_pptx_file_is_written(tmp_path: Path):
    briefing = _sample_briefing()
    output = tmp_path / "deck.pptx"
    build_pptx_deck(briefing, output)
    assert output.exists()
    assert output.stat().st_size > 0
