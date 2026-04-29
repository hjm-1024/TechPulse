import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { DOMAIN_META, domainColor } from "../constants/domains";

const DEFAULT_COLOR = "#60a5fa";

function nodeColor(d) {
  return domainColor(d.domain_tag);
}

function nodeRadius(d) {
  if (d.citation_count != null) return Math.max(5, Math.min(18, 5 + Math.sqrt(d.citation_count || 0)));
  return 7;
}

function nodeLabel(d) {
  return d.title?.slice(0, 40) + (d.title?.length > 40 ? "…" : "") ?? "";
}

export default function NetworkGraph({ type = "papers", domain = "" }) {
  const svgRef     = useRef(null);
  const [data, setData]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState(null);
  const [threshold, setThreshold] = useState(0.82);
  const [limit, setLimit] = useState(80);
  const [tooltip, setTooltip] = useState(null);

  async function load() {
    setLoading(true);
    setData(null);
    setError(null);
    try {
      const params = new URLSearchParams({ type, domain, limit, threshold });
      const resp = await fetch(`/api/insights/network?${params}`);
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        setError(err.detail || `서버 오류 (${resp.status})`);
        return;
      }
      const json = await resp.json();
      if (json.nodes.length === 0) {
        setError("논문 데이터가 없어요. Papers 수집 먼저 실행하세요.");
        return;
      }
      setData(json);
    } catch (e) {
      setError(`네트워크 오류: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!data || !svgRef.current) return;
    const { nodes, edges } = data;
    if (!nodes.length) return;

    const el   = svgRef.current;
    const W    = el.clientWidth || 900;
    const H    = 560;

    d3.select(el).selectAll("*").remove();

    const svg = d3.select(el)
      .attr("viewBox", `0 0 ${W} ${H}`)
      .style("background", "#0f1117");

    // Arrow marker
    svg.append("defs").append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 18).attr("refY", 0)
      .attr("markerWidth", 4).attr("markerHeight", 4)
      .attr("orient", "auto")
      .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#334155");

    // Build D3 link/node data
    const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));
    const links   = edges
      .filter(e => nodeMap[e.source] && nodeMap[e.target])
      .map(e => ({ ...e }));

    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(d => (1 - d.weight) * 160 + 40))
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(W / 2, H / 2))
      .force("collision", d3.forceCollide(d => nodeRadius(d) + 4));

    // Edges
    const link = svg.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#1e3a5f")
      .attr("stroke-opacity", d => 0.3 + d.weight * 0.5)
      .attr("stroke-width", d => (d.weight - 0.8) * 8);

    // Nodes
    const node = svg.append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", nodeRadius)
      .attr("fill", nodeColor)
      .attr("fill-opacity", 0.85)
      .attr("stroke", "#0f1117")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer")
      .on("mouseover", (event, d) => {
        setTooltip({
          x: event.offsetX, y: event.offsetY,
          title: d.title,
          meta: type === "papers"
            ? `${d.source?.replace(/_/g, " ")} · ${d.citation_count ?? 0} citations · ${(d.published_date || "").slice(0, 7)}`
            : `${d.patent_number ?? ""} · ${clean(d.assignee)} · ${(d.publication_date || "").slice(0, 7)}`,
          color: nodeColor(d),
        });
      })
      .on("mouseleave", () => setTooltip(null))
      .call(
        d3.drag()
          .on("start", (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
          .on("drag",  (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on("end",   (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      );

    sim.on("tick", () => {
      link
        .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      node
        .attr("cx", d => Math.max(nodeRadius(d), Math.min(W - nodeRadius(d), d.x)))
        .attr("cy", d => Math.max(nodeRadius(d), Math.min(H - nodeRadius(d), d.y)));
    });

    return () => sim.stop();
  }, [data]);

  function clean(s) { return (s || "").replace(/\s*\[[A-Z]{2}\]/g, "").slice(0, 30); }

  return (
    <div style={s.wrap}>
      <div style={s.controls}>
        <span style={s.label}>노드 수</span>
        <select value={limit} onChange={e => setLimit(+e.target.value)} style={s.sel}>
          {[40, 60, 80, 100, 150].map(v => <option key={v} value={v}>{v}</option>)}
        </select>

        <span style={s.label}>유사도 임계값</span>
        <select value={threshold} onChange={e => setThreshold(+e.target.value)} style={s.sel}>
          {[0.78, 0.80, 0.82, 0.84, 0.86, 0.88].map(v => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>

        <button onClick={load} style={s.btn} disabled={loading}>
          {loading ? "임베딩 계산 중…" : "그래프 생성"}
        </button>

        {data && (
          <span style={s.stat}>
            노드 {data.nodes.length}개 · 엣지 {data.edges.length}개
            {data.embedded > 0 && (
              <span style={{ color: "#22c55e", marginLeft: 6 }}>
                ({data.embedded}개 임베딩 신규 생성 · 다음부터 빠름)
              </span>
            )}
          </span>
        )}
      </div>

      <div style={{ position: "relative" }}>
        <svg ref={svgRef} style={{ ...s.svg, display: data ? "block" : "none" }} />
        {!data && !loading && !error && (
          <div style={s.placeholder}>
            <div>
              <p style={{ margin: "0 0 8px" }}>"그래프 생성" 버튼을 눌러 유사도 네트워크를 시각화하세요</p>
              <p style={{ margin: 0, fontSize: 12, color: "#475569" }}>
                첫 실행 시 Ollama(nomic-embed-text)로 임베딩을 계산합니다 — 노드 수만큼 시간이 걸려요
              </p>
            </div>
          </div>
        )}
        {loading && (
          <div style={s.placeholder}>
            <div style={{ textAlign: "center" }}>
              <p style={{ margin: "0 0 8px", color: "#60a5fa" }}>임베딩 계산 중…</p>
              <p style={{ margin: 0, fontSize: 12, color: "#475569" }}>
                Ollama로 {limit}개 논문의 벡터를 생성하고 있어요. 잠시 기다려주세요.
              </p>
            </div>
          </div>
        )}
        {error && (
          <div style={s.placeholder}>
            <div style={{ textAlign: "center", maxWidth: 420 }}>
              <p style={{ margin: "0 0 8px", color: "#ef4444" }}>오류</p>
              <p style={{ margin: 0, fontSize: 13, color: "#94a3b8", lineHeight: 1.6 }}>{error}</p>
            </div>
          </div>
        )}
        {tooltip && (
          <div style={{ ...s.tooltip, left: tooltip.x + 12, top: tooltip.y - 8 }}>
            <div style={{ ...s.tooltipDot, background: tooltip.color }} />
            <div>
              <p style={s.tooltipTitle}>{tooltip.title}</p>
              <p style={s.tooltipMeta}>{tooltip.meta}</p>
            </div>
          </div>
        )}
      </div>

      <div style={s.legend}>
        {Object.entries(DOMAIN_META).map(([tag, m]) => (
          <span key={tag} style={s.legendItem}>
            <span style={{ ...s.legendDot, background: m.color }} />
            {m.label_ko}
          </span>
        ))}
        <span style={{ ...s.legendItem, color: "#475569", marginLeft: 16 }}>
          원 크기 = 인용수 · 선 굵기 = 유사도
        </span>
      </div>
    </div>
  );
}

const s = {
  wrap: { background: "#131720", borderRadius: 12, padding: 20, marginBottom: 24 },
  controls: { display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" },
  label: { fontSize: 12, color: "#64748b" },
  sel: {
    background: "#1e2330", border: "1px solid #2d3748", borderRadius: 6,
    color: "#cbd5e1", padding: "5px 10px", fontSize: 12, cursor: "pointer",
  },
  btn: {
    padding: "6px 16px", background: "#3b82f6", border: "none", borderRadius: 6,
    color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 500,
  },
  stat: { fontSize: 12, color: "#64748b", marginLeft: 8 },
  svg: { width: "100%", height: 560, borderRadius: 8, display: "block" },
  placeholder: {
    position: "absolute", inset: 0, display: "flex", alignItems: "center",
    justifyContent: "center", color: "#334155", fontSize: 14,
  },
  tooltip: {
    position: "absolute", background: "#1e2330", border: "1px solid #2d3748",
    borderRadius: 8, padding: "8px 12px", pointerEvents: "none",
    maxWidth: 300, zIndex: 10, display: "flex", gap: 8, alignItems: "flex-start",
  },
  tooltipDot: { width: 8, height: 8, borderRadius: "50%", marginTop: 4, flexShrink: 0 },
  tooltipTitle: { fontSize: 13, color: "#f1f5f9", margin: 0, lineHeight: 1.4 },
  tooltipMeta:  { fontSize: 11, color: "#64748b", margin: "3px 0 0" },
  legend: { display: "flex", gap: 16, alignItems: "center", marginTop: 12, flexWrap: "wrap" },
  legendItem: { display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "#94a3b8" },
  legendDot: { width: 8, height: 8, borderRadius: "50%" },
};
