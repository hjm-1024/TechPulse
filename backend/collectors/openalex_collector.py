"""
OpenAlex collector — uses the free public REST API.

Polite pool: supply ?mailto=<email> for better rate limits (100k req/day).

The spec requires (is_oa=true OR cited_by_count>10) AND DOAJ source.
OpenAlex filters don't support OR across different fields in a single
request, so we run two filter passes per keyword and deduplicate by DOI/title.

  Pass A: is_oa:true + DOAJ  (open-access quality signal)
  Pass B: cited_by_count:>10 + DOAJ  (impact signal)
"""

import time
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, KEYWORDS, OPENALEX_EMAIL
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://api.openalex.org/works"
_PAGE_SIZE = 100
_RATE_LIMIT_SECS = 0.15   # ~6 req/s; safely under polite-pool ceiling
_MAX_RETRIES = 4

# Two filter templates — combined with OR logic via dual pass
_FILTER_TEMPLATES = [
    "title_and_abstract.search:{kw},primary_location.source.is_in_doaj:true,is_oa:true",
    "title_and_abstract.search:{kw},primary_location.source.is_in_doaj:true,cited_by_count:>10",
]


def _make_session() -> requests.Session:
    session = requests.Session()
    ua = "TechPulse/1.0 (research dashboard)"
    if OPENALEX_EMAIL:
        ua += f"; mailto:{OPENALEX_EMAIL}"
    session.headers.update({"User-Agent": ua})
    return session


def _build_params(filter_str: str, cursor: str) -> dict:
    params: dict = {
        "filter": filter_str,
        "select": (
            "id,title,abstract_inverted_index,authorships,"
            "publication_date,doi,cited_by_count,"
            "primary_location"
        ),
        "per-page": _PAGE_SIZE,
        "cursor": cursor,
        "sort": "cited_by_count:desc",
    }
    if OPENALEX_EMAIL:
        params["mailto"] = OPENALEX_EMAIL
    return params


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex stores abstracts as an inverted index {word: [positions]}."""
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, pos_list in inverted_index.items():
        for pos in pos_list:
            positions.append((pos, word))
    positions.sort()
    return " ".join(word for _, word in positions)


def _parse_work(item: dict, keyword: str) -> dict | None:
    title = (item.get("title") or "").strip()
    if not title:
        return None

    abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))

    authors = ", ".join(
        a.get("author", {}).get("display_name", "")
        for a in (item.get("authorships") or [])
        if a.get("author")
    )

    published_date = (item.get("publication_date") or "")[:10]

    raw_doi = item.get("doi") or ""
    doi = raw_doi.replace("https://doi.org/", "").strip() or None

    citation_count = item.get("cited_by_count") or 0

    loc = item.get("primary_location") or {}
    source = loc.get("source") or {}
    journal = source.get("display_name") or ""

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "published_date": published_date,
        "source": "openalex",
        "doi": doi,
        "citation_count": citation_count,
        "journal": journal,
        "domain_tag": (_dtmap or DOMAIN_TAG_MAP).get(keyword, "other"),
    }


def _fetch_page(
    filter_str: str, cursor: str, session: requests.Session
) -> tuple[list[dict], str | None]:
    """Return (items, next_cursor). Retries on 429/5xx with exponential backoff."""
    params = _build_params(filter_str, cursor)
    delay = 2.0

    for attempt in range(_MAX_RETRIES):
        resp = session.get(_BASE_URL, params=params, timeout=30)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", delay))
            logger.warning(
                "OpenAlex rate-limited (attempt %d/%d); sleeping %ds",
                attempt + 1, _MAX_RETRIES, wait,
            )
            time.sleep(wait)
            delay *= 2
            continue

        if resp.status_code >= 500:
            logger.warning(
                "OpenAlex server error %d (attempt %d/%d); sleeping %.0fs",
                resp.status_code, attempt + 1, _MAX_RETRIES, delay,
            )
            time.sleep(delay)
            delay *= 2
            continue

        resp.raise_for_status()
        data = resp.json()
        next_cursor = (data.get("meta") or {}).get("next_cursor")
        return data.get("results", []), next_cursor

    raise requests.RequestException(
        f"OpenAlex: gave up after {_MAX_RETRIES} retries (filter={filter_str!r})"
    )


def _fetch_all_pages(
    filter_str: str,
    session: requests.Session,
    max_results: int,
    seen: set[str],
) -> Generator[dict, None, None]:
    """Paginate a single filter query, skipping already-seen titles."""
    # Extracted here so both filter passes share dedup state via `seen`.
    cursor = "*"
    fetched = 0

    while fetched < max_results:
        try:
            items, next_cursor = _fetch_page(filter_str, cursor, session)
        except requests.RequestException as exc:
            logger.error("OpenAlex page failed: %s", exc)
            break

        if not items:
            break

        for item in items:
            paper = _parse_work(
                item, _keyword_from_filter(filter_str)
            )
            if paper is None:
                continue

            dedup_key = (paper["doi"] or paper["title"].lower())
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            yield paper
            fetched += 1

        if not next_cursor:
            break

        cursor = next_cursor
        time.sleep(_RATE_LIMIT_SECS)


def _keyword_from_filter(filter_str: str) -> str:
    """Extract the raw keyword from a filter string for domain tagging."""
    # filter_str starts with "title_and_abstract.search:<keyword>,..."
    try:
        return filter_str.split("title_and_abstract.search:")[1].split(",")[0]
    except IndexError:
        return ""


def fetch_papers(
    keywords: list[str] | None = None,
    days_back: int = 90,      # accepted for interface parity; not used in OA filter
    max_per_keyword: int = 500,
    domain_tag_map: dict | None = None,
) -> Generator[dict, None, None]:
    """Yield deduplicated paper dicts for each keyword (two filter passes each)."""
    if keywords is None:
        keywords = KEYWORDS
    _dtmap = domain_tag_map

    session = _make_session()

    for keyword in keywords:
        logger.info("OpenAlex | keyword=%r", keyword)

        seen: set[str] = set()
        fetched = 0

        for template in _FILTER_TEMPLATES:
            filter_str = template.format(kw=keyword)
            pass_label = "is_oa" if "is_oa" in filter_str else "cited>10"
            logger.debug("OpenAlex | keyword=%r | pass=%s", keyword, pass_label)

            for paper in _fetch_all_pages(filter_str, session, max_per_keyword - fetched, seen):
                yield paper
                fetched += 1
                if fetched >= max_per_keyword:
                    break

            if fetched >= max_per_keyword:
                break

            time.sleep(_RATE_LIMIT_SECS)

        logger.info("OpenAlex | keyword=%r | done, yielded %d papers", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
