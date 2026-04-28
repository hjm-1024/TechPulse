import { domainColor, domainLabel } from "../constants/domains";

export default function TopAssignees({ data }) {
  if (!data || data.length === 0) return null;

  const max = Math.max(...data.map((d) => d.count), 1);

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>Top Patent Assignees</h2>
      <div style={styles.list}>
        {data.map((row, i) => {
          const color = domainColor(row.domain_tag);
          const pct = (row.count / max) * 100;
          return (
            <div key={i} style={styles.row}>
              <span style={styles.rank}>{i + 1}</span>
              <div style={styles.info}>
                <div style={styles.nameRow}>
                  <span style={styles.name}>{row.assignee}</span>
                  <span style={{ ...styles.domainBadge, background: color + "22", color }}>
                    {domainLabel(row.domain_tag)}
                  </span>
                </div>
                <div style={styles.barTrack}>
                  <div style={{ ...styles.barFill, width: `${pct}%`, background: color }} />
                </div>
              </div>
              <span style={styles.count}>{row.count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles = {
  card: { background: "#1e2330", borderRadius: 12, padding: "24px 28px", marginBottom: 24 },
  title: { fontSize: 16, fontWeight: 600, color: "#e2e8f0", marginBottom: 20 },
  list: { display: "flex", flexDirection: "column", gap: 14 },
  row: { display: "flex", alignItems: "center", gap: 12 },
  rank: { width: 24, textAlign: "right", fontSize: 12, color: "#64748b", flexShrink: 0 },
  info: { flex: 1 },
  nameRow: { display: "flex", alignItems: "center", gap: 8, marginBottom: 5 },
  name: { fontSize: 13, color: "#e2e8f0", fontWeight: 500 },
  domainBadge: { fontSize: 10, padding: "1px 7px", borderRadius: 10, fontWeight: 500 },
  barTrack: { height: 4, background: "#2d3748", borderRadius: 2, overflow: "hidden" },
  barFill: { height: "100%", borderRadius: 2, transition: "width 0.6s ease" },
  count: { width: 36, textAlign: "right", fontSize: 13, fontWeight: 600, color: "#94a3b8", flexShrink: 0 },
};
