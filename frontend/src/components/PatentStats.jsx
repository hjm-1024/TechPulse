const DOMAIN_COLOR = { physical_ai_robotics: "#10b981", telecom_6g: "#f59e0b" };
const DOMAIN_LABEL = { physical_ai_robotics: "Physical AI & Robotics", telecom_6g: "Telecom & 6G" };
const SOURCE_COLOR = { patentsview: "#ef4444", kipris: "#3b82f6" };
const FLAG = { US: "🇺🇸", KR: "🇰🇷" };

export default function PatentStats({ data }) {
  if (!data || data.total === 0) return (
    <div style={styles.empty}>
      특허 데이터 없음 — <code>python run_collectors.py --type patents --days 365</code> 실행 후 새로고침
    </div>
  );

  return (
    <div style={styles.grid}>
      <div style={{ ...styles.card, borderTop: "3px solid #ef4444" }}>
        <p style={styles.label}>Total Patents</p>
        <p style={{ ...styles.value, color: "#ef4444" }}>{data.total.toLocaleString()}</p>
      </div>

      {Object.entries(data.by_domain).map(([k, v]) => (
        <div key={k} style={{ ...styles.card, borderTop: `3px solid ${DOMAIN_COLOR[k] ?? "#64748b"}` }}>
          <p style={styles.label}>{DOMAIN_LABEL[k] ?? k}</p>
          <p style={{ ...styles.value, color: DOMAIN_COLOR[k] ?? "#64748b" }}>{v.toLocaleString()}</p>
        </div>
      ))}

      <div style={{ ...styles.card, borderTop: "3px solid #64748b", gridColumn: "1 / -1" }}>
        <p style={styles.label}>By Source & Country</p>
        <div style={styles.row}>
          {Object.entries(data.by_source).map(([src, count]) => (
            <div key={src} style={styles.chip}>
              <span style={{ ...styles.dot, background: SOURCE_COLOR[src] ?? "#94a3b8" }} />
              <span style={styles.srcName}>{src === "patentsview" ? "PatentsView (US)" : "KIPRIS (KR)"}</span>
              <span style={styles.srcCount}>{count.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 24 },
  card: { background: "#1e2330", borderRadius: 12, padding: "20px 24px" },
  label: { fontSize: 12, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 },
  value: { fontSize: 32, fontWeight: 700 },
  row: { display: "flex", gap: 24, flexWrap: "wrap", marginTop: 12 },
  chip: { display: "flex", alignItems: "center", gap: 8 },
  dot: { width: 10, height: 10, borderRadius: "50%", display: "inline-block" },
  srcName: { fontSize: 13, color: "#cbd5e1" },
  srcCount: { fontSize: 13, fontWeight: 600, color: "#e2e8f0" },
  empty: { background: "#1e2330", borderRadius: 12, padding: 24, color: "#64748b", fontSize: 13, marginBottom: 24 },
};
