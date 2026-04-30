# TechPulse — 기술 동향 분석 플랫폼

논문(Semantic Scholar) + 특허(USPTO) 데이터를 도메인/키워드별로 수집하고,  
TF-IDF 기반 키워드 빈도 분석으로 연구 동향을 시각화합니다.

## 도메인 구성

| 도메인 | 키워드 |
|--------|--------|
| 인공지능 | LLM, 컴퓨터 비전, 강화학습, 자연어처리 |
| 데이터/클라우드 | 빅데이터, 클라우드 컴퓨팅, 엣지 컴퓨팅, 데이터 마이닝 |
| 보안/블록체인 | 사이버보안, 블록체인, 연합학습, 제로 트러스트 |
| 저탄소 *(신규)* | 탄소중립, 그린수소, 탄소포집저장, 재생에너지, ESG 기술 |

## 빠른 시작

### 백엔드
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 프론트엔드
```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속.

## 주요 기능

- **논문 수집**: Semantic Scholar API (무료, API 키 선택)
- **특허 수집**: USPTO PatentsView API (무료, 인증 불필요)
- **연구 동향 분석**: 클릭 한 번으로 TF-IDF 키워드 분석 + 연도별 트렌드 차트
  - 상위 20개 핵심 키워드 (가로 막대 차트)
  - 연도별 상위 5개 단어 빈도 변화 (라인 차트)
  - 요약 통계 (논문 수, 연도 범위, 평균 인용 수)

## 업그레이드 경로

키워드 분석을 BERT 수준으로 높이려면 `backend/analysis/keyword_analyzer.py`의  
TF-IDF 벡터라이저를 `sentence-transformers` 모델로 교체하면 됩니다.

## 환경 변수

| 변수 | 설명 |
|------|------|
| `S2_API_KEY` | Semantic Scholar API 키 (선택, 없으면 무료 제한 적용) |
