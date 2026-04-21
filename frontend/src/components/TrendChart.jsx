import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const COLORS = {
  physical_ai_robotics: "#10b981",
  telecom_6g: "#f59e0b",
};

const LABELS = {
  physical_ai_robotics: "Physical AI & Robotics",
  telecom_6g: "Telecom & 6G",
};

export default function TrendChart({ data }) {
  if (!data || data.length === 0) return <Empty />;

  const domains = Object.keys(COLORS);

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>Monthly Publication Trend</h2>
      <ResponsiveContainer width="100%" height={320}>
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
            formatter={(value) => LABELS[value] ?? value}
            wrapperStyle={{ color: "#94a3b8", fontSize: 12 }}
          />
          {domains.map((d) => (
            <Line
              key={d}
              type="monotone"
              dataKey={d}
              stroke={COLORS[d]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
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
