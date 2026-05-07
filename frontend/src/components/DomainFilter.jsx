import { useState } from "react";
import { domainColor, domainLabel } from "../constants/domains";

/**
 * Highlight one domain at a time, fading the rest.
 * Pass `active=false` when the chart is in its small (collapsed) state to
 * suppress the highlight effect — the selection is preserved across toggles
 * but only renders while expanded.
 */
export function useDomainHighlight(active = true) {
  const [selected, setSelected] = useState(null);
  const effective = active ? selected : null;

  const isFaded = (tag) => effective !== null && effective !== tag;

  const styleFor = (tag) => {
    if (!isFaded(tag)) {
      return { color: domainColor(tag), opacity: 1 };
    }
    return { color: "#475569", opacity: 0.18 };
  };

  return { selected, setSelected, styleFor, isFaded };
}

/**
 * Chip row to choose the highlighted domain. Render only when expanded.
 */
export function DomainFilter({ domains, selected, onChange }) {
  if (!domains || domains.length === 0) return null;

  return (
    <div style={s.row}>
      <button
        onClick={() => onChange(null)}
        style={{
          ...s.chip,
          ...(selected === null ? s.allActive : {}),
        }}
        title="모든 도메인 표시"
      >
        전체
      </button>
      {domains.map((d) => {
        const isActive = selected === d;
        const color = domainColor(d);
        return (
          <button
            key={d}
            onClick={() => onChange(isActive ? null : d)}
            style={{
              ...s.chip,
              borderColor: isActive ? color : "#2d3748",
              background:  isActive ? color + "22" : "transparent",
              color:       isActive ? color : "#94a3b8",
            }}
          >
            <span style={{ ...s.dot, background: color }} />
            {domainLabel(d)}
          </button>
        );
      })}
    </div>
  );
}

const s = {
  row: {
    display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14,
    padding: "10px 12px", background: "#0f1117", borderRadius: 8,
  },
  chip: {
    display: "inline-flex", alignItems: "center", gap: 6,
    padding: "5px 10px", border: "1px solid #2d3748", borderRadius: 999,
    background: "transparent", color: "#94a3b8",
    fontSize: 11, fontWeight: 500, cursor: "pointer",
    whiteSpace: "nowrap", transition: "all 0.15s",
  },
  allActive: {
    borderColor: "#3b82f6",
    background:  "rgba(59,130,246,0.15)",
    color:       "#fff",
  },
  dot: { width: 8, height: 8, borderRadius: "50%" },
};
