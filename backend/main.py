"""
Shield Risk Platform – FastAPI application entry point.

Start with:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.feasibility import router as feasibility_router
from backend.api.mitigation import router as mitigation_router
from backend.api.smolt_feasibility import router as smolt_router

# Ensure the reports directory exists at startup
_reports_dir = Path(__file__).resolve().parent / "static" / "reports"
_reports_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Shield Risk Platform API",
    description="PCC Feasibility & Suitability Tool – REST API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated PDF reports at /static/reports/<filename>
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)

app.include_router(feasibility_router, prefix="/api/feasibility", tags=["feasibility"])
app.include_router(mitigation_router, prefix="/api/mitigation", tags=["mitigation"])
app.include_router(smolt_router)


@app.get("/", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "service": "Shield Risk Platform API"}
