"""
Semantic Scholar collector — uses the public Graph API (no key required,
optional key raises rate limit from 1 req/s to 10 req/s).

Free-tier limit: 1 request / second without a key.
We skip papers with citationCount < 5 to reduce noise.
"""

import time
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, KEYWORDS, SEMANTIC_SCHOLAR_API_KEY
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "paperId,title,abstract,authors,year,citationCount,externalIds,publicationVenue"
_PAGE_SIZE = 100
_RATE_LIMIT_SECS = 1.1   # slightly over 1 s to stay safely under the 1 req/s ceiling
_MIN_CITATIONS = 5
_MAX_RETRIES = 4


def _make_session() -> requests.Session:
    session = requests.Session()
    headers = {"User-Agent": "TechPulse/1.0 (research dashboard)"}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    session.headers.update(headers)
    return session


def _parse_paper(item: dict, keyword: str, domain_tag_map=None) -> dict | None:
    title = (item.get("title") or "").strip()
    if not title:
        return None

    citation_count = item.get("citationCount") or 0
    if citation_count < _MIN_CITATIONS:
        return None

    abstract = (item.get("abstract") or "").replace("\n", " ").strip()

    authors = ", ".join(
        a.get("name", "") for a in (item.get("authors") or [])
    )

    year = item.get("year")
    published_date = f"{year}-01-01" if year else ""

    external_ids = item.get("externalIds") or {}
    doi = external_ids.get("DOI") or external_ids.get("doi") or None

    venue = item.get("publicationVenue") or {}
    journal = venue.get("name") or ""

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "published_date": published_date,
        "source": "semantic_scholar",
        "doi": doi,
        "citation_count": citation_count,
        "journal": journal,
        "domain_tag": (domain_tag_map or DOMAIN_TAG_MAP).get(keyword, "other"),
    }


def _fetch_page(
    keyword: str, offset: int, session: requests.Session
) -> tuple[list[dict], int]:
    """Return (items, total). Retries on 429/5xx with exponential backoff."""
    params = {
        "query": keyword,
        "fields": _FIELDS,
        "offset": offset,
        "limit": _PAGE_SIZE,
    }
    delay = 2.0
    for attempt in range(_MAX_RETRIES):
        resp = session.get(_BASE_URL, params=params, timeout=30)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", delay))
            logger.warning(
                "SemanticScholar rate-limited (attempt %d/%d); sleeping %ds",
                attempt + 1, _MAX_RETRIES, wait,
            )
            time.sleep(wait)
            delay *= 2
            continue

        if resp.status_code >= 500:
            logger.warning(
                "SemanticScholar server error %d (attempt %d/%d); sleeping %.0fs",
                resp.status_code, attempt + 1, _MAX_RETRIES, delay,
            )
            time.sleep(delay)
            delay *= 2
            continue

        resp.raise_for_status()
        data = resp.json()
        return data.get("data", []), data.get("total", 0)

    raise requests.RequestException(
        f"SemanticScholar: gave up after {_MAX_RETRIES} retries "
        f"(keyword={keyword!r}, offset={offset})"
    )


def fetch_papers(
    keywords: list[str] | None = None,
    days_back: int = 90,          # accepted for interface parity; SS doesn't filter by date natively
    max_per_keyword: int = 500,
    domain_tag_map: dict | None = None,
) -> Generator[dict, None, None]:
    """Yield paper dicts for each keyword, respecting the 1 req/s rate limit."""
    if keywords is None:
        keywords = KEYWORDS

    session = _make_session()

    for keyword in keywords:
        logger.info("SemanticScholar | keyword=%r", keyword)

        offset = 0
        fetched = 0

        while fetched < max_per_keyword:
            try:
                items, total = _fetch_page(keyword, offset, session)
            except requests.RequestException as exc:
                logger.error(
                    "SemanticScholar fetch failed (keyword=%r, offset=%d): %s",
                    keyword, offset, exc,
                )
                break

            if not items:
                break

            for item in items:
                paper = _parse_paper(item, keyword, domain_tag_map=domain_tag_map)
                if paper:
                    yield paper
                    fetched += 1

            logger.debug(
                "SemanticScholar | keyword=%r | fetched=%d / total=%d",
                keyword, fetched, total,
            )

            offset += _PAGE_SIZE
            if offset >= min(total, max_per_keyword):
                break

            time.sleep(_RATE_LIMIT_SECS)

        logger.info("SemanticScholar | keyword=%r | done, yielded %d papers", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
