import { useState, useEffect, useCallback, useRef } from "react";

function useDebounce(value, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export function useSearch() {
  const [type, setType]         = useState("papers");   // "papers" | "patents"
  const [mode, setMode]         = useState("keyword");  // "keyword" | "semantic"
  const [query, setQuery]       = useState("");
  const [domain, setDomain]     = useState("");
  const [source, setSource]     = useState("");
  const [sortBy, setSortBy]     = useState("citation_count");
  const [page, setPage]         = useState(1);

  const [results, setResults]   = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);

  const debouncedQuery = useDebounce(query, mode === "semantic" ? 600 : 350);
  const abortRef = useRef(null);

  const fetch = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setError(null);

    let endpoint;
    if (mode === "semantic") {
      const params = new URLSearchParams({ type, limit: 20 });
      if (debouncedQuery) params.set("q", debouncedQuery);
      if (domain)         params.set("domain", domain);
      if (source)         params.set("source", source);
      endpoint = `/api/search/semantic?${params}`;
    } else {
      const params = new URLSearchParams({ page, page_size: 20 });
      if (debouncedQuery) params.set("q", debouncedQuery);
      if (domain)         params.set("domain", domain);
      if (source)         params.set("source", source);
      endpoint = type === "papers"
        ? `/api/papers?${params}&sort_by=${sortBy}`
        : `/api/patents/list?${params}`;
    }

    try {
      const resp = await window.fetch(endpoint, { signal: abortRef.current.signal });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      setResults(data);
    } catch (e) {
      if (e.name !== "AbortError") setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [type, mode, debouncedQuery, domain, source, sortBy, page]);

  // Reset page when filters change
  useEffect(() => { setPage(1); }, [type, mode, debouncedQuery, domain, source, sortBy]);

  useEffect(() => { fetch(); }, [fetch]);

  return {
    type, setType,
    mode, setMode,
    query, setQuery,
    domain, setDomain,
    source, setSource,
    sortBy, setSortBy,
    page, setPage,
    results, loading, error,
  };
}
