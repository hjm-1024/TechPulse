"""
FastAPI application entry point.
Run with: uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import DB_PATH
from backend.db.schema import init_db, migrate_add_embeddings
from backend.db.patents_schema import init_patents_db
from backend.routers import papers, stats, patents
from backend.routers import semantic, ai

app = FastAPI(title="TechPulse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db(DB_PATH)
    init_patents_db(DB_PATH)
    migrate_add_embeddings(DB_PATH)


app.include_router(stats.router)
app.include_router(papers.router)
app.include_router(patents.router)
app.include_router(semantic.router)
app.include_router(ai.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
