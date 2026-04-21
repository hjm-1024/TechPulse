import { useState } from "react";

const DOMAIN_COLOR  = { physical_ai_robotics: "#10b981", telecom_6g: "#f59e0b" };
const DOMAIN_LABEL  = { physical_ai_robotics: "Robotics", telecom_6g: "6G" };
const SOURCE_COLOR  = {
  arxiv: "#f97316", semantic_scholar: "#8b5cf6", openalex: "#06b6d4",
  epo: "#ef4444", kipris: "#3b82f6",
};

export default function SearchResults({ results, loading, error, type, page, setPage }) {
  if (error) return <Notice text={`Error: ${error}`} />;
  if (loading && !results) return <LoadingSkeleton />;

  if (!results) return null;
  if (results.items.length === 0) return <Notice text="No results found." />;

  return (
    <div>
      <div style={{ opacity: loading ? 0.5 : 1, transition: "opacity 0.2s" }}>
        {results.items.map((item, i) =>
          type === "papers"
            ? <PaperCard key={item.id ?? i} paper={item} />
            : <PatentCard key={item.patent_number ?? i} patent={item} />
        )}
      </div>
      <Pagination page={page} total={results.pages} onPage={setPage} />
    </div>
  );
}

function PaperCard({ paper }) {
  const [open, setOpen] = useState(false);
  const domainColor = DOMAIN_COLOR[paper.domain_tag] ?? "#64748b";
  const srcColor    = SOURCE_COLOR[paper.source] ?? "#94a3b8";

  return (
    <div style={s.card}>
      <div style={s.cardTop}>
        <div style={s.badges}>
          <Badge color={srcColor}>{paper.source?.replace(/_/g, " ")}</Badge>
          <Badge color={domainColor}>{DOMAIN_LABEL[paper.domain_tag] ?? paper.domain_tag}</Badge>
          {paper.citation_count > 0 && (
            <span style={s.citations}>↑ {paper.citation_count.toLocaleString()}</span>
          )}
        </div>
        <span style={s.year}>{(paper.published_date || "").slice(0, 4)}</span>
      </div>

      <h3 style={s.title}>
        {paper.doi
          ? <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer" style={s.link}>
              {paper.title}
            </a>
          : paper.title
        }
      </h3>

      <p style={s.authors}>
        {truncateAuthors(paper.authors)}
      </p>

      {paper.journal && paper.journal !== "arXiv" && (
        <p style={s.journal}>{paper.journal}</p>
      )}

      {paper.abstract && (
        <>
          <p style={{ ...s.abstract, WebkitLineClamp: open ? "unset" : 3 }}>
            {paper.abstract}
          </p>
          {paper.abstract.length > 200 && (
            <button onClick={() => setOpen(!open)} style={s.toggle}>
              {open ? "Show less ▲" : "Show more ▼"}
            </button>
          )}
        </>
      )}
    </div>
  );
}

function PatentCard({ patent }) {
  const [open, setOpen] = useState(false);
  const domainColor = DOMAIN_COLOR[patent.domain_tag] ?? "#64748b";
  const srcColor    = SOURCE_COLOR[patent.source] ?? "#94a3b8";

  return (
    <div style={s.card}>
      <div style={s.cardTop}>
        <div style={s.badges}>
          <Badge color={srcColor}>{patent.source?.toUpperCase()}</Badge>
          <Badge color={domainColor}>{DOMAIN_LABEL[patent.domain_tag] ?? patent.domain_tag}</Badge>
          {patent.country && <Badge color="#64748b">{patent.country}</Badge>}
        </div>
        <span style={s.year}>{(patent.publication_date || "").slice(0, 4)}</span>
      </div>

      <h3 style={s.title}>{patent.title}</h3>

      <div style={s.metaRow}>
        <MetaItem label="Patent" value={patent.patent_number} mono />
        {patent.assignee && <MetaItem label="Assignee" value={truncate(patent.assignee, 60)} />}
        {patent.inventors && <MetaItem label="Inventors" value={truncateAuthors(patent.inventors)} />}
        {patent.ipc_codes && <MetaItem label="IPC" value={patent.ipc_codes} mono />}
        {patent.filing_date && <MetaItem label="Filed" value={patent.filing_date.slice(0, 10)} />}
      </div>

      {patent.abstract && (
        <>
          <p style={{ ...s.abstract, WebkitLineClamp: open ? "unset" : 3 }}>
            {patent.abstract}
          </p>
          {patent.abstract.length > 200 && (
            <button onClick={() => setOpen(!open)} style={s.toggle}>
              {open ? "Show less ▲" : "Show more ▼"}
            </button>
          )}
        </>
      )}
    </div>
  );
}

function Pagination({ page, total, onPage }) {
  if (!total || total <= 1) return null;
  const pages = Math.min(total, 999);

  return (
    <div style={s.pagination}>
      <button
        onClick={() => onPage(page - 1)}
        disabled={page <= 1}
        style={{ ...s.pageBtn, opacity: page <= 1 ? 0.3 : 1 }}
      >← Prev</button>

      <div style={s.pageNums}>
        {pageRange(page, pages).map((p, i) =>
          p === "…"
            ? <span key={`e${i}`} style={s.ellipsis}>…</span>
            : <button
                key={p}
                onClick={() => onPage(p)}
                style={{ ...s.pageBtn, ...(p === page ? s.pageBtnActive : {}) }}
              >{p}</button>
        )}
      </div>

      <button
        onClick={() => onPage(page + 1)}
        disabled={page >= pages}
        style={{ ...s.pageBtn, opacity: page >= pages ? 0.3 : 1 }}
      >Next →</button>
    </div>
  );
}

function pageRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, "…", total];
  if (current >= total - 3) return [1, "…", total-4, total-3, total-2, total-1, total];
  return [1, "…", current-1, current, current+1, "…", total];
}

function Badge({ color, children }) {
  return (
    <span style={{ ...s.badge, background: color + "22", color }}>
      {children}
    </span>
  );
}

function MetaItem({ label, value, mono = false }) {
  if (!value) return null;
  return (
    <span style={s.metaItem}>
      <span style={s.metaLabel}>{label}</span>
      <span style={mono ? { ...s.metaValue, fontFamily: "monospace", fontSize: 11 } : s.metaValue}>
        {value}
      </span>
    </span>
  );
}

function Notice({ text }) {
  return <div style={s.notice}>{text}</div>;
}

function LoadingSkeleton() {
  return (
    <div>
      {[1,2,3,4,5].map(i => (
        <div key={i} style={{ ...s.card, height: 120, opacity: 0.3 }} />
      ))}
    </div>
  );
}

function truncate(str, n) {
  return str && str.length > n ? str.slice(0, n) + "…" : str;
}

function truncateAuthors(authors) {
  if (!authors) return "";
  const parts = authors.split(", ");
  if (parts.length <= 3) return authors;
  return parts.slice(0, 3).join(", ") + ` +${parts.length - 3} more`;
}

const s = {
  card: {
    background: "#1e2330", borderRadius: 12, padding: "20px 24px",
    marginBottom: 12, borderLeft: "3px solid transparent",
    transition: "border-color 0.15s",
  },
  cardTop: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  badges: { display: "flex", gap: 6, flexWrap: "wrap" },
  badge: { display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 500 },
  citations: { fontSize: 12, color: "#f59e0b", fontWeight: 600, marginLeft: 4 },
  year: { fontSize: 12, color: "#64748b", flexShrink: 0 },
  title: { fontSize: 15, fontWeight: 600, color: "#f1f5f9", lineHeight: 1.5, marginBottom: 6 },
  link: { color: "#60a5fa", textDecoration: "none" },
  authors: { fontSize: 12, color: "#94a3b8", marginBottom: 4 },
  journal: { fontSize: 11, color: "#64748b", fontStyle: "italic", marginBottom: 6 },
  metaRow: { display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 10 },
  metaItem: { display: "flex", flexDirection: "column", gap: 2 },
  metaLabel: { fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 },
  metaValue: { fontSize: 12, color: "#cbd5e1" },
  abstract: {
    fontSize: 13, color: "#94a3b8", lineHeight: 1.6, marginTop: 10,
    display: "-webkit-box", WebkitBoxOrient: "vertical", overflow: "hidden",
  },
  toggle: {
    background: "none", border: "none", color: "#60a5fa",
    cursor: "pointer", fontSize: 12, padding: "4px 0", marginTop: 4,
  },
  pagination: { display: "flex", justifyContent: "center", alignItems: "center", gap: 6, padding: "24px 0" },
  pageNums: { display: "flex", gap: 4 },
  pageBtn: {
    background: "#1e2330", border: "1px solid #2d3748", borderRadius: 6,
    color: "#94a3b8", cursor: "pointer", padding: "6px 12px", fontSize: 13,
    transition: "all 0.15s",
  },
  pageBtnActive: { background: "#3b82f6", borderColor: "#3b82f6", color: "#fff" },
  ellipsis: { color: "#64748b", padding: "6px 4px", fontSize: 13 },
  notice: { color: "#64748b", textAlign: "center", padding: "60px 0", fontSize: 14 },
};
