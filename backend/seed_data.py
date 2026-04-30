"""
Initial domain/keyword seed data.
Run once after creating the database: python seed_data.py
"""
import sys
from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)

SEED = [
    {
        "name": "인공지능",
        "name_en": "Artificial Intelligence",
        "color": "#6366f1",
        "keywords": [
            {"name": "LLM", "name_en": "Large Language Model"},
            {"name": "컴퓨터 비전", "name_en": "Computer Vision"},
            {"name": "강화학습", "name_en": "Reinforcement Learning"},
            {"name": "자연어처리", "name_en": "Natural Language Processing"},
        ],
    },
    {
        "name": "데이터/클라우드",
        "name_en": "Data & Cloud",
        "color": "#0ea5e9",
        "keywords": [
            {"name": "빅데이터", "name_en": "Big Data"},
            {"name": "클라우드 컴퓨팅", "name_en": "Cloud Computing"},
            {"name": "엣지 컴퓨팅", "name_en": "Edge Computing"},
            {"name": "데이터 마이닝", "name_en": "Data Mining"},
        ],
    },
    {
        "name": "보안/블록체인",
        "name_en": "Security & Blockchain",
        "color": "#f59e0b",
        "keywords": [
            {"name": "사이버보안", "name_en": "Cybersecurity"},
            {"name": "블록체인", "name_en": "Blockchain"},
            {"name": "연합학습", "name_en": "Federated Learning"},
            {"name": "제로 트러스트", "name_en": "Zero Trust Security"},
        ],
    },
    {
        "name": "저탄소",
        "name_en": "Low Carbon",
        "color": "#22c55e",
        "keywords": [
            {"name": "탄소중립", "name_en": "Carbon Neutral"},
            {"name": "그린수소", "name_en": "Green Hydrogen"},
            {"name": "탄소포집저장", "name_en": "Carbon Capture and Storage"},
            {"name": "재생에너지", "name_en": "Renewable Energy"},
            {"name": "ESG 기술", "name_en": "ESG Technology"},
        ],
    },
]


def seed():
    db = SessionLocal()
    try:
        if db.query(models.Domain).count() > 0:
            print("Database already seeded. Skipping.")
            return

        for domain_data in SEED:
            domain = models.Domain(
                name=domain_data["name"],
                name_en=domain_data["name_en"],
                color=domain_data["color"],
            )
            db.add(domain)
            db.flush()

            for kw_data in domain_data["keywords"]:
                kw = models.Keyword(
                    domain_id=domain.id,
                    name=kw_data["name"],
                    name_en=kw_data["name_en"],
                )
                db.add(kw)

        db.commit()
        print("Seed complete: 4 domains, 17 keywords inserted.")
    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
