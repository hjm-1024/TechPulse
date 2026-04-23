import { useState, useEffect } from "react";

const SOURCE_OPTIONS = ["arxiv", "semantic_scholar", "openalex", "epo"];

function SourcePills({ sources, onChange }) {
  const active = new Set(sources.split(",").map(s => s.trim()).filter(Boolean));
  function toggle(src) {
    const next = new Set(active);
    next.has(src) ? next.delete(src) : next.add(src);
    onChange([...next].join(","));
  }
  return (
    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
      {SOURCE_OPTIONS.map(src => (
        <button
          key={src}
          onClick={() => toggle(src)}
          style={{
            padding: "2px 8px", borderRadius: 4, fontSize: 11, cursor: "pointer",
            fontWeight: 500, border: "1px solid",
            background: active.has(src) ? "#3b82f622" : "transparent",
            color:      active.has(src) ? "#3b82f6"   : "#475569",
            borderColor: active.has(src) ? "#3b82f6"  : "#2d3748",
          }}
        >
          {src}
        </button>
      ))}
    </div>
  );
}

function AddKeywordForm({ onAdd }) {
  const [kw,  setKw]  = useState("");
  const [tag, setTag] = useState("");
  const [src, setSrc] = useState("arxiv,semantic_scholar,openalex,epo");
  const [days, setDays] = useState(365);
  const [busy, setBusy] = useState(false);
  const [err,  setErr]  = useState("");

  async function submit(e) {
    e.preventDefault();
    if (!kw.trim() || !tag.trim()) { setErr("키워드와 도메인 태그는 필수입니다."); return; }
    setBusy(true); setErr("");
    try {
      const resp = await fetch("/api/config/keywords", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword: kw.trim(), domain_tag: tag.trim(), sources: src, days_back: days }),
      });
      if (resp.status === 409) { setErr("이미 존재하는 키워드입니다."); return; }
      if (!resp.ok) { setErr("추가 중 오류가 발생했습니다."); return; }
      setKw(""); setTag("");
      onAdd();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} style={s.addForm}>
      <span style={s.formLabel}>새 키워드 추가</span>
      <input
        value={kw} onChange={e => setKw(e.target.value)}
        placeholder="검색어 (예: neuromorphic computing)"
        style={s.input}
      />
      <input
        value={tag} onChange={e => setTag(e.target.value)}
        placeholder="도메인 태그 (예: neuromorphic)"
        style={s.input}
      />
      <select value={days} onChange={e => setDays(+e.target.value)} style={s.sel}>
        <option value={180}>180일</option>
        <option value={365}>1년</option>
        <option value={730}>2년</option>
      </select>
      <SourcePills sources={src} onChange={setSrc} />
      <button type="submit" style={s.addBtn} disabled={busy}>
        {busy ? "추가 중…" : "+ 추가"}
      </button>
      {err && <span style={s.errText}>{err}</span>}
    </form>
  );
}

function KeywordRow({ item, onToggle, onDelete }) {
  const active = item.active === 1;
  return (
    <tr style={{ borderBottom: "1px solid #1e2330" }}>
      <td style={s.td}>
        <button
          onClick={() => onToggle(item.id, active ? 0 : 1)}
          style={{
            ...s.toggleBtn,
            background: active ? "#10b98122" : "#1e2330",
            color:      active ? "#10b981"   : "#475569",
            borderColor: active ? "#10b981"  : "#2d3748",
          }}
        >
          {active ? "활성" : "비활성"}
        </button>
      </td>
      <td style={{ ...s.td, color: "#f1f5f9", fontWeight: 500 }}>{item.keyword}</td>
      <td style={s.td}>
        <span style={s.tagPill}>{item.domain_tag?.replace(/_/g, " ")}</span>
      </td>
      <td style={s.td}>
        <div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
          {item.sources?.split(",").map(src => (
            <span key={src} style={s.srcPill}>{src}</span>
          ))}
        </div>
      </td>
      <td style={s.td}>{item.days_back}일</td>
      <td style={s.td}>{item.added_at?.slice(0, 10) ?? "–"}</td>
      <td style={s.td}>
        <button onClick={() => onDelete(item.id)} style={s.delBtn}>삭제</button>
      </td>
    </tr>
  );
}

function StatsPanel({ stats }) {
  if (!stats) return null;
  const { totals, paper_sources, patent_sources, keywords } = stats;

  const domainMap = {};
  for (const kw of (keywords ?? [])) {
    const tag = kw.domain_tag;
    if (!domainMap[tag]) {
      domainMap[tag] = {
        papers: kw.paper_count ?? 0,
        patents: kw.patent_count ?? 0,
        paperRange: kw.paper_date_range,
        patentRange: kw.patent_date_range,
      };
    }
  }

  return (
    <div style={s.statsWrap}>
      <div style={s.totalRow}>
        <StatBox label="총 논문" value={totals?.papers ?? 0} color="#3b82f6" />
        <StatBox label="총 특허" value={totals?.patents ?? 0} color="#f59e0b" />
        <StatBox label="도메인 수" value={Object.keys(domainMap).length} color="#10b981" />
        <StatBox label="수집 출처" value={(paper_sources?.length ?? 0) + (patent_sources?.length ?? 0)} color="#a78bfa" />
      </div>

      <div style={s.domainGrid}>
        {Object.entries(domainMap).map(([tag, d]) => (
          <div key={tag} style={s.domainCard}>
            <p style={s.domainName}>{tag.replace(/_/g, " ")}</p>
            <div style={s.domainStats}>
              <span style={{ color: "#3b82f6" }}>논문 {d.papers.toLocaleString()}</span>
              <span style={{ color: "#f59e0b" }}>특허 {d.patents.toLocaleString()}</span>
            </div>
            {d.paperRange && (
              <p style={s.rangeText}>논문: {d.paperRange[0]?.slice(0,7)} ~ {d.paperRange[1]?.slice(0,7)}</p>
            )}
            {d.patentRange && (
              <p style={s.rangeText}>특허: {d.patentRange[0]?.slice(0,7)} ~ {d.patentRange[1]?.slice(0,7)}</p>
            )}
          </div>
        ))}
      </div>

      <div style={s.srcRow}>
        <div style={s.srcGroup}>
          <p style={s.srcTitle}>논문 출처별</p>
          {paper_sources?.map(r => (
            <div key={r.source} style={s.srcItem}>
              <span style={s.srcName}>{r.source}</span>
              <span style={s.srcCount}>{r.count.toLocaleString()}</span>
            </div>
          ))}
        </div>
        <div style={s.srcGroup}>
          <p style={s.srcTitle}>특허 출처별</p>
          {patent_sources?.map(r => (
            <div key={r.source} style={s.srcItem}>
              <span style={s.srcName}>{r.source}</span>
              <span style={s.srcCount}>{r.count.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatBox({ label, value, color }) {
  return (
    <div style={{ ...s.statBox, borderColor: color + "44" }}>
      <p style={{ ...s.statNum, color }}>{value.toLocaleString()}</p>
      <p style={s.statLabel}>{label}</p>
    </div>
  );
}

// ── Domain view panel ──────────────────────────────────────────────────────

function DomainPanel({ onRefresh }) {
  const [domains, setDomains] = useState(null);
  const [expanding, setExpanding] = useState(null);
  const [expandMsg, setExpandMsg] = useState({});
  const [open, setOpen] = useState({});

  useEffect(() => {
    fetch("/api/config/keywords/by-domain").then(r => r.json()).then(setDomains);
  }, []);

  async function handleExpand(domainTag) {
    setExpanding(domainTag);
    setExpandMsg(m => ({ ...m, [domainTag]: "" }));
    try {
      const resp = await fetch("/api/config/keywords/expand", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain_tag: domainTag, count: 8 }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setExpandMsg(m => ({ ...m, [domainTag]: `오류: ${data.detail}` }));
      } else {
        const msg = data.added.length > 0
          ? `✅ ${data.added.length}개 추가: ${data.added.slice(0, 3).join(", ")}${data.added.length > 3 ? "…" : ""}`
          : "새 키워드 없음 (모두 기존 키워드)";
        setExpandMsg(m => ({ ...m, [domainTag]: msg }));
        fetch("/api/config/keywords/by-domain").then(r => r.json()).then(setDomains);
        onRefresh();
      }
    } catch {
      setExpandMsg(m => ({ ...m, [domainTag]: "Ollama 연결 실패" }));
    } finally {
      setExpanding(null);
    }
  }

  if (!domains) return <div style={s.emptyMsg}>로딩 중…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {Object.entries(domains).map(([tag, domain]) => {
        const isOpen = open[tag];
        const activeCount = domain.keywords.filter(k => k.active === 1).length;
        return (
          <div key={tag} style={{ border: "1px solid #1e2330", borderRadius: 10, overflow: "hidden", background: "#0f1117" }}>
            {/* Header */}
            <div
              onClick={() => setOpen(p => ({ ...p, [tag]: !p[tag] }))}
              style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", cursor: "pointer", borderLeft: `4px solid ${domain.color}` }}
            >
              <div style={{ flex: 1 }}>
                <span style={{ fontWeight: 700, color: "#f1f5f9", fontSize: 13 }}>{domain.label_ko}</span>
                <span style={{ marginLeft: 8, fontSize: 11, color: "#64748b" }}>{domain.label}</span>
              </div>
              <span style={{ fontSize: 11, background: domain.color + "22", color: domain.color, padding: "2px 10px", borderRadius: 999, fontWeight: 600 }}>
                활성 {activeCount} / 전체 {domain.keywords.length}
              </span>
              <span style={{ color: "#475569", fontSize: 12 }}>{isOpen ? "▲" : "▼"}</span>
            </div>

            {/* Body */}
            {isOpen && (
              <div style={{ padding: "12px 16px", borderTop: "1px solid #1e2330" }}>
                {/* AI expand button */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                  <button
                    onClick={() => handleExpand(tag)}
                    disabled={expanding === tag}
                    style={{
                      padding: "5px 14px", fontSize: 12, fontWeight: 600, borderRadius: 6, cursor: "pointer",
                      background: "#8b5cf622", color: "#8b5cf6", border: "1px solid #8b5cf644",
                    }}
                  >
                    {expanding === tag ? "⏳ AI 확장 중…" : "✨ AI 키워드 자동확장"}
                  </button>
                  {expandMsg[tag] && (
                    <span style={{ fontSize: 12, color: expandMsg[tag].startsWith("✅") ? "#10b981" : "#f87171" }}>
                      {expandMsg[tag]}
                    </span>
                  )}
                </div>

                {/* Keyword chips */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {domain.keywords.map(kw => (
                    <span
                      key={kw.id}
                      style={{
                        padding: "3px 12px", borderRadius: 999, fontSize: 12, fontWeight: 500,
                        background: kw.active === 1 ? domain.color + "22" : "#1e2330",
                        color:      kw.active === 1 ? domain.color        : "#475569",
                        border: `1px solid ${kw.active === 1 ? domain.color + "55" : "#2d3748"}`,
                      }}
                    >
                      {kw.keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function CollectionConfig() {
  const [keywords, setKeywords] = useState([]);
  const [stats,    setStats]    = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [activeSection, setActiveSection] = useState("domains");

  async function fetchKeywords() {
    const resp = await fetch("/api/config/keywords");
    const json = await resp.json();
    setKeywords(json);
  }

  async function fetchStats() {
    setLoadingStats(true);
    try {
      const resp = await fetch("/api/config/stats");
      const json = await resp.json();
      setStats(json);
    } finally {
      setLoadingStats(false);
    }
  }

  useEffect(() => {
    fetchKeywords();
    fetchStats();
  }, []);

  async function handleToggle(id, active) {
    await fetch(`/api/config/keywords/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active }),
    });
    fetchKeywords();
  }

  async function handleDelete(id) {
    if (!confirm("이 키워드를 삭제할까요?")) return;
    await fetch(`/api/config/keywords/${id}`, { method: "DELETE" });
    fetchKeywords();
    fetchStats();
  }

  const sections = [
    { id: "domains",  label: "🗂️ 도메인별 키워드" },
    { id: "stats",    label: "📊 수집 현황" },
    { id: "keywords", label: "🔑 전체 키워드 관리" },
  ];

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <h2 style={s.heading}>⚙️ 수집 설정</h2>
        <p style={s.desc}>
          미래유망기술 도메인별 키워드를 확인하고, AI로 관련 키워드를 자동 확장하세요
        </p>
      </div>

      <div style={s.tabs}>
        {sections.map(sec => (
          <button
            key={sec.id}
            onClick={() => setActiveSection(sec.id)}
            style={{
              ...s.tabBtn,
              background:   activeSection === sec.id ? "#3b82f6" : "transparent",
              color:        activeSection === sec.id ? "#fff"    : "#94a3b8",
              borderBottom: activeSection === sec.id ? "2px solid #3b82f6" : "2px solid transparent",
            }}
          >
            {sec.label}
          </button>
        ))}
      </div>

      {activeSection === "domains" && (
        <DomainPanel onRefresh={() => { fetchKeywords(); fetchStats(); }} />
      )}

      {activeSection === "stats" && (
        loadingStats
          ? <div style={s.emptyMsg}>데이터 로딩 중…</div>
          : <StatsPanel stats={stats} />
      )}

      {activeSection === "keywords" && (
        <div>
          <AddKeywordForm onAdd={() => { fetchKeywords(); fetchStats(); }} />
          <div style={{ overflowX: "auto", marginTop: 16 }}>
            <table style={s.table}>
              <thead>
                <tr style={{ borderBottom: "1px solid #2d3748" }}>
                  {["상태", "키워드", "도메인", "출처", "기간", "등록일", ""].map(h => (
                    <th key={h} style={s.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {keywords.map(item => (
                  <KeywordRow
                    key={item.id}
                    item={item}
                    onToggle={handleToggle}
                    onDelete={handleDelete}
                  />
                ))}
              </tbody>
            </table>
            {keywords.length === 0 && (
              <div style={s.emptyMsg}>등록된 키워드가 없습니다</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const s = {
  wrap: { background: "#131720", borderRadius: 12, padding: 24 },
  header: { marginBottom: 16 },
  heading: { fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: "0 0 4px" },
  desc: { fontSize: 12, color: "#64748b", margin: 0 },
  tabs: { display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid #1e2330" },
  tabBtn: {
    padding: "8px 18px", border: "none", cursor: "pointer",
    fontSize: 13, fontWeight: 500, borderRadius: "6px 6px 0 0",
    transition: "all 0.15s",
  },

  // Stats panel
  statsWrap: { display: "flex", flexDirection: "column", gap: 20 },
  totalRow:  { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 },
  statBox: {
    background: "#0f1117", borderRadius: 8, padding: "14px 18px",
    border: "1px solid", textAlign: "center",
  },
  statNum:   { fontSize: 24, fontWeight: 700, margin: 0 },
  statLabel: { fontSize: 12, color: "#64748b", margin: "4px 0 0" },
  domainGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 },
  domainCard: {
    background: "#0f1117", borderRadius: 8, padding: "14px 16px",
    border: "1px solid #1e2330",
  },
  domainName: { fontSize: 13, fontWeight: 600, color: "#cbd5e1", margin: "0 0 8px", textTransform: "capitalize" },
  domainStats: { display: "flex", gap: 16, fontSize: 14, fontWeight: 700, marginBottom: 6 },
  rangeText: { fontSize: 11, color: "#475569", margin: "2px 0 0" },
  srcRow:  { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 },
  srcGroup: { background: "#0f1117", borderRadius: 8, padding: "14px 16px", border: "1px solid #1e2330" },
  srcTitle: { fontSize: 12, fontWeight: 600, color: "#64748b", margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.06em" },
  srcItem: { display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #1e2330" },
  srcName: { fontSize: 13, color: "#94a3b8" },
  srcCount: { fontSize: 13, color: "#cbd5e1", fontWeight: 600 },

  // Add form
  addForm: {
    display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
    padding: "14px 16px", background: "#0f1117", borderRadius: 8,
    border: "1px solid #2d3748",
  },
  formLabel: { fontSize: 12, fontWeight: 600, color: "#64748b", whiteSpace: "nowrap" },
  input: {
    background: "#1e2330", border: "1px solid #2d3748", borderRadius: 6,
    color: "#e2e8f0", padding: "6px 10px", fontSize: 12, minWidth: 180,
    outline: "none",
  },
  sel: {
    background: "#1e2330", border: "1px solid #2d3748", borderRadius: 6,
    color: "#cbd5e1", padding: "5px 10px", fontSize: 12, cursor: "pointer",
  },
  addBtn: {
    padding: "6px 14px", background: "#10b981", border: "none", borderRadius: 6,
    color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600,
  },
  errText: { fontSize: 12, color: "#f87171" },

  // Keyword table
  table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th: { padding: "8px 12px", textAlign: "left", fontSize: 11, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" },
  td: { padding: "10px 12px", color: "#94a3b8", verticalAlign: "middle" },
  toggleBtn: {
    padding: "3px 10px", borderRadius: 4, fontSize: 11,
    cursor: "pointer", fontWeight: 600, border: "1px solid",
  },
  tagPill: {
    fontSize: 11, background: "#1e2330", color: "#94a3b8",
    padding: "2px 8px", borderRadius: 4,
  },
  srcPill: {
    fontSize: 10, background: "#1e293b", color: "#60a5fa",
    padding: "1px 6px", borderRadius: 3,
  },
  delBtn: {
    padding: "3px 8px", background: "transparent", border: "1px solid #3d1515",
    borderRadius: 4, color: "#f87171", cursor: "pointer", fontSize: 11,
  },
  emptyMsg: { textAlign: "center", padding: "40px 0", color: "#334155", fontSize: 14 },
};
