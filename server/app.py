"""FastAPI application for the Email Triage Dashboard."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.routes import leads, research, briefings, pipeline, linkedin, call_prep, draft_email

app = FastAPI(title="Email Triage Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router)
app.include_router(research.router)
app.include_router(briefings.router)
app.include_router(pipeline.router)
app.include_router(linkedin.router)
app.include_router(call_prep.router)
app.include_router(draft_email.router)

# Serve report files (pptx, markdown)
reports_dir = Path(__file__).resolve().parent.parent / "reports"
if reports_dir.exists():
    app.mount("/api/reports", StaticFiles(directory=str(reports_dir)), name="reports")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    mode = "gitlab" if os.environ.get("GITLAB_MODE", "false").lower() == "true" else "anthropic"
    return {"mode": mode}
