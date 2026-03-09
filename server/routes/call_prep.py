"""Call-prep endpoints — generate structured discovery call briefs via Claude."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, timedelta
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


class CallPrepExportRequest(BaseModel):
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


# Keep old name as alias so existing imports don't break
CallPrepPptxRequest = CallPrepExportRequest


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


# ── A) Pre-Call Brief PDF ────────────────────────────────────────


@router.post("/{sender_email:path}/call-prep-pdf")
async def generate_call_prep_pdf(sender_email: str, data: CallPrepExportRequest):
    """Generate a dense single-page PDF reference brief."""
    lead = get_lead(sender_email)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    output_path = _build_call_prep_pdf(lead, data)
    return FileResponse(
        path=str(output_path),
        media_type="application/pdf",
        filename=f"pre-call-brief-{lead.get('company_name', 'prospect').replace(' ', '-').lower()}.pdf",
    )


def _build_call_prep_pdf(lead: dict, data: CallPrepExportRequest) -> Path:
    from fpdf import FPDF

    company = lead.get("company_name") or "Prospect"
    contact = lead.get("sender_name") or "Contact"
    title_str = lead.get("sender_title") or ""
    grade = lead.get("grade", "?")
    score = lead.get("score", 0)
    acv = lead.get("estimated_acv")
    acv_str = f"${acv:,}" if acv else "TBD"
    today = date.today().strftime("%B %d, %Y")

    pdf = FPDF(orientation="L", unit="mm", format="letter")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    W = pdf.w  # 279.4mm
    H = pdf.h  # 215.9mm
    M = 8  # margin

    # ── Dark header bar ──
    pdf.set_fill_color(26, 26, 26)
    pdf.rect(0, 0, W, 18, "F")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(M, 4)
    pdf.cell(0, 5, f"PRE-CALL BRIEF: {company.upper()}", new_x="LMARGIN")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(M, 10)
    header_detail = f"{contact}"
    if title_str:
        header_detail += f", {title_str}"
    header_detail += f"   |   Grade {grade}  ({score}/100)   |   ACV {acv_str}   |   {today}"
    pdf.cell(0, 4, header_detail, new_x="LMARGIN")

    # ── Accent line ──
    pdf.set_draw_color(212, 165, 116)
    pdf.set_line_width(0.8)
    pdf.line(0, 18, W, 18)

    # ── Layout constants ──
    COL_W = (W - M * 3) / 2  # two columns with center gap
    LEFT_X = M
    RIGHT_X = M + COL_W + M
    START_Y = 22
    LINE_H = 3.6
    SECTION_GAP = 2

    def _truncate(text: str, max_lines: int, line_chars: int = 80) -> str:
        """Wrap and truncate text to max_lines."""
        words = text.replace("\n", " ").split()
        lines: list[str] = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if len(test) > line_chars:
                lines.append(current)
                current = w
                if len(lines) >= max_lines:
                    break
            else:
                current = test
        if current and len(lines) < max_lines:
            lines.append(current)
        return "\n".join(lines[:max_lines])

    def _section_header(x: float, y: float, text: str) -> float:
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(212, 165, 116)
        pdf.set_xy(x, y)
        pdf.cell(COL_W, LINE_H, text.upper(), new_x="LMARGIN")
        # Divider line
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.15)
        pdf.line(x, y + LINE_H + 0.3, x + COL_W, y + LINE_H + 0.3)
        return y + LINE_H + 1.5

    def _body_text(x: float, y: float, text: str, max_lines: int = 3) -> float:
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(50, 50, 50)
        content = _truncate(text, max_lines)
        for line in content.split("\n"):
            pdf.set_xy(x, y)
            pdf.cell(COL_W, LINE_H, line, new_x="LMARGIN")
            y += LINE_H
        return y + SECTION_GAP

    def _bullet_list(x: float, y: float, items: list[str], max_items: int = 5, prefix: str = "") -> float:
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(50, 50, 50)
        for i, item in enumerate(items[:max_items]):
            label = f"{prefix}{i + 1}. " if prefix == "" else f"{prefix} "
            if prefix == "":
                label = f"{i + 1}. "
            text = _truncate(item, 1, line_chars=75)
            pdf.set_xy(x, y)
            pdf.cell(COL_W, LINE_H, f"{label}{text}", new_x="LMARGIN")
            y += LINE_H
        return y + SECTION_GAP

    # ── LEFT COLUMN ──
    y = START_Y

    y = _section_header(LEFT_X, y, "Contact Summary")
    y = _body_text(LEFT_X, y, data.contact_summary, max_lines=3)

    y = _section_header(LEFT_X, y, "Why They're Here")
    y = _body_text(LEFT_X, y, data.why_theyre_here, max_lines=3)

    y = _section_header(LEFT_X, y, "Current Stack")
    y = _body_text(LEFT_X, y, data.current_stack, max_lines=2)

    y = _section_header(LEFT_X, y, "Competitive Positioning")
    # Extract up to 3 bullet points from competitive positioning text
    comp_text = data.competitive_positioning
    comp_sentences = [s.strip() for s in comp_text.replace("\n", ". ").split(". ") if s.strip()]
    comp_bullets = comp_sentences[:3] if comp_sentences else [comp_text]
    for bullet in comp_bullets:
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(50, 50, 50)
        text = _truncate(bullet, 1, line_chars=75)
        pdf.set_xy(LEFT_X, y)
        pdf.cell(COL_W, LINE_H, f"  {text}", new_x="LMARGIN")
        y += LINE_H
    y += SECTION_GAP

    y = _section_header(LEFT_X, y, "Suggested Agenda")
    y = _bullet_list(LEFT_X, y, data.suggested_agenda, max_items=5)

    # ── RIGHT COLUMN ──
    y = START_Y

    y = _section_header(RIGHT_X, y, "Discovery Questions")
    y = _bullet_list(RIGHT_X, y, data.discovery_questions, max_items=5)

    y = _section_header(RIGHT_X, y, "Objection Prep")
    pdf.set_font("Helvetica", "", 7)
    for obj in data.objection_prep[:3]:
        objection = obj.get("objection", "")
        response = obj.get("response", "")
        pdf.set_text_color(180, 60, 60)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_xy(RIGHT_X, y)
        pdf.cell(COL_W, LINE_H, f"  {_truncate(objection, 1, 70)}", new_x="LMARGIN")
        y += LINE_H
        pdf.set_text_color(50, 50, 50)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_xy(RIGHT_X + 3, y)
        pdf.cell(COL_W - 3, LINE_H, _truncate(response, 1, 68), new_x="LMARGIN")
        y += LINE_H + 1
    y += SECTION_GAP

    y = _section_header(RIGHT_X, y, "Proposed Next Step")
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(26, 26, 26)
    next_step = _truncate(data.proposed_next_step, 2, 75)
    for line in next_step.split("\n"):
        pdf.set_xy(RIGHT_X, y)
        pdf.cell(COL_W, LINE_H, line, new_x="LMARGIN")
        y += LINE_H
    y += SECTION_GAP

    y = _section_header(RIGHT_X, y, "Deal Strategy")
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(50, 50, 50)
    pdf.set_xy(RIGHT_X, y)
    pdf.cell(COL_W, LINE_H, f"Land: {_truncate(data.land_strategy, 1, 70)}", new_x="LMARGIN")
    y += LINE_H
    pdf.set_xy(RIGHT_X, y)
    pdf.cell(COL_W, LINE_H, f"Expand: {_truncate(data.expand_strategy, 1, 68)}", new_x="LMARGIN")
    y += LINE_H + SECTION_GAP

    # ── Footer: Do Not Say ──
    footer_y = H - 12
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.15)
    pdf.line(M, footer_y, W - M, footer_y)
    footer_y += 1.5
    pdf.set_font("Helvetica", "BI", 6)
    pdf.set_text_color(180, 60, 60)
    pdf.set_xy(M, footer_y)
    dns_items = data.do_not_say[:5]
    dns_text = "DO NOT SAY:  " + "   |   ".join(dns_items) if dns_items else ""
    pdf.cell(W - M * 2, LINE_H, dns_text, new_x="LMARGIN")

    # Confidential footer
    pdf.set_font("Helvetica", "I", 5)
    pdf.set_text_color(150, 150, 150)
    pdf.set_xy(M, H - 6)
    pdf.cell(W - M * 2, 3, "INTERNAL USE ONLY  |  Blackburn Command Center  |  Generated by Claude", new_x="LMARGIN")

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    pdf.output(tmp.name)
    return Path(tmp.name)


# ── B) Customer-Facing PPTX Deck ────────────────────────────────


@router.post("/{sender_email:path}/call-prep-pptx")
async def generate_call_prep_pptx(sender_email: str, data: CallPrepExportRequest):
    """Generate an Anthropic-branded customer-facing PPTX deck with speaker notes."""
    lead = get_lead(sender_email)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    output_path = _build_customer_deck(lead, data)
    return FileResponse(
        path=str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"anthropic-{lead.get('company_name', 'prospect').replace(' ', '-').lower()}.pptx",
    )


def _build_customer_deck(lead: dict, data: CallPrepExportRequest) -> Path:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt, Emu

    # Anthropic brand colors
    BG_CREAM = RGBColor(245, 240, 232)       # #F5F0E8
    TEXT_DARK = RGBColor(26, 26, 26)          # #1A1A1A
    TEXT_BODY = RGBColor(68, 64, 60)          # #44403C
    ACCENT = RGBColor(212, 165, 116)          # #D4A574
    ACCENT_DARK = RGBColor(170, 130, 85)      # slightly darker accent
    MUTED = RGBColor(140, 135, 125)           # muted text
    WHITE = RGBColor(255, 255, 255)

    company = lead.get("company_name") or "Your Company"
    contact = lead.get("sender_name") or "Contact"
    today_str = date.today().strftime("%B %d, %Y")
    acv = lead.get("estimated_acv")
    acv_str = f"${acv:,}" if acv else "TBD"

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    def _set_bg(slide, color=BG_CREAM):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = color

    def _add_text(slide, x, y, w, h, text, size=12, bold=False, color=TEXT_DARK, align=PP_ALIGN.LEFT, font_name="Calibri"):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.font.name = font_name
        p.alignment = align
        return tf

    def _add_multiline(slide, x, y, w, h, lines, size=14, color=TEXT_BODY, bold=False, spacing=1.2, font_name="Calibri"):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line
            p.font.size = Pt(size)
            p.font.bold = bold
            p.font.color.rgb = color
            p.font.name = font_name
            p.space_after = Pt(size * spacing * 0.4)
        return tf

    def _add_notes(slide, text: str):
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = text

    def _accent_bar(slide, x, y, w, h):
        from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
        shape = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.RECTANGLE,
            Inches(x), Inches(y), Inches(w), Inches(h),
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = ACCENT
        shape.line.fill.background()
        return shape

    def _card_shape(slide, x, y, w, h, fill_color=WHITE):
        from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
        shape = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(y), Inches(w), Inches(h),
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
        shape.line.color.rgb = RGBColor(220, 215, 205)
        shape.line.width = Pt(0.5)
        return shape

    # ════════════════════════════════════════════════════════════════
    # SLIDE 1 — Title
    # ════════════════════════════════════════════════════════════════
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(s1)
    _accent_bar(s1, 0, 0, 13.333, 0.08)

    _add_text(s1, 1.0, 0.6, 6, 0.5, "anthropic", size=14, color=ACCENT, bold=True)
    _add_text(s1, 1.0, 2.0, 10, 1.5,
              f"Partnering with {company}\non AI", size=40, bold=True, color=TEXT_DARK)
    _accent_bar(s1, 1.0, 4.0, 1.5, 0.06)
    _add_text(s1, 1.0, 4.4, 8, 0.5,
              f"Prepared for {contact}  |  {today_str}", size=16, color=MUTED)

    _add_notes(s1, (
        f"INTRO TALK TRACK\n\n"
        f"Thank {contact} for taking the time. Reference their inbound interest.\n\n"
        f"Context:\n{data.contact_summary}\n\n"
        f"Company background:\n{data.company_snapshot}\n\n"
        f"Key: Establish credibility, show you've done homework, set collaborative tone. "
        f"This is a conversation, not a pitch."
    ))

    # ════════════════════════════════════════════════════════════════
    # SLIDE 2 — Agenda
    # ════════════════════════════════════════════════════════════════
    s2 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(s2)
    _accent_bar(s2, 0, 0, 13.333, 0.08)

    _add_text(s2, 1.0, 0.6, 6, 0.5, "anthropic", size=14, color=ACCENT, bold=True)
    _add_text(s2, 1.0, 1.2, 10, 0.8, "Today's Agenda", size=32, bold=True, color=TEXT_DARK)
    _accent_bar(s2, 1.0, 2.1, 1.0, 0.05)

    agenda_items = data.suggested_agenda[:5]
    time_allocs = ["5 min", "5 min", "5 min", "5 min", "5 min"]
    if len(agenda_items) == 5:
        time_allocs = ["3 min", "5 min", "7 min", "5 min", "5 min"]
    elif len(agenda_items) == 4:
        time_allocs = ["3 min", "7 min", "8 min", "7 min"]

    y_pos = 2.6
    for i, item in enumerate(agenda_items):
        _card_shape(s2, 1.0, y_pos, 11.0, 0.8)
        _add_text(s2, 1.3, y_pos + 0.15, 0.8, 0.5,
                  time_allocs[i] if i < len(time_allocs) else "5 min",
                  size=11, color=ACCENT, bold=True)
        _add_text(s2, 2.3, y_pos + 0.15, 9.5, 0.5,
                  item, size=14, color=TEXT_BODY)
        y_pos += 0.95

    notes_agenda = "AGENDA FRAMING\n\n"
    for i, item in enumerate(agenda_items):
        t = time_allocs[i] if i < len(time_allocs) else "5 min"
        notes_agenda += f"{i+1}. ({t}) {item}\n"
    notes_agenda += (
        f"\nHow to frame: 'I want to make sure we use our time well. "
        f"I'd love to start by understanding your current landscape, "
        f"then share how we might be able to help, and end with clear next steps. "
        f"Does that work?'"
    )
    _add_notes(s2, notes_agenda)

    # ════════════════════════════════════════════════════════════════
    # SLIDE 3 — Understanding Your AI Landscape
    # ════════════════════════════════════════════════════════════════
    s3 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(s3)
    _accent_bar(s3, 0, 0, 13.333, 0.08)

    _add_text(s3, 1.0, 0.6, 6, 0.5, "anthropic", size=14, color=ACCENT, bold=True)
    _add_text(s3, 1.0, 1.2, 10, 0.8, "Understanding Your AI Landscape", size=32, bold=True, color=TEXT_DARK)
    _accent_bar(s3, 1.0, 2.1, 1.0, 0.05)

    # Extract 3 challenge statements from why_theyre_here and current_stack
    challenges = []
    why_sentences = [s.strip() for s in data.why_theyre_here.replace("\n", ". ").split(". ") if s.strip()]
    stack_sentences = [s.strip() for s in data.current_stack.replace("\n", ". ").split(". ") if s.strip()]
    all_sentences = why_sentences + stack_sentences
    for s in all_sentences:
        if len(s) > 15:
            challenges.append(s)
        if len(challenges) >= 3:
            break
    while len(challenges) < 3:
        challenges.append("Exploring new AI capabilities for your team")

    card_x_positions = [1.0, 4.8, 8.6]
    for i, challenge in enumerate(challenges[:3]):
        _card_shape(s3, card_x_positions[i], 2.8, 3.5, 3.5)
        _accent_bar(s3, card_x_positions[i], 2.8, 3.5, 0.06)
        _add_text(s3, card_x_positions[i] + 0.3, 3.2, 2.9, 0.4,
                  f"0{i+1}", size=28, bold=True, color=ACCENT)
        _add_text(s3, card_x_positions[i] + 0.3, 3.9, 2.9, 2.2,
                  challenge, size=14, color=TEXT_BODY)

    notes_landscape = (
        f"DISCOVERY SECTION\n\n"
        f"Why they're here:\n{data.why_theyre_here}\n\n"
        f"Current stack:\n{data.current_stack}\n\n"
        f"DISCOVERY QUESTIONS TO ASK:\n"
    )
    for i, q in enumerate(data.discovery_questions[:5], 1):
        notes_landscape += f"{i}. {q}\n"
    notes_landscape += (
        f"\nListen more than you talk in this section. Use these questions "
        f"to uncover the real pain. Take notes on what they say — you'll "
        f"reference it in the next section."
    )
    _add_notes(s3, notes_landscape)

    # ════════════════════════════════════════════════════════════════
    # SLIDE 4 — Why Claude for {company}
    # ════════════════════════════════════════════════════════════════
    s4 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(s4)
    _accent_bar(s4, 0, 0, 13.333, 0.08)

    _add_text(s4, 1.0, 0.6, 6, 0.5, "anthropic", size=14, color=ACCENT, bold=True)
    _add_text(s4, 1.0, 1.2, 10, 0.8, f"Why Claude for {company}", size=32, bold=True, color=TEXT_DARK)
    _accent_bar(s4, 1.0, 2.1, 1.0, 0.05)

    # Extract advantages from competitive positioning
    comp_sentences = [s.strip() for s in data.competitive_positioning.replace("\n", ". ").split(". ") if len(s.strip()) > 10]
    advantages = []
    for i in range(0, len(comp_sentences), max(1, len(comp_sentences) // 3)):
        group = comp_sentences[i:i + max(1, len(comp_sentences) // 3)]
        if group:
            # First sentence as headline, rest as supporting
            advantages.append({
                "headline": group[0],
                "detail": " ".join(group[1:]) if len(group) > 1 else "",
            })
        if len(advantages) >= 3:
            break
    while len(advantages) < 3:
        advantages.append({"headline": "Purpose-built AI that works for your team", "detail": ""})

    y_pos = 2.8
    for i, adv in enumerate(advantages[:3]):
        _card_shape(s4, 1.0, y_pos, 11.0, 1.3)
        _accent_bar(s4, 1.0, y_pos, 0.08, 1.3)
        _add_text(s4, 1.4, y_pos + 0.15, 10.4, 0.5,
                  adv["headline"], size=18, bold=True, color=TEXT_DARK)
        if adv["detail"]:
            _add_text(s4, 1.4, y_pos + 0.7, 10.4, 0.5,
                      adv["detail"][:150], size=12, color=TEXT_BODY)
        y_pos += 1.5

    notes_why = (
        f"COMPETITIVE POSITIONING DETAIL\n\n"
        f"{data.competitive_positioning}\n\n"
        f"OBJECTION RESPONSES:\n"
    )
    for obj in data.objection_prep[:3]:
        notes_why += f"\nObjection: {obj.get('objection', '')}\n"
        notes_why += f"Response: {obj.get('response', '')}\n"
    notes_why += (
        f"\nKey: Connect advantages to THEIR specific pain points. "
        f"Reference what they said in the discovery section. "
        f"'Based on what you shared about X, here's why Claude is a good fit...'"
    )
    _add_notes(s4, notes_why)

    # ════════════════════════════════════════════════════════════════
    # SLIDE 5 — Proposed Pilot Program
    # ════════════════════════════════════════════════════════════════
    s5 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(s5)
    _accent_bar(s5, 0, 0, 13.333, 0.08)

    _add_text(s5, 1.0, 0.6, 6, 0.5, "anthropic", size=14, color=ACCENT, bold=True)
    _add_text(s5, 1.0, 1.2, 10, 0.8, "Proposed Pilot Program", size=32, bold=True, color=TEXT_DARK)
    _accent_bar(s5, 1.0, 2.1, 1.0, 0.05)

    # Extract land strategy short description
    land_short = data.land_strategy.split(".")[0] if "." in data.land_strategy else data.land_strategy
    expand_short = data.expand_strategy.split(".")[0] if "." in data.expand_strategy else data.expand_strategy

    phases = [
        {"label": "PHASE 1", "time": "30 Days", "desc": f"Pilot: {land_short[:80]}", "value": acv_str},
        {"label": "PHASE 2", "time": "90 Days", "desc": f"Expand: {expand_short[:80]}", "value": ""},
        {"label": "PHASE 3", "time": "12 Months", "desc": f"Full deployment across organization", "value": lead.get("tam_estimate") or ""},
    ]

    # Timeline visual
    # Connector line
    from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
    line_shape = s5.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(1.5), Inches(3.45), Inches(10.0), Inches(0.06),
    )
    line_shape.fill.solid()
    line_shape.fill.fore_color.rgb = ACCENT
    line_shape.line.fill.background()

    phase_x = [1.2, 5.0, 8.8]
    for i, phase in enumerate(phases):
        # Circle node
        circle = s5.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            Inches(phase_x[i] + 1.3), Inches(3.15), Inches(0.7), Inches(0.7),
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = ACCENT if i == 0 else BG_CREAM
        circle.line.color.rgb = ACCENT
        circle.line.width = Pt(2)

        _add_text(s5, phase_x[i] + 1.3, 3.2, 0.7, 0.6,
                  str(i + 1), size=20, bold=True,
                  color=WHITE if i == 0 else ACCENT,
                  align=PP_ALIGN.CENTER)

        # Card below
        _card_shape(s5, phase_x[i], 4.2, 3.6, 2.3)
        _add_text(s5, phase_x[i] + 0.2, 4.35, 3.2, 0.4,
                  f"{phase['label']}  —  {phase['time']}",
                  size=11, bold=True, color=ACCENT)
        _add_text(s5, phase_x[i] + 0.2, 4.85, 3.2, 1.0,
                  phase["desc"], size=13, color=TEXT_BODY)
        if phase["value"]:
            _add_text(s5, phase_x[i] + 0.2, 5.9, 3.2, 0.4,
                      phase["value"], size=16, bold=True, color=TEXT_DARK)

    notes_pilot = (
        f"FULL DEAL STRATEGY\n\n"
        f"LAND STRATEGY:\n{data.land_strategy}\n\n"
        f"EXPAND STRATEGY (12-MONTH):\n{data.expand_strategy}\n\n"
        f"ACV Target: {acv_str}\n"
        f"TAM Estimate: {lead.get('tam_estimate') or 'TBD'}\n"
        f"Expansion Potential: {lead.get('expansion_potential') or 'TBD'}\n\n"
        f"Present this as a low-risk starting point. Emphasize time-to-value. "
        f"Phase 1 should feel easy to say yes to."
    )
    _add_notes(s5, notes_pilot)

    # ════════════════════════════════════════════════════════════════
    # SLIDE 6 — Next Steps
    # ════════════════════════════════════════════════════════════════
    s6 = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(s6)
    _accent_bar(s6, 0, 0, 13.333, 0.08)

    _add_text(s6, 1.0, 0.6, 6, 0.5, "anthropic", size=14, color=ACCENT, bold=True)
    _add_text(s6, 1.0, 1.2, 10, 0.8, "Next Steps", size=32, bold=True, color=TEXT_DARK)
    _accent_bar(s6, 1.0, 2.1, 1.0, 0.05)

    # Build next steps from proposed_next_step
    next_step_items = [s.strip() for s in data.proposed_next_step.replace("\n", ". ").split(". ") if len(s.strip()) > 5]
    # Build 2-3 action items with dates
    d1 = (date.today() + timedelta(days=2)).strftime("%b %d")
    d2 = (date.today() + timedelta(days=7)).strftime("%b %d")
    d3 = (date.today() + timedelta(days=14)).strftime("%b %d")

    action_items = []
    if next_step_items:
        action_items.append({"action": next_step_items[0], "owner": "Parker / Anthropic", "date": d1})
    if len(next_step_items) > 1:
        action_items.append({"action": next_step_items[1], "owner": contact, "date": d2})
    else:
        action_items.append({"action": "Technical deep-dive with your engineering team", "owner": contact, "date": d2})
    action_items.append({"action": "Pilot kickoff with success criteria defined", "owner": "Joint", "date": d3})

    # Table-like layout
    _card_shape(s6, 1.0, 2.6, 11.0, 0.6, fill_color=RGBColor(235, 230, 222))
    _add_text(s6, 1.3, 2.7, 6, 0.4, "Action Item", size=11, bold=True, color=MUTED)
    _add_text(s6, 8.0, 2.7, 2, 0.4, "Owner", size=11, bold=True, color=MUTED)
    _add_text(s6, 10.5, 2.7, 2, 0.4, "Target Date", size=11, bold=True, color=MUTED)

    y_pos = 3.3
    for item in action_items[:3]:
        _card_shape(s6, 1.0, y_pos, 11.0, 0.8)
        _add_text(s6, 1.3, y_pos + 0.15, 6.5, 0.5,
                  item["action"][:90], size=14, color=TEXT_BODY)
        _add_text(s6, 8.0, y_pos + 0.15, 2, 0.5,
                  item["owner"], size=12, color=TEXT_BODY)
        _add_text(s6, 10.5, y_pos + 0.15, 2, 0.5,
                  item["date"], size=12, bold=True, color=ACCENT)
        y_pos += 0.95

    # Contact info
    _add_text(s6, 1.0, 6.3, 10, 0.5,
              "Parker Blackburn  |  parker@anthropic.com  |  Anthropic",
              size=12, color=MUTED)

    notes_next = (
        f"CLOSING SECTION\n\n"
        f"Proposed next step:\n{data.proposed_next_step}\n\n"
        f"Push for a specific date and time. Don't leave with 'we'll follow up.' "
        f"Ideal outcome: calendar invite sent before the call ends.\n\n"
        f"DO NOT SAY:\n"
    )
    for item in data.do_not_say[:5]:
        notes_next += f"- {item}\n"
    _add_notes(s6, notes_next)

    # Save
    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    prs.save(tmp.name)
    return Path(tmp.name)
