# TechPulse 요구사항 명세서 (Requirements Specification)

**버전:** 1.3
**작성일:** 2026-04-22
**갱신일:** 2026-05-03
**프로젝트:** TechPulse - 기술 인텔리전스 대시보드

---

## 변경 이력

| 버전 | 일자 | 주요 변경 |
|------|------|----------|
| 1.0 | 2026-04-22 | 초안 (논문·특허 수집, 기본 검색·요약·트렌드) |
| 1.1 | - | 텍스트 전처리 모듈 / 배치 dedup |
| 1.2 | - | 검색 UI(2컬럼·히스토리·하이라이팅) |
| **1.3** | **2026-05-03** | **도메인 13개 확장, 멀티라벨 재분류, `quality_flag`, 텍스트 정제 wire-in, 숨은 중복 탐지, 마이그레이션 CLI, 데이터 관리 UI, TF-IDF/BERT 분석** |

---

## 1. 시스템 개요

### 1.1 목적
다분야(물리 AI·통신·양자·반도체·신소재·저탄소·바이오 등 13개 도메인)의 최신 논문과 특허를 자동으로 수집·정제·재분류·분석·시각화하여, 연구자 및 기술 전략 담당자가 기술 트렌드를 신속하게 파악하게 한다.

### 1.2 핵심 모델 및 대상

| 구분 | 내용 |
|------|------|
| 임베딩 모델 | `nomic-embed-text` (Ollama, 768차원 float32) |
| 요약 모델 | `qwen3:14b-q8_0` (일반) / `qwen2.5:32b` (고품질) |
| 검색 대상 | 논문 (arXiv, Semantic Scholar, OpenAlex) + 특허 (Lens, EPO, KIPRIS) |
| 도메인 (13) | physical_ai_robotics, telecom_6g, quantum, semiconductors, advanced_materials, low_carbon, climate_tech, energy, biotech, cybersecurity, space, autonomous_driving, xr_metaverse |
| 언어 | 수집: 영어 / 요약 출력: 한국어 |
| 저장소 | SQLite (WAL 모드) |
| 인프라 | FastAPI + React/Vite, Ollama 로컬 서버 |
| 운영 모드 | 단일 머신 로컬 (서버 배포는 비목표) |

### 1.3 네트워크 구성

```
[수집 서버 (run_collectors.py | run_migration.py)]
    ↕ HTTP (외부 API) | 함수 호출 (마이그레이션)
[SQLite DB]
    ↕ SQL
[FastAPI 백엔드 :8000]  ──── BackgroundTasks (수집/정제/재분류 잡)
    ↕ REST JSON
[React 프론트 :5173]
    ↕ localhost HTTP
[Ollama :11434]  ← 임베딩·요약·도메인 프로토타입을 FastAPI/CLI가 전달
```

---

## 2. 기능 명세

### 2.1 데이터 수집 (FR-COL)

#### FR-COL-01: 논문 수집
키워드 기반으로 논문을 수집해 SQLite에 UPSERT.

- 흐름: `collection_config` 활성 키워드 순회 → 소스(arxiv / semantic_scholar / openalex)별 수집기 호출 → dict 리스트 반환 → **`clean_text()` 자동 적용** → `is_valid_abstract()` 실패 시 `quality_flag='short_abstract'` 마킹 → `upsert_papers()`
- UNIQUE: `doi` 또는 `(title, source)`
- 충돌 시: citation_count 비교, 큰 값 유지

#### FR-COL-02: 특허 수집
키워드 기반 Lens/EPO OPS/KIPRIS 수집. 동일 패턴, `(patent_number, source)` UNIQUE.

#### FR-COL-03: EPO 데이터 보강
`assignee` 누락 EPO 특허는 개별 biblio 호출로 출원인·발명자 보충, `clean_party_name()`으로 국가코드 제거.

#### FR-COL-04: 임베딩 생성
embedding이 없는 레코드 일괄 생성 (`title + abstract`, max 8000자, Ollama nomic-embed-text). float32 768d → bytes BLOB 저장.

#### FR-COL-05: 백그라운드 수집 잡 (v1.3)
프론트 또는 API에서 수집을 트리거할 수 있어야 함.
- `POST /api/config/collect {domains:[...], sources:[...], days_back:7}` → `collection_jobs` 등록 → FastAPI BackgroundTasks 또는 자체 JobRunner가 실행 → `progress`, `log_tail` 갱신 → `cancel` 가능
- 동시에 같은 `kind`의 잡은 1개만 (큐잉)

---

### 2.2 검색 (FR-SRCH)

#### FR-SRCH-01: 키워드 검색
SQL LIKE 기반. 멀티라벨 도메인 필터는 `paper_domains` JOIN 기반.
```sql
SELECT p.* FROM papers p
LEFT JOIN paper_domains pd ON pd.paper_id = p.id
WHERE (p.title LIKE :q OR p.abstract LIKE :q)
  AND (:domain IS NULL OR (pd.domain_tag = :domain AND pd.score >= 0.45))
  AND p.quality_flag IS NULL
ORDER BY citation_count DESC LIMIT :n OFFSET :off
```

#### FR-SRCH-02: 의미 검색 (Semantic)
쿼리 임베딩 vs 저장 임베딩 코사인 유사도. `quality_flag IS NULL` 자동 제외.

#### FR-SRCH-03: 유사 문서 탐색
대상 문서 임베딩 vs 같은 type의 모든 임베딩.

#### FR-SRCH-04: 논문↔특허 교차 링크
`/api/cross?from_type=papers&from_id=123&to_type=patents&limit=5`

---

### 2.3 AI 요약 (FR-AI)

#### FR-AI-01: LLM 한국어 요약
`POST /api/summarize {title, abstract, type, quality}` → Ollama 스트리밍 → 점진적 렌더링.

---

### 2.4 트렌드·인사이트 분석 (FR-TREND)

#### FR-TREND-01: 월별 트렌드
도메인별 월간 카운트. 멀티라벨이라 한 문서가 여러 도메인 합계에 기여.

#### FR-TREND-02: 이상치 감지 (v1.3)
EWMA(span=6) 잔차 z-score → `|z| ≥ 2`인 달에 🔥 뱃지. 응답 시 계산, 별도 저장 없음.

#### FR-TREND-03: 급부상 문서 (Emerging)
`emergence_score = log(1+citation) / log(1+days_since_publication)` 상위 N개.

#### FR-TREND-04: 분기별 TF-IDF 시계열 (v1.3)
- `/api/analysis/tfidf-trend?domain=...&top_k=20`
- 분기 단위로 TF-IDF 점수를 계산 → 직전 분기 대비 급상승 키워드 top-K 반환
- "최근에 새로 부상한 단어"를 어휘 기반으로 검출 (인용 기반 emerging과 보완)

#### FR-TREND-05: BERT 군집 (v1.3)
- `/api/analysis/bert-clusters?domain=...&min_cluster=10`
- HDBSCAN으로 임베딩 군집 → 각 군집의 대표 키워드(TF-IDF) 자동 라벨

---

### 2.5 네트워크 그래프 (FR-GRAPH)
도메인 내 상위 N개 문서 임베딩 → 코사인 ≥ threshold(기본 0.82) 쌍을 엣지로 → D3 force-directed.

---

### 2.6 텍스트 전처리 (FR-CLEAN) — v1.3 강화

#### FR-CLEAN-01: 자동 정제 (wire-in)
**모든 수집 경로의 upsert 직전에 `clean_text()` 자동 적용** — HTML 엔티티 디코딩, LaTeX/HTML 태그 제거, 공백 정규화. `cleaned_at` 타임스탬프 기록.

#### FR-CLEAN-02: 초록 유효성
80자 미만 또는 숫자/기호만 → 행을 **삭제하지 않고** `quality_flag='short_abstract'` 마킹. 분석 API에서 자동 제외.

#### FR-CLEAN-03: 기존 데이터 일괄 정제 (CLI)
```bash
python run_migration.py --steps clean,validate         # 적용
python run_migration.py --steps clean,validate --dry-run
```
멱등 — `cleaned_at IS NULL` 행만 처리.

---

### 2.7 중복 제거 (FR-DEDUP)

#### FR-DEDUP-01: 배치 내 (수집 시)
`normalize_title` 그룹화 → citation 최대 유지.

#### FR-DEDUP-02: 소스 간 (CLI, 기존)
```bash
python run_collectors.py --dedup [--dry-run]
```

#### FR-DEDUP-03: 임베딩 기반 숨은 중복 (v1.3)
- 같은 연도 내 cosine ≥ 0.93 (기본, 보수적) 쌍 탐지
- 인용 낮은 쪽 → `quality_flag='duplicate'` 마킹 (삭제 X)
- ```python run_migration.py --steps dedup [--dup-threshold 0.93] [--dry-run]```
- 임계값 변경: 0.95(엄격) ~ 0.90(공격적)

---

### 2.8 멀티라벨 도메인 재분류 (FR-RECLASS) — v1.3 신규

#### FR-RECLASS-01: 도메인 프로토타입 생성
`backend/config/domains.py`의 `DOMAIN_SEEDS`에서 각 도메인의 시드 텍스트(라벨 + 시드 키워드 concatenate)를 임베딩 → `domain_prototypes` 테이블에 13개 캐시.

#### FR-RECLASS-02: 문서 재분류
모든 papers/patents의 임베딩 vs 13개 프로토타입 cosine → top-3 (score ≥ 0.45) → `paper_domains(paper_id, domain_tag, score, rank)` upsert.
- `papers.domain_tag`는 호환성을 위해 유지(primary 도메인)
- 모든 분석 API는 `paper_domains` JOIN 기반으로 전환
- 임계값과 top-N은 분포 보고 튜닝

#### FR-RECLASS-03: 트리거
```bash
# 전체 재분류
python run_migration.py --steps prototypes,reclassify

# 신규 데이터만 (증분)
python run_migration.py --steps reclassify --since 2026-04-01

# API
POST /api/config/reclassify {rebuild_prototypes: false, threshold: 0.45}
```

신규 데이터: 수집 직후 `embed → reclassify` 자동 chain (옵션, 설정으로 켜고 끄기).

---

### 2.9 데이터 관리 (FR-DATA) — v1.3 신규

#### FR-DATA-01: 데이터 신선도 표시
- `GET /api/config/freshness` → `{papers_last, patents_last, per_source: {arxiv: ..., epo: ...}}`
- 헤더에 "마지막 업데이트: 3시간 전" 뱃지

#### FR-DATA-02: 단건 조회·삭제
- `GET /api/papers/{id}`, `GET /api/patents/{id}` — 상세
- `DELETE /api/papers/{id}`, `DELETE /api/patents/{id}` — `paper_domains` cascade
- 프론트: `SearchResults`, `TopPapers` 행에 더보기 메뉴 (편집 / 삭제 / quality_flag 토글)

#### FR-DATA-03: 일괄 삭제 (2-step confirm)
1. `POST /api/papers/bulk-delete {filters: {domain, source, date_range}}` → preview 응답 `{count, sample, confirm_token}`
2. `POST /api/papers/bulk-delete {confirm_token}` → 실제 삭제

#### FR-DATA-04: 품질 마킹 수동 조정
- `PATCH /api/papers/{id}/quality {flag: null | "low_quality" | "duplicate" | "short_abstract"}`
- 분석에서 임시로 제외하거나, 잘못 마킹된 행을 복구할 때 사용

#### FR-DATA-05: 잡 관리 UI
프론트 Config 탭의 `JobsPanel`:
- 진행 중·최근 잡 목록 (5초 polling)
- 각 잡의 status / progress bar / log_tail / 취소 버튼
- 잡 종류: collect, cleanup, reclassify, dedup

---

### 2.10 키워드 관리 (FR-KW)

#### FR-KW-01: 키워드 CRUD
- `GET /api/config/keywords`
- `POST /api/config/keywords {keyword, domain_tag, sources, days_back}`
- `PATCH /api/config/keywords/{id}` (활성/비활성 포함)
- `DELETE /api/config/keywords/{id}`

#### FR-KW-02: LLM 기반 키워드 확장
- `POST /api/config/keywords/expand {seed: "...", domain: "..."}` → Ollama 호출 → 관련 영문 키워드 N개 제안

---

### 2.11 검색 UI (FR-SEARCHUI) — v1.2 유지

- 2컬럼 레이아웃 (좌: 필터, 우: 결과)
- 라디오 버튼 도메인·소스 필터 (이제 13개 도메인)
- LocalStorage 검색 히스토리 (최근 8개)
- 검색어 하이라이팅 (`<mark>`)
- 히어로 검색창 (포커스 글로우)

---

## 3. 비기능 요구사항

### 3.1 성능

| 항목 | 목표 |
|------|------|
| 키워드 검색 응답 | < 200ms |
| 의미 검색 응답 | < 3s (10만 건 이하) |
| LLM 요약 첫 토큰 | < 5s |
| 멀티라벨 재분류 | 10만 건 < 30분 (Ollama 임베딩 캐시 활용) |
| 마이그레이션 dry-run | 5초 이내 영향 행 수 출력 |

### 3.2 데이터 품질

- 모든 신규 데이터: `clean_text()` 자동 적용 (upsert 직전 wire-in)
- 80자 미만 초록 → `quality_flag='short_abstract'` 마킹, 분석 자동 제외
- 숨은 중복: cosine ≥ 0.93, 같은 연도 → `quality_flag='duplicate'`
- 멀티라벨: 모든 문서가 top-1~3 도메인 + score(0.45 이상) 보유
- 모든 분석 API는 `WHERE quality_flag IS NULL` 기본 적용

### 3.3 안정성

- API 실패 시 최대 4회 지수 백오프 (2/4/8/16s)
- Ollama 연결 실패 시 embedding=NULL, 의미 검색·재분류·BERT에서만 제외
- SQLite WAL 모드
- 마이그레이션: 변경 단계 시작 전 자동 백업 (`.bak.YYYYMMDD-HHMMSS`)
- 모든 마이그레이션 단계 멱등 (여러 번 안전), dry-run 지원
- 프론트: 탭별 `ErrorBoundary` — 한 컴포넌트 실패가 다른 탭으로 전파 안 됨

### 3.4 운영 안전 원칙

| 원칙 | 의미 |
|------|------|
| **삭제 0건** | 마이그레이션은 `quality_flag` 마킹만, 절대 행 삭제 안 함 |
| **사용자 명시 삭제만** | DELETE / bulk-delete API는 사용자가 명시적으로 호출했을 때만 |
| **2-step confirm** | bulk 작업은 preview → token → 실행 |
| **자동 백업** | 변경 마이그레이션 시작 시 무조건 `.bak` 생성 |
| **롤백 한 줄** | `mv techpulse.db.bak.* techpulse.db` |

---

## 4. 현재 한계 및 처리 방침

| 번호 | 한계 | 심각도 | 처리 |
|------|------|--------|------|
| L-01 | 의미 검색 시 전체 embedding 메모리 로드 | 중 | v1.3 범위 외 (운영상 OK) |
| L-02 | abstract만 사용, full-text 없음 | 중 | 로드맵 |
| L-03 | 저자/assignee 정규화 약함 | 중 | 로드맵 (`Samsung Electronics Co., Ltd.` ≠ `SAMSUNG ELECTRONICS`) |
| L-04 | 자동 스케줄링 없음 (수동 또는 API 트리거) | 중 | 서버 배포 전까지 OK, APScheduler는 추후 |
| L-05 | USPTO/PatentsView 미구현 | 하 | 로드맵 |
| L-06 | 테스트 0건 | 중 | 라우터별 happy-path 1개씩 추가 (로드맵) |
| L-07 | 멀티라벨 임계값(0.45) 분포 보고 튜닝 필요 | 하 | 첫 마이그레이션 dry-run 결과로 결정 |

서버 배포 / 멀티 유저는 v1.3 범위 외.

---

## 5. v1.3 마이그레이션 절차 (사용자 가이드)

### 첫 실행 (권장)

```bash
# 1) 미리보기 — DB 변경 없음, 영향 행 수와 분포만 출력
python run_migration.py --dry-run --all

# 2) 분포 확인 후 실행 (자동 백업)
python run_migration.py --all
```

### 단계별 의미

| 단계 | 무엇을 함 | 되돌리기 |
|------|-----------|---------|
| backup | `.bak` 자동 생성 | - |
| clean | HTML/LaTeX 제거 → title/abstract 갱신 | 백업 복원 |
| validate | 짧은 초록 → `quality_flag='short_abstract'` | `PATCH .../quality {flag: null}` |
| embed | 누락 임베딩 생성 | - |
| prototypes | 13개 도메인 임베딩 생성 | `--rebuild` 재생성 |
| reclassify | `paper_domains`/`patent_domains` 채움 | 테이블 TRUNCATE 후 재실행 |
| dedup | 중복 → `quality_flag='duplicate'` | `PATCH .../quality {flag: null}` |

### 첫 실행 후 결정사항

- **임계값 튜닝**: dry-run 출력으로 (1) 멀티라벨 분포(평균 도메인 수), (2) 중복 후보 분포 확인 → 임계값(0.45 / 0.93) 조정
- **신규 데이터 자동 처리**: 수집 직후 `embed → reclassify` 자동 chain 활성화 여부 결정 (`backend/config/settings.py`의 `AUTO_RECLASSIFY=True`)

---

## 6. 우선순위 로드맵

### Phase A (v1.3 — 진행 중)
1. ✅ `clean_text` upsert wire-in
2. ✅ `quality_flag` 컬럼 + 분석 API 필터
3. ✅ 13개 도메인 + 프로토타입 + `paper_domains` 테이블
4. ✅ 멀티라벨 재분류 CLI + API
5. ✅ 숨은 중복 탐지
6. ✅ 마이그레이션 CLI (dry-run / 자동 백업 / 멱등)
7. ✅ 프론트 Config 탭 (CollectionRunner, MaintenancePanel, DataManagement, JobsPanel)
8. ✅ 단건/일괄 삭제 API + UI
9. ✅ 데이터 신선도 뱃지
10. ✅ TF-IDF 분기 시계열 / BERT 군집 / 트렌드 이상치 뱃지
11. ✅ 프론트 ErrorBoundary

### Phase B (다음)
- 논문↔특허 cross-link 사전계산 (`cross_links` 테이블)
- 저자/assignee 정규화 + co-authorship 그래프
- 키워드 자동 확장 UI 강화
- 라우터별 happy-path pytest

### Phase C (장기)
- APScheduler 자동 수집 (운영화 시점)
- USPTO/PatentsView 수집기
- PostgreSQL + pgvector 마이그레이션 (10만 건 이상 / 멀티 유저)
- 워치리스트 + 주간 다이제스트
- 하이브리드 검색 (BM25 + dense)
