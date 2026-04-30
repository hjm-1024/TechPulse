// Mirrors backend/db/config_schema.py DOMAIN_META — keep in sync
export const DOMAIN_META = {
  physical_ai_robotics: { label: "Physical AI & Robotics", label_ko: "물리AI/로봇",    color: "#10b981" },
  generative_ai:        { label: "Generative AI & LLM",    label_ko: "생성AI/LLM",     color: "#6366f1" },
  telecom_6g:           { label: "Telecom & 6G",           label_ko: "통신/6G",         color: "#f59e0b" },
  biotech_life_science: { label: "Biotech & Life Science", label_ko: "바이오/생명과학",  color: "#22c55e" },
  quantum:              { label: "Quantum Computing",      label_ko: "양자컴퓨팅",      color: "#8b5cf6" },
  semiconductors:       { label: "Semiconductors",         label_ko: "반도체",          color: "#ef4444" },
  clean_energy:         { label: "Clean Energy",           label_ko: "청정에너지",       color: "#fbbf24" },
  space_tech:           { label: "Space Technology",       label_ko: "우주기술",         color: "#0ea5e9" },
  bci_neurotech:        { label: "BCI & Neurotech",        label_ko: "뇌-컴인터페이스",  color: "#ec4899" },
  advanced_materials:   { label: "Advanced Materials",     label_ko: "신소재",          color: "#84cc16" },
  web3_blockchain:      { label: "Web3 & Blockchain",      label_ko: "블록체인/Web3",    color: "#f97316" },
  climate_tech:         { label: "Climate Tech",           label_ko: "기후테크",         color: "#06b6d4" },
  low_carbon:           { label: "Low-Carbon",             label_ko: "저탄소",           color: "#14b8a6" },
};

export function domainLabel(tag) {
  const m = DOMAIN_META[tag];
  return m ? `${m.label_ko}  ${m.label}` : tag;
}

export function domainColor(tag) {
  return DOMAIN_META[tag]?.color ?? "#64748b";
}
