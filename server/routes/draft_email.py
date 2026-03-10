"""Draft-email endpoints — generate personalized outreach emails via Claude."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from server.routes.call_prep import _load_api_key, _gather_context, _build_prompt

router = APIRouter(prefix="/api/leads", tags=["draft-email"])


DRAFT_EMAIL_TOOL = {
    "name": "generate_draft_email",
    "description": "Generate a personalized first-touch outreach email and follow-up.",
    "input_schema": {
        "type": "object",
        "required": ["subject", "body", "follow_up_subject", "follow_up_body"],
        "properties": {
            "subject": {
                "type": "string",
                "description": (
                    "A compelling, personalized email subject line. "
                    "Should hint at value without being clickbait."
                ),
            },
            "body": {
                "type": "string",
                "description": (
                    "The full email body, personalized to the lead's specific situation, "
                    "pain points, and use case. Reference something specific about their "
                    "company or role to show it's not a template. Keep under 200 words. "
                    "Professional but warm tone. Include a clear CTA (schedule a call, "
                    "see a demo, etc). Use line breaks between paragraphs."
                ),
            },
            "follow_up_subject": {
                "type": "string",
                "description": (
                    "A follow-up email subject line if they don't respond within 3 days."
                ),
            },
            "follow_up_body": {
                "type": "string",
                "description": (
                    "A shorter follow-up email body (under 100 words). Reference the "
                    "original email. Add new value or a different angle. "
                    "Use line breaks between paragraphs."
                ),
            },
        },
    },
}


@router.post("/{sender_email:path}/draft-email")
async def draft_email(sender_email: str):
    """Generate a personalized outreach email using Claude."""
    api_key = _load_api_key()
    ctx = _gather_context(sender_email)
    prompt = _build_prompt(ctx)

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    lead = ctx["lead"]
    sender_name = lead.get("sender_name") or "the contact"
    company = lead.get("company_name") or "their company"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        tools=[DRAFT_EMAIL_TOOL],
        tool_choice={"type": "tool", "name": "generate_draft_email"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"You are Parker Blackburn, an account executive at {'GitLab' if os.environ.get('GITLAB_MODE', 'false').lower() == 'true' else 'Anthropic'}. "
                    "Write a personalized first-touch outreach email to this inbound lead. "
                    "This person has already shown interest by reaching out, so acknowledge that. "
                    "Reference something specific about their company, role, or situation to show "
                    "this isn't a template. Keep the primary email under 200 words with a warm, "
                    "professional tone and a clear CTA (schedule a call, see a demo, etc). "
                    "Also write a shorter follow-up email (under 100 words) for if they don't "
                    "respond in 3 days — add new value or a different angle, don't just repeat.\n\n"
                    f"The lead is {sender_name} at {company}.\n\n"
                    f"{prompt}"
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "generate_draft_email":
            return block.input

    raise HTTPException(status_code=500, detail="Claude did not return a draft email result")
