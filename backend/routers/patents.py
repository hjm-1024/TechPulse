from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
import models
from collectors.patent_collector import fetch_patents

router = APIRouter(prefix="/api/patents", tags=["patents"])


class PatentOut(BaseModel):
    id: int
    patent_id: Optional[str]
    title: str
    abstract: Optional[str]
    year: Optional[int]
    assignee: Optional[str]
    inventors: Optional[str]
    country: Optional[str]
    url: Optional[str]

    class Config:
        from_attributes = True


@router.get("/{keyword_id}", response_model=List[PatentOut])
def get_patents(keyword_id: int, db: Session = Depends(get_db)):
    kw = db.query(models.Keyword).filter(models.Keyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    patents = (
        db.query(models.Patent)
        .filter(models.Patent.keyword_id == keyword_id)
        .order_by(models.Patent.year.desc())
        .all()
    )
    return patents


async def _collect_and_store(keyword_id: int, query: str):
    from database import SessionLocal
    db = SessionLocal()
    try:
        fetched = await fetch_patents(query, limit=100)
        existing_ids = {
            r[0]
            for r in db.query(models.Patent.patent_id).filter(models.Patent.keyword_id == keyword_id).all()
        }
        for item in fetched:
            if item["patent_id"] and item["patent_id"] in existing_ids:
                continue
            patent = models.Patent(keyword_id=keyword_id, **item)
            db.add(patent)
        db.commit()
    finally:
        db.close()


@router.post("/{keyword_id}/collect")
async def collect_patents(keyword_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    kw = db.query(models.Keyword).filter(models.Keyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    background_tasks.add_task(_collect_and_store, keyword_id, kw.name_en)
    return {"status": "collecting", "keyword": kw.name_en}
