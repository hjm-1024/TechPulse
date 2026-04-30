import { useContext } from "react";
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { domainLabel as getDomainLabel } from "../constants/domains";
import { ExpandedContext } from "./ExpandableCard";
import { DomainFilter, useDomainHighlight } from "./DomainFilter";

const SOURCE_COLOR = {
  arxiv: "#f97316",
  semantic_scholar: "#8b5cf6",
  openalex: "#06b6d4",
};

export default function SourceChart({ data }) {
  const expanded = useContext(ExpandedContext);
  const { selected, setSelected, isFaded } = useDomainHighlight(expanded);

  if (!data || data.length === 0) return null;

  // Pivot: [{domain_tag, domain (label), arxiv, semantic_scholar, openalex}]
  const pivot = {};
  const sources = new Set();
  for (const row of data) {
    const tag = row.domain_tag;
    pivot[tag] = pivot[tag] ?? { domain_tag: tag, domain: getDomainLabel(tag) };
    pivot[tag][row.source] = row.count;
    sources.add(row.source);
  }
  const chartData = Object.values(pivot);
  const domains = chartData.map((c) => c.domain_tag);

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>Papers by Source & Domain</h2>

      {expanded && (
        <DomainFilter domains={domains} selected={selected} onChange={setSelected} />
      )}

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
            <Bar
              key={src}
              dataKey={src}
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            >
              {chartData.map((entry, idx) => {
                const faded = isFaded(entry.domain_tag);
                return (
                  <Cell
                    key={idx}
                    fill={faded ? "#475569" : SOURCE_COLOR[src] ?? "#94a3b8"}
                    fillOpacity={faded ? 0.25 : 1}
                  />
                );
              })}
            </Bar>
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
