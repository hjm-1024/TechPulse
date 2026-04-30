from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from routers import domains, papers, patents, analysis
from seed_data import seed

models.Base.metadata.create_all(bind=engine)
seed()

app = FastAPI(title="TechPulse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(domains.router)
app.include_router(papers.router)
app.include_router(patents.router)
app.include_router(analysis.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "TechPulse API"}
