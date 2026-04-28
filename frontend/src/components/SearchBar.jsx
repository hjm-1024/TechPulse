import { DOMAIN_META } from "../constants/domains";

const PAPER_SOURCES  = ["arxiv", "semantic_scholar", "openalex"];
const PATENT_SOURCES = ["epo", "kipris", "lens"];
const DOMAINS = [
  { value: "", label: "All Domains" },
  ...Object.entries(DOMAIN_META).map(([tag, m]) => ({
    value: tag,
    label: `${m.label_ko}  ${m.label}`,
  })),
];
const SORT_OPTIONS = [
  { value: "citation_count", label: "Citations" },
  { value: "published_date", label: "Date" },
];

export default function SearchBar({
  type, setType,
  mode, setMode,
  query, setQuery,
  domain, setDomain,
  source, setSource,
  sortBy, setSortBy,
  total,
}) {
  const sources   = type === "papers" ? PAPER_SOURCES : PATENT_SOURCES;
  const isSemantic = mode === "semantic";

  return (
    <div style={s.wrap}>
      {/* Row 1: Papers/Patents toggle + mode toggle + result count */}
      <div style={s.typeRow}>
        {["papers", "patents"].map((t) => (
          <button
            key={t}
            onClick={() => { setType(t); setSource(""); }}
            style={{ ...s.typeBtn, ...(type === t ? s.typeBtnActive : {}) }}
          >
            {t === "papers" ? "📄 Papers" : "📋 Patents"}
          </button>
        ))}

        <div style={s.modeSep} />

        {/* Keyword / AI Semantic toggle */}
        <div style={s.modeToggle}>
          <button
            onClick={() => setMode("keyword")}
            style={{ ...s.modeBtn, ...(mode === "keyword" ? s.modeBtnActive : {}) }}
          >
            키워드 검색
          </button>
          <button
            onClick={() => setMode("semantic")}
            style={{ ...s.modeBtn, ...(mode === "semantic" ? s.modeSemanticActive : {}) }}
            title="nomic-embed-text로 의미 기반 유사도 검색 (Ollama 필요)"
          >
            ✨ AI 시맨틱 검색
          </button>
        </div>

        {total != null && (
          <span style={s.total}>{total.toLocaleString()} results</span>
        )}
      </div>

      {/* Search input */}
      <div style={{
        ...s.inputWrap,
        borderColor: isSemantic ? "#7c3aed" : "#2d3748",
        boxShadow: isSemantic ? "0 0 0 2px #7c3aed33" : "none",
      }}>
        <span style={s.icon}>{isSemantic ? "✨" : "🔍"}</span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={isSemantic
            ? "자연어로 검색 — 예: 로봇 팔 제어 강화학습"
            : type === "papers"
              ? "Search title or abstract…"
              : "Search patent title or description…"}
          style={s.input}
          autoFocus
        />
        {query && (
          <button onClick={() => setQuery("")} style={s.clear}>✕</button>
        )}
      </div>

      {isSemantic && (
        <div style={s.semanticHint}>
          의미 기반 검색 — 정확한 키워드 없이도 비슷한 개념의 문서를 찾아요 (Ollama + nomic-embed-text)
        </div>
      )}

      {/* Filter row */}
      <div style={s.filters}>
        <Select value={domain} onChange={setDomain} options={DOMAINS} />

        <Select
          value={source}
          onChange={setSource}
          options={[
            { value: "", label: "All Sources" },
            ...sources.map((s) => ({ value: s, label: s.replace("_", " ") })),
          ]}
        />

        {type === "papers" && mode === "keyword" && (
          <Select
            value={sortBy}
            onChange={setSortBy}
            options={SORT_OPTIONS}
            prefix="Sort: "
          />
        )}
      </div>
    </div>
  );
}

function Select({ value, onChange, options, prefix = "" }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} style={s.select}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{prefix}{o.label}</option>
      ))}
    </select>
  );
}

const s = {
  wrap: { marginBottom: 28 },
  typeRow: { display: "flex", alignItems: "center", gap: 8, marginBottom: 16, flexWrap: "wrap" },
  typeBtn: {
    padding: "7px 18px", border: "1px solid #2d3748", borderRadius: 8,
    background: "transparent", color: "#94a3b8", cursor: "pointer",
    fontSize: 13, fontWeight: 500, transition: "all 0.15s",
  },
  typeBtnActive: { background: "#3b82f6", borderColor: "#3b82f6", color: "#fff" },
  modeSep: { width: 1, height: 20, background: "#2d3748", margin: "0 4px" },
  modeToggle: { display: "flex", gap: 4 },
  modeBtn: {
    padding: "6px 14px", border: "1px solid #2d3748", borderRadius: 8,
    background: "transparent", color: "#64748b", cursor: "pointer",
    fontSize: 12, fontWeight: 500, transition: "all 0.15s",
  },
  modeBtnActive: { background: "#1e2330", borderColor: "#3b82f6", color: "#93c5fd" },
  modeSemanticActive: { background: "#2e1065", borderColor: "#7c3aed", color: "#c4b5fd" },
  total: { marginLeft: "auto", fontSize: 13, color: "#64748b" },
  inputWrap: {
    position: "relative", display: "flex", alignItems: "center",
    background: "#1e2330", border: "1px solid #2d3748", borderRadius: 12,
    padding: "0 16px", marginBottom: 8, transition: "border-color 0.2s, box-shadow 0.2s",
  },
  icon: { fontSize: 16, marginRight: 10, opacity: 0.7 },
  input: {
    flex: 1, background: "transparent", border: "none", outline: "none",
    color: "#e2e8f0", fontSize: 15, padding: "14px 0", fontFamily: "inherit",
  },
  clear: { background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 14, padding: 4 },
  semanticHint: {
    fontSize: 11, color: "#7c3aed", marginBottom: 10,
    padding: "4px 12px", background: "#2e106533", borderRadius: 6,
  },
  filters: { display: "flex", gap: 10, flexWrap: "wrap", marginTop: 4 },
  select: {
    background: "#1e2330", border: "1px solid #2d3748", borderRadius: 8,
    color: "#cbd5e1", padding: "7px 12px", fontSize: 13, cursor: "pointer", outline: "none",
  },
};
