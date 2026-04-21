"""
PatentsView collector — USPTO patent data via the free PatentsView API v1.
No API key required.

Docs: https://search.patentsview.org/docs/
Rate limit: not officially stated; we use 1 req/s to be safe.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, KEYWORDS
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://search.patentsview.org/api/v1/patent/"
_PAGE_SIZE = 100
_RATE_LIMIT_SECS = 1.1
_MAX_RETRIES = 4

_FIELDS = [
    "patent_id",
    "patent_title",
    "patent_abstract",
    "patent_date",
    "patent_type",
    "inventors.inventor_name_first",
    "inventors.inventor_name_last",
    "assignees.assignee_organization",
    "assignees.assignee_country",
    "ipcs.ipc_section",
    "ipcs.ipc_class",
    "ipcs.ipc_subclass",
    "applications.app_date",
]


def _build_query(keyword: str, days_back: int) -> dict:
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    return {
        "_and": [
            {"_text_any": {"patent_title": keyword, "patent_abstract": keyword}},
            {"_gte": {"patent_date": since}},
        ]
    }


def _parse_patent(item: dict, keyword: str) -> dict | None:
    title = (item.get("patent_title") or "").strip()
    if not title:
        return None

    abstract = (item.get("patent_abstract") or "").replace("\n", " ").strip()

    inventors_raw = item.get("inventors") or []
    inventors = ", ".join(
        f"{i.get('inventor_name_first', '')} {i.get('inventor_name_last', '')}".strip()
        for i in inventors_raw
    )

    assignees_raw = item.get("assignees") or []
    assignee = "; ".join(
        a.get("assignee_organization", "") or ""
        for a in assignees_raw
        if a.get("assignee_organization")
    )

    country = "US"
    for a in assignees_raw:
        if a.get("assignee_country"):
            country = a["assignee_country"]
            break

    ipcs_raw = item.get("ipcs") or []
    ipc_codes = ", ".join(
        f"{i.get('ipc_section','')}{i.get('ipc_class','')}{i.get('ipc_subclass','')}".strip()
        for i in ipcs_raw
    )

    apps_raw = item.get("applications") or []
    filing_date = apps_raw[0].get("app_date", "") if apps_raw else ""

    return {
        "patent_number": item.get("patent_id", ""),
        "title": title,
        "abstract": abstract,
        "inventors": inventors,
        "assignee": assignee,
        "filing_date": filing_date,
        "publication_date": item.get("patent_date", ""),
        "ipc_codes": ipc_codes,
        "source": "patentsview",
        "country": country,
        "domain_tag": DOMAIN_TAG_MAP.get(keyword, "other"),
    }


def _fetch_page(query: dict, page: int, session: requests.Session) -> tuple[list[dict], int]:
    payload = {
        "q": query,
        "f": _FIELDS,
        "o": {"per_page": _PAGE_SIZE, "page": page},
        "s": [{"patent_date": "desc"}],
    }
    delay = 2.0
    for attempt in range(_MAX_RETRIES):
        resp = session.post(_BASE_URL, json=payload, timeout=30)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", delay))
            logger.warning("PatentsView rate-limited (attempt %d); sleeping %ds", attempt + 1, wait)
            time.sleep(wait)
            delay *= 2
            continue

        if resp.status_code >= 500:
            logger.warning("PatentsView server error %d (attempt %d); sleeping %.0fs", resp.status_code, attempt + 1, delay)
            time.sleep(delay)
            delay *= 2
            continue

        resp.raise_for_status()
        data = resp.json()
        patents = data.get("patents") or []
        total = data.get("total_patent_count") or 0
        return patents, total

    raise requests.RequestException(f"PatentsView: gave up after {_MAX_RETRIES} retries")


def fetch_patents(
    keywords: list[str] | None = None,
    days_back: int = 365,
    max_per_keyword: int = 500,
) -> Generator[dict, None, None]:
    """Yield patent dicts for each keyword."""
    if keywords is None:
        keywords = KEYWORDS

    session = requests.Session()
    session.headers.update({
        "User-Agent": "TechPulse/1.0 (research dashboard)",
        "Content-Type": "application/json",
    })

    for keyword in keywords:
        logger.info("PatentsView | keyword=%r | days_back=%d", keyword, days_back)
        query = _build_query(keyword, days_back)

        page = 1
        fetched = 0

        while fetched < max_per_keyword:
            try:
                items, total = _fetch_page(query, page, session)
            except requests.RequestException as exc:
                logger.error("PatentsView fetch failed (keyword=%r, page=%d): %s", keyword, page, exc)
                break

            if not items:
                break

            for item in items:
                patent = _parse_patent(item, keyword)
                if patent:
                    yield patent
                    fetched += 1

            logger.debug("PatentsView | keyword=%r | fetched=%d / total=%d", keyword, fetched, total)

            if fetched >= total or page * _PAGE_SIZE >= min(total, max_per_keyword):
                break

            page += 1
            time.sleep(_RATE_LIMIT_SECS)

        logger.info("PatentsView | keyword=%r | done, yielded %d patents", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
