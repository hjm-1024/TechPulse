import { useState } from "react";

import { domainColor, domainLabel } from "../constants/domains";
const SOURCE_COLOR = {
  arxiv: "#f97316", semantic_scholar: "#8b5cf6", openalex: "#06b6d4",
  epo: "#ef4444", kipris: "#3b82f6",
};

/**
 * Shows similar documents (same type) or cross-type links (paper↔patent).
 *
 * Props:
 *   id        — document id
 *   type      — "papers" | "patents"
 *   crossType — if set, links to other type ("patents" | "papers")
 *   limit     — max results
 */
export default function SimilarDocs({ id, type, crossType = null, limit = 5 }) {
  const [items, setItems] = useState(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const targetType = crossType ?? type;

  async function toggle() {
    if (open) { setOpen(false); return; }
    setOpen(true);
    if (items !== null) return;

    setLoading(true);
    try {
      const url = crossType
        ? `/api/cross?from_type=${type}&from_id=${id}&to_type=${crossType}&limit=${limit}`
        : `/api/similar?type=${type}&id=${id}&limit=${limit}`;
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setItems(data.items ?? []);
    } catch (e) {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  const label = crossType
    ? (crossType === "patents" ? "관련 특허" : "관련 논문")
    : "비슷한 문서";

  return (
    <div style={s.wrap}>
      <button onClick={toggle} style={s.btn}>
        {loading
          ? `${label} 검색 중…`
          : open
            ? `▲ ${label} 닫기`
            : `▶ ${label} 찾기`}
      </button>

      {open && items !== null && (
        <div style={s.list}>
          {items.length === 0
            ? <span style={s.empty}>임베딩이 없거나 유사 문서가 없어요.</span>
            : items.map((doc, i) => (
                <SimilarItem key={i} doc={doc} type={targetType} />
              ))
          }
        </div>
      )}
    </div>
  );
}

function SimilarItem({ doc, type }) {
  const isPaper  = type === "papers";
  const title    = doc.title ?? "(제목 없음)";
  const year     = (isPaper ? doc.published_date : doc.publication_date)?.slice(0, 4) ?? "";
  const src      = doc.source ?? "";
  const srcColor = SOURCE_COLOR[src] ?? "#64748b";
  const domColor = domainColor(doc.domain_tag);
  const domLbl   = domainLabel(doc.domain_tag);
  const score    = doc.similarity != null ? `${Math.round(doc.similarity * 100)}%` : "";
  const href     = isPaper && doc.doi ? `https://doi.org/${doc.doi}` : null;

  return (
    <div style={s.item}>
      <div style={s.itemLeft}>
        <span style={s.score}>{score}</span>
        <div>
          <div style={s.badges}>
            <span style={{ ...s.badge, background: srcColor + "22", color: srcColor }}>
              {src.replace(/_/g, " ")}
            </span>
            {domLbl && (
              <span style={{ ...s.badge, background: domColor + "22", color: domColor }}>
                {domLbl}
              </span>
            )}
            {!isPaper && doc.country && (
              <span style={{ ...s.badge, background: "#33415533", color: "#94a3b8" }}>
                {doc.country}
              </span>
            )}
          </div>
          {href
            ? <a href={href} target="_blank" rel="noreferrer" style={s.titleLink}>{title}</a>
            : <span style={s.titlePlain}>{title}</span>
          }
          <div style={s.meta}>
            {isPaper
              ? `${src.replace(/_/g, " ")} · ${year}`
              : `${doc.patent_number ?? ""} · ${year}`
            }
          </div>
        </div>
      </div>
    </div>
  );
}

const s = {
  wrap: { marginTop: 12 },
  btn: {
    background: "none", border: "1px solid #1e3a5f", borderRadius: 6,
    color: "#60a5fa", cursor: "pointer", fontSize: 12, padding: "4px 12px",
    transition: "all 0.15s", marginRight: 8,
  },
  list: {
    marginTop: 8, borderLeft: "2px solid #1e3a5f",
    paddingLeft: 12, display: "flex", flexDirection: "column", gap: 10,
  },
  item: { display: "flex", alignItems: "flex-start" },
  itemLeft: { display: "flex", gap: 8, alignItems: "flex-start" },
  score: {
    fontSize: 11, color: "#3b82f6", fontWeight: 700,
    fontFamily: "monospace", minWidth: 36, paddingTop: 2,
  },
  badges: { display: "flex", gap: 4, marginBottom: 3 },
  badge: { fontSize: 10, padding: "1px 6px", borderRadius: 8, fontWeight: 500 },
  titleLink: { fontSize: 13, color: "#cbd5e1", lineHeight: 1.4, textDecoration: "none" },
  titlePlain: { fontSize: 13, color: "#cbd5e1", lineHeight: 1.4 },
  meta: { fontSize: 11, color: "#475569", marginTop: 2 },
  empty: { fontSize: 12, color: "#475569" },
};
