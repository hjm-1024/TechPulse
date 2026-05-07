import { domainLabel, domainColor } from "../constants/domains";

const SOURCE_COLOR = { lens: "#ef4444", epo: "#f97316", kipris: "#3b82f6" };
const SOURCE_LABEL = {
  lens:   "Lens.org (Worldwide)",
  epo:    "EPO OPS (Worldwide)",
  kipris: "KIPRIS (한국)",
};

export default function PatentStats({ data }) {
  if (!data || data.total === 0) return (
    <div style={styles.empty}>
      <p style={{ marginBottom: 12, fontSize: 14, color: "#94a3b8" }}>특허 데이터 없음</p>
      <p style={{ marginBottom: 8 }}>특허 수집을 위해 아래 API 키 중 하나 이상을 <code>.env</code>에 추가하세요:</p>
      <ul style={{ margin: "8px 0 12px 16px", lineHeight: 1.8 }}>
        <li><b>LENS_API_KEY</b> — <a href="https://www.lens.org" target="_blank" rel="noreferrer" style={{ color: "#60a5fa" }}>lens.org</a> 무료 가입 → Profile → API Access</li>
        <li><b>EPO_OPS_KEY / EPO_OPS_SECRET</b> — <a href="https://developers.epo.org" target="_blank" rel="noreferrer" style={{ color: "#60a5fa" }}>developers.epo.org</a> 무료 등록</li>
        <li><b>KIPRIS_API_KEY</b> — <a href="https://www.data.go.kr" target="_blank" rel="noreferrer" style={{ color: "#60a5fa" }}>data.go.kr</a> 키프리스 API 신청 (한국 특허)</li>
      </ul>
      <code style={{ fontSize: 12 }}>python run_collectors.py --type patents --days 2300</code>
    </div>
  );

  return (
    <div style={styles.grid}>
      <div style={{ ...styles.card, borderTop: "3px solid #ef4444" }}>
        <p style={styles.label}>Total Patents</p>
        <p style={{ ...styles.value, color: "#ef4444" }}>{data.total.toLocaleString()}</p>
      </div>

      {Object.entries(data.by_domain).map(([k, v]) => (
        <div key={k} style={{ ...styles.card, borderTop: `3px solid ${domainColor(k)}` }}>
          <p style={styles.label}>{domainLabel(k)}</p>
          <p style={{ ...styles.value, color: domainColor(k) }}>{v.toLocaleString()}</p>
        </div>
      ))}

      <div style={{ ...styles.card, borderTop: "3px solid #64748b", gridColumn: "1 / -1" }}>
        <p style={styles.label}>By Source & Country</p>
        <div style={styles.row}>
          {Object.entries(data.by_source).map(([src, count]) => (
            <div key={src} style={styles.chip}>
              <span style={{ ...styles.dot, background: SOURCE_COLOR[src] ?? "#94a3b8" }} />
              <span style={styles.srcName}>{SOURCE_LABEL[src] ?? src}</span>
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
  label: { fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 },
  value: { fontSize: 32, fontWeight: 700 },
  row: { display: "flex", gap: 24, flexWrap: "wrap", marginTop: 12 },
  chip: { display: "flex", alignItems: "center", gap: 8 },
  dot: { width: 10, height: 10, borderRadius: "50%", display: "inline-block" },
  srcName: { fontSize: 13, color: "#cbd5e1" },
  srcCount: { fontSize: 13, fontWeight: 600, color: "#e2e8f0" },
  empty: { background: "#1e2330", borderRadius: 12, padding: "20px 24px", color: "#64748b", fontSize: 13, marginBottom: 24, lineHeight: 1.6 },
};
