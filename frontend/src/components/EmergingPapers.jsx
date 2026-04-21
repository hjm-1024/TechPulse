import { useState } from "react";

const DOMAIN_COLOR = {
  physical_ai_robotics: "#10b981",
  telecom_6g: "#f59e0b",
};

function ScoreBadge({ score }) {
  const pct = Math.min(100, Math.round(score * 500));
  const color = score > 0.12 ? "#ef4444" : score > 0.07 ? "#f59e0b" : "#3b82f6";
  return (
    <span style={{ ...s.badge, background: color + "22", color, border: `1px solid ${color}44` }}>
      🔥 {score.toFixed(4)}
    </span>
  );
}

function DomainDot({ tag }) {
  const color = DOMAIN_COLOR[tag] ?? "#60a5fa";
  return (
    <span style={{ ...s.domainBadge, background: color + "22", color }}>
      {tag?.replace(/_/g, " ") ?? "기타"}
    </span>
  );
}

function PatentRow({ item }) {
  return (
    <div style={s.row}>
      <div style={s.rowTop}>
        <DomainDot tag={item.domain_tag} />
        <span style={s.patentNum}>{item.patent_number}</span>
        <span style={s.dateSmall}>{(item.publication_date || "").slice(0, 7)}</span>
      </div>
      <p style={s.title}>{item.title}</p>
      <div style={s.rowMeta}>
        <span style={s.meta}>{item.assignee || "–"}</span>
        <span style={s.meta}>{item.country}</span>
      </div>
    </div>
  );
}

function PaperRow({ item }) {
  return (
    <div style={s.row}>
      <div style={s.rowTop}>
        <DomainDot tag={item.domain_tag} />
        <ScoreBadge score={item.emergence_score} />
        <span style={s.citBadge}>인용 {item.citation_count ?? 0}</span>
        <span style={s.dateSmall}>{(item.published_date || "").slice(0, 7)}</span>
      </div>
      <p style={s.title}>{item.title}</p>
      <p style={s.meta}>{item.authors?.slice(0, 80)}{item.authors?.length > 80 ? "…" : ""}</p>
    </div>
  );
}

export default function EmergingPapers() {
  const [type,   setType]   = useState("papers");
  const [domain, setDomain] = useState("");
  const [days,   setDays]   = useState(365);
  const [limit,  setLimit]  = useState(20);
  const [data,   setData]   = useState(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setData(null);
    try {
      const params = new URLSearchParams({ type, domain, days, limit });
      const resp = await fetch(`/api/insights/emerging?${params}`);
      const json = await resp.json();
      setData(json);
    } finally {
      setLoading(false);
    }
  }

  const items = data?.items ?? [];

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <h2 style={s.heading}>🔥 신흥 기술 탐지</h2>
        <p style={s.desc}>인용 속도(인용수 / 경과일)가 높은 문서 — 최근 주목받는 연구를 빠르게 발견</p>
      </div>

      <div style={s.controls}>
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
            <option value="physical_ai_robotics">Physical AI & Robotics</option>
            <option value="telecom_6g">Telecom & 6G</option>
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
          <span style={s.label}>표시 수</span>
          <select value={limit} onChange={e => setLimit(+e.target.value)} style={s.sel}>
            {[10, 20, 30, 50].map(v => <option key={v} value={v}>{v}개</option>)}
          </select>
        </div>

        <button onClick={load} style={s.btn} disabled={loading}>
          {loading ? "분석 중…" : "분석 실행"}
        </button>

        {data && (
          <span style={s.stat}>
            {data.total}건 중 {items.length}건 표시
          </span>
        )}
      </div>

      {!data && !loading && (
        <div style={s.empty}>
          위 "분석 실행" 버튼을 눌러 신흥 기술 트렌드를 확인하세요
        </div>
      )}

      {loading && (
        <div style={s.empty}>분석 중…</div>
      )}

      {data && items.length === 0 && (
        <div style={s.empty}>해당 조건에 맞는 데이터가 없습니다</div>
      )}

      {items.length > 0 && (
        <div style={s.list}>
          {type === "papers"
            ? items.map((item, i) => (
                <div key={item.id} style={s.item}>
                  <span style={s.rank}>#{i + 1}</span>
                  <div style={{ flex: 1 }}>
                    <PaperRow item={item} />
                  </div>
                </div>
              ))
            : items.map((item, i) => (
                <div key={item.id} style={s.item}>
                  <span style={s.rank}>#{i + 1}</span>
                  <div style={{ flex: 1 }}>
                    <PatentRow item={item} />
                  </div>
                </div>
              ))
          }
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
  btn: {
    padding: "7px 18px", background: "#3b82f6", border: "none", borderRadius: 6,
    color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600,
  },
  stat: { fontSize: 12, color: "#64748b" },
  empty: {
    textAlign: "center", padding: "60px 0",
    color: "#334155", fontSize: 14,
  },
  list: { display: "flex", flexDirection: "column", gap: 0 },
  item: {
    display: "flex", alignItems: "flex-start", gap: 12,
    padding: "12px 0",
    borderBottom: "1px solid #1e2330",
  },
  rank: {
    minWidth: 32, fontSize: 12, color: "#475569",
    fontWeight: 700, paddingTop: 2,
  },
  row: { flex: 1 },
  rowTop: { display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" },
  title: { fontSize: 14, color: "#e2e8f0", margin: "0 0 4px", lineHeight: 1.4 },
  rowMeta: { display: "flex", gap: 12 },
  meta: { fontSize: 11, color: "#64748b" },
  dateSmall: { fontSize: 11, color: "#475569" },
  badge: {
    fontSize: 11, fontWeight: 600, padding: "2px 7px",
    borderRadius: 4, whiteSpace: "nowrap",
  },
  domainBadge: {
    fontSize: 10, fontWeight: 600, padding: "2px 7px",
    borderRadius: 4, textTransform: "uppercase", letterSpacing: "0.03em",
  },
  citBadge: {
    fontSize: 11, color: "#94a3b8",
    background: "#1e2330", padding: "2px 6px", borderRadius: 4,
  },
  patentNum: { fontSize: 11, color: "#94a3b8", fontFamily: "monospace" },
};
