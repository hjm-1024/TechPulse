# TechPulse 요구사항 명세서 (Requirements Specification)

**버전:** 1.0  
**작성일:** 2026-04-22  
**프로젝트:** TechPulse - 기술 인텔리전스 대시보드

---

## 1. 시스템 개요

### 1.1 목적
물리적 AI/로보틱스 및 통신/6G 분야의 최신 논문과 특허를 자동으로 수집·분석·시각화하여, 연구자 및 기술 전략 담당자가 기술 트렌드를 신속하게 파악할 수 있게 한다.

### 1.2 핵심 모델 및 대상

| 구분 | 내용 |
|------|------|
| 임베딩 모델 | `nomic-embed-text` (Ollama, 768차원 float32) |
| 요약 모델 | `qwen3:14b-q8_0` (일반) / `qwen2.5:32b` (고품질) |
| 검색 대상 | 논문 (arXiv, Semantic Scholar, OpenAlex) + 특허 (Lens, EPO, KIPRIS) |
| 도메인 | `physical_ai_robotics`, `telecom_6g` |
| 언어 | 수집: 영어 / 요약 출력: 한국어 |
| 저장소 | SQLite (WAL 모드) |
| 인프라 | FastAPI + React/Vite, Ollama 로컬 서버 |

### 1.3 네트워크 구성

```
[수집 서버 (run_collectors.py)]
    ↕ HTTP (외부 API)
[SQLite DB]
    ↕ SQL
[FastAPI 백엔드 :8000]
    ↕ REST JSON
[React 프론트 :5173]
    ↕ localhost HTTP
[Ollama :11434]  ← 임베딩·요약 요청을 FastAPI가 전달
```

모든 구성 요소가 단일 머신 내 로컬에서 동작. 외부 의존성은 데이터 수집 API만 해당.

---

## 2. 기능 명세

### 2.1 데이터 수집 (FR-COL)

#### FR-COL-01: 논문 수집

**기능:** 키워드 기반으로 논문 수집, SQLite에 UPSERT 저장

**작동 원리:**
1. `collection_config` 테이블의 활성화된 키워드를 순회
2. 각 키워드에 대해 설정된 소스(arxiv, semantic_scholar, openalex)별로 수집기 호출
3. 수집기가 HTTP 요청 → 응답 파싱 → `dict` 목록 반환
4. `upsert_papers()` 함수가 `INSERT OR REPLACE`로 중복 처리
5. UNIQUE 제약: `doi` 또는 `(title, source)` 조합

**사용 API:**
- arXiv: `http://export.arxiv.org/api/query?search_query=ti:"키워드"+OR+abs:"키워드"&start=0&max_results=100`
- Semantic Scholar: `https://api.semanticscholar.org/graph/v1/paper/search?query=키워드&fields=title,abstract,authors,citationCount,externalIds,venue`
- OpenAlex: `https://api.openalex.org/works?filter=keyword.search:키워드,is_oa:true&sort=cited_by_count:desc`

**입력:** 키워드 문자열, days_back (수집 기간), 도메인 태그  
**출력:** papers 테이블에 레코드 삽입/갱신

---

#### FR-COL-02: 특허 수집

**기능:** 키워드 기반으로 특허 수집 (Lens, EPO OPS, KIPRIS)

**작동 원리:**
1. 논문 수집과 동일한 키워드 순회 방식
2. 각 특허 수집기가 XML/JSON 응답 파싱
3. EPO는 OAuth2 토큰 발급 후 XML CQL 쿼리 실행
4. KIPRIS는 공공 XML API 호출 (한국 특허청)
5. `upsert_patents()`로 `(patent_number, source)` UNIQUE 기준 UPSERT

**사용 API:**
- Lens.org: `POST https://api.lens.org/patent/search` (JSON body)
- EPO OPS: `GET https://ops.epo.org/3.2/rest-services/published-data/search/biblio` (XML CQL)
- KIPRIS: `GET http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/wordSearchInfo` (XML)

**입력:** 키워드, 날짜 범위  
**출력:** patents 테이블에 레코드 삽입/갱신

---

#### FR-COL-03: EPO 특허 데이터 보강

**기능:** EPO 수집 시 누락된 출원인·발명자 정보를 개별 특허 조회로 보완

**작동 원리:**
1. `assignee IS NULL OR assignee = ''` 인 EPO 특허 목록 조회
2. 각 특허번호로 `https://ops.epo.org/3.2/rest-services/published-data/publication/docdb/{num}/biblio` 호출
3. XML에서 `applicant`, `inventor` 태그 파싱
4. `clean_party_name()`으로 `[KR]`, `[US]` 등 국가코드 제거 후 저장

---

#### FR-COL-04: 임베딩 생성

**기능:** 수집된 논문/특허의 제목+초록을 벡터화

**작동 원리:**
1. embedding이 없는 레코드 조회
2. `title + " " + abstract` 조합 (최대 8000자 truncate)
3. `POST http://localhost:11434/api/embeddings` 요청 (`model: nomic-embed-text`)
4. 응답 embedding 배열 → `numpy.array(dtype=float32)` → `bytes()` BLOB으로 저장

**모델:** `nomic-embed-text` (768차원)  
**서버:** Ollama (localhost:11434)

---

### 2.2 검색 (FR-SRCH)

#### FR-SRCH-01: 키워드 검색

**기능:** SQL LIKE를 이용한 텍스트 기반 검색

**작동 원리:**
```sql
SELECT * FROM papers
WHERE (title LIKE '%query%' OR abstract LIKE '%query%')
  AND domain_tag = :domain
  AND source = :source
ORDER BY citation_count DESC
LIMIT :page_size OFFSET :offset
```

**API:** `GET /api/papers?q=keyword&domain=physical_ai_robotics&source=arxiv&sort_by=citation_count&page=1`  
**응답:** `{total, page, page_size, pages, items: [...]}`

---

#### FR-SRCH-02: 의미 검색 (Semantic Search)

**기능:** 임베딩 기반 코사인 유사도 검색

**작동 원리:**
1. 검색어를 Ollama로 임베딩 (동일 모델: nomic-embed-text)
2. DB에서 embedding이 있는 모든 레코드 로드
3. 쿼리 벡터와 각 레코드의 저장된 벡터 사이 코사인 유사도 계산
4. 유사도 내림차순 정렬, 상위 limit개 반환

**코사인 유사도:**
```
similarity = dot(a, b) / (norm(a) × norm(b))
```

**API:** `GET /api/search/semantic?q=텍스트&type=papers&domain=telecom_6g&limit=20`  
**응답:** `[{id, title, abstract, ..., similarity: 0.92}]`

**제약:** 임베딩이 사전에 생성되어 있어야 함

---

#### FR-SRCH-03: 유사 문서 탐색

**기능:** 특정 문서와 가장 유사한 다른 문서 탐색

**작동 원리:**
1. 대상 문서의 embedding 로드
2. 같은 type의 모든 문서 embedding과 코사인 유사도 계산
3. 자기 자신 제외 후 상위 N개 반환

**API:** `GET /api/similar?type=papers&id=123&limit=5`

---

#### FR-SRCH-04: 논문↔특허 교차 링크

**기능:** 논문에서 관련 특허 (또는 반대) 탐색

**API:** `GET /api/cross?from_type=papers&from_id=123&to_type=patents&limit=5`

---

### 2.3 AI 요약 (FR-AI)

#### FR-AI-01: LLM 한국어 요약

**기능:** 논문/특허 제목+초록을 한국어 3~4문장으로 요약

**작동 원리:**
1. 프론트에서 `POST /api/summarize` 요청 (title, abstract, type, quality 포함)
2. FastAPI가 Ollama에 스트리밍 요청
3. 프롬프트: `"다음 {type}을 한국어로 3~4문장으로 요약해주세요:\n제목: {title}\n내용: {abstract}"`
4. `StreamingResponse`로 토큰 단위 스트리밍 전달
5. 프론트에서 점진적 텍스트 렌더링

**모델:**
- 일반: `qwen3:14b-q8_0` (빠름)
- 고품질: `qwen2.5:32b` (quality=true 시)

**API:** `POST /api/summarize` `{title, abstract, type, quality: bool}`

---

### 2.4 트렌드 분석 (FR-TREND)

#### FR-TREND-01: 월별 트렌드

**기능:** 월별 논문/특허 수 집계

**작동 원리:**
```sql
SELECT strftime('%Y-%m', published_date) as month,
       domain_tag, COUNT(*) as count
FROM papers
WHERE (:domain IS NULL OR domain_tag = :domain)
GROUP BY month, domain_tag
ORDER BY month
```

**API:** `GET /api/trend?domain=physical_ai_robotics`  
**응답:** `[{month: "2025-01", physical_ai_robotics: 42, telecom_6g: 18}]`

---

#### FR-TREND-02: 급부상 논문/특허

**기능:** 인용 속도가 빠른 최신 문서 탐지

**작동 원리:**
```
emergence_score = log(1 + citation_count) / log(1 + days_since_publication)
```
- 최근에 발표되었으면서 인용이 빠르게 쌓이는 문서를 발굴
- days 파라미터로 조회 기간 설정

**API:** `GET /api/insights/emerging?domain=telecom_6g&days=90&limit=10&type=papers`

---

### 2.5 네트워크 그래프 (FR-GRAPH)

#### FR-GRAPH-01: 유사도 기반 문서 네트워크

**기능:** 코사인 유사도로 연결된 문서 네트워크 D3 시각화

**작동 원리:**
1. 도메인 내 상위 N개 문서 로드 (embedding 있는 것만)
2. O(N²) 쌍 유사도 계산
3. similarity >= threshold (기본 0.82) 쌍을 엣지로 등록
4. `{nodes: [...], edges: [{source, target, weight}]}` 반환
5. D3 force-directed simulation으로 레이아웃 자동 계산

**API:** `GET /api/insights/network?type=papers&domain=physical_ai_robotics&limit=50&threshold=0.82`

---

### 2.5-a 텍스트 전처리 (FR-CLEAN) ✅ v1.1

#### FR-CLEAN-01: HTML/LaTeX 정제

**기능:** 수집된 원시 텍스트에서 HTML 태그, LaTeX 수식, 특수문자 제거

**작동 원리:**
1. `html.unescape()` → `&amp;`, `&lt;`, `&#x27;` 등 엔티티 디코딩
2. `_LATEX_RE.sub()` → `$E=mc^2$`, `\cite{...}` 등 LaTeX 토큰 공백으로 치환
3. `_TAG_RE.sub()` → `<sub>`, `<sup>`, `<i>` 등 HTML 태그 제거
4. `_WHITESPACE_RE.sub()` → 연속 공백/탭/개행 단일 공백으로 정규화

**적용 시점:** `upsert_papers()` / `upsert_patents()` 호출 직전 자동 적용

---

#### FR-CLEAN-02: 초록 유효성 검사

**기능:** 너무 짧거나 의미 없는 초록 필터링

**기준:**
- 80자 미만 초록 → skip
- 숫자/기호로만 이루어진 텍스트 → skip

---

### 2.5-b 중복 제거 (FR-DEDUP) ✅ v1.1

#### FR-DEDUP-01: 배치 내 중복 제거

**기능:** 같은 수집 실행에서 나온 동일 논문(다른 소스) 중 최적 레코드 유지

**작동 원리:**
1. 모든 레코드의 `normalize_title()` 계산 (소문자 + 특수문자 제거)
2. 정규화 키로 그룹화 → 같은 그룹 내 `citation_count` 최대값 레코드만 유지
3. 나머지 DB 삽입 시도 → `IntegrityError` → citation_count 비교 → 높으면 UPDATE

---

#### FR-DEDUP-02: 소스 간 교차 중복 제거 (배치)

**기능:** 기존 DB에서 서로 다른 소스로 저장된 동일 논문 탐지·제거

**실행:**
```bash
python run_collectors.py --dedup           # 실제 삭제
python run_collectors.py --dedup --dry-run # 미리보기 (삭제 없음)
```

**작동 원리:**
1. 전체 papers 테이블 로드 → 정규화 제목으로 그룹화
2. 그룹 크기 > 1인 것만 처리
3. 우선순위: DOI 있음 > citation_count 높음 → 1개 유지, 나머지 DELETE
4. 생존 레코드의 citation_count를 그룹 최대값으로 업데이트

---

### 2.7 검색 UI (FR-SEARCHUI) ✅ v1.2

#### FR-SEARCHUI-01: 2컬럼 구글형 레이아웃

**구성:**
- 상단: 히어로 검색창 (전체 너비, 포커스 시 글로우 효과)
- 좌측 사이드바 (220px): 도메인·소스·정렬 필터 (라디오 버튼), 최근 검색 칩
- 우측: 검색 결과 카드 목록

#### FR-SEARCHUI-02: 검색 히스토리

**기능:** 최근 8개 검색어를 LocalStorage에 저장·복원

**작동 원리:**
1. 검색 제출(Enter or 검색 버튼) 시 `localStorage['tp_search_history']`에 저장
2. 검색창 포커스 시 드롭다운으로 최근 검색어 표시
3. 클릭 시 검색어 즉시 적용
4. 사이드바에도 칩(Chip) 형태로 표시

#### FR-SEARCHUI-03: 검색어 하이라이팅

**기능:** 검색어와 매칭되는 텍스트를 제목·초록에서 노란색으로 강조

**작동 원리:**
1. 검색어를 공백 기준으로 분리 (2자 이상 토큰만)
2. 정규식으로 대소문자 무시 매칭
3. `<mark>` 스타일 컴포넌트로 래핑하여 렌더링

---

### 2.6 키워드 관리 (FR-KW)

#### FR-KW-01: 키워드 CRUD

**기능:** 수집 키워드를 DB에서 동적 관리

**API:**
- `GET /api/config/keywords` - 전체 키워드 목록
- `POST /api/config/keywords` - 키워드 추가 `{keyword, domain_tag, sources, days_back}`
- `PATCH /api/config/keywords/{id}` - 키워드 수정 (활성화/비활성화 포함)
- `DELETE /api/config/keywords/{id}` - 키워드 삭제

---

## 3. 비기능 요구사항

### 3.1 성능

| 항목 | 목표 |
|------|------|
| 키워드 검색 응답 | < 200ms |
| 의미 검색 응답 | < 3s (100개 이하) |
| LLM 요약 첫 토큰 | < 5s |
| 수집 속도 | 소스별 rate limit 준수 |

### 3.2 데이터 품질

- 논문 중복: DOI 또는 (title+source) UNIQUE 제약으로 방지
- 특허 중복: (patent_number+source) UNIQUE 제약으로 방지
- Semantic Scholar: citation_count >= 5 이하 필터링
- OpenAlex: OA 또는 cited_by_count > 10 기준 이중 필터

### 3.3 안정성

- API 실패 시 최대 4회 지수 백오프 재시도 (2s, 4s, 8s, 16s)
- Ollama 연결 실패 시 embedding = None (null), 검색 제외
- SQLite WAL 모드로 동시 읽기 성능 확보

---

## 4. 현재 한계 및 개선 방향

### 4.1 현재 한계

| 번호 | 한계 | 심각도 |
|------|------|--------|
| L-01 | 의미 검색 시 전체 embedding 메모리 로드 (확장성 낮음) | 중 |
| L-02 | 텍스트 전처리 부재 (HTML 태그, 특수문자 혼입 가능) | 중 |
| L-03 | 소스 간 동일 논문 중복 가능 (DOI 없는 경우) | 중 |
| L-04 | 키워드 자동 확장 없음 (관련 키워드 수동 추가 필요) | 하 |
| L-05 | 검색 UI가 단순 (필터/정렬 옵션 제한) | 하 |
| L-06 | 수집 스케줄링 없음 (수동 실행 필요) | 중 |
| L-07 | 특허 USPTO/PatentsView 수집기 미구현 (stub) | 하 |

---

## 5. 향후 로드맵

### Phase 1 — 데이터 품질 강화

#### [P1-1] 텍스트 전처리 파이프라인
- HTML 태그 제거 (`<sub>`, `<sup>`, 수식 등)
- 특수문자 정규화 (유니코드 정리)
- 초록 길이 필터 (너무 짧은 것 제외 < 50자)
- 제목 중복 유사도 기반 soft-dedup (동일 DOI 없어도 탐지)

#### [P1-2] 고급 중복 제거
- 제목 정규화 후 퍼지 매칭 (소문자, 특수문자 제거 후 비교)
- 소스 간 동일 논문 병합 (DOI 없는 경우 대비)
- 중복 발견 시 citation_count 최대값 유지

---

### Phase 2 — 검색 UX 고도화

#### [P2-1] 검색 사이트형 UI
- 구글/PubMed처럼 상단 검색창 + 좌측 필터 패널
- 날짜 범위 슬라이더 (from~to)
- 인용수 범위 필터
- 정렬 옵션: 관련도 / 최신순 / 인용수
- 결과 하이라이팅 (검색어 강조)
- 검색 히스토리 (로컬스토리지)

#### [P2-2] 키워드 태그 인터페이스
- 검색창에 Pill/Badge형 키워드 태그 추가/삭제
- 태그 AND/OR 조합 검색
- 자동완성 (기존 수집 키워드 기반)

---

### Phase 3 — 키워드 자동 확장 (AI 기반)

#### [P3-1] 관련 키워드 자동 추천
- 사용자가 "바이오" 도메인 추가 시 LLM에 관련 키워드 추천 요청
- 예시 프롬프트: `"'바이오테크' 분야의 기술 논문 수집에 적합한 영어 검색 키워드 10개를 JSON 배열로 반환하시오"`
- 추천된 키워드를 UI에서 선택적으로 활성화

#### [P3-2] 도메인 확장
- 현재 2개 도메인(Physical AI, Telecom/6G) → N개로 확장
- 도메인 추가 시 키워드 자동 시드
- 도메인별 색상 코딩

---

### Phase 4 — 수집 자동화

#### [P4-1] 스케줄링
- APScheduler로 매일 자동 수집 (이미 의존성 설치됨)
- 수집 상태 대시보드 (마지막 수집 시간, 신규 수집 수)
- 실패 알림 (로그 + 선택적 이메일)

#### [P4-2] USPTO 수집기 구현
- PatentsView API 활용
- 미국 특허 데이터 보완

---

### Phase 5 — 분석 고도화

#### [P5-1] 기술 클러스터링
- K-Means 또는 HDBSCAN으로 논문 클러스터링
- 클러스터별 자동 레이블링 (LLM)
- 클러스터 트렌드 시계열

#### [P5-2] 기관·연구자 분석
- 저자 네트워크 그래프
- 기관별 논문/특허 생산량 비교
- 신흥 연구 그룹 탐지

#### [P5-3] 경쟁사 트래킹
- 특정 기업(예: 삼성, 구글, 화웨이) 특허 모니터링
- 기업별 기술 포트폴리오 시각화

---

## 6. 즉시 실행 계획 (우선순위 순)

| 순위 | 작업 | 상태 | 예상 효과 | 난이도 |
|------|------|------|----------|--------|
| 1 | **텍스트 전처리** (HTML 정제, 길이 필터) | ✅ 완료 | 데이터 품질 향상 | 쉬움 |
| 2 | **소프트 중복 제거** (퍼지 제목 매칭) | ✅ 완료 | DB 정확도 향상 | 중간 |
| 3 | **검색 UI 개선** (구글형 레이아웃, 필터 패널) | ✅ 완료 | UX 대폭 향상 | 중간 |
| 4 | **키워드 자동 확장** (LLM 기반 관련어 추천) | 예정 | 수집 범위 확대 | 중간 |
| 5 | **APScheduler 자동 수집** | 예정 | 운영 자동화 | 중간 |
| 6 | **USPTO/PatentsView 수집기** | 예정 | 미국 특허 커버리지 | 어려움 |
| 7 | **클러스터링 + 자동 레이블링** | 예정 | 인사이트 깊이 향상 | 어려움 |
