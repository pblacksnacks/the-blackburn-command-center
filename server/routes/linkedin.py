from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.db import get_linkedin_all, get_linkedin_one, get_lead

# Add project root so agent imports work
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])

# In-memory job store
_jobs: dict[str, dict] = {}


class LinkedInSearchRequest(BaseModel):
    sender_email: str


@router.get("")
def list_linkedin():
    return get_linkedin_all()


@router.get("/search/status/{job_id}")
def search_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{sender_email:path}")
def linkedin_detail(sender_email: str):
    result = get_linkedin_one(sender_email)
    if not result:
        raise HTTPException(status_code=404, detail="LinkedIn profile not found")
    return result


@router.post("/search")
def search_linkedin(req: LinkedInSearchRequest):
    lead = get_lead(req.sender_email)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "id": job_id,
        "sender_email": req.sender_email,
        "status": "running",
        "started_at": time.time(),
        "finished_at": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_search_thread,
        args=(job_id, lead),
        daemon=True,
    )
    thread.start()

    return _jobs[job_id]


def _run_search_thread(job_id: str, lead: dict) -> None:
    try:
        from agents.linkedin_agent import LinkedInSearchAgent

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv(Path(PROJECT_ROOT) / ".env")
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        db_path = os.environ.get("TRIAGE_DB", str(Path(PROJECT_ROOT) / "triage.db"))
        agent = LinkedInSearchAgent(api_key=api_key, db_path=db_path)

        company_key = lead.get("company_domain") or (
            lead.get("company_name", "").lower().replace(" ", "_") if lead.get("company_name") else None
        )

        profile = agent.search_one(
            sender_email=lead["sender_email"],
            sender_name=lead.get("sender_name") or lead["sender_email"],
            company_name=lead.get("company_name"),
            company_domain=lead.get("company_domain"),
        )

        agent.store.upsert_contact(
            sender_email=lead["sender_email"],
            company_key=company_key,
            profile=profile,
        )

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["finished_at"] = time.time()

    except Exception as exc:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(exc)
        _jobs[job_id]["finished_at"] = time.time()
