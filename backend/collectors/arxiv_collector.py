"""
arXiv collector — fetches papers via the arXiv Atom API (no API key required).

Rate limit: arXiv asks for ≤1 request / 3 seconds; we respect that here.
"""

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, KEYWORDS
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_BASE_URL = "http://export.arxiv.org/api/query"
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}
_PAGE_SIZE = 100
_RATE_LIMIT_SECS = 3.0


def _build_query(keyword: str, days_back: int = 90) -> str:
    # arXiv submittedDate requires 14-digit timestamps (YYYYMMDDHHMMSS)
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y%m%d000000")
    return f'(ti:"{keyword}" OR abs:"{keyword}") AND submittedDate:[{since} TO 99991231235959]'


def _parse_entry(entry: ET.Element, keyword: str) -> dict | None:
    def _text(tag: str) -> str:
        el = entry.find(tag, _NS)
        return el.text.strip() if el is not None and el.text else ""

    title = _text("atom:title").replace("\n", " ")
    abstract = _text("atom:summary").replace("\n", " ")
    published = _text("atom:published")[:10]  # YYYY-MM-DD

    authors = ", ".join(
        (a.find("atom:name", _NS).text or "").strip()
        for a in entry.findall("atom:author", _NS)
        if a.find("atom:name", _NS) is not None
    )

    # DOI from arxiv:doi element or dx.doi.org link
    doi_el = entry.find("arxiv:doi", _NS)
    doi = doi_el.text.strip() if doi_el is not None and doi_el.text else ""
    if not doi:
        for link in entry.findall("atom:link", _NS):
            href = link.get("href", "")
            if "doi.org" in href:
                doi = href.split("doi.org/")[-1]
                break

    journal_el = entry.find("arxiv:journal_ref", _NS)
    journal = journal_el.text.strip() if journal_el is not None and journal_el.text else "arXiv"

    if not title:
        return None

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "published_date": published,
        "source": "arxiv",
        "doi": doi or None,
        "citation_count": 0,
        "journal": journal,
        "domain_tag": (_dtmap or DOMAIN_TAG_MAP).get(keyword, "other"),
    }


def _fetch_page(query: str, start: int, session: requests.Session) -> ET.Element:
    params = {
        "search_query": query,
        "start": start,
        "max_results": _PAGE_SIZE,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    resp = session.get(_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return ET.fromstring(resp.text)


def _total_results(root: ET.Element) -> int:
    el = root.find("opensearch:totalResults", _NS)
    return int(el.text) if el is not None and el.text else 0


def fetch_papers(
    keywords: list[str] | None = None,
    days_back: int = 90,
    max_per_keyword: int = 500,
    domain_tag_map: dict | None = None,
) -> Generator[dict, None, None]:
    """Yield paper dicts for each keyword, respecting arXiv rate limits."""
    if keywords is None:
        keywords = KEYWORDS
    _dtmap = domain_tag_map

    session = requests.Session()
    session.headers.update({"User-Agent": "TechPulse/1.0 (research dashboard)"})

    for keyword in keywords:
        query = _build_query(keyword, days_back)
        logger.info("arXiv | keyword=%r | query=%s", keyword, query)

        start = 0
        fetched = 0

        while fetched < max_per_keyword:
            try:
                root = _fetch_page(query, start, session)
            except requests.RequestException as exc:
                logger.error("arXiv fetch failed (keyword=%r, start=%d): %s", keyword, start, exc)
                break

            total = _total_results(root)
            entries = root.findall("atom:entry", _NS)

            if not entries:
                break

            for entry in entries:
                paper = _parse_entry(entry, keyword)
                if paper:
                    yield paper
                    fetched += 1

            logger.debug("arXiv | keyword=%r | fetched=%d / total=%d", keyword, fetched, total)

            start += _PAGE_SIZE
            if start >= min(total, max_per_keyword):
                break

            time.sleep(_RATE_LIMIT_SECS)

        logger.info("arXiv | keyword=%r | done, yielded %d papers", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
