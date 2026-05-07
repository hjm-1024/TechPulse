"""
Domain catalogue for multi-label reclassification.

Each domain has a `seed_text` — a single string concatenating the human label
and representative seed keywords. We embed this once via Ollama
(nomic-embed-text) and store the result in the `domain_prototypes` table.

To add a new domain:
  1. Add an entry below.
  2. Run: python run_migration.py --steps prototypes,reclassify
"""

DOMAIN_SEEDS: dict[str, dict[str, str]] = {
    "physical_ai_robotics": {
        "label_ko": "물리적 AI·로보틱스",
        "seed_text": (
            "Physical AI and Robotics: embodied AI, humanoid robot, "
            "manipulation, dexterous grasping, mobile manipulation, "
            "sim-to-real, world model, robot learning, VLA model, "
            "imitation learning, autonomous robot."
        ),
    },
    "telecom_6g": {
        "label_ko": "통신·6G",
        "seed_text": (
            "Telecommunications and 6G: 6G, mmWave, terahertz, "
            "non-terrestrial network, NTN, reconfigurable intelligent "
            "surface, RIS, beamforming, massive MIMO, open RAN, ORAN, "
            "network slicing, mobile communication."
        ),
    },
    "quantum": {
        "label_ko": "양자",
        "seed_text": (
            "Quantum technology: quantum computing, qubit, superconducting "
            "qubit, trapped ion, quantum error correction, surface code, "
            "quantum supremacy, variational quantum algorithm, quantum "
            "sensing, quantum communication, QKD."
        ),
    },
    "semiconductors": {
        "label_ko": "반도체",
        "seed_text": (
            "Semiconductors: EUV lithography, gate-all-around, GAA, "
            "advanced packaging, chiplet, HBM, high bandwidth memory, "
            "DRAM, NAND flash, CMOS scaling, transistor, foundry, "
            "wafer fabrication, semiconductor process node."
        ),
    },
    "advanced_materials": {
        "label_ko": "신소재",
        "seed_text": (
            "Advanced materials: graphene, 2D materials, transition metal "
            "dichalcogenide, perovskite, MXene, metamaterial, nanomaterial, "
            "nanocomposite, thin film, additive manufacturing, "
            "high-entropy alloy."
        ),
    },
    "low_carbon": {
        "label_ko": "저탄소",
        "seed_text": (
            "Low carbon technology: decarbonization, net zero, carbon "
            "neutral, green steel, green hydrogen, low-carbon cement, "
            "industrial decarbonization, emission reduction, scope 3 "
            "emissions, sustainable manufacturing."
        ),
    },
    "climate_tech": {
        "label_ko": "기후 기술",
        "seed_text": (
            "Climate technology: carbon capture, CCUS, direct air capture, "
            "DAC, climate adaptation, climate model, geoengineering, "
            "negative emission, nature-based solution, climate resilience."
        ),
    },
    "energy": {
        "label_ko": "에너지",
        "seed_text": (
            "Energy technology: solid-state battery, lithium-ion battery, "
            "sodium-ion battery, hydrogen fuel cell, electrolyzer, "
            "nuclear fusion, tokamak, perovskite solar cell, "
            "renewable energy, smart grid, energy storage."
        ),
    },
    "biotech": {
        "label_ko": "바이오",
        "seed_text": (
            "Biotechnology: mRNA vaccine, CRISPR, gene editing, base "
            "editing, prime editing, protein design, AlphaFold, "
            "synthetic biology, cell therapy, CAR-T, antibody-drug "
            "conjugate, ADC, organoid, bioinformatics."
        ),
    },
    "cybersecurity": {
        "label_ko": "사이버보안",
        "seed_text": (
            "Cybersecurity: post-quantum cryptography, lattice-based "
            "cryptography, zero trust architecture, intrusion detection, "
            "malware analysis, ransomware, supply chain attack, "
            "side-channel attack, hardware security, secure enclave."
        ),
    },
    "space": {
        "label_ko": "우주",
        "seed_text": (
            "Space technology: low earth orbit, LEO satellite, satellite "
            "constellation, reusable rocket, lunar exploration, Mars "
            "rover, in-space manufacturing, space debris, space "
            "situational awareness, satellite communication."
        ),
    },
    "autonomous_driving": {
        "label_ko": "자율주행",
        "seed_text": (
            "Autonomous driving: self-driving car, LiDAR, sensor fusion, "
            "end-to-end driving, BEV perception, occupancy network, "
            "high-definition map, V2X, advanced driver assistance, ADAS, "
            "autonomous vehicle, motion planning."
        ),
    },
    "xr_metaverse": {
        "label_ko": "XR·메타버스",
        "seed_text": (
            "Extended reality and metaverse: augmented reality, AR, "
            "virtual reality, VR, mixed reality, neural rendering, NeRF, "
            "Gaussian splatting, 3D reconstruction, volumetric video, "
            "haptic feedback, spatial computing."
        ),
    },
}


def all_domain_tags() -> list[str]:
    return list(DOMAIN_SEEDS.keys())


def get_seed_text(domain_tag: str) -> str | None:
    entry = DOMAIN_SEEDS.get(domain_tag)
    return entry["seed_text"] if entry else None
