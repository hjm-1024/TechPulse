import { useState, useEffect, useRef } from "react";
import SearchResults from "./SearchResults";

// ── Constants ────────────────────────────────────────────────────────────────
const DOMAINS = [
  { value: "",                    label: "전체 도메인" },
  { value: "physical_ai_robotics", label: "Physical AI & Robotics" },
  { value: "telecom_6g",           label: "Telecom & 6G" },
];

const PAPER_SOURCES  = ["arxiv", "semantic_scholar", "openalex"];
const PATENT_SOURCES = ["epo", "kipris", "lens"];

const SOURCE_LABEL = {
  arxiv:            "arXiv",
  semantic_scholar: "Semantic Scholar",
  openalex:         "OpenAlex",
  epo:              "EPO (유럽)",
  kipris:           "KIPRIS (한국)",
  lens:             "Lens.org",
};

const SORT_OPTIONS = [
  { value: "citation_count", label: "인용수 높은순" },
  { value: "published_date", label: "최신순" },
];

const MAX_HISTORY = 8;
const HISTORY_KEY = "tp_search_history";

// ── History helpers ──────────────────────────────────────────────────────────
function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); }
  catch { return []; }
}
function saveHistory(term) {
  if (!term?.trim()) return;
  const next = [term.trim(), ...loadHistory().filter(h => h !== term.trim())].slice(0, MAX_HISTORY);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
}
function clearHistory() {
  localStorage.removeItem(HISTORY_KEY);
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function SearchPage({ search }) {
  const [history, setHistory]       = useState(loadHistory);
  const [showDropdown, setShowDrop] = useState(false);
  const inputRef = useRef(null);

  const sources    = search.type === "papers" ? PAPER_SOURCES : PATENT_SOURCES;
  const isSemantic = search.mode === "semantic";

  function handleSubmit(e) {
    e.preventDefault();
    if (search.query.trim()) {
      saveHistory(search.query.trim());
      setHistory(loadHistory());
    }
    setShowDrop(false);
    inputRef.current?.blur();
  }

  function applyHistory(term) {
    search.setQuery(term);
    setShowDrop(false);
  }

  function handleClearHistory() {
    clearHistory();
    setHistory([]);
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    function onDown(e) {
      if (!e.target.closest("[data-search-wrap]")) setShowDrop(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  const resultCount = search.results?.total ?? search.results?.length ?? null;

  return (
    <div style={s.page}>
      {/* ═══════════════════════════════════════════════════════════════════
          TOP: Hero search bar
      ═══════════════════════════════════════════════════════════════════ */}
      <div style={s.hero}>
        {/* Type + Mode toggles */}
        <div style={s.toggleRow}>
          <div style={s.toggleGroup}>
            {["papers", "patents"].map(t => (
              <button
                key={t}
                onClick={() => { search.setType(t); search.setSource(""); }}
                style={{ ...s.typeBtn, ...(search.type === t ? s.typeBtnActive : {}) }}
              >
                {t === "papers" ? "📄 Papers" : "📋 Patents"}
              </button>
            ))}
          </div>

          <div style={s.sep} />

          <div style={s.toggleGroup}>
            <button
              onClick={() => search.setMode("keyword")}
              style={{ ...s.modeBtn, ...(search.mode === "keyword" ? s.modeBtnKw : {}) }}
            >
              키워드 검색
            </button>
            <button
              onClick={() => search.setMode("semantic")}
              style={{ ...s.modeBtn, ...(isSemantic ? s.modeBtnSem : {}) }}
              title="Ollama nomic-embed-text 임베딩 기반 의미 검색"
            >
              ✨ AI 시맨틱
            </button>
          </div>
        </div>

        {/* Search input */}
        <form onSubmit={handleSubmit} data-search-wrap style={{ position: "relative" }}>
          <div style={{
            ...s.inputBox,
            borderColor:  isSemantic ? "#7c3aed" : "#3b82f6",
            boxShadow:    isSemantic ? "0 0 0 3px #7c3aed22" : "0 0 0 3px #3b82f622",
          }}>
            <span style={s.searchIcon}>{isSemantic ? "✨" : "🔍"}</span>

            <input
              ref={inputRef}
              type="text"
              value={search.query}
              onChange={e => search.setQuery(e.target.value)}
              onFocus={() => setShowDrop(true)}
              placeholder={
                isSemantic
                  ? "자연어로 검색 — 예: 로봇 팔 제어 강화학습"
                  : search.type === "papers"
                    ? "논문 제목·초록 검색… 예: humanoid robot control"
                    : "특허 제목·설명 검색…"
              }
              style={s.input}
              autoComplete="off"
              autoFocus
            />

            {search.query && (
              <button type="button" onClick={() => { search.setQuery(""); inputRef.current?.focus(); }} style={s.clearBtn}>
                ✕
              </button>
            )}

            <button type="submit" style={{ ...s.submitBtn, background: isSemantic ? "#7c3aed" : "#3b82f6" }}>
              검색
            </button>
          </div>

          {/* History dropdown */}
          {showDropdown && history.length > 0 && (
            <div style={s.dropdown}>
              <div style={s.dropHeader}>
                <span style={s.dropLabel}>최근 검색</span>
                <button type="button" onClick={handleClearHistory} style={s.dropClear}>모두 지우기</button>
              </div>
              {history.map(h => (
                <button
                  key={h}
                  type="button"
                  onMouseDown={() => applyHistory(h)}
                  style={s.dropItem}
                >
                  <span style={{ opacity: 0.4, fontSize: 12 }}>🕒</span>
                  {h}
                </button>
              ))}
            </div>
          )}
        </form>

        {/* Stats bar */}
        <div style={s.statsBar}>
          {search.loading
            ? <span style={s.statsText}>검색 중…</span>
            : resultCount != null
              ? <span style={s.statsText}><b style={{ color: "#f1f5f9" }}>{resultCount.toLocaleString()}</b>개 결과</span>
              : null
          }
          {isSemantic && (
            <span style={s.semTag}>임베딩 기반 의미 검색 · nomic-embed-text</span>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          2-column: sidebar + results
      ═══════════════════════════════════════════════════════════════════ */}
      <div style={s.columns}>
        {/* ── Sidebar ────────────────────────────────────────────────── */}
        <aside style={s.sidebar}>
          {/* Domain */}
          <FilterBlock title="도메인">
            {DOMAINS.map(d => (
              <RadioRow
                key={d.value}
                name="domain"
                value={d.value}
                checked={search.domain === d.value}
                onChange={() => search.setDomain(d.value)}
                label={d.label}
              />
            ))}
          </FilterBlock>

          {/* Source */}
          <FilterBlock title="소스">
            <RadioRow
              name="source" value="" checked={search.source === ""}
              onChange={() => search.setSource("")} label="전체" />
            {sources.map(src => (
              <RadioRow
                key={src}
                name="source"
                value={src}
                checked={search.source === src}
                onChange={() => search.setSource(src)}
                label={SOURCE_LABEL[src] ?? src}
              />
            ))}
          </FilterBlock>

          {/* Sort (keyword + papers only) */}
          {search.type === "papers" && !isSemantic && (
            <FilterBlock title="정렬">
              {SORT_OPTIONS.map(o => (
                <RadioRow
                  key={o.value}
                  name="sort"
                  value={o.value}
                  checked={search.sortBy === o.value}
                  onChange={() => search.setSortBy(o.value)}
                  label={o.label}
                />
              ))}
            </FilterBlock>
          )}

          {/* Recent searches */}
          {history.length > 0 && (
            <FilterBlock title="최근 검색">
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {history.map(h => (
                  <button
                    key={h}
                    onClick={() => applyHistory(h)}
                    style={s.histChip}
                    title={h}
                  >
                    {h.length > 20 ? h.slice(0, 20) + "…" : h}
                  </button>
                ))}
                <button onClick={handleClearHistory} style={s.histClear}>지우기</button>
              </div>
            </FilterBlock>
          )}
        </aside>

        {/* ── Results ────────────────────────────────────────────────── */}
        <main style={s.results}>
          <SearchResults
            results={search.results}
            loading={search.loading}
            error={search.error}
            type={search.type}
            page={search.page}
            setPage={search.setPage}
            query={search.query}
          />
        </main>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────
function FilterBlock({ title, children }) {
  return (
    <div style={s.filterBlock}>
      <div style={s.filterTitle}>{title}</div>
      {children}
    </div>
  );
}

function RadioRow({ name, value, checked, onChange, label }) {
  return (
    <label style={s.radioRow}>
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={onChange}
        style={{ accentColor: "#3b82f6", cursor: "pointer", flexShrink: 0 }}
      />
      <span style={{ ...s.radioLabel, ...(checked ? s.radioLabelActive : {}) }}>
        {label}
      </span>
    </label>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = {
  page: { display: "flex", flexDirection: "column", gap: 20 },

  /* Hero */
  hero: {
    background: "#131720",
    border: "1px solid #1e2330",
    borderRadius: 16,
    padding: "24px 28px",
  },
  toggleRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 18,
    flexWrap: "wrap",
  },
  toggleGroup: { display: "flex", gap: 4 },
  sep: { width: 1, height: 22, background: "#2d3748", margin: "0 4px" },

  typeBtn: {
    padding: "7px 18px",
    border: "1px solid #2d3748",
    borderRadius: 8,
    background: "transparent",
    color: "#94a3b8",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 500,
    transition: "all 0.15s",
  },
  typeBtnActive: { background: "#3b82f6", borderColor: "#3b82f6", color: "#fff" },

  modeBtn: {
    padding: "6px 14px",
    border: "1px solid #2d3748",
    borderRadius: 8,
    background: "transparent",
    color: "#64748b",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
    transition: "all 0.15s",
  },
  modeBtnKw:  { background: "#1e2330", borderColor: "#3b82f6", color: "#93c5fd" },
  modeBtnSem: { background: "#2e1065", borderColor: "#7c3aed", color: "#c4b5fd" },

  /* Input */
  inputBox: {
    display: "flex",
    alignItems: "center",
    background: "#0f1117",
    border: "2px solid #3b82f6",
    borderRadius: 12,
    padding: "0 16px",
    transition: "all 0.2s",
  },
  searchIcon: { fontSize: 18, marginRight: 12, opacity: 0.6, flexShrink: 0 },
  input: {
    flex: 1,
    background: "transparent",
    border: "none",
    outline: "none",
    color: "#f1f5f9",
    fontSize: 16,
    padding: "16px 0",
    fontFamily: "inherit",
    minWidth: 0,
  },
  clearBtn: {
    background: "none",
    border: "none",
    color: "#64748b",
    cursor: "pointer",
    fontSize: 15,
    padding: "4px 8px",
    borderRadius: 4,
    flexShrink: 0,
  },
  submitBtn: {
    border: "none",
    color: "#fff",
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 600,
    padding: "9px 22px",
    borderRadius: 8,
    marginLeft: 10,
    flexShrink: 0,
    transition: "opacity 0.15s",
  },

  /* Dropdown */
  dropdown: {
    position: "absolute",
    top: "calc(100% + 6px)",
    left: 0, right: 0,
    background: "#1a2235",
    border: "1px solid #2d3748",
    borderRadius: 12,
    zIndex: 200,
    overflow: "hidden",
    boxShadow: "0 10px 40px #00000070",
  },
  dropHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 16px 8px",
    borderBottom: "1px solid #2d3748",
  },
  dropLabel: { fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 },
  dropClear: { background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 11 },
  dropItem: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    width: "100%",
    background: "none",
    border: "none",
    color: "#cbd5e1",
    cursor: "pointer",
    fontSize: 14,
    padding: "11px 16px",
    textAlign: "left",
    transition: "background 0.1s",
  },

  /* Stats */
  statsBar: { display: "flex", alignItems: "center", gap: 14, marginTop: 12, minHeight: 22 },
  statsText: { fontSize: 13, color: "#64748b" },
  semTag: {
    fontSize: 11,
    color: "#a78bfa",
    background: "#2e106522",
    padding: "3px 10px",
    borderRadius: 6,
    border: "1px solid #4c1d9540",
  },

  /* 2-column */
  columns: {
    display: "grid",
    gridTemplateColumns: "210px 1fr",
    gap: 20,
    alignItems: "start",
  },

  /* Sidebar */
  sidebar: {
    background: "#131720",
    border: "1px solid #1e2330",
    borderRadius: 14,
    padding: "18px 16px",
    position: "sticky",
    top: 24,
  },
  filterBlock: {
    marginBottom: 22,
    paddingBottom: 18,
    borderBottom: "1px solid #1e2330",
  },
  filterTitle: {
    fontSize: 10,
    fontWeight: 700,
    color: "#475569",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    marginBottom: 10,
  },
  radioRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    cursor: "pointer",
    padding: "3px 0",
  },
  radioLabel: { fontSize: 13, color: "#94a3b8", transition: "color 0.1s" },
  radioLabelActive: { color: "#f1f5f9", fontWeight: 500 },

  histChip: {
    background: "#1e2330",
    border: "1px solid #2d3748",
    borderRadius: 6,
    color: "#94a3b8",
    cursor: "pointer",
    fontSize: 12,
    padding: "5px 10px",
    textAlign: "left",
    transition: "all 0.1s",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  histClear: {
    background: "none",
    border: "none",
    color: "#475569",
    cursor: "pointer",
    fontSize: 11,
    padding: "2px 0",
    textAlign: "left",
    marginTop: 2,
  },

  /* Results */
  results: { minWidth: 0 },
};
