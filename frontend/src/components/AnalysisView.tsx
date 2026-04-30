import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
} from "recharts";
import { fetchAnalysis } from "../api/client";
import type { Keyword } from "../types";

interface Props {
  keyword: Keyword;
}

const LINE_COLORS = ["#818cf8", "#34d399", "#fb923c", "#f472b6", "#facc15"];

export default function AnalysisView({ keyword }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["analysis", keyword.id],
    queryFn: () => fetchAnalysis(keyword.id),
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <div className="animate-spin w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full" />
        <p className="text-sm text-gray-400">논문 초록/제목 분석 중…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-48">
        <p className="text-sm text-red-400">분석 데이터를 불러오지 못했습니다.</p>
      </div>
    );
  }

  if (!data || data.total_papers === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500">
        <svg className="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p className="text-sm">분석할 논문 데이터가 없습니다.</p>
        <p className="text-xs mt-1">논문 탭에서 먼저 데이터를 수집해주세요.</p>
      </div>
    );
  }

  const top20 = data.top_keywords.slice(0, 20).reverse();
  const hasYearTrend = data.yearly_trend.length > 1;

  return (
    <div className="space-y-8">
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="분석 논문 수" value={data.total_papers.toLocaleString()} unit="건" color="indigo" />
        <StatCard
          label="연도 범위"
          value={data.year_range[0] && data.year_range[1]
            ? `${data.year_range[0]} – ${data.year_range[1]}`
            : "–"}
          color="sky"
        />
        <StatCard label="평균 인용수" value={data.avg_citations.toLocaleString()} unit="회" color="amber" />
      </div>

      {/* Top keywords bar chart */}
      <section>
        <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
          <span className="w-1.5 h-4 bg-indigo-500 rounded" />
          주요 키워드 (TF-IDF 기반, 상위 20개)
          <span className="text-xs font-normal text-gray-500">— 제목 + 초록 분석</span>
        </h3>
        <div className="bg-gray-800/50 rounded-xl p-4">
          <ResponsiveContainer width="100%" height={380}>
            <BarChart data={top20} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fill: "#9ca3af", fontSize: 11 }}
                tickFormatter={(v) => v.toFixed(3)}
              />
              <YAxis
                type="category"
                dataKey="word"
                width={120}
                tick={{ fill: "#d1d5db", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 8 }}
                labelStyle={{ color: "#f3f4f6" }}
                formatter={(v: number) => [v.toFixed(5), "TF-IDF 점수"]}
              />
              <Bar dataKey="score" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Year-over-year trend */}
      {hasYearTrend && (
        <section>
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <span className="w-1.5 h-4 bg-emerald-500 rounded" />
            연도별 키워드 등장 빈도 (상위 5개 단어)
          </h3>
          <div className="bg-gray-800/50 rounded-xl p-4">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.yearly_trend} margin={{ left: 0, right: 16, top: 4, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="year" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 8 }}
                  labelStyle={{ color: "#f3f4f6", fontWeight: 600 }}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: "#d1d5db" }} />
                {data.top5_words.map((word, i) => (
                  <Line
                    key={word}
                    type="monotone"
                    dataKey={word}
                    stroke={LINE_COLORS[i % LINE_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: string;
  unit?: string;
  color: "indigo" | "sky" | "amber";
}) {
  const borderColor = { indigo: "border-indigo-500/30", sky: "border-sky-500/30", amber: "border-amber-500/30" }[color];
  const textColor = { indigo: "text-indigo-300", sky: "text-sky-300", amber: "text-amber-300" }[color];
  return (
    <div className={`bg-gray-800/50 border ${borderColor} rounded-xl px-4 py-3`}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-xl font-bold ${textColor}`}>
        {value}
        {unit && <span className="text-sm font-normal ml-1 text-gray-400">{unit}</span>}
      </p>
    </div>
  );
}
