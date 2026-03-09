"""Call-prep endpoints — generate structured discovery call briefs via Claude."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from server.db import get_lead, get_lead_emails, get_linkedin_one, get_research_one

# Allow agent imports
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

router = APIRouter(prefix="/api/leads", tags=["call-prep"])


# ── Coercion helpers ─────────────────────────────────────────────


def _coerce_str_list(v: object) -> list[str]:
    """Accept a list or a newline-delimited string."""
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str):
        return [line for line in v.split("\n") if line.strip()]
    return []


def _coerce_objection_list(v: object) -> list[dict]:
    """Accept a list of dicts, a list of strings, or a single string."""
    if isinstance(v, list):
        out: list[dict] = []
        for item in v:
            if isinstance(item, dict):
                out.append({
                    "objection": str(item.get("objection", "")),
                    "response": str(item.get("response", "")),
                })
            else:
                out.append({"objection": str(item), "response": ""})
        return out
    if isinstance(v, str):
        return [{"objection": line, "response": ""} for line in v.split("\n") if line.strip()]
    return []


# ── Response schema ──────────────────────────────────────────────


class CallPrepResponse(BaseModel):
    contact_summary: str
    company_snapshot: str
    why_theyre_here: str
    current_stack: str
    suggested_agenda: list[str]
    discovery_questions: list[str]
    objection_prep: list[dict]  # [{objection, response}]
    competitive_positioning: str
    land_strategy: str
    expand_strategy: str
    proposed_next_step: str
    do_not_say: list[str]


class CallPrepPptxRequest(BaseModel):
    contact_summary: str = ""
    company_snapshot: str = ""
    why_theyre_here: str = ""
    current_stack: str = ""
    suggested_agenda: list[str] = []
    discovery_questions: list[str] = []
    objection_prep: list[dict] = []
    competitive_positioning: str = ""
    land_strategy: str = ""
    expand_strategy: str = ""
    proposed_next_step: str = ""
    do_not_say: list[str] = []

    @field_validator("suggested_agenda", "discovery_questions", "do_not_say", mode="before")
    @classmethod
    def _coerce_str_lists(cls, v: object) -> list[str]:
        return _coerce_str_list(v)

    @field_validator("objection_prep", mode="before")
    @classmethod
    def _coerce_objections(cls, v: object) -> list[dict]:
        return _coerce_objection_list(v)


# ── Helpers ──────────────────────────────────────────────────────


def _load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        from dotenv import load_dotenv
        load_dotenv(Path(PROJECT_ROOT) / ".env")
        key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    return key


def _gather_context(sender_email: str) -> dict:
    """Pull all available data for a lead from the database."""
    lead = get_lead(sender_email)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    emails = get_lead_emails(sender_email)
    linkedin = get_linkedin_one(sender_email)

    # Fetch research by domain or company name
    research = None
    if lead.get("company_domain"):
        research = get_research_one(lead["company_domain"])
    if not research and lead.get("company_name"):
        company_key = lead["company_name"].lower().replace(" ", "_")
        research = get_research_one(company_key)

    return {
        "lead": lead,
        "emails": emails,
        "linkedin": linkedin,
        "research": research,
    }


def _build_prompt(ctx: dict) -> str:
    """Build the Claude prompt from all available context."""
    lead = ctx["lead"]
    linkedin = ctx["linkedin"]
    research = ctx["research"]
    emails = ctx["emails"]

    sections = []

    # Lead data
    sections.append(f"""## Lead Profile
- Name: {lead.get('sender_name') or 'Unknown'}
- Email: {lead['sender_email']}
- Title: {lead.get('sender_title') or 'Unknown'}
- Company: {lead.get('company_name') or 'Unknown'}
- Domain: {lead.get('company_domain') or 'Unknown'}
- Grade: {lead.get('grade')} ({lead.get('score')}/100)
- Intent: {lead.get('intent')}
- Use Case: {lead.get('use_case')}
- Product Fit: {lead.get('product_line_fit')}
- Buying Stage: {lead.get('buying_stage')}
- Current AI Provider: {lead.get('current_ai_provider') or 'Unknown'}
- Estimated ACV: ${lead.get('estimated_acv') or 0:,}
- Deal Size Tier: {lead.get('deal_size_tier')}
- TAM Estimate: {lead.get('tam_estimate') or 'Unknown'}
- Expansion Potential: {lead.get('expansion_potential') or 'Unknown'}""")

    # Scoring breakdown
    sections.append(f"""## Scoring Breakdown
- Intent Score: {lead.get('intent_score')}/30
- Domain Quality: {lead.get('domain_quality_score')}/25
- Urgency: {lead.get('urgency_score')}/20
- Content Depth: {lead.get('content_depth_score')}/15
- Authority: {lead.get('authority_score')}/10
- Reasoning: {lead.get('last_reasoning') or 'None'}""")

    # MEDDPICC
    meddpicc = lead.get("meddpicc_json", {})
    if isinstance(meddpicc, dict) and meddpicc:
        meddpicc_lines = []
        for key, val in meddpicc.items():
            if isinstance(val, dict):
                status = val.get("status", "unknown")
                evidence = val.get("evidence", "")
                gap = val.get("gap", "")
                question = val.get("question", "")
                meddpicc_lines.append(
                    f"- {key}: status={status}, evidence={evidence}, gap={gap}, question={question}"
                )
            else:
                meddpicc_lines.append(f"- {key}: {val}")
        sections.append("## MEDDPICC Assessment\n" + "\n".join(meddpicc_lines))

    # Discovery questions
    disc_qs = lead.get("discovery_questions_json", [])
    if disc_qs:
        sections.append("## Existing Discovery Questions\n" + "\n".join(f"- {q}" for q in disc_qs))

    # Competitive signals
    comp_signals = lead.get("competitive_signals_json", [])
    if comp_signals:
        sections.append("## Competitive Signals\n" + "\n".join(f"- {s}" for s in comp_signals))

    # Partnership
    synergies = lead.get("partnership_synergies_json", [])
    detractors = lead.get("partnership_detractors_json", [])
    if synergies or detractors:
        parts = []
        if synergies:
            parts.append("Synergies:\n" + "\n".join(f"+ {s}" for s in synergies))
        if detractors:
            parts.append("Detractors:\n" + "\n".join(f"- {d}" for d in detractors))
        sections.append("## Partnership Analysis\n" + "\n".join(parts))

    # Next best action
    if lead.get("next_best_action"):
        sections.append(f"## Next Best Action\n{lead['next_best_action']}")

    # LinkedIn profile
    if linkedin:
        li_parts = [
            f"- Full Name: {linkedin.get('full_name') or 'Unknown'}",
            f"- Headline: {linkedin.get('headline') or 'Unknown'}",
            f"- Location: {linkedin.get('location') or 'Unknown'}",
            f"- Current Title: {linkedin.get('current_title') or 'Unknown'}",
            f"- Current Company: {linkedin.get('current_company') or 'Unknown'}",
        ]
        if linkedin.get("summary"):
            li_parts.append(f"- Summary: {linkedin['summary']}")

        exp = linkedin.get("experience_json", [])
        if exp:
            li_parts.append("Experience:")
            for e in exp[:5]:
                dur = f" ({e.get('duration', '')})" if e.get("duration") else ""
                li_parts.append(f"  - {e.get('title', '?')} at {e.get('company', '?')}{dur}")

        sections.append("## LinkedIn Profile\n" + "\n".join(li_parts))

    # Company research
    if research:
        res_parts = [
            f"- Company: {research.get('company_name')}",
            f"- Description: {research.get('description') or 'Unknown'}",
            f"- Employees: {research.get('employee_range') or 'Unknown'}",
            f"- Funding: {research.get('funding_stage') or 'Unknown'}",
        ]
        news = research.get("recent_news_json", [])
        if news:
            res_parts.append("Recent News:")
            for n in news[:5]:
                res_parts.append(f"  - {n.get('title', '')}: {n.get('summary', '')}")
        sections.append("## Company Research\n" + "\n".join(res_parts))

    # Emails
    if emails:
        email_parts = []
        for e in emails[:5]:
            email_parts.append(
                f"Subject: {e.get('subject', '')}\n"
                f"Date: {e.get('received_at', '')}\n"
                f"Body:\n{e.get('body', '')}\n---"
            )
        sections.append("## Email History\n" + "\n".join(email_parts))

    return "\n\n".join(sections)


# ── Endpoints ────────────────────────────────────────────────────


CALL_PREP_TOOL = {
    "name": "generate_call_prep",
    "description": "Generate a structured call preparation brief for a discovery call.",
    "input_schema": {
        "type": "object",
        "required": [
            "contact_summary", "company_snapshot", "why_theyre_here",
            "current_stack", "suggested_agenda", "discovery_questions",
            "objection_prep", "competitive_positioning", "land_strategy",
            "expand_strategy", "proposed_next_step", "do_not_say",
        ],
        "properties": {
            "contact_summary": {
                "type": "string",
                "description": "2-3 sentences: who you're talking to — name, title, background from LinkedIn, what they likely care about based on their inbound email and role.",
            },
            "company_snapshot": {
                "type": "string",
                "description": "One paragraph: company overview including estimated revenue, employees, funding stage, recent news, and relevant tech stack details.",
            },
            "why_theyre_here": {
                "type": "string",
                "description": "The specific pain points and motivations extracted from their inbound email. What triggered them to reach out.",
            },
            "current_stack": {
                "type": "string",
                "description": "What AI provider they use now and what's working/not working based on competitive signals and email content.",
            },
            "suggested_agenda": {
                "type": "array",
                "items": {"type": "string"},
                "description": "5-bullet meeting framework for a 25-minute discovery call.",
            },
            "discovery_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Top 5 questions tailored to this specific lead. Refine and improve the existing discovery questions based on all available context.",
            },
            "objection_prep": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "objection": {"type": "string"},
                        "response": {"type": "string"},
                    },
                    "required": ["objection", "response"],
                },
                "description": "2-3 likely objections based on their current provider and situation, with suggested responses.",
            },
            "competitive_positioning": {
                "type": "string",
                "description": "Claude's specific advantages vs their current provider for their specific use cases.",
            },
            "land_strategy": {
                "type": "string",
                "description": "What to propose as the initial deal — specific product, number of seats, and pricing approach.",
            },
            "expand_strategy": {
                "type": "string",
                "description": "The full account TAM and how to grow the deal over 12 months across departments and products.",
            },
            "proposed_next_step": {
                "type": "string",
                "description": "What to propose at the end of the call as the concrete next step.",
            },
            "do_not_say": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Things to avoid mentioning — e.g. don't trash their existing integration if they just shipped it, don't mention features that aren't GA yet.",
            },
        },
    },
}


@router.post("/{sender_email:path}/call-prep")
async def generate_call_prep(sender_email: str):
    """Generate a structured call-prep brief using Claude."""
    api_key = _load_api_key()
    ctx = _gather_context(sender_email)
    prompt = _build_prompt(ctx)

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        tools=[CALL_PREP_TOOL],
        tool_choice={"type": "tool", "name": "generate_call_prep"},
        messages=[
            {
                "role": "user",
                "content": (
                    "You are preparing a sales rep for a 25-minute discovery call. "
                    "Generate a comprehensive call preparation brief based on all the data below. "
                    "Be specific and actionable — reference actual details from the emails, LinkedIn profile, "
                    "and company research. Do not be generic.\n\n"
                    f"{prompt}"
                ),
            }
        ],
    )

    # Extract tool use result
    for block in response.content:
        if block.type == "tool_use" and block.name == "generate_call_prep":
            return block.input

    raise HTTPException(status_code=500, detail="Claude did not return a call-prep result")


@router.post("/{sender_email:path}/call-prep-pptx")
async def generate_call_prep_pptx(sender_email: str, data: CallPrepPptxRequest):
    """Generate a dark-themed PPTX deck from call-prep data."""
    lead = get_lead(sender_email)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    output_path = _build_call_prep_pptx(lead, data)
    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"call-prep-{lead.get('company_name', 'prospect').replace(' ', '-').lower()}.pptx",
    )


# ── PPTX builder ────────────────────────────────────────────────


def _build_call_prep_pptx(lead: dict, data: CallPrepPptxRequest) -> Path:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    # Dark theme colors
    BG = RGBColor(18, 17, 16)
    ACCENT = RGBColor(212, 165, 116)
    TEXT_PRIMARY = RGBColor(245, 240, 232)
    TEXT_SECONDARY = RGBColor(200, 195, 185)
    TEXT_MUTED = RGBColor(155, 150, 140)
    CARD_BG = RGBColor(30, 27, 24)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    def _set_slide_bg(slide, color=BG):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = color

    def _add_text(slide, x, y, w, h, text, size=12, bold=False, color=TEXT_PRIMARY, align=PP_ALIGN.LEFT):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.alignment = align
        return tf

    def _add_section_header(slide, x, y, w, text):
        return _add_text(slide, x, y, w, 0.4, text, size=14, bold=True, color=ACCENT)

    def _add_body_text(slide, x, y, w, h, text):
        return _add_text(slide, x, y, w, h, text, size=11, color=TEXT_SECONDARY)

    def _add_card_bg(slide, x, y, w, h):
        from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
        shape = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(y), Inches(w), Inches(h),
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = CARD_BG
        shape.line.fill.background()
        return shape

    company = lead.get("company_name") or "Prospect"
    contact = lead.get("sender_name") or "Contact"

    # ── Slide 1: Title ──
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(s1)
    _add_text(s1, 0.8, 0.6, 11, 0.5, "BLACKBURN COMMAND CENTER", size=11, bold=True, color=ACCENT)
    _add_text(s1, 0.8, 1.4, 11, 1.0, f"Discovery Call Prep:\n{company}", size=32, bold=True, color=TEXT_PRIMARY)
    _add_text(s1, 0.8, 3.2, 11, 0.5, f"Contact: {contact}  |  {date.today().strftime('%B %d, %Y')}", size=14, color=TEXT_SECONDARY)

    grade = lead.get("grade", "?")
    score = lead.get("score", 0)
    acv = lead.get("estimated_acv")
    acv_str = f"${acv:,}" if acv else "TBD"
    _add_text(s1, 0.8, 4.2, 11, 0.5, f"Grade: {grade}  |  Score: {score}/100  |  ACV: {acv_str}", size=13, color=TEXT_MUTED)

    # ── Slide 2: Contact & Company ──
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(s2)
    _add_text(s2, 0.8, 0.4, 11, 0.5, "Contact & Company", size=24, bold=True, color=TEXT_PRIMARY)

    _add_card_bg(s2, 0.6, 1.2, 5.6, 5.5)
    _add_section_header(s2, 0.9, 1.4, 5, "Who You're Meeting")
    _add_body_text(s2, 0.9, 1.9, 5, 4.5, data.contact_summary)

    _add_card_bg(s2, 6.6, 1.2, 6.0, 5.5)
    _add_section_header(s2, 6.9, 1.4, 5.4, "Company Snapshot")
    _add_body_text(s2, 6.9, 1.9, 5.4, 4.5, data.company_snapshot)

    # ── Slide 3: Why They're Here ──
    s3 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(s3)
    _add_text(s3, 0.8, 0.4, 11, 0.5, "Why They're Here", size=24, bold=True, color=TEXT_PRIMARY)

    _add_card_bg(s3, 0.6, 1.2, 5.6, 5.5)
    _add_section_header(s3, 0.9, 1.4, 5, "Pain Points & Motivations")
    _add_body_text(s3, 0.9, 1.9, 5, 4.5, data.why_theyre_here)

    _add_card_bg(s3, 6.6, 1.2, 6.0, 5.5)
    _add_section_header(s3, 6.9, 1.4, 5.4, "Current Stack")
    _add_body_text(s3, 6.9, 1.9, 5.4, 4.5, data.current_stack)

    # ── Slide 4: Meeting Agenda ──
    s4 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(s4)
    _add_text(s4, 0.8, 0.4, 11, 0.5, "25-Minute Discovery Agenda", size=24, bold=True, color=TEXT_PRIMARY)
    _add_card_bg(s4, 0.6, 1.2, 12, 5.5)
    y = 1.5
    for i, item in enumerate(data.suggested_agenda[:5], 1):
        _add_text(s4, 0.9, y, 11.4, 0.8, f"{i}.  {item}", size=14, color=TEXT_SECONDARY)
        y += 0.9

    # ── Slide 5: Discovery Questions ──
    s5 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(s5)
    _add_text(s5, 0.8, 0.4, 11, 0.5, "Tailored Discovery Questions", size=24, bold=True, color=TEXT_PRIMARY)
    _add_card_bg(s5, 0.6, 1.2, 12, 5.5)
    y = 1.5
    for i, q in enumerate(data.discovery_questions[:5], 1):
        _add_text(s5, 0.9, y, 11.4, 0.8, f"{i}.  {q}", size=13, color=TEXT_SECONDARY)
        y += 0.9

    # ── Slide 6: Objection Prep ──
    s6 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(s6)
    _add_text(s6, 0.8, 0.4, 11, 0.5, "Objection Prep", size=24, bold=True, color=TEXT_PRIMARY)
    y = 1.2
    for obj in data.objection_prep[:3]:
        _add_card_bg(s6, 0.6, y, 12, 1.6)
        _add_section_header(s6, 0.9, y + 0.15, 11, f"Objection: {obj.get('objection', '')}")
        _add_body_text(s6, 0.9, y + 0.6, 11.2, 0.8, f"Response: {obj.get('response', '')}")
        y += 1.9

    # ── Slide 7: Competitive Positioning ──
    s7 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(s7)
    _add_text(s7, 0.8, 0.4, 11, 0.5, "Competitive Positioning", size=24, bold=True, color=TEXT_PRIMARY)
    _add_card_bg(s7, 0.6, 1.2, 12, 5.5)
    _add_body_text(s7, 0.9, 1.5, 11.4, 5, data.competitive_positioning)

    # ── Slide 8: Deal Strategy ──
    s8 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(s8)
    _add_text(s8, 0.8, 0.4, 11, 0.5, "Deal Strategy", size=24, bold=True, color=TEXT_PRIMARY)

    _add_card_bg(s8, 0.6, 1.2, 5.6, 5.5)
    _add_section_header(s8, 0.9, 1.4, 5, "Land Motion")
    _add_body_text(s8, 0.9, 1.9, 5, 4.5, data.land_strategy)

    _add_card_bg(s8, 6.6, 1.2, 6.0, 5.5)
    _add_section_header(s8, 6.9, 1.4, 5.4, "Expand Motion (12-Month)")
    _add_body_text(s8, 6.9, 1.9, 5.4, 4.5, data.expand_strategy)

    # ── Slide 9: Next Steps + Do Not Say ──
    s9 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(s9)
    _add_text(s9, 0.8, 0.4, 11, 0.5, "Proposed Next Steps", size=24, bold=True, color=TEXT_PRIMARY)

    _add_card_bg(s9, 0.6, 1.2, 5.6, 5.5)
    _add_section_header(s9, 0.9, 1.4, 5, "End-of-Call Proposal")
    _add_body_text(s9, 0.9, 1.9, 5, 4.5, data.proposed_next_step)

    _add_card_bg(s9, 6.6, 1.2, 6.0, 5.5)
    _add_section_header(s9, 6.9, 1.4, 5.4, "Do Not Say")
    y_dns = 1.9
    for item in data.do_not_say[:5]:
        _add_text(s9, 6.9, y_dns, 5.4, 0.6, f"  {item}", size=11, color=RGBColor(230, 120, 120))
        y_dns += 0.6

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    prs.save(tmp.name)
    return Path(tmp.name)
