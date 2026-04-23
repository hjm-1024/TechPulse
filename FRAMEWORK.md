# TechPulse 프레임워크 전체 구조

## 전체 아키텍처 한눈에 보기

```
외부 데이터 소스 → 수집기(Collectors) → SQLite DB → FastAPI 백엔드 → React 프론트엔드
                                              ↕
                                    Ollama (로컬 LLM)
```

---

## 1. 데이터 소스 계층

| 분류 | 소스 | 인증 | 요청 제한 | 커버리지 | 특이사항 |
|------|------|------|----------|---------|---------|
| 논문 | **arXiv** | 없음 | 3초/요청 | CS, 물리, 수학 | 프리프린트 중심 |
| 논문 | **Semantic Scholar** | 선택(키) | 1~10 req/s | 2억+ 논문 | 인용수 필터(≥5) |
| 논문 | **OpenAlex** | 이메일(선택) | 6 req/s | 전 분야 | OA + 인용수 기반 이중 쿼리 |
| 특허 | **Lens.org** | 무료 키 | 넉넉 | 전세계 | JSON 쿼리 |
| 특허 | **EPO OPS** | OAuth2 키 | 23 req/30s | 유럽+PCT | XML 파싱, 보강 쿼리 |
| 특허 | **KIPRIS** | 공공데이터 키 | 1 req/s | 한국 | XML 파싱 |

---

## 2. 수집-저장 파이프라인

| 단계 | 모듈 | 입력 | 출력 | 기술 |
|------|------|------|------|------|
| 수집 | `run_collectors.py` | 키워드 목록, 도메인 | 논문/특허 dict | Requests |
| **텍스트 전처리** | `utils/text_cleaner.py` | 원시 title/abstract | 정제된 텍스트 | html, re |
| **중복 제거** | `utils/text_cleaner.normalize_title()` | 제목 문자열 | 정규화 키 | regex |
| 저장 | `db/schema.py`, `db/patents_schema.py` | dict 리스트 | SQLite UPSERT | sqlite3 WAL |
| 임베딩 | `utils/embeddings.py` | title + abstract | float32 벡터 BLOB | Ollama nomic-embed-text (768dim) |
| 텍스트 정제 | `utils/text_utils.py` | 원시 이름 문자열 | 정제된 이름 | regex |

---

## 3. 데이터베이스 스키마

| 테이블 | 주요 컬럼 | UNIQUE 제약 | 인덱스 |
|--------|----------|------------|--------|
| `papers` | id, title, abstract, authors, published_date, source, doi, citation_count, journal, domain_tag, **embedding** | doi / (title+source) | doi, domain, date |
| `patents` | id, patent_number, title, abstract, inventors, assignee, filing_date, publication_date, ipc_codes, source, country, domain_tag, **embedding** | (patent_number+source) | domain, date, src |
| `collection_config` | id, keyword, domain_tag, active, sources, days_back, added_at, last_collected | keyword | - |

---

## 4. FastAPI 엔드포인트 맵

| 라우터 | 엔드포인트 | 메서드 | 기능 |
|--------|-----------|--------|------|
| papers | `/api/papers` | GET | 논문 목록 (페이징, 필터, 키워드 검색) |
| stats | `/api/summary` | GET | 소스별·도메인별 논문 수 |
| stats | `/api/trend` | GET | 월별 논문 트렌드 |
| stats | `/api/top` | GET | 인용수 상위 논문 |
| stats | `/api/sources` | GET | 소스별 분포 |
| patents | `/api/patents/summary` | GET | 특허 집계 (소스·도메인·국가) |
| patents | `/api/patents/trend` | GET | 월별 특허 트렌드 |
| patents | `/api/patents/list` | GET | 특허 목록 (페이징) |
| patents | `/api/patents/top-assignees` | GET | 상위 특허 출원인 |
| semantic | `/api/search/semantic` | GET | 임베딩 기반 의미 검색 |
| semantic | `/api/similar` | GET | 유사 문서 탐색 |
| semantic | `/api/cross` | GET | 논문↔특허 교차 링크 |
| ai | `/api/summarize` | POST | LLM 한국어 요약 (스트리밍) |
| ai | `/api/ollama/status` | GET | Ollama 모델 상태 확인 |
| insights | `/api/insights/emerging` | GET | 급부상 논문/특허 (인용 속도) |
| insights | `/api/insights/network` | GET | 유사도 네트워크 그래프 (D3용) |
| config | `/api/config/keywords` | GET/POST/PATCH/DELETE | 키워드 CRUD |
| config | `/api/config/stats` | GET | 수집 설정 현황 |
| config | `/api/config/domains` | GET | 도메인 목록 |

---

## 5. AI/ML 모델 계층

| 역할 | 모델 | 서버 | 입력 | 출력 | 비고 |
|------|------|------|------|------|------|
| 임베딩 | `nomic-embed-text` | Ollama (localhost:11434) | title + abstract (최대 8000자) | float32 벡터 768dim | 코사인 유사도 계산 |
| 요약 (일반) | `qwen3:14b-q8_0` | Ollama | title + abstract | 한국어 3~4문장 | 스트리밍 응답 |
| 요약 (고품질) | `qwen2.5:32b` | Ollama | title + abstract | 한국어 3~4문장 | quality=true 시 |

---

## 6. 프론트엔드 컴포넌트 맵

| 탭 | 컴포넌트 | 데이터 소스 | 라이브러리 |
|----|----------|------------|-----------|
| Papers | StatsCards, TrendChart, SourceChart, TopPapers | summary, trend, sources, top | Recharts |
| Patents | PatentStats, PatentTrendChart, TopAssignees | patents/summary, patents/trend, patents/top-assignees | Recharts |
| Search | **SearchPage**, SearchResults, SimilarDocs | papers or search/semantic, similar | React |
| Insights | EmergingPapers, NetworkGraph | insights/emerging, insights/network | D3.js |
| Config | CollectionConfig | config/keywords, config/stats | React |

---

## 6-1. 텍스트 전처리 파이프라인 (v1.1 추가)

| 함수 | 처리 내용 | 적용 시점 |
|------|----------|----------|
| `clean_text(text)` | HTML 태그 제거, 엔티티 디코딩(`&amp;`→`&`), LaTeX(`$...$`) 제거, 공백 정규화 | upsert 직전 |
| `is_valid_abstract(text)` | 80자 미만·숫자/기호만인 초록 필터링 | upsert 직전 |
| `normalize_title(title)` | 소문자 변환, 특수문자 제거 → 중복 감지용 정규화 키 생성 | 배치 dedup + DB dedup |

## 6-2. 중복 제거 전략 (v1.1 추가)

| 단계 | 방식 | 대상 |
|------|------|------|
| 배치 내 dedup | 정규화 제목 기준 그룹화 → citation_count 높은 것 유지 | 같은 수집 실행 내 |
| DB 충돌 시 | `IntegrityError` → citation_count 비교 → 높으면 UPDATE, 낮으면 skip | 소스 내 재수집 |
| 소스 간 dedup | `python run_collectors.py --dedup` (dry-run 지원) | 전체 DB 배치 정리 |

반환값: `(inserted, updated, skipped)` 세분화로 수집 로그 정확도 향상

## 6-3. 검색 UI (v1.2 추가)

| 항목 | 이전 | 개선 후 |
|------|------|---------|
| 레이아웃 | 상단 바 + 결과 리스트 | **2컬럼** (좌: 필터 사이드바, 우: 결과) |
| 도메인 필터 | 드롭다운 select | **라디오 버튼** (사이드바) |
| 소스 필터 | 드롭다운 select | **라디오 버튼** (사이드바) |
| 검색 히스토리 | 없음 | **LocalStorage 기반** 최근 8개, 드롭다운 + 사이드바 칩 |
| 검색어 하이라이팅 | 없음 | 제목·초록에서 매칭 키워드 **노란 마크** 강조 |
| 검색창 | 중간 크기 | 전체 너비 **히어로 입력창** (Google 스타일) |

---

## 7. 검색 모드 비교

| 항목 | 키워드 검색 | 의미(Semantic) 검색 |
|------|------------|-------------------|
| 방식 | SQL LIKE '%query%' | 코사인 유사도 (임베딩) |
| 속도 | 빠름 | 느림 (전수 비교) |
| 정확도 | 표면적 일치 | 의미적 유사성 |
| 전처리 필요 | 없음 | 임베딩 사전 생성 필수 |
| 결과 | 정확 매칭 | 유사도 점수 포함 |

---

## 8. 급부상 점수 계산식

```
Emergence Score = log(1 + citation_count) / log(1 + days_since_publication)
```
→ 최근에 발표됐는데 인용수가 빠르게 쌓이는 논문을 발굴

---

## 9. 네트워크 그래프 생성 원리

```
1. 도메인 내 상위 N개 문서 로드 (embedding 있는 것만)
2. 모든 쌍(pair)에 대해 코사인 유사도 계산
3. similarity >= threshold (기본 0.82) 인 쌍을 엣지로 생성
4. D3 force-directed graph로 시각화
```

---

## 10. 데이터 흐름 전체도

```
┌────────────────────────────────────────────────┐
│                  외부 데이터 소스                │
│  arXiv  │  Semantic Scholar  │  OpenAlex        │
│  Lens   │  EPO OPS           │  KIPRIS          │
└────────────────────┬───────────────────────────┘
                     │ HTTP (XML/JSON)
                     ▼
┌────────────────────────────────────────────────┐
│             Collectors (run_collectors.py)      │
│  키워드 × 소스 조합으로 순회 수집                │
│  UPSERT → 중복 방지                            │
└────────────────────┬───────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│              SQLite Database                    │
│  papers  │  patents  │  collection_config       │
└──────┬─────────────────────────┬───────────────┘
       │                         │
       ▼                         ▼
┌─────────────┐         ┌───────────────────┐
│ Ollama      │         │  FastAPI Backend   │
│ nomic-embed │◄───────►│  7개 라우터        │
│ qwen3:14b   │ embed / │  /api/*            │
│ qwen2.5:32b │ summary └────────┬──────────┘
└─────────────┘                  │ REST API
                                 ▼
                    ┌────────────────────────┐
                    │  React + Vite Frontend  │
                    │  Recharts + D3.js       │
                    │  5개 탭 대시보드         │
                    └────────────────────────┘
```
