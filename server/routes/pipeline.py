from __future__ import annotations

import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add project root so agent imports work
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# In-memory job store (fine for local dev)
_jobs: dict[str, dict] = {}


class PipelineRequest(BaseModel):
    stage: str = "full"
    demo: bool = True


@router.post("/run")
def run_pipeline(req: PipelineRequest):
    if req.stage not in ("full", "intake", "research", "briefing"):
        raise HTTPException(status_code=400, detail="Invalid stage")

    # Don't allow concurrent runs
    running = [j for j in _jobs.values() if j["status"] == "running"]
    if running:
        raise HTTPException(status_code=409, detail="Pipeline already running")

    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "id": job_id,
        "stage": req.stage,
        "demo": req.demo,
        "status": "running",
        "started_at": time.time(),
        "finished_at": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(job_id, req.stage, req.demo),
        daemon=True,
    )
    thread.start()

    return _jobs[job_id]


@router.get("/status/{job_id}")
def pipeline_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs")
def list_jobs():
    return list(_jobs.values())


def _run_pipeline_thread(job_id: str, stage: str, demo: bool) -> None:
    try:
        # Import here to avoid circular imports and keep server startup fast
        from main import run_full, run_intake, run_research, run_briefing

        runners = {
            "full": run_full,
            "intake": run_intake,
            "research": run_research,
            "briefing": run_briefing,
        }
        runners[stage](demo)

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["finished_at"] = time.time()

    except Exception as exc:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(exc)
        _jobs[job_id]["finished_at"] = time.time()
