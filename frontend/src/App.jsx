import { useState } from "react";
import { useApi } from "./hooks/useApi";
import StatsCards from "./components/StatsCards";
import TrendChart from "./components/TrendChart";
import SourceChart from "./components/SourceChart";
import TopPapers from "./components/TopPapers";

export default function App() {
  const [topDomain, setTopDomain] = useState(null);

  const { data: summary } = useApi("/api/summary");
  const { data: trend } = useApi("/api/trend");
  const { data: sources } = useApi("/api/sources");
  const { data: top } = useApi(
    `/api/top?limit=20${topDomain ? `&domain=${topDomain}` : ""}`
  );

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>TechPulse</h1>
          <p style={styles.subtitle}>Tech Trend Intelligence Dashboard</p>
        </div>
        <div style={styles.domains}>
          <DomainTag color="#10b981">Physical AI & Robotics</DomainTag>
          <DomainTag color="#f59e0b">Telecom & 6G</DomainTag>
        </div>
      </header>

      <main style={styles.main}>
        {summary ? <StatsCards data={summary} /> : <Skeleton height={120} />}

        <div style={styles.row2}>
          {trend ? <TrendChart data={trend} /> : <Skeleton height={360} />}
          {sources ? <SourceChart data={sources} /> : <Skeleton height={320} />}
        </div>

        {top ? (
          <TopPapers data={top} domain={topDomain} onDomainChange={setTopDomain} />
        ) : (
          <Skeleton height={400} />
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

function Skeleton({ height }) {
  return (
    <div style={{ background: "#1e2330", borderRadius: 12, height, marginBottom: 24, opacity: 0.5 }} />
  );
}

const styles = {
  root: { minHeight: "100vh", background: "#0f1117" },
  header: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "24px 40px", borderBottom: "1px solid #1e2330",
    background: "#131720",
  },
  title: { fontSize: 24, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.5px" },
  subtitle: { fontSize: 13, color: "#64748b", marginTop: 2 },
  domains: { display: "flex", gap: 8 },
  main: { maxWidth: 1280, margin: "0 auto", padding: "32px 40px" },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 0 },
};
