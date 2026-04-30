import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPapers, collectPapers } from "../api/client";
import type { Keyword } from "../types";

interface Props {
  keyword: Keyword;
}

export default function PapersView({ keyword }: Props) {
  const qc = useQueryClient();
  const { data: papers = [], isLoading } = useQuery({
    queryKey: ["papers", keyword.id],
    queryFn: () => fetchPapers(keyword.id),
  });

  const collect = useMutation({
    mutationFn: () => collectPapers(keyword.id),
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ["papers", keyword.id] }), 3000);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-400">
          총 <strong className="text-white">{papers.length}</strong>건
        </span>
        <button
          onClick={() => collect.mutate()}
          disabled={collect.isPending}
          className="px-4 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg transition-colors"
        >
          {collect.isPending ? "수집 중…" : "논문 수집"}
        </button>
      </div>

      {collect.isSuccess && (
        <div className="mb-4 px-4 py-2 text-sm bg-green-900/40 border border-green-700 rounded-lg text-green-300">
          수집을 시작했습니다. 잠시 후 목록이 업데이트됩니다.
        </div>
      )}

      {papers.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-gray-500">
          <svg className="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-sm">논문 데이터가 없습니다.</p>
          <p className="text-xs mt-1">위 버튼으로 수집을 시작하세요.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {papers.map((paper) => (
            <div key={paper.id} className="bg-gray-800/60 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <a
                    href={paper.url ?? "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-indigo-300 hover:text-indigo-200 leading-snug line-clamp-2"
                  >
                    {paper.title}
                  </a>
                  {paper.authors && (
                    <p className="text-xs text-gray-500 mt-1 truncate">{paper.authors}</p>
                  )}
                  {paper.abstract && (
                    <p className="text-xs text-gray-500 mt-2 line-clamp-2 leading-relaxed">
                      {paper.abstract}
                    </p>
                  )}
                </div>
                <div className="flex-shrink-0 text-right">
                  {paper.year && (
                    <span className="block text-xs text-gray-500">{paper.year}</span>
                  )}
                  <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 bg-yellow-500/10 border border-yellow-500/30 rounded-full text-xs text-yellow-400">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    {paper.citation_count.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
