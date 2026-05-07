# TechPulse 프레임워크 전체 구조

**버전:** 1.3
**갱신일:** 2026-05-03

## 전체 아키텍처 한눈에 보기

```
외부 데이터 소스 → 수집기(Collectors) → 텍스트 정제 → SQLite DB → FastAPI 백엔드 → React 프론트엔드
                                                          ↕            ↕
                                            Ollama (임베딩·요약·재분류)
                                                          ↕
                                           Migration CLI (정제·dedup·재분류)
```

핵심 변화 (v1.2 → v1.3):
- **도메인 13개로 확장** (저탄소·양자·반도체·신소재·바이오·에너지 등)
- **멀티라벨 도메인 재분류** (`paper_domains`, `patent_domains` 테이블 추가)
- **텍스트 정제 upsert 경로에 wire-in** (HTML/LaTeX 자동 제거)
- **`quality_flag` 컬럼**으로 저품질·중복 행 비파괴 마킹
- **숨은 중복 탐지** (임베딩 코사인 ≥ 0.93)
- **TF-IDF / BERT 분석 라우터 추가** (`/api/analysis/*`)
- **CLI 마이그레이션 스크립트** (`run_migration.py`, dry-run·자동 백업·멱등)
- **프론트엔드 데이터 관리 UI** (수집 실행 / 정비 / 삭제 패널)

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

## 2. 수집-저장 파이프라인 (v1.3 갱신)

| 단계 | 모듈 | 입력 | 출력 | 비고 |
|------|------|------|------|------|
| 수집 | `run_collectors.py`, `backend/collectors/*` | 키워드, 도메인 | dict 리스트 | 소스별 rate limit 준수 |
| **정제 (자동)** | `utils/text_cleaner.clean_text()` | 원시 title/abstract | 정제 텍스트 | upsert 직전 호출 (v1.3 wire-in) |
| **유효성 검사** | `utils/text_cleaner.is_valid_abstract()` | 초록 | bool | 80자 미만·기호만 → `quality_flag='short_abstract'` 마킹 |
| **배치 dedup** | `normalize_title()` 그룹화 | 정규화 키 | 대표 1건 | citation 우선 |
| 저장 | `db/schema.upsert_papers()`, `db/patents_schema.upsert_patents()` | dict 리스트 | UPSERT | UNIQUE 충돌 시 citation 비교 |
| 임베딩 | `utils/embeddings.py` | 정제 title + abstract | float32 768d BLOB | Ollama nomic-embed-text |
| **숨은 중복 탐지** | `migration/dedup_embeddings.py` | 임베딩 | `quality_flag='duplicate'` | cosine ≥ 0.93, 같은 연도, 인용 낮은 쪽 마킹 |
| **멀티라벨 재분류** | `migration/reclassify.py` | 임베딩 | `paper_domains` rows | top-3, score ≥ 0.45 |

---

## 3. 데이터베이스 스키마 (v1.3 갱신)

### 기존 테이블 변경

| 테이블 | 추가 컬럼 (v1.3) | 의미 |
|--------|----------------|------|
| `papers` | `quality_flag TEXT` | NULL=정상 / `short_abstract` / `duplicate` / `low_quality` |
| `papers` | `cleaned_at TIMESTAMP` | clean_text 적용 시각 |
| `patents` | `quality_flag TEXT`, `cleaned_at TIMESTAMP` | 동일 |
| `collection_config` | `last_count INTEGER` | 마지막 수집의 신규 건수 |

### 신규 테이블

| 테이블 | 컬럼 | 인덱스 | 용도 |
|--------|------|--------|------|
| `paper_domains` | `paper_id INT FK`, `domain_tag TEXT`, `score REAL`, `rank INT` (1~3) | (paper_id), (domain_tag, score) | 멀티라벨 도메인 |
| `patent_domains` | `patent_id INT FK`, `domain_tag TEXT`, `score REAL`, `rank INT` | (patent_id), (domain_tag, score) | 동일 |
| `domain_prototypes` | `domain_tag TEXT PK`, `embedding BLOB`, `built_at TIMESTAMP`, `seed_text TEXT` | - | 13개 프로토타입 임베딩 캐시 |
| `collection_jobs` | `id`, `kind TEXT` (collect/cleanup/reclassify/dedup), `status` (queued/running/done/error/cancelled), `params JSON`, `started_at`, `finished_at`, `log_tail TEXT`, `progress REAL` | (status), (started_at desc) | 백그라운드 작업 추적 |
| `cross_links` (선택) | `paper_id`, `patent_id`, `score REAL` | UNIQUE(paper_id, patent_id) | 논문↔특허 사전계산 |

### 분석 쿼리 변경 원칙

```sql
-- 이전 (단일 라벨)
SELECT ... FROM papers WHERE domain_tag = :d AND quality_flag IS NULL

-- 이후 (멀티 라벨)
SELECT p.* FROM papers p
JOIN paper_domains pd ON pd.paper_id = p.id
WHERE pd.domain_tag = :d AND pd.score >= 0.45
  AND p.quality_flag IS NULL
```

`papers.domain_tag`는 호환성을 위해 유지(= 수집 키워드의 primary 도메인). 모든 분석 API는 `paper_domains` JOIN 기반으로 전환.

---

## 4. 도메인 카탈로그 (13개)

| domain_tag | 한글 라벨 | 시드 키워드 (예시) |
|------------|-----------|-------------------|
| `physical_ai_robotics` | 물리적 AI·로보틱스 | embodied AI, humanoid, manipulation |
| `telecom_6g` | 통신·6G | 6G, mmWave, NTN, RIS |
| `quantum` | 양자 | quantum computing, qubit, error correction |
| `semiconductors` | 반도체 | EUV, GAA, advanced packaging, HBM |
| `advanced_materials` | 신소재 | graphene, 2D materials, perovskite |
| `low_carbon` | 저탄소 | decarbonization, net zero, green steel |
| `climate_tech` | 기후 기술 | carbon capture, DAC, climate adaptation |
| `energy` | 에너지 | solid-state battery, hydrogen, fusion |
| `biotech` | 바이오 | mRNA, CRISPR, protein design |
| `cybersecurity` | 사이버보안 | post-quantum crypto, zero trust |
| `space` | 우주 | LEO satellite, reusable rocket |
| `autonomous_driving` | 자율주행 | LiDAR, end-to-end driving |
| `xr_metaverse` | XR·메타버스 | AR/VR, neural rendering |

도메인 추가 시: `backend/config/domains.py`의 `DOMAIN_SEEDS`에 시드 텍스트 추가 → `python run_migration.py --steps prototypes,reclassify` 실행 → 모든 기존 데이터 자동 재태깅.

---

## 5. FastAPI 엔드포인트 맵 (v1.3 갱신)

### 기존 라우터 (멀티라벨 적용)

| 라우터 | 엔드포인트 | 메서드 | 비고 |
|--------|-----------|--------|------|
| papers | `/api/papers` | GET | `domain` 필터가 `paper_domains` JOIN으로 변경 |
| stats | `/api/summary`, `/api/trend`, `/api/top`, `/api/sources` | GET | `quality_flag IS NULL` + 멀티라벨 |
| patents | `/api/patents/*` | GET | 동일 패턴 |
| semantic | `/api/search/semantic`, `/api/similar`, `/api/cross` | GET | 변경 없음 |
| ai | `/api/summarize`, `/api/ollama/status` | POST/GET | 변경 없음 |
| insights | `/api/insights/emerging`, `/api/insights/network` | GET | 멀티라벨 + quality 필터 |
| analysis | `/api/analysis/tfidf`, `/api/analysis/tfidf-trend`, `/api/analysis/bert-clusters` | GET | TF-IDF 시계열 / BERT 군집 (v1.3 추가) |

### 신규 라우터: 데이터 관리

| 엔드포인트 | 메서드 | 기능 |
|-----------|--------|------|
| `/api/config/collect` | POST | 수집 잡 시작 (`{domains, sources, days_back}`) → `collection_jobs` 등록 후 BackgroundTasks |
| `/api/config/reclassify` | POST | 재분류 잡 시작 (`{rebuild_prototypes: bool, threshold: 0.45}`) |
| `/api/config/cleanup` | POST | 정제 + 숨은 중복 탐지 (`{dry_run: bool, dup_threshold: 0.93}`) |
| `/api/config/jobs` | GET | 진행 중·최근 잡 목록 (status, progress, log_tail 포함) |
| `/api/config/jobs/{id}` | GET | 잡 상세 |
| `/api/config/jobs/{id}/cancel` | POST | 진행 잡 취소 (cooperative cancel flag) |
| `/api/config/freshness` | GET | `{papers_last, patents_last, per_source: {...}}` 데이터 신선도 |
| `/api/papers/{id}` | GET / DELETE | 단건 상세 / 삭제 (관련 `paper_domains` cascade) |
| `/api/patents/{id}` | GET / DELETE | 동일 |
| `/api/papers/bulk-delete` | POST | 조건부 삭제 (`{filters, confirm_token}`) — preview 먼저 응답 |
| `/api/papers/{id}/quality` | PATCH | `quality_flag` 수동 조정 (분석 제외/복구) |

`bulk-delete`는 2-step: 첫 호출은 preview(영향 행 수 + 토큰 반환), 두 번째 호출은 토큰과 함께 실제 실행.

---

## 6. AI/ML 모델 계층 (v1.3 갱신)

| 역할 | 모델 | 서버 | 입력 | 출력 | 비고 |
|------|------|------|------|------|------|
| 임베딩 | `nomic-embed-text` | Ollama | title + abstract (max 8000자) | float32 768d | 모든 정제·재분류·검색의 기반 |
| 도메인 프로토타입 | `nomic-embed-text` | Ollama | 도메인 시드 텍스트 (라벨 + 시드 키워드 concatenate) | float32 768d × 13 | `domain_prototypes` 테이블 캐시 |
| 요약 (일반) | `qwen3:14b-q8_0` | Ollama | title + abstract | 한국어 3~4문장 | 스트리밍 |
| 요약 (고품질) | `qwen2.5:32b` | Ollama | title + abstract | 한국어 3~4문장 | quality=true |
| BERT 군집 | `nomic-embed-text` 임베딩 + scikit-learn HDBSCAN | 백엔드 | 임베딩 행렬 | 군집 라벨 | `/api/analysis/bert-clusters` |

---

## 7. 프론트엔드 컴포넌트 맵 (v1.3 갱신)

| 탭 | 컴포넌트 | 데이터 소스 | 비고 |
|----|----------|------------|------|
| Papers | `StatsCards`, `TrendChart`, `SourceChart`, `TopPapers` | summary, trend, sources, top | - |
| Patents | `PatentStats`, `PatentTrendChart`, `TopAssignees` | patents/* | - |
| Search | `SearchPage`, `SearchResults`, `SimilarDocs` | papers / search/semantic / similar | 2컬럼 + 히스토리 + 하이라이팅 (v1.2) |
| Insights | `EmergingPapers`, `NetworkGraph` | insights/emerging, insights/network | D3 force graph |
| Analysis | `TFIDFKeywords`, `TFIDFTrend`, `BERTClusters` | analysis/* | 분기별 emerging terms (v1.3) |
| Config | `CollectionConfig`, **`CollectionRunner`**, **`MaintenancePanel`**, **`DataManagement`**, **`JobsPanel`** | config/* | 신규 4개 패널 (v1.3) |
| 헤더 | `FreshnessBadge` | config/freshness | "마지막 업데이트: 3시간 전" (v1.3) |

### Config 탭 신규 패널 상세

| 패널 | 기능 |
|------|------|
| **CollectionRunner** | 도메인·소스 다중 선택 → "수집 시작" → 진행률 바 (JobsPanel에 자동 표시) |
| **MaintenancePanel** | 정제 / 재분류 / 숨은 중복 탐지 — 각각 dry-run 토글 + 결과 요약 (영향 행 수, 분포) |
| **DataManagement** | 필터(도메인·소스·날짜) → preview → 일괄 삭제 (2단계 confirm) / 단건은 SearchResults·TopPapers 행 메뉴에서 |
| **JobsPanel** | 진행 중·최근 잡 list (status, progress, log_tail 200자, cancel 버튼) — polling 5s |

전 탭에 `ErrorBoundary` 래핑(v1.3): 한 컴포넌트 실패가 탭 전체를 죽이지 않음.

---

## 8. 마이그레이션 / 운영 CLI (v1.3 신규)

```bash
# 미리보기 (DB 미수정)
python run_migration.py --dry-run

# 일부 단계만
python run_migration.py --steps clean,validate
python run_migration.py --steps embed,prototypes,reclassify
python run_migration.py --steps dedup --dup-threshold 0.93

# 전체 (백업 자동 생성)
python run_migration.py --all
```

### 단계 정의

| step | 모듈 | 동작 | 멱등 |
|------|------|------|------|
| `backup` | `migration/backup.py` | `data/techpulse.db.bak.YYYYMMDD-HHMMSS` 복사 | 매 실행 새 파일 |
| `clean` | `migration/clean_texts.py` | 모든 papers/patents의 title/abstract에 `clean_text()` 적용, `cleaned_at` 갱신 | `cleaned_at IS NULL`만 처리 |
| `validate` | `migration/validate.py` | `is_valid_abstract` 실패 → `quality_flag='short_abstract'` | 이미 마킹된 행 skip |
| `embed` | `migration/build_embeddings.py` | embedding 없는 행 일괄 생성 | `embedding IS NULL`만 |
| `prototypes` | `migration/build_prototypes.py` | 13개 도메인 프로토타입 임베딩 (재)생성 → `domain_prototypes` | `--rebuild` 시 강제 |
| `reclassify` | `migration/reclassify.py` | 모든 문서를 13개 프로토타입과 cosine 비교 → top-3 (≥ threshold) → `paper_domains`/`patent_domains` upsert | `--since YYYY-MM-DD`로 증분 가능 |
| `dedup` | `migration/dedup_embeddings.py` | 같은 연도 내 cosine ≥ threshold 쌍 탐지 → 인용 낮은 쪽 `quality_flag='duplicate'` | 이미 `duplicate` 마킹된 행 skip |

### 안전 원칙

1. **삭제 0건** — 저품질·중복은 `quality_flag` 마킹만. 분석 API는 `WHERE quality_flag IS NULL` 자동 필터.
2. **백업 자동** — `--all` 또는 변경 단계는 시작 시 무조건 `.bak` 생성.
3. **멱등** — 모든 단계가 "이미 처리된 행 skip" 로직 포함. 여러 번 돌려도 안전.
4. **dry-run** — 실제 변경 없이 영향 행 수와 분포 출력.
5. **롤백** — `mv data/techpulse.db.bak.* data/techpulse.db` 한 줄.

CLI 단계는 백엔드 라우터(`/api/config/cleanup`, `/api/config/reclassify`)에서 동일 함수를 호출 → 프론트와 CLI가 같은 코드 경로를 공유.

---

## 9. 트렌드·이상치 감지 (v1.3 신규)

월별 문서 수에 EWMA(span=6) 잔차 z-score를 계산해 `|z| ≥ 2`인 달에 🔥 뱃지를 `TrendChart`에 표시. 별도 테이블 없이 응답 시 계산.

```
score(month) = (count - EWMA_mean) / EWMA_std
```

---

## 10. 데이터 흐름 전체도 (v1.3)

```
┌────────────────────────────────────────────────┐
│                  외부 데이터 소스                │
│  arXiv │ S2 │ OpenAlex │ Lens │ EPO │ KIPRIS  │
└────────────────────┬───────────────────────────┘
                     │ HTTP
                     ▼
┌────────────────────────────────────────────────┐
│          Collectors → text_cleaner             │
│   배치 dedup → upsert (quality_flag 마킹)       │
└────────────────────┬───────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│              SQLite Database                    │
│  papers │ patents │ paper_domains │ ...         │
│  collection_jobs │ domain_prototypes            │
└──────┬──────────────────┬────────────┬─────────┘
       │                  │            │
       ▼                  ▼            ▼
┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Ollama      │  │ FastAPI Backend  │  │ Migration CLI    │
│ embed/sum   │◄─┤ + BackgroundTasks│  │ run_migration.py │
│             │  │ + JobRunner      │  │ (clean/dedup/    │
│             │  └────────┬─────────┘  │  reclassify)     │
└─────────────┘           │ REST       └─────┬────────────┘
                          ▼                  │
              ┌────────────────────────┐     │ 같은 함수 호출
              │  React + Vite Frontend │◄────┘
              │  + ErrorBoundary       │
              │  + Config 데이터 관리   │
              └────────────────────────┘
```
