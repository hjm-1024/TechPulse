import { useState } from "react";

const DOMAIN_COLOR  = { physical_ai_robotics: "#10b981", telecom_6g: "#f59e0b" };
const DOMAIN_LABEL  = { physical_ai_robotics: "Robotics", telecom_6g: "6G" };
const SOURCE_COLOR  = {
  arxiv: "#f97316", semantic_scholar: "#8b5cf6", openalex: "#06b6d4",
  epo: "#ef4444", kipris: "#3b82f6",
};

const COUNTRY_NAME = {
  US: "미국", KR: "한국", CN: "중국", JP: "일본", EP: "유럽(EP)",
  WO: "국제(PCT)", DE: "독일", FR: "프랑스", GB: "영국", TW: "대만",
};

// Kind codes: what type of document is this?
const KIND_LABEL = {
  A: "출원공개", A1: "출원공개", A2: "출원공개(2차)", A3: "조사보고서",
  B: "등록특허", B1: "등록특허", B2: "재심사후 등록",
  C: "수정본", U: "실용신안",
};

function extractKind(patentNumber) {
  const m = patentNumber?.match(/([A-Z]\d?)$/);
  return m ? m[1] : null;
}

function ipcLink(code) {
  const clean = code.trim().replace(/\s+/g, "");
  return `https://www.ipcpub.wipo.int/?section=${clean[0]}&class=${clean.slice(1,3)}&subclass=${clean[3]}&version=20240101&symbol=${encodeURIComponent(clean)}`;
}

function espacenetUrl(num) {
  return `https://worldwide.espacenet.com/patent/search?q=pn%3D${encodeURIComponent(num)}`;
}

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
  const kind        = extractKind(patent.patent_number);
  const kindLabel   = kind ? KIND_LABEL[kind] : null;
  const countryName = COUNTRY_NAME[patent.country] ?? patent.country;

  return (
    <div style={s.card}>
      {/* Top row: badges + links */}
      <div style={s.cardTop}>
        <div style={s.badges}>
          <Badge color={srcColor}>{patent.source?.toUpperCase()}</Badge>
          <Badge color={domainColor}>{DOMAIN_LABEL[patent.domain_tag] ?? patent.domain_tag}</Badge>
          {countryName && <Badge color="#64748b">{countryName}</Badge>}
          {kindLabel && (
            <Badge color={kind?.startsWith("B") ? "#10b981" : "#94a3b8"}>
              {kind} · {kindLabel}
            </Badge>
          )}
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <a href={espacenetUrl(patent.patent_number)} target="_blank" rel="noreferrer" style={s.extLink}>
            Espacenet ↗
          </a>
          <a href={`https://patents.google.com/patent/${patent.patent_number}`} target="_blank" rel="noreferrer" style={s.extLink}>
            Google Patents ↗
          </a>
        </div>
      </div>

      {/* Title */}
      <h3 style={s.title}>{patent.title}</h3>

      {/* Primary info grid */}
      <div style={s.infoGrid}>
        <InfoBlock label="특허번호 (Patent No.)" value={patent.patent_number} mono />
        {patent.assignee
          ? <InfoBlock label="출원인 / 권리자 (Applicant)" value={patent.assignee} />
          : <InfoBlock label="출원인 / 권리자 (Applicant)" value="—" muted />}
        {patent.inventors
          ? <InfoBlock label="발명자 (Inventors)" value={truncateAuthors(patent.inventors)} />
          : <InfoBlock label="발명자 (Inventors)" value="—" muted />}
      </div>

      {/* Dates row */}
      <div style={s.datesRow}>
        {patent.filing_date && (
          <DateBlock label="출원일 (Filing Date)" value={patent.filing_date.slice(0, 10)}
            note="특허 신청한 날짜 — 권리 시작점" />
        )}
        {patent.publication_date && (
          <DateBlock label="공개일 (Publication Date)" value={patent.publication_date.slice(0, 10)}
            note="공중에 공개된 날짜" />
        )}
      </div>

      {/* IPC classification */}
      {patent.ipc_codes && (
        <div style={s.ipcBlock}>
          <span style={s.ipcLabel}>IPC 기술분류</span>
          <div style={s.ipcTags}>
            {patent.ipc_codes.split(",").map(code => code.trim()).filter(Boolean).map(code => (
              <a key={code} href={ipcLink(code)} target="_blank" rel="noreferrer" style={s.ipcTag}>
                {code}
              </a>
            ))}
          </div>
          <span style={s.ipcHint}>클릭하면 WIPO IPC 분류 설명 확인</span>
        </div>
      )}

      {/* Abstract */}
      {patent.abstract && (
        <>
          <div style={s.abstractLabel}>초록 (Abstract)</div>
          <p style={{ ...s.abstract, WebkitLineClamp: open ? "unset" : 4 }}>
            {patent.abstract}
          </p>
          {patent.abstract.length > 250 && (
            <button onClick={() => setOpen(!open)} style={s.toggle}>
              {open ? "접기 ▲" : "더 보기 ▼"}
            </button>
          )}
        </>
      )}
    </div>
  );
}

function InfoBlock({ label, value, mono = false, muted = false }) {
  return (
    <div style={s.infoBlock}>
      <span style={s.infoLabel}>{label}</span>
      <span style={{
        ...s.infoValue,
        ...(mono ? { fontFamily: "monospace", fontSize: 12 } : {}),
        ...(muted ? { color: "#475569" } : {}),
      }}>
        {value}
      </span>
    </div>
  );
}

function DateBlock({ label, value, note }) {
  return (
    <div style={s.dateBlock}>
      <span style={s.infoLabel}>{label}</span>
      <span style={s.dateValue}>{value}</span>
      {note && <span style={s.dateNote}>{note}</span>}
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
  extLink: { fontSize: 11, color: "#60a5fa", textDecoration: "none", flexShrink: 0 },
  infoGrid: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px 20px", margin: "12px 0" },
  infoBlock: { display: "flex", flexDirection: "column", gap: 3 },
  infoLabel: { fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 },
  infoValue: { fontSize: 13, color: "#e2e8f0" },
  datesRow: { display: "flex", gap: 24, marginBottom: 12, flexWrap: "wrap" },
  dateBlock: { display: "flex", flexDirection: "column", gap: 2 },
  dateValue: { fontSize: 14, color: "#f1f5f9", fontWeight: 600, fontFamily: "monospace" },
  dateNote:  { fontSize: 10, color: "#475569", fontStyle: "italic", marginTop: 1 },
  ipcBlock:  { marginBottom: 12 },
  ipcLabel:  { fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, display: "block", marginBottom: 6 },
  ipcTags:   { display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 },
  ipcTag: {
    background: "#0f172a", border: "1px solid #334155", borderRadius: 4,
    color: "#93c5fd", padding: "2px 8px", fontSize: 11, fontFamily: "monospace",
    textDecoration: "none", cursor: "pointer",
  },
  ipcHint: { fontSize: 10, color: "#334155", fontStyle: "italic" },
  abstractLabel: { fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 },
  abstract: {
    fontSize: 13, color: "#94a3b8", lineHeight: 1.6, marginTop: 0,
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
