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
import SearchPage from "./components/SearchPage";
import EmergingPapers from "./components/EmergingPapers";
import TrendAnalysis from "./components/TrendAnalysis";
import NetworkGraph from "./components/NetworkGraph";
import CollectionConfig from "./components/CollectionConfig";
import ExpandableCard from "./components/ExpandableCard";

const TABS = [
  { id: "papers",   label: "📄 Papers"   },
  { id: "patents",  label: "📋 Patents"  },
  { id: "search",   label: "🔍 Search"   },
  { id: "insights", label: "📊 인사이트" },
  { id: "config",   label: "⚙️ 수집 설정" },
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
      </header>

      <main style={styles.main}>
        {/* ── Papers dashboard ── */}
        {tab === "papers" && (
          <>
            {summary ? <StatsCards data={summary} /> : <Skeleton h={120} />}
            <div style={styles.row2}>
              <ExpandableCard>
                {trend ? <TrendChart data={trend} /> : <Skeleton h={360} />}
              </ExpandableCard>
              <ExpandableCard>
                {sources ? <SourceChart data={sources} /> : <Skeleton h={320} />}
              </ExpandableCard>
            </div>
            <ExpandableCard>
              {top
                ? <TopPapers data={top} domain={topDomain} onDomainChange={setTopDomain} />
                : <Skeleton h={400} />}
            </ExpandableCard>
          </>
        )}

        {/* ── Patents dashboard ── */}
        {tab === "patents" && (
          <>
            <PatentStats data={patentSummary} />
            <div style={styles.row2}>
              <ExpandableCard>
                <PatentTrendChart data={patentTrend} />
              </ExpandableCard>
              <ExpandableCard>
                <TopAssignees data={assignees} />
              </ExpandableCard>
            </div>
          </>
        )}

        {/* ── Search ── */}
        {tab === "search" && <SearchPage search={search} />}

        {/* ── Insights ── */}
        {tab === "insights" && (
          <>
            <ExpandableCard>
              <EmergingPapers />
            </ExpandableCard>
            <ExpandableCard>
              <TrendAnalysis />
            </ExpandableCard>
            <div style={{ marginTop: 24 }}>
              <div style={{ marginBottom: 12 }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: "0 0 4px" }}>
                  🕸️ 유사도 네트워크
                </h2>
                <p style={{ fontSize: 12, color: "#64748b", margin: 0 }}>
                  임베딩 기반 코사인 유사도로 연결된 논문·특허 클러스터 시각화
                </p>
              </div>
              <ExpandableCard>
                <NetworkGraph />
              </ExpandableCard>
            </div>
          </>
        )}

        {/* ── Collection Config ── */}
        {tab === "config" && <CollectionConfig />}
      </main>
    </div>
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
  tabs:     { display: "flex", gap: 4 },
  tab: {
    padding: "8px 18px", border: "none", cursor: "pointer",
    fontSize: 13, fontWeight: 500, borderRadius: "6px 6px 0 0",
    transition: "all 0.15s",
  },
  main:    { maxWidth: 1280, margin: "0 auto", padding: "32px 40px" },
  row2:    { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 },
};
