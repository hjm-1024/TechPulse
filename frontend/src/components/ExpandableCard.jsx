import { useState, useEffect, createContext, useContext } from "react";

export const ExpandedContext = createContext(false);

const ExpandIcon = () => (
  <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d="M1 5V1h4M13 5V1H9M1 9v4h4M13 9v4H9" />
  </svg>
);
const CollapseIcon = () => (
  <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d="M5 1v4H1M9 1v4h4M5 13V9H1M9 13V9h4" />
  </svg>
);

export default function ExpandableCard({ children }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  return (
    <>
      {/* Normal card — hidden while modal is open to avoid duplicate SVG IDs */}
      <div style={{ position: "relative" }}>
        {!open && (
          <ExpandedContext.Provider value={false}>
            {children}
          </ExpandedContext.Provider>
        )}
        {!open && (
          <button onClick={() => setOpen(true)} style={s.expandBtn} title="전체화면 (F)">
            <ExpandIcon />
          </button>
        )}
        {/* Placeholder to preserve grid height while modal is open */}
        {open && <div style={s.placeholder} />}
      </div>

      {open && (
        <div style={s.overlay} onClick={(e) => e.target === e.currentTarget && setOpen(false)}>
          <div style={s.modal}>
            <button onClick={() => setOpen(false)} style={s.closeBtn} title="닫기 (ESC)">
              <CollapseIcon />
              <span style={{ marginLeft: 5, fontSize: 12 }}>닫기</span>
            </button>
            <ExpandedContext.Provider value={true}>
              {children}
            </ExpandedContext.Provider>
          </div>
        </div>
      )}
    </>
  );
}

const s = {
  expandBtn: {
    position: "absolute", top: 18, right: 18, zIndex: 2,
    display: "flex", alignItems: "center", justifyContent: "center",
    width: 28, height: 28,
    background: "rgba(30,35,48,0.85)", border: "1px solid #2d3748",
    borderRadius: 6, color: "#64748b", cursor: "pointer",
    transition: "color 0.15s, background 0.15s",
  },
  placeholder: {
    height: 320, background: "#1e2330", borderRadius: 12, opacity: 0.3,
  },
  overlay: {
    position: "fixed", inset: 0, zIndex: 1000,
    background: "rgba(0,0,0,0.8)",
    backdropFilter: "blur(4px)",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  modal: {
    position: "relative",
    width: "calc(100vw - 48px)", height: "calc(100vh - 48px)",
    maxWidth: 1600,
    background: "#131720", borderRadius: 16,
    overflow: "auto", padding: "24px 32px 32px",
    boxShadow: "0 24px 80px rgba(0,0,0,0.6)",
  },
  closeBtn: {
    position: "absolute", top: 16, right: 16, zIndex: 1,
    display: "flex", alignItems: "center",
    background: "rgba(255,255,255,0.06)", border: "1px solid #2d3748",
    borderRadius: 6, color: "#94a3b8", cursor: "pointer",
    padding: "5px 10px", fontSize: 12,
  },
};
