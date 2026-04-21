"""AI summarization endpoint via Ollama (qwen2.5:32b or qwen3:14b-q8_0)."""

import json
import os

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

OLLAMA_BASE    = "http://localhost:11434"
SUMMARY_MODEL  = os.getenv("OLLAMA_SUMMARY_MODEL", "qwen3:14b-q8_0")  # faster default
QUALITY_MODEL  = os.getenv("OLLAMA_QUALITY_MODEL", "qwen2.5:32b")


class SummarizeRequest(BaseModel):
    title: str
    abstract: str = ""
    type: str = "paper"   # "paper" | "patent"
    quality: bool = False  # True → use QUALITY_MODEL (slower but better)


def _build_prompt(title: str, abstract: str, doc_type: str) -> str:
    if doc_type == "patent":
        return (
            f"다음 특허를 한국어로 3~4문장으로 요약해주세요. "
            f"핵심 기술이 무엇인지, 기존 기술과 어떻게 다른지, 어떤 효과가 있는지 중심으로 설명해주세요.\n\n"
            f"특허 제목: {title}\n"
            f"초록: {abstract or '(초록 없음)'}\n\n"
            f"한국어 요약:"
        )
    return (
        f"다음 논문을 한국어로 3~4문장으로 요약해주세요. "
        f"연구 목적, 핵심 방법, 주요 결과를 중심으로 설명해주세요.\n\n"
        f"논문 제목: {title}\n"
        f"초록: {abstract or '(초록 없음)'}\n\n"
        f"한국어 요약:"
    )


@router.post("/api/summarize")
def summarize(body: SummarizeRequest):
    model = QUALITY_MODEL if body.quality else SUMMARY_MODEL
    prompt = _build_prompt(body.title, body.abstract, body.type)

    def stream():
        try:
            resp = requests.post(
                f"{OLLAMA_BASE}/api/generate",
                json={"model": model, "prompt": prompt, "stream": True,
                      "options": {"temperature": 0.3}},
                stream=True,
                timeout=120,
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
        except Exception as exc:
            yield f"\n[오류: {exc}]"

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")


@router.get("/api/ollama/status")
def ollama_status():
    """Check which models are available."""
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"available": True, "models": models,
                "summary_model": SUMMARY_MODEL, "quality_model": QUALITY_MODEL}
    except Exception:
        return {"available": False, "models": [], "summary_model": SUMMARY_MODEL}
