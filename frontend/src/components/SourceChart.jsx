import { useContext } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { domainLabel as getDomainLabel } from "../constants/domains";
import { ExpandedContext } from "./ExpandableCard";

const SOURCE_COLOR = {
  arxiv: "#f97316",
  semantic_scholar: "#8b5cf6",
  openalex: "#06b6d4",
};

export default function SourceChart({ data }) {
  const expanded = useContext(ExpandedContext);
  if (!data || data.length === 0) return null;

  // Pivot: [{domain_tag, arxiv, semantic_scholar, openalex}]
  const pivot = {};
  const sources = new Set();
  for (const row of data) {
    const domain = getDomainLabel(row.domain_tag);
    pivot[domain] = pivot[domain] ?? { domain };
    pivot[domain][row.source] = row.count;
    sources.add(row.source);
  }
  const chartData = Object.values(pivot);

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>Papers by Source & Domain</h2>
      <ResponsiveContainer width="100%" height={expanded ? 560 : 280}>
        <BarChart data={chartData} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
          <XAxis dataKey="domain" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={{ stroke: "#2d3748" }} tickLine={false} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: "#1e2330", border: "1px solid #2d3748", borderRadius: 8 }}
            labelStyle={{ color: "#e2e8f0", marginBottom: 4 }}
          />
          <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
          {[...sources].map((src) => (
            <Bar key={src} dataKey={src} fill={SOURCE_COLOR[src] ?? "#94a3b8"} radius={[4, 4, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

const styles = {
  card: { background: "#1e2330", borderRadius: 12, padding: "24px 28px", marginBottom: 24 },
  title: { fontSize: 16, fontWeight: 600, color: "#e2e8f0", marginBottom: 20 },
};
