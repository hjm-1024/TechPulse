import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchDomains } from "../api/client";
import type { Domain, Keyword } from "../types";

interface Props {
  selectedKeywordId: number | null;
  onSelect: (kw: Keyword, domain: Domain) => void;
}

export default function Sidebar({ selectedKeywordId, onSelect }: Props) {
  const { data: domains = [], isLoading } = useQuery({
    queryKey: ["domains"],
    queryFn: fetchDomains,
  });

  const [expandedDomains, setExpandedDomains] = useState<Set<number>>(new Set([1]));

  const toggleDomain = (id: number) => {
    setExpandedDomains((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <aside className="w-64 min-h-screen bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="px-5 py-4 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white tracking-tight">
          Tech<span className="text-indigo-400">Pulse</span>
        </h1>
        <p className="text-xs text-gray-500 mt-0.5">기술 동향 분석 플랫폼</p>
      </div>

      <nav className="flex-1 overflow-y-auto py-3">
        {isLoading && (
          <div className="px-5 py-3 text-sm text-gray-500 animate-pulse">로딩 중…</div>
        )}
        {domains.map((domain) => {
          const isOpen = expandedDomains.has(domain.id);
          return (
            <div key={domain.id} className="mb-1">
              <button
                onClick={() => toggleDomain(domain.id)}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-gray-300 hover:bg-gray-800 transition-colors"
              >
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: domain.color }}
                />
                <span className="flex-1 text-left">{domain.name}</span>
                <svg
                  className={`w-3.5 h-3.5 text-gray-500 transition-transform ${isOpen ? "rotate-90" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>

              {isOpen && (
                <ul className="ml-6 border-l border-gray-800 pl-3 py-1 space-y-0.5">
                  {domain.keywords.map((kw) => {
                    const isSelected = selectedKeywordId === kw.id;
                    return (
                      <li key={kw.id}>
                        <button
                          onClick={() => onSelect(kw, domain)}
                          className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                            isSelected
                              ? "bg-indigo-600/20 text-indigo-300 font-medium"
                              : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                          }`}
                        >
                          <span className="block">{kw.name}</span>
                          <span className="block text-xs text-gray-600 mt-0.5">
                            논문 {kw.paper_count} · 특허 {kw.patent_count}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
