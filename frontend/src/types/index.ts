export interface Keyword {
  id: number;
  name: string;
  name_en: string;
  paper_count: number;
  patent_count: number;
}

export interface Domain {
  id: number;
  name: string;
  name_en: string;
  color: string;
  keywords: Keyword[];
}

export interface Paper {
  id: number;
  paper_id: string | null;
  title: string;
  abstract: string | null;
  year: number | null;
  citation_count: number;
  authors: string | null;
  url: string | null;
  doi: string | null;
}

export interface Patent {
  id: number;
  patent_id: string | null;
  title: string;
  abstract: string | null;
  year: number | null;
  assignee: string | null;
  inventors: string | null;
  country: string | null;
  url: string | null;
}

export interface TopKeyword {
  word: string;
  score: number;
}

export interface YearlyTrendPoint {
  year: number;
  [word: string]: number;
}

export interface AnalysisResult {
  keyword: string;
  keyword_en: string;
  message?: string;
  top_keywords: TopKeyword[];
  yearly_trend: YearlyTrendPoint[];
  top5_words: string[];
  total_papers: number;
  year_range: [number | null, number | null];
  avg_citations: number;
}

export type TabType = "papers" | "patents" | "analysis";
