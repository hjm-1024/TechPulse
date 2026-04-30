import { useContext } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { domainColor, domainLabel } from "../constants/domains";
import { ExpandedContext } from "./ExpandableCard";
import { DomainFilter, useDomainHighlight } from "./DomainFilter";

export default function PatentTrendChart({ data }) {
  const expanded = useContext(ExpandedContext);
  const { selected, setSelected, isFaded } = useDomainHighlight(expanded);

  if (!data || data.length === 0) return null;

  const domains = [...new Set(data.flatMap(d => Object.keys(d).filter(k => k !== "month")))];

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>Patent Filing Trend (Monthly)</h2>

      {expanded && (
        <DomainFilter domains={domains} selected={selected} onChange={setSelected} />
      )}

      <ResponsiveContainer width="100%" height={expanded ? 560 : 280}>
        <AreaChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
          <defs>
            {domains.map((key) => {
              const color = domainColor(key);
              return (
                <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              );
            })}
            <linearGradient id="grad-faded" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#475569" stopOpacity={0.12} />
              <stop offset="95%" stopColor="#475569" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
          <XAxis dataKey="month" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#2d3748" }} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{ background: "#1e2330", border: "1px solid #2d3748", borderRadius: 8 }}
            labelStyle={{ color: "#e2e8f0", marginBottom: 4 }}
          />
          <Legend formatter={(v) => domainLabel(v)} wrapperStyle={{ color: "#94a3b8", fontSize: 11 }} />
          {/* Faded series first so the highlighted one paints on top */}
          {domains
            .slice()
            .sort((a, b) => Number(isFaded(b)) - Number(isFaded(a)))
            .map((key) => {
              const faded = isFaded(key);
              const color = faded ? "#475569" : domainColor(key);
              return (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={color}
                  strokeOpacity={faded ? 0.25 : 1}
                  strokeWidth={faded ? 1 : (selected === key ? 2.6 : 2)}
                  fill={faded ? "url(#grad-faded)" : `url(#grad-${key})`}
                  dot={false}
                  isAnimationActive={false}
                />
              );
            })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const styles = {
  card: { background: "#1e2330", borderRadius: 12, padding: "24px 28px", marginBottom: 24 },
  title: { fontSize: 16, fontWeight: 600, color: "#e2e8f0", marginBottom: 20 },
};
