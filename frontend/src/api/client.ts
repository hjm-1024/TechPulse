import axios from "axios";
import type { Domain, Paper, Patent, AnalysisResult } from "../types";

const api = axios.create({ baseURL: "/api" });

export const fetchDomains = async (): Promise<Domain[]> => {
  const { data } = await api.get("/domains/");
  return data;
};

export const fetchPapers = async (keywordId: number): Promise<Paper[]> => {
  const { data } = await api.get(`/papers/${keywordId}`);
  return data;
};

export const collectPapers = async (keywordId: number) => {
  const { data } = await api.post(`/papers/${keywordId}/collect`);
  return data;
};

export const fetchPatents = async (keywordId: number): Promise<Patent[]> => {
  const { data } = await api.get(`/patents/${keywordId}`);
  return data;
};

export const collectPatents = async (keywordId: number) => {
  const { data } = await api.post(`/patents/${keywordId}/collect`);
  return data;
};

export const fetchAnalysis = async (keywordId: number): Promise<AnalysisResult> => {
  const { data } = await api.get(`/analysis/${keywordId}`);
  return data;
};
