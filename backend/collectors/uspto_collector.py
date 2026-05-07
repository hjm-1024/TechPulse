"""
USPTO collector — US patent full-text search via USPTO's EFTS API.
No API key required.

Endpoint: https://efts.uspto.gov/LATEST/search-fields
Rate limit: not officially stated; we use 1 req/s to be polite.
"""

import time
from datetime import datetime, timedelta
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, KEYWORDS
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://efts.uspto.gov/LATEST/search-fields"
_PAGE_SIZE = 100
_RATE_LIMIT_SECS = 1.1
_MAX_RETRIES = 4


def _fetch_page(keyword: str, offset: int, since: str, session: requests.Session) -> tuple[list[dict], int]:
    params = {
        "searchText": keyword,
        "dateRangeField": "datePublished",
        "startdt": since,
        "start": offset,
        "rows": _PAGE_SIZE,
    }
    delay = 2.0
    for attempt in range(_MAX_RETRIES):
        try:
            resp = session.get(_BASE_URL, params=params, timeout=30)
        except requests.RequestException as exc:
            logger.warning("USPTO request error (attempt %d): %s", attempt + 1, exc)
            time.sleep(delay)
            delay *= 2
            continue

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", delay))
            logger.warning("USPTO rate-limited (attempt %d); sleeping %ds", attempt + 1, wait)
            time.sleep(wait)
            delay *= 2
            continue

        if resp.status_code >= 500:
            logger.warning("USPTO server error %d (attempt %d); sleeping %.0fs",
                           resp.status_code, attempt + 1, delay)
            time.sleep(delay)
            delay *= 2
            continue

        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", {})
        total = (hits.get("total") or {}).get("value", 0)
        return hits.get("hits") or [], total

    raise requests.RequestException(f"USPTO: gave up after {_MAX_RETRIES} retries")


def _parse_hit(hit: dict, keyword: str) -> dict | None:
    src = hit.get("_source") or {}

    title = (src.get("inventionTitle") or "").strip()
    if not title:
        return None

    abstract = (src.get("abstractText") or "").replace("\n", " ").strip()

    first_names = src.get("inventorNameFirst") or []
    last_names  = src.get("inventorNameLast") or []
    inventors = ", ".join(
        f"{f} {l}".strip()
        for f, l in zip(first_names, last_names)
    )

    assignee = "; ".join(src.get("assigneeEntityName") or [])
    country = (src.get("countryCode") or ["US"])[0] if isinstance(src.get("countryCode"), list) else (src.get("countryCode") or "US")

    ipc_raw = src.get("intlPatentClassification") or []
    ipc_codes = ", ".join(ipc_raw[:5])

    pub_date  = (src.get("datePublished") or "")[:10]
    file_date = (src.get("dateAppl") or "")[:10]

    patent_number = src.get("patentNumber") or src.get("applicationNumber") or ""

    if not patent_number:
        return None

    return {
        "patent_number": patent_number,
        "title": title,
        "abstract": abstract,
        "inventors": inventors,
        "assignee": assignee,
        "filing_date": file_date,
        "publication_date": pub_date,
        "ipc_codes": ipc_codes,
        "source": "uspto",
        "country": country if isinstance(country, str) else "US",
        "domain_tag": DOMAIN_TAG_MAP.get(keyword, "other"),
    }


def fetch_patents(
    keywords: list[str] | None = None,
    days_back: int = 365,
    max_per_keyword: int = 500,
) -> Generator[dict, None, None]:
    """Yield US patent dicts for each keyword."""
    if keywords is None:
        keywords = KEYWORDS

    session = requests.Session()
    session.headers.update({"User-Agent": "TechPulse/1.0 (research dashboard)"})

    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    for keyword in keywords:
        logger.info("USPTO | keyword=%r | since=%s", keyword, since)

        offset = 0
        fetched = 0

        while fetched < max_per_keyword:
            try:
                hits, total = _fetch_page(keyword, offset, since, session)
            except requests.RequestException as exc:
                logger.error("USPTO fetch failed (keyword=%r, offset=%d): %s", keyword, offset, exc)
                break

            if not hits:
                break

            for hit in hits:
                patent = _parse_hit(hit, keyword)
                if patent:
                    yield patent
                    fetched += 1

            logger.debug("USPTO | keyword=%r | fetched=%d / total=%d", keyword, fetched, total)

            offset += _PAGE_SIZE
            if offset >= min(total, max_per_keyword):
                break

            time.sleep(_RATE_LIMIT_SECS)

        logger.info("USPTO | keyword=%r | done, yielded %d patents", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
