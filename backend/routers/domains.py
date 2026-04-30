from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
import models

router = APIRouter(prefix="/api/domains", tags=["domains"])


class KeywordOut(BaseModel):
    id: int
    name: str
    name_en: str
    paper_count: int = 0
    patent_count: int = 0

    class Config:
        from_attributes = True


class DomainOut(BaseModel):
    id: int
    name: str
    name_en: Optional[str]
    color: str
    keywords: List[KeywordOut] = []

    class Config:
        from_attributes = True


@router.get("/", response_model=List[DomainOut])
def list_domains(db: Session = Depends(get_db)):
    domains = db.query(models.Domain).all()
    result = []
    for domain in domains:
        kw_out = []
        for kw in domain.keywords:
            paper_count = db.query(models.Paper).filter(models.Paper.keyword_id == kw.id).count()
            patent_count = db.query(models.Patent).filter(models.Patent.keyword_id == kw.id).count()
            kw_out.append(KeywordOut(
                id=kw.id,
                name=kw.name,
                name_en=kw.name_en,
                paper_count=paper_count,
                patent_count=patent_count,
            ))
        result.append(DomainOut(
            id=domain.id,
            name=domain.name,
            name_en=domain.name_en,
            color=domain.color,
            keywords=kw_out,
        ))
    return result
