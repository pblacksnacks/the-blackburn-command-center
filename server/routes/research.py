from __future__ import annotations

from fastapi import APIRouter, HTTPException

from server.db import get_research_all, get_research_one

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("")
def list_research():
    return get_research_all()


@router.get("/{company_key:path}")
def research_detail(company_key: str):
    result = get_research_one(company_key)
    if not result:
        raise HTTPException(status_code=404, detail="Company research not found")
    return result
