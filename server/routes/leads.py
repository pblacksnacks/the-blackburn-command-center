from __future__ import annotations

from fastapi import APIRouter, HTTPException

from server.db import get_leads, get_lead, get_lead_emails, get_lead_stats

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("")
def list_leads(
    grade: str | None = None,
    intent: str | None = None,
    buying_stage: str | None = None,
    use_case: str | None = None,
    sort_by: str = "score",
    order: str = "desc",
):
    return get_leads(
        grade=grade, intent=intent, buying_stage=buying_stage,
        use_case=use_case, sort_by=sort_by, order=order,
    )


@router.get("/stats")
def lead_stats():
    return get_lead_stats()


@router.get("/{sender_email:path}")
def lead_detail(sender_email: str):
    lead = get_lead(sender_email)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead["emails"] = get_lead_emails(sender_email)
    return lead
