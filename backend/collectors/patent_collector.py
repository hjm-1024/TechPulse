"""
USPTO PatentsView API collector (free, no auth required).
Docs: https://patentsview.org/apis/purpose
"""
import httpx
import json
from typing import List, Dict

BASE_URL = "https://api.patentsview.org/patents/query"

FIELDS = [
    "patent_id",
    "patent_title",
    "patent_abstract",
    "patent_date",
    "patent_type",
    "assignee_organization",
    "inventor_last_name",
    "inventor_first_name",
]


async def fetch_patents(query: str, limit: int = 100) -> List[Dict]:
    payload = {
        "q": {"_text_any": {"patent_title": query, "patent_abstract": query}},
        "f": FIELDS,
        "o": {"per_page": min(limit, 100), "page": 1},
        "s": [{"patent_date": "desc"}],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            BASE_URL,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    patents = []
    for item in (data.get("patents") or []):
        year = None
        date_str = item.get("patent_date", "")
        if date_str and len(date_str) >= 4:
            try:
                year = int(date_str[:4])
            except ValueError:
                pass

        assignees = item.get("assignees") or []
        assignee = assignees[0].get("assignee_organization", "") if assignees else ""

        inventors = item.get("inventors") or []
        inv_names = [
            f"{inv.get('inventor_first_name','')} {inv.get('inventor_last_name','')}".strip()
            for inv in inventors[:5]
        ]

        patents.append(
            {
                "patent_id": item.get("patent_id", ""),
                "title": item.get("patent_title", ""),
                "abstract": item.get("patent_abstract"),
                "year": year,
                "assignee": assignee,
                "inventors": ", ".join(inv_names),
                "country": "US",
                "url": f"https://patents.google.com/patent/US{item.get('patent_id','')}",
            }
        )
    return patents
