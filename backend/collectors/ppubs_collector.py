"""
USPTO PPUBS collector — uses the internal REST API that powers
https://ppubs.uspto.gov (USPTO Patent Public Search).

No API key or registration required. This is the same API the
USPTO's own search UI uses, so it's stable and freely accessible.
"""

import time
from datetime import datetime, timedelta
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, KEYWORDS
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_SEARCH_URL  = "https://ppubs.uspto.gov/dirsearch-public/patents/search"
_DETAIL_URL  = "https://ppubs.uspto.gov/dirsearch-public/patents/{guid}"
_SESSION_URL = "https://ppubs.uspto.gov/dirsearch-public/users/me/session"

_PAGE_SIZE = 25          # PPUBS caps at 25 per page
_RATE_LIMIT_SECS = 1.2
_MAX_RETRIES = 4


def _make_session() -> requests.Session:
    """Create a session with browser-like headers (PPUBS checks User-Agent)."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://ppubs.uspto.gov",
        "Referer": "https://ppubs.uspto.gov/",
    })
    # Establish session cookie (required by PPUBS)
    try:
        session.post(_SESSION_URL, json={}, timeout=15)
    except Exception:
        pass  # Session cookie optional; search still works most of the time
    return session


def _build_query(keyword: str, days_back: int) -> dict:
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%m-%d-%Y")
    today = datetime.utcnow().strftime("%m-%d-%Y")

    # PPUBS field codes: TTL=title, ABST=abstract
    escaped = keyword.replace('"', '\\"')
    query_str = f'(TTL/"{escaped}" OR ABST/"{escaped}")'

    return {
        "query": query_str,
        "start": 0,
        "pageCount": _PAGE_SIZE,
        "sort": "date_publ desc",
        "dateRange": "custom",
        "startDate": since,
        "endDate": today,
        "dbIds": ["US-PGPUB", "USPAT"],
        "queryId": 0,
        "domainId": 0,
    }


def _parse_patent(item: dict, keyword: str) -> dict | None:
    title = (
        item.get("title")
        or item.get("inventionTitle")
        or item.get("patent_title")
        or ""
    ).strip()
    if not title:
        return None

    abstract = (
        item.get("abstract")
        or item.get("abstractText")
        or ""
    ).replace("\n", " ").strip()

    # Patent / application number
    patent_number = (
        item.get("patentNumber")
        or item.get("documentNumber")
        or item.get("guid")
        or item.get("applicationNumber")
        or ""
    ).strip()
    if not patent_number:
        return None

    # Dates
    pub_date  = item.get("publicationDate") or item.get("date_publ") or ""
    file_date = item.get("filingDate") or item.get("applicationDate") or ""
    # Normalise YYYYMMDD → YYYY-MM-DD
    for raw in [pub_date, file_date]:
        pass
    def _fmt(d: str) -> str:
        d = d.replace("-", "").replace("/", "")
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else d

    pub_date  = _fmt(pub_date)
    file_date = _fmt(file_date)

    # Inventors
    inventors_raw = item.get("inventors") or item.get("inventorList") or []
    if isinstance(inventors_raw, list):
        inventors = ", ".join(
            (i.get("name") or f"{i.get('firstName','')} {i.get('lastName','')}").strip()
            for i in inventors_raw
            if isinstance(i, dict)
        )
    else:
        inventors = str(inventors_raw)

    # Assignees
    assignees_raw = item.get("assignees") or item.get("applicants") or []
    if isinstance(assignees_raw, list):
        assignee = "; ".join(
            (a.get("name") or a.get("orgName") or "").strip()
            for a in assignees_raw
            if isinstance(a, dict)
        )
    else:
        assignee = str(assignees_raw)

    # IPC codes
    ipc_raw = item.get("ipcCodes") or item.get("classifications") or []
    if isinstance(ipc_raw, list):
        ipc_codes = ", ".join(str(c) for c in ipc_raw[:5])
    else:
        ipc_codes = str(ipc_raw)

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
        "country": "US",
        "domain_tag": DOMAIN_TAG_MAP.get(keyword, "other"),
    }


def _fetch_page(
    payload: dict, session: requests.Session
) -> tuple[list[dict], int]:
    delay = 2.0
    for attempt in range(_MAX_RETRIES):
        try:
            resp = session.post(_SEARCH_URL, json=payload, timeout=30)
        except requests.RequestException as exc:
            logger.warning("PPUBS request error (attempt %d): %s", attempt + 1, exc)
            time.sleep(delay)
            delay *= 2
            continue

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", delay))
            logger.warning("PPUBS rate-limited (attempt %d); sleeping %ds", attempt + 1, wait)
            time.sleep(wait)
            delay *= 2
            continue

        if resp.status_code >= 500:
            logger.warning("PPUBS server error %d (attempt %d); sleeping %.0fs",
                           resp.status_code, attempt + 1, delay)
            time.sleep(delay)
            delay *= 2
            continue

        if not resp.ok:
            logger.error("PPUBS HTTP %d: %s", resp.status_code, resp.text[:300])
            return [], 0

        try:
            data = resp.json()
        except Exception:
            logger.error("PPUBS non-JSON response: %s", resp.text[:200])
            return [], 0

        # Response shape: {"totalCount": N, "patents": [...]}
        # or {"hits": {"total": N, "hits": [...]}}
        if isinstance(data, dict):
            total = (
                data.get("totalCount")
                or data.get("total")
                or (data.get("hits") or {}).get("total")
                or 0
            )
            items = (
                data.get("patents")
                or data.get("results")
                or (data.get("hits") or {}).get("hits")
                or []
            )
        elif isinstance(data, list):
            items = data
            total = len(data)
        else:
            return [], 0

        return items, int(total)

    raise requests.RequestException(f"PPUBS: gave up after {_MAX_RETRIES} retries")


def fetch_patents(
    keywords: list[str] | None = None,
    days_back: int = 365,
    max_per_keyword: int = 500,
) -> Generator[dict, None, None]:
    """Yield US patent dicts via USPTO Patent Public Search."""
    if keywords is None:
        keywords = KEYWORDS

    session = _make_session()

    for keyword in keywords:
        logger.info("PPUBS | keyword=%r | days_back=%d", keyword, days_back)
        payload = _build_query(keyword, days_back)

        fetched = 0
        page = 0

        while fetched < max_per_keyword:
            payload["start"] = page * _PAGE_SIZE

            try:
                items, total = _fetch_page(payload, session)
            except requests.RequestException as exc:
                logger.error("PPUBS fetch failed (keyword=%r, page=%d): %s", keyword, page, exc)
                break

            if not items:
                logger.debug("PPUBS | keyword=%r | no items on page %d (total=%d)", keyword, page, total)
                break

            for item in items:
                patent = _parse_patent(item, keyword)
                if patent:
                    yield patent
                    fetched += 1

            logger.debug("PPUBS | keyword=%r | page=%d | fetched=%d / total=%d",
                         keyword, page, fetched, total)

            page += 1
            if page * _PAGE_SIZE >= min(total, max_per_keyword):
                break

            time.sleep(_RATE_LIMIT_SECS)

        logger.info("PPUBS | keyword=%r | done, yielded %d patents", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
