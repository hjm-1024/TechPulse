import { DOMAIN_META, domainColor, domainLabel } from "../constants/domains";

const SOURCE_COLOR = {
  arxiv:            "#f97316",
  semantic_scholar: "#8b5cf6",
  openalex:         "#06b6d4",
};

const DOMAIN_OPTIONS = [
  { value: null, label: "All" },
  ...Object.entries(DOMAIN_META).map(([tag, m]) => ({
    value: tag,
    label: m.label_ko,
  })),
];

export default function TopPapers({ data, domain, onDomainChange }) {
  if (!data) return null;

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h2 style={styles.title}>Top Cited Papers</h2>
        <select
          value={domain ?? ""}
          onChange={e => onDomainChange(e.target.value || null)}
          style={styles.domainSel}
        >
          {DOMAIN_OPTIONS.map(o => (
            <option key={String(o.value)} value={o.value ?? ""}>{o.label}</option>
          ))}
        </select>
      </div>

      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              {["Title", "Authors", "Year", "Source", "Domain", "Citations"].map((h) => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((p, i) => {
              const dc = domainColor(p.domain_tag);
              return (
                <tr key={i} style={styles.tr}>
                  <td style={{ ...styles.td, maxWidth: 340 }}>
                    {p.doi
                      ? <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer" style={styles.link}>{p.title}</a>
                      : <span>{p.title}</span>
                    }
                  </td>
                  <td style={{ ...styles.td, color: "#94a3b8", maxWidth: 200 }}>
                    {(p.authors || "").split(", ").slice(0, 2).join(", ")}
                    {(p.authors || "").split(", ").length > 2 ? " et al." : ""}
                  </td>
                  <td style={styles.td}>{(p.published_date || "").slice(0, 4)}</td>
                  <td style={styles.td}>
                    <span style={{ ...styles.badge, background: (SOURCE_COLOR[p.source] ?? "#94a3b8") + "22", color: SOURCE_COLOR[p.source] ?? "#94a3b8" }}>
                      {p.source?.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td style={styles.td}>
                    <span style={{ ...styles.badge, background: dc + "22", color: dc }}>
                      {domainLabel(p.domain_tag)}
                    </span>
                  </td>
                  <td style={{ ...styles.td, textAlign: "right", fontWeight: 600, color: "#f1f5f9" }}>
                    {(p.citation_count || 0).toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const styles = {
  card: { background: "#1e2330", borderRadius: 12, padding: "24px 28px", marginBottom: 24 },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  title: { fontSize: 16, fontWeight: 600, color: "#e2e8f0" },
  domainSel: {
    background: "#131720", border: "1px solid #2d3748", borderRadius: 8,
    color: "#cbd5e1", padding: "6px 12px", fontSize: 12, cursor: "pointer", outline: "none",
  },
  tableWrap: { overflowX: "auto" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "8px 12px", fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, borderBottom: "1px solid #2d3748" },
  tr: { borderBottom: "1px solid #1a2035" },
  td: { padding: "12px 12px", fontSize: 13, color: "#cbd5e1", verticalAlign: "top" },
  badge: { display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 500 },
  link: { color: "#60a5fa", textDecoration: "none" },
};
