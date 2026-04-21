import { useState } from "react";
import { useApi } from "./hooks/useApi";
import { useSearch } from "./hooks/useSearch";
import StatsCards from "./components/StatsCards";
import TrendChart from "./components/TrendChart";
import SourceChart from "./components/SourceChart";
import TopPapers from "./components/TopPapers";
import PatentStats from "./components/PatentStats";
import PatentTrendChart from "./components/PatentTrendChart";
import TopAssignees from "./components/TopAssignees";
import SearchBar from "./components/SearchBar";
import SearchResults from "./components/SearchResults";

const TABS = [
  { id: "papers",  label: "📄 Papers"  },
  { id: "patents", label: "📋 Patents" },
  { id: "search",  label: "🔍 Search"  },
];

export default function App() {
  const [tab, setTab]         = useState("papers");
  const [topDomain, setTopDomain] = useState(null);

  // Dashboard data
  const { data: summary } = useApi("/api/summary");
  const { data: trend }   = useApi("/api/trend");
  const { data: sources } = useApi("/api/sources");
  const { data: top }     = useApi(`/api/top?limit=20${topDomain ? `&domain=${topDomain}` : ""}`);
  const { data: patentSummary } = useApi("/api/patents/summary");
  const { data: patentTrend }   = useApi("/api/patents/trend");
  const { data: assignees }     = useApi("/api/patents/top-assignees?limit=12");

  // Search state (always mounted so query persists across tab switches)
  const search = useSearch();

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>TechPulse</h1>
          <p style={styles.subtitle}>Tech Trend Intelligence Dashboard</p>
        </div>
        <div style={styles.right}>
          <nav style={styles.tabs}>
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  setTab(t.id);
                  if (t.id === "search") search.setType("papers");
                }}
                style={{
                  ...styles.tab,
                  color:        tab === t.id ? "#fff"    : "#94a3b8",
                  background:   tab === t.id ? "#3b82f6" : "transparent",
                  borderBottom: tab === t.id ? "2px solid #3b82f6" : "2px solid transparent",
                }}
              >
                {t.label}
              </button>
            ))}
          </nav>
          <div style={styles.domains}>
            <DomainTag color="#10b981">Physical AI & Robotics</DomainTag>
            <DomainTag color="#f59e0b">Telecom & 6G</DomainTag>
          </div>
        </div>
      </header>

      <main style={styles.main}>
        {/* ── Papers dashboard ── */}
        {tab === "papers" && (
          <>
            {summary ? <StatsCards data={summary} /> : <Skeleton h={120} />}
            <div style={styles.row2}>
              {trend   ? <TrendChart data={trend} />   : <Skeleton h={360} />}
              {sources ? <SourceChart data={sources} /> : <Skeleton h={320} />}
            </div>
            {top
              ? <TopPapers data={top} domain={topDomain} onDomainChange={setTopDomain} />
              : <Skeleton h={400} />}
          </>
        )}

        {/* ── Patents dashboard ── */}
        {tab === "patents" && (
          <>
            <PatentStats data={patentSummary} />
            <div style={styles.row2}>
              <PatentTrendChart data={patentTrend} />
              <TopAssignees data={assignees} />
            </div>
          </>
        )}

        {/* ── Search ── */}
        {tab === "search" && (
          <>
            <SearchBar
              type={search.type}       setType={search.setType}
              query={search.query}     setQuery={search.setQuery}
              domain={search.domain}   setDomain={search.setDomain}
              source={search.source}   setSource={search.setSource}
              sortBy={search.sortBy}   setSortBy={search.setSortBy}
              total={search.results?.total}
            />
            <SearchResults
              results={search.results}
              loading={search.loading}
              error={search.error}
              type={search.type}
              page={search.page}
              setPage={search.setPage}
            />
          </>
        )}
      </main>
    </div>
  );
}

function DomainTag({ color, children }) {
  return (
    <span style={{ background: color + "22", color, padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 500 }}>
      {children}
    </span>
  );
}

function Skeleton({ h }) {
  return <div style={{ background: "#1e2330", borderRadius: 12, height: h, marginBottom: 24, opacity: 0.4 }} />;
}

const styles = {
  root: { minHeight: "100vh", background: "#0f1117" },
  header: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "20px 40px", borderBottom: "1px solid #1e2330", background: "#131720",
  },
  title:    { fontSize: 24, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.5px" },
  subtitle: { fontSize: 13, color: "#64748b", marginTop: 2 },
  right:    { display: "flex", alignItems: "center", gap: 24 },
  tabs:     { display: "flex", gap: 4 },
  tab: {
    padding: "8px 18px", border: "none", cursor: "pointer",
    fontSize: 13, fontWeight: 500, borderRadius: "6px 6px 0 0",
    transition: "all 0.15s",
  },
  domains: { display: "flex", gap: 8 },
  main:    { maxWidth: 1280, margin: "0 auto", padding: "32px 40px" },
  row2:    { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 },
};
