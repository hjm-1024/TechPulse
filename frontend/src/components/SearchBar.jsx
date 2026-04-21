const PAPER_SOURCES  = ["arxiv", "semantic_scholar", "openalex"];
const PATENT_SOURCES = ["epo", "kipris"];
const DOMAINS = [
  { value: "", label: "All Domains" },
  { value: "physical_ai_robotics", label: "Physical AI & Robotics" },
  { value: "telecom_6g", label: "Telecom & 6G" },
];
const SORT_OPTIONS = [
  { value: "citation_count", label: "Citations" },
  { value: "published_date", label: "Date" },
];

export default function SearchBar({
  type, setType,
  query, setQuery,
  domain, setDomain,
  source, setSource,
  sortBy, setSortBy,
  total,
}) {
  const sources = type === "papers" ? PAPER_SOURCES : PATENT_SOURCES;

  return (
    <div style={s.wrap}>
      {/* Type toggle */}
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
        {total != null && (
          <span style={s.total}>{total.toLocaleString()} results</span>
        )}
      </div>

      {/* Search input */}
      <div style={s.inputWrap}>
        <span style={s.icon}>🔍</span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={type === "papers"
            ? "Search title or abstract…"
            : "Search patent title or description…"}
          style={s.input}
          autoFocus
        />
        {query && (
          <button onClick={() => setQuery("")} style={s.clear}>✕</button>
        )}
      </div>

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

        {type === "papers" && (
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
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={s.select}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {prefix}{o.label}
        </option>
      ))}
    </select>
  );
}

const s = {
  wrap: { marginBottom: 28 },
  typeRow: { display: "flex", alignItems: "center", gap: 8, marginBottom: 16 },
  typeBtn: {
    padding: "7px 18px", border: "1px solid #2d3748", borderRadius: 8,
    background: "transparent", color: "#94a3b8", cursor: "pointer",
    fontSize: 13, fontWeight: 500, transition: "all 0.15s",
  },
  typeBtnActive: { background: "#3b82f6", borderColor: "#3b82f6", color: "#fff" },
  total: { marginLeft: "auto", fontSize: 13, color: "#64748b" },
  inputWrap: {
    position: "relative", display: "flex", alignItems: "center",
    background: "#1e2330", border: "1px solid #2d3748", borderRadius: 12,
    padding: "0 16px", marginBottom: 12,
  },
  icon: { fontSize: 16, marginRight: 10, opacity: 0.5 },
  input: {
    flex: 1, background: "transparent", border: "none", outline: "none",
    color: "#e2e8f0", fontSize: 15, padding: "14px 0",
    fontFamily: "inherit",
  },
  clear: {
    background: "none", border: "none", color: "#64748b",
    cursor: "pointer", fontSize: 14, padding: 4,
  },
  filters: { display: "flex", gap: 10, flexWrap: "wrap" },
  select: {
    background: "#1e2330", border: "1px solid #2d3748", borderRadius: 8,
    color: "#cbd5e1", padding: "7px 12px", fontSize: 13,
    cursor: "pointer", outline: "none",
  },
};
