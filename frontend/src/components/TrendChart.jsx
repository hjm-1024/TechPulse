import { useContext } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { domainLabel } from "../constants/domains";
import { ExpandedContext } from "./ExpandableCard";
import { DomainFilter, useDomainHighlight } from "./DomainFilter";

export default function TrendChart({ data }) {
  const expanded = useContext(ExpandedContext);
  const { selected, setSelected, styleFor, isFaded } = useDomainHighlight(expanded);

  if (!data || data.length === 0) return <Empty />;

  // Derive domain keys from data (all keys except "month")
  const domains = [...new Set(data.flatMap(d => Object.keys(d).filter(k => k !== "month")))];

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>Monthly Publication Trend</h2>

      {expanded && (
        <DomainFilter domains={domains} selected={selected} onChange={setSelected} />
      )}

      <ResponsiveContainer width="100%" height={expanded ? 600 : 320}>
        <LineChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
          <XAxis
            dataKey="month"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#2d3748" }}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{ background: "#1e2330", border: "1px solid #2d3748", borderRadius: 8 }}
            labelStyle={{ color: "#e2e8f0", marginBottom: 4 }}
            itemStyle={{ color: "#cbd5e1" }}
          />
          <Legend
            formatter={(value) => domainLabel(value)}
            wrapperStyle={{ color: "#94a3b8", fontSize: 11 }}
          />
          {/* Render faded lines first so the highlighted one paints on top */}
          {domains
            .slice()
            .sort((a, b) => Number(isFaded(b)) - Number(isFaded(a)))
            .map((d) => {
              const { color, opacity } = styleFor(d);
              const faded = isFaded(d);
              return (
                <Line
                  key={d}
                  type="monotone"
                  dataKey={d}
                  stroke={color}
                  strokeOpacity={opacity}
                  strokeWidth={faded ? 1.2 : (selected === d ? 2.8 : 2)}
                  dot={false}
                  activeDot={faded ? false : { r: 4 }}
                  isAnimationActive={false}
                />
              );
            })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function Empty() {
  return (
    <div style={styles.card}>
      <h2 style={styles.title}>Monthly Publication Trend</h2>
      <p style={{ color: "#64748b", textAlign: "center", padding: 40 }}>No trend data available</p>
    </div>
  );
}

const styles = {
  card: { background: "#1e2330", borderRadius: 12, padding: "24px 28px", marginBottom: 24 },
  title: { fontSize: 16, fontWeight: 600, color: "#e2e8f0", marginBottom: 20 },
};
