from __future__ import annotations

from fastapi import APIRouter, HTTPException

from server.db import get_briefings, get_briefing

router = APIRouter(prefix="/api/briefings", tags=["briefings"])


@router.get("")
def list_briefings():
    return get_briefings()


@router.get("/{briefing_date}")
def briefing_detail(briefing_date: str):
    result = get_briefing(briefing_date)
    if not result:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return result
