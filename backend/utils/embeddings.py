"""
Embedding utilities using Ollama (nomic-embed-text).
Cosine similarity for semantic search.
"""
import numpy as np
import requests

from backend.utils.logger import get_logger

logger = get_logger(__name__)

OLLAMA_BASE  = "http://localhost:11434"
EMBED_MODEL  = "nomic-embed-text"


def embed_text(text: str) -> "np.ndarray | None":
    """Return float32 embedding vector, or None if Ollama is not reachable."""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text[:8000]},
            timeout=30,
        )
        resp.raise_for_status()
        return np.array(resp.json()["embedding"], dtype=np.float32)
    except Exception as exc:
        logger.debug("embed_text failed: %s", exc)
        return None


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def embed_record(title: str, abstract: str) -> "np.ndarray | None":
    """Embed title + abstract together (best for retrieval)."""
    text = f"{title}. {abstract or ''}".strip()
    return embed_text(text)
