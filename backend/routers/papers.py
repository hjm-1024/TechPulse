from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
import models
from collectors.semantic_scholar import fetch_papers

router = APIRouter(prefix="/api/papers", tags=["papers"])


class PaperOut(BaseModel):
    id: int
    paper_id: Optional[str]
    title: str
    abstract: Optional[str]
    year: Optional[int]
    citation_count: int
    authors: Optional[str]
    url: Optional[str]
    doi: Optional[str]

    class Config:
        from_attributes = True


@router.get("/{keyword_id}", response_model=List[PaperOut])
def get_papers(keyword_id: int, db: Session = Depends(get_db)):
    kw = db.query(models.Keyword).filter(models.Keyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    papers = (
        db.query(models.Paper)
        .filter(models.Paper.keyword_id == keyword_id)
        .order_by(models.Paper.citation_count.desc())
        .all()
    )
    return papers


async def _collect_and_store(keyword_id: int, query: str):
    from database import SessionLocal
    db = SessionLocal()
    try:
        fetched = await fetch_papers(query, limit=100)
        existing_ids = {
            r[0]
            for r in db.query(models.Paper.paper_id).filter(models.Paper.keyword_id == keyword_id).all()
        }
        new_count = 0
        for item in fetched:
            if item["paper_id"] and item["paper_id"] in existing_ids:
                continue
            paper = models.Paper(keyword_id=keyword_id, **item)
            db.add(paper)
            new_count += 1
        db.commit()
    finally:
        db.close()


@router.post("/{keyword_id}/collect")
async def collect_papers(keyword_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    kw = db.query(models.Keyword).filter(models.Keyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    background_tasks.add_task(_collect_and_store, keyword_id, kw.name_en)
    return {"status": "collecting", "keyword": kw.name_en}
