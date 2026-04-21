import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const COLORS = { physical_ai_robotics: "#10b981", telecom_6g: "#f59e0b" };
const LABELS = { physical_ai_robotics: "Physical AI & Robotics", telecom_6g: "Telecom & 6G" };

export default function PatentTrendChart({ data }) {
  if (!data || data.length === 0) return null;

  return (
    <div style={styles.card}>
      <h2 style={styles.title}>Patent Filing Trend (Monthly)</h2>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
          <defs>
            {Object.entries(COLORS).map(([key, color]) => (
              <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
          <XAxis dataKey="month" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#2d3748" }} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{ background: "#1e2330", border: "1px solid #2d3748", borderRadius: 8 }}
            labelStyle={{ color: "#e2e8f0", marginBottom: 4 }}
          />
          <Legend formatter={(v) => LABELS[v] ?? v} wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
          {Object.entries(COLORS).map(([key, color]) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              stroke={color}
              strokeWidth={2}
              fill={`url(#grad-${key})`}
              dot={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const styles = {
  card: { background: "#1e2330", borderRadius: 12, padding: "24px 28px", marginBottom: 24 },
  title: { fontSize: 16, fontWeight: 600, color: "#e2e8f0", marginBottom: 20 },
};
