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
  const [threshold, setThreshold] = useState(0.75);
  const [limit, setLimit] = useState(100);
  const [balanced, setBalanced] = useState(true);
  const [tooltip, setTooltip] = useState(null);

  async function load() {
    setLoading(true);
    setData(null);
    setError(null);
    try {
      const params = new URLSearchParams({ type, domain, limit, threshold, balanced });
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

    const el = svgRef.current;
    const W  = el.clientWidth || 900;
    const H  = 560;

    d3.select(el).selectAll("*").remove();

    const svg = d3.select(el)
      .attr("viewBox", `0 0 ${W} ${H}`)
      .style("background", "#0f1117");

    // Zoom + pan
    const g = svg.append("g");
    svg.call(
      d3.zoom()
        .scaleExtent([0.3, 4])
        .on("zoom", e => g.attr("transform", e.transform))
    );

    const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));
    const links   = edges
      .filter(e => nodeMap[e.source] && nodeMap[e.target])
      .map(e => ({ ...e }));

    // Degree map for hub highlighting
    const degree = {};
    links.forEach(e => {
      degree[e.source] = (degree[e.source] || 0) + 1;
      degree[e.target] = (degree[e.target] || 0) + 1;
    });

    // Unique domains → assign grid anchor positions for clustering
    const domainList = [...new Set(nodes.map(n => n.domain_tag))];
    const cols = Math.ceil(Math.sqrt(domainList.length));
    const domainAnchor = {};
    domainList.forEach((d, i) => {
      const col = i % cols, row = Math.floor(i / cols);
      const total_rows = Math.ceil(domainList.length / cols);
      domainAnchor[d] = {
        x: W * (0.15 + 0.7 * (col + 0.5) / cols),
        y: H * (0.12 + 0.76 * (row + 0.5) / total_rows),
      };
    });

    // Seed initial positions near domain anchor to bootstrap clustering
    nodes.forEach(n => {
      const a = domainAnchor[n.domain_tag] || { x: W / 2, y: H / 2 };
      n.x = a.x + (Math.random() - 0.5) * 60;
      n.y = a.y + (Math.random() - 0.5) * 60;
    });

    const sim = d3.forceSimulation(nodes)
      .force("link",
        d3.forceLink(links)
          .id(d => d.id)
          .distance(d => (1 - d.weight) * 80 + 20)
          .strength(d => 0.4 + d.weight * 0.4)
      )
      .force("charge", d3.forceManyBody().strength(-80).distanceMax(200))
      .force("clusterX",
        d3.forceX(d => (domainAnchor[d.domain_tag] || { x: W / 2 }).x).strength(0.12)
      )
      .force("clusterY",
        d3.forceY(d => (domainAnchor[d.domain_tag] || { y: H / 2 }).y).strength(0.12)
      )
      .force("collision", d3.forceCollide(d => nodeRadius(d) + 3).strength(0.8))
      .alphaDecay(0.025);

    // Edges
    const link = g.append("g").selectAll("line")
      .data(links).join("line")
      .attr("stroke", d => {
        const sn = nodeMap[d.source?.id ?? d.source];
        return sn ? domainColor(sn.domain_tag) : "#1e3a5f";
      })
      .attr("stroke-opacity", d => 0.2 + (d.weight - threshold) / (1 - threshold) * 0.6)
      .attr("stroke-width", d => 1 + (d.weight - threshold) / (1 - threshold) * 3);

    // Domain label backgrounds
    const labelGroup = g.append("g").attr("pointer-events", "none");

    // Nodes
    const node = g.append("g").selectAll("circle")
      .data(nodes).join("circle")
      .attr("r", d => nodeRadius(d) + (degree[d.id] ? Math.min(degree[d.id], 5) : 0))
      .attr("fill", nodeColor)
      .attr("fill-opacity", d => degree[d.id] ? 0.95 : 0.7)
      .attr("stroke", d => degree[d.id] ? nodeColor(d) : "#0f1117")
      .attr("stroke-width", d => degree[d.id] ? 2 : 1)
      .style("cursor", "pointer")
      .on("mouseover", (event, d) => {
        const svgRect = el.getBoundingClientRect();
        setTooltip({
          x: event.clientX - svgRect.left,
          y: event.clientY - svgRect.top,
          title: d.title,
          meta: type === "papers"
            ? `${d.source?.replace(/_/g, " ")} · ${d.citation_count ?? 0} citations · ${(d.published_date || "").slice(0, 7)}`
            : `${d.patent_number ?? ""} · ${clean(d.assignee)} · ${(d.publication_date || "").slice(0, 7)}`,
          color: nodeColor(d),
          degree: degree[d.id] || 0,
        });
      })
      .on("mouseleave", () => setTooltip(null))
      .call(
        d3.drag()
          .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
          .on("drag",  (e, d) => { d.fx = e.x; d.fy = e.y; })
          .on("end",   (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      );

    // Domain cluster labels (appear after simulation settles)
    const domainLabelData = domainList.map(d => ({ domain: d, anchor: domainAnchor[d] }));
    const domainLabels = labelGroup.selectAll("text")
      .data(domainLabelData).join("text")
      .text(d => DOMAIN_META[d.domain]?.label_ko ?? d.domain)
      .attr("x", d => d.anchor.x)
      .attr("y", d => d.anchor.y - 28)
      .attr("text-anchor", "middle")
      .attr("fill", d => DOMAIN_META[d.domain]?.color ?? "#64748b")
      .attr("font-size", 10)
      .attr("font-weight", 600)
      .attr("opacity", 0);

    let tickCount = 0;
    sim.on("tick", () => {
      tickCount++;
      link
        .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);
      // Fade in domain labels once layout settles
      if (tickCount > 80) {
        domainLabels.attr("opacity", Math.min(1, (tickCount - 80) / 40));
      }
    });

    return () => sim.stop();
  }, [data, threshold]);

  function clean(s) { return (s || "").replace(/\s*\[[A-Z]{2}\]/g, "").slice(0, 30); }

  return (
    <div style={s.wrap}>
      <div style={s.controls}>
        <span style={s.label}>노드 수</span>
        <select value={limit} onChange={e => setLimit(+e.target.value)} style={s.sel}>
          {[60, 80, 100, 120, 150].map(v => <option key={v} value={v}>{v}</option>)}
        </select>

        <span style={s.label}>유사도 임계값</span>
        <select value={threshold} onChange={e => setThreshold(+e.target.value)} style={s.sel}>
          {[0.70, 0.72, 0.75, 0.78, 0.80, 0.82, 0.85].map(v => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>

        <label style={{ ...s.label, display: "flex", alignItems: "center", gap: 5, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={balanced}
            onChange={e => setBalanced(e.target.checked)}
            style={{ accentColor: "#3b82f6" }}
          />
          도메인 균형
        </label>

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
