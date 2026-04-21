"""
FastAPI application entry point.
Run with: uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import DB_PATH
from backend.db.schema import init_db
from backend.routers import papers, stats

app = FastAPI(title="TechPulse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db(DB_PATH)


app.include_router(stats.router, prefix="/api")
app.include_router(papers.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
