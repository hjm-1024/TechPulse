import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import Sidebar from "./components/Sidebar";
import PapersView from "./components/PapersView";
import PatentsView from "./components/PatentsView";
import AnalysisView from "./components/AnalysisView";
import type { Domain, Keyword, TabType } from "./types";

export default function App() {
  const qc = useQueryClient();
  const [selectedKeyword, setSelectedKeyword] = useState<Keyword | null>(null);
  const [selectedDomain, setSelectedDomain] = useState<Domain | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("papers");

  const handleSelect = (kw: Keyword, domain: Domain) => {
    setSelectedKeyword(kw);
    setSelectedDomain(domain);
    setActiveTab("papers");
  };

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: "papers", label: "논문", icon: "📄" },
    { id: "patents", label: "특허", icon: "🔬" },
    { id: "analysis", label: "연구 동향 분석", icon: "📊" },
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar selectedKeywordId={selectedKeyword?.id ?? null} onSelect={handleSelect} />

      <main className="flex-1 overflow-y-auto">
        {!selectedKeyword ? (
          <div className="flex flex-col items-center justify-center h-full min-h-screen text-gray-500">
            <svg className="w-20 h-20 mb-4 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <p className="text-base">왼쪽 사이드바에서 키워드를 선택하세요</p>
            <p className="text-sm mt-1">논문 · 특허 · 연구 동향 분석을 한 곳에서</p>
          </div>
        ) : (
          <div className="max-w-5xl mx-auto px-6 py-6">
            {/* Header */}
            <div className="mb-6">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: selectedDomain?.color }}
                />
                {selectedDomain?.name}
              </div>
              <h2 className="text-2xl font-bold text-white">
                {selectedKeyword.name}
                <span className="ml-2 text-base font-normal text-gray-400">
                  {selectedKeyword.name_en}
                </span>
              </h2>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-700 mb-6 gap-1">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                      isActive
                        ? "border-indigo-500 text-indigo-300"
                        : "border-transparent text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    <span className="mr-1.5">{tab.icon}</span>
                    {tab.label}
                    {tab.id === "analysis" && isActive && (
                      <span className="ml-2 text-xs px-1.5 py-0.5 bg-indigo-500/20 text-indigo-400 rounded-full">
                        AI 분석
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Tab content */}
            {activeTab === "papers" && <PapersView keyword={selectedKeyword} />}
            {activeTab === "patents" && <PatentsView keyword={selectedKeyword} />}
            {activeTab === "analysis" && <AnalysisView keyword={selectedKeyword} />}
          </div>
        )}
      </main>
    </div>
  );
}
