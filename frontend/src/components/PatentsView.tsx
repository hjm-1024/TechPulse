import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPatents, collectPatents } from "../api/client";
import type { Keyword } from "../types";

interface Props {
  keyword: Keyword;
}

export default function PatentsView({ keyword }: Props) {
  const qc = useQueryClient();
  const { data: patents = [], isLoading } = useQuery({
    queryKey: ["patents", keyword.id],
    queryFn: () => fetchPatents(keyword.id),
  });

  const collect = useMutation({
    mutationFn: () => collectPatents(keyword.id),
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ["patents", keyword.id] }), 3000);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-400">
          총 <strong className="text-white">{patents.length}</strong>건
        </span>
        <button
          onClick={() => collect.mutate()}
          disabled={collect.isPending}
          className="px-4 py-1.5 text-sm bg-sky-600 hover:bg-sky-500 disabled:opacity-50 rounded-lg transition-colors"
        >
          {collect.isPending ? "수집 중…" : "특허 수집"}
        </button>
      </div>

      {collect.isSuccess && (
        <div className="mb-4 px-4 py-2 text-sm bg-green-900/40 border border-green-700 rounded-lg text-green-300">
          수집을 시작했습니다. 잠시 후 목록이 업데이트됩니다.
        </div>
      )}

      {patents.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-gray-500">
          <svg className="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p className="text-sm">특허 데이터가 없습니다.</p>
          <p className="text-xs mt-1">위 버튼으로 수집을 시작하세요.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {patents.map((patent) => (
            <div key={patent.id} className="bg-gray-800/60 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <a
                    href={patent.url ?? "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-sky-300 hover:text-sky-200 leading-snug line-clamp-2"
                  >
                    {patent.title}
                  </a>
                  {patent.assignee && (
                    <p className="text-xs text-gray-400 mt-1">{patent.assignee}</p>
                  )}
                  {patent.inventors && (
                    <p className="text-xs text-gray-500 mt-0.5 truncate">발명자: {patent.inventors}</p>
                  )}
                  {patent.abstract && (
                    <p className="text-xs text-gray-500 mt-2 line-clamp-2 leading-relaxed">
                      {patent.abstract}
                    </p>
                  )}
                </div>
                <div className="flex-shrink-0 text-right space-y-1">
                  {patent.year && (
                    <span className="block text-xs text-gray-500">{patent.year}</span>
                  )}
                  {patent.country && (
                    <span className="inline-block px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-300">
                      {patent.country}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
