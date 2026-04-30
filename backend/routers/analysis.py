from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from analysis.keyword_analyzer import analyze

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/{keyword_id}")
def get_analysis(keyword_id: int, db: Session = Depends(get_db)):
    kw = db.query(models.Keyword).filter(models.Keyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    papers = db.query(models.Paper).filter(models.Paper.keyword_id == keyword_id).all()
    if not papers:
        return {
            "keyword": kw.name,
            "keyword_en": kw.name_en,
            "message": "논문 데이터가 없습니다. 먼저 논문을 수집해주세요.",
            "top_keywords": [],
            "yearly_trend": [],
            "top5_words": [],
            "total_papers": 0,
            "year_range": [None, None],
            "avg_citations": 0,
        }

    result = analyze(papers)
    result["keyword"] = kw.name
    result["keyword_en"] = kw.name_en
    return result
