"""
Semantic Scholar Graph API collector.
Free tier: 100 requests / 5 min (no key). Set S2_API_KEY env var for higher limits.
"""
import os
import asyncio
import httpx
from typing import List, Dict

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,abstract,year,citationCount,authors,externalIds,url"


async def fetch_papers(query: str, limit: int = 100) -> List[Dict]:
    headers = {}
    api_key = os.getenv("S2_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    params = {"query": query, "limit": min(limit, 100), "fields": FIELDS}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}/paper/search", params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    papers = []
    for item in data.get("data", []):
        authors = [a.get("name", "") for a in item.get("authors", [])]
        ext_ids = item.get("externalIds") or {}
        papers.append(
            {
                "paper_id": item.get("paperId", ""),
                "title": item.get("title", ""),
                "abstract": item.get("abstract"),
                "year": item.get("year"),
                "citation_count": item.get("citationCount", 0),
                "authors": ", ".join(authors[:5]),
                "url": item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId','')}",
                "doi": ext_ids.get("DOI"),
            }
        )
    return papers
