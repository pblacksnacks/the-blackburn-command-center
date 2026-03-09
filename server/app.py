"""FastAPI application for the Email Triage Dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.routes import leads, research, briefings, pipeline, linkedin

app = FastAPI(title="Email Triage Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router)
app.include_router(research.router)
app.include_router(briefings.router)
app.include_router(pipeline.router)
app.include_router(linkedin.router)

# Serve report files (pptx, markdown)
reports_dir = Path(__file__).resolve().parent.parent / "reports"
if reports_dir.exists():
    app.mount("/api/reports", StaticFiles(directory=str(reports_dir)), name="reports")


@app.get("/api/health")
def health():
    return {"status": "ok"}
