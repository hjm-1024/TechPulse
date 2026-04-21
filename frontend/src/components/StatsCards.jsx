const DOMAIN_LABEL = {
  physical_ai_robotics: "Physical AI & Robotics",
  telecom_6g: "Telecom & 6G",
};

const SOURCE_COLOR = {
  arxiv: "#f97316",
  semantic_scholar: "#8b5cf6",
  openalex: "#06b6d4",
};

export default function StatsCards({ data }) {
  if (!data) return null;

  const cards = [
    { label: "Total Papers", value: data.total.toLocaleString(), accent: "#3b82f6" },
    ...Object.entries(data.by_domain).map(([k, v]) => ({
      label: DOMAIN_LABEL[k] ?? k,
      value: v.toLocaleString(),
      accent: k === "physical_ai_robotics" ? "#10b981" : "#f59e0b",
    })),
  ];

  return (
    <div style={styles.grid}>
      {cards.map((c) => (
        <div key={c.label} style={{ ...styles.card, borderTop: `3px solid ${c.accent}` }}>
          <p style={styles.label}>{c.label}</p>
          <p style={{ ...styles.value, color: c.accent }}>{c.value}</p>
        </div>
      ))}

      <div style={{ ...styles.card, borderTop: "3px solid #64748b", gridColumn: "1 / -1" }}>
        <p style={styles.label}>By Source</p>
        <div style={styles.sourceRow}>
          {Object.entries(data.by_source).map(([src, count]) => (
            <div key={src} style={styles.sourceChip}>
              <span style={{ ...styles.dot, background: SOURCE_COLOR[src] ?? "#94a3b8" }} />
              <span style={styles.srcName}>{src.replace("_", " ")}</span>
              <span style={styles.srcCount}>{count.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: 16,
    marginBottom: 32,
  },
  card: {
    background: "#1e2330",
    borderRadius: 12,
    padding: "20px 24px",
  },
  label: { fontSize: 12, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 },
  value: { fontSize: 32, fontWeight: 700 },
  sourceRow: { display: "flex", gap: 24, flexWrap: "wrap", marginTop: 12 },
  sourceChip: { display: "flex", alignItems: "center", gap: 8 },
  dot: { width: 10, height: 10, borderRadius: "50%", display: "inline-block" },
  srcName: { fontSize: 13, color: "#cbd5e1", textTransform: "capitalize" },
  srcCount: { fontSize: 13, fontWeight: 600, color: "#e2e8f0" },
};
