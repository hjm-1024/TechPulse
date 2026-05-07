import { useState } from "react";
import { DOMAIN_META } from "../constants/domains";

const METHOD_INFO = {
  tfidf: {
    label: "TF-IDF",
    desc: "문서 빈도(TF) × 역문서빈도(IDF). 빠르고 통계적 — 새로 등장한 핵심 용어 발굴에 적합.",
    scoreLabel: "TF·IDF",
  },
  bert: {
    label: "BERT (KeyBERT)",
    desc: "Ollama 임베딩 기반 의미 유사도. 후보 키워드와 문서 집합 중심 임베딩의 코사인 유사도로 정렬.",
    scoreLabel: "코사인",
  },
};

export default function TrendAnalysis() {
  const [method, setMethod] = useState("tfidf");
  const [type,   setType]   = useState("papers");
  const [domain, setDomain] = useState("");
  const [days,   setDays]   = useState(365);
  const [topK,   setTopK]   = useState(20);
  const [data,   setData]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,  setError]   = useState(null);

  async function load() {
    setLoading(true);
    setData(null);
    setError(null);
    try {
      const params = new URLSearchParams({ method, type, domain, days, top_k: topK });
      const resp = await fetch(`/api/insights/trend-analysis?${params}`);
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        setError(err.detail || `서버 오류 (${resp.status})`);
        return;
      }
      setData(await resp.json());
    } catch (e) {
      setError(`네트워크 오류: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  const keywords = data?.keywords ?? [];
  const maxScore = keywords.length ? keywords[0].score : 1;
  const info = METHOD_INFO[method];
  const gridCols = method === "tfidf"
    ? "40px 1fr 80px 60px 60px 200px"
    : "40px 1fr 80px 60px 200px";

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <h2 style={s.heading}>📈 연구동향 분석 — 키워드 추출</h2>
        <p style={s.desc}>{info.desc}</p>
      </div>

      <div style={s.controls}>
        <div style={s.controlGroup}>
          <span style={s.label}>방법</span>
          <div style={s.toggle}>
            {Object.entries(METHOD_INFO).map(([k, v]) => (
              <button
                key={k}
                onClick={() => setMethod(k)}
                style={{
                  ...s.toggleBtn,
                  background: method === k ? "#3b82f6" : "transparent",
                  color:      method === k ? "#fff"    : "#94a3b8",
                }}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>

        <div style={s.controlGroup}>
          <span style={s.label}>유형</span>
          <select value={type} onChange={e => setType(e.target.value)} style={s.sel}>
            <option value="papers">논문</option>
            <option value="patents">특허</option>
          </select>
        </div>

        <div style={s.controlGroup}>
          <span style={s.label}>도메인</span>
          <select value={domain} onChange={e => setDomain(e.target.value)} style={s.sel}>
            <option value="">전체</option>
            {Object.entries(DOMAIN_META).map(([tag, m]) => (
              <option key={tag} value={tag}>{m.label_ko}  {m.label}</option>
            ))}
          </select>
        </div>

        <div style={s.controlGroup}>
          <span style={s.label}>기간</span>
          <select value={days} onChange={e => setDays(+e.target.value)} style={s.sel}>
            <option value={90}>90일</option>
            <option value={180}>180일</option>
            <option value={365}>1년</option>
            <option value={730}>2년</option>
            <option value={1095}>3년</option>
          </select>
        </div>

        <div style={s.controlGroup}>
          <span style={s.label}>Top-K</span>
          <select value={topK} onChange={e => setTopK(+e.target.value)} style={s.sel}>
            {[10, 20, 30, 50].map(v => <option key={v} value={v}>{v}개</option>)}
          </select>
        </div>

        <button onClick={load} style={s.btn} disabled={loading}>
          {loading ? "분석 중…" : "분석 실행"}
        </button>

        {data && (
          <span style={s.stat}>
            대상 {data.subset_size}건
            {data.corpus_size != null && ` · 코퍼스 ${data.corpus_size}건`}
            {data.embedded_now != null && data.embedded_now > 0 && ` · 새 임베딩 ${data.embedded_now}건`}
          </span>
        )}
      </div>

      {!data && !loading && !error && (
        <div style={s.empty}>
          위 컨트롤로 방법(TF-IDF / BERT)·유형·도메인·기간을 정하고 "분석 실행"을 누르세요
        </div>
      )}

      {loading && (
        <div style={s.empty}>
          {method === "bert" ? "BERT 임베딩 계산 중… (Ollama 호출, 30~60초 소요 가능)" : "TF-IDF 계산 중…"}
        </div>
      )}

      {error && <div style={{ ...s.empty, color: "#ef4444", fontSize: 13 }}>{error}</div>}

      {data && keywords.length === 0 && (
        <div style={s.empty}>해당 조건에 맞는 키워드가 없습니다.</div>
      )}

      {keywords.length > 0 && (
        <div style={s.table}>
          <div style={{ ...s.tableHead, gridTemplateColumns: gridCols }}>
            <span style={s.colRank}>#</span>
            <span style={s.colTerm}>키워드</span>
            <span style={s.colScore}>{info.scoreLabel}</span>
            <span style={s.colTf}>TF</span>
            {method === "tfidf" && <span style={s.colDf}>DF</span>}
            <span style={s.colBar}>분포</span>
          </div>
          {keywords.map((kw, i) => {
            const pct = maxScore > 0 ? (kw.score / maxScore) * 100 : 0;
            return (
              <div key={kw.term} style={{ ...s.tableRow, gridTemplateColumns: gridCols }}>
                <span style={s.colRank}>{i + 1}</span>
                <span style={s.colTerm}>{kw.term}</span>
                <span style={s.colScore}>{kw.score}</span>
                <span style={s.colTf}>{kw.tf}</span>
                {method === "tfidf" && <span style={s.colDf}>{kw.df}</span>}
                <span style={s.colBar}>
                  <span style={{ ...s.bar, width: `${pct}%` }} />
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const s = {
  wrap: { background: "#131720", borderRadius: 12, padding: 24, marginBottom: 24 },
  header: { marginBottom: 16 },
  heading: { fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: "0 0 4px" },
  desc: { fontSize: 12, color: "#64748b", margin: 0 },
  controls: {
    display: "flex", alignItems: "center", gap: 12, marginBottom: 20,
    flexWrap: "wrap", padding: "12px 16px",
    background: "#0f1117", borderRadius: 8,
  },
  controlGroup: { display: "flex", alignItems: "center", gap: 6 },
  label: { fontSize: 12, color: "#64748b", whiteSpace: "nowrap" },
  sel: {
    background: "#1e2330", border: "1px solid #2d3748", borderRadius: 6,
    color: "#cbd5e1", padding: "5px 10px", fontSize: 12, cursor: "pointer",
  },
  toggle: {
    display: "flex", background: "#1e2330", border: "1px solid #2d3748",
    borderRadius: 6, overflow: "hidden",
  },
  toggleBtn: {
    border: "none", padding: "5px 12px", fontSize: 12, fontWeight: 600,
    cursor: "pointer", transition: "all 0.15s",
  },
  btn: {
    padding: "7px 18px", background: "#3b82f6", border: "none", borderRadius: 6,
    color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600,
  },
  stat: { fontSize: 12, color: "#64748b" },
  empty: { textAlign: "center", padding: "60px 0", color: "#334155", fontSize: 14 },
  table: { display: "flex", flexDirection: "column" },
  tableHead: {
    display: "grid",
    gap: 12, padding: "8px 12px", fontSize: 11,
    color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em",
    borderBottom: "1px solid #1e2330",
  },
  tableRow: {
    display: "grid",
    gap: 12, padding: "10px 12px", fontSize: 13,
    color: "#e2e8f0", alignItems: "center",
    borderBottom: "1px solid #1e2330",
  },
  colRank:  { fontSize: 12, color: "#475569", fontWeight: 700 },
  colTerm:  { fontWeight: 500 },
  colScore: { fontFamily: "monospace", fontSize: 12, color: "#3b82f6" },
  colTf:    { fontFamily: "monospace", fontSize: 12, color: "#94a3b8" },
  colDf:    { fontFamily: "monospace", fontSize: 12, color: "#64748b" },
  colBar:   { display: "flex", alignItems: "center" },
  bar: {
    height: 6, background: "linear-gradient(90deg, #3b82f6, #8b5cf6)",
    borderRadius: 3, minWidth: 2,
  },
};
